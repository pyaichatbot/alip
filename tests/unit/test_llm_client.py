"""Unit tests for LLM client implementations."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from core.llm.client import (
    LLMClient,
    ClaudeClient,
    AzureOpenAIClient,
    create_llm_client,
    OPENAI_AVAILABLE,
)


class TestClaudeClient:
    """Tests for ClaudeClient."""

    def test_claude_client_init_with_api_key(self):
        """Test ClaudeClient initialization with explicit API key."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('core.llm.client.Anthropic') as mock_anthropic:
                client = ClaudeClient(api_key="test-key")
                assert client.api_key == "test-key"
                mock_anthropic.assert_called_once_with(api_key="test-key")

    def test_claude_client_init_from_env(self):
        """Test ClaudeClient initialization from environment variable."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "env-key"}):
            with patch('core.llm.client.Anthropic') as mock_anthropic:
                client = ClaudeClient()
                assert client.api_key == "env-key"
                mock_anthropic.assert_called_once_with(api_key="env-key")

    def test_claude_client_init_missing_key(self):
        """Test ClaudeClient initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
                ClaudeClient()

    def test_claude_client_generate(self):
        """Test ClaudeClient generate method."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('core.llm.client.Anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.content = [Mock(text="Test response")]
                mock_client.messages.create.return_value = mock_response
                mock_anthropic.return_value = mock_client

                client = ClaudeClient()
                result = client.generate("Test prompt", system="System prompt")

                assert result == "Test response"
                mock_client.messages.create.assert_called_once()
                call_kwargs = mock_client.messages.create.call_args[1]
                assert call_kwargs["model"] == "claude-sonnet-4-20250514"
                assert call_kwargs["system"] == "System prompt"
                assert call_kwargs["messages"][0]["content"] == "Test prompt"

    def test_claude_client_generate_structured(self):
        """Test ClaudeClient generate_structured method."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('core.llm.client.Anthropic') as mock_anthropic:
                mock_client = Mock()
                mock_response = Mock()
                mock_response.content = [Mock(text='{"key": "value"}')]
                mock_client.messages.create.return_value = mock_response
                mock_anthropic.return_value = mock_client

                client = ClaudeClient()
                schema = {"type": "object", "properties": {"key": {"type": "string"}}}
                result = client.generate_structured("Test prompt", schema)

                assert result == {"key": "value"}


class TestAzureOpenAIClient:
    """Tests for AzureOpenAIClient."""

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_azure_client_init_with_params(self):
        """Test AzureOpenAIClient initialization with explicit parameters."""
        with patch('core.llm.client.AzureOpenAI') as mock_azure:
            client = AzureOpenAIClient(
                api_key="test-key",
                azure_endpoint="https://test.openai.azure.com/",
                model="gpt-4",
                deployment_name="gpt-4-deployment"
            )
            assert client.api_key == "test-key"
            assert client.azure_endpoint == "https://test.openai.azure.com/"
            assert client.model == "gpt-4"
            assert client.deployment_name == "gpt-4-deployment"
            mock_azure.assert_called_once()

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_azure_client_init_from_env(self):
        """Test AzureOpenAIClient initialization from environment variables."""
        with patch.dict(os.environ, {
            "AZURE_OPENAI_API_KEY": "env-key",
            "AZURE_OPENAI_ENDPOINT": "https://env.openai.azure.com/",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "env-deployment"
        }):
            with patch('core.llm.client.AzureOpenAI') as mock_azure:
                client = AzureOpenAIClient()
                assert client.api_key == "env-key"
                assert client.azure_endpoint == "https://env.openai.azure.com/"
                assert client.deployment_name == "env-deployment"
                mock_azure.assert_called_once()

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_azure_client_init_missing_key(self):
        """Test AzureOpenAIClient initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="AZURE_OPENAI_API_KEY not found"):
                AzureOpenAIClient(azure_endpoint="https://test.openai.azure.com/")

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_azure_client_init_missing_endpoint(self):
        """Test AzureOpenAIClient initialization fails without endpoint."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT not found"):
                AzureOpenAIClient(api_key="test-key")

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_azure_client_generate(self):
        """Test AzureOpenAIClient generate method."""
        with patch('core.llm.client.AzureOpenAI') as mock_azure:
            mock_client = Mock()
            mock_message = Mock()
            mock_message.content = "Test response"
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response = Mock()
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_response
            mock_azure.return_value = mock_client

            client = AzureOpenAIClient(
                api_key="test-key",
                azure_endpoint="https://test.openai.azure.com/",
                deployment_name="gpt-4"
            )
            result = client.generate("Test prompt", system="System prompt")

            assert result == "Test response"
            mock_client.chat.completions.create.assert_called_once()
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "gpt-4"
            assert len(call_kwargs["messages"]) == 2
            assert call_kwargs["messages"][0]["role"] == "system"
            assert call_kwargs["messages"][1]["role"] == "user"

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_azure_client_generate_structured_with_tool_call(self):
        """Test AzureOpenAIClient generate_structured with tool calling."""
        with patch('core.llm.client.AzureOpenAI') as mock_azure:
            mock_client = Mock()
            mock_function = Mock()
            mock_function.name = "extract_structured_data"
            mock_function.arguments = '{"key": "value"}'
            mock_tool_call = Mock()
            mock_tool_call.function = mock_function
            mock_message = Mock()
            mock_message.tool_calls = [mock_tool_call]
            mock_message.content = None
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response = Mock()
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_response
            mock_azure.return_value = mock_client

            client = AzureOpenAIClient(
                api_key="test-key",
                azure_endpoint="https://test.openai.azure.com/",
                deployment_name="gpt-4"
            )
            schema = {"type": "object", "properties": {"key": {"type": "string"}}}
            result = client.generate_structured("Test prompt", schema)

            assert result == {"key": "value"}
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            assert "tools" in call_kwargs or "functions" in call_kwargs

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_azure_client_generate_structured_fallback_to_json(self):
        """Test AzureOpenAIClient generate_structured fallback to JSON parsing."""
        with patch('core.llm.client.AzureOpenAI') as mock_azure:
            mock_client = Mock()
            mock_message = Mock()
            mock_message.function_call = None
            mock_message.content = '```json\n{"key": "value"}\n```'
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response = Mock()
            mock_response.choices = [mock_choice]
            mock_client.chat.completions.create.return_value = mock_response
            mock_azure.return_value = mock_client

            client = AzureOpenAIClient(
                api_key="test-key",
                azure_endpoint="https://test.openai.azure.com/",
                deployment_name="gpt-4"
            )
            schema = {"type": "object", "properties": {"key": {"type": "string"}}}
            result = client.generate_structured("Test prompt", schema)

            assert result == {"key": "value"}


class TestCreateLLMClient:
    """Tests for create_llm_client factory function."""

    def test_create_claude_client(self):
        """Test creating Claude client."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('core.llm.client.ClaudeClient') as mock_claude:
                client = create_llm_client("claude")
                mock_claude.assert_called_once()

    @pytest.mark.skipif(not OPENAI_AVAILABLE, reason="openai package not installed")
    def test_create_azure_client(self):
        """Test creating Azure OpenAI client."""
        with patch('core.llm.client.AzureOpenAIClient') as mock_azure:
            client = create_llm_client(
                "azure",
                api_key="test-key",
                azure_endpoint="https://test.openai.azure.com/"
            )
            mock_azure.assert_called_once()

    def test_create_unknown_provider(self):
        """Test creating client with unknown provider fails."""
        with pytest.raises(ValueError, match="Unknown provider"):
            create_llm_client("unknown")

    def test_create_client_default_provider(self):
        """Test default provider is claude."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch('core.llm.client.ClaudeClient') as mock_claude:
                client = create_llm_client()
                mock_claude.assert_called_once()

