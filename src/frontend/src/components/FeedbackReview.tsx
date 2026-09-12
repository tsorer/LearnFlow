import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { AuthUser } from "../types";
import { api, type FeedbackCategory, type FeedbackItem } from "../api/client";
import { CATEGORY_META } from "./MessageBubble";
import Layout from "./Layout";

const PAGE_SIZE = 50;

const CATEGORY_OPTIONS = Object.entries(CATEGORY_META) as [FeedbackCategory, { label: string; helpful: boolean }][];

interface Props { user: AuthUser; onLogout: () => void }

export default function FeedbackReview({ user, onLogout }: Props) {
  const navigate = useNavigate();
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [total, setTotal] = useState(0);
  const [helpfulFilter, setHelpfulFilter] = useState<"" | "true" | "false">("");
  const [categoryFilter, setCategoryFilter] = useState<"" | FeedbackCategory>("");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState("");

  const helpfulParam = helpfulFilter === "" ? null : helpfulFilter === "true";
  const categoryParam = categoryFilter === "" ? null : categoryFilter;

  // Guards against a stale response landing after a newer one: a slow
  // "Weitere laden" whose filter has since changed must not append its page
  // onto the new filter's list once it finally resolves. Bumped at the start
  // of every load; a response is applied only if it is still the most recent.
  const requestId = useRef(0);

  // Reset to the first page whenever a filter changes — mirrors QuizReview's
  // loadFirstPage: `limit` never exceeds PAGE_SIZE regardless of how many
  // pages were loaded before the filter changed.
  const loadFirstPage = useCallback(async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError("");
    // Cleared up front, not only on success: a filter change must drop the
    // previous filter's rows immediately, so a failed fetch leaves an empty
    // list under the error banner instead of the old filter's data sitting
    // there unlabelled. Without this, "Weitere laden" stayed clickable on
    // that stale total and appended the new filter's page 2 onto it.
    setItems([]);
    setTotal(0);
    try {
      const page = await api.listFeedback(helpfulParam, categoryParam, PAGE_SIZE, 0, user.token);
      if (id !== requestId.current) return;
      setItems(page.items);
      setTotal(page.total);
    } catch {
      if (id === requestId.current) setError("Feedback konnte nicht geladen werden. Bitte Seite neu laden.");
    } finally {
      // Guarded like the success branch above: an in-flight newer call owns
      // clearing the spinner once *it* settles. Without the guard, a stale
      // call finishing after a newer one started could flip loading off
      // while that newer request is still running.
      if (id === requestId.current) setLoading(false);
    }
  }, [helpfulFilter, categoryFilter, user.token]);

  useEffect(() => {
    void loadFirstPage();
  }, [loadFirstPage]);

  const loadMore = async () => {
    const id = ++requestId.current;
    setLoadingMore(true);
    setError("");
    try {
      const page = await api.listFeedback(helpfulParam, categoryParam, PAGE_SIZE, items.length, user.token);
      if (id !== requestId.current) return;
      setItems(prev => [...prev, ...page.items]);
      setTotal(page.total);
    } catch {
      if (id === requestId.current) setError("Weiteres Feedback konnte nicht geladen werden. Bitte erneut versuchen.");
    } finally {
      // Same guard as loadFirstPage's finally: only the still-current call
      // may clear the spinner.
      if (id === requestId.current) setLoadingMore(false);
    }
  };

  return (
    <Layout
      user={user}
      onLogout={onLogout}
      navItems={<button className="nav-item" onClick={() => navigate("/")}>Zurück zum Chat</button>}
    >
      <div style={{ flex: 1, overflowY: "auto", padding: "var(--space-4) var(--space-6)" }}>
        <div style={{ fontWeight: "var(--font-black)", fontSize: "var(--text-xl)", color: "var(--text-primary)", marginBottom: "var(--space-4)" }}>
          Feedback-Übersicht
        </div>

        {error && (
          <div role="alert" style={{
            background: "var(--red-tint)", color: "var(--red)", borderRadius: "var(--radius-sm)",
            padding: "8px 12px", fontSize: "var(--text-sm)", marginBottom: 12,
          }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, marginBottom: "var(--space-4)" }}>
          <label style={{ fontSize: "var(--text-xs)" }}>
            Bewertung{" "}
            <select
              aria-label="Bewertung filtern"
              value={helpfulFilter}
              onChange={e => setHelpfulFilter(e.target.value as "" | "true" | "false")}
            >
              <option value="">Alle</option>
              <option value="true">👍 Hilfreich</option>
              <option value="false">👎 Nicht hilfreich</option>
            </select>
          </label>
          <label style={{ fontSize: "var(--text-xs)" }}>
            Kategorie{" "}
            <select
              aria-label="Kategorie filtern"
              value={categoryFilter}
              onChange={e => setCategoryFilter(e.target.value as "" | FeedbackCategory)}
            >
              <option value="">Alle</option>
              {CATEGORY_OPTIONS.map(([value, meta]) => (
                <option key={value} value={value}>{meta.label}</option>
              ))}
            </select>
          </label>
        </div>

        {loading ? (
          <div style={{ color: "var(--text-muted)", textAlign: "center", marginTop: 40 }}>Lädt…</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontWeight: "var(--font-bold)", color: "var(--text-primary)", fontSize: "var(--text-sm)" }}>
              {total} Feedback{total === 1 ? "" : "s"}
            </div>
            {items.length === 0 && (
              <div style={{ color: "var(--text-muted)", fontSize: "var(--text-xs)" }}>Kein Feedback vorhanden.</div>
            )}
            {items.map(item => (
              <div key={item.id} className="card" style={{
                padding: "10px 14px", display: "flex", flexDirection: "column", gap: 6,
              }}>
                <div style={{ display: "flex", gap: 10, alignItems: "center", fontSize: "var(--text-sm)" }}>
                  <span>{item.helpful ? "👍" : "👎"}</span>
                  {item.category && (
                    <span className="badge badge-info" style={{ padding: "2px 6px", borderRadius: "var(--radius-sm)" }}>
                      {CATEGORY_META[item.category].label}
                    </span>
                  )}
                  <span style={{ color: "var(--text-muted)", fontSize: "var(--text-2xs)", marginLeft: "auto" }}>
                    {new Date(item.created_at).toLocaleString("de-CH")}
                  </span>
                </div>
                {item.comment && <div style={{ fontSize: "var(--text-sm)" }}>{item.comment}</div>}
              </div>
            ))}
            {items.length < total && (
              <button
                className="secondary"
                style={{ fontSize: "var(--text-xs)", alignSelf: "flex-start" }}
                disabled={loadingMore}
                onClick={loadMore}
              >
                {loadingMore ? "Lädt…" : "Weitere laden"}
              </button>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
