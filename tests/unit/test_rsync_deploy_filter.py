"""
test_rsync_deploy_filter.py — Point 4a : garde CI de non-fuite du filtre
rsync utilisé par scripts/deploy-to-box.sh.

Exécute un `rsync --dry-run` réel (racine du repo → dossier temporaire) avec
le même filtre (.rsync-plugin-deploy.filter, "merge") que le déploiement
réel, et échoue si l'un des chemins interdits (dev-only, jamais destinés à
la box Jeedom) apparaîtrait dans le transfert.

Rejouer :
    pytest tests/unit/test_rsync_deploy_filter.py -v
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FILTER_FILE = REPO_ROOT / ".rsync-plugin-deploy.filter"

# Chemins interdits sur la box : fichier/dossier .git, suites de tests,
# artefacts BMAD, venv, egg-info, node_modules, secrets .env*, docs, CI,
# scripts de dev. Doit correspondre à la liste du mandat (point 4a).
_FORBIDDEN_PREFIXES = (
    "tests/",
    "_bmad",
    ".venv",
    "node_modules",
    ".env",
    "docs/",
    ".github/",
    "scripts/",
)
_FORBIDDEN_SUFFIXES = (".egg-info",)
_FORBIDDEN_EXACT_BASENAMES = (".git",)

# Lignes de sortie rsync qui ne sont jamais des chemins transférés.
_NON_PATH_PREFIXES = (
    "sending incremental file list",
    "sent ",
    "total size is",
    "building file list",
)


def _is_forbidden(rel_path: str) -> bool:
    name = rel_path.rstrip("/")
    if not name or name == ".":
        return False
    base = name.split("/")[0]
    if base in _FORBIDDEN_EXACT_BASENAMES:
        return True
    if any(name.startswith(p) or base.startswith(p) for p in _FORBIDDEN_PREFIXES):
        return True
    if any(name.endswith(s) or base.endswith(s) for s in _FORBIDDEN_SUFFIXES):
        return True
    return False


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")
def test_dry_run_never_transfers_forbidden_dev_only_paths():
    """Given the real deploy rsync filter (.rsync-plugin-deploy.filter),
    When dry-running a transfer from the repo root to an empty target,
    Then no dev-only path (.git, tests/, _bmad*, .venv, *.egg-info,
    node_modules, .env*, docs/, .github/, scripts/) must be listed."""
    assert FILTER_FILE.is_file(), f"missing filter file: {FILTER_FILE}"

    with tempfile.TemporaryDirectory() as tmp:
        result = subprocess.run(
            [
                "rsync", "-avz", "--dry-run", "--delete", "--delete-excluded",
                f"--filter=merge {FILTER_FILE}",
                f"{REPO_ROOT}/", f"{tmp}/",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    transferred = [
        line for line in result.stdout.splitlines()
        if line and not line.startswith(_NON_PATH_PREFIXES)
    ]
    leaked = [line for line in transferred if _is_forbidden(line)]

    assert leaked == [], (
        "rsync dry-run would transfer forbidden dev-only path(s) to the box: "
        f"{leaked}\nFull output:\n{result.stdout}"
    )
