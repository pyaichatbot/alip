"""Core utility functions for ALIP."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(path: Path) -> Dict[str, Any]:
    """Load YAML configuration file.
    
    Args:
        path: Path to config file
        
    Returns:
        Parsed configuration dictionary
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, "r") as f:
        if path.suffix in [".yaml", ".yml"]:
            return yaml.safe_load(f)
        elif path.suffix == ".json":
            return json.load(f)
        else:
            raise ValueError(f"Unsupported config format: {path.suffix}")


def save_artifact(data: Any, path: Path, format: str = "json") -> None:
    """Save artifact to disk.
    
    Args:
        data: Data to save (dict, list, or pydantic model)
        path: Output path
        format: Format (json or yaml)
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert pydantic models to dict
    if hasattr(data, "model_dump"):
        data = data.model_dump(mode="json")
    
    with open(path, "w") as f:
        if format == "json":
            json.dump(data, f, indent=2, default=str)
        elif format == "yaml":
            yaml.dump(data, f, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported format: {format}")


def hash_artifact(obj: Any) -> str:
    """Generate SHA256 hash of an artifact.
    
    Args:
        obj: Object to hash
        
    Returns:
        Hex digest of hash
    """
    if hasattr(obj, "model_dump"):
        obj = obj.model_dump(mode="json")
    
    content = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


def redact_text(text: str, patterns: list[str] | None = None) -> str:
    """Redact sensitive information from text.
    
    Args:
        text: Input text
        patterns: Optional custom patterns (uses defaults if None)
        
    Returns:
        Redacted text
    """
    if patterns is None:
        patterns = [
            # Email addresses
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            # API keys (common patterns)
            r'\b[A-Za-z0-9]{32,}\b',
            # AWS keys
            r'AKIA[0-9A-Z]{16}',
            # Generic tokens
            r'token["\s:=]+[A-Za-z0-9_\-]{20,}',
            # Passwords
            r'password["\s:=]+\S+',
            # IP addresses (optional - commented for now)
            # r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
        ]
    
    result = text
    for pattern in patterns:
        result = re.sub(pattern, "[REDACTED]", result, flags=re.IGNORECASE)
    
    return result


def format_bytes(bytes: int) -> str:
    """Format bytes as human-readable string.
    
    Args:
        bytes: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} PB"


def format_duration(ms: float) -> str:
    """Format milliseconds as human-readable string.
    
    Args:
        ms: Duration in milliseconds
        
    Returns:
        Formatted string (e.g., "1.5s")
    """
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    elif ms < 3600000:
        return f"{ms/60000:.1f}m"
    else:
        return f"{ms/3600000:.1f}h"
