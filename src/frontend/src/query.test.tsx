/**
 * @vitest-environment jsdom
 *
 * T-20: the question UI (US-01). Until T-17 landed, POST /api/query answered
 * 501 and there was nothing here to test — the flow now returns real citations,
 * and the three acceptance criteria (client-side 3–1000, loading indicator,
 * clickable source references) each get their own case.
 *
 * Like upload.test.tsx and write-confirmation.test.tsx this runs against the
 * shared fetch stub (test/api.ts) instead of a module mock: the assertions are
 * about what leaves the app — in the validation cases, precisely that nothing
 * does.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import App from "./App";
import {
  MAX_QUESTION_CHARS,
  MIN_QUESTION_CHARS,
  validateQuestion,
} from "./components/ChatView";
import { installApiStub, installAppEnvironment, type ApiStub } from "../test/api";
import type { Citation, QueryResponse, Role } from "./api/client";

let api: ApiStub;

function citation(index: number, filename: string, excerpt = "Ein Auszug."): Citation {
  return {
    chunk_id: `chunk-${index}`,
    document_id: `doc-${index}`,
    filename,
    page: index,
    excerpt,
    index,
  };
}

/**
 * Typed against the spec, so a response the API could never send fails here —
 * which is what caught this fixture: it described the placeholder T-17 left
 * behind (suppressed, `generation_not_implemented`, "Quellen gefunden, Antwort
 * folgt"), and T-18 removed both the reason from the enum and the state from
 * the endpoint. The default is now the answer /api/query actually returns.
 */
function answer(overrides: Partial<QueryResponse> = {}): QueryResponse {
  return {
    session_id: "sess-1",
    answer_id: "ans-1",
    suppressed: false,
    suppression_reason: null,
    message: "SKOS verlangt je Sprache genau ein prefLabel.",
    refinement_hint: null,
    citations: [citation(1, "skos.pdf")],
    confidence: { score: 0.76, retrieval_score: 0.76, citation_coverage: 0, band: "hoch" },
    debug: null,
    ...overrides,
  };
}

/** Signs in and waits until the question UI stands. */
async function openChat(role: Role = "learner") {
  api.route("post", "/api/auth/login", 200, {
    access_token: "tok123",
    token_type: "bearer",
    role,
  });
  api.route("get", "/api/auth/me", 200, {
    id: "u1",
    email: "lara@learnflow.ch",
    role,
  });
  render(<App />);
  await userEvent.type(screen.getByLabelText(/e-mail/i), "lara@learnflow.ch");
  await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
  return await screen.findByLabelText("Frage");
}

const send = () => userEvent.click(screen.getByRole("button", { name: /senden/i }));

/** The question the app actually put on the wire. */
const sentQuestion = (index = 0) =>
  (api.requests("post", "/api/query")[index]?.json as { question?: string })?.question;

beforeEach(() => {
  api = installApiStub();
  installAppEnvironment();
  api.route("post", "/api/query", 200, answer());
});

afterEach(() => {
  api.release();
  cleanup();
  vi.unstubAllGlobals();
});

// --- AK 1: client-side length validation -----------------------------------

describe("validateQuestion", () => {
  it("rejects a question below the minimum", () => {
    expect(validateQuestion("ab")).toMatch(new RegExp(`${MIN_QUESTION_CHARS} Zeichen`));
  });

  it("rejects whitespace that only looks like a question", () => {
    expect(validateQuestion("     ")).not.toBeNull();
  });

  it("accepts a question exactly at the minimum — the API rejects below, not at", () => {
    expect(validateQuestion("abc")).toBeNull();
  });

  it("accepts a question exactly at the maximum", () => {
    expect(validateQuestion("a".repeat(MAX_QUESTION_CHARS))).toBeNull();
  });

  it("rejects one character above the maximum and names the current length", () => {
    const over = MAX_QUESTION_CHARS + 1;

    expect(validateQuestion("a".repeat(over))).toMatch(new RegExp(String(over)));
  });

  it("counts an emoji once, as the backend does", () => {
    // A JavaScript string is UTF-16 and `"🙂".length` is 2; pydantic applies
    // Python's len(), which counts code points. Counting units here would
    // refuse a question the API would still have accepted.
    const emoji = "🙂".repeat(MAX_QUESTION_CHARS);

    expect(validateQuestion(emoji)).toBeNull();
    expect(validateQuestion("🙂")).toMatch(new RegExp(`${MIN_QUESTION_CHARS} Zeichen`));
  });

  it("measures the trimmed question, because that is what gets sent", () => {
    // Both directions of the same trim: padding must not rescue a short
    // question, and must not sink one that fits once it is stripped.
    expect(validateQuestion("  ab  ")).not.toBeNull();
    expect(validateQuestion(`  ${"a".repeat(MAX_QUESTION_CHARS)}  `)).toBeNull();
  });
});

describe("Frage-UI", () => {
  it("sends a valid question with the session slot the contract declares", async () => {
    const field = await openChat();

    await userEvent.type(field, "Was regelt der EU AI Act?");
    await send();

    await waitFor(() => expect(api.count("post", "/api/query")).toBe(1));
    expect(sentQuestion()).toBe("Was regelt der EU AI Act?");
    expect(api.last("post", "/api/query")?.json).toMatchObject({ session_id: null });
    expect(api.last("post", "/api/query")?.authorization).toBe("Bearer tok123");
  });

  it("continues the session the first answer opened", async () => {
    const field = await openChat();
    await userEvent.type(field, "Erste Frage zum Korpus");
    await send();
    await waitFor(() => expect(api.count("post", "/api/query")).toBe(1));

    await userEvent.type(screen.getByLabelText("Frage"), "Zweite Frage zum Korpus");
    await send();

    await waitFor(() => expect(api.count("post", "/api/query")).toBe(2));
    expect(api.last("post", "/api/query")?.json).toMatchObject({ session_id: "sess-1" });
  });

  // The placeholder advertises Enter, and every other case here clicks the
  // button — which left the key handler with no coverage at all. Both halves
  // matter: Enter has to send, and Shift+Enter has to stay a line break, or a
  // two-paragraph question is impossible to write.
  it("sends on Enter", async () => {
    const field = await openChat();

    await userEvent.type(field, "Was regelt der EU AI Act?{Enter}");

    await waitFor(() => expect(api.count("post", "/api/query")).toBe(1));
    expect(sentQuestion()).toBe("Was regelt der EU AI Act?");
  });

  it("keeps Shift+Enter a line break instead of sending", async () => {
    const field = await openChat();

    await userEvent.type(field, "Erste Zeile{Shift>}{Enter}{/Shift}zweite Zeile");

    expect(api.count("post", "/api/query")).toBe(0);
    expect(field).toHaveValue("Erste Zeile\nzweite Zeile");
  });

  it("applies the same length check to the Enter path", async () => {
    // Two ways in, one rule — the button path must not be the only guarded one.
    const field = await openChat();

    await userEvent.type(field, "ab{Enter}");

    expect(await screen.findByRole("alert")).toHaveTextContent(/mindestens 3 Zeichen/);
    expect(api.count("post", "/api/query")).toBe(0);
  });

  it("rejects a too-short question before it reaches the network, with a reason", async () => {
    // Without the client-side check this travels to the API for a 422, whose
    // body is a list of field errors — the user sees "Fehler beim Abrufen" and
    // is told nothing about the length (US-01).
    const field = await openChat();

    await userEvent.type(field, "ab");
    await send();

    expect(await screen.findByRole("alert")).toHaveTextContent(/mindestens 3 Zeichen/);
    expect(api.count("post", "/api/query")).toBe(0);
  });

  it("rejects a too-long question before it reaches the network", async () => {
    const field = await openChat();

    // Pasted rather than typed: a thousand keystrokes is slow, and paste is
    // how a question of this length actually arrives.
    await userEvent.click(field);
    await userEvent.paste("a".repeat(MAX_QUESTION_CHARS + 1));
    await send();

    expect(await screen.findByRole("alert")).toHaveTextContent(/höchstens 1000 Zeichen/);
    expect(api.count("post", "/api/query")).toBe(0);
  });

  it("points the field at its hint, so the reason survives a refocus", async () => {
    // role="alert" announces the hint once, when it appears. Without the
    // description a screen reader returning to the field reports "invalid"
    // and nothing about why.
    const field = await openChat();
    expect(field).not.toHaveAttribute("aria-describedby");

    await userEvent.type(field, "ab");
    await send();

    const hint = await screen.findByRole("alert");
    expect(field).toHaveAttribute("aria-describedby", hint.id);
    expect(hint).toHaveTextContent(/mindestens 3 Zeichen/);
  });

  it("keeps the rejected question so it can be fixed instead of retyped", async () => {
    const field = await openChat();

    await userEvent.type(field, "ab");
    await send();

    expect(field).toHaveValue("ab");
  });

  it("clears the hint as soon as the question is edited", async () => {
    const field = await openChat();
    await userEvent.type(field, "ab");
    await send();
    expect(await screen.findByRole("alert")).toHaveTextContent(/mindestens/);

    await userEvent.type(field, "c");

    await waitFor(() => expect(screen.getByRole("alert")).toBeEmptyDOMElement());
  });

  it("counts down towards the limit before the send is refused", async () => {
    // The counter is what makes the upper bound noticeable while writing; only
    // seeing it on send would mean rewriting a question that is already long.
    const field = await openChat();

    await userEvent.click(field);
    await userEvent.paste("a".repeat(MAX_QUESTION_CHARS - 10));

    expect(screen.getByText(`${MAX_QUESTION_CHARS - 10} / ${MAX_QUESTION_CHARS}`)).toBeInTheDocument();
  });

  it("stays out of the way for a question nowhere near the limit", async () => {
    // Without this the counter could be permanently visible — an inverted
    // condition looks identical in the test above.
    const field = await openChat();

    await userEvent.type(field, "Was regelt der EU AI Act?");

    expect(screen.queryByText(new RegExp(`/ ${MAX_QUESTION_CHARS}`))).not.toBeInTheDocument();
  });

  // --- AK 2: loading indicator ---------------------------------------------

  it("shows the wait while the answer is in flight and clears it afterwards", async () => {
    const field = await openChat();
    api.hold("post", "/api/query");

    await userEvent.type(field, "Was regelt der EU AI Act?");
    await send();

    expect(await screen.findByRole("status")).toHaveTextContent(/Suche im Korpus/);
    // Both entry points closed while one answer is on its way — the send guard
    // alone would still let a second question through the key handler.
    expect(screen.getByLabelText("Frage")).toBeDisabled();
    expect(screen.getByRole("button", { name: /senden/i })).toBeDisabled();

    api.release("post", "/api/query");

    await waitFor(() => expect(screen.queryByRole("status")).not.toBeInTheDocument());
    expect(screen.getByLabelText("Frage")).toBeEnabled();
  });

  // --- AK 3: clickable source references ------------------------------------

  it("shows the answer's sources and unfolds one on click", async () => {
    api.route("post", "/api/query", 200, answer({
      citations: [citation(1, "skos.pdf", "Der belegende Abschnitt."), citation(2, "ai-act.pdf")],
    }));
    const field = await openChat();

    await userEvent.type(field, "Was regelt der EU AI Act?");
    await send();

    await userEvent.click(await screen.findByRole("button", { name: /2 Quellen/i }));
    const excerptToggle = screen.getByRole("button", { name: /Auszug ausklappen: \[1\] skos\.pdf/ });

    expect(excerptToggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByText("Der belegende Abschnitt.")).toBeInTheDocument();

    await userEvent.click(excerptToggle);

    expect(excerptToggle).toHaveAttribute("aria-expanded", "true");
  });

  it("opens the document viewer on the source reference with the belegenden Abschnitt highlighted", async () => {
    api.route("post", "/api/query", 200, answer({
      citations: [citation(1, "skos.pdf", "Der belegende Abschnitt.")],
    }));
    api.route("get", "/api/documents/{document_id}/content", 200, {
      id: "doc-1",
      filename: "skos.pdf",
      status: "available",
      chunks: [
        { chunk_id: "chunk-other", chunk_index: 0, page: null, heading: null, content: "Vorheriger Abschnitt." },
        { chunk_id: "chunk-1", chunk_index: 1, page: 1, heading: "Labels", content: "Der belegende Abschnitt." },
      ],
    });
    const field = await openChat();

    await userEvent.type(field, "Was regelt der EU AI Act?");
    await send();

    await userEvent.click(await screen.findByRole("button", { name: /1 Quelle/i }));
    await userEvent.click(screen.getByRole("button", { name: /Originaldokument öffnen: \[1\] skos\.pdf/ }));

    const dialog = await screen.findByRole("dialog", { name: /skos\.pdf/ });
    expect(within(dialog).getAllByText("Der belegende Abschnitt.")).toHaveLength(1);

    await userEvent.click(within(dialog).getByRole("button", { name: /schliessen/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("offers no sources when the gate suppressed without any", async () => {
    // The state T-17 produces below the retrieval gate: suppressed, and
    // deliberately no citations — nothing worth pointing at. An empty "0
    // Quellen" button would invite a click into nothing.
    api.route("post", "/api/query", 200, answer({
      suppressed: true,
      suppression_reason: "retrieval_gate",
      message: "Dazu finde ich nichts in den freigegebenen Unterlagen.",
      citations: [],
    }));
    const field = await openChat();

    await userEvent.type(field, "Wie hoch ist der Mindestlohn in Portugal?");
    await send();

    expect(await screen.findByText(/finde ich nichts/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Quelle/i })).not.toBeInTheDocument();
  });

  it("labels a source without a page without a dangling separator", async () => {
    // Markdown chunks carry no page, so `page: null` is the normal case for
    // part of the corpus — not an edge case.
    api.route("post", "/api/query", 200, answer({
      citations: [{ ...citation(1, "richtlinien.md"), page: null }],
    }));
    const field = await openChat();
    await userEvent.type(field, "Was regelt der EU AI Act?");
    await send();

    await userEvent.click(await screen.findByRole("button", { name: /1 Quelle/i }));

    expect(
      screen.getByRole("button", { name: "Originaldokument öffnen: [1] richtlinien.md" }),
    ).toBeInTheDocument();
  });

  it("numbers the sources as the answer will cite them", async () => {
    api.route("post", "/api/query", 200, answer({
      citations: [citation(1, "skos.pdf"), citation(2, "ai-act.pdf")],
    }));
    const field = await openChat();
    await userEvent.type(field, "Was regelt der EU AI Act?");
    await send();

    await userEvent.click(await screen.findByRole("button", { name: /2 Quellen/i }));

    expect(
      screen.getByRole("button", { name: /Originaldokument öffnen: \[1\] skos\.pdf · S\. 1/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Originaldokument öffnen: \[2\] ai-act\.pdf · S\. 2/ }),
    ).toBeInTheDocument();
  });

  // --- US-01: a failing service must not look like an answer ----------------

  it("names an unreachable retrieval service as the outage it is", async () => {
    // 503 is the status T-17 gave a provider or database failure precisely so
    // it would not be dressed up as a suppressed answer — the UI has to keep
    // that distinction rather than flatten it into "try again".
    api.route("post", "/api/query", 503, { detail: "Retrieval ist derzeit nicht verfügbar." });
    const field = await openChat();

    await userEvent.type(field, "Was regelt der EU AI Act?");
    await send();

    expect(await screen.findByText(/derzeit nicht erreichbar/)).toBeInTheDocument();
    expect(screen.queryByText(/prefLabel/)).not.toBeInTheDocument();
  });

  it("tells a rate limit from an outage and names the wait", async () => {
    // T-45: 429 passes by itself within a minute, 503 does not. Flattening both
    // into "Bitte versuche es erneut" tells the user to hammer a limit that is
    // counting exactly those attempts.
    api.route("post", "/api/query", 429, {
      detail: "Zu viele Anfragen. Bitte warte einen Moment und versuche es erneut.",
    });
    const field = await openChat();

    await userEvent.type(field, "Was regelt der EU AI Act?");
    await send();

    expect(await screen.findByText(/Zu viele Fragen in kurzer Zeit/)).toBeInTheDocument();
    expect(screen.queryByText(/nicht erreichbar/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Fehler beim Abrufen/)).not.toBeInTheDocument();
  });

  // --- Header: no control that acts on a view you cannot see ---------------

  it("starts a fresh session after Neuer Chat", async () => {
    const field = await openChat();
    await userEvent.type(field, "Erste Frage zum Korpus");
    await send();
    await waitFor(() => expect(api.count("post", "/api/query")).toBe(1));

    await userEvent.click(screen.getByRole("button", { name: /neuer chat/i }));
    await userEvent.type(screen.getByLabelText("Frage"), "Unabhaengige zweite Frage");
    await send();

    // Not "sess-1": a new chat that keeps the old session id would thread the
    // previous questions into it once T-18 uses the history.
    await waitFor(() => expect(api.count("post", "/api/query")).toBe(2));
    expect(api.last("post", "/api/query")?.json).toMatchObject({ session_id: null });
    expect(screen.queryByText("Erste Frage zum Korpus")).not.toBeInTheDocument();
  });

  it("carries no rejected question into the new chat", async () => {
    // The reset dropped the transcript and the session but left the field
    // alone, so a question refused for its length — and the red hint naming
    // that length — survived into a chat that had nothing to do with either.
    const field = await openChat();
    await userEvent.type(field, "ab");
    await send();
    expect(await screen.findByRole("alert")).toHaveTextContent(/mindestens 3 Zeichen/);

    await userEvent.click(screen.getByRole("button", { name: /neuer chat/i }));

    // The hint element stays mounted — it reserves its line so the layout does
    // not jump — so what has to go is its text, and with it the description.
    expect(screen.getByLabelText("Frage")).toHaveValue("");
    expect(screen.getByRole("alert")).toBeEmptyDOMElement();
    expect(screen.getByLabelText("Frage")).not.toHaveAttribute("aria-describedby");
  });

  it("cannot reset the chat out from under an answer that is still coming", async () => {
    // The reset would win the click and lose the race: `send` holds sessionId
    // and messages across the await, so the landing response puts the old
    // session id back and appends its answer to a transcript that no longer
    // carries the question. Closed by disabling, like the other two controls.
    const field = await openChat();
    api.hold("post", "/api/query");

    await userEvent.type(field, "Was regelt der EU AI Act?");
    await send();

    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /neuer chat/i })).toBeDisabled();

    api.release("post", "/api/query");

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /neuer chat/i })).toBeEnabled(),
    );
  });

  it("hides the chat-only controls while the document view is open", async () => {
    // Both used to sit in the header regardless: "Neuer Chat" cleared a
    // transcript nobody could see, and "⚙ Parameter" flipped its arrow over a
    // panel that only renders in the chat branch.
    api.route("get", "/api/admin/config", 200, { config: { retrieval_top_k: "20" } });
    api.route("get", "/api/documents", 200, []);
    await openChat("admin");
    expect(screen.getByRole("button", { name: /neuer chat/i })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /^dokumente$/i }));

    expect(await screen.findByRole("button", { name: /^chat$/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /neuer chat/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /parameter/i })).not.toBeInTheDocument();
  });

  it("falls back to a retryable message for any other failure", async () => {
    api.route("post", "/api/query", 422, {
      detail: [{ loc: ["body", "question"], msg: "too short", type: "value_error" }],
    });
    const field = await openChat();

    await userEvent.type(field, "Was regelt der EU AI Act?");
    await send();

    expect(await screen.findByText(/Bitte versuche es erneut/)).toBeInTheDocument();
  });
});
