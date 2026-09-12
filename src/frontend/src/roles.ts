import type { AuthUser } from "./types";

export interface RoleFlags {
  canUpload: boolean;
  canReview: boolean;
  canViewFeedback: boolean;
  isAdmin: boolean;
}

/**
 * Same three role checks ChatView used to compute locally (T-35/T-32),
 * centralised so the Sidebar's persistent nav items and ChatView's local
 * toggles read one definition instead of two copies drifting apart.
 * RouteGuards.tsx remains the actual enforcement; this only decides what
 * to show.
 */
export function getRoleFlags(user: AuthUser): RoleFlags {
  const isOwnerOrAdmin = user.role === "knowledge_owner" || user.role === "admin";
  return {
    canUpload: isOwnerOrAdmin,
    canReview: isOwnerOrAdmin,
    canViewFeedback: isOwnerOrAdmin,
    isAdmin: user.role === "admin",
  };
}
