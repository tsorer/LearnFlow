"""M2 (Tag 1, Modul 6): 3 handgeschriebene pytest-Tests fuer mycode.py.
Kein Delegieren -- Ziel ist, das Prinzip selbst anzuwenden, bevor Claude testet (M3).
"""
from mycode import ist_upload_gueltig


def test_gueltige_pdf():
    """Happy Path: kleine, erlaubte Datei."""
    assert ist_upload_gueltig("bericht.pdf", 500) == (True, "")


def test_grenzwert_10mb_ist_noch_gueltig():
    """Edge Case: genau 10 MB soll laut Spec noch erlaubt sein (>, nicht >=)."""
    zehn_mb = 10 * 1024 * 1024
    ok, _ = ist_upload_gueltig("grosse_datei.pdf", zehn_mb)
    assert ok is True


def test_falsches_format_wird_abgelehnt():
    """Edge Case: nicht erlaubte Dateiendung."""
    ok, grund = ist_upload_gueltig("programm.exe", 500)
    assert ok is False
    assert grund != ""


def test_negative_groesse_wirft_valueerror():
    """M4: NEUE Anforderung, die der aktuelle Code noch nicht erfuellt --
    soll den Generator im Orchestrator zu einer Nachbesserung zwingen."""
    import pytest
    with pytest.raises(ValueError):
        ist_upload_gueltig("bericht.pdf", -1)
