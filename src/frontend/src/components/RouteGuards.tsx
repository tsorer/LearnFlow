import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import type { AuthUser, Role } from "../types";

/**
 * Route-Guards fuer T-08. Zentral statt inline pro Route, damit eine neue
 * geschuetzte Seite nicht versehentlich ohne Guard angelegt wird.
 */

interface ProtectedProps {
  user: AuthUser | null;
  // Ohne Angabe darf jede angemeldete Rolle rein (Status quo vor T-35).
  roles?: Role[];
  // Render-Prop: erhaelt den garantiert vorhandenen User, spart ein `user!`.
  children: (user: AuthUser) => ReactElement;
}

/**
 * Ohne angemeldeten User zurueck auf /login. Mit `roles` zusaetzlich auf `/`,
 * wenn die Rolle nicht passt -- der User ist angemeldet, /login waere falsch,
 * und eine eigene Fehlerseite fuer einen Fall, den die Navigation nirgends
 * anbietet, waere Ballast (T-35, /quiz-review).
 */
export function ProtectedRoute({ user, roles, children }: ProtectedProps) {
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children(user);
}

interface GuestProps {
  user: AuthUser | null;
  children: ReactElement;
}

/** Nur fuer Nicht-Angemeldete; wer eingeloggt ist, gehoert auf die Startseite. */
export function GuestRoute({ user, children }: GuestProps) {
  return user ? <Navigate to="/" replace /> : children;
}
