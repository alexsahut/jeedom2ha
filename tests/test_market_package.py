"""Story A2 — paquet Market épuré : script de build, manifeste, branche release à blanc."""
import filecmp
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
MP_DIR = REPO / ".github" / "market-package"
SCRIPT = REPO / "scripts" / "build-market-package.sh"
sys.path.insert(0, str(MP_DIR))
import market_package as mp  # noqa: E402

ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, env=ENV,
                          capture_output=True, text=True).stdout.strip()


def sh(*args, repo=None, check=True):
    env = dict(ENV)
    if repo:
        env["MARKET_PACKAGE_REPO"] = str(repo)
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True,
                          text=True, check=check)


def write(root, rel, content="x\n"):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


@pytest.fixture
def fixture_repo(tmp_path):
    """Dépôt jouet : main (arbre complet + fichiers 'retain') et une branche beta ancienne."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    write(repo, "OLD_ONLY.txt", "présent seulement sur beta\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "beta initial")
    git(repo, "branch", "beta")
    git(repo, "rm", "-q", "OLD_ONLY.txt")
    for rel in ["plugin_info/info.json", "plugin_info/install.php", "core/php/a.php",
                "desktop/js/a.js", "resources/daemon/main.py", "resources/daemon/tests/t.py",
                "docs/fr_FR/changelog.md", "docs/fr_FR/changelog_beta.md", "docs/fr_FR/index.md",
                "docs/git-strategy.md", "docs/ci.md", "docs/index.md", ".github/ci.yml",
                ".claude/x.md", ".agent/x.md", ".agents/x.md", "_bmad/x.md", "_bmad-output/x.md",
                "tests/test_a.py", "scripts/s.sh", ".env", ".env.local", "README.md", "CLAUDE.md",
                ".gitignore", ".rsync-plugin-deploy.filter", "LICENSE", "Makefile",
                "3rdparty/README.md", "a/__pycache__/x.pyc"]:
        write(repo, rel)
    for rel in mp.load_manifest()["retain"]:
        write(repo, rel, "retain\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "main")
    return repo


def test_manifest_loads_and_keeps_docs_fr_fr():
    m = mp.load_manifest()
    assert mp.is_included(m["rules"], "docs/fr_FR/changelog.md")
    assert not mp.is_included(m["rules"], "docs/git-strategy.md")


DEV_FILES = ["CLAUDE.md", ".gitignore", ".rsync-plugin-deploy.filter"]


def test_exclusions_aligned_with_deploy_filter():
    """Le manifeste exclut tout ce qu'exclut le filtre de déploiement, plus les seuls fichiers de dev."""
    deploy = [ln.strip()[2:] for ln in (REPO / ".rsync-plugin-deploy.filter").read_text().splitlines()
              if ln.startswith("- ")]
    mine = [p for k, p in mp.load_manifest()["rules"] if k == "exclude"]
    assert sorted(set(mine) - set(deploy)) == sorted(DEV_FILES)
    assert set(deploy) - set(mine) == set()


def test_dev_files_forbidden_in_manifest():
    m = mp.load_manifest()
    for name in DEV_FILES:
        assert name in m["forbid"], name


def test_real_repo_package_has_no_dev_files(tmp_path):
    """Paquet construit sur le vrai dépôt (HEAD) : aucun fichier de dev ne doit réapparaître."""
    out = tmp_path / "pkg"
    sh("build", "HEAD", "--output", str(out))
    for name in DEV_FILES:
        assert not (out / name).exists(), name
    assert (out / "docs/fr_FR/index.md").exists()


def test_ac1_ac3_build_matches_filtered_source(fixture_repo, tmp_path):
    sha = git(fixture_repo, "rev-parse", "main")
    out = tmp_path / "pkg"
    sh("build", sha, "--output", str(out), repo=fixture_repo)
    # arbre de référence : le SHA source extrait puis filtré indépendamment (cat-file)
    expected = set()
    for rel in git(fixture_repo, "ls-tree", "-r", "--name-only", sha).splitlines():
        if mp.is_included(mp.load_manifest()["rules"], rel):
            expected.add(rel)
    assert set(mp.list_files(str(out))) == expected
    assert "docs/fr_FR/index.md" in expected
    for forbidden in [".github/ci.yml", ".claude/x.md", ".agent/x.md", ".agents/x.md",
                      "_bmad/x.md", "tests/test_a.py", "scripts/s.sh", "docs/git-strategy.md",
                      "CLAUDE.md", ".gitignore", ".rsync-plugin-deploy.filter",
                      "resources/daemon/tests/t.py", ".env", "README.md"]:
        assert not (out / forbidden).exists(), forbidden
    for rel in expected:  # contenu identique à celui du SHA source
        assert (out / rel).read_text() == git(fixture_repo, "show", f"{sha}:{rel}") + "\n"


def test_build_is_deterministic(fixture_repo, tmp_path):
    sha = git(fixture_repo, "rev-parse", "main")
    for name in ("a", "b"):
        sh("build", sha, "--output", str(tmp_path / name), "--tarball", str(tmp_path / f"{name}.tgz"),
           repo=fixture_repo)
    assert (tmp_path / "a.tgz").read_bytes() == (tmp_path / "b.tgz").read_bytes()
    cmp = filecmp.dircmp(tmp_path / "a", tmp_path / "b")
    assert not cmp.diff_files and not cmp.left_only and not cmp.right_only


def test_ac2_check_rejects_regressions(fixture_repo, tmp_path):
    sha = git(fixture_repo, "rev-parse", "main")
    out = tmp_path / "pkg"
    sh("build", sha, "--output", str(out), repo=fixture_repo)
    assert mp.check(str(out)) == []
    # fichier interdit présent
    write(out, ".github/workflows/x.yml")
    write(out, "tests/t.py")
    assert any(".github/workflows/x.yml" in v for v in mp.check(str(out)))
    # fichier requis absent
    (out / "docs/fr_FR/index.md").unlink()
    assert any("docs/fr_FR/index.md" in v for v in mp.check(str(out)))


def test_ac2_check_catches_manifest_rule_regression(fixture_repo, tmp_path):
    """Retirer une exclusion du manifeste est détecté par les garde-fous forbid figés."""
    weak = tmp_path / "weak.txt"
    lines = Path(mp.MANIFEST).read_text().splitlines(keepends=True)
    weak.write_text("".join(ln for ln in lines if ln.strip() != "exclude tests/"))
    manifest = mp.load_manifest(str(weak))
    sha = git(fixture_repo, "rev-parse", "main")
    out = tmp_path / "pkg"
    mp.build(sha, str(out), repo=str(fixture_repo), manifest=manifest)
    assert (out / "tests/test_a.py").exists()
    assert any("tests/" in v for v in mp.check(str(out), manifest=manifest))


def test_check_cli_exit_codes(tmp_path):
    write(tmp_path, "tests/t.py")
    r = subprocess.run([sys.executable, str(MP_DIR / "market_package.py"), "check", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "VIOLATION" in r.stderr


def test_ac4_release_branch_dry_run(fixture_repo):
    sha = git(fixture_repo, "rev-parse", "main")
    beta_before = git(fixture_repo, "rev-parse", "beta")
    r = sh("release", "v1.2.3", "--source", sha, "--base-ref", "beta", "--allow-untagged",
           repo=fixture_repo)
    assert "Aucun push effectué" in r.stdout
    assert git(fixture_repo, "log", "-1", "--format=%s", "release/v1.2.3") == f"release v1.2.3 (source {sha})"
    assert git(fixture_repo, "rev-parse", "release/v1.2.3~1") == beta_before  # créée depuis beta
    assert git(fixture_repo, "rev-parse", "beta") == beta_before  # beta intacte
    files = set(git(fixture_repo, "ls-tree", "-r", "--name-only", "release/v1.2.3").splitlines())
    assert "OLD_ONLY.txt" not in files and "docs/fr_FR/index.md" in files
    assert ".github/workflows/market-package-check.yml" in files
    assert ".github/ci.yml" not in files and "tests/test_a.py" not in files
    # aucune ref distante créée, aucun worktree résiduel
    assert git(fixture_repo, "remote") == ""
    assert git(fixture_repo, "worktree", "list").count("\n") == 0


def test_release_requires_deploy_tag_and_valid_version(fixture_repo):
    sha = git(fixture_repo, "rev-parse", "main")
    bad = sh("release", "v1.2.3", "--source", sha, "--base-ref", "beta", repo=fixture_repo, check=False)
    assert bad.returncode != 0 and "deploy-" in bad.stderr
    assert "release/v1.2.3" not in git(fixture_repo, "branch", "--list")
    bad = sh("release", "1.2", "--source", sha, "--base-ref", "beta", "--allow-untagged",
             repo=fixture_repo, check=False)
    assert bad.returncode != 0
    git(fixture_repo, "tag", "deploy-20261012-000000-abc1234", sha)
    sh("release", "v1.2.3", "--source", sha, "--base-ref", "beta", repo=fixture_repo)


def test_release_refuses_protected_branch_names(fixture_repo):
    sha = git(fixture_repo, "rev-parse", "main")
    r = sh("release", "v1.2.3", "--source", sha, "--base-ref", "beta", "--branch", "beta",
           "--allow-untagged", repo=fixture_repo, check=False)
    assert r.returncode != 0


def test_script_never_pushes():
    """Un `git push` n'apparaît que dans le texte d'aide affiché (heredoc final), jamais exécuté."""
    text = SCRIPT.read_text()
    executable = text.split("cat <<MSG")[0]
    assert "push" not in "\n".join(ln for ln in executable.splitlines() if not ln.lstrip().startswith("#"))


def test_check_ignores_git_metadata_of_a_checkout(fixture_repo, tmp_path):
    sha = git(fixture_repo, "rev-parse", "main")
    out = tmp_path / "tree"
    mp.build(sha, str(out), repo=str(fixture_repo), with_retained=True)
    write(out, ".git/HEAD", "ref: refs/heads/beta\n")
    assert mp.check(str(out), release_tree=True) == []


def test_release_pr_target_follows_base_ref(fixture_repo):
    sha = git(fixture_repo, "rev-parse", "main")
    git(fixture_repo, "branch", "stable", "beta")
    r = sh("release", "v1.2.3", "--source", sha, "--base-ref", "stable", "--allow-untagged",
           repo=fixture_repo)
    assert "--base stable --head release/v1.2.3" in r.stdout
    assert "--base beta" not in r.stdout
