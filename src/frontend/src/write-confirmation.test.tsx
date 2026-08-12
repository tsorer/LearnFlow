/**
 * @vitest-environment jsdom
 *
 * Review zu T-39: die UI darf einen Schreibvorgang erst bestaetigen, wenn er
 * angekommen ist, und ihn nicht doppelt absetzen. Beide Wege laufen heute gegen
 * den 501-Platzhalter (T-30, T-37) und ab der Umsetzung gegen echte Daten — die
 * Bestaetigung ist der Teil, der jetzt schon stimmen muss.
 *
 * Wie session.test.tsx gegen einen fetch-Stub statt gegen einen Modul-Mock:
 * geprueft wird, was tatsaechlich ueber die Leitung geht.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import App from "./App";

const routes = new Map<string, { status: number; body?: unknown }>();
let calls: string[] = [];

// Haelt Antworten an, bis der Test sie freigibt — nur so laesst sich ein
// zweiter Klick in das Fenster legen, in dem der erste noch unterwegs ist.
let hold: Promise<void> | null = null;
let release: () => void = () => {};

function holdResponses() {
  hold = new Promise<void>(resolve => {
    release = () => { hold = null; resolve(); };
  });
}

function route(method: string, path: string, status: number, body?: unknown) {
  routes.set(`${method} /api${path}`, { status, body });
}

async function fakeFetch(input: RequestInfo | URL, init?: RequestInit) {
  const request = input instanceof Request ? input : new Request(String(input), init);
  const key = `${request.method} ${new URL(request.url, "http://localhost").pathname}`;
  calls.push(key);
  const res = routes.get(key);
  if (!res) throw new Error(`Nicht gemockte Anfrage: ${key}`);
  if (hold) await hold;
  return new Response(res.body === undefined ? null : JSON.stringify(res.body), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

const countCalls = (key: string) => calls.filter(c => c === key).length;

async function login(email: string) {
  await userEvent.type(screen.getByLabelText(/e-mail/i), email);
  await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
}

function authRoutes(role: string) {
  route("POST", "/auth/login", 200, { access_token: "tok123", role });
  route("GET", "/auth/me", 200, { id: "u1", email: "u@learnflow.ch", role });
}

beforeEach(() => {
  routes.clear();
  calls = [];
  hold = null;
  vi.stubGlobal("fetch", vi.fn(fakeFetch));
  vi.stubGlobal("__BUILD_TIME__", new Date().toISOString());
  Element.prototype.scrollIntoView = vi.fn();
  window.history.pushState({}, "", "/");
});

afterEach(() => {
  release();
  cleanup();
  vi.unstubAllGlobals();
});

describe("Admin-Parameter (T-37)", () => {
  async function openPanel() {
    authRoutes("admin");
    route("GET", "/admin/config", 200, { config: { top_k: "20" } });
    render(<App />);
    await login("admin@learnflow.ch");
    await userEvent.click(await screen.findByRole("button", { name: /parameter/i }));
  }

  it("meldet kein Gespeichert, wenn der Schreibvorgang scheitert", async () => {
    // Der Kern des Befunds: `.catch(() => {})` liess das gruene Haekchen auch
    // dann erscheinen, wenn die config-Tabelle nie etwas gesehen hat — der
    // Admin haette gegen eine Schwelle gearbeitet, die nicht gesetzt ist.
    await openPanel();
    route("PUT", "/admin/config", 501, { detail: "Not implemented (T-37)" });

    await userEvent.click(screen.getByRole("button", { name: /^speichern$/i }));

    expect(await screen.findByText(/noch nicht speicherbar/i)).toBeInTheDocument();
    expect(screen.queryByText(/gespeichert/i)).not.toBeInTheDocument();
  });

  it("meldet Gespeichert, wenn der Schreibvorgang durchgeht", async () => {
    await openPanel();
    route("PUT", "/admin/config", 200, { config: { top_k: "20" } });

    await userEvent.click(screen.getByRole("button", { name: /^speichern$/i }));

    expect(await screen.findByText(/✓ Gespeichert/)).toBeInTheDocument();
  });
});

describe("Feedback (T-30)", () => {
  const FEEDBACK = "POST /api/answers/a1/feedback";

  /** Meldet einen Learner an und stellt eine Frage, bis die Daumen stehen. */
  async function askQuestion() {
    authRoutes("learner");
    route("POST", "/query", 200, {
      answer_id: "a1",
      session_id: "s1",
      message: "Antwort",
      suppressed: false,
    });
    render(<App />);
    await login("lara@learnflow.ch");
    await userEvent.type(await screen.findByPlaceholderText(/frage stellen/i), "Frage");
    await userEvent.click(screen.getByRole("button", { name: /senden/i }));
    return await screen.findByRole("button", { name: /^hilfreich$/i });
  }

  it("sendet nur einen POST, solange der erste noch laeuft", async () => {
    const thumbUp = await askQuestion();
    route("POST", "/answers/a1/feedback", 204);
    holdResponses();

    // `feedback` ist in diesem Fenster noch null und taugt nicht als Sperre —
    // ohne `submitting` waeren das zwei Zeilen zur selben answer_id, die
    // dritte davon mit widersprechendem `helpful`.
    fireEvent.click(thumbUp);
    fireEvent.click(thumbUp);
    fireEvent.click(screen.getByRole("button", { name: /nicht hilfreich/i }));

    expect(countCalls(FEEDBACK)).toBe(1);

    await act(async () => { release(); });
    expect(countCalls(FEEDBACK)).toBe(1);
  });

  it("laesst nach einem Fehlschlag eine erneute Bewertung zu", async () => {
    // Die Sperre darf nicht latchen: ein 501 heute heisst nicht, dass der
    // Nutzer nach T-30 nicht mehr bewerten darf.
    const thumbUp = await askQuestion();
    route("POST", "/answers/a1/feedback", 501, { detail: "Not implemented (T-30)" });

    await userEvent.click(thumbUp);

    expect(await screen.findByText(/noch nicht verfügbar/i)).toBeInTheDocument();
    expect(thumbUp).toBeEnabled();

    await userEvent.click(thumbUp);
    expect(countCalls(FEEDBACK)).toBe(2);
  });
});
