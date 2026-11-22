-- Unified enterprise-characteristics fact (ext_stec01/02/03 share the same grain:
-- freq/unit/nace_r2/trade_flow/partner/geo/period, differing only in the
-- characteristic dimension). characteristic_type tells which dataset a row came
-- from; values are converted to EUR.
WITH stec_01 AS (

    SELECT
        'size_class' AS characteristic_type,
        enterprise_size_class AS characteristic_code,
        frequency,
        unit,
        nace_r_2,
        trade_flow,
        partner,
        geo,
        time_period,
        obs_value,
        obs_flag,
        conf_status,
        last_update
    FROM {{ ref('stg_ext_stec_01') }}

),

stec_02 AS (

    SELECT
        'ebops_2010' AS characteristic_type,
        ebops_2010 AS characteristic_code,
        frequency,
        unit,
        nace_r_2,
        trade_flow,
        partner,
        geo,
        time_period,
        obs_value,
        obs_flag,
        conf_status,
        last_update
    FROM {{ ref('stg_ext_stec_02') }}

),

stec_03 AS (

    SELECT
        'enterprise_control' AS characteristic_type,
        enterprise_control AS characteristic_code,
        frequency,
        unit,
        nace_r_2,
        trade_flow,
        partner,
        geo,
        time_period,
        obs_value,
        obs_flag,
        conf_status,
        last_update
    FROM {{ ref('stg_ext_stec_03') }}

),

unioned AS (

    SELECT * FROM stec_01
    UNION ALL
    SELECT * FROM stec_02
    UNION ALL
    SELECT * FROM stec_03

)

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'unioned.characteristic_type', 'unioned.characteristic_code', 'unioned.frequency',
        'unioned.unit', 'unioned.nace_r_2', 'unioned.trade_flow', 'unioned.partner',
        'unioned.geo', 'unioned.time_period'
    ]) }} AS observation_key,
    unioned.characteristic_type,
    unioned.characteristic_code,
    c.characteristic_label,
    c.is_reporting_level AS characteristic_is_reporting_level,
    unioned.frequency,
    f.frequency_label,
    unioned.unit,
    unioned.nace_r_2,
    n.nace_r_2_label,
    unioned.trade_flow,
    fl.flow_label AS trade_flow_label,
    fl.flow_direction,
    unioned.partner,
    p.partner_label,
    p.partner_type,
    p.is_eu_member AS partner_is_eu_member,
    unioned.geo,
    g.geo_label,
    g.is_eu_aggregate AS geo_is_eu_aggregate,
    g.is_eu_member AS geo_is_eu_member,
    CAST(time_period AS INTEGER) AS year,
    obs_value,
    obs_value * u.multiplier_to_eur AS value_eur,
    obs_value IS NULL AS is_value_missing,
    obs_flag,
    conf_status,
    last_update
FROM unioned
LEFT JOIN {{ ref('stec_characteristics') }} c
    ON c.characteristic_type = unioned.characteristic_type
   AND c.characteristic_code = unioned.characteristic_code
LEFT JOIN {{ ref('frequencies') }} f
    ON f.frequency = unioned.frequency
LEFT JOIN {{ ref('nace_r2') }} n
    ON n.nace_r_2 = unioned.nace_r_2
LEFT JOIN {{ ref('flows') }} fl
    ON fl.flow_group = 'stec' AND fl.flow_code = unioned.trade_flow
LEFT JOIN {{ ref('int_partner') }} p
    ON p.partner = unioned.partner
LEFT JOIN {{ ref('int_geo_area') }} g
    ON g.geo = unioned.geo
LEFT JOIN {{ ref('units') }} u
    ON u.unit = unioned.unit
