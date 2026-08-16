import { useState, useEffect, useRef } from "react";
import type { AuthUser, Document } from "../types";
import { api } from "../api/client";

interface Props { user: AuthUser; onClose: () => void; }

const statusColor = { pending: "var(--muted)", processing: "var(--amber)", available: "var(--green)", failed: "var(--red)" };
const statusLabel = { pending: "Ausstehend", processing: "Verarbeitung…", available: "Verfügbar", failed: "Fehler" };

const POLL_INTERVAL_MS = 3000;

// Both mirror app/routers/documents.py. Checking here as well is not redundant:
// nginx caps the request body at 11 MB, so a file well over the limit is cut
// off by the proxy and comes back as an HTML 413 instead of the JSON error the
// API would send — the user would see markup. The `accept` attribute is no
// substitute either: it filters the file picker, but not what gets dropped.
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024; // ADR-003
export const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".md"];

/**
 * The reason this file cannot be uploaded, or null if it can.
 *
 * Format is checked before size, in the same order as the API (415 before
 * 413): a file that violates both must not be rejected here for one reason and
 * there for the other.
 */
export function validateFile(file: File): string | null {
  const dot = file.name.lastIndexOf(".");
  const ext = dot === -1 ? "" : file.name.slice(dot).toLowerCase();
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `${file.name}: nicht unterstütztes Format (erlaubt: PDF, DOCX, MD)`;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    return `${file.name}: ${(file.size / 1024 / 1024).toFixed(1)} MB überschreiten das Limit von 10 MB`;
  }
  return null;
}

export default function Upload({ user, onClose }: Props) {
  const [docs, setDocs] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [dragging, setDragging] = useState(false);

  // Only the newest writer may set `docs`. Four of them race: the initial
  // effect, the poll chain, the reload after an upload and the optimistic
  // removal on delete. Chaining the poll serialises it against itself but not
  // against the others, and a response that started earlier and lands later
  // would overwrite a newer list — an uploaded document disappears again, a
  // finished one flips back to "Verarbeitung…", a deleted one reappears.
  const writer = useRef(0);

  const load = () => {
    const seq = ++writer.current;
    return api
      .listDocuments(user.token)
      .then(next => {
        if (seq === writer.current) setDocs(next);
      })
      .catch(() => {});
  };
  useEffect(() => { load(); }, []);

  // Poll while the worker still has something in flight. Keyed off the boolean,
  // not off `docs`: a reload that fails leaves `docs` identical, and an effect
  // depending on it would never re-run — one network blip and the document
  // would sit on "Verarbeitung…" forever.
  //
  // Chained timeouts rather than setInterval: the next reload is scheduled only
  // once the previous one has settled, so a response slower than the interval
  // cannot overlap the next request and land out of order — an older
  // "processing" answer overtaking a newer "available" one would flip a
  // finished document back. Re-armed in finally, so a failure keeps it going.
  const inFlight = docs.some(d => d.status === "pending" || d.status === "processing");
  useEffect(() => {
    if (!inFlight) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const schedule = () => {
      timer = setTimeout(() => {
        void load().finally(() => {
          if (!cancelled) schedule();
        });
      }, POLL_INTERVAL_MS);
    };
    schedule();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [inFlight]);

  // A file dropped beside the zone is opened by the browser, which navigates
  // away from the SPA — and the JWT lives in memory only (ADR-002), so that
  // ends the session silently. Only the zone's own handler may accept a drop.
  useEffect(() => {
    const swallow = (e: DragEvent) => e.preventDefault();
    window.addEventListener("dragover", swallow);
    window.addEventListener("drop", swallow);
    return () => {
      window.removeEventListener("dragover", swallow);
      window.removeEventListener("drop", swallow);
    };
  }, []);

  const handleFiles = async (files: File[]) => {
    if (!files.length) return;
    const accepted: File[] = [];
    const rejected: string[] = [];
    for (const file of files) {
      const problem = validateFile(file);
      if (problem) rejected.push(problem);
      else accepted.push(file);
    }
    // Rejections stay visible even when other files go through: dropping five
    // files of which one is too large must not look like a complete success.
    setError(rejected.join(" · "));
    if (!accepted.length) return;

    setUploading(true);
    try {
      for (const file of accepted) {
        try {
          await api.uploadDocument(file, "default", user.token);
        } catch (err) {
          // Per file, not per batch: a failure on the second of three must not
          // stop the third from being sent — the user would see one error, a
          // list containing the first file, and nothing at all about the third.
          // Appended and named, because overwriting would swallow both the
          // rejections from above and the earlier failures of this batch.
          const reason = err instanceof Error ? err.message : "Upload fehlgeschlagen";
          rejected.push(`${file.name}: ${reason}`);
          setError(rejected.join(" · "));
        }
      }
    } finally {
      // Outside the try on purpose: when the second of two files fails, the
      // first one is already on the server. Without this reload it stays
      // invisible — no entry, so nothing marks it as in flight and no polling
      // starts either — and the user uploads it a second time.
      await load();
      setUploading(false);
    }
  };

  const handleInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    // Reset before awaiting: picking the same file twice in a row fires no
    // change event otherwise, so a corrected retry would appear to do nothing.
    e.target.value = "";
    await handleFiles(files);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    // Uploads run one request per file, so this window is seconds long for a
    // batch. Silently dropping the files would look exactly like a successful
    // drop — the zone has just highlighted and un-highlighted.
    if (uploading) {
      setError("Upload läuft noch — bitte warten, bevor weitere Dateien hinzukommen.");
      return;
    }
    void handleFiles(Array.from(e.dataTransfer.files));
  };

  const handleDelete = async (id: string) => {
    // Claims a sequence number like load() does, so a reload that was already
    // in flight cannot land afterwards and resurrect the removed row.
    const seq = ++writer.current;
    await api.deleteDocument(id, user.token).catch(() => {});
    if (seq === writer.current) setDocs(prev => prev.filter(d => d.id !== id));
  };

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: 32 }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: "var(--navy)" }}>Dokumente</h2>
          <button className="secondary" onClick={onClose}>← Zurück zum Chat</button>
        </div>

        {/* Upload area — click via the label, drag & drop via the handlers */}
        <label
          onDragOver={e => { e.preventDefault(); if (!uploading) setDragging(true); }}
          // Only when the pointer really leaves the zone: dragleave also fires
          // when it moves from the label onto one of its own children, and
          // reacting to that makes the whole zone flicker during the drag.
          onDragLeave={e => {
            if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragging(false);
          }}
          onDrop={handleDrop}
          style={{
            display: "block", border: `2px dashed ${dragging ? "var(--blue)" : "var(--border)"}`,
            borderRadius: 10,
            padding: "24px 32px", textAlign: "center", cursor: "pointer",
            background: uploading || dragging ? "var(--blue-lt)" : "var(--card)", marginBottom: 24,
            transition: "background 0.15s, border-color 0.15s",
          }}
        >
          <div style={{ fontSize: 24, marginBottom: 8 }}>📄</div>
          <div style={{ fontWeight: 700, color: "var(--navy)" }}>
            {uploading
              ? "Wird hochgeladen…"
              : dragging
                ? "Zum Hochladen loslassen"
                : "Dateien hierher ziehen oder klicken"}
          </div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 4 }}>
            PDF, DOCX oder Markdown · max. 10 MB pro Datei
          </div>
          <input
            type="file"
            accept={ALLOWED_EXTENSIONS.join(",")}
            multiple
            hidden
            onChange={handleInput}
            disabled={uploading}
          />
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
              background: "var(--card)", border: `1px solid ${d.status === "failed" ? "var(--red)" : "var(--border)"}`,
              borderRadius: 8, padding: "10px 14px",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{d.filename}</div>
                  <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 2 }}>
                    {d.chunk_count} Chunks · Bereich: {d.area}
                  </div>
                </div>
                <span style={{
                  fontSize: 11, fontWeight: 700, color: statusColor[d.status],
                  background: d.status === "available" ? "var(--green-lt)" : d.status === "failed" ? "var(--red-lt)" : "transparent",
                  borderRadius: 30, padding: "2px 8px",
                }}>
                  {statusLabel[d.status]}
                </span>
                {d.status === "failed" && d.error_message && (
                  <button
                    className="secondary"
                    style={{ fontSize: 11, padding: "3px 8px" }}
                    onClick={() => setExpanded(prev => ({ ...prev, [d.id]: !prev[d.id] }))}
                  >
                    {expanded[d.id] ? "▲ Details" : "▼ Details"}
                  </button>
                )}
                <button className="danger" style={{ fontSize: 12, padding: "4px 10px" }}
                  onClick={() => handleDelete(d.id)}>
                  Löschen
                </button>
              </div>
              {d.status === "failed" && d.error_message && expanded[d.id] && (
                <pre style={{
                  marginTop: 10, padding: "10px 12px",
                  background: "var(--red-lt)", color: "var(--red)",
                  borderRadius: 6, fontSize: 11, lineHeight: 1.5,
                  overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all",
                  maxHeight: 300, overflowY: "auto",
                }}>
                  {d.error_message}
                </pre>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
