import { useRef, useState } from "react";
import type { Message, ChunkDebugInfo, StageInfo, LLMCallInfo, DebugInfo, ConfidenceInfo, ConfidenceBand, SuppressionReason } from "../types";
import { api, type Citation, type FeedbackCategory } from "../api/client";

// Keyed by the FeedbackCategory enum in openapi.yaml, one entry per value
// (US-03: the first four apply to a thumbs-up, the remaining five to a
// thumbs-down). `Record<FeedbackCategory, …>` — not two hand-picked arrays —
// is what makes this exhaustive: an enum value added on either side without a
// matching entry here fails the build instead of silently missing from the
// picker, the same guarantee app/routers/feedback.py already has at import
// time for its own category split.
const CATEGORY_META: Record<FeedbackCategory, { label: string; helpful: boolean }> = {
  verstaendlich:       { label: "Verständlich",       helpful: true },
  vollstaendig:        { label: "Vollständig",        helpful: true },
  hilfreich_fuer_code: { label: "Hilfreich für Code",  helpful: true },
  quelle_passt_gut:    { label: "Quelle passt gut",    helpful: true },
  faktisch_falsch:     { label: "Faktisch falsch",     helpful: false },
  unvollstaendig:      { label: "Unvollständig",       helpful: false },
  veraltet:            { label: "Veraltet",            helpful: false },
  unverstaendlich:     { label: "Unverständlich",      helpful: false },
  quelle_stimmt_nicht: { label: "Quelle stimmt nicht", helpful: false },
};
const CATEGORY_ENTRIES = Object.entries(CATEGORY_META) as [FeedbackCategory, { label: string; helpful: boolean }][];
const categoriesFor = (helpful: boolean) => CATEGORY_ENTRIES.filter(([, meta]) => meta.helpful === helpful);

const COMMENT_MAX_LENGTH = 500;


const PARAM_LABELS: Record<string, string> = {
  similarity_threshold:     "Similarity-Schwellwert",
  min_retrieval_confidence: "Min. Retrieval-Konfidenz",
  min_citation_coverage:    "Min. Citation-Coverage",
  confidence_threshold_high:   "Band-Grenze «Hoch»",
  confidence_threshold_medium: "Band-Grenze «Mittel»",
  top_k:                    "Top-K Kandidaten",
  top_n:                    "Top-N ans LLM",
  self_check_band_low:      "Self-Check Zone (unten)",
  self_check_band_high:     "Self-Check Zone (oben)",
  llm_temperature:          "Temperature",
  llm_max_tokens:           "Max Tokens",
  llm_top_p:                "Top-P",
  llm_seed:                 "Seed",
};

// Keyed by the spec enum (see SuppressionReason): a reason added in
// openapi.yaml fails the type check here instead of rendering the raw key in
// the badge.
const suppressLabels: Record<SuppressionReason, string> = {
  retrieval_gate:       "Keine Chunks über Schwellwert",
  retrieval_confidence: "Retrieval-Konfidenz zu tief",
  generation_refused:   "Antwort nicht durch Quellen gedeckt",
  generation_truncated: "Antwort abgebrochen, zurückgehalten",
  citation_coverage:    "Zu wenig Aussagen belegt",
  citation_invalid:     "Antwort nannte eine erfundene Quelle",
  confidence_band:      "Konfidenz insgesamt zu tief",
  self_check:           "Self-Check fand ungedeckte Aussagen",
  configuration_error:  "Suche nicht korrekt konfiguriert",
};

// Keyed by the spec enum (see ConfidenceBand), same guarantee as the map above.
// Only `mittel` carries a badge, and the two nulls are the point of the table
// rather than gaps in it (T-27, US-02):
//   `hoch`    the answer stands on its sources — an unmarked answer is the good
//             case, and a badge on every answer would stop being a signal.
//   `niedrig` never reaches a delivered answer: it suppresses (ADR-008), and
//             what the learner then reads is the suppression badge plus the
//             refinement hint below, not a verdict on prose that was withheld.
// Whether stage 2 (the citation check) ran, derived from the suppression reason
// instead of from `debug.stages`. `debug` is filled for the admin role alone
// (openapi.yaml), so the old lookup answered "did not run" for every learner —
// including an answer whose `citation_coverage` was 1.0, which is how the chip
// came to contradict the composite score printed next to it.
//
// The pipeline order settles it without debug: `check_citations` sits behind a
// successful generation (app/routers/query.py), so every reason from the
// citation stage onwards means it ran, and every earlier one means it did not.
// A delivered answer always passed through it. `Record<SuppressionReason, …>`
// again, so a reason added to the spec has to be classified here rather than
// silently defaulting to one of the two answers.
const CITATION_STAGE_RAN: Record<SuppressionReason, boolean> = {
  retrieval_gate:       false,
  retrieval_confidence: false,
  generation_refused:   false,
  generation_truncated: false,
  configuration_error:  false,
  citation_coverage:    true,
  citation_invalid:     true,
  confidence_band:      true,
  self_check:           true,
};

const BAND_BADGES: Record<ConfidenceBand, { label: string; icon: string; note: string } | null> = {
  hoch: null,
  mittel: {
    label: "Eingeschränkt belegt",
    icon: "◐",
    note: "Die Quellen decken diese Antwort nur teilweise. Prüfe die angegebenen Stellen, bevor du dich darauf verlässt.",
  },
  niedrig: null,
};

function pct(v: number) { return `${Math.round(v * 100)}%`; }

// ── Chunk bar ──────────────────────────────────────────────────────────────
function ChunkBar({ chunk, threshold }: { chunk: ChunkDebugInfo; threshold: number }) {
  const [open, setOpen] = useState(false);
  const scorePct = Math.max(0, Math.min(100, Math.round(chunk.score * 100)));
  const thPct    = Math.round(threshold * 100);
  const color    = chunk.above_threshold ? "var(--green)" : "var(--red)";
  const parts    = [chunk.filename, chunk.page ? `S.${chunk.page}` : null, chunk.heading ? `— ${chunk.heading}` : null].filter(Boolean).join(" ");

  return (
    <div style={{ marginBottom: 5 }}>
      <div
        style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", userSelect: "none" }}
        onClick={() => setOpen(v => !v)}
      >
        <span style={{ width: 30, textAlign: "right", fontSize: 10, fontWeight: 700, color, flexShrink: 0 }}>
          {scorePct}%
        </span>
        <div style={{ flex: 1, position: "relative", height: 5, background: "var(--border)", borderRadius: 3 }}>
          <div style={{ width: `${scorePct}%`, height: "100%", background: color, borderRadius: 3 }} />
          {/* threshold marker */}
          <div style={{ position: "absolute", top: -2, left: `${thPct}%`, width: 2, height: 9, background: "var(--navy)", borderRadius: 1 }} />
        </div>
        <span style={{ fontSize: 10, color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 190 }}>
          {parts}
        </span>
        {chunk.in_top_n ? (
          <span style={{ flexShrink: 0, fontSize: 9, padding: "1px 5px", borderRadius: 8, background: "var(--blue)", color: "#fff", fontWeight: 700 }}>
            LLM
          </span>
        ) : (
          <span style={{ flexShrink: 0, fontSize: 9, color: "var(--border)", fontWeight: 600 }}>#{chunk.dense_rank}</span>
        )}
        <span style={{ fontSize: 9, color: "var(--muted)", flexShrink: 0 }}>{open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <pre style={{
          margin: "4px 0 0 36px", padding: "7px 10px",
          background: chunk.above_threshold ? "var(--green-lt)" : "var(--red-lt)",
          borderRadius: 6, fontSize: 10, lineHeight: 1.5,
          whiteSpace: "pre-wrap", wordBreak: "break-word",
          maxHeight: 180, overflowY: "auto", color: "var(--navy)",
        }}>
          {chunk.content}
        </pre>
      )}
    </div>
  );
}

// ── Pipeline step ──────────────────────────────────────────────────────────
function PipelineStep({
  num, stage, isLast,
}: { num: number; stage: StageInfo; isLast: boolean }) {
  const passed  = stage.ran && stage.passed;
  const failed  = stage.ran && !stage.passed;
  const skipped = !stage.ran;

  const dotColor   = skipped ? "var(--muted)" : passed ? "var(--green)" : "var(--red)";
  const labelColor = skipped ? "var(--muted)" : passed ? "var(--navy)"  : "var(--red)";
  const resultText = skipped ? "—" : passed ? "✓ OK" : "✗ STOPP";
  const resultColor = skipped ? "var(--muted)" : passed ? "var(--green)" : "var(--red)";

  // Value display: count (threshold≥1) stays integer, fraction → %, string as-is
  const valStr = stage.value === null || stage.value === undefined ? null
    : typeof stage.value === "number"
      ? (stage.threshold != null && stage.threshold >= 1 ? String(stage.value) : pct(stage.value))
      : String(stage.value);

  const thStr = stage.threshold === null || stage.threshold === undefined ? null
    : stage.threshold >= 1 ? `Min: ${stage.threshold}` : `Min: ${pct(stage.threshold)}`;

  return (
    <div style={{ display: "flex", gap: 0 }}>
      {/* Left: dot + connector line */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0, width: 22 }}>
        <div style={{
          width: 18, height: 18, borderRadius: "50%", flexShrink: 0,
          background: dotColor, color: "#fff",
          fontSize: 9, fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: `0 0 0 2px ${skipped ? "var(--border)" : passed ? "var(--green-lt)" : "var(--red-lt)"}`,
        }}>
          {num}
        </div>
        {!isLast && (
          <div style={{ flex: 1, width: 2, background: "var(--border)", minHeight: 10 }} />
        )}
      </div>

      {/* Right: content */}
      <div style={{ flex: 1, paddingLeft: 10, paddingBottom: isLast ? 0 : 10 }}>
        {/* Row: name + value + result */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: labelColor }}>{stage.name}</span>
          {valStr && (
            <span style={{ fontSize: 11, fontWeight: 800, color: failed ? "var(--red)" : "var(--navy)" }}>
              {valStr}
            </span>
          )}
          {thStr && (
            <span style={{ fontSize: 10, color: "var(--muted)" }}>{thStr}</span>
          )}
          <span style={{ fontSize: 10, fontWeight: 700, color: resultColor, marginLeft: "auto" }}>
            {resultText}
          </span>
        </div>
        {/* Detail line */}
        <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 2, fontFamily: "monospace", lineHeight: 1.5 }}>
          {stage.detail}
        </div>
      </div>
    </div>
  );
}

// ── LLM call node ──────────────────────────────────────────────────────────
function LLMCallNode({ call, isLast }: { call: LLMCallInfo; isLast: boolean }) {
  const [showPrompt,   setShowPrompt]   = useState(false);
  const [showResponse, setShowResponse] = useState(false);
  const isSelfCheck = call.step === "self_check";

  return (
    <div style={{ display: "flex", gap: 0 }}>
      {/* Left: dot + connector */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0, width: 22 }}>
        <div style={{
          width: 18, height: 18, borderRadius: 4, flexShrink: 0,
          background: isSelfCheck ? "var(--amber)" : "var(--blue)",
          color: "#fff", fontSize: 9, display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          🤖
        </div>
        {!isLast && <div style={{ flex: 1, width: 2, background: "var(--border)", minHeight: 10 }} />}
      </div>

      {/* Right: content */}
      <div style={{ flex: 1, paddingLeft: 10, paddingBottom: isLast ? 0 : 10 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--navy)", marginBottom: 5 }}>
          LLM · {call.label}
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button
            className="secondary"
            style={{ fontSize: 10, padding: "2px 8px" }}
            onClick={() => setShowPrompt(v => !v)}
          >
            {showPrompt ? "Prompt ▲" : "Prompt ▼"}
          </button>
          <button
            className="secondary"
            style={{ fontSize: 10, padding: "2px 8px" }}
            onClick={() => setShowResponse(v => !v)}
          >
            {showResponse ? "Antwort ▲" : "Antwort ▼"}
          </button>
        </div>
        {showPrompt && (
          <pre style={{
            marginTop: 6, padding: "8px 10px", borderRadius: 6,
            background: "var(--blue-lt)", fontSize: 10, lineHeight: 1.5,
            whiteSpace: "pre-wrap", wordBreak: "break-word",
            maxHeight: 260, overflowY: "auto", color: "var(--navy)",
          }}>
            {call.prompt}
          </pre>
        )}
        {showResponse && (
          <pre style={{
            marginTop: 6, padding: "8px 10px", borderRadius: 6,
            background: isSelfCheck ? "var(--amber-lt)" : "var(--green-lt)",
            fontSize: 10, lineHeight: 1.5,
            whiteSpace: "pre-wrap", wordBreak: "break-word",
            maxHeight: 260, overflowY: "auto", color: "var(--navy)",
          }}>
            {call.response}
          </pre>
        )}
      </div>
    </div>
  );
}

// ── Debug panel ────────────────────────────────────────────────────────────
function DebugPanel({ debug, confidence }: { debug: DebugInfo; confidence: ConfidenceInfo }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>

      {/* ── Chunks ── */}
      <div style={{
        background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8,
        padding: "10px 12px",
      }}>
        <div style={{ display: "flex", gap: 12, fontSize: 10, color: "var(--muted)", fontWeight: 600, marginBottom: 8, flexWrap: "wrap" }}>
          <span>Chunks</span>
          <span>Dense: <strong style={{ color: "var(--navy)" }}>{debug.total_dense_retrieved}</strong> abgerufen</span>
          <span>Schwellwert: <strong style={{ color: "var(--navy)" }}>{pct(debug.similarity_threshold)}</strong></span>
          <span>Sparse: <strong style={{ color: "var(--navy)" }}>{debug.sparse_count}</strong> Treffer</span>
          <span>Top-N ans LLM: <strong style={{ color: "var(--blue)" }}>{debug.top_n_used}</strong></span>
        </div>
        {/* Legend */}
        <div style={{ display: "flex", gap: 10, fontSize: 9, color: "var(--muted)", marginBottom: 7 }}>
          <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 2, background: "var(--green)", marginRight: 3 }} />über Schwellwert</span>
          <span><span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 2, background: "var(--red)", marginRight: 3 }} />darunter</span>
          <span><span style={{ display: "inline-block", padding: "0 4px", borderRadius: 6, background: "var(--blue)", color: "#fff", fontSize: 8, fontWeight: 700, marginRight: 3 }}>LLM</span>ans LLM gesendet</span>
          <span>▌ = Schwellwert</span>
        </div>
        {debug.chunks.map((c, i) => (
          <ChunkBar key={i} chunk={c} threshold={debug.similarity_threshold} />
        ))}
      </div>

      {/* ── Pipeline ── */}
      <div style={{
        background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8,
        padding: "10px 12px",
      }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "var(--muted)", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Pipeline
        </div>

        {/* Pipeline stages interleaved with the LLM calls each one triggers.
            Anchored on the stage id, never on its position: the backend decides
            how many stages it ships, and fixed indices went wrong every time
            that number changed. */}
        {debug.stages.map((s, i) => {
          const groundingCall = s.id === "retrieval_confidence" ? debug.llm_calls.find(c => c.step === "grounding") : null;
          const selfCheckCall = s.id === "self_check" ? debug.llm_calls.find(c => c.step === "self_check") : null;
          return (
            <div key={s.id}>
              <PipelineStep num={i + 1} stage={s} isLast={false} />
              {groundingCall && <LLMCallNode call={groundingCall} isLast={false} />}
              {/* The composite breakdown belongs to the stage that decides on it,
                  so it hangs under confidence_band rather than floating between
                  stages with a number of its own. Every value here comes from the
                  response — the invented 0.50/0.75 fallbacks this used to carry
                  showed a zone the backend was not using. */}
              {s.id === "confidence_band" && (
                <div style={{ display: "flex", gap: 0 }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0, width: 22 }}>
                    <div style={{ flex: 1, width: 2, background: "var(--border)", minHeight: 10 }} />
                  </div>
                  <div style={{ flex: 1, paddingLeft: 10, paddingBottom: 10 }}>
                    <div style={{ fontSize: 10, color: "var(--muted)", fontFamily: "monospace", lineHeight: 1.5 }}>
                      {debug.formula_breakdown}
                    </div>
                    <div style={{ display: "flex", gap: 6, marginTop: 5, flexWrap: "wrap" }}>
                      {[
                        { label: "Top-Score",  val: debug.retrieval_detail.top_score },
                        { label: "Mean-Score", val: debug.retrieval_detail.mean_score },
                        { label: "Density",    val: debug.retrieval_detail.evidence_density },
                        { label: "Citation",   val: confidence.citation_coverage },
                      ].map(item => (
                        <div key={item.label} style={{ padding: "2px 8px", borderRadius: 6, background: "var(--blue-lt)", fontSize: 10, display: "flex", gap: 4, alignItems: "baseline" }}>
                          <span style={{ fontWeight: 700, color: "var(--navy)" }}>{pct(item.val)}</span>
                          <span style={{ color: "var(--muted)" }}>{item.label}</span>
                        </div>
                      ))}
                      <span style={{ padding: "2px 8px", borderRadius: 6, background: "var(--border)", fontSize: 10, fontWeight: 700, color: "var(--navy)" }}>
                        Band: {confidence.band}
                      </span>
                    </div>
                  </div>
                </div>
              )}
              {selfCheckCall && <LLMCallNode call={selfCheckCall} isLast={false} />}
            </div>
          );
        })}

        {/* Active params for this query */}
        <div style={{ marginTop: 12, paddingTop: 10, borderTop: "1px solid var(--border)" }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 6 }}>
            Aktive Parameter dieser Anfrage
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
            {Object.entries(debug.params_used).map(([k, v]) => {
              if (v === null) return null;
              const display = typeof v === "number" && v > 0 && v < 1 ? pct(v) : String(v);
              return (
                <div key={k} style={{
                  padding: "2px 8px", borderRadius: 6, background: "var(--border)",
                  fontSize: 10, display: "flex", gap: 5,
                }}>
                  <span style={{ color: "var(--muted)" }}>{PARAM_LABELS[k] ?? k}</span>
                  <span style={{ fontWeight: 700, color: "var(--navy)" }}>{display}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Source reference ───────────────────────────────────────────────────────

// The API caps an excerpt at 400 characters (EXCERPT_MAX_CHARS in query.py),
// which is several lines in this column. Clamped until asked for, so a list of
// five sources stays scannable.
const EXCERPT_CLAMP_LINES = 2;

/**
 * One clickable source reference (US-01, T-20).
 *
 * Clicking unfolds the full excerpt. That is deliberately a real behaviour and
 * not a placeholder: T-21 (#28) hangs the document viewer off this same
 * control, and until the backend can deliver a document's content there is
 * nothing honest for a click to open. What T-20 owes is the reference the user
 * can operate; what T-21 adds is where it leads.
 */
function CitationEntry({ citation }: { citation: Citation }) {
  const [expanded, setExpanded] = useState(false);
  const label = `[${citation.index}] ${citation.filename}${citation.page ? ` · S. ${citation.page}` : ""}`;

  return (
    <button
      onClick={() => setExpanded(v => !v)}
      aria-expanded={expanded}
      aria-label={label}
      style={{
        // fontFamily, not the `font` shorthand: `font: inherit` would reset
        // font-size along with it and, applied after fontSize in key order,
        // silently undo the 12px the label below relies on.
        background: "var(--blue-lt)", border: "none", borderRadius: 8,
        padding: "8px 12px", fontSize: 12, textAlign: "left", width: "100%",
        cursor: "pointer", display: "block", fontFamily: "inherit",
      }}
    >
      <div style={{ fontWeight: 700, color: "var(--navy)", marginBottom: 4 }}>
        {label} <span style={{ fontWeight: 400, color: "var(--muted)" }}>{expanded ? "▲" : "▼"}</span>
      </div>
      <div style={{
        color: "var(--muted)", lineHeight: 1.45, fontSize: 12,
        ...(expanded ? {} : {
          display: "-webkit-box",
          WebkitLineClamp: EXCERPT_CLAMP_LINES,
          WebkitBoxOrient: "vertical" as const,
          overflow: "hidden",
        }),
      }}>
        {citation.excerpt}
      </div>
    </button>
  );
}

// ── Main component ─────────────────────────────────────────────────────────
interface Props { message: Message; token: string; }

export default function MessageBubble({ message: m, token }: Props) {
  const [feedback, setFeedback] = useState<boolean | null>(null);
  // Thumb the picker is currently open for; null once a rating is stored or
  // before either thumb has been clicked.
  const [pendingThumb, setPendingThumb] = useState<boolean | null>(null);
  const [category, setCategory] = useState<FeedbackCategory | null>(null);
  const [comment, setComment] = useState("");
  const [feedbackError, setFeedbackError] = useState("");
  // A ref, not state: nothing renders from it, and a ref is already set when
  // the next click handler runs. State would only hold if React flushed the
  // update before that click — true for discrete events today, but an implicit
  // dependency for a guard whose whole job is to be unconditional.
  const submitting = useRef(false);
  const [showSources, setShowSources] = useState(false);

  const selectThumb = (helpful: boolean) => {
    if (feedback !== null || submitting.current) return;
    setPendingThumb(helpful);
    setCategory(null);
    setFeedbackError("");
  };

  const cancelFeedback = () => {
    if (submitting.current) return;
    setPendingThumb(null);
    setCategory(null);
    setComment("");
    setFeedbackError("");
  };

  const submitFeedback = async () => {
    // `feedback` only guards a stored rating — it is set after the await, so
    // during the request it is still null. Without `submitting` a double click
    // on "Absenden" posts twice for the same answer_id; from T-30 on that is
    // two rows with contradicting `helpful`, and the US-03 evaluation cannot
    // tell which one the user meant.
    if (!m.answer_id || pendingThumb === null || category === null || feedback !== null || submitting.current) return;
    submitting.current = true;
    setFeedbackError("");
    try {
      await api.submitFeedback(m.answer_id, pendingThumb, category, comment.trim() || null, token);
      // Marked only once it is actually stored — a rating the request could
      // still reject (404/400) must not latch the button as saved.
      setFeedback(pendingThumb);
      setPendingThumb(null);
      setCategory(null);
      setComment("");
    } catch {
      setFeedbackError("Bewertung konnte nicht gespeichert werden.");
    } finally {
      submitting.current = false;
    }
  };

  if (m.role === "user") {
    return (
      <div style={{ alignSelf: "flex-end", maxWidth: "75%" }}>
        <div style={{
          background: "var(--navy)", color: "#fff", borderRadius: "12px 12px 2px 12px",
          padding: "10px 14px", fontSize: 14, lineHeight: 1.5,
        }}>
          {m.content}
        </div>
      </div>
    );
  }

  const d = m.debug;
  // Only for an answer that was actually delivered: a suppressed one carries no
  // prose to qualify, and its own badge already says why it is missing.
  const band = !m.suppressed && m.confidence ? BAND_BADGES[m.confidence.band] : null;
  // One block, two roles, deliberately told apart (US-02: the states have to be
  // distinguishable). Amber warns about prose the learner did get; the quiet one
  // helps with a question whose answer was withheld, where the ⚠ badge above
  // already carries the warning and a second one would only shout. The label
  // draws the same line for a screen reader, which cannot see the colour.
  const note = band
    ? {
        label: "Hinweis zur Belegung der Antwort",
        body: band.note,
        background: "var(--amber-lt)",
        border: "var(--amber)",
      }
    : m.suppressed && m.refinement_hint
      ? {
          label: "Tipp zur Präzisierung der Frage",
          body: <><strong>Tipp: </strong>{m.refinement_hint}</>,
          background: "var(--card)",
          border: "var(--border)",
        }
      : null;

  return (
    <div style={{ alignSelf: "flex-start", maxWidth: "90%", display: "flex", flexDirection: "column", gap: 8 }}>

      {/* Answer */}
      <div style={{
        background: "var(--card)", border: "1px solid var(--border)",
        borderRadius: "2px 12px 12px 12px",
        padding: "10px 14px", fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-wrap",
      }}>
        {m.content}
      </div>

      {/* Metric bar — thresholds from actual query params, not hardcoded.
          Not gated on m.confidence: configuration_error returns confidence null,
          and its badge is the only thing telling the user why nothing came back. */}
      {(m.confidence || m.suppression_reason) && (
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          {/* First in the row on purpose: this is the one chip US-02 asks a
              learner to read, the percentages behind it are the detail. */}
          {band && (
            <span style={{
              fontSize: 11, padding: "2px 9px", borderRadius: 20, fontWeight: 700,
              background: "var(--amber-lt)", color: "var(--amber)",
            }}>
              <span aria-hidden="true">{band.icon} </span>{band.label}
            </span>
          )}
          {m.confidence && (<>
          <span style={{
            background: "var(--blue-lt)", color: "var(--navy)",
            borderRadius: 20, padding: "2px 10px", fontSize: 11, fontWeight: 700,
          }}>
            Composite: {pct(m.confidence.score)}
          </span>
          {(() => {
            // Coloured only against a threshold we actually have. params_used is
            // filled for admins alone, and the invented fallback (0.55, while the
            // backend default is 0.40) painted every learner's answer red whose
            // score sat between the two — for a stage that had passed it.
            // `confidence.band` is the value US-02 wants shown here, but the
            // learner-facing badge for it is T-27; today the band appears only
            // in the admin debug panel, so this block stays a raw comparison
            // and simply declines to colour what it cannot judge.
            const minRet = d?.params_used?.min_retrieval_confidence ?? null;
            const retFail = minRet !== null && m.confidence!.retrieval_score < minRet;
            const minCit = d?.params_used?.min_citation_coverage ?? null;
            // Only meaningful once stage 2 ran. Below the retrieval gates the
            // coverage is 0.0 for "not measured", and painting that red would
            // report a failure of a check that never happened (ADR-008).
            const citRan = m.suppression_reason
              ? CITATION_STAGE_RAN[m.suppression_reason]
              : true;
            const citFail = citRan && minCit !== null && m.confidence!.citation_coverage < minCit;
            return (
              <>
                <span style={{
                  fontSize: 11, padding: "2px 8px", borderRadius: 20, fontWeight: 600,
                  background: retFail ? "var(--red-lt)" : "var(--blue-lt)",
                  color: retFail ? "var(--red)" : "var(--navy)",
                }}>
                  Retrieval: {pct(m.confidence!.retrieval_score)}
                </span>
                <span style={{
                  fontSize: 11, padding: "2px 8px", borderRadius: 20, fontWeight: 600,
                  background: citFail ? "var(--red-lt)" : citRan ? "var(--blue-lt)" : "var(--bg)",
                  color: citFail ? "var(--red)" : citRan ? "var(--navy)" : "var(--muted)",
                }}>
                  {citRan ? `Citation: ${pct(m.confidence!.citation_coverage)}` : "Citation: nicht gelaufen"}
                </span>
              </>
            );
          })()}
          </>)}
          {m.suppression_reason && (
            <span style={{
              fontSize: 11, padding: "2px 8px", borderRadius: 20, fontWeight: 600,
              background: "var(--amber-lt)", color: "var(--amber)",
            }}>
              ⚠ {suppressLabels[m.suppression_reason] ?? m.suppression_reason}
            </span>
          )}
          {m.citations && m.citations.length > 0 && (
            <button className="secondary" style={{ fontSize: 11, padding: "2px 9px" }}
              onClick={() => setShowSources(v => !v)}>
              {showSources ? `Quellen ▲` : `${m.citations.length} Quelle${m.citations.length > 1 ? "n" : ""} ▼`}
            </button>
          )}
        </div>
      )}

      {/* The badge's explanatory text (US-02: colour + icon + hint) and, after a
          suppression, the backend's advice on what to try next — see `note`
          above for why the two look different. `role="note"` rather than
          "alert": the text arrives with the answer and must not interrupt a
          screen reader mid-sentence. */}
      {note && (
        <div role="note" aria-label={note.label} style={{
          fontSize: 12, lineHeight: 1.5, color: "var(--text)",
          background: note.background, border: `1px solid ${note.border}`,
          borderRadius: 8, padding: "8px 12px",
        }}>
          {note.body}
        </div>
      )}

      {/* Sources */}
      {showSources && m.citations && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {m.citations.map(c => <CitationEntry key={c.chunk_id} citation={c} />)}
        </div>
      )}

      {/* Always-visible debug panel */}
      {d && m.confidence && (
        <DebugPanel debug={d} confidence={m.confidence} />
      )}

      {/* Feedback */}
      {m.answer_id && !m.suppressed && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {feedback !== null ? (
            <span style={{ fontSize: 11, color: "var(--green)", fontWeight: 600 }}>
              ✓ Danke für dein Feedback!
            </span>
          ) : (
            <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
              <span style={{ fontSize: 11, color: "var(--muted)" }}>Hilfreich?</span>
              {([true, false] as const).map(helpful => (
                <button key={String(helpful)} onClick={() => selectThumb(helpful)}
                  aria-label={helpful ? "Hilfreich" : "Nicht hilfreich"}
                  style={{
                    background: pendingThumb === helpful ? "var(--blue)" : "transparent",
                    color: pendingThumb === helpful ? "#fff" : "var(--muted)",
                    border: "1px solid var(--border)", borderRadius: 4,
                    padding: "1px 6px", fontSize: 11,
                  }}>
                  {helpful ? "👍" : "👎"}
                </button>
              ))}
            </div>
          )}

          {pendingThumb !== null && (
            <div style={{
              background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8,
              padding: "8px 10px", display: "flex", flexDirection: "column", gap: 6,
            }}>
              <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
                {categoriesFor(pendingThumb).map(([value, meta]) => (
                  <button key={value} onClick={() => setCategory(value)}
                    className={category === value ? "primary" : "secondary"}
                    style={{ fontSize: 11, padding: "2px 9px" }}>
                    {meta.label}
                  </button>
                ))}
              </div>
              <textarea
                value={comment}
                onChange={e => setComment(e.target.value.slice(0, COMMENT_MAX_LENGTH))}
                maxLength={COMMENT_MAX_LENGTH}
                placeholder="Optional: Anmerkung ergänzen…"
                rows={2}
                style={{ resize: "none", fontSize: 12 }}
              />
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <button className="primary" onClick={submitFeedback} disabled={category === null}
                  style={{ fontSize: 11, padding: "2px 10px" }}>
                  Absenden
                </button>
                <button className="secondary" onClick={cancelFeedback}
                  style={{ fontSize: 11, padding: "2px 10px" }}>
                  Abbrechen
                </button>
                <span style={{ fontSize: 10, color: "var(--muted)", marginLeft: "auto" }}>
                  {comment.length}/{COMMENT_MAX_LENGTH}
                </span>
                {feedbackError && (
                  <span style={{ fontSize: 11, color: "var(--red)" }}>{feedbackError}</span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
