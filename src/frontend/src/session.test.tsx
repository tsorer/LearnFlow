/**
 * @vitest-environment jsdom
 *
 * T-40: Ein 401 auf einer authentifizierten Anfrage beendet die Sitzung und
 * fuehrt zurueck auf /login.
 *
 * Anders als auth.test.tsx wird hier NICHT das api-Modul gemockt, sondern
 * `fetch` — die 401-Erkennung sitzt in client.ts selbst und waere gegen einen
 * Modul-Mock nicht pruefbar.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import App from "./App";

const routes = new Map<string, { status: number; body?: unknown }>();

function route(method: string, path: string, status: number, body?: unknown) {
  routes.set(`${method} /api${path}`, { status, body });
}

function fakeFetch(input: RequestInfo | URL, init?: RequestInit) {
  const key = `${init?.method ?? "GET"} ${String(input)}`;
  const res = routes.get(key);
  if (!res) throw new Error(`Nicht gemockte Anfrage: ${key}`);
  return Promise.resolve({
    ok: res.status >= 200 && res.status < 300,
    status: res.status,
    json: async () => res.body,
    text: async () => (res.body === undefined ? "" : JSON.stringify(res.body)),
  } as Response);
}

/** Meldet den Seed-Learner an und wartet, bis ChatView steht. */
async function login() {
  await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
  await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
}

beforeEach(() => {
  routes.clear();
  vi.stubGlobal("fetch", vi.fn(fakeFetch));
  vi.stubGlobal("__BUILD_TIME__", new Date().toISOString());
  Element.prototype.scrollIntoView = vi.fn();
  window.history.pushState({}, "", "/");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Session-Ablauf (T-40)", () => {
  it("leitet bei 401 auf einer geschuetzten Ansicht zurueck auf /login (AK 1, AK 3)", async () => {
    route("POST", "/auth/login", 200, { access_token: "tok123", role: "learner" });
    route("GET", "/auth/me", 200, { id: "u1", email: "lara@learnflow.ch", role: "learner" });
    // Token laeuft waehrend der Sitzung ab (T-06: 1 h Gueltigkeit).
    route("POST", "/query", 401, { detail: "Not authenticated" });

    render(<App />);
    await login();
    await screen.findByRole("button", { name: /abmelden/i });
    expect(window.location.pathname).toBe("/");

    await userEvent.type(screen.getByPlaceholderText(/frage stellen/i), "Was gilt fuer SKOS?");
    await userEvent.click(screen.getByRole("button", { name: /senden/i }));

    await waitFor(() => expect(window.location.pathname).toBe("/login"));
    expect(screen.getByLabelText(/passwort/i)).toBeInTheDocument();
    expect(await screen.findByText(/sitzung abgelaufen/i)).toBeInTheDocument();
  });

  it("meldet einen 401 aus /auth/login weiterhin als falsches Passwort (AK 2)", async () => {
    route("POST", "/auth/login", 401, { detail: "Ungueltige Zugangsdaten" });

    render(<App />);
    await login();

    expect(await screen.findByText(/e-mail oder passwort falsch/i)).toBeInTheDocument();
    expect(screen.queryByText(/sitzung abgelaufen/i)).not.toBeInTheDocument();
  });

  it("blendet den Hinweis nach erneuter Anmeldung wieder aus", async () => {
    route("POST", "/auth/login", 200, { access_token: "tok123", role: "learner" });
    route("GET", "/auth/me", 200, { id: "u1", email: "lara@learnflow.ch", role: "learner" });
    route("POST", "/query", 401, { detail: "Not authenticated" });

    render(<App />);
    await login();
    await screen.findByRole("button", { name: /abmelden/i });
    await userEvent.type(screen.getByPlaceholderText(/frage stellen/i), "Frage");
    await userEvent.click(screen.getByRole("button", { name: /senden/i }));
    await screen.findByText(/sitzung abgelaufen/i);

    await login();

    await screen.findByRole("button", { name: /abmelden/i });
    expect(screen.queryByText(/sitzung abgelaufen/i)).not.toBeInTheDocument();
  });
});
