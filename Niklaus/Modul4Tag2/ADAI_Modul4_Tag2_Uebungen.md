# Team-Setup & Git-Workflow — Drei Übungen

**CAS Application Development with AI (ADAI) · 2026 — Modul 4 · Tag 2**
BFH Biel · Ilja Rasin

---

**Heute richtet ihr euer Team und eure Zusammenarbeit ein — Rollen, Git-Workflow und CLAUDE.md als Projekt-Gedächtnis.**

## Zeitplan

| Block | Zeit | Thema |
|-------|------|-------|
| Ü1 | 09:15–10:00 | Team-Rollen — Wer macht was im Team? |
| Ü2 | 10:15–11:00 | Git-Workflow — Branches · PRs · Reviews |
| Ü3 | 11:00–12:00 | CLAUDE.md — Projekt-Gedächtnis schreiben |

---

## Ü1 · Team-Rollen verteilen — 09:15–10:00

*Wer übernimmt welche Verantwortung — und wie hilft AI dabei?*

> **Kontext:** In einem kleinen Team (2–3 Personen) hat niemand einen festen Titel — alle programmieren. Aber jemand muss für bestimmte Dinge **verantwortlich** sein, sonst fällt es zwischen die Stühle.
>
> **Die drei Verantwortungsbereiche:**
> - **Tech Lead** — trifft die letzte Architektur-Entscheidung wenn das Team uneinig ist. Leitet Code Reviews. Hält technische Schulden im Blick. Das ist kein «Chef» — eher der technische Kompass.
> - **Developer** — jeder im Team ist Developer. Implementiert Features, schreibt Tests, erstellt PRs. Hier geht es um die tägliche Umsetzungsarbeit.
> - **QA / DevOps** — verantwortlich dass Qualität gesichert ist und Deployment funktioniert. In kleinen Teams oft eine Person die «den Überblick über Tests und CI/CD behält».
>
> **Wichtig:** Eine Person kann mehrere Rollen haben. Bei 2 Personen übernimmt einer Tech Lead + DevOps, der andere fokussiert auf Development + QA.

### Teil 1 · Rollen im Team verteilen (15 Min)

**Besprecht ehrlich wer welche Stärken hat. Verteilt die Verantwortungsbereiche:**

| Rolle | Wer übernimmt das? | Warum diese Person? |
|-------|-------------------|---------------------|
| 🏗️ Tech Lead | | |
| 💻 Lead Developer | | |
| 🧪 QA / DevOps | | |

### Teil 2 · AI als Teammitglied einplanen (20 Min)

**Claude Code ist wie ein viertes Teammitglied. Überlegt für jede Rolle: wo hilft AI konkret?**

Prompt für Claude:

```
Wir sind ein Team von [2/3] Personen für ein [PROJEKTNAME].
Tech-Stack: [EUER STACK]

Für jede dieser Rollen — wo kann Claude Code uns konkret helfen?
- Tech Lead (Architektur, Reviews)
- Developer (Implementation, Tests)
- QA/DevOps (Testing, CI/CD, Deployment)

Gib konkrete Beispiele — keine allgemeinen Floskeln.
Was sollte der Mensch behalten, was kann AI übernehmen?
```

**Wo AI uns am meisten hilft — und was wir Menschen behalten:**

```
 
```

> 💡 **Wichtigste Regel:** AI macht Vorschläge und beschleunigt — aber die Verantwortung für Entscheidungen bleibt immer beim Menschen mit der jeweiligen Rolle.

---

## Ü2 · Git-Workflow aufsetzen — 10:15–11:00

*Branches, Pull Requests, Code Review — die Sprache der Zusammenarbeit.*

> **Kontext:** Ohne Regeln entsteht Chaos — Code wird überschrieben, niemand weiss was aktuell ist. Git-Workflow ist die Lösung.
>
> **Die zentrale Idee — Branches:**
> - **`main`** — der heilige Branch. Hier ist nur Code der funktioniert. Niemand committed direkt hierher. Immer grün, immer deploybar.
> - **`feature/TASK-001-...`** — für jeden Task ein eigener Branch. Du arbeitest isoliert, ohne andere zu stören. Wenn fertig: zurück in `main` via Pull Request.
> - **`fix/...`** — für Bugfixes. Schnell rein, schnell raus.
>
> **Der Pull Request (PR) ist das Herzstück:** Ein PR sagt: «Ich will meinen Branch in main mergen — bitte schaut drüber.» Erst wenn jemand (oder Claude) reviewt und approved hat, wird gemergt. So kommt nie ungeprüfter Code in `main`.
>
> **Mit AI:** Bevor ein Mensch reviewt, lässt man Claude den Code prüfen — Bugs, Stil, vergessene Logs. Das spart dem menschlichen Reviewer Zeit.

### Teil 1 · Euren Branch-Workflow festlegen (15 Min)

**Einigt euch im Team auf eure Regeln:**

| Frage | Unsere Regel |
|-------|-------------|
| Wie benennen wir Branches? | |
| Wer darf in `main` mergen? | |
| Wie viele Reviews braucht ein PR? | |
| Nutzen wir Claude für Pre-Review? | |
| Wie oft mergen wir (täglich/pro Task)? | |

### Teil 2 · Den Workflow einmal durchspielen (20 Min)

**Spielt einen kompletten Durchlauf durch — jeder macht einmal einen kleinen Branch:**

| Schritt | Aktion |
|---------|--------|
| 1 | Branch erstellen: `git checkout -b feature/TASK-001-test` |
| 2 | Kleine Änderung machen (z.B. README ergänzen) + committen |
| 3 | Branch pushen: `git push origin feature/TASK-001-test` |
| 4 | Auf GitHub einen Pull Request öffnen |
| 5 | Teammitglied reviewt den PR + gibt Kommentar |
| 6 | Mergen + Branch löschen |

**Was war unklar oder hat nicht funktioniert?**

```
 
```

> ⚠️ **Häufiger Anfängerfehler:** zu lange auf einem Branch arbeiten. Je länger ein Branch lebt, desto schwieriger der Merge. Regel: **ein Task = ein Branch = max 1–2 Tage.**

---

## Ü3 · CLAUDE.md schreiben — 11:00–12:00

*Das Gedächtnis das Claude Code bei jedem Prompt mitliest.*

> **Kontext:** Wenn ihr Claude Code im Projekt startet, sucht es automatisch nach einer Datei namens `CLAUDE.md` im Projekt-Root. Was darin steht, liest Claude bei **JEDEM Prompt** mit — ohne dass ihr es wiederholen müsst.
>
> Stellt es euch vor wie das Onboarding für ein neues Teammitglied:
> - **Stack** — welche Sprachen, Frameworks, Datenbanken nutzt ihr? So schlägt Claude keine fremden Technologien vor.
> - **Architektur** — eure ADR-Entscheidungen. «Modularer Monolith, REST API». So baut Claude im richtigen Stil.
> - **Konventionen** — Test-Framework, Branch-Naming, Code-Style. So passt der generierte Code zu eurem.
> - **Was Claude NICHT tun soll** — explizite Verbote. «Keine `print()` Statements, keine hardcodierten Secrets». Das wird respektiert.
>
> **Der Effekt:** Statt bei jedem Prompt «Wir nutzen FastAPI und PostgreSQL, schreib Tests mit pytest...» zu wiederholen, schreibt ihr es EINMAL in `CLAUDE.md`. Danach kennt Claude euren Kontext.
>
> **Praktischer Bonus:** Wenn ein neues Teammitglied dazukommt, liest es `CLAUDE.md` und versteht sofort die wichtigsten Entscheidungen des Projekts.

### Teil 1 · Euer CLAUDE.md mit AI entwerfen (25 Min)

**Nutzt eure Architecture-Entscheidungen aus Modul 3 als Basis:**

```
Hilf mir eine CLAUDE.md für unser Projekt zu schreiben.

Lies zuerst diese Dokumente im Repo:
- Docs/06_Architecture-Draft.md
- Docs/04_ADR-001_Architekturstil.md
- Docs/04_ADR-002_Backend-Frontend-Stack.md
- Docs/04_ADR-003_Datenpersistenz.md
- Docs/04_ADR-004_LLM-Provider.md
- Docs/04_ADR-006_Background-Worker.md
- Docs/04_ADR-008_Konfidenz-Pipeline.md
- Docs/04_ADR-010_API-First.md

Erstelle daraus eine CLAUDE.md mit den Abschnitten:
## Stack
## Architektur (mit ADR-Referenzen)
## Konventionen (Tests, Branches, PRs)
## Was Claude NICHT tun soll

Halte es konkret und kurz — keine Romane.
```

**Unsere CLAUDE.md — Entwurf:**

```
 
```

### Teil 2 · CLAUDE.md testen (10 Min)

**Legt die Datei im Projekt an und testet ob Claude Code sie versteht:**

```
# Im Projekt-Ordner mit Claude Code:
claude

> Was ist unser Tech-Stack?
> Welches Architektur-Pattern nutzen wir?
> Schreib einen kleinen Test — beachte unsere Konventionen.
```

**Hat Claude unseren Kontext korrekt verstanden? Was fehlte?**

```
 
```

---

## Ausblick: Lab heute Nachmittag

Am Nachmittag setzt ihr euer komplettes Dev Environment auf:

- GitHub Repo erstellen + Team einladen + Branch-Strategie
- Projekt-Struktur mit Claude Code generieren
- CLAUDE.md finalisieren und committen
- Abschlusspräsentation: Modul 4 abschliessen

---

*CAS ADAI 2026 · BFH Biel · Modul 4 Tag 2 · Ilja Rasin*
