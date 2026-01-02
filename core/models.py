"""Core data models for ALIP."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    """Review gate status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUEST_CHANGES = "request_changes"


class ConfidenceLevel(str, Enum):
    """Confidence level for AI-generated insights."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceReference(BaseModel):
    """Reference to source artifact."""

    type: str  # 'repo', 'db', 'doc', 'log'
    path: str
    line_number: Optional[int] = None
    snippet: Optional[str] = None
    timestamp: Optional[datetime] = None


class EngagementConfig(BaseModel):
    """Configuration for a client engagement."""

    engagement_id: str
    client_name: str
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    state: str = "new"  # NEW → INGESTED → ANALYZED → REVIEWED → FINALIZED
    read_only_mode: bool = True
    redaction_enabled: bool = True
    store_raw_data: bool = False
    output_formats: List[str] = Field(default=["md", "json"])
    locale: str = "en"  # en, de, etc.
    
    def update_state(self, new_state: str) -> None:
        """Update engagement state and timestamp."""
        self.state = new_state
        self.updated_at = datetime.now()


class WorkspacePaths(BaseModel):
    """Workspace directory structure."""

    root: Path
    engagement_id: str
    raw: Path
    processed: Path
    artifacts: Path
    reports: Path
    config: Path

    @classmethod
    def create(cls, engagement_id: str, base_dir: Path = Path("./workspace")) -> "WorkspacePaths":
        """Create workspace directory structure."""
        root = base_dir / engagement_id
        return cls(
            root=root,
            engagement_id=engagement_id,
            raw=root / "raw",
            processed=root / "processed",
            artifacts=root / "artifacts",
            reports=root / "reports",
            config=root / "config",
        )

    def ensure_exists(self) -> None:
        """Create all workspace directories."""
        for path in [self.root, self.raw, self.processed, self.artifacts, self.reports, self.config]:
            path.mkdir(parents=True, exist_ok=True)


class RepoInventory(BaseModel):
    """Repository inventory metadata."""

    path: str
    total_files: int
    languages: Dict[str, int]  # language -> file count
    lines_of_code: int
    dependency_files: List[str]
    last_modified: Optional[datetime] = None
    git_info: Optional[Dict[str, Any]] = None


class DBSchema(BaseModel):
    """Database schema metadata."""

    database_name: str
    tables: List[Dict[str, Any]]
    indexes: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    total_tables: int
    total_columns: int


class QueryEvent(BaseModel):
    """Parsed query log event."""

    query: str
    timestamp: datetime
    duration_ms: float
    rows_affected: Optional[int] = None
    database: Optional[str] = None
    user: Optional[str] = None


class DocArtifact(BaseModel):
    """Ingested document artifact."""

    path: str
    type: str  # pdf, docx, md, txt
    title: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DependencyNode(BaseModel):
    """Node in dependency graph."""

    id: str
    type: str  # service, module, table, job
    name: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DependencyEdge(BaseModel):
    """Edge in dependency graph."""

    source: str
    target: str
    type: str  # calls, depends_on, uses
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DependencyGraph(BaseModel):
    """System dependency graph."""

    nodes: List[DependencyNode]
    edges: List[DependencyEdge]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CostDriver(BaseModel):
    """Identified cost driver."""

    title: str
    description: str
    estimated_impact: str  # high, medium, low
    evidence: List[SourceReference]
    confidence: ConfidenceLevel
    metrics: Dict[str, Any] = Field(default_factory=dict)


class Risk(BaseModel):
    """Identified risk."""

    title: str
    description: str
    severity: str  # critical, high, medium, low
    category: str  # spof, tribal_knowledge, manual_ops, security
    evidence: List[SourceReference]
    confidence: ConfidenceLevel
    mitigation: Optional[str] = None


class Opportunity(BaseModel):
    """AI opportunity recommendation."""

    title: str
    description: str
    category: str  # automation, optimization, modernization
    estimated_benefit: str
    effort_level: str  # low, medium, high
    safety_level: str  # safe, requires_testing, risky
    evidence: List[SourceReference]
    confidence: ConfidenceLevel


class AnalysisArtifact(BaseModel):
    """Generic analysis artifact with metadata."""

    artifact_type: str
    engagement_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    data: Dict[str, Any]
    sources: List[SourceReference]
    metrics: Dict[str, Any] = Field(default_factory=dict)
    review_status: ReviewStatus = ReviewStatus.PENDING
    confidence: Optional[ConfidenceLevel] = None
