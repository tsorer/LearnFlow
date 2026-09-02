/**
 * @vitest-environment jsdom
 *
 * T-54: the admin chunk panel has to explain its own order (Issue #115).
 *
 * The panel sorts by RRF but showed neither the sparse rank nor the RRF score,
 * so a chunk below the similarity threshold could sit in the LLM context above
 * one well over it with nothing on screen saying why. That is not a bug in the
 * pipeline — RRF fuses ranks, not scores (ADR-007) — but the view could not
 * say so.
 *
 * The cases are written as the three things an admin has to be able to read off
 * a row: where each search ranked the chunk, what that produced, and why a red
 * chunk is nevertheless in the context.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import App from "./App";
import { installApiStub, installAppEnvironment, type ApiStub } from "../test/api";
import type { ChunkDebugInfo, DebugInfo, QueryResponse } from "./api/client";

let api: ApiStub;

/** `RANK_ABSENT` in app/services/retrieval.py: this search did not find it. */
const ABSENT = 0;

function chunk(overrides: Partial<ChunkDebugInfo> = {}): ChunkDebugInfo {
  return {
    chunk_id: "chunk-1",
    document_id: "doc-1",
    filename: "skos-richtlinien.pdf",
    page: 7,
    heading: "Hierarchische Relationen",
    score: 0.62,
    above_threshold: true,
    in_top_n: true,
    dense_rank: 1,
    sparse_rank: 2,
    rrf_score: 0.032522,
    content: "Ein Chunk mit Inhalt.",
    ...overrides,
  };
}

/**
 * The chunk from the issue: a pure full-text hit, below the threshold, and in
 * the context anyway because it is rank 1 on the sparse side.
 */
const SPARSE_ONLY = chunk({
  chunk_id: "chunk-2",
  filename: "eu-ai-act_de.pdf",
  page: 12,
  heading: "Art. 6 Hochrisiko-Einstufung",
  score: 0.24,
  above_threshold: false,
  in_top_n: true,
  dense_rank: ABSENT,
  sparse_rank: 1,
  rrf_score: 0.016393,
});

function debugInfo(chunks: ChunkDebugInfo[]): DebugInfo {
  return {
    chunks,
    stages: [],
    llm_calls: [],
    similarity_threshold: 0.41,
    min_retrieval_confidence: 0.4,
    min_citation_coverage: 0.5,
    self_check_ran: false,
    retrieval_detail: { top_score: 0.62, mean_score: 0.43, evidence_density: 0.4, result: 0.55, count: 2 },
    params_used: { rrf_k: 60, context_top_n: 5 },
    dense_above_threshold: 1,
    total_dense_retrieved: 5,
    sparse_count: 4,
    top_n_used: 2,
    formula_breakdown: "0.5*0.55 + 0.5*0.9",
  };
}

function answer(chunks: ChunkDebugInfo[]): QueryResponse {
  return {
    session_id: "sess-1",
    answer_id: "ans-1",
    suppressed: false,
    suppression_reason: null,
    message: "Der AI Act stuft Systeme nach Risiko ein.",
    refinement_hint: null,
    citations: [],
    confidence: { score: 0.72, retrieval_score: 0.55, citation_coverage: 0.9, band: "mittel" },
    debug: debugInfo(chunks),
  };
}

/** Signs in as an admin and asks one question, so the debug panel is on screen. */
async function ask(response: QueryResponse) {
  api.route("post", "/api/auth/login", 200, {
    access_token: "tok123",
    token_type: "bearer",
    role: "admin",
  });
  api.route("get", "/api/auth/me", 200, {
    id: "u1",
    email: "admin@learnflow.ch",
    role: "admin",
  });
  // The panel loads it on mount for the admin role; shape per the spec.
  api.route("get", "/api/admin/config", 200, { config: {} });
  api.route("post", "/api/query", 200, response);

  render(<App />);
  await userEvent.type(screen.getByLabelText(/e-mail/i), "admin@learnflow.ch");
  await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
  await userEvent.type(await screen.findByLabelText("Frage"), "Was regelt der EU AI Act?");
  await userEvent.click(screen.getByRole("button", { name: /senden/i }));
  await screen.findByText(response.message!);
}

beforeEach(() => {
  api = installApiStub();
  installAppEnvironment();
});

afterEach(() => {
  api.release();
  cleanup();
  vi.unstubAllGlobals();
});

describe("Herkunft je Chunk (T-54)", () => {
  it("zeigt beide Ränge auch bei einem Chunk mit LLM-Badge", async () => {
    // The regression the issue names: `in_top_n` used to replace the rank
    // entirely, so the five chunks that actually reach the LLM were the only
    // ones showing no provenance at all.
    await ask(answer([SPARSE_ONLY]));

    // Scoped to the row: the legend carries an "LLM" badge of its own, and the
    // point here is that badge and ranks now share one row instead of one
    // replacing the other.
    const row = screen.getByText(/eu-ai-act_de\.pdf/).parentElement!;
    expect(within(row).getByTitle("Volltextsuche: Rang 1")).toHaveTextContent("1");
    expect(within(row).getByTitle("Vektorsuche: nicht gefunden")).toBeInTheDocument();
    expect(within(row).getByText("LLM")).toBeInTheDocument();
  });

  it("rendert RANK_ABSENT als Gedankenstrich, nicht als «#0»", async () => {
    await ask(answer([SPARSE_ONLY]));

    expect(screen.getByTitle("Vektorsuche: nicht gefunden")).toHaveTextContent("—");
    expect(screen.queryByText("#0")).not.toBeInTheDocument();
  });

  it("macht den RRF-Score ablesbar, mit der Rechnung dahinter", async () => {
    await ask(answer([chunk(), SPARSE_ONLY]));

    // Visible in the row …
    expect(screen.getByText(".0325")).toBeInTheDocument();
    // … and the arithmetic that produced it, with the k of this request. Both
    // ranks contribute for a chunk found twice, one for a chunk found once.
    expect(screen.getByTitle("RRF 1/(60+1) + 1/(60+2) = 0.032522")).toBeInTheDocument();
    expect(screen.getByTitle("RRF 1/(60+1) = 0.016393")).toBeInTheDocument();
  });

  it("erklärt einen roten Chunk im Kontext aus der Zeile heraus", async () => {
    // The acceptance criterion, verbatim: "im Kontext, weil Sparse-Rang 1, bei
    // Cosine 0.24" has to be readable without leaving the panel.
    await ask(answer([SPARSE_ONLY]));

    await userEvent.click(screen.getByText(/eu-ai-act_de\.pdf/));

    expect(screen.getByText(/Dense — nicht gefunden · Sparse 1/)).toBeInTheDocument();
    expect(screen.getByText("1/(60+1) = 0.016393")).toBeInTheDocument();
    expect(screen.getByText(/0\.24 — unter Schwelle 0\.41/)).toBeInTheDocument();
    expect(
      screen.getByText(/Nur die Volltextsuche hat ihn gefunden.*Trotzdem im Kontext/s),
    ).toBeInTheDocument();
  });

  it("erklärt umgekehrt auch einen Chunk über Schwelle, der weggeschnitten wurde", async () => {
    const cut = chunk({ chunk_id: "chunk-3", in_top_n: false, sparse_rank: ABSENT, rrf_score: 0.015625 });
    await ask(answer([cut]));

    await userEvent.click(screen.getByText(/skos-richtlinien\.pdf/));

    expect(
      screen.getByText(/Über der Schwelle, aber nicht im Kontext/),
    ).toBeInTheDocument();
  });

  it("sagt einem Screenreader, was der Gedankenstrich bedeutet", async () => {
    // Der Strich ist ein rein optisches Signal, und `title` wird nicht
    // verlässlich vorgelesen. Dieselbe Lösung wie bei QuizCard: die Aussage
    // steht als .sr-only-Text daneben, die Glyphe ist aria-hidden.
    await ask(answer([SPARSE_ONLY]));

    const cell = screen.getByTitle("Vektorsuche: nicht gefunden");
    const spoken = within(cell).getByText("Vektorsuche: nicht gefunden");
    expect(spoken).toHaveClass("sr-only");
    expect(within(cell).getByText("—")).toHaveAttribute("aria-hidden", "true");
  });

  it("benennt die neuen Spalten in einer Kopfzeile", async () => {
    await ask(answer([chunk()]));

    const header = screen.getByTitle(/Sortierschlüssel/);
    expect(header).toHaveTextContent("RRF");
    expect(within(header.parentElement!).getByTitle("Rang in der Vektorsuche")).toHaveTextContent("D");
    expect(within(header.parentElement!).getByTitle("Rang in der Volltextsuche")).toHaveTextContent("S");
  });
});
