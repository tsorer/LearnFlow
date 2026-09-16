import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { AuthUser } from "../types";
import { getRoleFlags } from "../roles";

interface CommandItem {
  id: string;
  label: string;
  run: () => void;
}

interface Props {
  open: boolean;
  onClose: () => void;
  user: AuthUser;
  onLogout: () => void;
}

/**
 * Strg/Cmd+K quick-nav (UX pass 2026-09). Destinations only — role-gated the
 * same way the Sidebar is, so it never offers a page RouteGuards would bounce
 * the user straight back out of.
 */
export default function CommandPalette({ open, onClose, user, onLogout }: Props) {
  const navigate = useNavigate();
  const { canUpload, canReview, canViewFeedback, isAdmin } = getRoleFlags(user);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const items: CommandItem[] = useMemo(() => {
    const list: CommandItem[] = [
      { id: "chat", label: "KI-Chat", run: () => navigate("/") },
      { id: "quiz", label: "Quiz starten", run: () => navigate("/quiz") },
    ];
    if (canUpload) list.push({ id: "docs", label: "Dokumente", run: () => navigate("/dokumente") });
    if (canReview) list.push({ id: "quiz-review", label: "Quiz-Dashboard", run: () => navigate("/quiz-review") });
    if (canViewFeedback) list.push({ id: "feedback", label: "Feedback", run: () => navigate("/feedback") });
    if (isAdmin) list.push({ id: "params", label: "Parameter", run: () => navigate("/parameter") });
    list.push({ id: "logout", label: "Abmelden", run: onLogout });
    return list;
  }, [canUpload, canReview, canViewFeedback, isAdmin, navigate, onLogout]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? items.filter(i => i.label.toLowerCase().includes(q)) : items;
  }, [items, query]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActiveIndex(0);
    const id = requestAnimationFrame(() => inputRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [open]);

  // A query that removes the row under the current selection must not leave
  // the highlight on a row that no longer exists.
  useEffect(() => { setActiveIndex(0); }, [query]);

  if (!open) return null;

  const activate = (item: CommandItem | undefined) => {
    if (!item) return;
    item.run();
    onClose();
  };

  return (
    <div className="cmdk-backdrop" onClick={onClose}>
      <div className="cmdk-panel" role="dialog" aria-modal="true" aria-label="Befehle" onClick={e => e.stopPropagation()}>
        <input
          ref={inputRef}
          className="cmdk-input"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Wohin? (Chat, Quiz, Dokumente, Parameter …)"
          aria-label="Befehle durchsuchen"
          role="combobox"
          aria-expanded="true"
          aria-controls="cmdk-listbox"
          onKeyDown={e => {
            if (e.key === "ArrowDown") { e.preventDefault(); setActiveIndex(i => Math.min(i + 1, filtered.length - 1)); }
            else if (e.key === "ArrowUp") { e.preventDefault(); setActiveIndex(i => Math.max(i - 1, 0)); }
            else if (e.key === "Enter") { e.preventDefault(); activate(filtered[activeIndex]); }
            else if (e.key === "Escape") { e.preventDefault(); onClose(); }
          }}
        />
        <div id="cmdk-listbox" className="cmdk-list" role="listbox">
          {filtered.length === 0 && <div className="cmdk-empty">Keine Treffer.</div>}
          {filtered.map((item, i) => (
            <button
              key={item.id}
              type="button"
              role="option"
              aria-selected={i === activeIndex}
              className={`cmdk-item${i === activeIndex ? " active" : ""}`}
              onMouseEnter={() => setActiveIndex(i)}
              onClick={() => activate(item)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
