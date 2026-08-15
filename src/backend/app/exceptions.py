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
