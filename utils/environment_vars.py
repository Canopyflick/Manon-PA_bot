from dataclasses import dataclass
import os

@dataclass
class EnvironmentVars:
    TELEGRAM_API_KEY: str
    OPENAI_API_KEY: str
    EC_OPENAI_API_KEY: str
    DATABASE_URL: str
    LANGCHAIN_TRACING_V2: bool
    LANGCHAIN_ENDPOINT: str
    LANGCHAIN_API_KEY: str
    LANGCHAIN_PROJECT: str

def is_running_on_heroku() -> bool:
    return bool(os.getenv('HEROKU_ENV'))


def is_running_locally() -> bool:
    return not is_running_on_heroku()


def load_environment_vars() -> EnvironmentVars:
    if not is_running_on_heroku():
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)
        except ImportError:
            raise

    return EnvironmentVars(
        TELEGRAM_API_KEY=os.getenv('LOCAL_TELEGRAM_API_KEY'),
        OPENAI_API_KEY=os.getenv('OPENAI_API_KEY'),
        EC_OPENAI_API_KEY=os.getenv('EC_OPENAI_API_KEY'),
        DATABASE_URL=os.getenv('DATABASE_URL') or os.getenv('LOCAL_DB_URL'),
        LANGCHAIN_TRACING_V2=os.getenv('LANGCHAIN_TRACING_V2', 'false').lower() in ('true', '1'),
        LANGCHAIN_ENDPOINT=os.getenv('LANGCHAIN_ENDPOINT'),
        LANGCHAIN_API_KEY=os.getenv('LANGCHAIN_API_KEY'),
        LANGCHAIN_PROJECT=os.getenv('LANGCHAIN_PROJECT')
    )

# Global ENV_VARS object
ENV_VARS = load_environment_vars()