"""
test_deploy_rollback_lib.py — Points 5, 6, 7 : preuve unitaire, SANS SSH ni
box réelle, de la logique de scripts/deploy-rollback-lib.sh utilisée par le
mode --rollback de deploy-to-box.sh.

Comme scripts/deploy-version-file.sh, cette bibliothèque ne contient aucun
appel ssh/scp : elle est sourcée ici en local (bash pur, avec `sudo` stubbé
en simple passthrough puisqu'aucun compte www-data réel n'est nécessaire
pour prouver la logique) exactement comme elle l'est via
`ssh ... bash -s --` dans deploy-to-box.sh — seul l'environnement
d'exécution change, jamais les fonctions testées.

Rejouer :
    pytest tests/unit/test_deploy_rollback_lib.py -v
"""
import subprocess
import tarfile
from pathlib import Path

LIB = Path(__file__).resolve().parents[2] / "scripts" / "deploy-rollback-lib.sh"

# `sudo` est stubbé en passthrough : les fonctions de la lib gardent leurs
# appels `sudo` explicites (même forme qu'en production), mais aucun compte
# www-data réel n'est requis pour les rejouer localement.
_SUDO_STUB = 'sudo() { "$@"; }; '


def _run_bash(snippet: str, extra_prelude: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", f"set -euo pipefail; {_SUDO_STUB}{extra_prelude}source '{LIB}'; {snippet}"],
        capture_output=True,
        text=True,
    )


def _make_archive(tmp_path: Path, entries: dict) -> Path:
    """Build a .tar.gz at tmp_path/src.tar.gz whose members are the given
    {relative_path: content} mapping (relative_path drives the on-disk tar
    entry name, so callers control whether jeedom2ha/ is the root or not)."""
    archive = tmp_path / "src.tar.gz"
    staging = tmp_path / "_staging"
    staging.mkdir()
    for rel_path, content in entries.items():
        full = staging / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
    with tarfile.open(archive, "w:gz") as tar:
        for rel_path in entries:
            tar.add(staging / rel_path, arcname=rel_path)
    return archive


class TestValidateRollbackArchive:
    """jeedom2ha_validate_rollback_archive — point 5."""

    def test_accepts_archive_rooted_at_jeedom2ha(self, tmp_path):
        archive = _make_archive(tmp_path, {"jeedom2ha/core/class/jeedom2ha.class.php": "<?php"})

        result = _run_bash(f'jeedom2ha_validate_rollback_archive "{archive}"')

        assert result.returncode == 0, result.stderr

    def test_rejects_archive_without_jeedom2ha_root(self, tmp_path):
        archive = _make_archive(tmp_path, {"otherplugin/file.php": "<?php"})

        result = _run_bash(f'jeedom2ha_validate_rollback_archive "{archive}"')

        assert result.returncode != 0
        assert "racine jeedom2ha/ absente" in result.stderr

    def test_rejects_archive_with_content_outside_jeedom2ha(self, tmp_path):
        archive = _make_archive(
            tmp_path,
            {
                "jeedom2ha/core/class/jeedom2ha.class.php": "<?php",
                "otherplugin/file.php": "<?php",
            },
        )

        result = _run_bash(f'jeedom2ha_validate_rollback_archive "{archive}"')

        assert result.returncode != 0
        assert "contenu hors jeedom2ha/" in result.stderr

    def test_rejects_unreadable_archive(self, tmp_path):
        missing = tmp_path / "does-not-exist.tar.gz"

        result = _run_bash(f'jeedom2ha_validate_rollback_archive "{missing}"')

        assert result.returncode != 0
        assert "lecture de l'archive impossible" in result.stderr

    def test_survives_repeated_runs_on_a_large_archive_without_sigpipe(self, tmp_path):
        # Point 5 régression : l'ancien code pipait `tar -tzf ... | grep -q
        # ...` sous pipefail. Avec suffisamment d'entrées, grep pouvait
        # trouver sa correspondance dans les toutes premières lignes et
        # sortir avant que tar ait fini d'écrire le reste — tar recevait
        # alors SIGPIPE et pipefail faisait échouer tout le pipeline, même
        # pour une archive valide. On rejoue la validation plusieurs fois
        # sur une archive à de nombreuses entrées pour prouver l'absence de
        # flakiness.
        entries = {"jeedom2ha/README.md": "root marker, matches on line 1"}
        for i in range(2000):
            entries[f"jeedom2ha/data/entry-{i:05d}.txt"] = f"payload {i}"
        archive = _make_archive(tmp_path, entries)

        for _ in range(20):
            result = _run_bash(f'jeedom2ha_validate_rollback_archive "{archive}"')
            assert result.returncode == 0, result.stderr


class TestBackupPluginDir:
    """jeedom2ha_backup_plugin_dir — point 7 (rollback réversible)."""

    def test_fails_when_plugin_missing_and_required(self, tmp_path):
        missing_plugin = tmp_path / "plugins" / "jeedom2ha"
        backup_dir = tmp_path / "backups"

        result = _run_bash(
            f'jeedom2ha_backup_plugin_dir "{missing_plugin}" "{backup_dir}" "$(id -un):$(id -un)" '
            '"jeedom2ha-pre-rollback" "true"'
        )

        assert result.returncode != 0
        assert "plugin absent" in result.stderr

    def test_succeeds_when_plugin_missing_and_not_required(self, tmp_path):
        missing_plugin = tmp_path / "plugins" / "jeedom2ha"
        backup_dir = tmp_path / "backups"

        result = _run_bash(
            f'jeedom2ha_backup_plugin_dir "{missing_plugin}" "{backup_dir}" "$(id -un):$(id -un)" '
            '"jeedom2ha-pre-rollback" "false"'
        )

        assert result.returncode == 0, result.stderr
        assert "__JEEDOM2HA_BACKUP_ARCHIVE__=" not in result.stdout

    def test_archives_plugin_including_data_dir_with_expected_perms(self, tmp_path):
        plugin_path = tmp_path / "plugins" / "jeedom2ha"
        (plugin_path / "core" / "class").mkdir(parents=True)
        (plugin_path / "core" / "class" / "jeedom2ha.class.php").write_text("<?php")
        (plugin_path / "data").mkdir()
        (plugin_path / "data" / "overrides.json").write_text('{"kept": true}')
        backup_dir = tmp_path / "backups"

        result = _run_bash(
            f'jeedom2ha_backup_plugin_dir "{plugin_path}" "{backup_dir}" "$(id -un):$(id -un)" '
            '"jeedom2ha-pre-rollback" "true"'
        )

        assert result.returncode == 0, result.stderr

        marker_lines = [
            line for line in result.stdout.splitlines() if line.startswith("__JEEDOM2HA_BACKUP_ARCHIVE__=")
        ]
        assert len(marker_lines) == 1
        archive = Path(marker_lines[0].split("=", 1)[1])
        assert archive.exists()
        assert archive.parent == backup_dir

        assert oct(backup_dir.stat().st_mode & 0o777) == "0o700"
        assert oct(archive.stat().st_mode & 0o777) == "0o600"

        with tarfile.open(archive, "r:gz") as tar:
            names = tar.getnames()
        assert any(name.endswith("jeedom2ha/data/overrides.json") for name in names)
        assert any(name.endswith("jeedom2ha/core/class/jeedom2ha.class.php") for name in names)


class TestStopDaemonWithPidFallback:
    """jeedom2ha_stop_daemon_with_pid_fallback — point 6."""

    def test_returns_immediately_when_plugin_class_stop_succeeds(self, tmp_path):
        pid_file = tmp_path / "deamon.pid"  # deliberately absent — must never be consulted

        result = _run_bash(
            f'jeedom2ha_stop_daemon_with_pid_fallback "{pid_file}"',
            extra_prelude='jeedom2ha_stop_via_plugin_class() { return 0; }; ',
        )

        assert result.returncode == 0, result.stderr
        assert "Daemon arrêté via jeedom2ha::deamon_stop()." in result.stdout

    def test_falls_back_gracefully_when_no_pid_file_exists(self, tmp_path):
        pid_file = tmp_path / "deamon.pid"

        result = _run_bash(
            f'jeedom2ha_stop_daemon_with_pid_fallback "{pid_file}"',
            extra_prelude='jeedom2ha_stop_via_plugin_class() { return 1; }; ',
        )

        assert result.returncode == 0, result.stderr
        assert "Aucun PID file" in result.stdout

    def test_falls_back_gracefully_on_invalid_pid_file_content(self, tmp_path):
        pid_file = tmp_path / "deamon.pid"
        pid_file.write_text("not-a-pid")

        result = _run_bash(
            f'jeedom2ha_stop_daemon_with_pid_fallback "{pid_file}"',
            extra_prelude='jeedom2ha_stop_via_plugin_class() { return 1; }; ',
        )

        assert result.returncode == 0, result.stderr
        assert "PID file invalide" in result.stdout

    def test_falls_back_gracefully_when_pid_process_is_already_gone(self, tmp_path):
        pid_file = tmp_path / "deamon.pid"
        pid_file.write_text("999999")
        signal_log = tmp_path / "signals.log"

        result = _run_bash(
            f'jeedom2ha_stop_daemon_with_pid_fallback "{pid_file}"',
            extra_prelude=(
                f'JEEDOM2HA_PROC_ROOT="{tmp_path}/missing-proc"; SIGNAL_LOG="{signal_log}"; '
                'jeedom2ha_stop_via_plugin_class() { return 1; }; '
                'sudo() { if [ "$1" = -u ]; then shift 2; fi; '
                'if [ "$1" = kill ]; then echo "$*" >> "$SIGNAL_LOG"; return 0; fi; "$@"; }; '
            ),
        )

        assert result.returncode == 0, result.stderr
        assert "/proc/999999 est absent" in result.stdout
        assert not signal_log.exists()

    def test_refuses_pid_owned_by_another_user_without_signalling(self, tmp_path):
        pid_file = tmp_path / "deamon.pid"
        proc_root = tmp_path / "proc"
        pid = "4242"
        proc = proc_root / pid
        proc.mkdir(parents=True)
        (proc / "status").write_text("Name:\tother\nUid:\t0\t0\t0\t0\n")
        (proc / "cmdline").write_bytes(b"python\0/var/www/html/plugins/jeedom2ha/resources/daemon/main.py\0")
        pid_file.write_text(pid)
        signal_log = tmp_path / "signals.log"

        result = _run_bash(
            f'jeedom2ha_stop_daemon_with_pid_fallback "{pid_file}"',
            extra_prelude=(
                f'JEEDOM2HA_PROC_ROOT="{proc_root}"; SIGNAL_LOG="{signal_log}"; '
                'jeedom2ha_stop_via_plugin_class() { return 1; }; '
                'sudo() { if [ "$1" = -u ]; then shift 2; fi; '
                'if [ "$1" = kill ]; then echo "$*" >> "$SIGNAL_LOG"; return 0; fi; "$@"; }; '
            ),
        )

        assert result.returncode == 0, result.stderr
        assert "propriétaire différent" in result.stdout
        assert not signal_log.exists()

    def test_refuses_pid_with_unrelated_cmdline_without_signalling(self, tmp_path):
        pid_file = tmp_path / "deamon.pid"
        proc_root = tmp_path / "proc"
        pid = "4243"
        proc = proc_root / pid
        proc.mkdir(parents=True)
        www_data_uid = subprocess.check_output(["id", "-u", "www-data"], text=True).strip()
        (proc / "status").write_text(f"Name:\tzigbee\nUid:\t{www_data_uid}\t{www_data_uid}\t{www_data_uid}\t{www_data_uid}\n")
        (proc / "cmdline").write_bytes(b"python\0/opt/zigbee/daemon.py\0")
        pid_file.write_text(pid)
        signal_log = tmp_path / "signals.log"

        result = _run_bash(
            f'jeedom2ha_stop_daemon_with_pid_fallback "{pid_file}"',
            extra_prelude=(
                f'JEEDOM2HA_PROC_ROOT="{proc_root}"; SIGNAL_LOG="{signal_log}"; '
                'jeedom2ha_stop_via_plugin_class() { return 1; }; '
                'sudo() { if [ "$1" = -u ]; then shift 2; fi; '
                'if [ "$1" = kill ]; then echo "$*" >> "$SIGNAL_LOG"; return 0; fi; "$@"; }; '
            ),
        )

        assert result.returncode == 0, result.stderr
        assert "cmdline ne correspond pas" in result.stdout
        assert not signal_log.exists()


def test_library_never_references_ssh_or_scp():
    """Host-agnostic: no ssh/scp call inside the library itself — this is
    what makes it safe and meaningful to test here, on local temp
    directories and locally-spawned processes, without ever connecting to
    the real Jeedom box."""
    code_lines = [
        line for line in LIB.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    assert not any("ssh" in line for line in code_lines)
    assert not any("scp" in line for line in code_lines)
