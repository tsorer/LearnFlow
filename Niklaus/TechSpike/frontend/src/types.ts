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
  score: number;
  retrieval_score: number;
  citation_coverage: number;
}

export interface ChunkDebugInfo {
  filename: string;
  page: number | null;
  heading: string | null;
  score: number;
  above_threshold: boolean;
  in_top_n: boolean;
  dense_rank: number;
  content: string;
}

export interface StageInfo {
  id: string;
  name: string;
  ran: boolean;
  passed: boolean;
  value: number | string | null;
  threshold: number | null;
  detail: string;
}

export interface LLMCallInfo {
  step: string;
  label: string;
  prompt: string;
  response: string;
}

export interface DebugInfo {
  chunks: ChunkDebugInfo[];
  stages: StageInfo[];
  llm_calls: LLMCallInfo[];
  similarity_threshold: number;
  min_retrieval_confidence: number;
  min_citation_coverage: number;
  self_check_ran: boolean;
  self_check_verdict: string | null;
  retrieval_detail: {
    top_score: number;
    mean_score: number;
    evidence_density: number;
    result: number;
    count: number;
  };
  params_used: Record<string, number | null>;
  dense_above_threshold: number;
  total_dense_retrieved: number;
  sparse_count: number;
  top_n_used: number;
  formula_breakdown: string;
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
  debug: DebugInfo | null;
}

export interface Document {
  id: string;
  filename: string;
  status: "pending" | "processing" | "available" | "failed";
  area: string;
  chunk_count: number;
  error_message?: string | null;
  created_at: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  answer_id?: string;
  suppressed?: boolean;
  suppression_reason?: string | null;
  citations?: Citation[];
  confidence?: ConfidenceInfo | null;
  debug?: DebugInfo | null;
}
