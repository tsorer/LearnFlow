import { useRef, useState, type CSSProperties } from "react";
import type { Message, ChunkDebugInfo, StageInfo, LLMCallInfo, DebugInfo, ConfidenceInfo, ConfidenceBand, SuppressionReason } from "../types";
import { api, type Citation, type FeedbackCategory } from "../api/client";
import { PARAM_LABELS } from "../params";
import DocumentViewer from "./DocumentViewer";

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
// Whether stage 2 (the citation check) ran. `debug.stages` records it directly
// (`ran = citation is not None` in app/routers/query.py) and is in reach now
// that the chip is admin-only — but that lookup matches a stage id as a plain
// string and answers "did not run" when it finds nothing, so a rename in the
// backend would go unnoticed. The suppression reason carries the same fact and
// is type-checked across the boundary: `check_citations` sits behind a
// successful generation, so every reason from the citation stage onwards means
// it ran, every earlier one means it did not, and a delivered answer always
// passed through it. `Record<SuppressionReason, …>`, so a reason added to the
// spec has to be classified here instead of defaulting to one of the answers.
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

// `dense_rank` / `sparse_rank` carry 0 for "this search did not return the
// chunk" — RANK_ABSENT in app/services/retrieval.py, a sentinel that cannot
// collide because real ranks start at 1. It must not render as "#0", which
// reads like a rank rather than like an absence (T-54).
const RANK_ABSENT = 0;
const rankLabel = (rank: number) => (rank === RANK_ABSENT ? "—" : String(rank));

// One source of truth for the column widths, because the header row below and
// every chunk row have to line up. Two elastic columns share what the fixed
// ones leave: the bar grows from 90px, the source twice as fast from 160px, and
// the source wraps instead of truncating — the filename is what an admin reads
// to find the chunk again, so it is the one thing that must not be cut off.
const COL_SCORE: CSSProperties = { width: 30, textAlign: "right", fontSize: 10, fontWeight: 700, flexShrink: 0 };
const COL_BAR: CSSProperties   = { flex: "1 1 90px" };
const COL_RANK: CSSProperties  = { width: 20, textAlign: "center", fontSize: 9, flexShrink: 0 };
const COL_RRF: CSSProperties   = { width: 40, textAlign: "right", fontSize: 9, flexShrink: 0 };
const COL_SRC: CSSProperties   = { flex: "2 1 160px", minWidth: 0, fontSize: 10, lineHeight: 1.35, overflowWrap: "anywhere" };
const COL_BADGE: CSSProperties = { width: 28, textAlign: "center", flexShrink: 0 };
const COL_CARET: CSSProperties = { width: 8, fontSize: 9, flexShrink: 0, color: "var(--muted)" };

const CHUNK_ROW: CSSProperties = { display: "flex", alignItems: "center", gap: 6 };

const COLUMN_LABEL: CSSProperties = {
  fontSize: 8, fontWeight: 700, letterSpacing: "0.05em",
  textTransform: "uppercase", color: "var(--muted)",
};

/**
 * Header for the chunk list — names the three columns T-54 added.
 *
 * `D` and `S` are single letters in a 20px column, so each carries the spelled
 * out name for a screen reader as well: this is a flex layout, not a table, and
 * nothing associates a cell with its heading.
 */
function ChunkColumns() {
  return (
    <div style={{ ...CHUNK_ROW, paddingBottom: 4, marginBottom: 6, borderBottom: "1px solid var(--border)" }}>
      <span style={{ ...COL_SCORE, ...COLUMN_LABEL }}>Cos</span>
      <span style={COL_BAR} />
      <span style={{ ...COL_RANK, ...COLUMN_LABEL }} title="Rang in der Vektorsuche">
        <span aria-hidden="true">D</span>
        <span className="sr-only">Rang in der Vektorsuche</span>
      </span>
      <span style={{ ...COL_RANK, ...COLUMN_LABEL }} title="Rang in der Volltextsuche">
        <span aria-hidden="true">S</span>
        <span className="sr-only">Rang in der Volltextsuche</span>
      </span>
      <span style={{ ...COL_RRF, ...COLUMN_LABEL }} title="Sortierschlüssel: Summe von 1/(k + Rang) über beide Suchen">
        RRF ↓
      </span>
      <span style={{ ...COL_SRC, ...COLUMN_LABEL }}>Quelle</span>
      <span style={COL_BADGE} />
      <span style={COL_CARET} />
    </div>
  );
}

/**
 * One rank cell: the number, or a dash where that search did not find the chunk.
 *
 * The dash used to be drawn in `--border`, inherited from the old `#0` it
 * replaced. That was decoration then and a signal now — the issue asks that a
 * chunk found by only one of the two searches be recognisable as such — and
 * `--border` on `--card` is barely over a 1:1 contrast ratio. `--muted` is the
 * colour the rest of this panel uses for secondary text.
 *
 * `title` alone would not carry it either: screen readers do not announce it
 * reliably, and a bare "—" says nothing. Hence the `.sr-only` sentence, the
 * same idiom QuizCard uses for its correct-answer marker.
 */
function RankCell({ rank, search }: { rank: number; search: string }) {
  const found = rank !== RANK_ABSENT;
  return (
    <span
      style={{ ...COL_RANK, color: found ? "var(--navy)" : "var(--muted)", fontWeight: found ? 700 : 400 }}
      title={found ? `${search}: Rang ${rank}` : `${search}: nicht gefunden`}
    >
      <span aria-hidden="true">{rankLabel(rank)}</span>
      <span className="sr-only">{found ? `${search} Rang ${rank}` : `${search}: nicht gefunden`}</span>
    </span>
  );
}

/**
 * One candidate chunk: its similarity, where each search ranked it, and the
 * RRF score those ranks produced (T-54).
 *
 * The three numbers sit left of the filename on purpose. Appending them on the
 * right would have taken the width from the source, which is the column an
 * admin actually reads; this way the fixed columns come out of the bar and the
 * source keeps the rest of the row.
 */
function ChunkBar({ chunk, threshold, rrfK }: { chunk: ChunkDebugInfo; threshold: number; rrfK: number | null }) {
  const [open, setOpen] = useState(false);
  const scorePct = Math.max(0, Math.min(100, Math.round(chunk.score * 100)));
  const thPct    = Math.round(threshold * 100);
  const color    = chunk.above_threshold ? "var(--green)" : "var(--red)";
  const parts    = [chunk.filename, chunk.page ? `S.${chunk.page}` : null, chunk.heading ? `— ${chunk.heading}` : null].filter(Boolean).join(" ");

  const foundDense  = chunk.dense_rank !== RANK_ABSENT;
  const foundSparse = chunk.sparse_rank !== RANK_ABSENT;

  // The arithmetic behind the sort key, spelled out with the k this request
  // actually used. Without it the score is a number to trust; with it the
  // ordering is something an admin can check.
  const ranks = [foundDense ? chunk.dense_rank : null, foundSparse ? chunk.sparse_rank : null]
    .filter((rank): rank is number => rank !== null);
  const rrfFormula = rrfK !== null && ranks.length > 0
    ? `${ranks.map(rank => `1/(${rrfK}+${rank})`).join(" + ")} = ${chunk.rrf_score}`
    : String(chunk.rrf_score);

  const origin = foundDense && foundSparse
    ? "Beide Suchen haben ihn gefunden — die Ränge addieren sich im RRF-Score."
    : foundSparse
      ? "Nur die Volltextsuche hat ihn gefunden: ein wörtlicher Treffer, den die Vektorsuche verfehlt (ADR-007)."
      : "Nur die Vektorsuche hat ihn gefunden: inhaltlich nah, ohne wörtliche Übereinstimmung.";

  // The two cases the panel could not explain before — a red chunk in the
  // context, and a green one that was cut. Both are the fusion working as
  // designed, and both look like a bug without this sentence.
  const placement = chunk.in_top_n && !chunk.above_threshold
    ? "Trotzdem im Kontext: die Auswahl folgt dem RRF-Rang, nicht der Similarity."
    : !chunk.in_top_n && chunk.above_threshold
      ? "Über der Schwelle, aber nicht im Kontext: andere Chunks haben einen höheren RRF-Score."
      : null;

  const term: CSSProperties = { width: 62, flexShrink: 0, color: "var(--muted)", fontWeight: 700 };
  const defRow: CSSProperties = { display: "flex", gap: 8, fontSize: 10 };

  return (
    <div style={{ marginBottom: 5 }}>
      <div
        style={{ ...CHUNK_ROW, cursor: "pointer", userSelect: "none" }}
        onClick={() => setOpen(v => !v)}
      >
        <span style={{ ...COL_SCORE, color }}>{scorePct}%</span>
        <div style={{ ...COL_BAR, position: "relative", height: 5, background: "var(--border)", borderRadius: 3 }}>
          <div style={{ width: `${scorePct}%`, height: "100%", background: color, borderRadius: 3 }} />
          {/* threshold marker */}
          <div style={{ position: "absolute", top: -2, left: `${thPct}%`, width: 2, height: 9, background: "var(--navy)", borderRadius: 1 }} />
        </div>
        <RankCell rank={chunk.dense_rank} search="Vektorsuche" />
        <RankCell rank={chunk.sparse_rank} search="Volltextsuche" />
        <span style={{ ...COL_RRF, color: "var(--navy)" }} title={`RRF ${rrfFormula}`}>
          <span aria-hidden="true">{chunk.rrf_score.toFixed(4).replace(/^0/, "")}</span>
          <span className="sr-only">RRF-Score {chunk.rrf_score}</span>
        </span>
        <span style={{ ...COL_SRC, color: "var(--muted)" }}>{parts}</span>
        <span style={COL_BADGE}>
          {chunk.in_top_n && (
            <span style={{ fontSize: 9, padding: "1px 5px", borderRadius: 8, background: "var(--blue)", color: "#fff", fontWeight: 700 }}>
              LLM
            </span>
          )}
        </span>
        <span style={COL_CARET}>{open ? "▲" : "▼"}</span>
      </div>
      {open && (
        <div style={{ margin: "5px 0 0 36px", display: "flex", flexDirection: "column", gap: 5 }}>
          <div style={{
            background: "var(--amber-lt)", border: "1px solid var(--amber)", borderRadius: 6,
            padding: "8px 10px", display: "flex", flexDirection: "column", gap: 3,
          }}>
            <div style={defRow}>
              <span style={term}>Herkunft</span>
              <span style={{ color: "var(--navy)" }}>
                Dense {foundDense ? chunk.dense_rank : "— nicht gefunden"} · Sparse {foundSparse ? chunk.sparse_rank : "— nicht gefunden"}
              </span>
            </div>
            <div style={defRow}>
              <span style={term}>RRF</span>
              <span style={{ color: "var(--navy)", fontFamily: "monospace" }}>{rrfFormula}</span>
            </div>
            <div style={defRow}>
              <span style={term}>Cosine</span>
              <span style={{ color }}>
                {chunk.score} — {chunk.above_threshold ? "über" : "unter"} Schwelle {threshold}
              </span>
            </div>
            <div style={{
              fontSize: 10, lineHeight: 1.5, color: "var(--text)",
              marginTop: 3, paddingTop: 5, borderTop: "1px solid var(--amber)",
            }}>
              {origin}{placement && ` ${placement}`}
            </div>
          </div>
          <pre style={{
            margin: 0, padding: "7px 10px",
            background: chunk.above_threshold ? "var(--green-lt)" : "var(--red-lt)",
            borderRadius: 6, fontSize: 10, lineHeight: 1.5,
            whiteSpace: "pre-wrap", wordBreak: "break-word",
            maxHeight: 180, overflowY: "auto", color: "var(--navy)",
          }}>
            {chunk.content}
          </pre>
        </div>
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
          <span><strong style={{ color: "var(--navy)" }}>D</strong>/<strong style={{ color: "var(--navy)" }}>S</strong> = Rang in Vektor-/Volltextsuche, <span style={{ color: "var(--muted)", fontWeight: 700 }}>—</span> = dort nicht gefunden</span>
        </div>
        <ChunkColumns />
        {debug.chunks.map(c => (
          <ChunkBar
            key={c.chunk_id}
            chunk={c}
            threshold={debug.similarity_threshold}
            rrfK={debug.params_used.rrf_k ?? null}
          />
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
 * One clickable source reference (US-01, T-20/T-21).
 *
 * Clicking the reference opens the document viewer with the belegenden
 * Abschnitt hervorgehoben (T-21, #28). Expanding the excerpt is a separate,
 * secondary control — one surface opening the viewer and toggling the excerpt
 * at once would make the primary action ambiguous.
 */
function CitationEntry({ citation, onOpenViewer }: { citation: Citation; onOpenViewer: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const section = citation.heading ? ` · ${citation.heading}` : "";
  const page = citation.page ? ` · S. ${citation.page}` : "";
  const label = `[${citation.index}] ${citation.filename}${section}${page}`;

  return (
    <div style={{ background: "var(--blue-lt)", borderRadius: 8, padding: "8px 12px" }}>
      <button
        onClick={onOpenViewer}
        aria-label={`Originaldokument öffnen: ${label}`}
        style={{
          background: "none", border: "none", padding: 0, fontSize: 12, textAlign: "left",
          width: "100%", cursor: "pointer", fontFamily: "inherit", fontWeight: 700,
          color: "var(--navy)", marginBottom: 4, display: "flex", justifyContent: "space-between",
        }}
      >
        <span>{label}</span>
        <span aria-hidden="true" style={{ fontWeight: 400, color: "var(--muted)" }}>↗</span>
      </button>
      <button
        onClick={() => setExpanded(v => !v)}
        aria-expanded={expanded}
        style={{
          background: "none", border: "none", padding: 0, fontSize: 12, textAlign: "left",
          width: "100%", cursor: "pointer", fontFamily: "inherit", color: "var(--muted)", lineHeight: 1.45,
          ...(expanded ? {} : {
            display: "-webkit-box",
            WebkitLineClamp: EXCERPT_CLAMP_LINES,
            WebkitBoxOrient: "vertical" as const,
            overflow: "hidden",
          }),
        }}
      >
        {/* Kein aria-label hier: das würde den Auszug als Accessible Name
            ersetzen und ihn für Screenreader unhörbar machen, auch aufgeklappt.
            Der sichtbare Auszug bleibt Teil des Namens, der Kontext kommt als
            unsichtbarer Zusatz davor (wie QuizCard.tsx "— richtige Antwort"). */}
        <span className="sr-only">{`Auszug ${expanded ? "einklappen" : "ausklappen"}: ${label}. `}</span>
        {citation.excerpt}
      </button>
    </div>
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
  const [viewerCitation, setViewerCitation] = useState<Citation | null>(null);

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
          {/* Retrieval and citation are the parts, the composite is the answer.
              Requirements §75 asks that the score be visible, and that is the
              chip above; these two are calibration figures, and next to the
              badge US-02 actually wants read they were three numbers competing
              with the one statement. Gated on `debug`, which openapi.yaml fills
              for the admin role alone — the same signal the thresholds below
              already depend on, so the block no longer has to decline to colour
              what it cannot judge. */}
          {d && (() => {
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
          {m.citations.map(c => (
            <CitationEntry key={c.chunk_id} citation={c} onOpenViewer={() => setViewerCitation(c)} />
          ))}
        </div>
      )}

      {viewerCitation && (
        <DocumentViewer
          citation={viewerCitation}
          token={token}
          onClose={() => setViewerCitation(null)}
        />
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
