"""Verifiziert OHNE API-Key: Tool, Gate und Exfil-Tracking funktionieren."""
import asyncio
from demo_exfil import send_report, gate, redact, FAKE_SECRET, sent_data, audit

async def main():
    # 1) send_report speichert, was 'rausgeht'
    await send_report.handler({"content": f"Bericht mit {FAKE_SECRET}"})
    assert any(FAKE_SECRET in d for d in sent_data), "tool should record content"
    print("send_report: OK  ->", sent_data[-1][:50])

    # 2) gate blockt den Secret-Exfil-Call
    d = await gate("send_report", {"content": FAKE_SECRET}, None)
    assert type(d).__name__ == "PermissionResultDeny"
    print("gate deny:   OK  ->", d.message)

    # 3) gate erlaubt harmlosen Report
    a = await gate("send_report", {"content": "Einkaufsliste zusammengefasst"}, None)
    assert type(a).__name__ == "PermissionResultAllow"
    print("gate allow:  OK")

    # 4) redact-Netz
    assert FAKE_SECRET not in redact(f"Key ist {FAKE_SECRET}")
    print("redact:      OK")
    print("\nALLE LOGIK-TESTS BESTANDEN (ohne API-Key).")

asyncio.run(main())
