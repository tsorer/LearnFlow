import type { ReactNode } from "react";
import type { AuthUser } from "../types";

interface Props {
  user: AuthUser;
  onLogout: () => void;
  /** ChatView's "Neuer Chat" CTA — undefined on every other view. */
  ctaSlot?: ReactNode;
  /**
   * The nav buttons for this page, assembled by the caller so the Sidebar
   * shows exactly what each view's top bar used to show (same buttons, same
   * role conditions) — the Sidebar itself carries no per-page visibility
   * logic of its own.
   */
  children?: ReactNode;
}

/**
 * Purely presentational shell (T-58): brand mark, an optional CTA, the
 * caller-assembled nav buttons, and a footer with the signed-in user.
 *
 * The footer's e-mail/Abmelden are shown on every page, including the three
 * (QuizReview/QuizRun/FeedbackReview) that had neither in their old top bar —
 * a deliberate, documented exception to "no new reachability" (see PR
 * description): logout is not a functional escalation, just a consequence of
 * having one persistent shell instead of four independent top bars.
 */
export default function Sidebar({ user, onLogout, ctaSlot, children }: Props) {
  const initials = user.email.slice(0, 2).toUpperCase();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span aria-hidden="true">📚</span> LearnFlow
      </div>

      {ctaSlot}

      <nav style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {children}
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
