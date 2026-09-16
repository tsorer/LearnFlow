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
"""

import logging

FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"

DEFAULT_LEVEL = "INFO"

#: Die Logger, für die `LOG_LEVEL` gilt — unsere eigenen, nach Paketnamen.
OWN_LOGGERS = ("app", "worker")

#: Alles andere. Bewusst nicht am konfigurierten Level beteiligt (Review zu
#: PR #140): `LOG_LEVEL` steuert die Ausführlichkeit *dieses* Systems, nicht die
#: seiner Abhängigkeiten. Stünde der Root-Logger auf INFO, schriebe `httpx` eine
#: Zeile pro Provider-Aufruf — also mehrere pro `/query` und pro Embedding-Batch
#: — und `LOG_LEVEL=DEBUG` zöge zusätzlich `httpcore` und LiteLLMs eigene
#: Ausgabe mit hoch. WARNING statt vollständig stummschalten, damit eine echte
#: Warnung einer Bibliothek weiterhin sichtbar ist; wer die Aufrufe sehen will,
#: hebt den Level dieses einen Loggers gezielt an.
THIRD_PARTY_LEVEL = logging.WARNING


def configure_logging(level: str = DEFAULT_LEVEL) -> None:
    """Format und Level setzen: Handler am Root, Level an `OWN_LOGGERS`.

    Der Handler muss an den Root, weil dorthin alles propagiert — der *Level*
    aber nicht, siehe `THIRD_PARTY_LEVEL`. Ein propagierter Record wird nur vom
    Level seines Ursprungsloggers und vom Level des Handlers geprüft, nicht vom
    Level des Root-Loggers; `app.services.quiz` auf DEBUG erreicht die Ausgabe
    also auch, während der Root auf WARNING steht.

    Ein unbrauchbarer `LOG_LEVEL` fällt auf INFO zurück und sagt das, statt den
    Prozess zu beenden — dieselbe Abwägung wie bei den Reaper-Werten in
    `worker/main.py` (`_clamped_int`): ein Tippfehler in einer Betriebsgrösse
    darf nicht dazu führen, dass gar nichts mehr läuft. Fail-closed gilt für
    Antworten an Nutzer (ADR-008), nicht für die Ausführlichkeit des Logs.

    `force=True`, damit ein zweiter Aufruf nicht stillschweigend wirkungslos
    bleibt: `basicConfig` tut sonst nichts, sobald der Root-Logger schon einen
    Handler hat — was unter pytest (caplog) und bei einem Reload der Fall ist.
    Deshalb ruft weder die API noch der Worker diese Funktion beim Import auf,
    sondern erst beim tatsächlichen Start (Lifespan bzw. `main()`): ein Import
    von `app.main`, der keinen Server hochfährt, soll fremde Handler nicht
    entfernen.
    """
    resolved = logging.getLevelNamesMapping().get(level.strip().upper())

    # NOTSET (0) ist kein Level, auf dem man loggt, sondern der Sentinel „erbe
    # vom Elternlogger". An `OWN_LOGGERS` gesetzt hiesse er konkret: erbe vom
    # Root — und der steht hier auf WARNING. `LOG_LEVEL=NOTSET` bekäme damit
    # das Gegenteil dessen, was jemand erwartet, der den ausführlichsten Wert
    # der Liste wählt. Also wie ein unbrauchbarer Wert behandelt, inklusive der
    # Warnung: still auf INFO drehen wäre der Fehler aus dem ersten Review.
    if resolved is None or resolved == logging.NOTSET:
        effective: int | str = DEFAULT_LEVEL
        unusable = True
    else:
        effective = resolved
        unusable = False

    logging.basicConfig(level=THIRD_PARTY_LEVEL, format=FORMAT, force=True)
    for name in OWN_LOGGERS:
        logging.getLogger(name).setLevel(effective)

    if unusable:
        logging.getLogger(__name__).warning(
            "LOG_LEVEL=%r ist kein brauchbarer Level — es gilt %s", level, DEFAULT_LEVEL
        )
