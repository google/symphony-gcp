SELECT 
time,
source,
run,
event,
sym_request,
node_template,
cluster,
node,
pod,
acn
FROM `symphony-dev-2.log_dataset_default.logs` LIMIT 1000