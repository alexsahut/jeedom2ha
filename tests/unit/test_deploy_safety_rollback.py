"""Guardrails and rollback wiring for deploy-to-box.sh, without a Jeedom box."""
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "deploy-to-box.sh"


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
printf '{"check_runs":[{"status":"completed","conclusion":"%s"}]}\n' "$MOCK_CI_CONCLUSION"
"""
    )
    (bin_dir / "jq").write_text(
        """#!/bin/sh
case "$*" in
  *check_runs*) printf 'completed\t%s\n' "$MOCK_CI_CONCLUSION" ;;
  *) printf 'ok\n' ;;
esac
"""
    )
    (bin_dir / "ssh").write_text(
        """#!/bin/sh
printf 'ARGS: %s\n' "$*" >> "$MOCK_SSH_LOG"
stdin=$(cat)
printf '%s\n' "$stdin" >> "$MOCK_SSH_STDIN"
case "$*" in
  *localSecret*) printf '{"local_secret":"test","daemon_port":"55080"}\n' ;;
  *curl*) printf '{"status":"ok"}\n' ;;
esac
"""
    )
    for tool in bin_dir.iterdir():
        tool.chmod(0o755)
    return bin_dir


def _run(tmp_path: Path, *args: str, **env_overrides: str) -> subprocess.CompletedProcess:
    bin_dir = _write_mock_tools(tmp_path)
    env = os.environ | {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "JEEDOM_BOX_HOST": "mock-box",
        "MOCK_GIT_STATE": "clean",
        "MOCK_CI_CONCLUSION": "success",
        "MOCK_SSH_LOG": str(tmp_path / "ssh.log"),
        "MOCK_SSH_STDIN": str(tmp_path / "ssh.stdin"),
    } | env_overrides
    return subprocess.run([str(SCRIPT), *args], cwd=REPO_ROOT, env=env, text=True, capture_output=True)


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
