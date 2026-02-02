"""
Configuration manager for Slide Creator.
Handles API keys and settings storage with interactive prompts.
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv, set_key, dotenv_values


class ConfigManager:
    """Manages application configuration and API keys."""

    def __init__(self, env_path: Optional[str] = None):
        # Determine the .env file path
        if env_path:
            self.env_path = Path(env_path)
        else:
            # Check if running as executable
            import sys
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                base_path = Path(sys.executable).parent
            else:
                # Running as script - use project root
                base_path = Path(__file__).parent.parent

            self.env_path = base_path / ".env"
            self.env_example_path = base_path / ".env.example"

        # Ensure .env exists
        self._ensure_env_exists()

        # Load environment
        load_dotenv(self.env_path)

    def _ensure_env_exists(self):
        """Create .env file if it doesn't exist."""
        if not self.env_path.exists():
            # Try to copy from .env.example
            if hasattr(self, 'env_example_path') and self.env_example_path.exists():
                import shutil
                shutil.copy(self.env_example_path, self.env_path)
            else:
                # Create minimal .env
                self.env_path.write_text(self._get_default_env_content())

    def _get_default_env_content(self) -> str:
        """Get default .env content."""
        return """# Slide Creator Configuration
# API Keys
OPENAI_API_KEY=
GAMMA_API_KEY=

# OpenAI Settings
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE_REVIEW=0.4
OPENAI_TEMPERATURE_OUTLINE=0.5
OPENAI_TEMPERATURE_SPEC=0.6

# Gamma Settings
GAMMA_API_URL=https://api.gamma.app/v1
GAMMA_USE_MOCK=true

# Iteration Limits
MAX_STORYLINE_ITERATIONS=3
MAX_OUTLINE_ITERATIONS=5
MAX_SLIDE_SPEC_ITERATIONS=5
MAX_GAMMA_ITERATIONS=3

# Output
OUTPUT_DIR=./output
SESSIONS_DIR=./sessions
LOGS_DIR=./logs

# Presentation Defaults
DEFAULT_FONT=Calibri
DEFAULT_FONT_SIZE_TITLE=28
DEFAULT_FONT_SIZE_BODY=14
DEFAULT_MARGIN_INCHES=0.5
"""

    def reload(self):
        """Reload configuration from .env file."""
        load_dotenv(self.env_path, override=True)

    # ============ API KEYS ============

    def get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key."""
        return os.getenv("OPENAI_API_KEY") or None

    def set_openai_api_key(self, key: str) -> None:
        """Set OpenAI API key."""
        set_key(str(self.env_path), "OPENAI_API_KEY", key)
        os.environ["OPENAI_API_KEY"] = key

    def get_gamma_api_key(self) -> Optional[str]:
        """Get Gamma API key."""
        return os.getenv("GAMMA_API_KEY") or None

    def set_gamma_api_key(self, key: str) -> None:
        """Set Gamma API key."""
        set_key(str(self.env_path), "GAMMA_API_KEY", key)
        os.environ["GAMMA_API_KEY"] = key
        # If a key is set, disable mock
        if key:
            self.set_gamma_use_mock(False)

    def get_gamma_use_mock(self) -> bool:
        """Check if Gamma mock is enabled."""
        return os.getenv("GAMMA_USE_MOCK", "true").lower() == "true"

    def set_gamma_use_mock(self, use_mock: bool) -> None:
        """Set Gamma mock mode."""
        value = "true" if use_mock else "false"
        set_key(str(self.env_path), "GAMMA_USE_MOCK", value)
        os.environ["GAMMA_USE_MOCK"] = value

    # ============ VALIDATION ============

    def is_openai_configured(self) -> bool:
        """Check if OpenAI API key is configured."""
        key = self.get_openai_api_key()
        return bool(key and len(key) > 10)

    def is_gamma_configured(self) -> bool:
        """Check if Gamma API key is configured (or mock is enabled)."""
        if self.get_gamma_use_mock():
            return True
        key = self.get_gamma_api_key()
        return bool(key and len(key) > 10)

    def validate_openai_key(self, key: str) -> tuple[bool, str]:
        """Validate OpenAI API key format."""
        if not key:
            return False, "API key cannot be empty"
        if not key.startswith("sk-"):
            return False, "OpenAI API key should start with 'sk-'"
        if len(key) < 20:
            return False, "API key seems too short"
        return True, "Valid format"

    # ============ SETTINGS ============

    def get_openai_model(self) -> str:
        """Get OpenAI model name."""
        return os.getenv("OPENAI_MODEL", "gpt-4o")

    def set_openai_model(self, model: str) -> None:
        """Set OpenAI model name."""
        set_key(str(self.env_path), "OPENAI_MODEL", model)
        os.environ["OPENAI_MODEL"] = model

    def get_all_settings(self) -> dict:
        """Get all current settings."""
        return {
            "openai_api_key": self._mask_key(self.get_openai_api_key()),
            "openai_model": self.get_openai_model(),
            "gamma_api_key": self._mask_key(self.get_gamma_api_key()),
            "gamma_use_mock": self.get_gamma_use_mock(),
            "max_storyline_iterations": os.getenv("MAX_STORYLINE_ITERATIONS", "3"),
            "max_outline_iterations": os.getenv("MAX_OUTLINE_ITERATIONS", "5"),
            "output_dir": os.getenv("OUTPUT_DIR", "./output"),
        }

    def _mask_key(self, key: Optional[str]) -> str:
        """Mask API key for display."""
        if not key:
            return "(not set)"
        if len(key) < 10:
            return "****"
        return f"{key[:8]}...{key[-4:]}"


# Global config instance
_config: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get the global config manager instance."""
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config
