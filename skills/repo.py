"""Repository ingestion skills."""

import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Make git import optional
try:
    from git import Repo
    from git.exc import InvalidGitRepositoryError
    HAS_GIT = True
except ImportError:
    HAS_GIT = False
    Repo = None
    InvalidGitRepositoryError = Exception

from core.models import RepoInventory


# Language detection by file extension
LANGUAGE_MAP = {
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JavaScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Bash",
    ".ps1": "PowerShell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".xml": "XML",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".md": "Markdown",
}

# Dependency files to look for
DEPENDENCY_FILES = [
    "requirements.txt",
    "Pipfile",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "go.mod",
    "Cargo.toml",
]

# Directories to skip
SKIP_DIRS = {
    ".git",
    ".svn",
    "node_modules",
    "__pycache__",
    "venv",
    "env",
    ".venv",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
}


def scan_repo(path: Path, max_files: int = 10000) -> RepoInventory:
    """Scan repository and extract metadata.
    
    Args:
        path: Path to repository root
        max_files: Maximum files to scan (safety limit)
        
    Returns:
        RepoInventory object with metadata
    """
    if not path.exists():
        raise FileNotFoundError(f"Repository path not found: {path}")
    
    # Initialize counters
    language_counts: Counter = Counter()
    total_files = 0
    total_lines = 0
    dependency_files: List[str] = []
    
    # Get git info if available
    git_info: Optional[Dict] = None
    if HAS_GIT:
        try:
            repo = Repo(path)
            git_info = {
                "has_git": True,
                "current_branch": repo.active_branch.name if not repo.head.is_detached else "detached",
                "commit_count": sum(1 for _ in repo.iter_commits()),
                "remote_url": repo.remotes.origin.url if repo.remotes else None,
            }
            last_commit = repo.head.commit
            last_modified = datetime.fromtimestamp(last_commit.committed_date)
        except (InvalidGitRepositoryError, ValueError, Exception):
            git_info = {"has_git": False}
            last_modified = None
    else:
        git_info = {"has_git": False, "error": "GitPython not installed"}
        last_modified = None
    
    # Walk directory tree
    for root, dirs, files in os.walk(path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        for file in files:
            if total_files >= max_files:
                break
            
            file_path = Path(root) / file
            suffix = file_path.suffix.lower()
            
            # Count by language
            if suffix in LANGUAGE_MAP:
                language = LANGUAGE_MAP[suffix]
                language_counts[language] += 1
                
                # Count lines of code
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        total_lines += sum(1 for _ in f)
                except Exception:
                    pass  # Skip files we can't read
            
            # Check for dependency files
            if file in DEPENDENCY_FILES:
                rel_path = str(file_path.relative_to(path))
                dependency_files.append(rel_path)
            
            total_files += 1
    
    return RepoInventory(
        path=str(path),
        total_files=total_files,
        languages=dict(language_counts),
        lines_of_code=total_lines,
        dependency_files=dependency_files,
        last_modified=last_modified,
        git_info=git_info,
    )


def detect_languages(files: List[Path]) -> Dict[str, int]:
    """Detect programming languages from file list.
    
    Args:
        files: List of file paths
        
    Returns:
        Dictionary mapping language to file count
    """
    language_counts: Counter = Counter()
    
    for file in files:
        suffix = file.suffix.lower()
        if suffix in LANGUAGE_MAP:
            language = LANGUAGE_MAP[suffix]
            language_counts[language] += 1
    
    return dict(language_counts)


def extract_dependency_files(path: Path) -> List[str]:
    """Extract list of dependency management files.
    
    Args:
        path: Repository root path
        
    Returns:
        List of relative paths to dependency files
    """
    found_files: List[str] = []
    
    for root, dirs, files in os.walk(path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        for file in files:
            if file in DEPENDENCY_FILES:
                file_path = Path(root) / file
                rel_path = str(file_path.relative_to(path))
                found_files.append(rel_path)
    
    return found_files


def count_lines_of_code(path: Path, extensions: Optional[List[str]] = None) -> int:
    """Count total lines of code in repository.
    
    Args:
        path: Repository root path
        extensions: Optional list of extensions to count (e.g., ['.py', '.js'])
                   If None, counts all code files
        
    Returns:
        Total line count
    """
    total_lines = 0
    
    for root, dirs, files in os.walk(path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        for file in files:
            file_path = Path(root) / file
            suffix = file_path.suffix.lower()
            
            # Filter by extension if specified
            if extensions and suffix not in extensions:
                continue
            
            # Only count known code files
            if suffix not in LANGUAGE_MAP:
                continue
            
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    total_lines += sum(1 for _ in f)
            except Exception:
                pass  # Skip files we can't read
    
    return total_lines
