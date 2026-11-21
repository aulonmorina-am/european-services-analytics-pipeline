-- Service classification dimension (BPM6 bop_item codes), seed-backed.
-- Hierarchy and ICT focus flag come from the Eurostat codelist.
-- is_reporting_level is declared in the seed, not inferred from the hierarchy:
-- SOX ("commercial services") is a child of S but its value equals the sum of its
-- 11 siblings, so it must not be summed alongside them.
SELECT
    bop_item,
    bop_item_label,
    nullif(parent_bop_item, '') AS parent_bop_item,
    is_ict_service::boolean AS is_ict_service,
    is_reporting_level::boolean AS is_reporting_level
FROM {{ ref('bop_items') }}
