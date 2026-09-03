/**
 * @vitest-environment jsdom
 *
 * T-36: Laras Quiz-Durchlauf (US-08). Läuft wie quiz-review.test.tsx gegen den
 * geteilten fetch-Stub (test/api.ts), damit Pfad, Methode und Statuscode gegen
 * das generierte Schema geprüft werden.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import App from "./App";
import { scoreOf } from "./components/QuizRun";
import { installApiStub, installAppEnvironment, type ApiStub } from "../test/api";
import type { QuizQuestion } from "./api/client";

let api: ApiStub;

function question(overrides: Partial<QuizQuestion> = {}): QuizQuestion {
  return {
    id: "q-1",
    document_id: "doc-1",
    chunk_id: "chunk-1",
    question: "Was verlangt SKOS je Sprache?",
    options: ["Genau ein prefLabel", "Beliebig viele altLabel", "Kein Label", "Nur ein altLabel"],
    correct_answer: "A",
    explanation: "SKOS erlaubt je Sprache genau ein prefLabel.",
    source_excerpt: "Jede Konzeptbezeichnung darf pro Sprache nur ein prefLabel tragen.",
    status: "approved",
    created_at: "2026-08-20T10:00:00Z",
    approved_at: "2026-08-20T11:00:00Z",
    ...overrides,
  };
}

/** Signs in and opens the quiz via the header button. */
async function openQuiz(role: "learner" | "knowledge_owner" | "admin" = "learner") {
  api.route("post", "/api/auth/login", 200, { access_token: "tok123", token_type: "bearer", role });
  api.route("get", "/api/auth/me", 200, { id: "u1", email: "lara@learnflow.ch", role });
  render(<App />);
  await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
  await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
  await userEvent.click(await screen.findByRole("button", { name: /quiz starten/i }));
}

/** Answers the currently shown question with the given letter and advances. */
async function answer(letter: "A" | "B" | "C" | "D", nextLabel: RegExp = /weiter|auswertung anzeigen/i) {
  await userEvent.click(screen.getByRole("radio", { name: new RegExp(`^${letter}\\b`) }));
  await userEvent.click(screen.getByRole("button", { name: nextLabel }));
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

describe("Ablauf (AK: 5 Fragen sequenziell, Ergebnis richtig/falsch + Erklärung + Quelle)", () => {
  it("zeigt Fragen nacheinander und danach das Ergebnis mit Erklärung und Quellen-Link", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, {
      items: [
        question({ id: "q-1", question: "Frage eins", correct_answer: "A" }),
        question({ id: "q-2", question: "Frage zwei", correct_answer: "B" }),
      ],
      total: 2,
    });
    await openQuiz();

    expect(await screen.findByText("Frage eins")).toBeInTheDocument();
    expect(screen.getByText(/frage 1 von 2/i)).toBeInTheDocument();
    // "Weiter" ist gesperrt, bis eine Option gewählt ist.
    expect(screen.getByRole("button", { name: /weiter/i })).toBeDisabled();

    await answer("A");
    expect(await screen.findByText("Frage zwei")).toBeInTheDocument();

    await answer("C", /auswertung anzeigen/i);

    expect(await screen.findByText(/1 von 2 richtig/i)).toBeInTheDocument();
    expect(screen.getByText(/^richtig$/i)).toBeInTheDocument();
    expect(screen.getByText(/^falsch$/i)).toBeInTheDocument();
    expect(screen.getAllByText(/SKOS erlaubt je Sprache genau ein prefLabel/).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /quelle ansehen/i }).length).toBe(2);
  });

  it("öffnet den Dokument-Viewer über den Quellen-Link", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, {
      items: [question({ id: "q-1" })],
      total: 1,
    });
    await openQuiz();
    await answer("A", /auswertung anzeigen/i);

    api.routeQuery("get", "/api/documents/{document_id}/content", { around: "chunk-1" }, 200, {
      id: "doc-1",
      filename: "skos-richtlinie.md",
      status: "available",
      chunks: [{ chunk_id: "chunk-1", chunk_index: 0, page: null, heading: null, content: "Jede Konzeptbezeichnung…" }],
    });

    await userEvent.click(screen.getByRole("button", { name: /quelle ansehen/i }));

    expect(await screen.findByText("skos-richtlinie.md")).toBeInTheDocument();
  });

  it("zeigt bei ersetzter Quelle (chunk_id: null) die Passage als Text statt eines Links", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, {
      items: [question({ id: "q-1", chunk_id: null })],
      total: 1,
    });
    await openQuiz();
    await answer("A", /auswertung anzeigen/i);

    // openapi.yaml nennt source_excerpt "das einzige verbliebene Zeugnis der
    // Passage" für diesen Fall — sie muss also sichtbar bleiben, nicht nur
    // der Hinweis, dass es keinen Link mehr gibt.
    expect(await screen.findByText(/jede konzeptbezeichnung darf pro sprache/i)).toBeInTheDocument();
    expect(screen.getByText(/quelle ersetzt/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /quelle ansehen/i })).not.toBeInTheDocument();
  });
});

describe("Leerer Bestand (AK: Button sichtbar, Hinweistext statt Quiz)", () => {
  it("zeigt den Hinweis, wenn keine Fragen freigegeben sind", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, { items: [], total: 0 });
    await openQuiz();

    expect(
      await screen.findByText(/es sind noch keine quizfragen für diesen bereich freigegeben/i),
    ).toBeInTheDocument();
  });
});

describe("Kurze Runde (Hinweis bei weniger als 5 Fragen)", () => {
  it("weist darauf hin, wenn der Pool weniger als 5 Fragen enthält", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, {
      items: [question({ id: "q-1" }), question({ id: "q-2" })],
      total: 2,
    });
    await openQuiz();

    expect(await screen.findByText(/nur 2 von 5 fragen freigegeben/i)).toBeInTheDocument();
  });

  it("zeigt keinen Kurz-Hinweis bei 5 Fragen", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, {
      items: Array.from({ length: 5 }, (_, i) => question({ id: `q-${i}` })),
      total: 5,
    });
    await openQuiz();

    await screen.findByText(/frage 1 von 5/i);
    expect(screen.queryByText(/fragen freigegeben — diese runde/i)).not.toBeInTheDocument();
  });

  it("bleibt auch auf der Auswertungsseite sichtbar, statt eine kurze Runde als vollständig auszugeben", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, {
      items: [question({ id: "q-1" }), question({ id: "q-2" })],
      total: 2,
    });
    await openQuiz();
    await answer("A");
    await answer("A", /auswertung anzeigen/i);

    expect(await screen.findByText(/2 von 2 richtig/i)).toBeInTheDocument();
    expect(screen.getByText(/nur 2 von 5 fragen freigegeben/i)).toBeInTheDocument();
  });
});

describe("Fokus (a11y)", () => {
  it("setzt den Fokus auf die neue Frage, statt ihn auf <body> fallen zu lassen", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, {
      items: [question({ id: "q-1", question: "Frage eins" }), question({ id: "q-2", question: "Frage zwei" })],
      total: 2,
    });
    await openQuiz();
    await screen.findByText("Frage eins");

    await answer("A");

    await screen.findByText("Frage zwei");
    expect(screen.getByText(/frage 2 von 2/i)).toHaveFocus();
  });

  it("gibt den Fokus nach dem Schliessen des Dokument-Viewers an den auslösenden Button zurück", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, { items: [question({ id: "q-1" })], total: 1 });
    await openQuiz();
    await answer("A", /auswertung anzeigen/i);
    api.routeQuery("get", "/api/documents/{document_id}/content", { around: "chunk-1" }, 200, {
      id: "doc-1", filename: "skos-richtlinie.md", status: "available",
      chunks: [{ chunk_id: "chunk-1", chunk_index: 0, page: null, heading: null, content: "Text." }],
    });

    const openButton = await screen.findByRole("button", { name: /quelle ansehen/i });
    await userEvent.click(openButton);
    await userEvent.click(await screen.findByRole("button", { name: /viewer schliessen/i }));

    expect(openButton).toHaveFocus();
  });
});

describe("Neue Runde (kein Sackgassen-Ergebnis)", () => {
  it("lädt nach 'Neue Runde starten' eine frische Stichprobe und setzt den Fortschritt zurück", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, { items: [question({ id: "q-1" })], total: 1 });
    await openQuiz();
    await answer("A", /auswertung anzeigen/i);
    await screen.findByText(/1 von 1 richtig/i);

    api.route("get", "/api/quiz/questions/sample", 200, { items: [question({ id: "q-2", question: "Neue Frage" })], total: 1 });
    await userEvent.click(screen.getByRole("button", { name: /neue runde starten/i }));

    expect(await screen.findByText("Neue Frage")).toBeInTheDocument();
    expect(screen.queryByText(/richtig$/i)).not.toBeInTheDocument();
  });
});

describe("Fehlerfall beim Laden", () => {
  it("meldet einen fehlgeschlagenen Ladevorgang sichtbar", async () => {
    // Keine Route für GET /api/quiz/questions/sample registriert → scheitert.
    await openQuiz();

    expect(await screen.findByRole("alert")).toHaveTextContent(/quiz konnte nicht geladen werden/i);
  });
});

describe("Zugriff (AK: für jede angemeldete Rolle erreichbar)", () => {
  it("zeigt den 'Quiz starten'-Button auch Lernenden", async () => {
    api.route("get", "/api/quiz/questions/sample", 200, { items: [], total: 0 });
    await openQuiz("learner");
    expect(await screen.findByText(/es sind noch keine quizfragen/i)).toBeInTheDocument();
  });
});

describe("Chat-Historie bleibt über /quiz erhalten (US-09)", () => {
  it("zeigt den Chat-Verlauf und führt dieselbe Session fort, nachdem Lara Quiz starten und Zurück zum Chat geklickt hat", async () => {
    api.route("post", "/api/auth/login", 200, { access_token: "tok123", token_type: "bearer", role: "learner" });
    api.route("get", "/api/auth/me", 200, { id: "u1", email: "lara@learnflow.ch", role: "learner" });
    api.route("post", "/api/query", 200, {
      session_id: "sess-1",
      answer_id: "ans-1",
      suppressed: false,
      suppression_reason: null,
      message: "Erste Antwort.",
      refinement_hint: null,
      citations: [],
      confidence: null,
      debug: null,
    });
    api.route("get", "/api/quiz/questions/sample", 200, { items: [], total: 0 });

    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    await userEvent.type(await screen.findByLabelText("Frage"), "Was verlangt SKOS je Sprache?");
    await userEvent.click(screen.getByRole("button", { name: /senden/i }));
    await screen.findByText("Erste Antwort.");

    // /quiz unmountet ChatView — ein dort lokaler State wäre jetzt weg.
    await userEvent.click(screen.getByRole("button", { name: /quiz starten/i }));
    await screen.findByText(/es sind noch keine quizfragen/i);
    await userEvent.click(screen.getByRole("button", { name: /zurück zum chat/i }));

    // AK 2: Verlauf bleibt für die Browser-Session sichtbar.
    expect(await screen.findByText("Was verlangt SKOS je Sprache?")).toBeInTheDocument();
    expect(screen.getByText("Erste Antwort.")).toBeInTheDocument();

    // AK 1: eine Folgefrage läuft in derselben Session weiter, nicht neu.
    await userEvent.type(screen.getByLabelText("Frage"), "Und für Deutsch?");
    await userEvent.click(screen.getByRole("button", { name: /senden/i }));

    expect(api.last("post", "/api/query")?.json).toMatchObject({ session_id: "sess-1" });
  });

  it("leert den Verlauf beim Abmelden — die nächste Anmeldung startet nicht in einer fremden Sitzung", async () => {
    api.route("post", "/api/auth/login", 200, { access_token: "tok123", token_type: "bearer", role: "learner" });
    api.route("get", "/api/auth/me", 200, { id: "u1", email: "lara@learnflow.ch", role: "learner" });
    api.route("post", "/api/query", 200, {
      session_id: "sess-1", answer_id: "ans-1", suppressed: false, suppression_reason: null,
      message: "Erste Antwort.", refinement_hint: null, citations: [], confidence: null, debug: null,
    });

    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
    await userEvent.type(await screen.findByLabelText("Frage"), "Was verlangt SKOS je Sprache?");
    await userEvent.click(screen.getByRole("button", { name: /senden/i }));
    await screen.findByText("Erste Antwort.");

    await userEvent.click(screen.getByRole("button", { name: /abmelden/i }));
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    await screen.findByLabelText("Frage");
    expect(screen.queryByText("Erste Antwort.")).not.toBeInTheDocument();
  });
});

describe("scoreOf (reine Funktion)", () => {
  it("zählt nur mit correct_answer übereinstimmende Antworten", () => {
    const questions = [
      question({ id: "q-1", correct_answer: "A" }),
      question({ id: "q-2", correct_answer: "B" }),
    ];
    expect(scoreOf(questions, { "q-1": "A", "q-2": "C" })).toBe(1);
    expect(scoreOf(questions, { "q-1": "A", "q-2": "B" })).toBe(2);
    expect(scoreOf(questions, {})).toBe(0);
  });
});
