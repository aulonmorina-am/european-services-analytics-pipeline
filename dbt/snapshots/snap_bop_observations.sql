{% snapshot snap_bop_observations %}

{{
    config(
        target_schema='snapshots',
        unique_key='observation_key',
        strategy='check',
        check_cols=['obs_value']
    )
}}

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'frequency',
        'currency',
        'bop_item',
        'bop_flow',
        'partner',
        'geo',
        'time_period'
    ]) }} AS observation_key,

    *

FROM {{ ref('stg_bop_its_6_det') }}

{% endsnapshot %}