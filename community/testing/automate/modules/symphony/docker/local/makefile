# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

ifeq ($(WORKDIR),)
    $(error WORKDIR variable is not set.)
endif

ifeq ($(TF_VAR_docker_repository),)
    $(error TF_VAR_docker_repository variable is not set.)
endif

IMAGE_NAME:=sym-compute
BASE_IMAGE:=rocky9
SYM_VERSION:=7.3.2
IMAGE_TAG=$(BASE_IMAGE)-$(SYM_VERSION)

SYM_BIN_NAME:=install.bin
SYM_PATCH_NAME:=patch.tar.gz
SYM_BIN_GCS_PATH:=gs://symphony_dev_2/symphony_binaries/sym-${SYM_VERSION}.0_x86_64.bin
SYM_PATCH_GCS_PATH:=gs://symphony_dev_2/symphony_binaries/sym-7.3.2.0_x86_64_build601711.tar.gz

# Ensure docker is installed
.PHONY: check-docker
check-docker:
	@command -v docker > /dev/null || (echo "$(RED)Docker not found. Please install Buildx$(NC)" && exit 1)
	@echo "$(GREEN)✓ Terraform found: $$(docker --version)$(NC)"

.PHONY: check-buildx
check-buildx: check-docker
	@docker buildx version >/dev/null 2>&1 || (echo "$(RED)Buildx not found. Please install Buildx$(NC)" && exit 1)
	@echo "$(GREEN)✓ Buildx found: $$(docker buildx version)$(NC)"

.PHONY: configure-docker-registry
configure-docker-registry:
	@(set -e; \
	(gcloud auth configure-docker $(TF_VAR_docker_registry_location)-docker.pkg.dev --quiet 2> /dev/null && \
	echo "$(GREEN)✓ Configured Docker registry $(NC)") || \
	(echo "$(RED)Failed to configure docker registry.$(NC)" && exit 1))

.PHONY: download-dependencies-gcs
download-dependencies-gcs: 
	@set -e; \
	if [ ! -f ./$(SYM_VERSION)/$(SYM_BIN_NAME) ]; then \
		echo "Downloading Symphony $(SYM_VERSION) binary"; \
		gcloud storage cp $(SYM_BIN_GCS_PATH) ./$(SYM_VERSION)/$(SYM_BIN_NAME); \
	fi; \
	if [ ! -f ./$(SYM_VERSION)/$(SYM_PATCH_NAME) ]; then \
		echo "Downloading $(SYM_VERSION) patch file..."; \
		if [ "$(SYM_VERSION)" = "7.3.1" ]; then \
			touch ./$(SYM_VERSION)/$(SYM_PATCH_NAME); \
		else \
			gcloud storage cp $(SYM_PATCH_GCS_PATH) ./$(SYM_VERSION)/$(SYM_PATCH_NAME); \
		fi; \
	fi

.PHONY: build
build: check-buildx configure-docker-registry download-dependencies-gcs
	@(set -e; \
	docker buildx build ./$(SYM_VERSION) \
	--file ./Dockerfile \
	--tag $(TF_VAR_docker_repository)/$(IMAGE_NAME):$(IMAGE_TAG) \
	--progress plain \
	--build-arg base_image="$(BASE_IMAGE)" \
	--build-arg sym-version="$(SYM_VERSION)" \
	--push)

.PHONY: secondary
secondary: 
	@export PROJECT_NAME=$$TF_VAR_project_id; \
	export IMAGE_NAME=sym-compute-50; \
	export ZONE=us-central1-a; \
	export DISK_SIZE=50; \
	bash -c 'gcloud builds submit --config <(envsubst < bootimage.yaml) --no-source'