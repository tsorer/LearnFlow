/**
 * @vitest-environment jsdom
 *
 * T-08: JWT wird ausschliesslich im React-State gehalten (ADR-002).
 * Der Test rendert App real und prüft die Invariante gegen die Komponente —
 * nicht gegen einen Mock —, sodass ein Rückfall auf localStorage auffällt.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import App from "./App";
import { ApiError, api } from "./api/client";

// ApiError bleibt die echte Klasse — Login.tsx prueft per instanceof darauf.
// Der 401-Handler ist hier eine Attrappe: die Session-Logik gehoert zu T-40 und
// wird in session.test.tsx gegen den echten client.ts geprueft.
vi.mock("./api/client", async () => {
  const actual = await vi.importActual<typeof import("./api/client")>("./api/client");
  return {
    ApiError: actual.ApiError,
    setUnauthorizedHandler: vi.fn(),
    api: { login: vi.fn(), me: vi.fn() },
  };
});

const mockLogin = vi.mocked(api.login);
const mockMe = vi.mocked(api.me);

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  vi.clearAllMocks();
  // Vite ersetzt __BUILD_TIME__ via define() beim Build; unter Vitest fehlt es.
  vi.stubGlobal("__BUILD_TIME__", new Date().toISOString());
  // jsdom implementiert scrollIntoView nicht (von ChatView nach Login genutzt).
  Element.prototype.scrollIntoView = vi.fn();
  // Jeder Test startet auf der geschützten Wurzel.
  window.history.pushState({}, "", "/");
});

afterEach(cleanup);

describe("App auth (T-08)", () => {
  it("leitet unauthentifizierten Zugriff auf die geschützte Route nach /login um (AK 3)", () => {
    render(<App />);
    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/passwort/i)).toBeInTheDocument();
    expect(window.location.pathname).toBe("/login");
  });

  it("speichert nach erfolgreichem Login keinen Token in localStorage/sessionStorage", async () => {
    mockLogin.mockResolvedValue({ access_token: "tok123", token_type: "bearer", role: "learner" });
    mockMe.mockResolvedValue({ id: "u1", email: "lara@learnflow.ch", role: "learner" });

    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    // Login-Formular verschwindet → ChatView ist gemountet, User ist im State.
    await waitFor(() =>
      expect(screen.queryByLabelText(/passwort/i)).not.toBeInTheDocument(),
    );
    // AK 1: Credentials werden an POST /auth/login gesendet.
    expect(mockLogin).toHaveBeenCalledWith("lara@learnflow.ch", "secret");
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("leitet nach Logout zurück auf /login (AK 3)", async () => {
    mockLogin.mockResolvedValue({ access_token: "tok123", token_type: "bearer", role: "learner" });
    mockMe.mockResolvedValue({ id: "u1", email: "lara@learnflow.ch", role: "learner" });

    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    const logout = await screen.findByRole("button", { name: /abmelden/i });
    await userEvent.click(logout);

    await waitFor(() => expect(screen.getByLabelText(/passwort/i)).toBeInTheDocument());
    expect(window.location.pathname).toBe("/login");
  });

  it("zeigt eine Fehlermeldung bei falschem Passwort und schreibt nichts in den Storage", async () => {
    mockLogin.mockRejectedValue(new Error("HTTP 401"));

    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    expect(await screen.findByText(/e-mail oder passwort falsch/i)).toBeInTheDocument();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
    expect(mockMe).not.toHaveBeenCalled();
  });

  it("meldet ein Rate-Limit (429) nicht als falsches Passwort", async () => {
    mockLogin.mockRejectedValue(new ApiError(429, '{"detail":"Rate limit exceeded"}'));

    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "correct");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    expect(await screen.findByText(/zu viele login-versuche/i)).toBeInTheDocument();
    expect(screen.queryByText(/e-mail oder passwort falsch/i)).not.toBeInTheDocument();
  });

  it("meldet einen Fehler in /auth/me nicht als falsches Passwort", async () => {
    mockLogin.mockResolvedValue({ access_token: "tok123", token_type: "bearer", role: "learner" });
    mockMe.mockRejectedValue(new Error("HTTP 500"));

    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "correct");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    expect(await screen.findByText(/profil konnte aber nicht geladen werden/i)).toBeInTheDocument();
    expect(screen.queryByText(/e-mail oder passwort falsch/i)).not.toBeInTheDocument();
    // Kein User im State → Route bleibt geschuetzt, Formular ist erneut absendbar.
    expect(window.location.pathname).toBe("/login");
    expect(screen.getByRole("button", { name: /anmelden/i })).toBeEnabled();
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it("haelt angemeldete User von /login fern (GuestRoute)", async () => {
    mockLogin.mockResolvedValue({ access_token: "tok123", token_type: "bearer", role: "learner" });
    mockMe.mockResolvedValue({ id: "u1", email: "lara@learnflow.ch", role: "learner" });

    window.history.pushState({}, "", "/login");
    render(<App />);
    await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
    await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
    await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));

    await waitFor(() => expect(window.location.pathname).toBe("/"));
    expect(screen.queryByLabelText(/passwort/i)).not.toBeInTheDocument();
  });
});
