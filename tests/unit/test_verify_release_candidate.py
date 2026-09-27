"""
test_verify_release_candidate.py — preuve unitaire, SANS SSH ni box réelle,
que scripts/verify-release-candidate.sh déréférence bien un tag annoté vers
le COMMIT qu'il pointe (jamais l'objet tag lui-même — bug documenté dans
docs/release-market.md §6 : `git rev-parse v1.1.0` rend l'objet tag
`e1325f0...`, pas le commit `166cb7b...`), et que la comparaison candidat
<-> box repose sur un contenu VERSION déjà lu (simulé/fixture), jamais sur un
vrai appel ssh.

Rejouer :
    pytest tests/unit/test_verify_release_candidate.py -v
"""
import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "scripts" / "verify-release-candidate-lib.sh"
SCRIPT = REPO_ROOT / "scripts" / "verify-release-candidate.sh"


def _run_bash(snippet: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", f"set -euo pipefail; source '{LIB}'; {snippet}"],
        capture_output=True,
        text=True,
    )


def _git(*args, cwd, check=True):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=check)


def _make_repo_with_one_commit(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "file.txt").write_text("v1")
    _git("add", "file.txt", cwd=repo)
    _git("commit", "-q", "-m", "candidate", cwd=repo)
    return repo


class TestTagCommitShaDereferencesAnnotatedTags:
    """Point 1 — bug historique : `git rev-parse <tag>` seul rend l'objet tag
    (annoté), pas le commit pointé. `jeedom2ha_tag_commit_sha` doit toujours
    rendre le commit."""

    def test_annotated_tag_dereferences_to_the_commit_it_points_to(self, tmp_path):
        repo = _make_repo_with_one_commit(tmp_path)
        candidate_sha = _git("rev-parse", "HEAD", cwd=repo).stdout.strip()
        _git("tag", "-a", "v1.0.0", "-m", "release", cwd=repo)
        raw_tag_object_sha = _git("rev-parse", "v1.0.0", cwd=repo).stdout.strip()

        result = _run_bash(f"jeedom2ha_tag_commit_sha '{repo}' v1.0.0")

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == candidate_sha
        # Preuve que le bug existe bien pour ce type de tag : l'objet tag brut
        # a un SHA différent du commit, sans quoi ce test ne prouverait rien.
        assert raw_tag_object_sha != candidate_sha
        assert result.stdout.strip() != raw_tag_object_sha


class TestCheckTagMatchesCandidate:
    def test_annotated_tag_pointing_at_candidate_succeeds(self, tmp_path):
        """Cas conforme : le tag annoté pointe exactement sur le candidat."""
        repo = _make_repo_with_one_commit(tmp_path)
        candidate_sha = _git("rev-parse", "HEAD", cwd=repo).stdout.strip()
        _git("tag", "-a", "v1.0.0", "-m", "release", cwd=repo)

        result = _run_bash(
            f"jeedom2ha_check_tag_matches_candidate '{repo}' {candidate_sha} v1.0.0"
        )

        assert result.returncode == 0, result.stderr
        assert "[OK]" in result.stdout

    def test_annotated_tag_pointing_elsewhere_fails_for_the_right_reason(self, tmp_path):
        """Cas d'échec : le tag existe mais pointe sur un autre commit que le
        candidat — doit échouer à cause du SHA différent, pas à cause du bug
        d'objet tag (déjà couvert et corrigé par jeedom2ha_tag_commit_sha)."""
        repo = _make_repo_with_one_commit(tmp_path)
        first_commit_sha = _git("rev-parse", "HEAD", cwd=repo).stdout.strip()
        _git("tag", "-a", "v1.0.0", "-m", "release", cwd=repo)
        (repo / "file.txt").write_text("v2")
        _git("commit", "-aqm", "second", cwd=repo)
        candidate_sha = _git("rev-parse", "HEAD", cwd=repo).stdout.strip()
        assert candidate_sha != first_commit_sha

        result = _run_bash(
            f"jeedom2ha_check_tag_matches_candidate '{repo}' {candidate_sha} v1.0.0"
        )

        assert result.returncode == 1
        assert "[ECHEC]" in result.stderr
        assert first_commit_sha in result.stderr
        assert candidate_sha in result.stderr

    def test_missing_tag_is_informational_not_a_failure(self, tmp_path):
        repo = _make_repo_with_one_commit(tmp_path)
        candidate_sha = _git("rev-parse", "HEAD", cwd=repo).stdout.strip()

        result = _run_bash(
            f"jeedom2ha_check_tag_matches_candidate '{repo}' {candidate_sha} v9.9.9"
        )

        assert result.returncode == 0, result.stderr
        assert "[INFO]" in result.stdout


class TestCheckBoxShaMatchesCandidate:
    """La lecture de la box est SIMULÉE : ces tests passent directement le
    contenu VERSION comme une fixture, jamais un vrai appel ssh."""

    def test_matching_sha_succeeds(self):
        content = "version=0.3.0\nsha=deadbeef\ndeployed_at=2026-09-27T00:00:00Z\ngit_status=clean\n"

        result = _run_bash(f"jeedom2ha_check_box_sha_matches_candidate deadbeef '{content}'")

        assert result.returncode == 0, result.stderr
        assert "[OK]" in result.stdout

    def test_different_sha_fails(self):
        content = "version=0.3.0\nsha=deadbeef\ndeployed_at=2026-09-27T00:00:00Z\ngit_status=clean\n"

        result = _run_bash(f"jeedom2ha_check_box_sha_matches_candidate cafebabe '{content}'")

        assert result.returncode == 1
        assert "[ECHEC]" in result.stderr

    def test_empty_version_content_fails(self):
        """Simule un VERSION illisible/absent sur la box (sortie ssh+cat
        vide), sans jamais faire de vrai appel ssh."""
        result = _run_bash("jeedom2ha_check_box_sha_matches_candidate deadbeef ''")

        assert result.returncode == 1
        assert "impossible de lire VERSION" in result.stderr

    def test_dirty_git_status_fails_even_with_matching_sha(self):
        """Un déploiement fait depuis un arbre de travail sale peut committer
        le bon SHA dans VERSION tout en ayant déployé un contenu différent de
        ce commit (fichiers modifiés non commités déployés par-dessus) : doit
        échouer même si le SHA correspond exactement."""
        content = "version=0.3.0\nsha=deadbeef\ndeployed_at=2026-09-27T00:00:00Z\ngit_status=dirty\n"

        result = _run_bash(f"jeedom2ha_check_box_sha_matches_candidate deadbeef '{content}'")

        assert result.returncode == 1
        assert "[ECHEC]" in result.stderr
        assert "git_status=dirty" in result.stderr

    def test_missing_git_status_field_fails(self):
        """VERSION sans champ git_status (format inattendu ou ancien) : ne
        doit jamais être traité silencieusement comme propre."""
        content = "version=0.3.0\nsha=deadbeef\ndeployed_at=2026-09-27T00:00:00Z\n"

        result = _run_bash(f"jeedom2ha_check_box_sha_matches_candidate deadbeef '{content}'")

        assert result.returncode == 1
        assert "[ECHEC]" in result.stderr
        assert "git_status" in result.stderr


def test_library_never_references_ssh_or_scp():
    """Host-agnostic par construction : c'est ce qui rend les tests ci-dessus
    valides sans jamais se connecter à la box réelle (192.168.1.21)."""
    code_lines = [
        line for line in LIB.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    assert not any("ssh" in line for line in code_lines)
    assert not any("scp" in line for line in code_lines)


class TestFullScriptWiringWithMockedSsh:
    """Vérifie le câblage complet du script (candidat réel de ce repo, tag
    résolu via git, lecture VERSION) avec un binaire `ssh` MOCKÉ placé en
    tête de PATH — jamais de connexion réseau réelle."""

    def _write_mock_ssh(self, bin_dir: Path, content: str) -> None:
        bin_dir.mkdir(exist_ok=True)
        ssh_stub = bin_dir / "ssh"
        ssh_stub.write_text(f"#!/bin/sh\nprintf '%s' '{content}'\n")
        ssh_stub.chmod(0o755)

    def test_succeeds_when_mocked_box_reports_the_candidate_sha(self, tmp_path):
        head_sha = _git("rev-parse", "HEAD", cwd=REPO_ROOT).stdout.strip()
        info_json = _git("show", "HEAD:plugin_info/info.json", cwd=REPO_ROOT).stdout
        plugin_version = json.loads(info_json)["pluginVersion"]
        content = (
            f"version={plugin_version}\nsha={head_sha}\n"
            "deployed_at=2026-09-27T00:00:00Z\ngit_status=clean\n"
        )
        bin_dir = tmp_path / "bin"
        self._write_mock_ssh(bin_dir, content)
        env = os.environ | {
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "JEEDOM_BOX_HOST": "mock-box",
        }

        result = subprocess.run(
            [str(SCRIPT), "HEAD"], env=env, capture_output=True, text=True, cwd=REPO_ROOT
        )

        assert result.returncode == 0, result.stderr
        assert "candidat strictement identique" in result.stdout

    def test_fails_when_mocked_box_reports_a_different_sha(self, tmp_path):
        bin_dir = tmp_path / "bin"
        self._write_mock_ssh(
            bin_dir,
            "version=0.0.1\nsha=0000000000000000000000000000000000000000\n"
            "deployed_at=2026-09-27T00:00:00Z\ngit_status=clean\n",
        )
        env = os.environ | {
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "JEEDOM_BOX_HOST": "mock-box",
        }

        result = subprocess.run(
            [str(SCRIPT), "HEAD"], env=env, capture_output=True, text=True, cwd=REPO_ROOT
        )

        assert result.returncode == 1
        assert "différent du SHA déployé sur la box" in result.stderr

    def test_requires_jeedom_box_host(self, tmp_path):
        env = {k: v for k, v in os.environ.items() if k != "JEEDOM_BOX_HOST"}

        result = subprocess.run(
            [str(SCRIPT), "HEAD"], env=env, capture_output=True, text=True, cwd=REPO_ROOT
        )

        assert result.returncode == 1
        assert "JEEDOM_BOX_HOST is not set" in result.stderr
