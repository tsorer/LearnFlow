# Chatverlauf — Umsetzung T-24 (Konfidenz-Schwellenwert in der `config`-Tabelle)

**Datum:** 2026-08-09
**Branch:** `feat/T-24-config-confidence-threshold` (von `feat/T-12-parsing-chunking`, nicht von `main`)
**Gegenstand:** [Issue #31](https://github.com/tsorer/LearnFlow/issues/31) „[T-24] DB config-Tabelle: Konfidenz-Schwellenwert"
**Ergebnis:** ein Commit `e7125fe`, lokal — Push und PR noch offen

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen. Entscheidungen aus den Rückfrage-Dialogen sind als Tabellen wiedergegeben.

---

## 1 — Nutzer

> Erstelle einen Plan für die Umsetzung von https://github.com/tsorer/LearnFlow/issues/31.

### Claude

*(Plan-Modus — keine Änderungen ausser der Plan-Datei.)*

**Bestandsaufnahme:** Issue #31 via `gh`, dazu ADR-008, US-02/US-11 in `Docs/02_Requirements.md`, `Docs/08_ERD.md`, `Ops/07_Pilotstart-Checkliste.md`, `openapi.yaml`, die Alembic-Historie sowie `app/`- und `worker/`-Code.

Befund:

- Tabelle `config` und ORM-Modell `Config` existieren bereits (Migration `0004`, `app/models/tables.py:121`) — **keine Schema-Migration nötig**, nur ein Seed.
- Gesetzt sind bereits `min_retrieval_confidence` 0.40 (ADR-008 Stufe 1) und `min_citation_coverage` 0.50 (Stufe 2) — **nicht** aber die Schwellen für den *angezeigten* Komposit-Score, um den US-02 geht.
- Im `app/`-Teil liest **nichts** aus `config`. Einziger Leser ist der Worker über raw asyncpg (`read_chunk_config`), bewusst ohne Cache — genau das Muster, das „ohne Neustart" erfüllt.
- **Widerspruch in den Docs:** `Ops/07_Pilotstart-Checkliste.md` legt `confidence_threshold_high` / `_medium` / `stale_threshold_days` von Hand per `INSERT` an; das ERD kennt diese Keys nicht und nennt für Stale den real existierenden Key `stale_days`.
- `PATCH /admin/config` ist ein eigenes Ticket (T-37) → kein Endpoint, damit auch keine `openapi.yaml`-Änderung (ADR-010 gewahrt).

**Entscheidungen (Rückfrage-Runde 1):**

| Frage | Entscheid |
|---|---|
| Welche config-Keys? | **Band-Schwellen** `confidence_threshold_high` 0.75 + `confidence_threshold_medium` 0.45 — deckt das ADR-008-Bändermodell ab und löst den Widerspruch Ops ↔ ERD auf |
| Wie weit geht das Backend? | **Service + Unit-Tests**, kein Endpoint (T-37 setzt darauf auf) |
| Reload-Mechanik | **Kein Cache, Read-per-Use** — analog `read_chunk_config` |

Danach vollständiger Plan mit Migration, Service-Signatur, Testliste, Docs-Updates und Verifikationsschritten vorgelegt.

---

## 2 — Nutzer

> *(Plan freigegeben)*

### Claude

**Vor dem ersten Schritt neu geprüft** — und der Git-Stand hatte sich gegenüber dem Sitzungsbeginn geändert: Branch war inzwischen `Frank`, Working Tree sauber, die T-12-Änderungen committet.

Dabei ein Fund, der den Plan berührte: **Migration `0007_chunking_config` liegt nicht auf `main`**, sondern im offenen [PR #65](https://github.com/tsorer/LearnFlow/pull/65). Ein `0008` mit `down_revision = "0007"` wäre auf einem Branch von `main` nicht lauffähig gewesen.

**Entscheidung (Rückfrage-Runde 2):**

| Frage | Entscheid |
|---|---|
| Branch-Basis, da 0007 noch nicht auf `main` | **Auf dem T-12-Branch stapeln** — Migration wird `0008`, sofort lauffähig; PR-Base nach dem Merge von #65 auf `main` |

**Umgesetzt:**

- `alembic/versions/0008_confidence_thresholds.py` — seedet beide Keys nach dem Muster von `0007` (`op.get_bind()` + `sa.text(...)` mit Params-Dict, weil `op.execute` keine Parameter binden kann). Die Band-Semantik steht in den `description`-Spalten: `score >= high` → Hoch, `score >= medium` → Mittel, darunter unterdrückt — die `>=` bleiben `>=` (CLAUDE.md-Tripwire zu ADR-008).
- `app/services/config.py` — `read_confidence_thresholds(db)` liest pro Aufruf über das bisher ungenutzte `Config`-ORM-Modell; frozen Dataclass `ConfidenceThresholds` als Rückgabe. Fehlender Key, nicht-numerischer Wert und die Invariante `medium > high` fallen auf die Modul-Defaults zurück und loggen eine Warnung, statt die Pipeline mit einer unbewachten oder invertierten Schwelle laufen zu lassen (fail-closed).
- `tests/test_services_config.py` — 6 Tests (DB-Werte, fehlende Keys, gemischt, nicht-numerisch, invertierte Bänder, und als AK-Nachweis zwei aufeinanderfolgende Aufrufe mit unterschiedlichen Werten). Dateiname bewusst `test_services_config.py`, da `tests/test_config.py` bereits die pydantic-`Settings` testet.
- Docs: ERD um beide Keys und Migration `0008` ergänzt; Pilotstart-Checkliste 3.2 vom manuellen `INSERT` auf „prüfen + nachjustieren per `UPDATE`" umgestellt und `stale_threshold_days` auf `stale_days` korrigiert.

**Checks:** `ruff` ✅ · `mypy app worker` ✅ · `pytest` 64 ✅ · Frontend-Gate (`npm ci` + lint + tsc + vitest) ✅. Zwei kleine Korrekturen unterwegs: eine E501-Zeile und eine mypy-strict-Annotation für `dict(result.all())` (SQLAlchemy-`Row` ist nicht als `tuple[str, str]` typisiert).

**Manuelle Verifikation im laufenden System:**

| AK | Nachweis |
|---|---|
| Schwellenwert in DB gespeichert | `alembic upgrade head`, beide Keys per psql sichtbar |
| Änderung wirkt sofort ohne Neustart | Reader im laufenden `src-api-1` alle 5 s; nach `UPDATE … SET value='0.90'` per psql liefert der nächste Read `high=0.9` — Read 0: `0.75`, Read 1–5: `0.9`, kein Container-Neustart dazwischen |
| Default-Wert vorhanden | Seed in `0008` **und** Modul-Konstanten als Fallback (Tests 2/3) |

Zusätzlich `alembic downgrade 0007` → beide Keys weg, `upgrade head` → wieder da. Manuell gesetzter Wert 0.90 dabei auf 0.75 zurückgesetzt.

**Hindernis:** Der erste Commit enthielt nur die beiden Docs — die drei neuen Backend-Dateien fehlten. Ursache: das Quellverzeichnis heisst auf der Platte `Src`, git trackt es als `src` (`core.ignorecase=true`); `git add src/...` erfasst **neue** Dateien dann lautlos nicht. Mit `git add Src/...` nachgeholt und den (unpushed) Commit amendiert. Kontrolle über `git show --stat HEAD`, nicht über den Exit-Code.

---

## 3 — Nutzer

> zum Branch Frank wechseln und Chatverlauf bitte nach Frank/Prompts als md-Datei exportieren

### Claude

Auf `Frank` gewechselt (T-24-Commit bleibt auf seinem Branch), Verlauf als diese Datei abgelegt.

---

## Ergebnis

- **Ein Commit** `e7125fe` auf `feat/T-24-config-confidence-threshold`, +250/−7 über 5 Dateien.
- **Alle drei Akzeptanzkriterien** aus Issue #31 erfüllt und im laufenden System durchgespielt.
- **Doc-Inkonsistenz** zwischen Pilotstart-Checkliste und ERD mitbereinigt (Keys werden jetzt migriert, `stale_days` statt `stale_threshold_days`).
- **Offen für die DoD:** Push, PR und Review durch eine zweite Person.

### Bewusste Abgrenzungen

| Nicht umgesetzt | Grund |
|---|---|
| `PATCH /admin/config` | Eigenes Ticket T-37 |
| Berechnung des Komposit-Scores und die Band-Zuordnung selbst | Gehört zur Query-Pipeline; `/api/query` ist heute ein Stub — ein Konsument ohne Aufrufer wäre Ballast (DoD-Kriterium Code-Qualität) |
| `openapi.yaml` | Keine neue API-Oberfläche → keine Spec-Änderung nötig (ADR-010) |

### Bekannte offene Punkte

- Der Branch sitzt auf `feat/T-12-parsing-chunking`. Die PR-Base muss auf `main` gesetzt werden, sobald #65 gemergt ist — sonst enthält der Diff auch T-12.
- Die in ADR-008 erwähnten **Gewichte** der Komposit-Konfidenz sind weiterhin nicht in `config` gesetzt; sie gehören zum Ticket, das den Score tatsächlich berechnet.
- Die Startwerte 0.75 / 0.45 stammen aus der Pilotstart-Checkliste und sind laut ADR-008 unkalibrierte Hypothesen.
