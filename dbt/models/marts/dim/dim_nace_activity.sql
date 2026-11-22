-- Economic activity dimension (NACE rev. 2) for the stec fact.
-- The stec data reports a mix of single sections (C, F, G, H, J, K, M, N) and
-- grouped ones (A_B = agriculture + mining, D_E = electricity + water,
-- I_L_O-U = everything else). Only the single sections are additive; the grouped
-- codes overlap them, so summing across all codes double-counts. is_reporting_level
-- marks the additive rows that value metrics filter to.
--
-- There is deliberately no single-letter "section" column: A_B is not section A,
-- it is A and B. Deriving one letter from a grouped code would mislabel the row.
SELECT
    nace_r_2,
    nace_r_2_label,
    LENGTH(nace_r_2) = 1 AS is_reporting_level
FROM {{ ref('nace_r2') }}
