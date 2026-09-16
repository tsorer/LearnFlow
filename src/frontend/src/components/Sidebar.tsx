import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import type { AuthUser } from "../types";
import { getRoleFlags } from "../roles";

interface Props {
  user: AuthUser;
  onLogout: () => void;
  /** Page-specific primary action (ChatView's "Neuer Chat", QuizReview's
   *  "Fragen generieren") — undefined where a page has none. Rendered after
   *  the nav items, before the footer. */
  ctaSlot?: ReactNode;
  /** ChatView's "Dokumente"/"Chat" toggle — a local view-mode switch, not a
   *  route, so it stays ChatView-only rather than becoming a nav item here. */
  workspaceExtra?: ReactNode;
  /** ChatView's "⚙ Parameter ▲/▼" toggle — same reasoning as workspaceExtra. */
  adminExtra?: ReactNode;
}

/**
 * The persistent left navigation (T-58): one consistent set of destinations
 * on every authenticated page, rather than each page only showing what its
 * old top bar happened to show. "KI-Chat"/"Quiz starten"/"Quiz-Dashboard"/
 * "Feedback" are real routes, so they are reachable and highlighted the same
 * way regardless of where the user currently is — the inconsistent,
 * page-dependent menu this replaces was itself the bug (T-58 follow-up).
 */
export default function Sidebar({ user, onLogout, ctaSlot, workspaceExtra, adminExtra }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const { canReview, canViewFeedback } = getRoleFlags(user);
  const initials = user.email.slice(0, 2).toUpperCase();
  const isActive = (path: string) => location.pathname === path;

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span aria-hidden="true">📚</span> LearnFlow
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        <div className="sidebar-group-label">Arbeitsbereich</div>
        <button className={`nav-item${isActive("/") ? " active" : ""}`} onClick={() => navigate("/")}>
          KI-Chat
        </button>
        {workspaceExtra}

        <div className="sidebar-group-label">Lernen</div>
        <button className={`nav-item${isActive("/quiz") ? " active" : ""}`} onClick={() => navigate("/quiz")}>
          Quiz starten
        </button>
        {canReview && (
          <button className={`nav-item${isActive("/quiz-review") ? " active" : ""}`} onClick={() => navigate("/quiz-review")}>
            Quiz-Dashboard
          </button>
        )}

        {/* Only shown with something under it — an empty label right above
            ctaSlot would read as if the CTA belonged to this group (learner
            role: no Feedback, no adminExtra). */}
        {(canViewFeedback || adminExtra) && <div className="sidebar-group-label">Verwaltung</div>}
        {canViewFeedback && (
          <button className={`nav-item${isActive("/feedback") ? " active" : ""}`} onClick={() => navigate("/feedback")}>
            Feedback
          </button>
        )}
        {adminExtra}
      </nav>

      {ctaSlot}

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
