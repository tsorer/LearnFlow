"""pytest-Suite fuer `check_encoding_m4.py`.

Deckt ab:
  * Happy Path      - die vier Funktionen im Normalbetrieb
  * Grenzwerte      - leere Datei, abgeschnittenes BOM, NUL-Byte genau am Blockrand
  * Falsche Typen   - None, float, int (== Dateideskriptor!), Verzeichnis, fehlende Datei
  * "Vergessene" Faelle - CRLF-Erhalt, Idempotenz, cp1252-vor-latin-1-Reihenfolge,
    Dateinamen mit Leerzeichen/Umlauten, Rename-Parsing

Ausfuehren:  python -m pytest test_claude.py -v
"""

from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Modul unter Test laden (Dateiname ist kein Paket -> explizit ueber den Pfad)
# ---------------------------------------------------------------------------

_MODULE_PATH = Path(__file__).with_name("check_encoding_m4.py")
_spec = importlib.util.spec_from_file_location("check_encoding_m4", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
check_encoding = importlib.util.module_from_spec(_spec)
sys.modules["check_encoding_m4"] = check_encoding
_spec.loader.exec_module(check_encoding)

detect_encoding_and_bom = check_encoding.detect_encoding_and_bom
convert_to_utf8_no_bom = check_encoding.convert_to_utf8_no_bom
is_binary = check_encoding.is_binary
uncommitted_files = check_encoding.uncommitted_files
main = check_encoding.main


# ---------------------------------------------------------------------------
# Fixtures / Helfer
# ---------------------------------------------------------------------------


@pytest.fixture
def write(tmp_path: Path):
    """Schreibt rohe Bytes in eine Datei unter tmp_path und gibt den Pfad zurueck."""

    def _write(name: str, data: bytes) -> Path:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    return _write


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return result.stdout


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Frisches Repo mit lokaler Identitaet (unabhaengig von der globalen Config)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test Runner")
    _git(repo, "config", "commit.gpgsign", "false")
    return repo


def _commit(repo: Path, name: str, data: bytes) -> Path:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    _git(repo, "add", "--", name)
    _git(repo, "commit", "-q", "-m", "add " + name)
    return path


@pytest.fixture
def readonly():
    """Setzt das Read-only-Flag und nimmt es im Teardown wieder zurueck - sonst
    bekommt pytest sein tmp_path-Verzeichnis nicht mehr geloescht."""
    touched: list[Path] = []

    def _readonly(path: Path) -> Path:
        path.chmod(stat.S_IREAD)
        try:
            with open(path, "a"):
                pass
        except OSError:
            touched.append(path)
            return path
        # root (bzw. ein Admin-Prozess) ignoriert das Flag - dann ist hier nichts
        # zu testen.
        path.chmod(stat.S_IWRITE | stat.S_IREAD)
        pytest.skip("Prozess umgeht den Schreibschutz - Test nicht aussagekraeftig")

    yield _readonly

    for path in touched:
        path.chmod(stat.S_IWRITE | stat.S_IREAD)


# ===========================================================================
# 1. Happy Path - detect_encoding_and_bom
# ===========================================================================


def test_detect_plain_ascii_is_utf8_without_bom(write):
    assert detect_encoding_and_bom(write("a.txt", b"hello world\n")) == ("utf-8", False)


def test_detect_utf8_with_umlauts_without_bom(write):
    path = write("u.txt", "Grüezi mitenand — ÄÖÜ\n".encode("utf-8"))
    assert detect_encoding_and_bom(path) == ("utf-8", False)


@pytest.mark.parametrize(
    ("bom", "expected"),
    [
        (b"\xef\xbb\xbf", "utf-8-sig"),
        (b"\xff\xfe", "utf-16-le"),
        (b"\xfe\xff", "utf-16-be"),
        (b"\xff\xfe\x00\x00", "utf-32-le"),
        (b"\x00\x00\xfe\xff", "utf-32-be"),
    ],
)
def test_detect_recognises_every_bom(write, bom, expected):
    path = write("bom.txt", bom + b"rest of the file")
    assert detect_encoding_and_bom(path) == (expected, True)


def test_detect_falls_back_to_cp1252_for_non_utf8_bytes(write):
    # 0xe9 ist als einzelnes Byte kein gueltiges UTF-8; in cp1252 wie in latin-1
    # ist es "é" - cp1252 wird zuerst probiert und gewinnt.
    assert detect_encoding_and_bom(write("l.txt", b"caf\xe9\n")) == ("cp1252", False)


def test_detect_accepts_str_path(write):
    """Die Signatur sagt Path, dank open() funktioniert str aber genauso."""
    path = write("s.txt", b"plain\n")
    assert detect_encoding_and_bom(str(path)) == ("utf-8", False)


# ===========================================================================
# 2. Grenzwerte - detect_encoding_and_bom / is_binary
# ===========================================================================


def test_detect_empty_file_counts_as_utf8(write):
    """Leere Datei: kein BOM, und b"" dekodiert fehlerfrei als UTF-8."""
    assert detect_encoding_and_bom(write("empty.txt", b"")) == ("utf-8", False)


def test_detect_bom_only_file_is_utf8_sig(write):
    """Genau 3 Bytes - kuerzer als der 4-Byte-Lesepuffer."""
    assert detect_encoding_and_bom(write("bom.txt", b"\xef\xbb\xbf")) == ("utf-8-sig", True)


def test_detect_truncated_bom_is_not_a_bom(write):
    """Zwei von drei BOM-Bytes sind kein BOM - und kein gueltiges UTF-8."""
    assert detect_encoding_and_bom(write("t.txt", b"\xef\xbb")) == ("cp1252", False)


def test_detect_utf8_multibyte_split_at_read_boundary(write):
    """Das 4-Byte-Fenster darf ein Mehrbyte-Zeichen zerschneiden - fuer die
    Erkennung wird ohnehin die ganze Datei dekodiert."""
    path = write("m.txt", b"abc" + "ä".encode("utf-8") * 100)
    assert detect_encoding_and_bom(path) == ("utf-8", False)


def test_is_binary_detects_nul_in_first_block(write):
    assert is_binary(write("b.bin", b"A" * 100 + b"\x00" + b"B" * 100)) is True


def test_is_binary_nul_at_last_byte_of_first_block(write):
    """Grenzwert: NUL an Offset 8191 liegt noch im gelesenen Block."""
    assert is_binary(write("b.bin", b"A" * 8191 + b"\x00")) is True


def test_is_binary_misses_nul_directly_after_first_block(write):
    """Grenzwert, den ein fauler Entwickler vergisst: NUL an Offset 8192 liegt
    genau ein Byte hinter dem Lesefenster - die Datei gilt als Text."""
    assert is_binary(write("b.bin", b"A" * 8192 + b"\x00")) is False


def test_is_binary_empty_file_is_text(write):
    assert is_binary(write("empty.txt", b"")) is False


# ===========================================================================
# 3. Ungueltige Eingaben / falsche Typen
# ===========================================================================


@pytest.mark.parametrize(
    "func", [is_binary, detect_encoding_and_bom, convert_to_utf8_no_bom]
)
@pytest.mark.parametrize("bad", [None, 1.5, [], {"path": "x"}])
def test_functions_reject_non_path_types(func, bad):
    with pytest.raises(TypeError):
        func(bad)


def test_int_argument_is_treated_as_file_descriptor_not_as_path():
    """Faellt gern durch: int ist fuer open() kein Pfad, sondern ein fd.
    Ein geschlossener fd liefert daher OSError statt TypeError."""
    fd = os.open(os.devnull, os.O_RDONLY)
    os.close(fd)
    with pytest.raises(OSError):
        is_binary(fd)


def test_missing_file_raises_filenotfound(tmp_path):
    with pytest.raises(FileNotFoundError):
        detect_encoding_and_bom(tmp_path / "does-not-exist.txt")


def test_directory_argument_raises_oserror(tmp_path):
    """IsADirectoryError (POSIX) bzw. PermissionError (Windows) - beides OSError."""
    with pytest.raises(OSError):
        is_binary(tmp_path)


def test_convert_raises_on_unknown_encoding(write, monkeypatch):
    """Der ValueError-Pfad ist nur erreichbar, wenn die Erkennung "unknown" liefert."""
    path = write("x.txt", b"whatever")
    monkeypatch.setattr(
        check_encoding, "detect_encoding_and_bom", lambda _p: ("unknown", False)
    )
    with pytest.raises(ValueError, match="Cannot determine encoding"):
        convert_to_utf8_no_bom(path)


# ===========================================================================
# 4. Happy Path - convert_to_utf8_no_bom
# ===========================================================================


def test_convert_strips_utf8_bom(write):
    text = "Grüezi\n"
    path = write("s.txt", b"\xef\xbb\xbf" + text.encode("utf-8"))
    convert_to_utf8_no_bom(path)
    assert path.read_bytes() == text.encode("utf-8")
    assert detect_encoding_and_bom(path) == ("utf-8", False)


def test_convert_latin1_to_utf8(write):
    text = "café\n"
    path = write("l.txt", text.encode("latin-1"))
    convert_to_utf8_no_bom(path)
    assert path.read_bytes() == text.encode("utf-8")


@pytest.mark.parametrize(
    ("codec", "bom"),
    [
        ("utf-16-le", b"\xff\xfe"),
        ("utf-16-be", b"\xfe\xff"),
        ("utf-32-le", b"\xff\xfe\x00\x00"),
        ("utf-32-be", b"\x00\x00\xfe\xff"),
    ],
)
def test_convert_utf16_and_utf32_leave_no_bom_behind(write, codec, bom):
    """Der endian-spezifische Codec wuerde U+FEFF im Text stehen lassen und als
    UTF-8-BOM zurueckschreiben - genau das darf nicht mehr passieren."""
    text = "Zürich\n"
    path = write("w.txt", bom + text.encode(codec))
    convert_to_utf8_no_bom(path)
    assert path.read_bytes() == text.encode("utf-8")
    assert detect_encoding_and_bom(path) == ("utf-8", False)


def test_convert_bom_only_file_becomes_empty(write):
    path = write("b.txt", b"\xef\xbb\xbf")
    convert_to_utf8_no_bom(path)
    assert path.read_bytes() == b""


def test_convert_is_idempotent_and_byte_stable(write):
    """Zweiter Lauf darf nichts mehr veraendern - und der erste Lauf darf eine
    saubere UTF-8-Datei nicht anfassen (kein BOM, kein Newline angehaengt)."""
    original = "schon sauber: äöü\n".encode("utf-8")
    path = write("ok.txt", original)
    convert_to_utf8_no_bom(path)
    assert path.read_bytes() == original
    convert_to_utf8_no_bom(path)
    assert path.read_bytes() == original


def test_convert_preserves_crlf_line_endings(write):
    """Klassischer vergessener Fall: ohne newline="" wuerde Python die CRLF beim
    Lesen zu LF normalisieren und beim Schreiben wieder aufblaehen."""
    path = write("crlf.txt", "a\r\nb\r\n".encode("latin-1"))
    convert_to_utf8_no_bom(path)
    assert path.read_bytes() == b"a\r\nb\r\n"


def test_convert_preserves_mixed_line_endings(write):
    path = write("mixed.txt", b"a\r\nb\nc\rd")
    convert_to_utf8_no_bom(path)
    assert path.read_bytes() == b"a\r\nb\nc\rd"


def test_convert_file_without_trailing_newline(write):
    text = "kein Newline: ü"
    path = write("n.txt", text.encode("latin-1"))
    convert_to_utf8_no_bom(path)
    assert path.read_bytes() == text.encode("utf-8")


# ===========================================================================
# 5. Faelle, die ein fauler Entwickler vergisst
# ===========================================================================


def test_fallback_never_reports_unknown(write):
    """latin-1 als letzter Kandidat dekodiert JEDE Bytefolge - "unknown" und
    damit der ValueError in convert_to_utf8_no_bom sind unerreichbar. Der
    Rueckgabewert bleibt reine Absicherung."""
    for chunk in (b"\x00", b"\x81\x8d\x90\x9d", bytes(range(256))):
        path = write("any.bin", chunk)
        encoding, has_bom = detect_encoding_and_bom(path)
        assert has_bom is False
        assert encoding in ("utf-8", "cp1252", "latin-1")


def test_cp1252_smart_quotes_survive_the_conversion(write):
    """0x93/0x94 sind in cp1252 typografische Anfuehrungszeichen. Mit latin-1
    zuerst wuerden daraus die C1-Steuerzeichen U+0093/U+0094 - stiller
    Datenverlust ohne jede Fehlermeldung."""
    path = write("word.txt", b"\x93Zitat\x94")
    assert detect_encoding_and_bom(path) == ("cp1252", False)
    convert_to_utf8_no_bom(path)
    content = path.read_text(encoding="utf-8")
    assert content == "“Zitat”"
    assert content != "\x93Zitat\x94"  # das waere die latin-1-Lesart


def test_cp1252_only_bytes_are_decoded_correctly(write):
    """Die uebrigen 0x80-0x9f-Bytes, die latin-1 verstuemmeln wuerde."""
    path = write("chars.txt", b"\x80 \x85 \x91 \x96 \x99")
    assert detect_encoding_and_bom(path) == ("cp1252", False)
    convert_to_utf8_no_bom(path)
    assert path.read_text(encoding="utf-8") == "€ … ‘ – ™"


def test_bytes_undefined_in_cp1252_fall_through_to_latin1(write):
    """Genau diese fuenf Bytes sind in cp1252 nicht belegt - erst dafuer ist der
    latin-1-Zweig da, und nur so bleibt er ueberhaupt erreichbar."""
    for byte in (b"\x81", b"\x8d", b"\x8f", b"\x90", b"\x9d"):
        path = write("undef.txt", b"text" + byte)
        assert detect_encoding_and_bom(path) == ("latin-1", False)


def test_single_undefined_byte_drops_whole_file_to_latin1(write):
    """Vergessener Fall: ein einziges undefiniertes Byte kippt die Erkennung -
    die Anfuehrungszeichen derselben Datei werden dann doch zu C1-Zeichen."""
    path = write("mixed.txt", b"\x93Zitat\x94\x81")
    assert detect_encoding_and_bom(path) == ("latin-1", False)
    convert_to_utf8_no_bom(path)
    assert path.read_text(encoding="utf-8") == "\x93Zitat\x94\x81"


def test_utf16_without_bom_is_mistaken_for_utf8(write):
    """Ueberraschend: ASCII-in-UTF-16-LE ist Byte fuer Byte gueltiges UTF-8 (NUL
    ist ein legales UTF-8-Zeichen). Die Erkennung meldet also "utf-8, kein BOM"
    und wuerde die Datei unangetastet lassen - nur is_binary() rettet sie, weil
    die NUL-Bytes sie als Binaerdatei markieren."""
    path = write("u16.txt", "hallo".encode("utf-16-le"))
    assert detect_encoding_and_bom(path) == ("utf-8", False)
    assert is_binary(path) is True


def test_convert_replaces_in_place_without_backup(write):
    """Die Datei wird in-place ueberschrieben - gleicher Pfad, keine Sicherung."""
    path = write("p.txt", "ü".encode("latin-1"))
    before = sorted(p.name for p in path.parent.iterdir())
    convert_to_utf8_no_bom(path)
    assert sorted(p.name for p in path.parent.iterdir()) == before


def test_readonly_file_is_still_readable(write, readonly):
    """Lesen ist vom Schreibschutz nicht betroffen - die Erkennung laeuft normal."""
    path = readonly(write("ro.txt", "testAeoeue".encode("cp1252")))
    assert is_binary(path) is False
    assert detect_encoding_and_bom(path) == ("utf-8", False)


def test_convert_on_readonly_file_raises_without_truncating(write, readonly):
    """Vergessener Fall: die Zieldatei ist schreibgeschuetzt. open(..., "w")
    kuerzt die Datei beim Oeffnen - schlaegt schon das Oeffnen fehl, bleibt der
    Inhalt zum Glueck vollstaendig erhalten. Kein halb geschriebener Rest."""
    original = "testÄöü".encode("cp1252")
    path = readonly(write("ro.txt", original))
    assert detect_encoding_and_bom(path) == ("cp1252", False)

    with pytest.raises(PermissionError):
        convert_to_utf8_no_bom(path)

    assert path.read_bytes() == original


# ===========================================================================
# 6. uncommitted_files (echtes Git-Repo)
# ===========================================================================


def test_uncommitted_files_finds_untracked_file(git_repo):
    (git_repo / "new.txt").write_bytes(b"hi\n")
    repo_root, files = uncommitted_files(git_repo)
    assert repo_root.samefile(git_repo)
    assert [f.name for f in files] == ["new.txt"]
    assert files[0].is_absolute()


def test_uncommitted_files_finds_modified_and_staged(git_repo):
    _commit(git_repo, "tracked.txt", b"v1\n")
    (git_repo / "tracked.txt").write_bytes(b"v2\n")
    (git_repo / "staged.txt").write_bytes(b"neu\n")
    _git(git_repo, "add", "--", "staged.txt")
    _, files = uncommitted_files(git_repo)
    assert sorted(f.name for f in files) == ["staged.txt", "tracked.txt"]


def test_uncommitted_files_ignores_clean_repo(git_repo):
    _commit(git_repo, "clean.txt", b"nichts zu tun\n")
    _, files = uncommitted_files(git_repo)
    assert files == []


def test_uncommitted_files_drops_deleted_entries(git_repo):
    _commit(git_repo, "gone.txt", b"weg\n")
    (git_repo / "gone.txt").unlink()
    (git_repo / "still.txt").write_bytes(b"da\n")
    _, files = uncommitted_files(git_repo)
    assert [f.name for f in files] == ["still.txt"]


def test_uncommitted_files_skips_rename_source(git_repo):
    """Bei -z folgt dem Rename-Eintrag der Quellpfad als eigener Eintrag. Wird er
    nicht uebersprungen, geraet das Parsing aus dem Tritt."""
    _commit(git_repo, "old.txt", b"inhalt\n")
    _git(git_repo, "mv", "old.txt", "new.txt")
    (git_repo / "zzz.txt").write_bytes(b"nachfolger\n")
    _, files = uncommitted_files(git_repo)
    assert sorted(f.name for f in files) == ["new.txt", "zzz.txt"]


def test_uncommitted_files_keeps_paths_with_spaces(git_repo):
    """Genau dafuer ist -z da - im Zeilenmodus waere der Pfad zusaetzlich
    in Anfuehrungszeichen gequotet."""
    (git_repo / "mit leerzeichen.txt").write_bytes(b"x\n")
    _, files = uncommitted_files(git_repo)
    assert [f.name for f in files] == ["mit leerzeichen.txt"]


def test_uncommitted_files_keeps_non_ascii_paths(git_repo):
    """Im -z-Modus quotet git nicht (kein core.quotepath-Oktal-Escape), der Pfad
    muesste also 1:1 ankommen."""
    name = "Grüezi.txt"
    (git_repo / name).write_bytes(b"x\n")
    _, files = uncommitted_files(git_repo)
    assert [f.name for f in files] == [name]
    assert files[0].is_file()


def test_uncommitted_files_returns_no_directories(git_repo):
    """-uall listet Dateien einzeln auf; der is_file()-Filter haelt Verzeichnisse
    zusaetzlich draussen."""
    (git_repo / "sub").mkdir()
    (git_repo / "sub" / "inner.txt").write_bytes(b"x\n")
    _, files = uncommitted_files(git_repo)
    assert [f.relative_to(git_repo).as_posix() for f in files] == ["sub/inner.txt"]
    assert all(f.is_file() for f in files)


def test_uncommitted_files_scope_narrows_result(git_repo):
    (git_repo / "root.txt").write_bytes(b"x\n")
    (git_repo / "sub").mkdir()
    (git_repo / "sub" / "inner.txt").write_bytes(b"x\n")
    repo_root, files = uncommitted_files(git_repo / "sub")
    assert repo_root.samefile(git_repo)
    assert [f.name for f in files] == ["inner.txt"]


def test_uncommitted_files_outside_repo_raises(tmp_path):
    outside = tmp_path / "kein_repo"
    outside.mkdir()
    with pytest.raises(subprocess.CalledProcessError):
        uncommitted_files(outside)


def test_uncommitted_files_missing_scope_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        uncommitted_files(tmp_path / "gibt-es-nicht")


# ===========================================================================
# 7. main() - Zusammenspiel und Exit-Codes
# ===========================================================================


def test_main_converts_and_reports(git_repo, monkeypatch, capsys):
    latin = "café\n"
    clean = "schon utf-8: ü\n"
    (git_repo / "latin.txt").write_bytes(latin.encode("latin-1"))
    (git_repo / "clean.txt").write_bytes(clean.encode("utf-8"))
    monkeypatch.setattr(sys, "argv", ["check_encoding_m4.py", str(git_repo)])

    assert main() == 0

    out = capsys.readouterr().out
    assert "Files checked: 2" in out
    assert "Files changed: 1" in out
    assert "latin.txt" in out
    assert (git_repo / "latin.txt").read_bytes() == latin.encode("utf-8")
    assert (git_repo / "clean.txt").read_bytes() == clean.encode("utf-8")


def test_main_without_argument_uses_cwd(git_repo, monkeypatch, capsys):
    (git_repo / "x.txt").write_bytes(b"ok\n")
    monkeypatch.setattr(sys, "argv", ["check_encoding_m4.py"])
    monkeypatch.chdir(git_repo)

    assert main() == 0
    assert "Files checked: 1" in capsys.readouterr().out


def test_main_on_clean_repo_returns_zero(git_repo, monkeypatch, capsys):
    _commit(git_repo, "clean.txt", b"nichts\n")
    monkeypatch.setattr(sys, "argv", ["check_encoding_m4.py", str(git_repo)])

    assert main() == 0
    out = capsys.readouterr().out
    assert "No uncommitted files found" in out
    assert "Files checked: 0" in out


def test_main_skips_binary_files_without_counting_them_as_checked(
    git_repo, monkeypatch, capsys
):
    """Vergessener Fall: Binaerdateien zaehlen weder als geprueft noch als
    geaendert - und duerfen auf keinen Fall konvertiert werden."""
    payload = b"PNG\x00\x01\x02\xff\xfe"
    (git_repo / "image.png").write_bytes(payload)
    monkeypatch.setattr(sys, "argv", ["check_encoding_m4.py", str(git_repo)])

    assert main() == 0
    out = capsys.readouterr().out
    assert "binary, skipped" in out
    assert "Files checked: 0" in out
    assert "Files skipped (binary): 1" in out
    assert (git_repo / "image.png").read_bytes() == payload


def test_main_returns_one_when_git_fails(tmp_path, monkeypatch, capsys):
    outside = tmp_path / "kein_repo"
    outside.mkdir()
    monkeypatch.setattr(sys, "argv", ["check_encoding_m4.py", str(outside)])

    assert main() == 1
    assert "ERROR: git failed" in capsys.readouterr().out


def test_main_returns_one_when_conversion_fails(git_repo, monkeypatch, capsys):
    (git_repo / "latin.txt").write_bytes(b"caf\xe9\n")
    monkeypatch.setattr(sys, "argv", ["check_encoding_m4.py", str(git_repo)])

    def boom(_path):
        raise PermissionError("file is locked")

    monkeypatch.setattr(check_encoding, "convert_to_utf8_no_bom", boom)

    assert main() == 1
    out = capsys.readouterr().out
    assert "Errors:" in out
    assert "file is locked" in out
    assert (git_repo / "latin.txt").read_bytes() == b"caf\xe9\n"


def test_main_reports_relative_labels_with_forward_slashes(
    git_repo, monkeypatch, capsys
):
    """Auch auf Windows sollen Labels mit / ausgegeben werden."""
    (git_repo / "sub").mkdir()
    (git_repo / "sub" / "deep.txt").write_bytes(b"ok\n")
    monkeypatch.setattr(sys, "argv", ["check_encoding_m4.py", str(git_repo)])

    assert main() == 0
    out = capsys.readouterr().out
    assert "sub/deep.txt" in out
    assert "sub\\deep.txt" not in out


def test_main_reports_readonly_file_as_error(git_repo, readonly, monkeypatch, capsys):
    """Ende zu Ende mit echtem Schreibschutz statt gemocktem Fehler: Exit 1, die
    Datei taucht in der Fehlerliste auf und bleibt unveraendert liegen."""
    original = "testÄöü".encode("cp1252")
    path = git_repo / "test.txt"
    path.write_bytes(original)
    readonly(path)
    monkeypatch.setattr(sys, "argv", ["check_encoding_m4.py", str(git_repo)])

    assert main() == 1

    out = capsys.readouterr().out
    assert "Errors:" in out
    assert "Failed to convert test.txt" in out
    assert "Files checked: 1" in out
    assert "Files changed: 0" in out
    assert path.read_bytes() == original


def test_main_leaves_readonly_utf8_file_alone(git_repo, readonly, monkeypatch, capsys):
    """Der Schreibschutz stoert nur, wenn wirklich konvertiert wird - eine schon
    saubere Datei wird nie zum Schreiben geoeffnet."""
    original = ("schon sauber: ü" + chr(10)).encode("utf-8")
    path = git_repo / "clean.txt"
    path.write_bytes(original)
    readonly(path)
    monkeypatch.setattr(sys, "argv", ["check_encoding_m4.py", str(git_repo)])

    assert main() == 0

    out = capsys.readouterr().out
    assert "Files checked: 1" in out
    assert "Files changed: 0" in out
    assert path.read_bytes() == original
