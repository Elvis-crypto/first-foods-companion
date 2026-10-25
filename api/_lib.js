import { createClerkClient } from "@clerk/backend";
import { neon } from "@neondatabase/serverless";

const PRODUCTION = "https://first-foods-companion.vercel.app";
const PATH_RE = /^\/(?:hu\/)?(?:about\.html|topics\/(?:[a-z0-9-]+\.html)?|recipes\/(?:[a-z0-9-]+\.html)?)?$/;
const KEY_RE = /^[a-z0-9:_-]{1,80}$/;
const MAX_BODY = 8000;

let clerk;
let schemaReady;

export function publishableKey() {
  return process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || process.env.CLERK_PUBLISHABLE_KEY || "";
}

export function databaseUrl() {
  return process.env.DATABASE_URL || process.env.POSTGRES_URL || "";
}

export function authConfigured() {
  return Boolean(publishableKey() && process.env.CLERK_SECRET_KEY && databaseUrl());
}

export function json(res, status, body) {
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.status(status).json(body);
}

export function normalizePath(input) {
  if (typeof input !== "string") return "";
  let path = input.split("?")[0].split("#")[0];
  if (!path.startsWith("/") || path.length > 180) return "";
  if (path.includes("..") || path.includes("\\") || path.includes("\0")) return "";
  path = path.replace(/\/{2,}/g, "/");
  if (path.endsWith("/index.html")) path = path.slice(0, -"index.html".length);
  if (path === "") path = "/";
  if (!PATH_RE.test(path)) return "";
  return path;
}

export function normalizeKey(input) {
  if (typeof input !== "string" || !KEY_RE.test(input)) return "";
  return input;
}

export function normalizeBody(input) {
  if (typeof input !== "string" || input.length > MAX_BODY || input.includes("\0")) return null;
  return input;
}

export function sqlClient() {
  const url = databaseUrl();
  if (!url) return null;
  return neon(url);
}

export async function ensureSchema(sql) {
  if (!schemaReady) {
    schemaReady = sql`CREATE TABLE IF NOT EXISTS text_edits (
      user_id text NOT NULL,
      page_path text NOT NULL,
      edit_key text NOT NULL,
      body text NOT NULL,
      updated_at timestamptz NOT NULL DEFAULT now(),
      PRIMARY KEY (user_id, page_path, edit_key)
    )`.catch((error) => {
      schemaReady = null;
      throw error;
    });
  }
  await schemaReady;
}

function partiesFor(req) {
  const origin = String(req.headers.origin || "");
  const list = [PRODUCTION];
  if (/^https:\/\/first-foods-companion[\w.-]*\.vercel\.app$/.test(origin)) list.push(origin);
  if (/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)) list.push(origin);
  return list;
}

function toWebRequest(req) {
  const host = req.headers["x-forwarded-host"] || req.headers.host || "first-foods-companion.vercel.app";
  const proto = String(req.headers["x-forwarded-proto"] || "https").split(",")[0].trim();
  const headers = new Headers();
  for (const [key, value] of Object.entries(req.headers)) {
    if (typeof value === "string") headers.set(key, value);
    else if (Array.isArray(value)) headers.set(key, value.join(", "));
  }
  return new Request(`${proto}://${host}${req.url || "/"}`, { method: req.method, headers });
}

export async function userIdFrom(req) {
  const secretKey = process.env.CLERK_SECRET_KEY || "";
  const key = publishableKey();
  if (!secretKey || !key) return "";
  if (!clerk) clerk = createClerkClient({ secretKey, publishableKey: key });
  const state = await clerk.authenticateRequest(toWebRequest(req), {
    acceptsToken: "session_token",
    authorizedParties: partiesFor(req),
  });
  const auth = typeof state.toAuth === "function" ? state.toAuth() : null;
  return auth && auth.userId ? String(auth.userId) : "";
}

export async function readJson(req) {
  const length = Number(req.headers["content-length"] || 0);
  if (length > 20000) {
    const error = new Error("too-large");
    error.status = 413;
    throw error;
  }
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string" && req.body) return JSON.parse(req.body);
  const chunks = [];
  for await (const chunk of req) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  if (!chunks.length) return {};
  const raw = Buffer.concat(chunks).toString("utf8");
  if (!raw) return {};
  if (raw.length > 20000) {
    const error = new Error("too-large");
    error.status = 413;
    throw error;
  }
  return JSON.parse(raw);
}
