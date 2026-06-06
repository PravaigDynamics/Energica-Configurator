import type { NextApiRequest, NextApiResponse } from "next";

function getBackendUrl(): string {
  if (process.env.BACKEND_URL) return process.env.BACKEND_URL;
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}/_/backend`;
  return "http://localhost:8000";
}

export const config = { api: { bodyParser: true, responseLimit: false } };

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const segments = Array.isArray(req.query.path) ? req.query.path : [req.query.path ?? ""];
  const path = segments.join("/");

  const { path: _p, ...rest } = req.query;
  const qs = new URLSearchParams();
  Object.entries(rest).forEach(([k, v]) =>
    Array.isArray(v) ? v.forEach((x) => qs.append(k, x)) : v && qs.set(k, v)
  );
  const qString = qs.toString();
  const targetUrl = `${getBackendUrl()}/${path}${qString ? "?" + qString : ""}`;

  const fetchOptions: RequestInit = { method: req.method };
  if (req.method !== "GET" && req.method !== "HEAD" && req.body) {
    fetchOptions.headers = { "Content-Type": "application/json" };
    fetchOptions.body = JSON.stringify(req.body);
  }

  let upstream: Response;
  try {
    upstream = await fetch(targetUrl, fetchOptions);
  } catch (err) {
    res.status(502).json({ detail: `Upstream unreachable: ${(err as Error).message}` });
    return;
  }

  const contentType = upstream.headers.get("content-type") ?? "";
  res.status(upstream.status);

  if (contentType.includes("image/")) {
    res.setHeader("Content-Type", contentType);
    const buf = await upstream.arrayBuffer();
    res.send(Buffer.from(buf));
  } else {
    res.setHeader("Content-Type", contentType || "application/json");
    res.send(await upstream.text());
  }
}
