"""The gold eval dataset is loadable and internally consistent (T-47).

The dataset is the expectation the eval measures against, so a broken or
inconsistent file makes every eval result meaningless -- and does so quietly:
an unresolvable source reference looks exactly like a retrieval miss. Three
questions in the EU AI Act seed sat in the repo as invalid YAML until this
file was consolidated, which is the failure mode these tests close.

The file lives in LearningCorpus/ next to the corpus PDFs, outside the backend
image. docker-compose mounts it read-only into the api container so the same
test runs there and in CI, where the checkout has the whole repo.
"""

import pathlib

import pypdf
import pytest
import yaml

from app.services.parsing import DOCX_CONTENT_TYPE, MARKDOWN_CONTENT_TYPE, PDF_CONTENT_TYPE

DATASET_NAME = "gold-eval-dataset.yaml"
CATEGORIES = {"in_corpus", "out_of_corpus", "adversarial"}
QUESTION_FIELDS = {
    "id",
    "corpus",
    "category",
    "question",
    "expected_refusal",
    "reference_answer",
    "expected_source",
    "version_sensitive",
    "notes",
}
# parsing.py fills exactly one of page/heading per content type, never both.
ANCHOR_BY_CONTENT_TYPE = {
    PDF_CONTENT_TYPE: "pages",
    DOCX_CONTENT_TYPE: "headings",
    MARKDOWN_CONTENT_TYPE: "headings",
}


def _corpus_dir() -> pathlib.Path:
    """Walk up until LearningCorpus/ turns up.

    Not a fixed number of parents: from src/backend/tests that is three levels,
    but in the api container the mount sits at /LearningCorpus and there are
    only two levels above /app/tests to walk.
    """
    here = pathlib.Path(__file__).resolve()
    for base in (here, *here.parents):
        candidate = base / "LearningCorpus"
        if (candidate / DATASET_NAME).is_file():
            return candidate
    raise AssertionError(
        f"{DATASET_NAME} not found. Outside CI the api container needs the "
        "LearningCorpus mount from docker-compose.yml."
    )


@pytest.fixture(scope="module")
def corpus_dir() -> pathlib.Path:
    return _corpus_dir()


@pytest.fixture(scope="module")
def dataset(corpus_dir: pathlib.Path) -> dict:
    """One safe_load, no markdown scraping -- that is the point (T-47)."""
    with (corpus_dir / DATASET_NAME).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_loads_with_a_single_parser_call(dataset: dict) -> None:
    assert dataset["version"] == 1
    assert dataset["corpora"]
    assert dataset["questions"]


def test_every_corpus_names_a_document_that_exists(
    dataset: dict, corpus_dir: pathlib.Path
) -> None:
    for key, corpus in dataset["corpora"].items():
        assert (corpus_dir / corpus["document"]).is_file(), f"{key}: document missing"
        assert corpus["title"]


def test_corpus_anchor_matches_its_content_type(dataset: dict) -> None:
    """A page reference into a .docx would be unresolvable: parsing.py leaves
    page NULL there and fills heading instead."""
    for key, corpus in dataset["corpora"].items():
        expected = ANCHOR_BY_CONTENT_TYPE.get(corpus["content_type"])
        assert expected is not None, f"{key}: content type the parser does not support"
        assert corpus["anchor"] == expected, f"{key}: anchor does not match content type"


def test_question_ids_are_unique(dataset: dict) -> None:
    ids = [q["id"] for q in dataset["questions"]]

    assert len(ids) == len(set(ids))


def test_questions_carry_exactly_the_declared_fields(dataset: dict) -> None:
    for question in dataset["questions"]:
        assert set(question) == QUESTION_FIELDS, f"{question.get('id')}: field mismatch"
        assert question["category"] in CATEGORIES
        assert question["corpus"] in dataset["corpora"]
        assert question["question"].strip()


def test_expected_source_id_is_gone(dataset: dict) -> None:
    """Chunk UUIDs point nowhere after a re-index -- the field must not come back."""
    assert not any("expected_source_id" in q for q in dataset["questions"])


def test_refusals_carry_no_answer_and_no_source(dataset: dict) -> None:
    for question in dataset["questions"]:
        if question["expected_refusal"]:
            assert question["reference_answer"] is None, question["id"]
            assert question["expected_source"] is None, question["id"]
        else:
            assert question["reference_answer"], question["id"]


def test_out_of_corpus_questions_expect_a_refusal(dataset: dict) -> None:
    for question in dataset["questions"]:
        if question["category"] == "out_of_corpus":
            assert question["expected_refusal"], question["id"]


def test_sources_use_the_anchor_their_corpus_declares(dataset: dict) -> None:
    for question in dataset["questions"]:
        source = question["expected_source"]
        if source is None:
            continue
        anchor = dataset["corpora"][question["corpus"]]["anchor"]
        other = "headings" if anchor == "pages" else "pages"

        assert anchor in source, f"{question['id']}: missing {anchor}"
        assert other not in source, f"{question['id']}: carries {other} as well"
        assert source["locator"].strip(), f"{question['id']}: empty locator"


def test_page_references_exist_in_the_pdf(dataset: dict, corpus_dir: pathlib.Path) -> None:
    """Guards the trap the seeds fell into: they cited printed page numbers,
    while parsing.py counts PDF pages from 1 (the SAMW guide differs by two)."""
    page_counts = {
        key: len(pypdf.PdfReader(corpus_dir / corpus["document"]).pages)
        for key, corpus in dataset["corpora"].items()
        if corpus["anchor"] == "pages"
    }

    for question in dataset["questions"]:
        source = question["expected_source"]
        if source is None or not source.get("pages"):
            continue
        for page in source["pages"]:
            assert isinstance(page, int)
            assert 1 <= page <= page_counts[question["corpus"]], (
                f"{question['id']}: page {page} outside the document"
            )
