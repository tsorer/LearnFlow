def band_for(score: float, medium: float, high: float) -> str:
    for name, val in [("score", score), ("medium", medium), ("high", high)]:
        if not isinstance(val, (int, float)):
            raise TypeError(f"{name} muss ein numerischer Typ sein, got {type(val).__name__}")
    if medium >= high:
        raise ValueError(f"medium muss kleiner als high sein ({medium} >= {high})")
    if score >= high:
        return "hoch"
    if score >= medium:
        return "mittel"
    return "niedrig"
