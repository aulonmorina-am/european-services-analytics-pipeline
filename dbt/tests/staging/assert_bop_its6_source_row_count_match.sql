-- Staging deduplicates re-ingested Fivetran files, so compare against the
-- distinct business-key count in the source, not the raw row count.
WITH source_distinct_keys AS (

    SELECT COUNT(DISTINCT CONCAT_WS('|', freq, currency, bop_item, stk_flow, partner, geo, time_period)) AS total_rows
    FROM {{ source('eurostat', 'bop_its_6_det') }}

),

staging_count AS (

    SELECT COUNT(*) AS total_rows
    FROM {{ ref('stg_bop_its_6_det') }}

)

SELECT
    source_distinct_keys.total_rows AS source_distinct_rows,
    staging_count.total_rows AS staging_rows

FROM source_distinct_keys
CROSS JOIN staging_count

WHERE source_distinct_keys.total_rows <> staging_count.total_rows