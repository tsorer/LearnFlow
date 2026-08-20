# Umsetzungsplan T-18 — LiteLLM-Integration: Prompt-Template + Antwort-Generierung

Issue: https://github.com/tsorer/LearnFlow/issues/25 · Story US-01 · Bereich Backend
Abhängig von: T-17 (#24, aktuell im Review) · Vorgelagert für: T-19, T-23, T-25, T-26

---

## 1. Ausgangslage

T-17 (`feat/T-17-query-retrieval`) liefert `POST /query` mit hybridem Retrieval und den
deterministischen Stufen 0 (Retrieval-Gate) und 1 (Retrieval-Konfidenz). Der Endpoint ist
bewusst **immer** `suppressed`, weil es keine Generierung gibt. T-18 ersetzt genau diesen
Platzhalter.

T-17 hat die Nahtstellen schon markiert; T-18 fasst nur diese an:

| Stelle in T-17 | Was T-18 daraus macht |
|---|---|
| `MESSAGE_GENERATION_PENDING` / `REASON_GENERATION_PENDING` | entfallen |
| `suppressed=True` (hart) | `False`, wenn Stufe 0 + 1 passieren |
| `message` = Platzhaltertext | generierte Antwort |
| `Answer.answer_text = None` | generierter Text |
| `DebugInfo.llm_calls = []` | ein Eintrag `step="grounding"` |
| `confidence.citation_coverage = 0.0`, `score = retrieval_score` | **bleibt so** (→ T-19/T-23) |
| `self_check_ran = False` | **bleibt so** (→ T-25) |

**Vorbedingung:** T-17 ist in `main`. Der T-18-Branch wird von `origin/main` abgezweigt,
nicht vom T-17-Branch (sonst hängt der PR an einem fremden Branch).

### Was aus dem T-17-Review noch kippen kann

Nur vier Dinge sind für T-18 überhaupt relevant. Ändert der Review daran nichts, ist dieser
Plan unverändert gültig:

1. Reihenfolge und Inhalt von `RetrievalOutcome.context` (= Kontext fürs LLM),
2. `_to_citations()` / `Citation.index` (1-basiert, gleiche Reihenfolge wie der Kontext),
3. die Konstantennamen `REASON_*` / `STAGE_*`,
4. die 503-Semantik bei Provider-Ausfall (wird für den LLM-Aufruf wiederverwendet).

---

## 2. Scope-Abgrenzung — was T-18 *nicht* ist

Der Backlog trennt die Pipeline in eigene Issues. T-18 baut nur die Generierung:

| Nicht in T-18 | Issue |
|---|---|
| Quellenreferenz-Validierung, Citation-Coverage (ADR-008 Stufe 2) | T-19 (#26) |
| Komposit-Konfidenz-Score (ADR-008 Anzeige) | T-23 (#30) |
| LLM-Self-Check (ADR-008 Stufe 3) | T-25 (#32) |
| Verdrahtung der Unterdrückungsreihenfolge | T-26 (#33) |
| Frage-UI / Konfidenz-Badges | T-20, T-27 |

Konkret: `citation_coverage` bleibt `0.0`, `confidence.score` bleibt der Retrieval-Score,
`self_check_ran` bleibt `false`, `stages` behält die zwei Einträge aus T-17.

---

## 3. Entscheidungspunkte — alle drei entschieden (2026-08-16)

### A — Fail-closed-Lücke zwischen T-18 und T-19 *(entschieden: Option A)*

Nach T-18 wird eine Antwort ausgeliefert, die **keine** Post-Generierungs-Prüfung durchlaufen
hat (Stufe 2/3 sind T-19/T-25). Das ist eine bewusste Abweichung vom Endzustand in ADR-008.

- **Option A (gewählt):** T-18 liefert die Antwort aus. Schutz sind das Retrieval-Gate,
  die Retrieval-Konfidenz, der strikte Grounding-Prompt, `temperature=0` und das
  Verweigerungs-Sentinel (siehe 5.2). T-19 folgt direkt danach; die Lücke wird im PR und in
  ADR-008 als temporärer Zustand benannt. Kein Produktivkorpus im MVP (ADR-004), also kein
  echtes Nutzerrisiko im Zeitfenster.
- **Option B:** Die Minimalprüfung „Antwort ohne mindestens eine `[n]`-Referenz → unterdrückt"
  schon in T-18. Kostet ~10 Zeilen, ist aber wörtlich Akzeptanzkriterium 1+2 von T-19 —
  T-19 wäre danach halb leer und der Review muss zweimal über dieselbe Logik.

### B — LLM-Parameter: Code-Konstanten oder `config`-Tabelle? *(entschieden: Konstanten)*

Das Frontend (`ChatView.tsx`) rendert bereits Regler für `llm_temperature`, `llm_max_tokens`,
`llm_top_p`, `llm_seed` und liest sie aus `params_used`. Trotzdem bleiben sie in T-18
Modul-Konstanten in `generation.py`, analog `embedding.py`:

1. **Kein Fail-closed-Rückfall.** Jeder heutige Config-Wert fällt bei einem kaputten Eintrag
   auf einen *strengeren* Default zurück (`_as_float` akzeptiert nur `[0, 1]`). `temperature
   = 1.8` dagegen läuft einfach durch — die Pipeline halluziniert williger und keine Stufe
   bemerkt es. Genau die Sorte Wert, die ADR-008 nicht ohne Review veränderbar haben will.
2. **`temperature=0` ist Voraussetzung, kein Kalibrierungsknopf.** ADR-009 setzt
   reproduzierbare Generierung voraus; ist der Wert zur Laufzeit verstellbar, lässt sich ein
   Eval-Ergebnis keiner Code-Revision mehr zuordnen. Die `config`-Tabelle ist für Werte, die
   der Pilot bewusst nachjustiert — dieser soll nie von 0 weg.
3. **Heute kein Nutzen.** `GET` und `PUT /admin/config` antworten beide 501 (T-37). Die
   Regler bekommen ohnehin keine Werte und können keine speichern. Bis T-37 wäre ein
   Config-Eintrag nur über psql erreichbar — und `llm_temperature` (0–2), `llm_max_tokens`
   und `llm_seed` (unbeschränkte Ints) bräuchten je einen neuen Reader mit eigener
   Validierung in `config.py`, weil `_as_float` sie ablehnt. Neue Oberfläche im
   fail-closed-Modul für einen Nutzen zwei Issues später.
4. **Akzeptanzkriterium 3 ist davon unberührt.** Provider-Austauschbarkeit liefern LiteLLM
   und `settings.llm_model`; ADR-004 behandelt den Wechsel auf Azure OpenAI EU als
   Deployment-Entscheidung mit Vorbedingungen (Pilotstart-Checkliste), nicht als
   Laufzeit-Schalter.

**Folgearbeit (nicht T-18):** die Abgrenzung ist als Kommentar an T-37 (#44) festgehalten —
die LLM-Parameter sind ausdrücklich nicht Teil von T-37, damit T-37 unabhängig von T-18
umsetzbar bleibt (Abhängigkeiten weiterhin nur T-24, T-07). Ein eigenes Issue für die
Einführung der Schlüssel (Alembic-Seed, Reader mit eigenem Wertebereich, Verdrahtung in
`generation.py`) wird **nach** der Umsetzung von T-18 angelegt — im Zuschnitt von T-42, nicht
darin. Bis dahin fallen die Regler im UI auf ihre Defaults zurück.

### C — Namensschema `suppression_reason` (Backend ≠ Frontend) *(entschieden: Backend behalten)*

Backend (T-17): `retrieval_gate`, `retrieval_confidence`.
Frontend (`MessageBubble.tsx`, aus dem UI-Spike): `no_relevant_chunks`,
`low_retrieval_confidence`, `low_citation_coverage`, `low_composite_score`, `self_check_failed`.
Das Frontend fällt heute auf die Rohstrings zurück, bricht also nicht — zeigt aber technische
IDs. **Empfehlung:** Backend-Namen behalten, Frontend-Labels in T-20/T-27 nachziehen; nicht in
T-18 mitfixen. Kein Blocker für T-18.

---

## 4. Spec zuerst (ADR-010)

Der Vertrag deckt T-18 bereits ab: `LLMCallInfo`, `message`, `refinement_hint`,
`self_check_ran` stehen seit T-03/T-17 in `openapi.yaml`. **Es gibt keine Schema-Änderung.**

Ein einziger Diff, rein beschreibend — die 503 von `POST /api/query` nennt heute nur
Embedding-Provider und Datenbank:

```yaml
        '503':
          description: >
-           Retrieval nicht verfügbar (Embedding-Provider oder Datenbank). Kein
+           Retrieval oder Antwortgenerierung nicht verfügbar (LLM-/Embedding-
+           Provider oder Datenbank). Kein
            fachliches Ergebnis, sondern ein Infrastrukturfehler — bewusst nicht
            als Unterdrückung getarnt (ADR-008).
```

`make generate-api` trotzdem ausführen und `schema.d.ts` prüfen: Erwartung ist ein leerer
Diff. Ist er nicht leer, stimmt eine Annahme oben nicht.

---

## 5. Implementierung

### 5.1 Neues Modul `src/backend/app/services/generation.py`

Eigenes Modul, nicht in `retrieval.py` und nicht in `confidence.py`: `confidence.py` ist
laut eigenem Docstring I/O-frei und deterministisch, ein LLM-Aufruf gehört dort nicht hinein.
Isoliert aufrufbar = DoD-Kriterium 3.

```python
@dataclass(frozen=True)
class GenerationResult:
    answer: str | None      # None, wenn das Modell verweigert hat
    prompt: str             # gerenderter Prompt, nur für DebugInfo.llm_calls
    raw_response: str       # unverändert, für DebugInfo.llm_calls

async def generate_answer(question: str, context: Sequence[RetrievalHit]) -> GenerationResult
def build_prompt(question: str, context: Sequence[RetrievalHit]) -> tuple[str, str]  # system, user
```

`generate_answer` bekommt die `RetrievalHit`s, nicht die Session oder den Request — die
Komponente muss ohne DB und ohne FastAPI testbar sein.

LiteLLM-Aufruf exakt nach dem Muster von `embedding.py` (das ist die Antwort auf
Akzeptanzkriterium 3 „Provider austauschbar": keine Provider-Verzweigung im Code, alles über
`settings`):

```python
await litellm.acompletion(
    model=settings.llm_model,
    messages=[{"role": "system", ...}, {"role": "user", ...}],
    temperature=0.0,                 # reproduzierbar für ADR-009-Eval
    max_tokens=MAX_ANSWER_TOKENS,
    api_base=settings.litellm_base_url or None,
    api_version=settings.litellm_api_version or None,
    api_key=settings.litellm_api_key or settings.openai_api_key,
    timeout=TIMEOUT_SECONDS,
    num_retries=MAX_RETRIES,
)
```

Konstanten mit Begründung im Modul: `TIMEOUT_SECONDS = 30.0` (Performance-NFA p95 ≤ 10 s,
T-22 — 600 s LiteLLM-Default ist inakzeptabel), `MAX_RETRIES = 1` (jeder Retry addiert voll
auf die wahrgenommene Wartezeit, es gibt kein Streaming — ADR-002),
`MAX_ANSWER_TOKENS ≈ 800`.

`settings` braucht keine neuen Felder: `llm_model` existiert bereits in `app/config.py`.

### 5.2 Grounding-Prompt-Kontrakt (ADR-007 Punkt 4, ADR-008 offener Punkt 2)

Das Referenzformat ist eine Architekturfestlegung, nicht ein Implementierungsdetail —
ADR-008 führt „Citation-Format festlegen" als offenen Punkt. T-18 legt fest:

- **Referenzformat:** `[n]`, `n` = `Citation.index` (1-basiert, Reihenfolge des Kontexts).
  Damit kann T-19 deterministisch parsen und die Fussnote zeigt auf denselben Chunk, den die
  Citation-Liste ausliefert.
- **Verweigerung:** Deckt der Kontext die Frage nicht, antwortet das Modell **ausschliesslich**
  mit dem Sentinel `WEISS_NICHT`. Ein Sentinel statt Freitext, weil ein Freitext-„weiss ich
  nicht" nicht von einer Antwort unterscheidbar ist und ADR-008 unterdrückte Antworten auf
  standardisierten Text festlegt.
- **Kontextblock:** pro Chunk `[n] (dateiname, S. x — Überschrift)` plus Inhalt, klar
  abgegrenzt, mit der expliziten Instruktion, dass der Kontext Daten sind und keine
  Anweisungen (Prompt-Injection über hochgeladene Dokumente).
- Antwortsprache Deutsch, sachlich, keine Spekulation, kein Vorwissen.

Der Prompt-Text lebt als Konstante in `generation.py` (nicht in der DB): eine Prompt-Änderung
verändert das Verhalten der Pipeline und muss durch Review und Eval, nicht über eine
Config-Zeile.

### 5.3 Änderungen in `app/routers/query.py`

Nach dem bestehenden `confidence_passed`-Block:

1. Passieren Stufe 0 + 1 → `generate_answer(request.question, outcome.context)`.
2. Fehler des Providers → `503` über denselben Pfad wie das Retrieval heute
   (`logger.exception`, Provider-Message nie in die Response — sie enthält `api_base` und
   Key-Fragmente).
3. `result.answer is None` (Sentinel) → `suppressed=True`, neue Konstanten
   `REASON_GENERATION_REFUSED = "generation_refused"` und ein eigener Meldungstext
   („Die gefundenen Stellen decken deine Frage nicht ab …"). Citations bleiben erhalten —
   die Quellen sind echt, nur die Deckung fehlt.
4. Sonst: `suppressed=False`, `message = result.answer`, `Answer.answer_text = result.answer`,
   `Answer.suppressed = False`. `confidence_score` / `retrieval_confidence` unverändert aus
   Stufe 1 (T-23 ersetzt das).
5. `DebugInfo.llm_calls` bekommt genau dann einen Eintrag, wenn generiert wurde:
   `step="grounding"` (dieser String wird vom Frontend gesucht),
   `label="Antwortgenerierung (Grounding-Prompt, ADR-007)"`, `prompt`, `response`.
   Nur für Admins — der Prompt enthält den vollen Chunk-Text.
6. `citations` bleiben unverändert alle Kontext-Chunks. Auf die tatsächlich zitierten zu
   reduzieren, setzt das Parsen der Referenzen voraus → T-19.

Konstanten `MESSAGE_GENERATION_PENDING` / `REASON_GENERATION_PENDING` und der zugehörige
Zweig entfallen; der Docstring des Moduls (er beschreibt heute explizit „keine Generierung")
wird mitgezogen.

---

## 6. Tests

**`tests/test_generation.py`** (neu, ohne DB, ohne FastAPI):

- Prompt enthält System-Instruktion, alle Kontext-Chunks und die Nutzerfrage → deckt
  Akzeptanzkriterium 1 direkt ab.
- Nummerierung im Prompt `[1..n]` stimmt mit `Citation.index` aus `_to_citations()` überein
  (gleiche Reihenfolge) — sonst zeigt die Fussnote der Antwort auf den falschen Chunk.
- Metadaten (Dateiname, Seite, Überschrift) stehen am Chunk.
- Sentinel `WEISS_NICHT` → `answer is None`; Antwort mit `[1]` → Text unverändert
  durchgereicht (kein Nachbearbeiten).
- `litellm.acompletion` wird mit `settings.llm_model`, `temperature=0.0` und dem
  Key-Fallback aufgerufen (Provider-Austauschbarkeit, Akzeptanzkriterium 3).
- Provider-Fehler wird nach oben durchgereicht, nicht abgefangen.

**`tests/test_query.py`** (erweitern, `generate_answer` in `app.routers.query` mocken):

- **Kein LLM-Aufruf unterhalb des Gates** — der Mock wird nicht awaited. Das ist der
  zentrale Regressionstest für ADR-007/ADR-008 und muss bei jeder späteren Pipeline-Änderung
  halten.
- Kein LLM-Aufruf bei Stufe-1-Unterdrückung.
- Stufen 0+1 bestanden → `suppressed=false`, `message` = generierter Text, Citations
  nummeriert.
- Sentinel → `suppressed=true`, `suppression_reason == "generation_refused"`, Citations bleiben.
- LLM-Ausfall → 503, kein Key-Fragment und kein `api_base` im Body (analog zum
  bestehenden Retrieval-Test).
- Admin sieht `llm_calls[0].step == "grounding"` mit Prompt; Learner sieht `debug is None`.

**E2E:** nichts Neues. Ein echter LLM-Aufruf in CI braucht einen Key und ist nicht
deterministisch; `e2e/test_retrieval_sql.py` deckt die SQL-Seite ab.

**Eval (DoD):** ein CI-Eval-Gate existiert noch nicht (T-28 offen, ADR-009 nicht
implementiert). Ersatzweise manuell gegen `LearningCorpus/Eval-Gold-Dataset-*.md`:
einige In-Corpus-Fragen (Antwort mit Referenzen) und Out-of-Corpus-Fragen (Sentinel bzw.
schon Gate-Unterdrückung) im laufenden Stack durchspielen und das Ergebnis im PR notieren.

---

## 7. Docs

- **ADR-007**, Abschnitt „Grounding-Prompt-Kontrakt": Präzisierung (T-18) mit Referenzformat
  `[n]` und Verweigerungs-Sentinel — gleiche Form wie die T-17-Präzisierung beim Gate.
- **ADR-008**, offener Punkt 2 („Citation-Format festlegen") auf erledigt setzen und auf
  ADR-007 verweisen. Bei Entscheidung A aus Abschnitt 3 zusätzlich der Hinweis, dass die
  Stufen 2/3 bis T-19/T-25 fehlen.
- Kein neues ADR: T-18 entscheidet nichts, was nicht in ADR-004/007/008 schon steht.

---

## 8. Ablauf

1. T-17 gemerged abwarten, `git fetch origin`, Abweichungen aus dem Review gegen Abschnitt 1
   prüfen.
2. `git switch -c feat/T-18-llm-generation origin/main` — danach **diese Plan-Datei als ersten
   Commit** auf den Branch (`Frank/Prompts/2026-08-15_T-18-Umsetzungsplan.md`, liegt bis dahin
   untracked im Working Tree und übersteht den Branch-Wechsel).
3. `openapi.yaml` (503-Beschreibung), `make generate-api`, leeren `schema.d.ts`-Diff bestätigen.
5. `generation.py` + `test_generation.py`.
6. `query.py` + `test_query.py` erweitern.
7. ADR-007/008 nachziehen.
8. `make qa` grün; Stack hoch, Akzeptanzkriterien manuell durchspielen (In-Corpus /
   Out-of-Corpus / Provider-Ausfall via falschem Key).
9. PR `feat/T-18-llm-generation: LLM answer generation with grounding prompt`, Review durch
   zweite Person. Push/PR macht der Nutzer selbst.

**Reihenfolge-Empfehlung:** T-19 direkt nach T-18 einplanen, damit die Lücke aus
Entscheidungspunkt A kurz bleibt.

## 8a. Abweichungen bei der Umsetzung (2026-08-18)

Der T-17-Branch hatte sich beim Rebase gegenüber Abschnitt 1 bewegt. Zwei Annahmen des Plans
gelten deshalb nicht mehr:

1. **Die Spec-Änderung ist keine reine Beschreibung.** T-17 hat `suppression_reason` als
   geschlossenes Enum deklariert. `generation_not_implemented` wird durch `generation_refused`
   ersetzt, das ist eine Schema-Änderung — `schema.d.ts` ändert sich mit, und der Kommentar in
   `query.py` verlangt den passenden Frontend-Label im selben PR. `MessageBubble.tsx` ist
   deshalb Teil dieses PRs, anders als in Entscheidungspunkt C angenommen. Ohne die Anpassung
   wäre `npm run check` rot: die Label-Map ist als `Record<SuppressionReason, string>` typisiert.
2. **Neuer Pfad `configuration_error`.** T-17 übersetzt eine unbrauchbare Schwelle in eine
   unterdrückte Antwort statt in einen 500 und leitet jeden Ausgang durch
   `_persist_and_respond`. Dieser Helfer bekommt in T-18 zwei Parameter (`answer_text`,
   `suppressed`) statt der bisher fest verdrahteten Werte.

3. **Nachtrag aus dem Review (2026-08-18).** Vier Befunde sind in den PR eingeflossen:
   `finish_reason == "length"` wird ausgewertet und führt zum neuen Grund
   `generation_truncated` (fail-closed, ADR-008); im Admin-Panel war der Composite-Block an
   feste Stufen-Indizes gebunden und rendert seit T-17 nie — jetzt an Stage-IDs verankert; das
   Citation-Badge verglich die noch nicht berechneten 0.0 gegen die Schwelle und färbte jede
   korrekte Antwort rot; und das Unterdrückungs-Badge hing an `m.confidence`, womit
   `configuration_error` als einziger Grund unsichtbar war. Nicht übernommen: Gate über die
   Top-`n` (dokumentierter Entscheid in ADR-007, Kalibrierungsfrage), fehlende Prüfung
   `context_top_n <= retrieval_top_k` (Folge-Issue, Wirkung ≤ 0.067 am Score) und das
   Rate-Limit (bereits als T-45 offen).

Unverändert gültig: Kontextreihenfolge, `Citation.index`, die 503-Semantik und die
Scope-Abgrenzung gegen T-19/T-23/T-25.

## 9. Definition of Done — Prüfung gegen die Akzeptanzkriterien

| Kriterium | Nachweis |
|---|---|
| Prompt-Template enthält System-Anweisung, Kontext-Chunks, Nutzerfrage | `test_generation.py`, Prompt-Assertions |
| Antwort wird via LiteLLM generiert | `query.py` → `generate_answer` → `litellm.acompletion`; manueller Durchlauf |
| LLM-Provider austauschbar (LiteLLM-Abstraktion) | keine Provider-Verzweigung, alles aus `settings` (wie `embedding.py`); Test auf die Aufrufparameter |
| RAG-Komponente isoliert aufrufbar | `generate_answer` ohne DB/FastAPI testbar |
| CI grün | `make qa` |
| Eval-Gate nicht verschlechtert | manuell gegen Gold-Dataset (kein automatisiertes Gate vorhanden, T-28) |
