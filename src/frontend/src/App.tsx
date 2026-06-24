import { useState } from "react";
import type { AuthUser } from "./types";
import Login from "./components/Login";
import ChatView from "./components/ChatView";

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(null);

  if (!user) return <Login onLogin={setUser} />;
  return <ChatView user={user} onLogout={() => setUser(null)} />;
}
