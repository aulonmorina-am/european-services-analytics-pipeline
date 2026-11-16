-- Fact: BPM6 international trade in services. Long grain — one row per
-- year x service x flow x partner x reporting area, value in EUR.
-- NULL value_eur is legitimate (confidential/missing observations, ~18% of rows):
-- it must stay NULL, never coalesced to 0.
WITH base AS (

    SELECT * FROM {{ ref('int_bop_its_6_det') }}

),

-- Safeguard against unit duplication after EUR conversion (MIO_EUR vs THS_EUR
-- would double-count in sums). Verified 0 multi-currency keys today; keep as no-op guard.
deduplicated AS (

    SELECT *
    FROM base
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY year, bop_item, bop_flow, partner, geo
        ORDER BY CASE WHEN currency = 'MIO_EUR' THEN 0 ELSE 1 END, currency
    ) = 1

)

SELECT
    observation_key,
    year,
    bop_item,
    bop_flow AS flow_code,
    partner,
    geo,
    value_eur,
    is_value_missing,
    obs_flag,
    conf_status,
    last_update
FROM deduplicated
