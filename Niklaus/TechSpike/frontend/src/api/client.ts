import type { Document, QueryResponse } from "../types";

const BASE = "/api";

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
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
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
