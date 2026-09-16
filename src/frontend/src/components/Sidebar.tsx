import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { AuthUser } from "../types";
import { getRoleFlags } from "../roles";

interface Props {
  user: AuthUser;
  onLogout: () => void;
  /** ChatView's "Dokumente"/"Chat" toggle — a local view-mode switch, not a
   *  route, so it stays ChatView-only rather than becoming a nav item here.
   *  Grouped under "Verwaltung". */
  workspaceExtra?: ReactNode;
  /** ChatView's "⚙ Parameter ▲/▼" toggle — same reasoning as workspaceExtra,
   *  same group. */
  adminExtra?: ReactNode;
}

/**
 * The persistent left navigation (T-58): one consistent set of destinations
 * on every authenticated page, rather than each page only showing what its
 * old top bar happened to show. "KI-Chat"/"Quiz starten"/"Quiz-Dashboard"/
 * "Feedback" are real routes, so they are reachable and highlighted the same
 * way regardless of where the user currently is — the inconsistent,
 * page-dependent menu this replaces was itself a bug (T-58 follow-up).
 *
 * Mutating actions ("Neuer Chat", "Fragen generieren") are not nav items —
 * they live next to each page's own title as an action button, not here.
 */
export default function Sidebar({ user, onLogout, workspaceExtra, adminExtra }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const { canReview, canViewFeedback } = getRoleFlags(user);
  const initials = user.email.slice(0, 2).toUpperCase();
  const isActive = (path: string) => location.pathname === path;
  const hasVerwaltung = Boolean(workspaceExtra) || canReview || canViewFeedback || Boolean(adminExtra);

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span aria-hidden="true">📚</span> LearnFlow
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <div className="sidebar-group-label">Lernen</div>
        <button className={`nav-item${isActive("/") ? " active" : ""}`} onClick={() => navigate("/")}>
          KI-Chat
        </button>
        <button className={`nav-item${isActive("/quiz") ? " active" : ""}`} onClick={() => navigate("/quiz")}>
          Quiz starten
        </button>

        {/* Only shown with something under it — an empty label directly
            above the footer would read as if it belonged to nothing. */}
        {hasVerwaltung && <div className="sidebar-group-label">Verwaltung</div>}
        {workspaceExtra}
        {canReview && (
          <button className={`nav-item${isActive("/quiz-review") ? " active" : ""}`} onClick={() => navigate("/quiz-review")}>
            Quiz-Dashboard
          </button>
        )}
        {canViewFeedback && (
          <button className={`nav-item${isActive("/feedback") ? " active" : ""}`} onClick={() => navigate("/feedback")}>
            Feedback
          </button>
        )}
        {adminExtra}
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
