-- Fivetran appends rows for every new checksum-named file, so Eurostat
-- revisions re-add business keys. Keep only the latest ingested row per key.
WITH deduplicated AS (
    SELECT *
    FROM {{ source('eurostat', 'ext_stec_03') }}
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY freq, unit, enterpr, stk_flow, nace_r_2, partner, geo, time_period
        ORDER BY _fivetran_synced DESC, _file DESC
    ) = 1
)

SELECT
    dataflow,
    TRY_TO_TIMESTAMP_NTZ(
        last_update,
        'DD/MM/YY HH24:MI:SS'
    ) AS last_update,
    freq AS frequency,
    unit,
    enterpr AS enterprise_control,
    stk_flow AS trade_flow,
    nace_r_2,
    partner,
    geo,
    time_period,
    obs_value,
    obs_flag,
    conf_status
FROM deduplicated
