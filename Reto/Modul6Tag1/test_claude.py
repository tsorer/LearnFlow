"""M3 (Tag 1, Modul 6): Von Claude generierte pytest-Tests fuer mycode.py.
Deckt ab: Happy Path, Grenzwerte, ungueltige Eingaben (falsche Typen),
und Faelle, die leicht vergessen werden.
"""
import pytest

from mycode import ist_upload_gueltig, MAXIMALE_GROESSE_BYTES


# --- Happy Path ---

@pytest.mark.parametrize("dateiname", ["bericht.pdf", "vertrag.docx", "notizen.md"])
def test_alle_erlaubten_endungen_werden_akzeptiert(dateiname):
    ok, grund = ist_upload_gueltig(dateiname, 1000)
    assert ok is True
    assert grund == ""


# --- Grenzwerte ---

def test_groesse_null_ist_gueltig():
    ok, _ = ist_upload_gueltig("leer.pdf", 0)
    assert ok is True


def test_groesse_genau_maximum_ist_noch_gueltig():
    ok, _ = ist_upload_gueltig("grenz.pdf", MAXIMALE_GROESSE_BYTES)
    assert ok is True


def test_groesse_ein_byte_ueber_maximum_ist_ungueltig():
    ok, grund = ist_upload_gueltig("zu_gross.pdf", MAXIMALE_GROESSE_BYTES + 1)
    assert ok is False
    assert grund != ""


def test_negative_groesse_ist_ungueltig():
    ok, grund = ist_upload_gueltig("negativ.pdf", -1)
    assert ok is False
    assert grund != ""


# --- Ungueltige Eingaben (falsche Typen) ---

def test_groesse_als_string_wirft_typeerror():
    with pytest.raises(TypeError):
        ist_upload_gueltig("bericht.pdf", "500")


def test_groesse_als_none_wirft_typeerror():
    with pytest.raises(TypeError):
        ist_upload_gueltig("bericht.pdf", None)


def test_dateiname_als_none_wirft_fehler():
    with pytest.raises(AttributeError):
        ist_upload_gueltig(None, 500)


def test_dateiname_als_zahl_wirft_fehler():
    with pytest.raises(AttributeError):
        ist_upload_gueltig(12345, 500)


# --- Faelle, die ein fauler Entwickler vergessen wuerde ---

def test_endung_gross_geschrieben_wird_akzeptiert():
    """Case-Insensitivitaet der Endung (.PDF statt .pdf)."""
    ok, _ = ist_upload_gueltig("BERICHT.PDF", 500)
    assert ok is True


def test_dateiname_ohne_punkt_wird_abgelehnt():
    ok, grund = ist_upload_gueltig("ohnepunkt", 500)
    assert ok is False
    assert grund != ""


def test_leerer_dateiname_wird_abgelehnt():
    ok, grund = ist_upload_gueltig("", 500)
    assert ok is False
    assert grund != ""


def test_mehrere_punkte_im_dateinamen_nutzt_letzte_endung():
    """z.B. 'archiv.tar.pdf' -- nur die letzte Endung zaehlt."""
    ok, _ = ist_upload_gueltig("archiv.tar.pdf", 500)
    assert ok is True


def test_dateiname_nur_punkt_und_endung_ohne_namen():
    """Randfall: '.pdf' hat keinen eigentlichen Dateinamen, wird aber
    von der aktuellen Implementierung als gueltig durchgelassen."""
    ok, _ = ist_upload_gueltig(".pdf", 500)
    assert ok is True
