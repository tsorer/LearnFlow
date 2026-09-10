"""T-55: mehrere Eval-Läufe nebeneinander lesbar machen.

`make eval EVAL_PROFILE=…` misst je Aufruf **ein** Profil und schreibt sein
Ergebnis nach `eval/out/<profil>/<zeitstempel>/`. Die interessante Frage stellt
sich aber erst zwischen den Läufen: dieselbe Frage, drei Modelle, drei
Ergebnisse — woran liegt der Unterschied?

Dieses Modul beantwortet das aus den bereits geschriebenen Dateien und misst
selbst nichts nach. Es liest je Profil den **neuesten** Lauf und schreibt einen
Markdown-Bericht nach stdout:

    docker exec src-api-1 python -m eval.compare > EvalAnalysis/<datum>_<titel>.md

Die Umleitung passiert bewusst auf dem Host. `EvalAnalysis/` liegt ausserhalb
von `src/backend/` und ist deshalb nicht in den Container gemountet — über
stdout braucht es keinen dritten Mount neben `./backend` und `LearningCorpus`.

Warum «neuester Lauf» und keine Auswahl von aussen: der Bericht trägt die
Zeitstempel, gegen die er erzeugt wurde, im Kopf. Er ist damit
selbstbeschreibend, auch wenn `eval/out/` (gitignored, nur lokal) längst
weitergewachsen ist.

`details.json` ist die Voraussetzung — der Trace je LLM-Aufruf, den
`conftest.py` mitschreibt. Ältere Läufe haben nur `run.json` und CSV; die
überspringt `_newest_run` still, statt den Bericht mit Lücken zu füllen.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path
from typing import Any

from eval.profiles import PROFILES

OUT_DIR = Path(__file__).parent / "out"

#: Die Wire-Werte aus `app/routers/query.py` in Fliesstext. Vollständig gehalten,
#: damit ein Bericht nie einen rohen Schlüssel zeigt; taucht doch einer auf, ist
#: der Grund neu und der Bericht soll ihn sichtbar durchreichen statt zu raten.
REASON_LABELS = {
    "retrieval_gate": "Retrieval",
    "retrieval_confidence": "Retrieval-Konfidenz",
    "generation_refused": "Generierung",
    "generation_truncated": "Generierung abgeschnitten",
    "citation_coverage": "Coverage",
    "citation_invalid": "Referenz erfunden",
    "confidence_band": "Konfidenzband",
    "self_check": "Self-Check",
    "configuration_error": "Konfigurationsfehler",
}

ANSWERED = "Antwort"


class Run:
    """Ein Lauf, so wie er auf der Platte liegt."""

    def __init__(self, profile: str, directory: Path) -> None:
        self.profile = profile
        self.directory = directory
        self.meta: dict[str, Any] = json.loads(
            (directory / "run.json").read_text(encoding="utf-8")
        )
        entries: list[dict[str, Any]] = json.loads(
            (directory / "details.json").read_text(encoding="utf-8")
        )
        self.details = {e["id"]: e for e in entries}
        self.order = [e["id"] for e in entries]


def _newest_run(profile: str) -> Run | None:
    """Der jüngste Lauf eines Profils, der einen Trace mitbringt."""
    directory = OUT_DIR / profile
    if not directory.is_dir():
        return None
    # Der Zeitstempel im Verzeichnisnamen ist ISO-8601 in UTC und damit
    # lexikografisch sortierbar — kein Parsen nötig.
    for candidate in sorted(directory.iterdir(), reverse=True):
        if (candidate / "details.json").is_file() and (candidate / "run.json").is_file():
            return Run(profile, candidate)
    return None


def _outcome(entry: dict[str, Any]) -> str:
    """Was mit einer Frage passiert ist, in einem Wort."""
    response = entry["response"]
    if not response.get("suppressed"):
        return ANSWERED
    reason = response.get("suppression_reason")
    return REASON_LABELS.get(reason, f"verweigert: {reason}")


def _stage_value(entry: dict[str, Any], stage_id: str) -> float | None:
    """Der gemessene Wert einer Pipeline-Stufe, sofern sie überhaupt lief."""
    for stage in entry["response"]["debug"]["stages"]:
        if stage["id"] == stage_id and stage["ran"]:
            value = stage.get("value")
            return float(value) if value is not None else None
    return None


def _calls(run: Run) -> list[dict[str, Any]]:
    return [call for entry in run.details.values() for call in entry["llm_trace"]]


def _median(values: list[float]) -> float:
    return sorted(values)[len(values) // 2] if values else 0.0


def _de(text: str) -> str:
    """Dezimalpunkt zu Komma — der Bericht ist deutsch."""
    return text.replace(".", ",")


def _quote(text: str) -> str:
    """Mehrzeiligen Text als Blockquote.

    Zeilenweise, nicht nur die erste: die Antworten enthalten Aufzählungen, und
    ohne Präfix je Zeile fällt alles ab der zweiten aus dem Zitat heraus und
    wird als Fliesstext des Berichts gelesen — also genau die Verwechslung
    zwischen Modellausgabe und Auswertung, die dieser Abschnitt vermeiden soll.
    """
    return "\n".join(f"> {line}".rstrip() for line in text.strip().splitlines())


def _header(runs: list[Run]) -> list[str]:
    lines = [
        "# Eval-Messreihe — Modellvergleich",
        "",
        "Erzeugt mit `python -m eval.compare` aus den Läufen unten. Gemessen wird die",
        "Out-of-Corpus-Refusal-Rate des Gold-Datasets (ADR-009); das Gate von 90 %",
        "gilt nur für das ausgelieferte Profil.",
        "",
        "## Läufe",
        "",
        "| Profil | Modell | Refusal-Rate | Fragen | Gate | Lauf | Git-SHA |",
        "|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        meta = run.meta
        gate = "ja" if meta.get("gated") else "nein"
        rate = _de(f"{meta['refusal_rate']:.1%}").replace("%", " %")
        lines.append(
            f"| `{run.profile}` | {meta['model']} | **{rate}** | "
            f"{meta['questions']} | {gate} | {run.directory.name} | "
            f"{meta.get('git_sha') or '—'} |"
        )
    return lines


def _thresholds(runs: list[Run]) -> list[str]:
    """Die wirksamen Schwellen — nur dann als Tabelle, wenn sie abweichen.

    Sie sollten über alle Läufe gleich sein, weil `conftest.py` sie innerhalb
    der Transaktion auf die Seed-Defaults setzt. Genau deshalb ist eine
    Abweichung meldenswert: sie hiesse, zwei Läufe messen verschiedene
    Pipelines und ihre Raten sind nicht vergleichbar.
    """
    configs = {run.profile: run.meta.get("measured_config", {}) for run in runs}
    distinct = {json.dumps(c, sort_keys=True) for c in configs.values()}
    lines = ["", "## Wirksame Schwellen", ""]
    if len(distinct) == 1:
        first = next(iter(configs.values()))
        lines.append("Über alle Läufe identisch (Seed-Defaults), die Raten sind vergleichbar:")
        lines.append("")
        lines.append("| Parameter | Wert |")
        lines.append("|---|---|")
        lines += [f"| `{k}` | {v} |" for k, v in sorted(first.items())]
        return lines
    lines.append(
        "**Achtung: die Läufe messen gegen verschiedene Schwellen.** Ihre Raten sind "
        "nicht direkt vergleichbar."
    )
    lines.append("")
    keys = sorted({k for c in configs.values() for k in c})
    lines.append("| Parameter | " + " | ".join(f"`{p}`" for p in configs) + " |")
    lines.append("|---" * (len(configs) + 1) + "|")
    for key in keys:
        values = " | ".join(str(c.get(key, "—")) for c in configs.values())
        lines.append(f"| `{key}` | {values} |")
    return lines


def _per_question(runs: list[Run]) -> list[str]:
    lines = [
        "",
        "## Pro Frage",
        "",
        "`*` markiert eine Abweichung von der Erwartung des Gold-Datasets.",
        "",
        "| Frage | erwartet | " + " | ".join(f"`{r.profile}`" for r in runs) + " |",
        "|---" * (len(runs) + 2) + "|",
    ]
    for qid in runs[0].order:
        expected = runs[0].details[qid]["expected_refusal"]
        cells = []
        for run in runs:
            entry = run.details.get(qid)
            if entry is None:
                cells.append("—")
                continue
            deviates = bool(entry["response"].get("suppressed")) != bool(expected)
            cells.append(_outcome(entry) + (" `*`" if deviates else ""))
        lines.append(
            f"| `{qid}` | {'Verweigerung' if expected else 'Antwort'} | " + " | ".join(cells) + " |"
        )
    return lines


def _reason_distribution(runs: list[Run]) -> list[str]:
    lines = [
        "",
        "## Woran es scheitert",
        "",
        "Wo die Pipeline unterdrückt hat — die Verteilung sagt mehr als die Rate:",
        "eine Verweigerung durch das Modell selbst (`Generierung`) ist ein anderes",
        "Verhalten als eine, die erst eine nachgelagerte Schwelle erzwingt.",
        "",
        "| Profil | Verteilung |",
        "|---|---|",
    ]
    for run in runs:
        counter = collections.Counter(_outcome(e) for e in run.details.values())
        parts = ", ".join(f"{label} {count}" for label, count in counter.most_common())
        lines.append(f"| `{run.profile}` | {parts} |")
    return lines


def _llm_calls(runs: list[Run]) -> list[str]:
    lines = [
        "",
        "## LLM-Aufrufe",
        "",
        "`finish_reason` ist die Kontrolle gegen Messartefakte: ein Lauf mit `length`",
        "oder mit leeren Antworten misst das Token-Budget, nicht das Modell. Beides",
        "muss 0 sein, damit die Raten oben etwas bedeuten.",
        "",
        "| Profil | Aufrufe | finish_reason | leer | Fehler | Σ Dauer | max | median |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        calls = _calls(run)
        finish = collections.Counter(c["finish_reason"] for c in calls)
        empty = sum(1 for c in calls if c["response_chars"] == 0)
        errors = sum(1 for c in calls if c.get("error"))
        durations = [float(c["duration_s"]) for c in calls]
        finish_text = ", ".join(f"`{k}` {v}" for k, v in finish.most_common())
        lines.append(
            f"| `{run.profile}` | {len(calls)} | {finish_text} | {empty} | {errors} | "
            f"{sum(durations):.0f} s | {_de(f'{max(durations, default=0.0):.1f}')} s | "
            f"{_de(f'{_median(durations):.1f}')} s |"
        )

    lines += [
        "",
        "Token-Verbrauch, gemessen am Anbieter:",
        "",
        "| Profil | Prompt max | Prompt median | Completion max |",
        "|---|---|---|---|",
    ]
    for run in runs:
        usages = [c["usage"] for c in _calls(run) if c.get("usage")]
        prompt = [float(u["prompt_tokens"]) for u in usages if u.get("prompt_tokens")]
        completion = [float(u["completion_tokens"]) for u in usages if u.get("completion_tokens")]
        lines.append(
            f"| `{run.profile}` | {max(prompt, default=0):.0f} | {_median(prompt):.0f} | "
            f"{max(completion, default=0):.0f} |"
        )
    return lines


def _self_check(runs: list[Run]) -> list[str]:
    lines = [
        "",
        "## Self-Check (ADR-008, Stufe 3)",
        "",
        "Die Stufe läuft nur im Konfidenz-Grenzband. Wie oft sie überhaupt greift,",
        "ist selbst ein Befund: eine kurze, vollständig belegte Antwort landet im",
        "Band «hoch» und wird gar nicht mehr geprüft.",
        "",
        "| Profil | gelaufen | Urteile |",
        "|---|---|---|",
    ]
    for run in runs:
        ran = [e for e in run.details.values() if e["response"]["debug"].get("self_check_ran")]
        verdicts = collections.Counter(
            str(e["response"]["debug"].get("self_check_verdict")) for e in ran
        )
        parts = ", ".join(f"{k} {v}" for k, v in verdicts.most_common()) or "—"
        lines.append(f"| `{run.profile}` | {len(ran)} von {len(run.details)} | {parts} |")
    return lines


def _deviations(runs: list[Run]) -> list[str]:
    """Die abweichenden Antworten im Wortlaut.

    Der teuerste Teil der Auswertung und der einzige, den keine Kennzahl
    ersetzt: ob eine ausgelieferte Antwort eine Halluzination ist oder eine
    Verweigerung in Prosa, die nur das WEISS_NICHT-Protokoll verfehlt hat,
    steht ausschliesslich im Text.
    """
    lines = [
        "",
        "## Abweichungen im Wortlaut",
        "",
        "Jede Antwort, die entgegen der Erwartung ausgeliefert wurde. Die Einordnung",
        "muss ein Mensch vornehmen — die Kennzahlen oben unterscheiden nicht zwischen",
        "einer erfundenen Aussage und einer korrekten Verweigerung im Fliesstext.",
    ]
    for run in runs:
        meta = run.meta
        lines += ["", f"### `{run.profile}` — {meta['model']}", ""]
        deviating = [
            e
            for e in run.details.values()
            if bool(e["response"].get("suppressed")) != bool(e["expected_refusal"])
        ]
        if not deviating:
            lines.append("Keine Abweichung.")
            continue
        for entry in deviating:
            response = entry["response"]
            confidence = response.get("confidence") or {}
            coverage = _stage_value(entry, "citation_coverage")
            score = confidence.get("score")
            lines += [
                f"**`{entry['id']}`** — {entry['question']}",
                "",
                _quote(response.get("message") or ""),
                "",
                f"Konfidenz {_de(str(score)) if score is not None else '—'} "
                f"(Band «{confidence.get('band', '—')}»), Citation-Coverage "
                f"{_de(str(coverage)) if coverage is not None else '—'}, "
                f"Self-Check {response['debug'].get('self_check_verdict') or 'nicht gelaufen'}.",
                "",
            ]
    return lines


def build_report(runs: list[Run]) -> str:
    sections = (
        _header(runs)
        + _thresholds(runs)
        + _per_question(runs)
        + _reason_distribution(runs)
        + _llm_calls(runs)
        + _self_check(runs)
        + _deviations(runs)
    )
    return "\n".join(sections) + "\n"


def main() -> int:
    runs = [run for run in (_newest_run(name) for name in PROFILES) if run is not None]
    if not runs:
        print(
            f"Kein Lauf mit details.json unter {OUT_DIR}. Zuerst `make eval` "
            f"je Profil ausführen."
        )
        return 1
    print(build_report(runs), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
