-- ================================
-- Cognitive Database Agent - Security Testing
-- ================================
-- Purpose: Verify that RLS policies are working correctly
-- This script tests all three roles and their access patterns
-- ================================

-- ================================
-- SETUP: Create test session
-- ================================

-- ================================
-- TEST 1: Admin Role - Full Access
-- ================================

-- Switch to admin role
SET LOCAL ROLE db_admin;

-- Test SELECT (should see all regions)
DO $$
DECLARE
    total_count INTEGER;
    north_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_count FROM sales_data;
    SELECT COUNT(*) INTO north_count FROM sales_data WHERE region = 'North';

    RAISE NOTICE 'Admin SELECT test:';
    RAISE NOTICE '  Total records visible: %', total_count;
    RAISE NOTICE '  North region records: %', north_count;

    IF total_count >= 48 THEN
        RAISE NOTICE '  ✓ PASS: Admin can see all records';
    ELSE
        RAISE NOTICE '  ✗ FAIL: Admin should see all records';
    END IF;
END $$;

-- Test INSERT (should succeed)
DO $$
BEGIN
    INSERT INTO sales_data (year, quarter, amount, region, product)
    VALUES (2024, 1, 999999.99, 'North', 'Test Product');

    RAISE NOTICE 'Admin INSERT test:';
    RAISE NOTICE '  ✓ PASS: Admin can insert records';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  ✗ FAIL: Admin insert failed: %', SQLERRM;
END $$;

-- Test UPDATE (should succeed)
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE sales_data
    SET amount = 888888.88
    WHERE year = 2024 AND quarter = 1 AND product = 'Test Product';

    GET DIAGNOSTICS updated_count = ROW_COUNT;

    RAISE NOTICE 'Admin UPDATE test:';
    RAISE NOTICE '  Updated % records', updated_count;
    RAISE NOTICE '  ✓ PASS: Admin can update records';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  ✗ FAIL: Admin update failed: %', SQLERRM;
END $$;

-- Test DELETE (should succeed)
DO $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sales_data
    WHERE year = 2024 AND quarter = 1 AND product = 'Test Product';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RAISE NOTICE 'Admin DELETE test:';
    RAISE NOTICE '  Deleted % records', deleted_count;
    RAISE NOTICE '  ✓ PASS: Admin can delete records';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  ✗ FAIL: Admin delete failed: %', SQLERRM;
END $$;

-- Reset role
RESET ROLE;

-- ================================
-- TEST 2: Manager Role - Regional Access
-- ================================

-- Switch to manager role and set region to North
SET LOCAL ROLE db_manager;
SET LOCAL app.user_region = 'North';

-- Test SELECT (should only see North region)
DO $$
DECLARE
    total_count INTEGER;
    north_count INTEGER;
    south_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_count FROM sales_data;
    SELECT COUNT(*) INTO north_count FROM sales_data WHERE region = 'North';
    SELECT COUNT(*) INTO south_count FROM sales_data WHERE region = 'South';

    RAISE NOTICE 'Manager SELECT test (region = North):';
    RAISE NOTICE '  Total records visible: %', total_count;
    RAISE NOTICE '  North region records: %', north_count;
    RAISE NOTICE '  South region records: %', south_count;

    IF total_count = north_count AND south_count = 0 THEN
        RAISE NOTICE '  ✓ PASS: Manager can only see their region';
    ELSE
        RAISE NOTICE '  ✗ FAIL: Manager should only see North region';
    END IF;
END $$;

-- Test INSERT in allowed region (should succeed)
DO $$
BEGIN
    INSERT INTO sales_data (year, quarter, amount, region, product)
    VALUES (2024, 1, 777777.77, 'North', 'Manager Test Product');

    RAISE NOTICE 'Manager INSERT test (own region):';
    RAISE NOTICE '  ✓ PASS: Manager can insert in their region';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  ✗ FAIL: Manager insert in own region failed: %', SQLERRM;
END $$;

-- Test INSERT in different region (should fail)
DO $$
BEGIN
    INSERT INTO sales_data (year, quarter, amount, region, product)
    VALUES (2024, 1, 666666.66, 'South', 'Forbidden Product');

    RAISE NOTICE 'Manager INSERT test (other region):';
    RAISE NOTICE '  ✗ FAIL: Manager should NOT be able to insert in other regions';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  ✓ PASS: Manager blocked from inserting in other regions';
        RAISE NOTICE '  Error: %', SQLERRM;
END $$;

-- Test UPDATE in allowed region (should succeed)
DO $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE sales_data
    SET amount = 555555.55
    WHERE year = 2024 AND quarter = 1 AND region = 'North';

    GET DIAGNOSTICS updated_count = ROW_COUNT;

    RAISE NOTICE 'Manager UPDATE test (own region):';
    RAISE NOTICE '  Updated % records', updated_count;
    RAISE NOTICE '  ✓ PASS: Manager can update their region';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  ✗ FAIL: Manager update failed: %', SQLERRM;
END $$;

-- Test DELETE in allowed region (should succeed)
DO $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sales_data
    WHERE year = 2024 AND quarter = 1 AND region = 'North';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RAISE NOTICE 'Manager DELETE test (own region):';
    RAISE NOTICE '  Deleted % records', deleted_count;
    RAISE NOTICE '  ✓ PASS: Manager can delete in their region';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  ✗ FAIL: Manager delete failed: %', SQLERRM;
END $$;

-- Try to DELETE from different region (should affect 0 rows)
DO $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sales_data
    WHERE region = 'South' AND year = 2021;

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RAISE NOTICE 'Manager DELETE test (other region):';
    IF deleted_count = 0 THEN
        RAISE NOTICE '  ✓ PASS: Manager cannot delete other regions (% rows affected)', deleted_count;
    ELSE
        RAISE NOTICE '  ✗ FAIL: Manager should not delete other regions';
    END IF;
END $$;

-- Reset role
RESET ROLE;

-- ================================
-- TEST 3: Viewer Role - Read-Only Access
-- ================================

-- Switch to viewer role
SET LOCAL ROLE db_viewer;

-- Test SELECT (should see all regions)
DO $$
DECLARE
    total_count INTEGER;
    regions_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_count FROM sales_data;
    SELECT COUNT(DISTINCT region) INTO regions_count FROM sales_data;

    RAISE NOTICE 'Viewer SELECT test:';
    RAISE NOTICE '  Total records visible: %', total_count;
    RAISE NOTICE '  Distinct regions visible: %', regions_count;

    IF total_count >= 48 AND regions_count = 4 THEN
        RAISE NOTICE '  ✓ PASS: Viewer can read all records';
    ELSE
        RAISE NOTICE '  ✗ FAIL: Viewer should see all records and regions';
    END IF;
END $$;

-- Test INSERT (should fail)
DO $$
BEGIN
    INSERT INTO sales_data (year, quarter, amount, region, product)
    VALUES (2024, 1, 111111.11, 'North', 'Viewer Test');

    RAISE NOTICE 'Viewer INSERT test:';
    RAISE NOTICE '  ✗ FAIL: Viewer should NOT be able to insert';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  ✓ PASS: Viewer blocked from inserting';
        RAISE NOTICE '  Error: %', SQLERRM;
END $$;

-- Test UPDATE (should fail)
DO $$
BEGIN
    UPDATE sales_data
    SET amount = 222222.22
    WHERE year = 2021 AND region = 'North';

    RAISE NOTICE 'Viewer UPDATE test:';
    RAISE NOTICE '  ✗ FAIL: Viewer should NOT be able to update';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  ✓ PASS: Viewer blocked from updating';
        RAISE NOTICE '  Error: %', SQLERRM;
END $$;

-- Test DELETE (should fail)
DO $$
BEGIN
    DELETE FROM sales_data WHERE year = 2021;

    RAISE NOTICE 'Viewer DELETE test:';
    RAISE NOTICE '  ✗ FAIL: Viewer should NOT be able to delete';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '  ✓ PASS: Viewer blocked from deleting';
        RAISE NOTICE '  Error: %', SQLERRM;
END $$;

-- Reset role
RESET ROLE;

-- ================================
-- TEST 4: Cross-Region Access Test
-- ================================

-- Test South region manager
SET LOCAL ROLE db_manager;
SET LOCAL app.user_region = 'South';

DO $$
DECLARE
    south_count INTEGER;
    north_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO south_count FROM sales_data WHERE region = 'South';
    SELECT COUNT(*) INTO north_count FROM sales_data WHERE region = 'North';

    RAISE NOTICE 'South region manager:';
    RAISE NOTICE '  Can see South records: %', south_count;
    RAISE NOTICE '  Can see North records: %', north_count;

    IF south_count > 0 AND north_count = 0 THEN
        RAISE NOTICE '  ✓ PASS: Regional isolation working correctly';
    ELSE
        RAISE NOTICE '  ✗ FAIL: Regional isolation not working';
    END IF;
END $$;

RESET ROLE;

-- ================================
-- Final Summary
-- ================================

-- ================================
-- Verify final state
-- ================================
SELECT
    'Final Data Count' as check_name,
    COUNT(*) as total_records,
    COUNT(DISTINCT region) as regions,
    COUNT(DISTINCT year) as years
FROM sales_data;
