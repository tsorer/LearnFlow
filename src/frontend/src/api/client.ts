import type { Document, QueryResponse } from "../types";

const BASE = "/api";

/** Carries the HTTP status so callers can tell 429 (rate limited) from 401. */
export class ApiError extends Error {
  constructor(readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

let onUnauthorized: (() => void) | null = null;

/**
 * Registers the session teardown that runs when the API rejects an
 * authenticated request with 401 — typically an expired JWT (T-06: 1 h).
 * Without it a 401 only surfaces as a generic error and the user is stranded
 * on a dead page instead of being sent back to the login (T-40).
 */
export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

async function req<T>(
  method: string,
  path: string,
  token?: string,
  body?: unknown,
  isForm = false,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (!isForm && body) headers["Content-Type"] = "application/json";

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: isForm ? (body as FormData) : body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    // Only a request that carried a token can have an expired session. A 401
    // from /auth/login (which sends none) stays a credentials error and must
    // not be reported as "Sitzung abgelaufen".
    if (res.status === 401 && token) onUnauthorized?.();
    const text = await res.text();
    throw new ApiError(res.status, text || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    req<{ access_token: string; role: string }>("POST", "/auth/login", undefined, { email, password }),

  me: (token: string) =>
    req<{ id: string; email: string; role: string }>("GET", "/auth/me", token),

  query: (question: string, session_id: string | null, token: string) =>
    req<QueryResponse>("POST", "/query", token, { question, session_id }),

  listDocuments: (token: string) =>
    req<Document[]>("GET", "/documents", token),

  uploadDocument: (file: File, area: string, token: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("area", area);
    return req<Document>("POST", "/documents", token, form, true);
  },

  deleteDocument: (id: string, token: string) =>
    req<void>("DELETE", `/documents/${id}`, token),

  submitFeedback: (answerId: string, rating: number, comment: string | null, token: string) =>
    req<void>("POST", `/answers/${answerId}/feedback`, token, { rating, comment }),

  getConfig: (token: string) =>
    req<{ config: Record<string, string> }>("GET", "/admin/config", token),

  updateConfig: (config: Record<string, string>, token: string) =>
    req<{ config: Record<string, string> }>("PUT", "/admin/config", token, { config }),
};
