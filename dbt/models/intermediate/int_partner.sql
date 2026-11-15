-- Partner dimension: reporting/partner areas from the Eurostat PARTNER codelist.
-- Distinguishes single countries from geopolitical aggregates (extra-EU, world, ...).
SELECT
    partner,
    partner_label,
    partner_type,
    is_eu_member::boolean AS is_eu_member,
    is_extra_eu_aggregate::boolean AS is_extra_eu_aggregate
FROM {{ ref('partners') }}
