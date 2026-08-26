def band_for(score: float, medium: float, high: float) -> str:
    if not (0.0 <= score <= 1.0):
        raise ValueError(f"score muss im Bereich [0.0, 1.0] liegen, ist aber {score}")
    if not (0.0 <= medium <= 1.0):
        raise ValueError(f"medium muss im Bereich [0.0, 1.0] liegen, ist aber {medium}")
    if not (0.0 <= high <= 1.0):
        raise ValueError(f"high muss im Bereich [0.0, 1.0] liegen, ist aber {high}")
    if medium >= high:
        raise ValueError(f"medium muss strikt kleiner als high sein, aber medium={medium} >= high={high}")
    if score >= high:
        return 'hoch'
    if score >= medium:
        return 'mittel'
    return 'niedrig'


def test_normalfall_unter_medium():
    assert band_for(0.29, 0.3, 0.7) == 'niedrig'


def test_normalfall_auf_medium():
    assert band_for(0.30, 0.3, 0.7) == 'mittel'


def test_normalfall_zwischen_schwellen():
    assert band_for(0.31, 0.3, 0.7) == 'mittel'


def test_normalfall_knapp_unter_high():
    assert band_for(0.69, 0.3, 0.7) == 'mittel'


def test_normalfall_auf_high():
    assert band_for(0.70, 0.3, 0.7) == 'hoch'


def test_normalfall_ueber_high():
    assert band_for(0.71, 0.3, 0.7) == 'hoch'


def test_score_minimum():
    assert band_for(0.0, 0.3, 0.7) == 'niedrig'


def test_score_maximum():
    assert band_for(1.0, 0.3, 0.7) == 'hoch'


def test_medium_gleich_high_mitte():
    import pytest
    with pytest.raises(ValueError):
        band_for(0.5, 0.5, 0.5)


def test_medium_gleich_high_rand():
    import pytest
    with pytest.raises(ValueError):
        band_for(0.0, 0.3, 0.3)


def test_schwelle_medium_null():
    assert band_for(0.0, 0.0, 0.5) == 'mittel'


def test_schwelle_score_auf_high_null_medium():
    assert band_for(0.5, 0.0, 0.5) == 'hoch'


def test_schwelle_score_auf_medium_oben():
    assert band_for(0.5, 0.5, 1.0) == 'mittel'


def test_schwelle_score_auf_high_eins():
    assert band_for(1.0, 0.5, 1.0) == 'hoch'


def test_score_zu_klein():
    import pytest
    with pytest.raises(ValueError):
        band_for(-0.01, 0.3, 0.7)


def test_score_zu_gross():
    import pytest
    with pytest.raises(ValueError):
        band_for(1.01, 0.3, 0.7)


def test_medium_zu_klein():
    import pytest
    with pytest.raises(ValueError):
        band_for(0.5, -0.1, 0.7)


def test_medium_zu_gross():
    import pytest
    with pytest.raises(ValueError):
        band_for(0.5, 1.1, 1.5)


def test_high_zu_gross():
    import pytest
    with pytest.raises(ValueError):
        band_for(0.5, 0.3, 1.5)


def test_medium_groesser_als_high():
    import pytest
    with pytest.raises(ValueError):
        band_for(0.5, 0.7, 0.4)
