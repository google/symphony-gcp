# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

ifeq ($(WORKDIR),)
    $(error WORKDIR variable is not set.)
endif

ifeq ($(TF_VAR_state_bucket),)
    $(error TF_VAR_state_bucket variable is not set.)
endif

ifeq ($(TARGET_MATRIX),)
    $(error TARGET_MATRIX variable is not set.)
endif

SYM_SHARED_DIR = $(WORKDIR)/automate/instances/sym-shared
TARGET_MATRIX_PATH := $(SYM_SHARED_DIR)/matrix/$(TARGET_MATRIX).json
TARGET_MATRIX_EXISTS := $(shell test -f $(TARGET_MATRIX_PATH))

ifeq ($(TARGET_MATRIX_EXISTS),yes)
    $(error TARGET_MATRIX file does not exist.)
endif

CI_SHARED_DIR = $(WORKDIR)/automate/continuous-integration/sym-shared-snapshots

# Ensure terraform is installed
.PHONY: check-terraform
check-terraform:
	@command -v terraform > /dev/null || (echo "$(RED)Terraform not found. Please install terraform$(NC)" && exit 1)
	@echo "$(GREEN)✓ Terraform found: $$(terraform version -json | jq -r .terraform_version)$(NC)"

.PHONY: apply-shared
apply-shared: check-terraform
	@(set -e; \
	cd $(SYM_SHARED_DIR); \
	terraform init -backend-config="bucket=$(TF_VAR_state_bucket)"; \
	terraform workspace new $(TARGET_MATRIX) || true; \
	export TF_WORKSPACE=$(TARGET_MATRIX); \
	terraform validate; \
	PLAN_FILE=$$(mktemp); \
	terraform plan -var-file=$(TARGET_MATRIX_PATH) -var=install_only=true -out=$$PLAN_FILE; \
	terraform apply $$PLAN_FILE)

.PHONY: apply-shared-snapshot 
apply-shared-snapshot: check-terraform
	@(set -e; \
	cd $(CI_SHARED_DIR); \
	terraform init -backend-config="bucket=$(TF_VAR_state_bucket)"; \
	terraform workspace new $(TARGET_MATRIX) || true; \
	export TF_WORKSPACE=$(TARGET_MATRIX); \
	terraform validate; \
	PLAN_FILE=$$(mktemp); \
	terraform plan -out=$$PLAN_FILE \
	-replace null_resource.startup_finished \
	-replace google_compute_snapshot.nfs_snapshot \
	-replace google_compute_image.nfs_image \
	-replace google_compute_image.mgmt_image \
	-replace google_compute_image.compute_image; \
	terraform apply $$PLAN_FILE)
	
.PHONY: destroy-shared
destroy-shared: check-terraform
	@(set -e; \
	cd $(SYM_SHARED_DIR); \
	PLAN_FILE=$$(mktemp); \
	terraform plan -destroy -var-file=$(TARGET_MATRIX_PATH) -out=$$PLAN_FILE; \
	terraform apply $$PLAN_FILE) 

.PHONY: shared-snap
shared-snap: check-terraform
	@echo "Running shared snapshot workflow..."
	$(MAKE) apply-shared || (echo "apply-shared failed" && exit 1)
	$(MAKE) apply-shared-snapshot || (echo "apply-shared-snapshot failed" && exit 1)
	$(MAKE) destroy-shared || (echo "destroy-shared failed" && exit 1)
	@echo "Shared snapshot workflow completed successfully"
