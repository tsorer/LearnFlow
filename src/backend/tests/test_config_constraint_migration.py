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


def test_the_latest_revision_keeps_every_validated_key() -> None:
    unit_interval, _ = _validated_by_0014()
    current = _literals("0017_documents_index_version")

    missing = unit_interval - set(current["UNIT_INTERVAL_KEYS"])
    assert not missing, (
        f"0017 drops {sorted(missing)} from the CHECK — those keys would take any value"
    )


def test_the_downgrade_restores_the_previous_state_exactly() -> None:
    """Going back to 0016 has to leave the constraint 0014 built — neither a
    narrower nor a wider one, or a rollback quietly changes what the database
    accepts.

    This covers the count keys of the upgrade too: `NEW_COUNT_KEYS` is built by
    unpacking `OLD_COUNT_KEYS`, so pinning the old list pins both.
    """
    unit_interval, counts = _validated_by_0014()
    current = _literals("0017_documents_index_version")

    assert set(current["UNIT_INTERVAL_KEYS"]) == unit_interval
    assert set(current["OLD_COUNT_KEYS"]) == counts
