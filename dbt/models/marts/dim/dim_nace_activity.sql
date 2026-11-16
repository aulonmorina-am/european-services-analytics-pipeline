-- Economic activity dimension (NACE rev. 2) for the stec fact. nace_section is
-- the one-letter section (A, C, J = information & communication, ...).
SELECT
    nace_r_2,
    nace_r_2_label,
    nace_section
FROM {{ ref('nace_r2') }}
