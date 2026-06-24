# L3 · Testen & committen
**Zeit:** 14:30 – 15:30  
**Thema:** Verifizieren, dann sauber auf GitHub pushen

---

## Schritt 1 · Tests + Selbstverifikation (25 Min)

Erinnert euch an **Layer 2 (Verifier):** vertraut nicht blind. Lasst Claude Tests schreiben UND ausführen:

```
> Schreibe Tests für diesen Task die unsere
  Akzeptanzkriterien abdecken — auch die Edge Cases.

> führe die Tests aus und zeig mir das Ergebnis
```

Optional — zweite Meinung (Layer 2, Technik 3):
```
> Wechsle die Rolle: review diesen Code kritisch.
  Wo könnte er in Produktion brechen?
```

**Reflexionsfragen:**
- Sind alle Tests grün? Welche Edge Cases hat Claude getestet?
- Hat der kritische Review noch etwas gefunden?

---

## Schritt 2 · Branch, Commit & Push (35 Min)

Nutzt euren Git-Workflow aus Modul 4: eigener Branch, dann Pull Request. Niemand pusht direkt in `main`.

```
> Erstelle einen Branch feature/TASK-XXX-beschreibung,
  committe unsere Änderungen mit einer sinnvollen
  deutschen Commit-Message und pushe den Branch.
```

Dann auf GitHub: Pull Request öffnen (Review kommt in Modul 5A Tag 2 / Modul 6).

> **Profi-Tipp:** Bittet Claude vor dem Commit «fasse zusammen was wir geändert haben» — so bekommt ihr eine gute Commit-Message und versteht selbst nochmal den Umfang.

**Reflexionsfragen:**
- Branch-Name:
- Ist der PR offen?
