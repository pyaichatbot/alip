"""Workspace management skills."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.models import EngagementConfig, WorkspacePaths
from core.utils import save_artifact


def init_workspace(
    engagement_id: str,
    client_name: str,
    base_dir: Path = Path("./workspace"),
    config_overrides: Optional[dict] = None,
) -> WorkspacePaths:
    """Initialize workspace for a new engagement.
    
    Args:
        engagement_id: Unique engagement identifier
        client_name: Client/company name
        base_dir: Base directory for all workspaces
        config_overrides: Optional configuration overrides
        
    Returns:
        WorkspacePaths object with created directories
    """
    # Create workspace structure
    workspace = WorkspacePaths.create(engagement_id, base_dir)
    workspace.ensure_exists()
    
    # Create engagement configuration
    config = EngagementConfig(
        engagement_id=engagement_id,
        client_name=client_name,
        **(config_overrides or {}),
    )
    
    # Save configuration
    config_path = workspace.config / "engagement.json"
    save_artifact(config, config_path, format="json")
    
    # Create README
    readme_path = workspace.root / "README.md"
    readme_content = f"""# ALIP Engagement: {client_name}

**Engagement ID:** {engagement_id}
**Created:** {datetime.now().isoformat()}
**Mode:** Read-Only Analysis

## Directory Structure

- `raw/` - Raw ingested data (redacted)
- `processed/` - Processed/normalized data
- `artifacts/` - Analysis artifacts (JSON + MD)
- `reports/` - Final reports
- `config/` - Engagement configuration

## Safety Notes

- This engagement operates in **READ-ONLY** mode
- All client data is redacted according to policy
- Raw data is NOT stored (only derived metadata)
- All outputs require human review before delivery
"""
    
    with open(readme_path, "w") as f:
        f.write(readme_content)
    
    # Create .gitignore
    gitignore_path = workspace.root / ".gitignore"
    gitignore_content = """# ALIP workspace - prevent accidental commits
raw/
*.log
*.tmp
.env
secrets/
"""
    
    with open(gitignore_path, "w") as f:
        f.write(gitignore_content)
    
    return workspace


def load_workspace(engagement_id: str, base_dir: Path = Path("./workspace")) -> WorkspacePaths:
    """Load existing workspace.
    
    Args:
        engagement_id: Engagement identifier
        base_dir: Base directory for workspaces
        
    Returns:
        WorkspacePaths object
        
    Raises:
        FileNotFoundError: If workspace doesn't exist
    """
    workspace = WorkspacePaths.create(engagement_id, base_dir)
    
    if not workspace.root.exists():
        raise FileNotFoundError(f"Workspace not found: {workspace.root}")
    
    if not workspace.config.exists():
        raise FileNotFoundError(f"Workspace config not found: {workspace.config}")
    
    return workspace


def load_engagement_config(workspace: WorkspacePaths) -> EngagementConfig:
    """Load engagement configuration from workspace.
    
    Args:
        workspace: WorkspacePaths object
        
    Returns:
        EngagementConfig object
    """
    config_path = workspace.config / "engagement.json"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    
    with open(config_path, "r") as f:
        data = json.load(f)
    
    return EngagementConfig(**data)


def save_engagement_config(workspace: WorkspacePaths, config: EngagementConfig) -> None:
    """Save engagement configuration to workspace.
    
    Args:
        workspace: WorkspacePaths object
        config: EngagementConfig to save
    """
    config_path = workspace.config / "engagement.json"
    save_artifact(config, config_path, format="json")
