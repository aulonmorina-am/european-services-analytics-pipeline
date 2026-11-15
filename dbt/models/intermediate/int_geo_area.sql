-- Reporting-area dimension (Eurostat GEO codelist restricted to extracted geos).
SELECT
    geo,
    geo_label,
    is_eu_aggregate::boolean AS is_eu_aggregate,
    is_eu_member::boolean AS is_eu_member
FROM {{ ref('geo_areas') }}
