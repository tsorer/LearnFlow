import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { AuthUser, Message } from "../types";
import { api, ApiError, type ConfigMap } from "../api/client";
import { getRoleFlags } from "../roles";
import Layout from "./Layout";
import Upload from "./Upload";
import MessageBubble from "./MessageBubble";
import {
  ANSWER_PARAM_DEFS,
  READ_ONLY_PARAM_DEFS,
  RETRIEVAL_PARAM_DEFS,
  type ConfigKey,
  type ParamDef,
} from "../params";

const GROUP_LABEL_STYLE = {
  fontSize: "var(--text-3xs)",
  fontWeight: "var(--font-bold)",
  color: "var(--text-muted)",
  textTransform: "uppercase",
  letterSpacing: ".06em",
  marginBottom: 8,
} as const;

/** One labelled block of sliders. Declared outside ChatView so React keeps the
 *  inputs mounted across re-renders — a component defined inside the parent is
 *  a new type on every render and would drop focus after each keystroke. */
function ParamGroup({
  title,
  defs,
  params,
  onChange,
}: {
  title: string;
  defs: readonly ParamDef[];
  // `ConfigMap`, nicht `Record<string, string>` (T-46): der Zustand oben ist es
  // schon, und nur so sagt der Typ die Nullability richtig. `getConfig` fängt
  // seinen Fehler ab und lässt `params` als `{}` stehen, und in `ConfigMap`
  // ist jeder Schlüssel optional — `params[p.key]` ist zur Laufzeit also
  // wirklich `undefined`. Unter `Record<string, string>` typisierte der
  // Compiler es als `string`, womit das `?? ""` unten wie toter Defensivcode
  // aussieht: wer es entfernt, rendert jeden Regler mit `value={undefined}`
  // und macht die Inputs uncontrolled.
  params: ConfigMap;
  onChange: (key: ConfigKey, value: string) => void;
}) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={GROUP_LABEL_STYLE}>{title}</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "10px 20px" }}>
        {defs.map(p => {
          const raw = params[p.key] ?? "";
          return (
            <div key={p.key}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-2xs)", fontWeight: "var(--font-bold)", color: "var(--text-primary)", marginBottom: 3 }}>
                <label htmlFor={`param-${p.key}`}>{p.label}</label>
                <input
                  id={`param-${p.key}`}
                  type="number"
                  value={raw}
                  min={p.min} max={p.max} step={p.step}
                  onChange={e => onChange(p.key, e.target.value)}
                  style={{ width: 56, textAlign: "right", fontSize: "var(--text-2xs)", padding: "1px 4px", fontWeight: "var(--font-bold)" }}
                />
              </div>
              {p.type === "float" && (
                <input
                  type="range"
                  aria-label={`${p.label} (Schieberegler)`}
                  min={p.min} max={p.max} step={p.step}
                  value={parseFloat(raw) || 0}
                  onChange={e => onChange(p.key, e.target.value)}
                  style={{ width: "100%", accentColor: "var(--coral)", height: 4 }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

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

export default function ChatView({ user, onLogout, messages, setMessages, sessionId, setSessionId, busy, setBusy }: Props) {
  const navigate = useNavigate();
  const [input, setInput] = useState("");
  const [inputError, setInputError] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [showParams, setShowParams] = useState(false);
  const [params, setParams] = useState<ConfigMap>({});
  const [paramSaved, setParamSaved] = useState(false);
  const [paramError, setParamError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const { canUpload, canReview, canViewFeedback, isAdmin } = getRoleFlags(user);

  useEffect(() => {
    if (!isAdmin) return;
    api.getConfig(user.token).then(setParams).catch(() => {});
  }, []);

  // `ConfigKey`, nicht `string` (T-46): ein Schlüssel, den die config-Tabelle
  // nicht kennt, ist damit ein tsc-Fehler statt einer 422 beim Speichern.
  const updateParam = useCallback((key: ConfigKey, val: string) => {
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
    } catch (err) {
      // The backend names the offending key and the rule it broke — a shape
      // violation from `_validate_shape`, or the message of the deferred band
      // trigger ("confidence_threshold_medium (0.8) darf nicht über
      // confidence_threshold_high (0.75) liegen"), which `errorMessage` in the
      // client lifts out of `detail`. Swallowing it left the admin with a panel
      // of ten fields, an all-or-nothing PUT, and nothing to say which one
      // broke — the failure this panel exists to end.
      //
      // `HTTP <status>` is what `errorMessage` returns when it found no usable
      // `detail`, so it is the one message worth replacing: a bare status code
      // helps an admin less than the sentence below.
      const detail =
        err instanceof ApiError && err.message !== `HTTP ${err.status}` ? err.message : null;
      setParamError(detail ?? "Parameter konnten nicht gespeichert werden.");
    }
  };

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
    <Layout
      user={user}
      onLogout={onLogout}
      ctaSlot={!showUpload && (
        // Disabled while an answer is on its way, like the textarea and the
        // send button: `send` holds `sessionId` and `messages` across the
        // await, so a reset in that window is undone when the response
        // lands — the old session id returns and the answer is appended to
        // a transcript that no longer holds its question.
        <button className="sidebar-cta" onClick={newChat} disabled={busy}>Neuer Chat</button>
      )}
      navItems={<>
        {canUpload && (
          <button className={`nav-item${showUpload ? " active" : ""}`} onClick={() => setShowUpload(v => !v)}>
            {showUpload ? "Chat" : "Dokumente"}
          </button>
        )}
        <button className="nav-item" onClick={() => navigate("/quiz")}>Quiz starten</button>
        {canReview && (
          <button className="nav-item" onClick={() => navigate("/quiz-review")}>Quiz-Review</button>
        )}
        {canViewFeedback && (
          <button className="nav-item" onClick={() => navigate("/feedback")}>Feedback</button>
        )}
        {/* Hidden in the document view, because it acts on nothing there: the
            parameter panel lives in the chat branch, so from here the button
            only flipped an arrow. */}
        {isAdmin && !showUpload && (
          <button className={`nav-item${showParams ? " active" : ""}`} onClick={() => setShowParams(v => !v)}>
            {showParams ? "⚙ Parameter ▲" : "⚙ Parameter ▼"}
          </button>
        )}
      </>}
    >
      {showUpload && canUpload ? (
        <Upload user={user} onClose={() => setShowUpload(false)} />
      ) : (
        <>
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

          {/* RAG Parameter Panel */}
          {showParams && isAdmin && (
            <div style={{ borderTop: "1px solid var(--border)", background: "var(--violet-tint)", padding: "14px var(--space-6)", flexShrink: 0 }}>
              <div style={{ maxWidth: 760, margin: "0 auto" }}>
                <ParamGroup
                  title="Retrieval · welche Quellen in den Kontext kommen"
                  defs={RETRIEVAL_PARAM_DEFS}
                  params={params}
                  onChange={updateParam}
                />
                <ParamGroup
                  title="Antwort · wann der Antwort getraut wird"
                  defs={ANSWER_PARAM_DEFS}
                  params={params}
                  onChange={updateParam}
                />

                {/* Nur zur Ansicht. Eine Änderung wirkt erst nach vollständiger
                    Re-Indexierung des Korpus, deshalb weist PUT sie zurück (T-42). */}
                <div style={{ borderTop: "1px solid var(--border)", paddingTop: 10, marginTop: 2, marginBottom: 12 }}>
                  <div style={GROUP_LABEL_STYLE}>Indexierung · erfordert Re-Indexierung, hier nicht änderbar</div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "10px 20px" }}>
                    {READ_ONLY_PARAM_DEFS.map(p => (
                      <div key={p.key} style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-2xs)", fontWeight: "var(--font-bold)", color: "var(--text-muted)" }}>
                        <span>{p.label}</span>
                        <span>{params[p.key] ?? "—"}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <button className="primary" style={{ fontSize: "var(--text-2xs)", padding: "5px 14px" }} onClick={saveParams}>
                    Speichern
                  </button>
                  {paramSaved && <span style={{ fontSize: "var(--text-2xs)", color: "var(--olive)", fontWeight: "var(--font-semibold)" }}>✓ Gespeichert</span>}
                  {paramError && <span style={{ fontSize: "var(--text-2xs)", color: "var(--red)", fontWeight: "var(--font-semibold)" }}>{paramError}</span>}
                </div>
              </div>
            </div>
          )}

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
        </>
      )}
    </Layout>
  );
}
