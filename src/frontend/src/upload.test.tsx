/**
 * @vitest-environment jsdom
 *
 * T-16: die Upload-UI. Gegen den gemeinsamen fetch-Stub (test/api.ts) —
 * geprueft wird, was tatsaechlich ueber die Leitung geht, in drei Faellen
 * gerade, dass nichts geht.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup, fireEvent, act, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import Upload, { MAX_UPLOAD_BYTES, validateFile } from "./components/Upload";
import { installApiStub, type ApiStub } from "../test/api";
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

/** The hidden file input behind the click path. */
const picker = () => dropZone().querySelector('input[type="file"]') as HTMLInputElement;

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

  it("sends the rest of the batch after one file fails, and names each failure", async () => {
    // The loop used to abort on the first error, so files after it were never
    // sent — and nothing said so. The user saw one message, a list containing
    // the files before the failure, and assumed the rest had arrived.
    show();
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));
    api.route("post", "/api/documents", 413, { detail: "Zu gross" });

    drop([file("a.pdf"), file("b.pdf"), file("c.pdf")]);

    await waitFor(() => expect(api.count("post", "/api/documents")).toBe(3));
    for (const name of ["a.pdf", "b.pdf", "c.pdf"]) {
      expect(await screen.findByText(new RegExp(name.replace(".", "\\.")))).toBeInTheDocument();
    }
  });

  it("does not resurrect a deleted document when a stale reload lands afterwards", async () => {
    // A poll started before the delete and answering after it would overwrite
    // the optimistic removal with a list that still contains the document.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.route("get", "/api/documents", 200, [doc("korpus.pdf", "processing")]);
    api.route("delete", "/api/documents/{document_id}", 204);

    show();
    expect(await screen.findByText("korpus.pdf")).toBeInTheDocument();

    // Second poll goes out and is stalled — it still carries the old list.
    api.hold("get");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    await waitFor(() => expect(api.count("get", "/api/documents")).toBe(2));

    fireEvent.click(screen.getByRole("button", { name: /löschen/i }));
    await waitFor(() => expect(api.count("delete", "/api/documents/{document_id}")).toBe(1));

    api.release("get");
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });

    expect(screen.queryByText("korpus.pdf")).not.toBeInTheDocument();
  });

  // AK 1 aus #23 verlangt beide Wege. Bis hierher ging jeder Test ueber den
  // Drop, `handleInput` war damit ungedeckt — samt dem value-Reset und der
  // disabled-Verdrahtung, die beide ihren eigenen Bug schon hatten.
  describe("Klick-Pfad", () => {
    it("uploads a file chosen through the file picker", async () => {
      show();
      await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

      await userEvent.upload(picker(), file("gewaehlt.pdf", 256));

      await waitFor(() => expect(api.count("post", "/api/documents")).toBe(1));
      expect(sentFile().name).toBe("gewaehlt.pdf");
      expect(sentFile().size).toBe(256);
    });

    it("applies the same validation as the drop path", async () => {
      show();
      await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

      await userEvent.upload(picker(), file("gross.pdf", OVERSIZED));

      expect(await screen.findByText(/überschreiten das Limit/)).toBeInTheDocument();
      expect(api.count("post", "/api/documents")).toBe(0);
    });

    it("clears the input so the same file can be picked again after a fix", async () => {
      // The browser fires no change event when the same file is selected twice
      // in a row, so without the reset a corrected retry looks like nothing
      // happens at all. Asserting the reset itself, because the missing second
      // event is a browser behaviour jsdom does not reproduce.
      show();
      await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

      await userEvent.upload(picker(), file("korpus.pdf"));

      await waitFor(() => expect(api.count("post", "/api/documents")).toBe(1));
      expect(picker().value).toBe("");
    });

    it("disables the picker while an upload is running", async () => {
      show();
      await waitFor(() => expect(api.count("get", "/api/documents")).toBe(1));

      api.hold("post");
      await userEvent.upload(picker(), file("korpus.pdf"));
      await waitFor(() => expect(api.count("post", "/api/documents")).toBe(1));

      expect(picker()).toBeDisabled();

      api.release("post");
      await waitFor(() => expect(picker()).toBeEnabled());
    });
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
