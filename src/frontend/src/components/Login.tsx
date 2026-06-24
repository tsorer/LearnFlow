import { useState } from "react";
import type { AuthUser } from "../types";
import { api } from "../api/client";

interface Props { onLogin: (u: AuthUser) => void; }

export default function Login({ onLogin }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const res = await api.login(email, password);
      const me = await api.me(res.access_token);
      onLogin({ ...me, role: me.role as AuthUser["role"], token: res.access_token });
    } catch {
      setError("E-Mail oder Passwort falsch.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <form onSubmit={submit} style={{
        background: "var(--card)", border: "1px solid var(--border)", borderRadius: 12,
        padding: "40px 48px", width: 360, display: "flex", flexDirection: "column", gap: 16,
      }}>
        <div style={{ fontWeight: 800, fontSize: 22, color: "var(--navy)", marginBottom: 4 }}>
          📚 LearnFlow
        </div>
        <div style={{ color: "var(--muted)", fontSize: 13, marginBottom: 8 }}>
          Melde dich mit deinem Account an.
        </div>
        {error && (
          <div style={{ background: "var(--red-lt)", color: "var(--red)", borderRadius: 6, padding: "8px 12px", fontSize: 13 }}>
            {error}
          </div>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="login-email" style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)" }}>E-MAIL</label>
          <input id="login-email" type="email" value={email} onChange={e => setEmail(e.target.value)} required autoFocus />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <label htmlFor="login-password" style={{ fontSize: 12, fontWeight: 600, color: "var(--muted)" }}>PASSWORT</label>
          <input id="login-password" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
        </div>
        <button type="submit" className="primary" disabled={busy} style={{ marginTop: 8, padding: "10px 14px" }}>
          {busy ? "Anmelden…" : "Anmelden"}
        </button>
        <div style={{ textAlign: "center", fontSize: 11, color: "var(--muted)", marginTop: 4 }}>
          Build {new Date(__BUILD_TIME__).toLocaleString("de-CH", {
            day: "2-digit", month: "2-digit", year: "numeric",
            hour: "2-digit", minute: "2-digit",
          })}
        </div>
      </form>
    </div>
  );
}
