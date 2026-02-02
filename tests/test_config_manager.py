"""
Tests for config manager.
"""
import os
import pytest
import tempfile
import shutil
from pathlib import Path

from app.config_manager import ConfigManager


class TestConfigManager:
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        temp = tempfile.mkdtemp()
        yield temp
        shutil.rmtree(temp)

    @pytest.fixture
    def config(self, temp_dir):
        """Create a ConfigManager with temporary .env file."""
        env_path = os.path.join(temp_dir, ".env")
        return ConfigManager(env_path=env_path)

    def test_creates_env_file(self, temp_dir):
        """Test that .env file is created if it doesn't exist."""
        env_path = os.path.join(temp_dir, ".env")
        assert not os.path.exists(env_path)

        config = ConfigManager(env_path=env_path)
        assert os.path.exists(env_path)

    def test_set_and_get_openai_key(self, config):
        """Test setting and getting OpenAI API key."""
        test_key = "sk-test1234567890abcdef"
        config.set_openai_api_key(test_key)

        # Should be in environment
        assert os.environ.get("OPENAI_API_KEY") == test_key

        # Should be retrievable
        assert config.get_openai_api_key() == test_key

    def test_set_and_get_gamma_key(self, config):
        """Test setting and getting Gamma API key."""
        test_key = "gamma_test_key_12345"
        config.set_gamma_api_key(test_key)

        assert config.get_gamma_api_key() == test_key
        # Setting Gamma key should disable mock mode
        assert config.get_gamma_use_mock() is False

    def test_gamma_mock_mode(self, config):
        """Test Gamma mock mode toggle."""
        # Default should be mock enabled
        config.set_gamma_use_mock(True)
        assert config.get_gamma_use_mock() is True

        config.set_gamma_use_mock(False)
        assert config.get_gamma_use_mock() is False

    def test_is_openai_configured(self, config):
        """Test OpenAI configuration check."""
        # Initially not configured
        assert config.is_openai_configured() is False

        # Set a valid key
        config.set_openai_api_key("sk-validkey12345678901234567890")
        assert config.is_openai_configured() is True

        # Empty key should not be valid
        config.set_openai_api_key("")
        assert config.is_openai_configured() is False

    def test_is_gamma_configured(self, config):
        """Test Gamma configuration check."""
        # With mock enabled, should be considered configured
        config.set_gamma_use_mock(True)
        assert config.is_gamma_configured() is True

        # Without mock and without key, not configured
        config.set_gamma_use_mock(False)
        assert config.is_gamma_configured() is False

        # With key, should be configured
        config.set_gamma_api_key("gamma_key_12345678901234")
        assert config.is_gamma_configured() is True

    def test_validate_openai_key(self, config):
        """Test OpenAI key validation."""
        # Valid key
        is_valid, msg = config.validate_openai_key("sk-validkey12345678901234567890")
        assert is_valid is True

        # Empty key
        is_valid, msg = config.validate_openai_key("")
        assert is_valid is False

        # Key without sk- prefix
        is_valid, msg = config.validate_openai_key("invalidkey12345")
        assert is_valid is False
        assert "sk-" in msg

        # Too short key
        is_valid, msg = config.validate_openai_key("sk-short")
        assert is_valid is False

    def test_mask_key(self, config):
        """Test key masking for display."""
        # None should show (not set)
        assert config._mask_key(None) == "(not set)"

        # Short key should be masked completely
        assert config._mask_key("short") == "****"

        # Normal key should show first 8 and last 4
        masked = config._mask_key("sk-1234567890abcdefghij")
        assert masked.startswith("sk-12345")
        assert masked.endswith("ghij")
        assert "..." in masked

    def test_get_all_settings(self, config):
        """Test getting all settings."""
        config.set_openai_api_key("sk-testkey12345678901234567890")
        config.set_gamma_use_mock(True)

        settings = config.get_all_settings()

        assert "openai_api_key" in settings
        assert "openai_model" in settings
        assert "gamma_api_key" in settings
        assert "gamma_use_mock" in settings
        assert settings["gamma_use_mock"] is True

    def test_openai_model(self, config):
        """Test OpenAI model setting."""
        # Default model
        default = config.get_openai_model()
        assert default == "gpt-4o"

        # Change model
        config.set_openai_model("gpt-4-turbo")
        assert config.get_openai_model() == "gpt-4-turbo"

    def test_reload(self, config, temp_dir):
        """Test configuration reload."""
        # Set a key
        config.set_openai_api_key("sk-original12345678901234567890")

        # Manually modify the .env file
        env_path = os.path.join(temp_dir, ".env")
        with open(env_path, "r") as f:
            content = f.read()
        content = content.replace("sk-original12345678901234567890", "sk-modified12345678901234567890")
        with open(env_path, "w") as f:
            f.write(content)

        # Reload should pick up the change
        config.reload()
        assert config.get_openai_api_key() == "sk-modified12345678901234567890"
