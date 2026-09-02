# Chatverlauf — Umsetzung T-18 (LiteLLM-Integration: Prompt-Template + Antwort-Generierung)

**Datum:** 2026-08-15 (Planung) bis 2026-08-19 (Umsetzung, PR, Review-Nachgang)
**Branch:** `feat/T-18-llm-generation` → [PR #84](https://github.com/tsorer/LearnFlow/pull/84), gemerged als `7425ee8`
**Gegenstand:** [Issue #25](https://github.com/tsorer/LearnFlow/issues/25) „[T-18] LiteLLM-Integration: Prompt-Template + Antwort-Generierung"
**Ergebnis:** drei Commits (Plan, Umsetzung, Review-Nachgang), CI grün auf allen drei Jobs, in `main`

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen. Entscheidungen aus den Rückfrage-Dialogen sind als Tabellen wiedergegeben.

---

## 1 — Nutzer

> erstelle einen Umsetzungplan für https://github.com/tsorer/LearnFlow/issues/25 (T-18). Berücksichtige dabei auch den Branch für T-17. Ist noch im Review, ich erwarte aber keine grossen Änderungen. Die Umsetzung erfolgt aber erst, wenn T-17 im main ist.

### Claude

**Bestandsaufnahme:** Issue #25 via `gh`, der T-17-Branch (`query.py`, `retrieval.py`, `confidence.py`, `config.py`, `openapi.yaml`), ADR-007/008, das bestehende Frontend (`ChatView.tsx`, `MessageBubble.tsx`) und der gesamte offene Backlog.

Befund:

- Der Vertrag deckt T-18 bereits ab — `LLMCallInfo`, `message`, `refinement_hint`, `self_check_ran` stehen seit T-03/T-17 in `openapi.yaml`. Erwartete Spec-Änderung: nur die 503-Beschreibung.
- T-17 hat die Nahtstellen markiert (`REASON_GENERATION_PENDING`, `llm_calls = []`, `suppressed = True` hart, `answer_text = None`) — T-18 fasst genau diese an.
- **Scope ist enger als er aussieht:** Citation-Validierung (#26), Komposit-Score (#30), Self-Check (#32) und die Verdrahtung (#33) sind eigene Issues.
- Nebenbefund: #30 (T-23) beschreibt den Konfidenz-Score als semantische Ähnlichkeit Antwort ↔ Chunks, ADR-008 als Kombination aus Retrieval-Konfidenz und Citation-Coverage. Echter Widerspruch, gehört aber zu T-23.

Plan als `Frank/Prompts/2026-08-15_T-18-Umsetzungsplan.md` abgelegt, mit drei offenen Entscheidungspunkten.

---

## 2 — Nutzer

> für Punkt 1 stimme ich zu: Benennen, da T-19 gleich anschliessend umgesetzt wird. Punkt 2: wieso kein config-Eintrag? Punkt 3 sehe ich auch so.

### Claude

Eingeräumt, dass die erste Begründung („verändert keine Retrieval-Qualität", das Kriterium aus `embedding.py`) hier nur halb passt — Temperature und Max-Tokens verändern sehr wohl die Antwortqualität. Das tragfähige Kriterium ist ein anderes:

| Argument | Inhalt |
|---|---|
| Kein Fail-closed-Rückfall | Jeder Config-Wert fällt bei kaputtem Eintrag auf einen *strengeren* Default (`_as_float` akzeptiert nur `[0, 1]`). `temperature = 1.8` läuft einfach durch — keine Stufe bemerkt es |
| Voraussetzung statt Knopf | ADR-009 setzt reproduzierbare Generierung voraus; zur Laufzeit verstellbar liesse sich ein Eval-Ergebnis keiner Code-Revision mehr zuordnen |
| Heute kein Nutzen | `GET`/`PUT /admin/config` antworten beide 501 (T-37); die Regler im UI bekommen ohnehin nichts. Neue Reader mit eigenem Wertebereich wären neue Oberfläche im fail-closed-Modul |
| AC 3 unberührt | Provider-Austauschbarkeit liefern LiteLLM + `settings.llm_model`; ADR-004 behandelt den Azure-Wechsel als Deployment-Entscheidung |

Abschnitt 3B des Plans entsprechend nachgeschärft, 3A und 3C als entschieden markiert.

---

## 3 — Nutzer

> wäre es sinnvoll T-37 zu erweitern statt ein neues Issue zu machen?

### Claude

Teils. Die Frage zerfällt in zwei Stücke:

- **Gehört zu T-37:** welche Schlüssel über die API schreibbar sind. Steht dort bereits als offener Punkt im Issue-Body.
- **Gehört nicht zu T-37:** die Schlüssel überhaupt einzuführen (Alembic-Seed, Reader mit anderem Wertebereich als `_as_float`, Verdrahtung in `generation.py`).

Ausschlaggebend war die Abhängigkeitsrichtung: T-37 hängt an T-24 und T-07 und ist damit sofort machbar. Mit den LLM-Parametern darin hinge es plötzlich an T-18 — der falsche Preis für ein gespartes Issue.

---

## 4 — Nutzer

> schreib erstmal den Kommentar bei T-37, damit es neu erst nach T-18 umgesetzt werden soll. Das andere Issue erstellen wir besser erst nach der Umsetzung von T-18

### Claude

Rückfrage vor dem Schreiben, weil der Satz zwei Lesarten zuliess:

| Lesart | Entscheid |
|---|---|
| T-37 als Ganzes nach T-18 einplanen | — |
| **Nur die LLM-Parameter nach T-18, T-37 bleibt unabhängig** | **gewählt** |

[Kommentar an #44](https://github.com/tsorer/LearnFlow/issues/44#issuecomment-5306722755) gepostet: Whitelist mit Wertebereich je Schlüssel, LLM-Parameter ausdrücklich nicht Teil von T-37, eigenes Issue nach T-18. Plan-Datei nachgezogen.

---

## 5 — Nutzer

> ja, die Plan-Datei soll in den T-18-Branch

### Claude

Als Schritt 2 in den Ablauf eingetragen (Branch anlegen → Plan-Datei als erster Commit). Bis dahin bleibt sie untracked und übersteht den Branch-Wechsel.

---

## 6 — Nutzer

> erstelle schon mal den T-18-Branch

### Claude

`feat/T-18-llm-generation` von `origin/main` abgezweigt (nicht vom T-17-Branch), Plan-Datei als erster Commit. Hinweis, dass der Branch T-17 noch nicht enthält und nach dem Merge ein Rebase fällig ist.

---

## 7 — Nutzer

> ich hab ein rebase auf T-17 gemacht. Ist zwar immer noch nicht im main, aber du kannst mit der Umsetzung beginnen. Oder spricht was dagegen?

### Claude

Nichts Grundsätzliches — mit zwei Vorbehalten: der PR enthält bis zum T-17-Merge dessen Commit, und bei Review-Änderungen an den vier Nahtstellen wird neu rebased.

**Beim Patchen fiel auf, dass der T-17-Stand sich bewegt hatte** — zwei Plan-Annahmen waren hinfällig:

| Annahme im Plan | Realität nach dem Rebase |
|---|---|
| Spec-Änderung ist rein beschreibend | `suppression_reason` ist ein geschlossenes **Enum** → Schema-Änderung, `schema.d.ts` und `MessageBubble.tsx` müssen in denselben PR |
| Ein Ausgang pro Zweig | Neuer Pfad `configuration_error`, alle Ausgänge laufen über `_persist_and_respond` → zwei neue Parameter |

Umgesetzt: `openapi.yaml` (503-Text, Enum), `app/services/generation.py` (Grounding-Prompt-Kontrakt mit `[n]`-Referenzformat und Sentinel `WEISS_NICHT`, LiteLLM-Aufruf nach dem Muster von `embedding.py`), `query.py` (Generierung nur hinter beiden Gates, 503-Trennung, `llm_calls`), `tests/test_generation.py` (17 Tests), `test_query.py` (6 neue Tests), ADR-007 (Präzisierung T-18) und ADR-008 (offener Punkt 2 erledigt, Zwischenstand als Punkt 4).

---

## 8 — Nutzer

> mach eine kritische Bewertung von diesen Findings: […sieben Findings aus einem externen Review…]

### Claude

Findings im Code gegengeprüft, statt sie zu übernehmen. Ergebnis der Prüfung floss direkt in die nächste Runde ein (siehe 9). Kern: vier waren real, drei nicht bzw. bereits anderweitig erfasst.

---

## 9 — Nutzer

> ja, mach das — abgeschnittene Antwort unterdrücken

### Claude

Vier Befunde umgesetzt — die zwei benannten Frontend-Bugs, die Truncation und zusätzlich das unerreichbare Suppression-Badge, das im selben Codeblock lag:

| Befund | Fix |
|---|---|
| `finish_reason` ignoriert | Am Token-Limit abgeschnittene Antwort wird ganz zurückgehalten, eigener Grund `generation_truncated` mit eigenem Meldungstext. Fehlendes Feld gilt *nicht* als abgeschnitten |
| Composite-Block an festen Indizes (`i === 2`) | Auf Stage-IDs verankert — rendert bei zwei wie bei vier Stufen |
| Citation-Badge gegen 0.0 eingefärbt | Neutral, beschriftet als offen bis T-19 |
| Suppression-Badge in `{m.confidence && …}` | Herausgezogen, damit `configuration_error` sichtbar wird |

Nicht übernommen: Gate über die Top-`n` (dokumentierter ADR-007-Entscheid, Kalibrierungsfrage), fehlende Prüfung `context_top_n <= retrieval_top_k` (Folge-Issue, Wirkung ≤ 0.067 am Score), Rate-Limit (bereits #79/T-45).

---

## 10 — Nutzer

> T-17 ist im main und ich hab ein rebase gemacht. Prüfe nochmal ob der pr erstellt werden kann

### Claude

Festgestellt, dass der Rebase die beiden Commits zu einem verschmolzen hatte — Inhalt vollständig, per Inhaltsprüfung bestätigt. Diff gegen den gemergten T-17 stimmig, keine verwaisten Referenzen auf `generation_not_implemented`, generierte Typen deckungsgleich mit dem Enum.

Docker-Daemon war aus → Docker Desktop gestartet, Alembic auf `0012 (head)`. QA: Backend `ruff`/`mypy`/223 Tests, Frontend Lint/tsc/49 Tests, E2E 21 Tests — alle grün. PR-Text vorbereitet.

---

## 11 — Nutzer

> mach den manuellen Durchlauf gegen den echten Provider

### Claude

Vier Fälle gegen OpenAI Direct, Korpus `SKOS-Richtlinien.pdf` (200 Chunks, Area `default`), als Admin:

| Fall | Ergebnis |
|---|---|
| In-Corpus (GBL-01 aus dem Gold-Dataset) | `suppressed: false`, Score 0.7834, Antwort mit Beleg `[1]`, 5 Citations — deckt sich mit der `reference_answer` |
| Out-of-Corpus, Retrieval täuscht sich (ELG) | Beide Gates passieren (Score 0.6614), das Modell verweigert → `generation_refused` |
| Off-Domain (Dieselmotor) | `retrieval_gate`, Top-Score 0.2867, `llm_calls: []` — kein Provider-Aufruf |
| Provider-Ausfall (ungültiger Key) | `AuthenticationError` wird durchgereicht, Meldung bleibt im Log |

Der zweite Fall ist der aussagekräftige: gefangen hat es erst der Grounding-Prompt — die Defense-in-Depth aus ADR-008. Der Ausfall wurde auf Service-Ebene im Container geprüft statt über `.env`, um den laufenden Stack und die Secrets nicht anzufassen.

---

## 12 — Nutzer

> mach den push und erstelle den PR

### Claude

Gepusht, [PR #84](https://github.com/tsorer/LearnFlow/pull/84) erstellt (Base `main`, Titel mit Branchnamen präfixt). CI grün: `backend` 1m45s, `frontend` 22s, `e2e` 1m42s.

---

## 13 — Nutzer

> mach eine Bewertung der Vor- und Nachteile für die beiden angegebenen Punkte in PR-Review https://github.com/tsorer/LearnFlow/pull/84

### Claude

Beide Punkte gegen den Branch-Stand verifiziert, beide faktisch korrekt.

**Punkt 1 — `?? 0.55` im Retrieval-Badge.** Ergänzung zur Review-Sicht: die Zahl im Frontend ist strukturell ein Rateversuch, nicht nur ein falscher Wert — die echte Schwelle ist per Design kalibrierbar. Optionen: Fallback korrigieren (gleiche Fehlerklasse, nur seltener) · für Nicht-Admins nicht einfärben (**empfohlen**, konsistent mit der Citation-Entscheidung im selben PR) · Schwellen für alle ausliefern (baut etwas, das T-27 wieder ersetzt).

**Punkt 2 — Latenzbudget.** Teilweiser Widerspruch: ein Timeout ist kein Latenzbudget. Auf 10 s geklemmt würde er die langsamsten legitimen Antworten in 503er verwandeln — bessere Messgrösse, schlechteres Produkt. Was der Review richtig trifft, ist der **Retry**: er verdoppelt genau den langsamen Fall, und Provider-Degradation ist über Requests korreliert, verschiebt das Perzentil also als Block. Optionen: nur kommentieren · **Retry streichen (empfohlen)** · Timeout senken (ungemessen wie vorher, nur kleiner) · Deadline über die Pipeline (gehört zu T-22, wo gemessen wird).

---

## 14 — Nutzer

> mach beide Empfehlungen, B und B und wechsle den Branch

### Claude

Zurück auf `feat/T-18-llm-generation` (das Arbeitsverzeichnis stand zwischenzeitlich auf `Frank`).

- **Frontend:** `minRet` ist `null` ohne `params_used`, `retFail` bleibt dann `false` — eingefärbt wird nur gegen die echte Schwelle.
- **Backend:** `MAX_RETRIES = 0`, begründet aus dem Unterschied Worker/Request statt aus LiteLLMs Default. Timeout bleibt bewusst bei 30 s, mit der Notiz, dass ein Timeout eine Obergrenze ist und kein Budget; die Zahl ist T-22 zugewiesen.
- Dazu eine Testzeile, die `num_retries == 0` festhält, und der veraltete Kommentar in `MessageBubble.tsx:21` (T-19/T-25 statt T-18) — eine Inkonsistenz, die dieser PR selbst hinterlassen hatte.

QA erneut grün. Commit `b394ace`, Push beim Nutzer.

---

## 15 — Nutzer

> nein, schon erledigt. Exportier wieder den Chatverlauf nach Frank/Prompts

### Claude

Git-Stand geprüft: PR #84 gemerged, `main` bei `7425ee8`, beide Nachbesserungen enthalten. Verlauf als diese Datei abgelegt.

---

## Ergebnis

- **Drei Commits** auf `feat/T-18-llm-generation` (Plan · Umsetzung inkl. Review-Runde · Nachgang zum PR-Review), gemerged als `7425ee8`.
- **Alle drei Akzeptanzkriterien** aus Issue #25 erfüllt und im laufenden System gegen den echten Provider durchgespielt.
- **Kernbeleg:** `test_no_llm_call_below_the_retrieval_gate` macht aus der ADR-007-Behauptung einen Test — der Off-Domain-Durchlauf bestätigt sie im laufenden System (`llm_calls: []`).
- **Entschieden und dokumentiert:** Referenzformat `[n] = Citation.index` und Verweigerungs-Sentinel `WEISS_NICHT` (ADR-007-Präzisierung) — damit ist der offene Punkt 2 aus ADR-008 erledigt.

### Bewusste Abgrenzungen

| Nicht umgesetzt | Grund |
|---|---|
| Citation-Coverage / Referenz-Validierung | ADR-008 Stufe 2 → #26 (T-19), folgt unmittelbar |
| Komposit-Konfidenz-Score | #30 (T-23); `confidence.score` bleibt bis dahin die Retrieval-Konfidenz allein |
| Self-Check | ADR-008 Stufe 3 → #32 (T-25) |
| LLM-Parameter in der `config`-Tabelle | Kein Fail-closed-Rückfall, kein Nutzen vor T-37; eigenes Issue nach T-18, Abgrenzung als Kommentar an #44 festgehalten |
| Gate über alle Kandidaten statt Top-`n` | Dokumentierter ADR-007-Entscheid, Kalibrierungsfrage für den Eval-Spike |
| Rate-Limit auf `/api/query` | Bereits als #79 (T-45) offen — ändert mit diesem PR aber seinen Charakter: von Hygiene zu Kostenkontrolle |

### Bekannte offene Punkte

- **Fail-closed-Lücke bis T-19/T-25:** eine ausgelieferte Antwort ruht auf zwei Gates plus Grounding-Prompt. Bewusst entschieden, in ADR-008 als Zwischenstand dokumentiert.
- **Keine Frontend-Tests** für die drei Rendering-Fixes; eine `MessageBubble`-Testdatei existiert nicht.
- **`MAX_ANSWER_TOKENS = 800`** entscheidet inzwischen über Unterdrückungen, steht aber im Code — als Kalibrierkandidat für den Eval-Spike noch nicht in ADR-007 vermerkt.
- **Prompt-Regel 3 vs. 4:** eine Ausgabe, die mit dem Sentinel beginnt und danach teilweise antwortet, wird per `startswith` vollständig verworfen. Fail-closed, aber welche Regel gewinnt, steht nirgends.
- **Chunk-Text kann eine Sektions-Überschrift fälschen** (`\n\n[9] (echt.pdf)`); der eigentliche Fang ist Stufe 2 — gehört in #26 notiert.
- **Eval-Gate bleibt unmessbar** bis #35 (T-28). Dass die Pipeline jetzt bis zur Auslieferung geschlossen ist, macht das Ticket dringend.
