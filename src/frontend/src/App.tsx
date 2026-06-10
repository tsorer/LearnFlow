import { useState, useEffect } from "react";
import type { AuthUser } from "./types";
import { api } from "./api/client";
import Login from "./components/Login";
import ChatView from "./components/ChatView";

const TOKEN_KEY = "lf_token";

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) { setLoading(false); return; }
    api.me(token)
      .then((me) => setUser({ ...me, role: me.role as AuthUser["role"], token }))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false));
  }, []);

  const handleLogin = (u: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, u.token);
    setUser(u);
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  };

  if (loading) return <div style={{ padding: 32, color: "var(--muted)" }}>Laden…</div>;
  if (!user) return <Login onLogin={handleLogin} />;
  return <ChatView user={user} onLogout={handleLogout} />;
}
