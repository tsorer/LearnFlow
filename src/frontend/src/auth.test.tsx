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
import { api } from "./api/client";

vi.mock("./api/client", () => ({
  api: { login: vi.fn(), me: vi.fn() },
}));

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
    mockLogin.mockResolvedValue({ access_token: "tok123", role: "learner" });
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
    mockLogin.mockResolvedValue({ access_token: "tok123", role: "learner" });
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
  });
});
