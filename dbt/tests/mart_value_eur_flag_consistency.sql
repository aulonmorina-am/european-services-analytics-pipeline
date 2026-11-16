-- value_eur must be NULL exactly when the observation is flagged missing.
-- Guards against both fabricated zeros (coalesce) and lost flags.
SELECT 'fct_bop_services_trade' AS model_name, observation_key
FROM {{ ref('fct_bop_services_trade') }}
WHERE (value_eur IS NULL) <> is_value_missing

UNION ALL

SELECT 'fct_stec_services_trade', observation_key
FROM {{ ref('fct_stec_services_trade') }}
WHERE (value_eur IS NULL) <> is_value_missing
