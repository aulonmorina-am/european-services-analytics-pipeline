-- Fact: BPM6 international trade in services. Long grain — one row per
-- year x service x flow x partner x reporting area, value in EUR.
-- NULL value_eur is legitimate (confidential/missing observations, ~18% of rows):
-- it must stay NULL, never coalesced to 0.

SELECT
    observation_key,
    year,
    DATEFROMPARTS(year, 1, 1) AS year_start,
    bop_item,
    bop_flow AS flow_code,
    partner,
    geo,
    value_eur,
    is_value_missing,
    obs_flag,
    conf_status,
    last_update
FROM {{ ref('int_bop_its_6_det') }}