/**
 * @vitest-environment jsdom
 *
 * T-27: what a learner is told about how well an answer is backed (US-02).
 *
 * The pipeline behind it is tested in the backend; what is under test here is
 * the last step, which had no reader until now. Two of the three states the
 * spec describes never reached the screen: `confidence.band` appeared only in
 * the admin debug panel, and `refinement_hint` — filled by the backend for
 * every suppression (Requirements §71) — was not carried out of the response at
 * all.
 *
 * The cases are written as the three states a learner can end up in, because
 * the acceptance criterion is that they are distinguishable: an answer that
 * stands on its sources, one that only partly does, and one that was withheld.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import App from "./App";
import { installApiStub, installAppEnvironment, type ApiStub } from "../test/api";
import type { DebugInfo, QueryResponse } from "./api/client";

let api: ApiStub;

/**
 * Typed against the spec, like the fixture in query.test.tsx — a state the API
 * could never produce cannot be asserted on here.
 */
function answer(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return {
    session_id: "sess-1",
    answer_id: "ans-1",
    suppressed: false,
    suppression_reason: null,
    message: "SKOS verlangt je Sprache genau ein prefLabel.",
    refinement_hint: null,
    citations: [
      {
        chunk_id: "chunk-1",
        document_id: "doc-1",
        filename: "skos.pdf",
        page: 1,
        excerpt: "Ein Auszug.",
        index: 1,
      },
    ],
    confidence: { score: 0.82, retrieval_score: 0.82, citation_coverage: 0.9, band: "hoch" },
    debug: null,
    ...overrides,
  };
}

/**
 * The `debug` payload the API sends to the admin role and to nobody else
 * (openapi.yaml). Only `params_used` carries anything a case here reads; the
 * rest is filled because the schema requires it, which is also what keeps this
 * fixture honest — a field added to DebugInfo fails the type check instead of
 * quietly missing from the admin view under test.
 */
function debugInfo(overrides: Partial<DebugInfo> = {}): DebugInfo {
  return {
    chunks: [],
    stages: [],
    llm_calls: [],
    similarity_threshold: 0.35,
    min_retrieval_confidence: 0.4,
    min_citation_coverage: 0.5,
    self_check_ran: false,
    retrieval_detail: {
      top_score: 0.8,
      mean_score: 0.6,
      evidence_density: 0.5,
      result: 0.59,
      count: 5,
    },
    params_used: { min_retrieval_confidence: 0.4, min_citation_coverage: 0.5 },
    dense_above_threshold: 5,
    total_dense_retrieved: 20,
    sparse_count: 12,
    top_n_used: 5,
    formula_breakdown: "0.4*0.59 + …",
    ...overrides,
  };
}

/** Signs in as a learner and asks one question, so the bubble is on screen. */
async function ask(response: QueryResponse) {
  api.route("post", "/api/auth/login", 200, {
    access_token: "tok123",
    token_type: "bearer",
    role: "learner",
  });
  api.route("get", "/api/auth/me", 200, {
    id: "u1",
    email: "lara@learnflow.ch",
    role: "learner",
  });
  api.route("post", "/api/query", 200, response);

  render(<App />);
  await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
  await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
  await userEvent.type(await screen.findByLabelText("Frage"), "Was verlangt SKOS je Sprache?");
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

// --- AK 1: the "Eingeschränkt belegt" badge --------------------------------

describe("Band «mittel»", () => {
  it("markiert die Antwort als eingeschränkt belegt", async () => {
    await ask(answer({
      confidence: { score: 0.6, retrieval_score: 0.6, citation_coverage: 0.5, band: "mittel" },
    }));

    expect(screen.getByText(/Eingeschränkt belegt/)).toBeInTheDocument();
  });

  it("nennt dazu, was der Lernende tun soll — Farbe und Icon allein sagen es nicht", async () => {
    await ask(answer({
      confidence: { score: 0.6, retrieval_score: 0.6, citation_coverage: 0.5, band: "mittel" },
    }));

    expect(screen.getByRole("note", { name: /Belegung der Antwort/i }))
      .toHaveTextContent(/nur teilweise/i);
  });
});

describe("Band «hoch»", () => {
  it("bleibt unmarkiert — sonst wäre das Badge kein Signal mehr", async () => {
    await ask(answer());

    expect(screen.queryByText(/Eingeschränkt belegt/)).not.toBeInTheDocument();
    expect(screen.queryByRole("note")).not.toBeInTheDocument();
  });
});

// --- AK 2: the refinement hint after a suppression -------------------------

describe("Unterdrückte Antwort", () => {
  const suppressed = answer({
    suppressed: true,
    suppression_reason: "retrieval_gate",
    message: "Zu dieser Frage habe ich keine belastbaren Informationen im Korpus gefunden.",
    refinement_hint: "Nenne einen konkreten Prozess, ein Dokument oder einen Artikel.",
    citations: [],
    confidence: { score: 0.2, retrieval_score: 0.2, citation_coverage: 0, band: "niedrig" },
  });

  it("zeigt den Präzisierungs-Hinweis des Backends", async () => {
    await ask(suppressed);

    expect(screen.getByRole("note", { name: /Präzisierung der Frage/i })).toHaveTextContent(
      /Nenne einen konkreten Prozess, ein Dokument oder einen Artikel\./,
    );
  });

  it("trägt kein Konfidenz-Badge — es gäbe keinen Text, den es qualifizieren könnte", async () => {
    // `mittel` and suppressed at once: the score can sit in the middle band
    // while a later stage withholds the answer (self-check, invented citation).
    // The badge would then rate prose the learner never gets to read.
    await ask(answer({
      ...suppressed,
      suppression_reason: "self_check",
      confidence: { score: 0.6, retrieval_score: 0.6, citation_coverage: 0.5, band: "mittel" },
    }));

    expect(screen.queryByText(/Eingeschränkt belegt/)).not.toBeInTheDocument();
  });
});

// --- The citation chip, which had been reading a field learners never get ---

describe("Chip «Citation»", () => {
  it("nennt die Quote, wenn Stufe 2 gelaufen ist — auch ohne debug", async () => {
    // The chip used to derive "did it run?" from `debug.stages`, and an empty
    // `stages` list — as here — answered "did not run" for an answer whose
    // coverage was 1.0. It now comes from the suppression reason, which the
    // response always carries and which the compiler checks against the spec.
    await ask(answer({
      confidence: { score: 0.793, retrieval_score: 0.586, citation_coverage: 1, band: "hoch" },
      debug: debugInfo(),
    }));

    expect(screen.getByText("Citation: 100%")).toBeInTheDocument();
    expect(screen.queryByText(/Citation: nicht gelaufen/)).not.toBeInTheDocument();
  });

  it("nennt die Quote auch bei einer Unterdrückung *durch* Stufe 2", async () => {
    // The half the first case does not reach, and the one a screenshot of the
    // running stack caught: suppressed, so the old lookup and the new one both
    // have a reason to work with — but here the reason IS the citation check,
    // which cannot have suppressed without running. Reporting "nicht gelaufen"
    // next to «Zu wenig Aussagen belegt» contradicts the badge beside it.
    await ask(answer({
      suppressed: true,
      suppression_reason: "citation_coverage",
      message: "Die erzeugte Antwort war nicht ausreichend durch die gefundenen Stellen belegt.",
      refinement_hint: "Grenze die Frage auf einen Punkt ein.",
      confidence: { score: 0.46, retrieval_score: 0.59, citation_coverage: 0.33, band: "niedrig" },
      debug: debugInfo(),
    }));

    expect(screen.getByText("Citation: 33%")).toBeInTheDocument();
    expect(screen.queryByText(/Citation: nicht gelaufen/)).not.toBeInTheDocument();
  });

  it("sagt «nicht gelaufen», wenn vor der Generierung unterdrückt wurde", async () => {
    // Here 0.0 really does mean "not measured": the pipeline stopped at stage 0,
    // and reporting 0 % would blame a check that never happened (ADR-008).
    await ask(answer({
      suppressed: true,
      suppression_reason: "retrieval_gate",
      message: "Dazu finde ich nichts in den freigegebenen Unterlagen.",
      refinement_hint: "Nenne einen konkreten Prozess.",
      citations: [],
      confidence: { score: 0.22, retrieval_score: 0.22, citation_coverage: 0, band: "niedrig" },
      debug: debugInfo(),
    }));

    expect(screen.getByText("Citation: nicht gelaufen")).toBeInTheDocument();
  });
});

// --- Which numbers a learner is shown at all --------------------------------

describe("Detail-Chips", () => {
  it("zeigt Lernenden den Komposit-Score, aber nicht seine Bestandteile", async () => {
    // Requirements §75 asks that the score be visible — that is `Composite`.
    // `Retrieval` and `Citation` are calibration figures: next to the badge US-02
    // wants read, they were three numbers competing with the one statement.
    await ask(answer({ debug: null }));

    expect(screen.getByText(/^Composite:/)).toBeInTheDocument();
    expect(screen.queryByText(/^Retrieval:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Citation:/)).not.toBeInTheDocument();
  });

  it("zeigt sie in der Admin-Ansicht weiterhin", async () => {
    await ask(answer({ debug: debugInfo() }));

    expect(screen.getByText(/^Retrieval:/)).toBeInTheDocument();
    expect(screen.getByText(/^Citation:/)).toBeInTheDocument();
  });
});

// --- AK 3: the three states stay distinguishable ---------------------------

describe("Abgrenzung der Zustände", () => {
  it("zeigt keinen Hinweis, wenn die Antwort steht — auch wenn einer mitgeliefert wird", async () => {
    // Defends the gate rather than the backend's behaviour: today a hint comes
    // only with a reason, and a delivered answer has nothing to refine.
    await ask(answer({ refinement_hint: "Sollte hier nicht erscheinen." }));

    expect(screen.queryByText(/Sollte hier nicht erscheinen\./)).not.toBeInTheDocument();
  });

  it("beschriftet die zwei Hinweisblöcke verschieden", async () => {
    // They never share a message, but they sit under one another in the
    // transcript. Identical wrappers made two different states look like one —
    // the label is what tells them apart where the colour cannot (screen
    // reader), and it is the assertable half of that distinction.
    await ask(answer({
      confidence: { score: 0.6, retrieval_score: 0.6, citation_coverage: 0.5, band: "mittel" },
    }));

    expect(screen.getByRole("note")).toHaveAccessibleName(/Belegung der Antwort/i);
    expect(screen.queryByRole("note", { name: /Präzisierung der Frage/i })).not.toBeInTheDocument();
  });
});
