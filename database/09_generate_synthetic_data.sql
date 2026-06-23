-- ================================
-- Cognitive Database Agent - Generate Synthetic Data
-- ================================
-- Purpose: Populates the sales_data table with more synthetic records for testing.
-- Generates data for years 2024 and 2025 across all regions with corresponding manager assignments.
-- ================================

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

    RAISE NOTICE '✓ Successfully inserted 500 synthetic sales records for 2024 and 2025';
END $$;
