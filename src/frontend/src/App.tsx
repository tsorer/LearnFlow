import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import type { AuthUser } from "./types";
import Login from "./components/Login";
import ChatView from "./components/ChatView";
import QuizReview from "./components/QuizReview";
import FeedbackReview from "./components/FeedbackReview";
import { ProtectedRoute, GuestRoute } from "./components/RouteGuards";
import { setUnauthorizedHandler } from "./api/client";

export default function App() {
  // JWT/User nur im Memory (ADR-002) — bewusst kein localStorage.
  const [user, setUser] = useState<AuthUser | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  // Ein 401 auf einer authentifizierten Anfrage beendet die Sitzung. Der leere
  // User-State laesst ProtectedRoute auf /login umleiten (T-40).
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setSessionExpired(true);
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const login = (u: AuthUser) => {
    setSessionExpired(false);
    setUser(u);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <GuestRoute user={user}>
              <Login onLogin={login} sessionExpired={sessionExpired} />
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
        <Route
          path="/quiz-review"
          element={
            <ProtectedRoute user={user} roles={["knowledge_owner", "admin"]}>
              {u => <QuizReview user={u} />}
            </ProtectedRoute>
          }
        />
        <Route
          path="/feedback"
          element={
            <ProtectedRoute user={user} roles={["knowledge_owner", "admin"]}>
              {u => <FeedbackReview user={u} />}
            </ProtectedRoute>
          }
        />
        {/* Unbekannte Pfade: auf die geschützte Wurzel, die ihrerseits zum Login leitet. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
