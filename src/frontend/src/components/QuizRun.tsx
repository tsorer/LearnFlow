import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type QuizQuestion } from "../api/client";
import DocumentViewer from "./DocumentViewer";

const OPTION_LETTERS = ["A", "B", "C", "D"] as const;
type Letter = (typeof OPTION_LETTERS)[number];

// Ziellänge eines Durchlaufs (US-08: "5 Multiple-Choice-Fragen"). Der Pool
// kann weniger als 5 freigegebene Fragen enthalten -- das ist kein Fehler,
// die Runde ist dann entsprechend kürzer (siehe Hinweis unten).
const TARGET_LENGTH = 5;

interface Props { token: string }

/** Frage-ID → gewählter Buchstabe. Nur im Browser-State, nie an ein Backend
 * gemeldet (US-08: "nicht personenbezogen gespeichert oder ausgewertet"). */
type Answers = Record<string, Letter>;

export function scoreOf(questions: QuizQuestion[], answers: Answers): number {
  return questions.filter(q => answers[q.id] === q.correct_answer).length;
}

/** Öffnet den DocumentViewer mit nur den zwei IDs, die er braucht -- nicht der
 * ganzen Frage, die zufällig auch eine davon trägt. */
interface ViewerTarget { documentId: string; chunkId: string }

export default function QuizRun({ token }: Props) {
  const navigate = useNavigate();
  const [questions, setQuestions] = useState<QuizQuestion[] | null>(null);
  // `total` ist die Poolgröße laut Endpoint (openapi.yaml, app/routers/quiz.py
  // sample_questions): ein `count(*)` über den ganzen freigegebenen Pool,
  // *ohne* das Limit von `items`. Bei 20 freigegebenen Fragen liefert der
  // Endpoint `total: 20, items: 5` -- `total` ist also nicht "wie viele Fragen
  // diese Runde hat". `items.length` bleibt `min(total, TARGET_LENGTH)`, also
  // ist `total < TARGET_LENGTH` gleichbedeutend mit `items.length <
  // TARGET_LENGTH` und beide ergäben denselben `shortRound` -- `total` steht
  // hier trotzdem, weil es die Absicht ("Pool ist knapp") im Code ausdrückt
  // statt nur im Kopf. Für alles andere (z. B. "Frage X von …") ist `total`
  // die falsche Zahl; dafür ist `items.length`/`totalQuestions` gemeint.
  const [total, setTotal] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Answers>({});
  const [finished, setFinished] = useState(false);
  const [viewerTarget, setViewerTarget] = useState<ViewerTarget | null>(null);

  // Auch der "Neue Runde"-Button ruft das hier auf, nicht nur der Mount-Effekt
  // -- eine Runde ist sonst eine Sackgasse, obwohl der Pool weitere Fragen hat.
  const load = useCallback(() => {
    setQuestions(null);
    setError("");
    setIndex(0);
    setAnswers({});
    setFinished(false);
    api.getQuizSample(token)
      .then(page => { setQuestions(page.items); setTotal(page.total); })
      .catch(() => setError("Quiz konnte nicht geladen werden. Bitte erneut versuchen."));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const shortRound = total !== null && total > 0 && total < TARGET_LENGTH;

  const select = (letter: Letter) => {
    if (!questions) return;
    setAnswers(prev => ({ ...prev, [questions[index].id]: letter }));
  };

  const next = () => {
    if (!questions) return;
    if (index + 1 < questions.length) setIndex(i => i + 1);
    else setFinished(true);
  };

  return (
    <div style={{ display: "flex", height: "100vh", flexDirection: "column" }}>
      <div style={{
        background: "var(--navy)", color: "#fff", padding: "0 24px",
        height: 52, display: "flex", alignItems: "center", justifyContent: "space-between",
        flexShrink: 0,
      }}>
        <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-.02em" }}>📚 LearnFlow · Quiz</div>
        <button className="secondary" style={{ fontSize: 12 }} onClick={() => navigate("/")}>
          Zurück zum Chat
        </button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", justifyContent: "center" }}>
        <div style={{ width: "min(560px, 100%)", display: "flex", flexDirection: "column", gap: 16 }}>
          {error && (
            <div role="alert" style={{
              background: "var(--red-lt)", color: "var(--red)", borderRadius: 8,
              padding: "8px 12px", fontSize: 13,
            }}>
              {error}
            </div>
          )}

          {!error && !questions && <div role="status" style={{ color: "var(--muted)" }}>Lädt…</div>}

          {questions && questions.length === 0 && (
            <div role="status" style={{
              background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10,
              padding: 16, fontSize: 14, color: "var(--text)",
            }}>
              Es sind noch keine Quizfragen für diesen Bereich freigegeben.
            </div>
          )}

          {questions && questions.length > 0 && !finished && (
            <QuestionCard
              question={questions[index]}
              questionNumber={index + 1}
              totalQuestions={questions.length}
              shortRound={shortRound}
              selected={answers[questions[index].id] ?? null}
              onSelect={select}
              onNext={next}
            />
          )}

          {questions && questions.length > 0 && finished && (
            <ResultView
              questions={questions}
              answers={answers}
              shortRound={shortRound}
              onOpenSource={q => setViewerTarget({ documentId: q.document_id, chunkId: q.chunk_id as string })}
              onRestart={load}
            />
          )}
        </div>
      </div>

      {viewerTarget && (
        <DocumentViewer
          documentId={viewerTarget.documentId}
          chunkId={viewerTarget.chunkId}
          token={token}
          onClose={() => setViewerTarget(null)}
        />
      )}
    </div>
  );
}

interface QuestionCardProps {
  question: QuizQuestion;
  questionNumber: number;
  totalQuestions: number;
  shortRound: boolean;
  selected: Letter | null;
  onSelect: (letter: Letter) => void;
  onNext: () => void;
}

function QuestionCard({ question: q, questionNumber, totalQuestions, shortRound, selected, onSelect, onNext }: QuestionCardProps) {
  const isLast = questionNumber === totalQuestions;
  const headingRef = useRef<HTMLDivElement>(null);

  // "Weiter" wird deaktiviert, sobald die neue Frage rendert (noch keine
  // Auswahl) -- der Browser wirft den Fokus dann auf <body>, weil er nicht
  // auf einem disabled-Element bleiben kann. Ohne diesen Fix müsste ein
  // Tastaturnutzer nach jeder Frage von vorn tabben, und ein Screenreader
  // sagt die neue Frage nie an (vgl. Fokus-Handling in DocumentViewer.tsx).
  // Fokussiert wird ein Container mit explizitem `aria-label` statt nur des
  // sichtbaren Zähler-Texts: ein fokussierter <div> liest zuverlässig nur
  // seinen eigenen Text vor, nicht das <legend> mit der eigentlichen Frage
  // eine Ebene darunter -- ohne das Label würde "Weiter" nur "Frage 2 von 2"
  // ankündigen und die Frage selbst verschlucken.
  useEffect(() => {
    headingRef.current?.focus();
  }, [questionNumber]);

  return (
    <div style={{
      background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10,
      padding: 20, display: "flex", flexDirection: "column", gap: 14,
    }}>
      {shortRound && questionNumber === 1 && (
        <div role="status" style={{
          background: "var(--amber-lt)", color: "var(--amber)", borderRadius: 8,
          padding: "6px 10px", fontSize: 12,
        }}>
          Nur {totalQuestions} von {TARGET_LENGTH} Fragen freigegeben — diese Runde ist entsprechend kürzer.
        </div>
      )}

      <div
        ref={headingRef}
        tabIndex={-1}
        role="group"
        aria-label={`Frage ${questionNumber} von ${totalQuestions}: ${q.question}`}
        style={{ outline: "none" }}
      >
        <div style={{ fontSize: 12, color: "var(--muted)" }}>
          Frage {questionNumber} von {totalQuestions}
        </div>
      </div>

      <fieldset style={{ border: "none", padding: 0, margin: 0 }}>
        <legend style={{ fontWeight: 700, color: "var(--navy)", fontSize: 15, marginBottom: 12, padding: 0 }}>
          {q.question}
        </legend>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {OPTION_LETTERS.map((letter, i) => (
            <label
              key={letter}
              style={{
                display: "flex", alignItems: "center", gap: 8, cursor: "pointer",
                padding: "6px 8px", borderRadius: 8,
                background: selected === letter ? "var(--blue-lt)" : "transparent",
              }}
            >
              <input
                type="radio"
                name={`answer-${q.id}`}
                checked={selected === letter}
                onChange={() => onSelect(letter)}
              />
              <span style={{ fontSize: 12, fontWeight: 700, minWidth: 16, color: "var(--muted)" }}>{letter}</span>
              <span style={{ fontSize: 13 }}>{q.options[i]}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <button className="primary" disabled={selected === null} onClick={onNext} style={{ alignSelf: "flex-start" }}>
        {isLast ? "Auswertung anzeigen" : "Weiter"}
      </button>
    </div>
  );
}

interface ResultViewProps {
  questions: QuizQuestion[];
  answers: Answers;
  shortRound: boolean;
  onOpenSource: (question: QuizQuestion) => void;
  onRestart: () => void;
}

function ResultView({ questions, answers, shortRound, onOpenSource, onRestart }: ResultViewProps) {
  const score = scoreOf(questions, answers);
  const headingRef = useRef<HTMLDivElement>(null);

  // "Auswertung anzeigen" (die letzte Frage) verschwindet mit der ganzen
  // QuestionCard aus dem DOM, derselbe Fokusverlust wie bei "Weiter" -- hier
  // gibt es aber kein disabled-Element, das ihn auslöst, sondern schlicht kein
  // Nachfolger, der ihn übernimmt. Reiner Mount-Effekt: ResultView wird pro
  // Auswertung genau einmal gemountet.
  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {shortRound && (
        <div role="status" style={{
          background: "var(--amber-lt)", color: "var(--amber)", borderRadius: 8,
          padding: "6px 10px", fontSize: 12,
        }}>
          Nur {questions.length} von {TARGET_LENGTH} Fragen freigegeben — diese Runde war entsprechend kürzer.
        </div>
      )}

      <div ref={headingRef} tabIndex={-1} style={{ fontWeight: 800, fontSize: 18, color: "var(--navy)", outline: "none" }}>
        {score} von {questions.length} richtig
      </div>
      {questions.map((q, i) => {
        const chosen = answers[q.id];
        const isCorrect = chosen === q.correct_answer;
        const chosenIndex = OPTION_LETTERS.indexOf(chosen);
        const correctIndex = OPTION_LETTERS.indexOf(q.correct_answer);
        return (
          <div key={q.id} style={{
            background: "var(--card)", border: "1px solid var(--border)", borderRadius: 10,
            padding: 16, display: "flex", flexDirection: "column", gap: 8,
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
              <div style={{ fontWeight: 700, color: "var(--navy)" }}>{i + 1}. {q.question}</div>
              <span style={{
                flexShrink: 0, fontSize: 11, fontWeight: 700, borderRadius: 6, padding: "2px 8px",
                background: isCorrect ? "var(--green-lt)" : "var(--red-lt)",
                color: isCorrect ? "var(--green)" : "var(--red)",
              }}>
                {isCorrect ? "Richtig" : "Falsch"}
              </span>
            </div>

            <div style={{ fontSize: 13, color: "var(--text)" }}>
              Deine Antwort: {chosen} — {q.options[chosenIndex]}
            </div>
            {!isCorrect && (
              <div style={{ fontSize: 13, color: "var(--green)" }}>
                Richtige Antwort: {q.correct_answer} — {q.options[correctIndex]}
              </div>
            )}

            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", marginBottom: 2 }}>Erklärung</div>
              <div style={{ fontSize: 13, color: "var(--text)" }}>{q.explanation}</div>
            </div>

            {q.chunk_id === null && (
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)", marginBottom: 2 }}>Quellen-Passage</div>
                <blockquote style={{
                  margin: 0, borderLeft: "3px solid var(--blue)", paddingLeft: 10,
                  fontSize: 12, color: "var(--muted)", fontStyle: "italic",
                }}>
                  {q.source_excerpt}
                </blockquote>
              </div>
            )}

            {q.chunk_id ? (
              <button
                className="secondary"
                style={{ fontSize: 12, alignSelf: "flex-start" }}
                onClick={() => onOpenSource(q)}
                aria-label={`Quelle ansehen für Frage ${i + 1}`}
              >
                Quelle ansehen ↗
              </button>
            ) : (
              // Dokument wurde durch eine neue Fassung ersetzt (QuizCard.tsx
              // kennt denselben Zustand): kein Chunk mehr, zu dem der Viewer
              // öffnen könnte, aber die Passage oben bleibt sichtbar --
              // openapi.yaml nennt sie "das einzige verbliebene Zeugnis".
              <span style={{ fontSize: 12, color: "var(--muted)" }}>
                Quelle ersetzt — das Dokument liegt nicht mehr in dieser Fassung vor.
              </span>
            )}
          </div>
        );
      })}

      <button className="primary" style={{ alignSelf: "flex-start" }} onClick={onRestart}>
        Neue Runde starten
      </button>
    </div>
  );
}
