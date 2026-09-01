import { useState } from "react";
import type { QuizQuestion, QuizQuestionUpdate } from "../api/client";

const OPTION_LETTERS = ["A", "B", "C", "D"] as const;

const statusActions: Record<QuizQuestion["status"], { label: string; patch: QuizQuestionUpdate }[]> = {
  pending: [
    { label: "Freigeben", patch: { status: "approved" } },
    { label: "Ablehnen", patch: { status: "rejected" } },
  ],
  approved: [
    { label: "Freigabe zurückziehen", patch: { status: "pending" } },
    { label: "Ablehnen", patch: { status: "rejected" } },
  ],
  rejected: [
    { label: "Freigeben", patch: { status: "approved" } },
    { label: "Zurück in die Prüfung", patch: { status: "pending" } },
  ],
};

/**
 * The fields actually changed against `original`, or null if none were.
 *
 * Only a value that differs from the stored one counts as a content change
 * (openapi.yaml, PATCH /api/quiz/questions/{question_id}) — sending every
 * field back unconditionally would make every save look like an edit and pull
 * an approved question back into review for nothing.
 */
export function diffQuestion(
  original: QuizQuestion,
  draft: {
    question: string;
    options: string[];
    correct_answer: QuizQuestion["correct_answer"];
    explanation: string;
  },
): QuizQuestionUpdate | null {
  const patch: QuizQuestionUpdate = {};
  if (draft.question !== original.question) patch.question = draft.question;
  if (draft.options.some((o, i) => o !== original.options[i])) patch.options = draft.options;
  if (draft.correct_answer !== original.correct_answer) patch.correct_answer = draft.correct_answer;
  if (draft.explanation !== original.explanation) patch.explanation = draft.explanation;
  return Object.keys(patch).length > 0 ? patch : null;
}

interface Props {
  question: QuizQuestion;
  busy: boolean;
  onAction: (patch: QuizQuestionUpdate) => void;
  // Resolves to whether the save succeeded, so the card only leaves edit mode
  // once the PATCH actually landed — a rejection keeps the draft on screen
  // instead of silently discarding it (QuizReview owns the request and its
  // error message; the card only owns the editing/not-editing state).
  onSave: (patch: QuizQuestionUpdate) => Promise<boolean>;
}

export default function QuizCard({ question: q, busy, onAction, onSave }: Props) {
  const [editing, setEditing] = useState(false);
  const [question, setQuestion] = useState(q.question);
  const [options, setOptions] = useState(q.options);
  const [correctAnswer, setCorrectAnswer] = useState<QuizQuestion["correct_answer"]>(q.correct_answer);
  const [explanation, setExplanation] = useState(q.explanation);

  const save = async (patch: QuizQuestionUpdate) => {
    if (await onSave(patch)) setEditing(false);
  };

  const startEdit = () => {
    setQuestion(q.question);
    setOptions(q.options);
    setCorrectAnswer(q.correct_answer);
    setExplanation(q.explanation);
    setEditing(true);
  };

  const patch = diffQuestion(q, { question, options, correct_answer: correctAnswer, explanation });
  // Nur eine bereits freigegebene Frage kann durch eine inhaltliche Aenderung
  // zurueckgestuft werden -- bei pending/rejected gibt es keine Freigabe, die
  // verloren gehen koennte.
  const wouldDemote = q.status === "approved" && patch !== null;

  return (
    <div style={{
      background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10,
      padding: 14, display: "flex", flexDirection: "column", gap: 10,
    }}>
      {q.chunk_id === null && (
        <div
          title="Das Dokument wurde durch eine neue Fassung ersetzt; die Frage ist deshalb auf 'pending' zurückgefallen. Die Quellen-Passage unten ist der einzige verbliebene Beleg."
          style={{
            alignSelf: "flex-start", background: "var(--amber-lt)", color: "var(--amber)",
            fontSize: 11, fontWeight: 700, borderRadius: 6, padding: "2px 8px",
          }}
        >
          Quelle ersetzt
        </div>
      )}

      {editing ? (
        <textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          rows={2}
          style={{ width: "100%", fontWeight: 700 }}
        />
      ) : (
        <div style={{ fontWeight: 700, color: "var(--navy)" }}>{q.question}</div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {OPTION_LETTERS.map((letter, i) => {
          const isCorrect = editing ? correctAnswer === letter : q.correct_answer === letter;
          return (
            <div key={letter} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {editing && (
                <input
                  type="radio"
                  name={`correct-${q.id}`}
                  checked={correctAnswer === letter}
                  onChange={() => setCorrectAnswer(letter)}
                  aria-label={`${letter} ist die richtige Antwort`}
                />
              )}
              <span style={{
                fontSize: 12, fontWeight: 700, minWidth: 16,
                color: isCorrect ? "var(--green)" : "var(--muted)",
              }}>
                {letter}
              </span>
              {editing ? (
                <input
                  value={options[i]}
                  onChange={e => setOptions(prev => prev.map((o, idx) => (idx === i ? e.target.value : o)))}
                  style={{ flex: 1, fontSize: 13 }}
                />
              ) : (
                // Colour alone (WCAG 1.4.1) is not enough to mark the correct
                // option for colour-blind reviewers or screen readers, so a
                // checkmark and an aria-label carry the same information.
                <span
                  style={{
                    fontSize: 13, flex: 1,
                    color: isCorrect ? "var(--green)" : "var(--text)",
                    fontWeight: isCorrect ? 700 : 400,
                  }}
                  aria-label={isCorrect ? `${q.options[i]} — richtige Antwort` : undefined}
                >
                  {isCorrect && <span aria-hidden="true">✓ </span>}
                  {q.options[i]}
                </span>
              )}
            </div>
          );
        })}
      </div>

      <div>
        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", marginBottom: 2 }}>Erklärung</div>
        {editing ? (
          <textarea
            value={explanation}
            onChange={e => setExplanation(e.target.value)}
            rows={2}
            style={{ width: "100%", fontSize: 13 }}
          />
        ) : (
          <div style={{ fontSize: 13, color: "var(--text)" }}>{q.explanation}</div>
        )}
      </div>

      <div>
        <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", marginBottom: 2 }}>Quellen-Passage</div>
        <blockquote style={{
          margin: 0, borderLeft: "3px solid var(--blue)", paddingLeft: 10,
          fontSize: 12, color: "var(--muted)", fontStyle: "italic",
        }}>
          {q.source_excerpt}
        </blockquote>
      </div>

      <div style={{ fontSize: 11, color: "var(--muted)" }}>
        Erzeugt: {new Date(q.created_at).toLocaleString("de-CH")}
        {q.status === "approved" && q.approved_at && (
          <> · Freigegeben: {new Date(q.approved_at).toLocaleString("de-CH")}</>
        )}
      </div>

      {editing && wouldDemote && (
        <div style={{
          fontSize: 12, color: "var(--amber)", background: "var(--amber-lt)",
          borderRadius: 6, padding: "6px 10px",
        }}>
          Diese Änderung nimmt die Freigabe zurück — die Frage geht zurück in die Prüfung.
        </div>
      )}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {editing ? (
          <>
            <button
              className="primary"
              disabled={busy || patch === null}
              onClick={() => patch && save(patch)}
            >
              Speichern
            </button>
            {wouldDemote && (
              <button
                className="primary"
                disabled={busy || patch === null}
                onClick={() => patch && save({ ...patch, status: "approved" })}
              >
                Speichern und freigeben
              </button>
            )}
            <button className="secondary" disabled={busy} onClick={() => setEditing(false)}>
              Abbrechen
            </button>
          </>
        ) : (
          <>
            {statusActions[q.status].map(a => (
              <button key={a.label} className="secondary" disabled={busy} onClick={() => onAction(a.patch)}>
                {a.label}
              </button>
            ))}
            <button className="secondary" disabled={busy} onClick={startEdit}>
              Editieren
            </button>
          </>
        )}
      </div>
    </div>
  );
}
