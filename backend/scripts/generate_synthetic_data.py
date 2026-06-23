#!/usr/bin/env python3
import sys
import os
import psycopg2

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'cognitive_db_agent')
DB_USER = os.getenv('DB_USER', 'postgres')
# Use password from .env (e.g. postgres) or default dev password
DB_PASSWORD = os.getenv('DB_PASSWORD', 'sibyl_sql_dev_password')

def main():
    print(f"Connecting to database {DB_NAME} at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        conn.autocommit = True
        cursor = conn.cursor()
    except Exception as e:
        print(f"Failed with password in env ({e}), trying password 'postgres'...")
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password='postgres',
                database=DB_NAME
            )
            conn.autocommit = True
            cursor = conn.cursor()
        except Exception as ex:
            print(f"Failed with password 'postgres' ({ex}), trying 'sibyl_sql_dev_password'...")
            try:
                conn = psycopg2.connect(
                    host=DB_HOST,
                    port=DB_PORT,
                    user=DB_USER,
                    password='sibyl_sql_dev_password',
                    database=DB_NAME
                )
                conn.autocommit = True
                cursor = conn.cursor()
            except Exception as ex2:
                print(f"All connection attempts failed: {ex2}")
                sys.exit(1)
            
    print("Connected successfully!")
    
    sql = """
    DO $$
    DECLARE
        bob_id UUID;
        carol_id UUID;
        dave_id UUID;
        eve_id UUID;
        i INT;
        regions TEXT[] := ARRAY['North', 'South', 'East', 'West'];
        products TEXT[] := ARRAY['Product A', 'Product B', 'Product C', 'Product D', 'Product E'];
        user_ids UUID[];
    BEGIN
        -- Get manager user IDs to preserve RLS associations
        SELECT id INTO bob_id FROM users WHERE username = 'bob_manager_north';
        SELECT id INTO carol_id FROM users WHERE username = 'carol_manager_south';
        SELECT id INTO dave_id FROM users WHERE username = 'dave_manager_east';
        SELECT id INTO eve_id FROM users WHERE username = 'eve_manager_west';

        user_ids := ARRAY[bob_id, carol_id, dave_id, eve_id];

        -- Insert 500 synthetic sales records
        FOR i IN 1..500 LOOP
            DECLARE
                year_val INT := 2024 + floor(random() * 2)::INT;      -- 2024 or 2025
                quarter_val INT := 1 + floor(random() * 4)::INT;     -- 1 to 4
                region_idx INT := 1 + floor(random() * 4)::INT;      -- 1 to 4
                product_idx INT := 1 + floor(random() * 5)::INT;     -- 1 to 5
                amount_val DECIMAL(15, 2) := (30000 + (random() * 470000))::DECIMAL(15,2);
                region_val TEXT;
                user_id_val UUID;
                product_val TEXT;
            BEGIN
                region_val := regions[region_idx];
                user_id_val := user_ids[region_idx];
                product_val := products[product_idx];

                INSERT INTO sales_data (year, quarter, amount, region, product, user_id)
                VALUES (year_val, quarter_val, amount_val, region_val, product_val, user_id_val);
            END;
        END LOOP;

        RAISE NOTICE '✓ Successfully inserted 500 synthetic sales records';
    END $$;
    """
    
    print("Running synthetic data generation SQL...")
    try:
        cursor.execute(sql)
        for notice in conn.notices:
            print(notice.strip())
        print("Done!")
    except Exception as e:
        print(f"Execution failed: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
