import type { ReactNode } from "react";
import type { AuthUser } from "../types";
import Sidebar from "./Sidebar";

interface Props {
  user: AuthUser;
  onLogout: () => void;
  ctaSlot?: ReactNode;
  navItems?: ReactNode;
  children: ReactNode;
}

/** Replaces the four duplicated `background: var(--navy)` top bars with one
 *  left sidebar (T-58). `Login` stays outside this — it has no chrome. */
export default function Layout({ user, onLogout, ctaSlot, navItems, children }: Props) {
  return (
    <div className="app-shell">
      <Sidebar user={user} onLogout={onLogout} ctaSlot={ctaSlot}>{navItems}</Sidebar>
      <main className="app-main">{children}</main>
    </div>
  );
}
