"""Unit tests for core utilities."""

import json
from pathlib import Path

import pytest

from core.models import RepoInventory
from core.utils import (
    format_bytes,
    format_duration,
    hash_artifact,
    load_config,
    redact_text,
    save_artifact,
)


def test_redact_email() -> None:
    """Test email redaction."""
    text = "Contact john.doe@example.com for details"
    redacted = redact_text(text)
    assert "john.doe@example.com" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_multiple_patterns() -> None:
    """Test redacting multiple patterns."""
    text = """
    Email: admin@company.com
    Password: secretpass123
    Token: abc123def456ghi789jkl012mno345pqr678
    """
    redacted = redact_text(text)
    assert "admin@company.com" not in redacted
    assert "secretpass123" not in redacted
    assert "abc123def456ghi789jkl012mno345pqr678" not in redacted


def test_redact_custom_patterns() -> None:
    """Test redaction with custom patterns."""
    text = "SSN: 123-45-6789"
    patterns = [r"\d{3}-\d{2}-\d{4}"]
    redacted = redact_text(text, patterns)
    assert "123-45-6789" not in redacted
    assert "[REDACTED]" in redacted


def test_hash_artifact() -> None:
    """Test artifact hashing."""
    data = {"key": "value", "number": 42}
    hash1 = hash_artifact(data)
    hash2 = hash_artifact(data)
    
    # Same data should produce same hash
    assert hash1 == hash2
    
    # Hash should be hex string
    assert len(hash1) == 64
    assert all(c in "0123456789abcdef" for c in hash1)


def test_hash_artifact_pydantic() -> None:
    """Test hashing pydantic models."""
    model = RepoInventory(
        path="/test",
        total_files=10,
        languages={"Python": 5},
        lines_of_code=100,
        dependency_files=[],
    )
    
    hash1 = hash_artifact(model)
    assert len(hash1) == 64


def test_save_artifact_json(tmp_path: Path) -> None:
    """Test saving artifact as JSON."""
    data = {"test": "data", "number": 123}
    output = tmp_path / "test.json"
    
    save_artifact(data, output, format="json")
    
    assert output.exists()
    with open(output) as f:
        loaded = json.load(f)
    assert loaded == data


def test_save_artifact_creates_dirs(tmp_path: Path) -> None:
    """Test that save_artifact creates parent directories."""
    output = tmp_path / "deep" / "nested" / "dir" / "test.json"
    
    save_artifact({"test": "data"}, output)
    
    assert output.exists()


def test_load_config_yaml(tmp_path: Path) -> None:
    """Test loading YAML configuration."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
engagement_id: test-001
client_name: Test Corp
read_only_mode: true
""")
    
    config = load_config(config_file)
    assert config["engagement_id"] == "test-001"
    assert config["client_name"] == "Test Corp"
    assert config["read_only_mode"] is True


def test_load_config_json(tmp_path: Path) -> None:
    """Test loading JSON configuration."""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"engagement_id": "test-002", "enabled": true}')
    
    config = load_config(config_file)
    assert config["engagement_id"] == "test-002"
    assert config["enabled"] is True


def test_load_config_not_found() -> None:
    """Test loading non-existent config."""
    with pytest.raises(FileNotFoundError):
        load_config(Path("/nonexistent/config.yaml"))


def test_format_bytes() -> None:
    """Test byte formatting."""
    assert format_bytes(100) == "100.0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"
    assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"


def test_format_duration() -> None:
    """Test duration formatting."""
    assert format_duration(100) == "100ms"
    assert format_duration(1000) == "1.0s"
    assert format_duration(1500) == "1.5s"
    assert format_duration(60000) == "1.0m"
    assert format_duration(3600000) == "1.0h"
