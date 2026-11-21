-- Service classification dimension (BPM6 bop_item) with drill-down hierarchy.
-- service_level: 0 = total 'S', 1 = sections (SA..SZ), 2-3 = sub-items (SI, SI2, SI21Z...).
-- Never sum across levels: 'S' already contains SI* etc.
-- The BPM6 hierarchy nests, so a level-1 section already contains all its
-- children: summing across levels multiplies the total.
--
-- is_reporting_level is NOT "service_level = 1". SOX ("commercial services") is a
-- level-1 child of S whose value equals the sum of its 11 siblings, so it overlaps
-- them. The seed declares the reporting grain explicitly to keep SOX out of it;
-- summing all 14 level-1 children over-counts exports by ~42%.
WITH RECURSIVE hierarchy AS (

    SELECT
        bop_item,
        parent_bop_item,
        0 AS service_level
    FROM {{ ref('int_bop_item') }}
    WHERE parent_bop_item IS NULL

    UNION ALL

    SELECT
        child.bop_item,
        child.parent_bop_item,
        parent.service_level + 1
    FROM {{ ref('int_bop_item') }} child
    JOIN hierarchy parent
        ON child.parent_bop_item = parent.bop_item

)

SELECT
    item.bop_item,
    item.bop_item_label,
    item.parent_bop_item,
    hierarchy.service_level,
    item.is_ict_service,
    item.is_reporting_level
FROM {{ ref('int_bop_item') }} item
LEFT JOIN hierarchy
    ON hierarchy.bop_item = item.bop_item
