SELECT 
  time_window,
  SUM(pod_create_count) OVER (ORDER BY time_window) as pod_create,
  SUM(pod_delete_count) OVER (ORDER BY time_window) as pod_delete
FROM (
  SELECT 
    TIMESTAMP_TRUNC(time, MINUTE) as time_window,
    COUNTIF(event = "pod:create") as pod_create_count,
    COUNTIF(event = "pod:delete") as pod_delete_count
  FROM `symphony-dev-2.log_dataset_default.logs`
  WHERE cluster = "cluster-who"
  GROUP BY TIMESTAMP_TRUNC(time, MINUTE)
)
ORDER BY time_window DESC
LIMIT 1000