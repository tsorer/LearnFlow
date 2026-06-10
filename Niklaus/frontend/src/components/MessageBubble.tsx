import { useState } from "react";
import type { Message } from "../types";
import { api } from "../api/client";

const bandColor = { high: "var(--green)", medium: "var(--amber)", low: "var(--red)" };
const bandBg = { high: "var(--green-lt)", medium: "var(--amber-lt)", low: "var(--red-lt)" };
const bandLabel = { high: "Hoch", medium: "Mittel", low: "Tief" };

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

  const band = m.confidence?.band;

  return (
    <div style={{ alignSelf: "flex-start", maxWidth: "85%", display: "flex", flexDirection: "column", gap: 6 }}>
      {m.suppressed && (
        <div style={{
          background: "var(--amber-lt)", color: "var(--amber)", borderRadius: 8,
          padding: "6px 12px", fontSize: 12, fontWeight: 600,
        }}>
          ⚠ Keine belastbaren Informationen gefunden
        </div>
      )}

      <div style={{
        background: "var(--card)", border: "1px solid var(--border)",
        borderRadius: "2px 12px 12px 12px",
        padding: "10px 14px", fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-wrap",
      }}>
        {m.content}
      </div>

      {/* Confidence + sources row */}
      {!m.suppressed && m.confidence && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {band && (
            <span style={{
              background: bandBg[band], color: bandColor[band],
              borderRadius: 30, padding: "2px 9px", fontSize: 11, fontWeight: 700,
            }}>
              Konfidenz {bandLabel[band]} · {Math.round(m.confidence.score * 100)}%
            </span>
          )}
          {m.citations && m.citations.length > 0 && (
            <button className="secondary" style={{ fontSize: 11, padding: "2px 9px" }}
              onClick={() => setShowSources(v => !v)}>
              {showSources ? "Quellen verbergen" : `${m.citations.length} Quelle${m.citations.length > 1 ? "n" : ""}`}
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
