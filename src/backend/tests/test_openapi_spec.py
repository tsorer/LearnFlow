from pathlib import Path

from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename

SPEC_PATH = Path(__file__).parent.parent / "openapi.yaml"

# Endpunkte aus US-01..US-05, die als Stubs vorhanden sein muessen.
EXPECTED_OPERATIONS = [
    ("/api/auth/login", "post"),
    ("/api/auth/me", "get"),
    ("/api/auth/logout", "post"),
    ("/api/query", "post"),
    ("/api/feedback", "post"),
    ("/api/documents", "get"),
    ("/api/documents", "post"),
    ("/api/documents/{document_id}", "delete"),
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
    for name in ("LoginRequest", "TokenResponse", "DocumentUploadResponse"):
        assert name in schemas, f"Schema fehlt: {name}"
