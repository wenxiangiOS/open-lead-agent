"""Tests for configuration module."""

import pytest
import os
from pathlib import Path
from unittest.mock import patch, mock_open

from src.config.settings import Settings
from src.config.validators import validate_api_key, validate_model_name


class TestSettings:
    """Test Settings class functionality."""

    def test_settings_initialization_with_valid_env(self):
        """Test Settings initializes correctly with valid environment variables."""
        with patch.dict('os.environ', {
            'ARK_API_KEY': 'test-api-key-123',
            'MODEL_NAME': 'doubao-test-model',
            'VOLC_ACCESS_KEY': 'test-access-key',
            'VOLC_SECRET_KEY': 'test-secret-key'
        }):
            settings = Settings()

            assert settings.api_key == 'test-api-key-123'
            assert settings.model_name == 'doubao-test-model'
            assert settings.base_url == "https://ark.cn-beijing.volces.com/api/v3"

    def test_settings_initialization_with_defaults(self):
        """Test Settings uses defaults when environment variables are not set."""
        with patch.dict('os.environ', {}, clear=True):
            with patch('src.config.settings.load_env') as mock_load_env:
                settings = Settings()

                # Default values should be used
                assert settings.api_key == "在这里填入你的API_KEY"
                assert settings.model_name == "doubao-seed-1-6-251015"
                assert settings.base_url == "https://ark.cn-beijing.volces.com/api/v3"

    def test_load_env_reads_file_correctly(self):
        """Test that load_env correctly reads .env file."""
        env_content = """
ARK_API_KEY=test-from-file
MODEL_NAME=doubao-file-model
# This should be ignored
VOLC_ACCESS_KEY=file-access-key
        """

        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=env_content)):
                with patch.dict('os.environ', {}, clear=True):
                    from src.config.settings import load_env
                    load_env()

                    assert os.environ.get('ARK_API_KEY') == 'test-from-file'
                    assert os.environ.get('MODEL_NAME') == 'doubao-file-model'
                    assert os.environ.get('VOLC_ACCESS_KEY') == 'file-access-key'

    def test_load_env_handles_missing_file(self):
        """Test that load_env handles missing .env file gracefully."""
        with patch('pathlib.Path.exists', return_value=False):
            # Should not raise any exception
            from src.config.settings import load_env
            load_env()


class TestValidators:
    """Test validation functions."""

    def test_validate_api_key_with_valid_key(self):
        """Test validate_api_key with valid API key."""
        # Valid API keys should not raise exception
        validate_api_key('valid-api-key-123')
        validate_api_key('19150ea9-a898-4c8c-8877-2f58a8a641fb')

    def test_validate_api_key_with_invalid_key(self):
        """Test validate_api_key with invalid API key."""
        with pytest.raises(ValueError, match="Invalid API key format"):
            validate_api_key('')
        with pytest.raises(ValueError, match="Invalid API key format"):
            validate_api_key('too-short')

    def test_validate_model_name_with_valid_name(self):
        """Test validate_model_name with valid model names."""
        # Valid model names should not raise exception
        validate_model_name('doubao-seed-1-6-251015')
        validate_model_name('doubao-pro-1-8-251228')

    def test_validate_model_name_with_invalid_name(self):
        """Test validate_model_name with invalid model name."""
        with pytest.raises(ValueError, match="Invalid model name"):
            validate_model_name('')
        with pytest.raises(ValueError, match="Invalid model name"):
            validate_model_name('invalid-model-name')