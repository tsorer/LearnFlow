# L2 · Der Ewigkeits-Check LearnFlow

> Modul 8 · Tag 1 · Deliverable 2 — baut auf [L1_Datenfluss-Karte.md](L1_Datenfluss-Karte.md) auf.
> Frage: Wo ist der Punkt ohne Rückkehr?

## Das Ergebnis in einem Satz

**LearnFlow macht selbst kein Training — belegbar. Ob der Anbieter eines macht, weiss
niemand von uns, und deshalb sind die vier externen Datenarten 🔴 unbestätigt.**
Im ganzen Backend gibt es genau vier LLM-Aufrufe und alle vier sind reine Inferenz;
kein Fine-Tuning, kein persistenter Modell-Kontext auf unserer Seite. Der Punkt ohne
Rückkehr liegt ausserhalb unseres Codes — und genau dort haben wir nichts geprüft.

> ### ⚠️ Korrektur vom 2026-09-09
>
> Die erste Fassung dieses Dokuments stand auf „**0 × 🔴**". Das war fail-open und
> widersprach dem eigenen Text: Prüf-Frage 2 („trainiert der Anbieter auf Eingaben?")
> ist als **offen** markiert, und aus einer offenen Ewigkeitsfrage darf keine grüne
> Bilanz werden. `Docs/04_ADR-008_Konfidenz-Pipeline.md` schreibt für dieses Projekt
> fail-closed vor — eine nicht bestätigte Zusicherung ist wie eine verletzte zu
> behandeln. Die vier externen Datenarten stehen deshalb jetzt auf **🔴 unbestätigt**:
> nicht, weil bekannt wäre, dass trainiert wird, sondern weil niemand weiss, dass nicht.
>
> Unabhängig vom Training gilt ohnehin: **der Versand ist irreversibel.** Es gibt
> keinen Löschknopf beim Anbieter. „Kein Training" beantwortet nur, ob die Daten in
> *Gewichte* fliessen — nicht, ob sie weg sind.

Die vollständige externe Oberfläche, mit Beleg:

| Aufruf | Was geht raus | Beleg |
|---|---|---|
| `litellm.aembedding` | Dokument-Chunks (Worker) **und** jede Nutzerfrage (Retrieval) | `src/backend/app/services/embedding.py:40` |
| `litellm.acompletion` | Frage + Top-N-Chunk-Volltext | `src/backend/app/services/generation.py:157` |
| `litellm.acompletion` | Frage + Antwort + dieselben Chunks nochmals | `src/backend/app/services/self_check.py:156` |
| `litellm.acompletion` | Chunk-Volltext (Quiz-Generierung) | `src/backend/app/services/quiz.py:147` |

`grep -rni "fine.tune\|finetun\|training" src/backend/app src/backend/worker src/frontend/src`
→ **null Treffer.** Das ist die Beweislage für „kein 🔴 im eigenen Code".

---

## Die Markierung

| # | Datenart | Kat. | Begründung |
|---|---|---|---|
| 1 | Konto (E-Mail, Hash, Rolle) | 🟢 | `users`-Zeile, technisch löschbar. `uploaded_by`/`changed_by` sind `ON DELETE SET NULL` — die Löschung reisst nichts mit. |
| 2 | Passwort Klartext | 🟢 | existiert nur für die Dauer eines Requests, wird nie geschrieben |
| 3 | JWT | 🟢 | Browser-Memory, max. 1 h, kein localStorage (`App.tsx:13`) |
| 4 | Dokument-Rohbytes | 🟢 | `documents.content`, `DELETE /documents/{id}` existiert |
| 5 | **Dokument-Text als Chunks** | 🟢 + 🔴? | lokal löschbar (Kaskade). Aber: **jeder Chunk war schon beim Embedding-Anbieter**, und beim Antworten geht er als Prompt-Kontext erneut raus. Die lokale Löschung holt nichts zurück. |
| 6 | Embeddings | 🟢 | Vektor liegt lokal; extern war der *Text*, der ihn erzeugt hat (→ 5) |
| 7 | **Fragen der Lernenden** | 🟢 + 🔴? | `answers.question` ist löschbar — aber jede Frage war 2–3× beim Anbieter: Embedding, Antwort-Prompt, ggf. Self-Check |
| 8 | Antworten + Scores | 🟢 + 🔴? | die Antwort geht im Self-Check-Prompt ein zweites Mal raus |
| 9 | Query-Session | 🟢 | rein lokal, verlässt das System nie |
| 10 | Feedback + Freitext | 🟢 | rein lokal. Freitext ≤ 500 Zeichen geht an **keinen** LLM-Aufruf — bewusst nicht in die Pipeline gehängt |
| 11 | Quiz + `source_excerpt` | 🟢 + 🔴? | Chunk-Text war im Generierungs-Prompt |
| 12 | Config + `changed_by` | 🟢 | lokal |
| 13 | Job-Payload | 🟢 | nur `document_id` |
| 14 | `pgqueuer_log` + Traceback | 🟢 | lokal, aber ohne TTL — löschbar heisst nicht: wird gelöscht |
| 15 | App-Logs (`user_id`, Exceptions) | 🟢 | Docker json-file, löschbar. Ohne Rotation wächst es unbegrenzt |
| 16 | nginx-Log (**Client-IP**) | 🟢 | dito |
| 17 | `documents.error_message` | 🟢 | wird vom nächsten erfolgreichen Lauf überschrieben |
| 18 | Secrets | 🟢 | rotierbar — das ist bei Secrets die relevante Form von „löschbar" |
| 19 | Rate-Limit-Zähler | 🟢 | Prozessspeicher |

**Bilanz: 4 Datenarten 🔴 unbestätigt (5, 7, 8, 11), alles Übrige 🟢.**

`🔴?` heisst: extern *und* die Ewigkeitsfrage ist ungeprüft. Es wird erst zu einem
sauberen 🟠, wenn jemand Prüf-Frage 2 und 4 beantwortet hat — und selbst dann bleibt der
Versand unwiderruflich.

Wichtige Lesehilfe zu den vielen 🟢: *löschbar* ist eine Eigenschaft des Datenmodells,
nicht eine Aussage über die Praxis. Aus L1: es gibt keine einzige Frist, und der einzige
tatsächlich implementierte Löschpfad ist `DELETE /documents/{id}`. Alle 🟢 hier sind
„könnte gelöscht werden", keines ist „wird gelöscht".

---

## Die vier Prüf-Fragen

**☑ 1 · Nutzt das Projekt Fine-Tuning oder Training auf eigenen Daten?**
**Nein — belegbar.** Vier LiteLLM-Aufrufe, alle Inferenz (Tabelle oben). Keine
Trainings-Bibliothek, kein Fine-Tuning-Endpoint, kein Datenexport für Training.

**☐ 2 · Sendet ihr Daten an einen Anbieter, der auf Eingaben trainiert?**
**Im Code nicht entscheidbar — offen, und das ist die Antwort, nicht eine Vorstufe
davon.** Der Code sagt nur *wohin*: `OPENAI_API_KEY` gegen `api.openai.com`, weil
`LITELLM_BASE_URL` im MVP leer ist (`src/.env.example`, `app/config.py:47`).

Der Kenntnisstand, auf den man versucht ist sich zu stützen: OpenAI gibt für die **API**
(im Unterschied zu ChatGPT-Consumer) an, Eingaben nicht standardmässig zum Modelltraining
zu verwenden, bei befristeter Aufbewahrung fürs Abuse-Monitoring. **Darauf darf sich
dieses Dokument nicht stützen**, aus drei Gründen:

1. **Es gibt einen Opt-in.** OpenAI hat Programme angeboten, bei denen eine Organisation
   API-Daten fürs Training freigeben kann (u. a. gegen Gratis-Tokens). Wer das je
   angeklickt hat, hat den Default umgedreht. In *unserem* Konto hat niemand nachgesehen.
2. **Eine Löschzusage ist kein Naturgesetz.** Im Verfahren *NYT v. OpenAI* wurde OpenAI
   2025 gerichtlich verpflichtet, Logs aufzubewahren, die sonst gelöscht worden wären;
   Umfang und Fortbestand wurden danach bestritten und angepasst. Der heutige Stand ist
   hier nicht bekannt. Die Lehre bleibt: eine Aufbewahrungsfrist des Anbieters kann von
   aussen ausgehebelt werden.
3. **Es gibt keine Zusage an uns.** Kein AVV, kein Enterprise-Vertrag, keine Zeile in
   `Ops/07_Pilotstart-Checkliste.md`. Wir stützen uns auf eine Webseite, nicht auf eine
   vertragliche Zusicherung — und Webseiten ändern sich ohne Migrationsskript.

**Und selbst ein bestätigtes „kein Training" beantwortet die falsche Frage.** Es sagt,
ob die Daten in *Gewichte* fliessen. Es sagt nicht, ob sie weg sind: einen Löschknopf
beim Anbieter haben wir in keinem Fall.

**☑ 3 · Landen Nutzer-Daten in einem dauerhaften Vektor-Store, der Teil des
Modell-Kontexts wird?**
**Teilweise — und die interessante Hälfte ist ein Nein.**
- Dokument-Chunks: ja, `chunks.embedding` ist dauerhaft und wird über Retrieval zum
  Prompt-Kontext jeder Antwort. Aber es ist **unser** Store, in **unserer** Postgres,
  mit Kaskaden-Löschung. Der Store selbst ist 🟢; 🔴? ist der Weg dorthin — jeder
  Chunk war beim Embedding-Anbieter, bevor der Vektor bei uns lag.
- Nutzerfragen: **nein.** `answers.question` wird geschrieben, aber nie eingebettet
  und nie indexiert. Es gibt keinen Pfad, auf dem eine Frage in den Korpus gerät und
  damit in künftige Antworten anderer Nutzer einfliesst. Das ist die Grenze, die
  hier schon steht.

**☐ 4 · Gibt es ein „opt out of training" beim Anbieter — ist es aktiv?**
**Nicht geprüft, und nirgends vorgesehen.** `Ops/07_Pilotstart-Checkliste.md` hat unter
Punkt 2 zwei Zeilen zum Provider — 2.1 „auf Azure OpenAI EU umgestellt", 2.2 „Embedding
ebenfalls" — und **keine Zeile zu Training-Opt-out, Aufbewahrungsfrist oder
Auftragsverarbeitungsvertrag**. Der Checklisten-Punkt sichert die Datenresidenz und
hört genau dort auf, wo die Ewigkeitsfrage anfängt.

### Wie 🔴? zu 🟠 wird — die offene Aufgabe

Nichts davon ist im Repo erledigbar; alle vier Punkte brauchen jemanden mit
Konto- und Vertragszugriff:

- [ ] Im OpenAI-Org-Dashboard nachsehen, ob Daten-Sharing / Training auf API-Eingaben
      für diese Organisation aktiv ist — und den Befund **mit Datum** festhalten,
      nicht nur abstellen.
- [ ] Die geltende Aufbewahrungsdauer für API-Daten schriftlich haben; klären, ob
      Zero Data Retention für dieses Konto verfügbar ist.
- [ ] AVV / Data Processing Addendum abschliessen — der Unterschied zwischen einer
      Webseite und einer Zusage an uns.
- [ ] Dieselben drei Punkte für **Azure OpenAI EU** beantworten, bevor umgestellt wird.
      EU-Datenresidenz ist eine Aussage über den *Ort*, nicht über die *Verwendung* —
      Punkt 2.1 der Pilotstart-Checkliste löst die Ewigkeitsfrage nicht mit.
- [ ] Diese vier Zeilen als Punkte in `Ops/07_Pilotstart-Checkliste.md` aufnehmen,
      damit der Befund nicht in einem Lab-Dokument endet.

Bis alle Häkchen gesetzt sind, bleibt die Markierung 🔴 unbestätigt. Das ist keine
Behauptung über OpenAI — es ist die Weigerung, eine ungeprüfte Zusage als Grenze zu
zählen.

---

## Zwei Funde, die aus dem Doc-Abgleich kommen

### A · Die Query-Logs sind nicht pseudonymisiert — die Spec sagt, sie seien es

`Docs/03_QualityAttributes.md:12` (Security-NFA):

> „Feedback und Query-Logs werden **pseudonymisiert** gespeichert"

Für das Feedback stimmt das und ist im Code sauber durchgezogen (`feedback` ohne
`user_id`). Für die Query-Logs stimmt es nicht: `answers.question` hängt über
`answers.session_id → query_sessions.user_id` direkt an der Person
(`tables.py:151`, `:160`). Kein Hash, kein Pseudonym, kein Aggregat — die
Klartext-Frage und die User-UUID sind einen Join voneinander entfernt.

Dieselbe Formulierung steht in `Docs/03_QualityAttributes.md:79`,
`Docs/06_Architecture-Draft.md:18` und `Docs/05_C4-C2_Container.md:62`. Vier Stellen
behaupten eine Eigenschaft, die eine der beiden genannten Tabellen nicht hat.
→ **Entweder die Spec korrigieren oder das Datenmodell.** Das ist L3-Material.

### B · Die fehlenden Fristen sind ein bewusster, datierter Aufschub

Anders als es in L1 aussieht, ist das kein Vergessen —
`Docs/02_Requirements.md:278` und `Docs/06_Architecture-Draft.md:18`:

> „DSGVO-Löschantrag-Workflow und Aufbewahrungsfristen → Post-MVP
> (Entscheid 2026-06-04; Pilot < 30 interne Nutzer, kein produktiver Betrieb)"

Der Entscheid trägt sich, solange die Prämisse trägt. Beide Hälften davon —
„< 30 interne Nutzer" und „kein produktiver Betrieb" — sind genau die Bedingungen,
die der Pilotstart aufhebt.

---

## Was das Ausmass vergrössert — die Auslöser

Die Kategorie ist schon 🔴?; diese drei Ereignisse ändern nicht *ob*, sondern *wie viel*
und *wie sicher*. Jedes einzelne macht aus einem ungeprüften Risiko einen konkreten
Schaden:

1. **Das erste echte interne Dokument geht über OpenAI Direct raus.** Dann ist der
   Volltext des Unternehmenskorpus auf US-Servern, unwiderruflich, und zwar chunkweise
   *und* nochmals in jedem Antwort-Prompt. ADR-004 und ADR-005 nennen das beide
   ausdrücklich als Compliance-Verstoss; die Mitigation ist eine Checklisten-Zeile.
   Beide ADRs schlagen zusätzlich einen **Guard im Code** vor, der einen Nicht-EU-Provider
   bei „intern/produktiv" markiertem Korpus ablehnt — dieser Guard ist nicht gebaut.
   Es gibt heute nichts im Code, was einen Upload eines echten Dokuments verhindert.

2. **Es stellt sich heraus, dass beim Anbieter Training auf Eingaben aktiv ist** — sei
   es durch einen alten Opt-in, sei es durch eine Änderung der Bedingungen (Prüf-Frage
   2/4). Dann ist rückwirkend alles in Gewichten, was je durch die vier Aufrufe ging:
   jeder Chunk, jede Frage, jede Antwort. Rückwirkend ist hier das Wort, das zählt —
   die Prüfung von morgen repariert den Versand von gestern nicht.

3. **Das Feedback wird künftig in die Pipeline gehängt.** Heute geht der Freitext an
   keinen LLM-Aufruf. Der Tag, an dem jemand „lass das Modell die Feedback-Kommentare
   auswerten" umsetzt, macht aus der pseudonymisierten Tabelle einen externen Datenfluss —
   mit den Freitexten, in denen erfahrungsgemäss am ehesten Namen und Fälle stehen.

**Antwort auf die Leitfrage:** Der Punkt ohne Rückkehr ist bereits überschritten — jede
Frage und jeder Chunk, der je durch die vier Aufrufe ging, ist aus unserer Kontrolle
heraus, und ob er in Gewichten gelandet ist, weiss niemand von uns. Was uns heute noch
schützt, ist ausschliesslich der **Inhalt**: im Korpus liegen nur öffentliche Dokumente
(EU AI Act, SKOS-Richtlinien, SAMW-Leitfaden), und die Fragen des Pilotkreises sind
harmlos. Das ist eine Eigenschaft der aktuellen Testdaten, keine Grenze im Code — und
der Tag, an dem sich der Inhalt ändert, steht im Kalender, nicht im Repository.
