"""Lint-Regeln für das LearnFlow Gold-Eval-Dataset (ADR-009, Enabler EVAL-1).

Reine Logik, bewusst ohne Abhängigkeit zum claude_agent_sdk: so ist die
Regelmenge isoliert testbar (DoD-Kriterium 3) und lässt sich später auch
ausserhalb des Agenten nutzen — etwa als CI-Vorprüfung, bevor das Dataset im
Eval-Gate (EVAL-3) verbindlich wird.

Die Regeln prüfen *Form und Konsistenz*, nicht fachliche Korrektheit: ob eine
Referenzantwort inhaltlich stimmt, entscheidet weiterhin der Bereichs-
verantwortliche.
"""

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

import yaml

# Kategorien und Zielverteilung aus ADR-009 ("~60/25/15").
CATEGORIES = ("in_corpus", "out_of_corpus", "adversarial")
TARGET_DISTRIBUTION = {"in_corpus": 0.60, "out_of_corpus": 0.25, "adversarial": 0.15}

# ADR-009 schreibt nur "~" — ohne Toleranz meldet jede Datei eine Abweichung.
# 10 Prozentpunkte lassen die 58/27/15 des Seeds durch und schlagen bei einer
# echten Schieflage (z. B. 80 % in_corpus) an.
DISTRIBUTION_TOLERANCE = 0.10

# Unter dieser Menge ist ein Anteil keine Aussage — wer einen einzelnen Eintrag
# prüft, soll keine Verteilungs-Befunde zurückbekommen.
DISTRIBUTION_MIN_ENTRIES = 10

# Pilot-Umfang laut ADR-009: ~80-100 Fragen.
PILOT_MIN_ENTRIES = 80

# Ohne diese Felder ist ein Eintrag für das Harness (EVAL-2) unbrauchbar.
REQUIRED_FIELDS = ("id", "category", "question", "expected_refusal")

# Platzhalter, mit denen die Seed-Datasets erstellt wurden.
PLACEHOLDERS = frozenset({"tbd", "todo", "?", ""})


# Beginn eines Top-Level-Listeneintrags, für das satzweise Parsen.
_RECORD_START = re.compile(r"^- ", re.MULTILINE)
_RECORD_ID = re.compile(r"^-\s*id:\s*(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class BrokenEntry:
    """Ein Eintrag, dessen YAML sich nicht lesen lässt.

    Ein einziges falsches Anführungszeichen darf nicht die Prüfung der übrigen
    Einträge verhindern — der kaputte Satz wird als eigener Befund gemeldet.
    """

    entry_id: str
    reason: str


@dataclass(frozen=True)
class EntryReport:
    """Befunde zu genau einem Dataset-Eintrag."""

    entry_id: str
    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.problems


@dataclass(frozen=True)
class DatasetReport:
    """Befunde zu einem ganzen Dataset: pro Eintrag plus dateiweite Regeln."""

    entries: tuple[EntryReport, ...]
    findings: tuple[str, ...]

    @property
    def ok_count(self) -> int:
        return sum(1 for entry in self.entries if entry.ok)


def parse_entries(text: str) -> list[object]:
    """Liest Einträge aus rohem YAML oder aus einem Markdown-Dokument.

    Die Seed-Datasets liegen als Markdown mit einem ```yaml-Block vor, der
    Rest der Datei ist Prosa. Deshalb werden Code-Fences extrahiert, sobald
    welche vorhanden sind — sonst gilt der ganze Text als YAML.

    Scheitert das Dokument als Ganzes, wird satzweise erneut geparst: die
    lesbaren Einträge werden geprüft, die kaputten als `BrokenEntry` gemeldet.
    """
    blocks = _yaml_blocks(text)
    payload = "\n".join(blocks) if blocks else text

    try:
        data = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        records = _parse_record_wise(payload)
        if records:
            return records
        raise ValueError(f"YAML nicht lesbar: {exc}") from exc

    if data is None:
        return []
    if isinstance(data, dict):  # ein einzelner Eintrag ohne Listen-Strich
        return [data]
    if not isinstance(data, list):
        raise ValueError(f"YAML ergibt {type(data).__name__}, erwartet wird eine Liste von Einträgen")
    return data


def lint_entry(entry: object) -> EntryReport:
    """Prüft einen Eintrag gegen das Schema aus ADR-009."""
    if isinstance(entry, BrokenEntry):
        return EntryReport(entry.entry_id, (f"YAML nicht lesbar: {entry.reason}",))
    if not isinstance(entry, dict):
        return EntryReport("?", (f"kein Mapping, sondern {type(entry).__name__}",))

    entry_id = str(entry.get("id") or "?")
    problems: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in entry:
            problems.append(f"Pflichtfeld fehlt: {field}")

    category = entry.get("category")
    if "category" in entry and category not in CATEGORIES:
        problems.append(f"ungültige category: {category!r} (erlaubt: {', '.join(CATEGORIES)})")

    if _is_blank(entry.get("question")):
        problems.append("question ist leer")

    refusal = entry.get("expected_refusal")
    if "expected_refusal" in entry and not isinstance(refusal, bool):
        problems.append(f"expected_refusal muss true/false sein, ist {refusal!r}")

    if "version_sensitive" in entry and not isinstance(entry.get("version_sensitive"), bool):
        problems.append(f"version_sensitive muss true/false sein, ist {entry['version_sensitive']!r}")

    # Out-of-Corpus misst die "Weiss ich nicht"-Quote (ADR-009, ≥ 90 %) — ein
    # solcher Eintrag mit expected_refusal=false wäre ein Messfehler im Gate.
    if category == "out_of_corpus" and refusal is False:
        problems.append("out_of_corpus mit expected_refusal: false — widerspricht dem Refusal-Gate")

    if refusal is False and _is_blank(entry.get("reference_answer")):
        problems.append("beantwortbare Frage ohne reference_answer")

    # Fail-closed (ADR-008): eine unterdrückte Antwort liefert nie generierten
    # Inhalt. Eine Referenzantwort daneben ist ein Widerspruch in der Erwartung.
    if refusal is True and not _is_blank(entry.get("reference_answer")):
        problems.append("expected_refusal: true, trotzdem reference_answer gesetzt")

    # Nur beantwortbare Fragen brauchen Quell-Chunk-IDs (ADR-009).
    if refusal is False and _is_placeholder(entry.get("expected_source_id")):
        problems.append("expected_source_id fehlt oder ist TBD — nicht CI-tauglich")

    return EntryReport(entry_id, tuple(problems))


def lint_dataset(entries: Sequence[object]) -> DatasetReport:
    """Prüft alle Einträge plus die dateiweiten Regeln (IDs, Verteilung, Umfang)."""
    reports = tuple(lint_entry(entry) for entry in entries)
    findings: list[str] = []

    duplicates = sorted(
        entry_id
        for entry_id, count in Counter(report.entry_id for report in reports).items()
        if count > 1 and entry_id != "?"
    )
    if duplicates:
        findings.append(f"doppelte IDs: {', '.join(duplicates)}")

    # Nur eingeordnete Einträge zählen: ein nicht lesbarer Eintrag hat keine
    # Kategorie und würde sonst alle Anteile nach unten ziehen.
    counts = Counter(
        entry["category"]
        for entry in entries
        if isinstance(entry, dict) and entry.get("category") in CATEGORIES
    )
    categorised = sum(counts.values())
    if categorised >= DISTRIBUTION_MIN_ENTRIES:
        for category, target in TARGET_DISTRIBUTION.items():
            share = counts.get(category, 0) / categorised
            if abs(share - target) > DISTRIBUTION_TOLERANCE:
                findings.append(
                    f"Verteilung {category}: {share:.0%} (Ziel ~{target:.0%}, "
                    f"Toleranz ±{DISTRIBUTION_TOLERANCE:.0%})"
                )

    total = len(reports)

    if 0 < total < PILOT_MIN_ENTRIES:
        findings.append(f"Umfang {total} Fragen — ADR-009 nennt ~{PILOT_MIN_ENTRIES}-100 für den Pilot")

    return DatasetReport(reports, tuple(findings))


def format_report(report: DatasetReport) -> str:
    """Kompakter Text für den Agent-Loop — eine Zeile pro Befund."""
    total = len(report.entries)
    noun = "Eintrag" if total == 1 else "Einträge"
    lines = [f"{total} {noun} · {report.ok_count} ohne Befund · {total - report.ok_count} mit Befund"]

    for entry in report.entries:
        for problem in entry.problems:
            lines.append(f"{entry.entry_id}: {problem}")

    for finding in report.findings:
        lines.append(f"Dataset: {finding}")

    return "\n".join(lines)


def _parse_record_wise(payload: str) -> list[object]:
    """Parst jeden Top-Level-Listeneintrag einzeln; kaputte werden markiert."""
    starts = [match.start() for match in _RECORD_START.finditer(payload)]
    if not starts:
        return []

    bounds = list(zip(starts, starts[1:] + [len(payload)]))
    entries: list[object] = []

    for start, end in bounds:
        record = payload[start:end]
        try:
            parsed = yaml.safe_load(record)
        except yaml.YAMLError as exc:
            entries.append(BrokenEntry(_record_id(record), _first_line(str(exc))))
            continue
        # Ein "- ..."-Block ergibt eine Liste mit genau einem Element.
        entries.extend(parsed if isinstance(parsed, list) else [parsed])

    return entries


def _record_id(record: str) -> str:
    match = _RECORD_ID.search(record)
    return match.group(1).strip().strip("\"'") if match else "?"


def _first_line(message: str) -> str:
    return message.splitlines()[0].strip() if message.strip() else "unbekannter YAML-Fehler"


def _yaml_blocks(text: str) -> list[str]:
    """Inhalt aller ```yaml-Fences, in Reihenfolge des Auftretens."""
    blocks: list[str] = []
    current: list[str] | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if current is None:
            if stripped.startswith("```") and stripped[3:].strip().lower() in ("yaml", "yml"):
                current = []
        elif stripped.startswith("```"):
            blocks.append("\n".join(current))
            current = None
        else:
            current.append(line)

    if current:  # unbalancierter Fence am Dateiende
        blocks.append("\n".join(current))
    return blocks


def _is_blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _is_placeholder(value: object) -> bool:
    if value is None:
        return True
    return str(value).strip().lower() in PLACEHOLDERS
