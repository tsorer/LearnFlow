import pytest

from app.exceptions import EmbeddingConfigError
from app.services.embedding_config import (
    EmbeddingConfig,
    embedding_config_from,
    verify_embedding_config,
)


def test_parses_a_complete_row_set() -> None:
    values = {"embed_model": "text-embedding-3-small", "embed_dimensions": "1536"}

    config = embedding_config_from(values)

    assert config == EmbeddingConfig(model="text-embedding-3-small", dimensions=1536)


@pytest.mark.parametrize(
    "values",
    [
        {},  # migration 0018 seeds both rows unconditionally -- missing means not migrated
        {"embed_dimensions": "1536"},
        {"embed_model": "", "embed_dimensions": "1536"},
        {"embed_model": "   ", "embed_dimensions": "1536"},
    ],
)
def test_missing_or_empty_model_fails_closed(values: dict[str, str]) -> None:
    with pytest.raises(EmbeddingConfigError):
        embedding_config_from(values)


@pytest.mark.parametrize(
    "raw_dimensions",
    ["abc", "0", "-1", "2001", ""],
)
def test_unusable_dimensions_fail_closed(raw_dimensions: str) -> None:
    values = {"embed_model": "text-embedding-3-small", "embed_dimensions": raw_dimensions}

    with pytest.raises(EmbeddingConfigError):
        embedding_config_from(values)


def test_2000_dimensions_is_the_accepted_upper_bound() -> None:
    values = {"embed_model": "text-embedding-3-large", "embed_dimensions": "2000"}

    assert embedding_config_from(values).dimensions == 2000


def test_model_value_is_stripped() -> None:
    """Not just validated as non-empty after stripping, but actually stored
    stripped -- otherwise a value with incidental whitespace (a stray `psql`
    edit, a copy-paste) would never equal Settings' clean one in
    verify_embedding_config, a false-positive drift lockout."""
    values = {"embed_model": "  text-embedding-3-small  ", "embed_dimensions": "1536"}

    assert embedding_config_from(values).model == "text-embedding-3-small"


def test_matching_configuration_does_not_raise() -> None:
    config = EmbeddingConfig(model="text-embedding-3-small", dimensions=1536)

    verify_embedding_config(config, config)


@pytest.mark.parametrize(
    ("persisted", "configured"),
    [
        (
            EmbeddingConfig(model="text-embedding-3-small", dimensions=1536),
            EmbeddingConfig(model="bge-m3", dimensions=1536),
        ),
        (
            EmbeddingConfig(model="text-embedding-3-small", dimensions=1536),
            EmbeddingConfig(model="text-embedding-3-small", dimensions=1024),
        ),
    ],
)
def test_model_or_dimension_drift_raises(
    persisted: EmbeddingConfig, configured: EmbeddingConfig
) -> None:
    """Same dimension, different model (T-42's actual bug: pgvector can't tell
    two 1536-dim models apart) and same model, different dimension both count
    as drift -- neither should be waved through."""
    with pytest.raises(EmbeddingConfigError):
        verify_embedding_config(persisted, configured)
