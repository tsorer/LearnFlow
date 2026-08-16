/**
 * @vitest-environment jsdom
 *
 * From the T-39 review: the UI may confirm a write only once it has actually
 * arrived, and must not send it twice. That confirmation is the part which has
 * to be right before the endpoints even exist.
 *
 * Each of the two write paths is checked against two failure cases:
 *
 *   - a status the spec carries permanently (422 resp. 404). That one survives
 *     T-30 and T-37.
 *   - the 501 placeholder, which both endpoints actually return today. It is
 *     the only answer users currently get to see, and without this case the
 *     corresponding messages would have no test at all.
 *
 * The 501 case has a built-in expiry date: as soon as T-30 resp. T-37 takes the
 * code out of the spec, the typed routes reject it and the test stops
 * compiling. That is deliberate — it surfaces in exactly the commit that also
 * has to remove the 501 branch in ChatView resp. MessageBubble. Delete both
 * together then; do not swap the status code.
 *
 * Like session.test.tsx, this runs against the shared fetch stub (test/api.ts)
 * rather than a module mock: what is asserted is what goes over the wire.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup, fireEvent, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import App from "./App";
import type { Role } from "./api/client";
import { installApiStub, installAppEnvironment, type ApiStub } from "../test/api";

let api: ApiStub;

async function login(email: string) {
  await userEvent.type(screen.getByLabelText(/e-mail/i), email);
  await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
}

function authRoutes(role: Role) {
  api.route("post", "/api/auth/login", 200, {
    access_token: "tok123",
    token_type: "bearer",
    role,
  });
  api.route("get", "/api/auth/me", 200, { id: "u1", email: "u@learnflow.ch", role });
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

describe("admin parameters (T-37)", () => {
  async function openPanel() {
    authRoutes("admin");
    api.route("get", "/api/admin/config", 200, { config: { top_k: "20" } });
    render(<App />);
    await login("admin@learnflow.ch");
    await userEvent.click(await screen.findByRole("button", { name: /parameter/i }));
  }

  it("reports no success when the write fails", async () => {
    // The core of the finding: `.catch(() => {})` showed the green check even
    // when the config table had never seen anything — the admin would go on
    // working against a threshold that is not set.
    await openPanel();
    // 422 rather than the 501 placeholder: T-37 takes 501 out of the spec, 422
    // ("unknown key or invalid value") stays. That way the test survives the
    // implementation instead of failing against the typed routes.
    api.route("put", "/api/admin/config", 422, { detail: "Unbekannter Schluessel" });

    await userEvent.click(screen.getByRole("button", { name: /^speichern$/i }));

    expect(await screen.findByText(/konnten nicht gespeichert werden/i)).toBeInTheDocument();
    // Match the check mark, not /gespeichert/i: the error message contains that
    // word itself ("konnten nicht gespeichert werden").
    expect(screen.queryByText(/✓ Gespeichert/)).not.toBeInTheDocument();
  });

  it("names the 501 placeholder while T-37 is open", async () => {
    // Goes away once T-37 removes 501 from the spec — see the file header.
    await openPanel();
    api.route("put", "/api/admin/config", 501, { detail: "Not implemented (T-37)" });

    await userEvent.click(screen.getByRole("button", { name: /^speichern$/i }));

    expect(await screen.findByText(/noch nicht speicherbar/i)).toBeInTheDocument();
    expect(screen.queryByText(/✓ Gespeichert/)).not.toBeInTheDocument();
  });

  it("reports success when the write goes through", async () => {
    await openPanel();
    api.route("put", "/api/admin/config", 200, { config: { top_k: "20" } });

    await userEvent.click(screen.getByRole("button", { name: /^speichern$/i }));

    expect(await screen.findByText(/✓ Gespeichert/)).toBeInTheDocument();
  });
});

describe("feedback (T-30)", () => {
  const FEEDBACK = "/api/answers/{answer_id}/feedback" as const;
  const feedbackCalls = () => api.count("post", FEEDBACK);

  /** Signs a learner in and asks a question, until the thumbs are on screen. */
  async function askQuestion() {
    authRoutes("learner");
    api.route("post", "/api/query", 200, {
      answer_id: "a1",
      session_id: "s1",
      message: "Antwort",
      suppressed: false,
      // Required by the spec — the old hand-written mock omitted it, which is
      // exactly the drift the typed routes now prevent.
      citations: [],
    });
    render(<App />);
    await login("lara@learnflow.ch");
    await userEvent.type(await screen.findByPlaceholderText(/frage stellen/i), "Frage");
    await userEvent.click(screen.getByRole("button", { name: /senden/i }));
    return await screen.findByRole("button", { name: /^hilfreich$/i });
  }

  it("sends only one POST while the first is still in flight", async () => {
    const thumbUp = await askQuestion();
    api.route("post", FEEDBACK, 204);
    api.hold();

    // `feedback` is still null inside this window and is useless as a lock —
    // without `submitting` these would be two rows for the same answer_id, the
    // third of them with a contradicting `helpful`.
    fireEvent.click(thumbUp);
    fireEvent.click(thumbUp);
    fireEvent.click(screen.getByRole("button", { name: /nicht hilfreich/i }));

    expect(feedbackCalls()).toBe(1);

    await act(async () => { api.release(); });
    expect(feedbackCalls()).toBe(1);
  });

  it("allows another rating after a failure", async () => {
    // The lock must not latch: a failed write does not mean the user is no
    // longer allowed to rate.
    //
    // 404 rather than the 501 placeholder: T-30 takes 501 out of the spec for
    // this endpoint (leaving 204/401/404/400), and the typed routes would then
    // rightly reject the line. 404 stays in the contract permanently, so the
    // test survives the switch.
    const thumbUp = await askQuestion();
    api.route("post", FEEDBACK, 404, { detail: "Antwort nicht gefunden" });

    await userEvent.click(thumbUp);

    expect(await screen.findByText(/konnte nicht gespeichert werden/i)).toBeInTheDocument();
    expect(thumbUp).toBeEnabled();

    await userEvent.click(thumbUp);
    expect(feedbackCalls()).toBe(2);
  });

  it("names the 501 placeholder while T-30 is open", async () => {
    // Goes away once T-30 removes 501 from the spec — see the file header.
    const thumbUp = await askQuestion();
    api.route("post", FEEDBACK, 501, { detail: "Not implemented (T-30)" });

    await userEvent.click(thumbUp);

    expect(await screen.findByText(/noch nicht verfügbar/i)).toBeInTheDocument();
    expect(thumbUp).toBeEnabled();
  });
});
