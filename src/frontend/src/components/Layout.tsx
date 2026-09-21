import { useState, type ReactNode } from "react";
import type { AuthUser } from "../types";
import Sidebar from "./Sidebar";

interface Props {
  user: AuthUser;
  onLogout: () => void;
  children: ReactNode;
}

/** Replaces the four duplicated `background: var(--navy)` top bars with one
 *  left sidebar (T-58). `Login` stays outside this — it has no chrome.
 *
 *  Also owns the off-canvas toggle for narrow viewports (UX pass 2026-09),
 *  where the sidebar's fixed 236px would otherwise eat most of the screen. */
export default function Layout({ user, onLogout, children }: Props) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="app-shell">
      <button
        type="button"
        className="mobile-nav-toggle"
        aria-label={mobileNavOpen ? "Navigation schliessen" : "Navigation öffnen"}
        aria-expanded={mobileNavOpen}
        onClick={() => setMobileNavOpen(v => !v)}
      >
        <span aria-hidden="true">{mobileNavOpen ? "✕" : "☰"}</span>
      </button>
      {mobileNavOpen && <div className="sidebar-backdrop" onClick={() => setMobileNavOpen(false)} />}
      <Sidebar
        user={user}
        onLogout={onLogout}
        mobileOpen={mobileNavOpen}
        onNavigate={() => setMobileNavOpen(false)}
      />
      <main className="app-main">{children}</main>
    </div>
  );
}
