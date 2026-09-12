"""Tests for AI provider integration (OpenAI + OpenRouter), configuration, and fallbacks."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from tidyos.config import AppConfig
from tidyos.storage.repository import StorageRepository
from tidyos.tools.openai_client import (
    AIProviderConfig,
    OpenAIClient,
    get_active_ai_config,
)
from tidyos.agents.librarian import LibrarianAgent


def test_ai_provider_config_defaults():
    # OpenAI default configuration
    cfg_openai = AIProviderConfig(provider="openai", api_key="sk-test", model="gpt-4o-mini")
    assert cfg_openai.provider == "openai"
    assert cfg_openai.api_key == "sk-test"
    assert cfg_openai.model == "gpt-4o-mini"
    assert cfg_openai.base_url is None

    # OpenRouter default configuration
    cfg_router = AIProviderConfig(provider="openrouter", api_key="sk-or-test", model="openai/gpt-4o-mini")
    assert cfg_router.provider == "openrouter"
    assert cfg_router.api_key == "sk-or-test"
    assert cfg_router.model == "openai/gpt-4o-mini"
    assert cfg_router.base_url == "https://openrouter.ai/api/v1"


def test_repository_preferences_crud(tmp_path: Path):
    db_path = tmp_path / "pref_test.db"
    repo = StorageRepository(db_path)

    # Initial get of non-existent key returns default
    assert repo.get_preference("ai_provider", "default_val") == "default_val"
    assert repo.get_preference("ai_provider") is None

    # Set preference
    repo.set_preference("ai_provider", "openrouter")
    assert repo.get_preference("ai_provider") == "openrouter"

    repo.set_preference("openrouter_model", "anthropic/claude-3.5-sonnet")
    assert repo.get_preference("openrouter_model") == "anthropic/claude-3.5-sonnet"

    # Update preference
    repo.set_preference("ai_provider", "openai")
    assert repo.get_preference("ai_provider") == "openai"

    # Delete preference
    repo.delete_preference("ai_provider")
    assert repo.get_preference("ai_provider") is None

    repo.close()


def test_get_active_ai_config_priority(tmp_path: Path):
    db_path = tmp_path / "config_test.db"
    repo = StorageRepository(db_path)

    # When no preference exists, falls back to AppConfig defaults/env
    active_default = get_active_ai_config(repo)
    assert active_default.provider in ("openai", "openrouter")

    # When SQLite preference is set, it overrides config
    repo.set_preference("ai_provider", "openrouter")
    repo.set_preference("openrouter_api_key", "sk-or-v1-my-key")
    repo.set_preference("openrouter_model", "meta-llama/llama-3.3-70b-instruct")

    active_pref = get_active_ai_config(repo)
    assert active_pref.provider == "openrouter"
    assert active_pref.api_key == "sk-or-v1-my-key"
    assert active_pref.model == "meta-llama/llama-3.3-70b-instruct"
    assert active_pref.base_url == "https://openrouter.ai/api/v1"

    repo.close()


def test_openai_client_provider_resolution():
    # OpenAI client
    client_oai = OpenAIClient(provider="openai", api_key="sk-openai-123", model="gpt-4o")
    assert client_oai.provider == "openai"
    assert client_oai.model == "gpt-4o"
    assert client_oai.base_url is None
    assert client_oai.is_available() is True

    # OpenRouter client
    client_router = OpenAIClient(provider="openrouter", api_key="sk-or-v1-456", model="openai/gpt-4o-mini")
    assert client_router.provider == "openrouter"
    assert client_router.model == "openai/gpt-4o-mini"
    assert client_router.base_url == "https://openrouter.ai/api/v1"
    assert client_router.is_available() is True

    # Empty client
    client_none = OpenAIClient(api_key="", provider="openai")
    assert client_none.is_available() is False


def test_test_connection_empty_key():
    client = OpenAIClient(api_key="")
    success, msg = client.test_connection()
    assert success is False
    assert "missing" in msg.lower()


def test_test_connection_mocked_success():
    client = OpenAIClient(provider="openrouter", api_key="sk-or-mock", model="openai/gpt-4o-mini")
    mock_sdk = MagicMock()
    mock_model = MagicMock()
    mock_model.id = "openai/gpt-4o-mini"
    mock_page = MagicMock()
    mock_page.data = [mock_model]
    mock_sdk.models.list.return_value = mock_page

    with patch.object(client, "_client", mock_sdk):
        success, msg = client.test_connection()
        assert success is True
        assert msg == "Connection successful"


def test_test_connection_mocked_invalid_key():
    client = OpenAIClient(provider="openai", api_key="sk-invalid")
    mock_sdk = MagicMock()
    mock_sdk.models.list.side_effect = Exception("Error 401: Unauthorized - Invalid API key provided")

    with patch.object(client, "_client", mock_sdk):
        success, msg = client.test_connection()
        assert success is False
        assert msg == "Invalid API key"


def test_test_connection_mocked_model_unavailable():
    client = OpenAIClient(provider="openai", api_key="sk-valid", model="non-existent-model")
    mock_sdk = MagicMock()
    mock_sdk.models.list.return_value = MagicMock()
    mock_sdk.models.retrieve.side_effect = Exception("Error 404: The model `non-existent-model` does not exist")

    with patch.object(client, "_client", mock_sdk):
        success, msg = client.test_connection()
        assert success is False
        assert msg == "Model unavailable"


def test_test_connection_mocked_provider_unreachable():
    client = OpenAIClient(provider="openrouter", api_key="sk-valid")
    mock_sdk = MagicMock()
    mock_sdk.models.list.side_effect = Exception("Connection timed out: provider unreachable")

    with patch.object(client, "_client", mock_sdk):
        success, msg = client.test_connection()
        assert success is False
        assert msg == "Provider unreachable"


def test_describe_image_vision_unsupported_fallback():
    """Verify that if a model does not support vision, describe_image degrades gracefully to heuristics."""
    client = OpenAIClient(provider="openrouter", api_key="sk-mock-key", model="deepseek/deepseek-chat")
    mock_sdk = MagicMock()
    # Simulate an error where the model doesn't support image inputs
    mock_sdk.chat.completions.create.side_effect = Exception("400 Model does not support image input")

    with patch.object(client, "_client", mock_sdk):
        result = client.describe_image(
            base64_image="aW1hZ2VkYXRh",
            filename="diagram.png",
            mime_type="image/png",
            path_context="Projects/arch",
            extracted_text="Diagram showing architecture",
        )
        # Should gracefully return local heuristic result without raising
        assert result is not None
        assert "document_type" in result
        assert result.get("confidence", 0) > 0.0
        assert result["analysis_source"] in ("local_heuristic", "local_ocr_heuristic")


def test_librarian_with_openrouter_provider(tmp_path: Path):
    """Verify LibrarianAgent functions seamlessly when configured with OpenRouter."""
    db_path = tmp_path / "lib_or.db"
    repo = StorageRepository(db_path)
    repo.set_preference("ai_provider", "openrouter")
    repo.set_preference("openrouter_api_key", "sk-or-v1-test")
    repo.set_preference("openrouter_model", "openai/gpt-4o-mini")

    librarian = LibrarianAgent(repository=repo)
    assert librarian.openai_client.provider == "openrouter"
    assert librarian.openai_client.model == "openai/gpt-4o-mini"
    assert librarian.openai_client.base_url == "https://openrouter.ai/api/v1"

    # Offline / local document analysis fallback works as expected
    test_doc = tmp_path / "notes.txt"
    test_doc.write_text("Meeting notes discussing Q3 roadmap and feature deadlines.", encoding="utf-8")
    u = librarian.analyze_file(test_doc)
    assert u.document_type in ("meeting_notes", "documentation", "report", "notes")
    assert u.confidence > 0.0
    repo.close()
