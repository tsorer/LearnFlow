from pathlib import Path

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

from app.models.tables import DocumentStatus, QuizQuestionStatus
from app.routers import admin, query
from app.services.config import ConfidenceThresholds, PipelineConfig
from app.services.embedding_config import EMBEDDING_CONFIG_KEYS
from app.services.self_check import SelfCheckResult

SPEC_PATH = Path(__file__).parent.parent / "openapi.yaml"

# Endpoints from US-01..US-05 and US-11. Completeness against the
# implementation is checked in both directions by test_rbac.py; this list is
# what must be there for business reasons, so an accidental deletion shows up.
EXPECTED_OPERATIONS = [
    ("/api/auth/login", "post"),
    ("/api/auth/me", "get"),
    ("/api/auth/logout", "post"),
    ("/api/query", "post"),
    # Feedback hangs off the answer, not the query (US-03, ERD:
    # feedback.answer_id). Until T-39 this was /api/feedback with {query_id}.
    ("/api/answers/{answer_id}/feedback", "post"),
    ("/api/feedback", "get"),
    ("/api/documents", "get"),
    ("/api/documents", "post"),
    ("/api/documents/{document_id}", "delete"),
    ("/api/admin/config", "get"),
    ("/api/admin/config", "put"),
    ("/api/quiz/generate", "post"),
    ("/api/quiz/questions", "get"),
    ("/api/quiz/questions/sample", "get"),
    ("/api/quiz/questions/{question_id}", "patch"),
]


def test_openapi_spec_is_valid():
    spec, _ = read_from_filename(str(SPEC_PATH))
    validate(spec)  # wirft OpenAPIValidationError bei ungueltiger Spec


def test_all_us_endpoints_present():
    spec, _ = read_from_filename(str(SPEC_PATH))
    paths = spec["paths"]
    for path, method in EXPECTED_OPERATIONS:
        assert path in paths, f"Pfad fehlt in der Spec: {path}"
        assert method in paths[path], f"Methode {method.upper()} fehlt fuer {path}"


def test_document_status_enum_matches_the_model():
    """The status values are part of the contract, so they exist twice: as the
    DocumentStatus schema the frontend types are generated from, and as the enum
    the API and the worker write. A value added on one side only would reach the
    database without any client being able to render it (ADR-010)."""
    spec, _ = read_from_filename(str(SPEC_PATH))
    assert {s.value for s in DocumentStatus} == set(
        spec["components"]["schemas"]["DocumentStatus"]["enum"]
    )


def test_quiz_status_enum_matches_the_model():
    """Same contract as DocumentStatus, and the same failure if it drifts.

    The column is a plain varchar with a CHECK, so the three values live in the
    database, in this enum and in the spec the frontend types come from. A value
    added on one side only is either a status no client can render or a promise
    to the frontend that no writer keeps.
    """
    spec, _ = read_from_filename(str(SPEC_PATH))
    assert {s.value for s in QuizQuestionStatus} == set(
        spec["components"]["schemas"]["QuizQuestionStatus"]["enum"]
    )


def test_auth_and_upload_schemas_defined():
    spec, _ = read_from_filename(str(SPEC_PATH))
    schemas = spec["components"]["schemas"]
    for name in ("LoginRequest", "TokenResponse", "DocumentResponse"):
        assert name in schemas, f"Schema fehlt: {name}"


def test_suppression_reasons_match_the_spec_enum():
    """The wire values of `suppression_reason`, checked in both directions.

    Nothing else pins the two sides together. The backend constants are plain
    strings, and the frontend only type-checks its label map against the *spec*
    — so a typo in a REASON_* constant ships a reason no label matches, and the
    badge falls back to rendering the raw key at the user. The reverse gap is
    just as quiet: an enum value the backend can never emit is a promise to the
    frontend that nothing keeps.

    Collected by prefix rather than listed, so a reason added for T-25 is
    covered without anyone remembering this test.
    """
    spec, _ = read_from_filename(str(SPEC_PATH))
    declared = set(
        spec["components"]["schemas"]["QueryResponse"]["properties"]["suppression_reason"]["enum"]
    )
    emitted = {
        value
        for name, value in vars(query).items()
        if name.startswith("REASON_") and isinstance(value, str)
    }

    assert emitted == declared, (
        f"Nur im Code: {sorted(emitted - declared)} · nur in der Spec: {sorted(declared - emitted)}"
    )


def _emitted_by_prefix(prefix: str) -> set[str]:
    """The wire values behind a family of constants in `app.routers.query`.

    Collected by prefix rather than listed, for the same reason as
    `test_suppression_reasons_match_the_spec_enum` above: a value added for a
    later ticket is covered without anyone remembering these tests.
    """
    return {
        value
        for name, value in vars(query).items()
        if name.startswith(prefix) and isinstance(value, str)
    }


def test_stage_ids_match_the_spec_enum():
    """`StageInfo.id`, checked in both directions (T-46).

    The admin view groups the LLM calls under their stage by comparing this
    string (`MessageBubble.tsx`). Before T-46 the field was `type: string` and
    the five values lived in a prose description, so a typo on either side
    produced a condition that is simply never true — no error, just a stage
    that silently stops showing its call.
    """
    spec, _ = read_from_filename(str(SPEC_PATH))
    declared = set(spec["components"]["schemas"]["StageInfo"]["properties"]["id"]["enum"])
    emitted = _emitted_by_prefix("STAGE_")

    assert emitted == declared, (
        f"Nur im Code: {sorted(emitted - declared)} · nur in der Spec: {sorted(declared - emitted)}"
    )


def test_stage_ids_are_a_subset_of_the_suppression_reasons():
    """Why an enum is right here despite `DebugInfo`'s "not part of the
    contract" caveat (T-46, review on #86): every stage id is already frozen as
    a `suppression_reason` value. Leaving `id` loose would mean the same string
    is binding under one name and free under another. If this ever fails, that
    argument no longer holds and the ADR-010 addendum needs revisiting.
    """
    spec, _ = read_from_filename(str(SPEC_PATH))
    reasons = set(
        spec["components"]["schemas"]["QueryResponse"]["properties"]["suppression_reason"]["enum"]
    )

    assert _emitted_by_prefix("STAGE_") <= reasons


def test_llm_call_steps_match_the_spec_enum():
    """`LLMCallInfo.step`, checked in both directions (T-46). Same failure mode
    as the stage ids: the admin view finds a stage's call by this string.
    """
    spec, _ = read_from_filename(str(SPEC_PATH))
    declared = set(spec["components"]["schemas"]["LLMCallInfo"]["properties"]["step"]["enum"])
    emitted = _emitted_by_prefix("STEP_")

    assert emitted == declared, (
        f"Nur im Code: {sorted(emitted - declared)} · nur in der Spec: {sorted(declared - emitted)}"
    )


def test_params_used_keys_match_the_spec():
    """`DebugInfo.params_used`, checked in both directions (T-46).

    OAS 3.0 has no `propertyNames`, so the key set is written as `properties`
    with `additionalProperties: false` rather than as an enum. Both the shape
    and the completeness promise of the description are asserted here: every
    key the router emits is declared, and every declared key is `required` —
    "wer kalibriert, braucht alle, nicht nur die ausgelösten".
    """
    spec, _ = read_from_filename(str(SPEC_PATH))
    schema = spec["components"]["schemas"]["DebugInfo"]["properties"]["params_used"]
    declared = set(schema["properties"])
    emitted = set(
        query.params_used(
            PipelineConfig(
                similarity_threshold=0.35,
                min_retrieval_confidence=0.40,
                min_citation_coverage=0.50,
                self_check_band_low=0.45,
                self_check_band_high=0.75,
                retrieval_top_k=20,
                context_top_n=5,
                rrf_k=60,
            ),
            ConfidenceThresholds(high=0.75, medium=0.45),
        )
    )

    assert emitted == declared, (
        f"Nur im Code: {sorted(emitted - declared)} · nur in der Spec: {sorted(declared - emitted)}"
    )
    assert set(schema["required"]) == declared
    assert schema["additionalProperties"] is False


def test_config_keys_the_api_writes_are_declared_in_the_spec():
    """`ConfigMap`, code -> spec (T-46).

    Only one direction is checkable here: `chunk_size`, `chunk_overlap` and
    `stale_days` are read by literal, not through a `*_KEYS` constant, so there
    is no Python name to collect them under. The other direction — a declared
    key that no config row backs — is caught at runtime instead: `update_config`
    422s any key absent from the table, and the frontend types its parameter
    lists as `ConfigKey` from this very schema.
    """
    spec, _ = read_from_filename(str(SPEC_PATH))
    declared = set(spec["components"]["schemas"]["ConfigMap"]["properties"])

    assert admin.WRITABLE_KEYS <= declared, sorted(admin.WRITABLE_KEYS - declared)
    assert set(EMBEDDING_CONFIG_KEYS) <= declared
    assert spec["components"]["schemas"]["ConfigMap"]["additionalProperties"] is False


def test_self_check_verdicts_match_the_spec_enum():
    """The string form of `StageInfo.value`, both directions (T-46).

    Collected by prefix like the two families above: `VERDICT_COVERED` and
    `VERDICT_UNCOVERED` are imported into `query`, `VERDICT_UNREADABLE` is
    defined there, so `vars(query)` sees all three.

    Weaker consequences than the stage ids — the admin view renders this value
    (`String(stage.value)`) instead of comparing it, so a drift here shows a
    wrong word rather than a condition that is never true. Declared anyway: a
    closed set belongs in the spec, and `VERDICT_COVERED`/`_UNCOVERED` are the
    tokens the self-check prompt asks the model for, so changing one is a
    change to that prompt's protocol and should not pass unnoticed.
    """
    spec, _ = read_from_filename(str(SPEC_PATH))
    string_variant = next(
        branch
        for branch in spec["components"]["schemas"]["StageInfo"]["properties"]["value"]["oneOf"]
        if branch["type"] == "string"
    )
    declared = set(string_variant["enum"])
    emitted = _emitted_by_prefix("VERDICT_")

    assert emitted == declared, (
        f"Nur im Code: {sorted(emitted - declared)} · nur in der Spec: {sorted(declared - emitted)}"
    )


def test_the_unreadable_verdict_is_what_an_unparsed_self_check_reports():
    """`VERDICT_UNREADABLE` is the only one of the three the spec enum lists
    that this module produces itself — the other two are the self-check
    prompt's protocol tokens, passed through unchanged. Pinned here because a
    rename would otherwise only surface in the enum test above, which cannot
    say which of the three moved.
    """
    unparsed = SelfCheckResult(
        passed=False, verdict_parsed=False, uncovered="", prompt="", raw_response="???"
    )

    assert query._self_check_value(unparsed) == query.VERDICT_UNREADABLE
    assert query._self_check_value(None) is None
