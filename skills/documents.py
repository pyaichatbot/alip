"""Document ingestion skills."""

from pathlib import Path
from typing import List

import docx
from PyPDF2 import PdfReader

from core.models import DocArtifact


def ingest_docs(directory: Path, max_size_mb: int = 10) -> List[DocArtifact]:
    """Ingest documents from directory.
    
    Args:
        directory: Directory containing documents
        max_size_mb: Maximum file size to process (MB)
        
    Returns:
        List of DocArtifact objects
    """
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    artifacts: List[DocArtifact] = []
    max_size_bytes = max_size_mb * 1024 * 1024
    
    # Supported extensions
    supported = {".pdf", ".docx", ".md", ".txt"}
    
    for file_path in directory.rglob("*"):
        if not file_path.is_file():
            continue
        
        if file_path.suffix.lower() not in supported:
            continue
        
        # Check file size
        if file_path.stat().st_size > max_size_bytes:
            continue
        
        try:
            artifact = ingest_single_doc(file_path)
            artifacts.append(artifact)
        except Exception as e:
            # Log error but continue processing other files
            print(f"Warning: Failed to ingest {file_path}: {e}")
            continue
    
    return artifacts


def ingest_single_doc(file_path: Path) -> DocArtifact:
    """Ingest a single document file.
    
    Args:
        file_path: Path to document
        
    Returns:
        DocArtifact object
    """
    suffix = file_path.suffix.lower()
    
    if suffix == ".pdf":
        content = _extract_pdf(file_path)
        doc_type = "pdf"
    elif suffix == ".docx":
        content = _extract_docx(file_path)
        doc_type = "docx"
    elif suffix == ".md":
        content = _extract_text(file_path)
        doc_type = "md"
    elif suffix == ".txt":
        content = _extract_text(file_path)
        doc_type = "txt"
    else:
        raise ValueError(f"Unsupported document type: {suffix}")
    
    # Extract title (use first line or filename)
    lines = content.strip().split("\n")
    title = lines[0][:100] if lines else file_path.stem
    
    return DocArtifact(
        path=str(file_path),
        type=doc_type,
        title=title,
        content=content,
        metadata={
            "file_size": file_path.stat().st_size,
            "file_name": file_path.name,
        },
    )


def _extract_pdf(file_path: Path) -> str:
    """Extract text from PDF file."""
    reader = PdfReader(str(file_path))
    text_parts: List[str] = []
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    
    return "\n\n".join(text_parts)


def _extract_docx(file_path: Path) -> str:
    """Extract text from DOCX file."""
    doc = docx.Document(str(file_path))
    text_parts: List[str] = []
    
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)
    
    return "\n\n".join(text_parts)


def _extract_text(file_path: Path) -> str:
    """Extract text from plain text file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def summarize_docs(docs: List[DocArtifact], max_length: int = 500) -> str:
    """Create a summary of document collection.
    
    Args:
        docs: List of document artifacts
        max_length: Maximum summary length per document
        
    Returns:
        Combined summary text
    """
    summaries: List[str] = []
    
    for doc in docs:
        # Create basic summary (first N chars)
        content_preview = doc.content[:max_length]
        if len(doc.content) > max_length:
            content_preview += "..."
        
        summary = f"**{doc.title}** ({doc.type}):\n{content_preview}\n"
        summaries.append(summary)
    
    return "\n\n".join(summaries)
