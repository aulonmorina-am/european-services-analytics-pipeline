SELECT
    dataflow,
    TRY_TO_TIMESTAMP_NTZ(
        last_update, 'DD/MM/YY HH24:MI:SS'
    ) AS last_update,
    freq AS frequency,
    currency,
    bop_item,
    stk_flow AS bop_flow,
    partner,
    geo,
    time_period,
    obs_value
FROM {{ source('eurostat', 'bop_its_6_det') }}