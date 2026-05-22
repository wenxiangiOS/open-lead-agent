from src.llm import LLMSettings


def test_llm_settings_do_not_bind_to_a_default_model(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    settings = LLMSettings.from_env()

    assert settings.provider == "openai_compatible"
    assert settings.api_key == ""
    assert settings.model == ""
    assert settings.base_url == ""
    assert settings.max_retries == 0


def test_llm_settings_read_external_configuration(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "custom-model")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.com/v1")

    settings = LLMSettings.from_env()

    assert settings.api_key == "test-key"
    assert settings.model == "custom-model"
    assert settings.base_url == "https://example.com/v1"


def test_llm_settings_read_retry_configuration(monkeypatch):
    monkeypatch.setenv("LLM_MAX_RETRIES", "2")

    settings = LLMSettings.from_env()

    assert settings.max_retries == 2
