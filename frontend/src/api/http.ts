// frontend/src/api/http.ts
// Low-level fetch wrapper. No auth, no retries: those live in api/client.ts.

import { API_BASE } from "@/config/env";
import { ApiError, ErrorCode } from "@/exceptions/errors";

export type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  query?: Record<string, QueryValue>;
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = API_BASE + path;
  if (!query) return url;
  // URLSearchParams encodes "+" as %2B, which timestamps with offsets need.
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

function validationMessage(items: unknown[]): string {
  const parts = items.slice(0, 3).map((item) => {
    const { loc, msg } = item as { loc?: unknown[]; msg?: string };
    const last = loc && loc.length > 0 ? loc[loc.length - 1] : "";
    const field = String(last).replace(/_/g, " ");
    const text = (msg ?? "Invalid value").replace(/^Value error, /, "").replace(/\.$/, "");
    return field ? `${field[0].toUpperCase()}${field.slice(1)}: ${text}.` : `${text}.`;
  });
  return parts.join(" ") || "Check the fields and try again.";
}

async function parseError(res: Response): Promise<ApiError> {
  const retry = Number(res.headers.get("Retry-After"));
  const retryAfter = Number.isFinite(retry) && retry > 0 ? retry : undefined;

  let detail: unknown;
  try {
    detail = (await res.json())?.detail;
  } catch {
    detail = undefined;
  }

  if (detail && typeof detail === "object" && !Array.isArray(detail) && "code" in detail) {
    const d = detail as { code: string; message?: string };
    return new ApiError(res.status, d.code, d.message ?? "Request failed.", retryAfter);
  }
  // FastAPI's own request validation (422) returns a list, not {code, message}.
  if (Array.isArray(detail)) {
    return new ApiError(res.status, ErrorCode.Validation, validationMessage(detail));
  }
  if (typeof detail === "string") return new ApiError(res.status, ErrorCode.Http, detail);
  if (res.status >= 500) return new ApiError(res.status, ErrorCode.Server, "Server error.");
  return new ApiError(res.status, ErrorCode.Http, `Request failed (${res.status}).`);
}

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json", ...opts.headers };
  let body: string | undefined;
  if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.body);
  }

  let res: Response;
  try {
    res = await fetch(buildUrl(path, opts.query), {
      method: opts.method ?? "GET",
      headers,
      body,
      signal: opts.signal,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw new ApiError(0, ErrorCode.Network, "Can't reach the server.");
  }
  if (!res.ok) throw await parseError(res);
  return res;
}

export async function requestJson<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await send(path, opts);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function requestBlob(path: string, opts: RequestOptions = {}): Promise<Blob> {
  const res = await send(path, { ...opts, headers: { Accept: "image/png", ...opts.headers } });
  return res.blob();
}
