/**
 * @vitest-environment jsdom
 *
 * T-38: the admin parameter panel (US-11).
 *
 * The panel predates the `PUT /api/admin/config` contract from T-37 and had
 * drifted away from it: two sliders sent a key under a name the config table
 * never had (`top_k`, `top_n`), four sent keys that do not exist at all
 * (`llm_*`), and two offered values the endpoint deliberately refuses to write
 * (`chunk_size`, `chunk_overlap`). Since PUT is all-or-nothing, touching any of
 * them failed the whole save — including the thresholds next to it that were
 * perfectly valid.
 *
 * These cases pin the contract from the outside: what the panel offers, and
 * what actually leaves the app when it is saved. Like query.test.tsx they run
 * against the shared fetch stub rather than a module mock, because the
 * assertion that matters is about the request on the wire.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import "@testing-library/jest-dom/vitest";
import App from "./App";
import { installApiStub, installAppEnvironment, type ApiStub } from "../test/api";
import { PARAM_LABELS } from "./params";

let api: ApiStub;

/**
 * Die Schlüssel, die `POST /api/query` in `debug.params_used` legt
 * (`app/routers/query.py`) — jede Schwelle, gegen die entschieden wurde, auch
 * die von Stufen, die nicht liefen.
 *
 * Bewusst als Literal und nicht aus PARAM_LABELS abgeleitet: das hier ist ein
 * Vertrag mit dem Backend, und eine Schwelle, die dort dazukommt, ohne hier eine
 * Beschriftung zu haben, erscheint dem Admin als roher Bezeichner. Genau so
 * standen `retrieval_top_k`, `context_top_n` und `rrf_k` unbeschriftet in der
 * Debug-Ansicht, während das Panel sie unter falschem Namen verschickte.
 */
const PARAMS_USED_KEYS = [
  "similarity_threshold",
  "min_retrieval_confidence",
  "min_citation_coverage",
  "confidence_threshold_medium",
  "confidence_threshold_high",
  "self_check_band_low",
  "self_check_band_high",
  "retrieval_top_k",
  "context_top_n",
  "rrf_k",
] as const;

/** Every row `GET /admin/config` returns — the writable ones and the rest. */
const CONFIG: Record<string, string> = {
  similarity_threshold: "0.35",
  min_retrieval_confidence: "0.40",
  min_citation_coverage: "0.50",
  confidence_threshold_medium: "0.45",
  confidence_threshold_high: "0.75",
  self_check_band_low: "0.45",
  self_check_band_high: "0.75",
  retrieval_top_k: "20",
  context_top_n: "5",
  rrf_k: "60",
  chunk_size: "512",
  chunk_overlap: "64",
  stale_days: "90",
  processing_timeout_seconds: "2700",
  processing_max_attempts: "3",
};

/** The ten parameters that take effect on the next question, with the value
 *  each one should carry after the panel opens (AK 2, "Aktueller Wert
 *  vorausgefüllt"). */
const EDITABLE: ReadonlyArray<readonly [string, number]> = [
  ["Similarity-Schwellwert", 0.35],
  ["Min. Retrieval-Konfidenz", 0.4],
  ["Kandidaten je Suche", 20],
  ["Chunks ans LLM", 5],
  ["RRF-Dämpfung", 60],
  ["Min. Citation-Coverage", 0.5],
  ["Band «mittel» ab", 0.45],
  ["Band «hoch» ab", 0.75],
  ["Self-Check Zone (unten)", 0.45],
  ["Self-Check Zone (oben)", 0.75],
];

async function openPanel() {
  api.route("post", "/api/auth/login", 200, {
    access_token: "tok123",
    token_type: "bearer",
    role: "admin",
  });
  api.route("get", "/api/auth/me", 200, {
    id: "u1",
    email: "admin@learnflow.ch",
    role: "admin",
  });
  api.route("get", "/api/admin/config", 200, { config: CONFIG });
  api.route("get", "/api/documents", 200, []);

  render(<App />);
  await userEvent.type(screen.getByLabelText(/e-mail/i), "admin@learnflow.ch");
  await userEvent.type(screen.getByLabelText(/passwort/i), "secret");
  await userEvent.click(screen.getByRole("button", { name: /anmelden/i }));
  await screen.findByLabelText("Frage");
  await userEvent.click(screen.getByRole("button", { name: /parameter/i }));
}

/** The config object the app last put on the wire. */
function savedConfig(): Record<string, string> {
  const requests = api.requests("put", "/api/admin/config");
  return (requests[requests.length - 1]?.json as { config: Record<string, string> }).config;
}

beforeEach(() => {
  api = installApiStub();
  installAppEnvironment();
});

afterEach(() => {
  api.release();
  cleanup();
  vi.unstubAllGlobals();
});

describe("admin parameter panel", () => {
  it("offers every immediately effective parameter, pre-filled from the config table", async () => {
    await openPanel();

    for (const [label, value] of EDITABLE) {
      expect(screen.getByLabelText(label)).toHaveValue(value);
    }
  });

  it("shows the values a change would invalidate the index for, without offering to edit them", async () => {
    // `chunk_size`/`chunk_overlap` are real and worth seeing while calibrating,
    // but PUT refuses them: a new chunk size only applies to documents indexed
    // after the change (T-42). Visible, not editable.
    await openPanel();

    expect(screen.getByText("Chunk-Grösse (Tokens)")).toBeInTheDocument();
    expect(screen.getByText("512")).toBeInTheDocument();
    expect(screen.queryByLabelText("Chunk-Grösse (Tokens)")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Chunk-Overlap (Tokens)")).not.toBeInTheDocument();
  });

  it("has no control for a key the config table does not have", async () => {
    // The four LLM sliders are deferred to their own issue (comment on #44):
    // they need a seed, readers with other ranges and wiring into the
    // generation. Until then they must not exist here, because every one of
    // them 422s the entire save.
    await openPanel();

    for (const label of ["Temperature", "Max Tokens", "Top-P", "Seed (Reproduzierb.)"]) {
      expect(screen.queryByLabelText(label)).not.toBeInTheDocument();
    }
  });

  it("saves the edited value under the name the config table uses", async () => {
    // The regression this whole ticket is about: the slider was labelled
    // "Top-K" and sent `top_k`, while the row is called `retrieval_top_k`.
    api.route("put", "/api/admin/config", 200, { config: { ...CONFIG, retrieval_top_k: "30" } });
    await openPanel();

    const field = screen.getByLabelText("Kandidaten je Suche");
    await userEvent.clear(field);
    await userEvent.type(field, "30");
    await userEvent.click(screen.getByRole("button", { name: /speichern/i }));

    await waitFor(() => expect(api.requests("put", "/api/admin/config")).toHaveLength(1));
    const sent = savedConfig();
    expect(sent.retrieval_top_k).toBe("30");
    expect(sent).not.toHaveProperty("top_k");
    expect(sent).not.toHaveProperty("llm_temperature");
  });

  it("passes the non-writable rows back unchanged so the round-trip is accepted", async () => {
    // PUT takes the whole object back. A non-writable key is only an error if
    // its value differs from what is stored (admin.py), so the panel must not
    // drop or rewrite the rows it cannot edit.
    api.route("put", "/api/admin/config", 200, { config: CONFIG });
    await openPanel();

    const field = screen.getByLabelText("Band «hoch» ab");
    await userEvent.clear(field);
    await userEvent.type(field, "0.8");
    await userEvent.click(screen.getByRole("button", { name: /speichern/i }));

    await waitFor(() => expect(api.requests("put", "/api/admin/config")).toHaveLength(1));
    const sent = savedConfig();
    expect(sent.confidence_threshold_high).toBe("0.8");
    expect(sent.chunk_size).toBe(CONFIG.chunk_size);
    expect(sent.stale_days).toBe(CONFIG.stale_days);
  });
});

describe("PARAM_LABELS", () => {
  it("beschriftet jede Schwelle, die die Debug-Ansicht einer Antwort erhält", () => {
    for (const key of PARAMS_USED_KEYS) {
      expect(PARAM_LABELS[key]).toBeTruthy();
    }
  });

  it("kennt keinen Schlüssel, den es in der config-Tabelle nicht gibt", () => {
    // Die vier llm_* standen hier, ohne dass es je eine Zeile für sie gab —
    // tote Einträge, die nichts beschrifteten und die Liste plausibel aussehen
    // liessen. Ihr Feature ist in ein eigenes Issue vertagt.
    for (const key of Object.keys(PARAM_LABELS)) {
      expect(key.startsWith("llm_")).toBe(false);
    }
    expect(PARAM_LABELS).not.toHaveProperty("top_k");
    expect(PARAM_LABELS).not.toHaveProperty("top_n");
  });
});

// Der abgelehnte Speichervorgang selbst ist bereits in write-confirmation.test.tsx
// abgedeckt ("admin parameters (T-37) > reports no success when the write fails")
// und wird hier nicht wiederholt.
