-- Service classification dimension (BPM6 bop_item codes), seed-backed.
-- Hierarchy and ICT focus flag come from the Eurostat codelist.
SELECT
    bop_item,
    bop_item_label,
    nullif(parent_bop_item, '') AS parent_bop_item,
    is_ict_service::boolean AS is_ict_service
FROM {{ ref('bop_items') }}
