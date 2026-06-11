import { useState } from "react";
import type { Message, ChunkDebugInfo, StageInfo, LLMCallInfo, DebugInfo, ConfidenceInfo } from "../types";
import { api } from "../api/client";


const PARAM_LABELS: Record<string, string> = {
  similarity_threshold:     "Similarity-Schwellwert",
  min_retrieval_confidence: "Min. Retrieval-Konfidenz",
  min_citation_coverage:    "Min. Citation-Coverage",
  top_k:                    "Top-K Kandidaten",
  top_n:                    "Top-N ans LLM",
  self_check_band_low:      "Self-Check Zone (unten)",
  self_check_band_high:     "Self-Check Zone (oben)",
  llm_temperature:          "Temperature",
  llm_max_tokens:           "Max Tokens",
  llm_top_p:                "Top-P",
  llm_seed:                 "Seed",
};

const suppressLabels: Record<string, string> = {
  no_relevant_chunks:       "Keine Chunks über Schwellwert",
  low_retrieval_confidence: "Retrieval-Konfidenz zu tief",
  low_citation_coverage:    "Citation-Coverage zu tief",
  low_composite_score:      "Composite Score unter Self-Check Zone",
  self_check_failed:        "Self-Check fehlgeschlagen",
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
      ? (stage.threshold !== null && stage.threshold >= 1 ? String(stage.value) : pct(stage.value))
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

        {/* Pipeline stages interleaved with LLM calls and Composite */}
        {debug.stages.map((s, i) => {
          const groundingCall = i === 1 ? debug.llm_calls.find(c => c.step === "grounding") : null;
          const selfCheckCall = i === 3 ? debug.llm_calls.find(c => c.step === "self_check") : null;
          // Insert Composite Score between Citation (i=2) and Self-Check (i=3)
          const showComposite = i === 2;
          return (
            <div key={s.id}>
              <PipelineStep num={i < 3 ? i + 1 : i + 2} stage={s} isLast={false} />
              {groundingCall && <LLMCallNode call={groundingCall} isLast={false} />}
              {showComposite && (() => {
                const scLow  = debug.params_used.self_check_band_low  ?? 0.50;
                const scHigh = debug.params_used.self_check_band_high ?? 0.75;
                const score  = confidence.score;
                const below  = score < scLow;
                const inZone = score >= scLow && score < scHigh;
                const dotColor    = below ? "var(--red)"   : inZone ? "var(--amber)"   : "var(--green)";
                const dotShadow   = below ? "var(--red-lt)": inZone ? "var(--amber-lt)": "var(--green-lt)";
                const statusText  = below ? "✗ STOPP"      : inZone ? "→ Self-Check"   : "✓ OK";
                const statusColor = below ? "var(--red)"   : inZone ? "var(--amber)"   : "var(--green)";
                return (
                  <div style={{ display: "flex", gap: 0 }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", flexShrink: 0, width: 22 }}>
                      <div style={{
                        width: 18, height: 18, borderRadius: "50%", flexShrink: 0,
                        background: dotColor, color: "#fff",
                        fontSize: 9, fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center",
                        boxShadow: `0 0 0 2px ${dotShadow}`,
                      }}>4</div>
                      <div style={{ flex: 1, width: 2, background: "var(--border)", minHeight: 10 }} />
                    </div>
                    <div style={{ flex: 1, paddingLeft: 10, paddingBottom: 10 }}>
                      <div style={{ display: "flex", alignItems: "baseline", gap: 8, flexWrap: "wrap" }}>
                        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--navy)" }}>Composite Score</span>
                        <span style={{ fontSize: 11, fontWeight: 800, color: dotColor }}>{pct(score)}</span>
                        <span style={{ fontSize: 10, color: "var(--muted)" }}>
                          Zone: {pct(scLow)}–{pct(scHigh)}
                        </span>
                        <span style={{ fontSize: 10, fontWeight: 700, color: statusColor, marginLeft: "auto" }}>{statusText}</span>
                      </div>
                      <div style={{ fontSize: 10, color: "var(--muted)", marginTop: 2, fontFamily: "monospace" }}>
                        {debug.formula_breakdown}
                      </div>
                      <div style={{ display: "flex", gap: 6, marginTop: 5, flexWrap: "wrap" }}>
                        {[
                          { label: "Top-Score",    val: debug.retrieval_detail.top_score },
                          { label: "Mean-Score",   val: debug.retrieval_detail.mean_score },
                          { label: "Density (÷5)", val: debug.retrieval_detail.evidence_density },
                        ].map(item => (
                          <div key={item.label} style={{ padding: "2px 8px", borderRadius: 6, background: "var(--blue-lt)", fontSize: 10, display: "flex", gap: 4, alignItems: "baseline" }}>
                            <span style={{ fontWeight: 700, color: "var(--navy)" }}>{pct(item.val)}</span>
                            <span style={{ color: "var(--muted)" }}>{item.label}</span>
                          </div>
                        ))}
                        <span style={{ fontSize: 10, color: "var(--muted)", alignSelf: "center" }}>→ 0.5×Top + 0.3×Mean + 0.2×Density</span>
                      </div>
                    </div>
                  </div>
                );
              })()}
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

// ── Main component ─────────────────────────────────────────────────────────
interface Props { message: Message; token: string; }

export default function MessageBubble({ message: m, token }: Props) {
  const [feedback, setFeedback] = useState<number | null>(null);
  const [showSources, setShowSources] = useState(false);

  const submitFeedback = async (rating: number) => {
    if (!m.answer_id || feedback !== null) return;
    setFeedback(rating);
    await api.submitFeedback(m.answer_id, rating, null, token).catch(() => {});
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

      {/* Metric bar — thresholds from actual query params, not hardcoded */}
      {m.confidence && (
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{
            background: "var(--blue-lt)", color: "var(--navy)",
            borderRadius: 20, padding: "2px 10px", fontSize: 11, fontWeight: 700,
          }}>
            Composite: {pct(m.confidence.score)}
          </span>
          {(() => {
            const minRet = d?.params_used?.min_retrieval_confidence ?? 0.55;
            const minCit = d?.params_used?.min_citation_coverage ?? 0.50;
            const retFail = m.confidence!.retrieval_score < minRet;
            const citFail = m.confidence!.citation_coverage < minCit;
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
                  background: citFail ? "var(--red-lt)" : "var(--blue-lt)",
                  color: citFail ? "var(--red)" : "var(--navy)",
                }}>
                  Citation: {pct(m.confidence!.citation_coverage)}
                </span>
              </>
            );
          })()}
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

      {/* Sources */}
      {showSources && m.citations && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {m.citations.map(c => (
            <div key={c.chunk_id} style={{
              background: "var(--blue-lt)", borderRadius: 8, padding: "8px 12px", fontSize: 12,
            }}>
              <div style={{ fontWeight: 700, color: "var(--navy)", marginBottom: 4 }}>
                [{c.index}] {c.filename}{c.page ? ` · S. ${c.page}` : ""}
              </div>
              <div style={{ color: "var(--muted)", lineHeight: 1.45 }}>{c.excerpt}</div>
            </div>
          ))}
        </div>
      )}

      {/* Always-visible debug panel */}
      {d && m.confidence && (
        <DebugPanel debug={d} confidence={m.confidence} />
      )}

      {/* Feedback */}
      {m.answer_id && !m.suppressed && (
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <span style={{ fontSize: 11, color: "var(--muted)" }}>Hilfreich?</span>
          {[1, 2, 3, 4, 5].map(r => (
            <button key={r} onClick={() => submitFeedback(r)}
              style={{
                background: feedback === r ? "var(--blue)" : "transparent",
                color: feedback === r ? "#fff" : "var(--muted)",
                border: "1px solid var(--border)", borderRadius: 4,
                padding: "1px 6px", fontSize: 11,
              }}>
              {r}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
