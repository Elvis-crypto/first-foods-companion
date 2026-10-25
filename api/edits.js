import {
  authConfigured,
  ensureSchema,
  json,
  normalizeBody,
  normalizeKey,
  normalizePath,
  readJson,
  sqlClient,
  userIdFrom,
} from "./_lib.js";

function queryValue(req, name) {
  if (req.query && typeof req.query[name] === "string") return req.query[name];
  const url = new URL(req.url || "/", "https://first-foods-companion.vercel.app");
  return url.searchParams.get(name) || "";
}

export default async function handler(req, res) {
  try {
    if (!authConfigured()) return json(res, 503, { error: "unavailable" });
    const method = req.method || "GET";
    if (!["GET", "PUT", "DELETE"].includes(method)) return json(res, 405, { error: "method" });

    const userId = await userIdFrom(req);
    if (!userId) return json(res, 401, { error: "signed-out" });

    const sql = sqlClient();
    if (!sql) return json(res, 503, { error: "unavailable" });
    await ensureSchema(sql);

    if (method === "GET") {
      const path = normalizePath(queryValue(req, "path"));
      if (!path) return json(res, 400, { error: "path" });
      const rows = await sql`
        SELECT edit_key, body
        FROM text_edits
        WHERE user_id = ${userId} AND page_path = ${path}
        ORDER BY edit_key
        LIMIT 500
      `;
      const edits = {};
      for (const row of rows) {
        if (typeof row.body === "string") edits[row.edit_key] = row.body;
      }
      return json(res, 200, { edits });
    }

    const payload = await readJson(req);
    const path = normalizePath(payload && payload.path);
    if (!path) return json(res, 400, { error: "path" });

    if (method === "DELETE" && payload && payload.reset === true) {
      await sql`DELETE FROM text_edits WHERE user_id = ${userId} AND page_path = ${path}`;
      return json(res, 200, { ok: true });
    }

    const key = normalizeKey(payload && payload.key);
    if (!key) return json(res, 400, { error: "key" });

    if (method === "DELETE") {
      await sql`
        DELETE FROM text_edits
        WHERE user_id = ${userId} AND page_path = ${path} AND edit_key = ${key}
      `;
      return json(res, 200, { ok: true });
    }

    const body = normalizeBody(payload && payload.body);
    if (body === null) return json(res, 400, { error: "body" });
    await sql`
      INSERT INTO text_edits (user_id, page_path, edit_key, body)
      VALUES (${userId}, ${path}, ${key}, ${body})
      ON CONFLICT (user_id, page_path, edit_key)
      DO UPDATE SET body = EXCLUDED.body, updated_at = now()
    `;
    return json(res, 200, { ok: true });
  } catch (error) {
    const status = error && error.status === 413 ? 413 : 500;
    return json(res, status, { error: status === 413 ? "too-large" : "unavailable" });
  }
}
