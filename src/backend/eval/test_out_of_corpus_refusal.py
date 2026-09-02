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

Precondition: a running stack with seeded users and the LearningCorpus PDFs
indexed — `make up && make seed && make seed-corpus`.
"""

import csv
import os
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from eval.gold_dataset import load_corpora, load_out_of_corpus_questions
from seed_users import USERS

BASE_URL = os.environ.get("E2E_BASE_URL", "http://webapp")

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

# POST /query allows 10/minute per account (app/routers/query.py, QUERY_RATE_LIMIT).
# Spacing requests 6.5s apart stays under that on paper (~9.2/min), but a slow
# provider response can still push a request into the next account over the
# limit — hence the 429 retry below rather than a hard assert on the status.
REQUEST_INTERVAL_S = 6.5
RATE_LIMIT_RETRY_S = 65  # outlives a 1-minute window with margin
MAX_RETRIES = 2

# Bind-mounted into the api container (docker-compose.yml: `./backend:/app`), so
# this also lands in src/backend/eval/out/ on the host.
RESULTS_DIR = Path(__file__).parent / "out"
RESULTS_CSV = RESULTS_DIR / "refusal-results.csv"


@pytest.fixture(scope="module")
def client() -> Iterator[httpx.Client]:
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture(scope="module")
def token(client: httpx.Client) -> str:
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 429:
        pytest.fail(
            "Rate limit exhausted (5 logins/minute/IP) -- shared with seed_corpus.py "
            "and any e2e run in the same minute. Wait a minute and retry."
        )
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def _assert_corpus_is_indexed(client: httpx.Client, headers: dict[str, str]) -> None:
    """A refusal is only evidence of anything if there was a corpus to miss.

    Without this, a dead worker or a `seed-corpus` that silently uploaded
    nothing looks identical to a perfect run: every question hits the
    retrieval gate and refusal_rate reads 100% either way (review on #100).
    """
    r = client.get("/api/documents", headers=headers)
    assert r.status_code == 200, r.text
    by_filename = {d["filename"]: d for d in r.json()}

    missing = []
    for corpus in load_corpora():
        doc = by_filename.get(corpus.filename)
        if doc is None:
            missing.append(f"{corpus.filename}: not uploaded")
        elif doc["status"] != "available":
            missing.append(f"{corpus.filename}: status={doc['status']}")
    if missing:
        pytest.fail(
            "Corpus not fully indexed, refusal rate would be meaningless: "
            + "; ".join(missing)
            + ". Run `make seed-corpus` against the running stack first."
        )


def _query_with_retry(
    client: httpx.Client, headers: dict[str, str], question: str
) -> dict[str, object]:
    for attempt in range(MAX_RETRIES + 1):
        r = client.post("/api/query", json={"question": question}, headers=headers)
        if r.status_code == 429:
            if attempt == MAX_RETRIES:
                pytest.fail(f"Rate limit exhausted after {MAX_RETRIES} retries: {question!r}")
            wait_s = float(r.headers.get("Retry-After", RATE_LIMIT_RETRY_S))
            time.sleep(wait_s)
            continue
        assert r.status_code == 200, r.text
        return r.json()  # type: ignore[no-any-return]
    raise AssertionError("unreachable")  # pragma: no cover


def test_out_of_corpus_refusal_rate(client: httpx.Client, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    _assert_corpus_is_indexed(client, headers)

    questions = load_out_of_corpus_questions()
    # Guards the acceptance criterion itself: if a future edit to the seed files
    # drops entries below the ticket's target, the gate should say so rather than
    # silently grading a smaller, easier sample.
    assert len(questions) >= 20, (
        f"Expected at least 20 out-of-corpus questions, found {len(questions)}"
    )

    mismatches: list[tuple[str, str, bool, str | None]] = []

    RESULTS_DIR.mkdir(exist_ok=True)
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
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
        )

        for i, q in enumerate(questions):
            if i:
                time.sleep(REQUEST_INTERVAL_S)
            body = _query_with_retry(client, headers, q.question)

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
    print(f"\nOut-of-corpus refusal rate: {refusal_rate:.0%} ({len(questions)} questions)")
    print(f"Per-question results: {RESULTS_CSV}")
    for qid, question, actual_refusal, reason in mismatches:
        expected = "a refusal" if not actual_refusal else "an answer"
        got = f"refused ({reason})" if actual_refusal else "answered"
        print(f"  {qid}: expected {expected}, got {got} -- {question}")

    assert refusal_rate >= REFUSAL_RATE_GATE, (
        f"Refusal rate {refusal_rate:.0%} is below the {REFUSAL_RATE_GATE:.0%} gate "
        f"(ADR-009): {len(mismatches)}/{len(questions)} did not match their expected "
        f"outcome. Details: {RESULTS_CSV}"
    )
