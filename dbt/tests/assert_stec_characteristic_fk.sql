-- The stec characteristic FK is composite (characteristic_type + characteristic_code):
-- TOTAL and UNK exist under both size_class and enterprise_control, so a single-column
-- relationships test on characteristic_code cannot detect a mismatched pair.


SELECT
    u.observation_key,
    u.characteristic_type,
    u.characteristic_code
FROM {{ ref('int_ext_stec_union') }} AS u
LEFT JOIN {{ ref('stec_characteristics') }} AS c
    ON u.characteristic_type = c.characteristic_type
    AND u.characteristic_code = c.characteristic_code

WHERE c.characteristic_type IS NULL