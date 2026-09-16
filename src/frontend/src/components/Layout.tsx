import type { Dispatch, ReactNode, SetStateAction } from "react";
import type { AuthUser } from "../types";
import Sidebar from "./Sidebar";

/** The "Dokumente"/"Parameter" view state, lifted to App.tsx so the Sidebar
 *  can open them from any page (T-58 review) — every view that renders
 *  `Layout` threads these straight through without reading them itself
 *  (only `ChatView` actually does). */
export interface SidebarPanelState {
  showUpload: boolean;
  setShowUpload: Dispatch<SetStateAction<boolean>>;
  showParams: boolean;
  setShowParams: Dispatch<SetStateAction<boolean>>;
}

interface Props extends SidebarPanelState {
  user: AuthUser;
  onLogout: () => void;
  children: ReactNode;
}

/** Replaces the four duplicated `background: var(--navy)` top bars with one
 *  left sidebar (T-58). `Login` stays outside this — it has no chrome. */
export default function Layout({ user, onLogout, showUpload, setShowUpload, showParams, setShowParams, children }: Props) {
  return (
    <div className="app-shell">
      <Sidebar
        user={user}
        onLogout={onLogout}
        showUpload={showUpload}
        setShowUpload={setShowUpload}
        showParams={showParams}
        setShowParams={setShowParams}
      />
      <main className="app-main">{children}</main>
    </div>
  );
}
