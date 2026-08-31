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
import type { QueryResponse } from "./api/client";

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

    expect(screen.getByRole("note")).toHaveTextContent(/nur teilweise/i);
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

    expect(screen.getByRole("note")).toHaveTextContent(
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

// --- AK 3: the three states stay distinguishable ---------------------------

describe("Abgrenzung der Zustände", () => {
  it("zeigt keinen Hinweis, wenn die Antwort steht — auch wenn einer mitgeliefert wird", async () => {
    // Defends the gate rather than the backend's behaviour: today a hint comes
    // only with a reason, and a delivered answer has nothing to refine.
    await ask(answer({ refinement_hint: "Sollte hier nicht erscheinen." }));

    expect(screen.queryByText(/Sollte hier nicht erscheinen\./)).not.toBeInTheDocument();
  });
});
