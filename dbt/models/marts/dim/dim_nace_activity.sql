-- Economic activity dimension (NACE rev. 2) for the stec fact. nace_section is
-- the one-letter section (A, C, J = information & communication, ...).
-- The stec data reports NACE only at section level (1-char codes); the other
-- codes in the seed (A_B, D_E, UNK, TOTAL, I_L_O-U) are aggregates that overlap
-- the sections, so summing across all codes double-counts. is_reporting_level
-- marks the section rows that value metrics filter to.
SELECT
    nace_r_2,
    nace_r_2_label,
    nace_section,
    LENGTH(nace_r_2) = 1 AS is_reporting_level
FROM {{ ref('nace_r2') }}
