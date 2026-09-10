"""T-28: out-of-corpus refusal rate against the real, indexed LearningCorpus —
the release gate ADR-009 requires (>= 90% "Weiss ich nicht"). Not yet a CI job
(T-53, #110 — no OPENAI_API_KEY secret exists in the repo); run manually via
`make eval`.

Deliberately narrow: this exercises only the two deterministic gates and the
LLM's own refusal (`generation_refused`), because an out-of-corpus question never
reaches stage 3 (composite confidence / self-check) — confirmed against the live
stack in the calibration note on #35 (`suppression_reason: retrieval_gate`,
`llm_calls: []`, stages 2/2b/3 all `ran=false`). In-corpus reliability
(hallucination rate, false-suppression) needs the gold dataset's in_corpus
questions and is a separate, later slice of ADR-009.

Since T-55 the run happens in-process against the ASGI app, inside a
transaction that is rolled back — see `conftest.py` for why. Precondition is
therefore only a reachable database with the corpus indexed
(`make up && make seed && make seed-corpus`), not a stack serving HTTP.
"""

import csv
import json
import os
from typing import Any

import httpx
import pytest

from eval.gold_dataset import assert_corpus_is_indexed_async, load_out_of_corpus_questions
from eval.profiles import Profile
from seed_users import USERS

# Admin, not a knowledge_owner or learner: `debug` in the response (self_check_ran,
# per-chunk scores) is only populated for the admin role. The calibration note on
# #35 asks for this harness to capture it so a later in-corpus extension does not
# have to re-derive that decision. Also the role GET /documents needs below.
_ADMIN = next(u for u in USERS if u["role"] == "admin")
EMAIL = os.environ.get("E2E_ADMIN_EMAIL", _ADMIN["email"])
PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", _ADMIN["password"])

REFUSAL_RATE_GATE = 0.90  # ADR-009 / issue #35, DoD Kriterium 4

# `configuration_error` is /query turning an unreadable threshold row into a safe
# "Weiss ich nicht" (ADR-008) rather than a 500 — correct for a learner, but not a
# refusal this gate should credit: it says nothing about retrieval, and a fully
# broken pipeline would score 100% on it. Excluded from what counts as "refused".
CONFIGURATION_ERROR = "configuration_error"

CSV_COLUMNS = [
    "id",
    "expected_refusal",
    "suppressed",
    "suppression_reason",
    "confidence_score",
    "confidence_band",
    "retrieval_score",
    "citation_coverage",
    "self_check_ran",
    "self_check_verdict",
]


@pytest.fixture
async def token(client: httpx.AsyncClient) -> str:
    """No 429 handling any more: the limiter is off for the in-process run
    (`conftest.py`), so the 5-logins-per-minute window that this fixture used to
    trip over — shared with seed_corpus.py and any e2e run in the same minute —
    cannot apply."""
    r = await client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def _write_run_json(
    out_dir: Any,
    profile: Profile,
    measured_config: dict[str, object],
    refusal_rate: float,
    total: int,
    mismatches: list[tuple[str, str, bool, str | None]],
) -> None:
    """The record that makes a number readable three months later.

    The path already carries profile and timestamp, but a path is metadata that
    does not survive a copy. Until T-55 nothing at all recorded what a run was
    measured against, and the three runs of 2026-09-09 could only be told apart
    because the files had been renamed by hand.
    """
    (out_dir / "run.json").write_text(
        json.dumps(
            {
                "profile": profile.name,
                "model": profile.model,
                "gated": profile.gated,
                "overrides": {
                    "timeout_seconds": profile.timeout_seconds,
                    "max_answer_tokens": profile.max_answer_tokens,
                    "self_check_timeout_seconds": profile.self_check_timeout_seconds,
                    "max_verdict_tokens": profile.max_verdict_tokens,
                    "extra_completion_kwargs": profile.extra_completion_kwargs,
                },
                "measured_config": {k: str(v) for k, v in measured_config.items()},
                "refusal_rate": round(refusal_rate, 4),
                "questions": total,
                "mismatches": [
                    {"id": qid, "question": q, "reason": reason}
                    for qid, q, _refused, reason in mismatches
                ],
                # Vom Makefile gesetzt: im Container gibt es kein git, und
                # `.git` liegt ausserhalb des gemounteten `src/backend`.
                "git_sha": os.environ.get("EVAL_GIT_SHA"),
                "gate": REFUSAL_RATE_GATE,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


async def test_out_of_corpus_refusal_rate(
    client: httpx.AsyncClient,
    token: str,
    profile: Profile,
    measured_config: dict[str, object],
    eval_out_dir: Any,
    llm_trace: list[dict[str, Any]],
) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    await assert_corpus_is_indexed_async(client, headers)

    questions = load_out_of_corpus_questions()
    # Guards the acceptance criterion itself: if a future edit to the seed files
    # drops entries below the ticket's target, the gate should say so rather than
    # silently grading a smaller, easier sample.
    assert len(questions) >= 20, (
        f"Expected at least 20 out-of-corpus questions, found {len(questions)}"
    )

    mismatches: list[tuple[str, str, bool, str | None]] = []
    # Die vollständige Antwort je Frage, inklusive `debug.llm_calls` mit Prompt
    # und Rohtext jedes LLM-Aufrufs — dasselbe, was die Admin-Ansicht zeigt.
    # Die CSV daneben trägt nur Kennzahlen, und an ihr endet die Auswertung
    # genau dort, wo sie interessant wird: warum eine Antwort abgeschnitten
    # wurde, oder was ein Self-Check geantwortet hat, der als «unlesbar» galt,
    # steht in keiner Spalte. Lokal kostet das Mitschreiben nichts.
    details: list[dict[str, Any]] = []
    results_csv = eval_out_dir / "refusal-results.csv"

    with results_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_COLUMNS)

        for q in questions:
            trace_from = len(llm_trace)
            r = await client.post(
                "/api/query", json={"question": q.question}, headers=headers
            )
            assert r.status_code == 200, r.text
            body = r.json()
            details.append({
                "id": q.id,
                "question": q.question,
                "expected_refusal": q.expected_refusal,
                "response": body,
                # Die Provider-Sicht auf dieselben Aufrufe, die `debug.llm_calls`
                # oben aus Anwendungssicht zeigt: `finish_reason`, Token-Zahlen,
                # Dauer und die tatsächlich gesendeten Stellschrauben. Die
                # Reihenfolge stimmt mit `debug.llm_calls` überein.
                "llm_trace": llm_trace[trace_from:],
            })

            reason = body.get("suppression_reason")
            # A configuration_error is a test/infra failure wearing a refusal's
            # clothes (see CONFIGURATION_ERROR above) -- never counts as one.
            actual_refusal = bool(body["suppressed"]) and reason != CONFIGURATION_ERROR

            confidence = body.get("confidence") or {}
            debug = body.get("debug") or {}
            writer.writerow(
                [
                    q.id,
                    q.expected_refusal,
                    body["suppressed"],
                    reason,
                    confidence.get("score"),
                    confidence.get("band"),
                    confidence.get("retrieval_score"),
                    confidence.get("citation_coverage"),
                    debug.get("self_check_ran"),
                    debug.get("self_check_verdict"),
                ]
            )
            f.flush()  # one row survives even if a later question crashes the run

            if actual_refusal != q.expected_refusal:
                mismatches.append((q.id, q.question, actual_refusal, reason))

    refusal_rate = (len(questions) - len(mismatches)) / len(questions)
    _write_run_json(
        eval_out_dir, profile, measured_config, refusal_rate, len(questions), mismatches
    )
    (eval_out_dir / "details.json").write_text(
        json.dumps(details, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print(f"\nProfil {profile.name} ({profile.model})")
    print(f"Out-of-corpus refusal rate: {refusal_rate:.0%} ({len(questions)} questions)")
    print(f"Per-question results: {eval_out_dir}")
    for qid, question, actual_refusal, reason in mismatches:
        expected = "a refusal" if not actual_refusal else "an answer"
        got = f"refused ({reason})" if actual_refusal else "answered"
        print(f"  {qid}: expected {expected}, got {got} -- {question}")

    if not profile.gated:
        # Ein Vergleichslauf ist eine Messreihe, kein Release-Gate (T-55). Beides
        # in dieselbe rote Meldung zu giessen nähme dem Gate seine Aussage: ein
        # lokales Modell, das 73 % erreicht, hat nichts kaputt gemacht.
        print(f"Profil {profile.name} ist nicht gated — Ergebnis gemeldet, kein Gate.")
        return

    assert refusal_rate >= REFUSAL_RATE_GATE, (
        f"Refusal rate {refusal_rate:.0%} is below the {REFUSAL_RATE_GATE:.0%} gate "
        f"(ADR-009): {len(mismatches)}/{len(questions)} did not match their expected "
        f"outcome. Details: {eval_out_dir}"
    )
