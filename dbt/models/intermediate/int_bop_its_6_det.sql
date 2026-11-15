-- Typed fact for international trade in services (BPM6, bop_its6_det).
-- One row per frequency/currency/bop_item/flow/partner/geo/period.
-- Values are converted to EUR; flags make extra-EU vs intra-EU and ICT visible.
WITH base AS (

    SELECT
        frequency,
        currency,
        bop_item,
        bop_flow,
        partner,
        geo,
        time_period,
        obs_value,
        obs_flag,
        conf_status,
        last_update
    FROM {{ ref('stg_bop_its_6_det') }}

),

typed AS (

    SELECT
        {{ dbt_utils.generate_surrogate_key([
            'base.frequency', 'base.currency', 'base.bop_item', 'base.bop_flow',
            'base.partner', 'base.geo', 'base.time_period'
        ]) }} AS observation_key,
        base.frequency,
        f.frequency_label,
        base.currency,
        base.bop_item,
        bi.bop_item_label,
        bi.is_ict_service,
        base.bop_flow,
        fl.flow_label AS bop_flow_label,
        fl.flow_direction,
        base.partner,
        p.partner_label,
        p.partner_type,
        p.is_eu_member AS partner_is_eu_member,
        p.is_extra_eu_aggregate AS partner_is_extra_eu_aggregate,
        base.geo,
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
    FROM base
    LEFT JOIN {{ ref('frequencies') }} f
        ON f.frequency = base.frequency
    LEFT JOIN {{ ref('int_bop_item') }} bi
        ON bi.bop_item = base.bop_item
    LEFT JOIN {{ ref('flows') }} fl
        ON fl.flow_group = 'bop' AND fl.flow_code = base.bop_flow
    LEFT JOIN {{ ref('int_partner') }} p
        ON p.partner = base.partner
    LEFT JOIN {{ ref('int_geo_area') }} g
        ON g.geo = base.geo
    LEFT JOIN {{ ref('units') }} u
        ON u.unit = base.currency

)

SELECT * FROM typed
