-- Partner dimension: countries vs geopolitical aggregates (extra-EU27, rest of
-- world, ...). Aggregates overlap with the countries they contain — filter on
-- partner_type / flags in BI, never sum both.
SELECT
    partner,
    partner_label,
    partner_type,
    is_eu_member,
    is_extra_eu_aggregate
FROM {{ ref('int_partner') }}
