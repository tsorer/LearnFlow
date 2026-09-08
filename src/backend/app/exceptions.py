"""Exception types shared by the API and the worker."""


class UserFacingError(Exception):
    """An error whose message is written for the person who uploaded the document.

    documents.error_message is served by GET /documents and GET /documents/{id}
    to every knowledge_owner and admin — not only to the uploader, since neither
    endpoint filters by who uploaded — and is rendered verbatim by the frontend.
    Only the message of this class is written there; every other exception is
    replaced by a generic text, because provider errors carry api_base,
    deployment names and, on an auth failure, a fragment of the API key. The
    full error always stays in the worker log.

    Deliberately derived from Exception, not ValueError: the previous rule
    ("our own errors are the ValueErrors") held only as long as no third-party
    type inherited from ValueError, and nothing checked that on a dependency
    upgrade. Raising this class states the intent at the point of the raise.
    """


class EmbeddingConfigError(Exception):
    """The embedding configuration cannot be verified as safe to run with.

    Raised by `app/services/embedding_config.py` at process startup, in the
    API and the worker alike, for two distinct reasons that both mean the
    same thing to a caller here: don't run. Either the `config` table's
    `embed_model`/`embed_dimensions` row is missing or unparsable (migration
    0018 should prevent this, same defense-in-depth as `ConfigurationError`
    in `app/services/config.py`), or it is readable but disagrees with the
    running `Settings` — the drift ADR-005 and T-42 exist to catch, since
    pgvector silently accepts vectors from a different model of the same
    dimension into the same index.

    Not `UserFacingError`: nobody uploaded a document and nobody asked a
    question yet, so there is no request to attach a message to. Not
    `ConfigurationError`: that type answers a request with "Weiss ich
    nicht"; this one is meant to stop the process before it accepts any.
    """
