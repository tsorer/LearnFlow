import { useLocation, useNavigate } from "react-router-dom";
import type { AuthUser } from "../types";
import { getRoleFlags } from "../roles";

interface Props {
  user: AuthUser;
  onLogout: () => void;
  mobileOpen: boolean;
  // Closes the off-canvas drawer after a destination is picked — without it a
  // nav click on a narrow viewport lands on the new page with the drawer
  // still covering it.
  onNavigate: () => void;
}

/**
 * The persistent left navigation (T-58): one consistent set of destinations
 * on every authenticated page, visible or not based only on role — never on
 * which page happens to be open. Every item below, including "Dokumente" and
 * "Parameter", is a real route (UX pass 2026-09) — they used to be booleans
 * toggling a panel inside ChatView, which meant a page had no URL, no
 * deep link, and — because `isActive("/")` and the toggle could both be true
 * at once — could show two nav items as "active" simultaneously.
 *
 * Mutating actions ("Neuer Chat", "Fragen generieren") are not nav items —
 * they live next to each page's own title as an action button, not here.
 */
export default function Sidebar({ user, onLogout, mobileOpen, onNavigate }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const { canUpload, canReview, canViewFeedback, isAdmin } = getRoleFlags(user);
  const initials = user.email.slice(0, 2).toUpperCase();
  const isActive = (path: string) => location.pathname === path;

  const go = (path: string) => {
    navigate(path);
    onNavigate();
  };

  const hasVerwaltung = canUpload || canReview || canViewFeedback || isAdmin;

  return (
    <aside className={`sidebar${mobileOpen ? " open" : ""}`}>
      <div className="sidebar-brand">
        <span aria-hidden="true">📚</span> LearnFlow
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <div className="sidebar-group-label">Lernen</div>
        <button className={`nav-item${isActive("/") ? " active" : ""}`} aria-current={isActive("/") ? "page" : undefined} onClick={() => go("/")}>
          KI-Chat
        </button>
        <button className={`nav-item${isActive("/quiz") ? " active" : ""}`} aria-current={isActive("/quiz") ? "page" : undefined} onClick={() => go("/quiz")}>
          Quiz starten
        </button>

        {/* Only shown with something under it — an empty label directly
            above the footer would read as if it belonged to nothing. */}
        {hasVerwaltung && <div className="sidebar-group-label">Verwaltung</div>}
        {canUpload && (
          <button className={`nav-item${isActive("/dokumente") ? " active" : ""}`} aria-current={isActive("/dokumente") ? "page" : undefined} onClick={() => go("/dokumente")}>
            Dokumente
          </button>
        )}
        {canReview && (
          <button className={`nav-item${isActive("/quiz-review") ? " active" : ""}`} aria-current={isActive("/quiz-review") ? "page" : undefined} onClick={() => go("/quiz-review")}>
            Quiz-Dashboard
          </button>
        )}
        {canViewFeedback && (
          <button className={`nav-item${isActive("/feedback") ? " active" : ""}`} aria-current={isActive("/feedback") ? "page" : undefined} onClick={() => go("/feedback")}>
            Feedback
          </button>
        )}
        {isAdmin && (
          <button className={`nav-item${isActive("/parameter") ? " active" : ""}`} aria-current={isActive("/parameter") ? "page" : undefined} onClick={() => go("/parameter")}>
            Parameter
          </button>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-user-row">
          <div className="sidebar-user-avatar">{initials}</div>
          <div className="sidebar-user-meta">
            <div className="sidebar-user-email">{user.email}</div>
            <button className="sidebar-logout" onClick={onLogout}>Abmelden</button>
          </div>
        </div>
      </div>
    </aside>
  );
}
