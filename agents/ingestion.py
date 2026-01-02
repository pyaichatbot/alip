"""IngestionAgent - Collects and normalizes input data."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.models import AnalysisArtifact, DocArtifact, RepoInventory, SourceReference
from core.utils import hash_artifact, redact_text, save_artifact
from skills.database import parse_query_log, parse_schema_export
from skills.documents import ingest_docs
from skills.repo import scan_repo


class IngestionAgent:
    """Agent responsible for ingesting and normalizing legacy system data."""

    def __init__(self, workspace_paths: Any, engagement_config: Any):
        """Initialize ingestion agent.
        
        Args:
            workspace_paths: WorkspacePaths object
            engagement_config: EngagementConfig object
        """
        self.workspace = workspace_paths
        self.config = engagement_config

    def ingest_repository(self, repo_path: Path) -> AnalysisArtifact:
        """Ingest repository and create inventory artifact.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            AnalysisArtifact with repository inventory
        """
        print(f"[IngestionAgent] Scanning repository: {repo_path}")
        
        # Scan repository
        inventory = scan_repo(repo_path)
        
        # Apply redaction if enabled
        if self.config.redaction_enabled:
            if inventory.git_info and inventory.git_info.get("remote_url"):
                inventory.git_info["remote_url"] = redact_text(inventory.git_info["remote_url"])
        
        # Create source reference
        sources = [
            SourceReference(
                type="repo",
                path=str(repo_path),
                timestamp=datetime.now(),
            )
        ]
        
        # Create artifact
        artifact = AnalysisArtifact(
            artifact_type="repo_inventory",
            engagement_id=self.config.engagement_id,
            data=inventory.model_dump(),
            sources=sources,
            metrics={
                "total_files": inventory.total_files,
                "total_lines": inventory.lines_of_code,
                "language_count": len(inventory.languages),
            },
        )
        
        # Save to workspace
        self._save_artifact(artifact, "repo_inventory")
        
        print(f"[IngestionAgent] Repository scan complete: {inventory.total_files} files, "
              f"{inventory.lines_of_code} LOC")
        
        return artifact

    def ingest_database_schema(self, schema_file: Path) -> AnalysisArtifact:
        """Ingest database schema.
        
        Args:
            schema_file: Path to schema export file
            
        Returns:
            AnalysisArtifact with database schema
        """
        print(f"[IngestionAgent] Parsing database schema: {schema_file}")
        
        # Parse schema
        schema = parse_schema_export(schema_file)
        
        # Create source reference
        sources = [
            SourceReference(
                type="db",
                path=str(schema_file),
                timestamp=datetime.now(),
            )
        ]
        
        # Create artifact
        artifact = AnalysisArtifact(
            artifact_type="db_schema",
            engagement_id=self.config.engagement_id,
            data=schema.model_dump(),
            sources=sources,
            metrics={
                "total_tables": schema.total_tables,
                "total_columns": schema.total_columns,
                "total_indexes": len(schema.indexes),
            },
        )
        
        # Save to workspace
        self._save_artifact(artifact, "db_schema")
        
        print(f"[IngestionAgent] Schema parsed: {schema.total_tables} tables, "
              f"{schema.total_columns} columns")
        
        return artifact

    def ingest_query_logs(self, log_file: Path, limit: Optional[int] = 1000) -> AnalysisArtifact:
        """Ingest database query logs.
        
        Args:
            log_file: Path to query log file
            limit: Maximum number of queries to parse
            
        Returns:
            AnalysisArtifact with query events
        """
        print(f"[IngestionAgent] Parsing query logs: {log_file}")
        
        # Parse query log
        events = parse_query_log(log_file, limit=limit)
        
        # Redact queries if enabled
        if self.config.redaction_enabled:
            for event in events:
                event.query = redact_text(event.query)
                if event.user:
                    event.user = redact_text(event.user)
        
        # Create source reference
        sources = [
            SourceReference(
                type="log",
                path=str(log_file),
                timestamp=datetime.now(),
            )
        ]
        
        # Create artifact
        artifact = AnalysisArtifact(
            artifact_type="query_logs",
            engagement_id=self.config.engagement_id,
            data={"events": [e.model_dump() for e in events]},
            sources=sources,
            metrics={
                "total_queries": len(events),
                "unique_queries": len(set(e.query for e in events)),
            },
        )
        
        # Save to workspace
        self._save_artifact(artifact, "query_logs")
        
        print(f"[IngestionAgent] Query log parsed: {len(events)} queries")
        
        return artifact

    def ingest_documents(self, docs_dir: Path) -> AnalysisArtifact:
        """Ingest documentation files.
        
        Args:
            docs_dir: Directory containing documents
            
        Returns:
            AnalysisArtifact with document collection
        """
        print(f"[IngestionAgent] Ingesting documents from: {docs_dir}")
        
        # Ingest documents
        docs = ingest_docs(docs_dir)
        
        # Redact content if enabled
        if self.config.redaction_enabled:
            for doc in docs:
                doc.content = redact_text(doc.content)
        
        # Create source references
        sources = [
            SourceReference(
                type="doc",
                path=doc.path,
                timestamp=datetime.now(),
            )
            for doc in docs
        ]
        
        # Create artifact
        artifact = AnalysisArtifact(
            artifact_type="documents",
            engagement_id=self.config.engagement_id,
            data={"documents": [d.model_dump() for d in docs]},
            sources=sources,
            metrics={
                "total_documents": len(docs),
                "total_chars": sum(len(d.content) for d in docs),
            },
        )
        
        # Save to workspace
        self._save_artifact(artifact, "documents")
        
        print(f"[IngestionAgent] Documents ingested: {len(docs)} files")
        
        return artifact

    def _save_artifact(self, artifact: AnalysisArtifact, name: str) -> None:
        """Save artifact to workspace in multiple formats.
        
        Args:
            artifact: Artifact to save
            name: Base filename
        """
        # Save JSON
        json_path = self.workspace.artifacts / f"{name}.json"
        save_artifact(artifact, json_path, format="json")
        
        # Save human-readable markdown
        md_path = self.workspace.artifacts / f"{name}.md"
        md_content = self._artifact_to_markdown(artifact)
        with open(md_path, "w") as f:
            f.write(md_content)
        
        # Save sources
        sources_path = self.workspace.artifacts / f"{name}_sources.json"
        save_artifact({"sources": [s.model_dump() for s in artifact.sources]}, sources_path)
        
        # Save metrics
        metrics_path = self.workspace.artifacts / f"{name}_metrics.json"
        save_artifact(artifact.metrics, metrics_path)

    def _artifact_to_markdown(self, artifact: AnalysisArtifact) -> str:
        """Convert artifact to markdown format.
        
        Args:
            artifact: Artifact to convert
            
        Returns:
            Markdown string
        """
        lines = [
            f"# {artifact.artifact_type.replace('_', ' ').title()}",
            "",
            f"**Engagement ID:** {artifact.engagement_id}",
            f"**Created:** {artifact.created_at.isoformat()}",
            f"**Status:** {artifact.review_status.value}",
            "",
            "## Metrics",
            "",
        ]
        
        for key, value in artifact.metrics.items():
            lines.append(f"- **{key}:** {value}")
        
        lines.extend([
            "",
            "## Sources",
            "",
        ])
        
        for source in artifact.sources:
            lines.append(f"- {source.type}: `{source.path}`")
        
        lines.extend([
            "",
            "## Data",
            "",
            "```json",
            str(artifact.data)[:500] + "..." if len(str(artifact.data)) > 500 else str(artifact.data),
            "```",
        ])
        
        return "\n".join(lines)
