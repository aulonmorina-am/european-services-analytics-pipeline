SELECT 
    dataflow,
    TRY_TO_TIMESTAMP_NTZ(
        last_update, 'DD/MM/YY HH24:MI:SS'
    ) AS last_update,
    freq AS frequency,
    unit,
    sizeclas AS enterprise_size_class,
    stk_flow AS trade_flow,
    nace_r_2,
    partner,
    geo,
    time_period,
    obs_value
FROM {{ source('eurostat', 'ext_stec_01') }}