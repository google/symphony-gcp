import json
import logging
import logging.handlers
import os
import socket
import subprocess
import sys
import tempfile
import warnings

import pytest

from common import log_bootstrap

def _remove_managed_handlers():
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if isinstance(
            handler,
            (log_bootstrap._ProviderLogHandler, log_bootstrap._ProviderNullHandler),
        ):
            root_logger.removeHandler(handler)
            handler.close()
    logging.captureWarnings(False)
    

@pytest.fixture(autouse=True)
def isolate_root_logger():
    """Isolate the root logger for each test"""
    _remove_managed_handlers()
    yield
    _remove_managed_handlers()


def test_default_log_file_honors_hostfactory_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_PROVIDER_LOGDIR", str(tmp_path))
    monkeypatch.setenv("HF_PROVIDER_NAME", "myprovider")
    monkeypatch.setenv("EGOSC_INSTANCE_HOST", "testhost")

    assert log_bootstrap.default_log_file() == str(
        tmp_path / "myprovider-provider.testhost.log"
    )


def test_default_log_file_falls_back_to_hostname(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_PROVIDER_LOGDIR", str(tmp_path))
    monkeypatch.delenv("HF_PROVIDER_NAME", raising=False)
    monkeypatch.delenv("EGOSC_INSTANCE_HOST", raising=False)

    expected = f"gcp-symphony-provider.{socket.gethostname()}.log"
    assert os.path.basename(log_bootstrap.default_log_file()) == expected


def test_default_log_file_matches_wrapper_script_fallback(monkeypatch):
    monkeypatch.delenv("HF_PROVIDER_LOGDIR", raising=False)

    assert os.path.dirname(log_bootstrap.default_log_file()) == tempfile.gettempdir()


def test_bootstrap_routes_warnings_to_log_not_stderr(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HF_PROVIDER_LOGDIR", str(tmp_path))
    monkeypatch.setenv("EGOSC_INSTANCE_HOST", "testhost")
    monkeypatch.delenv("HF_PROVIDER_NAME", raising=False)

    log_bootstrap.bootstrap_logging()
    with warnings.catch_warnings():
        warnings.simplefilter("always")
        warnings.warn("synthetic-runtime-warning", FutureWarning)
    log_bootstrap._installed_handler().flush()

    log_file_path = tmp_path / "gcp-symphony-provider.testhost.log"
    assert "synthetic-runtime-warning" in log_file_path.read_text()
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""

def test_bootstrap_is_idempotent(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_PROVIDER_LOGDIR", str(tmp_path))
    root_logger = logging.getLogger()
    handlers_before = len(root_logger.handlers)

    log_bootstrap.bootstrap_logging()
    log_bootstrap.bootstrap_logging()

    assert len(root_logger.handlers) == handlers_before + 1


def test_bootstrap_falls_back_to_tempdir(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_PROVIDER_LOGDIR", str(tmp_path / "nonexistent_dir"))
    fallback_dir = tmp_path / "tempdir"
    fallback_dir.mkdir()
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(fallback_dir))

    log_bootstrap.bootstrap_logging()

    handler = log_bootstrap._installed_handler()
    assert isinstance(handler, logging.handlers.RotatingFileHandler)
    assert os.path.dirname(handler.baseFilename) == str(fallback_dir)


def test_bootstrap_never_attaches_stream_handler(monkeypatch, tmp_path):
    missing = tmp_path / "missing"
    monkeypatch.setenv("HF_PROVIDER_LOGDIR", str(missing / "logs"))
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(missing / "tmp"))
    
    root_logger = logging.getLogger()
    handlers_before  = list(root_logger.handlers)
    log_bootstrap.bootstrap_logging()

    added_handlers = [handler for handler in root_logger.handlers if handler not in handlers_before]
    assert len(added_handlers) == 1
    assert isinstance(added_handlers[0], logging.NullHandler)

def test_bootstrap_reinstalls_after_external_handler_removal(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_PROVIDER_LOGDIR", str(tmp_path))
    log_bootstrap.bootstrap_logging()

    root_logger = logging.getLogger()
    root_logger.removeHandler(log_bootstrap._installed_handler())
    assert log_bootstrap._installed_handler() is None

    log_bootstrap.bootstrap_logging()
    assert log_bootstrap._installed_handler() is not None


def test_configure_logging_applies_provider_config(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_PROVIDER_LOGDIR", str(tmp_path))
    log_bootstrap.bootstrap_logging()

    custom_logfile = tmp_path / "custom.log"
    log_bootstrap.configure_logging(
        logfile=str(custom_logfile), level="INFO", max_bytes=1024, backup_count=2
    )

    assert logging.getLogger().level == logging.INFO
    handler = log_bootstrap._installed_handler()
    assert os.path.abspath(handler.baseFilename) == os.path.abspath(str(custom_logfile))

    logging.getLogger("contract.test").info("test-info-message")
    handler.flush()
    assert "test-info-message" in custom_logfile.read_text()


def test_configure_logging_reuses_handler_when_unchanged(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_PROVIDER_LOGDIR", str(tmp_path))
    log_bootstrap.bootstrap_logging()
    handler = log_bootstrap._installed_handler()

    log_bootstrap.configure_logging(
        logfile=log_bootstrap.default_log_file(),
        level="WARNING",
        max_bytes=log_bootstrap.DEFAULT_LOG_MAX_BYTES,
        backup_count=log_bootstrap.DEFAULT_LOG_BACKUP_COUNT
    )

    assert log_bootstrap._installed_handler() is handler


def test_configure_logging_keeps_old_target_when_new_unwritable(monkeypatch, tmp_path):
    monkeypatch.setenv("HF_PROVIDER_LOGDIR", str(tmp_path))
    log_bootstrap.bootstrap_logging()
    old_handler = log_bootstrap._installed_handler()

    log_bootstrap.configure_logging(logfile=str(tmp_path / "missing" / "x.log"))

    assert log_bootstrap._installed_handler() is old_handler


def test_import_time_warning_is_captured_end_to_end(tmp_path, src_dir):
    script = "\n".join(
        [
            "from common.log_bootstrap import bootstrap_logging",
            "bootstrap_logging()",
            "import warnings",
            "warnings.warn('synthetic-import-time-warning', FutureWarning)",
            'print(\'{"ok": true}\')'
        ]
    )
    env = os.environ.copy()

    env.pop("HF_PROVIDER_NAME", None)
    env.pop("GCP_HF_LOG_LEVEL", None)
    env["HF_PROVIDER_LOGDIR"] = str(tmp_path)
    env["EGOSC_INSTANCE_HOST"] = "e2ehost"
    env["PYTHONPATH"] = str(src_dir) + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONWARNINGS"] = "always"

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env=env,
        timeout=60
    )

    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert json.loads(result.stdout) == {"ok": True}
    assert result.stderr == ""
    log_content = (tmp_path / "gcp-symphony-provider.e2ehost.log").read_text()
    assert "synthetic-import-time-warning" in log_content