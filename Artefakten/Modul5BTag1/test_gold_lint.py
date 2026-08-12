"""Tests für die Lint-Regeln (ohne SDK, ohne Netz).

Ausführen aus diesem Verzeichnis:  pytest
"""

import pytest

from gold_lint import (
    DISTRIBUTION_TOLERANCE,
    PILOT_MIN_ENTRIES,
    format_report,
    lint_dataset,
    lint_entry,
    parse_entries,
)


def make_entry(**overrides):
    """Ein gültiger In-Corpus-Eintrag; einzelne Felder gezielt überschreibbar."""
    entry = {
        "id": "GBL-01",
        "category": "in_corpus",
        "question": "Was umfasst der Grundbedarf für den Lebensunterhalt?",
        "expected_refusal": False,
        "reference_answer": "Nahrung, Kleider, Energieverbrauch, ...",
        "expected_source": "Kapitel Grundbedarf (GBL)",
        "expected_source_id": "chunk-42",
        "version_sensitive": False,
    }
    entry.update(overrides)
    return entry


def problems(entry) -> str:
    return " | ".join(lint_entry(entry).problems)


def test_valid_entry_has_no_problems():
    assert lint_entry(make_entry()).ok


def test_valid_refusal_entry_has_no_problems():
    entry = make_entry(
        id="OOC-01",
        category="out_of_corpus",
        expected_refusal=True,
        reference_answer=None,
        expected_source=None,
        expected_source_id=None,
    )
    assert lint_entry(entry).ok


def test_missing_required_field_is_reported():
    entry = make_entry()
    del entry["question"]
    assert "Pflichtfeld fehlt: question" in problems(entry)


def test_unknown_category_is_reported():
    assert "ungültige category" in problems(make_entry(category="edge_case"))


def test_out_of_corpus_must_expect_refusal():
    entry = make_entry(category="out_of_corpus", expected_refusal=False)
    assert "widerspricht dem Refusal-Gate" in problems(entry)


def test_answerable_entry_needs_reference_answer():
    assert "ohne reference_answer" in problems(make_entry(reference_answer=None))


def test_refusal_entry_must_not_carry_reference_answer():
    entry = make_entry(
        category="out_of_corpus", expected_refusal=True, reference_answer="CHF 1061"
    )
    assert "trotzdem reference_answer gesetzt" in problems(entry)


@pytest.mark.parametrize("value", ["TBD", "todo", "", None])
def test_placeholder_source_id_blocks_ci(value):
    assert "expected_source_id" in problems(make_entry(expected_source_id=value))


def test_source_id_not_required_for_refusal_entries():
    entry = make_entry(
        category="out_of_corpus",
        expected_refusal=True,
        reference_answer=None,
        expected_source_id="TBD",
    )
    assert lint_entry(entry).ok


def test_non_boolean_refusal_is_reported():
    assert "expected_refusal muss true/false sein" in problems(make_entry(expected_refusal="ja"))


def test_non_mapping_entry_does_not_crash():
    report = lint_entry("GBL-01")
    assert not report.ok
    assert "kein Mapping" in report.problems[0]


def test_duplicate_ids_are_reported():
    report = lint_dataset([make_entry(), make_entry()])
    assert any("doppelte IDs: GBL-01" in finding for finding in report.findings)


def test_balanced_dataset_reports_no_distribution_finding():
    entries = (
        [make_entry(id=f"IN-{i}") for i in range(60)]
        + [
            make_entry(
                id=f"OOC-{i}",
                category="out_of_corpus",
                expected_refusal=True,
                reference_answer=None,
            )
            for i in range(25)
        ]
        + [make_entry(id=f"ADV-{i}", category="adversarial") for i in range(15)]
    )
    report = lint_dataset(entries)
    assert report.ok_count == len(entries)
    assert not report.findings


def test_skewed_distribution_is_reported():
    entries = [make_entry(id=f"IN-{i}") for i in range(100)]
    report = lint_dataset(entries)
    assert any(finding.startswith("Verteilung in_corpus") for finding in report.findings)
    assert any(finding.startswith("Verteilung out_of_corpus") for finding in report.findings)


def test_distribution_ignores_unparseable_entries():
    entries = (
        [make_entry(id=f"IN-{i}") for i in range(6)]
        + [
            make_entry(
                id=f"OOC-{i}",
                category="out_of_corpus",
                expected_refusal=True,
                reference_answer=None,
            )
            for i in range(3)
        ]
        + [make_entry(id="ADV-0", category="adversarial")]
    )
    balanced = lint_dataset(entries)
    assert not any(finding.startswith("Verteilung") for finding in balanced.findings)

    # Dieselben zehn Einträge plus drei kaputte: die Verteilung bleibt 60/30/10
    entries += parse_entries("- id: KAPUTT-1\n  question: \"a „b\" c\"\n") * 3
    with_broken = lint_dataset(entries)
    assert not any(finding.startswith("Verteilung") for finding in with_broken.findings)


def test_distribution_tolerance_is_not_exceeded_by_the_seed_split():
    # 58/27/15 wie im Seed-Dataset — innerhalb der Toleranz, also kein Befund
    assert abs(0.58 - 0.60) <= DISTRIBUTION_TOLERANCE
    assert abs(0.27 - 0.25) <= DISTRIBUTION_TOLERANCE


def test_single_entry_gets_no_distribution_finding():
    report = lint_dataset([make_entry()])
    assert not any(finding.startswith("Verteilung") for finding in report.findings)


def test_small_dataset_is_flagged_against_pilot_size():
    report = lint_dataset([make_entry(id=f"IN-{i}") for i in range(26)])
    assert any(str(PILOT_MIN_ENTRIES) in finding for finding in report.findings)


def test_parse_entries_reads_yaml_fence_from_markdown():
    text = """# Dataset

Prosa, die kein YAML ist.

```yaml
- id: GBL-01
  category: in_corpus
  question: "Frage?"
  expected_refusal: false
```

Nachwort.
"""
    entries = parse_entries(text)
    assert [entry["id"] for entry in entries] == ["GBL-01"]


def test_parse_entries_accepts_raw_yaml_list():
    entries = parse_entries("- id: A\n  category: in_corpus\n")
    assert entries[0]["category"] == "in_corpus"


def test_parse_entries_wraps_single_mapping():
    assert parse_entries("id: A\ncategory: in_corpus\n") == [{"id": "A", "category": "in_corpus"}]


def test_parse_entries_rejects_yaml_without_any_record():
    with pytest.raises(ValueError, match="YAML nicht lesbar"):
        parse_entries("id: A\n  bad: [")


def test_one_broken_record_does_not_hide_the_others():
    # Typografische Anführungszeichen in einem "..."-String — genau der Fehler,
    # der in einem der Seed-Datasets steckt.
    text = """```yaml
- id: OK-01
  category: in_corpus
  question: "Frage?"
  expected_refusal: true
- id: KAPUTT-01
  category: in_corpus
  question: "Wer gilt als „Anbieter" eines KI-Systems?"
  expected_refusal: true
- id: OK-02
  category: in_corpus
  question: "Andere Frage?"
  expected_refusal: true
```"""
    report = lint_dataset(parse_entries(text))
    by_id = {entry.entry_id: entry for entry in report.entries}
    assert set(by_id) == {"OK-01", "KAPUTT-01", "OK-02"}
    assert by_id["OK-01"].ok
    assert by_id["OK-02"].ok
    assert "YAML nicht lesbar" in by_id["KAPUTT-01"].problems[0]


def test_format_report_lists_counts_and_findings():
    text = format_report(lint_dataset([make_entry(), make_entry(expected_source_id="TBD")]))
    assert text.startswith("2 Einträge · 1 ohne Befund · 1 mit Befund")
    assert "GBL-01: expected_source_id" in text
    assert "Dataset: doppelte IDs" in text
