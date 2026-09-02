/**
 * @vitest-environment jsdom
 *
 * T-35: das Quiz-Review-Dashboard (US-07). Wie query.test.tsx läuft dies gegen
 * den geteilten fetch-Stub (test/api.ts) statt gegen einen Modul-Mock, damit
 * Pfad, Methode und Statuscode gegen das generierte Schema geprüft werden.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
import { ProtectedRoute } from "./components/RouteGuards";
import { diffQuestion } from "./components/QuizCard";
import { generationFailureMessage } from "./components/QuizReview";
import { installApiStub, installAppEnvironment, type ApiStub } from "../test/api";
import { ApiError, type QuizQuestion, type Role } from "./api/client";

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
    status: "pending",
    created_at: "2026-08-20T10:00:00Z",
    approved_at: null,
    ...overrides,
  };
}

function routeQuestions(
  byStatus: Partial<Record<QuizQuestion["status"], QuizQuestion[]>>,
) {
  (["pending", "approved", "rejected"] as const).forEach(status => {
    const items = byStatus[status] ?? [];
    api.routeQuery("get", "/api/quiz/questions", { status }, 200, { items, total: items.length });
  });
}

/** Signs in as knowledge_owner and opens the board via the header button. */
async function openBoard(role: Role = "knowledge_owner") {
  api.route("post", "/api/auth/login", 200, { access_token: "tok123", token_type: "bearer", role });
  api.route("get", "/api/auth/me", 200, { id: "u1", email: "stefan@learnflow.ch", role });
  render(<App />);
  await userEvent.type(screen.getByLabelText(/e-mail/i), "stefan@learnflow.ch");
  await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
  await userEvent.click(await screen.findByRole("button", { name: /quiz-review/i }));
  await screen.findByText(/ausstehend/i);
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

describe("Board (AK: drei Spalten, Karteninhalt)", () => {
  it("zeigt drei Spalten mit total und die Kartendetails", async () => {
    routeQuestions({ pending: [question()] });
    await openBoard();

    expect(screen.getByText(/ausstehend \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/freigegeben \(0\)/i)).toBeInTheDocument();
    expect(screen.getByText(/abgelehnt \(0\)/i)).toBeInTheDocument();

    expect(screen.getByText("Was verlangt SKOS je Sprache?")).toBeInTheDocument();
    // Enthält jetzt zusätzlich das Häkchen als sichtbaren Text davor, deshalb
    // eine Teilübereinstimmung statt des exakten Optionstexts.
    expect(screen.getByText(/Genau ein prefLabel/)).toBeInTheDocument();
    expect(screen.getByText(/SKOS erlaubt je Sprache genau ein prefLabel/)).toBeInTheDocument();
    expect(screen.getByText(/Jede Konzeptbezeichnung darf pro Sprache/)).toBeInTheDocument();
  });

  it("markiert die richtige Antwort für Screenreader — nicht nur über Farbe (WCAG 1.4.1)", async () => {
    routeQuestions({ pending: [question()] });
    await openBoard();

    // Ein `aria-label` auf einem rollenlosen <span> wird von der
    // Accessible-Name-Berechnung ignoriert (Chrome); die Markierung muss
    // deshalb echter, nicht versteckter Text sein. Das Häkchen ist sichtbarer
    // Text, der Zusatz "— richtige Antwort" eine per .sr-only nur optisch
    // versteckte Ergänzung — beides zusammen bildet den Accessible Name.
    const srOnlySuffix = screen.getByText(/— richtige Antwort/);
    expect(srOnlySuffix).toHaveClass("sr-only");
    // Der umschliessende <span> traegt die volle Information als Text — nicht
    // nur der versteckte Zusatz.
    expect(srOnlySuffix.parentElement?.textContent).toBe("✓ Genau ein prefLabel — richtige Antwort");

    // Die falschen Optionen tragen keinen solchen Zusatz.
    expect(screen.queryByText(/Beliebig viele altLabel.*richtige Antwort/)).not.toBeInTheDocument();
  });

  it("markiert eine Frage mit chunk_id: null als 'Quelle ersetzt'", async () => {
    routeQuestions({ pending: [question({ chunk_id: null })] });
    await openBoard();

    expect(screen.getByText(/quelle ersetzt/i)).toBeInTheDocument();
  });

  it("zeigt approved_at nur bei freigegebenen Fragen", async () => {
    routeQuestions({
      approved: [question({ id: "q-2", status: "approved", approved_at: "2026-08-21T09:00:00Z" })],
    });
    await openBoard();

    expect(screen.getByText(/freigegeben: /i)).toBeInTheDocument();
  });
});

describe("Fehlerfälle beim Laden", () => {
  it("meldet einen fehlgeschlagenen Initial-Load sichtbar", async () => {
    api.route("post", "/api/auth/login", 200, { access_token: "tok123", token_type: "bearer", role: "knowledge_owner" });
    api.route("get", "/api/auth/me", 200, { id: "u1", email: "stefan@learnflow.ch", role: "knowledge_owner" });
    // Keine Route für GET /api/quiz/questions registriert → jede Spalte scheitert.
    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "stefan@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
    await userEvent.click(await screen.findByRole("button", { name: /quiz-review/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/fragen konnten nicht geladen werden/i);
  });
});

describe("Pagination (echtes Offset-Paging statt wachsendem limit)", () => {
  it("hängt bei 'Weitere laden' die nächste Seite per Offset an, statt limit zu vergrößern", async () => {
    api.routeQuery("get", "/api/quiz/questions", { status: "approved" }, 200, { items: [], total: 0 });
    api.routeQuery("get", "/api/quiz/questions", { status: "rejected" }, 200, { items: [], total: 0 });
    api.routeQuery("get", "/api/quiz/questions", { status: "pending", offset: "0" }, 200, {
      items: [question({ id: "q-1", question: "Frage eins" })],
      total: 2,
    });
    api.routeQuery("get", "/api/quiz/questions", { status: "pending", offset: "1" }, 200, {
      items: [question({ id: "q-2", question: "Frage zwei" })],
      total: 2,
    });
    await openBoard();

    expect(screen.getByText("Frage eins")).toBeInTheDocument();
    expect(screen.queryByText("Frage zwei")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /weitere laden/i }));

    // Erscheint nur, wenn der zweite Request wirklich offset=1 statt einem
    // vergrößerten limit an dieselbe offset=0-Route schickte — genau die
    // Unterscheidung, die vorher am Backend-Cap (limit ≤ 200) scheiterte.
    expect(await screen.findByText("Frage zwei")).toBeInTheDocument();
    expect(screen.getByText("Frage eins")).toBeInTheDocument();
    // Seite vollständig geladen (2 von 2) → kein Button mehr.
    expect(screen.queryByRole("button", { name: /weitere laden/i })).not.toBeInTheDocument();
  });
});

describe("Statuswechsel (AK: freigeben / ablehnen / zurückziehen)", () => {
  it("gibt eine ausstehende Frage frei und schickt genau den Status-Patch", async () => {
    routeQuestions({ pending: [question()] });
    await openBoard();
    api.route("patch", "/api/quiz/questions/{question_id}", 200, question({ status: "approved" }));

    await userEvent.click(screen.getByRole("button", { name: /^freigeben$/i }));

    await waitFor(() => expect(api.count("patch", "/api/quiz/questions/{question_id}")).toBe(1));
    expect(api.last("patch", "/api/quiz/questions/{question_id}")?.json).toEqual({ status: "approved" });
  });

  it("zieht eine Freigabe zurück", async () => {
    routeQuestions({ approved: [question({ status: "approved", approved_at: "2026-08-21T09:00:00Z" })] });
    await openBoard();
    api.route("patch", "/api/quiz/questions/{question_id}", 200, question({ status: "pending" }));

    await userEvent.click(screen.getByRole("button", { name: /freigabe zurückziehen/i }));

    expect(api.last("patch", "/api/quiz/questions/{question_id}")?.json).toEqual({ status: "pending" });
  });

  it("lehnt eine ausstehende Frage ab", async () => {
    routeQuestions({ pending: [question()] });
    await openBoard();
    api.route("patch", "/api/quiz/questions/{question_id}", 200, question({ status: "rejected" }));

    await userEvent.click(screen.getByRole("button", { name: /^ablehnen$/i }));

    expect(api.last("patch", "/api/quiz/questions/{question_id}")?.json).toEqual({ status: "rejected" });
  });

  it("gibt eine abgelehnte Frage frei", async () => {
    routeQuestions({ rejected: [question({ status: "rejected" })] });
    await openBoard();
    api.route("patch", "/api/quiz/questions/{question_id}", 200, question({ status: "approved" }));

    await userEvent.click(screen.getByRole("button", { name: /^freigeben$/i }));

    expect(api.last("patch", "/api/quiz/questions/{question_id}")?.json).toEqual({ status: "approved" });
  });

  it("schickt eine abgelehnte Frage zurück in die Prüfung", async () => {
    routeQuestions({ rejected: [question({ status: "rejected" })] });
    await openBoard();
    api.route("patch", "/api/quiz/questions/{question_id}", 200, question({ status: "pending" }));

    await userEvent.click(screen.getByRole("button", { name: /zurück in die prüfung/i }));

    expect(api.last("patch", "/api/quiz/questions/{question_id}")?.json).toEqual({ status: "pending" });
  });
});

describe("Editieren (AK: question/options/correct_answer/explanation, Rückstufung sichtbar)", () => {
  it("schickt beim Speichern nur das geänderte Feld", async () => {
    routeQuestions({ pending: [question()] });
    await openBoard();
    api.route("patch", "/api/quiz/questions/{question_id}", 200, question());

    await userEvent.click(screen.getByRole("button", { name: /editieren/i }));
    const explanationBox = screen.getByDisplayValue(/SKOS erlaubt je Sprache genau ein prefLabel/);
    await userEvent.clear(explanationBox);
    await userEvent.type(explanationBox, "Neue Begründung.");
    await userEvent.click(screen.getByRole("button", { name: /^speichern$/i }));

    await waitFor(() => expect(api.count("patch", "/api/quiz/questions/{question_id}")).toBe(1));
    expect(api.last("patch", "/api/quiz/questions/{question_id}")?.json).toEqual({
      explanation: "Neue Begründung.",
    });
  });

  it("zeigt den Rückstufungs-Hinweis nur beim Editieren einer freigegebenen Frage und erlaubt 'Speichern und freigeben'", async () => {
    routeQuestions({ approved: [question({ status: "approved", approved_at: "2026-08-21T09:00:00Z" })] });
    await openBoard();
    api.route("patch", "/api/quiz/questions/{question_id}", 200, question({ status: "approved" }));

    await userEvent.click(screen.getByRole("button", { name: /editieren/i }));
    expect(screen.queryByText(/geht zurück in die prüfung/i)).not.toBeInTheDocument();

    const explanationBox = screen.getByDisplayValue(/SKOS erlaubt je Sprache genau ein prefLabel/);
    await userEvent.clear(explanationBox);
    await userEvent.type(explanationBox, "Präzisierte Begründung.");

    expect(screen.getByText(/geht zurück in die prüfung/i)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /speichern und freigeben/i }));

    expect(api.last("patch", "/api/quiz/questions/{question_id}")?.json).toEqual({
      explanation: "Präzisierte Begründung.",
      status: "approved",
    });
  });

  it("behält den Entwurf im Editiermodus, wenn das Speichern fehlschlägt", async () => {
    routeQuestions({ pending: [question()] });
    await openBoard();
    api.route("patch", "/api/quiz/questions/{question_id}", 422, {
      detail: [{ loc: ["body", "explanation"], msg: "kaputt", type: "value_error" }],
    });

    await userEvent.click(screen.getByRole("button", { name: /editieren/i }));
    const explanationBox = screen.getByDisplayValue(/SKOS erlaubt je Sprache genau ein prefLabel/);
    await userEvent.clear(explanationBox);
    await userEvent.type(explanationBox, "Entwurf, der nicht verloren gehen darf.");
    await userEvent.click(screen.getByRole("button", { name: /^speichern$/i }));

    // Der PATCH ging raus und schlug fehl — die Karte bleibt trotzdem im
    // Editiermodus mit dem eingegebenen Text, statt ihn stillschweigend zu
    // verwerfen (onSave löst den Editiermodus nur bei Erfolg auf).
    expect(await screen.findByRole("alert")).toHaveTextContent(/änderung konnte nicht gespeichert werden/i);
    expect(screen.getByDisplayValue("Entwurf, der nicht verloren gehen darf.")).toBeInTheDocument();
  });
});

describe("diffQuestion (reine Funktion)", () => {
  const base = question();

  it("liefert null, wenn nichts geändert wurde", () => {
    expect(
      diffQuestion(base, {
        question: base.question,
        options: base.options,
        correct_answer: base.correct_answer,
        explanation: base.explanation,
      }),
    ).toBeNull();
  });

  it("liefert nur die geänderten Felder", () => {
    expect(
      diffQuestion(base, {
        question: base.question,
        options: base.options,
        correct_answer: "B",
        explanation: base.explanation,
      }),
    ).toEqual({ correct_answer: "B" });
  });
});

describe("Generierung (AK: Button, Pending-Spalte, Fehlerfälle 409/429/503)", () => {
  it("löst die Generierung aus und lädt die Pending-Spalte neu", async () => {
    routeQuestions({});
    await openBoard();
    api.route("post", "/api/quiz/generate", 201, { generated: 2, questions: [question(), question({ id: "q-2" })] });
    routeQuestions({ pending: [question(), question({ id: "q-2" })] });

    await userEvent.click(screen.getByRole("button", { name: /fragen generieren/i }));

    await waitFor(() => expect(api.count("post", "/api/quiz/generate")).toBe(1));
    expect(await screen.findByText(/2 neue frage/i)).toBeInTheDocument();
  });

  it("blendet die Erfolgsmeldung der Generierung aus, sobald eine andere Aktion läuft", async () => {
    routeQuestions({});
    await openBoard();
    api.route("post", "/api/quiz/generate", 201, { generated: 1, questions: [question()] });
    routeQuestions({ pending: [question()] });

    await userEvent.click(screen.getByRole("button", { name: /fragen generieren/i }));
    expect(await screen.findByText(/1 neue frage/i)).toBeInTheDocument();

    // Ohne setNotice("") in mutate() bliebe die Meldung stehen, obwohl sie
    // sich auf die Generierung bezieht und nichts mehr mit dem Freigeben zu
    // tun hat.
    api.route("patch", "/api/quiz/questions/{question_id}", 200, question({ status: "approved" }));
    await userEvent.click(screen.getByRole("button", { name: /^freigeben$/i }));

    await waitFor(() => expect(screen.queryByText(/1 neue frage/i)).not.toBeInTheDocument());
  });

  it("meldet 409 (kein indexiertes Dokument) sichtbar", async () => {
    routeQuestions({});
    await openBoard();
    api.route("post", "/api/quiz/generate", 409, { detail: "Fehler" });

    await userEvent.click(screen.getByRole("button", { name: /fragen generieren/i }));

    expect(await screen.findByText(/kein indexiertes dokument/i)).toBeInTheDocument();
  });

  it("meldet 429 (Rate Limit) sichtbar", async () => {
    routeQuestions({});
    await openBoard();
    api.route("post", "/api/quiz/generate", 429, { detail: "Fehler" });

    await userEvent.click(screen.getByRole("button", { name: /fragen generieren/i }));

    expect(await screen.findByText(/zu viele generierungen/i)).toBeInTheDocument();
  });

  it("meldet 503 (Provider nicht erreichbar) sichtbar", async () => {
    routeQuestions({});
    await openBoard();
    api.route("post", "/api/quiz/generate", 503, { detail: "Fehler" });

    await userEvent.click(screen.getByRole("button", { name: /fragen generieren/i }));

    expect(await screen.findByText(/nicht erreichbar/i)).toBeInTheDocument();
  });
});

describe("generationFailureMessage (reine Funktion)", () => {
  it("kennt 409, 429, 503 und einen generischen Fall", () => {
    expect(generationFailureMessage(new ApiError(409, "x"))).toMatch(/kein indexiertes dokument/i);
    expect(generationFailureMessage(new ApiError(429, "x"))).toMatch(/zu viele generierungen/i);
    expect(generationFailureMessage(new ApiError(503, "x"))).toMatch(/nicht erreichbar/i);
    expect(generationFailureMessage(new Error("other"))).toMatch(/fehler bei der generierung/i);
  });
});

describe("Zugriffsschutz (AK: /quiz-review nur für knowledge_owner/admin)", () => {
  it("zeigt den Quiz-Review-Button Lernenden nicht an", async () => {
    api.route("post", "/api/auth/login", 200, { access_token: "tok123", token_type: "bearer", role: "learner" });
    api.route("get", "/api/auth/me", 200, { id: "u2", email: "lara@learnflow.ch", role: "learner" });
    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    await screen.findByLabelText(/frage/i);
    expect(screen.queryByRole("button", { name: /quiz-review/i })).not.toBeInTheDocument();
  });

  it("ProtectedRoute leitet eine falsche Rolle von /quiz-review weg", () => {
    render(
      <MemoryRouter initialEntries={["/start"]}>
        <ProtectedRoute
          user={{ id: "u2", email: "lara@learnflow.ch", role: "learner", token: "t" }}
          roles={["knowledge_owner", "admin"]}
        >
          {() => <div>Quiz-Review-Board</div>}
        </ProtectedRoute>
      </MemoryRouter>,
    );
    expect(screen.queryByText("Quiz-Review-Board")).not.toBeInTheDocument();
  });

  it("ProtectedRoute rendert für eine passende Rolle", () => {
    render(
      <MemoryRouter initialEntries={["/start"]}>
        <ProtectedRoute
          user={{ id: "u1", email: "stefan@learnflow.ch", role: "knowledge_owner", token: "t" }}
          roles={["knowledge_owner", "admin"]}
        >
          {() => <div>Quiz-Review-Board</div>}
        </ProtectedRoute>
      </MemoryRouter>,
    );
    expect(screen.getByText("Quiz-Review-Board")).toBeInTheDocument();
  });
});
