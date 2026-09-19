"""Render Q1.json / Q2.json (from trace_pipeline.py) as readable Markdown.

Host-side, standard library only: python render_trace.py
Every number is copied from the JSON; nothing is recomputed except the
stage-1 formula, which is spelled out with its operands for the slide.
"""

import json
from pathlib import Path

HERE = Path(__file__).parent

DOCS = {
    "fedlex": "OBV",
    "EU_AI_ACT": "EU AI Act",
    "SKOS": "SKOS",
    "leitfaden_samw": "SAMW",
}


def doc(name: str) -> str:
    return next((short for prefix, short in DOCS.items() if name.startswith(prefix)), name)


def f4(x: float | None) -> str:
    return "–" if x is None else f"{x:.4f}"


def cell(text: str) -> str:
    return " ".join((text or "").split()).replace("|", "\\|")


def block(text: str) -> str:
    return "```text\n" + (text or "").rstrip() + "\n```"


def render(d: dict) -> str:
    api = d["api_response"]
    dbg = api.get("debug") or {}
    p = d["config"]["pipeline"]
    th = d["config"]["thresholds"]
    k = p["rrf_k"]
    out: list[str] = []
    w = out.append

    w(f"# {d['key']} — Pipeline-Trace\n")
    w(f"> **{d['question']}**\n")
    w("Rohdaten: `" + d["key"] + ".json`. Erzeugt von `trace_pipeline.py` gegen den laufenden Stack; "
      "Stufen, Prompts und Modellantworten stammen aus dem echten `POST /query` (Rolle admin), "
      "alles Übrige aus denselben Service-Funktionen nachgezogen. "
      f"Kontext identisch mit dem echten Lauf: **{d['consistency']['same_context_same_order']}**.\n")

    # 1 ── Zerschneiden der Frage
    c = d["1_query_cutting"]
    w("## 1 · Wie die Frage zerschnitten wird\n")
    w("### 1a · Für die Volltextsuche (Sparse)\n")
    w("`retrieval.py::to_tsquery_terms` — Regex `\\w+`, dann Stoppwörter und Terme < 2 Zeichen raus, "
      "höchstens 10 Terme, mit `|` (ODER) verknüpft.\n")
    w("| Token | behalten | Grund |\n|---|---|---|")
    for t in c["per_token"]:
        w(f"| `{t['token']}` | {'✓' if t['kept'] else '✗'} | {t['dropped_because'] or ''} |")
    w("")
    w(f"- An Postgres übergeben: `{c['tsquery_input']}`")
    w(f"- Postgres macht daraus (Stemming, eigene Stoppwörter): `{c['postgres_tsquery']}`")
    w(f"- Zum Vergleich — so zerlegt Postgres die **ganze** Frage: `{c['postgres_question_tsvector']}`\n")
    w("### 1b · Für das Embedding (Dense)\n")
    b = c["bpe_tokens_for_embedding"]
    w(f"Tokenizer `{b['encoding']}`, **{b['count']} Tokens**:\n")
    w(" ".join(f"`{piece}`" for piece in b["pieces"]) + "\n")
    e = d["2_embedding"]
    w(f"Embedding: {e['dimensions']} Dimensionen, L2-Norm {e['l2_norm']:.4f}, "
      f"erste 8 Werte `{', '.join(f'{v:+.4f}' for v in e['first_8'])}` …\n")

    # 2 ── Suche
    w("## 2 · Was die beiden Suchen finden\n")
    size = d["4b_corpus_size"]
    w(f"Korpus: {size['chunks_ranked_dense']} Chunks. Dense rankt alle, "
      f"Sparse trifft {size['chunks_matching_sparse']}. Je Suche gehen die Top {p['retrieval_top_k']} weiter.\n")
    w(f"### 2a · Dense — Cosine-Ähnlichkeit (pgvector/HNSW), Top {p['retrieval_top_k']}\n")
    w(f"| # | Dok. | S. | Chunk | Cosine | ≥ {p['similarity_threshold']} | Anfang |\n|---|---|---|---|---|---|---|")
    for r in d["3_dense_top_k"]:
        ok = "✓" if r["cosine"] >= p["similarity_threshold"] else ""
        w(f"| {r['rank']} | {doc(r['filename'])} | {r['page']} | {r['chunk_index']} | {f4(r['cosine'])} | {ok} | {cell(r['content_preview'])[:90]} |")
    w("")
    w(f"### 2b · Sparse — Volltext `ts_rank_cd` (tsvector/GIN), Top {p['retrieval_top_k']}\n")
    w("| # | Dok. | S. | Chunk | ts_rank_cd | getroffene Lexeme | Cosine | Anfang |\n|---|---|---|---|---|---|---|---|")
    for r in d["4_sparse_top_k"]:
        lex = ", ".join(r["matched_lexemes"])
        w(f"| {r['rank']} | {doc(r['filename'])} | {r['page']} | {r['chunk_index']} | {r['ts_rank_cd']} | `{lex}` | {f4(r['cosine'])} | {cell(r['content_preview'])[:70]} |")
    w("")

    # 3 ── Fusion
    w("## 3 · Fusion — Reciprocal Rank Fusion\n")
    w(f"`rrf = 1/({k} + dense_rank) + 1/({k} + sparse_rank)` — Rang 0 heisst «nicht in dieser Liste», "
      f"trägt nichts bei. Die ersten **{p['context_top_n']}** gehen als Kontext ans Modell.\n")
    w("| Fusion | Kontext | Dok. | S. | Chunk | Dense-Rang | Sparse-Rang | 1/(k+d) | 1/(k+s) | RRF | Cosine |\n"
      "|---|---|---|---|---|---|---|---|---|---|---|")
    for r in d["5_fusion"]:
        ctx = "**→ [" + str(r["fused_rank"]) + "]**" if r["in_context"] else ""
        w(f"| {r['fused_rank']} | {ctx} | {doc(r['filename'])} | {r['page']} | {r['chunk_index']} | "
          f"{r['dense_rank'] or '–'} | {r['sparse_rank'] or '–'} | {r['rrf_dense_part']:.6f} | "
          f"{r['rrf_sparse_part']:.6f} | {r['rrf_score']:.6f} | {f4(r['cosine'])} |")
    w("")

    # 4 ── Wo die Antwort wirklich steht
    w("## 4 · Wo die Antwort tatsächlich steht\n")
    w("Gesucht per SQL: Chunks der OBV mit «innerorts» und «km/h». Nicht Teil der Pipeline — nur um zu zeigen, wo der richtige Chunk gelandet ist.\n")
    w("| Chunk | S. | Dense-Rang im Korpus | Cosine | Sparse-Rang im Korpus | getroffene Lexeme | Fusions-Rang | im Kontext |\n|---|---|---|---|---|---|---|---|")
    for g in d["11_ground_truth_chunks"]:
        w(f"| {g['chunk_index']} | {g['page']} | {g['dense_rank_in_corpus']} | {f4(g['cosine'])} | "
          f"{g['sparse_rank_in_corpus'] or '–'} | `{', '.join(g['matched_lexemes'])}` | {g['fused_rank'] or '–'} | "
          f"{'✓' if g['in_context'] else '✗'} |")
    w("")

    # 5 ── Kontext + Chunking
    w("## 5 · Der Kontext, den das Modell sieht — und wie er geschnitten wurde\n")
    w("Chunking (Worker, `chunking.py`): Ziel 512 Tokens, 64 Tokens Überlappung, strukturbewusst "
      "(Absatz → Satz → Zeile → Wort). Seitenwechsel und Überschriftwechsel sind harte Grenzen — "
      "über eine Seitengrenze gibt es keine Überlappung.\n")
    w("| Dokument | Chunks | Tokens min / Median / max |\n|---|---|---|")
    for ch in d["10_chunking"]:
        w(f"| {doc(ch['filename'])} | {ch['chunk_count']} | {ch['tokens_min']} / {ch['tokens_median']} / {ch['tokens_max']} |")
    w("")
    ctx_by_id = {c["chunk_id"]: (ch, c) for ch in d["10_chunking"] for c in ch["context_chunks"]}
    for r in d["5_fusion"]:
        if not r["in_context"]:
            continue
        ch, c = ctx_by_id[r["chunk_id"]]
        ov = c["overlap_with_previous"]
        w(f"### [{r['fused_rank']}] {doc(ch['filename'])}, S. {c['page']}, Chunk {c['chunk_index']} — {c['tokens']} Tokens\n")
        if ov["chars"]:
            w(f"Überlappt {ov['chars']} Zeichen mit Chunk {c['chunk_index'] - 1}: «{cell(ov['text'])[:160]}»\n")
        else:
            w(f"Keine Überlappung mit Chunk {c['chunk_index'] - 1} (Seitengrenze).\n")
        w(block(c["content"]) + "\n")

    # 6 ── Stufe 0 / 1
    g0 = d["6_stage0_gate"]
    s1 = d["7_stage1_confidence"]
    dt = s1["detail"]
    w("## 6 · Stufe 0 — Retrieval-Gate\n")
    w(f"`{g0['rule']}` mit Schwelle {g0['threshold']}. Kontext-Scores: "
      f"{', '.join(f4(x) for x in g0['context_scores'])} → **{'bestanden' if g0['passed'] else 'unterdrückt'}**.\n")
    w("## 7 · Stufe 1 — Retrieval-Konfidenz\n")
    w(f"`{s1['formula']}`\n")
    w(f"= 0.5 × {dt['top_score']} + 0.3 × {dt['mean_score']} + 0.2 × {dt['evidence_density']}  "
      f"= **{dt['result']}**  gegen Schwelle {s1['threshold']} → **{'bestanden' if s1['passed'] else 'unterdrückt'}**\n")
    w(f"(`top` = bester Cosine im Kontext, `mean` = Mittel der {dt['count']} Kontext-Scores, "
      f"`density` = Anteil ≥ {p['similarity_threshold']})\n")

    # 7 ── Generierung
    calls = dbg.get("llm_calls", [])
    gen = next((x for x in calls if x["step"] != "self_check"), None)
    sc = next((x for x in calls if x["step"] == "self_check"), None)
    w("## 8 · Generierung — LLM-Aufruf 1\n")
    if gen:
        w("<details><summary>Vollständiger Prompt (System + User)</summary>\n")
        w(block(gen["prompt"]) + "\n</details>\n")
        w("**Antwort des Modells:**\n")
        w(block(gen["response"]) + "\n")

    # 8 ── Stufe 2
    w("## 9 · Stufe 2 — Citation-Check (deterministisch)\n")
    w(f"Antwort in Segmente zerlegt; ein Segment zählt ab {4} Wörtern (ohne Referenzen), "
      f"gültig sind Referenzen 1…{p['context_top_n']}.\n")
    w("| Segment | Referenzen | Wörter | zählt | belegt |\n|---|---|---|---|---|")
    for s in d["8_stage2_segments"]:
        w(f"| {cell(s['segment'])} | {s['references']} | {s['words_without_refs']} | "
          f"{'✓' if s['counted'] else '✗'} | {'✓' if s['covered'] else '✗'} |")
    r2 = d["8_stage2_result"]
    w("")
    if r2:
        w(f"Coverage = {r2['covered']} / {r2['segments']} = **{r2['coverage']}** gegen Schwelle "
          f"{p['min_citation_coverage']}; erfundene Referenzen: {r2['fabricated'] or 'keine'} → "
          f"**{'bestanden' if r2['valid'] and r2['coverage'] >= p['min_citation_coverage'] else 'unterdrückt'}**\n")

    # 9 ── Komposit
    cp = d["9_composite"]
    cd = cp["detail"]
    w("## 10 · Komposit und Band\n")
    w(f"`0.5 × retrieval + 0.5 × coverage` = 0.5 × {cd['retrieval_score']} + 0.5 × {cd['citation_coverage']} "
      f"= **{cd['result']}** → Band **{cp['band']}** (Mittel ab {th['medium']}, Hoch ab {th['high']})\n")
    lo, hi = cp["self_check_band"]
    w(f"Self-Check-Grenzband {lo} ≤ c < {hi}: **{'ja — Stufe 3 läuft' if cp['in_self_check_band'] else 'nein — Stufe 3 läuft nicht'}**\n")

    # 10 ── Stufe 3
    w("## 11 · Stufe 3 — Self-Check (LLM-Aufruf 2)\n")
    if sc:
        w("<details><summary>Vollständiger Prompt</summary>\n")
        w(block(sc["prompt"]) + "\n</details>\n")
        w(f"**Urteil:** `{sc['response'].strip()}`\n")
    else:
        w("Nicht gelaufen — der Score liegt ausserhalb des Grenzbands.\n")

    # 11 ── Stufen laut API
    w("## 12 · Stufen, wie die API sie meldet (`debug.stages`)\n")
    w("| Stufe | gelaufen | bestanden | Wert | Schwelle | Detail |\n|---|---|---|---|---|---|")
    for s in dbg.get("stages", []):
        w(f"| `{s['id']}` | {'✓' if s['ran'] else '–'} | {'✓' if s['passed'] else '✗'} | {s['value']} | "
          f"{s['threshold'] if s['threshold'] is not None else '–'} | {cell(s['detail'])} |")
    w("")

    # 12 ── Ergebnis
    w("## 13 · Was der Benutzer sieht\n")
    conf = api.get("confidence") or {}
    w(f"- Unterdrückt: **{api['suppressed']}** {('— ' + api['suppression_reason']) if api['suppression_reason'] else ''}")
    w(f"- Konfidenz: {conf.get('score')} · Band **{conf.get('band')}**")
    w(f"- Antwort: «{cell(api.get('message') or '')}»")
    for cit in api.get("citations", []):
        w(f"- Quelle [{cit['index']}]: {doc(cit['filename'])}, S. {cit['page']}")
    w("")
    return "\n".join(out)


def main() -> None:
    for key in ("Q1", "Q2"):
        data = json.loads((HERE / f"{key}.json").read_text(encoding="utf-8"))
        (HERE / f"{key}_trace.md").write_text(render(data), encoding="utf-8")
        print(f"{key}_trace.md written")


if __name__ == "__main__":
    main()
