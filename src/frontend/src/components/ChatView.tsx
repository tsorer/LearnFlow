import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { AuthUser, Message } from "../types";
import { api, ApiError } from "../api/client";
import Upload from "./Upload";
import MessageBubble from "./MessageBubble";

const PARAM_DEFS = [
  { key: "similarity_threshold",     label: "Similarity-Schwellwert",   type: "float", min: 0,  max: 1,    step: 0.01 },
  { key: "min_retrieval_confidence", label: "Min. Retrieval-Konfidenz", type: "float", min: 0,  max: 1,    step: 0.01 },
  { key: "min_citation_coverage",    label: "Min. Citation-Coverage",   type: "float", min: 0,  max: 1,    step: 0.01 },
  { key: "self_check_band_low",      label: "Self-Check Zone (unten)", type: "float", min: 0,  max: 1,    step: 0.01 },
  { key: "self_check_band_high",     label: "Self-Check Zone (oben)",  type: "float", min: 0,  max: 1,    step: 0.01 },
  { key: "top_k",                    label: "Top-K Kandidaten",         type: "int",   min: 1,  max: 100,  step: 1    },
  { key: "top_n",                    label: "Top-N ans LLM",            type: "int",   min: 1,  max: 50,   step: 1    },
  { key: "chunk_size",               label: "Chunk-Grösse (Tokens)",    type: "int",   min: 64, max: 2048, step: 64   },
  { key: "chunk_overlap",            label: "Chunk-Overlap (Tokens)",   type: "int",   min: 0,  max: 512,  step: 16   },
] as const;

const LLM_PARAM_DEFS = [
  { key: "llm_temperature", label: "Temperature",         min: 0,  max: 2,          step: 0.01, hint: "Standard: 1.0 — für RAG empfohlen: 0.0–0.2" },
  { key: "llm_max_tokens",  label: "Max Tokens",          min: 1,  max: 8192,       step: 1,    hint: "Standard: Modell-Max (kein Limit)" },
  { key: "llm_top_p",       label: "Top-P",               min: 0,  max: 1,          step: 0.01, hint: "Standard: 1.0 — nicht gleichzeitig mit Temperature setzen" },
  { key: "llm_seed",        label: "Seed (Reproduzierb.)", min: 0,  max: 2147483647, step: 1,    hint: "Standard: zufällig — gleicher Seed → gleiche Antwort" },
] as const;

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

interface Props { user: AuthUser; onLogout: () => void; }

export default function ChatView({ user, onLogout }: Props) {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [inputError, setInputError] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [showParams, setShowParams] = useState(false);
  const [params, setParams] = useState<Record<string, string>>({});
  const [paramSaved, setParamSaved] = useState(false);
  const [paramError, setParamError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const isAdmin = user.role === "admin";

  useEffect(() => {
    if (!isAdmin) return;
    api.getConfig(user.token).then(setParams).catch(() => {});
  }, []);

  const updateParam = useCallback((key: string, val: string) => {
    setParams(prev => ({ ...prev, [key]: val }));
    setParamSaved(false);
    setParamError("");
  }, []);

  const saveParams = async () => {
    setParamError("");
    try {
      await api.updateConfig(params, user.token);
      // Confirmed only once the write actually returned. Swallowing the
      // rejection showed the green check even when the config table never
      // received it: the admin would go on believing a fail-closed threshold
      // was stored that wasn't (ADR-008).
      setParamSaved(true);
      setTimeout(() => setParamSaved(false), 2000);
    } catch {
      setParamError("Parameter konnten nicht gespeichert werden.");
    }
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const canUpload = user.role === "knowledge_owner" || user.role === "admin";
  // Same role set as canUpload today, but a distinct permission (T-35's
  // /quiz-review, not document upload) — kept separate so the two do not
  // silently start meaning "one or the other" if they ever diverge.
  const canReview = user.role === "knowledge_owner" || user.role === "admin";

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
    <div style={{ display: "flex", height: "100vh", flexDirection: "column" }}>
      {/* Header */}
      <div style={{
        background: "var(--navy)", color: "#fff", padding: "0 24px",
        height: 52, display: "flex", alignItems: "center", justifyContent: "space-between",
        flexShrink: 0,
      }}>
        <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-.02em" }}>📚 LearnFlow</div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {canUpload && (
            <button className="secondary" style={{ fontSize: 12 }} onClick={() => setShowUpload(v => !v)}>
              {showUpload ? "Chat" : "Dokumente"}
            </button>
          )}
          {canReview && (
            <button className="secondary" style={{ fontSize: 12 }} onClick={() => navigate("/quiz-review")}>
              Quiz-Review
            </button>
          )}
          {/* Both hidden in the document view, because neither acts on it: the
              parameter panel and the transcript live in the chat branch, so
              from here the buttons only flipped an arrow resp. cleared
              something invisible. */}
          {isAdmin && !showUpload && (
            <button className="secondary" style={{ fontSize: 12 }} onClick={() => setShowParams(v => !v)}>
              {showParams ? "⚙ Parameter ▲" : "⚙ Parameter ▼"}
            </button>
          )}
          {/* Disabled while an answer is on its way, like the textarea and the
              send button: `send` holds `sessionId` and `messages` across the
              await, so a reset in that window is undone when the response
              lands — the old session id returns and the answer is appended to
              a transcript that no longer holds its question. */}
          {!showUpload && (
            <button className="secondary" style={{ fontSize: 12 }} onClick={newChat} disabled={busy}>
              Neuer Chat
            </button>
          )}
          <span style={{ fontSize: 12, color: "rgba(255,255,255,.5)" }}>{user.email}</span>
          <button className="secondary" style={{ fontSize: 12 }} onClick={onLogout}>Abmelden</button>
        </div>
      </div>

      {showUpload && canUpload ? (
        <Upload user={user} onClose={() => setShowUpload(false)} />
      ) : (
        <>
          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "24px 0" }}>
            <div style={{ maxWidth: 760, margin: "0 auto", padding: "0 24px", display: "flex", flexDirection: "column", gap: 16 }}>
              {messages.length === 0 && (
                <div style={{ textAlign: "center", color: "var(--muted)", marginTop: 80 }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>📚</div>
                  <div style={{ fontWeight: 700, fontSize: 18, color: "var(--navy)" }}>Stelle eine Frage</div>
                  <div style={{ fontSize: 13, marginTop: 6 }}>Ich beantworte sie auf Basis der Dokumente im Korpus.</div>
                </div>
              )}
              {messages.map((m, i) => <MessageBubble key={i} message={m} token={user.token} />)}
              {/* role="status" so the wait is announced rather than only
                  drawn — the answer takes seconds (NFA: p95 ≤ 10 s). */}
              {busy && (
                <div role="status" style={{ color: "var(--muted)", fontSize: 13, padding: "8px 0" }}>
                  Suche im Korpus…
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          {/* RAG Parameter Panel */}
          {showParams && isAdmin && (
            <div style={{ borderTop: "1px solid var(--border)", background: "var(--blue-lt)", padding: "14px 24px", flexShrink: 0 }}>
              <div style={{ maxWidth: 760, margin: "0 auto" }}>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "10px 20px", marginBottom: 10 }}>
                  {PARAM_DEFS.map(p => {
                    const raw = params[p.key] ?? "";
                    const num = parseFloat(raw) || 0;
                    return (
                      <div key={p.key}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, fontWeight: 700, color: "var(--navy)", marginBottom: 3 }}>
                          <span>{p.label}</span>
                          <input
                            type="number"
                            value={raw}
                            min={p.min} max={p.max} step={p.step}
                            onChange={e => updateParam(p.key, e.target.value)}
                            style={{ width: 56, textAlign: "right", fontSize: 11, padding: "1px 4px", fontWeight: 700 }}
                          />
                        </div>
                        {p.type === "float" && (
                          <input
                            type="range"
                            min={p.min} max={p.max} step={p.step}
                            value={num}
                            onChange={e => updateParam(p.key, e.target.value)}
                            style={{ width: "100%", accentColor: "var(--blue)", height: 4 }}
                          />
                        )}
                      </div>
                    );
                  })}
                </div>
                {/* LLM-Parameter — optional, leer = OpenAI-Standard */}
                <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, marginTop: 2 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 8 }}>
                    LLM-Parameter · leer = OpenAI-Standard
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "10px 20px", marginBottom: 10 }}>
                    {LLM_PARAM_DEFS.map(p => {
                      const raw = params[p.key] ?? "";
                      return (
                        <div key={p.key}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 11, fontWeight: 700, color: "var(--navy)", marginBottom: 3 }}>
                            <span>{p.label}</span>
                            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                              <input
                                type="number"
                                value={raw}
                                min={p.min} max={p.max} step={p.step}
                                onChange={e => updateParam(p.key, e.target.value)}
                                style={{ width: 76, textAlign: "right", fontSize: 11, padding: "1px 4px", fontWeight: raw ? 700 : 400 }}
                              />
                              {raw !== "" && (
                                <button
                                  onClick={() => updateParam(p.key, "")}
                                  title="Auf OpenAI-Standard zurücksetzen"
                                  style={{ fontSize: 13, lineHeight: "14px", padding: "0 4px", background: "none", border: "1px solid var(--border)", cursor: "pointer", color: "var(--muted)", borderRadius: 3 }}
                                >×</button>
                              )}
                            </div>
                          </div>
                          <div style={{ fontSize: 10, color: "var(--muted)", fontStyle: "italic" }}>
                            {raw === "" ? p.hint : ""}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <button className="primary" style={{ fontSize: 12, padding: "5px 14px" }} onClick={saveParams}>
                    Speichern
                  </button>
                  {paramSaved && <span style={{ fontSize: 12, color: "var(--green)", fontWeight: 600 }}>✓ Gespeichert</span>}
                  {paramError && <span style={{ fontSize: 12, color: "var(--red)", fontWeight: 600 }}>{paramError}</span>}
                </div>
              </div>
            </div>
          )}

          {/* Input */}
          <div style={{
            borderTop: "1px solid var(--border)", padding: "16px 24px",
            background: "var(--card)", flexShrink: 0,
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
                <span id={INPUT_ERROR_ID} role="alert" style={{ fontSize: 12, color: "var(--red)", fontWeight: 600 }}>
                  {inputError}
                </span>
                {/* Counted the same way as the check that rejects it, or the
                    counter would say 998 while the send is refused at 1001. */}
                {questionLength(input.trim()) > COUNTER_VISIBLE_FROM && (
                  <span style={{
                    fontSize: 12, whiteSpace: "nowrap",
                    color: questionLength(input.trim()) > MAX_QUESTION_CHARS ? "var(--red)" : "var(--muted)",
                  }}>
                    {questionLength(input.trim())} / {MAX_QUESTION_CHARS}
                  </span>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
