/**
 * Die Pipeline-Parameter, die ein Admin zu sehen bekommt — an einer Stelle.
 *
 * Vorher hielten `ChatView` (die Regler) und `MessageBubble` (die Debug-Badges
 * einer Antwort) je eine eigene Liste derselben Schlüssel. Beide sind vom
 * Vertrag aus T-37 abgedriftet, und zwar unterschiedlich weit: die eine schickte
 * `top_k` an einen Endpunkt, der nur `retrieval_top_k` kennt, die andere
 * beschriftete `retrieval_top_k` gar nicht und zeigte den rohen Schlüssel. Zwei
 * Listen derselben Menge driften auseinander, sobald jemand nur eine anfasst —
 * deshalb steht die Menge jetzt hier, und die Beschriftungen leiten sich davon
 * ab statt danebenzustehen.
 *
 * Die Gruppierung folgt der Konsequenz einer Änderung, nicht dem Thema: alles in
 * RETRIEVAL und ANSWER wird pro Anfrage aus `config` gelesen und wirkt auf die
 * nächste Frage (US-11). Die Werte in READ_ONLY wirken erst nach vollständiger
 * Re-Indexierung des Korpus und werden von `PUT /api/admin/config` deshalb
 * abgelehnt (T-42).
 *
 * Aus Migration `0012`s CHECK stammt, was die Datenbank erzwingt: Schwellen in
 * [0, 1], die drei Zähler als positive Ganzzahlen — also `min` und, bei den
 * Schwellen, `max`. Die Obergrenzen der Zähler (100/50/200) stehen dort
 * **nicht**; der CHECK ist nach oben offen. Sie sind hier als Bedienschutz
 * gewählt und dürfen bewegt werden, ohne dass eine Migration nachzieht — was
 * die Datenbank ablehnt, sagen die anderen Grenzen.
 *
 * `step` ist reine Bedienung. PUT ist all-or-nothing, also kostet ein einziges
 * Feld ausserhalb des von der DB erzwungenen Bereichs die gesamte Speicherung —
 * auch die unberührten Werte daneben.
 */

export type ParamDef = {
  key: string;
  label: string;
  type: "float" | "int";
  min: number;
  max: number;
  step: number;
};

/** Welche Chunks überhaupt in den Kontext kommen (ADR-007). */
export const RETRIEVAL_PARAM_DEFS: readonly ParamDef[] = [
  { key: "similarity_threshold",     label: "Similarity-Schwellwert",   type: "float", min: 0, max: 1,   step: 0.01 },
  { key: "min_retrieval_confidence", label: "Min. Retrieval-Konfidenz", type: "float", min: 0, max: 1,   step: 0.01 },
  { key: "retrieval_top_k",          label: "Kandidaten je Suche",      type: "int",   min: 1, max: 100, step: 1    },
  { key: "context_top_n",            label: "Chunks ans LLM",           type: "int",   min: 1, max: 50,  step: 1    },
  { key: "rrf_k",                    label: "RRF-Dämpfung",             type: "int",   min: 1, max: 200, step: 1    },
];

/** Wann einer erzeugten Antwort getraut wird (ADR-008). */
export const ANSWER_PARAM_DEFS: readonly ParamDef[] = [
  { key: "min_citation_coverage",       label: "Min. Citation-Coverage",  type: "float", min: 0, max: 1, step: 0.01 },
  { key: "confidence_threshold_medium", label: "Band «mittel» ab",        type: "float", min: 0, max: 1, step: 0.01 },
  { key: "confidence_threshold_high",   label: "Band «hoch» ab",          type: "float", min: 0, max: 1, step: 0.01 },
  { key: "self_check_band_low",         label: "Self-Check Zone (unten)", type: "float", min: 0, max: 1, step: 0.01 },
  { key: "self_check_band_high",        label: "Self-Check Zone (oben)",  type: "float", min: 0, max: 1, step: 0.01 },
];

/**
 * Sichtbar, aber nicht änderbar. Eine Kalibrieransicht, die die Hälfte der
 * Parameter verschweigt, lädt zu falschen Schlüssen ein — eine neue
 * Chunk-Grösse wirkt aber nur auf danach indexierte Dokumente, und ohne
 * vollständigen Re-Index wird der Korpus halb alt und halb neu, ohne dass es
 * irgendwo steht (ADR-007). Schreibbar zu machen ist Sache von T-42.
 */
export const READ_ONLY_PARAM_DEFS = [
  { key: "chunk_size",    label: "Chunk-Grösse (Tokens)" },
  { key: "chunk_overlap", label: "Chunk-Overlap (Tokens)" },
] as const;

/**
 * Beschriftung je Schlüssel, abgeleitet statt gepflegt.
 *
 * `debug.params_used` liefert jede Schwelle, gegen die eine Anfrage entschieden
 * wurde — auch die von Stufen, die nicht liefen. Ein Schlüssel, der hier fehlt,
 * erscheint dem Admin als roher Bezeichner; genau das passierte mit
 * `retrieval_top_k`, `context_top_n` und `rrf_k`.
 */
export const PARAM_LABELS: Record<string, string> = Object.fromEntries(
  [...RETRIEVAL_PARAM_DEFS, ...ANSWER_PARAM_DEFS, ...READ_ONLY_PARAM_DEFS].map(
    p => [p.key, p.label],
  ),
);
