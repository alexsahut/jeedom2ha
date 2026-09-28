"""Regression tests for deploy SSH stdin programs, without a Jeedom box."""

import os
import shlex
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "deploy-to-box.sh"


def _extract_function(name: str) -> str:
    text = SCRIPT.read_text()
    start = text.index(f"{name}() {{")
    end = text.index("\n}\n", start) + len("\n}\n")
    return text[start:end]


def _write_fake_tools(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "ssh").write_text(
        """#!/bin/sh
printf '%s\\n' "$@" > "$MOCK_SSH_ARGV"
stdin=$(mktemp)
cat > "$stdin"
remote=
seen_bash=false
for arg in "$@"; do
  if [ "$seen_bash" = true ]; then
    remote="$remote $arg"
  elif [ "$arg" = bash ]; then
    seen_bash=true
    remote=bash
  fi
done
if [ "$seen_bash" = true ]; then
  sh -c "$remote" < "$stdin"
fi
status=$?
rm -f "$stdin"
exit "$status"
"""
    )
    (bin_dir / "curl").write_text(
        """#!/bin/sh
printf '%s\\n' "$@" > "$MOCK_CURL_ARGV"
while [ "$#" -gt 0 ]; do
  if [ "$1" = -K ]; then
    cat "$2" > "$MOCK_CURL_CONFIG"
    break
  fi
  shift
done
printf '{"status":"ok"}\\n'
"""
    )
    for tool in bin_dir.iterdir():
        tool.chmod(0o755)
    return bin_dir


def _run_curl_helper(tmp_path: Path, method: str, data_file: str = "") -> subprocess.CompletedProcess:
    bin_dir = _write_fake_tools(tmp_path)
    helper = tmp_path / "helper.sh"
    helper.write_text(_extract_function("jeedom2ha_curl_with_secret"))
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "MOCK_SSH_ARGV": str(tmp_path / "ssh.argv"),
        "MOCK_CURL_ARGV": str(tmp_path / "curl.argv"),
        "MOCK_CURL_CONFIG": str(tmp_path / "curl.config"),
    }
    command = (
        "set -euo pipefail; "
        f"source {helper}; "
        "LOCAL_SECRET='secret-for-argv-test'; "
        "SSH_OPTS=(-o BatchMode=yes); SSH_TARGET=mock-box; "
        "jeedom2ha_curl_with_secret http://127.0.0.1:55080/action/test 5 "
        f"{shlex.quote(method)} {shlex.quote(data_file)}"
    )
    return subprocess.run(["bash", "-c", command], text=True, capture_output=True, env=env)


def _assert_secret_never_in_argv(tmp_path: Path) -> None:
    secret = "secret-for-argv-test"
    assert secret not in (tmp_path / "ssh.argv").read_text()
    assert secret not in (tmp_path / "curl.argv").read_text()


def test_get_without_data_file_survives_real_ssh_argument_recomposition(tmp_path):
    result = _run_curl_helper(tmp_path, "GET")

    assert result.returncode == 0, result.stderr
    _assert_secret_never_in_argv(tmp_path)
    config = (tmp_path / "curl.config").read_text()
    assert 'url = "http://127.0.0.1:55080/action/test"' in config
    assert "request = POST" not in config


def test_post_with_data_file_survives_real_ssh_argument_recomposition(tmp_path):
    result = _run_curl_helper(tmp_path, "POST", "/tmp/body with spaces.json")

    assert result.returncode == 0, result.stderr
    _assert_secret_never_in_argv(tmp_path)
    config = (tmp_path / "curl.config").read_text()
    assert "request = POST" in config
    assert "data-binary = @/tmp/body with spaces.json" in config


def test_deploy_surfaces_last_readiness_and_control_errors_without_secret():
    source = SCRIPT.read_text()

    assert "_last_readiness_error=" in source
    assert "Dernière erreur readiness:" in source
    assert 'jeedom2ha_curl_with_secret "${DAEMON_API}/system/status" 3 GET 2>&1' in source
    assert 'Daemon injoignable sur ${DAEMON_API}: ${_status_raw:-aucune sortie}' in source
    assert 'Appel /action/sync échoué: ${_sync_raw:-aucune sortie}' in source
