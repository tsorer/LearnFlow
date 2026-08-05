import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import type { AuthUser } from "./types";
import Login from "./components/Login";
import ChatView from "./components/ChatView";
import { ProtectedRoute, GuestRoute } from "./components/RouteGuards";

export default function App() {
  // JWT/User nur im Memory (ADR-002) — bewusst kein localStorage.
  const [user, setUser] = useState<AuthUser | null>(null);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestRoute user={user}>
              <Login onLogin={setUser} />
            </GuestRoute>
          }
        />
        <Route
          path="/"
          element={
            <ProtectedRoute user={user}>
              {u => <ChatView user={u} onLogout={() => setUser(null)} />}
            </ProtectedRoute>
          }
        />
        {/* Unbekannte Pfade: auf die geschützte Wurzel, die ihrerseits zum Login leitet. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
