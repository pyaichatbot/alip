"""Production-grade multi-language parser using tree-sitter.

Tree-sitter provides accurate, fast parsing for all major languages
with a unified query API. This is the ONLY parser we should use in production.

Supported languages:
- Python, Java, JavaScript/TypeScript, C#, PHP, Go, Ruby, Rust, C/C++

Installation:
    pip install tree-sitter tree-sitter-languages

Note: tree-sitter-languages includes pre-built parsers for all major languages.
No need to build/compile individual language grammars.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Any
import re

try:
    from tree_sitter import Language, Parser, Node
    from tree_sitter_languages import get_language, get_parser
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False
    Language = None
    Parser = None
    Node = None


class TreeSitterExtractor:
    """Production parser using tree-sitter for all languages.
    
    This is a proper AST-based parser that works for all languages,
    not regex hacks. Use this in production.
    """
    
    # Language detection by extension
    EXTENSION_MAP = {
        '.py': 'python',
        '.java': 'java',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'tsx',
        '.cs': 'c_sharp',
        '.php': 'php',
        '.go': 'go',
        '.rb': 'ruby',
        '.rs': 'rust',
        '.c': 'c',
        '.h': 'c',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.hpp': 'cpp',
        '.sql': 'sql',
    }
    
    # SQL keywords to detect queries
    SQL_KEYWORDS = {'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER'}
    
    def __init__(self):
        """Initialize tree-sitter parsers."""
        if not HAS_TREE_SITTER:
            raise ImportError(
                "tree-sitter is required for production use. Install with:\n"
                "  pip install tree-sitter tree-sitter-languages"
            )
        
        self.parsers = {}
        self._init_parsers()
    
    def _init_parsers(self):
        """Initialize parsers for all supported languages."""
        for lang in ['python', 'java', 'javascript', 'typescript', 'tsx', 
                     'c_sharp', 'php', 'go', 'ruby', 'rust', 'c', 'cpp']:
            try:
                self.parsers[lang] = get_parser(lang)
            except Exception as e:
                print(f"Warning: Could not load parser for {lang}: {e}")
    
    def detect_language(self, file_path: Path) -> Optional[str]:
        """Detect language from file extension."""
        return self.EXTENSION_MAP.get(file_path.suffix.lower())
    
    def extract_dependencies(self, file_path: Path) -> Dict[str, Any]:
        """Extract dependencies from any source file.
        
        Args:
            file_path: Path to source file
            
        Returns:
            Unified dependency structure
        """
        language = self.detect_language(file_path)
        if not language or language not in self.parsers:
            return self._empty_result(language or 'unknown')
        
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()
        except Exception:
            return self._empty_result(language)
        
        # Parse with tree-sitter
        parser = self.parsers[language]
        tree = parser.parse(source_code)
        
        # Extract dependencies based on language
        if language == 'python':
            return self._extract_python(tree, source_code, file_path)
        elif language == 'java':
            return self._extract_java(tree, source_code, file_path)
        elif language in ['javascript', 'typescript', 'tsx']:
            return self._extract_javascript(tree, source_code, file_path)
        elif language == 'c_sharp':
            return self._extract_csharp(tree, source_code, file_path)
        elif language == 'php':
            return self._extract_php(tree, source_code, file_path)
        elif language == 'go':
            return self._extract_go(tree, source_code, file_path)
        elif language == 'ruby':
            return self._extract_ruby(tree, source_code, file_path)
        else:
            return self._extract_generic(tree, source_code, file_path, language)
    
    def _extract_python(self, tree: Any, source: bytes, file_path: Path) -> Dict:
        """Extract Python dependencies using tree-sitter."""
        imports = []
        from_imports = {}
        sql_queries = []
        db_calls = []
        classes = []
        
        def walk_tree(node: Node):
            """Walk AST and extract information."""
            # Import statements
            if node.type == 'import_statement':
                for child in node.children:
                    if child.type == 'dotted_name':
                        imports.append(self._node_text(child, source))
            
            # From imports
            elif node.type == 'import_from_statement':
                module = None
                names = []
                for child in node.children:
                    if child.type == 'dotted_name':
                        module = self._node_text(child, source)
                    elif child.type == 'import_prefix':
                        # Handle relative imports
                        module = self._node_text(child, source)
                    elif child.type in ['aliased_import', 'dotted_name', 'identifier']:
                        name = self._node_text(child, source)
                        if name not in ['from', 'import', 'as']:
                            names.append(name)
                
                if module and names:
                    from_imports[module] = names
            
            # String literals (for SQL)
            elif node.type == 'string':
                text = self._node_text(node, source).strip('"\'')
                if any(kw in text.upper() for kw in self.SQL_KEYWORDS):
                    sql_queries.append({
                        'query': text,
                        'line': node.start_point[0] + 1,
                        'type': self._get_query_type(text),
                        'table': self._extract_table_name(text)
                    })
            
            # Function calls (for DB operations)
            elif node.type == 'call':
                func_node = node.child_by_field_name('function')
                if func_node:
                    func_name = self._node_text(func_node, source)
                    if any(pattern in func_name.lower() for pattern in ['execute', 'query', 'fetch']):
                        db_calls.append({
                            'name': func_name,
                            'line': node.start_point[0] + 1
                        })
            
            # Class definitions
            elif node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    classes.append(self._node_text(name_node, source))
            
            # Recurse
            for child in node.children:
                walk_tree(child)
        
        walk_tree(tree.root_node)
        
        return {
            'language': 'python',
            'imports': {'imports': sorted(set(imports)), 'from_imports': from_imports},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
            'classes': classes,
        }
    
    def _extract_java(self, tree: Any, source: bytes, file_path: Path) -> Dict:
        """Extract Java dependencies using tree-sitter."""
        imports = []
        sql_queries = []
        db_calls = []
        classes = []
        
        def walk_tree(node: Node):
            # Import declarations
            if node.type == 'import_declaration':
                import_node = node.child_by_field_name('name')
                if import_node:
                    imports.append(self._node_text(import_node, source))
            
            # String literals (SQL)
            elif node.type == 'string_literal':
                text = self._node_text(node, source).strip('"')
                if any(kw in text.upper() for kw in self.SQL_KEYWORDS):
                    sql_queries.append({
                        'query': text,
                        'line': node.start_point[0] + 1,
                        'type': self._get_query_type(text),
                        'table': self._extract_table_name(text)
                    })
            
            # Method invocations (JDBC calls)
            elif node.type == 'method_invocation':
                name_node = node.child_by_field_name('name')
                if name_node:
                    method_name = self._node_text(name_node, source)
                    if method_name in ['execute', 'executeQuery', 'executeUpdate', 
                                      'prepareStatement', 'createQuery']:
                        db_calls.append({
                            'name': method_name,
                            'line': node.start_point[0] + 1
                        })
            
            # Class declarations
            elif node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                if name_node:
                    classes.append(self._node_text(name_node, source))
            
            for child in node.children:
                walk_tree(child)
        
        walk_tree(tree.root_node)
        
        return {
            'language': 'java',
            'imports': {'imports': sorted(set(imports)), 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
            'classes': classes,
        }
    
    def _extract_javascript(self, tree: Any, source: bytes, file_path: Path) -> Dict:
        """Extract JavaScript/TypeScript dependencies."""
        imports = []
        sql_queries = []
        db_calls = []
        
        def walk_tree(node: Node):
            # Import statements
            if node.type == 'import_statement':
                source_node = node.child_by_field_name('source')
                if source_node:
                    import_path = self._node_text(source_node, source).strip('"\'')
                    imports.append(import_path)
            
            # Require calls
            elif node.type == 'call_expression':
                func_node = node.child_by_field_name('function')
                if func_node and self._node_text(func_node, source) == 'require':
                    # Get first argument
                    args_node = node.child_by_field_name('arguments')
                    if args_node and args_node.child_count > 0:
                        for child in args_node.children:
                            if child.type == 'string':
                                imports.append(self._node_text(child, source).strip('"\''))
            
            # String literals and template strings (SQL)
            elif node.type in ['string', 'template_string']:
                text = self._node_text(node, source).strip('"`\'')
                if any(kw in text.upper() for kw in self.SQL_KEYWORDS):
                    sql_queries.append({
                        'query': text,
                        'line': node.start_point[0] + 1,
                        'type': self._get_query_type(text),
                        'table': self._extract_table_name(text)
                    })
            
            # Method calls (DB operations)
            elif node.type == 'call_expression':
                func_node = node.child_by_field_name('function')
                if func_node and func_node.type == 'member_expression':
                    prop_node = func_node.child_by_field_name('property')
                    if prop_node:
                        method = self._node_text(prop_node, source)
                        if method in ['query', 'execute', 'run', 'all', 'get']:
                            db_calls.append({
                                'name': method,
                                'line': node.start_point[0] + 1
                            })
            
            for child in node.children:
                walk_tree(child)
        
        walk_tree(tree.root_node)
        
        return {
            'language': 'javascript',
            'imports': {'imports': sorted(set(imports)), 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
        }
    
    def _extract_csharp(self, tree: Any, source: bytes, file_path: Path) -> Dict:
        """Extract C# dependencies."""
        imports = []
        sql_queries = []
        db_calls = []
        
        def walk_tree(node: Node):
            # Using directives
            if node.type == 'using_directive':
                name_node = node.child_by_field_name('name')
                if name_node:
                    imports.append(self._node_text(name_node, source))
            
            # String literals (SQL)
            elif node.type in ['string_literal', 'verbatim_string_literal']:
                text = self._node_text(node, source).strip('@"\'')
                if any(kw in text.upper() for kw in self.SQL_KEYWORDS):
                    sql_queries.append({
                        'query': text,
                        'line': node.start_point[0] + 1,
                        'type': self._get_query_type(text),
                        'table': self._extract_table_name(text)
                    })
            
            # Method invocations (ADO.NET)
            elif node.type == 'invocation_expression':
                for child in node.children:
                    if child.type == 'member_access_expression':
                        name_node = child.child_by_field_name('name')
                        if name_node:
                            method = self._node_text(name_node, source)
                            if method in ['ExecuteReader', 'ExecuteNonQuery', 'ExecuteScalar']:
                                db_calls.append({
                                    'name': method,
                                    'line': node.start_point[0] + 1
                                })
            
            for child in node.children:
                walk_tree(child)
        
        walk_tree(tree.root_node)
        
        return {
            'language': 'csharp',
            'imports': {'imports': sorted(set(imports)), 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
        }
    
    def _extract_php(self, tree: Any, source: bytes, file_path: Path) -> Dict:
        """Extract PHP dependencies."""
        imports = []
        sql_queries = []
        db_calls = []
        
        def walk_tree(node: Node):
            # Include/require statements
            if node.type in ['include_expression', 'include_once_expression',
                            'require_expression', 'require_once_expression']:
                for child in node.children:
                    if child.type == 'string':
                        imports.append(self._node_text(child, source).strip('"\''))
            
            # String literals (SQL)
            elif node.type == 'string':
                text = self._node_text(node, source).strip('"\'')
                if any(kw in text.upper() for kw in self.SQL_KEYWORDS):
                    sql_queries.append({
                        'query': text,
                        'line': node.start_point[0] + 1,
                        'type': self._get_query_type(text),
                        'table': self._extract_table_name(text)
                    })
            
            # Function calls (MySQL, PDO)
            elif node.type == 'function_call_expression':
                name_node = node.child_by_field_name('function')
                if name_node:
                    func_name = self._node_text(name_node, source)
                    if any(pattern in func_name for pattern in ['query', 'execute', 'prepare', 'mysqli', 'mysql']):
                        db_calls.append({
                            'name': func_name,
                            'line': node.start_point[0] + 1
                        })
            
            for child in node.children:
                walk_tree(child)
        
        walk_tree(tree.root_node)
        
        return {
            'language': 'php',
            'imports': {'imports': sorted(set(imports)), 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
        }
    
    def _extract_go(self, tree: Any, source: bytes, file_path: Path) -> Dict:
        """Extract Go dependencies."""
        imports = []
        sql_queries = []
        db_calls = []
        
        def walk_tree(node: Node):
            # Import declarations
            if node.type == 'import_spec':
                path_node = node.child_by_field_name('path')
                if path_node:
                    imports.append(self._node_text(path_node, source).strip('"'))
            
            # String literals (SQL)
            elif node.type in ['interpreted_string_literal', 'raw_string_literal']:
                text = self._node_text(node, source).strip('"`')
                if any(kw in text.upper() for kw in self.SQL_KEYWORDS):
                    sql_queries.append({
                        'query': text,
                        'line': node.start_point[0] + 1,
                        'type': self._get_query_type(text),
                        'table': self._extract_table_name(text)
                    })
            
            for child in node.children:
                walk_tree(child)
        
        walk_tree(tree.root_node)
        
        return {
            'language': 'go',
            'imports': {'imports': sorted(set(imports)), 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
        }
    
    def _extract_ruby(self, tree: Any, source: bytes, file_path: Path) -> Dict:
        """Extract Ruby dependencies."""
        imports = []
        sql_queries = []
        db_calls = []
        
        def walk_tree(node: Node):
            # Require statements
            if node.type == 'call':
                method_node = node.child_by_field_name('method')
                if method_node and self._node_text(method_node, source) == 'require':
                    args_node = node.child_by_field_name('arguments')
                    if args_node:
                        for child in args_node.children:
                            if child.type == 'string':
                                imports.append(self._node_text(child, source).strip('"\''))
            
            # String literals (SQL)
            elif node.type == 'string':
                text = self._node_text(node, source).strip('"\'')
                if any(kw in text.upper() for kw in self.SQL_KEYWORDS):
                    sql_queries.append({
                        'query': text,
                        'line': node.start_point[0] + 1,
                        'type': self._get_query_type(text),
                        'table': self._extract_table_name(text)
                    })
            
            for child in node.children:
                walk_tree(child)
        
        walk_tree(tree.root_node)
        
        return {
            'language': 'ruby',
            'imports': {'imports': sorted(set(imports)), 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': db_calls,
        }
    
    def _extract_generic(self, tree: Any, source: bytes, file_path: Path, language: str) -> Dict:
        """Generic extraction for other languages."""
        sql_queries = []
        
        def walk_tree(node: Node):
            if 'string' in node.type.lower():
                text = self._node_text(node, source).strip('"\'`')
                if any(kw in text.upper() for kw in self.SQL_KEYWORDS):
                    sql_queries.append({
                        'query': text,
                        'line': node.start_point[0] + 1,
                        'type': self._get_query_type(text),
                        'table': self._extract_table_name(text)
                    })
            
            for child in node.children:
                walk_tree(child)
        
        walk_tree(tree.root_node)
        
        return {
            'language': language,
            'imports': {'imports': [], 'from_imports': {}},
            'sql_queries': sql_queries,
            'db_calls': [],
        }
    
    def _node_text(self, node: Node, source: bytes) -> str:
        """Extract text from node."""
        return source[node.start_byte:node.end_byte].decode('utf-8')
    
    def _get_query_type(self, query: str) -> Optional[str]:
        """Determine SQL query type."""
        query_upper = query.upper().strip()
        for keyword in self.SQL_KEYWORDS:
            if query_upper.startswith(keyword):
                return keyword
        return None
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name from SQL query."""
        patterns = [
            (r'FROM\s+(\w+)', 'FROM'),
            (r'INTO\s+(\w+)', 'INTO'),
            (r'UPDATE\s+(\w+)', 'UPDATE'),
            (r'TABLE\s+(\w+)', 'TABLE'),
        ]
        
        for pattern, _ in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _empty_result(self, language: str) -> Dict:
        """Return empty result structure."""
        return {
            'language': language,
            'imports': {'imports': [], 'from_imports': {}},
            'sql_queries': [],
            'db_calls': [],
        }


def scan_directory_with_tree_sitter(directory: Path) -> Dict[str, Dict]:
    """Scan directory using tree-sitter for all files.
    
    Args:
        directory: Root directory to scan
        
    Returns:
        Dict mapping file paths to dependency info
    """
    if not HAS_TREE_SITTER:
        raise ImportError(
            "tree-sitter is required. Install with:\n"
            "  pip install tree-sitter tree-sitter-languages"
        )
    
    extractor = TreeSitterExtractor()
    results = {}
    
    for file_path in directory.rglob('*'):
        if not file_path.is_file():
            continue
        
        # Skip common non-source directories
        if any(skip in str(file_path) for skip in ['__pycache__', 'node_modules', '.git', 'venv']):
            continue
        
        language = extractor.detect_language(file_path)
        if not language:
            continue
        
        try:
            rel_path = file_path.relative_to(directory)
            dependencies = extractor.extract_dependencies(file_path)
            results[str(rel_path)] = dependencies
        except Exception as e:
            print(f"Warning: Failed to parse {file_path}: {e}")
            continue
    
    return results
