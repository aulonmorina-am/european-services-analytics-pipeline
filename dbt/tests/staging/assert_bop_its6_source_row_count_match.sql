WITH source_count AS (

    SELECT COUNT(*) AS total_rows
    FROM {{ source('eurostat', 'bop_its_6_det') }}

),

staging_count AS (

    SELECT COUNT(*) AS total_rows
    FROM {{ ref('stg_bop_its_6_det') }}

)

SELECT
    source_count.total_rows AS source_rows,
    staging_count.total_rows AS staging_rows

FROM source_count
CROSS JOIN staging_count

WHERE source_count.total_rows <> staging_count.total_rows