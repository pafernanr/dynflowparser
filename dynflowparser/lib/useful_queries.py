# Get Action input filtering by step.error and action.execution_plan_uuid
SELECT a.class, a.data, a.input
FROM steps s LEFT JOIN actions a
  ON s.action_id = a.id
WHERE
  a.execution_plan_uuid='978db0ef-cfc4-4ca4-8bb0-bdf5cad36030'
  AND s.error LIKE '%Could not lookup a publication_href for repo%'
wn