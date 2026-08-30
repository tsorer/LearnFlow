def band_for(score: float, medium: float, high: float) -> str:
    if score >= high:
        return 'hoch'
    if score >= medium:
        return 'mittel'
    return 'niedrig'


if __name__ == "__main__":
    # T1 – klarer 'hoch'-Fall
    assert band_for(0.9, 0.5, 0.8) == 'hoch', "T1: score=0.9 sollte 'hoch' ergeben"

    # T2 – klarer 'mittel'-Fall
    assert band_for(0.6, 0.5, 0.8) == 'mittel', "T2: score=0.6 sollte 'mittel' ergeben"

    # T3 – klarer 'niedrig'-Fall
    assert band_for(0.3, 0.5, 0.8) == 'niedrig', "T3: score=0.3 sollte 'niedrig' ergeben"

    # T4 – Score genau auf high
    assert band_for(0.8, 0.5, 0.8) == 'hoch', "T4: score genau auf high sollte 'hoch' ergeben"

    # T5 – Score genau auf medium
    assert band_for(0.5, 0.5, 0.8) == 'mittel', "T5: score genau auf medium sollte 'mittel' ergeben"

    # T6 – medium == high, Score auf Schwelle (Mittelband unerreichbar)
    assert band_for(0.6, 0.6, 0.6) == 'hoch', "T6: medium==high, score auf Schwelle sollte 'hoch' ergeben"

    # T7 – Score knapp unter medium
    assert band_for(0.4999, 0.5, 0.8) == 'niedrig', "T7: score knapp unter medium sollte 'niedrig' ergeben"

    print("Alle Tests bestanden.")
