"""Database analysis skills (read-only)."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import sqlparse

from core.models import DBSchema, QueryEvent


def parse_schema_export(file: Path) -> DBSchema:
    """Parse database schema from export file (JSON or SQL DDL).
    
    Args:
        file: Path to schema export file
        
    Returns:
        DBSchema object
    """
    if not file.exists():
        raise FileNotFoundError(f"Schema file not found: {file}")
    
    suffix = file.suffix.lower()
    
    if suffix == ".json":
        return _parse_schema_json(file)
    elif suffix == ".sql":
        return _parse_schema_sql(file)
    else:
        raise ValueError(f"Unsupported schema format: {suffix}")


def _parse_schema_json(file: Path) -> DBSchema:
    """Parse JSON schema export."""
    with open(file, "r") as f:
        data = json.load(f)
    
    # Handle different JSON schema formats
    # This is a simplified implementation - production would handle various formats
    
    if "database_name" in data:
        return DBSchema(**data)
    else:
        # Try to infer structure
        tables = data.get("tables", [])
        return DBSchema(
            database_name=data.get("name", "unknown"),
            tables=tables,
            indexes=data.get("indexes", []),
            relationships=data.get("relationships", []),
            total_tables=len(tables),
            total_columns=sum(len(t.get("columns", [])) for t in tables),
        )


def _parse_schema_sql(file: Path) -> DBSchema:
    """Parse SQL DDL schema export.
    
    This is a simplified implementation that extracts basic table info.
    Production version would use a proper SQL parser or database introspection.
    """
    with open(file, "r") as f:
        sql = f.read()
    
    # Parse SQL statements
    statements = sqlparse.split(sql)
    
    tables: List[Dict[str, Any]] = []
    indexes: List[Dict[str, Any]] = []
    
    for statement in statements:
        parsed = sqlparse.parse(statement)[0]
        stmt_type = parsed.get_type()
        
        if stmt_type == "CREATE":
            # Extract table name
            tokens = [t for t in parsed.tokens if not t.is_whitespace]
            
            # Look for CREATE TABLE
            if any("TABLE" in str(t).upper() for t in tokens):
                table_info = _extract_table_info(statement)
                if table_info:
                    tables.append(table_info)
            
            # Look for CREATE INDEX
            elif any("INDEX" in str(t).upper() for t in tokens):
                index_info = _extract_index_info(statement)
                if index_info:
                    indexes.append(index_info)
    
    total_columns = sum(len(t.get("columns", [])) for t in tables)
    
    return DBSchema(
        database_name="imported_schema",
        tables=tables,
        indexes=indexes,
        relationships=[],  # Would need FK analysis
        total_tables=len(tables),
        total_columns=total_columns,
    )


def _extract_table_info(statement: str) -> Optional[Dict[str, Any]]:
    """Extract table information from CREATE TABLE statement."""
    # Simplified extraction - production would use proper SQL AST
    match = re.search(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", statement, re.IGNORECASE)
    if not match:
        return None
    
    table_name = match.group(1)
    
    # Extract column definitions (simplified)
    columns: List[Dict[str, str]] = []
    column_pattern = r"(\w+)\s+(VARCHAR|INT|INTEGER|TEXT|DECIMAL|DATE|TIMESTAMP|BOOLEAN)"
    
    for match in re.finditer(column_pattern, statement, re.IGNORECASE):
        columns.append({
            "name": match.group(1),
            "type": match.group(2).upper(),
        })
    
    return {
        "name": table_name,
        "columns": columns,
        "row_count": None,  # Not available from DDL
    }


def _extract_index_info(statement: str) -> Optional[Dict[str, Any]]:
    """Extract index information from CREATE INDEX statement."""
    match = re.search(r"CREATE\s+(?:UNIQUE\s+)?INDEX\s+(\w+)\s+ON\s+(\w+)", statement, re.IGNORECASE)
    if not match:
        return None
    
    return {
        "name": match.group(1),
        "table": match.group(2),
        "unique": "UNIQUE" in statement.upper(),
    }


def parse_query_log(file: Path, limit: Optional[int] = None) -> List[QueryEvent]:
    """Parse database query log file.
    
    Args:
        file: Path to query log file
        limit: Optional limit on number of events to parse
        
    Returns:
        List of QueryEvent objects
    """
    if not file.exists():
        raise FileNotFoundError(f"Query log not found: {file}")
    
    suffix = file.suffix.lower()
    
    if suffix == ".json":
        return _parse_query_log_json(file, limit)
    elif suffix in [".log", ".txt"]:
        return _parse_query_log_text(file, limit)
    else:
        raise ValueError(f"Unsupported log format: {suffix}")


def _parse_query_log_json(file: Path, limit: Optional[int]) -> List[QueryEvent]:
    """Parse JSON query log."""
    with open(file, "r") as f:
        data = json.load(f)
    
    events: List[QueryEvent] = []
    
    # Handle array or newline-delimited JSON
    if isinstance(data, list):
        entries = data
    else:
        # Assume single entry or need to read line by line
        entries = [data]
    
    for entry in entries[:limit] if limit else entries:
        try:
            events.append(QueryEvent(
                query=entry.get("query", ""),
                timestamp=datetime.fromisoformat(entry.get("timestamp", datetime.now().isoformat())),
                duration_ms=float(entry.get("duration_ms", 0)),
                rows_affected=entry.get("rows_affected"),
                database=entry.get("database"),
                user=entry.get("user"),
            ))
        except Exception:
            continue  # Skip malformed entries
    
    return events


def _parse_query_log_text(file: Path, limit: Optional[int]) -> List[QueryEvent]:
    """Parse text-based query log.
    
    This is a simplified parser for demonstration.
    Production would handle various log formats.
    """
    events: List[QueryEvent] = []
    
    with open(file, "r") as f:
        for i, line in enumerate(f):
            if limit and i >= limit:
                break
            
            # Try to extract timestamp and query
            # Example format: "2024-01-01 12:00:00 [INFO] Query: SELECT * FROM users; Duration: 123ms"
            timestamp_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", line)
            query_match = re.search(r"Query:\s*(.+?)(?:;|\s+Duration:)", line)
            duration_match = re.search(r"Duration:\s*(\d+(?:\.\d+)?)ms", line)
            
            if query_match:
                timestamp = datetime.fromisoformat(timestamp_match.group(1)) if timestamp_match else datetime.now()
                query = query_match.group(1).strip()
                duration = float(duration_match.group(1)) if duration_match else 0.0
                
                events.append(QueryEvent(
                    query=query,
                    timestamp=timestamp,
                    duration_ms=duration,
                ))
    
    return events


def estimate_query_cost(events: List[QueryEvent], schema: Optional[DBSchema] = None) -> Dict[str, Any]:
    """Estimate query cost from log events.
    
    Args:
        events: List of query events
        schema: Optional schema for enhanced analysis
        
    Returns:
        Dictionary with cost metrics
    """
    if not events:
        return {
            "total_queries": 0,
            "total_duration_ms": 0,
            "avg_duration_ms": 0,
            "slowest_queries": [],
        }
    
    # Calculate basic metrics
    total_duration = sum(e.duration_ms for e in events)
    avg_duration = total_duration / len(events)
    
    # Find slowest queries
    slowest = sorted(events, key=lambda e: e.duration_ms, reverse=True)[:10]
    
    # Analyze query types
    query_types = {
        "SELECT": 0,
        "INSERT": 0,
        "UPDATE": 0,
        "DELETE": 0,
        "OTHER": 0,
    }
    
    for event in events:
        query_upper = event.query.upper().strip()
        for qtype in query_types:
            if query_upper.startswith(qtype):
                query_types[qtype] += 1
                break
        else:
            query_types["OTHER"] += 1
    
    return {
        "total_queries": len(events),
        "total_duration_ms": total_duration,
        "avg_duration_ms": avg_duration,
        "query_types": query_types,
        "slowest_queries": [
            {
                "query": e.query[:100] + "..." if len(e.query) > 100 else e.query,
                "duration_ms": e.duration_ms,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in slowest
        ],
    }
