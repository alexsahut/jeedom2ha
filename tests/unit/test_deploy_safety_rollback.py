"""Guardrails and rollback wiring for deploy-to-box.sh, without a Jeedom box."""
import os
import subprocess
from pathlib import Path
from typing import Optional

import pytest


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
    result = _run(tmp_path, MOCK_CI_CONCLUSION=conclusion, timeout=3)

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
