from pathlib import Path

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

from app.models.tables import DocumentStatus, QuizQuestionStatus
from app.routers import query

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
