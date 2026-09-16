import { useState, useRef, useEffect } from "react";
import type { AuthUser, Message } from "../types";
import { api, ApiError } from "../api/client";
import Layout from "./Layout";
import MessageBubble from "./MessageBubble";

// Mirrors QueryRequest in openapi.yaml (question: minLength 3, maxLength 1000).
// Checked here as well as there because the backend answers a violation with a
// 422 whose body is a list of field errors — it reaches the user as a generic
// failure and says nothing about what to change (US-01).
export const MIN_QUESTION_CHARS = 3;
export const MAX_QUESTION_CHARS = 1000;

// Below this the counter stays out of the way; above it the user is close
// enough to the limit that finding out only on send would mean rewriting.
const COUNTER_VISIBLE_FROM = MAX_QUESTION_CHARS - 100;

// Ties the textarea to its hint via aria-describedby.
const INPUT_ERROR_ID = "question-error";

/**
 * The question's length as the backend counts it.
 *
 * Spread, not `.length`: a JavaScript string is UTF-16, so an emoji or any
 * other character outside the BMP counts as two. Python's `len()` — which is
 * what pydantic applies to `question` — counts code points, so `"🙂".length`
 * is 2 on this side and 1 on the other. Iterating the string yields code
 * points and puts both ends on the same number.
 */
function questionLength(question: string): number {
  return [...question].length;
}

/**
 * The reason a question cannot be sent, or null when it can.
 *
 * Measured on the trimmed question because that is what `send` puts on the
 * wire — validating the raw value would reject three spaces and accept a
 * 1000-character question with a trailing newline the backend then refuses.
 */
export function validateQuestion(question: string): string | null {
  const length = questionLength(question.trim());
  if (length < MIN_QUESTION_CHARS) {
    return `Die Frage braucht mindestens ${MIN_QUESTION_CHARS} Zeichen.`;
  }
  if (length > MAX_QUESTION_CHARS) {
    return `Die Frage darf höchstens ${MAX_QUESTION_CHARS} Zeichen haben — aktuell ${length}.`;
  }
  return null;
}

/**
 * One sentence per outcome the API separates, because the next step differs.
 *
 * 429 (T-45) passes by itself and says how long to wait; 503 is an outage the
 * user can only sit out (US-01); anything else is worth retrying now. Repeating
 * the server's own German text would be worse than mapping the status here —
 * the body says "warte einen Moment" for the login limit too, and cannot know
 * that this one is about asking questions. None of the three invents an answer:
 * the bubble stays `suppressed`.
 */
function failureMessage(err: unknown): string {
  if (err instanceof ApiError && err.status === 429) {
    return "Zu viele Fragen in kurzer Zeit. Bitte warte eine Minute und frage dann erneut.";
  }
  if (err instanceof ApiError && err.status === 503) {
    return "Die Suche ist derzeit nicht erreichbar. Bitte versuche es in einigen Minuten erneut.";
  }
  return "Fehler beim Abrufen der Antwort. Bitte versuche es erneut.";
}

interface Props {
  user: AuthUser;
  onLogout: () => void;
  // Liegen in App (T-36): /quiz und /quiz-review unmounten ChatView, ein
  // hier lokaler State wäre beim Zurücknavigieren leer bzw. zurückgesetzt —
  // US-09 verlangt die Historie für die ganze Browser-Session. `busy` gehört
  // dazu: bliebe es lokal, würde ein Remount es auf `false` zurücksetzen,
  // während eine vor der Navigation gestartete `query` noch läuft und beim
  // Landen still in `messages`/`sessionId` schreibt (siehe Kommentar bei
  // `send`) — die Sperre gegen "Neuer Chat"/eine zweite Frage während des
  // Wartens griffe dann nicht mehr.
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  sessionId: string | null;
  setSessionId: React.Dispatch<React.SetStateAction<string | null>>;
  busy: boolean;
  setBusy: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function ChatView({
  user, onLogout, messages, setMessages, sessionId, setSessionId, busy, setBusy,
}: Props) {
  const [input, setInput] = useState("");
  const [inputError, setInputError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (busy) return;
    const q = input.trim();
    const invalid = validateQuestion(q);
    if (invalid) {
      // The input is kept, not cleared: a question that is 20 characters too
      // long has to be shortenable, not retyped.
      setInputError(invalid);
      return;
    }
    setInputError("");
    setInput("");
    setBusy(true);
    setMessages(prev => [...prev, { role: "user", content: q }]);

    try {
      const res = await api.query(q, sessionId, user.token);
      setSessionId(res.session_id);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: res.message ?? "Ich weiss es nicht.",
        answer_id: res.answer_id,
        suppressed: res.suppressed,
        suppression_reason: res.suppression_reason,
        refinement_hint: res.refinement_hint,
        citations: res.citations,
        confidence: res.confidence,
        debug: res.debug,
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: failureMessage(err),
        suppressed: true,
      }]);
    } finally {
      setBusy(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  // The draft and its hint belong to the chat being discarded. Keeping them
  // while the transcript goes would open the "new" chat on a question the user
  // never sent and a reason that refers to nothing on screen.
  const newChat = () => {
    setMessages([]);
    setSessionId(null);
    setInput("");
    setInputError("");
  };

  return (
    <Layout user={user} onLogout={onLogout}>
      {/* Title + primary action, like every other page's header */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "var(--space-4) var(--space-6) 0",
      }}>
        <div style={{ fontWeight: "var(--font-black)", fontSize: "var(--text-xl)", color: "var(--text-primary)" }}>KI-Chat</div>
        {/* Disabled while an answer is on its way, like the textarea and the
            send button: `send` holds `sessionId` and `messages` across the
            await, so a reset in that window is undone when the response
            lands — the old session id returns and the answer is appended to
            a transcript that no longer holds its question. */}
        <button className="primary" onClick={newChat} disabled={busy}>Neuer Chat</button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-6) 0" }}>
        <div style={{ maxWidth: 760, margin: "0 auto", padding: "0 var(--space-6)", display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
          {messages.length === 0 && (
            <div style={{ textAlign: "center", color: "var(--text-muted)", marginTop: 80 }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>📚</div>
              <div style={{ fontWeight: "var(--font-bold)", fontSize: "var(--text-xl)", color: "var(--text-primary)" }}>Stelle eine Frage</div>
              <div style={{ fontSize: "var(--text-sm)", marginTop: 6 }}>Ich beantworte sie auf Basis der Dokumente im Korpus.</div>
            </div>
          )}
          {messages.map((m, i) => <MessageBubble key={i} message={m} token={user.token} />)}
          {/* role="status" so the wait is announced rather than only
              drawn — the answer takes seconds (NFA: p95 ≤ 10 s). */}
          {busy && (
            <div role="status" style={{ color: "var(--text-muted)", fontSize: "var(--text-sm)", padding: "8px 0" }}>
              Suche im Korpus…
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Input */}
      <div style={{
        borderTop: "1px solid var(--border)", padding: "var(--space-4) var(--space-6)",
        background: "var(--surface)", flexShrink: 0,
      }}>
        <div style={{ maxWidth: 760, margin: "0 auto" }}>
          <div style={{ display: "flex", gap: 10 }}>
            <textarea
              value={input}
              // Deliberately no `maxLength`: the attribute truncates a
              // pasted question silently, and US-01 asks for a hint rather
              // than for the tail to disappear unremarked.
              onChange={e => { setInput(e.target.value); setInputError(""); }}
              onKeyDown={handleKey}
              placeholder="Frage stellen… (Enter zum Senden)"
              aria-label="Frage"
              aria-invalid={inputError !== ""}
              // role="alert" announces the hint once, when it appears.
              // Returning to the field later would say nothing about why it
              // is invalid, so the message is also its description.
              aria-describedby={inputError ? INPUT_ERROR_ID : undefined}
              disabled={busy}
              rows={2}
              style={{ resize: "none", flex: 1 }}
            />
            {/* Enabled for anything non-empty, not only for a valid
                question: a disabled button rejects silently, and the whole
                point of the criterion is that the user is told why. */}
            <button className="primary" onClick={send} disabled={busy || !input.trim()}
              style={{ alignSelf: "flex-end", padding: "10px 18px" }}>
              Senden
            </button>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, marginTop: 6, minHeight: 16 }}>
            <span id={INPUT_ERROR_ID} role="alert" style={{ fontSize: "var(--text-xs)", color: "var(--red)", fontWeight: "var(--font-semibold)" }}>
              {inputError}
            </span>
            {/* Counted the same way as the check that rejects it, or the
                counter would say 998 while the send is refused at 1001. */}
            {questionLength(input.trim()) > COUNTER_VISIBLE_FROM && (
              <span style={{
                fontSize: "var(--text-xs)", whiteSpace: "nowrap",
                color: questionLength(input.trim()) > MAX_QUESTION_CHARS ? "var(--red)" : "var(--text-muted)",
              }}>
                {questionLength(input.trim())} / {MAX_QUESTION_CHARS}
              </span>
            )}
          </div>
        </div>
      </div>
    </Layout>
  );
}
