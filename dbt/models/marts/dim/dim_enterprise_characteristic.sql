-- Enterprise characteristic dimension for the stec fact: enterprise size class
-- (ext_stec01), EBOPS 2010 product (ext_stec02), enterprise control (ext_stec03).
--
-- The three types are INDEPENDENT partitions of the same survey population, not
-- additive slices: summing them triple-counts. Each partition also contains
-- nested/overlapping codes (0-49 contains 10-49 and LT10; SJ1-3 sit inside SJ;
-- DOMC_ABR/NABR sit inside DOMC). is_reporting_level marks the one "all
-- characteristics" row per type, so a value metric filtered to it reads one
-- partition without double-counting.
SELECT
    characteristic_type || '-' || characteristic_code AS characteristic_key,
    characteristic_type,
    characteristic_code,
    characteristic_label,
    is_reporting_level::boolean AS is_reporting_level
FROM {{ ref('stec_characteristics') }}
