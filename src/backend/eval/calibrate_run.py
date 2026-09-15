"""T-57: Schicht B — echte Läufe (ADR-009 calibration loop).

Ruft `generate_answer()`, `check_citations()` und `run_self_check()` direkt auf statt über
`POST /api/query` (`app/routers/query.py`): der Router triggert Stufe 3 nur innerhalb des
`self_check_band`, AC 5 verlangt sie aber für *jede* generierte Antwort (Band effektiv
`[0,1]`) — nur so ist `self_check_band_low/high` später (Schicht C, `eval/
calibrate_report.py`) reine Arithmetik auf einem bereits aufgezeichneten Verdikt statt eine
Entscheidung, die ein zweites Mal nachgeholt werden müsste.

Ein echter Lauf kostet einen LLM-Aufruf (Generierung) plus, erzwungen, einen zweiten
(Self-Check) — pro **eindeutigem** `(question_id, context_chunk_ids)`-Paar, nicht pro
Parameterkombination: verschiedene `(A1, A2)`-Kandidaten erzeugen für dieselbe Frage oft
denselben Kontext, und `eval/calibrate_grid.py::pre_generation_outcome` liefert dafür schon
die geordnete Chunk-Id-Tupel, die den Cache-Schlüssel bilden (AC 4).
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Chunk
from app.services.confidence import CitationDetail, check_citations
from app.services.generation import GenerationResult, generate_answer
from app.services.retrieval import RetrievalHit
from app.services.self_check import SelfCheckResult, run_self_check

DedupKey = tuple[str, tuple[str, ...]]


def dedup_key(question_id: str, context: Sequence[RetrievalHit]) -> DedupKey:
    """`(question_id, ordered chunk ids)` — order matters (T-57, AC 4).

    Not a sorted set: the context order is the numbering the generation prompt shows the
    model (`render_context`, `app/services/generation.py`) and that citation indices refer
    to. Two `(A1, A2)` candidates that retrieve the same chunk *set* in a different order
    (a different `rrf_k` can do that even when `retrieval_top_k`/`context_top_n` agree) would
    otherwise collide on one cached answer that does not match either prompt.
    """
    return (question_id, tuple(str(hit.chunk_id) for hit in context))


@dataclasses.dataclass(frozen=True)
class RunResult:
    """One real run: a generated answer plus the forced self-check on it.

    `None` fields mean the corresponding stage never produced anything — a refused or
    truncated generation has no citations and no self-check to run against (mirrors
    `app/routers/query.py`'s own `citation`/`self_check` being `None` in those cases).
    """

    question_id: str
    context_chunk_ids: tuple[str, ...]
    answer: str | None
    truncated: bool
    citation: CitationDetail | None
    self_check: SelfCheckResult | None


async def chunk_contents(db: AsyncSession, chunk_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Chunk text by id — the one thing the snapshot deliberately does not carry."""
    if not chunk_ids:
        return {}
    result = await db.execute(select(Chunk.id, Chunk.content).where(Chunk.id.in_(chunk_ids)))
    return {row.id: row.content for row in result.all()}


def hydrate_context(
    context: Sequence[RetrievalHit], contents: dict[uuid.UUID, str]
) -> list[RetrievalHit]:
    """Replace the empty `content` snapshot rows carry with the real chunk text.

    `dataclasses.replace`, not a second `RetrievalHit` construction: keeps every other field
    (`score`, `rrf_score`, the ranks) exactly as `context_for()` computed it — only `content`
    was ever a placeholder (`eval/calibrate_snapshot.py::snapshot_row_as_hit_dict`).
    """
    return [
        dataclasses.replace(hit, content=contents.get(hit.chunk_id, hit.content))
        for hit in context
    ]


async def run_once(
    question: str, question_id: str, context: Sequence[RetrievalHit]
) -> RunResult:
    """One real generation, plus a forced self-check on any delivered answer (AC 5).

    Mirrors the shape of `app/routers/query.py`'s pipeline (generation → citation check →
    self-check) but without the router's band gate on stage 3, and without persisting an
    `answers` row — the sweep reads nothing back from the database that it wrote itself.
    """
    context_chunk_ids = tuple(str(hit.chunk_id) for hit in context)
    generation: GenerationResult = await generate_answer(question, context)

    if generation.truncated or generation.answer is None:
        return RunResult(
            question_id=question_id,
            context_chunk_ids=context_chunk_ids,
            answer=None,
            truncated=generation.truncated,
            citation=None,
            self_check=None,
        )

    citation = check_citations(generation.answer, len(context))
    # Erzwungen, unabhängig vom Komposit-Score (AC 5) — anders als
    # `app/routers/query.py`, das nur innerhalb von `self_check_band` aufruft.
    self_check = await run_self_check(question, generation.answer, context)

    return RunResult(
        question_id=question_id,
        context_chunk_ids=context_chunk_ids,
        answer=generation.answer,
        truncated=False,
        citation=citation,
        self_check=self_check,
    )


def _citation_as_dict(detail: CitationDetail | None) -> dict[str, Any] | None:
    return None if detail is None else dataclasses.asdict(detail)


def _self_check_as_dict(result: SelfCheckResult | None) -> dict[str, Any] | None:
    return None if result is None else dataclasses.asdict(result)


def write_runs(results: list[RunResult], out_dir: pathlib.Path) -> pathlib.Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "runs.json"
    payload = {
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ"),
        "note": (
            "Jede Generierung ist eine Stichprobe von 1 -- TEMPERATURE=0.0 macht die "
            "Generierung nicht deterministisch, siehe eval/calibrate_report.py."
        ),
        "runs": [
            {
                "question_id": r.question_id,
                "context_chunk_ids": list(r.context_chunk_ids),
                "answer": r.answer,
                "truncated": r.truncated,
                "citation": _citation_as_dict(r.citation),
                "self_check": _self_check_as_dict(r.self_check),
            }
            for r in results
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_runs(path: pathlib.Path) -> dict[DedupKey, RunResult]:
    """Liest ein `runs.json` zurück -- Gegenstück zu `write_runs()`.

    Erlaubt, `eval/calibrate_report.py` erneut über einen bereits bezahlten Schicht-B-Lauf
    laufen zu lassen (z. B. nach einer Korrektur an der Auswertung selbst), ohne die echten
    Läufe zu wiederholen.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    results: dict[DedupKey, RunResult] = {}
    for entry in raw["runs"]:
        citation = (
            CitationDetail(
                coverage=entry["citation"]["coverage"],
                segments=entry["citation"]["segments"],
                covered=entry["citation"]["covered"],
                referenced=tuple(entry["citation"]["referenced"]),
                fabricated=tuple(entry["citation"]["fabricated"]),
                valid=entry["citation"]["valid"],
            )
            if entry["citation"] is not None
            else None
        )
        self_check = (
            SelfCheckResult(
                passed=entry["self_check"]["passed"],
                verdict_parsed=entry["self_check"]["verdict_parsed"],
                uncovered=entry["self_check"]["uncovered"],
                prompt=entry["self_check"]["prompt"],
                raw_response=entry["self_check"]["raw_response"],
            )
            if entry["self_check"] is not None
            else None
        )
        context_chunk_ids = tuple(entry["context_chunk_ids"])
        result = RunResult(
            question_id=entry["question_id"],
            context_chunk_ids=context_chunk_ids,
            answer=entry["answer"],
            truncated=entry["truncated"],
            citation=citation,
            self_check=self_check,
        )
        results[(entry["question_id"], context_chunk_ids)] = result
    return results
