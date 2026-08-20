# CommentChecker

Ein Agent, der vor dem Commit prüft, ob **deutsche Kommentare** im Code stehen,
und für die Funde eine englische Fassung vorschlägt.

Übung Modul 5B. Herkunft: Modul5BTag1, hier wird er fertiggestellt.

## Die Konvention, die er durchsetzt

Kommentare und Docstrings im Code sind **englisch**. Deutsch bleibt `Docs/`,
`Ops/`, README, PR-Texten und Issues vorbehalten (CLAUDE.md, Team-Absprache).

## Der eigentliche Punkt: die Arbeitsteilung

Das ist der Grund, warum dieser Agent existiert — nicht die Kommentarprüfung:

| | entscheidet | Kosten | Verhalten |
|---|---|---|---|
| **Python** | was eindeutig ist | keine | immer gleich |
| **Modell** | die Zweifelsfälle | pro Lauf | urteilt |

Umlaute, deutsche Füllwörter und transliterierte Formen (`ueber`, `waere`,
`fuer`) findet ein Regex sicher, sofort und gratis. **Wer dafür ein LLM bezahlt,
bezahlt für `grep`.**

Zwei Folgerungen, die im Code stehen:

- Findet die Regel **gar nichts**, wird kein Modell aufgerufen. Der häufigste
  Fall im Alltag kostet also nichts. Ein Prüfer, der bei jedem Commit Geld
  kostet, wird abgeschaltet.
- **Blockieren tut die deterministische Hälfte.** Das Modell darf zusätzlich
  blockieren (wenn es einen Zweifelsfall als deutsch einstuft), aber ein
  eindeutiger Fund bleibt ein Fund, egal was das Modell sagt.

## Aufbau

| Datei | Rolle | braucht |
|---|---|---|
| `staging.py` | die Git-Hälfte: was committet werden soll, als Pfad + Inhalt | Git-Repo |
| `comment_rules.py` | die Sprach-Hälfte: Kommentare herauslösen, Signale, Einstufung | nichts |
| `comment_checker.py` | die Agent-Hälfte: zwei Tools, System-Prompt, Ergebnis-Logik | SDK + Key |
| `test_staging.py` | Trockentest der Git-Hälfte, in einem Wegwerf-Repo | Git |
| `test_comment_rules.py` | Trockentest der Regeln | nichts |
| `smoke_comment_checker.py` | Trockenlauf der Tool-Wrapper | Git-Repo |

Die Trennung ist dieselbe wie bei `confidence.py` / `third_agent.py` aus Tag 1:
**Logik ohne SDK, Wrapper ohne Logik.** Deshalb laufen `test_comment_rules.py`
und `test_staging.py` ohne API-Key, ohne Container, ohne Kosten.

Die beiden Logik-Module wissen nichts voneinander:

```
staging.py         kennt Git, kennt keine Kommentare
comment_rules.py   kennt Sprache, kennt kein Git
comment_checker.py führt sie zusammen — drei Zeilen, mehr darf die Naht nicht sein
```

`staging.py` bekommt den Dateifilter als Argument (`comment_rules.unterstuetzt`),
statt ihn zu kennen. Damit ist es für jeden weiteren Pre-Commit-Prüfer brauchbar
— es weiss nicht, wofür es gelesen wird.

## Ablauf

```
git diff --cached --name-only        Was soll committet werden?
        ↓
git show :<pfad>                     Der gestagte Blob, nicht die Datei auf der Platte
        ↓
comment_rules.pruefe_datei()         Kommentare herauslösen, Signale, Einstufung
        ↓
    ┌───────────────┬────────────────┐
  sicher        verdächtig       unauffällig
    │               │                │
    └───────┬───────┘             ignoriert
            ↓
    kein Fund → fertig, kein Modell, keine Kosten
    sonst     → Modell (siehe unten)
```

## Was `sicher` und `verdächtig` unterscheidet

Nicht, **ob** das Modell läuft — das hängt allein daran, ob überhaupt etwas
gefunden wurde. Unterschiedlich ist, was das Modell damit tut und was der
Exit-Code daraus macht:

| | Aufgabe des Modells | Exit-Code |
|---|---|---|
| `sicher` | schon entschieden — nur die englische Fassung vorschlagen | blockiert **bedingungslos** |
| `verdächtig` | Deutsch oder Englisch mit Fachbegriff? Urteilen, dann übersetzen | blockiert nur, wenn das Modell es als deutsch einstuft |

Die Einstufung spart also nicht den Aufruf, sondern das **Nachdenken innerhalb
des Aufrufs** — weniger Tokens, kein Nullbetrag.

Wirklich gratis sind zwei Fälle: kein Fund, oder `--alle` (nur die
deterministische Hälfte, für die CI gedacht).

## Der Subagent

Dieselbe Arbeitsteilung wie zwischen Python und Modell, eine Ebene höher gezogen
— diesmal zwischen teurem und billigem Modell:

```
Python   ↔  Modell     was eindeutig ist  ↔  was Urteil braucht
Sonnet   ↔  Haiku      urteilen           ↔  übersetzen
```

| | Haupt-Agent | Subagent `uebersetzer` |
|---|---|---|
| Modell | `claude-sonnet-4-6` | `haiku` |
| Aufgabe | Zweifelsfälle beurteilen, Bericht schreiben | englische Fassungen schreiben |
| Sieht `staged_comments` | ja | **nein** |
| Sieht `language_signals` | ja (soll aber nicht) | ja |

**Der Subagent bekommt `staged_comments` nicht.** Er kann den Staging-Bereich
gar nicht lesen — er bearbeitet nur den Text, den der Haupt-Agent ihm im Auftrag
übergibt. Minimalrechte auf der zweiten Ebene, mit derselben Begründung wie auf
der ersten. Anders als `allowed_tools` ist die `tools`-Liste eines Subagenten
eine *echte* Schranke; in `test_subagent.py` liess sich das direkt beobachten.

**Umgekehrt gilt das nicht.** Der Haupt-Agent *kann* `language_signals` aufrufen,
obwohl der Prompt ihm die Rolle nicht zuweist: MCP-Tools sind über `mcp_servers`
verfügbar, und `allowed_tools` regelt nur die Rückfrage. Ihn wirklich fernzuhalten
bräuchte **zwei getrennte MCP-Server** — einen pro Rolle. Die Rollentrennung ist
hier also beim Subagenten durchgesetzt und beim Haupt-Agenten nur beschrieben.
Das gehört so gesagt, statt es als Grenze auszugeben.

### Was der erste scharfe Lauf gekostet hat

`allowed_tools` gilt für die **ganze Session, Subagenten eingeschlossen**.
`AgentDefinition.tools` sagt nur, was der Subagent *sieht* — ob er es *benutzen*
darf, steht in `allowed_tools`.

Im ersten Lauf fehlte `language_signals` dort, weil der Haupt-Agent es nicht
brauchen sollte. Folge: der Übersetzer durfte seine Gegenprobe nicht aufrufen,
delegierte dreimal neu und lieferte am Ende ungeprüft — 9 Turns, $0.16. Der
Agent schlug dann vor, die Berechtigung „einmalig zu erteilen"; das wäre
wirkungslos gewesen, weil das Skript nicht-interaktiv läuft und `setting_sources=[]`
nichts von der Platte liest oder dorthin schreibt. **Die Erlaubnis gehört in den
Code, nicht in einen Klick.**

Immerhin hat er nicht so getan, als sei die Gegenprobe gelaufen, sondern es
gemeldet. Fail-loud statt still falsch.

### Offen: der `bash`-Aufruf

Im selben Lauf tauchte nach einer Delegation `>>> TOOL-CALL: bash` im Stream auf
— mit `tools=["mcp__sprache__language_signals"]` sollte das nicht möglich sein.
Die Ursache ist **nicht geklärt**. Bis dahin steht ein Riegel: der Subagent hat
zusätzlich eine `disallowedTools`-Sperrliste (`Bash`, `bash`, `Read`, `Write`,
`Edit`, `Grep`, `Glob`, `Agent` — letzteres, damit er nicht weiterdelegiert). Eine
Sperrliste schlägt jede Freigabe. `smoke_comment_checker.py` prüft, dass sie steht.

Im Lauf sichtbar als:

```
>>> TOOL-CALL: mcp__sprache__staged_comments
>>> DELEGIERT an Subagent: 'uebersetzer'
```

Der `subagent_type` wird bewusst ausgeschrieben: zieht der Haupt-Agent einen
eingebauten Typ statt unseren, fällt das sonst nicht auf.

**Ehrlich zur Rechnung:** bei einer Handvoll Kommentare kostet der Umweg mehr,
als die Haiku-Übersetzung spart — ein zusätzlicher Turn und ein zweiter Aufruf.
Er lohnt sich, wenn ein Commit regelmässig viele deutsche Kommentare enthält.
Hier steht er als Übung, und weil er die Rollentrennung sichtbar macht.

Gelesen wird der **gestagte Blob**, nicht die Arbeitskopie: wer eine Änderung
nur teilweise staged, committet auch nur diesen Teil — und genau der wird
geprüft.

## Ausführen

```bash
# 1. Regeln testen — ohne alles
python test_comment_rules.py

# 2. Git-Hälfte testen — Wegwerf-Repo unter tempfile, fasst deinen Stand nicht an
python test_staging.py

# 3. Tool-Wrapper trocken prüfen — braucht ein Git-Repo, kein Modell
python smoke_comment_checker.py

# 4. Nur die deterministische Hälfte, kein Modell, keine Kosten
python comment_checker.py --alle

# 5. Voller Lauf: Modell urteilt über die Zweifelsfälle
python comment_checker.py
```

Exit-Code `1`, wenn etwas zu übersetzen ist — damit taugt das Skript als
Pre-Commit-Hook. Exit-Code `2`, wenn der Staging-Bereich nicht lesbar ist.

## Die Regeln im Detail

**Drei Signale**, jedes für sich schwach, zusammen aussagekräftig:

| Signal | Beispiel | Fallstrick, der behandelt ist |
|---|---|---|
| Umlaute | `ä ö ü Ä Ö Ü ß` | — |
| Stoppwörter | `der`, `nicht`, `wird`, `dass` | als **ganze Wörter**, sonst trifft `die` in `died` |
| Transliteration | `ueber`, `waere`, `fuer` | als **Wortliste**, ein Muster wie `ue` träfe `queue`, `value`, `true` |

**Drei Einstufungen:**

- `sicher` — kein englischer Satz sieht so aus. Auslöser: eine transliterierte
  Form, oder ≥ 2 verschiedene Stoppwörter, oder 1 Stoppwort + Umlaut.
- `verdächtig` — irgendein Signal, aber nicht eindeutig. Typisch: ein einzelner
  Umlaut, der ein Fachbegriff in einem englischen Satz sein kann
  (*„the Rückfall applies here"*). **Das ist der Fall, für den es den Agent gibt.**
- `unauffällig` — kein Signal. Taucht gar nicht erst auf.

**Sprachen:** `.py` (via `tokenize` + `ast`), `.ts`/`.tsx`/`.js`/`.mjs`,
`.yaml`/`.yml`, `Makefile`.

## Was bewusst nicht geprüft wird

**Nur Kommentare und Docstrings, keine Strings.** Das schliesst die häufigsten
Fehlalarme von vornherein aus — sie tauchen gar nicht erst auf:

- Selektoren auf deutsche UI-Texte: `getByRole({name: /löschen/i})`
- Erwartete Meldungstexte in Zusicherungen
- Mock-Antworten, die echte deutsche API-Meldungen nachbilden

Das ist Code, kein Kommentar.

## Minimalrechte

Das Modell bekommt kein `Read` und kein `Bash` — nur die beiden Tools. Es kann
nicht im Repo herumsuchen, sondern urteilt über genau die Kommentare, die aus
dem Staging-Bereich kommen.

**Durchgesetzt wird das von `tools=[]`, nicht von `allowed_tools`.** Die zwei
Felder sehen ähnlich aus und tun Verschiedenes — das ist die Stelle, an der
Minimalrechte am häufigsten scheitern:

| Feld | Bedeutung |
|---|---|
| `tools` | welche eingebauten Tools es **überhaupt gibt** |
| `allowed_tools` | welche davon **ohne Rückfrage** benutzt werden dürfen |

Die SDK-Dokumentation sagt es selbst: `allowed_tools` sind *„tool names that are
auto-allowed without prompting for permission"*. Steht ein Tool nicht drin, ist
es trotzdem im Kontext und kann angefordert werden. In `test_subagent.py` (Tag 2)
liess sich das direkt beobachten: `allowed_tools=["Read", "Grep"]` — und das
Modell rief `Agent` auf.

**Vier Quellen, jede einzeln geschlossen.** Keine deckt eine andere mit ab:

| Option | Wert | schliesst |
|---|---|---|
| `tools` | `["Agent"]` | alle eingebauten Tools **ausser** dem Delegations-Tool |
| `skills` | `[]` | alle Skills |
| `setting_sources` | `[]` | CLAUDE.md, `.claude/agents`, `settings.json` |
| `strict_mcp_config` | `True` | fremde MCP-Server aus `.mcp.json` |

Die Falle dabei: bei `skills` und `setting_sources` heisst `None` **nicht** „aus",
sondern „CLI-Standard" — also *alles*. Ein vergessenes Feld sieht aus wie ein
geschlossenes. Deshalb prüft `smoke_comment_checker.py` auf die leere Liste und
nicht bloss darauf, dass der Wert falsch ist.

**Zusätzlich zugeschnitten sind die Tools selbst.** `staged_comments` nimmt gar
keinen Parameter, `language_signals` nur einen Text. Das Modell kann also keinen
Pfad, kein Verzeichnis und kein Muster nennen — es gibt schlicht keine Stelle,
an der es den Zugriff ausweiten könnte. Der Pfad in `git show :<pfad>` stammt aus
der Ausgabe von `git diff --cached`, nie aus dem Modell; `subprocess.run` bekommt
ein Tupel und kein `shell=True`. Das ist `Bash` ohne Sprengradius.

**`tools` ist nicht mehr leer — das ist der Preis des Subagents.** Delegieren
läuft über das eingebaute `Agent`-Tool; ohne den Eintrag gäbe es keinen Weg zum
Subagenten und `agents=` wäre tote Konfiguration. Die Liste ist deshalb bewusst
genau **einen** Eintrag lang: kein `Read`, kein `Bash`, kein `Write`. Der Handel
steht so im Code und wird von `smoke_comment_checker.py` festgenagelt
(`opts.tools == ["Agent"]`).

**Nicht benutzt: `can_use_tool`.** Der Callback wäre die härteste Variante, aber
er verlangt den Streaming-Modus — mit `query(prompt="…")` wirft das SDK. Ausserdem
werden Tools aus `allowed_tools` auto-erlaubt und erreichen ihn gar nicht. Nach
`tools=[]` und `skills=[]` bleibt nichts übrig, was er noch ablehnen könnte.

## Bekannte Lücken, bewusst in Kauf genommen

- **Deutsch ohne Marker wird nicht erkannt.** *„Rechnet Werte um"* hat weder
  Umlaut noch Stoppwort noch Transliteration. Die Signalliste breiter zu machen
  (Endungen wie `-er`, `-ung`) würde `user`, `header`, `config` treffen — der
  Preis wäre höher als der Nutzen. Festgehalten in `test_comment_rules.py`.
- **Fachbegriff ohne Umlaut fällt nicht auf.** *„The Bereichsverantwortliche may
  upload"* ist `unauffällig`. Richtig so: der Satz ist englisch.
- **`.md`, `.sql`, `.sh` werden ignoriert.** Markdown ist Doku, dort ist Deutsch
  erwünscht.

## Offene Punkte

Was zum Fertigstellen noch aussteht:

1. **Der Pre-Commit-Hook fehlt.** Der Exit-Code ist da, die Hook-Datei nicht.
   Ohne sie ist es ein Skript, das man von Hand aufruft — also eines, das man
   vergisst.
2. **Selbstreferenz.** `comment_rules.py` und `comment_checker.py` sind selbst
   deutsch kommentiert (mit transliterierten Umlauten). Werden sie gestaged,
   meldet der Prüfer **sich selbst** — korrekt nach seiner eigenen Regel.
   Entscheidung nötig: Kommentare ins Englische übersetzen (konsistent, aber der
   didaktische Wert der deutschen Erklärungen geht verloren), oder die beiden
   Dateien ausnehmen (bequem, aber eine Ausnahme, die man begründen muss).
3. **`_raute` kennt keine Strings.** In YAML und Makefile gilt jedes `#` als
   Kommentarbeginn — auch in `key: "wert # kein Kommentar"`. Bei Python löst
   `tokenize` das korrekt, hier nicht. YAML verlangt ausserdem ein Leerzeichen
   vor `#`; das wird nicht geprüft, `key: a#b` schlägt also fälschlich an.
4. **Die Gegenprobe wird nicht erzwungen.** Der System-Prompt verlangt, den
   englischen Vorschlag mit `language_signals` gegenzuprüfen. Nichts im Code
   stellt sicher, dass das passiert ist.
5. **Umbenannte Dateien fallen durch.** `--diff-filter=ACM` deckt Added, Copied
   und Modified ab — nicht `R`. Eine Datei, die im selben Commit umbenannt *und*
   geändert wird, wird nicht geprüft.
6. **Keine CI-Einbindung.** `--alle` ist genau dafür gedacht (kein Modell,
   niemand wartet auf ein Urteil), wird aber nirgends aufgerufen.

## Änderungen gegenüber Modul5BTag1

**1. Repo-Wurzel über Git statt gezählter Pfade.** `REPO` wurde von
`Path(__file__).parent.parent.parent` auf `git rev-parse --show-toplevel`
umgestellt. Ein gezählter Pfad bricht **still**, sobald der Ordner die Ebene
wechselt: `git` läuft dann im falschen Verzeichnis und meldet einen leeren
Staging-Bereich statt eines Fehlers — der Prüfer wäre grün, ohne etwas geprüft zu
haben. Genau das ist bei diesem Umzug passiert.

**2. Minimalrechte tatsächlich durchgesetzt.** Der Docstring behauptete schon in
Tag 1, das Modell bekomme kein `Read` und kein `Bash`. Durchgesetzt hat das nur
`allowed_tools` — also gar nicht. Neu: `tools=[]`, `skills=[]`,
`setting_sources=[]`, `strict_mcp_config=True` und `cwd`. Siehe Abschnitt
*Minimalrechte*.

**3. `max_turns` von 20 auf 10.** Die Aufgabe braucht einen Aufruf von
`staged_comments`, ein paar Gegenproben und die Antwort. 20 war grosszügig für
etwas, das bei jedem Commit läuft.

**4. Der Trockenlauf prüft die Zusicherungen mit.** `smoke_comment_checker.py`
hat neu einen Block *Rechte* und einen Block *Deckel*. Eine Zusicherung, die
nirgends geprüft wird, ist eine Absicht — keine Zusicherung.

**5. Git-Hälfte in `staging.py` herausgelöst.** Vorher steckte die
Datenbeschaffung in `comment_checker.py` und war damit an das SDK gekoppelt: um
sie zu testen, musste man ein Modul importieren, das `claude_agent_sdk` mitzieht.
Genau das, was `comment_rules.py` bewusst vermeidet. Jetzt hat auch die Git-Seite
ihren abhängigkeitsfreien Test.

**6. Subagent `uebersetzer` fest eingebaut.** Haupt-Agent (Sonnet) urteilt,
Subagent (Haiku) übersetzt. Kosten: `tools` ist von `[]` auf `["Agent"]`
gewachsen. Siehe Abschnitt *Der Subagent*.

Kein eigenes **MCP-Tool** — bewusst. Das Modell hat kein `Read`; eine Liste von
Pfaden wäre Information, mit der es nichts anfangen kann, dafür ein zusätzlicher
Turn und eine zweite Beschreibung, die mit `staged_comments` konkurriert. Die
Trennung gehört in den Code, nicht an die Modell-Oberfläche.
