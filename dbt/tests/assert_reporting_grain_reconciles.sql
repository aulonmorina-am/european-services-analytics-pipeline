-- The reporting grain must be additive: summing one reporter's country-level
-- partner rows must not exceed its own reported "to the world" total. A ratio
-- above 1 means the metric layer is counting overlapping partner or geo
-- aggregates (the defect that inflated BOP exports ~5x and STEC ~4.9x).
--
-- Both sides are compared on the SAME series: the BPM6 total row 'S' for BOP and
-- the NACE 'TOTAL' row for STEC. Comparing the section rows against the total
-- row would mix populations and fail for reasons unrelated to the grain.
--
-- A shortfall is expected (unallocated / confidential value); an overcount is a
-- regression.

WITH bop AS (

    SELECT
        'bop' AS source,
        f.year,
        f.geo,
        SUM(CASE WHEN p.partner_type = 'country' THEN f.value_eur END) AS country_partners_eur,
        SUM(CASE WHEN f.partner = 'WRL_REST' THEN f.value_eur END) AS world_eur
    FROM {{ ref('fct_bop_services_trade') }} AS f
    INNER JOIN {{ ref('dim_partner') }} AS p
        ON p.partner = f.partner
    WHERE f.flow_code = 'CRE'
      AND f.bop_item = 'S'
      AND f.geo <> 'EU27_2020'
    GROUP BY f.year, f.geo

),

stec AS (

    SELECT
        'stec' AS source,
        f.year,
        f.geo,
        SUM(CASE WHEN p.partner_type = 'country' THEN f.value_eur END) AS country_partners_eur,
        SUM(CASE WHEN f.partner = 'WRL_REST' THEN f.value_eur END) AS world_eur
    FROM {{ ref('fct_stec_services_trade') }} AS f
    INNER JOIN {{ ref('dim_partner') }} AS p
        ON p.partner = f.partner
    WHERE f.flow_code = 'EXP'
      AND f.characteristic_type = 'ebops_2010'
      AND f.characteristic_code = 'S'
      AND f.nace_r_2 = 'TOTAL'
      AND f.geo <> 'EU27_2020'
    GROUP BY f.year, f.geo

),

combined AS (

    SELECT * FROM bop
    UNION ALL
    SELECT * FROM stec

)

SELECT
    source,
    year,
    geo,
    country_partners_eur,
    world_eur,
    ROUND(country_partners_eur / NULLIF(world_eur, 0), 3) AS ratio
FROM combined
WHERE world_eur IS NOT NULL
  AND country_partners_eur IS NOT NULL
  AND country_partners_eur > world_eur * 1.05
