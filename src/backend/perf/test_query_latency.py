"""T-22: p95 latency of POST /query under concurrent load from several
accounts, against the real, indexed LearningCorpus.

Measures the open point ADR-008 leaves (Docs/04_ADR-008_Konfidenz-Pipeline.md:143,
:202-204): stage 3's optional second provider call (self-check boundary band)
is the latency risk the Performance-NFA (p95 <= 10 s) is about. Not a CI job
(T-53, #110 -- no OPENAI_API_KEY secret exists in the repo, same constraint as
`eval`, T-28); run manually via `make perf`.

Precondition: a running stack with seeded users and the LearningCorpus PDFs
indexed -- `make up && make seed && make seed-corpus`.

Uses in-corpus questions, not out-of-corpus ones: out-of-corpus questions never
reach stage 3 (they're refused at the deterministic retrieval gate, see
eval/test_out_of_corpus_refusal.py), while in-corpus questions produce real
answers and exercise retrieval, generation and -- in the self-check boundary
band -- the second provider call this measurement is about.

Concurrency: 5 of the 6 seed accounts (seed_users.USERS), not all 6 -- login
is limited to 5/minute/IP (app/routers/auth.py), so a 6th login in the same
run would itself be refused. All 5 log in first (sequential, one shared IP),
then each fires its own share of the 45 in-corpus questions -- round-robin
split, ~9 per account -- sequentially against itself (POST /query is limited
to 10/minute/account, app/routers/query.py), while all 5 accounts run
concurrently via asyncio.gather: real concurrency on the API/DB/provider side,
approximating Normallast with multiple simultaneous users.
"""

import asyncio
import csv
import os
import statistics
import time
from pathlib import Path
from typing import Any

import httpx
import pytest

from eval.gold_dataset import (
    InCorpusQuestion,
    assert_corpus_is_indexed,
    load_in_corpus_questions,
)
from seed_users import USERS

BASE_URL = os.environ.get("E2E_BASE_URL", "http://webapp")

P95_GATE_S = 10.0  # Docs/03_QualityAttributes.md Performance-NFA, ADR-008:143

# POST /query allows 10/minute per account (app/routers/query.py, QUERY_RATE_LIMIT).
# Each account only fires ~9 requests here, comfortably under that on paper, but a
# slow provider response can still push a request into the next account over the
# limit -- hence the 429 retry below rather than a hard assert on the status (same
# reasoning as eval/test_out_of_corpus_refusal.py).
RATE_LIMIT_RETRY_S = 65  # outlives a 1-minute window with margin
MAX_RETRIES = 2

# Login is 5/minute/IP (app/routers/auth.py): using all 6 seed accounts would
# refuse the 6th login within the same run, so this measurement uses 5.
ACCOUNTS = USERS[:5]

# Bind-mounted into the api container (docker-compose.yml: `./backend:/app`), so
# this also lands in src/backend/perf/out/ on the host.
RESULTS_DIR = Path(__file__).parent / "out"
RESULTS_CSV = RESULTS_DIR / "latency-results.csv"


def _split_round_robin(
    questions: list[InCorpusQuestion], n: int
) -> list[list[InCorpusQuestion]]:
    return [questions[i::n] for i in range(n)]


def _login(client: httpx.Client, email: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    if r.status_code == 429:
        pytest.fail(
            "Rate limit exhausted (5 logins/minute/IP) -- shared with seed_corpus.py "
            "and any e2e/eval run in the same minute. Wait a minute and retry."
        )
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


async def _query_with_retry(
    client: httpx.AsyncClient, headers: dict[str, str], question: str
) -> tuple[httpx.Response, float]:
    for attempt in range(MAX_RETRIES + 1):
        start = time.perf_counter()
        r = await client.post("/api/query", json={"question": question}, headers=headers)
        latency_s = time.perf_counter() - start
        if r.status_code == 429:
            if attempt == MAX_RETRIES:
                pytest.fail(f"Rate limit exhausted after {MAX_RETRIES} retries: {question!r}")
            wait_s = float(r.headers.get("Retry-After", RATE_LIMIT_RETRY_S))
            await asyncio.sleep(wait_s)
            continue
        assert r.status_code == 200, r.text
        return r, latency_s
    raise AssertionError("unreachable")  # pragma: no cover


async def _run_account(
    client: httpx.AsyncClient,
    email: str,
    token: str,
    questions: list[InCorpusQuestion],
    rows: list[dict[str, Any]],
) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    for q in questions:
        r, latency_s = await _query_with_retry(client, headers, q.question)
        body = r.json()
        rows.append(
            {
                "account": email,
                "question_id": q.id,
                "status_code": r.status_code,
                "latency_s": latency_s,
                "suppressed": body.get("suppressed"),
                "suppression_reason": body.get("suppression_reason"),
            }
        )


def test_query_latency_p95() -> None:
    questions = load_in_corpus_questions()
    # Guards the acceptance criterion itself: if a future edit to the seed files
    # drops entries below the ticket's target, the gate should say so rather than
    # silently measuring a smaller, easier sample.
    assert len(questions) >= 20, (
        f"Expected at least 20 in-corpus questions, found {len(questions)}"
    )

    tokens: dict[str, str] = {}
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as sync_client:
        for account in ACCOUNTS:
            tokens[account["email"]] = _login(
                sync_client, account["email"], account["password"]
            )

        # Searched over the full USERS list, not ACCOUNTS: which account is admin is
        # a property of seed_users.py, not of the slice this measurement happens to
        # use. The assertion below is what actually ties the two together.
        admin = next(u for u in USERS if u["role"] == "admin")
        assert admin["email"] in tokens, (
            f"Admin account {admin['email']!r} is not among the {len(ACCOUNTS)} accounts "
            "this measurement logs in -- seed_users.USERS was reordered/extended. "
            "assert_corpus_is_indexed needs an admin/knowledge_owner token; adjust ACCOUNTS "
            "or this lookup."
        )
        assert_corpus_is_indexed(
            sync_client, {"Authorization": f"Bearer {tokens[admin['email']]}"}
        )

    async def _run() -> list[dict[str, Any]]:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            shares = _split_round_robin(questions, len(ACCOUNTS))
            rows: list[dict[str, Any]] = []
            await asyncio.gather(
                *(
                    _run_account(client, account["email"], tokens[account["email"]], share, rows)
                    for account, share in zip(ACCOUNTS, shares, strict=True)
                )
            )
            return rows

    rows = asyncio.run(_run())

    RESULTS_DIR.mkdir(exist_ok=True)
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "account",
                "question_id",
                "status_code",
                "latency_s",
                "suppressed",
                "suppression_reason",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    latencies = [r["latency_s"] for r in rows]
    p95 = statistics.quantiles(latencies, n=100)[94]
    print(
        f"\nQuery latency: p95={p95:.2f}s mean={statistics.mean(latencies):.2f}s "
        f"min={min(latencies):.2f}s max={max(latencies):.2f}s ({len(latencies)} requests)"
    )
    print(f"Per-request results: {RESULTS_CSV}")

    assert p95 <= P95_GATE_S, (
        f"p95 latency {p95:.2f}s exceeds the {P95_GATE_S:.0f}s Performance-NFA "
        f"(ADR-008). Details: {RESULTS_CSV}"
    )
