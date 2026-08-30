def band_for(score: float, medium: float, high: float) -> str:
    if medium < 0.0:
        raise ValueError(f"medium must be >= 0.0, got {medium}")
    if medium > high:
        raise ValueError(f"medium must be <= high, got medium={medium}, high={high}")
    if high > 1.0:
        raise ValueError(f"high must be <= 1.0, got {high}")

    if score >= high:
        return 'hoch'
    if score >= medium:
        return 'mittel'
    return 'niedrig'
