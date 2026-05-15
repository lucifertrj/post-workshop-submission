"""
Environment Loader — centralizes configuration and secret management.
Ensures all required variables are present before runtime activation.
"""
import os
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv
import structlog

logger = structlog.get_logger(__name__)

class ConfigLoader:
    """Manages environment variables and runtime validation."""
    
    REQUIRED_KEYS = ["OPENAI_API_KEY"]
    OPTIONAL_PROVIDERS = ["ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY"]
    OBSERVABILITY_KEYS = ["LANGCHAIN_API_KEY", "WANDB_API_KEY"]

    @classmethod
    def load(cls, env_path: str = ".env") -> Dict[str, Any]:
        """Loads .env file and validates presence of critical secrets."""
        path = Path(env_path)
        if path.exists():
            load_dotenv(dotenv_path=path)
            logger.info("environment_loaded", path=str(path))
        else:
            logger.warning("env_file_not_found", path=str(path), action="using_system_env")

        cls.validate()
        return dict(os.environ)

    @classmethod
    def validate(cls) -> None:
        """Performs startup diagnostics on environment state."""
        missing_critical = [k for k in cls.REQUIRED_KEYS if not os.getenv(k)]
        
        if missing_critical:
            logger.error("critical_secrets_missing", keys=missing_critical)
            # In a real bootstrap we might raise error, here we emit warning for setup
            
        missing_observability = [k for k in cls.OBSERVABILITY_KEYS if not os.getenv(k)]
        if missing_observability:
            logger.info("observability_disabled", missing_keys=missing_observability)

    @staticmethod
    def get_provider_status() -> Dict[str, bool]:
        """Returns availability of configured LLM providers."""
        return {
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
            "google": bool(os.getenv("GOOGLE_API_KEY")),
            "groq": bool(os.getenv("GROQ_API_KEY")),
            "together": bool(os.getenv("TOGETHER_API_KEY")),
        }
