resource "google_artifact_registry_repository" "docker-registry" {
    repository_id = var.docker_registry
    description = "Docker repository for Symphony GCP UAT"
    location = var.docker_registry_location
    format = "DOCKER"
}

resource "google_artifact_registry_repository" "python-registry" {
    repository_id = var.python_registry
    description = "Docker repository for Symphony GCP UAT"
    location = var.python_registry_location
    format = "PYTHON"
}