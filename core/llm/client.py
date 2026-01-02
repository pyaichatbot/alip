"""LLM client abstraction for vendor-agnostic AI calls."""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

from anthropic import Anthropic


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
        provider: Provider name ('claude' or 'local')
        **kwargs: Provider-specific arguments
        
    Returns:
        LLM client instance
    """
    if provider == "claude":
        return ClaudeClient(**kwargs)
    elif provider == "local":
        return LocalClient(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")
