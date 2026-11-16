-- Calendar dimension for the annual data. Derived from the facts so it
-- adapts automatically when the extraction range extends beyond 2022-2024.
WITH years AS (

    SELECT DISTINCT year FROM {{ ref('int_bop_its_6_det') }}
    UNION
    SELECT DISTINCT year FROM {{ ref('int_ext_stec_union') }}

)

SELECT
    year,
    year = (SELECT MAX(year) FROM years) AS is_latest_year
FROM years
