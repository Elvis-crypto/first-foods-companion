import { authConfigured, json, publishableKey } from "./_lib.js";

export default function handler(req, res) {
  if (req.method !== "GET") return json(res, 405, { error: "method" });
  const enabled = authConfigured();
  return json(res, 200, {
    enabled,
    publishableKey: enabled ? publishableKey() : "",
  });
}
