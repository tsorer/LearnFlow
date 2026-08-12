from pathlib import Path

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

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


def test_auth_and_upload_schemas_defined():
    spec, _ = read_from_filename(str(SPEC_PATH))
    schemas = spec["components"]["schemas"]
    for name in ("LoginRequest", "TokenResponse", "DocumentResponse"):
        assert name in schemas, f"Schema fehlt: {name}"
