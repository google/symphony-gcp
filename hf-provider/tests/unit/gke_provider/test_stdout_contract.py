import json
import subprocess
import sys

def test_get_available_templates_stdout_is_pure_json(
    tmp_path, make_cli_env, provider_config_dir, provider_log_name
):
    env = make_cli_env(provider_config_dir / "gcpgkeinst", tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "gke_provider", "getAvailableTemplates"],
        capture_output=True,
        text=True,
        env=env,
        timeout=180
    )

    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    parsed = json.loads(result.stdout)
    assert "templates" in parsed
    assert result.stderr == ""
    assert (tmp_path / provider_log_name).exists()


def test_failure_exits_1_with_error_message_on_stdout(
        tmp_path, make_cli_env, provider_config_dir, provider_log_name
):
    env = make_cli_env(provider_config_dir / "gcpgkeinst", tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "gke_provider", "requestMachines", "{}"],
        capture_output=True,
        text=True,
        env=env,
        timeout=180
    )

    assert result.returncode == 1, f"stdout: {result.stdout}\nstderr: {result.stderr}"
    assert result.stdout.startswith("Error:")
    assert result.stderr == ""
    assert "Traceback" in (tmp_path / provider_log_name).read_text()