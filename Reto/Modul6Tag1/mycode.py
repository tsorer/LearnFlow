from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024
ERLAUBTE_ENDUNGEN = {".pdf", ".docx", ".md"}


def ist_upload_gueltig(dateiname: str, groesse_bytes: int) -> tuple[bool, str]:
    endung = Path(dateiname).suffix.lower()
    if endung not in ERLAUBTE_ENDUNGEN:
        return (False, "Dateiformat nicht erlaubt. Erlaubt sind: .pdf, .docx, .md")

    if groesse_bytes < 0:
        raise ValueError("groesse_bytes darf nicht negativ sein")

    if groesse_bytes == 0:
        return (False, "Dateigrösse muss grösser als 0 Bytes sein")

    if groesse_bytes > MAX_BYTES:
        return (False, "Datei überschreitet die maximale Grösse von 10 MB")

    return (True, "")