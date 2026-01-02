#!/usr/bin/env python3
"""Demo script to showcase ALIP functionality.

This script creates a demo engagement and ingests sample data.
"""

import json
from pathlib import Path

# Create demo data directory
demo_dir = Path(__file__).parent / "demo_data"
demo_dir.mkdir(exist_ok=True)

# 1. Create sample repository files
repo_dir = demo_dir / "sample_repo"
repo_dir.mkdir(exist_ok=True)

# Main application file
(repo_dir / "app.py").write_text('''"""Main application module."""

from database import get_connection
from utils import format_date


def process_orders():
    """Process pending orders."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, customer_id, total, created_at
        FROM orders
        WHERE status = 'pending'
        ORDER BY created_at DESC
    """)
    
    for order in cursor.fetchall():
        print(f"Processing order {order[0]}")
        # Complex business logic here
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    process_orders()
''')

# Database module
(repo_dir / "database.py").write_text('''"""Database connection utilities."""

import psycopg2


def get_connection():
    """Get database connection."""
    return psycopg2.connect(
        host="localhost",
        database="legacy_erp",
        user="admin",
        password="secretpass123"  # TODO: Move to env vars
    )
''')

# Utilities
(repo_dir / "utils.py").write_text('''"""Utility functions."""

from datetime import datetime


def format_date(date):
    """Format date for display."""
    return date.strftime("%Y-%m-%d")


def calculate_total(items):
    """Calculate order total."""
    return sum(item['price'] * item['quantity'] for item in items)
''')

# Requirements
(repo_dir / "requirements.txt").write_text('''psycopg2==2.9.0
python-dateutil==2.8.2
requests==2.28.0
''')

# 2. Create sample database schema
schema_file = demo_dir / "schema.sql"
schema_file.write_text('''-- Legacy ERP Database Schema

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    total DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock INTEGER DEFAULT 0
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_products_sku ON products(sku);
''')

# 3. Create sample query log
query_log_file = demo_dir / "queries.json"
queries = [
    {
        "query": "SELECT * FROM orders WHERE status = 'pending'",
        "timestamp": "2024-01-01T10:00:00",
        "duration_ms": 245.5,
        "rows_affected": 150,
        "database": "legacy_erp",
    },
    {
        "query": "SELECT * FROM customers WHERE email = 'john@example.com'",
        "timestamp": "2024-01-01T10:01:00",
        "duration_ms": 12.3,
        "rows_affected": 1,
    },
    {
        "query": "SELECT COUNT(*) FROM orders",
        "timestamp": "2024-01-01T10:02:00",
        "duration_ms": 1234.7,
        "rows_affected": 5000,
    },
    {
        "query": "UPDATE orders SET status = 'completed' WHERE id = 123",
        "timestamp": "2024-01-01T10:03:00",
        "duration_ms": 45.2,
        "rows_affected": 1,
    },
    {
        "query": "INSERT INTO orders (customer_id, total, status) VALUES (456, 99.99, 'pending')",
        "timestamp": "2024-01-01T10:04:00",
        "duration_ms": 23.1,
        "rows_affected": 1,
    },
]

with open(query_log_file, "w") as f:
    json.dump(queries, f, indent=2)

# 4. Create sample documentation
docs_dir = demo_dir / "docs"
docs_dir.mkdir(exist_ok=True)

(docs_dir / "architecture.md").write_text('''# Legacy ERP Architecture

## Overview

The Legacy ERP system is a monolithic Python application that manages:
- Customer data
- Order processing
- Inventory management
- Invoicing

## Components

### Database
- PostgreSQL 10
- 4 main tables (customers, orders, order_items, products)
- Manual backups (weekly)

### Application
- Python 2.7 (⚠️ EOL)
- Flask web framework
- Direct SQL queries (no ORM)

## Known Issues

1. **Performance**: Orders query taking >1s during peak hours
2. **Security**: Passwords hardcoded in database.py
3. **Maintenance**: No automated testing
4. **Documentation**: Tribal knowledge, retiring staff

## Dependencies

See requirements.txt (last updated 2019)
''')

(docs_dir / "runbook.txt").write_text('''LEGACY ERP RUNBOOK

STARTUP:
1. Start PostgreSQL service
2. Run python app.py
3. Check logs in /var/log/erp.log

SHUTDOWN:
1. Stop app.py (Ctrl+C)
2. Backup database: pg_dump legacy_erp > backup.sql

TROUBLESHOOTING:
- If orders not processing, check database connection
- If slow queries, restart PostgreSQL
- Contact John (ext 1234) for urgent issues

BACKUP SCHEDULE:
- Daily: Incremental
- Weekly: Full backup to tape
- Manual process (run backup.sh)
''')

print("✓ Demo data created successfully!")
print(f"\nDemo data location: {demo_dir.absolute()}")
print("\nTo run the demo:")
print("  1. alip new --name 'Demo Corp' --id demo-001")
print(f"  2. alip ingest --engagement demo-001 \\")
print(f"       --repo {repo_dir.absolute()} \\")
print(f"       --db-schema {schema_file.absolute()} \\")
print(f"       --query-logs {query_log_file.absolute()} \\")
print(f"       --docs {docs_dir.absolute()}")
print("  3. alip list")
