# Changelog

All hf-provider notable changes to this project will be documented in this file.

## [0.3.7] - 2026-07-16

Relevant PRs:
- #92 - Redirect provider-script stderr to prevent HostFactory JSON parsing failures
- #97 - Fixed GCE service-account credentials path handling
- #98 - Route python warnings/future-warnings through provider logging
- #99 - Integrate provider fixes, standardize locked `uv` workflows

#### Added
- Added `src/common/log_bootstrap.py` to initialize shared logging for `hf-gce`, `hf-gke`, and `hf-monitor`.
- Added automatic capture of Python warnings and routing them to the provider log instead of `stderr`.
- Added fallback logging to the system temporary directory when the configured provider log directory is unavailable.
- Added some new test cases related to logging.

#### Fixed
- Fixed malformed HostFactory responses caused by warnings or diagnostic messages being mixed with JSON output.
- Redirected `stderr` from all GCE and GKE wrapper scripts to the provider log, keeping `stdout` reserved for command responses only.
- Fixed duplicate log records and concurrent rotation causes by multiple handlers writing to the same log file.
- Prevented logging from creating a file named `None` when `HF_PROVIDER_LOGDIR` is unset.
- Prevented logging fallbacks from writing to `stderr` when no log directory is writable.
- Fixed failed commands returning exit code `0`; provider failures now return exit code `1`, output the error message through `stdout`, and record the trackback in the provider log.
- Fixed `hf-gke` treating an empty command result as successful response.
- Fixed GCE service-account authentication failing with `'str' object has no attribute 'stat'` when `GCP_CREDENTIALS_FILE` is configured.
- Fixed relative GCE credential paths by resolving them against the provider configuration directory.
- Allowed missing or invalid service-account files to fall back to the `Application Default Credentials` instead of terminating the provider.

#### Changed
- Initialized provider logging before importing third-party libraries import-time warnings are captured.
- Centralized GCE an GKE logging configuration through the shared logging bootstrap.
- Updated provider configuration loading to reapply the configured log path, level, maximum file size and rotation count.
- Standardized the `stdout` contract so successful responses contain clean JSON and failed responses follow the HostFactory error-response behavior.

### Build and Release Infrastructure

#### Added
- Added the required `uv` version to `pyproject.toml`.

#### Changed
- Pinned the GitHub Actions runner to `ubuntu-24.04`.
- Pinned `uv` to version `0.11.26`.
- Changed dependency installation to `uv sync --locked`.
- Change unit-test and Pyinstaller execution to use `uv run --locked`.
- Regenerated uv.lock to synchronize the resolved dependency versions used by source and RPM builds.  

## [0.3.6] - 2026-01-22

Relevant PRs:
- #52 - RPM build `PATH` fix
- #54 - Tag-based RPM versions
- #55 - Shell quoting fix
- #56 - Provider unit-test fixes
- #61 - RPM build improvements, hf-monitor packaging, and unit-test integration
- #62 - GCE and GKE provider installation-validation scripts

#### Added
- Added the validation scripts to the GCE and GKE RPM package specifications as executable files.

#### Fixed
- Fixed failing unit tests for both GCE and GKE providers.
- Cleared cached GKE configuration state between tests to prevent `lru_cache` data from leakiing across test cases.
- Removed a non-atomic `call_count` assertion from the GCE instance-fetching test.
- Prevented intermittent GitHub Actions failures where the returned instance count was correct but the mock call count had not been updated consistently.

#### Changed
- Updated GCE mocks to configure methods on the factory-created client instance.
- Updated assertions to match the actual client-contrustion and invocation flow.

### Build and Release Infrastructure

#### Added
- Added `usr/bin` to `GITHUB_PATH` before building the provider command-line applications.
- Added automatic RPM version detection from Git tags.
- Added the missing `hf-monitor` executable to the RPM build workflow

#### Fixed
- Fixed RPM workflows failures caused by required executables not being found in the build environment.
- Fixed malformed shell quoting in the tag-version extraction command introduced by PR #54. Corrected the expression that removes the leading `v` from `github.ref_name`.
- Prevented shell parsing failures while setting the `VERSION` environment variable.

#### Changed
- Tags matching the following pattern are converted into RPM versions `v0.3.6` -> `0.3.6`
- Updated the GCE RPM package description to state the `hf-monitor` is used to track and monitor GCE VM events.
- Non-semantic-version tags fall back to RPM version `1.0.0`.
- Updated generated artifact names to use the calculated version instead of a hardcoded `1.0.0`.
- Refactored dependency, virtual-environment, and Pyinstaller setup into a clearer build-pipeline stage.
- Replace the older direct Pyinstaller commmands with the maintained specification-file-based commands: `uv run pyinstaller hf-gce.spec --clean...`

## [0.3.5] - 2025-12-17

Relevant PRs:
- #46 - RHEL 10 RPM build support.
- #44 - Centralized provider installation
- #42 - Expired-machine database cleanup

#### Added
- Added a machine db `trim` operation that permanently deletes expired returned-machine records.
- Added the `trimDB` CLI command.
- The cleanup command can be executed manually, through an external scheduler or automatically, depending on configuration.
- Added `AUTO_RUN_TRIM_DB_CMD` to control automatic cleanup behavior and `RETURNED_VM_TTL` to define how many days returned VM records are retained.
- Added database-name configuration support.

#### Fixed
- Reduced the risk of initialization being executed multiple times concurrently. 
- Prevented repeated database-cleanup execution.
- Corrected and narrowed expired-machine deletion criteria.

#### Changed
- Moved process-level GCE initialization into a dedicated `initialize.py` module.
- Added `_init_all()` as the central initialization method. Protected initialization with a thread lock.
- Preserved initialization within `cmd_get_available_templates()` because it is considered the safest location for that command. Initialization exceptions are logged and propagated instead of being silently ignored.
- Removed the automatic trim trigger from the group-delete handler. Narrowed the cleanup query to avoid deleting records outside the intended returned-machine retention criteria.

### Build and Release Infrastructure

#### Added
- Added RHEL/Rocky Linux 10 to the RPM build matrix.
- Retained support for RHEL/Rocky Linux 8 and 9.
- Added OS-specific Python package selection:
    - `python39` for versions 8 and 9.
    - `python3` for version 10.
- Added Node.js installation to the build environment.

#### Fixed
- Improved RPM build compatibility with RHEL/Rocky Linux 10.

#### Changed
- Replaced `pip3 install uv` with official `uv` installation script.

## [0.3.4] - 2025-10-17

#### Added
- Added rotating file-log support for both GCE and GKE providers.
- Added the `LOG_MAX_FILE_SIZE = 10 MB` and `LOG_MAX_ROTATE = 5` configuration options.

#### Fixed
- Prevented provider log files for growing indefinitely by introducing maximum-size and backup-count controls.

#### Changed
- Introduced RotatingFileHandler for controlling log-file growth.
- Applied the same rotating-file behavior to both `gce_provider/config.py` and `gke_provider/config.py`


## [0.3.3] - 2025-10-17

#### Added
- Standalone `hf-monitor` executable for running GCE provider event-monitoring process.
- Added a corresponding `hf-monitor.spec` pyinstaller build specification.
- Added the `hf-monitor` entry point to `pyproject.toml`.
- Added the `--monitor` option to `hf-gce`.

#### Fixed
- Fixed incorrect `getRequestStatus` response and JSON structure.
- Fixed machines being reported as running while still pending; centralized database retry behavior.

#### Changed
- Updated the provider build process to use pyinstaller with `--clean`.
- Updated GCE installation and monitoring documentation.
- Updated build instructions to generate and install both `hf-gce` and `hf-monitor`.
- Allowed the GCE provider to launch its monitoring daemon through: `hf-gce <command> --monitor`

#### Deprecated
- The legacy `gcphf` command remained available for backward compatibility.
- The project configuration explicitly marked `gcphf` as slated for future removal.
- Users should migrate the provider-specific commands: `hf-gce`, `hf-gke`, and `hf-monitor`.