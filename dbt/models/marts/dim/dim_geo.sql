-- Reporting-area dimension. EU27_2020 (is_eu_aggregate) overlaps with the member
-- country rows — filter to one level in BI, never sum both.
SELECT
    geo,
    geo_label,
    is_eu_aggregate,
    is_eu_member
FROM {{ ref('int_geo_area') }}
