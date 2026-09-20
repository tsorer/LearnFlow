"""Baut Block 5 (Fazit & Ausblick) neu — fünf Folien, rund 4:55.

Fünf Fragen, eine pro Folie: Hält es? · Wo ist noch Luft? · Warum nicht sofort? ·
Geht das auch lokal? · Was kommt als Nächstes? Bewusst gestrichen (20.09.): die zwei
wirkungslosen Prüfstufen (zu sehr Innensicht) und der Re-Ranker als eigene Folie — er
steht als Punkt bei den nächsten Schritten. Beides in ../Block5_Notizen.md.

Ablösung von `build_block5.py` (Stand 19.09., 6 Folien): Die Wortsuche hatte dort drei
Folien und ist inzwischen in Block 2 erzählt. Vier Abschnitte: was hält · was wir gelernt
haben · was wir ändern würden · Ausblick.

Sprachregel für diesen Block (Entscheid Niklaus, 20.09.2026): **positiv formulieren** —
nicht, was wir nicht gemacht haben, sondern was sich damit machen lässt. Beispiel Folie 2:
Die Schwellenwerte wurden nie optimiert; das steht als unbenutzter Hebel da, nicht als
Versäumnis. Das «durchgefallene» Ergebnis des ersten Kalibrierungslaufs steht deshalb nicht
auf den Folien, sondern in ../Block5_Notizen.md. Der Kalibrierungslauf hat seit dem
20.09. keine eigene Folie mehr — er steht als Halbsatz im Kasten von Folie 2, damit der
Block weniger Punkte hat.

Bewusst **nicht** enthalten (Entscheid Niklaus, 20.09.2026): die strenge Neuberechnung
der Halluzinationsrate über ausgelieferte Out-of-Corpus-Antworten (2,9 %). Begründung und
Antwort für den Fall einer Nachfrage stehen in ../Block5_Notizen.md.

Ordner (relativ zu dieser Datei):
    ../Archive/Block2_Technischer-Aufbau.html   Vorlage: CSS und Foliennavigation
    ../Block5_Fazit-Ausblick.html               Ergebnis

Belege: Docs/10_Kalibrierungsbericht.md · EvalAnalysis/Optimierung/kennzahlen.csv und
Pipeline-Review.md (T-62-Branch) · ADR-008/009 · GitHub #142, #110, #138, #136.

Aufruf:  python build_block5_v2.py
"""

import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TEMPLATE = BASE / "Archive" / "Block2_Technischer-Aufbau.html"
OUT = BASE / "Block5_Fazit-Ausblick.html"

v1 = TEMPLATE.read_text(encoding="utf-8")
head, rest = v1.split('  <main class="deck"', 1)
tail = rest[rest.index("  </main>") + len("  </main>"):]
head = head.replace("<title>LearnFlow – Technischer Aufbau</title>", "<title>LearnFlow – Fazit &amp; Ausblick</title>")

EXTRA_CSS = """
    /* ── Block 5 ─────────────────────────────────────────────────────── */
    .wrail { display: flex; gap: 6px; margin-bottom: 22px; }
    .wrail span {
      padding: 7px 12px; border-radius: 99px; background: rgba(16, 30, 54, .06); color: #9aa1ac;
      font-size: 13px; font-weight: 780; letter-spacing: .02em; white-space: nowrap;
    }
    .wrail span.done { background: var(--teal-pale); color: var(--teal-dark); }
    .wrail span.on { background: var(--ink); color: var(--white); }

    .learning.bad { border-left-color: var(--coral); }
    .learning.bad strong { color: var(--coral-dark); }
    .learning.aha { border-left-color: var(--amber); }
    .learning.aha strong { color: var(--amber-dark); }

    .panel.center { display: flex; flex-direction: column; justify-content: center; }

    .gates { display: grid; gap: 12px; }
    .gates > div { display: grid; grid-template-columns: 1fr auto 104px; gap: 16px; align-items: center; padding: 16px 18px; border: 1px solid var(--line); border-radius: 16px; background: var(--white); }
    .gates h3 { margin: 0 0 3px; color: var(--ink); font-size: 18.5px; font-weight: 780; }
    .gates small { display: block; color: var(--muted); font-size: 14.5px; font-weight: 640; }
    .gates b { color: var(--teal-dark); font-size: 28px; font-weight: 850; font-variant-numeric: tabular-nums; letter-spacing: -.03em; }
    .gates em { font-style: normal; justify-self: end; padding: 7px 13px; border-radius: 99px; font-size: 14px; font-weight: 820; white-space: nowrap; background: var(--teal-pale); color: var(--teal-dark); }
    .gates .fail { border-color: rgba(214, 90, 74, .55); }
    .gates .fail b { color: var(--coral-dark); }
    .gates .fail em { background: var(--coral-pale); color: var(--coral-dark); }

    .stat { display: grid; gap: 14px; }
    .stat.two { grid-template-columns: 1fr 1fr; }
    .stat > div { padding: 20px 22px; border-radius: 18px; background: var(--paper); }
    .stat b { display: block; color: var(--teal-dark); font-size: 40px; font-weight: 850; letter-spacing: -.045em; line-height: 1; }
    .stat.warn b { color: var(--amber-dark); }
    .stat span { display: block; margin-top: 8px; color: var(--ink); font-size: 17px; font-weight: 760; line-height: 1.35; }
    .stat small { display: block; margin-top: 5px; color: var(--muted); font-size: 14.5px; font-weight: 640; line-height: 1.4; }

    .vs { width: 100%; border-collapse: collapse; }
    .vs th { padding: 0 10px 9px; color: var(--muted); font-size: 12.5px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; text-align: left; }
    .vs th.r, .vs td.r { text-align: right; }
    .vs td { padding: 12px 10px; border-top: 1px solid var(--line); color: var(--text); font-size: 17px; font-weight: 680; white-space: nowrap; }
    .vs td.l { color: var(--muted); font-size: 15.5px; font-weight: 700; }
    .vs td.v { font-variant-numeric: tabular-nums; font-weight: 820; color: var(--ink); }
    .vs td.ok { color: var(--teal-dark); font-weight: 820; }
    .vs td.bad { color: var(--coral-dark); font-weight: 820; }
    .vs tr.hi td { background: var(--teal-pale); }
    .vs tr.hi td.l { color: var(--teal-dark); font-weight: 820; }

    .pipe { display: grid; gap: 9px; }
    .pipe > div { display: grid; grid-template-columns: 34px 1fr auto; gap: 14px; align-items: center; padding: 12px 15px; border: 1px solid var(--line); border-radius: 13px; background: var(--white); }
    .pipe b { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; background: var(--paper); color: var(--muted); font-size: 15px; font-weight: 850; }
    .pipe h3 { margin: 0; color: var(--ink); font-size: 18px; font-weight: 760; }
    .pipe small { display: block; margin-top: 2px; color: var(--muted); font-size: 14.5px; font-weight: 620; }
    .pipe .tag { padding: 6px 11px; border-radius: 99px; background: var(--paper); color: var(--muted); font-size: 13px; font-weight: 800; white-space: nowrap; }
    .pipe .tag.off { background: var(--coral-pale); color: var(--coral-dark); }
    .pipe .tag.on { background: var(--teal-pale); color: var(--teal-dark); }
    .pipe .tag.llm { background: var(--ink); color: var(--white); }

    .listhead { margin: 18px 0 9px; color: var(--muted); font-size: 13px; font-weight: 820; letter-spacing: .1em; text-transform: uppercase; }
    .pipe.done > div { background: transparent; border-style: dashed; }
    .pipe.done h3 { color: var(--muted); font-weight: 700; }
    .pipe.done .tag { background: var(--teal-pale); color: var(--teal-dark); }

    .spot {
      margin-top: 12px; padding: 22px 24px; border-radius: 20px; background: var(--amber-pale);
      box-shadow: inset 6px 0 0 var(--amber);
    }
    .spot .h { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; }
    .spot .h b { color: var(--ink); font-size: 30px; font-weight: 850; letter-spacing: -.035em; }
    .spot .h em { font-style: normal; padding: 8px 15px; border-radius: 99px; background: var(--amber-dark); color: var(--white); font-size: 15px; font-weight: 850; white-space: nowrap; }
    .spot .v { margin-top: 12px; font: 700 17px/1.6 var(--mono); color: var(--amber-dark); }
    .spot .s { margin-top: 8px; color: var(--amber-dark); font-size: 15px; font-weight: 700; opacity: .85; }

    .quote { margin: 0; padding: 20px 22px; border-radius: 16px; background: var(--paper); color: var(--ink); font-size: 18.5px; font-weight: 700; line-height: 1.5; }
    .quote span { display: block; margin-top: 10px; color: var(--muted); font-size: 14.5px; font-weight: 700; }

    .hw { display: grid; grid-template-columns: auto 1fr; gap: 20px; align-items: center; margin-top: 16px; padding: 18px 20px; border-radius: 18px; background: var(--teal-pale); }
    .hw b { color: var(--teal-dark); font-size: 26px; font-weight: 850; letter-spacing: -.03em; white-space: nowrap; }
    .hw b small { display: block; margin-top: 4px; color: var(--teal-dark); font-size: 13px; font-weight: 750; letter-spacing: .04em; text-transform: uppercase; opacity: .8; }
    .hw span { color: var(--teal-dark); font-size: 16px; font-weight: 680; line-height: 1.45; }

    .weigh { display: grid; grid-template-columns: auto 1fr; gap: 18px; align-items: center; padding: 15px 20px; border-radius: 16px; background: var(--paper); }
    .weigh b { color: var(--teal-dark); font-size: 30px; font-weight: 850; letter-spacing: -.04em; white-space: nowrap; }
    .weigh span { color: var(--text); font-size: 16px; font-weight: 660; line-height: 1.4; }

    .defect { margin-top: 16px; padding: 22px 24px 20px; border-radius: 20px; background: var(--coral-pale); box-shadow: inset 6px 0 0 var(--coral); }
    .defect h3 { margin: 0 0 4px; color: var(--coral-dark); font-size: 13px; font-weight: 820; letter-spacing: .1em; text-transform: uppercase; }
    .defect .qq { margin: 0 0 16px; color: var(--ink); font-size: 20px; font-weight: 800; line-height: 1.35; }
    .defect .row { display: grid; grid-template-columns: 158px 1fr; gap: 16px; align-items: baseline; padding: 11px 0; border-top: 1px solid rgba(214, 90, 74, .22); }
    .defect .row b { color: var(--coral-dark); font-size: 13.5px; font-weight: 820; letter-spacing: .06em; text-transform: uppercase; }
    .defect .row span { color: var(--ink); font-size: 18px; font-weight: 740; line-height: 1.35; }
    .defect .row.ok b { color: var(--teal-dark); }
    .defect .row.ok span { color: var(--teal-dark); }
    .defect .foot { margin-top: 14px; padding-top: 13px; border-top: 1px solid rgba(214, 90, 74, .22); color: var(--coral-dark); font-size: 15.5px; font-weight: 700; line-height: 1.45; }

    .two-big { display: grid; gap: 16px; }
    .two-big > div { display: grid; grid-template-columns: 156px 1fr; gap: 20px; align-items: center; padding: 20px 22px; border-radius: 20px; background: var(--white); border: 1px solid var(--line); }
    .two-big h3 { margin: 0 0 6px; color: var(--ink); font-size: 22px; font-weight: 850; letter-spacing: -.025em; }
    .two-big p { margin: 0; color: var(--muted); font-size: 16.5px; font-weight: 640; line-height: 1.42; }
    .two-big .lead-num { display: grid; place-items: center; height: 100%; color: var(--teal-dark); font-size: 46px; font-weight: 850; letter-spacing: -.045em; line-height: 1; text-align: center; }
    .two-big .lead-num small { display: block; margin-top: 6px; color: var(--muted); font-size: 14px; font-weight: 700; letter-spacing: 0; }
    .two-big > div.hi { background: #fdf6e6; border-color: rgba(214, 160, 60, .45); }
    .medals { width: 156px; height: 112px; display: block; }
    .medals text { font: 800 12px Inter, sans-serif; text-anchor: middle; letter-spacing: .04em; text-transform: uppercase; }

    .next { display: grid; gap: 12px; counter-reset: n; }
    .next > div { display: grid; grid-template-columns: 38px 1fr; gap: 16px; align-items: start; padding: 15px 18px; border: 1px solid var(--line); border-radius: 16px; background: var(--white); }
    .next > div::before { counter-increment: n; content: counter(n); display: grid; place-items: center; width: 32px; height: 32px; border-radius: 10px; background: var(--ink); color: var(--white); font-size: 15px; font-weight: 850; }
    .next h3 { margin: 0 0 3px; color: var(--ink); font-size: 18px; font-weight: 800; }
    .next p { margin: 0; color: var(--muted); font-size: 15.5px; font-weight: 640; line-height: 1.4; }

    .close { display: grid; gap: 14px; }
    .close > div { padding: 20px 22px; border-radius: 18px; background: var(--white); border: 1px solid var(--line); }
    .close h3 { margin: 0 0 5px; color: var(--muted); font-size: 13px; font-weight: 820; letter-spacing: .1em; text-transform: uppercase; }
    .close p { margin: 0; color: var(--ink); font-size: 19px; font-weight: 740; line-height: 1.4; }
    .close > div.hi { background: var(--teal-pale); border-color: transparent; }
    .close > div.hi h3 { color: var(--teal-dark); }
    .close > div.hi p { color: var(--teal-dark); }
"""
marker = "\n    @media (prefers-reduced-motion: reduce)"
assert head.count(marker) == 1
head = head.replace(marker, EXTRA_CSS + marker)

PARTS = ["Was hält", "Was wir gelernt haben", "Ausblick"]


def rail(current: int) -> str:
    spans = []
    for i, name in enumerate(PARTS, 1):
        cls = "on" if i == current else ("done" if i < current else "")
        spans.append(f'<span class="{cls}">{name}</span>')
    return '<div class="wrail">' + "".join(spans) + "</div>"


def slide(label: str, story: str, panel: str, part: int = 0) -> str:
    return f"""
    <section class="slide" aria-label="{label}">
      <header class="topbar">
        <div class="brand"><span class="brand-mark" aria-hidden="true">LF</span><span>LearnFlow</span></div>
        <div class="context" data-title="Fazit &amp; Ausblick"></div>
      </header>
      <div class="content">
        <div class="story">
          {rail(part) if part else ""}
          {story}
        </div>
        <div class="panel center">
          {panel}
        </div>
      </div>
      <div class="page-number"></div>
    </section>
"""


S = []

# ── Was hält ─────────────────────────────────────────────────────────────
S.append(slide("Zwei von drei",
    """<div class="eyebrow">Fazit</div>
          <h1>Zwei von drei selbst gesetzten Grenzen <span class="accent">sind erreicht</span></h1>
          <p class="lead">Die drei Grenzen haben wir uns zu Beginn gegeben, lange vor der ersten Messung: nichts erfinden, ablehnen was nicht drinsteht, antworten was drinsteht. Hier das Ergebnis des letzten Laufs mit dem Referenzmodell.</p>
          <div class="learning">
            <strong>Das Versprechen hält</strong>
            Keine Antwort ohne Beleg: In keinem Lauf und bei keinem der fünf getesteten Modelle hat das System je eine Quelle erfunden.
          </div>""",
    """<div class="panel-label"><span>Eval-Lauf 16.09. · gpt-4o-mini</span><span class="status">80 Fragen</span></div>
          <div class="gates">
            <div><div><h3>Nichts erfinden</h3><small>erfundene Belege · Grenze: 0 %</small></div><b>0 %</b><em>erreicht</em></div>
            <div><div><h3>Ablehnen, was nicht drinsteht</h3><small>«Weiss ich nicht» bei fremden Fragen · Grenze: ≥ 90 %</small></div><b>90,9 %</b><em>erreicht</em></div>
            <div class="fail"><div><h3>Antworten, was drinsteht</h3><small>fälschlich abgelehnt · Grenze: ≤ 15 %</small></div><b>22,2 %</b><em>noch offen</em></div>
          </div>""",
    part=1))

# ── Was wir gelernt haben ────────────────────────────────────────────────
S.append(slide("Zwischenstand",
    """<div class="eyebrow">Optimierung und Potenzial</div>
          <h1>Bei der dritten Grenze ist <span class="accent">noch Luft</span></h1>
          <p class="lead">Der Wert ist von 31,1 auf 22,2 Prozent gefallen. Gedreht haben wir dabei am Prompt und an der Belegprüfung — an den Schwellenwerten selbst nie. Die drei Zahlen, ab denen unterdrückt wird, sind Schätzungen vom ersten Tag.</p>
          <div class="learning aha">
            <strong>Das Potenzial — und das Werkzeug dafür</strong>
            Die naheliegendste Stellschraube ist also noch unbenutzt. Inzwischen muss sie auch niemand mehr schätzen: Ein Lauf rechnet tausende Kombinationen auf gespeicherten Suchergebnissen durch — ohne Modellaufruf — und schlägt Werte vor, die sich nachrechnen lassen.
          </div>""",
    """<div class="panel-label"><span>Woran wir gedreht haben — und woran nicht</span></div>
          <div class="stat">
            <div><b>31,1 → 22,2 %</b><span>fälschlich abgelehnte Antworten, vorher und nachher</span><small>gemessen an denselben 80 Testfragen</small></div>
          </div>
          <p class="listhead">Was wir dafür verändert haben</p>
          <div class="pipe done">
            <div><b>1</b><div><h3>Belegprüfung feiner schneiden</h3></div><span class="tag">gebracht</span></div>
            <div><b>2</b><div><h3>Prompt schärfen</h3></div><span class="tag">gebracht</span></div>
          </div>
          <div class="spot">
            <div class="h"><b>Die Schwellenwerte</b><em>nie angefasst</em></div>
            <div class="v">Ähnlichkeit 0,35 · Fundlage 0,40 · Belege 0,50</div>
            <div class="s">Startwerte vom ersten Tag — geschätzt, nie nachgerechnet.</div>
          </div>""",
    part=2))

S.append(slide("Massstab",
    """<div class="eyebrow">Was wir gelernt haben</div>
          <h1>Zuerst muss der <span class="accent">Massstab stimmen</span></h1>
          <p class="lead">Die 90,9 Prozent von vorhin heissen: 20 von 22 Fragen richtig abgelehnt. Zwei Fragen anders beantwortet — und wir liegen unter der Grenze. So fein lässt sich mit 80 Fragen nicht steuern.</p>
          <div class="learning bad">
            <strong>Und eine falsche Frage wiegt doppelt</strong>
            Steht ein Eintrag falsch im Gold-Dataset, misst man dauerhaft gegen die falsche Erwartung. Genau das ist uns passiert: Die Pipeline hat richtig geantwortet — und wurde dafür als Fehler gezählt.
          </div>""",
    """<div class="panel-label"><span>80 Testfragen — und was daran hängt</span></div>
          <div class="weigh"><b>20 von 22</b><span>Fragen ausserhalb des Korpus richtig abgelehnt — das sind die 90,9 % von vorhin. Eine Frage mehr oder weniger: 4,5 Prozentpunkte.</span></div>
          <div class="defect">
            <h3>Eine dieser Fragen stimmt nicht</h3>
            <p class="qq">«Innert welcher Frist müssen schwerwiegende unerwünschte Ereignisse gemeldet werden?»</p>
            <div class="row"><b>Das Gold sagt</b><span>Steht nicht im Korpus → muss «Weiss ich nicht» antworten</span></div>
            <div class="row ok"><b>Im Leitfaden steht</b><span>Die Frist — schwarz auf weiss</span></div>
            <div class="foot">Die Pipeline hat richtig geantwortet und wurde dafür als Fehler gezählt. Drei solche Einträge haben wir gefunden — nach der Abnahme prüft niemand mehr gegen die Quelle.</div>
          </div>""",
    part=2))

# ── Ausblick ─────────────────────────────────────────────────────────────
S.append(slide("Lokale Modelle",
    """<div class="eyebrow">Ausblick</div>
          <h1>Lokale Modelle: <span class="accent">die Qualität ist da</span></h1>
          <p class="lead">Fünf Modelle durch dieselbe Pipeline. Das beste davon erfindet nichts, hält unser Ausgabeprotokoll zu hundert Prozent ein — und lehnt weniger richtige Antworten fälschlich ab als unsere Cloud-Referenz.</p>
          <div class="learning">
            <strong>Näher dran als gedacht</strong>
            Bei der Ablehnungsquote fehlt gemma4 genau eine Frage von 22. Zwei seiner Fehler waren ausserdem unsere: Antworten, die an einem zu tief gesetzten Token-Limit abgeschnitten wurden.
          </div>""",
    """<div class="panel-label"><span>Fünf Modelle, gleiche Pipeline</span><span class="status">dieselben 80 Fragen</span></div>
          <table class="vs">
            <tr><th>Modell</th><th class="r">lehnt fremde<br>Fragen ab</th><th class="r">lehnt richtige<br>fälschlich ab</th><th class="r">Protokoll<br>eingehalten</th></tr>
            <tr><td class="l">gpt-4o-mini · Cloud-Referenz</td><td class="v r ok">90,9 %</td><td class="v r bad">22,2 %</td><td class="v r">93 %</td></tr>
            <tr class="hi"><td class="l">gemma4 · 26B · lokal</td><td class="v r">86,4 %</td><td class="v r ok">11,1 %</td><td class="v r ok">100 %</td></tr>
            <tr><td class="l">qwen3 · 8B · lokal</td><td class="v r bad">68,2 %</td><td class="v r ok">6,7 %</td><td class="v r">97 %</td></tr>
            <tr><td class="l">gpt-oss · 20B · lokal</td><td class="v r ok">95,5 %</td><td class="v r bad">37,8 %</td><td class="v r bad">81 %</td></tr>
            <tr><td class="l">ministral · 14B · lokal</td><td class="v r ok">95,5 %</td><td class="v r bad">40,0 %</td><td class="v r">91 %</td></tr>
          </table>
          <div class="hw"><b>24–48 GB<small>Grafikspeicher</small></b><span>Gemessen haben wir bewusst auf einer 8-GB-Karte — da läuft ein 18-GB-Modell teilweise auf der CPU. Mit einer passenden Workstation, Grössenordnung 3000 bis 6000 Franken, fällt dieser Engpass weg.</span></div>""",
    part=3))

S.append(slide("Was als Nächstes",
    """<div class="eyebrow">Ausblick</div>
          <h1>Erst der Massstab, <span class="accent">dann der grösste Hebel</span></h1>
          <p class="lead">Zwei Dinge stehen als Nächstes an. Beide sind messbar, und für beide liegt die Vorarbeit schon da.</p>
          <div class="learning">
            <strong>Und das Versprechen von Anfang an?</strong>
            Keine Antwort ohne Beleg — das hält. Was wir dazugelernt haben: Der Beleg dafür, dass es hält, ist die eigentliche Arbeit.
          </div>""",
    """<div class="panel-label"><span>Nächste Schritte</span></div>
          <div class="two-big">
            <div class="hi">
              <svg class="medals" viewBox="0 0 132 96" role="img" aria-label="Eine Goldmedaille und eine Bronzemedaille nebeneinander"><path d="M22 8 L34 8 L46 34 L34 38 Z" fill="#c9ced6"/><path d="M52 8 L40 8 L28 34 L40 38 Z" fill="#dde1e7"/><circle cx="37" cy="56" r="26" fill="#e3b04b"/><circle cx="37" cy="56" r="19" fill="#f0cb7d"/><path d="M86 8 L98 8 L110 34 L98 38 Z" fill="#c9ced6"/><path d="M116 8 L104 8 L92 34 L104 38 Z" fill="#dde1e7"/><circle cx="101" cy="56" r="26" fill="#a9713f"/><circle cx="101" cy="56" r="19" fill="#c08c5c"/><text x="37" y="94" fill="#8a6a1f">Gold</text><text x="101" y="94" fill="#8a5a33">Bronze</text></svg>
              <div><h3>Gold muss Gold sein</h3><p>Mehr Testfragen — und jede einzelne gegen die Quelle geprüft. Drei unserer Einträge waren Bronze, und im Dataset sieht man das keinem an.</p></div>
            </div>
            <div>
              <div class="lead-num">13/15<small>fehlende Quellen</small></div>
              <div><h3>Die Auswahl schlägt die Suche</h3><p>Fast jede fehlende Quelle lag schon in der Kandidatenliste — nur nicht unter den fünf, die das Modell sieht. Besser auswählen statt besser suchen: bis zu 17 Prozentpunkte.</p></div>
            </div>
          </div>
          <div class="panel-foot" style="margin-top:16px">Dazu, ohne grosse Worte: die Prüfung automatisch bei jeder Änderung, die Konfiguration an einer Stelle statt an fünf — und vor dem Pilot der Wechsel auf den europäischen Anbieter.</div>""",
    part=3))

SLIDES = (
    '  <main class="deck" aria-label="LearnFlow Fazit und Ausblick">\n'
    + "".join(S).replace('<section class="slide"', '<section class="slide active"', 1)
    + "\n"
)
OUT.write_text(head + SLIDES + "  </main>" + tail, encoding="utf-8")
print("Folien:", SLIDES.count('<section class="slide'))


# ── Q1 behält sein Abzeichen aus Block 2 ─────────────────────────────────
Q_CSS = """
    :root { --q1: #2f5bd3; --q2: #8b3fd9; }
    .qb {
      display: inline-flex; align-items: center; gap: .32em; vertical-align: .06em;
      padding: .16em .55em .16em .38em; border-radius: 99px; color: #fff;
      font-size: clamp(16px, .7em, 30px); font-weight: 850; line-height: 1.15; white-space: nowrap;
    }
    .qb.q1 { background: var(--q1); }
    .qb.q2 { background: var(--q2); }
    .qb .qi { display: inline-grid; place-items: center; width: 1.25em; height: 1.25em; border-radius: 50%; background: rgba(255, 255, 255, .22); font-size: .95em; font-weight: 900; }
"""
BADGE = {
    "1": '<span class="qb q1" title="Frage 1 aus Block 2"><span class="qi">§</span>Q1</span>',
    "2": '<span class="qb q2" title="Frage 2 aus Block 2"><span class="qi">·</span>Q2</span>',
}

html = OUT.read_text(encoding="utf-8")
html = html.replace(marker, Q_CSS + marker)
head_part, main_part = html.split('  <main class="deck"', 1)
main_part = re.sub(r"(?<=>)[^<>]+(?=<)",
                   lambda m: re.sub(r"\bQ([12])\b", lambda q: BADGE[q.group(1)], m.group(0)),
                   main_part)
OUT.write_text(head_part + '  <main class="deck"' + main_part, encoding="utf-8")
print("geschrieben:", OUT)
