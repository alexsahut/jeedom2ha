"""Guardrails and rollback wiring for deploy-to-box.sh, without a Jeedom box."""
import os
import shlex
import subprocess
import tarfile
from pathlib import Path
from typing import Optional

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "deploy-to-box.sh"
ROLLBACK_LIB = REPO_ROOT / "scripts" / "deploy-rollback-lib.sh"


def _write_mock_tools(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "git").write_text(
        """#!/bin/sh
case "$*" in
  *"status --porcelain"*) [ "$MOCK_GIT_STATE" = dirty ] && printf '?? untracked-file\n' ;;
  *"rev-parse HEAD"*) printf '0123456789abcdef0123456789abcdef01234567\n' ;;
  *"config --get remote.origin.url"*) printf 'https://github.com/example/jeedom2ha.git\n' ;;
esac
"""
    )
    (bin_dir / "gh").write_text(
        """#!/bin/sh
printf '{"check_runs":[{"status":"%s","conclusion":"%s"}]}\n' "$MOCK_CI_STATUS" "$MOCK_CI_CONCLUSION"
"""
    )
    (bin_dir / "jq").write_text(
        """#!/bin/sh
case "$*" in
  *check_runs*) printf '%s\t%s\n' "$MOCK_CI_STATUS" "$MOCK_CI_CONCLUSION" ;;
  *) printf 'ok\n' ;;
esac
"""
    )
    (bin_dir / "ssh").write_text(
        """#!/bin/sh
printf 'ARGS: %s\n' "$*" >> "$MOCK_SSH_LOG"
stdin=$(cat)
printf '%s\n' "$stdin" >> "$MOCK_SSH_STDIN"
case "$*" in *"bash -s"*) _is_remote_program=true ;; *) _is_remote_program=false ;; esac
if [ -n "$MOCK_SSH_OUTPUT" ] && [ "$_is_remote_program" = true ]; then
  printf '%s\n' "$MOCK_SSH_OUTPUT"
  exit "${MOCK_SSH_EXIT:-0}"
fi
case "$*" in
  *localSecret*) printf '{"local_secret":"test","daemon_port":"55080"}\n' ;;
  *curl*) printf '{"status":"ok"}\n' ;;
esac
"""
    )
    for tool in bin_dir.iterdir():
        tool.chmod(0o755)
    return bin_dir


def _run(
    tmp_path: Path, *args: str, timeout: Optional[float] = None, **env_overrides: str
) -> subprocess.CompletedProcess:
    bin_dir = _write_mock_tools(tmp_path)
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "JEEDOM_BOX_HOST": "mock-box",
        "MOCK_GIT_STATE": "clean",
        "MOCK_CI_STATUS": "completed",
        "MOCK_CI_CONCLUSION": "success",
        "MOCK_SSH_LOG": str(tmp_path / "ssh.log"),
        "MOCK_SSH_STDIN": str(tmp_path / "ssh.stdin"),
    } | env_overrides
    try:
        return subprocess.run(
            [str(SCRIPT), *args], cwd=REPO_ROOT, env=env, text=True, capture_output=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        # The mocked ssh binary cannot speak the rsync wire protocol: once a
        # run gets past the guardrails it will eventually hang on the real
        # rsync-over-ssh transfer. Tests that only care about guardrail
        # behaviour pass a short timeout and inspect this partial result
        # instead of waiting for (or working around) that unrelated hang.
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return subprocess.CompletedProcess(exc.cmd, returncode=None, stdout=stdout, stderr=stderr)


def test_refuses_dirty_tree_before_any_ssh(tmp_path):
    result = _run(tmp_path, MOCK_GIT_STATE="dirty")

    assert result.returncode != 0
    assert "arbre Git local est sale" in result.stderr
    assert not (tmp_path / "ssh.log").exists()


def test_refuses_non_green_ci_before_any_ssh(tmp_path):
    result = _run(tmp_path, MOCK_CI_CONCLUSION="failure")

    assert result.returncode != 0
    assert "CI non verte" in result.stderr
    assert not (tmp_path / "ssh.log").exists()


# Point 4 — le gate CI était trop strict : sur le SHA de référence 85fdb7e,
# le check-run Burn-In est completed/skipped, et l'ancien gate le refusait
# (seule la conclusion "success" était acceptée). "skipped" et "neutral"
# doivent désormais passer ; un check encore "in_progress"/"queued" doit
# rester un refus, jamais un succès implicite.
@pytest.mark.parametrize("conclusion", ["success", "skipped", "neutral"])
def test_accepts_completed_check_run_with_valid_conclusion(tmp_path, conclusion):
    # A full (non --dry-run) run would go on to invoke a real rsync over the
    # mocked ssh binary, which does not speak the rsync wire protocol — that
    # would fail for reasons unrelated to the CI gate under test here. What
    # matters for this test is only that the gate itself let the run proceed
    # past jeedom2ha_verify_deploy_source to the SSH pre-checks: the gate
    # error messages must never appear, and ssh.log (written by the very
    # first ssh pre-check call) must exist.
    # The test must reach the first SSH pre-check, but the mocked run then
    # intentionally blocks at rsync.  A generous timeout avoids CI-host
    # scheduling jitter being mistaken for a rejected valid conclusion.
    result = _run(tmp_path, MOCK_CI_CONCLUSION=conclusion, timeout=10)

    assert "CI non verte" not in result.stderr
    assert "check-run non terminé" not in result.stderr
    assert (tmp_path / "ssh.log").exists()


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "timed_out", "action_required"])
def test_refuses_completed_check_run_with_invalid_conclusion(tmp_path, conclusion):
    result = _run(tmp_path, MOCK_CI_CONCLUSION=conclusion)

    assert result.returncode != 0
    assert "CI non verte" in result.stderr
    assert not (tmp_path / "ssh.log").exists()


@pytest.mark.parametrize("status", ["in_progress", "queued"])
def test_refuses_check_run_not_yet_completed_even_with_success_like_conclusion(tmp_path, status):
    # A running check-run must never be treated as an implicit success, even
    # if its (still provisional) conclusion field happens to read "success".
    result = _run(tmp_path, MOCK_CI_STATUS=status, MOCK_CI_CONCLUSION="success")

    assert result.returncode != 0
    assert "check-run non terminé" in result.stderr
    assert not (tmp_path / "ssh.log").exists()


def _extract_function(name: str) -> str:
    """Slice a single top-level `name() { ... }` function verbatim out of
    deploy-to-box.sh. The script runs guardrail code unconditionally at
    source time (arg parsing, jeedom2ha_verify_deploy_source, ...), so it
    cannot be sourced wholesale just to reach one function further down —
    slicing lets point 9's tag/push logic be exercised on its own, with a
    mocked git binary, without a full (real-rsync-requiring) deploy run."""
    text = SCRIPT.read_text()
    start = text.index(f"{name}() {{")
    end = text.index("\n}\n", start) + len("\n}\n")
    return text[start:end]


def _run_tag_function(tmp_path: Path, *, push_should_fail: bool) -> "tuple[subprocess.CompletedProcess, str]":
    func_src = _extract_function("jeedom2ha_create_and_push_deploy_tag")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    git_log = tmp_path / "git.log"
    (bin_dir / "git").write_text(
        f"""#!/bin/sh
printf '%s\\n' "$*" >> "{git_log}"
case "$*" in
  *"push origin"*) exit {1 if push_should_fail else 0} ;;
  *) exit 0 ;;
esac
"""
    )
    (bin_dir / "git").chmod(0o755)
    script = tmp_path / "tag_func.sh"
    script.write_text(func_src)
    env = os.environ | {"PATH": f"{bin_dir}:{os.environ['PATH']}", "REPO_ROOT": str(REPO_ROOT)}
    result = subprocess.run(
        ["bash", "-c", f"set -euo pipefail; source '{script}'; jeedom2ha_create_and_push_deploy_tag deadbeef 2026-09-27T00:00:00Z"],
        env=env,
        capture_output=True,
        text=True,
    )
    return result, (git_log.read_text() if git_log.exists() else "")


def test_creates_and_pushes_deploy_tag_to_origin(tmp_path):
    # Point 9 — a deploy tag left local-only is useless for shared
    # traceability; it must be pushed to origin.
    result, git_log = _run_tag_function(tmp_path, push_should_fail=False)

    assert result.returncode == 0, result.stderr
    assert "Tag annoté créé" in result.stdout
    assert "Tag poussé vers origin" in result.stdout
    assert "tag -a deploy-deadbeef-" in git_log
    assert "push origin deploy-deadbeef-" in git_log


def test_tag_push_failure_warns_but_does_not_fail_the_deploy(tmp_path):
    # A push failure at this stage is a non-blocking warning: the deploy
    # itself already succeeded, and the local tag remains available for a
    # later manual push.
    result, git_log = _run_tag_function(tmp_path, push_should_fail=True)

    assert result.returncode == 0, result.stderr
    assert "Tag annoté créé" in result.stdout
    assert "push du tag" in result.stderr
    assert "a échoué" in result.stderr
    assert "push origin deploy-deadbeef-" in git_log


def test_rollback_requires_an_archive_argument(tmp_path):
    result = _run(tmp_path, "--rollback")

    assert result.returncode != 0
    assert "--rollback requires a remote .tar.gz archive path" in result.stderr


def test_rollback_parses_archive_and_builds_safe_remote_restart(tmp_path):
    archive = "/home/test/jeedom2ha-backups/jeedom2ha-20260927T000000Z-a.tar.gz"
    result = _run(tmp_path, "--rollback", archive)

    assert result.returncode == 0, result.stderr
    remote_program = (tmp_path / "ssh.stdin").read_text()
    assert archive in (tmp_path / "ssh.log").read_text()
    assert 'sudo tar -xzf "$' + '{ARCHIVE}" -C "$' + '{_work}"' in remote_program
    assert "jeedom2ha::deamon_stop();" in remote_program
    assert "jeedom2ha::deamon_start()" in remote_program
    assert "sudo -u www-data" in remote_program


def test_rollback_failure_after_backup_prints_remote_output_and_backup_path(tmp_path):
    archive = "/home/test/jeedom2ha-backups/previous.tar.gz"
    pre_rollback = "/home/test/jeedom2ha-backups/jeedom2ha-pre-rollback-safe.tar.gz"
    result = _run(
        tmp_path,
        "--rollback",
        archive,
        MOCK_SSH_OUTPUT=f"__JEEDOM2HA_BACKUP_ARCHIVE__={pre_rollback}\nremote restore failed",
        MOCK_SSH_EXIT="17",
    )

    assert result.returncode == 17
    assert "remote restore failed" in result.stdout
    assert pre_rollback in result.stderr


def test_after_inventory_is_captured_only_after_successful_sync():
    code = SCRIPT.read_text()
    after_inventory = code.index('jeedom2ha_inventory_discovery "after"')
    sync_success = code.index('echo "  OK — ${_summary}"')
    assert after_inventory > sync_success


def _extract_rollback_extraction_snippet() -> str:
    """Slice the exact remote extraction block — from the ARCHIVE/PLUGIN_PATH
    positional args through the 'jeedom2ha/ absente' guard — verbatim out of
    jeedom2ha_rollback_archive() in deploy-to-box.sh. This is the real code
    under test (not a hand-copied reimplementation), so a regression in the
    shipped script is caught even if the surrounding code moves around."""
    text = SCRIPT.read_text()
    start_marker = 'ARCHIVE="$1"; PLUGIN_PATH="$2"; JEEDOM_ROOT="$3"; BACKUP_DIR="$4"; BOX_USER="$5"'
    end_marker = (
        'sudo test -d "${_work}/jeedom2ha" || '
        '{ echo "ERROR: jeedom2ha/ absente après extraction." >&2; exit 1; }'
    )
    start = text.index(start_marker)
    end = text.index(end_marker, start) + len(end_marker)
    return text[start:end]


# `sudo` here is not a plain passthrough (as in test_deploy_rollback_lib.py):
# it faithfully models the real permission wall a `sudo mktemp -d`/`sudo tar
# -xzf` pair creates on the box (a root-owned, non-traversable work dir) —
# without relying on Unix permission bits, which a root-run test process
# (common in CI containers) would simply bypass, making the wall a no-op and
# letting the pre-fix, unprivileged `[[ -d ... ]]` pass through undetected
# (caught in review: reproduced locally with `sudo pytest -k
# rollback_extraction_check`, where the "would have caught the old bug" test
# failed under root with the mode-000 version of this stub). Renaming the
# work dir out of the way is a real filesystem-existence barrier instead: it
# blocks root exactly as it blocks anyone else, since a path that has been
# renamed away simply is not there to look up, privilege or not.
# `sudo mktemp -d` renames its freshly created directory to `<path>.locked`
# right away; any *other* `sudo ...` call temporarily renames all tracked
# work dirs back to their real path (like real root bypassing permission
# checks) before renaming them away again. A bare, unprefixed command
# touching that same directory — the exact shape of the regression this test
# guards against — finds nothing at that path and fails, exactly as it would
# against a real root-owned, non-traversable directory on the box.
_PRIVILEGE_WALL_SUDO_STUB = '''
LOCKED_DIRS_FILE="$(mktemp)"
sudo() {
  if [ "$1" = "mktemp" ]; then
    shift
    local d
    d=$(command mktemp "$@")
    mv "$d" "$d.locked"
    printf '%s\\n' "$d" >> "$LOCKED_DIRS_FILE"
    printf '%s\\n' "$d"
    return 0
  fi
  local -a _unlocked=()
  if [ -s "$LOCKED_DIRS_FILE" ]; then
    while IFS= read -r d; do
      if [ -e "$d.locked" ]; then
        mv "$d.locked" "$d"
        _unlocked+=("$d")
      fi
    done < "$LOCKED_DIRS_FILE"
  fi
  "$@"
  local rc=$?
  for d in "${_unlocked[@]}"; do
    [ -e "$d" ] && mv "$d" "$d.locked" 2>/dev/null
  done
  return $rc
}
'''


def _make_rollback_archive(tmp_path: Path) -> Path:
    archive = tmp_path / "rollback-src.tar.gz"
    staging = tmp_path / "_staging"
    (staging / "jeedom2ha" / "core" / "class").mkdir(parents=True)
    (staging / "jeedom2ha" / "core" / "class" / "jeedom2ha.class.php").write_text("<?php")
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(staging / "jeedom2ha", arcname="jeedom2ha")
    return archive


def _run_rollback_extraction(tmp_path: Path, snippet: str) -> subprocess.CompletedProcess:
    archive = _make_rollback_archive(tmp_path)
    plugin_path = tmp_path / "plugins" / "jeedom2ha"
    plugin_path.parent.mkdir(parents=True, exist_ok=True)  # e.g. /var/www/html/plugins on the box
    script = f'''
set -euo pipefail
{_PRIVILEGE_WALL_SUDO_STUB}
source "{ROLLBACK_LIB}"
{snippet}
echo "EXTRACTION_OK"
'''
    return subprocess.run(
        ["bash", "-c", script, "bash", str(archive), str(plugin_path), "x", "x", "x"],
        capture_output=True,
        text=True,
    )


def test_rollback_extraction_check_survives_a_root_owned_non_traversable_work_dir():
    # Regression: `sudo mktemp -d` / `sudo tar -xzf` create and populate the
    # extraction work dir as root, which real terrain exposed as a
    # non-traversable directory for the unprivileged SSH user. The presence
    # check right after extraction must itself run under `sudo`, or it fails
    # even though the archive extracted successfully (observed on the box:
    # "ERROR: jeedom2ha/ absente après extraction." against an intact
    # archive, confirmed valid by a separate read-only `tar -tzf`).
    with_tmp = Path(__import__("tempfile").mkdtemp())
    try:
        snippet = _extract_rollback_extraction_snippet()
        result = _run_rollback_extraction(with_tmp, snippet)
        assert result.returncode == 0, result.stderr
        assert "EXTRACTION_OK" in result.stdout
        assert "jeedom2ha/ absente" not in result.stderr
    finally:
        subprocess.run(["chmod", "-R", "u+rwx", str(with_tmp)])
        subprocess.run(["rm", "-rf", str(with_tmp)])


def test_rollback_extraction_check_would_have_caught_the_old_unprivileged_bug():
    # Proof the harness above actually exercises the permission wall: the
    # pre-fix `[[ -d "${_work}/jeedom2ha" ]]` (no sudo) run against the same
    # locked-down work dir must fail exactly like the real terrain incident.
    with_tmp = Path(__import__("tempfile").mkdtemp())
    try:
        buggy_snippet = (
            'ARCHIVE="$1"; PLUGIN_PATH="$2"\n'
            'set -euo pipefail\n'
            '[[ -r "${ARCHIVE}" ]] || { echo "ERROR: archive inaccessible: ${ARCHIVE}" >&2; exit 1; }\n'
            'jeedom2ha_validate_rollback_archive "${ARCHIVE}"\n'
            '_parent=$(dirname "${PLUGIN_PATH}")\n'
            '_work=$(sudo mktemp -d "${_parent}/.jeedom2ha-rollback.XXXXXX")\n'
            'cleanup() { sudo rm -rf "${_work}"; }\n'
            'trap cleanup EXIT\n'
            'sudo tar -xzf "${ARCHIVE}" -C "${_work}"\n'
            '[[ -d "${_work}/jeedom2ha" ]] || '
            '{ echo "ERROR: jeedom2ha/ absente après extraction." >&2; exit 1; }\n'
        )
        result = _run_rollback_extraction(with_tmp, buggy_snippet)
        assert result.returncode != 0
        assert "jeedom2ha/ absente après extraction" in result.stderr
    finally:
        subprocess.run(["chmod", "-R", "u+rwx", str(with_tmp)])
        subprocess.run(["rm", "-rf", str(with_tmp)])


# --- CC-20: secrets must never reach ssh's/curl's/mosquitto_sub's argv -----
#
# Unlike _write_mock_tools's `ssh` (which only replays a canned
# $MOCK_SSH_OUTPUT), the mock below actually executes the piped remote
# script locally, after the `--` separator, against whatever mocked remote
# tools (curl / mosquitto_sub / sudo) are placed earlier on PATH. That is
# what lets these tests exercise the real stdin-transmission mechanism
# end-to-end, instead of only inspecting the local ssh invocation.


def _write_remote_exec_ssh_mock(bin_dir: Path) -> None:
    (bin_dir / "ssh").write_text(
        """#!/bin/bash
printf 'ARGS: %s\\n' "$*" >> "$MOCK_SSH_LOG"
stdin=$(cat)
printf '%s\\n' "$stdin" >> "$MOCK_SSH_STDIN"
remote_args=()
capture=0
for a in "$@"; do
  if [ "$capture" = 1 ]; then
    remote_args+=("$a")
  fi
  if [ "$a" = "--" ]; then
    capture=1
  fi
done
printf '%s' "$stdin" | bash -s -- "${remote_args[@]}"
"""
    )
    (bin_dir / "ssh").chmod(0o755)


def test_curl_with_secret_transmits_via_stdin_not_argv(tmp_path):
    # CC-20: jeedom2ha_curl_with_secret must never place LOCAL_SECRET on
    # ssh's or curl's command line (visible via `ps`/`/proc/<pid>/cmdline`
    # to any local user, on the deploy machine and on the box). It must
    # travel as bash source over stdin (printf %q) and land in a chmod-600
    # curl -K config file on the remote side. This fails against the
    # pre-fix script, which built the header directly into the command
    # string sent to ssh.
    func_src = _extract_function("jeedom2ha_curl_with_secret")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_remote_exec_ssh_mock(bin_dir)

    # Quote and backslashes: exercises curl -K's own escaping rules.
    secret = 'p@ss"word\\with\\backslash'

    curl_argv_log = tmp_path / "curl.argv.log"
    curl_config_log = tmp_path / "curl.config.log"
    (bin_dir / "curl").write_text(
        """#!/bin/bash
printf 'ARGS: %s\\n' "$*" >> "$MOCK_CURL_ARGV_LOG"
if [ "$1" = "-K" ]; then
  cat "$2" >> "$MOCK_CURL_CONFIG_LOG"
fi
printf '{"status":"ok"}\\n'
"""
    )
    (bin_dir / "curl").chmod(0o755)

    script = tmp_path / "curl_func.sh"
    script.write_text(func_src)
    ssh_log = tmp_path / "ssh.log"
    ssh_stdin = tmp_path / "ssh.stdin"
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "MOCK_SSH_LOG": str(ssh_log),
        "MOCK_SSH_STDIN": str(ssh_stdin),
        "MOCK_CURL_ARGV_LOG": str(curl_argv_log),
        "MOCK_CURL_CONFIG_LOG": str(curl_config_log),
        "LOCAL_SECRET": secret,
    }
    result = subprocess.run(
        [
            "bash", "-c",
            f"set -euo pipefail; SSH_OPTS=(); SSH_TARGET=mock-target; "
            f"source '{script}'; "
            f"jeedom2ha_curl_with_secret 'https://127.0.0.1:5555/system/status' 5 GET",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert secret not in ssh_log.read_text()
    assert secret not in curl_argv_log.read_text()
    assert "LOCAL_SECRET=" in ssh_stdin.read_text()
    escaped = secret.replace("\\", "\\\\").replace('"', '\\"')
    assert f'header = "X-Local-Secret: {escaped}"' in curl_config_log.read_text()


def test_mqtt_credentials_never_in_ssh_argv(tmp_path):
    # CC-20: MQTT credentials must never appear in ssh's or mosquitto_sub's
    # argv. They travel over stdin (printf %q, same mechanism as the curl
    # helper above) and land in a chmod-600 mosquitto -o options file on the
    # remote side, written in mosquitto's own raw `-u <value>` / `-P
    # <value>` format (mosquitto does no shell-style unescaping of that
    # file — see client_shared.c). This fails against the pre-fix script,
    # which passed MQTT_USER/MQTT_PASS as positional args to
    # `ssh ... bash -s --`.
    func_src = "\n".join(
        [
            _extract_function("jeedom2ha_mqtt_auth_snippet"),
            _extract_function("jeedom2ha_inventory_discovery"),
        ]
    )
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_remote_exec_ssh_mock(bin_dir)

    # Quotes, spaces and backslashes: adversarial values a real password
    # could contain, and exactly what raw (unescaped) mosquitto -o lines
    # must still carry unchanged.
    mqtt_user = 'mqtt"user\\with\\backslash'
    mqtt_pass = "p@ss word's \\back \"quoted\""

    mosquitto_argv_log = tmp_path / "mosquitto.argv.log"
    mosquitto_opts_log = tmp_path / "mosquitto.opts.log"
    (bin_dir / "mosquitto_sub").write_text(
        """#!/bin/bash
printf 'ARGS: %s\\n' "$*" >> "$MOCK_MOSQUITTO_ARGV_LOG"
for ((i=1; i<=$#; i++)); do
  if [ "${!i}" = "-o" ]; then
    j=$((i + 1))
    cat "${!j}" >> "$MOCK_MOSQUITTO_OPTS_LOG"
  fi
done
printf 'homeassistant/switch/jeedom2ha_pool/config\\n'
"""
    )
    (bin_dir / "mosquitto_sub").chmod(0o755)
    (bin_dir / "sudo").write_text("#!/bin/sh\nexec \"$@\"\n")
    (bin_dir / "sudo").chmod(0o755)

    backup_dir = tmp_path / "backups"
    script = tmp_path / "mqtt_func.sh"
    script.write_text(func_src)
    ssh_log = tmp_path / "ssh.log"
    ssh_stdin = tmp_path / "ssh.stdin"
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "MOCK_SSH_LOG": str(ssh_log),
        "MOCK_SSH_STDIN": str(ssh_stdin),
        "MOCK_MOSQUITTO_ARGV_LOG": str(mosquitto_argv_log),
        "MOCK_MOSQUITTO_OPTS_LOG": str(mosquitto_opts_log),
    }
    result = subprocess.run(
        [
            "bash", "-c",
            f"set -euo pipefail; SSH_OPTS=(); SSH_TARGET=mock-target; "
            f"_mqtt_host=127.0.0.1; _mqtt_port=1883; "
            f"_mqtt_user={shlex.quote(mqtt_user)}; _mqtt_pass={shlex.quote(mqtt_pass)}; "
            f"JEEDOM_BACKUP_DIR={shlex.quote(str(backup_dir))}; "
            f"source '{script}'; "
            f"jeedom2ha_inventory_discovery after",
        ],
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    ssh_argv = ssh_log.read_text()
    mosquitto_argv = mosquitto_argv_log.read_text()
    assert mqtt_user not in ssh_argv
    assert mqtt_pass not in ssh_argv
    assert mqtt_user not in mosquitto_argv
    assert mqtt_pass not in mosquitto_argv
    assert "MQTT_USER=" in ssh_stdin.read_text()
    opts_content = mosquitto_opts_log.read_text()
    assert f"-u {mqtt_user}\n" in opts_content
    assert f"-P {mqtt_pass}\n" in opts_content
