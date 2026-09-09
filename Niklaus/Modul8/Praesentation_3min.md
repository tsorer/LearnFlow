# Präsentation · 3 Minuten — LearnFlow, Datenfluss-Audit

> Modul 8 · Tag 1 · Abschluss. Sprechtext, nicht Folientext.
> Zeitbudget: 180 s. Die Klammern sind Regieanweisungen, nicht zum Vorlesen.

---

## Einstieg · 15 s

> LearnFlow ist ein RAG-Assistent für interne Weiterbildung. Vier Container, Postgres
> mit pgvector, LLM über LiteLLM. Wir haben heute jede Datenart im Code gesucht — mit
> Datei-Beleg, nicht aus dem Gedächtnis. Neunzehn sind es geworden.

---

## 1 · Der 🔴-Fluss · 45 s

*(Diese Antwort ist unser interessantester Punkt — Zeit dafür nehmen.)*

> Erste Frage: gibt es bei uns einen Fluss, der nie zurückkommt.
>
> Unsere erste Antwort war: nein. Wir konnten das sogar belegen — im ganzen Backend
> gibt es genau vier LLM-Aufrufe, und alle vier sind reine Inferenz. Kein Fine-Tuning,
> kein Training, `grep` findet nichts.
>
> Diese Antwort war falsch. Nicht faktisch — sie beantwortet die falsche Frage.
> Sie sagt, was **wir** mit den Daten machen. Die Ewigkeitsfrage ist aber, was der
> **Anbieter** damit macht. Und das steht in keinem Repository.
>
> Was wir gefunden haben: niemand bei uns hat je im OpenAI-Konto nachgesehen, ob
> Training auf Eingaben aktiv ist. Es gibt keinen Auftragsverarbeitungsvertrag. In
> unserer Pilotstart-Checkliste stehen zwei Zeilen zum Provider, beide nur zur
> EU-Datenresidenz — also zum **Ort**, nicht zur **Verwendung**.
>
> Unser eigenes ADR-008 schreibt fail-closed vor: eine ungeprüfte Zusicherung wird
> behandelt wie eine verletzte. Also steht in unserem Dokument jetzt nicht 🟢 und nicht
> 🟠, sondern **🔴 unbestätigt**. Nicht weil wir wüssten, dass trainiert wird — sondern
> weil niemand weiss, dass nicht.
>
> Und selbst ein bestätigtes „kein Training" hilft nur halb: einen Löschknopf beim
> Anbieter haben wir in keinem Fall.

---

## 2 · Die Grenze, die wir eingezogen haben · 45 s

*(Auf `L3_Minimieren-und-trennen.md` verweisen, nicht vorlesen.)*

> Zweitens: zwei Grenzen, als Patch ausgearbeitet.
>
> Die erste ist eine Frist auf den Fragen. Nach 30 Tagen wird die Verbindung zur
> Person gekappt — `user_id` auf NULL. Nach 90 Tagen ist der Fragetext selbst weg.
>
> Der interessante Teil ist, wie: **UPDATE, nicht DELETE.** Wir wollten zuerst alte
> Zeilen löschen. Dann haben wir gesehen, dass das Feedback per Fremdschlüssel
> kaskadiert — ein DELETE hätte die komplette Feedback-Historie unseres
> Bereichsverantwortlichen mitgenommen. Lautlos, weil eine Kaskade nichts protokolliert.
> Das Nullen der Spalte behält jede Bewertung und entfernt nur den Freitext.
>
> Die zweite Grenze ist banal und deshalb typisch: unsere Logs hatten **keine
> Rotation**. Docker-Default, unbegrenzt. Drin stehen User-IDs, Client-IPs und
> Provider-Tracebacks. Niemand hat je entschieden, das für immer aufzubewahren — es war
> der Default. Jetzt: 3 × 10 MB pro Container.

---

## 3 · Der gefährlichste Fund · 60 s

*(Wenn ein Bildschirm da ist: die vier Zeilen SQL aus `L4_Threat-Model.md` zeigen.)*

> Drittens, und das ist der Fund, den wir vorher nicht auf dem Schirm hatten.
>
> Jede Frage, die je jemand gestellt hat, liegt im Klartext in der Datenbank. Über die
> Session hängt sie an einer namentlich bekannten Person. Unbegrenzt lange.
>
> Und: **kein einziger Endpoint liest diese Spalte je zurück.** Wir schreiben sie seit
> Tag eins und haben sie nie verwendet.
>
> Dazu kommt der Teil, der wirklich unangenehm ist. An vier Stellen in unserer
> Architekturdokumentation steht: „Feedback und Query-Logs werden pseudonymisiert
> gespeichert." Für das Feedback stimmt das, sauber durchgezogen bis in die API. Für
> die Query-Logs stimmt es nicht. Klartext-Frage und User-ID sind einen Join
> voneinander entfernt. Vier Dokumente behaupten eine Eigenschaft, die das Datenmodell
> nicht hat.
>
> Unser Threat Model dazu, in einem Satz: Der Angreifer ist kein Krimineller, sondern
> ein Insider mit Host-Zugriff. Er braucht keinen Exploit, nur ein `docker exec` und
> einen Zweifach-Join. Rollenrechte, Rate-Limiting, unsere ganze Konfidenz-Pipeline —
> nichts davon liegt auf diesem Weg, die schützen alle die API. Und es fällt nicht auf:
> es gibt kein Audit-Log, und die Anwendung loggt nur Fehler. Eine erfolgreiche Frage
> hinterlässt gar keine Zeile.
>
> Seine Beute wäre ein Profil darüber, was welche Kollegin wann nicht gewusst hat.
> Über ein Jahr hinweg.

---

## Schluss · 15 s

> Zwei Sätze zum Mitnehmen.
>
> Erstens: Die gefährlichste Datenart in unserem System war die, die niemand braucht —
> gesammelt, weil eine Spalte einmal angelegt wurde, nicht weil jemand sie wollte.
>
> Zweitens: Was wir vorher für die Grenze gehalten haben — EU-Datenresidenz — ist eine
> Aussage über den Ort. Nicht über die Verwendung, und nicht über die Dauer.

---

# Regie

| Abschnitt | Zeit | Kumuliert | Was zeigen |
|---|---|---|---|
| Einstieg | 15 s | 0:15 | — |
| 1 · 🔴-Fluss | 45 s | 1:00 | Die 4-Zeilen-Tabelle der LLM-Aufrufe aus L2 |
| 2 · Grenze | 45 s | 1:45 | — (erzählen, nicht zeigen) |
| 3 · Fund | 60 s | 2:45 | Das SQL aus L4 |
| Schluss | 15 s | 3:00 | — |

**Wenn die Zeit knapp wird:** Punkt 2 auf die Frist kürzen, Log-Rotation weglassen.
Punkt 3 nie kürzen — das ist der Fund.

**Wenn Zeit übrig ist:** die Zahl nachschieben, dass es im ganzen Backend genau zwei
`DELETE FROM` gibt — und keines davon räumt personenbezogene Daten weg.

---

# Wenn nachgefragt wird

**„Ihr habt euer Ergebnis mitten im Lab umgedreht — was war der Auslöser?"**
Die Frage, ob wir uns sicher sind, dass OpenAI nicht auf Prompts trainiert. Wir waren
es nicht. Wir hatten eine Anbieter-Aussage als Befund notiert. Ein Befund ist es erst,
wenn jemand nachgesehen hat.

**„Warum löscht ihr die Fragen nicht einfach ganz?"**
Wäre die stärkere Grenze, und wir haben sie bewusst nicht gewählt: ADR-009 kalibriert
die Konfidenz-Schwellen gegen echte Fragen, dafür braucht es ein Fenster. 90 Tage sind
der Preis. Fällt die Eval-Begründung weg, fällt auch der Grund für die Spalte.

**„Löst Azure OpenAI EU euer Problem nicht?"**
Nur die Hälfte. Datenresidenz ist der Ort. Ob dort auf Eingaben trainiert wird und wie
lange aufbewahrt wird, ist eine zweite Frage — dieselbe, die wir für OpenAI Direct
nicht beantworten können. Beide gehören in die Pilotstart-Checkliste, und dort stehen
sie heute nicht.

**„Ist das nicht bei jeder Datenbank so mit dem Insider?"**
Ja. Was unseren Fall schlechter macht, sind drei Dinge zusammen: die Daten sind
unbegrenzt aufbewahrt, sie sind per Design personenbezogen, und niemand liest sie —
also fällt ein Missbrauch nicht einmal auf.

**„Habt ihr die Patches eingebaut?"**
Nein, bewusst nicht. Unser Prozess verlangt Issue, Feature-Branch, Tests und grüne CI.
Die Diffs sind vollständig und anwendbar; sie gehen als Issue ins Backlog.
