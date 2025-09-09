# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Directories
TF_DIR ?= .

# Ensure terraform is installed
.PHONY: check-terraform
check-terraform:
	@command -v terraform > /dev/null || (echo "$(RED)Terraform not found. Please install terraform$(NC)" && exit 1)
	@echo "$(GREEN)✓ Terraform found: $$(terraform version -json | jq -r .terraform_version)$(NC)"

.PHONY: redeploy
redeploy: check-terraform
	cd $(TF_DIR) && terraform apply \
		-replace=kubernetes_job.bootstrap-hostfactory-operator \
		-replace=null_resource.update-configuration-files \
		-var-file=$(VAR_FILE)

.PHONY: reconfig
reconfig: check-terraform
	cd $(TF_DIR) && terraform apply \
		-replace=null_resource.update-configuration-files \
		-var-file=$(VAR_FILE)

.PHONY: undeploy
undeploy: check-terraform
	cd $(TF_DIR) && terraform apply \
		-replace=kubernetes_job.cleanup-hostfactory-operator \
		-var=job_cleanup_enabled=true \
		-var-file=$(VAR_FILE)
