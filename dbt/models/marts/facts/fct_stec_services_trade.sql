-- Fact: services trade by enterprise characteristics (ext_stec01/02/03 unified).
-- Long grain — one row per year x characteristic x nace x flow x partner x geo, value in EUR.
-- NULL value_eur is legitimate (confidential/missing observations): never coalesced to 0.

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
FROM {{ ref('int_ext_stec_union') }}