"""T-55: der Eval läuft in-process gegen die ASGI-App, in einer Transaktion,
die am Ende zurückgerollt wird.

Vorher fuhr er echtes HTTP gegen den laufenden Stack (`E2E_BASE_URL`), mit drei
Folgen, die alle hier verschwinden:

1. **Er schrieb in die Entwicklungsdatenbank.** Jede Frage hinterliess eine
   `answers`-Zeile; ein Nachmittag Testläufe hatte 52 davon angesammelt (#123).
   Weil die Session jetzt von hier kommt, hängt sie an einer äusseren
   Transaktion: das `db.commit()` der Pipeline (`app/routers/query.py`) wird zum
   Savepoint-Release, und der Rollback am Ende verwirft alles. Das Aufräumen
   kann dabei nicht vergessen werden — stirbt der Prozess, rollt Postgres selbst
   zurück, wenn die Verbindung wegfällt.

2. **Der Messwert hing am Zustand der Datenbank.** Derselbe Korpus ergab 90,9 %
   oder 95,5 %, je nachdem, wie die Schwellen gerade kalibriert waren. Der Lauf
   setzt sie jetzt *in der Transaktion* auf die Seed-Defaults: reproduzierbar,
   und eine lokale Kalibrierung überlebt unberührt.

3. **Das Rate-Limit taktete den Lauf.** 6,5 s Pause vor jeder Frage, damit
   `POST /api/query` (10/Minute) nicht 429 antwortet — von 2:45 min Laufzeit
   waren 2:23 min reines Warten. In-process wird der Limiter abgeschaltet.

Was **nicht** wegfällt: der gemessene Pfad. Die Anfragen gehen weiterhin durch
den echten Route-Handler samt Auth, Retrieval, allen drei Stufen und der
Persistenz. Nur uvicorn und nginx sind draussen — beim Messen von RAG-Qualität
sind sie Rauschen (für die ausgelieferte Verteilung ist `e2e/` zuständig).

Bekannte Einschränkung: `ASGITransport` startet den Lifespan nicht, also läuft
`verify_embedding_config` (T-42) hier nicht. Für den Eval unkritisch — er misst
gegen einen bereits indexierten Korpus, dessen Vektoren zur Konfiguration
passen, sonst hätte die Indexierung nichts geschrieben.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import litellm
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.database import engine, get_db
from app.limiter import limiter
from app.main import app
from app.services import config as config_service
from app.services import generation, self_check
from eval.profiles import Profile, resolve

#: Die Werte, gegen die gemessen wird — dieselben, die Migration 0004/0008
#: seedet, hier aus den Code-Defaults gezogen, damit beide Quellen nicht
#: getrennt driften können.
SEED_DEFAULTS: dict[str, object] = {
    "similarity_threshold": config_service.DEFAULT_SIMILARITY_THRESHOLD,
    "min_retrieval_confidence": config_service.DEFAULT_MIN_RETRIEVAL_CONFIDENCE,
    "min_citation_coverage": config_service.DEFAULT_MIN_CITATION_COVERAGE,
    "confidence_threshold_medium": config_service.DEFAULT_CONFIDENCE_THRESHOLD_MEDIUM,
    "confidence_threshold_high": config_service.DEFAULT_CONFIDENCE_THRESHOLD_HIGH,
    "self_check_band_low": config_service.DEFAULT_SELF_CHECK_BAND_LOW,
    "self_check_band_high": config_service.DEFAULT_SELF_CHECK_BAND_HIGH,
    "retrieval_top_k": config_service.DEFAULT_RETRIEVAL_TOP_K,
    "context_top_n": config_service.DEFAULT_CONTEXT_TOP_N,
    "rrf_k": config_service.DEFAULT_RRF_K,
}


@pytest.fixture(scope="session")
def profile() -> Profile:
    """Welche Messkonfiguration dieser Lauf misst (`EVAL_PROFILE`)."""
    return resolve(os.environ.get("EVAL_PROFILE"))


@pytest_asyncio.fixture
async def db_connection() -> AsyncIterator[AsyncConnection]:
    """Eine Verbindung mit offener Transaktion, die garantiert zurückgerollt wird.

    Alles, was die Pipeline während des Laufs schreibt, hängt daran und ist
    danach verschwunden — auch das, was sie selbst committet.
    """
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            yield conn
        finally:
            await trans.rollback()


@pytest_asyncio.fixture
async def measured_config(db_connection: AsyncConnection) -> AsyncIterator[dict[str, object]]:
    """Setzt die Seed-Defaults — innerhalb der Transaktion, also nur für diesen Lauf.

    Absichtlich nicht «vorher sichern, nachher zurückschreiben»: das ist die
    Krücke, die in den e2e-Modulen steht und nach einem Abbruch nicht greift.
    Hier erledigt es der Rollback.
    """
    for key, value in SEED_DEFAULTS.items():
        await db_connection.execute(
            text("UPDATE config SET value = :v WHERE key = :k"),
            {"v": str(value), "k": key},
        )
    yield SEED_DEFAULTS


@pytest_asyncio.fixture
async def client(
    db_connection: AsyncConnection,
    measured_config: dict[str, object],
    profile: Profile,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[httpx.AsyncClient]:
    """Die echte ASGI-App, ohne uvicorn und ohne nginx."""

    async def _get_db() -> AsyncIterator[AsyncSession]:
        # `create_savepoint`, damit das commit() der Pipeline die äussere
        # Transaktion nicht beendet, sondern nur einen Savepoint freigibt.
        #
        # `expire_on_commit=False` spiegelt `AsyncSessionLocal` (app/database.py)
        # und ist hier nicht kosmetisch: `_persist_and_respond` liest `answer.id`
        # *nach* dem commit(), und mit dem Default würde das ein Lazy-Refresh
        # auslösen — synchrones IO im Async-Kontext, das als `MissingGreenlet`
        # hochkommt. Die überschriebene Session muss die Einstellungen der
        # echten tragen, sonst misst der Eval eine Pipeline mit anderem
        # Sitzungsverhalten als die ausgelieferte.
        session = AsyncSession(
            bind=db_connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_db] = _get_db
    # Sonst taktet `POST /api/query` (10/Minute) den Lauf auf 6,5 s je Frage.
    monkeypatch.setattr(limiter, "enabled", False)
    _apply(profile, monkeypatch)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://eval") as c:
        yield c

    app.dependency_overrides.clear()


def _apply(profile: Profile, monkeypatch: pytest.MonkeyPatch) -> None:
    """Das Profil auf die Pipeline legen — ohne eine Zeile in `app/` zu ändern.

    `settings.llm_model` wird zur Laufzeit gelesen, die Budgets sind
    Modulkonstanten, und die Zusatzargumente gehen über einen Wrapper um
    `litellm.acompletion`, den `generation` und `self_check` beide benutzen.
    Was ein Profil überschreiben darf, steht in `eval/profiles.py`.
    """
    from app.config import settings

    monkeypatch.setattr(settings, "llm_model", profile.model)
    if profile.timeout_seconds is not None:
        monkeypatch.setattr(generation, "TIMEOUT_SECONDS", profile.timeout_seconds)
    if profile.max_answer_tokens is not None:
        monkeypatch.setattr(generation, "MAX_ANSWER_TOKENS", profile.max_answer_tokens)
    if profile.self_check_timeout_seconds is not None:
        monkeypatch.setattr(self_check, "TIMEOUT_SECONDS", profile.self_check_timeout_seconds)

    if profile.extra_completion_kwargs:
        original = litellm.acompletion
        extra = dict(profile.extra_completion_kwargs)

        async def _with_extra(**kwargs: Any) -> Any:
            return await original(**{**kwargs, **extra})

        monkeypatch.setattr(litellm, "acompletion", _with_extra)


@pytest.fixture
def eval_out_dir(profile: Profile) -> Iterator[Any]:
    """`eval/out/<profil>/<zeitstempel>/` — ein Lauf überschreibt keinen anderen."""
    import datetime
    import pathlib

    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    path = pathlib.Path(__file__).parent / "out" / profile.name / stamp
    path.mkdir(parents=True, exist_ok=True)
    yield path
