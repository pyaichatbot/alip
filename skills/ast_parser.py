"""AST parser for extracting code dependencies and patterns.

This module provides functions to analyze Python source code using
the Abstract Syntax Tree (AST) to extract:
- Import statements
- Function calls
- SQL queries embedded in code
- Class definitions and relationships
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class DependencyExtractor(ast.NodeVisitor):
    """AST visitor to extract dependencies from Python code."""

    def __init__(self):
        """Initialize extractor."""
        self.imports: Set[str] = set()
        self.from_imports: Dict[str, List[str]] = {}
        self.function_calls: Set[str] = set()
        self.class_names: Set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        """Extract import statements."""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Extract from...import statements."""
        if node.module:
            imported_names = [alias.name for alias in node.names]
            if node.module in self.from_imports:
                self.from_imports[node.module].extend(imported_names)
            else:
                self.from_imports[node.module] = imported_names
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Extract function calls."""
        func_name = self._get_call_name(node.func)
        if func_name:
            self.function_calls.add(func_name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class definitions."""
        self.class_names.add(node.name)
        self.generic_visit(node)

    def _get_call_name(self, node: ast.expr) -> Optional[str]:
        """Get the name of a function call."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # For methods like obj.method()
            value = self._get_call_name(node.value)
            if value:
                return f"{value}.{node.attr}"
            return node.attr
        return None


def parse_python_imports(file_path: Path) -> Dict[str, List[str]]:
    """Extract all import statements from a Python file.
    
    Args:
        file_path: Path to Python source file
        
    Returns:
        Dict with 'imports' (simple imports) and 'from_imports' (module -> names)
        
    Example:
        {
            'imports': ['os', 'sys', 'json'],
            'from_imports': {
                'pathlib': ['Path'],
                'typing': ['Dict', 'List']
            }
        }
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(file_path))
        extractor = DependencyExtractor()
        extractor.visit(tree)
        
        return {
            'imports': sorted(list(extractor.imports)),
            'from_imports': {
                k: sorted(v) for k, v in extractor.from_imports.items()
            }
        }
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return {'imports': [], 'from_imports': {}}


def find_function_calls(file_path: Path, target_patterns: Optional[List[str]] = None) -> List[Dict]:
    """Find function calls in Python code.
    
    Args:
        file_path: Path to Python source file
        target_patterns: Optional list of patterns to match (e.g., ['execute', 'query'])
        
    Returns:
        List of function call dictionaries with name and line number
        
    Example:
        [
            {'name': 'conn.execute', 'line': 42},
            {'name': 'cursor.fetchall', 'line': 43}
        ]
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(file_path))
        extractor = DependencyExtractor()
        extractor.visit(tree)
        
        # Get line numbers for each call
        calls = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = extractor._get_call_name(node.func)
                if func_name:
                    # Filter by patterns if provided
                    if target_patterns:
                        if any(pattern in func_name.lower() for pattern in target_patterns):
                            calls.append({
                                'name': func_name,
                                'line': node.lineno
                            })
                    else:
                        calls.append({
                            'name': func_name,
                            'line': node.lineno
                        })
        
        return calls
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return []


def extract_sql_queries(file_path: Path) -> List[Dict]:
    """Extract SQL queries from Python code.
    
    Looks for:
    - String literals containing SQL keywords
    - conn.execute(), cursor.execute() calls
    - SQL in multiline strings
    
    Args:
        file_path: Path to Python source file
        
    Returns:
        List of SQL query dictionaries with query, line, and type
        
    Example:
        [
            {
                'query': 'SELECT * FROM users',
                'line': 42,
                'type': 'SELECT',
                'table': 'users'
            }
        ]
    """
    sql_keywords = r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|FROM|WHERE|JOIN)\b'
    queries = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, start=1):
            # Look for SQL keywords in strings
            if re.search(sql_keywords, line, re.IGNORECASE):
                # Try to extract the query
                # Pattern 1: execute("SELECT ...")
                execute_pattern = r'\.execute\s*\(\s*["\'](.+?)["\']'
                match = re.search(execute_pattern, line)
                
                if match:
                    query = match.group(1)
                else:
                    # Pattern 2: Just a string with SQL
                    string_pattern = r'["\'](.+?)["\']'
                    match = re.search(string_pattern, line)
                    if match:
                        query = match.group(1)
                    else:
                        continue
                
                # Determine query type
                query_upper = query.upper()
                query_type = None
                for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP']:
                    if query_upper.strip().startswith(keyword):
                        query_type = keyword
                        break
                
                # Extract table name (basic)
                table = None
                from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
                if from_match:
                    table = from_match.group(1)
                else:
                    into_match = re.search(r'INTO\s+(\w+)', query, re.IGNORECASE)
                    if into_match:
                        table = into_match.group(1)
                    else:
                        update_match = re.search(r'UPDATE\s+(\w+)', query, re.IGNORECASE)
                        if update_match:
                            table = update_match.group(1)
                
                queries.append({
                    'query': query.strip(),
                    'line': line_num,
                    'type': query_type,
                    'table': table
                })
    
    except (UnicodeDecodeError, FileNotFoundError):
        pass
    
    return queries


def extract_class_hierarchy(file_path: Path) -> Dict[str, List[str]]:
    """Extract class definitions and their base classes.
    
    Args:
        file_path: Path to Python source file
        
    Returns:
        Dict mapping class name to list of base classes
        
    Example:
        {
            'UserService': ['BaseService'],
            'AdminUser': ['User', 'Admin']
        }
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(file_path))
        
        hierarchy = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        # For qualified names like module.Class
                        bases.append(base.attr)
                
                hierarchy[node.name] = bases
        
        return hierarchy
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        return {}


def scan_directory_for_dependencies(
    directory: Path,
    extensions: Optional[List[str]] = None
) -> Dict[str, Dict]:
    """Scan entire directory for Python dependencies.
    
    Args:
        directory: Root directory to scan
        extensions: File extensions to process (default: ['.py'])
        
    Returns:
        Dict mapping file paths to their dependency info
        
    Example:
        {
            'src/api.py': {
                'imports': ['flask', 'json'],
                'sql_queries': [...],
                'functions_called': [...]
            }
        }
    """
    if extensions is None:
        extensions = ['.py']
    
    results = {}
    
    for ext in extensions:
        for file_path in directory.rglob(f'*{ext}'):
            if '__pycache__' in str(file_path):
                continue
            
            rel_path = file_path.relative_to(directory)
            
            imports = parse_python_imports(file_path)
            sql_queries = extract_sql_queries(file_path)
            db_calls = find_function_calls(file_path, ['execute', 'query', 'fetch'])
            
            results[str(rel_path)] = {
                'imports': imports,
                'sql_queries': sql_queries,
                'db_calls': db_calls,
                'classes': extract_class_hierarchy(file_path)
            }
    
    return results
