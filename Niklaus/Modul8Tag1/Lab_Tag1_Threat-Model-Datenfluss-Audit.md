# Modul 8 · Tag 1 — Lab: Threat Model + Datenfluss-Audit

> CAS Application Development with AI (ADAI) · 2026 · BFH Biel · Ilja Rasin
> Quelle: `ADAI_Modul8_Tag1_Lab_v2.docx` (Kopie in diesem Verzeichnis)

**Verteidigung ist Architektur — was fliesst wohin, und was bleibt für immer?**

Am Ende des Nachmittags habt ihr für EUER KI-Projekt eine Datenfluss-Karte, einen
markierten Punkt ohne Rückkehr, konkrete Minimierungen im Code und ein kleines
Threat Model — genau die Denkweise vom Vormittag, angewandt auf euer eigenes System.

> 🔁 **Der rote Faden**
> Alles, was ihr heute erfasst, fragt ihr: braucht das System diese Daten wirklich —
> und was passiert, wenn sie in ein Modell fliessen? Daten ohne Zweck sind Risiko.
> Ein Datenfluss, den ihr nicht kennt, ist eine offene Tür. Beides wollen wir nicht.

## Deliverables

| # | Deliverable | Beschreibung |
|---|---|---|
| 1 | Datenfluss-Karte | Jede Datenart eures Systems: Quelle → Verarbeitung → Speicher → wer sieht sie |
| 2 | Ewigkeits-Markierung | Welche Daten fliessen in ein Modell/Training/Kontext — der Punkt ohne Rückkehr |
| 3 | Minimierung im Code | Mindestens zwei konkrete Änderungen: weglassen, kürzer aufbewahren, trennen |
| 4 | Threat Model (1 Seite) | Ein Angreifer · ein Weg · eine Grenze, die ihn stoppt |

## Ablauf

| Block | Zeit | Thema |
|---|---|---|
| L1 | 13:00–13:45 | Datenfluss-Karte |
| L2 | 13:45–14:30 | Ewigkeits-Check |
| L3 | 14:30–15:15 | Minimieren & trennen |
| L4 | 15:15–15:30 | Threat Model |

---

## L1 · Datenfluss-Karte
**13:00 – 13:45 · Bevor man etwas schützt, muss man wissen, wohin es fliesst.**

### Schritt 1 · Alle Datenarten sammeln

Nehmt euer KI-Projekt. Listet JEDE Art von Daten auf, die es berührt — nicht nur die
offensichtlichen. Fragt Claude Code, wenn ihr unsicher seid:

> Analysiere dieses Projekt. Liste JEDE Art von Daten auf, die es aufnimmt, verarbeitet,
> speichert oder an Dritte sendet. Pro Datenart: Quelle · wo gespeichert · wie lange ·
> wer/was sieht sie · geht sie an eine externe API/ein Modell? Nur was im Code steht —
> mit Datei-Beleg.

Der Zusatz „mit Datei-Beleg" macht die Karte PRÜFBAR — wie beim README gestern.
Ohne Beleg ist es eine Vermutung.

### Schritt 2 · Die Karte zeichnen

Für jede Datenart eine Zeile. Papier oder Whiteboard reicht — Hauptsache sichtbar.
Remote-Teams: Markdown-Tabelle im geteilten Dokument, Ergebnis in den Kurs-Kanal:

```
Datenart        Quelle        Speicher       Aufbewahrung   Extern?
─────────────────────────────────────────────────────────────────────
z.B. Prompts    User-Input    Logfile        ???            → LLM-API
z.B. E-Mails    Upload        Vektor-DB      unbegrenzt     Embedding-Modell
```

> 💡 **Achtung: der unsichtbare Fluss**
> Die gefährlichsten Datenflüsse sind die, die man NICHT plant: Prompts, die geloggt
> werden. Dokumente, die in einen Vektor-Store gehen. Kontext, der an eine externe API
> geht. Sucht gezielt danach.

**Leitfrage:** Welche Datenart hat euch überrascht — welche fliesst irgendwohin, wo ihr
sie nicht erwartet habt?

---

## L2 · Der Ewigkeits-Check
**13:45 – 14:30 · Daten sind löschbar. Gewichte nicht. Wo ist bei euch der Punkt ohne Rückkehr?**

Geht eure Datenfluss-Karte durch und markiert jede Datenart mit einer der drei Kategorien:

| Kategorie | Bedeutung |
|---|---|
| 🟢 **LÖSCHBAR** | Liegt in DB/Datei/Log. Kann gelöscht werden, Frist setzbar. Recht auf Vergessen funktioniert. |
| 🟠 **EXTERN** | Geht an eine fremde API (LLM, Embedding, Cloud). Ihr verliert die Kontrolle — aber es ist (noch) kein Training. |
| 🔴 **EWIG** | Fliesst in ein Training / Fine-Tuning / dauerhaften Modell-Kontext. Punkt ohne Rückkehr. Nicht mehr entfernbar. |

**Prüf-Fragen für die 🔴-Kategorie:**

- [ ] Nutzt euer Projekt Fine-Tuning oder Training auf eigenen Daten? → alles, was da hineingeht, ist EWIG.
- [ ] Sendet ihr Daten an einen Anbieter, der auf Eingaben trainiert? (Default-Einstellung prüfen! Manche tun es, wenn man nicht widerspricht.)
- [ ] Landen Nutzer-Daten in einem dauerhaften Vektor-Store, der Teil des Modell-Kontexts wird?
- [ ] Gibt es eine Einstellung „opt out of training" beim API-Anbieter — ist sie aktiv?

> ⚠️ **Der stille Default**
> Viele „gratis" KI-Dienste trainieren standardmässig auf euren Eingaben — es sei denn,
> ihr widersprecht aktiv. Genau der Köder-und-Haken-Mechanismus vom Vormittag: gratis,
> weil ihr mit dem Rohstoff eures Denkens zahlt. Prüft die Einstellung.

**Leitfrage:** Wo ist bei EUREM Projekt der Punkt ohne Rückkehr — welche Daten könntet
ihr nie wieder herausbekommen?

---

## L3 · Minimieren & trennen
**14:30 – 15:15 · Die beste Art, Daten zu schützen: sie gar nicht haben. Jetzt konkret, im Code.**

Wählt aus eurer Karte mindestens ZWEI Datenflüsse und wendet eine der Grenzen an.
Nicht theoretisch — als echte Änderung im Code oder in der Konfiguration.

| # | Grenze | Anwendung |
|---|---|---|
| 1 | **Weglassen** | Braucht das System diese Daten WIRKLICH? Sammelt ihr etwas „für später", „könnte nützlich sein"? Streichen. Nicht erfasste Daten sind das sicherste Datum. |
| 2 | **Kürzer halten** | Logs, die ewig bleiben → Frist setzen (z. B. 30 Tage, dann Löschung). Prompts, die gespeichert werden → braucht ihr die Historie? |
| 3 | **Trennen (Silos)** | Personendaten vom Rest trennen. Kein vereintes Profil. Was zusammen liegt, leakt zusammen. |
| 4 | **Nicht ins Training** | opt-out beim API-Anbieter aktivieren. Sensible Daten NICHT in Fine-Tuning. Lokale/anonymisierte Daten, wo möglich. |

Claude Code kann helfen — aber IHR entscheidet, was weg kann:

> Wo in diesem Projekt werden personenbezogene oder sensible Daten gespeichert oder an
> externe Dienste gesendet? Schlage für jeden Fall vor: weglassen, kürzer aufbewahren,
> oder trennen. Zeige die konkrete Code-Stelle. Ich entscheide, was umgesetzt wird.

**Leitfrage:** Welche zwei Änderungen habt ihr umgesetzt — und welche Daten fliessen
jetzt NICHT mehr?

---

## L4 · Threat Model — eine Seite
**15:15 – 15:30 · Ein Angreifer. Ein Weg. Eine Grenze, die ihn stoppt.**

Kein 40-seitiges Dokument. Ein Absatz, der drei Fragen beantwortet — für den
gefährlichsten Datenfluss aus eurer Karte:

| Frage | Inhalt |
|---|---|
| **WER?** | Wer will an diese Daten — und warum sind sie wertvoll? (Krimineller, Datenbroker, fremder Staat, Insider?) |
| **WIE?** | Welcher Weg? (Leak beim Anbieter · abgegriffener Prompt · Account-Übernahme · Daten im Training, die nie zurückkommen) |
| **GRENZE?** | Was stoppt ihn — oder macht die Beute wertlos? (Daten gar nicht sammeln · Frist · opt-out vom Training · Trennung) |

> 🎯 **Die Faustregel**
> Ihr könnt die Sicherheit eures Anbieters nicht kontrollieren — nur, WAS ihr ihm gebt.
> Die stärkste Grenze ist fast immer die erste: Daten, die es nicht gibt, kann niemand
> stehlen und kein Modell für immer verschlucken.

---

## Präsentation (3 Min pro Team)

1. Zeigt EINEN Datenfluss aus eurer Karte, der nie zurückkommt (🔴 EWIG) — oder erklärt, warum ihr keinen habt.
2. Eine Grenze, die ihr heute eingezogen habt: welche Daten fliessen jetzt nicht mehr?
3. Der gefährlichste Fund eures Audits — der Datenfluss, den ihr vorher nicht auf dem Schirm hattet.

---

*BFH · CAS ADAI 2026 · Modul 8 · Tag 1 — Lab*
