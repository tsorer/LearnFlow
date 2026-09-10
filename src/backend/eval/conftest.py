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

import datetime
import os
import pathlib
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
import litellm
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.config import settings
from app.database import engine, get_db
from app.limiter import limiter
from app.main import app
from app.services import config as config_service
from app.services import generation, self_check
from app.services.embedding_config import (
    EMBEDDING_CONFIG_KEYS,
    embedding_config_from,
    verify_embedding_config,
)
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


@pytest.fixture
def llm_trace() -> list[dict[str, Any]]:
    """Ein Eintrag je `litellm.acompletion`, in Aufrufreihenfolge.

    Der Test schneidet die Liste je Frage auf und legt sie in `details.json` —
    siehe `_record` für das, was drinsteht, und warum es nicht in der Spec steht.
    """
    return []


@pytest_asyncio.fixture
async def embedding_config_matches(db_connection: AsyncConnection) -> None:
    """Der Wächter, den `ASGITransport` mitnimmt — hier von Hand nachgezogen.

    `httpx.ASGITransport` startet den Lifespan nicht, und damit entfällt die
    Prüfung aus `app/main.py`, die `Settings` gegen die von Migration 0018
    persistierte Konfiguration hält (T-42). Das Fehlen ist nicht neutral, es
    kippt das Gate in die **falsche** Richtung: laufen die beiden bei gleicher
    Dimension auseinander — Korpus unter einem 1536-dim-Modell indexiert,
    `EMBED_MODEL` danach gewechselt —, passen die Query-Embeddings nicht mehr
    zum Index. Das Retrieval liefert Rauschen, jede Frage fällt ins
    Retrieval-Gate, und die Refusal-Rate liest sich als 100 %: **grün**.

    `assert_corpus_is_indexed_async` fängt das nicht, die Dokumente sind ja da.
    Dass es in der Praxis bisher auffiel, lag an der Ausführungsart — `make
    eval` läuft per `docker exec src-api-1`, und der Container hat beim Start
    selbst geprüft. Das ist Zufall der Umgebung, nicht Konstruktion, und
    ADR-008 ist fail-closed (Review zu #128).
    """
    result = await db_connection.execute(
        text("SELECT key, value FROM config WHERE key = ANY(:keys)"),
        {"keys": list(EMBEDDING_CONFIG_KEYS)},
    )
    values = {key: value for key, value in result.all()}
    # Beide Seiten durch denselben Parser, wie im Lifespan: sonst vergleicht
    # ein ungestripptes `Settings.embed_model` gegen den gestrippten
    # persistierten Wert.
    verify_embedding_config(
        embedding_config_from(values),
        embedding_config_from(
            {
                "embed_model": settings.embed_model,
                "embed_dimensions": str(settings.embed_dimensions),
            }
        ),
    )


@pytest_asyncio.fixture
async def client(
    db_connection: AsyncConnection,
    measured_config: dict[str, object],
    embedding_config_matches: None,
    profile: Profile,
    llm_trace: list[dict[str, Any]],
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

    # Ab hier im `try`, damit ein Fehler im Setup den Override nicht am
    # modulglobalen `app` zurücklässt: der Code nach `yield` liefe dann nie,
    # und jeder folgende Test im selben Prozess spräche gegen eine
    # geschlossene Verbindung. `tests/conftest.py` fängt genau das mit einer
    # autouse-Fixture ab, `eval/` hat keine (Review zu #128).
    #
    # `pop` statt `clear`: die Map gehört der App, nicht dieser Fixture.
    app.dependency_overrides[get_db] = _get_db
    try:
        # Sonst taktet `POST /api/query` (10/Minute) den Lauf auf 6,5 s je Frage.
        monkeypatch.setattr(limiter, "enabled", False)
        _apply(profile, monkeypatch, llm_trace)

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://eval") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)


def _apply(
    profile: Profile, monkeypatch: pytest.MonkeyPatch, trace: list[dict[str, Any]]
) -> None:
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
    if profile.max_verdict_tokens is not None:
        monkeypatch.setattr(self_check, "MAX_VERDICT_TOKENS", profile.max_verdict_tokens)

    original = litellm.acompletion
    extra = dict(profile.extra_completion_kwargs)

    async def _wrapped(**kwargs: Any) -> Any:
        sent = {**kwargs, **extra}
        started = time.monotonic()
        try:
            r = await original(**sent)
        except Exception as exc:  # noqa: BLE001 — im Protokoll festhalten, dann weiterreichen
            trace.append(_record(sent, started, error=exc))
            raise
        trace.append(_record(sent, started, response=r))
        return r

    monkeypatch.setattr(litellm, "acompletion", _wrapped)


def _record(
    sent: dict[str, Any],
    started: float,
    response: Any = None,
    error: BaseException | None = None,
) -> dict[str, Any]:
    """Was ein einzelner LLM-Aufruf über sich preisgibt.

    Bewusst mehr, als `LLMCallInfo` in `openapi.yaml` führt: dort stehen nur
    `step`, `label`, `prompt` und `response`, und genau das reichte zweimal
    nicht. Eine leere Antwort sieht in der API identisch aus, egal ob das
    Modell nichts sagen wollte, der Kontext den Prompt beschnitten hat oder das
    Token-Budget vor dem ersten sichtbaren Zeichen aufgebraucht war — der
    Unterschied steht allein in `finish_reason` und den `usage`-Zahlen. Beide
    Male (Kontextfenster 4096, Verdict-Budget 300) wurde deshalb erst ein
    manuell nachgestellter Aufruf zur Diagnose.

    Hier statt in der Spec, weil der Eval ohnehin einen Wrapper um
    `litellm.acompletion` legt und damit an Daten kommt, die die API nie
    ausliefert — ohne eine Zeile Produktivcode und ohne den Vertrag zu ändern.
    """
    usage = getattr(response, "usage", None)
    choice = (getattr(response, "choices", None) or [None])[0]
    content = getattr(getattr(choice, "message", None), "content", None) or ""
    return {
        "model": sent.get("model"),
        "duration_s": round(time.monotonic() - started, 2),
        "finish_reason": getattr(choice, "finish_reason", None),
        "response_chars": len(content),
        # Die tatsächlich abgeschickten Stellschrauben. Hätte das hier gestanden,
        # wären `max_tokens=300` und das fehlende `num_ctx` sofort sichtbar
        # gewesen, statt aus dem Verhalten erschlossen werden zu müssen.
        "sent": {
            k: sent.get(k)
            for k in ("max_tokens", "num_ctx", "temperature", "timeout", "think")
            if sent.get(k) is not None
        },
        "prompt_chars": sum(len(m.get("content") or "") for m in sent.get("messages") or []),
        "usage": {
            k: getattr(usage, k, None)
            for k in ("prompt_tokens", "completion_tokens", "total_tokens")
        }
        if usage is not None
        else None,
        "error": f"{type(error).__name__}: {error}" if error is not None else None,
    }


@pytest.fixture
def eval_out_dir(profile: Profile) -> Iterator[pathlib.Path]:
    """`eval/out/<profil>/<zeitstempel>/` — ein Lauf überschreibt keinen anderen."""
    stamp = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    path = pathlib.Path(__file__).parent / "out" / profile.name / stamp
    path.mkdir(parents=True, exist_ok=True)
    yield path
