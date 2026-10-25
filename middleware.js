// First visit follows the IP country. A lang cookie from the language menu wins after that.
import { next } from "@vercel/functions";

const STATIC = /\.(?:css|js|jpg|jpeg|png|webp|svg|ico|txt|xml|json|woff2?)$/i;

function cookie(request, name) {
  const raw = request.headers.get("cookie") || "";
  const match = raw.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
  return match ? decodeURIComponent(match[1]) : "";
}

function toHungarian(path) {
  if (path === "/hu" || path.startsWith("/hu/")) return path;
  if (path === "/") return "/hu/";
  return "/hu" + path;
}

function toEnglish(path) {
  if (path === "/hu") return "/";
  if (path.startsWith("/hu/")) return path.slice(3) || "/";
  return path;
}

export default function middleware(request) {
  const url = new URL(request.url);
  const path = url.pathname;
  if (path.startsWith("/assets/") || STATIC.test(path)) return next();

  const chosen = cookie(request, "lang");
  const country = request.headers.get("x-vercel-ip-country") || "";
  const lang = chosen === "hu" || chosen === "en" ? chosen : country === "HU" ? "hu" : "en";
  const target = lang === "hu" ? toHungarian(path) : toEnglish(path);
  if (target === path) return next();

  url.pathname = target;
  return Response.redirect(url, 307);
}

export const config = {
  matcher: ["/((?!assets/).*)"],
};
