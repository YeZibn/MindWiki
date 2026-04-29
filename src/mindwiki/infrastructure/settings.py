"""Application settings placeholders."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOTENV_PATH = PROJECT_ROOT / ".env"


def _load_dotenv_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a local `.env` file."""

    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ[key] = value


@dataclass(slots=True)
class Settings:
    database_url: str = ""
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model_id: str = ""
    llm_model_mini_id: str = ""
    llm_timeout_ms: int = 30000
    llm_rerank_base_url: str = ""
    llm_rerank_api_key: str = ""
    llm_rerank_model_id: str = ""
    llm_rerank_timeout_ms: int = 30000
    llm_embedding_base_url: str = ""
    llm_embedding_api_key: str = ""
    llm_embedding_model_id: str = ""
    llm_embedding_timeout_ms: int = 30000
    milvus_uri: str = ""
    milvus_token: str = ""
    milvus_collection_name: str = "mindwiki_chunks"


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "")
    if not raw_value:
        return default

    try:
        return int(raw_value)
    except ValueError:
        return default


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv_file(DOTENV_PATH)
    return Settings(
        database_url=os.getenv("MINDWIKI_DATABASE_URL", ""),
        llm_base_url=os.getenv("LLM_BASE_URL", ""),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_model_id=os.getenv("LLM_MODEL_ID", ""),
        llm_model_mini_id=os.getenv("LLM_MODEL_MINI_ID", ""),
        llm_timeout_ms=_get_int_env("LLM_TIMEOUT_MS", 30000),
        llm_rerank_base_url=os.getenv("LLM_RERANK_BASE_URL", ""),
        llm_rerank_api_key=os.getenv("LLM_RERANK_API_KEY", ""),
        llm_rerank_model_id=os.getenv("LLM_RERANK_MODEL_ID", ""),
        llm_rerank_timeout_ms=_get_int_env("LLM_RERANK_TIMEOUT_MS", 30000),
        llm_embedding_base_url=os.getenv("LLM_EMBEDDING_BASE_URL", ""),
        llm_embedding_api_key=os.getenv("LLM_EMBEDDING_API_KEY", ""),
        llm_embedding_model_id=os.getenv("LLM_EMBEDDING_MODEL_ID", ""),
        llm_embedding_timeout_ms=_get_int_env("LLM_EMBEDDING_TIMEOUT_MS", 30000),
        milvus_uri=os.getenv("SYSTEM_MEMORY_MILVUS_URI", os.getenv("MILVUS_URI", "")),
        milvus_token=os.getenv("SYSTEM_MEMORY_MILVUS_TOKEN", os.getenv("MILVUS_TOKEN", "")),
        milvus_collection_name=os.getenv("MILVUS_COLLECTION_NAME", "mindwiki_chunks"),
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()
