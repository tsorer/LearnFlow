/**
 * @vitest-environment jsdom
 *
 * T-32: Stefans Feedback-Übersicht (US-03). Wie quiz-review.test.tsx läuft
 * dies gegen den geteilten fetch-Stub (test/api.ts) statt gegen einen
 * Modul-Mock, damit Pfad, Methode und Statuscode gegen das generierte Schema
 * geprüft werden.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import { MemoryRouter } from "react-router-dom";
import App from "./App";
import { ProtectedRoute } from "./components/RouteGuards";
import { installApiStub, installAppEnvironment, type ApiStub } from "../test/api";
import type { FeedbackItem } from "./api/client";

let api: ApiStub;

function item(overrides: Partial<FeedbackItem> = {}): FeedbackItem {
  return {
    id: "f-1",
    helpful: true,
    category: "verstaendlich",
    comment: "Sehr klar erklärt",
    created_at: "2026-08-20T10:00:00Z",
    ...overrides,
  };
}

/** Signs in and opens the dashboard via the header button. */
async function openDashboard(role: "knowledge_owner" | "admin" = "knowledge_owner") {
  api.route("post", "/api/auth/login", 200, { access_token: "tok123", token_type: "bearer", role });
  api.route("get", "/api/auth/me", 200, { id: "u1", email: "stefan@learnflow.ch", role });
  render(<App />);
  await userEvent.type(screen.getByLabelText(/e-mail/i), "stefan@learnflow.ch");
  await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
  await userEvent.click(await screen.findByRole("button", { name: /feedback/i }));
  await screen.findByText(/feedback-übersicht/i);
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

describe("Liste (AK: alle Feedbacks sichtbar, Freitext lesbar)", () => {
  it("zeigt Bewertung, Kategorie und Freitext einer Zeile", async () => {
    api.route("get", "/api/feedback", 200, { items: [item()], total: 1 });
    await openDashboard();

    expect(screen.getByText(/1 feedback$/i)).toBeInTheDocument();
    expect(screen.getByText("👍")).toBeInTheDocument();
    // "Verständlich" existiert zweimal im DOM (Kategorie-Filter-Option und
    // Badge); der Selektor grenzt auf das Badge ein.
    expect(screen.getByText("Verständlich", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("Sehr klar erklärt")).toBeInTheDocument();
  });

  it("zeigt eine leere Liste ohne Zeilen an", async () => {
    api.route("get", "/api/feedback", 200, { items: [], total: 0 });
    await openDashboard();

    expect(screen.getByText(/kein feedback vorhanden/i)).toBeInTheDocument();
  });

  it("rendert ein Feedback ohne Kategorie und ohne Kommentar", async () => {
    api.route("get", "/api/feedback", 200, {
      items: [item({ category: null, comment: null })],
      total: 1,
    });
    await openDashboard();

    expect(screen.getByText("👍")).toBeInTheDocument();
    expect(screen.queryByText("Verständlich", { selector: "span" })).not.toBeInTheDocument();
  });
});

describe("Filter (AK: filterbar nach Bewertung und Kategorie)", () => {
  it("schickt helpful als Query-Parameter und lädt neu", async () => {
    // Ohne Filter (Default "") sendet der Client keinen helpful-Parameter —
    // openapi-fetch laesst ein undefined-Query-Feld weg.
    api.route("get", "/api/feedback", 200, { items: [item()], total: 1 });
    await openDashboard();
    expect(screen.getByText("Sehr klar erklärt")).toBeInTheDocument();

    api.routeQuery("get", "/api/feedback", { helpful: "false" }, 200, {
      items: [item({ helpful: false, category: "veraltet", comment: "War veraltet" })],
      total: 1,
    });
    await userEvent.selectOptions(screen.getByLabelText(/bewertung filtern/i), "false");

    // Erscheint nur, wenn wirklich helpful=false gesendet wurde — sonst hätte
    // die Default-Route (ohne Query) weiter geantwortet.
    expect(await screen.findByText("War veraltet")).toBeInTheDocument();
    expect(screen.queryByText("Sehr klar erklärt")).not.toBeInTheDocument();
  });

  it("schickt category als Query-Parameter und lädt neu", async () => {
    api.route("get", "/api/feedback", 200, { items: [item()], total: 1 });
    await openDashboard();
    expect(screen.getByText("Sehr klar erklärt")).toBeInTheDocument();

    api.routeQuery("get", "/api/feedback", { category: "veraltet" }, 200, {
      items: [item({ category: "veraltet", helpful: false, comment: "War veraltet" })],
      total: 1,
    });
    await userEvent.selectOptions(screen.getByLabelText(/kategorie filtern/i), "veraltet");

    expect(await screen.findByText("War veraltet")).toBeInTheDocument();
    expect(screen.queryByText("Sehr klar erklärt")).not.toBeInTheDocument();
  });
});

describe("Race: Filterwechsel während 'Weitere laden' noch offen ist", () => {
  it("verwirft eine spät eintreffende Weitere-laden-Antwort, wenn zwischenzeitlich gefiltert wurde", async () => {
    api.route("get", "/api/feedback", 200, { items: [item({ id: "f-1", comment: "Seite eins" })], total: 2 });
    await openDashboard();
    expect(screen.getByText("Seite eins")).toBeInTheDocument();

    // "Weitere laden" schickt eine Anfrage, die absichtlich offen bleibt...
    api.hold("get", "/api/feedback");
    await userEvent.click(screen.getByRole("button", { name: /weitere laden/i }));

    // ...bevor sie zurückkommt, wechselt der Filter und schickt eine zweite.
    api.routeQuery("get", "/api/feedback", { helpful: "false" }, 200, {
      items: [item({ id: "f-3", helpful: false, category: "veraltet", comment: "Nur negatives" })],
      total: 1,
    });
    await userEvent.selectOptions(screen.getByLabelText(/bewertung filtern/i), "false");

    api.release("get", "/api/feedback");

    // Die veraltete Weitere-laden-Seite darf die neue Filter-Liste nicht überschreiben.
    expect(await screen.findByText("Nur negatives")).toBeInTheDocument();
    expect(screen.queryByText("Seite eins")).not.toBeInTheDocument();
  });
});

describe("Pagination (echtes Offset-Paging statt wachsendem limit)", () => {
  it("hängt bei 'Weitere laden' die nächste Seite per Offset an", async () => {
    api.routeQuery("get", "/api/feedback", { offset: "0" }, 200, {
      items: [item({ id: "f-1", comment: "Erstes" })],
      total: 2,
    });
    api.routeQuery("get", "/api/feedback", { offset: "1" }, 200, {
      items: [item({ id: "f-2", comment: "Zweites" })],
      total: 2,
    });
    await openDashboard();

    expect(screen.getByText("Erstes")).toBeInTheDocument();
    expect(screen.queryByText("Zweites")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /weitere laden/i }));

    expect(await screen.findByText("Zweites")).toBeInTheDocument();
    expect(screen.getByText("Erstes")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /weitere laden/i })).not.toBeInTheDocument();
  });
});

describe("Fehlerfälle beim Laden", () => {
  it("meldet einen fehlgeschlagenen Initial-Load sichtbar", async () => {
    api.route("post", "/api/auth/login", 200, { access_token: "tok123", token_type: "bearer", role: "knowledge_owner" });
    api.route("get", "/api/auth/me", 200, { id: "u1", email: "stefan@learnflow.ch", role: "knowledge_owner" });
    // Keine Route für GET /api/feedback registriert → der Load scheitert.
    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "stefan@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
    await userEvent.click(await screen.findByRole("button", { name: /feedback/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/feedback konnte nicht geladen werden/i);
  });
});

describe("Zugriffsschutz (AK: nur für knowledge_owner/admin)", () => {
  it("zeigt den Feedback-Button Lernenden nicht an", async () => {
    api.route("post", "/api/auth/login", 200, { access_token: "tok123", token_type: "bearer", role: "learner" });
    api.route("get", "/api/auth/me", 200, { id: "u2", email: "lara@learnflow.ch", role: "learner" });
    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    await screen.findByLabelText(/frage/i);
    expect(screen.queryByRole("button", { name: /feedback/i })).not.toBeInTheDocument();
  });

  it("ProtectedRoute leitet eine falsche Rolle von /feedback weg", () => {
    render(
      <MemoryRouter initialEntries={["/start"]}>
        <ProtectedRoute
          user={{ id: "u2", email: "lara@learnflow.ch", role: "learner", token: "t" }}
          roles={["knowledge_owner", "admin"]}
        >
          {() => <div>Feedback-Übersicht</div>}
        </ProtectedRoute>
      </MemoryRouter>,
    );
    expect(screen.queryByText("Feedback-Übersicht")).not.toBeInTheDocument();
  });
});
