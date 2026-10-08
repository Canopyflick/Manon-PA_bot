from dataclasses import dataclass
import os, logging
from typing import Optional

from dotenv import load_dotenv
load_dotenv(override=True)

logger = logging.getLogger(__name__)

@dataclass
class EnvironmentVars:
    ENV_MODE: str
    TELEGRAM_API_KEY: str
    OPENAI_API_KEY: str
    EC_OPENAI_API_KEY: str
    DATABASE_URL: str
    LANGCHAIN_TRACING_V2: bool
    LANGCHAIN_ENDPOINT: str
    LANGCHAIN_API_KEY: str
    APPROVED_USER_IDS: list[int]
    BEN_ID: int
    LANGCHAIN_PROJECT: Optional[str] = None
    AUDIO_OPENAI_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    GOALS_API_CORS_ORIGINS: Optional[str] = None
    GOALS_API_PORT: int = 8000

def detect_env_mode() -> str:
    mode = os.getenv("ENV_MODE", "").lower()
    if mode in ("dev", "prod"):
        return mode
    return "not set"

def is_running_prod() -> bool:
    return ENV_MODE == "prod"

def is_running_dev() -> bool:
    return ENV_MODE == "dev"

ENV_MODE = detect_env_mode()
logger.info(f"🛠️  Running in {ENV_MODE.upper()} mode")

def load_environment_vars() -> EnvironmentVars:
    try:
        load_dotenv(override=True)
    except ImportError:
        raise RuntimeError("dotenv module is required but not installed.")

    def get_env_var(name: str, required: bool = True) -> str | None:
        """Fetch an environment variable, log a warning if optional and missing."""
        value = os.getenv(name)
        if value is None or value.strip() == "":
            if required:
                raise ValueError(f"❌ Missing required environment variable: {name}")
            else:
                logger.warning(f"⚠️ Optional environment variable '{name}' is missing or empty.")
            return None  # Return None if missing but optional
        return value

    return EnvironmentVars(
        ENV_MODE=get_env_var('ENV_MODE'),
        TELEGRAM_API_KEY=get_env_var('TELEGRAM_API_KEY'),
        OPENAI_API_KEY=get_env_var('OPENAI_API_KEY'),
        AUDIO_OPENAI_API_KEY=get_env_var('AUDIO_OPENAI_API_KEY', required=False),
        EC_OPENAI_API_KEY=get_env_var('EC_OPENAI_API_KEY', required=False),
        DATABASE_URL=get_env_var('DATABASE_URL', required=False),
        LANGCHAIN_TRACING_V2=os.getenv('LANGCHAIN_TRACING_V2', 'false').lower() in ('true', '1'),
        LANGCHAIN_ENDPOINT=get_env_var('LANGCHAIN_ENDPOINT', required=False),
        LANGCHAIN_API_KEY=get_env_var('LANGCHAIN_API_KEY', required=False),
        LANGCHAIN_PROJECT=get_env_var('LANGCHAIN_PROJECT', required=False),
        APPROVED_USER_IDS=[
            int(uid) for uid in os.getenv("APPROVED_USER_IDS", "").split(",") if uid.strip().isdigit()
        ] if os.getenv("APPROVED_USER_IDS") else [],
        BEN_ID=int(get_env_var('BEN_ID')),
        OPENROUTER_API_KEY=get_env_var('OPENROUTER_API_KEY', required=False),
        SUPABASE_URL=get_env_var('SUPABASE_URL', required=False),
        SUPABASE_ANON_KEY=get_env_var('SUPABASE_ANON_KEY', required=False),
        GOALS_API_CORS_ORIGINS=get_env_var('GOALS_API_CORS_ORIGINS', required=False),
        GOALS_API_PORT=int(os.getenv('GOALS_API_PORT', '8000') or '8000'),
    )

# Global ENV_VARS object
ENV_VARS = load_environment_vars()
