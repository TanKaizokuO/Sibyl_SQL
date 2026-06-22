#!/bin/bash
# ==================================
# Cognitive Database Agent - Database Setup Script
# ==================================
# This script sets up the PostgreSQL database with:
# - Extensions (pgvector, uuid-ossp)
# - Tables (users, roles, permissions, sales_data, sales_archive, knowledge_documents)
# - Sample data
# - Row-Level Security (RLS) policies
# ==================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Database Setup Script${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

# Load environment variables
source .env

# Database connection parameters
DB_NAME="${DB_NAME:-cognitive_db_agent}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

echo -e "${YELLOW}Database: ${DB_NAME}${NC}"
echo -e "${YELLOW}User: ${DB_USER}${NC}"
echo -e "${YELLOW}Host: ${DB_HOST}:${DB_PORT}${NC}"
echo ""

# Function to run SQL file
run_sql() {
    local file=$1
    local description=$2

    echo -e "${YELLOW}Running: ${description}...${NC}"
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$file"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ ${description} completed${NC}"
    else
        echo -e "${RED}✗ ${description} failed${NC}"
        exit 1
    fi
    echo ""
}

# Check if database exists
echo -e "${YELLOW}Checking database connection...${NC}"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}Cannot connect to database: ${DB_NAME}${NC}"
    echo -e "${YELLOW}Creating database...${NC}"
    PGPASSWORD=$DB_PASSWORD createdb -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Database created${NC}"
    else
        echo -e "${RED}✗ Failed to create database${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Database connection successful${NC}"
fi
echo ""

# Run SQL scripts in order
run_sql "database/01_setup_extensions.sql" "Setting up extensions (pgvector, uuid-ossp)"
run_sql "database/02_create_tables.sql" "Creating tables"
run_sql "database/03_insert_sample_data.sql" "Inserting sample data"
run_sql "database/04_create_rls_policies.sql" "Creating RLS policies"
run_sql "database/05_test_security.sql" "Testing security policies"

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✓ Database setup completed!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Install Python dependencies: pip install -r requirements.txt"
echo "3. Ingest schema knowledge: python -m backend.scripts.ingest_knowledge"
echo "4. Start the API server: python backend/main.py"
echo "5. Try the CLI demo: python backend/cli_demo.py"
echo ""
