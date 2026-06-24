import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import type { AuthUser } from "./types";
import Login from "./components/Login";
import ChatView from "./components/ChatView";

export default function App() {
  // JWT/User nur im Memory (ADR-002) — bewusst kein localStorage.
  const [user, setUser] = useState<AuthUser | null>(null);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={user ? <Navigate to="/" replace /> : <Login onLogin={setUser} />}
        />
        <Route
          path="/"
          element={
            user
              ? <ChatView user={user} onLogout={() => setUser(null)} />
              : <Navigate to="/login" replace />
          }
        />
        {/* Unbekannte Pfade: auf die geschützte Wurzel, die ihrerseits zum Login leitet. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
