import litellm
from app.config import settings


async def embed(texts: list[str]) -> list[list[float]]:
    kwargs = {
        "model": settings.embed_model,
        "input": texts,
        "api_key": settings.openai_api_key,
    }
    if settings.litellm_base_url:
        kwargs["api_base"] = settings.litellm_base_url
        kwargs["api_version"] = settings.litellm_api_version
        kwargs["api_key"] = settings.litellm_api_key

    response = await litellm.aembedding(**kwargs)
    return [item["embedding"] for item in response.data]


async def embed_one(text: str) -> list[float]:
    results = await embed([text])
    return results[0]
