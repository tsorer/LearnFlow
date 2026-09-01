# Chatverlauf — T-50 PDF-Textextraktion: zerrissene Wörter reparieren

**Datum:** 2026-08-29 bis 2026-08-31
**Branch:** `feat/T-50-pdf-text-extraction`, angelegt von `origin/main` (`42591eb`). Nach dem Merge von T-43 (#104) und T-47/T-48 (#101) mit `git rebase` auf `fbff407` umgesetzt — konfliktfrei.
**Gegenstand:** [#102](https://github.com/tsorer/LearnFlow/issues/102) „[T-50] PDF-Textextraktion: zerrissene Wörter machen die Sparse-Suche unbrauchbar" (Sprint 6, US-01, ADR-007). Blockiert T-28 (#35).
**Ergebnis:** [PR #103](https://github.com/tsorer/LearnFlow/pull/103) mit zwei Commits, approved von `luenlestra`, CI grün. Kernbefund: **beide** Fehlerbilder lagen im Extraktor, nicht in den Daten — das EU-AI-Act-PDF ist intakt, pypdf < 6.16.2 hat die Wortlücken erfunden.

> Nutzer-Prompts wörtlich aus dem Sitzungstranskript (`c6eb7f5a-….jsonl`). Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> Implement GitHub issue T-50 in tsorer/LearnFlow: https://github.com/tsorer/LearnFlow/issues/102
>
> Start by reading the issue in full (`gh issue view 102 --repo tsorer/LearnFlow`) — it carries the measurements, both root causes, and the acceptance criteria. Follow the "Entwicklungsprozess" section of CLAUDE.md: read the issue, check the relevant Docs/ (ADR-007 for hybrid retrieval), work on a feature branch `feat/T-50-pdf-text-extraction` branched from origin/main, and open a PR only when asked.
>
> Short version of the problem: `src/backend/app/services/parsing.py` (`_parse_pdf` + `_normalise`) leaves words split apart for two of the three corpus documents, which makes the sparse half of hybrid retrieval miss them entirely.
>
> 1. `leitfaden_samw_forschung_menschen_2_auflage_2015.pdf` — 903 soft hyphens (U+00AD) survive parsing and split words at line breaks ("Zu­\nsatzprotokoll", "ratifi­\nzierte"). `_normalise` handles `\xa0` but not `\xad`. This is the cheap, unambiguous fix.
> 2. `EU_AI_ACT_OJ_L_202401689_DE_TXT.pdf` — the PDF text layer carries stray intra-word spaces ("hochr iskant", "Prof iling", "Abweiche nd"). Harder: a space-repair heuristic risks corrupting correct text, so first check whether the PDF can be re-sourced with a clean text layer (it is the official EU Official Journal DE version).
>
> *(gefolgt von den Hinweisen zur Verifikationsumgebung: laufender Stack, Korpus-Mount, `MSYS_NO_PATHCONV=1`, Baseline-Queries, QA im Container)*

### Claude

**Ursache 2 bestätigt wie beschrieben** — 903 Soft Hyphens im SAMW-Leitfaden. Aber beim Nachzählen fiel auf, dass das Zeichen dort **zwei Rollen** hat: 767-mal trennt es ein Wort am Zeilenumbruch, 136-mal steht es als sichtbarer Bindestrich mitten in der Zeile (`SAMW­Richtlinien`, `ICH­Leitlinie`, `Spital­ und`). Pauschales Löschen — die naheliegende Lesart des Issues — hätte `Spitalund` erzeugt.

**Ursache 1 stellte sich als etwas anderes heraus.** Statt die Heuristik zu bauen, die das Issue befürchtet, den Content-Stream aufgemacht:

- Das PDF zeichnet jedes Wort in Fragmenten mit expliziter `Td`-Positionierung (`( I H V W J)Tj 1.798 0 Td ( H O H J W )Tj` = „festg" + „elegt").
- Die Space-Entscheidung von pypdf instrumentiert: `moved_width=17.18` gegen `str_widths=1.813` bei `spacewidth=0.1` — Faktor ~9.55 zu gross.
- Der Grund: `9.5541 0 0 9.5541 … cm` bei Schriftgrösse 1. `crlf_space_check` verglich den **cm-skalierten** Vorschub gegen eine Schwelle, die nur die Textmatrix skaliert.

**Gegenprobe mit zwei fremden Bibliotheken** (in `--target`-Installationen, ohne die Container-Umgebung anzufassen): pdfminer.six und pypdfium2 lesen aus demselben PDF `hochriskant` **37-mal** — genau die Zahl aus dem Issue. Der Text-Layer war nie kaputt.

**Bevor ein Bibliothekswechsel vorgeschlagen wurde**, die naheliegendste Frage geprüft: `pip index versions pypdf` zeigte 6.16.2 gegenüber installierten 6.15.0. Damit `hochriskant` 37, `broken 0`. Der Diff der beiden Versionen bestätigte die Diagnose wörtlich — `scale_prev_x` kommt jetzt aus der kombinierten Matrix statt aus `tm_prev`.

Damit war die Antwort auf AK 2: **weder neu beschaffen noch heuristisch reparieren**, sondern `pypdf>=6.16.2` als Untergrenze. 6.16.0 und 6.16.1 gegengeprüft — beide noch fehlerhaft, die Untergrenze ist also exakt.

---

## 2 — Nutzer

> Continue from where you left off.

> Erneut versuchen

*(Sitzungsunterbrechung; zwei Harness-Prompts hintereinander.)*

### Claude

Ist-Zustand geprüft statt angenommen — Branch und Änderungen an `parsing.py`/`requirements.txt` waren intakt. Dann fertiggestellt:

- **`_normalise`:** `_SOFT_HYPHEN_BREAK` fügt die Worttrennung zusammen, der Rest wird zu `-`.
- **Zwei Fixtures von Hand gebaut** (732 B / 700 B), wie `sample.pdf`: `hyphenated.pdf` mit beiden Soft-Hyphen-Rollen, `scaled_text.pdf` mit der `cm`-Geometrie des EU-AI-Act-PDFs. Letzteres gegen beide pypdf-Versionen geprüft — liefert auf 6.15.0 `'hochr iskant einzustufen'`, auf 6.16.2 `'hochriskant einzustufen'`. Die Versionsuntergrenze ist damit ausführbar festgehalten, nicht nur kommentiert.
- **ADR-007** um „Präzisierung (T-50)" ergänzt (AK 2).
- **Ein Ärgernis unterwegs:** Der Bash-Tool-Heredoc verschluckte eine Backslash-Ebene, wodurch echte U+00AD-Zeichen in einen Quellcode-Kommentar gerieten. Auf `\xad`-Schreibweise vereinheitlicht und gegengeprüft, dass keine unsichtbaren Zeichen im Repo landen.

QA grün (`ruff`, `mypy`, 436 Tests). Ein Commit, nicht gepusht.

**Offen gelassen und benannt:** Der Stack mountete `./backend` aus dem Haupt-Checkout, nicht aus dem Worktree — die Abnahme „im laufenden System" war damit nicht durchgespielt. Stattdessen die Worker-Pipeline offline reproduziert (`parse` → `chunk_blocks` 512/64 → `to_tsvector('german', …)` gegen dieselbe Postgres-Instanz) und gefragt, ob der Stack umgezogen werden soll.

---

## 3 — Nutzer

> du kannst zu einem echte Branch wechseln und es dort durchspielen

### Claude

Den Haupt-Checkout **nicht** angefasst (`feat/T-50-…` war im Worktree ausgecheckt, ein zweiter Checkout desselben Branches ist ohnehin gesperrt). Stattdessen den Stack aus dem Worktree hochgezogen — gleicher Compose-Projektname `src`, DB-Volume und `webapp` unberührt:

- `.env` kopiert (gitignored), `api` und `worker` neu gebaut, damit pypdf 6.16.2 aus dem Image kommt statt nachgeschoben.
- **Fund:** Der `/LearningCorpus`-Mount steckte in keinem Compose-File und war nach dem Recreate weg. Die drei PDFs per `docker cp` hineingelegt, SHA-256 gegen `LearningCorpus/` geprüft.
- Korpora über die API neu hochgeladen (Login als `knowledge_owner`, Replace-Pfad aus T-15), auf `available` gewartet.

**Zahlen aus dem echten Index**, exakt wie offline vorhergesagt:

| Begriff | Korpus | vorher | nachher |
|---|---|---:|---:|
| `hochriskant` | EU AI Act | 0 | 28 |
| `Protokollierung` | EU AI Act | 0 | 2 |
| `Zusatzprotokoll` | SAMW | 0 | 1 |
| `Subsidiarität` | SKOS *(Kontrolle)* | 9 | 9 |

SKOS blieb bei exakt 200 Chunks — AK 5 belegt. EU fiel von 625 auf 525, weil ~44 000 erfundene Leerzeichen wegfallen. 0 von 939 Chunks enthielten noch ein U+00AD.

---

## 4 — Nutzer

> ergänze am besten einen Hinweis im PR, das docker-compase.yml mit T-47 angepasst wird. push unf pr erstellen

### Claude

Issue [#95](https://github.com/tsorer/LearnFlow/issues/95) (T-47) gelesen, um die Referenz korrekt zu setzen — die Eval-Harness braucht den Mount ohnehin, er gehört dorthin und nicht in einen Parsing-Fix.

[PR #103](https://github.com/tsorer/LearnFlow/pull/103) angelegt, Titel mit Branchnamen präfixt (Repo-Konvention). Im Body: beide Ursachen mit Messwerten, der AK-2-Entscheid samt Begründung, die Vorher/Nachher-Tabelle, der Hinweis auf den nötigen Re-Upload und der `docker-compose.yml`-Hinweis mit Verweis auf T-47.

---

## 5 — Nutzer

> kannst du noch den commit umbenennen, so das 'T-50:' am Anfang und nicht '(T-50)' an Ende steht?

### Claude

`git commit --amend` auf die Subject-Zeile, Body unverändert, `--force-with-lease` gepusht:

```
T-50: fix(parsing): keep PDF words whole so sparse retrieval can find them
```

Die Schreibweise wörtlich übernommen — Doppelpunkt nach der Nummer, Conventional-Commit-Präfix dahinter — und rückgefragt, falls doch ohne den ersten Doppelpunkt gemeint. Die Memory-Notiz zur Konvention entsprechend präzisiert.

Angeboten, das redundante `(T-50)` auch aus dem PR-Titel zu streichen; der Branchname enthält die Nummer bereits.

---

## 6 — Nutzer

> Name ist OK so. Anscheinend läuft der Container noch über den Worktree, stelle es wieder auf src um.

### Claude

Über `docker compose --project-directory` auf den Haupt-Checkout zurückgestellt, ohne die Shell dorthin zu wechseln. `db` und `webapp` liefen durch, das Volume blieb unberührt. Den kopierten `.env` aus dem Worktree gelöscht.

**Drei Dinge dazu benannt**, statt nur „erledigt" zu melden: Der Index bleibt korrigiert, während der laufende Code wieder der von `main` ohne den Fix ist — ein Upload vor dem Merge würde erneut zerrissene Chunks erzeugen. Das Image trägt pypdf 6.16.2 (durch `>=4.0.0` gedeckt, kein Konflikt). Und `/LearningCorpus` war wieder weg.

---

## 7 — Nutzer

> bewerte das Feedback von https://github.com/tsorer/LearnFlow/pull/103

### Claude

Review von `luenlestra`: approved, mit eigenen Messungen statt Diff-Lektüre. Die Strukturzahlen deckten sich auf den Eintrag genau mit den eigenen (903 / 767 / 136).

**Finding 1 selbst nachgestellt statt geglaubt** — Docker lief zu dem Zeitpunkt nicht, also auf Host-Python mit zwei `--target`-Installationen:

```
pypdf 6.15.0 | \n vor \xad:  326 | 'Zusatzprotokoll' nach _normalise: 0
pypdf 6.16.2 | \n vor \xad:    0 | 'Zusatzprotokoll' nach _normalise: 1
```

Das Finding stimmte und war **untertrieben**: nicht ein Wort, sondern 326 der 903 Trennstellen. Und der Ausfall ist schlimmer als „nicht zusammengefügt" — durch das nachfolgende `.replace("\xad", "-")` wird aus `Me\n\xad\nthodi` ein `Me\n-\nthodi`.

**Gegenvorschlag statt Zustimmung:** Das Review empfahl einen Kommentarsatz. Stattdessen die Zeichenklasse erweitert (`[ \t]` → `[ \t\n]`) und nachgewiesen, dass das auf der festgelegten Untergrenze für alle drei Korpora **byte-identisch** ist — Reparatur an der Wurzel statt Dokumentation der Falle.

**Finding 2** (`<7`-Cap) mit Begründung abgelehnt: Der Bruch geschah *innerhalb* von Major 6, ein Cap bei 7 hätte ihn nicht gefangen; die Fixtures prüfen auf exakte Gleichheit und CI installiert mangels Lockfile stets das neueste pypdf. Die Schwachstelle des eigenen Arguments mitgenannt. **Finding 3** und **Operativ** als Annahme bzw. als bereits richtig verortet abgehakt.

---

## 8 — Nutzer

> ja und docker läuft wieder (und ich hab den Branch auf T-50 gewechselt)

### Claude

Regex erweitert, Kommentar ergänzt, Regressionstest über den **Markdown-Pfad** — kein PDF-Fixture kann das abdecken, weil die Umbruchseite der Extraktor wählt, nicht das Dokument. Test gegen die alte Regex gegengeprüft: rot (`'Me\nthodik und ratifizierte'`).

**Zwei Umgebungsfunde**, beide gemeldet statt umgangen:

- `src-api-1` im Crash-Loop, nicht wegen T-50: Die Dev-DB stand auf Alembic-Revision `0017`, die nur auf `feat/T-43-worker-reaper` existierte. Das Muster aus der Drift-Notiz.
- QA lief deshalb in einem Wegwerf-Container aus demselben Image mit `--env-file` am `src_api-db`-Netz — gleiche Toolchain, vergleichbare Zahlen. Grün: 437 Tests.

Commit `7bb1ec7` einzeln gepusht (Korrekturen nach dem PR nicht squashen) und die Review-Antwort als PR-Kommentar gepostet.

---

## 9 — Nutzer

> mach ein rebase auf den main (T-43 ist nun gemergt) und wiederhole nochmal die Tests

### Claude

Rebase auf `fbff407` — konfliktfrei, beide Commits unverändert repliziert. QA: `ruff` ✓, `mypy` ✓, **468 Tests** (T-43 und T-47 bringen 31 dazu), `test_parsing.py` 10.

**Zwei Nebenwirkungen geprüft statt vermutet:**

- Der Alembic-Drift ist weg — T-43 bringt `0017` mit. `api` testweise neu gestartet: kommt sauber hoch. Das zuvor angebotene manuelle Downgrade war damit hinfällig.
- T-47 hat den `/LearningCorpus`-Mount in `docker-compose.yml` eingebaut; nach dem Rebase ist er da. Der PR-Hinweis „kommt mit T-47" hat sich erfüllt.

Abnahmezahlen im Index unverändert. Nicht gepusht — der Rebase braucht einen Force-Push auf einen PR mit Approve, dafür erst nachgefragt.

---

## 10 — Nutzer

> ja, force-push und PR-Body nachziehen

### Claude

`7bb1ec7 → 1843b12` mit `--force-with-lease`. PR **MERGEABLE**, Approve steht.

PR-Body an drei veralteten Stellen nachgezogen: der `docker-compose.yml`-Absatz jetzt als durch T-47 erledigt markiert (alter Kontext kurz erhalten, damit der Kommentarverlauf lesbar bleibt), ein neuer Punkt zum Rebase samt Alembic-Nebeneffekt, Testzahl von 436 auf 468.

**Angemerkt:** Der Approve gilt formal weiter, bezieht sich aber auf `7bb1ec7`. Inhaltlich identisch — ob `luenlestra` nochmal draufschaut, ist Teamentscheidung.

---

## 11 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Sitzungstranskript (`c6eb7f5a-….jsonl`) statt Rekonstruktion aus dem Gedächtnis verwendet; die zwölf Nutzer-Prompts byte-genau daraus übernommen. Bestehende Konvention aus `Frank/Prompts/` gelesen (zuletzt `2026-08-26_T-23-T-25-T-26-Konfidenz-Pipeline-PR-93.md`) und übernommen: Kopf mit Datum/Branch/Gegenstand/Ergebnis, nummerierte Abschnitte, Prompts wörtlich, Antworten als Zusammenfassung.

Kein Commit — nicht verlangt, und der Export gehört inhaltlich nicht in den T-50-PR.

---

## Was diese Sitzung methodisch geprägt hat

**Das Issue hatte in einem Punkt unrecht, und das war der entscheidende.** Es beschrieb für den EU AI Act einen kaputten Text-Layer und stellte zwei Optionen zur Wahl: PDF neu beschaffen oder Text heuristisch reparieren. Beide hätten funktioniert und beide wären falsch gewesen — die Daten waren intakt, der Extraktor nicht. Wer nur die vorgegebenen Optionen abarbeitet, hätte eine Heuristik gebaut, die auf Jahre in `_normalise` gestanden hätte.

**Die billigste Hypothese kam zu spät.** Erst wurden Content-Streams gelesen, pypdf instrumentiert und zwei Fremdbibliotheken getestet — dann erst `pip index versions pypdf`. Die Reihenfolge hätte umgekehrt eine Stunde gespart. Dass die Diagnose am Ende trotzdem zur Untergrenze passte und der Versionsdiff sie wörtlich bestätigte, war Glück in der Sache, nicht in der Methode.

**Das Review hat den einen Punkt gefunden, den die eigene Prüfung nicht abdeckte** — und der eigene Nachvollzug zeigte, dass er grösser war als beschrieben. Dass die Antwort darauf nicht der vorgeschlagene Kommentarsatz war, sondern eine Zeichenklasse, hat den Befund aus der Dokumentation in den Code verlegt, wo er nicht mehr vergessen werden kann.
