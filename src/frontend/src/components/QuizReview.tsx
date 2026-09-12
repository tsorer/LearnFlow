import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { AuthUser } from "../types";
import { api, ApiError, type QuizQuestion, type QuizQuestionStatus, type QuizQuestionUpdate } from "../api/client";
import Layout from "./Layout";
import QuizCard from "./QuizCard";

const PAGE_SIZE = 50;

const COLUMNS: { status: QuizQuestionStatus; label: string }[] = [
  { status: "pending", label: "Ausstehend" },
  { status: "approved", label: "Freigegeben" },
  { status: "rejected", label: "Abgelehnt" },
];

interface Column {
  items: QuizQuestion[];
  total: number;
}

const emptyColumn: Column = { items: [], total: 0 };

/**
 * The message the generation button's failure becomes, or a generic one for
 * anything the spec did not carve out a status for. Mirrors failureMessage in
 * ChatView.tsx: mapped here rather than passed through, so the UI does not
 * depend on the exact German the backend happens to send.
 */
export function generationFailureMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "Kein indexiertes Dokument im Bereich — bitte zuerst ein Dokument hochladen.";
    if (err.status === 429) return "Zu viele Generierungen in kurzer Zeit (max. 3/Minute). Bitte kurz warten.";
    if (err.status === 503) return "Der LLM-Provider ist derzeit nicht erreichbar. Bitte später erneut versuchen.";
  }
  return "Fehler bei der Generierung. Bitte erneut versuchen.";
}

interface Props { user: AuthUser; onLogout: () => void }

export default function QuizReview({ user, onLogout }: Props) {
  const navigate = useNavigate();
  const [columns, setColumns] = useState<Record<QuizQuestionStatus, Column>>({
    pending: emptyColumn,
    approved: emptyColumn,
    rejected: emptyColumn,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [generating, setGenerating] = useState(false);
  const [notice, setNotice] = useState("");
  const [mutating, setMutating] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState<QuizQuestionStatus | null>(null);

  /**
   * Resets every column to its first page. `limit` never exceeds `PAGE_SIZE`
   * regardless of how many pages a column had loaded before — the backend
   * caps `limit` at 200 (openapi.yaml), and reloading a grown limit after
   * every action was exactly what made "Weitere laden" 422 the whole board
   * once a column passed that cap.
   */
  const loadFirstPage = useCallback(async () => {
    setError("");
    try {
      const results = await Promise.all(
        COLUMNS.map(c => api.listQuizQuestions(c.status, PAGE_SIZE, 0, user.token)),
      );
      setColumns(prev => {
        const next = { ...prev };
        COLUMNS.forEach((c, i) => {
          next[c.status] = { items: results[i].items, total: results[i].total };
        });
        return next;
      });
    } catch {
      setError("Fragen konnten nicht geladen werden. Bitte Seite neu laden.");
    } finally {
      setLoading(false);
    }
  }, [user.token]);

  useEffect(() => {
    void loadFirstPage();
  }, [loadFirstPage]);

  /** Fetches the next page for exactly one column and appends it — real offset paging, not a bigger `limit`. */
  const loadMore = async (status: QuizQuestionStatus) => {
    setLoadingMore(status);
    setError("");
    setNotice("");
    try {
      const offset = columns[status].items.length;
      const page = await api.listQuizQuestions(status, PAGE_SIZE, offset, user.token);
      setColumns(prev => ({
        ...prev,
        [status]: { items: [...prev[status].items, ...page.items], total: page.total },
      }));
    } catch {
      setError("Weitere Fragen konnten nicht geladen werden. Bitte erneut versuchen.");
    } finally {
      setLoadingMore(null);
    }
  };

  const generate = async () => {
    setGenerating(true);
    setNotice("");
    setError("");
    try {
      const result = await api.generateQuiz(user.token);
      // generated === 0 does not occur here: the backend answers an empty
      // result with 503 rather than a 201 with nothing in it (ADR-008), so a
      // successful response always carries at least one question.
      setNotice(`${result.generated} neue Frage(n) erzeugt.`);
      await loadFirstPage();
    } catch (err) {
      setError(generationFailureMessage(err));
    } finally {
      setGenerating(false);
    }
  };

  // Returns whether the PATCH succeeded: QuizCard only leaves edit mode on
  // success, so a failed save keeps the draft on screen instead of losing it.
  const mutate = async (questionId: string, patch: QuizQuestionUpdate): Promise<boolean> => {
    setMutating(questionId);
    setError("");
    setNotice("");
    try {
      await api.updateQuizQuestion(questionId, patch, user.token);
      await loadFirstPage();
      return true;
    } catch {
      setError("Änderung konnte nicht gespeichert werden. Bitte erneut versuchen.");
      return false;
    } finally {
      setMutating(null);
    }
  };

  return (
    <Layout
      user={user}
      onLogout={onLogout}
      navItems={<button className="nav-item" onClick={() => navigate("/")}>Zurück zum Chat</button>}
    >
      <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-4) var(--space-6)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-4)" }}>
          <div style={{ fontWeight: "var(--font-black)", fontSize: "var(--text-xl)", color: "var(--text-primary)" }}>Quiz-Review</div>
          <button className="primary" onClick={generate} disabled={generating}>
            {generating ? "Generiere…" : "Fragen generieren"}
          </button>
        </div>

        {error && (
          <div role="alert" style={{
            background: "var(--red-tint)", color: "var(--red)", borderRadius: "var(--radius-sm)",
            padding: "8px 12px", fontSize: "var(--text-sm)", marginBottom: 12,
          }}>
            {error}
          </div>
        )}
        {notice && (
          <div role="status" style={{
            background: "var(--olive-tint)", color: "var(--olive)", borderRadius: "var(--radius-sm)",
            padding: "8px 12px", fontSize: "var(--text-sm)", marginBottom: 12,
          }}>
            {notice}
          </div>
        )}
        {loading ? (
          <div style={{ color: "var(--text-muted)", textAlign: "center", marginTop: 40 }}>Lädt…</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(280px, 1fr))", gap: "var(--space-4)" }}>
            {COLUMNS.map(({ status, label }) => {
              const col = columns[status];
              return (
                <div key={status} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div style={{ fontWeight: "var(--font-bold)", color: "var(--text-primary)", fontSize: "var(--text-sm)" }}>
                    {label} ({col.total})
                  </div>
                  {col.items.length === 0 && (
                    <div style={{ color: "var(--text-muted)", fontSize: "var(--text-xs)" }}>Keine Fragen.</div>
                  )}
                  {col.items.map(q => (
                    <QuizCard
                      key={q.id}
                      question={q}
                      busy={mutating === q.id}
                      onAction={patch => mutate(q.id, patch)}
                      onSave={patch => mutate(q.id, patch)}
                    />
                  ))}
                  {col.items.length < col.total && (
                    <button
                      className="secondary"
                      style={{ fontSize: "var(--text-xs)" }}
                      disabled={loadingMore === status}
                      onClick={() => loadMore(status)}
                    >
                      {loadingMore === status ? "Lädt…" : "Weitere laden"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
}
