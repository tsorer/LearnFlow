/**
 * @vitest-environment jsdom
 *
 * T-16: die Upload-UI. Gegen den gemeinsamen fetch-Stub (src/test/api.ts) —
 * geprueft wird, was tatsaechlich ueber die Leitung geht, in drei Faellen
 * gerade, dass nichts geht.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup, fireEvent, act, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import Upload, { MAX_UPLOAD_BYTES, validateFile } from "./components/Upload";
import { installApiStub, type ApiStub } from "./test/api";
import type { AuthUser, Document } from "./types";

const user: AuthUser = {
  id: "u1",
  email: "ko@learnflow.ch",
  role: "knowledge_owner",
  token: "tok123",
};

/** A File with real bytes, so its size survives serialisation. */
function file(name: string, size = 32): File {
  return new File([new Uint8Array(size)], name);
}

const OVERSIZED = MAX_UPLOAD_BYTES + 1;

/** Typed against the spec, so a document the API could never return fails here. */
function doc(filename: string, status: Document["status"]): Document {
  return {
    id: `id-${filename}`,
    filename,
    status,
    area: "default",
    chunk_count: status === "available" ? 3 : 0,
    error_message: null,
    created_at: "2026-08-15T10:00:00Z",
  };
}

let api: ApiStub;

const show = () => render(<Upload user={user} onClose={() => {}} />);

/**
 * The label carrying the drop handlers, found via the format hint: the headline
 * above it changes between idle, dragging and uploading, the hint does not.
 */
const dropZone = () =>
  screen.getByText(/PDF, DOCX oder Markdown/i).closest("label") as HTMLLabelElement;

const drop = (files: File[]) => fireEvent.drop(dropZone(), { dataTransfer: { files } });

/** The file the app put into the multipart body of the nth upload. */
function sentFile(index = 0): File {
  const sent = api.requests("post", "/api/documents")[index]?.form?.get("file");
  if (!(sent instanceof File)) throw new Error(`Kein File im Request ${index}: ${String(sent)}`);
  return sent;
}

beforeEach(() => {
  api = installApiStub();
  api.route("get", "/api/documents", 200, []);
  api.route("post", "/api/documents", 201, doc("neu.pdf", "pending"));
});

afterEach(() => {
  api.release();
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("validateFile", () => {
  it.each([".pdf", ".docx", ".md"])("accepts %s", ext => {
    expect(validateFile(file(`korpus${ext}`))).toBeNull();
  });

  it("accepts an uppercase extension — the API lowercases it too", () => {
    expect(validateFile(file("Korpus.PDF"))).toBeNull();
  });

  it("rejects a format the API would answer with 415", () => {
    expect(validateFile(file("notizen.txt"))).toMatch(/nicht unterstütztes Format/);
  });

  it("rejects a file without any extension", () => {
    expect(validateFile(file("README"))).toMatch(/nicht unterstütztes Format/);
  });

  it("rejects a file above the 10 MB limit", () => {
    expect(validateFile(file("gross.pdf", OVERSIZED))).toMatch(/10 MB/);
  });

  it("accepts a file exactly at the limit — the API rejects above, not at", () => {
    expect(validateFile(file("genau.pdf", MAX_UPLOAD_BYTES))).toBeNull();
  });

  it("reports the format first when both are wrong, in the API's order", () => {
    expect(validateFile(file("gross.txt", OVERSIZED))).toMatch(/nicht unterstütztes Format/);
  });
});

describe("Upload", () => {
  it("uploads a dropped file", async () => {
    show();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

    drop([file("korpus.pdf", 512)]);

    await waitFor(() => expect(api.count("post", "/api/documents")).toBe(1));
    expect(sentFile().name).toBe("korpus.pdf");
    expect(sentFile().size).toBe(512);
    // MVP: exactly one hardcoded pilot area (documents.py), and the backend
    // answers anything else with 400 — so the field has to travel.
    expect(api.last("post", "/api/documents")?.form?.get("area")).toBe("default");
    expect(api.last("post", "/api/documents")?.authorization).toBe("Bearer tok123");
  });

  it("reloads the list after an upload instead of waiting for the next poll", async () => {
    show();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

    drop([file("korpus.pdf")]);

    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(2));
  });

  it("names the supported formats and the size limit without any interaction", async () => {
    show();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

    expect(screen.getByText(/PDF, DOCX oder Markdown/i)).toBeInTheDocument();
    expect(screen.getByText(/max\. 10 MB pro Datei/i)).toBeInTheDocument();
  });

  it("rejects an oversized file before it reaches the network", async () => {
    show();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

    drop([file("gross.pdf", OVERSIZED)]);

    // Not /10 MB/: the zone's own hint carries that too, and matching both
    // would pass without any error being shown at all.
    expect(await screen.findByText(/überschreiten das Limit/)).toBeInTheDocument();
    expect(api.count("post", "/api/documents")).toBe(0);
  });

  it("rejects a dropped format the picker would have filtered", async () => {
    // `accept` only constrains the file dialog — a drop bypasses it entirely,
    // so without the explicit check this would travel to the API for a 415.
    show();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

    drop([file("notizen.txt")]);

    expect(await screen.findByText(/nicht unterstütztes Format/)).toBeInTheDocument();
    expect(api.count("post", "/api/documents")).toBe(0);
  });

  it("uploads the valid files of a mixed drop and still reports the rejected one", async () => {
    show();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

    drop([file("gut.pdf"), file("gross.md", OVERSIZED)]);

    await waitFor(() => expect(api.count("post", "/api/documents")).toBe(1));
    expect(sentFile().name).toBe("gut.pdf");
    expect(screen.getByText(/gross\.md/)).toBeInTheDocument();
  });

  it("reloads the list even when the upload fails", async () => {
    // Without the reload in finally, a batch whose second file fails leaves the
    // first one on the server but invisible — no entry, so nothing marks it as
    // in flight and no polling starts either. The user uploads it again.
    show();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));
    api.route("post", "/api/documents", 413, { detail: "Datei überschreitet das 10-MB-Limit" });

    drop([file("korpus.pdf")]);

    expect(await screen.findByText(/10-MB-Limit/)).toBeInTheDocument();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(2));
  });

  it("keeps a rejection visible when another file's upload then fails", async () => {
    show();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));
    api.route("post", "/api/documents", 413, { detail: "Datei überschreitet das 10-MB-Limit" });

    drop([file("gut.pdf"), file("notizen.txt")]);

    // Both have to survive: the server error must not overwrite the message
    // that says a file was skipped before anything was sent.
    expect(await screen.findByText(/10-MB-Limit/)).toBeInTheDocument();
    expect(screen.getByText(/nicht unterstütztes Format/)).toBeInTheDocument();
  });

  it("says so when a drop lands while an upload is still running", async () => {
    show();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

    api.hold();
    drop([file("erste.pdf")]);
    await waitFor(() => expect(api.count("post", "/api/documents")).toBe(1));

    drop([file("zweite.pdf")]);

    // Silently discarding looks exactly like a successful drop — the zone has
    // highlighted and un-highlighted either way.
    expect(await screen.findByText(/Upload läuft noch/)).toBeInTheDocument();
    expect(api.count("post", "/api/documents")).toBe(1);
  });

  it("polls while a document is processing and stops once it is available", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.route("get", "/api/documents", 200, [doc("korpus.pdf", "processing")]);

    show();
    await waitFor(() => expect(screen.getByText("Verarbeitung…")).toBeInTheDocument());

    api.route("get", "/api/documents", 200, [doc("korpus.pdf", "available")]);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(await screen.findByText("Verfügbar")).toBeInTheDocument();

    // Nothing left in flight: further ticks must not keep asking.
    const settled = api.count("get", "/api/documents");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(9000);
    });
    expect(api.count("get", "/api/documents")).toBe(settled);
  });

  it("keeps polling after a failed reload", async () => {
    // The regression this replaces: the poll effect depended on `docs`, and a
    // rejected reload leaves that array identical — the effect never re-ran and
    // the document stayed on "Verarbeitung…" for good.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.route("get", "/api/documents", 200, [doc("korpus.pdf", "processing")]);

    show();
    await waitFor(() => expect(screen.getByText("Verarbeitung…")).toBeInTheDocument());

    const failing = vi.fn().mockRejectedValue(new Error("Netzwerk weg"));
    const working = globalThis.fetch;
    vi.stubGlobal("fetch", failing);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(failing).toHaveBeenCalled();

    vi.stubGlobal("fetch", working);
    api.route("get", "/api/documents", 200, [doc("korpus.pdf", "available")]);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });

    expect(await screen.findByText("Verfügbar")).toBeInTheDocument();
  });
});
