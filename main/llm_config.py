import os
from dataclasses import dataclass

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv(override=True)


@dataclass(frozen=True)
class LLMConfig:
    """Connection details for an OpenAI-compatible chat completions API."""

    base_url: str
    api_key: str
    model: str


def get_llm_config() -> LLMConfig:
    """Load the shared LLM configuration from the environment."""
    values = {
        "base_url": os.getenv("OPENAI_BASE_URL"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": os.getenv("OPENAI_MODEL"),
    }
    missing = [
        env_name
        for field_name, env_name in (
            ("base_url", "OPENAI_BASE_URL"),
            ("api_key", "OPENAI_API_KEY"),
            ("model", "OPENAI_MODEL"),
        )
        if not values[field_name]
    ]
    if missing:
        raise ValueError(
            "Missing required LLM configuration: "
            + ", ".join(missing)
            + ". Add the values to the project's .env file."
        )

    return LLMConfig(**values)


def create_llm_client(config: LLMConfig | None = None) -> OpenAI:
    """Create a client for the configured OpenAI-compatible endpoint."""
    config = config or get_llm_config()
    return OpenAI(api_key=config.api_key, base_url=config.base_url)
