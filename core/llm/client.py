"""LLM client abstraction for vendor-agnostic AI calls."""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ) -> str:
        """Generate completion from prompt.
        
        Args:
            prompt: User prompt
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated text
        """
        pass

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured output matching schema.
        
        Args:
            prompt: User prompt
            schema: JSON schema for output
            system: Optional system prompt
            
        Returns:
            Structured output as dictionary
        """
        pass


class ClaudeClient(LLMClient):
    """Anthropic Claude client implementation."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """Initialize Claude client.
        
        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if None)
            model: Model to use
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = model

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ) -> str:
        """Generate completion from Claude."""
        messages = [{"role": "user", "content": prompt}]
        
        # Build kwargs to avoid sending empty list for system
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        
        # Only add system if provided
        if system:
            kwargs["system"] = system
        
        response = self.client.messages.create(**kwargs)
        
        return response.content[0].text

    def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured output from Claude.
        
        Note: This is a simplified implementation. Production would use
        Claude's native structured output features or more sophisticated parsing.
        """
        import json
        
        schema_str = json.dumps(schema, indent=2)
        enhanced_prompt = f"""{prompt}

Please respond with valid JSON matching this schema:
{schema_str}

Respond with ONLY the JSON object, no markdown or explanations."""

        response_text = self.generate(
            prompt=enhanced_prompt,
            system=system,
            temperature=0.1,  # Lower temp for structured output
        )
        
        # Extract JSON from response (handle markdown code blocks)
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(1)
        
        return json.loads(response_text)


class AzureOpenAIClient(LLMClient):
    """Azure OpenAI client implementation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_version: str = "2024-02-15-preview",
        azure_endpoint: Optional[str] = None,
        model: str = "gpt-4",
        deployment_name: Optional[str] = None,
    ):
        """Initialize Azure OpenAI client.
        
        Args:
            api_key: Azure OpenAI API key (uses AZURE_OPENAI_API_KEY env var if None)
            api_version: API version to use
            azure_endpoint: Azure endpoint URL (uses AZURE_OPENAI_ENDPOINT env var if None)
            model: Model name (e.g., "gpt-4", "gpt-4-turbo", "gpt-35-turbo")
            deployment_name: Deployment name (uses model if None, or AZURE_OPENAI_DEPLOYMENT_NAME env var)
        """
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package is required for Azure OpenAI support. "
                "Install it with: pip install openai"
            )
        
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not found in environment")
        
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        if not self.azure_endpoint:
            raise ValueError("AZURE_OPENAI_ENDPOINT not found in environment")
        
        self.api_version = api_version
        self.model = model
        self.deployment_name = deployment_name or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") or model
        
        self.client = AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.azure_endpoint,
        )

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ) -> str:
        """Generate completion from Azure OpenAI."""
        messages = []
        
        # Add system message if provided
        if system:
            messages.append({"role": "system", "content": system})
        
        # Add user message
        messages.append({"role": "user", "content": prompt})
        
        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        return response.choices[0].message.content

    def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured output from Azure OpenAI.
        
        Uses tools/function calling with JSON schema for structured output.
        Falls back to JSON parsing if function calling is not available.
        """
        import json
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        # Try using tools API (newer format)
        try:
            tool_def = {
                "type": "function",
                "function": {
                    "name": "extract_structured_data",
                    "description": "Extract structured data based on the provided schema",
                    "parameters": schema,
                }
            }
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                tools=[tool_def],
                tool_choice={"type": "function", "function": {"name": "extract_structured_data"}},
                temperature=0.1,  # Lower temp for structured output
            )
            
            # Extract tool call arguments
            message = response.choices[0].message
            if message.tool_calls and len(message.tool_calls) > 0:
                tool_call = message.tool_calls[0]
                if tool_call.function.name == "extract_structured_data":
                    return json.loads(tool_call.function.arguments)
        except (AttributeError, KeyError, TypeError):
            # Fallback to older functions API or direct JSON parsing
            pass
        
        # Fallback: try older functions API
        try:
            function_def = {
                "name": "extract_structured_data",
                "description": "Extract structured data based on the provided schema",
                "parameters": schema,
            }
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                functions=[function_def],
                function_call={"name": "extract_structured_data"},
                temperature=0.1,
            )
            
            message = response.choices[0].message
            if hasattr(message, 'function_call') and message.function_call:
                if message.function_call.name == "extract_structured_data":
                    return json.loads(message.function_call.arguments)
        except (AttributeError, KeyError, TypeError):
            pass
        
        # Final fallback: request JSON in prompt and parse from content
        schema_str = json.dumps(schema, indent=2)
        enhanced_prompt = f"""{prompt}

Please respond with valid JSON matching this schema:
{schema_str}

Respond with ONLY the JSON object, no markdown or explanations."""

        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[m for m in messages[:-1]] + [{"role": "user", "content": enhanced_prompt}],
            temperature=0.1,
        )
        
        message = response.choices[0].message
        if message.content:
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', message.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            # Try direct JSON parse
            try:
                return json.loads(message.content)
            except json.JSONDecodeError:
                pass
        
        raise ValueError("Failed to extract structured output from Azure OpenAI response")


class LocalClient(LLMClient):
    """Placeholder for local/open-source model client."""

    def __init__(self, model_path: Optional[Path] = None):
        """Initialize local client.
        
        Args:
            model_path: Path to local model (future implementation)
        """
        raise NotImplementedError("LocalClient not yet implemented")

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4000,
        temperature: float = 0.3,
    ) -> str:
        raise NotImplementedError("LocalClient not yet implemented")

    def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError("LocalClient not yet implemented")


def create_llm_client(provider: str = "claude", **kwargs: Any) -> LLMClient:
    """Factory function to create LLM client.
    
    Args:
        provider: Provider name ('claude', 'azure', or 'local')
        **kwargs: Provider-specific arguments
        
    Returns:
        LLM client instance
        
    Examples:
        # Claude (default)
        client = create_llm_client("claude", model="claude-sonnet-4-20250514")
        
        # Azure OpenAI
        client = create_llm_client(
            "azure",
            model="gpt-4",
            azure_endpoint="https://your-resource.openai.azure.com/",
            api_key="your-api-key"
        )
    """
    if provider == "claude":
        return ClaudeClient(**kwargs)
    elif provider == "azure":
        return AzureOpenAIClient(**kwargs)
    elif provider == "local":
        return LocalClient(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}. Supported: 'claude', 'azure', 'local'")
