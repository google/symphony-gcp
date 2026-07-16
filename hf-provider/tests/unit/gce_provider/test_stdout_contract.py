import json
import shutil
import subprocess
import sys

import pytest



@pytest.fixture
def gce_cli_env(tmp_path, make_cli_env, provider_config_dir):
    conf_dir = tmp_path / "conf"
    shutil.copytree(provider_config_dir / "gcpgceinst", conf_dir)
    config_path = conf_dir / "gcpgceinstprov_config.json"
    provider_conf = json.loads(config_path.read_text())
    provider_conf["PUBSUB_AUTOLAUNCH"] = False
    config_path.write_text(json.dumps(provider_conf))

    db_dir = tmp_path / "db"
    db_dir.mkdir()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    env = make_cli_env(conf_dir, log_dir)
    env["HF_DBDIR"] = str(db_dir)
    return env, log_dir


def test_get_available_templates_is_pure_json(gce_cli_env, provider_log_name):
    env, log_dir = gce_cli_env

    result = subprocess.run(
        [sys.executable, "-m", "gce_provider", "getAvailableTemplates"],
        capture_output=True,
        text=True,
        env=env,
        timeout=180
    )

    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    parsed = json.loads(result.stdout)
    assert "templates" in parsed
    assert result.stderr == ""
    assert (log_dir / provider_log_name).exists()


def test_failure_exits_1_with_error_message_on_stdout(gce_cli_env, provider_log_name):
    env, log_dir = gce_cli_env

    result = subprocess.run(
        [sys.executable, "-m", "gce_provider", "requestMachines", "{}"],
        capture_output=True,
        text=True,
        env=env,
        timeout=180
    )

    assert result.returncode == 1, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert result.stdout.startswith("Error:")
    assert result.stderr == ""
    assert "Traceback" in (log_dir / provider_log_name).read_text()