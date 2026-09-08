#!/usr/bin/env python
"""T-28: uploads and indexes the real LearningCorpus PDFs against the running
stack, so the eval harness (eval/test_out_of_corpus_refusal.py) has a real,
non-empty corpus to test refusal against.

Idempotent: POST /documents replaces an existing document of the same filename
(T-15), so re-running this after a corpus PDF changes re-indexes it instead of
duplicating it.

Run inside api container: python seed_corpus.py
Precondition: a running stack with seeded users (`make up && make seed`).
"""

import os
import sys
import time
from pathlib import Path

import httpx

from eval.gold_dataset import load_corpora
from seed_users import USERS

BASE_URL = os.environ.get("E2E_BASE_URL", "http://webapp")
CORPUS_DIR = Path(os.environ.get("LEARNING_CORPUS_DIR", "/LearningCorpus"))
POLL_TIMEOUT_S = 600
POLL_INTERVAL_S = 5

# Any knowledge_owner will do -- uploading is what needs the role, not who.
_OWNER = next(u for u in USERS if u["role"] == "knowledge_owner")
EMAIL = os.environ.get("E2E_OWNER_EMAIL", _OWNER["email"])
PASSWORD = os.environ.get("E2E_OWNER_PASSWORD", _OWNER["password"])


def main() -> None:
    # The dataset's corpora, not "whatever PDFs happen to be in the directory":
    # an extra or unrelated file there must not silently become part of what
    # the eval measures against (review on #100).
    corpora = load_corpora()

    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        r = client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
        r.raise_for_status()
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        pending: dict[str, str] = {}  # document_id -> filename
        for corpus in corpora:
            file_path = CORPUS_DIR / corpus.path
            if not file_path.is_file():
                sys.exit(f"{corpus.path}: not found under {CORPUS_DIR}")
            with file_path.open("rb") as f:
                r = client.post(
                    "/api/documents",
                    files={"file": (corpus.filename, f, "application/pdf")},
                    headers=headers,
                )
            r.raise_for_status()
            body = r.json()
            pending[body["id"]] = corpus.filename
            print(f"uploaded {corpus.filename} -> {body['id']} ({body['status']})")

        deadline = time.monotonic() + POLL_TIMEOUT_S
        while pending and time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL_S)
            for document_id, name in list(pending.items()):
                r = client.get(f"/api/documents/{document_id}", headers=headers)
                r.raise_for_status()
                body = r.json()
                if body["status"] == "available":
                    print(f"{name}: available ({body['chunk_count']} chunks)")
                    del pending[document_id]
                elif body["status"] == "failed":
                    sys.exit(f"{name}: indexing failed -- {body['error_message']}")

        if pending:
            sys.exit(f"Timed out after {POLL_TIMEOUT_S}s waiting for: {sorted(pending.values())}")


if __name__ == "__main__":
    main()
