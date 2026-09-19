import { useEffect, useState, type ReactNode } from "react";
import type { AuthUser } from "../types";
import Sidebar from "./Sidebar";
import CommandPalette from "./CommandPalette";

interface Props {
  user: AuthUser;
  onLogout: () => void;
  children: ReactNode;
}

/** Replaces the four duplicated `background: var(--navy)` top bars with one
 *  left sidebar (T-58). `Login` stays outside this — it has no chrome.
 *
 *  Also owns the two pieces of chrome that sit above every page rather than
 *  belonging to one (UX pass 2026-09): the off-canvas toggle for narrow
 *  viewports, where the sidebar's fixed 236px would otherwise eat most of the
 *  screen, and the Strg/Cmd+K command palette. */
export default function Layout({ user, onLogout, children }: Props) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(v => !v);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

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
        onOpenSearch={() => setPaletteOpen(true)}
      />
      <main className="app-main">{children}</main>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} user={user} onLogout={onLogout} />
    </div>
  );
}
