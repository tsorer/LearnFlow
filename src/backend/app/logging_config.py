"""Logging-Konfiguration für API und Worker (T-63).

Bis T-63 rief nur `worker/main.py` `basicConfig` auf. Die API konfigurierte
nichts, also griff Pythons lastResort-Handler, und der steht auf WARNING: alles
ab WARNING erschien, aber **nackt** — nur der Meldungstext, ohne Zeitstempel und
ohne Loggernamen, also ohne die zwei Angaben, die eine Zeile im gemischten
`docker compose logs` überhaupt zuordenbar machen. INFO und DEBUG aus `app/`
fielen ersatzlos weg; die beiden `logger.debug`-Zeilen in `services/config.py`
etwa waren nicht einschaltbar.

Ein gemeinsames Modul statt zweier `basicConfig`-Aufrufe, weil der Nutzen genau
in der Gleichheit liegt: `docker compose logs` mischt beide Container in einen
Strom, und zwei Formate darin sind schlechter lesbar als eines.

Bewusst `basicConfig` und keine `dictConfig`: uvicorn bringt seine eigene
Konfiguration für die `uvicorn.*`-Logger mit und lässt den Root-Logger in Ruhe.
Genau dorthin propagieren die `app.*`-Logger, und genau dort fehlte der Handler.
Eine eigene `dictConfig` würde stattdessen mit uvicorns Konfiguration um
dieselben Logger konkurrieren, ohne dass dieses Projekt etwas davon hätte.

**Zwei Level, nicht eines** (Review zu PR #140): `LOG_LEVEL` gilt für die Logger
dieses Systems, `LOG_LEVEL_THIRD_PARTY` für alle übrigen. Der Grund für die
Trennung ist der Lärm — stünde auch nur ein Level am Root, schriebe `httpx` eine
Zeile pro Provider-Aufruf, also mehrere pro `/query` und pro Embedding-Batch, und
`LOG_LEVEL=DEBUG` zöge zusätzlich `httpcore` und LiteLLMs eigene Ausgabe hoch.
Der Grund für die zweite *Einstellung* statt einer festen Konstante ist der
umgekehrte Fall: wenn ein Job nicht angenommen wird, will man die `debug`-Zeilen
von pgqueuer sehen, und dafür soll niemand Code ändern und neu bauen müssen.
Vor T-63 stand der Worker auf Root-INFO und hatte diese Sicht; eine feste
Konstante hätte sie ihm genommen.

Eine Grenze, die man kennen muss: `LOG_LEVEL_THIRD_PARTY` wirkt über den
Root-Logger und erreicht damit nur Logger **ohne eigenen Level**. `pgqueuer` und
`httpcore` gehören dazu, `httpx` nicht — `import litellm` setzt diesen Logger
selbst auf WARNING (gemessen 2026-09-19), und ein Kind-Level schlägt den Root.
`LOG_LEVEL_THIRD_PARTY=DEBUG` bringt also die pgqueuer- und httpcore-Zeilen
zurück, nicht aber die `HTTP Request:`-Zeilen von httpx. Das ist kein Mangel
dieser Funktion, sondern eine Festlegung von litellm; wer sie aufheben will,
muss den Level von `httpx` nach dem Import zurücksetzen.
"""

import logging

FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

#: Für die Logger dieses Systems (`LOG_LEVEL`).
DEFAULT_LEVEL = "INFO"

#: Für alles andere (`LOG_LEVEL_THIRD_PARTY`). WARNING statt vollständig
#: stumm, damit eine echte Warnung einer Bibliothek auch im Normalbetrieb
#: sichtbar bleibt — die Ruhe soll nicht mit Blindheit erkauft sein.
DEFAULT_THIRD_PARTY_LEVEL = "WARNING"

#: Die Logger, für die `LOG_LEVEL` gilt — unsere eigenen, nach Paketnamen.
OWN_LOGGERS = ("app", "worker")


def configure_logging(
    level: str = DEFAULT_LEVEL, third_party_level: str = DEFAULT_THIRD_PARTY_LEVEL
) -> None:
    """Format und Level setzen: Handler am Root, zwei Level.

    Der Handler muss an den Root, weil dorthin alles propagiert. Der Level des
    Roots wirkt dabei nur auf Logger *ohne* eigenen Level — also auf die der
    Bibliotheken; ein propagierter Record aus `app.*` wird nur vom Level seines
    Ursprungsloggers und vom Level des Handlers geprüft, nicht vom Level des
    Roots. Deshalb genügt es, `OWN_LOGGERS` direkt zu setzen und den Rest über
    den Root zu regeln.

    Ein unbrauchbarer Level fällt auf den jeweiligen Default zurück und sagt
    das, statt den Prozess zu beenden — dieselbe Abwägung wie bei den
    Reaper-Werten in `worker/main.py` (`_clamped_int`): ein Tippfehler in einer
    Betriebsgrösse darf nicht dazu führen, dass gar nichts mehr läuft.
    Fail-closed gilt für Antworten an Nutzer (ADR-008), nicht für die
    Ausführlichkeit des Logs.

    `force=True`, damit ein zweiter Aufruf nicht stillschweigend wirkungslos
    bleibt: `basicConfig` tut sonst nichts, sobald der Root-Logger schon einen
    Handler hat — was unter pytest (caplog) und bei einem Reload der Fall ist.
    Deshalb ruft weder die API noch der Worker diese Funktion beim Import auf,
    sondern erst beim tatsächlichen Start (Lifespan bzw. `main()`): ein Import
    von `app.main`, der keinen Server hochfährt, soll fremde Handler nicht
    entfernen.
    """
    own, own_usable = _resolve(level, DEFAULT_LEVEL)
    third_party, third_party_usable = _resolve(third_party_level, DEFAULT_THIRD_PARTY_LEVEL)

    logging.basicConfig(level=third_party, format=FORMAT, force=True)
    for name in OWN_LOGGERS:
        logging.getLogger(name).setLevel(own)

    log = logging.getLogger(__name__)
    if not own_usable:
        log.warning("LOG_LEVEL=%r ist kein brauchbarer Level — es gilt %s", level, DEFAULT_LEVEL)
    if not third_party_usable:
        log.warning(
            "LOG_LEVEL_THIRD_PARTY=%r ist kein brauchbarer Level — es gilt %s",
            third_party_level,
            DEFAULT_THIRD_PARTY_LEVEL,
        )


def _resolve(level: str, default: str) -> tuple[int | str, bool]:
    """Einen Levelnamen in einen Wert übersetzen; zweites Element sagt, ob er
    brauchbar war.

    NOTSET (0) ist kein Level, auf dem man loggt, sondern der Sentinel „erbe vom
    Elternlogger". An einem `OWN_LOGGERS`-Eintrag hiesse er konkret: erbe vom
    Root — also den Level der Bibliotheken, normalerweise WARNING. Wer den
    ausführlichsten Wert der Liste wählt, bekäme damit den zweitleisesten.
    Deshalb zählt NOTSET wie ein unbekannter Wert, inklusive der Warnung beim
    Aufrufer: still auf den Default drehen wäre der Fehler aus dem ersten Review.
    """
    resolved = logging.getLevelNamesMapping().get(level.strip().upper())
    if resolved is None or resolved == logging.NOTSET:
        return default, False
    return resolved, True
