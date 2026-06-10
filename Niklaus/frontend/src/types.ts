export type Role = "learner" | "knowledge_owner" | "admin";

export interface AuthUser {
  id: string;
  email: string;
  role: Role;
  token: string;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  filename: string;
  page: number | null;
  excerpt: string;
  index: number;
}

export interface ConfidenceInfo {
  band: "high" | "medium" | "low";
  score: number;
  retrieval_score: number;
  citation_coverage: number;
}

export interface QueryResponse {
  session_id: string;
  answer_id: string;
  suppressed: boolean;
  suppression_reason: string | null;
  message: string | null;
  refinement_hint: string | null;
  citations: Citation[];
  confidence: ConfidenceInfo | null;
}

export interface Document {
  id: string;
  filename: string;
  status: "pending" | "processing" | "available" | "failed";
  area: string;
  chunk_count: number;
  created_at: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  answer_id?: string;
  suppressed?: boolean;
  citations?: Citation[];
  confidence?: ConfidenceInfo | null;
}
