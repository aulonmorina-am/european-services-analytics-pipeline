-- Flow dimension shared by both facts. bop: BAL/CRE/DEB; stec: EXP/IMP.
-- Codes are disjoint across groups, so flow_code alone is a valid key.
SELECT
    flow_group,
    flow_code,
    flow_label,
    flow_direction
FROM {{ ref('flows') }}
