"""Unit tests for repository skills."""

from pathlib import Path

import pytest

from skills.repo import (
    count_lines_of_code,
    detect_languages,
    extract_dependency_files,
    scan_repo,
)


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Create a sample repository for testing."""
    repo = tmp_path / "sample_repo"
    repo.mkdir()
    
    # Create Python files
    (repo / "main.py").write_text("""
def hello():
    print("Hello, World!")

if __name__ == "__main__":
    hello()
""")
    
    (repo / "utils.py").write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""")
    
    # Create JavaScript file
    (repo / "script.js").write_text("""
function greet(name) {
    console.log(`Hello, ${name}!`);
}
""")
    
    # Create dependency file
    (repo / "requirements.txt").write_text("""
requests==2.28.0
pytest==7.0.0
""")
    
    # Create subdirectory
    subdir = repo / "src"
    subdir.mkdir()
    (subdir / "helper.py").write_text("# Helper module\n")
    
    # Create node_modules (should be skipped)
    node_modules = repo / "node_modules"
    node_modules.mkdir()
    (node_modules / "package.js").write_text("// Should be ignored\n")
    
    return repo


def test_scan_repo(sample_repo: Path) -> None:
    """Test repository scanning."""
    inventory = scan_repo(sample_repo)
    
    assert inventory.path == str(sample_repo)
    assert inventory.total_files > 0
    assert "Python" in inventory.languages
    assert "JavaScript" in inventory.languages
    assert inventory.lines_of_code > 0
    assert "requirements.txt" in inventory.dependency_files


def test_scan_repo_languages(sample_repo: Path) -> None:
    """Test language detection in repo scan."""
    inventory = scan_repo(sample_repo)
    
    # Should detect Python and JavaScript
    assert inventory.languages.get("Python", 0) >= 3  # main.py, utils.py, helper.py
    assert inventory.languages.get("JavaScript", 0) >= 1  # script.js


def test_scan_repo_skips_excluded_dirs(sample_repo: Path) -> None:
    """Test that scan skips excluded directories."""
    inventory = scan_repo(sample_repo)
    
    # node_modules should be skipped, so package.js shouldn't be counted
    # Total files should not include files in node_modules
    assert inventory.total_files < 10  # Small number, not including node_modules


def test_scan_repo_not_found() -> None:
    """Test scanning non-existent repository."""
    with pytest.raises(FileNotFoundError):
        scan_repo(Path("/nonexistent/repo"))


def test_detect_languages() -> None:
    """Test language detection from file list."""
    files = [
        Path("test.py"),
        Path("script.js"),
        Path("style.css"),
        Path("another.py"),
    ]
    
    languages = detect_languages(files)
    
    assert languages["Python"] == 2
    assert languages["JavaScript"] == 1
    assert languages["CSS"] == 1


def test_detect_languages_empty() -> None:
    """Test language detection with empty list."""
    languages = detect_languages([])
    assert languages == {}


def test_extract_dependency_files(sample_repo: Path) -> None:
    """Test dependency file extraction."""
    deps = extract_dependency_files(sample_repo)
    
    assert len(deps) > 0
    assert any("requirements.txt" in d for d in deps)


def test_count_lines_of_code(sample_repo: Path) -> None:
    """Test line counting."""
    total = count_lines_of_code(sample_repo)
    assert total > 0


def test_count_lines_of_code_filtered(sample_repo: Path) -> None:
    """Test line counting with extension filter."""
    python_lines = count_lines_of_code(sample_repo, extensions=[".py"])
    total_lines = count_lines_of_code(sample_repo)
    
    # Python lines should be less than or equal to total
    assert python_lines <= total_lines
    assert python_lines > 0


def test_scan_repo_with_git(tmp_path: Path) -> None:
    """Test scanning repository with git info."""
    # Create a simple repo without git
    repo = tmp_path / "no_git_repo"
    repo.mkdir()
    (repo / "test.py").write_text("print('test')\n")
    
    inventory = scan_repo(repo)
    
    # Should handle missing git gracefully
    assert inventory.git_info is not None
    assert inventory.git_info["has_git"] is False
