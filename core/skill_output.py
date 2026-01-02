"""Structured output wrapper for all skill functions."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.models import ConfidenceLevel, SourceReference


class SkillOutput(BaseModel):
    """Standardized output for all skill functions.
    
    Every skill must return this structure to ensure:
    - Consistent metadata across all outputs
    - Traceability via sources
    - Confidence scoring
    - Timestamp tracking
    """

    skill_name: str
    data: Any
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    sources: List[SourceReference] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    warnings: List[str] = Field(default_factory=list)
    
    def add_source(
        self,
        source_type: str,
        path: str,
        line_number: Optional[int] = None,
        snippet: Optional[str] = None,
    ) -> None:
        """Add a source reference.
        
        Args:
            source_type: Type of source (repo, db, doc, log)
            path: Path to source
            line_number: Optional line number
            snippet: Optional code/text snippet
        """
        self.sources.append(
            SourceReference(
                type=source_type,
                path=path,
                line_number=line_number,
                snippet=snippet,
                timestamp=datetime.now(),
            )
        )
    
    def add_warning(self, message: str) -> None:
        """Add a warning message.
        
        Args:
            message: Warning message
        """
        self.warnings.append(message)
    
    def set_confidence(self, level: ConfidenceLevel, reason: Optional[str] = None) -> None:
        """Set confidence level.
        
        Args:
            level: Confidence level
            reason: Optional reason for confidence level
        """
        self.confidence = level
        if reason:
            self.metadata["confidence_reason"] = reason


def create_skill_output(
    skill_name: str,
    data: Any,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    sources: Optional[List[SourceReference]] = None,
    **metadata: Any,
) -> SkillOutput:
    """Factory function to create SkillOutput.
    
    Args:
        skill_name: Name of the skill
        data: Output data
        confidence: Confidence level
        sources: Source references
        **metadata: Additional metadata
        
    Returns:
        SkillOutput instance
    """
    return SkillOutput(
        skill_name=skill_name,
        data=data,
        confidence=confidence,
        sources=sources or [],
        metadata=metadata,
    )


# Example usage decorator
def skill_wrapper(skill_name: str):
    """Decorator to wrap skill functions with SkillOutput.
    
    Usage:
        @skill_wrapper("scan_repo")
        def scan_repo(path: Path) -> dict:
            # ... implementation
            return {"total_files": 100}
    
    Returns SkillOutput instead of raw dict.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # If already SkillOutput, return as-is
            if isinstance(result, SkillOutput):
                return result
            
            # Otherwise wrap in SkillOutput
            return create_skill_output(
                skill_name=skill_name,
                data=result,
                confidence=ConfidenceLevel.HIGH,
            )
        return wrapper
    return decorator
