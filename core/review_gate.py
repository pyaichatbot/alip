"""Review Gate - Human-in-the-Loop approval system."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.models import AnalysisArtifact, ReviewStatus


class ReviewDecision(BaseModel):
    """Review decision for an artifact."""

    artifact_id: str
    reviewer: str
    decision: ReviewStatus
    timestamp: datetime = Field(default_factory=datetime.now)
    comments: str = ""
    required_changes: List[str] = Field(default_factory=list)


class ReviewGate:
    """Human-in-the-loop review gate for artifacts.
    
    Enforces that all artifacts must be reviewed before
    they can be used in subsequent stages.
    """

    def __init__(self, workspace_path: Path):
        """Initialize review gate.
        
        Args:
            workspace_path: Path to engagement workspace
        """
        self.workspace_path = workspace_path
        self.review_log_path = workspace_path / "artifacts" / "reviews.json"
        self._ensure_review_log()
    
    def _ensure_review_log(self) -> None:
        """Ensure review log file exists."""
        if not self.review_log_path.exists():
            self.review_log_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_reviews([])
    
    def _load_reviews(self) -> List[Dict[str, Any]]:
        """Load review decisions from log."""
        if not self.review_log_path.exists():
            return []
        
        with open(self.review_log_path, "r") as f:
            return json.load(f)
    
    def _save_reviews(self, reviews: List[Dict[str, Any]]) -> None:
        """Save review decisions to log."""
        with open(self.review_log_path, "w") as f:
            json.dump(reviews, f, indent=2, default=str)
    
    def submit_for_review(
        self,
        artifact: AnalysisArtifact,
        artifact_path: Path,
    ) -> None:
        """Submit artifact for review.
        
        Args:
            artifact: Artifact to review
            artifact_path: Path to artifact file
        """
        # Mark as pending review
        artifact.review_status = ReviewStatus.PENDING
        
        # Save updated artifact
        with open(artifact_path, "w") as f:
            json.dump(artifact.model_dump(mode="json"), f, indent=2, default=str)
        
        print(f"\n{'='*60}")
        print(f"REVIEW REQUIRED: {artifact.artifact_type}")
        print(f"{'='*60}")
        print(f"Engagement: {artifact.engagement_id}")
        print(f"Created: {artifact.created_at}")
        print(f"Confidence: {artifact.confidence or 'N/A'}")
        print(f"\nMetrics:")
        for key, value in artifact.metrics.items():
            print(f"  - {key}: {value}")
        print(f"\nSources:")
        for source in artifact.sources[:3]:  # Show first 3
            print(f"  - {source.type}: {source.path}")
        if len(artifact.sources) > 3:
            print(f"  ... and {len(artifact.sources) - 3} more")
        print(f"\nArtifact saved to: {artifact_path}")
        print(f"{'='*60}\n")
    
    def approve(
        self,
        artifact_id: str,
        reviewer: str,
        comments: str = "",
    ) -> ReviewDecision:
        """Approve an artifact.
        
        Args:
            artifact_id: Artifact identifier
            reviewer: Reviewer name/ID
            comments: Optional review comments
            
        Returns:
            ReviewDecision object
        """
        decision = ReviewDecision(
            artifact_id=artifact_id,
            reviewer=reviewer,
            decision=ReviewStatus.APPROVED,
            comments=comments,
        )
        
        # Log the decision
        reviews = self._load_reviews()
        reviews.append(decision.model_dump(mode="json"))
        self._save_reviews(reviews)
        
        print(f"✓ Artifact '{artifact_id}' APPROVED by {reviewer}")
        if comments:
            print(f"  Comments: {comments}")
        
        return decision
    
    def reject(
        self,
        artifact_id: str,
        reviewer: str,
        reason: str,
        required_changes: Optional[List[str]] = None,
    ) -> ReviewDecision:
        """Reject an artifact.
        
        Args:
            artifact_id: Artifact identifier
            reviewer: Reviewer name/ID
            reason: Reason for rejection
            required_changes: List of required changes
            
        Returns:
            ReviewDecision object
        """
        decision = ReviewDecision(
            artifact_id=artifact_id,
            reviewer=reviewer,
            decision=ReviewStatus.REJECTED,
            comments=reason,
            required_changes=required_changes or [],
        )
        
        # Log the decision
        reviews = self._load_reviews()
        reviews.append(decision.model_dump(mode="json"))
        self._save_reviews(reviews)
        
        print(f"✗ Artifact '{artifact_id}' REJECTED by {reviewer}")
        print(f"  Reason: {reason}")
        if required_changes:
            print("  Required changes:")
            for change in required_changes:
                print(f"    - {change}")
        
        return decision
    
    def request_changes(
        self,
        artifact_id: str,
        reviewer: str,
        changes: List[str],
        comments: str = "",
    ) -> ReviewDecision:
        """Request changes to an artifact.
        
        Args:
            artifact_id: Artifact identifier
            reviewer: Reviewer name/ID
            changes: List of requested changes
            comments: Optional additional comments
            
        Returns:
            ReviewDecision object
        """
        decision = ReviewDecision(
            artifact_id=artifact_id,
            reviewer=reviewer,
            decision=ReviewStatus.REQUEST_CHANGES,
            comments=comments,
            required_changes=changes,
        )
        
        # Log the decision
        reviews = self._load_reviews()
        reviews.append(decision.model_dump(mode="json"))
        self._save_reviews(reviews)
        
        print(f"⚠ Changes requested for '{artifact_id}' by {reviewer}")
        print("  Requested changes:")
        for change in changes:
            print(f"    - {change}")
        if comments:
            print(f"  Comments: {comments}")
        
        return decision
    
    def get_artifact_status(self, artifact_id: str) -> Optional[ReviewStatus]:
        """Get current review status of an artifact.
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            Current ReviewStatus or None if not found
        """
        reviews = self._load_reviews()
        
        # Get most recent review for this artifact
        artifact_reviews = [
            r for r in reviews if r.get("artifact_id") == artifact_id
        ]
        
        if not artifact_reviews:
            return None
        
        # Return most recent decision
        latest = sorted(artifact_reviews, key=lambda r: r["timestamp"])[-1]
        return ReviewStatus(latest["decision"])
    
    def get_pending_reviews(self) -> List[str]:
        """Get list of artifacts pending review.
        
        Returns:
            List of artifact IDs with pending status
        """
        reviews = self._load_reviews()
        
        # Track latest status per artifact
        latest_status: Dict[str, str] = {}
        for review in sorted(reviews, key=lambda r: r["timestamp"]):
            latest_status[review["artifact_id"]] = review["decision"]
        
        # Return artifacts with pending status
        return [
            aid for aid, status in latest_status.items()
            if status == ReviewStatus.PENDING.value
        ]
    
    def get_review_summary(self) -> Dict[str, int]:
        """Get summary of review statuses.
        
        Returns:
            Dict mapping status to count
        """
        reviews = self._load_reviews()
        
        # Track latest status per artifact
        latest_status: Dict[str, str] = {}
        for review in sorted(reviews, key=lambda r: r["timestamp"]):
            latest_status[review["artifact_id"]] = review["decision"]
        
        # Count by status
        summary = {
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "request_changes": 0,
        }
        
        for status in latest_status.values():
            summary[status] = summary.get(status, 0) + 1
        
        return summary
