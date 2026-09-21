"""Block 5 — überarbeitete Fassung (v3), Ausgangslage: alle Folien der Fassung vom 20.09.

Quellen (beide archiviert, werden nur gelesen):
    A20 = ../Archive/2026-09-20/Block5_Fazit-Ausblick.html   (20.09., 5 Folien, mit Bereichsleiste)
    A19 = ../Archive/Block5_Fazit-Ausblick.html              (19.09., 6 Folien, ohne Leiste)
Ergebnis:
    ../Block5_Fazit-Ausblick.html

Kopf (CSS) und Fuss (Navigation) stammen aus A20. Jede Folie wird unverändert aus
ihrer Quelle übernommen; Korrekturen stehen als (alt, neu)-Paare bei der Folie —
alt ist ein Text oder ein Regex — und müssen genau einmal treffen, sonst bricht der
Build ab. Gleiches Verfahren wie build_block2_v4.py.

    python build/build_block5_v3.py
"""

import base64
import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
SOURCES = {
    "A20": BASE / "Archive" / "2026-09-20" / "Block5_Fazit-Ausblick.html",
    "A19": BASE / "Archive" / "Block5_Fazit-Ausblick.html",
}
OUT = BASE / "Block5_Fazit-Ausblick.html"

# CSS-Ergänzungen zum Kopf von A20.
EXTRA_CSS = """
    /* v3: Bild Gold/Bronze links auf «Gold muss Gold sein» — dunkler Bildhintergrund, daher
       abgerundet und mit Schatten, damit es auf der hellen Folie als Karte steht */
    .goldimg { display: block; width: 440px; height: auto; margin-top: 34px; border-radius: 20px;
               box-shadow: 0 18px 40px rgba(16, 30, 54, .22); }
"""

# Illustration Gold/Bronze (assets/gold.png, 1536 × 1024). Beim Build eingebettet, siehe unten.
GOLD_IMG = ('<img class="goldimg" src="assets/gold.png" alt="Eine glänzende Goldmedaille neben einer '
            'matten Bronzemedaille">')

# Modellvergleich mit den drei Grenzen als Spalten (Reihenfolge und Begriffe wie F1).
MODEL_TABLE = """\
          <table class="vs">
            <tr><th>Modell</th><th class="r">erfundene<br>Belege</th><th class="r">«Weiss ich nicht»<br>bei fremden Fragen</th><th class="r">fälschlich<br>abgelehnt</th></tr>
            <tr><td class="l">Grenze</td><td class="l r">0 %</td><td class="l r">≥ 90 %</td><td class="l r">≤ 15 %</td></tr>
            <tr><td class="l">gpt-4o-mini · Cloud-Referenz</td><td class="v r ok">0 %</td><td class="v r ok">90,9 %</td><td class="v r bad">22,2 %</td></tr>
            <tr class="hi"><td class="l">gemma4 · 26B · lokal</td><td class="v r ok">0 %</td><td class="v r">86,4 %</td><td class="v r ok">11,1 %</td></tr>
            <tr><td class="l">qwen3 · 8B · lokal</td><td class="v r ok">0 %</td><td class="v r bad">68,2 %</td><td class="v r ok">6,7 %</td></tr>
            <tr><td class="l">gpt-oss · 20B · lokal</td><td class="v r ok">0 %</td><td class="v r ok">95,5 %</td><td class="v r bad">37,8 %</td></tr>
            <tr><td class="l">ministral · 14B · lokal</td><td class="v r ok">0 %</td><td class="v r ok">95,5 %</td><td class="v r bad">40,0 %</td></tr>
          </table>
"""

# (Quelle, Foliennummer 1-basiert, Korrekturen)
SLIDES = [
    ("A20", 1, []),  # Zwei von drei selbst gesetzten Grenzen sind erreicht
    ("A20", 2, []),  # Bei der dritten Grenze ist noch Luft
    # F3 «Massstab» und F5 «Was als Nächstes» zusammengelegt zu «Gold muss Gold sein», zwei Punkte:
    # grösser werden und zu 100 % stimmen — als zwei Karten im rechten Kasten, ohne Detailbelege.
    # «Drei» Fragen nach Issue #142 (T-65, offen): SAMW-OOC-03, SKOS-ADV-01, SKOS-IPV-02.
    # F5 entfällt damit ganz, auch «Die Auswahl schlägt die Suche» (13/15) und die Fusszeile.
    ("A20", 3, [
        ('aria-label="Massstab"', 'aria-label="Gold muss Gold sein"'),
        ('<h1>Zuerst muss der <span class="accent">Massstab stimmen</span></h1>',
         '<h1>Gold muss <span class="accent">Gold sein</span></h1>'),
        (re.compile(r'<p class="lead">Die 90,9 Prozent von vorhin.*?</p>'),
         '<p class="lead">Das Gold-Dataset ist der Massstab für jedes Tuning der Pipeline. '
         'Damit das Tuning genauer wird, braucht es zwei Dinge.</p>'),
        # Links nur Titel, Einstieg und das Bild Gold/Bronze; die zwei Punkte stehen rechts.
        (re.compile(r'[ \t]*<div class="learning bad">.*?</div>\n', re.S),
         '          ' + GOLD_IMG + '\n'),
        # Rechts ohne Detailbelege (Rechnung 4,5 Prozentpunkte, Bronze-Beispiel) — nur die zwei Punkte
        # als Karten im Stil der früheren «Nächste Schritte» (.two-big).
        ('<span>80 Testfragen — und was daran hängt</span>', '<span>Was das Gold-Dataset braucht</span>'),
        (re.compile(r'[ \t]*<div class="weigh">.*?\n          </div>\n', re.S),
         '          <div class="two-big">\n'
         '            <div>\n'
         '              <div class="lead-num">1</div>\n'
         '              <div><h3>Grösser werden</h3><p>Mit 80 Testfragen wiegt jede einzelne mehrere '
         'Prozentpunkte. Für ein genaueres Tuning braucht es mehr Testfragen.</p></div>\n'
         '            </div>\n'
         '            <div class="hi">\n'
         '              <div class="lead-num">2</div>\n'
         '              <div><h3>Zu 100 % stimmen</h3><p>Ein falscher Eintrag lässt jede Optimierung in die '
         'falsche Richtung laufen. Bei uns waren drei von 80 Testfragen eher Bronze als Gold.</p></div>\n'
         '            </div>\n'
         '          </div>\n'),
    ]),
    # Lokale Modelle: die Qualität ist da — getauscht mit F5, kommt jetzt zuletzt.
    # Spalten = die drei Grenzen, gleiche Begriffe und Reihenfolge wie F1; «Protokoll eingehalten»
    # (Protokolltreue, eine Diagnosegrösse, keine Grenze) fällt weg. Werte: Runde R04 aus
    # EvalAnalysis/Optimierung/kennzahlen.csv (Branch T-62), halluzination_alle = 0 bei allen fünf.
    ("A20", 4, [
        ("Fünf Modelle durch dieselbe Pipeline. Das beste davon erfindet nichts, hält unser "
         "Ausgabeprotokoll zu hundert Prozent ein — und lehnt weniger richtige Antworten fälschlich "
         "ab als unsere Cloud-Referenz.",
         # Lesart der Tabelle, Spalte für Spalte. «Stärker» gilt nur für gpt-oss und ministral
         # (95,5 % gegenüber 90,9 %); gemma4 und qwen3 liegen darunter. Die Streuung bei
         # «fälschlich abgelehnt» entsteht vollständig nach dem Modellaufruf (suppression_reason
         # R04: Modell lehnt selbst ab, zu wenig Belege, Self-Check) — daher die Vermutung.
         "Fünf Modelle durch dieselbe Pipeline. Erfundene Belege: keines, alle gleich gut. "
         "«Weiss ich nicht» bei fremden Fragen: zwei der vier lokalen Modelle sind stärker als die "
         "Cloud-Referenz. Fälschlich abgelehnt: sehr unterschiedlich — vermutlich, weil jedes Modell "
         "anders mit einer dünnen Grundlage umgeht."),
        # Kasten «Näher dran als gedacht» ganz weg.
        (re.compile(r'[ \t]*<div class="learning">.*?</div>\n', re.S), ""),
        (re.compile(r'[ \t]*<table class="vs">.*?</table>\n', re.S), MODEL_TABLE),
    ]),
]


def split_slides(name: str, html: str) -> tuple[str, list[str], str]:
    """Teilt in Kopf, Folien (<section class="slide ...">, verschachtelte
    <section> innerhalb einer Folie inklusive) und Fuss."""
    main_end = html.rfind("\n", 0, html.find("</main>")) + 1
    slides, pos, head_end = [], 0, None
    while (start := html.find('<section class="slide', pos, main_end)) != -1:
        line_start = html.rfind("\n", 0, start) + 1
        if head_end is None:
            head_end = line_start
        depth, i, end = 0, start, None
        while True:
            nxt_open = html.find("<section", i, main_end)
            nxt_close = html.find("</section>", i, main_end)
            if nxt_close == -1:
                print(f"  Warnung: {name} F{len(slides) + 1} ist nicht geschlossen — endet an </main>")
                end = main_end
                break
            if nxt_open != -1 and nxt_open < nxt_close:
                depth, i = depth + 1, nxt_open + len("<section")
            else:
                depth, i = depth - 1, nxt_close + len("</section>")
                if depth == 0:
                    end = html.find("\n", i) + 1
                    while html.startswith("\n", end) and end < main_end:  # Leerzeile nach der Folie behalten
                        end += 1
                    break
        slides.append(html[line_start:end])
        pos = end
    return html[:head_end], slides, html[pos:]


parsed = {k: split_slides(k, p.read_text(encoding="utf-8")) for k, p in SOURCES.items()}
for k, (_, s, _) in parsed.items():
    print(f"{k}: {len(s)} Folien")

out_slides = []
for src, n, fixes in SLIDES:
    slide = parsed[src][1][n - 1]
    for old, new in fixes:
        if isinstance(old, re.Pattern):
            slide, hits = old.subn(lambda _: new, slide)
            label = old.pattern
        else:
            hits = slide.count(old)
            slide = slide.replace(old, new)
            label = old
        if hits != 1:
            raise SystemExit(f"{src} F{n}: Korrektur trifft {hits}× statt 1×: {label[:60]}")
    slide = slide.replace('<section class="slide active"', '<section class="slide"', 1)
    out_slides.append(slide)
out_slides[0] = out_slides[0].replace('<section class="slide"', '<section class="slide active"', 1)

head, _, tail = parsed["A20"]
if head.count("  </style>") != 1:
    raise SystemExit("A20: </style> nicht eindeutig")
head = head.replace("  </style>", EXTRA_CSS + "  </style>")
deck = head + "".join(out_slides) + tail


# Bilder einbetten wie in build_block2_v4.py: ein relativer Pfad bricht, sobald die Datei
# allein weitergegeben oder in einer Vorschau geöffnet wird.
def embed(m: re.Match) -> str:
    return f'src="data:image/png;base64,{base64.b64encode((BASE / m.group(1)).read_bytes()).decode()}"'


deck = re.sub(r'src="(assets/[^"]+\.png)"', embed, deck)
OUT.write_text(deck, encoding="utf-8")
print(f"Folien: {len(out_slides)} → {OUT.name}")
