import time
from pathlib import Path


class FileHealthChecker:
    """File-based health checker for Kubernetes probes."""

    def __init__(self, health_file: str = "/tmp/operator-health"):
        self.health_file = Path(health_file)
        self.ready_file = Path(f"{health_file}-ready")

    def mark_healthy(self) -> None:
        """Mark the operator as healthy by creating/updating the health file."""
        try:
            self.health_file.touch()
            with open(self.health_file, "w") as f:
                f.write(str(int(time.time())))
        except Exception:
            pass  # Ignore errors to avoid affecting operator functionality

    def mark_ready(self, ready: bool = True) -> None:
        """Mark the operator as ready or not ready."""
        try:
            if ready:
                self.ready_file.touch()
                with open(self.ready_file, "w") as f:
                    f.write(str(int(time.time())))
            else:
                if self.ready_file.exists():
                    self.ready_file.unlink()
        except Exception:
            pass  # Ignore errors

    def is_healthy(self, max_age_seconds: int = 60) -> bool:
        """Check if the operator is healthy based on file timestamp."""
        try:
            if not self.health_file.exists():
                return False

            file_age = time.time() - self.health_file.stat().st_mtime
            return file_age <= max_age_seconds
        except Exception:
            return False

    def is_ready(self) -> bool:
        """Check if the operator is ready."""
        return self.ready_file.exists()

    def cleanup(self) -> None:
        """Clean up health files."""
        try:
            if self.health_file.exists():
                self.health_file.unlink()
            if self.ready_file.exists():
                self.ready_file.unlink()
        except Exception:
            pass
