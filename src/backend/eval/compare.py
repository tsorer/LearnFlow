"""T-55: mehrere Eval-Läufe nebeneinander lesbar machen.

`make eval EVAL_PROFILE=…` misst je Aufruf **ein** Profil und schreibt sein
Ergebnis nach `eval/out/<profil>/<zeitstempel>/`. Die interessante Frage stellt
sich aber erst zwischen den Läufen: dieselbe Frage, drei Modelle, drei
Ergebnisse — woran liegt der Unterschied?

Dieses Modul beantwortet das aus den bereits geschriebenen Dateien und misst
selbst nichts nach. Es liest je Profil den **neuesten** Lauf und schreibt einen
Markdown-Bericht nach stdout:

    docker exec src-api-1 python -m eval.compare > EvalAnalysis/<datum>_<titel>.md

Optional mit Einschätzungen je abweichender Antwort (Dateien vorher in den
Container kopieren, `EvalAnalysis/` ist nicht gemountet):

    python -m eval.compare --einschaetzung /tmp/labels.csv --holdout /tmp/holdout.json

Die Umleitung passiert bewusst auf dem Host. `EvalAnalysis/` liegt ausserhalb
von `src/backend/` und ist deshalb nicht in den Container gemountet — über
stdout braucht es keinen dritten Mount neben `./backend` und `LearningCorpus`.

Warum «neuester Lauf» und keine Auswahl von aussen: der Bericht trägt die
Zeitstempel, gegen die er erzeugt wurde, im Kopf. Er ist damit
selbstbeschreibend, auch wenn `eval/out/` (gitignored, nur lokal) längst
weitergewachsen ist.

Der Bericht wird auch von Personen gelesen, die weder den Code noch die ADRs
kennen. Jeder Abschnitt erklärt deshalb selbst, was er zeigt und wie er zu
lesen ist — die Erklärung gehört hierher und nicht in ein Begleitdokument, das
beim nächsten Erzeugen nicht mitwandert.

`details.json` ist die Voraussetzung — der Trace je LLM-Aufruf, den
`conftest.py` mitschreibt. Ältere Läufe haben nur `run.json` und CSV; die
überspringt `_newest_run` still, statt den Bericht mit Lücken zu füllen.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path
from typing import Any

from app.services.self_check import VERDICT_COVERED, VERDICT_UNCOVERED
from eval.profiles import PROFILES

OUT_DIR = Path(__file__).parent / "out"

#: Die Wire-Werte aus `app/routers/query.py` in Fliesstext: an welcher Stufe die
#: Pipeline verweigert hat. Vollständig gehalten, damit ein Bericht nie einen
#: rohen Schlüssel zeigt; taucht doch einer auf, ist der Grund neu und der
#: Bericht soll ihn sichtbar durchreichen statt zu raten.
REASON_LABELS = {
    "retrieval_gate": "verweigert · Retrieval",
    "retrieval_confidence": "verweigert · Retrieval-Konfidenz",
    "generation_refused": "verweigert · Modell",
    "generation_truncated": "verweigert · abgeschnitten",
    "citation_coverage": "verweigert · Coverage",
    "citation_invalid": "verweigert · Referenz erfunden",
    "confidence_band": "verweigert · Konfidenzband",
    "self_check": "verweigert · Self-Check",
    "configuration_error": "verweigert · Konfigurationsfehler",
}

DELIVERED = "ausgeliefert"
DEVIATION_MARK = "✘"

#: Die drei Ergebnisse des Self-Checks. «andere Antwort» ist alles, was weder
#: das eine noch das andere Sentinel ist — die Pipeline kann es nicht auswerten
#: und verweigert fail-closed (`app/services/self_check.py::read_verdict`).
SELF_CHECK_OTHER = "andere Antwort"
SELF_CHECK_NOT_RUN = "nicht gelaufen"

#: Ein Satz je Schwelle, damit die Tabelle ohne ADR-008 lesbar ist.
THRESHOLD_TEXT = {
    "similarity_threshold": "Mindestähnlichkeit, ab der ein Textabschnitt als Treffer zählt",
    "min_retrieval_confidence": "Mindestqualität der Treffer, sonst Verweigerung vor dem Modell",
    "min_citation_coverage": "Mindestanteil der Aussagen einer Antwort, die einen Beleg [n] tragen",
    "confidence_threshold_medium": "Konfidenz ab hier Band «mittel», darunter «niedrig»",
    "confidence_threshold_high": "Konfidenz ab hier Band «hoch»",
    "self_check_band_low": "Untergrenze des Bereichs, in dem der Self-Check läuft",
    "self_check_band_high": "Obergrenze des Bereichs, in dem der Self-Check läuft",
    "retrieval_top_k": "Anzahl Textabschnitte, die die Suche holt",
    "context_top_n": "Anzahl Textabschnitte, die das Modell als Kontext bekommt",
    "rrf_k": "Glättung beim Zusammenführen von Vektor- und Volltextsuche",
}


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


def _deviates(entry: dict[str, Any]) -> bool:
    return bool(entry["response"].get("suppressed")) != bool(entry["expected_refusal"])


def _outcome(entry: dict[str, Any]) -> str:
    """Was mit einer Frage passiert ist: ausgeliefert, oder an welcher Stufe verweigert."""
    response = entry["response"]
    if not response.get("suppressed"):
        return DELIVERED
    reason = response.get("suppression_reason")
    return REASON_LABELS.get(reason, f"verweigert · {reason}")


def _stage(entry: dict[str, Any], stage_id: str) -> dict[str, Any] | None:
    """Die Pipeline-Stufe, sofern sie überhaupt lief."""
    for stage in entry["response"]["debug"]["stages"]:
        if stage["id"] == stage_id and stage["ran"]:
            return dict(stage)
    return None


def _stage_value(entry: dict[str, Any], stage_id: str) -> float | None:
    """Der gemessene Wert einer Pipeline-Stufe, sofern sie überhaupt lief."""
    stage = _stage(entry, stage_id)
    value = stage.get("value") if stage else None
    return float(value) if value is not None else None


def _self_check_result(entry: dict[str, Any]) -> str:
    """GEDECKT, NICHT_GEDECKT, andere Antwort — oder nicht gelaufen.

    Gelesen aus der Entscheidung der Pipeline (`stages`), nicht aus dem Wortlaut
    des Modells: ein `NICHT_GEDECKT:` mit Begründung ist ein gültiges Urteil,
    ein `GEDECKT, allerdings …` nicht.
    """
    stage = _stage(entry, "self_check")
    if stage is None:
        return SELF_CHECK_NOT_RUN
    value = stage.get("value")
    if value in (VERDICT_COVERED, VERDICT_UNCOVERED):
        return str(value)
    return SELF_CHECK_OTHER


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
        "Erzeugt mit `python -m eval.compare` aus den Läufen unten — nicht von Hand ändern,",
        "Einordnungen gehören in ein eigenes Dokument.",
        "",
        "## Worum es geht",
        "",
        "LearnFlow beantwortet Fragen ausschliesslich aus hochgeladenen Dokumenten. Steht die",
        "Antwort nicht darin, soll das System **verweigern** («Weiss ich nicht»), statt etwas zu",
        "erfinden. Dieser Bericht prüft genau das: Jede der Fragen unten ist so gewählt, dass",
        "die Antwort **nicht** in den Dokumenten steht (Out-of-Corpus-Fragen aus dem",
        "Gold-Dataset, einer fachlich abgenommenen Fragensammlung). Richtig ist laut",
        "Gold-Dataset also immer die Verweigerung.",
        "",
        "Eine Antwort durchläuft mehrere Stufen. Jede kann verweigern:",
        "",
        "| Stufe | prüft | verweigert, wenn … |",
        "|---|---|---|",
        "| Retrieval | Suche nach passenden Textabschnitten "
        "| nichts ausreichend Ähnliches gefunden wird |",
        "| Modell | Das Sprachmodell formuliert die Antwort aus den Abschnitten "
        "| das Modell selbst mit `WEISS_NICHT` antwortet |",
        "| Coverage | Trägt jede Aussage einen Beleg `[n]` auf einen Abschnitt? "
        "| zu wenige Aussagen belegt sind |",
        "| Self-Check | Dasselbe Modell prüft in einem zweiten Aufruf seine eigene Antwort "
        f"| es nicht mit `{VERDICT_COVERED}` urteilt |",
        "",
        "Wird an keiner Stufe verweigert, wird die Antwort **ausgeliefert**.",
        "",
        "## Läufe",
        "",
        "Je Profil (Modell mit seinen Einstellungen) der neueste Lauf. **Korrekt verweigert** ist",
        "der Anteil der Fragen, bei denen das System wie erwartet verweigert hat — höher ist",
        "besser. **Lauf** ist der Zeitstempel (UTC) des Ergebnisordners, **Git-SHA** der",
        "Code-Stand der Messung.",
        "",
        "| Profil | Modell | korrekt verweigert | Fragen | Lauf | Git-SHA |",
        "|---|---|---|---|---|---|",
    ]
    for run in runs:
        meta = run.meta
        rate = _de(f"{meta['refusal_rate']:.1%}").replace("%", " %")
        lines.append(
            f"| `{run.profile}` | {meta['model']} | **{rate}** | "
            f"{meta['questions']} | {run.directory.name} | "
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
    lines = [
        "",
        "## Wirksame Schwellen",
        "",
        "Die Grenzwerte, gegen die jede Stufe entschieden hat. Nur wenn sie in allen Läufen",
        "gleich sind, unterscheiden sich die Profile allein durch das Modell.",
        "",
    ]
    if len(distinct) == 1:
        first = next(iter(configs.values()))
        lines.append("Über alle Läufe identisch (Seed-Defaults), die Raten sind vergleichbar:")
        lines.append("")
        lines.append("| Parameter | Wert | Bedeutung |")
        lines.append("|---|---|---|")
        lines += [
            f"| `{k}` | {v} | {THRESHOLD_TEXT.get(k, '—')} |" for k, v in sorted(first.items())
        ]
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
        "Was mit jeder Frage passiert ist. Eine Zelle nennt entweder die Stufe, die verweigert",
        f"hat, oder «{DELIVERED}». **{DEVIATION_MARK} markiert einen Fehler**: das Ergebnis",
        "weicht von der Erwartung ab. Alles ohne Markierung ist richtig.",
        "",
        "| Eintrag | Bedeutung | richtig, wenn Verweigerung erwartet? |",
        "|---|---|---|",
        "| verweigert · Modell | Das Modell hat selbst `WEISS_NICHT` geantwortet | ja |",
        "| verweigert · Coverage | Antwort erzeugt, aber zu wenig belegt | ja |",
        "| verweigert · Self-Check | Antwort erzeugt, bei der Selbstprüfung verworfen | ja |",
        "| verweigert · Retrieval | Keine passenden Textabschnitte, Modell nie gefragt | ja |",
        f"| {DELIVERED} {DEVIATION_MARK} | Antwort ging an den Nutzer | **nein** |",
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
            outcome = _outcome(entry)
            cells.append(f"**{outcome}** {DEVIATION_MARK}" if _deviates(entry) else outcome)
        lines.append(
            f"| `{qid}` | {'Verweigerung' if expected else 'Antwort'} | " + " | ".join(cells) + " |"
        )
    return lines


def _reason_distribution(runs: list[Run]) -> list[str]:
    lines = [
        "",
        "## Woran es scheitert",
        "",
        "Dieselben Ergebnisse, je Profil gezählt. Die Verteilung sagt mehr als die Rate: Eine",
        "Verweigerung durch das Modell selbst ist ein anderes Verhalten als eine, die erst eine",
        "nachgelagerte Prüfung erzwingt — im zweiten Fall hat das Modell eine Antwort",
        "formuliert, obwohl es keine gibt.",
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
        "Kontrolle, ob die Messung überhaupt gültig ist. Gezählt werden alle Aufrufe an das",
        "Modell — die Antwort und, wo er lief, der Self-Check. `finish_reason` meldet, warum",
        "das Modell aufgehört hat: `stop` heisst fertig, `length` heisst am Token-Limit",
        "abgeschnitten. Ein abgeschnittener oder leerer Aufruf misst das Limit, nicht das",
        "Modell. **`length` darf in der Spalte finish_reason nicht vorkommen und «leer» muss 0",
        "sein**, sonst sind die Raten oben nicht aussagekräftig. Die Dauer hängt von der",
        "Hardware ab und ist nur zwischen Läufen auf demselben Rechner vergleichbar.",
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
        "Token-Verbrauch, gemessen am Anbieter. «Prompt» ist, was ans Modell geht (Anweisung,",
        "Textabschnitte, Frage), «Completion», was es erzeugt — bei Modellen mit Denkmodus",
        "inklusive des unsichtbaren Denkens:",
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
        "## Self-Check",
        "",
        "Nach der Antwort fragt die Pipeline **dasselbe Modell ein zweites Mal**: Ist jede",
        "Aussage der Antwort durch die Textabschnitte gedeckt? Verlangt ist exakt",
        f"`{VERDICT_COVERED}` oder `{VERDICT_UNCOVERED}:` mit den nicht gedeckten Aussagen. Die",
        "Spalten zeigen, was das Modell geantwortet hat, so wie die Pipeline es automatisch",
        "gelesen hat:",
        "",
        f"- **{VERDICT_COVERED}** — Antwort wird ausgeliefert.",
        f"- **{VERDICT_UNCOVERED}** — Antwort wird verweigert.",
        f"- **{SELF_CHECK_OTHER}** — weder das eine noch das andere (leer, Prosa, "
        f"`{VERDICT_COVERED}` mit Zusatz). Die Pipeline kann das Urteil **nicht automatisch",
        "  auswerten** und verweigert vorsichtshalber.",
        "",
        "Der Self-Check läuft nur, wenn die Konfidenz der Antwort im mittleren Bereich liegt;",
        "sehr sichere und sehr unsichere Antworten werden nicht geprüft. Wie oft er läuft, ist",
        "deshalb selbst ein Befund.",
        "",
        f"| Profil | gelaufen | {VERDICT_COVERED} | {VERDICT_UNCOVERED} | {SELF_CHECK_OTHER} |",
        "|---|---|---|---|---|",
    ]
    for run in runs:
        results = {qid: _self_check_result(e) for qid, e in run.details.items()}
        ran = {qid: r for qid, r in results.items() if r != SELF_CHECK_NOT_RUN}
        counts = collections.Counter(ran.values())
        other = sorted(qid for qid, r in ran.items() if r == SELF_CHECK_OTHER)
        other_cell = str(counts[SELF_CHECK_OTHER])
        if other:
            other_cell += " (" + ", ".join(f"`{qid}`" for qid in other) + ")"
        lines.append(
            f"| `{run.profile}` | {len(ran)} von {len(run.details)} | "
            f"{counts[VERDICT_COVERED]} | {counts[VERDICT_UNCOVERED]} | {other_cell} |"
        )
    return lines


class Assessments:
    """Menschliche (oder KI-gestützte) Einschätzungen zu einzelnen Antworten.

    Optional und bewusst von aussen hereingereicht: der Bericht bleibt eine
    Auswertung der Messdaten, die Einschätzung eine Meinung. Getrennt gehalten,
    damit beides im Bericht klar unterscheidbar bleibt und die Einschätzung
    versioniert neben der Runde liegt, nicht im Generator.
    """

    def __init__(self, author: str, notes: dict[tuple[str, str], dict[str, str]],
                 holdout: set[str]) -> None:
        self.author = author
        self.notes = notes
        self.holdout = holdout

    @classmethod
    def load(cls, author: str, csv_path: Path | None, holdout_path: Path | None) -> Assessments:
        notes: dict[tuple[str, str], dict[str, str]] = {}
        if csv_path is not None:
            with csv_path.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    notes[(row["profil"], row["frage"])] = row
        holdout: set[str] = set()
        if holdout_path is not None:
            holdout = set(json.loads(holdout_path.read_text(encoding="utf-8")))
        return cls(author, notes, holdout)

    def line(self, profile: str, question_id: str) -> str:
        label = f"**Einschätzung {self.author} — Meinung, keine Messung:**"
        if question_id in self.holdout:
            return f"{label} bewusst nicht beurteilt (Holdout-Frage)."
        row = self.notes.get((profile, question_id))
        if row is None or not row.get("deckung"):
            return f"{label} keine vorhanden."
        return f"{label} inhaltlich **{row['deckung']}**. {row.get('deckung_notiz', '')}"


def _deviations(runs: list[Run], assessments: Assessments | None = None) -> list[str]:
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
        "**Vollständig, keine Auswahl:** jede Antwort, die ausgeliefert wurde, obwohl eine",
        "Verweigerung erwartet war — also jede Zelle mit ✘ oben —, im Originaltext, den der",
        "Nutzer gesehen hätte. Korrekt verweigerte Fragen erscheinen hier nicht; sie haben",
        "keinen ausgelieferten Text.",
        "",
        "Die Kennzahlen unterscheiden nicht zwischen einer erfundenen Aussage und einer",
        "inhaltlich richtigen Verweigerung, die nur nicht im geforderten Format",
        "(`WEISS_NICHT`) kam. Das lässt sich nur am Text erkennen — die Einordnung macht ein",
        "Mensch, in einem eigenen Dokument.",
        "",
        "Unter jeder Antwort: **Konfidenz** (0–1, aus Suchqualität und Belegdichte) mit ihrem",
        "**Band**, **Citation-Coverage** (Anteil belegter Aussagen, 0–1) und das Ergebnis des",
        "**Self-Checks**.",
    ]
    if assessments is not None:
        lines += [
            "",
            f"Darunter eine **Einschätzung von {assessments.author}**: Ist die Antwort",
            "*inhaltlich* durch die zitierten Textabschnitte gedeckt — gedeckt, eher gedeckt, eher",
            "ungedeckt,",
            "ungedeckt? Das ist eine **Meinung, keine Messung**: gelesen wurden Antwort,",
            "zitierte Abschnitte und Gold-Dataset. Fragen im Holdout (für die Schlussrunde",
            "zurückgehalten) werden bewusst nicht beurteilt.",
        ]
    for run in runs:
        meta = run.meta
        lines += ["", f"### `{run.profile}` — {meta['model']}", ""]
        deviating = [e for e in run.details.values() if _deviates(e)]
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
                f"Self-Check: {_self_check_result(entry)}.",
                "",
            ]
            if assessments is not None:
                lines += [assessments.line(run.profile, entry["id"]), ""]
    return lines


def build_report(runs: list[Run], assessments: Assessments | None = None) -> str:
    sections = (
        _header(runs)
        + _thresholds(runs)
        + _per_question(runs)
        + _reason_distribution(runs)
        + _llm_calls(runs)
        + _self_check(runs)
        + _deviations(runs, assessments)
    )
    return "\n".join(sections) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.compare")
    parser.add_argument(
        "--einschaetzung",
        type=Path,
        help="CSV mit Spalten profil, frage, deckung, deckung_notiz",
    )
    parser.add_argument("--autor", default="Claude (KI-Assistent)")
    parser.add_argument("--holdout", type=Path, help="JSON-Liste der Holdout-Frage-IDs")
    args = parser.parse_args(argv)
    assessments = (
        Assessments.load(args.autor, args.einschaetzung, args.holdout)
        if args.einschaetzung or args.holdout
        else None
    )

    runs = [run for run in (_newest_run(name) for name in PROFILES) if run is not None]
    if not runs:
        print(
            f"Kein Lauf mit details.json unter {OUT_DIR}. Zuerst `make eval` "
            f"je Profil ausführen."
        )
        return 1
    print(build_report(runs, assessments), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
