import { useEffect, useRef, useState } from "react";
import { api, ApiError, type Citation, type DocumentContent } from "../api/client";

interface Props {
  citation: Citation;
  token: string;
  onClose: () => void;
}

const FOCUSABLE_SELECTOR = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Renders the parsed document text (its chunks), not the uploaded original
 * (ADR-003): the belegende Abschnitt *is* the chunk, so highlighting it is
 * exact instead of a coordinate guess against a PDF/DOCX/MD rendering. Any
 * authenticated role may open this — a query answer already cited the chunk,
 * so a viewer showing it discloses nothing the citation didn't already.
 */
export default function DocumentViewer({ citation, token, onClose }: Props) {
  const [content, setContent] = useState<DocumentContent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const highlightRef = useRef<HTMLDivElement>(null);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setContent(null);
    setError(null);
    api.getDocumentContent(citation.document_id, citation.chunk_id, token)
      .then(result => { if (!cancelled) setContent(result); })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 409) {
          setError("Dokument wird noch verarbeitet und ist noch nicht anzeigbar.");
        } else if (err instanceof ApiError && err.status === 404) {
          setError("Dokument wurde nicht gefunden.");
        } else {
          setError("Dokument konnte nicht geladen werden.");
        }
      });
    return () => { cancelled = true; };
  }, [citation.document_id, citation.chunk_id, token]);

  // Eigener Effekt mit leerem Dependency-Array: läuft nur beim Mount. An
  // [onClose] gehängt lief er bei jedem Rerender der Elternkomponente neu
  // (MessageBubble übergibt ein bei jedem Render neues onClose) und riss den
  // Fokus vom Schliessen-Button zurück, egal wo der Nutzer gerade war.
  //
  // Die Cleanup-Funktion stellt den Fokus auf das Element zurück, das den
  // Viewer geöffnet hat (WAI-ARIA-Dialog-Pattern): sie läuft beim Unmount,
  // und MessageBubble unmountet den Viewer genau dann, wenn onClose den
  // State zurücksetzt.
  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    return () => previouslyFocused?.focus();
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      // Fokus-Falle: Tab zirkuliert innerhalb des Dialogs statt in die Seite
      // dahinter weiterzulaufen (WAI-ARIA-Dialog-Pattern).
      if (e.key !== "Tab" || !dialogRef.current) return;
      const focusables = dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  useEffect(() => {
    highlightRef.current?.scrollIntoView({ block: "center" });
  }, [content]);

  return (
    <div
      role="presentation"
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000,
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Originaldokument ${citation.filename}`}
        onClick={e => e.stopPropagation()}
        style={{
          background: "var(--card)", borderRadius: 12, width: "min(720px, 90vw)",
          maxHeight: "85vh", display: "flex", flexDirection: "column", overflow: "hidden",
        }}
      >
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "12px 16px", borderBottom: "1px solid var(--border)",
        }}>
          <strong style={{ fontSize: 14, color: "var(--navy)" }}>{citation.filename}</strong>
          <button
            ref={closeRef}
            onClick={onClose}
            aria-label="Viewer schliessen"
            style={{
              background: "none", border: "none", fontSize: 18, cursor: "pointer",
              color: "var(--muted)", lineHeight: 1,
            }}
          >
            ✕
          </button>
        </div>
        <div style={{ padding: 16, overflowY: "auto", fontSize: 13, lineHeight: 1.6, color: "var(--text)" }}>
          {error && <p role="alert" style={{ color: "var(--red)" }}>{error}</p>}
          {!error && !content && <p role="status">Lädt…</p>}
          {content?.chunks.map(chunk => {
            const isHighlighted = chunk.chunk_id === citation.chunk_id;
            return (
              <div
                key={chunk.chunk_id}
                ref={isHighlighted ? highlightRef : undefined}
                // aria-current, nicht nur Farbe/Rahmen: "welcher Abschnitt
                // belegt die Antwort" ist genau die Information, die T-21
                // liefern soll, und Farbe allein kommt bei Screenreadern nicht an.
                aria-current={isHighlighted ? "true" : undefined}
                style={{
                  padding: "8px 10px", marginBottom: 8, borderRadius: 8,
                  background: isHighlighted ? "var(--blue-lt)" : "transparent",
                  border: isHighlighted ? "1px solid var(--navy)" : "1px solid transparent",
                }}
              >
                {isHighlighted && <span className="sr-only">Belegender Abschnitt: </span>}
                {chunk.heading && (
                  <div style={{ fontWeight: 700, marginBottom: 4, color: "var(--navy)" }}>
                    {chunk.heading}
                  </div>
                )}
                <div style={{ whiteSpace: "pre-wrap" }}>{chunk.content}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
