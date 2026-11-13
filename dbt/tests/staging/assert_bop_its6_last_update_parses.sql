SELECT
    _FILE,
    _LINE,
    last_update
FROM {{ source('eurostat', 'bop_its_6_det') }}
WHERE last_update IS NOT NULL
  AND TRY_TO_TIMESTAMP_NTZ(
      last_update,
      'DD/MM/YY HH24:MI:SS'
  ) IS NULL