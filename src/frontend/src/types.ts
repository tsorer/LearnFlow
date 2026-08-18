// UI-only types. Everything crossing the API boundary comes from the generated
// schema (T-39) — the source is src/backend/openapi.yaml, not this file.
// Citation, ConfidenceInfo, DebugInfo and QueryResponse used to be hand-written
// here and had drifted from the spec; that is what this arrangement prevents.
import type {
  ChunkDebugInfo,
  Citation,
  ConfidenceInfo,
  DebugInfo,
  DocumentResponse,
  LLMCallInfo,
  QueryResponse,
  Role,
  StageInfo,
} from "./api/client";

// Re-exported are the ones components actually import from here. Role and
// Citation are needed internally only (AuthUser resp. Message); anyone needing
// them directly takes them from ./api/client.
export type { ChunkDebugInfo, ConfidenceInfo, DebugInfo, LLMCallInfo, StageInfo };

/**
 * The closed set of `suppression_reason` values, straight from the spec enum —
 * so a reason added in openapi.yaml breaks the label map at compile time
 * instead of surfacing the raw key to the user.
 */
export type SuppressionReason = NonNullable<QueryResponse["suppression_reason"]>;

/** A document as the API returns it. */
export type Document = DocumentResponse;

/** Signed-in user including the token — the token lives in memory only (ADR-002). */
export interface AuthUser {
  id: string;
  email: string;
  role: Role;
  token: string;
}

/**
 * One line in the chat transcript. Client-side only: the API knows answers, not
 * messages — the fields from `answer_id` on are the parts of a QueryResponse
 * this component keeps.
 */
export interface Message {
  role: "user" | "assistant";
  content: string;
  answer_id?: string;
  suppressed?: boolean;
  suppression_reason?: SuppressionReason | null;
  citations?: Citation[];
  confidence?: ConfidenceInfo | null;
  debug?: DebugInfo | null;
}
