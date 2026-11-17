-- Fact: services trade by enterprise characteristics (ext_stec01/02/03 unified).
-- Long grain — one row per year x characteristic x nace x flow x partner x geo, value in EUR.
-- NULL value_eur is legitimate (confidential/missing observations): never coalesce to 0.
WITH base AS (

    SELECT * FROM {{ ref('int_ext_stec_union') }}

),

-- Safeguard against unit duplication after EUR conversion. Verified 0 multi-unit
-- keys today; keep as no-op guard.
deduplicated AS (

    SELECT *
    FROM base
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY year, characteristic_type, characteristic_code, nace_r_2, trade_flow, partner, geo
        ORDER BY CASE WHEN unit = 'MIO_EUR' THEN 0 ELSE 1 END, unit
    ) = 1

)

SELECT
    observation_key,
    year,
    DATEFROMPARTS(year, 1, 1) AS year_start,
    characteristic_type || '-' || characteristic_code AS characteristic_key,
    characteristic_type,
    characteristic_code,
    nace_r_2,
    trade_flow AS flow_code,
    partner,
    geo,
    value_eur,
    is_value_missing,
    obs_flag,
    conf_status,
    last_update
FROM deduplicated
