-- Enterprise characteristic dimension for the stec fact: enterprise size class
-- (ext_stec01), EBOPS 2010 product (ext_stec02), enterprise control (ext_stec03).
SELECT
    characteristic_type,
    characteristic_code,
    characteristic_label
FROM {{ ref('stec_characteristics') }}
