SELECT 
timestamp as Time,
TO_JSON_STRING(data) as TitleMessage,
hostname as Label1,
direction,
script as Title,
FROM `symphony-dev-2.log_dataset_default.test` WHERE TIMESTAMP_TRUNC(_PARTITIONTIME, DAY) = TIMESTAMP("2025-07-10") 
ORDER BY timestamp DESC
LIMIT 10
