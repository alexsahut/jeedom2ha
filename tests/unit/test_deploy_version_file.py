"""
test_deploy_version_file.py — Point 1c : preuve unitaire, SANS SSH ni box
réelle, que la logique d'écriture atomique du fichier VERSION utilisée par
scripts/deploy-to-box.sh est correcte.

scripts/deploy-version-file.sh ne contient aucun appel ssh/scp : il est
sourcé ici en local (bash pur, répertoire temporaire jouant le rôle de la
racine du plugin sur la box) exactement comme il l'est via
`ssh ... sudo bash -s` dans deploy-to-box.sh — seul l'environnement
d'exécution change, jamais la fonction testée.

Rejouer :
    pytest tests/unit/test_deploy_version_file.py -v
"""
import subprocess
from pathlib import Path

LIB = Path(__file__).resolve().parents[2] / "scripts" / "deploy-version-file.sh"


def _run_bash(snippet: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", f"set -euo pipefail; source '{LIB}'; {snippet}"],
        capture_output=True,
        text=True,
    )


class TestRenderVersionContent:
    """jeedom2ha_render_version_content builds the exact VERSION file content."""

    def test_renders_expected_key_value_lines(self):
        """Given version/sha/date/status,
        When rendered,
        Then all 4 fields appear as key=value lines in order."""
        result = _run_bash(
            'jeedom2ha_render_version_content "0.3.0" "deadbeef" '
            '"2026-09-27T00:00:00Z" "clean"'
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout == (
            "version=0.3.0\n"
            "sha=deadbeef\n"
            "deployed_at=2026-09-27T00:00:00Z\n"
            "git_status=clean\n"
        )


class TestWriteVersionFileAtomic:
    """jeedom2ha_write_version_file_atomic — atomic write + readback."""

    def test_writes_and_reads_back_content(self, tmp_path):
        """Given a fake plugin-root directory (no ssh involved at all),
        When writing VERSION,
        Then the readback printed on stdout matches exactly what was written,
        and the file on disk matches too."""
        content = "version=0.3.0\nsha=deadbeef\ndeployed_at=2026-09-27T00:00:00Z\ngit_status=clean\n"

        result = _run_bash(f'jeedom2ha_write_version_file_atomic "{tmp_path}" "{content}"')

        assert result.returncode == 0, result.stderr
        assert result.stdout == content
        assert (tmp_path / "VERSION").read_text() == content

    def test_leaves_no_temp_file_behind(self, tmp_path):
        """After the atomic write, no VERSION.tmp.* file must remain
        (the mv is the last step, no intermediate state is ever left)."""
        _run_bash(f'jeedom2ha_write_version_file_atomic "{tmp_path}" "hello"')

        assert list(tmp_path.glob("VERSION.tmp.*")) == []
        assert (tmp_path / "VERSION").exists()

    def test_overwrites_existing_version_file_fully(self, tmp_path):
        """Given a pre-existing VERSION file with different content,
        When rewritten,
        Then the old content is fully replaced, not appended."""
        (tmp_path / "VERSION").write_text("stale-content-that-must-disappear")

        result = _run_bash(f'jeedom2ha_write_version_file_atomic "{tmp_path}" "fresh-content"')

        assert result.stdout == "fresh-content"
        assert (tmp_path / "VERSION").read_text() == "fresh-content"

    def test_library_never_references_ssh_or_scp(self):
        """The library must be host-agnostic (no ssh/scp call inside it) —
        this is precisely what makes it safe and meaningful to test here,
        on local temp directories, without ever connecting to the real
        Jeedom box at 192.168.1.21. Comments are allowed to mention
        ssh/scp (to explain how deploy-to-box.sh uses this file); only
        actual code lines are checked."""
        code_lines = [
            line for line in LIB.read_text().splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]

        assert not any("ssh" in line for line in code_lines)
        assert not any("scp" in line for line in code_lines)
