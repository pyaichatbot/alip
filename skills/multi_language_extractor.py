"""Multi-language dependency extractor for legacy systems.

Supports:
- Python (AST-based)
- JavaScript/TypeScript (regex + basic parsing)
- Java (regex-based)
- C# (regex-based)
- PHP (regex-based)
- SQL (direct queries)
- Generic fallback (pattern matching)

For production systems, consider using:
- tree-sitter (universal parser)
- Language-specific parsers (javaparser, esprima, etc.)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set


class LanguageDetector:
    """Detect programming language from file extension."""
    
    LANGUAGE_MAP = {
        '.py': 'python',
        '.java': 'java',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.go': 'go',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.sql': 'sql',
        '.pl': 'perl',
        '.cbl': 'cobol',
        '.cob': 'cobol',
    }
    
    @classmethod
    def detect(cls, file_path: Path) -> str:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()
        return cls.LANGUAGE_MAP.get(ext, 'unknown')


class MultiLanguageDependencyExtractor:
    """Extract dependencies from multiple programming languages."""
    
    def __init__(self):
        """Initialize extractors for each language."""
        self.extractors = {
            'python': PythonExtractor(),
            'java': JavaExtractor(),
            'javascript': JavaScriptExtractor(),
            'typescript': JavaScriptExtractor(),  # Similar to JS
            'csharp': CSharpExtractor(),
            'php': PHPExtractor(),
            'sql': SQLExtractor(),
            'generic': GenericExtractor(),  # Fallback
        }
    
    def extract_dependencies(
        self,
        file_path: Path,
        language: Optional[str] = None
    ) -> Dict:
        """Extract dependencies from a file.
        
        Args:
            file_path: Path to source file
            language: Optional language override
            
        Returns:
            Dict with imports, db_queries, function_calls, etc.
        """
        if language is None:
            language = LanguageDetector.detect(file_path)
        
        # Get appropriate extractor
        extractor = self.extractors.get(language, self.extractors['generic'])
        
        try:
            return extractor.extract(file_path)
        except Exception as e:
            # Fallback to generic extractor on error
            return self.extractors['generic'].extract(file_path)


class PythonExtractor:
    """Python-specific dependency extractor using AST."""
    
    def extract(self, file_path: Path) -> Dict:
        """Extract Python dependencies."""
        # Use the existing ast_parser
        from skills.ast_parser import (
            parse_python_imports,
            extract_sql_queries,
            find_function_calls
        )
        
        imports = parse_python_imports(file_path)
        sql_queries = extract_sql_queries(file_path)
        db_calls = find_function_calls(file_path, ['execute', 'query', 'fetch'])
        
        return {
            'language': 'python',
            'imports': imports,
            'sql_queries': sql_queries,
            'db_calls': db_calls,
        }


class JavaExtractor:
    """Java dependency extractor using regex patterns."""
    
    def extract(self, file_path: Path) -> Dict:
        """Extract Java dependencies."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return self._empty_result()
        
        imports = self._extract_imports(content)
        sql_queries = self._extract_sql_queries(content)
        db_calls = self._extract_db_calls(content)
        
        return {
            'language': 'java',
            'imports': {'imports': imports, 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
        }
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract Java import statements."""
        # Pattern: import package.name.Class;
        pattern = r'import\s+([\w.]+)\s*;'
        matches = re.findall(pattern, content)
        return sorted(set(matches))
    
    def _extract_sql_queries(self, content: str) -> List[Dict]:
        """Extract SQL from Java strings."""
        queries = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Look for SQL keywords in strings
            if re.search(r'(SELECT|INSERT|UPDATE|DELETE|CREATE)\b', line, re.IGNORECASE):
                # Try to extract the query
                # Pattern: "SELECT ..." or """SELECT ..."""
                query_pattern = r'["\']([^"\']*(?:SELECT|INSERT|UPDATE|DELETE|CREATE)[^"\']*)["\']'
                match = re.search(query_pattern, line, re.IGNORECASE)
                
                if match:
                    query = match.group(1)
                    query_type = self._get_query_type(query)
                    table = self._extract_table_name(query)
                    
                    queries.append({
                        'query': query.strip(),
                        'line': line_num,
                        'type': query_type,
                        'table': table
                    })
        
        return queries
    
    def _extract_db_calls(self, content: str) -> List[Dict]:
        """Extract database method calls."""
        calls = []
        
        # Common Java DB patterns
        patterns = [
            r'\.executeQuery\s*\(',
            r'\.executeUpdate\s*\(',
            r'\.execute\s*\(',
            r'\.prepareStatement\s*\(',
            r'\.createQuery\s*\(',  # JPA
        ]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    method = pattern.replace(r'\s*\(', '').replace('\.', '')
                    calls.append({
                        'name': method,
                        'line': line_num
                    })
        
        return calls
    
    def _get_query_type(self, query: str) -> Optional[str]:
        """Determine SQL query type."""
        query_upper = query.upper().strip()
        for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP']:
            if query_upper.startswith(keyword):
                return keyword
        return None
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name from SQL query."""
        # FROM table
        from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        if from_match:
            return from_match.group(1)
        
        # INTO table
        into_match = re.search(r'INTO\s+(\w+)', query, re.IGNORECASE)
        if into_match:
            return into_match.group(1)
        
        # UPDATE table
        update_match = re.search(r'UPDATE\s+(\w+)', query, re.IGNORECASE)
        if update_match:
            return update_match.group(1)
        
        return None
    
    def _empty_result(self) -> Dict:
        """Return empty result structure."""
        return {
            'language': 'java',
            'imports': {'imports': [], 'from_imports': {}},
            'sql_queries': [],
            'db_calls': [],
        }


class JavaScriptExtractor:
    """JavaScript/TypeScript dependency extractor."""
    
    def extract(self, file_path: Path) -> Dict:
        """Extract JavaScript dependencies."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return self._empty_result()
        
        imports = self._extract_imports(content)
        sql_queries = self._extract_sql_queries(content)
        db_calls = self._extract_db_calls(content)
        
        return {
            'language': 'javascript',
            'imports': {'imports': imports, 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
        }
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract JS/TS imports."""
        imports = []
        
        # import X from 'module'
        pattern1 = r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
        imports.extend(re.findall(pattern1, content))
        
        # const X = require('module')
        pattern2 = r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"
        imports.extend(re.findall(pattern2, content))
        
        return sorted(set(imports))
    
    def _extract_sql_queries(self, content: str) -> List[Dict]:
        """Extract SQL from JS strings and template literals."""
        queries = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            # Check for SQL keywords
            if re.search(r'(SELECT|INSERT|UPDATE|DELETE)\b', line, re.IGNORECASE):
                # String literals
                string_pattern = r'["\']([^"\']*(?:SELECT|INSERT|UPDATE|DELETE)[^"\']*)["\']'
                # Template literals
                template_pattern = r'`([^`]*(?:SELECT|INSERT|UPDATE|DELETE)[^`]*)`'
                
                for pattern in [string_pattern, template_pattern]:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        query = match.group(1)
                        queries.append({
                            'query': query.strip(),
                            'line': line_num,
                            'type': self._get_query_type(query),
                            'table': self._extract_table_name(query)
                        })
        
        return queries
    
    def _extract_db_calls(self, content: str) -> List[Dict]:
        """Extract database method calls."""
        calls = []
        
        patterns = [
            r'\.query\s*\(',
            r'\.execute\s*\(',
            r'\.run\s*\(',
            r'\.all\s*\(',
            r'\.get\s*\(',
        ]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    method = pattern.replace(r'\s*\(', '').replace('\.', '')
                    calls.append({
                        'name': method,
                        'line': line_num
                    })
        
        return calls
    
    def _get_query_type(self, query: str) -> Optional[str]:
        """Determine SQL query type."""
        query_upper = query.upper().strip()
        for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
            if keyword in query_upper:
                return keyword
        return None
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name from SQL."""
        from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        if from_match:
            return from_match.group(1)
        
        into_match = re.search(r'INTO\s+(\w+)', query, re.IGNORECASE)
        if into_match:
            return into_match.group(1)
        
        return None
    
    def _empty_result(self) -> Dict:
        """Return empty result."""
        return {
            'language': 'javascript',
            'imports': {'imports': [], 'from_imports': {}},
            'sql_queries': [],
            'db_calls': [],
        }


class CSharpExtractor:
    """C# dependency extractor."""
    
    def extract(self, file_path: Path) -> Dict:
        """Extract C# dependencies."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return self._empty_result()
        
        imports = self._extract_usings(content)
        sql_queries = self._extract_sql_queries(content)
        db_calls = self._extract_db_calls(content)
        
        return {
            'language': 'csharp',
            'imports': {'imports': imports, 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
        }
    
    def _extract_usings(self, content: str) -> List[str]:
        """Extract using statements."""
        pattern = r'using\s+([\w.]+)\s*;'
        matches = re.findall(pattern, content)
        return sorted(set(matches))
    
    def _extract_sql_queries(self, content: str) -> List[Dict]:
        """Extract SQL from C# strings."""
        queries = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(SELECT|INSERT|UPDATE|DELETE)\b', line, re.IGNORECASE):
                # C# string: "..." or @"..."
                pattern = r'@?"([^"]*(?:SELECT|INSERT|UPDATE|DELETE)[^"]*)"'
                match = re.search(pattern, line, re.IGNORECASE)
                
                if match:
                    query = match.group(1)
                    queries.append({
                        'query': query.strip(),
                        'line': line_num,
                        'type': self._get_query_type(query),
                        'table': self._extract_table_name(query)
                    })
        
        return queries
    
    def _extract_db_calls(self, content: str) -> List[Dict]:
        """Extract ADO.NET calls."""
        calls = []
        
        patterns = [
            r'\.ExecuteReader\s*\(',
            r'\.ExecuteScalar\s*\(',
            r'\.ExecuteNonQuery\s*\(',
            r'new SqlCommand\s*\(',
        ]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    calls.append({
                        'name': pattern.replace(r'\s*\(', '').replace('\.', '').replace('new ', ''),
                        'line': line_num
                    })
        
        return calls
    
    def _get_query_type(self, query: str) -> Optional[str]:
        """Get query type."""
        for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
            if keyword in query.upper():
                return keyword
        return None
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name."""
        from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        return from_match.group(1) if from_match else None
    
    def _empty_result(self) -> Dict:
        """Empty result."""
        return {
            'language': 'csharp',
            'imports': {'imports': [], 'from_imports': {}},
            'sql_queries': [],
            'db_calls': [],
        }


class PHPExtractor:
    """PHP dependency extractor."""
    
    def extract(self, file_path: Path) -> Dict:
        """Extract PHP dependencies."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return self._empty_result()
        
        imports = self._extract_includes(content)
        sql_queries = self._extract_sql_queries(content)
        db_calls = self._extract_db_calls(content)
        
        return {
            'language': 'php',
            'imports': {'imports': imports, 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
        }
    
    def _extract_includes(self, content: str) -> List[str]:
        """Extract require/include statements."""
        patterns = [
            r'require\s+["\']([^"\']+)["\']',
            r'require_once\s+["\']([^"\']+)["\']',
            r'include\s+["\']([^"\']+)["\']',
            r'include_once\s+["\']([^"\']+)["\']',
        ]
        
        imports = []
        for pattern in patterns:
            imports.extend(re.findall(pattern, content))
        
        return sorted(set(imports))
    
    def _extract_sql_queries(self, content: str) -> List[Dict]:
        """Extract SQL from PHP."""
        queries = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if re.search(r'(SELECT|INSERT|UPDATE|DELETE)\b', line, re.IGNORECASE):
                pattern = r'["\']([^"\']*(?:SELECT|INSERT|UPDATE|DELETE)[^"\']*)["\']'
                match = re.search(pattern, line, re.IGNORECASE)
                
                if match:
                    query = match.group(1)
                    queries.append({
                        'query': query.strip(),
                        'line': line_num,
                        'type': self._get_query_type(query),
                        'table': self._extract_table_name(query)
                    })
        
        return queries
    
    def _extract_db_calls(self, content: str) -> List[Dict]:
        """Extract MySQL/PDO calls."""
        calls = []
        
        patterns = [
            r'mysql_query\s*\(',
            r'mysqli_query\s*\(',
            r'->query\s*\(',
            r'->execute\s*\(',
            r'->prepare\s*\(',
        ]
        
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line):
                    calls.append({
                        'name': pattern.replace(r'\s*\(', '').replace('->', ''),
                        'line': line_num
                    })
        
        return calls
    
    def _get_query_type(self, query: str) -> Optional[str]:
        """Get query type."""
        for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
            if keyword in query.upper():
                return keyword
        return None
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name."""
        from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        return from_match.group(1) if from_match else None
    
    def _empty_result(self) -> Dict:
        """Empty result."""
        return {
            'language': 'php',
            'imports': {'imports': [], 'from_imports': {}},
            'sql_queries': [],
            'db_calls': [],
        }


class SQLExtractor:
    """SQL file extractor."""
    
    def extract(self, file_path: Path) -> Dict:
        """Extract from .sql files."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            return self._empty_result()
        
        tables = self._extract_tables(content)
        
        return {
            'language': 'sql',
            'imports': {'imports': [], 'from_imports': {}},
            'sql_queries': [],
            'tables_defined': tables,
        }
    
    def _extract_tables(self, content: str) -> List[str]:
        """Extract table names from CREATE statements."""
        pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)'
        matches = re.findall(pattern, content, re.IGNORECASE)
        return sorted(set(matches))
    
    def _empty_result(self) -> Dict:
        """Empty result."""
        return {
            'language': 'sql',
            'imports': {'imports': [], 'from_imports': {}},
            'sql_queries': [],
            'tables_defined': [],
        }


class GenericExtractor:
    """Generic fallback extractor for unknown languages."""
    
    def extract(self, file_path: Path) -> Dict:
        """Extract basic patterns from any text file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except:
            return self._empty_result()
        
        # Try to find SQL queries at least
        sql_queries = self._extract_sql_queries(content)
        
        return {
            'language': 'unknown',
            'imports': {'imports': [], 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': [],
        }
    
    def _extract_sql_queries(self, content: str) -> List[Dict]:
        """Extract SQL from any text."""
        queries = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE)\b', line, re.IGNORECASE):
                # Try to extract query from quotes
                patterns = [
                    r'["\']([^"\']*(?:SELECT|INSERT|UPDATE|DELETE)[^"\']*)["\']',
                    r'`([^`]*(?:SELECT|INSERT|UPDATE|DELETE)[^`]*)`',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        query = match.group(1)
                        queries.append({
                            'query': query.strip(),
                            'line': line_num,
                            'type': self._get_query_type(query),
                            'table': self._extract_table_name(query)
                        })
                        break
        
        return queries
    
    def _get_query_type(self, query: str) -> Optional[str]:
        """Get query type."""
        for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE']:
            if keyword in query.upper():
                return keyword
        return None
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name."""
        from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        return from_match.group(1) if from_match else None
    
    def _empty_result(self) -> Dict:
        """Empty result."""
        return {
            'language': 'unknown',
            'imports': {'imports': [], 'from_imports': {}},
            'sql_queries': [],
            'db_calls': [],
        }


def scan_multi_language_directory(directory: Path) -> Dict[str, Dict]:
    """Scan directory for dependencies in all supported languages.
    
    Args:
        directory: Root directory to scan
        
    Returns:
        Dict mapping file paths to their dependency info
    """
    extractor = MultiLanguageDependencyExtractor()
    results = {}
    
    # Scan all files
    for file_path in directory.rglob('*'):
        if file_path.is_file() and '__pycache__' not in str(file_path):
            language = LanguageDetector.detect(file_path)
            
            # Skip binary and unknown files
            if language == 'unknown' and file_path.suffix in ['.exe', '.dll', '.so', '.class']:
                continue
            
            rel_path = file_path.relative_to(directory)
            dependencies = extractor.extract_dependencies(file_path, language)
            
            results[str(rel_path)] = dependencies
    
    return results
