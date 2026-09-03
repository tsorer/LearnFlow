import { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import type { AuthUser, Message } from "./types";
import Login from "./components/Login";
import ChatView from "./components/ChatView";
import QuizReview from "./components/QuizReview";
import QuizRun from "./components/QuizRun";
import { ProtectedRoute, GuestRoute } from "./components/RouteGuards";
import { setUnauthorizedHandler } from "./api/client";

export default function App() {
  // JWT/User nur im Memory (ADR-002) — bewusst kein localStorage.
  const [user, setUser] = useState<AuthUser | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  // Chat-Transkript und Session-ID liegen hier statt in ChatView (T-36):
  // /quiz und /quiz-review unmounten ChatView, ein dort lokaler State wäre
  // beim Zurücknavigieren leer. US-09 verlangt die Historie für die ganze
  // Browser-Session, nicht nur während ChatView gemountet ist.
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Ein 401 auf einer authentifizierten Anfrage beendet die Sitzung. Der leere
  // User-State laesst ProtectedRoute auf /login umleiten (T-40).
  useEffect(() => {
    setUnauthorizedHandler(() => {
      setUser(null);
      setSessionExpired(true);
      setMessages([]);
      setSessionId(null);
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  const login = (u: AuthUser) => {
    setSessionExpired(false);
    setUser(u);
  };

  // Abmelden beendet die Browser-Session im Sinn von US-09 (AC 5) — die
  // Historie gehört zur angemeldeten Sitzung und darf nicht an die nächste
  // Anmeldung (ggf. ein anderes Konto) weitergereicht werden.
  const logout = () => {
    setUser(null);
    setMessages([]);
    setSessionId(null);
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
              {u => (
                <ChatView
                  user={u}
                  onLogout={logout}
                  messages={messages}
                  setMessages={setMessages}
                  sessionId={sessionId}
                  setSessionId={setSessionId}
                />
              )}
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
          path="/quiz"
          element={
            <ProtectedRoute user={user}>
              {u => <QuizRun token={u.token} />}
            </ProtectedRoute>
          }
        />
        {/* Unbekannte Pfade: auf die geschützte Wurzel, die ihrerseits zum Login leitet. */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
