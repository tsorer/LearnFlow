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

Der dritte Job **`e2e`** (T-09) ruft `make e2e`: das Target startet einen Stack per
Docker Compose, seedet die Testuser und lässt `pytest e2e` laufen. Geprüft wird der
Login-Flow über nginx gegen die echte Datenbank. Er deckt die Nahtstellen ab, welche
die beiden Sprach-Jobs prinzipbedingt nicht sehen — das `/api`-Rewrite von nginx, den
SPA-Fallback und den echten bcrypt-Hash aus der `users`-Tabelle.

**Eigenes Compose-Projekt, flüchtige Datenbank (T-55, #123).** `make e2e` fährt
nicht den Entwicklungs-Stack, sondern ein zweites Projekt (`learnflow-e2e`, siehe
`docker-compose.e2e.yml`) mit eigenen Containern und eigenem Netz. Die Datenbank
liegt dort auf **tmpfs** — im Arbeitsspeicher, mit dem Lauf verschwunden. Der
Entwicklungs-Stack läuft unberührt daneben; er muss dafür nicht einmal gestartet
sein.

Das schliesst zwei Dinge, die vorher nur durch Sorgfalt zusammengehalten wurden:

- Ein e2e-Lauf hinterliess Dokumente, Antworten und verstellte `config`-Zeilen in
  der Entwicklungsdatenbank. Der Round-Trip-Test in `test_admin_config_endpoint.py`
  überschrieb ausserdem `changed_at`/`changed_by` **jeder** schreibbaren Zeile — die
  Frage «wer hat diesen Schwellenwert wann gesetzt» war nach jedem Lauf
  unbeantwortbar. Nachgemessen: nach einem vollen Lauf im eigenen Projekt sind
  Dokumentzahl und `changed_at` der Entwicklungsdatenbank unverändert.
- `pgdata` trägt in `docker-compose.yml` einen **globalen** Namen
  (`learnflow_pgdata`), ist also nicht projektgebunden. Das e2e-Projekt überschreibt
  den Mount, sodass es dieses Volume gar nicht erst sieht.

Bei einem roten Lauf bleibt der Stack absichtlich stehen: `make e2e-logs` für die
Container-Logs, `make e2e-down` zum Aufräumen. Bei einem grünen räumt das Target
selbst ab.

Der nächste `make e2e` räumt in jedem Fall zuerst auf, bevor er hochfährt. Ohne
das liefe ein Retry nach einem roten Lauf gegen dessen Datenbank — `up -d --wait`
recreated laufende, unveränderte Container nicht — und gegen denselben
api-Prozess mit warmem Rate-Limiter: `/auth/login` erlaubt 5/min/IP, und die
Suite macht genau fünf Logins aus derselben Container-IP. Die Zusage «pro Lauf
neu migriert und geseedet» gilt damit auch für den Wiederholungslauf. Nachschau
ist trotzdem möglich: der Stack steht, bis man den nächsten Lauf startet.

**Kein vierter CI-Job für den Eval:** Es gibt (noch) kein `OPENAI_API_KEY`-Secret
im Repo — nicht auf Repo-, Environment- oder Org-Ebene. Ein Job, der sich deshalb
bei jedem Lauf bedingungslos selbst überspringt, wurde bewusst **nicht** gemergt:
er erschiene in der Checks-Liste und sähe wie ein Gate aus, ohne je etwas zu
messen — GitHub wertet einen übersprungenen Required Check als bestanden, was
genau die stille Aufweichung wäre, die ADR-009 verhindern soll (Review auf #100).
Die Out-of-Corpus-Refusal-Rate (T-28, ADR-009 DoD-Kriterium 4: ≥ 90 % „Weiss ich
nicht" auf den 22 Out-of-Corpus-Fragen) und, seit T-56, die In-Corpus-Gates
(Halluzinationsrate = 0 %, False-Suppression ≤ 15 % Startwert, auf den 45
In-Corpus- und 13 Adversarial-Fragen — siehe ADR-009 Abschnitt 2A) aus
`LearningCorpus/gold-eval-dataset.yaml` (T-47/T-48) sind deshalb vorerst ein
**manuell auszuführendes Release-Gate**:

```bash
make up && make seed && make seed-corpus && make eval
```

**Was der Lauf anfasst (T-55, #123).** Seit T-55 läuft der Eval in-process gegen
die ASGI-App, in einer Transaktion, die am Ende zurückgerollt wird. Er
hinterlässt deshalb **keine Zeile** in der Datenbank — vorher sammelte jeder Lauf
22 `answers`-Zeilen in der Entwicklungsdatenbank an. Gemessen wird immer gegen
die Seed-Defaults der Schwellen, gesetzt innerhalb derselben Transaktion: eine
lokale Kalibrierung bleibt unberührt, und zwei Läufe sind vergleichbar. Vorher
hing der Messwert am Zustand der Datenbank — derselbe Korpus ergab 90,9 % oder
95,5 %, je nach kalibrierten Schwellen.

Der Lauf spricht dadurch kein HTTP mehr nach aussen. Fachlich braucht er nur
noch eine erreichbare Datenbank mit indexiertem Korpus — technisch weiterhin
den stehenden api-Container, weil `make eval` per `docker exec src-api-1`
startet. Der ist seither aber blosser Ausführungsort, nicht mehr das gemessene
System.

**Laufzeit und Kosten (`make eval`, beide Tests, Profil `openai`, gemessen
2026-09-11 gegen `gpt-4o-mini`):** die Out-of-Corpus-Refusal-Rate (22 Fragen,
kein echter Generierungsaufruf — das Retrieval-Gate greift vor jedem LLM-Call)
läuft in ~45 s. Der In-Corpus-Test (T-56, 58 Fragen, **echte** Generierung plus
im Self-Check-Grenzband ein zweiter Aufruf) braucht ~2:25 min für 77
LLM-Aufrufe (~166 k Prompt-, ~3,7 k Antwort-Token) — rund drei Rappen bei den
zum Zeitpunkt der Messung geltenden `gpt-4o-mini`-Preisen. Zusammen liegt
`make eval` damit bei rund 3 Minuten und deutlich unter zehn Rappen pro Lauf.
Beide Zahlen schwanken mit der Provider-Latenz und -Preisliste, nicht nur mit
dem Code — für ein Budget genügt die Grössenordnung.

**Messvarianten.** `EVAL_PROFILE` wählt die Konfiguration (`eval/profiles.py`):

```bash
make eval                              # ausgeliefertes Profil — das Gate
make eval EVAL_PROFILE=qwen3-local     # Vergleichslauf, meldet ohne zu gaten
```

Ein Profil darf nur Modell und Zeitbudgets setzen; `TEMPERATURE` und die
Schwellen bleiben ausgeschlossen (`tests/test_eval_profiles.py` hält das fest).
**Das Gate greift nur beim ausgelieferten Profil** — ein Vergleichslauf gegen ein
lokales Modell ist ein Messergebnis, kein gerissenes Release-Gate.

Jeder Lauf schreibt nach `src/backend/eval/out/<profil>/<zeitstempel>/`, dort
neben der CSV ein `run.json` mit Modell, wirksamen Schwellen, Überschreibungen
und Git-SHA. Ein Pfad überlebt Kopieren nicht, ein `run.json` schon. Der
In-Corpus-Test (T-56) schreibt in ein eigenes Unterverzeichnis,
`.../<profil>/in-corpus/<zeitstempel>/` — sonst würde `eval/compare.py`, das
je Profil den *neuesten* Lauf liest, nach einem `make eval` (beide Tests im
selben Prozess) den falschen der beiden Läufe erwischen.

`eval/out/` ist gitignored und rein lokal. Was aufbewahrt werden soll, gehört
nach `EvalAnalysis/` — dort erzeugt `python -m eval.compare` aus den Läufen
mehrerer Profile einen Vergleichsbericht, daneben steht die Einordnung von
Hand. Siehe `EvalAnalysis/README.md`.

Automatisierung in CI folgt mit **T-53 (#110)**, gekoppelt an den ohnehin
anstehenden Wechsel auf Azure OpenAI EU (ADR-004) — dort auch die Fragen nach
Trigger (`pull_request` vs. `push`/`workflow_dispatch`) und Secret-Scope geklärt.
Bis dahin bleiben **beide** Eval-Tests manuelle Release-Gates, aus demselben
Grund (kein `OPENAI_API_KEY`-Secret).

**In-Corpus-Gates (T-56).** Der erste Lauf gegen die Seed-Defaults
(2026-09-11, `EvalAnalysis/2026-09-11_In-Corpus-Befunde.md`) hält das
Halluzinations-Gate (0 % über 33 ausgelieferte Antworten), reisst aber das
False-Suppression-Gate deutlich (33–38 % über mehrere Läufe gegen den
15-%-Startwert — die Rate schwankt lauf-zu-lauf, siehe die Befunde-Datei).
Das ist der erwartete erste Befund, kein Fehler im Test — ADR-009 nennt 15 %
ausdrücklich als zu kalibrierenden Startwert, und das Gate wurde dafür
**nicht** aufgeweicht. Die Kalibrierung selbst ist **T-57 (#125)**; bis dahin ist
`make eval` (der In-Corpus-Teil) lokal rot und meldet damit korrekt einen noch
offenen Zustand — **kein** Required Check und damit ohne Wirkung auf `main`.

Aus demselben Grund kein eigener CI-Job für die p95-Latenzmessung (T-22, #29,
ADR-008: „Offen bleibt die Latenz" — der optionale zweite LLM-Aufruf im
Self-Check-Grenzband ist das Latenzrisiko): kein `OPENAI_API_KEY`-Secret, und
zusätzlich ungeeignet für einen Required Check, weil das Ergebnis von externer
Provider-Latenz abhängt, nicht nur vom Code. Auch das bleibt vorerst ein
manuell auszuführender lokaler Check:

```bash
make up && make seed && make seed-corpus && make perf
```

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

make e2e     # Job `e2e` — fährt seit T-55 seinen eigenen Stack hoch und wieder ab;
             # der Entwicklungs-Stack muss dafür nicht laufen
```

Die CI führt für `e2e` wörtlich denselben Befehl aus. Vorher waren es dort drei
Schritte (`up`, `seed`, `e2e`) und lokal ein anderer Ablauf — nur einer von beiden
war je getestet.

Zusätzlich, aber **kein CI-Job** (siehe oben — manuelles Release-Gate bis T-53 #110):

```bash
make up && make seed && make seed-corpus && make eval   # braucht ausserdem
                                                          # einen echten
                                                          # OPENAI_API_KEY in .env
make up && make seed && make seed-corpus && make perf    # dito, p95-Latenz (T-22)
```

`make e2e`, `make eval` und `make perf` sind bewusst nicht Teil von `make qa`: sie
brauchen Container, während `make qa` ohne sie auskommen soll. `make e2e` bringt
seine seit T-55 selbst mit; `eval` und `perf` setzen den laufenden Entwicklungs-Stack
samt indexiertem Korpus voraus. `make eval` misst darin in-process und spricht kein
HTTP mehr nach aussen — den api-Container braucht er weiterhin, aber als
Ausführungsort des `docker exec`, nicht mehr als gemessenes System.

**Seriell, und das ist zugesichert.** Innerhalb einer Suite schreiben mehrere Module
dieselben `config`-Zeilen; parallel ausgeführt zögen sie einander die Schwellen weg,
nichtdeterministisch. Bisher passierte das nur deshalb nicht, weil `pytest-xdist`
nicht installiert ist — ein `-n auto` in `addopts` hätte gereicht. Seit T-55 sagt
`e2e/conftest.py` in dem Fall beim Start ab und nennt den Grund, statt hinterher
unerklärlich rot zu werden.

Zwischen den Suiten ist die Frage seit T-55 entschärft: `e2e` fährt eine eigene
Datenbank (tmpfs, eigenes Compose-Projekt), und `eval` rollt seine Transaktion am
Ende zurück. Geteilt wird nur noch die Entwicklungsdatenbank zwischen `eval` und
`perf`.

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
   (erscheinen in der Liste, sobald der Workflow einmal gelaufen ist).
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
Das Eval-Gate (DoD-Kriterium 4, ADR-009) ist als `make eval` nach demselben Muster
vorbereitet (T-28) — vorerst nur für die Out-of-Corpus-Refusal-Rate und als manueller
Schritt, mangels CI-Secret noch kein eigener Job (siehe oben, T-53 #110). Die
In-Corpus-Metriken folgen als eigener Ausbauschritt von ADR-009. Dieselbe
Automatisierungslücke gilt für `make perf` (T-22, #29, p95-Latenz), das nach exakt
demselben Muster gebaut ist.
