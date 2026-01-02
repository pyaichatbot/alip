# Contributing to ALIP

Thank you for your interest in contributing to the AI-Assisted Legacy Intelligence Platform!

## Development Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd alip
   ```

2. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

3. **Set up environment**
   ```bash
   # For LLM features (optional for core development)
   export ANTHROPIC_API_KEY="your-key-here"
   ```

4. **Verify installation**
   ```bash
   pytest -q
   ```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

Follow these guidelines:

- Keep functions small and typed
- Add docstrings to all public functions
- Follow PEP 8 style guide
- Maintain read-only safety guarantees

### 3. Write Tests

Every new feature must include tests:

```bash
# Create test file in tests/unit/
touch tests/unit/test_your_feature.py
```

Example test structure:

```python
"""Unit tests for your feature."""

import pytest
from your_module import your_function


def test_basic_functionality():
    """Test basic case."""
    result = your_function(input_data)
    assert result == expected_output


def test_edge_case():
    """Test edge case."""
    with pytest.raises(ValueError):
        your_function(invalid_input)
```

### 4. Run Quality Checks

```bash
# Run tests
pytest -q

# Format code
black .

# Lint code
ruff check .

# Check coverage
pytest --cov=alip --cov-report=term-missing
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add your feature description"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### 6. Submit Pull Request

1. Push your branch
2. Create pull request with description
3. Ensure all CI checks pass
4. Request review from maintainers

---

## Code Style

### Python Style

```python
# Good: Clear, typed, documented
def scan_repo(path: Path, max_files: int = 10000) -> RepoInventory:
    """Scan repository and extract metadata.
    
    Args:
        path: Path to repository root
        max_files: Maximum files to scan (safety limit)
        
    Returns:
        RepoInventory object with metadata
    """
    # Implementation
    pass


# Bad: No types, no docs, unclear
def scan(p, m=10000):
    # What does this do?
    pass
```

### Function Organization

1. **Keep skills pure and testable**
   - No side effects beyond return value
   - Deterministic when possible
   - Easy to unit test

2. **Use dependency injection**
   ```python
   # Good
   def analyze(data: Data, llm_client: LLMClient) -> Result:
       pass
   
   # Bad - hard to test
   def analyze(data: Data) -> Result:
       llm_client = ClaudeClient()  # Hardcoded dependency
       pass
   ```

3. **Prefer composition over inheritance**

### File Organization

```
module/
├── __init__.py      # Public API exports
├── core.py          # Core functionality
├── utils.py         # Helper functions
└── models.py        # Data models
```

---

## Testing Guidelines

### Unit Tests

- Test individual functions in isolation
- Use fixtures for test data
- Mock external dependencies
- Aim for >80% coverage

```python
@pytest.fixture
def sample_data(tmp_path: Path) -> Path:
    """Create sample test data."""
    data_file = tmp_path / "data.json"
    data_file.write_text('{"key": "value"}')
    return data_file


def test_function(sample_data: Path):
    """Test with fixture data."""
    result = process_file(sample_data)
    assert result.success
```

### Integration Tests

- Test multiple components together
- Use realistic data scenarios
- Verify end-to-end workflows

### Test Data

- Never commit real client data
- Use only synthetic fixtures
- Store fixtures in `tests/fixtures/`

---

## Safety Requirements

### Read-Only Guarantee

All code must maintain read-only safety:

```python
# NEVER write to client systems
# NEVER modify production data
# ALWAYS verify read-only mode

if not config.read_only_mode:
    raise ValueError("Write operations not permitted")
```

### Data Security

```python
# ALWAYS redact sensitive data
if config.redaction_enabled:
    data = redact_text(data)

# NEVER store raw credentials
# NEVER log sensitive information
# ALWAYS use secure connections
```

### Error Handling

```python
# Fail safely
try:
    risky_operation()
except Exception as e:
    logger.error(f"Safe failure: {e}")
    # Return safe default
    return None
```

---

## Documentation

### Code Documentation

```python
def complex_function(
    data: Dict[str, Any],
    options: Optional[Config] = None,
) -> Result:
    """Brief one-line description.
    
    Longer description if needed. Explain what the function does,
    not how it does it (code should be self-explanatory).
    
    Args:
        data: Description of data parameter
        options: Optional configuration
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When data is invalid
        FileNotFoundError: When file doesn't exist
        
    Examples:
        >>> result = complex_function({"key": "value"})
        >>> print(result.status)
        'success'
    """
    pass
```

### README Updates

Update README.md when:
- Adding new features
- Changing CLI interface
- Adding dependencies
- Changing architecture

---

## Architecture Decisions

### When to Add a New Agent

Create a new agent when:
- Responsibility is distinct and cohesive
- Processing is complex enough to warrant separation
- Reusability across multiple engagements

### When to Add a New Skill

Create a new skill when:
- Function is reusable across agents
- Logic is self-contained
- Testing is straightforward

### When to Use LLM

Use LLM only for:
- Summarization
- Hypothesis generation
- Documentation narrative
- Recommendations with caveats

Always extract structure deterministically first.

---

## Performance Guidelines

### Efficiency

```python
# Good: Early exit
def process_large_dataset(data: List, limit: int = 1000):
    results = []
    for i, item in enumerate(data):
        if i >= limit:
            break
        results.append(process(item))
    return results


# Bad: Process everything then slice
def process_large_dataset(data: List, limit: int = 1000):
    results = [process(item) for item in data]
    return results[:limit]
```

### Memory

- Stream large files instead of loading entirely
- Use generators for large datasets
- Clean up resources in finally blocks

---

## Common Pitfalls

### ❌ Don't

```python
# Hardcoded credentials
API_KEY = "sk-1234..."

# Untyped functions
def process(data):
    return data

# No error handling
result = risky_call()

# Side effects in tests
def test_function():
    with open("/tmp/test", "w") as f:  # Pollutes filesystem
        f.write("test")
```

### ✅ Do

```python
# Environment variables
api_key = os.getenv("API_KEY")

# Typed functions
def process(data: Dict[str, Any]) -> Result:
    return Result(data)

# Proper error handling
try:
    result = risky_call()
except Exception as e:
    logger.error(f"Error: {e}")
    return None

# Clean tests with fixtures
def test_function(tmp_path: Path):
    test_file = tmp_path / "test"
    test_file.write_text("test")
```

---

## Getting Help

### Resources

- [Python Documentation](https://docs.python.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Pytest Documentation](https://docs.pytest.org/)

### Questions

- Open an issue for bugs
- Start a discussion for questions
- Contact maintainers for urgent matters

---

## Review Process

### Pull Request Checklist

- [ ] Tests pass (`pytest`)
- [ ] Code is formatted (`black .`)
- [ ] Code is linted (`ruff check .`)
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No real client data included
- [ ] Safety guarantees maintained

### Review Criteria

Reviewers will check:
1. Correctness
2. Test coverage
3. Code style
4. Documentation
5. Safety compliance

---

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release tag
4. Build and publish (maintainers only)

---

Thank you for contributing to ALIP! 🚀
