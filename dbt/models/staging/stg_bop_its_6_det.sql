-- Fivetran appends rows for every new checksum-named file, so Eurostat
-- revisions re-add business keys. Keep only the latest ingested row per key.
WITH deduplicated AS (
    SELECT *
    FROM {{ source('eurostat', 'bop_its_6_det') }}
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY freq, currency, bop_item, stk_flow, partner, geo, time_period
        ORDER BY _fivetran_synced DESC, _file DESC
    ) = 1
)

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
    obs_value,
    obs_flag,
    conf_status
FROM deduplicated