"""Unit tests for database skills."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from skills.database import (
    estimate_query_cost,
    parse_query_log,
    parse_schema_export,
)


@pytest.fixture
def sample_schema_json(tmp_path: Path) -> Path:
    """Create sample JSON schema file."""
    schema_file = tmp_path / "schema.json"
    schema_data = {
        "database_name": "test_db",
        "tables": [
            {
                "name": "users",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "email", "type": "VARCHAR"},
                    {"name": "created_at", "type": "TIMESTAMP"},
                ],
                "row_count": 1000,
            },
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "user_id", "type": "INTEGER"},
                    {"name": "total", "type": "DECIMAL"},
                ],
                "row_count": 5000,
            },
        ],
        "indexes": [
            {"name": "idx_users_email", "table": "users"},
        ],
        "relationships": [
            {"from_table": "orders", "to_table": "users", "type": "foreign_key"},
        ],
        "total_tables": 2,
        "total_columns": 6,
    }
    
    with open(schema_file, "w") as f:
        json.dump(schema_data, f)
    
    return schema_file


@pytest.fixture
def sample_schema_sql(tmp_path: Path) -> Path:
    """Create sample SQL schema file."""
    schema_file = tmp_path / "schema.sql"
    schema_file.write_text("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    total DECIMAL(10, 2),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX idx_users_email ON users(email);
""")
    
    return schema_file


@pytest.fixture
def sample_query_log_json(tmp_path: Path) -> Path:
    """Create sample JSON query log."""
    log_file = tmp_path / "queries.json"
    log_data = [
        {
            "query": "SELECT * FROM users WHERE email = 'test@example.com'",
            "timestamp": "2024-01-01T10:00:00",
            "duration_ms": 45.2,
            "rows_affected": 1,
            "database": "test_db",
        },
        {
            "query": "SELECT COUNT(*) FROM orders",
            "timestamp": "2024-01-01T10:01:00",
            "duration_ms": 123.5,
            "rows_affected": 5000,
        },
        {
            "query": "INSERT INTO users (email) VALUES ('new@example.com')",
            "timestamp": "2024-01-01T10:02:00",
            "duration_ms": 12.3,
            "rows_affected": 1,
        },
    ]
    
    with open(log_file, "w") as f:
        json.dump(log_data, f)
    
    return log_file


def test_parse_schema_json(sample_schema_json: Path) -> None:
    """Test parsing JSON schema."""
    schema = parse_schema_export(sample_schema_json)
    
    assert schema.database_name == "test_db"
    assert schema.total_tables == 2
    assert schema.total_columns == 6
    assert len(schema.tables) == 2
    assert len(schema.indexes) == 1


def test_parse_schema_sql(sample_schema_sql: Path) -> None:
    """Test parsing SQL DDL schema."""
    schema = parse_schema_export(sample_schema_sql)
    
    assert schema.total_tables == 2
    assert len(schema.tables) == 2
    
    # Check table names
    table_names = {t["name"] for t in schema.tables}
    assert "users" in table_names
    assert "orders" in table_names


def test_parse_schema_not_found() -> None:
    """Test parsing non-existent schema."""
    with pytest.raises(FileNotFoundError):
        parse_schema_export(Path("/nonexistent/schema.json"))


def test_parse_schema_unsupported_format(tmp_path: Path) -> None:
    """Test parsing unsupported schema format."""
    bad_file = tmp_path / "schema.xml"
    bad_file.write_text("<schema></schema>")
    
    with pytest.raises(ValueError):
        parse_schema_export(bad_file)


def test_parse_query_log_json(sample_query_log_json: Path) -> None:
    """Test parsing JSON query log."""
    events = parse_query_log(sample_query_log_json)
    
    assert len(events) == 3
    assert events[0].query.startswith("SELECT")
    assert events[0].duration_ms == 45.2
    assert events[1].duration_ms == 123.5


def test_parse_query_log_with_limit(sample_query_log_json: Path) -> None:
    """Test parsing query log with limit."""
    events = parse_query_log(sample_query_log_json, limit=2)
    
    assert len(events) == 2


def test_parse_query_log_not_found() -> None:
    """Test parsing non-existent log."""
    with pytest.raises(FileNotFoundError):
        parse_query_log(Path("/nonexistent/queries.json"))


def test_estimate_query_cost_empty() -> None:
    """Test cost estimation with empty event list."""
    cost = estimate_query_cost([])
    
    assert cost["total_queries"] == 0
    assert cost["total_duration_ms"] == 0
    assert cost["avg_duration_ms"] == 0


def test_estimate_query_cost(sample_query_log_json: Path) -> None:
    """Test query cost estimation."""
    events = parse_query_log(sample_query_log_json)
    cost = estimate_query_cost(events)
    
    assert cost["total_queries"] == 3
    assert cost["total_duration_ms"] > 0
    assert cost["avg_duration_ms"] > 0
    assert "query_types" in cost
    assert "slowest_queries" in cost


def test_estimate_query_cost_query_types(sample_query_log_json: Path) -> None:
    """Test query type breakdown in cost estimation."""
    events = parse_query_log(sample_query_log_json)
    cost = estimate_query_cost(events)
    
    query_types = cost["query_types"]
    assert query_types["SELECT"] == 2
    assert query_types["INSERT"] == 1


def test_estimate_query_cost_slowest(sample_query_log_json: Path) -> None:
    """Test slowest query identification."""
    events = parse_query_log(sample_query_log_json)
    cost = estimate_query_cost(events)
    
    slowest = cost["slowest_queries"]
    assert len(slowest) > 0
    
    # First slowest should be the COUNT query (123.5ms)
    assert slowest[0]["duration_ms"] == 123.5
