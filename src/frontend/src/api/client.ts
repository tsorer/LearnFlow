// Typed against openapi.yaml (ADR-010). Every path, method, body and response
// below is checked against src/api/schema.d.ts, which is generated from the
// spec — a backend change that alters the contract breaks this file at compile
// time instead of at runtime. Regenerate with `npm run generate:api`; CI fails
// if the committed types no longer match the spec.
import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

type Schemas = components["schemas"];

// Exported are the ones named elsewhere (types.ts builds Message and AuthUser
// on them). The rest only serve as signatures in this module — callers get
// them inferred anyway.
export type Role = Schemas["Role"];
export type Citation = Schemas["Citation"];
export type ConfidenceInfo = Schemas["ConfidenceInfo"];
export type DebugInfo = Schemas["DebugInfo"];
export type ChunkDebugInfo = Schemas["ChunkDebugInfo"];
export type StageInfo = Schemas["StageInfo"];
export type LLMCallInfo = Schemas["LLMCallInfo"];
export type DocumentResponse = Schemas["DocumentResponse"];

type User = Schemas["User"];
type TokenResponse = Schemas["TokenResponse"];
export type QueryResponse = Schemas["QueryResponse"];
export type FeedbackCategory = Schemas["FeedbackCategory"];

/** Carries the HTTP status so callers can tell 429 from 401 from 501. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
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

// Paths in the schema already carry the /api prefix that nginx rewrites away,
// so the base only supplies the origin. It has to be absolute: openapi-fetch
// builds a `Request`, and outside a browser (jsdom, Node) that rejects a
// relative URL — with an empty base the whole client throws under test.
const client = createClient<paths>({
  baseUrl: typeof window === "undefined" ? "http://localhost" : window.location.origin,
  // Resolved per call instead of captured at creation: createClient runs on
  // module import, so a fetch replaced later — a test stub, instrumentation —
  // would otherwise never be seen.
  fetch: (request) => globalThis.fetch(request),
});

client.use({
  onResponse({ request, response }) {
    // Only a request that carried a token can have an expired session. A 401
    // from /auth/login (which sends none) stays a credentials error and must
    // not be reported as "Sitzung abgelaufen".
    if (response.status === 401 && request.headers.get("Authorization")) {
      onUnauthorized?.();
    }
    return undefined;
  },
});

const auth = (token: string) => ({ Authorization: `Bearer ${token}` });

/** One FastAPI validation error out of the list its 422 responses carry. */
interface ValidationItem {
  msg?: unknown;
  loc?: unknown[];
}

/**
 * Turns an error body into the text the UI shows. Three shapes reach this,
 * and each has a caller that renders it verbatim (Upload.tsx, Login.tsx):
 *
 *   {"detail": "…"}        our own HTTPExceptions
 *   {"detail": [{…}, …]}   FastAPI request validation — a list, so plain
 *                          stringification would yield "[object Object]"
 *   plain text / HTML      nginx (413, 502) never produces JSON
 */
function errorMessage(error: unknown, status: number): string {
  if (typeof error === "string" && error.trim() !== "") return error;

  const detail = (error as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail !== "") return detail;

  if (Array.isArray(detail)) {
    const messages = (detail as ValidationItem[])
      .map(item => {
        const field = Array.isArray(item.loc) ? item.loc.filter(p => p !== "body").join(".") : "";
        return field ? `${field}: ${String(item.msg)}` : String(item.msg);
      })
      .filter(Boolean);
    if (messages.length > 0) return messages.join("; ");
  }

  return `HTTP ${status}`;
}

/** openapi-fetch returns errors instead of throwing; the app expects throws. */
function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.error !== undefined || !result.response.ok) {
    throw new ApiError(result.response.status, errorMessage(result.error, result.response.status));
  }
  return result.data as T;
}

export const api = {
  login: async (email: string, password: string): Promise<TokenResponse> =>
    unwrap(await client.POST("/api/auth/login", { body: { email, password } })),

  me: async (token: string): Promise<User> =>
    unwrap(await client.GET("/api/auth/me", { headers: auth(token) })),

  logout: async (token: string): Promise<void> => {
    unwrap(await client.POST("/api/auth/logout", { headers: auth(token) }));
  },

  query: async (
    question: string,
    session_id: string | null,
    token: string,
  ): Promise<QueryResponse> =>
    unwrap(
      await client.POST("/api/query", { headers: auth(token), body: { question, session_id } }),
    ),

  listDocuments: async (token: string): Promise<DocumentResponse[]> =>
    unwrap(await client.GET("/api/documents", { headers: auth(token) })),

  uploadDocument: async (file: File, area: string, token: string): Promise<DocumentResponse> =>
    unwrap(
      await client.POST("/api/documents", {
        headers: auth(token),
        body: { file: file as unknown as string, area },
        // multipart/form-data: the generated type models `file` as a binary
        // string, the wire format needs a real FormData.
        bodySerializer(body) {
          const form = new FormData();
          form.append("file", file);
          // Sent whenever the caller supplied one, empty string included: the
          // backend rejects a non-pilot area with 422, and dropping the field
          // would turn that rejection into a silent default instead.
          if (body?.area !== undefined) form.append("area", body.area);
          return form;
        },
      }),
    ),

  deleteDocument: async (id: string, token: string): Promise<void> => {
    unwrap(
      await client.DELETE("/api/documents/{document_id}", {
        headers: auth(token),
        params: { path: { document_id: id } },
      }),
    );
  },

  submitFeedback: async (
    answerId: string,
    helpful: boolean,
    category: FeedbackCategory | null,
    comment: string | null,
    token: string,
  ): Promise<void> => {
    unwrap(
      await client.POST("/api/answers/{answer_id}/feedback", {
        headers: auth(token),
        params: { path: { answer_id: answerId } },
        body: { helpful, category, comment },
      }),
    );
  },

  getConfig: async (token: string): Promise<Record<string, string>> =>
    unwrap(await client.GET("/api/admin/config", { headers: auth(token) })).config,

  updateConfig: async (
    config: Record<string, string>,
    token: string,
  ): Promise<Record<string, string>> =>
    unwrap(await client.PUT("/api/admin/config", { headers: auth(token), body: { config } }))
      .config,
};
