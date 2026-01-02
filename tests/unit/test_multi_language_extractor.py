"""Tests for multi-language dependency extractor."""

import pytest
from pathlib import Path
from skills.multi_language_extractor import (
    LanguageDetector,
    MultiLanguageDependencyExtractor,
    JavaExtractor,
    JavaScriptExtractor,
    CSharpExtractor,
    PHPExtractor,
    scan_multi_language_directory,
)


def test_language_detector():
    """Test language detection from file extensions."""
    assert LanguageDetector.detect(Path("test.py")) == "python"
    assert LanguageDetector.detect(Path("test.java")) == "java"
    assert LanguageDetector.detect(Path("test.js")) == "javascript"
    assert LanguageDetector.detect(Path("test.ts")) == "typescript"
    assert LanguageDetector.detect(Path("test.cs")) == "csharp"
    assert LanguageDetector.detect(Path("test.php")) == "php"
    assert LanguageDetector.detect(Path("test.sql")) == "sql"
    assert LanguageDetector.detect(Path("test.unknown")) == "unknown"


def test_java_import_extraction(tmp_path: Path):
    """Test Java import extraction."""
    java_code = '''
package com.example;

import java.util.List;
import java.sql.Connection;
import com.company.Service;

public class UserService {
    // code
}
'''
    
    file_path = tmp_path / "UserService.java"
    file_path.write_text(java_code)
    
    extractor = JavaExtractor()
    result = extractor.extract(file_path)
    
    assert result['language'] == 'java'
    assert 'java.util.List' in result['imports']['imports']
    assert 'java.sql.Connection' in result['imports']['imports']
    assert 'com.company.Service' in result['imports']['imports']


def test_java_sql_extraction(tmp_path: Path):
    """Test SQL extraction from Java."""
    java_code = '''
public class UserDAO {
    public User findById(int id) {
        String sql = "SELECT id, name, email FROM users WHERE id = ?";
        PreparedStatement stmt = conn.prepareStatement(sql);
        return stmt.executeQuery();
    }
    
    public void create(User user) {
        String query = "INSERT INTO users (name, email) VALUES (?, ?)";
        conn.executeUpdate(query);
    }
}
'''
    
    file_path = tmp_path / "UserDAO.java"
    file_path.write_text(java_code)
    
    extractor = JavaExtractor()
    result = extractor.extract(file_path)
    
    assert len(result['sql_queries']) >= 2
    
    # Check SELECT query
    select_queries = [q for q in result['sql_queries'] if q['type'] == 'SELECT']
    assert len(select_queries) >= 1
    assert select_queries[0]['table'] == 'users'
    
    # Check INSERT query
    insert_queries = [q for q in result['sql_queries'] if q['type'] == 'INSERT']
    assert len(insert_queries) >= 1
    assert insert_queries[0]['table'] == 'users'


def test_javascript_import_extraction(tmp_path: Path):
    """Test JavaScript import extraction."""
    js_code = '''
import express from 'express';
import { Pool } from 'pg';
const mysql = require('mysql');

// code
'''
    
    file_path = tmp_path / "server.js"
    file_path.write_text(js_code)
    
    extractor = JavaScriptExtractor()
    result = extractor.extract(file_path)
    
    assert result['language'] == 'javascript'
    assert 'express' in result['imports']['imports']
    assert 'pg' in result['imports']['imports']
    assert 'mysql' in result['imports']['imports']


def test_javascript_sql_extraction(tmp_path: Path):
    """Test SQL extraction from JavaScript."""
    js_code = '''
async function getUsers() {
    const query = "SELECT * FROM users WHERE active = true";
    return await db.query(query);
}

async function createOrder(userId, total) {
    const sql = `INSERT INTO orders (user_id, total) VALUES ($1, $2)`;
    await db.execute(sql, [userId, total]);
}
'''
    
    file_path = tmp_path / "db.js"
    file_path.write_text(js_code)
    
    extractor = JavaScriptExtractor()
    result = extractor.extract(file_path)
    
    assert len(result['sql_queries']) >= 2
    
    # Check queries
    assert any(q['type'] == 'SELECT' for q in result['sql_queries'])
    assert any(q['type'] == 'INSERT' for q in result['sql_queries'])
    assert any(q['table'] == 'users' for q in result['sql_queries'])
    assert any(q['table'] == 'orders' for q in result['sql_queries'])


def test_csharp_using_extraction(tmp_path: Path):
    """Test C# using extraction."""
    cs_code = '''
using System;
using System.Data;
using System.Data.SqlClient;

namespace MyApp {
    public class UserService {
        // code
    }
}
'''
    
    file_path = tmp_path / "UserService.cs"
    file_path.write_text(cs_code)
    
    extractor = CSharpExtractor()
    result = extractor.extract(file_path)
    
    assert result['language'] == 'csharp'
    assert 'System' in result['imports']['imports']
    assert 'System.Data' in result['imports']['imports']
    assert 'System.Data.SqlClient' in result['imports']['imports']


def test_csharp_sql_extraction(tmp_path: Path):
    """Test SQL extraction from C#."""
    cs_code = '''
public class UserRepository {
    public User GetById(int id) {
        string sql = "SELECT id, name FROM users WHERE id = @id";
        SqlCommand cmd = new SqlCommand(sql, connection);
        return cmd.ExecuteReader();
    }
    
    public void Update(User user) {
        var query = @"UPDATE users SET name = @name WHERE id = @id";
        cmd.ExecuteNonQuery();
    }
}
'''
    
    file_path = tmp_path / "UserRepository.cs"
    file_path.write_text(cs_code)
    
    extractor = CSharpExtractor()
    result = extractor.extract(file_path)
    
    assert len(result['sql_queries']) >= 2
    assert any(q['type'] == 'SELECT' for q in result['sql_queries'])
    assert any(q['type'] == 'UPDATE' for q in result['sql_queries'])


def test_php_include_extraction(tmp_path: Path):
    """Test PHP include/require extraction."""
    php_code = '''
<?php
require_once 'config.php';
include 'functions.php';
require 'db.php';

// code
?>
'''
    
    file_path = tmp_path / "index.php"
    file_path.write_text(php_code)
    
    extractor = PHPExtractor()
    result = extractor.extract(file_path)
    
    assert result['language'] == 'php'
    assert 'config.php' in result['imports']['imports']
    assert 'functions.php' in result['imports']['imports']
    assert 'db.php' in result['imports']['imports']


def test_php_sql_extraction(tmp_path: Path):
    """Test SQL extraction from PHP."""
    php_code = '''
<?php
function getUsers() {
    $sql = "SELECT * FROM users WHERE status = 'active'";
    return mysqli_query($conn, $sql);
}

function createUser($name, $email) {
    $query = "INSERT INTO users (name, email) VALUES ('$name', '$email')";
    mysql_query($query);
}
?>
'''
    
    file_path = tmp_path / "users.php"
    file_path.write_text(php_code)
    
    extractor = PHPExtractor()
    result = extractor.extract(file_path)
    
    assert len(result['sql_queries']) >= 2
    assert any(q['type'] == 'SELECT' for q in result['sql_queries'])
    assert any(q['type'] == 'INSERT' for q in result['sql_queries'])


def test_multi_language_extractor(tmp_path: Path):
    """Test multi-language extractor dispatches correctly."""
    extractor = MultiLanguageDependencyExtractor()
    
    # Python file
    py_file = tmp_path / "test.py"
    py_file.write_text("import os\n")
    result = extractor.extract_dependencies(py_file)
    assert result['language'] == 'python'
    
    # Java file
    java_file = tmp_path / "Test.java"
    java_file.write_text("import java.util.List;\n")
    result = extractor.extract_dependencies(java_file)
    assert result['language'] == 'java'
    
    # JavaScript file
    js_file = tmp_path / "test.js"
    js_file.write_text("const x = require('express');\n")
    result = extractor.extract_dependencies(js_file)
    assert result['language'] == 'javascript'


def test_scan_multi_language_directory(tmp_path: Path):
    """Test scanning directory with multiple languages."""
    # Create Python file
    (tmp_path / "app.py").write_text('''
import os
conn.execute("SELECT * FROM users")
''')
    
    # Create Java file
    (tmp_path / "Main.java").write_text('''
import java.util.List;
String sql = "SELECT * FROM orders";
''')
    
    # Create JavaScript file
    (tmp_path / "server.js").write_text('''
const db = require('pg');
await db.query("SELECT * FROM products");
''')
    
    results = scan_multi_language_directory(tmp_path)
    
    # Should find all 3 files
    assert len(results) == 3
    
    # Check languages detected
    languages = [r['language'] for r in results.values()]
    assert 'python' in languages
    assert 'java' in languages
    assert 'javascript' in languages
    
    # Check SQL queries found
    all_queries = []
    for result in results.values():
        all_queries.extend(result.get('sql_queries', []))
    
    assert len(all_queries) >= 3
    tables = [q['table'] for q in all_queries if q.get('table')]
    assert 'users' in tables
    assert 'orders' in tables
    assert 'products' in tables


def test_generic_extractor_fallback(tmp_path: Path):
    """Test generic extractor for unknown file types."""
    unknown_file = tmp_path / "script.xyz"
    unknown_file.write_text('''
# Some unknown language
query = "SELECT * FROM data"
''')
    
    extractor = MultiLanguageDependencyExtractor()
    result = extractor.extract_dependencies(unknown_file)
    
    # Should still extract SQL
    assert len(result['sql_queries']) >= 1
    assert result['sql_queries'][0]['table'] == 'data'
