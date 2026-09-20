import type { AuthUser } from "./types";

export interface RoleFlags {
  canUpload: boolean;
  canReview: boolean;
  canViewFeedback: boolean;
  isAdmin: boolean;
}

/**
 * Same role checks ChatView used to compute locally (T-35/T-32),
 * centralised so the Sidebar's persistent nav items read one definition
 * instead of copies drifting apart. RouteGuards.tsx remains the actual
 * enforcement; this only decides what to show.
 *
 * canUpload / canReview / canViewFeedback are deliberately three separate
 * expressions even though they are identical today: they are three separate
 * permissions (T-32 opens feedback to learners), and one shared boolean would
 * silently move the other two along with it.
 */
export function getRoleFlags(user: AuthUser): RoleFlags {
  return {
    canUpload: user.role === "knowledge_owner" || user.role === "admin",
    canReview: user.role === "knowledge_owner" || user.role === "admin",
    canViewFeedback: user.role === "knowledge_owner" || user.role === "admin",
    isAdmin: user.role === "admin",
  };
}
