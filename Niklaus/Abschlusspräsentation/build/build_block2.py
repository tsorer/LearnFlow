"""Baut Block 2 (Technischer Aufbau) — eine Aussage pro Folie.

Ordner (relativ zu dieser Datei):
    ../Archive/Block2_Technischer-Aufbau.html   Vorlage: CSS, Navigation und vier Folien
    ../Archive/Block2_Technischer-Aufbau_v2.html   Ergebnis
    ../assets/                                  Bilder (wird bei Bedarf aus Archive kopiert)

Aufruf:  python build_block2.py
"""

import re
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
TEMPLATE = BASE / "Archive" / "Block2_Technischer-Aufbau.html"
DIR = BASE / "Archive"          # alte Stände bleiben im Archiv
OUT = DIR / "Block2_Technischer-Aufbau_v2.html"

# Bilder müssen neben dem Ergebnis liegen, sonst lädt das Lara-Portrait nicht.
if not (DIR / "assets").exists() and (BASE / "Archive" / "assets").exists():
    shutil.copytree(BASE / "Archive" / "assets", DIR / "assets")

v1 = TEMPLATE.read_text(encoding="utf-8")

head, rest = v1.split('  <main class="deck"', 1)
tail = rest[rest.index("  </main>") + len("  </main>"):]


def v1_section(label: str) -> str:
    m = re.search(rf'    <section class="slide[^"]*" aria-label="{re.escape(label)}">.*?</section>', v1, re.S)
    assert m, label
    return m.group(0).replace('class="slide active"', 'class="slide"')


EXTRA_CSS = """
    /* ── v2: eine Aussage pro Folie ──────────────────────────────────── */
    .prail { display: flex; gap: 6px; margin-bottom: 26px; }
    .prail span {
      padding: 7px 12px; border-radius: 99px; background: rgba(16, 30, 54, .06); color: #9aa1ac;
      font-size: 13px; font-weight: 780; letter-spacing: .02em; white-space: nowrap;
    }
    .prail span.done { background: var(--teal-pale); color: var(--teal-dark); }
    .prail span.on { background: var(--ink); color: var(--white); }

    .big-lead { max-width: 600px; margin: 26px 0 0; color: #566173; font-size: 22px; line-height: 1.45; letter-spacing: -.014em; }
    .take {
      max-width: 620px; margin-top: 26px; padding: 16px 0 16px 22px; border-left: 4px solid var(--amber);
      color: var(--ink); font-size: 20px; font-weight: 700; line-height: 1.4;
    }
    .take.good { border-left-color: var(--teal); }
    .take.bad { border-left-color: var(--coral); }

    .panel.center { display: flex; flex-direction: column; justify-content: center; }

    .bigpair { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    .bigcard { padding: 30px 28px 26px; border-radius: 24px; background: var(--paper); }
    .bigcard .q { color: var(--muted); font-size: 15px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
    .bigcard .n { margin: 14px 0 10px; color: var(--teal-dark); font-size: 76px; font-weight: 850; letter-spacing: -.055em; line-height: .95; }
    .bigcard .t { color: var(--ink); font-size: 19px; font-weight: 700; line-height: 1.35; }
    .bigcard .s { margin-top: 6px; color: var(--muted); font-size: 16px; font-weight: 620; line-height: 1.4; }
    .bigcard.ok { background: var(--teal-pale); }
    .bigcard.warn { background: var(--amber-pale); }
    .bigcard.warn .n { color: var(--amber-dark); }
    .bigcard.bad { background: var(--coral-pale); }
    .bigcard.bad .n { color: var(--coral-dark); }

    .xform { display: grid; gap: 14px; }
    .xrow { display: grid; grid-template-columns: 150px 1fr; gap: 16px; align-items: center; }
    .xrow .l { color: var(--muted); font-size: 14px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; line-height: 1.3; }
    .xarrow { padding-left: 166px; color: var(--muted); font-size: 22px; line-height: .6; }
    .chip {
      display: inline-block; margin: 3px 4px 3px 0; padding: 8px 12px; border-radius: 10px; vertical-align: top;
      background: var(--white); border: 1px solid var(--line); color: var(--ink); font-size: 19px; font-weight: 720;
    }
    .chip small { display: block; margin-top: 2px; font-size: 12.5px; font-weight: 650; color: var(--muted); text-align: center; text-decoration: none; }
    .chip.out { color: #a3a9b2; text-decoration: line-through; border-style: dashed; background: transparent; }
    .chip.ok { background: var(--teal-pale); border-color: transparent; color: var(--teal-dark); }
    .chip.ok small { color: var(--teal-dark); }
    .chip.bad { background: var(--coral-pale); border-color: transparent; color: var(--coral-dark); }
    .chip.bad small { color: var(--coral-dark); }
    .chip.warn { background: var(--amber-pale); border-color: transparent; color: var(--amber-dark); }
    .chip.warn small { color: var(--amber-dark); }
    .chip.hl { outline: 3px solid var(--coral); outline-offset: 2px; }

    .vecdemo { display: grid; gap: 22px; }
    .vecrow { display: grid; grid-template-columns: 1fr 44px 1.2fr; gap: 12px; align-items: center; }
    .vecrow .txt { padding: 16px 18px; border-radius: 14px; background: var(--ink); color: var(--white); font-size: 19px; font-weight: 700; line-height: 1.3; }
    .vecrow .txt.doc { background: var(--white); color: var(--ink); border: 1px solid var(--line); }
    .vecrow .arr { color: var(--muted); font-size: 28px; text-align: center; }
    .vecrow .nums { padding: 14px 16px; border-radius: 14px; background: var(--paper); font: 700 16px/1.45 var(--mono); color: var(--text); }
    .vecrow .nums small { display: block; font-family: Inter, sans-serif; font-size: 13px; font-weight: 700; color: var(--muted); }
    .near { padding: 16px 20px; border-radius: 16px; background: var(--teal-pale); color: var(--teal-dark); font-size: 19px; font-weight: 760; text-align: center; }
    .vecnote { margin-top: 14px; color: var(--muted); font-size: 14px; font-weight: 620; text-align: center; }

    .toplist { width: 100%; border-collapse: collapse; }
    .toplist td { padding: 12px 10px; border-top: 1px solid var(--line); font-size: 18px; font-weight: 650; color: var(--text); }
    .toplist td.r { width: 52px; color: var(--muted); font-weight: 800; font-variant-numeric: tabular-nums; }
    .toplist td.v { text-align: right; color: var(--muted); font-size: 16px; }
    .toplist tr.gt td { background: var(--teal-pale); color: var(--teal-dark); font-weight: 820; }
    .toplist tr.gt td.v { color: var(--teal-dark); }
    .toplist tr.cut td { border-bottom: 3px solid var(--ink); }
    .toplist tr.out td { color: #a3a9b2; }
    .doc { display: inline-block; padding: 3px 10px; border-radius: 8px; font-size: 15px; font-weight: 800; white-space: nowrap; }
    .doc.obv { background: var(--teal-pale); color: var(--teal-dark); }
    .doc.fremd { background: var(--coral-pale); color: var(--coral-dark); }
    .toplist tr.gt .doc.obv { background: var(--white); }
    .listhead { margin: 0 0 10px; color: var(--muted); font-size: 14px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
    .cutnote { margin-top: 12px; color: var(--muted); font-size: 15px; font-weight: 650; }

    .law {
      margin: 0; padding: 22px 24px; border-radius: 18px; background: var(--white); border: 1px solid var(--line);
      font: 600 19px/1.6 var(--mono); color: var(--muted); white-space: pre-wrap;
    }
    .law .hit { background: var(--teal-pale); color: var(--teal-dark); font-weight: 800; padding: 0 4px; border-radius: 5px; }
    .law .ans { color: var(--ink); font-weight: 800; background: #fcf3dc; padding: 0 4px; border-radius: 5px; }
    .law-src { margin-top: 14px; color: var(--muted); font-size: 16px; font-weight: 650; }
    .absent { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; align-items: center; }
    .absent em { font-style: normal; color: var(--muted); font-size: 17px; font-weight: 700; }
    .absent span { padding: 8px 14px; border-radius: 10px; background: var(--coral-pale); color: var(--coral-dark); font-size: 18px; font-weight: 780; text-decoration: line-through; }

    .mix { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .mixcol { padding: 18px; border-radius: 18px; background: var(--paper); }
    .mixrow { display: flex; justify-content: space-between; padding: 9px 0; border-bottom: 1px solid rgba(16,30,54,.08); font-size: 18px; font-weight: 700; color: var(--ink); }
    .mixrow:last-child { border-bottom: 0; }
    .mixrow span:last-child { color: var(--teal-dark); font-variant-numeric: tabular-nums; }
    .mixrow.win span { color: var(--teal-dark); font-weight: 850; }
    .mixsum { margin-top: 18px; padding: 18px 20px; border-radius: 16px; background: var(--ink); color: var(--white); font-size: 19px; font-weight: 700; line-height: 1.45; }
    .mixsum b { color: #a8e7e2; }


    .mixq { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
    .mixq section { padding: 18px 18px 16px; border-radius: 20px; background: var(--paper); display: flex; flex-direction: column; }
    .mixq h2 { margin: 0 0 12px; font-size: 18px; }
    .mrow { display: grid; grid-template-columns: 30px 1fr auto; gap: 10px; align-items: center; padding: 10px 10px; border-radius: 12px; }
    .mrow + .mrow { margin-top: 6px; }
    .mrow .r { color: var(--muted); font-size: 18px; font-weight: 850; text-align: center; }
    .mrow.gt { background: var(--teal-pale); outline: 2px solid var(--teal); }
    .mrow.gt .doc.obv { background: var(--white); }
    .src2 { display: flex; gap: 5px; }
    .src2 span {
      display: grid; place-items: center; width: 28px; height: 28px; border-radius: 8px;
      font-size: 14px; font-weight: 850;
    }
    .src2 .b { background: var(--ink); color: var(--white); }
    .src2 .w { background: var(--white); color: var(--ink); border: 2px solid var(--ink); }
    .src2 .none { background: transparent; border: 2px dashed #c9c4b8; color: transparent; }
    .mixfoot { margin-top: auto; padding-top: 14px; color: var(--ink); font-size: 16.5px; font-weight: 700; line-height: 1.4; }
    .mixlegend { display: flex; gap: 22px; margin-top: 16px; color: var(--muted); font-size: 15px; font-weight: 700; align-items: center; }
    .mixlegend .src2 span { width: 24px; height: 24px; font-size: 12px; }
    .mixlegend > div { display: flex; gap: 8px; align-items: center; }

    .evalcats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0 0 78px; }
    .evalcats div { padding: 12px 14px; border-radius: 14px; background: var(--paper); }
    .evalcats b { display: block; color: var(--teal-dark); font-size: 30px; font-weight: 850; letter-spacing: -.04em; line-height: 1; }
    .evalcats span { display: block; margin-top: 5px; color: var(--ink); font-size: 16px; font-weight: 780; }
    .evalcats small { display: block; margin-top: 2px; color: var(--muted); font-size: 14px; font-weight: 620; line-height: 1.3; }
    .gates { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 10px 0 0 78px; }
    .gates div { padding: 12px 14px; border-radius: 14px; background: var(--white); border: 2px solid var(--ink); }
    .gates span { display: block; color: var(--ink); font-size: 15.5px; font-weight: 780; line-height: 1.3; }
    .gates b { display: block; margin-top: 6px; color: var(--ink); font-size: 26px; font-weight: 850; letter-spacing: -.03em; }
    .gates small { display: block; color: var(--muted); font-size: 13.5px; font-weight: 650; }

    .larasees { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .larasees div { padding: 12px 14px; border-radius: 14px; font-size: 16px; font-weight: 780; white-space: nowrap; }
    .larasees .q1s { background: var(--teal-pale); color: var(--teal-dark); }
    .larasees .q2s { background: var(--amber-pale); color: var(--amber-dark); }
    .bars { display: grid; gap: 10px; }
    /* Stufe 1: selbsterklärende Tabelle */

    .formula {
      max-width: 600px; margin-top: 22px; padding: 14px 18px; border-radius: 14px; background: var(--white);
      border: 1px solid var(--line); color: var(--text); font: 650 17px/1.55 var(--mono);
    }
    .formula span { color: var(--teal-dark); font-weight: 850; }
    .fund { width: 100%; border-collapse: separate; border-spacing: 0 6px; }
    .fund th { padding: 0 10px 4px; color: var(--muted); font-size: 13px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; text-align: right; vertical-align: bottom; }
    .fund th:first-child { text-align: left; }
    .fund th.what-if { color: var(--coral-dark); }
    .fund td { padding: 10px 10px; background: var(--paper); text-align: right; vertical-align: middle; }
    .fund td:first-child { text-align: left; border-radius: 12px 0 0 12px; }
    .fund td:last-child { border-radius: 0 12px 12px 0; }
    .fund td.lbl b { display: block; color: var(--ink); font-size: 17px; font-weight: 800; }
    .fund td.lbl small { display: block; margin-top: 2px; color: var(--muted); font-size: 14px; font-weight: 620; line-height: 1.3; }
    .fund td.lbl i { font-style: normal; color: var(--teal-dark); font-weight: 800; }
    .fund td.v { width: 122px; }
    .fund td.v b { display: block; color: var(--ink); font-size: 20px; font-weight: 820; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .fund td.v small { display: block; margin-top: 2px; color: var(--muted); font-size: 13px; font-weight: 650; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .fund td.v.low b { color: var(--coral-dark); }
    .fund td.wi { background: #fbf1ef; }
    .fund tr.sum td { background: var(--ink); }
    .fund tr.sum td.lbl b { color: var(--white); }
    .fund tr.sum td.lbl small { color: #c9d3e2; }
    .fund tr.sum td.v b { color: #a8e7e2; font-size: 24px; }
    .fund tr.sum td.v.no b { color: #ffb4a8; }
    .fund tr.sum td.v small { color: #c9d3e2; }
    .bars.b40 .bar { grid-template-columns: 210px 1fr 60px; }
    .bars.b40 .thr { left: 40%; }
    .bars.b40 .fill.q1 { background: rgba(47, 91, 211, .55); }
    .bars.b40 .fill.q2 { background: rgba(139, 63, 217, .55); }
    .bars.b40 .fill.no { background: rgba(207, 102, 92, .6); }

    .bar { display: grid; grid-template-columns: 190px 1fr 60px; gap: 14px; align-items: center; }
    .bar .track { position: relative; height: 22px; border-radius: 6px; background: var(--paper); }
    .bar .fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 6px; background: rgba(15, 168, 160, .55); }
    .bar .fill.low { background: rgba(207, 102, 92, .55); }
    .bar .thr { position: absolute; top: -5px; bottom: -5px; width: 3px; background: var(--ink); border-radius: 2px; left: 58.33%; }
    .bar .v { font-size: 17px; font-weight: 800; color: var(--ink); text-align: right; font-variant-numeric: tabular-nums; }
    .bars-note { margin-top: 12px; color: var(--muted); font-size: 14px; font-weight: 650; }

    .scale { position: relative; height: 150px; margin: 10px 8px 0; }
    .scale .zones { position: absolute; left: 0; right: 0; top: 50px; height: 34px; display: flex; border-radius: 8px; overflow: hidden; }
    .scale .zone { display: grid; place-items: center; font-size: 13px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }
    .z-bad { background: var(--coral-pale); color: var(--coral-dark); }
    .z-warn { background: var(--amber-pale); color: var(--amber-dark); }
    .z-ok { background: var(--teal-pale); color: var(--teal-dark); }
    .scale .tick { position: absolute; top: 92px; transform: translateX(-50%); color: var(--muted); font-size: 14px; font-weight: 700; }
    .scale .pin { position: absolute; transform: translateX(-50%); text-align: center; font-size: 17px; font-weight: 850; white-space: nowrap; }
    .scale .pin.top { top: 0; }
    .scale .pin.top::after { content: ""; display: block; width: 3px; height: 20px; margin: 4px auto 0; background: currentColor; border-radius: 2px; }
    .scale .pin.bottom { top: 84px; }
    .scale .pin.bottom::before { content: ""; display: block; width: 3px; height: 30px; margin: 0 auto 4px; background: currentColor; border-radius: 2px; }
    .pin.q1 { color: var(--teal-dark); }
    .pin.q2 { color: var(--amber-dark); }

    .calc { display: grid; gap: 10px; }
    .calc div { display: grid; grid-template-columns: 1fr 120px 120px; gap: 10px; padding: 12px 16px; border-radius: 12px; background: var(--paper); font-size: 18px; font-weight: 650; color: var(--text); }
    .calc div b { text-align: right; color: var(--ink); font-weight: 820; font-variant-numeric: tabular-nums; }
    .calc div b.warn { color: var(--amber-dark); }
    .calc div.h { background: transparent; padding: 0 16px; color: var(--muted); font-size: 14px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
    .calc div.h b { color: var(--muted); font-weight: 800; }
    .calc div.sum { background: var(--ink); color: var(--white); }
    .calc div.sum b { color: #a8e7e2; font-size: 22px; }

    .blk { padding: 16px 20px; border-radius: 16px; background: var(--paper); }
    .blk h4 { margin: 0 0 10px; color: var(--muted); font-size: 13px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
    .rules { margin: 0; padding-left: 22px; color: var(--ink); font-size: 19px; font-weight: 680; line-height: 1.55; }
    .ctx { display: grid; gap: 8px; }
    .ctx div { display: grid; grid-template-columns: 44px 150px 1fr; gap: 10px; align-items: baseline; font-size: 17px; font-weight: 620; color: var(--muted); line-height: 1.35; }
    .ctx div b { color: var(--ink); font: 800 17px var(--mono); }
    .ctx div.star, .ctx div.star b { color: var(--teal-dark); font-weight: 780; }
    .ctx div.fremd, .ctx div.fremd b { color: var(--coral-dark); }
    .stack { display: grid; gap: 16px; }

    .ansbox { padding: 22px 24px; border-radius: 18px; background: var(--ink); color: var(--white); font-size: 22px; font-weight: 700; line-height: 1.4; }
    .ansbox small { display: block; margin-bottom: 8px; color: #a8e7e2; font-size: 13px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
    .ansbox .ref { padding: 0 6px; border-radius: 6px; background: rgba(168, 231, 226, .18); color: #a8e7e2; font-family: var(--mono); }

    .seg { padding: 18px 20px; border-radius: 16px; background: var(--white); border: 1px solid var(--line); font-size: 19px; font-weight: 650; line-height: 1.45; color: var(--ink); }
    .seg .ref { padding: 1px 7px; border-radius: 6px; background: var(--teal-pale); color: var(--teal-dark); font: 800 18px var(--mono); }
    .seg-res { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
    .seg-res span { padding: 7px 12px; border-radius: 10px; background: var(--teal-pale); color: var(--teal-dark); font-size: 16px; font-weight: 780; }

    .verdict { display: grid; place-items: center; padding: 30px 20px; border-radius: 20px; font-size: 40px; font-weight: 850; letter-spacing: -.03em; text-align: center; }
    .verdict.ok { background: var(--teal-pale); color: var(--teal-dark); }
    .verdict.skip { background: var(--paper); color: var(--muted); font-size: 28px; font-weight: 760; }
    .verdict small { display: block; margin-top: 8px; font-size: 16px; font-weight: 650; letter-spacing: 0; color: var(--muted); }

    .srcs { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }
    .srcs span { padding: 7px 12px; border-radius: 10px; font-size: 15px; font-weight: 780; background: var(--teal-pale); color: var(--teal-dark); }
    .srcs span.fremd { background: var(--coral-pale); color: var(--coral-dark); }
    .srcs span.cited { outline: 3px solid var(--teal); outline-offset: 1px; }
    .conf { display: inline-block; margin-top: 12px; padding: 7px 14px; border-radius: 99px; font-size: 16px; font-weight: 800; }
    .conf.ok { background: var(--teal-pale); color: var(--teal-dark); }
    .conf.warn { background: var(--amber-pale); color: var(--amber-dark); }

    .insights { display: grid; gap: 14px; }
    .insight { display: grid; grid-template-columns: 130px 1fr; gap: 20px; align-items: center; padding: 20px 22px; border-radius: 18px; background: var(--white); border: 1px solid var(--line); }
    .insight strong { color: var(--teal-dark); font-size: 38px; font-weight: 850; letter-spacing: -.05em; line-height: 1; }
    .insight.warn strong { color: var(--amber-dark); }
    .insight.bad strong { color: var(--coral-dark); }
    .insight h3 { margin: 0 0 5px; color: var(--ink); font-size: 20px; font-weight: 800; }
    .insight p { margin: 0; color: var(--muted); font-size: 16.5px; font-weight: 620; line-height: 1.4; }

    .phases { display: grid; gap: 12px; }
    .phase { display: grid; grid-template-columns: 60px 1fr auto; gap: 18px; align-items: center; padding: 16px 20px; border: 1px solid var(--line); border-radius: 18px; background: var(--white); }
    .phase b { display: grid; place-items: center; width: 50px; height: 50px; border-radius: 14px; background: var(--teal-pale); color: var(--teal-dark); font-size: 21px; font-weight: 850; }
    .phase h3 { margin: 0 0 3px; color: var(--ink); font-size: 21px; font-weight: 800; letter-spacing: -.02em; }
    .phase p { margin: 0; color: var(--muted); font-size: 16.5px; font-weight: 620; line-height: 1.35; }
    .phase .tag { padding: 6px 12px; border-radius: 99px; font-size: 13.5px; font-weight: 800; white-space: nowrap; background: var(--paper); color: var(--muted); }
    .phase .tag.llm { background: var(--ink); color: var(--white); }
    .phase .tag.gate { background: var(--coral-pale); color: var(--coral-dark); }
    .phase.gate { border-left: 5px solid var(--coral); }
    .phase.llm b { background: var(--ink); color: var(--white); }
"""
marker = "\n    @media (prefers-reduced-motion: reduce)"
assert head.count(marker) == 1
head = head.replace(marker, EXTRA_CSS + marker)

PHASES = ["Suchen", "Mischen", "Vorprüfung", "Antworten", "Nachprüfung"]


def rail(current: int) -> str:
    spans = []
    for i, name in enumerate(PHASES, 1):
        cls = "on" if i == current else ("done" if i < current else "")
        spans.append(f'<span class="{cls}">{i} {name}</span>')
    return '<div class="prail">' + "".join(spans) + "</div>"


def slide(label: str, story: str, panel: str, phase: int = 0, center: bool = True) -> str:
    r = rail(phase) if phase else ""
    pcls = "panel center" if center else "panel"
    return f"""
    <section class="slide" aria-label="{label}">
      <header class="topbar">
        <div class="brand"><span class="brand-mark" aria-hidden="true">LF</span><span>LearnFlow</span></div>
        <div class="context" data-title="Technischer Aufbau"></div>
      </header>
      <div class="content">
        <div class="story">
          {r}
          {story}
        </div>
        <div class="{pcls}">
          {panel}
        </div>
      </div>
      <div class="page-number"></div>
    </section>
"""


S = []

S.append(slide("Die richtige Antwort",
    """<div class="eyebrow">Worauf wir hinauswollen</div>
          <h1>Die Antwort steht in der <span class="accent">Ordnungsbussen&shy;verordnung</span></h1>
          <p class="big-lead">Innerorts 6 bis 10 km/h zu schnell kostet 120 Franken. Die Frage ist: Findet die Pipeline diese Zeile – bei beiden Formulierungen?</p>""",
    """<div class="panel-label"><span>OBV · Anhang 1 · Seite 12</span><span class="status">im Korpus</span></div>
          <pre class="law">303. 1. Überschreiten allgemeiner,
fahrzeugbedingter oder signalisierter
Höchstgeschwindigkeit … innerorts

a. um  1– 5 km/h    40
<span class="ans">b. um  6–10 km/h   120</span>
c. um 11–15 km/h   250</pre>
          <div class="law-src">Beträge in Franken. Die Stelle ist einer von 1017 Abschnitten im Korpus.</div>"""))

S.append(slide("Die Pipeline im Überblick",
    """<div class="eyebrow">Die Pipeline im Überblick</div>
          <h1>Erst suchen, dann antworten, <span class="accent">dann prüfen</span></h1>
          <p class="big-lead">Das Sprachmodell antwortet nie frei. Es bekommt nur fünf Abschnitte aus dem Korpus – und die Antwort muss danach Prüfungen bestehen.</p>
          <div class="take good">Scheitert eine Prüfung, sagt LearnFlow «Weiss ich nicht», statt zu raten.</div>""",
    """<div class="panel-label"><span>Fünf Phasen</span><span class="status">höchstens zwei Sprachmodell-Aufrufe</span></div>
          <div class="phases">
            <div class="phase"><b>1</b><div><h3>Suchen</h3><p>Zwei Suchen: nach Bedeutung und nach Wörtern.</p></div><span class="tag">Datenbank</span></div>
            <div class="phase"><b>2</b><div><h3>Mischen</h3><p>Aus zwei Listen wird eine. Nur 5 Abschnitte gehen weiter.</p></div><span class="tag">Rechnung</span></div>
            <div class="phase gate"><b>3</b><div><h3>Vorprüfung</h3><p>Ist genug Passendes gefunden?</p></div><span class="tag gate">kann stoppen</span></div>
            <div class="phase llm"><b>4</b><div><h3>Antworten</h3><p>Das Modell antwortet nur aus den 5 Abschnitten.</p></div><span class="tag llm">Sprachmodell</span></div>
            <div class="phase gate"><b>5</b><div><h3>Nachprüfung</h3><p>Stimmen die Belege? Reicht das Vertrauen?</p></div><span class="tag gate">kann stoppen</span></div>
          </div>"""))

S.append(slide("Bedeutungssuche erklärt",
    """<div class="eyebrow">Phase 1 · Suchen</div>
          <h1>Suche 1: nach <span class="accent">Bedeutung</span></h1>
          <p class="big-lead">Frage und jeder Abschnitt werden in 1536 Zahlen übersetzt. Texte mit ähnlicher Bedeutung bekommen ähnliche Zahlen – auch ohne gemeinsames Wort.</p>
          <div class="take good">Die Bedeutungssuche findet beide – Tippfehler stören sie kaum.</div>""",
    """<div class="panel-label"><span>Text wird zu Zahlen</span><span class="status">Embedding</span></div>
          <div class="vecdemo">
            <div class="vecrow"><div class="txt">«6 km/h zu schnell»</div><div class="arr">→</div><div class="nums"><small>Frage</small>[ 0.03, −0.01, 0.07, … ]</div></div>
            <div class="vecrow"><div class="txt doc">«Überschreiten der Höchst&shy;geschwindigkeit»</div><div class="arr">→</div><div class="nums"><small>Abschnitt im Gesetz</small>[ 0.03, −0.02, 0.06, … ]</div></div>
            <div class="near">Ähnliche Zahlen = ähnliche Bedeutung → Treffer</div>
          </div>
          <div class="vecnote">Zahlen zur Veranschaulichung</div>
          <p class="listhead" style="margin-top:22px">Wo steht die richtige Stelle? · von 1017 Abschnitten</p>
          <div class="bigpair">
            <div class="bigcard ok" style="padding:18px 22px"><div class="q">Q1 · formal</div><div class="n" style="font-size:52px; margin:8px 0 0">Platz 1</div></div>
            <div class="bigcard ok" style="padding:18px 22px"><div class="q">Q2 · Alltag</div><div class="n" style="font-size:52px; margin:8px 0 0">Platz 2</div></div>
          </div>""",
    phase=1))

S.append(slide("Wortsuche Q1",
    """<div class="eyebrow">Phase 1 · Suchen · Q1</div>
          <h1>Suche 2: nach <span class="accent">Wörtern</span></h1>
          <p class="big-lead">Die Wortsuche sucht die Wörter selbst. Dafür wird die Frage zerlegt: Füllwörter raus, Wörter auf ihren Stamm gekürzt. Stark bei exakten Fachbegriffen – dafür haben wir sie eingebaut.</p>""",
    """<div class="panel-label"><span>Q1 · Suchbegriffe</span><span class="status">Treffer im Korpus</span></div>
          <div class="xform">
            <div class="xrow"><span class="l">Frage</span><div><span class="chip out">Ich</span><span class="chip">fahre</span><span class="chip">innerorts</span><span class="chip out hl">6</span><span class="chip hl">Km/h</span><span class="chip out">zu</span><span class="chip">schnell</span><span class="chip out">wie</span><span class="chip">hoch</span><span class="chip out">ist</span><span class="chip out">die</span><span class="chip">Busse</span></div></div>
            <div class="xarrow">↓</div>
            <div class="xrow"><span class="l">Treffer</span><div><span class="chip ok">fahr<small>15</small></span><span class="chip ok">innerort<small>5</small></span><span class="chip warn">km<small>2</small></span><span class="chip ok">schnell<small>4</small></span><span class="chip ok">hoch<small>13</small></span><span class="chip ok">buss<small>1</small></span></div></div>
          </div>
          <div class="take bad" style="margin-top:30px; max-width:none">Die präzisesten Angaben fallen weg: «6» ist zu kurz, «Km/h» wird am Schrägstrich zerrissen. Im Gesetz steht «km/h» als ein Wort – 5 Treffer, darunter die richtige Stelle.</div>""",
    phase=1))

S.append(slide("Wortsuche Q2",
    """<div class="eyebrow">Phase 1 · Suchen · Q2</div>
          <h1>Q2 sucht praktisch nur nach <span class="accent">«wurde»</span></h1>
          <p class="big-lead">«wurde» steht nicht auf der Füllwort-Liste – und kommt in jedem Dokument des Korpus vor. Die Tippfehler treffen gar nichts.</p>""",
    """<div class="panel-label"><span>Q2 · Suchbegriffe</span><span class="status">Treffer im Korpus</span></div>
          <div class="xform">
            <div class="xrow"><span class="l">Frage</span><div><span class="chip out">Ich</span><span class="chip">wurde</span><span class="chip">innerorts</span><span class="chip out">mit</span><span class="chip out">6</span><span class="chip">zuschnell</span><span class="chip">gebliztz</span><span class="chip out">was</span><span class="chip">kostet</span><span class="chip out">mich</span><span class="chip out">das</span></div></div>
            <div class="xarrow">↓</div>
            <div class="xrow"><span class="l">Treffer</span><div><span class="chip bad">wurd<small>161</small></span><span class="chip ok">innerort<small>5</small></span><span class="chip warn">zuschnell<small>0</small></span><span class="chip warn">gebliztz<small>0</small></span><span class="chip warn">kostet<small>0</small></span></div></div>
          </div>
          <div class="take bad" style="margin-top:30px; max-width:none">161 von 1017 Abschnitten enthalten «wurde» – 120 davon im EU AI Act.</div>""",
    phase=1))

S.append(slide("Warum die Wortsuche danebenliegt",
    """<div class="eyebrow">Phase 1 · Suchen</div>
          <h1>Das Gesetz spricht eine <span class="accent">andere Sprache</span></h1>
          <p class="big-lead">Selbst ohne Tippfehler: In der richtigen Stelle steht weder «Busse» noch «schnell». Frage und Antwort teilen nur ein Wort.</p>""",
    """<div class="panel-label"><span>Die richtige Stelle</span><span class="status">OBV S. 12 · Teil 2</span></div>
          <pre class="law">303. 1. Überschreiten allgemeiner,
fahrzeugbedingter oder signalisierter
Höchstgeschwindigkeit … <span class="hit">innerorts</span>

a. um  1– 5 km/h    40
b. um  6–10 km/h   120
c. um 11–15 km/h   250</pre>
          <div class="absent"><em>kommt nicht vor:</em><span>Busse</span><span>schnell</span><span>kostet</span><span>geblitzt</span></div>""",
    phase=1))

S.append(slide("Wortsuche Ergebnis",
    """<div class="eyebrow">Phase 1 · Suchen</div>
          <h1>Die Wortsuche <span class="accent">findet keine der beiden</span></h1>
          <p class="big-lead">Jede Suche gibt nur ihre besten 20 Abschnitte weiter. Die richtige Stelle ist bei keiner Frage dabei.</p>""",
    """<div class="panel-label"><span>Wo steht die richtige Stelle?</span><span class="status">Wortsuche · Top 20</span></div>
          <div class="bigpair">
            <div class="bigcard warn"><div class="q">Q1 · formal</div><div class="n">Platz 22</div><div class="t">zwei Plätze zu tief</div><div class="s">In den Top 20: fast nur OBV – aber nicht die richtige Stelle.</div></div>
            <div class="bigcard bad"><div class="q">Q2 · Alltag</div><div class="n">Platz 119</div><div class="t">weit ausserhalb</div><div class="s">In den Top 20: kein einziger OBV-Abschnitt – nur EU AI Act, SKOS, SAMW.</div></div>
          </div>""",
    phase=1))

S.append(slide("Mischen",
    """<div class="eyebrow">Phase 2 · Mischen</div>
          <h1>Aus zwei Listen werden <span class="accent">fünf Abschnitte</span></h1>
          <p class="big-lead">Jede Liste vergibt Punkte nach Platz – nicht nach Ähnlichkeit. Wer in beiden Listen steht, bekommt doppelt Punkte und zieht vorbei.</p>
          <div class="take">Nur die ersten fünf gehen ans Modell.</div>""",
    """<div class="panel-label"><span>Die fünf Abschnitte nach dem Mischen</span><span class="status">★ = Antwort</span></div>
          <div class="mixq">
            <section>
              <h2>Q1 · formal</h2>
              <div class="mrow"><span class="r">1</span><span><span class="doc obv">OBV S. 12 · Teil 1</span></span><span class="src2"><span class="b">B</span><span class="w">W</span></span></div>
              <div class="mrow"><span class="r">2</span><span><span class="doc obv">OBV S. 16</span></span><span class="src2"><span class="b">B</span><span class="w">W</span></span></div>
              <div class="mrow"><span class="r">3</span><span><span class="doc obv">OBV S. 19</span></span><span class="src2"><span class="b">B</span><span class="w">W</span></span></div>
              <div class="mrow"><span class="r">4</span><span><span class="doc obv">OBV S. 18</span></span><span class="src2"><span class="b">B</span><span class="w">W</span></span></div>
              <div class="mrow gt"><span class="r">5</span><span><span class="doc obv">★ OBV S. 12 · Teil 2</span></span><span class="src2"><span class="b">B</span><span class="none">W</span></span></div>
              <div class="mixfoot">Die Antwort war in der Bedeutungssuche auf Platz 1 – hier nur noch auf Platz 5. Knapp drin.</div>
            </section>
            <section>
              <h2>Q2 · Alltag</h2>
              <div class="mrow"><span class="r">1</span><span><span class="doc obv">OBV S. 24</span></span><span class="src2"><span class="b">B</span><span class="none">W</span></span></div>
              <div class="mrow"><span class="r">2</span><span><span class="doc fremd">AI Act S. 109</span></span><span class="src2"><span class="none">B</span><span class="w">W</span></span></div>
              <div class="mrow gt"><span class="r">3</span><span><span class="doc obv">★ OBV S. 12 · Teil 2</span></span><span class="src2"><span class="b">B</span><span class="none">W</span></span></div>
              <div class="mrow"><span class="r">4</span><span><span class="doc fremd">AI Act S. 121</span></span><span class="src2"><span class="none">B</span><span class="w">W</span></span></div>
              <div class="mrow"><span class="r">5</span><span><span class="doc obv">OBV S. 20</span></span><span class="src2"><span class="b">B</span><span class="none">W</span></span></div>
              <div class="mixfoot">Die Listen haben nichts gemeinsam – abwechselnd gemischt. Zwei von fünf aus dem EU AI Act.</div>
            </section>
          </div>
          <div class="mixlegend">
            <div><span class="src2"><span class="b">B</span></span>gefunden von der Bedeutungssuche</div>
            <div><span class="src2"><span class="w">W</span></span>gefunden von der Wortsuche</div>
          </div>""",
    phase=2))

S.append(slide("Vorprüfung Stufe 0",
    """<div class="eyebrow">Phase 3 · Vorprüfung · Stufe 0</div>
          <h1>Ist überhaupt <span class="accent">etwas Passendes</span> dabei?</h1>
          <p class="big-lead">Mindestens einer der fünf Abschnitte muss ähnlich genug sein (≥ 0,35). Sonst: «Weiss ich nicht», ohne das Sprachmodell zu fragen.</p>
          <div class="take">Beide bestehen. Die zwei AI-Act-Abschnitte liegen unter der Grenze – bleiben aber im Kontext.</div>""",
    """<div class="panel-label"><span>Ähnlichkeit der fünf Abschnitte</span><span class="status">Grenze 0,35</span></div>
          <p class="listhead">Q1 · formal</p>
          <div class="bars">
            <div class="bar"><span class="doc obv">OBV S. 12 · Teil 1</span><span class="track"><span class="fill" style="width:79.6%"></span><span class="thr"></span></span><span class="v">0,48</span></div>
            <div class="bar"><span class="doc obv">OBV S. 16</span><span class="track"><span class="fill" style="width:77.3%"></span><span class="thr"></span></span><span class="v">0,46</span></div>
            <div class="bar"><span class="doc obv">OBV S. 19</span><span class="track"><span class="fill" style="width:72.9%"></span><span class="thr"></span></span><span class="v">0,44</span></div>
            <div class="bar"><span class="doc obv">OBV S. 18</span><span class="track"><span class="fill" style="width:72.7%"></span><span class="thr"></span></span><span class="v">0,44</span></div>
            <div class="bar"><span class="doc obv">★ OBV S. 12 · Teil 2</span><span class="track"><span class="fill" style="width:87.3%"></span><span class="thr"></span></span><span class="v">0,52</span></div>
          </div>
          <p class="listhead" style="margin-top:22px">Q2 · Alltag</p>
          <div class="bars">
            <div class="bar"><span class="doc obv">OBV S. 24</span><span class="track"><span class="fill" style="width:73.2%"></span><span class="thr"></span></span><span class="v">0,44</span></div>
            <div class="bar"><span class="doc fremd">AI Act S. 109</span><span class="track"><span class="fill low" style="width:26.4%"></span><span class="thr"></span></span><span class="v">0,16</span></div>
            <div class="bar"><span class="doc obv">★ OBV S. 12 · Teil 2</span><span class="track"><span class="fill" style="width:72.6%"></span><span class="thr"></span></span><span class="v">0,44</span></div>
            <div class="bar"><span class="doc fremd">AI Act S. 121</span><span class="track"><span class="fill low" style="width:35.6%"></span><span class="thr"></span></span><span class="v">0,21</span></div>
            <div class="bar"><span class="doc obv">OBV S. 20</span><span class="track"><span class="fill" style="width:72.3%"></span><span class="thr"></span></span><span class="v">0,43</span></div>
          </div>
          <div class="bars-note">Schwarze Linie = Grenze 0,35. Skala 0 bis 0,6.</div>""",
    phase=3))

S.append(slide("Vorprüfung Stufe 1",
    """<div class="eyebrow">Phase 3 · Vorprüfung · Stufe 1</div>
          <h1>Wie gut ist die <span class="accent">Fundlage</span> insgesamt?</h1>
          <p class="big-lead">Aus den fünf Ähnlichkeiten der letzten Folie wird ein einziger Wert. Er muss mindestens 0,40 erreichen – sonst «Weiss ich nicht».</p>
          <div class="formula"><span>Fundlage</span> = 0,5 × bester Treffer<br>+ 0,3 × Durchschnitt<br>+ 0,2 × Anteil über 0,35</div>
          <div class="take bad">Q2 besteht nur knapp. Wäre auf Platz 5 der nächste Kandidat gelandet – ein SKOS-Abschnitt statt OBV S. 20 –, wären es 0,39: «Weiss ich nicht», obwohl die Antwort im Kontext steht. (nachgerechnet)</div>""",
    """<div class="panel-label"><span>Drei Zutaten, gewichtet</span><span class="status">Grenze 0,40</span></div>
          <table class="fund">
            <thead><tr><th>Zutat · was sie misst</th><th>Q1</th><th>Q2</th></tr></thead>
            <tbody>
              <tr><td class="lbl"><b>Bester Treffer · <i>50 %</i></b><small>der ähnlichste der fünf Abschnitte</small></td>
                  <td class="v"><b>0,52</b><small>→ 0,26</small></td><td class="v"><b>0,44</b><small>→ 0,22</small></td></tr>
              <tr><td class="lbl"><b>Durchschnitt · <i>30 %</i></b><small>wie ähnlich die fünf im Schnitt sind</small></td>
                  <td class="v"><b>0,47</b><small>→ 0,14</small></td><td class="v low"><b>0,34</b><small>→ 0,10</small></td></tr>
              <tr><td class="lbl"><b>Anteil guter Abschnitte · <i>20 %</i></b><small>wie viele über 0,35 liegen</small></td>
                  <td class="v"><b>5 von 5</b><small>→ 0,20</small></td><td class="v low"><b>3 von 5</b><small>→ 0,12</small></td></tr>
              <tr class="sum"><td class="lbl"><b>Fundlage</b><small>Summe der Beiträge</small></td>
                  <td class="v"><b>0,60</b><small>weiter</small></td><td class="v"><b>0,44</b><small>weiter – knapp</small></td></tr>
            </tbody>
          </table>
          <div class="bars b40" style="margin-top:18px">
            <div class="bar"><span>Q1</span><span class="track"><span class="fill q1" style="width:60.2%"></span><span class="thr"></span></span><span class="v">0,60</span></div>
            <div class="bar"><span>Q2</span><span class="track"><span class="fill q2" style="width:44.0%"></span><span class="thr"></span></span><span class="v">0,44</span></div>
          </div>
          <div class="bars-note">Schwarze Linie = Grenze 0,40.</div>""",
    phase=3))

S.append(slide("Was das Modell bekommt",
    """<div class="eyebrow">Phase 4 · Antworten</div>
          <h1>Das Modell bekommt <span class="accent">Regeln und fünf Abschnitte</span></h1>
          <p class="big-lead">Die Abschnitte sind nummeriert. Jede Aussage muss mit einer Nummer belegt werden – sonst muss das Modell «WEISS_NICHT» schreiben.</p>""",
    """<div class="panel-label"><span>Was das Modell bei Q2 sieht</span><span class="status">gpt-4o-mini</span></div>
          <div class="stack">
            <div class="blk"><h4>Regeln · gekürzt</h4>
              <ol class="rules">
                <li>Nur aus den Abschnitten. Kein Vorwissen.</li>
                <li>Jede Aussage mit Nummer belegen, z. B. [1].</li>
                <li>Nicht abgedeckt? Nur «WEISS_NICHT».</li>
              </ol>
            </div>
            <div class="blk"><h4>Fünf Abschnitte</h4>
              <div class="ctx">
                <div><b>[1]</b><span>OBV S. 24</span><span>Rückstrahler, Rückspiegel …</span></div>
                <div class="fremd"><b>[2]</b><span>AI Act S. 109</span><span>«Die Kommission teilt ihren Beschluss … mit.»</span></div>
                <div class="star"><b>[3]</b><span>★ S. 12 · Teil 2</span><span>… innerorts … um 6–10 km/h 120</span></div>
                <div class="fremd"><b>[4]</b><span>AI Act S. 121</span><span>«… in Verkehr gebracht … wurden …»</span></div>
                <div><b>[5]</b><span>OBV S. 20</span><span>Höchstgeschwindigkeitszeichen …</span></div>
              </div>
            </div>
          </div>""",
    phase=4))

S.append(slide("Die Antworten",
    """<div class="eyebrow">Phase 4 · Antworten</div>
          <h1>Beide Antworten sind <span class="accent">richtig</span></h1>
          <p class="big-lead">120 Franken, mit genau einem Beleg auf den richtigen Abschnitt.</p>
          <div class="take good">Bei Q2 übergeht das Modell die zwei AI-Act-Abschnitte und belegt nur mit [3].</div>""",
    """<div class="panel-label"><span>Antwort des Modells</span><span class="status">beide: 120 Franken</span></div>
          <div class="stack">
            <div class="ansbox"><small>Q1 · formal</small>Die Busse für das Überschreiten der … Höchstgeschwindigkeit innerorts um 6–10 km/h beträgt 120 Franken <span class="ref">[5]</span>.</div>
            <div class="ansbox"><small>Q2 · Alltag</small>Das Überschreiten der Höchstgeschwindigkeit innerorts um 6–10 km/h kostet 120 Franken <span class="ref">[3]</span>.</div>
          </div>""",
    phase=4))

S.append(slide("Nachprüfung Vertrauen",
    """<div class="eyebrow">Phase 5 · Nachprüfung · Stufe 2</div>
          <h1>Wie viel <span class="accent">Vertrauen</span> insgesamt?</h1>
          <p class="big-lead">Zur Fundlage kommt jetzt die Belegprüfung: Hat jeder Satz der Antwort eine gültige Quellennummer? Beides zusammen ergibt das Vertrauen – und entscheidet über das Band: hoch, mittel oder «Weiss ich nicht».</p>
          <div class="formula"><span>Vertrauen</span> = 0,5 × Fundlage<br>+ 0,5 × Belege</div>
          <div class="take">Gleiche Antwort, gleiche Belege – nur die schwächere Fundlage bringt Q2 ins mittlere Band.</div>""",
    """<div class="panel-label"><span>Zwei Zutaten, je zur Hälfte</span><span class="status">Band</span></div>
          <table class="fund">
            <thead><tr><th>Zutat · was sie misst</th><th>Q1</th><th>Q2</th></tr></thead>
            <tbody>
              <tr><td class="lbl"><b>Fundlage · <i>50 %</i></b><small>wie gut die fünf gefundenen Abschnitte zur Frage passen – Stufe 1</small></td>
                  <td class="v"><b>0,60</b><small>→ 0,30</small></td><td class="v low"><b>0,44</b><small>→ 0,22</small></td></tr>
              <tr><td class="lbl"><b>Belege · <i>50 %</i></b><small>Anteil der Sätze in der Antwort mit gültiger Quellennummer – geprüft ohne Sprachmodell</small></td>
                  <td class="v"><b>1 von 1</b><small>1,0 → 0,50</small></td><td class="v"><b>1 von 1</b><small>1,0 → 0,50</small></td></tr>
              <tr class="sum"><td class="lbl"><b>Vertrauen</b><small>Summe der Beiträge</small></td>
                  <td class="v"><b>0,80</b><small>hoch</small></td><td class="v"><b>0,72</b><small>mittel</small></td></tr>
            </tbody>
          </table>
          <div class="scale" style="margin-top:22px">
            <div class="zones"><div class="zone z-bad" style="width:45%">Weiss ich nicht</div><div class="zone z-warn" style="width:30%">mittel</div><div class="zone z-ok" style="width:25%">hoch</div></div>
            <span class="tick" style="left:0%">0</span><span class="tick" style="left:45%">0,45</span><span class="tick" style="left:75%">0,75</span><span class="tick" style="left:100%">1</span>
            <span class="pin top q1" style="left:80.1%">Q1 0,80</span>
            <span class="pin bottom q2" style="left:72%">Q2 0,72</span>
          </div>""",
    phase=5))

S.append(slide("Nachprüfung Self-Check",
    """<div class="eyebrow">Phase 5 · Nachprüfung · Stufe 3</div>
          <h1>Im Zweifel prüft ein <span class="accent">zweites Urteil</span></h1>
          <p class="big-lead">Bei mittlerem Vertrauen bekommt das Modell die eigene Antwort noch einmal vorgelegt – zusammen mit den fünf Abschnitten – und muss urteilen, ob jede Aussage darin steht.</p>
          <div class="formula"><span>Self-Check</span>, wenn 0,45 ≤ Vertrauen &lt; 0,75<br>GEDECKT → Antwort ausliefern<br>sonst → «Weiss ich nicht»</div>
          <div class="take good">Fail-closed heisst hier nicht unterdrücken, sondern genauer hinschauen, wenn die Grundlage dünner ist.</div>""",
    """<div class="panel-label"><span>Zweiter Modellaufruf</span><span class="status">nur im mittleren Band</span></div>
          <div class="blk"><h4>Was das Modell gefragt wird · gekürzt</h4>
            <ol class="rules">
              <li>Prüfe nur, ob der Kontext die Antwort deckt – nicht, ob sie vollständig ist.</li>
              <li>Kein Vorwissen: Richtiges, das nicht im Kontext steht, gilt als nicht gedeckt.</li>
              <li>Antworte nur mit GEDECKT oder NICHT_GEDECKT.</li>
            </ol>
          </div>
          <div class="bigpair" style="margin-top:18px">
            <div><p class="listhead">Q1 · Vertrauen hoch</p><div class="verdict skip">nicht nötig<small>1 Modellaufruf insgesamt</small></div></div>
            <div><p class="listhead">Q2 · Vertrauen mittel</p><div class="verdict ok">GEDECKT<small>ausgeliefert · 2 Modellaufrufe</small></div></div>
          </div>""",
    phase=5))

S.append(slide("Was das Beispiel zeigt",
    """<div class="eyebrow">Was das Beispiel zeigt</div>
          <h1>Nicht der Inhalt unterscheidet die Fragen, <span class="accent">sondern die Wörter</span></h1>
          <p class="big-lead">Lara formuliert nicht wie das Gesetz. Die Pipeline muss damit rechnen.</p>""",
    """<div class="panel-label"><span>Drei Befunde</span><span class="status">Q1 und Q2</span></div>
          <div class="insights">
            <div class="insight"><strong>1 → 5</strong><div><h3>Das Mischen kann den besten Treffer verdrängen</h3><p>Die Bedeutungssuche hatte die Antwort auf Platz 1 – ins Modell kam sie als letzte von fünf.</p></div></div>
            <div class="insight bad"><strong>2 von 5</strong><div><h3>Alltagssprache holt Fremdes herein</h3><p>Ein Füllwort und zwei Tippfehler – und zwei Abschnitte stammen aus dem EU AI Act. Lara sieht sie sogar in der Quellenliste unter der Antwort.</p></div></div>
            <div class="insight warn"><strong>0,44</strong><div><h3>Die Pipeline merkt die dünnere Grundlage</h3><p>Knapp über der Grenze, Vertrauen mittel, zweite Prüfung – die Antwort ist richtig und wurde ernsthaft geprüft.</p></div></div>
          </div>
          <p class="listhead" style="margin-top:20px">Was Lara sieht</p>
          <div class="larasees">
            <div class="q1s">Q1 · 120 Fr. · Vertrauen hoch</div>
            <div class="q2s">Q2 · 120 Fr. · Vertrauen mittel</div>
          </div>"""))


EVAL = slide("Eval und Gold-Dataset",
    """<div class="eyebrow">Eval · Gold-Dataset</div>
          <h1>Wie prüft man, ob die <span class="accent">Pipeline</span> gut ist?</h1>
          <p class="big-lead">Man stellt ihr Fragen, deren richtige Antwort man schon kennt – und vergleicht. Diese Fragen heissen Gold-Dataset.</p>
          <div class="take good">Gemessen, nicht geschätzt: Jede Änderung an der Pipeline muss sich an denselben 80 Fragen beweisen.</div>
          <p class="sub-label" style="margin-top:26px">Ein Eintrag</p>
          <div class="code-block"><span class="k">id:</span>               SKOS-PRINZ-02
<span class="k">question:</span>         Was bedeutet das Bedarfsdeckungsprinzip?
<span class="k">category:</span>         in_corpus
<span class="k">expected_refusal:</span> <span class="ok">false</span>
<span class="k">expected_source:</span>  Seiten 6–8 · A.3 Prinzipien der Sozialhilfe</div>""",
    """<div class="panel-label"><span>So funktioniert das Eval</span><span class="status">vor jedem Release</span></div>
          <div class="phases">
            <div class="phase"><b>1</b><div><h3>Fragen mit bekannter Antwort</h3><p>Bei jeder Frage ist festgehalten, ob die Antwort im Korpus steht – und auf welcher Seite.</p></div><span class="tag">80 Fragen</span></div>
          </div>
          <div class="evalcats">
            <div><b>45</b><span>Antwort steht drin</span><small>→ muss antworten und belegen</small></div>
            <div><b>22</b><span>steht nicht drin</span><small>→ muss «Weiss ich nicht» sagen</small></div>
            <div><b>13</b><span>Fangfragen</span><small>→ falsche Annahme korrigieren</small></div>
          </div>
          <div class="phases" style="margin-top:12px">
            <div class="phase"><b>2</b><div><h3>Pipeline antworten lassen</h3><p>Alle 80 Fragen laufen durch die echte Pipeline.</p></div><span class="tag">automatisch</span></div>
            <div class="phase"><b>3</b><div><h3>Vergleichen</h3><p>Drei Grenzen müssen halten, sonst geht nichts in Produktion.</p></div><span class="tag gate">Gates</span></div>
          </div>
          <div class="gates">
            <div><span>Nichts erfinden</span><b>0 %</b><small>erfundene Belege</small></div>
            <div><span>Ablehnen, was nicht drinsteht</span><b>≥ 90 %</b><small>«Weiss ich nicht»</small></div>
            <div><span>Antworten, was drinsteht</span><b>≤ 15 %</b><small>fälschlich abgelehnt</small></div>
          </div>""")

SLIDES = (
    '  <main class="deck" aria-label="LearnFlow Technischer Aufbau">\n\n'
    + v1_section("Architektur").replace('class="slide"', 'class="slide active"', 1) + "\n\n"
    + v1_section("Das Beispiel") + "\n"
    + "".join(S) + "\n"
    + EVAL + "\n\n"
    + v1_section("Gold muss Gold sein") + "\n\n"
)

OUT.write_text(head + SLIDES + "  </main>" + tail, encoding="utf-8")
print("ok", SLIDES.count('<section class="slide'))


# ── Q1/Q2 identity: every mention gets the same badge ────────────────────
# Q1 = blue with a paragraph sign (formal, legal language), Q2 = violet with a
# speech bubble (everyday language). Blue and violet on purpose: teal, amber and
# coral already mean good, tight and bad on these slides.
Q_CSS = """
    /* ── Q1/Q2-Abzeichen ─────────────────────────────────────────────── */
    :root { --q1: #2f5bd3; --q1-pale: #e8eefc; --q2: #8b3fd9; --q2-pale: #f3eafc; }
    .qb {
      display: inline-flex; align-items: center; gap: .32em; vertical-align: .06em;
      padding: .16em .55em .16em .38em; border-radius: 99px; color: #fff;
      font-size: clamp(17px, .7em, 32px); font-weight: 850; letter-spacing: .01em; line-height: 1.15;
      text-transform: none; white-space: nowrap; font-style: normal;
    }
    .qb.q1 { background: var(--q1); }
    .qb.q2 { background: var(--q2); }
    .qb .qi {
      display: inline-grid; place-items: center; width: 1.25em; height: 1.25em; border-radius: 50%;
      background: rgba(255, 255, 255, .22); font-size: .95em; font-weight: 900;
    }
    .qb .qi svg { width: .82em; height: .82em; display: block; }
    .qpanel.q1p { border-top: 7px solid var(--q1); }
    .qpanel.q2p { border-top: 7px solid var(--q2); }
    .bubble.b1 { box-shadow: inset 7px 0 0 var(--q1), 0 14px 28px rgba(16, 30, 54, .16); }
    .bubble.b2 { box-shadow: inset 7px 0 0 var(--q2), 0 14px 28px rgba(16, 30, 54, .16); }
    .ask-label .q { color: inherit; }
    .ask-label .qb { font-size: 22px; margin-right: 4px; }
    .bigcard .q .qb, .listhead .qb, .blk h4 .qb, .ansbox small .qb { font-size: 20px; margin-right: 4px; }
    .calc div.h .qb { font-size: 18px; }
    .panel-label .qb { font-size: 18px; margin-right: 2px; }
"""

BUBBLE_SVG = ('<svg viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" '
              'd="M2 2.5h12a1 1 0 0 1 1 1v7a1 1 0 0 1-1 1H7l-3.5 3v-3H2a1 1 0 0 1-1-1v-7a1 1 0 0 1 1-1z"/></svg>')
BADGE = {
    "1": '<span class="qb q1" title="Frage 1 · formal"><span class="qi">§</span>Q1</span>',
    "2": f'<span class="qb q2" title="Frage 2 · Alltag"><span class="qi">{BUBBLE_SVG}</span>Q2</span>',
}

# Slides about one question only get a coloured top edge on their card.
SINGLE_Q = {
    "Wortsuche Q1": "1",
    "Wortsuche Q2": "2", "Was das Modell bekommt": "2",
}


def _badge_text(html: str) -> str:
    """Replace Q1/Q2 in text nodes only — attributes (aria-label, title) stay plain."""
    def text_node(m: re.Match) -> str:
        return re.sub(r"\bQ([12])\b", lambda q: BADGE[q.group(1)], m.group(0))
    return re.sub(r"(?<=>)[^<>]+(?=<)", text_node, html)


out_path = OUT
html = out_path.read_text(encoding="utf-8")
assert html.count(marker) == 1
html = html.replace(marker, Q_CSS + marker)

head_part, main_part = html.split('  <main class="deck"', 1)
main_part = _badge_text(main_part)

for label, q in SINGLE_Q.items():
    start = main_part.index(f'aria-label="{label}"')
    idx = main_part.index('<div class="panel', start)
    main_part = main_part[:idx] + f'<div class="panel qpanel q{q}p' + main_part[idx + len('<div class="panel'):]

beispiel = main_part.index('aria-label="Das Beispiel"')
for n in ("1", "2"):
    idx = main_part.index('class="bubble"', beispiel)
    main_part = main_part[:idx] + f'class="bubble b{n}"' + main_part[idx + len('class="bubble"'):]

out_path.write_text(head_part + '  <main class="deck"' + main_part, encoding="utf-8")
print("badges:", main_part.count('class="qb q1"'), main_part.count('class="qb q2"'))
