# L3 · Minimieren & trennen — Patch-Vorschlag

> Modul 8 · Tag 1 · Deliverable 3 — baut auf [L1](L1_Datenfluss-Karte.md) und [L2](L2_Ewigkeits-Check.md) auf.
> **Status: Vorschlag. `src/` ist unberührt.** Die Diffs unten sind vollständig und anwendbar;
> vor dem Anwenden braucht es nach `CLAUDE.md` ein Issue, einen Feature-Branch und `make qa`.

## Die zwei Änderungen

| | Grenze | Was danach nicht mehr fliesst |
|---|---|---|
| **A** | 2 · kürzer halten + 3 · trennen | Nach 30 Tagen ist keine Frage mehr einer Person zuzuordnen; nach 90 Tagen ist der Fragetext weg |
| **B** | 2 · kürzer halten | App- und nginx-Logs (mit `user_id` und Client-IP) wachsen nicht mehr unbegrenzt — max. 30 MB pro Container statt unendlich |

**Was beide *nicht* tun:** sie ändern nichts an 🟠. Was einmal bei OpenAI war, holt keine
Frist zurück. Diese Patches begrenzen die lokale Kopie — die externe Grenze ist der
Provider-Wechsel aus ADR-004, nicht dies hier.

---

# Änderung A · `answers.question`: Frist + Entkopplung

## Warum

Aus L2, Fund A: `Docs/03_QualityAttributes.md:12` verspricht „Feedback und Query-Logs
werden pseudonymisiert gespeichert". Für das Feedback stimmt es. Für die Query-Logs
nicht — `answers.question` (Klartext) hängt über `answers.session_id →
query_sessions.user_id` an der Person, unbegrenzt, und **kein Endpoint liest die Spalte
je zurück**.

## Zwei Uhren, mit Absicht

- **30 Tage → die Verbindung.** `query_sessions.user_id = NULL`. Danach ist die Frage
  nicht mehr zuordenbar — das, was die Spec ohnehin behauptet.
- **90 Tage → der Text.** Eine Frage identifiziert ihren Autor auch allein
  („wie melde ich meinen Sohn Max für …"). Die Entkopplung ist deshalb nicht die ganze
  Arbeit. 90 Tage lassen ADR-009 ein Kalibrierungsfenster über echte Fragen.

## `UPDATE`, nicht `DELETE` — der wichtigste Entscheid im Patch

`feedback.answer_id` ist `ON DELETE CASCADE` (`tables.py:189`, Migration 0011). Alte
`answers`-Zeilen zu löschen würde **Stefans komplette Feedback-Historie mitlöschen**
(T-32) — lautlos, weil die Kaskade nichts protokolliert. Das Nullen der Spalte behält
jede Zeile, jeden Konfidenz-Score und jede Bewertung und entfernt nur den Freitext.

## Warum Konstanten und keine `config`-Zeilen

Der Reaper liest seine Werte aus der `config`-Tabelle (`worker/main.py:425`). Diese hier
bewusst nicht: eine Aufbewahrungsfrist ist eine Datenschutz-Zusage, kein
Betriebsparameter. Als `config`-Zeile könnte ein Admin sie über die Admin-UI (T-37)
still auf zehn Jahre setzen; als Konstante muss die Änderung durch einen PR. Dieselbe
Begründung, mit der ADR-008 den Grounding-Prompt aus der `config`-Tabelle heraushält.

---

## A1 · Neue Migration `alembic/versions/0019_answers_question_nullable.py`

```python
r"""Allow `answers.question` to be NULL, so a retention pass can clear it

`answers.question` has been NOT NULL since 0004, which was right while the
column was only ever written. It is still only ever written -- no endpoint
reads it back -- but it is now also something that has to *stop* existing
after 90 days (Docs/03_QualityAttributes.md, Security). NULL is what "the
question was here and has been removed" looks like; an empty string would be
indistinguishable from a question of length zero, which the API's
`min_length=3` (app/routers/query.py) never produced.

The column stays in place rather than being dropped: `answers` is what ADR-009
calibrates against, and a question inside the retention window is exactly what
makes a suppression decision reviewable.

Revision ID: 0019
Revises: 0018
Create Date: 2026-09-09
"""

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("answers", "question", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    # A downgrade cannot restore what the retention pass removed -- the text is
    # gone, that is the point of it. Cleared rows get an empty string so the
    # NOT NULL can be restored at all; that this is lossy is the honest state,
    # not a bug to work around.
    op.execute(sa.text("UPDATE answers SET question = '' WHERE question IS NULL"))
    op.alter_column("answers", "question", existing_type=sa.Text(), nullable=False)
```

## A2 · `src/backend/app/models/tables.py`

```diff
 class Answer(Base):
     __tablename__ = "answers"
     __table_args__ = (Index("ix_answers_session_id", "session_id"),)
 
     id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
     session_id: Mapped[uuid.UUID] = mapped_column(
         UUID(as_uuid=True), ForeignKey("query_sessions.id", ondelete="CASCADE"), nullable=False
     )
-    question: Mapped[str] = mapped_column(Text, nullable=False)
+    # Nullable since migration 0019, and NULL has one meaning only: the
+    # retention pass in worker/main.py has removed the text. Nothing else in
+    # the system writes NULL here -- POST /query requires min_length=3.
+    question: Mapped[str | None] = mapped_column(Text, nullable=True)
     answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
```

## A3 · `src/backend/worker/main.py`

**Import** (Kopf der Datei):

```diff
 import asyncio
 import json
 import logging
+import time
 import uuid
```

**Konstanten und SQL** — direkt nach `REQUEUE_DOCUMENT` (ca. Zeile 375):

```python
# --- Aufbewahrungsfristen (Datenminimierung) ---------------------------------
#
# Module constants and deliberately *not* `config` rows, unlike the reaper's
# timeout above: a retention period is a data-protection commitment, not an
# operational knob. As a `config` row an admin could raise it to ten years
# through the admin UI (T-37) with nobody reviewing it; as a constant the
# change has to pass a PR. Same reason ADR-008 keeps the grounding prompt out
# of that table.
SESSION_LINK_RETENTION_DAYS = 30
QUESTION_TEXT_RETENTION_DAYS = 90

# The prune has its own clock. The reaper repairs a run that is minutes late
# and therefore runs every <= 300 s; a deadline measured in days does not need
# that, and at the reaper's cadence both UPDATEs would scan `answers` 288 times
# a day to find, almost always, nothing.
PRUNE_INTERVAL_SECONDS = 3600

# Two statements, because they remove two different things.
#
# The first severs the link: after SESSION_LINK_RETENTION_DAYS the question can
# no longer be traced to a person, which is what Docs/03_QualityAttributes.md
# has claimed about query logs all along. Losing the link does not break
# anything downstream -- `_resolve_session` (app/routers/query.py) starts a new
# session when `user_id` does not match, and a session id that old is far past
# the 1 h JWT anyway.
ANONYMISE_SESSIONS = """
    UPDATE query_sessions
       SET user_id = NULL
     WHERE user_id IS NOT NULL
       AND created_at < now() - ($1::int * interval '1 day')
"""

# The second removes the text, because a question identifies its author on its
# own often enough ("wie melde ich meinen Sohn Max für ...") that severing the
# link is not the whole job.
#
# UPDATE and not DELETE, and this is the load-bearing part: `feedback.answer_id`
# is ON DELETE CASCADE (migration 0011), so deleting old answer rows would take
# Stefan's feedback history (T-32) with them -- silently, because a cascade
# reports nothing. Nulling the column keeps every row, every confidence score
# and every rating, and drops only the free text ADR-009 no longer needs.
CLEAR_QUESTION_TEXT = """
    UPDATE answers
       SET question = NULL
     WHERE question IS NOT NULL
       AND created_at < now() - ($1::int * interval '1 day')
"""


async def prune_personal_data(conn: asyncpg.Connection) -> tuple[int, int]:
    """Enforce both retention periods. Returns the two row counts, for the log.

    One transaction, so a crash between the statements cannot leave a database
    in which the link was severed but the text of the same period is still
    there -- the two are one promise, not two.
    """
    async with conn.transaction():
        sessions = await conn.execute(ANONYMISE_SESSIONS, SESSION_LINK_RETENTION_DAYS)
        questions = await conn.execute(CLEAR_QUESTION_TEXT, QUESTION_TEXT_RETENTION_DAYS)
    return _row_count(sessions), _row_count(questions)


def _row_count(command_tag: str) -> int:
    """asyncpg returns the command tag ("UPDATE 12"); the number is the point."""
    return int(command_tag.rsplit(" ", 1)[-1])
```

**Einhängen in `reaper_loop`** (ca. Zeile 466):

```diff
 async def reaper_loop(pool: asyncpg.Pool) -> None:
     """Run the reaper for as long as the worker lives.
+
+    It also carries the retention pass. Not because the two belong together --
+    they repair nothing in common -- but because this is the only loop the
+    worker already keeps alive, and two UPDATEs an hour do not justify a second
+    scheduler to start, supervise and shut down.
     """
     interval = reaper_interval(DEFAULT_PROCESSING_TIMEOUT_SECONDS)
+    # 0.0 rather than "now": time.monotonic() starts well above zero, so the
+    # first pass prunes immediately instead of an hour into the container's life.
+    next_prune = 0.0
     while True:
         await asyncio.sleep(interval)
         try:
             async with pool.acquire() as conn:
                 timeout_seconds, max_attempts = await read_reaper_config(conn)
                 interval = reaper_interval(timeout_seconds)
                 await reap_stuck_documents(conn, timeout_seconds, max_attempts)
+                now = time.monotonic()
+                if now >= next_prune:
+                    # Before the counter is advanced: a failing prune should be
+                    # retried on the next pass, not skipped for another hour.
+                    sessions, questions = await prune_personal_data(conn)
+                    next_prune = now + PRUNE_INTERVAL_SECONDS
+                    # Only when something happened. A pass that finds nothing is
+                    # the normal case and must not fill the log this change
+                    # exists to keep small (see change B).
+                    if sessions or questions:
+                        log.info(
+                            "Retention: %s Sessions entkoppelt, %s Fragetexte gelöscht",
+                            sessions,
+                            questions,
+                        )
         except Exception:
             log.exception("Reaper pass failed — next attempt in %s s", interval)
```

## A4 · Tests

**`src/backend/tests/test_worker.py`** — Unit, ohne Datenbank:

```python
async def test_prune_uses_both_retention_periods() -> None:
    """The two clocks must not drift into one — that would silently either
    keep the text 60 days too long or drop it 60 days too early."""
    calls: list[tuple[str, int]] = []

    class FakeConn:
        def transaction(self):  # noqa: ANN202 - test double
            return contextlib.nullcontext()

        async def execute(self, sql: str, days: int) -> str:
            calls.append((sql, days))
            return "UPDATE 3"

    sessions, questions = await prune_personal_data(FakeConn())

    assert calls[0][1] == SESSION_LINK_RETENTION_DAYS == 30
    assert calls[1][1] == QUESTION_TEXT_RETENTION_DAYS == 90
    assert (sessions, questions) == (3, 3)


def test_prune_never_deletes_answer_rows() -> None:
    """`feedback.answer_id` is ON DELETE CASCADE — a DELETE here would take
    Stefan's feedback history with it (T-32). Held in place by a test rather
    than by a comment, because the cascade reports nothing when it fires."""
    assert "DELETE" not in ANONYMISE_SESSIONS.upper()
    assert "DELETE" not in CLEAR_QUESTION_TEXT.upper()
```

**`src/backend/e2e/test_retention.py`** — neu, gegen die echte DB (Muster:
`e2e/test_documents_cascade.py`, weil nur eine echte Abfrage zeigt, ob das `UPDATE`
gegriffen hat):

```python
"""Modul-8-Datenminimierung: die Aufbewahrungsfristen greifen wirklich.

Vorbedingung: laufender Stack (`make up && make seed`).
"""

async def test_prune_severs_link_and_clears_text(conn) -> None:
    old = datetime.now(UTC) - timedelta(days=100)
    recent = datetime.now(UTC) - timedelta(days=10)

    old_session, old_answer = await _seed_answer(conn, created_at=old)
    new_session, new_answer = await _seed_answer(conn, created_at=recent)

    await prune_personal_data(conn)

    # 100 Tage: beide Fristen abgelaufen
    assert await _user_id(conn, old_session) is None
    assert await _question(conn, old_answer) is None
    # 10 Tage: keine der beiden
    assert await _user_id(conn, new_session) is not None
    assert await _question(conn, new_answer) is not None


async def test_prune_keeps_feedback(conn) -> None:
    """Der Grund für UPDATE statt DELETE — explizit geprüft."""
    session, answer = await _seed_answer(conn, created_at=datetime.now(UTC) - timedelta(days=200))
    await _seed_feedback(conn, answer_id=answer, helpful=True)

    await prune_personal_data(conn)

    assert await _feedback_count(conn, answer) == 1
```

## A5 · Spec nachziehen — sonst bleibt die Doku falsch

`CLAUDE.md`: „Spec und Code gehen zusammen". Vier Stellen behaupten heute eine
Eigenschaft, die das Datenmodell nicht hat. Mit dem Patch stimmt die Aussage — aber
erst nach Ablauf der Frist, und das gehört hingeschrieben:

```diff
--- Docs/03_QualityAttributes.md   (Zeile 12, Security-NFA)
-· Feedback und Query-Logs werden pseudonymisiert gespeichert
+· Feedback wird pseudonymisiert gespeichert (keine `user_id` in der Tabelle)
+· Query-Logs werden nach 30 Tagen von der Person entkoppelt, der Fragetext
+  nach 90 Tagen gelöscht (worker/main.py, Aufbewahrungsfristen)
```

Gleiche Korrektur nötig in `Docs/03_QualityAttributes.md:79`,
`Docs/06_Architecture-Draft.md:18` und `Docs/05_C4-C2_Container.md:62`.

Ebenso `Docs/02_Requirements.md:278` — dort steht „Aufbewahrungsfristen für Query-Logs
und Feedback-Freitext nicht definiert — Post-MVP". Für die Query-Logs wäre das mit
diesem Patch erledigt; der Feedback-Freitext bleibt offen und sollte als solcher
stehen bleiben, statt die Zeile ganz zu streichen.

## A6 · Was der Patch nicht kann

- **Kein Löschantrag-Workflow.** Eine Frist ist keine Auskunft und kein
  Löschbegehren auf Zuruf. `Docs/02_Requirements.md:278` bleibt für diesen Teil gültig.
- **Ohne Index.** `query_sessions.created_at` und `answers.created_at` haben keinen.
  Stündlich zwei Seq-Scans sind beim Pilot-Volumen (< 30 Nutzer) irrelevant; bei
  ernsthaftem Wachstum braucht es einen partiellen Index
  (`WHERE user_id IS NOT NULL` bzw. `WHERE question IS NOT NULL`).
- **Nichts an 🟠.** Die Frage war längst beim Provider, bevor die Uhr zu laufen begann.

---

# Änderung B · Log-Rotation in `docker-compose.yml`

## Warum

Aus L1, #15/#16: `src/docker-compose.yml` hat keinen `logging:`-Block. Damit gilt der
Docker-Default `json-file` **ohne Rotation und ohne Grössenlimit**. Was da unbegrenzt
wächst, ist personenbezogen:

- `app/routers/query.py:341,371,534,561` und `quiz.py:164,174` loggen `user_id=%s`
- nginx loggt im Default-`combined`-Format die **Client-IP** jedes Requests
- `worker/main.py:120` loggt Provider-Tracebacks — der Kommentar dort sagt selbst, dass
  die bei einem Auth-Fehler ein Fragment des API-Keys enthalten

Niemand hat je entschieden, das für immer aufzubewahren. Es ist der Default.

## Der Patch

```diff
--- src/docker-compose.yml
+++ src/docker-compose.yml
@@
 networks:
   # db is reachable from api and worker on separate networks, so api and worker
   # never share a network with each other — worker (which parses untrusted
   # uploads) cannot reach api:8000 directly, only through nginx on the edge
   # network. That's what makes --forwarded-allow-ips='*' on api safe below.
   api-db:
   worker-db:
   edge:
 
+# Logs sind hier personenbezogen: die App loggt `user_id`
+# (app/routers/query.py), nginx loggt die Client-IP jedes Requests, und der
+# Worker loggt Provider-Tracebacks (worker/main.py — laut Kommentar dort bei
+# einem Auth-Fehler mitsamt einem Fragment des API-Keys). Ohne diesen Block
+# gilt der Docker-Default json-file *ohne* Rotation und ohne Limit: die Dateien
+# wachsen, bis die Platte voll ist, und niemand hat je entschieden, sie so
+# lange aufzubewahren.
+#
+# 3 × 10 MB pro Container: genug, um einen Vorfall vom Vortag zu untersuchen,
+# und eine Obergrenze statt keiner. Eine Frist in Tagen kann json-file nicht —
+# wer die braucht, braucht einen anderen Log-Treiber, nicht eine grössere Zahl.
+x-logging: &default-logging
+  driver: json-file
+  options:
+    max-size: "10m"
+    max-file: "3"
+
 services:
   db:
     image: pgvector/pgvector:pg17
     restart: unless-stopped
+    logging: *default-logging
     environment:
@@
   api:
     build:
       context: ./backend
       args:
         INSTALL_DEV: "true"
+    logging: *default-logging
@@
   worker:
     build:
       context: ./backend
       args:
         INSTALL_DEV: "false"
+    logging: *default-logging
@@
   webapp:
     build:
       context: ./frontend
     restart: unless-stopped
+    logging: *default-logging
```

## Prüfung

```bash
cd src && docker compose config | grep -A4 "logging:"   # Anker aufgelöst?
make up
docker inspect src-api-1 --format '{{ json .HostConfig.LogConfig }}'
# erwartet: {"Type":"json-file","Config":{"max-file":"3","max-size":"10m"}}
```

Kein Test in `make qa` deckt das ab — `docker-compose.yml` wird von keiner Suite
gelesen. Die Prüfung oben ist die Verifikation; sie gehört in die PR-Beschreibung.

## Grenzen

`json-file` kann keine Frist in Tagen, nur eine Grösse. Ein System mit wenig Verkehr
behält seine Logs damit länger als eines mit viel — die Rotation ist eine Obergrenze
gegen unbegrenztes Wachstum, keine Aufbewahrungsfrist. Wer eine echte Frist braucht,
braucht einen Log-Treiber mit Zeitachse; das ist eine Betriebsentscheidung für
`Ops/`, nicht für diesen Patch.

---

## Antwort auf die Leitfrage L3

**Welche zwei Änderungen — und welche Daten fliessen jetzt nicht mehr?**

1. Nach 30 Tagen fliesst keine Verbindung mehr zwischen einer Frage und der Person, die
   sie gestellt hat; nach 90 Tagen fliesst der Fragetext gar nicht mehr. Vorher: beides
   unbegrenzt, in einer Spalte, die nie jemand liest.
2. `user_id`, Client-IPs und Provider-Tracebacks fliessen nicht mehr unbegrenzt ins
   Dateisystem, sondern in maximal 30 MB pro Container.

Und der ehrliche Teil: beides betrifft nur die lokale Kopie. Der externe Fluss aus L2
ist davon unberührt — dort hilft keine Frist, sondern nur der Provider-Wechsel.
