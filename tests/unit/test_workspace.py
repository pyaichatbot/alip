"""Unit tests for workspace skills."""

import json
from pathlib import Path

import pytest

from core.models import EngagementConfig, WorkspacePaths
from skills.workspace import (
    init_workspace,
    load_engagement_config,
    load_workspace,
    save_engagement_config,
)


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create temporary workspace directory."""
    return tmp_path / "test_workspace"


def test_init_workspace(temp_workspace: Path) -> None:
    """Test workspace initialization."""
    workspace = init_workspace(
        engagement_id="test-001",
        client_name="Test Corp",
        base_dir=temp_workspace,
    )
    
    # Check workspace structure
    assert workspace.root.exists()
    assert workspace.raw.exists()
    assert workspace.processed.exists()
    assert workspace.artifacts.exists()
    assert workspace.reports.exists()
    assert workspace.config.exists()
    
    # Check config file
    config_file = workspace.config / "engagement.json"
    assert config_file.exists()
    
    with open(config_file) as f:
        config_data = json.load(f)
    
    assert config_data["engagement_id"] == "test-001"
    assert config_data["client_name"] == "Test Corp"
    assert config_data["read_only_mode"] is True
    
    # Check README
    readme = workspace.root / "README.md"
    assert readme.exists()
    assert "test-001" in readme.read_text()


def test_init_workspace_with_overrides(temp_workspace: Path) -> None:
    """Test workspace initialization with config overrides."""
    workspace = init_workspace(
        engagement_id="test-002",
        client_name="Custom Corp",
        base_dir=temp_workspace,
        config_overrides={
            "locale": "de",
            "output_formats": ["md", "pdf"],
        },
    )
    
    config = load_engagement_config(workspace)
    assert config.locale == "de"
    assert config.output_formats == ["md", "pdf"]


def test_load_workspace(temp_workspace: Path) -> None:
    """Test loading existing workspace."""
    # Create workspace
    original = init_workspace(
        engagement_id="test-003",
        client_name="Load Test Corp",
        base_dir=temp_workspace,
    )
    
    # Load workspace
    loaded = load_workspace("test-003", temp_workspace)
    
    assert loaded.root == original.root
    assert loaded.engagement_id == original.engagement_id


def test_load_workspace_not_found(temp_workspace: Path) -> None:
    """Test loading non-existent workspace."""
    with pytest.raises(FileNotFoundError):
        load_workspace("nonexistent", temp_workspace)


def test_load_engagement_config(temp_workspace: Path) -> None:
    """Test loading engagement configuration."""
    workspace = init_workspace(
        engagement_id="test-004",
        client_name="Config Test Corp",
        base_dir=temp_workspace,
    )
    
    config = load_engagement_config(workspace)
    
    assert isinstance(config, EngagementConfig)
    assert config.engagement_id == "test-004"
    assert config.client_name == "Config Test Corp"


def test_save_engagement_config(temp_workspace: Path) -> None:
    """Test saving engagement configuration."""
    workspace = init_workspace(
        engagement_id="test-005",
        client_name="Save Test Corp",
        base_dir=temp_workspace,
    )
    
    # Load and modify config
    config = load_engagement_config(workspace)
    config.locale = "fr"
    
    # Save modified config
    save_engagement_config(workspace, config)
    
    # Reload and verify
    reloaded = load_engagement_config(workspace)
    assert reloaded.locale == "fr"


def test_workspace_paths_create() -> None:
    """Test WorkspacePaths creation."""
    paths = WorkspacePaths.create("test-eng", Path("/tmp/test"))
    
    assert paths.engagement_id == "test-eng"
    assert paths.root == Path("/tmp/test/test-eng")
    assert paths.raw == Path("/tmp/test/test-eng/raw")
    assert paths.artifacts == Path("/tmp/test/test-eng/artifacts")
