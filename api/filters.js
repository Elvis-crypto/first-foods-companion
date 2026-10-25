import {
  authConfigured,
  ensureSchema,
  json,
  normalizeFilters,
  readJson,
  sqlClient,
  userIdFrom,
} from "./_lib.js";

export default async function handler(req, res) {
  try {
    if (!authConfigured()) return json(res, 503, { error: "unavailable" });
    const method = req.method || "GET";
    if (method !== "GET" && method !== "PUT") return json(res, 405, { error: "method" });

    const userId = await userIdFrom(req);
    if (!userId) return json(res, 401, { error: "signed-out" });

    const sql = sqlClient();
    if (!sql) return json(res, 503, { error: "unavailable" });
    await ensureSchema(sql);

    if (method === "GET") {
      const rows = await sql`SELECT body FROM user_filters WHERE user_id = ${userId} LIMIT 1`;
      const raw = rows[0] && typeof rows[0].body === "string" ? rows[0].body : "";
      let filters = null;
      if (raw) {
        try {
          filters = normalizeFilters(JSON.parse(raw));
        } catch {
          filters = null;
        }
      }
      return json(res, 200, { filters });
    }

    const payload = await readJson(req);
    const filters = normalizeFilters(payload && payload.filters);
    if (!filters) return json(res, 400, { error: "filters" });
    await sql`
      INSERT INTO user_filters (user_id, body)
      VALUES (${userId}, ${JSON.stringify(filters)})
      ON CONFLICT (user_id) DO UPDATE SET body = EXCLUDED.body, updated_at = now()
    `;
    return json(res, 200, { ok: true });
  } catch (error) {
    const status = error && error.status === 413 ? 413 : 500;
    return json(res, status, { error: status === 413 ? "too-large" : "unavailable" });
  }
}
