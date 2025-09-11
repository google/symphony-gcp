# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

DOCKER_IMAGE:=bqingestor
DOCKER_TAG:=test

ifeq ($(WORKDIR),)
    $(error WORKDIR variable is not set.)
endif

ifeq ($(TF_VAR_python_repository),)
    $(error TF_VAR_python_repository variable is not set.)
endif

ifeq ($(TF_VAR_docker_repository),)
    $(error TF_VAR_docker_repository variable is not set.)
endif

ifeq ($(TF_VAR_docker_registry_location),)
    $(error TF_VAR_docker_registry_location variable is not set.)
endif

# Ensure docker is installed
.PHONY: check-docker
check-docker:
	@command -v docker > /dev/null || (echo "$(RED)Docker not found. Please install Buildx$(NC)" && exit 1)
	@echo "$(GREEN)✓ Terraform found: $$(docker --version)$(NC)"

.PHONY: check-buildx
check-buildx: check-docker
	@docker buildx version >/dev/null 2>&1 || (echo "$(RED)Buildx not found. Please install Buildx$(NC)" && exit 1)
	@echo "$(GREEN)✓ Buildx found: $$(docker buildx version)$(NC)"

.PHONY: check-uv
check-uv:
	@command -v uv > /dev/null || (echo "$(RED)uv not found. Please install uv$(NC)" && exit 1)
	@echo "$(GREEN)✓ uv found: $$(uv --version)$(NC)"

.PHONY: configure-docker-registry
configure-docker-registry:
	@(set -e; \
	(gcloud auth configure-docker $(TF_VAR_docker_registry_location)-docker.pkg.dev --quiet 2> /dev/null && \
	echo "$(GREEN)✓ Configured Docker registry $(NC)") || \
	(echo "$(RED)Failed to configure docker registry.$(NC)" && exit 1))

.PHONY: push
push: check-buildx configure-docker-registry
	@(set -e; \
	docker buildx build . \
	--tag $(TF_VAR_docker_repository)/$(DOCKER_IMAGE):$(DOCKER_TAG) \
	--push)