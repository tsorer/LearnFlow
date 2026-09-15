"""T-63: die gemeinsame Logging-Konfiguration von API und Worker.

Der Punkt der Tests ist nicht, dass `basicConfig` funktioniert, sondern die zwei
Zusagen, die diese Datei dem Betrieb macht: ein `app.*`-Logger erreicht die
Ausgabe mit Zeitstempel und Namen, und ein vertippter `LOG_LEVEL` beendet den
Prozess nicht.
"""

import logging

import pytest

from app.logging_config import DEFAULT_LEVEL, FORMAT, configure_logging


@pytest.fixture(autouse=True)
def _restore_root_logger():
    """Die Root-Konfiguration wiederherstellen — `configure_logging` setzt sie
    mit `force=True`, und ohne das hier nähme der erste Test dem Rest der Suite
    das Logging weg."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)


def test_app_logger_reaches_the_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Der eigentliche Grund für T-63: vor der Konfiguration kam eine
    INFO-Zeile aus `app/` nirgends an."""
    configure_logging("INFO")

    logging.getLogger("app.services.quiz").info("Frage verworfen")

    err = capsys.readouterr().err
    assert "Frage verworfen" in err
    # Der Loggername macht die Zeile im gemischten `docker compose logs`
    # zuordenbar — genau das fehlte dem nackten lastResort-Handler.
    assert "app.services.quiz" in err


def test_level_is_applied(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("WARNING")

    logging.getLogger("app.services.quiz").info("zu leise")
    logging.getLogger("app.services.quiz").warning("laut genug")

    err = capsys.readouterr().err
    assert "zu leise" not in err
    assert "laut genug" in err


def test_lowercase_level_is_accepted(capsys: pytest.CaptureFixture[str]) -> None:
    """`LOG_LEVEL=debug` in einer .env ist der Normalfall, nicht der Sonderfall."""
    configure_logging("debug")

    logging.getLogger("app.services.config").debug("Default greift")

    assert "Default greift" in capsys.readouterr().err


def test_unknown_level_falls_back_and_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    """Ein Tippfehler in einer Betriebsgrösse darf den Start nicht verhindern —
    dieselbe Abwägung wie bei den Reaper-Werten (`worker/main.py`)."""
    configure_logging("VERBOSE")

    assert logging.getLogger().level == logging.getLevelNamesMapping()[DEFAULT_LEVEL]
    err = capsys.readouterr().err
    assert "VERBOSE" in err
    assert DEFAULT_LEVEL in err


def test_notset_is_honoured_not_swallowed(capsys: pytest.CaptureFixture[str]) -> None:
    """NOTSET ist ein gueltiger Levelname und steht fuer 0. Eine
    Wahrheitspruefung auf den aufgeloesten Wert haette genau diesen Level auf
    INFO gedreht -- und zwar ohne die Warnung, die jeden Ersatz begleiten soll."""
    configure_logging("NOTSET")

    assert logging.getLogger().level == logging.NOTSET
    logging.getLogger("app.services.config").debug("bei NOTSET sichtbar")

    err = capsys.readouterr().err
    assert "bei NOTSET sichtbar" in err
    assert "kein bekannter Level" not in err


def test_second_call_is_not_silently_ignored(capsys: pytest.CaptureFixture[str]) -> None:
    """Ohne `force=True` täte `basicConfig` beim zweiten Aufruf nichts — und
    unter pytest oder nach einem Reload ist der zweite Aufruf der Normalfall."""
    configure_logging("ERROR")
    configure_logging("INFO")

    logging.getLogger("app.routers.query").info("nach dem zweiten Aufruf")

    assert "nach dem zweiten Aufruf" in capsys.readouterr().err


def test_format_carries_time_level_and_name() -> None:
    """Die vier Felder sind der Grund, warum API und Worker sich dieselbe
    Konfiguration teilen, statt je eine eigene zu haben."""
    for field in ("%(asctime)s", "%(levelname)s", "%(name)s", "%(message)s"):
        assert field in FORMAT
