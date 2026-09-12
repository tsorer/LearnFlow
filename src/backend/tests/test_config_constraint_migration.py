"""The `config` CHECK constraint must only ever grow (ADR-008, fail-closed).

Every revision that touches `ck_config_confidence_threshold_value` drops it and
recreates it from a list of keys spelled out in that revision — deliberately, so
each migration keeps describing the state it creates even if an older one is
squashed away. The cost of that choice is that a revision copying the list from
the wrong predecessor silently *shrinks* the constraint: the forgotten keys fall
into the `ELSE true` arm, where every value passes.

That is not a theoretical risk. `0017` first carried `0012`'s list forward and
lost the self-check band `0014` had added, which let `self_check_band_low = 1.5`
through — caught by `e2e/test_config_self_check_band.py`, i.e. by the one CI job
that needs the full stack and does not run in `make qa`. This test brings that
feedback into the unit suite.

The key lists are read out of the migration sources rather than imported: with
pytest's working directory at the backend root, `import alembic` resolves to the
`alembic/` migrations folder next to it, not to the installed library, so
`from alembic import op` inside a revision fails. Reading the literals sidesteps
that entirely and keeps the test out of the migrations' import machinery.
"""

import ast
import re
from pathlib import Path
from typing import Any

VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _literals(revision: str) -> dict[str, Any]:
    """Every module-level `NAME = <literal>` of a revision, by name.

    `NEW_UNIT_INTERVAL_KEYS` of 0014 is deliberately not among them — it is
    built by unpacking, so the callers below compose it from the three literals
    it is made of.
    """
    tree = ast.parse((VERSIONS / f"{revision}.py").read_text(encoding="utf-8"))
    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            values[target.id] = ast.literal_eval(node.value)
        except ValueError:
            continue
    return values


def _validated_by_0014() -> tuple[set[str], set[str]]:
    """The constraint as 0014 left it: unit-interval keys, count keys."""
    literals = _literals("0014_self_check_band")
    unit_interval = set(literals["OLD_UNIT_INTERVAL_KEYS"]) | {
        literals["KEY_LOW"],
        literals["KEY_HIGH"],
    }
    return unit_interval, set(literals["COUNT_KEYS"])


def _validated_by_0019() -> tuple[set[str], set[str], set[str]]:
    """The constraint as 0019 left it: unit-interval keys, retention-days
    keys, count keys. 0020 (T-51/T-61) is the first revision after 0019 to
    touch this constraint, so this is what it has to carry forward whole."""
    literals = _literals("0019_retention")
    return (
        set(literals["UNIT_INTERVAL_KEYS"]),
        set(literals["RETENTION_DAYS_KEYS"]),
        set(literals["COUNT_KEYS"]),
    )


def test_the_latest_revision_keeps_every_validated_key() -> None:
    unit_interval_0014, counts_0014 = _validated_by_0014()
    unit_interval_0019, retention_0019, counts_0019 = _validated_by_0019()
    current = _literals("0020_index_progress_at")

    missing_unit_interval = (unit_interval_0014 | unit_interval_0019) - set(
        current["UNIT_INTERVAL_KEYS"]
    )
    assert not missing_unit_interval, (
        f"0020 drops {sorted(missing_unit_interval)} from the CHECK — those keys "
        "would take any value"
    )

    missing_retention = retention_0019 - set(current["RETENTION_DAYS_KEYS"])
    assert not missing_retention, (
        f"0020 drops {sorted(missing_retention)} from the CHECK — those keys would take any value"
    )

    # 0018 doesn't touch COUNT_KEYS (unlike UNIT_INTERVAL_KEYS, no revision
    # between 0014 and 0018 renamed it either, so the plain literal is checked
    # directly here rather than composed like OLD_COUNT_KEYS/NEW_COUNT_KEYS in
    # 0017) -- checked anyway, so this test guards the whole constraint the
    # newest revision creates, not only half of it (review on PR #120).
    missing_counts = (counts_0014 | counts_0019) - set(current["COUNT_KEYS"])
    assert not missing_counts, (
        f"0020 drops {sorted(missing_counts)} from the CHECK — those keys would take any value"
    )

    # 0020's own two keys (T-51/T-61) — declared in COUNT_KEYS as before, but
    # actually validated by the tighter PROCESSING_SECONDS_RANGE arm ahead of
    # it, same construction 0019 uses for the retention keys.
    assert set(current["PROCESSING_SECONDS_KEYS"]) == {
        "processing_stall_seconds",
        "processing_timeout_seconds",
    }


def test_the_downgrade_restores_the_previous_state_exactly() -> None:
    """Going back to 0019 has to leave the constraint 0019 built — neither a
    narrower nor a wider one, or a rollback quietly changes what the database
    accepts.
    """
    unit_interval, retention, counts = _validated_by_0019()
    current = _literals("0020_index_progress_at")

    assert set(current["UNIT_INTERVAL_KEYS"]) == unit_interval
    assert set(current["RETENTION_DAYS_KEYS"]) == retention
    assert set(current["COUNT_KEYS"]) == counts


def test_the_processing_seconds_range_matches_the_admin_api() -> None:
    """T-61 (#132): the migration's CHECK, `app/routers/admin.py`'s fast-fail
    and `worker/main.py`'s own clamp (next test) each spell out the same
    `[120, 999999]` range independently — a deliberate repetition, same
    reasoning as `0012`'s regexes being copied rather than imported into this
    migration. Independent means driftable: this pins that all three still
    agree, since neither the admin endpoint nor the worker's clamp is
    reachable from a migration test any other way.
    """
    from app.routers.admin import PROCESSING_SECONDS_KEYS, PROCESSING_SECONDS_RANGE

    current = _literals("0020_index_progress_at")
    assert current["PROCESSING_SECONDS_RANGE"] == PROCESSING_SECONDS_RANGE.pattern
    assert set(current["PROCESSING_SECONDS_KEYS"]) == set(PROCESSING_SECONDS_KEYS)


def test_the_processing_seconds_range_matches_the_workers_bounds() -> None:
    """`read_reaper_config`'s clamp (`worker/main.py`) uses plain ints,
    `MIN_PROCESSING_SECONDS`/`MAX_PROCESSING_SECONDS`, not the migration's
    regex — the two must describe the same range, or a value the CHECK
    accepts could still be silently replaced by the worker's own default on
    read, or the reverse."""
    from worker.main import MAX_PROCESSING_SECONDS, MIN_PROCESSING_SECONDS

    pattern = re.compile(_literals("0020_index_progress_at")["PROCESSING_SECONDS_RANGE"])
    assert not pattern.fullmatch(str(MIN_PROCESSING_SECONDS - 1))
    assert pattern.fullmatch(str(MIN_PROCESSING_SECONDS))
    assert pattern.fullmatch(str(MAX_PROCESSING_SECONDS))
    assert not pattern.fullmatch(str(MAX_PROCESSING_SECONDS + 1))
