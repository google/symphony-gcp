from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from typing import Optional

from gcp_symphony_operator.config import Config


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints."""

    def __init__(self, config: Config, *args):
        self.logger = config.logger
        super().__init__(*args)

    def do_GET(self) -> None:
        """Handle GET requests for health checks."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        elif self.path == "/ready":
            # Check if operator context is ready
            from gcp_symphony_operator.workers.context import get_op_context

            if (context := get_op_context()) and context.is_ready():
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Ready")
            else:
                self.send_response(503)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Not Ready")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args) -> None:
        """Override to use our logger instead of stderr."""
        self.logger.debug(format % args)


class HealthServer:
    """Simple HTTP server for health checks."""

    def __init__(
        self,
        config: Config,
    ):
        self.port = config.health_check_port
        self.config = config
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[Thread] = None
        self.logger = config.logger

    def start(self) -> None:
        """Start the health server in a separate thread."""
        if self.server is not None:
            return

        try:
            self.server = HTTPServer(
                ("", self.port), lambda *args: HealthHandler(self.config, *args)
            )
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.logger.info(f"✅ Health server started on port {self.port}")
        except Exception as e:
            self.logger.error(f"❌ Failed to start health server: {e}")

    def stop(self) -> None:
        """Stop the health server."""
        self.logger.info("🛑 Stopping health server...")
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
        self.logger.info("✅ Health server stopped")
