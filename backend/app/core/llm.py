"""LLM client factory — returns ChatOpenAI or AzureChatOpenAI based on config."""

from langchain_openai import AzureChatOpenAI, ChatOpenAI

from app.core.config import settings


def get_llm(quality: str = "fast") -> ChatOpenAI | AzureChatOpenAI:
    """Get an LLM client.

    Args:
        quality: "fast" for scoring/decision (gpt-4o-mini), "quality" for email drafting (gpt-4o)
    """
    if settings.LLM_PROVIDER == "azure_openai":
        deployment = (
            settings.AZURE_OPENAI_DEPLOYMENT_QUALITY
            if quality == "quality"
            else settings.AZURE_OPENAI_DEPLOYMENT_FAST
        )
        return AzureChatOpenAI(
            azure_deployment=deployment,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            temperature=0.3 if quality == "fast" else 0.7,
        )

    model = (
        settings.LLM_MODEL_QUALITY if quality == "quality" else settings.LLM_MODEL_FAST
    )
    return ChatOpenAI(
        model=model,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.3 if quality == "fast" else 0.7,
    )


def has_llm_key() -> bool:
    """Check if an LLM API key is configured."""
    if settings.LLM_PROVIDER == "azure_openai":
        return bool(settings.AZURE_OPENAI_API_KEY)
    return bool(settings.OPENAI_API_KEY)
