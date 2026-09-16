import { useLocation, useNavigate } from "react-router-dom";
import type { AuthUser } from "../types";
import { getRoleFlags } from "../roles";
import type { SidebarPanelState } from "./Layout";

interface Props extends SidebarPanelState {
  user: AuthUser;
  onLogout: () => void;
}

/**
 * The persistent left navigation (T-58): one consistent set of destinations
 * on every authenticated page, visible or not based only on role — never on
 * which page happens to be open. "KI-Chat"/"Quiz starten"/"Quiz-Dashboard"/
 * "Feedback" are real routes. "Dokumente"/"Parameter" are not (they toggle a
 * view inside ChatView, lifted to App so the Sidebar can reach them from any
 * page too) — clicking either from elsewhere navigates to "/" and opens it;
 * clicking from ChatView itself toggles it, same as before.
 *
 * Mutating actions ("Neuer Chat", "Fragen generieren") are not nav items —
 * they live next to each page's own title as an action button, not here.
 */
export default function Sidebar({ user, onLogout, showUpload, setShowUpload, showParams, setShowParams }: Props) {
  const navigate = useNavigate();
  const location = useLocation();
  const { canUpload, canReview, canViewFeedback, isAdmin } = getRoleFlags(user);
  const initials = user.email.slice(0, 2).toUpperCase();
  const onChat = location.pathname === "/";
  const isActive = (path: string) => location.pathname === path;

  const docsActive = onChat && showUpload;
  const openDocuments = () => {
    if (onChat) {
      setShowUpload(v => !v);
    } else {
      setShowUpload(true);
      navigate("/");
    }
  };

  const paramsActive = onChat && !showUpload && showParams;
  const openParams = () => {
    if (onChat && !showUpload) {
      setShowParams(v => !v);
    } else {
      setShowParams(true);
      setShowUpload(false);
      navigate("/");
    }
  };

  const hasVerwaltung = canUpload || canReview || canViewFeedback || isAdmin;

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
        {canUpload && (
          <button className={`nav-item${docsActive ? " active" : ""}`} onClick={openDocuments}>
            {docsActive ? "Chat" : "Dokumente"}
          </button>
        )}
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
        {isAdmin && (
          <button className={`nav-item${paramsActive ? " active" : ""}`} onClick={openParams}>
            {paramsActive ? "⚙ Parameter ▲" : "⚙ Parameter ▼"}
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
