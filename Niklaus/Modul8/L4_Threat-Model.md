# L4 · Threat Model LearnFlow — eine Seite

> Modul 8 · Tag 1 · Deliverable 4 — ein Angreifer, ein Weg, eine Grenze.
> Gegenstand: der gefährlichste Datenfluss aus [L1](L1_Datenfluss-Karte.md).

## Der Datenfluss

**Das Fragenarchiv: `answers.question` → `query_sessions.user_id` → `users.email`.**

Warum dieser und nicht der Korpus: **die Dokumente existieren anderswo.** Sie sind
gesichert, sie liegen im Fileshare, in unserem Fall sind sie sogar öffentlich. Das
Fragenarchiv existiert **nirgendwo sonst**. Es ist die einzige Datensammlung im System,
die durch den Betrieb erst entsteht — und sie ist per Datenmodell einer namentlich
bekannten Person zugeordnet, unbegrenzt lange, in einer Spalte, die kein einziger
Endpoint je liest.

---

## WER?

**Ein Insider mit Host-Zugriff** — Admin, Entwickler, Ops. Nicht der Krimineller
von aussen, nicht der fremde Staat: für die realistische Bedrohung dieses Systems
braucht es keinen Angriff.

Wertvoll ist das Archiv, weil es etwas erfasst, das sonst nirgends steht: **was welche
Kollegin wann nicht gewusst hat.** Eine Frageliste über ein Jahr ist ein Kompetenz- und
Verhaltensprofil. „Wie kündige ich korrekt", „Regeln zur Freistellung", „darf ich
Kundendaten in ein KI-Tool geben" — jede einzelne Frage ist harmlos, die Sammlung mit
Namen und Zeitstempel ist es nicht. Sie taugt für Leistungsbeurteilung, für eine
Kündigungsbegründung, für die Frage, wer gerade wechseln will.

Der Insider ist auch deshalb der richtige Angreifer, weil das Verhältnis von Aufwand zu
Schaden hier am schlechtesten ist: Aufwand praktisch null, Schaden vollständig.

## WIE?

Kein Exploit. Drei Zeilen:

```bash
docker exec -it src-db-1 psql -U learnflow -d learnflow
SELECT u.email, a.created_at, a.question
  FROM answers a
  JOIN query_sessions s ON s.id = a.session_id
  JOIN users u          ON u.id = s.user_id
 ORDER BY a.created_at;
```

Was diesen Weg offen hält, steht im Repo:

- **Kein zusätzliches Geheimnis nötig.** Wer in der `docker`-Gruppe ist, ist auf dem
  Host faktisch root; das DB-Passwort steht ohnehin in `src/.env`
  (`docker-compose.yml`, `POSTGRES_PASSWORD: ${DB_PASSWORD}`).
- **RBAC greift nicht.** Die drei Rollen (`app/auth/dependencies.py`) schützen die API.
  Dieser Weg geht an der API vorbei.
- **Keine Spur.** Es gibt kein Audit-Log auf DB-Lesezugriffe. Und die Anwendung loggt
  ausschliesslich Fehlerfälle (`logger.exception` in `app/routers/query.py`) — eine
  erfolgreiche Frage hinterlässt **gar keine** Logzeile. Es gibt also nicht einmal
  einen Vergleichsdatensatz, gegen den ein Missbrauch auffallen könnte.
- **Keine zeitliche Grenze.** Aus L1: keine Frist, kein Cleanup. Der Bestand ist alles
  seit Tag eins.
- **Niemand vermisst die Spalte.** Kein Endpoint liest sie. Ein Dump fällt niemandem
  auf, weil die Daten im Normalbetrieb keine Funktion haben.

*Zweitweg, ohne Insider:* In `nginx.conf` ist TLS auskommentiert. Solange das so ist,
laufen JWT und Fragen im Klartext über das Netz — dafür braucht es allerdings eine
Netzposition, während der Insider nichts weiter braucht als seinen Arbeitsplatz.

## GRENZE?

**Was ihn nicht stoppt:** RBAC, Rate-Limiting, die fail-closed-Pipeline, TLS. Alle vier
schützen die API. Der Angreifer ist längst dahinter.

**Was wirkt — die Beute kleiner machen:** die Aufbewahrungsfristen aus
[L3](L3_Minimieren-und-trennen.md). Nach 30 Tagen ist `query_sessions.user_id` NULL,
nach 90 Tagen ist der Fragetext weg. Der `JOIN` oben liefert dann statt „jede Frage
seit Tag eins, mit Namen" noch **maximal 30 Tage zuordenbare Fragen**. Der Insider
kommt weiterhin an die Tabelle — aber ein 30-Tage-Ausschnitt ist kein Profil.

**Was stärker wäre:** die Spalte gar nicht schreiben. Nichts liest sie; ein
`Answer(question=None)` in `app/routers/query.py:606` macht die Beute zu null. Bewusst
nicht gewählt, weil ADR-009 ein Kalibrierungsfenster über echte Fragen braucht — die 90
Tage sind der Preis dafür, und er ist damit **eine benannte Entscheidung statt eines
Defaults**. Fällt die Eval-Begründung weg, fällt auch der Grund für die Spalte.

**Die ehrliche Grenze dieses Modells:** Nichts in diesem System stoppt einen Insider
mit Host-Zugriff. Wer das will, braucht getrennte Betriebsrollen, verschlüsselte
Backups und ein Audit-Log auf DB-Ebene — das ist Betrieb, nicht Applikation. Was in
unserer Hand liegt, ist ausschliesslich die Menge: **Daten, die es nicht mehr gibt,
kann auch der Insider nicht ausleiten.** Genau die Faustregel des Labs.

---

## Die drei nächstgefährlichsten Flüsse (je eine Zeile)

| Fluss | Wer/Wie | Grenze |
|---|---|---|
| **Der ungeprüfte Provider-Fluss** ([L2](L2_Ewigkeits-Check.md), 🔴 unbestätigt) | Kein Angreifer — wir selbst, durch Nichtprüfen. Chunks, Fragen und Antworten sind längst draussen | Nicht mehr abwendbar für das Versendete. Vorwärts: Konto prüfen, AVV, Azure OpenAI EU |
| **Erstes echtes internes Dokument über OpenAI Direct** | Ein gutgläubiger knowledge_owner mit Upload-Recht | Der Code-Guard aus ADR-004/005, der nicht gebaut ist. Heute hindert nichts den Upload |
| **Fehlendes TLS** (`nginx.conf`, auskommentiert) | Netzposition → JWT und Fragen im Klartext | Ops/07 Punkt 1.6; die Konfiguration liegt vorbereitet in der Datei |

---

## Der Absatz, falls es einer sein muss

> Das gefährlichste Datum in LearnFlow ist nicht der Korpus — der existiert anderswo —
> sondern das Archiv aller je gestellten Fragen, das der Betrieb erst erzeugt und das
> über `query_sessions.user_id` namentlich zuordenbar ist. Der realistische Angreifer
> ist kein Krimineller, sondern ein Insider mit Host-Zugriff; er braucht keinen Exploit,
> nur ein `docker exec` und einen Zweifach-Join, und weder RBAC noch Rate-Limiting noch
> die Konfidenz-Pipeline liegen auf diesem Weg. Sein Gewinn ist ein Kompetenz- und
> Verhaltensprofil jedes Pilotnutzers seit Tag eins, weil es keine Aufbewahrungsfrist
> gibt und niemand die Spalte je liest — ein Missbrauch fiele also nicht einmal auf.
> Stoppen lässt er sich in der Applikation nicht. Die einzige Grenze, die wir selbst
> ziehen können, ist die Menge: Entkopplung nach 30 Tagen, Löschung des Fragetexts nach
> 90. Danach ist die Beute ein Ausschnitt statt einer Biografie.
