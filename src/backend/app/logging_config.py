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


def configure_logging(level: str = DEFAULT_LEVEL) -> None:
    """Root-Handler und Format setzen.

    Ein unbrauchbarer `LOG_LEVEL` fällt auf INFO zurück und sagt das, statt den
    Prozess zu beenden — dieselbe Abwägung wie bei den Reaper-Werten in
    `worker/main.py` (`_clamped_int`): ein Tippfehler in einer Betriebsgrösse
    darf nicht dazu führen, dass gar nichts mehr läuft. Fail-closed gilt für
    Antworten an Nutzer (ADR-008), nicht für die Ausführlichkeit des Logs.

    `force=True`, damit ein zweiter Aufruf nicht stillschweigend wirkungslos
    bleibt: `basicConfig` tut sonst nichts, sobald der Root-Logger schon einen
    Handler hat — was unter pytest (caplog) und bei einem Reload der Fall ist.
    """
    resolved = logging.getLevelNamesMapping().get(level.strip().upper())
    unknown = resolved is None

    # `is None`, nicht `or`: NOTSET ist ein gültiger Name und steht für 0, also
    # für einen falsy Wert. Eine Wahrheitsprüfung hätte ausgerechnet den
    # ausführlichsten Level stillschweigend auf INFO gedreht — und dabei die
    # Warnung übersprungen, die dieser Funktion zufolge jeden Ersatz begleitet.
    logging.basicConfig(
        level=DEFAULT_LEVEL if unknown else resolved, format=FORMAT, force=True
    )

    if unknown:
        logging.getLogger(__name__).warning(
            "LOG_LEVEL=%r ist kein bekannter Level — es gilt %s", level, DEFAULT_LEVEL
        )
