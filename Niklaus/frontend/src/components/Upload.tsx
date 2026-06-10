import { useState, useEffect } from "react";
import type { AuthUser, Document } from "../types";
import { api } from "../api/client";

interface Props { user: AuthUser; onClose: () => void; }

const statusColor = { pending: "var(--muted)", processing: "var(--amber)", available: "var(--green)", failed: "var(--red)" };
const statusLabel = { pending: "Ausstehend", processing: "Verarbeitung…", available: "Verfügbar", failed: "Fehler" };

export default function Upload({ user, onClose }: Props) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const load = () => api.listDocuments(user.token).then(setDocs).catch(() => {});
  useEffect(() => { load(); }, []);

  // Poll status for processing documents
  useEffect(() => {
    const processing = docs.some(d => d.status === "pending" || d.status === "processing");
    if (!processing) return;
    const t = setTimeout(load, 3000);
    return () => clearTimeout(t);
  }, [docs]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    setUploading(true); setError("");
    try {
      for (const file of files) {
        await api.uploadDocument(file, "default", user.token);
      }
      await load();
    } catch (err: any) {
      setError(err.message ?? "Upload fehlgeschlagen");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (id: string) => {
    await api.deleteDocument(id, user.token).catch(() => {});
    setDocs(prev => prev.filter(d => d.id !== id));
  };

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: 32 }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: "var(--navy)" }}>Dokumente</h2>
          <button className="secondary" onClick={onClose}>← Zurück zum Chat</button>
        </div>

        {/* Upload area */}
        <label style={{
          display: "block", border: "2px dashed var(--border)", borderRadius: 10,
          padding: "24px 32px", textAlign: "center", cursor: "pointer",
          background: uploading ? "var(--blue-lt)" : "var(--card)", marginBottom: 24,
          transition: "background 0.15s",
        }}>
          <div style={{ fontSize: 24, marginBottom: 8 }}>📄</div>
          <div style={{ fontWeight: 700, color: "var(--navy)" }}>
            {uploading ? "Wird hochgeladen…" : "PDF, DOCX oder MD hochladen"}
          </div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>Max. 10 MB pro Datei</div>
          <input type="file" accept=".pdf,.docx,.md,.txt" multiple hidden onChange={handleUpload} disabled={uploading} />
        </label>

        {error && (
          <div style={{ background: "var(--red-lt)", color: "var(--red)", borderRadius: 8, padding: "8px 14px", marginBottom: 16, fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* Document list */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {docs.length === 0 && (
            <div style={{ color: "var(--muted)", fontSize: 13, textAlign: "center", padding: 24 }}>
              Noch keine Dokumente im Korpus.
            </div>
          )}
          {docs.map(d => (
            <div key={d.id} style={{
              background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8,
              padding: "10px 14px", display: "flex", alignItems: "center", gap: 12,
            }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{d.filename}</div>
                <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                  {d.chunk_count} Chunks · Bereich: {d.area}
                </div>
              </div>
              <span style={{
                fontSize: 11, fontWeight: 700, color: statusColor[d.status],
                background: d.status === "available" ? "var(--green-lt)" : "transparent",
                borderRadius: 30, padding: "2px 8px",
              }}>
                {statusLabel[d.status]}
              </span>
              <button className="danger" style={{ fontSize: 12, padding: "4px 10px" }}
                onClick={() => handleDelete(d.id)}>
                Löschen
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
