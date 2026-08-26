```python
from __future__ import annotations

import codecs
from pathlib import Path

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


def is_utf8_encoded(path: str | Path) -> bool:
    decoder = codecs.getincrementaldecoder("utf-8")("strict")
    with open(path, "rb") as fh:
        while chunk := fh.read(_CHUNK_SIZE):
            try:
                decoder.decode(chunk)
            except UnicodeDecodeError:
                return False
    try:
        decoder.decode(b"", final=True)
    except UnicodeDecodeError:
        return False
    return True
```