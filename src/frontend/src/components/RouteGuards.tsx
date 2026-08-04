import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import type { AuthUser } from "../types";

/**
 * Route-Guards fuer T-08. Zentral statt inline pro Route, damit eine neue
 * geschuetzte Seite nicht versehentlich ohne Guard angelegt wird.
 */

interface ProtectedProps {
  user: AuthUser | null;
  // Render-Prop: erhaelt den garantiert vorhandenen User, spart ein `user!`.
  children: (user: AuthUser) => ReactElement;
}

/** Ohne angemeldeten User zurueck auf /login. */
export function ProtectedRoute({ user, children }: ProtectedProps) {
  return user ? children(user) : <Navigate to="/login" replace />;
}

interface GuestProps {
  user: AuthUser | null;
  children: ReactElement;
}

/** Nur fuer Nicht-Angemeldete; wer eingeloggt ist, gehoert auf die Startseite. */
export function GuestRoute({ user, children }: GuestProps) {
  return user ? <Navigate to="/" replace /> : children;
}
