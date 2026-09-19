"""T-63: die gemeinsame Logging-Konfiguration von API und Worker.

Der Punkt der Tests ist nicht, dass `basicConfig` funktioniert, sondern die
Zusagen, die diese Datei dem Betrieb macht: ein `app.*`-Logger erreicht die
Ausgabe mit Zeitstempel und Namen, `LOG_LEVEL` steuert dabei *nur* die eigenen
Logger und nicht die der Abhängigkeiten, und ein vertippter Wert beendet den
Prozess nicht.
"""

import logging
import pathlib
import subprocess
import sys

import pytest

from app.logging_config import (
    DEFAULT_LEVEL,
    DEFAULT_THIRD_PARTY_LEVEL,
    FORMAT,
    OWN_LOGGERS,
    configure_logging,
)


@pytest.fixture(autouse=True)
def _restore_logging():
    """Root-Konfiguration und die Level der eigenen Logger wiederherstellen.

    `configure_logging` setzt beides mit `force=True` bzw. `setLevel`; ohne das
    hier nähme der erste Test dem Rest der Suite das Logging weg.
    """
    root = logging.getLogger()
    handlers, root_level = root.handlers[:], root.level
    own = {name: logging.getLogger(name).level for name in OWN_LOGGERS}
    yield
    root.handlers[:] = handlers
    root.setLevel(root_level)
    for name, level in own.items():
        logging.getLogger(name).setLevel(level)


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


def test_worker_logger_reaches_the_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Der Worker hängt an derselben Konfiguration — und `worker` ist ein
    eigener Paketname, der ohne Eintrag in OWN_LOGGERS am Root hängenbliebe."""
    configure_logging("INFO")

    logging.getLogger("worker.main").info("Worker ready")

    assert "Worker ready" in capsys.readouterr().err


def test_third_party_loggers_stay_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    """Review zu PR #140: stünde der *Root* auf dem konfigurierten Level,
    schriebe `httpx` eine Zeile pro Provider-Aufruf — also mehrere pro `/query`.
    LOG_LEVEL steuert die Ausführlichkeit dieses Systems, nicht die seiner
    Abhängigkeiten."""
    configure_logging("DEBUG")

    logging.getLogger("httpx").info('HTTP Request: POST https://api.openai.com/v1/embeddings')
    logging.getLogger("httpcore.http11").debug("send_request_headers")

    assert capsys.readouterr().err == ""


def test_a_third_party_warning_still_gets_through(capsys: pytest.CaptureFixture[str]) -> None:
    """WARNING statt stumm: eine echte Warnung einer Bibliothek soll sichtbar
    bleiben, sonst wäre die Ruhe mit Blindheit erkauft."""
    configure_logging("INFO")

    logging.getLogger("httpx").warning("Verbindung wird wiederholt")

    assert "Verbindung wird wiederholt" in capsys.readouterr().err
    assert logging.getLogger().level == logging.getLevelNamesMapping()[DEFAULT_THIRD_PARTY_LEVEL]


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

    fallback = logging.getLevelNamesMapping()[DEFAULT_LEVEL]
    assert all(logging.getLogger(name).level == fallback for name in OWN_LOGGERS)
    err = capsys.readouterr().err
    assert "VERBOSE" in err
    assert DEFAULT_LEVEL in err


def test_notset_is_rejected_loudly(capsys: pytest.CaptureFixture[str]) -> None:
    """NOTSET ist kein Level, auf dem man loggt, sondern „erbe vom Eltern-
    logger" — an `app` gesetzt hiesse das konkret: erbe die WARNING des Roots.
    Wer den ausführlichsten Wert der Liste wählt, bekäme also den zweitleisesten.
    Deshalb wie ein unbrauchbarer Wert behandelt — aber *mit* Warnung, denn
    stilles Ersetzen war der Befund aus dem ersten Review."""
    configure_logging("NOTSET")

    fallback = logging.getLevelNamesMapping()[DEFAULT_LEVEL]
    assert all(logging.getLogger(name).level == fallback for name in OWN_LOGGERS)
    err = capsys.readouterr().err
    assert "NOTSET" in err
    assert DEFAULT_LEVEL in err


def test_second_call_is_not_silently_ignored(capsys: pytest.CaptureFixture[str]) -> None:
    """Ohne `force=True` täte `basicConfig` beim zweiten Aufruf nichts — und
    unter pytest oder nach einem Reload ist der zweite Aufruf der Normalfall."""
    configure_logging("ERROR")
    configure_logging("INFO")

    logging.getLogger("app.routers.query").info("nach dem zweiten Aufruf")

    assert "nach dem zweiten Aufruf" in capsys.readouterr().err


def test_third_party_level_is_configurable(capsys: pytest.CaptureFixture[str]) -> None:
    """Der Kern des zweiten Review-Durchgangs: die Bibliotheks-Zeilen sind über
    eine Einstellung erreichbar, nicht nur über einen Code-Change. Vor T-63 sah
    der Worker sie (Root stand auf INFO); mit einer festen Konstante hätte er
    diese Sicht verloren."""
    configure_logging("INFO", "DEBUG")

    logging.getLogger("pgqueuer.qm").debug("job not picked up")

    assert "job not picked up" in capsys.readouterr().err


def test_the_two_levels_are_independent(capsys: pytest.CaptureFixture[str]) -> None:
    """Der Diagnosefall soll nicht erzwingen, dass auch das eigene Log lauter
    wird — und umgekehrt.

    Absichtlich `pgqueuer` und nicht `httpx`: Letzterer bekommt beim Import von
    litellm einen *eigenen* Level verpasst und hört dann nicht mehr auf den Root
    — siehe den Docstring von `app/logging_config.py`.
    """
    configure_logging("ERROR", "DEBUG")

    logging.getLogger("app.routers.query").info("eigenes INFO, soll schweigen")
    logging.getLogger("pgqueuer.qm").debug("fremdes DEBUG, soll durch")

    err = capsys.readouterr().err
    assert "eigenes INFO" not in err
    assert "fremdes DEBUG" in err


def test_unknown_third_party_level_falls_back_and_says_so(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dieselbe Regel wie für LOG_LEVEL -- und die Meldung nennt den Namen der
    Einstellung, damit klar ist, welche der beiden gemeint ist."""
    configure_logging("INFO", "GESPRAECHIG")

    err = capsys.readouterr().err
    assert "LOG_LEVEL_THIRD_PARTY" in err
    assert "GESPRAECHIG" in err
    assert logging.getLogger().level == logging.getLevelNamesMapping()[DEFAULT_THIRD_PARTY_LEVEL]


def test_importing_app_main_does_not_configure_logging() -> None:
    """Review zu PR #140: `configure_logging` laeuft mit `force=True` und
    entfernt dabei bestehende Root-Handler. Ein Import von `app.main` ist aber
    kein startender Server -- pytest importiert das Modul beim Einsammeln, und
    ein kuenftiger Entry-Point koennte sein Logging vorher selbst einrichten.
    Deshalb haengt der Aufruf am Lifespan, nicht am Import.

    Eigener Interpreter, weil `app.main` in dieser Suite laengst importiert ist
    und ein zweiter Import im selben Prozess nichts mehr ausfuehrt.
    """
    probe = (
        "import logging;"
        "h = logging.StreamHandler();"
        "logging.getLogger().addHandler(h);"
        "import app.main;"
        "print(h in logging.getLogger().handlers)"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=pathlib.Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("True"), (
        "Der Import von app.main hat einen fremden Root-Handler entfernt: "
        f"{result.stdout}{result.stderr}"
    )


def test_format_carries_time_level_and_name() -> None:
    """Die vier Felder sind der Grund, warum API und Worker sich dieselbe
    Konfiguration teilen, statt je eine eigene zu haben."""
    for field in ("%(asctime)s", "%(levelname)s", "%(name)s", "%(message)s"):
        assert field in FORMAT
