"""
test_deploy_preserve_python_venv.py — l'étape 1b de scripts/deploy-to-box.sh
(promotion staging → dossier du plugin) ne doit jamais effacer ni dégrader
`resources/python_venv/`.

Ce venv n'appartient pas au dépôt : c'est le cœur Jeedom (gestion des
dépendances, section `pip3` de plugin_info/packages.json) qui le crée dans le
dossier du plugin, et `system::getCmdPython3('jeedom2ha')` renvoie son
interpréteur à `jeedom2ha::deamon_start()`. Constaté sur la VM de démo
(Jeedom 4.6.1, Debian 12) : après `deploy-to-box.sh --restart-daemon`, le
`rsync -a --delete` de l'étape 1b supprimait le venv (absent du staging) et le
démon ne démarrait plus (`sh: 1: …/resources/python_venv/bin/python3: not found`).

Le bloc distant de l'étape 1b est extrait tel quel du script (pas une copie
réécrite à la main), puis exécuté localement contre une arborescence
fictive ; seul `sudo` est remplacé (passe-plat, sans le chown www-data).

Rejouer :
    pytest tests/unit/test_deploy_preserve_python_venv.py -v
"""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "deploy-to-box.sh"

_STEP_1B_HEADER = 'echo "  1b. sudo promote → ${JEEDOM_BOX_PATH}/"'

# `sudo` passe-plat ; le chown vers www-data est neutralisé (l'utilisateur
# n'existe pas forcément sur l'hôte de test et n'est pas l'objet du test).
_SUDO_STUB = '''
sudo() {
  if [ "$1" = "chown" ]; then return 0; fi
  "$@"
}
'''


def _extract_step_1b_remote_body() -> str:
    """Corps exact du heredoc distant de l'étape 1b (entre `bash <<REMOTE`
    et `REMOTE`), extrait de deploy-to-box.sh."""
    text = SCRIPT.read_text()
    start = text.index(_STEP_1B_HEADER)
    heredoc_open = text.index("bash <<REMOTE\n", start) + len("bash <<REMOTE\n")
    heredoc_close = text.index("\nREMOTE\n", heredoc_open)
    return text[heredoc_open:heredoc_close]


def _make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _build_tree(tmp_path: Path) -> "tuple[Path, Path]":
    staging = tmp_path / "staging"
    (staging / "resources" / "daemon").mkdir(parents=True)
    (staging / "resources" / "daemon" / "main.py").write_text("# daemon\n")
    (staging / "plugin_info").mkdir()
    (staging / "plugin_info" / "packages.json").write_text("{}\n")

    plugin = tmp_path / "plugins" / "jeedom2ha"
    venv_bin = plugin / "resources" / "python_venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python3").write_text("#!/bin/sh\n")
    _make_executable(venv_bin / "python3")
    (venv_bin / "pip3").write_text("#!/bin/sh\n")
    _make_executable(venv_bin / "pip3")
    (plugin / "resources" / "python_venv" / "pyvenv.cfg").write_text("home = /usr/bin\n")
    (plugin / "resources" / "daemon").mkdir(parents=True)
    (plugin / "resources" / "daemon" / "obsolete.py").write_text("# retiré du dépôt\n")
    (plugin / "data").mkdir()
    (plugin / "data" / "runtime.json").write_text("{}\n")
    return staging, plugin


def _run_step_1b(tmp_path: Path, staging: Path, plugin: Path) -> subprocess.CompletedProcess:
    body = _extract_step_1b_remote_body()
    # Le heredoc est non quoté : ${JEEDOM_STAGING_DIR} et ${JEEDOM_BOX_PATH}
    # sont développés côté poste ; on les fournit ici comme variables shell.
    script = (
        "set -euo pipefail\n"
        f"{_SUDO_STUB}\n"
        f'JEEDOM_STAGING_DIR="{staging}"\n'
        f'JEEDOM_BOX_PATH="{plugin}"\n'
        f"{body}\n"
    )
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True)


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")
def test_step_1b_preserves_core_managed_python_venv(tmp_path):
    staging, plugin = _build_tree(tmp_path)

    result = _run_step_1b(tmp_path, staging, plugin)

    assert result.returncode == 0, result.stderr
    venv_python = plugin / "resources" / "python_venv" / "bin" / "python3"
    assert venv_python.is_file(), "l'étape 1b a supprimé resources/python_venv/ (démon non démarrable)"
    assert (plugin / "resources" / "python_venv" / "pyvenv.cfg").is_file()


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")
def test_step_1b_keeps_python_venv_executables_executable(tmp_path):
    # Le chmod 644 récursif de l'étape 1b ne doit pas retirer le bit x des
    # exécutables du venv (interpréteur copié, pip3, scripts console).
    staging, plugin = _build_tree(tmp_path)

    result = _run_step_1b(tmp_path, staging, plugin)

    assert result.returncode == 0, result.stderr
    venv_bin = plugin / "resources" / "python_venv" / "bin"
    for name in ("python3", "pip3"):
        assert os.access(venv_bin / name, os.X_OK), f"{name} du venv n'est plus exécutable après l'étape 1b"


@pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")
def test_step_1b_still_mirrors_staging_and_keeps_data(tmp_path):
    # Non-régression : l'exclusion du venv ne doit pas désactiver le --delete
    # pour le reste du plugin, ni toucher à data/.
    staging, plugin = _build_tree(tmp_path)

    result = _run_step_1b(tmp_path, staging, plugin)

    assert result.returncode == 0, result.stderr
    assert not (plugin / "resources" / "daemon" / "obsolete.py").exists()
    assert (plugin / "resources" / "daemon" / "main.py").is_file()
    assert os.access(plugin / "resources" / "daemon" / "main.py", os.X_OK)
    assert (plugin / "plugin_info" / "packages.json").is_file()
    assert (plugin / "data" / "runtime.json").is_file()
