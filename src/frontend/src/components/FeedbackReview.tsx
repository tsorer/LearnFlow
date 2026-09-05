import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { AuthUser } from "../types";
import { api, type FeedbackCategory, type FeedbackItem } from "../api/client";
import { CATEGORY_META } from "./MessageBubble";

const PAGE_SIZE = 50;

const CATEGORY_OPTIONS = Object.entries(CATEGORY_META) as [FeedbackCategory, { label: string; helpful: boolean }][];

interface Props { user: AuthUser }

export default function FeedbackReview({ user }: Props) {
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
    try {
      const page = await api.listFeedback(helpfulParam, categoryParam, PAGE_SIZE, 0, user.token);
      if (id !== requestId.current) return;
      setItems(page.items);
      setTotal(page.total);
    } catch {
      if (id === requestId.current) setError("Feedback konnte nicht geladen werden. Bitte Seite neu laden.");
    } finally {
      // Always cleared, staleness notwithstanding: this specific call is done
      // either way, and nothing else resets loading's spinner for it.
      setLoading(false);
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
      // Always cleared, staleness notwithstanding: this specific call is done
      // either way, and nothing else resets loadingMore's spinner for it.
      setLoadingMore(false);
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", flexDirection: "column" }}>
      <div style={{
        background: "var(--navy)", color: "#fff", padding: "0 24px",
        height: 52, display: "flex", alignItems: "center", justifyContent: "space-between",
        flexShrink: 0,
      }}>
        <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-.02em" }}>📚 LearnFlow · Feedback-Übersicht</div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <button className="secondary" style={{ fontSize: 12 }} onClick={() => navigate("/")}>
            Zurück zum Chat
          </button>
          <span style={{ fontSize: 12, color: "rgba(255,255,255,.5)" }}>{user.email}</span>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px" }}>
        {error && (
          <div role="alert" style={{
            background: "var(--red-lt)", color: "var(--red)", borderRadius: 8,
            padding: "8px 12px", fontSize: 13, marginBottom: 12,
          }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
          <label style={{ fontSize: 12 }}>
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
          <label style={{ fontSize: 12 }}>
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
          <div style={{ color: "var(--muted)", textAlign: "center", marginTop: 40 }}>Lädt…</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ fontWeight: 700, color: "var(--navy)", fontSize: 14 }}>
              {total} Feedback{total === 1 ? "" : "s"}
            </div>
            {items.length === 0 && (
              <div style={{ color: "var(--muted)", fontSize: 12 }}>Kein Feedback vorhanden.</div>
            )}
            {items.map(item => (
              <div
                key={item.id}
                style={{
                  border: "1px solid var(--border)", borderRadius: 8, padding: "10px 14px",
                  display: "flex", flexDirection: "column", gap: 6,
                }}
              >
                <div style={{ display: "flex", gap: 10, alignItems: "center", fontSize: 13 }}>
                  <span>{item.helpful ? "👍" : "👎"}</span>
                  {item.category && (
                    <span style={{
                      fontSize: 11, fontWeight: 600, color: "var(--navy)",
                      background: "var(--bg-alt, #f0f0f0)", borderRadius: 4, padding: "2px 6px",
                    }}>
                      {CATEGORY_META[item.category].label}
                    </span>
                  )}
                  <span style={{ color: "var(--muted)", fontSize: 11, marginLeft: "auto" }}>
                    {new Date(item.created_at).toLocaleString("de-CH")}
                  </span>
                </div>
                {item.comment && <div style={{ fontSize: 13 }}>{item.comment}</div>}
              </div>
            ))}
            {items.length < total && (
              <button
                className="secondary"
                style={{ fontSize: 12, alignSelf: "flex-start" }}
                disabled={loadingMore}
                onClick={loadMore}
              >
                {loadingMore ? "Lädt…" : "Weitere laden"}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
