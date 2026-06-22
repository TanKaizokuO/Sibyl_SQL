#!/usr/bin/env python3
"""
Alternative Database Setup Script - Pure Python
================================================
Sets up the PostgreSQL database using Python instead of psql command-line tools.
Use this if you don't have PostgreSQL bin directory in your PATH.

This script:
1. Creates the database
2. Runs all SQL setup scripts
3. Tests the connection
"""

import sys
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'cognitive_db_agent')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(text)
    print("=" * 60 + "\n")

def run_sql_file(cursor, filepath):
    """Execute a SQL file."""
    print(f"Running: {os.path.basename(filepath)}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sql = f.read()
            cursor.execute(sql)
        print(f"✓ {os.path.basename(filepath)} completed")
        return True
    except Exception as e:
        print(f"✗ {os.path.basename(filepath)} failed: {e}")
        return False

def main():
    """Main setup function."""
    print_header("Database Setup Script (Python)")

    print(f"Database: {DB_NAME}")
    print(f"User: {DB_USER}")
    print(f"Host: {DB_HOST}:{DB_PORT}\n")

    if not DB_PASSWORD:
        print("Error: DB_PASSWORD not set in .env file!")
        sys.exit(1)

    # Step 1: Connect to PostgreSQL (default database)
    print("Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database='postgres'  # Connect to default database first
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print("✓ Connected to PostgreSQL\n")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check PostgreSQL service is running")
        print("  2. Verify DB_PASSWORD in .env file")
        print("  3. Ensure PostgreSQL is listening on localhost:5432")
        sys.exit(1)

    # Step 2: Create database if it doesn't exist
    print(f"Checking if database '{DB_NAME}' exists...")
    try:
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()

        if not exists:
            print(f"Creating database '{DB_NAME}'...")
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"✓ Database '{DB_NAME}' created")
        else:
            print(f"✓ Database '{DB_NAME}' already exists")
    except Exception as e:
        print(f"✗ Database creation failed: {e}")
        cursor.close()
        conn.close()
        sys.exit(1)

    # Close connection to default database
    cursor.close()
    conn.close()

    # Step 3: Connect to our new database
    print(f"\nConnecting to '{DB_NAME}'...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print(f"✓ Connected to '{DB_NAME}'\n")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sys.exit(1)

    # Step 4: Run SQL scripts
    sql_files = [
        ('database/01_setup_extensions.sql', 'Setting up extensions (pgvector, uuid-ossp)'),
        ('database/02_create_tables.sql', 'Creating tables'),
        ('database/03_insert_sample_data.sql', 'Inserting sample data'),
        ('database/04_create_rls_policies.sql', 'Creating RLS policies'),
        ('database/05_test_security.sql', 'Testing security policies'),
        ('database/07_create_auth_tables.sql', 'Creating authentication tables'),
        ('database/08_create_audit_log.sql', 'Creating audit log tables'),
    ]

    all_success = True
    for filepath, description in sql_files:
        print(f"\n{description}...")
        if not run_sql_file(cursor, filepath):
            all_success = False
            if 'extensions' in filepath:
                print("\nIf you see 'pgvector extension not found':")
                print("  1. Download pgvector for Windows from:")
                print("     https://github.com/pgvector/pgvector/releases")
                print("  2. Copy vector.dll to PostgreSQL lib directory")
                print("  3. Restart PostgreSQL service")
                print("  4. Run this script again")
            break

    # Close connection
    cursor.close()
    conn.close()

    # Summary
    print_header("Setup Complete!" if all_success else "Setup Failed")

    if all_success:
        print("Database setup completed successfully!\n")
        print("Next steps:")
        print("  1. Install Python dependencies: uv pip install -r requirements.txt")
        print("  2. Ingest schema knowledge: python backend\\scripts\\ingest_knowledge.py")
        print("  3. Start the API server: python backend\\main.py")
        print("  4. Try the CLI demo: python backend\\cli_demo.py\n")
    else:
        print("Database setup failed. Check the error messages above.\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
