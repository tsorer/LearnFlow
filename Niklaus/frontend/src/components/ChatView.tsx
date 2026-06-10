import { useState, useRef, useEffect } from "react";
import type { AuthUser, Message } from "../types";
import { api } from "../api/client";
import Upload from "./Upload";
import MessageBubble from "./MessageBubble";

interface Props { user: AuthUser; onLogout: () => void; }

export default function ChatView({ user, onLogout }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const canUpload = user.role === "knowledge_owner" || user.role === "admin";

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    setMessages(prev => [...prev, { role: "user", content: q }]);

    try {
      const res = await api.query(q, sessionId, user.token);
      setSessionId(res.session_id);
      setMessages(prev => [...prev, {
        role: "assistant",
        content: res.message ?? "Ich weiss es nicht.",
        answer_id: res.answer_id,
        suppressed: res.suppressed,
        citations: res.citations,
        confidence: res.confidence,
      }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Fehler beim Abrufen der Antwort. Bitte versuche es erneut.",
        suppressed: true,
      }]);
    } finally {
      setBusy(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const newChat = () => { setMessages([]); setSessionId(null); };

  return (
    <div style={{ display: "flex", height: "100vh", flexDirection: "column" }}>
      {/* Header */}
      <div style={{
        background: "var(--navy)", color: "#fff", padding: "0 24px",
        height: 52, display: "flex", alignItems: "center", justifyContent: "space-between",
        flexShrink: 0,
      }}>
        <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: "-.02em" }}>📚 LearnFlow</div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {canUpload && (
            <button className="secondary" style={{ fontSize: 12 }} onClick={() => setShowUpload(v => !v)}>
              {showUpload ? "Chat" : "Dokumente"}
            </button>
          )}
          <button className="secondary" style={{ fontSize: 12 }} onClick={newChat}>Neuer Chat</button>
          <span style={{ fontSize: 12, color: "rgba(255,255,255,.5)" }}>{user.email}</span>
          <button className="secondary" style={{ fontSize: 12 }} onClick={onLogout}>Abmelden</button>
        </div>
      </div>

      {showUpload && canUpload ? (
        <Upload user={user} onClose={() => setShowUpload(false)} />
      ) : (
        <>
          {/* Messages */}
          <div style={{ flex: 1, overflowY: "auto", padding: "24px 0" }}>
            <div style={{ maxWidth: 760, margin: "0 auto", padding: "0 24px", display: "flex", flexDirection: "column", gap: 16 }}>
              {messages.length === 0 && (
                <div style={{ textAlign: "center", color: "var(--muted)", marginTop: 80 }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>📚</div>
                  <div style={{ fontWeight: 700, fontSize: 18, color: "var(--navy)" }}>Stelle eine Frage</div>
                  <div style={{ fontSize: 13, marginTop: 6 }}>Ich beantworte sie auf Basis der Dokumente im Korpus.</div>
                </div>
              )}
              {messages.map((m, i) => <MessageBubble key={i} message={m} token={user.token} />)}
              {busy && (
                <div style={{ color: "var(--muted)", fontSize: 13, padding: "8px 0" }}>
                  Suche im Korpus…
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          {/* Input */}
          <div style={{
            borderTop: "1px solid var(--border)", padding: "16px 24px",
            background: "var(--card)", flexShrink: 0,
          }}>
            <div style={{ maxWidth: 760, margin: "0 auto", display: "flex", gap: 10 }}>
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Frage stellen… (Enter zum Senden)"
                disabled={busy}
                rows={2}
                style={{ resize: "none", flex: 1 }}
              />
              <button className="primary" onClick={send} disabled={busy || !input.trim()}
                style={{ alignSelf: "flex-end", padding: "10px 18px" }}>
                Senden
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
