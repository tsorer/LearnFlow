# Chatverlauf — Review PR #94 (Rückfrage vor Ersetzung eines gleichnamigen Dokuments, #92)

**Datum:** 2026-09-08
**Branch (Arbeitsverzeichnis):** zu Beginn `feat/T-23-T-25-T-26-konfidenz-pipeline`, am Ende `main` — vom Nutzer nebenbei gewechselt, von Claude nicht angefasst. Der Review-Gegenstand wurde ausschliesslich gelesen (`gh pr view/diff/checks`, `git show pr-94:<pfad>`, `git grep pr-94`), nie ausgecheckt. Einzige Repo-Änderung: `git fetch origin pull/94/head:pr-94` legte den lokalen Ref `pr-94` an.
**Gegenstand:** [PR #94](https://github.com/tsorer/LearnFlow/pull/94) „feat/92-upload-replace-confirmation: Rückfrage vor Ersetzung eines gleichnamigen Dokuments" (Issue [#92](https://github.com/tsorer/LearnFlow/issues/92), Folge von T-15/PR #87, US-04), Autor `luenlestra`, 7 Dateien, +261/−28
**Ergebnis:** Review als [Kommentar](https://github.com/tsorer/LearnFlow/pull/94#issuecomment-5424721140) gepostet; Verdikt „kann so gemergt werden", fünf Befunde, keiner blockierend.

> Rekonstruktion des Verlaufs. Nutzer-Prompts wörtlich, Claude-Antworten als Zusammenfassung der Aussagen und durchgeführten Aktionen.

---

## 1 — Nutzer

> mach ein Review von https://github.com/tsorer/LearnFlow/pull/94

### Claude

**Vorgehen:** PR-Metadaten und Diff via `gh`; Issue #92 gelesen und die vier AK gegen die Umsetzung gestellt. PR-Branch als Ref geholt und über `git show pr-94:<pfad>` gelesen — kein Checkout, weil das Arbeitsverzeichnis dem Nutzer gehört. Gegengeprüft gegen den vollen `app/routers/documents.py` (nicht nur den Diff-Ausschnitt), `app/models/tables.py` (FK-Definition von `uploaded_by`), `openapi.yaml` (Umgebung der neuen Property), `tests/test_openapi_spec.py`, den generierten `schema.d.ts`, `src/frontend/src/types.ts`, `src/frontend/src/index.css` und das Test-Setup in `upload.test.tsx`. CI-Status und Review-Stand über `gh pr checks` / `gh pr view --json reviews,mergeable`.

**Nicht ausgeführt:** `make qa`, pytest und e2e liefen nicht — der Docker-Daemon war nicht gestartet (`npipe:////./pipe/dockerDesktopLinuxEngine` nicht erreichbar). Grundlage ist der grüne CI-Run (`backend` · `frontend` · `e2e`), was im Review ausdrücklich als Einschränkung benannt wurde.

**Verdikt: kann so gemergt werden.** Alle vier AK aus #92 erfüllt, Spec-First (ADR-010) eingehalten, `schema.d.ts` regeneriert mitcommittet, `mergeable: MERGEABLE`, noch kein Review vorhanden.

**Fünf Befunde, keiner blockierend:**

1. **Modal ohne Escape und ohne Fokus-Führung** (`Upload.tsx:237`) — als einziger Punkt „sollte vor dem Merge rein". `role="dialog" aria-modal="true"` ist gesetzt, aber der Fokus bleibt hinter dem Overlay, Tab läuft durch die Seite darunter, Escape tut nichts. Der Dialog blockiert die komplette Batch-Schleife (das Promise löst nur per Button-Klick auf), wer mit Tastatur arbeitet, kommt praktisch nur blind wieder raus. Verschärfend: es ist der erste Modal im Frontend (`git grep 'role="dialog"'` findet nur diese Stelle), der Pattern wird kopiert.
2. **`isOther` ist false bei unbekanntem Hochladenden** (`Upload.tsx:64`) — `!!existing.uploaded_by && existing.uploaded_by !== user.email` lässt den Warnhinweis bei gelöschtem Konto (`uploaded_by === null`) weg; das Dokument liest sich dann wie das eigene. In einem Projekt, das sich sonst fail-closed verhält (ADR-008), sollte „unbekannt" eher warnen. `existing.uploaded_by !== user.email` allein genügte.
3. **Stehengebliebene Erfolgsmeldung** (`Upload.tsx:150`) — `setNotice("")` steht nach dem `if (!accepted.length) return;`. Wird ein ganzer Batch von `validateFile` abgelehnt, bleibt das grüne „… ersetzt das bestehende Dokument" der vorherigen Runde neben der neuen roten Fehlermeldung stehen.
4. **Offenes Promise beim Unmount mit geöffnetem Dialog** (`Upload.tsx:56`) — `resolveConfirm.current` wird nie gerufen, `handleFiles` hängt dauerhaft, `uploading` bleibt true. Heute kaum erreichbar, aber Befund 1 ändert daran nichts.
5. **Nits** — „Ersetzung abgebrochen" landet in der roten Fehlerbox, obwohl ein bewusster Abbruch kein Fehler ist (Geschmacksfrage, begründet) · zwei Muster für dieselbe Auflösung im Backend: `outerjoin` in `list_documents`, zweiter Roundtrip per `db.scalar` in `get_document`.

**Explizit gegengeprüft und für korrekt befunden** (im Kommentar als eigener Abschnitt, damit sichtbar ist, was nicht bloss ungeprüft durchging): beide Upload-Pfade setzen `uploaded_by = user.id` — `_replace` tut es ausdrücklich, also ist `user.email` ohne Nachladen richtig · `outerjoin` statt Inner-Join ist nötig, `users.id` ist PK, also keine Zeilenvervielfachung, und `defer(Document.content)` greift auch beim Tupel-Select · `uploaded_by` optional statt `required` in der Spec deckt sich mit `error_message`, ist also Hausstil · `unwrap(result)` wird im Objektliteral vor `result.response.status` ausgewertet, ein Fehlerstatus wirft also, statt als `replaced: false` durchzurutschen · einziger Aufrufer von `uploadDocument` mitgezogen, `Document = DocumentResponse` macht den Test-Helper spec-typisiert · alle verwendeten CSS-Variablen und `button.secondary/.danger` existieren in `index.css` · alle drei Dokument-Endpoints hängen an `require_knowledge_owner`, die neue E-Mail ist für Lernende nicht sichtbar.

**Ausdrücklich festgehalten:** Die DoD von #92 verlangt „Review durch eine zweite Person" — diese Analyse ersetzt das nicht.

---

## 2 — Nutzer

> Ja

(auf die Rückfrage „Soll ich das als Kommentar an den PR posten?")

### Claude

Als Issue-Kommentar gepostet: [#94 (comment)](https://github.com/tsorer/LearnFlow/pull/94#issuecomment-5424721140), bewusst als normaler Kommentar und nicht als formales Review — ein „Approve" von Claude würde die DoD-Anforderung „Review durch eine zweite Person" nur verwässern. Der Kommentar enthält dieselben fünf Befunde plus den Abschnitt „Geprüft und in Ordnung" und die Einschränkung, dass pytest/e2e lokal nicht nachgefahren wurden.

---

## 3 — Nutzer

> exportiere den Chatverlauf nach Frank/Prompts

### Claude

Bestehende Exporte in `Frank/Prompts/` als Vorlage gelesen (`2026-08-24_PR-91-Review-T-45.md` als jüngstes Review-Beispiel) und dieses Dokument nach der dort etablierten Konvention erstellt. Kein Branch-Wechsel, kein Commit — beides war nicht verlangt, und der aktive Branch ist `main`.
