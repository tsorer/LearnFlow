import type { AuthUser } from "../types";
import Layout from "./Layout";
import Upload from "./Upload";

interface Props {
  user: AuthUser;
  onLogout: () => void;
}

/** `/dokumente` — used to be a boolean toggled inside ChatView (UX pass
 *  2026-09: it is now a real route, like every other Sidebar destination). */
export default function DocumentsPage({ user, onLogout }: Props) {
  return (
    <Layout user={user} onLogout={onLogout}>
      <Upload user={user} />
    </Layout>
  );
}
