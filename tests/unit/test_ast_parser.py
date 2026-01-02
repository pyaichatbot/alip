"""Tests for AST parser skill."""

import pytest
from pathlib import Path
from skills.ast_parser import (
    parse_python_imports,
    find_function_calls,
    extract_sql_queries,
    extract_class_hierarchy,
    scan_directory_for_dependencies,
)


@pytest.fixture
def sample_python_file(tmp_path: Path) -> Path:
    """Create a sample Python file for testing."""
    code = '''
import os
import sys
from pathlib import Path
from typing import Dict, List

class UserService:
    """Service for user operations."""
    
    def get_user(self, user_id: int):
        conn = get_connection()
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()
    
    def create_user(self, email: str):
        conn = get_connection()
        conn.execute("INSERT INTO users (email) VALUES (?)", (email,))
        conn.commit()
'''
    
    file_path = tmp_path / "test_module.py"
    file_path.write_text(code)
    return file_path


@pytest.fixture
def complex_python_file(tmp_path: Path) -> Path:
    """Create a more complex Python file."""
    code = '''
from flask import Flask, request
from database import get_connection
import json

class BaseService:
    pass

class UserService(BaseService):
    def list_users(self):
        result = self.db.query("SELECT id, email, name FROM users")
        return result.fetchall()
    
    def update_user(self, user_id, data):
        query = "UPDATE users SET name = ? WHERE id = ?"
        self.db.execute(query, (data['name'], user_id))

class AdminUser(UserService):
    pass
'''
    
    file_path = tmp_path / "complex.py"
    file_path.write_text(code)
    return file_path


def test_parse_python_imports_simple(sample_python_file: Path):
    """Test parsing simple imports."""
    result = parse_python_imports(sample_python_file)
    
    assert 'imports' in result
    assert 'from_imports' in result
    
    # Check simple imports
    assert 'os' in result['imports']
    assert 'sys' in result['imports']
    
    # Check from imports
    assert 'pathlib' in result['from_imports']
    assert 'Path' in result['from_imports']['pathlib']
    assert 'typing' in result['from_imports']
    assert 'Dict' in result['from_imports']['typing']
    assert 'List' in result['from_imports']['typing']


def test_parse_python_imports_complex(complex_python_file: Path):
    """Test parsing imports from complex file."""
    result = parse_python_imports(complex_python_file)
    
    assert 'flask' in result['from_imports']
    assert 'Flask' in result['from_imports']['flask']
    assert 'request' in result['from_imports']['flask']
    
    assert 'database' in result['from_imports']
    assert 'get_connection' in result['from_imports']['database']
    
    assert 'json' in result['imports']


def test_parse_invalid_file(tmp_path: Path):
    """Test parsing invalid Python file."""
    invalid_file = tmp_path / "invalid.py"
    invalid_file.write_text("this is not valid python ][][")
    
    result = parse_python_imports(invalid_file)
    
    # Should return empty results, not crash
    assert result['imports'] == []
    assert result['from_imports'] == {}


def test_find_function_calls(sample_python_file: Path):
    """Test finding function calls in code."""
    # Find all database-related calls
    calls = find_function_calls(sample_python_file, ['execute', 'fetch'])
    
    assert len(calls) > 0
    
    # Check we found execute calls
    execute_calls = [c for c in calls if 'execute' in c['name']]
    assert len(execute_calls) >= 2
    
    # Check we found fetchone
    fetch_calls = [c for c in calls if 'fetch' in c['name']]
    assert len(fetch_calls) >= 1
    
    # Check line numbers are present
    for call in calls:
        assert 'line' in call
        assert call['line'] > 0


def test_find_function_calls_no_filter(sample_python_file: Path):
    """Test finding all function calls without filter."""
    calls = find_function_calls(sample_python_file)
    
    # Should find all calls including get_connection, execute, fetchone, commit
    assert len(calls) >= 4
    
    call_names = [c['name'] for c in calls]
    assert 'get_connection' in call_names


def test_extract_sql_queries(sample_python_file: Path):
    """Test extracting SQL queries from code."""
    queries = extract_sql_queries(sample_python_file)
    
    assert len(queries) == 2
    
    # Check SELECT query
    select_query = queries[0]
    assert 'SELECT' in select_query['query'].upper()
    assert select_query['type'] == 'SELECT'
    assert select_query['table'] == 'users'
    assert select_query['line'] > 0
    
    # Check INSERT query
    insert_query = queries[1]
    assert 'INSERT' in insert_query['query'].upper()
    assert insert_query['type'] == 'INSERT'
    assert insert_query['table'] == 'users'


def test_extract_sql_queries_complex(complex_python_file: Path):
    """Test extracting queries from complex file."""
    queries = extract_sql_queries(complex_python_file)
    
    assert len(queries) >= 2
    
    # Check we got SELECT
    select_queries = [q for q in queries if q['type'] == 'SELECT']
    assert len(select_queries) >= 1
    
    # Check we got UPDATE
    update_queries = [q for q in queries if q['type'] == 'UPDATE']
    assert len(update_queries) >= 1


def test_extract_class_hierarchy(sample_python_file: Path):
    """Test extracting class hierarchy."""
    hierarchy = extract_class_hierarchy(sample_python_file)
    
    assert 'UserService' in hierarchy
    # UserService has no base classes
    assert hierarchy['UserService'] == []


def test_extract_class_hierarchy_complex(complex_python_file: Path):
    """Test extracting complex class hierarchy."""
    hierarchy = extract_class_hierarchy(complex_python_file)
    
    assert 'BaseService' in hierarchy
    assert hierarchy['BaseService'] == []
    
    assert 'UserService' in hierarchy
    assert 'BaseService' in hierarchy['UserService']
    
    assert 'AdminUser' in hierarchy
    assert 'UserService' in hierarchy['AdminUser']


def test_scan_directory_for_dependencies(tmp_path: Path):
    """Test scanning entire directory."""
    # Create multiple files
    (tmp_path / "module1.py").write_text("""
import os
conn.execute("SELECT * FROM users")
""")
    
    (tmp_path / "module2.py").write_text("""
from typing import List
class MyClass:
    pass
""")
    
    # Create subdirectory
    subdir = tmp_path / "submodule"
    subdir.mkdir()
    (subdir / "module3.py").write_text("""
import sys
query("SELECT * FROM orders")
""")
    
    results = scan_directory_for_dependencies(tmp_path)
    
    # Should find all 3 files
    assert len(results) >= 3
    
    # Check module1.py
    assert 'module1.py' in results or str(Path('module1.py')) in results
    module1_key = 'module1.py' if 'module1.py' in results else str(Path('module1.py'))
    assert 'os' in results[module1_key]['imports']['imports']
    assert len(results[module1_key]['sql_queries']) >= 1
    
    # Check module2.py
    assert 'module2.py' in results or str(Path('module2.py')) in results
    module2_key = 'module2.py' if 'module2.py' in results else str(Path('module2.py'))
    assert 'typing' in results[module2_key]['imports']['from_imports']
    assert 'MyClass' in results[module2_key]['classes']


def test_empty_file(tmp_path: Path):
    """Test parsing empty file."""
    empty_file = tmp_path / "empty.py"
    empty_file.write_text("")
    
    result = parse_python_imports(empty_file)
    assert result['imports'] == []
    assert result['from_imports'] == {}
    
    calls = find_function_calls(empty_file)
    assert calls == []
    
    queries = extract_sql_queries(empty_file)
    assert queries == []


def test_file_with_comments_only(tmp_path: Path):
    """Test file with only comments."""
    comment_file = tmp_path / "comments.py"
    comment_file.write_text("""
# This is a comment
# Another comment
# SELECT * FROM users -- this is in a comment
""")
    
    queries = extract_sql_queries(comment_file)
    # Should not extract SQL from comments
    assert len(queries) == 0
