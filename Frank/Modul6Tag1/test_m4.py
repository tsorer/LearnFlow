"""M4-Spec fuer den pytest-Evaluator: die Tests, die check_encoding_m4.py erfuellen muss.

Bewusst klein gehalten (9 Tests statt der 73 aus test_claude.py) - der Orchestrator
schickt dem Generator nur die letzten 800 Zeichen der pytest-Ausgabe als Feedback.
Ein knapper Report ist dort mehr wert als vollstaendige Abdeckung.

Ausgangslage: check_encoding_m4.py ist eine Kopie von check_encoding.py (v1) und
faellt bei drei Tests durch. Der Generator muss nachbessern.
"""

from __future__ import annotations

import importlib.util
import stat
import subprocess
import sys
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).with_name("check_encoding_m4.py")
_spec = importlib.util.spec_from_file_location("check_encoding_m4", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
sys.modules["check_encoding_m4"] = mod
_spec.loader.exec_module(mod)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (
        ("init", "-q"),
        ("config", "user.email", "test@example.invalid"),
        ("config", "user.name", "Test Runner"),
    ):
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)
    return repo


# --- Bug 1: BOM bei UTF-16/UTF-32 -------------------------------------------


@pytest.mark.parametrize(
    ("codec", "bom"),
    [
        ("utf-16-le", b"\xff\xfe"),
        ("utf-16-be", b"\xfe\xff"),
        ("utf-32-le", b"\xff\xfe\x00\x00"),
        ("utf-32-be", b"\x00\x00\xfe\xff"),
    ],
)
def test_utf16_und_utf32_ohne_bom_zurueckschreiben(tmp_path, codec, bom):
    """Nach der Konvertierung darf KEIN BOM mehr in der Datei stehen."""
    text = "Zuerich\n"
    path = tmp_path / "f.txt"
    path.write_bytes(bom + text.encode(codec))

    mod.convert_to_utf8_no_bom(path)

    assert path.read_bytes() == text.encode("utf-8")


# --- Bug 2: git-Ausgabe ist UTF-8 -------------------------------------------


def test_umlaut_dateiname_wird_gefunden(git_repo):
    """git meldet Pfade als UTF-8-Bytes - unabhaengig von der Locale-Codepage."""
    (git_repo / "Grüezi.txt").write_bytes(b"x\n")

    _, files = mod.uncommitted_files(git_repo)

    assert [f.name for f in files] == ["Grüezi.txt"]


# --- Bug 3: cp1252 vor latin-1 ----------------------------------------------


def test_cp1252_anfuehrungszeichen_bleiben_erhalten(tmp_path):
    """0x93/0x94 sind typografische Anfuehrungszeichen, keine Steuerzeichen."""
    path = tmp_path / "f.txt"
    path.write_bytes(b"\x93Zitat\x94")

    mod.convert_to_utf8_no_bom(path)

    assert path.read_text(encoding="utf-8") == "“Zitat”"


def test_in_cp1252_undefinierte_bytes_fallen_auf_latin1(tmp_path):
    """0x81 ist in cp1252 nicht belegt - latin-1 muss weiter als Netz dienen."""
    path = tmp_path / "f.txt"
    path.write_bytes(b"text\x81")

    encoding, has_bom = mod.detect_encoding_and_bom(path)

    assert (encoding, has_bom) == ("latin-1", False)


# --- Regressionen: das darf beim Nachbessern nicht kaputtgehen ---------------


def test_saubere_utf8_datei_bleibt_bytegleich(tmp_path):
    original = "schon sauber: äöü\n".encode("utf-8")
    path = tmp_path / "f.txt"
    path.write_bytes(original)

    mod.convert_to_utf8_no_bom(path)

    assert path.read_bytes() == original


def test_crlf_bleibt_erhalten(tmp_path):
    path = tmp_path / "f.txt"
    path.write_bytes(b"a\r\nb\r\n")

    mod.convert_to_utf8_no_bom(path)

    assert path.read_bytes() == b"a\r\nb\r\n"


def test_binaerdatei_wird_uebersprungen(git_repo, monkeypatch, capsys):
    payload = b"PNG\x00\x01\x02\xff\xfe"
    (git_repo / "image.png").write_bytes(payload)
    monkeypatch.setattr(sys, "argv", ["check_encoding_m4.py", str(git_repo)])

    assert mod.main() == 0
    assert "Files checked: 0" in capsys.readouterr().out
    assert (git_repo / "image.png").read_bytes() == payload


def test_schreibgeschuetzte_datei_wird_nicht_gekuerzt(tmp_path):
    """open(..., "w") kuerzt beim Oeffnen - schlaegt es fehl, muss der Inhalt
    vollstaendig erhalten bleiben."""
    original = "testÄöü".encode("cp1252")
    path = tmp_path / "f.txt"
    path.write_bytes(original)
    path.chmod(stat.S_IREAD)
    try:
        with open(path, "a"):
            pytest.skip("Prozess umgeht den Schreibschutz - Test nicht aussagekraeftig")
    except OSError:
        pass

    try:
        with pytest.raises(PermissionError):
            mod.convert_to_utf8_no_bom(path)
        assert path.read_bytes() == original
    finally:
        path.chmod(stat.S_IWRITE | stat.S_IREAD)
