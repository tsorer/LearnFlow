# CI-Runbook — "grün" lokal und als Merge-Gate

*Bezug: DoD-Kriterium 2 „CI grün: Lint + Type-Check + Tests" · Stack: ADR-002 (Python 3.13/FastAPI · React 18/TypeScript)*

---

## Was „grün" bedeutet

Bei jedem Push und Pull Request läuft ein fester Satz Checks. **Grün = jeder Check
hat Exit-Code 0.** Schlägt einer fehl (Exit-Code ≠ 0), ist der Lauf **rot**. Der Wert
liegt darin, dass es maschinell und für alle gleich passiert — nicht „lief bei mir".

Die Checks laufen in drei Jobs: je einer pro Sprache, plus einer gegen den
vollständigen Stack.

| Ebene | Backend (Python) | Frontend (TypeScript) |
|---|---|---|
| Lint / Stil | `ruff check .` | `eslint .` |
| Typen | `mypy` | `tsc --noEmit` |
| Tests | `pytest` | `vitest run` |

Der dritte Job **`e2e`** (T-09) startet den Stack per Docker Compose, seedet die
Testuser und ruft `pytest e2e`: geprüft wird der Login-Flow über nginx gegen die
echte Datenbank. Er deckt die Nahtstellen ab, welche die beiden Sprach-Jobs
prinzipbedingt nicht sehen — das `/api`-Rewrite von nginx, den SPA-Fallback und
den echten bcrypt-Hash aus der `users`-Tabelle.

`tsc --noEmit` und `mypy` sind das Review-Netz aus ADR-002: sie fangen genau die
Fehlerklasse KI-generierten Codes (falsche Props, erfundene Signaturen, ungenutzte
Variablen) zur Compile-Zeit ab.

### Leeres Scaffold = grün

Solange noch kein Quellcode existiert, übersprigen sich die Typ-/Test-Checks selbst und
der Lauf ist grün — so funktioniert das Merge-Gate ab dem ersten Tag, ohne `main` zu
blockieren. Die Checks überspringen sich selbst und greifen automatisch, sobald die
erste Datei dazukommt:

- **mypy** läuft erst, wenn eine `.py`-Datei existiert (Guard im Workflow/`Makefile`).
- **pytest** wertet „keine Tests" (Exit-Code 5) als grün; ein echter Testfehler (Exit
  1) bleibt rot.
- **tsc** läuft erst, wenn eine `.ts`/`.tsx`-Datei unter `src/` liegt
  (`scripts/check-types.mjs`).
- **vitest** läuft mit `--passWithNoTests`.

---

## Verifikation 1 — lokal, vor dem Push

Aus `src/` führen diese Befehle lokal aus, was die CI ausführt:

```bash
make qa      # Jobs `backend` + `frontend`
make qa-be   # nur Python
make qa-fe   # nur TypeScript

make up && make seed && make e2e   # Job `e2e` — braucht den laufenden Stack
```

`make e2e` ist bewusst nicht Teil von `make qa`: es setzt gestartete Container
voraus, während `make qa` ohne sie auskommen soll.

Eine separate Toolchain-Installation braucht es nicht — `make qa-be` läuft im
api-Container, `make qa-fe` in einem `node:22-alpine`-Wegwerfcontainer. Für das
Frontend gilt: `package-lock.json` committen, die CI nutzt `npm ci`.

So sieht der grüne Lauf aus (Beispielmodul `app/confidence.py` + Test):

```
Ran 4 tests ... OK
-> Exit-Code: 0
```

Und so der rote — jemand ändert in `should_answer` das `>=` zu `>` und bricht damit
das Fail-closed-Verhalten an der Schwelle:

```
AssertionError: False is not true   (test_boundary)
FAILED (failures=1)
-> Exit-Code: 1
```

Der Exit-Code ist das einzige Signal, auf das die CI hört.

---

## Verifikation 2 — in der CI, als erzwungenes Merge-Gate

> **Status (2026-08-12): aktuell deaktiviert.** Die Regel wurde im Rahmen von T-41
> aktiviert und verifiziert (Issue #64), auf Team-Entscheid aber wieder entfernt, weil
> alle im Team direkt auf `main` Artifakte pushen können müssen — „Require a pull request before
> merging" verhindert das für alle, auch für Admins. Die Anleitung unten bleibt als
> Vorlage stehen, falls die Regel später wieder aktiviert wird.

Die Datei `.github/workflows/ci.yml` führt dieselben Befehle bei jedem PR auf einem
sauberen Runner aus. Damit „grün" nicht Vertrauenssache ist, sondern **technisch
erzwungen**, einmalig in GitHub einstellen:

1. Repo → **Settings → Branches → Add branch protection rule**
2. Branch-Pattern: `main`
3. **Require status checks to pass before merging** aktivieren
4. Als erforderliche Checks **`backend`**, **`frontend`** und **`e2e`** auswählen
   (erscheinen in der Liste, sobald der Workflow einmal gelaufen ist)
5. Empfohlen: **Require a pull request before merging** (greift mit DoD-Kriterium 1,
   Review durch eine zweite Person)

Ergebnis: Ein roter PR lässt sich nicht mergen. **„CI grün" = grüner Haken am PR.**

---

## Reproduzierbarkeit

- **Backend:** Tool-Versionen sind in `backend/requirements-dev.txt` gepinnt — lokal
  und in CI identisch.
- **Frontend:** `package-lock.json` committen; die CI nutzt `npm ci` (installiert exakt
  den Lockfile-Stand). Ohne committeten Lockfile schlägt `npm ci` fehl.

---

## Erweitern

Neue Checks gehören an **eine** Stelle und werden von beiden Verifikationswegen
übernommen: einen Befehl in `frontend/package.json` (`scripts.check`) bzw. ins
`Makefile` aufnehmen — `make check` und die CI ziehen automatisch nach.
Das spätere Eval-Gate (DoD-Kriterium 4, ADR-009) wird als zusätzlicher CI-Job nach
demselben Muster ergänzt.
