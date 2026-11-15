"""
test_deploy_promote_lib.py — incident du 15/11/2026 : pendant l'étape 1b de
scripts/deploy-to-box.sh (promotion staging → plugins/jeedom2ha), le cœur
Jeedom a journalisé « Fichier introuvable : …/core/class/jeedom2ha.class.php »
puis « Plugin introuvable : jeedom2ha », et plugin::byId() →
forceDisablePlugin() a mis le plugin à active=0. Le déploiement a rendu rc 0.

Ce fichier prouve, SANS SSH ni box réelle, la logique de
scripts/deploy-promote-lib.sh (sourcée ici en local, envoyée telle quelle à la
box par deploy-to-box.sh) :
  - le dossier vu par Jeedom n'est jamais incomplet ni fermé à « others »
    pendant la promotion (observateur qui sonde l'arborescence en continu),
    et le même observateur détecte bien l'ancienne promotion en place ;
  - data/ et resources/python_venv/ sont conservés (mêmes inodes) ;
  - repli rsync --delay-updates quand l'échange atomique est indisponible ;
  - un arbre préparé incomplet n'est jamais basculé ;
  - le contrôle après promotion (PHP sous l'utilisateur web, autoload, journal
    plugin) échoue avec un message clair et ne réactive jamais le plugin.

`sudo` est stubbé : `-u <user>` exécute sous l'utilisateur courant et `chown`
est neutralisé (pas de compte www-data sur l'hôte de test). Comme le processus
de test peut tourner en root (conteneurs CI) et contourner les permissions,
l'observateur vérifie les BITS de mode « others » (ce que verrait www-data,
qui n'est ni propriétaire ni dans le groupe du compte SSH), pas os.access().

Rejouer :
    pytest tests/unit/test_deploy_promote_lib.py -v
"""
import os
import shutil
import stat
import subprocess
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "scripts" / "deploy-promote-lib.sh"
SCRIPT = REPO_ROOT / "scripts" / "deploy-to-box.sh"

pytestmark = pytest.mark.skipif(shutil.which("rsync") is None, reason="rsync not installed")

# chown est neutralisé mais ralenti : c'est la fenêtre entre la copie et la
# remise des droits qui a déclenché l'incident ; on l'élargit pour que
# l'observateur la voie à coup sûr si elle est visible de Jeedom.
_SUDO_STUB = '''
sudo() {
  if [ "$1" = "-u" ]; then shift 2; fi
  if [ "$1" = "chown" ]; then sleep 0.4; return 0; fi
  "$@"
}
'''

# Ancienne étape 1b (avant correctif), à l'identique de deploy-to-box.sh au
# commit 40e1421 : sert à prouver que l'observateur détecte bien le défaut.
_PRE_FIX_STEP_1B = '''
sudo mkdir -p "${JEEDOM_BOX_PATH}"
sudo rsync -a --delete --exclude 'data/' --exclude '/resources/python_venv/' "${JEEDOM_STAGING_DIR}/" "${JEEDOM_BOX_PATH}/"
sudo chown -R www-data:www-data "${JEEDOM_BOX_PATH}"
sudo find "${JEEDOM_BOX_PATH}" -path "${JEEDOM_BOX_PATH}/resources/python_venv" -prune -o -type d -exec chmod 755 {} \\;
sudo find "${JEEDOM_BOX_PATH}" -path "${JEEDOM_BOX_PATH}/resources/python_venv" -prune -o -type f -exec chmod 644 {} \\;
sudo chmod +x "${JEEDOM_BOX_PATH}/resources/daemon/main.py"
'''

_WATCHED = ("core/class/jeedom2ha.class.php", "plugin_info/info.json")


def _bash(script: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", f"set -euo pipefail\n{_SUDO_STUB}\nsource '{LIB}'\n{script}", "bash", *args],
        capture_output=True,
        text=True,
    )


def _write(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(mode)


def _build(tmp_path: Path, staging_dir_mode: int = 0o700, staging_file_mode: int = 0o600):
    """Staging aux modes restrictifs (cas de l'incident : propriétaire et modes
    venus du poste de déploiement) et plugin en place sain (www-data, 755/644)."""
    staging = tmp_path / "staging"
    _write(staging / "core" / "class" / "jeedom2ha.class.php", "<?php // v2\n", staging_file_mode)
    _write(staging / "core" / "ajax" / "jeedom2ha.ajax.php", "<?php\n", staging_file_mode)
    _write(staging / "plugin_info" / "info.json", '{"id": "jeedom2ha", "v": 2}\n', staging_file_mode)
    _write(staging / "resources" / "daemon" / "main.py", "# daemon v2\n", staging_file_mode)
    _write(staging / "resources" / "daemon" / "new_module.py", "# new\n", staging_file_mode)
    for d in [staging, *[p for p in staging.rglob("*") if p.is_dir()]]:
        d.chmod(staging_dir_mode)

    plugins = tmp_path / "plugins"
    live = plugins / "jeedom2ha"
    _write(live / "core" / "class" / "jeedom2ha.class.php", "<?php // v1\n", 0o644)
    _write(live / "plugin_info" / "info.json", '{"id": "jeedom2ha", "v": 1}\n', 0o644)
    _write(live / "resources" / "daemon" / "main.py", "# daemon v1\n", 0o755)
    _write(live / "resources" / "daemon" / "obsolete.py", "# retiré\n", 0o644)
    _write(live / "data" / "overrides.json", '{"user": "config"}\n', 0o644)
    _write(live / "resources" / "python_venv" / "bin" / "python3", "#!/bin/sh\n", 0o755)
    _write(live / "resources" / "python_venv" / "pyvenv.cfg", "home = /usr/bin\n", 0o644)
    for d in [p for p in live.rglob("*") if p.is_dir()] + [live]:
        d.chmod(0o755)
    return staging, live


def _visible_to_others(live: Path, rel: str) -> "str | None":
    """None si <live>/<rel> est atteignable et lisible par un utilisateur
    « others » (www-data) ; sinon la raison."""
    cur = live
    try:
        if not stat.S_ISDIR(cur.lstat().st_mode) or (cur.stat().st_mode & 0o005) != 0o005:
            return f"{cur} fermé (mode {oct(cur.stat().st_mode & 0o777)})"
        for part in Path(rel).parts[:-1]:
            cur = cur / part
            m = cur.stat().st_mode
            if (m & 0o005) != 0o005:
                return f"{cur} non traversable (mode {oct(m & 0o777)})"
        f = live / rel
        if (f.stat().st_mode & 0o004) == 0:
            return f"{f} illisible (mode {oct(f.stat().st_mode & 0o777)})"
    except FileNotFoundError as exc:
        return f"absent : {exc.filename}"
    return None


class _Watcher(threading.Thread):
    def __init__(self, live: Path):
        super().__init__(daemon=True)
        self.live = live
        self.problems: "list[str]" = []
        self.samples = 0
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.is_set():
            for rel in _WATCHED:
                problem = _visible_to_others(self.live, rel)
                if problem:
                    self.problems.append(problem)
            self.samples += 1
            time.sleep(0.002)

    def stop(self):
        self._stop_event.set()
        self.join()


def _watched_run(live: Path, script: str, *args: str) -> "tuple[subprocess.CompletedProcess, _Watcher]":
    watcher = _Watcher(live)
    watcher.start()
    try:
        result = _bash(script, *args)
    finally:
        watcher.stop()
    return result, watcher


# Démon arrêté par défaut (deploy-to-box.sh l'arrête avant la bascule) ; un
# test peut redéfinir la fonction pour simuler le contraire.
_NO_DAEMON = "jeedom2ha_daemon_running() { return 1; }"


def _promote(staging: Path, live: Path, prelude: str = ""):
    return _watched_run(
        live,
        f'{_NO_DAEMON}\n{prelude}\njeedom2ha_promote_plugin_dir "$1" "$2" www-data:www-data',
        str(staging), str(live),
    )


def _inodes(live: Path) -> dict:
    return {
        "data_dir": (live / "data").stat().st_ino,
        "data_file": (live / "data" / "overrides.json").stat().st_ino,
        "venv_dir": (live / "resources" / "python_venv").stat().st_ino,
    }


def _previous_work(result: subprocess.CompletedProcess) -> Path:
    marks = [line.split("=", 1)[1] for line in result.stdout.splitlines()
             if line.startswith("__JEEDOM2HA_PREVIOUS_WORK__=")]
    assert len(marks) == 1, result.stdout
    return Path(marks[0])


def _assert_promoted(live: Path, inodes: dict):
    assert (live / "core" / "class" / "jeedom2ha.class.php").read_text() == "<?php // v2\n"
    assert (live / "resources" / "daemon" / "new_module.py").is_file()
    assert not (live / "resources" / "daemon" / "obsolete.py").exists()
    # data/ et venv : les MÊMES dossiers (déplacés ou laissés en place, jamais copiés).
    assert (live / "data" / "overrides.json").read_text() == '{"user": "config"}\n'
    assert _inodes(live) == inodes
    assert os.stat(live / "resources" / "python_venv" / "bin" / "python3").st_mode & 0o111
    # Modes Jeedom posés sur le code (data/ et venv : gérés par le démon / le cœur).
    for p in [live, *live.rglob("*")]:
        if "python_venv" in p.parts or "data" in p.relative_to(live).parts:
            continue
        mode = p.stat().st_mode & 0o777
        if p.is_dir():
            assert mode == 0o755, (p, oct(mode))
        elif p.name == "main.py":
            assert mode == 0o755, (p, oct(mode))
        else:
            assert mode == 0o644, (p, oct(mode))


def test_observer_catches_the_pre_fix_promotion(tmp_path):
    # Preuve que le harnais voit bien le défaut de l'incident : l'ancienne
    # étape 1b recopie les modes 700/600 du staging sur le plugin en place
    # avant le chown/chmod de rattrapage.
    staging, live = _build(tmp_path)
    result, watcher = _watched_run(
        live,
        f'JEEDOM_STAGING_DIR="$1"\nJEEDOM_BOX_PATH="$2"\n{_PRE_FIX_STEP_1B}',
        str(staging), str(live),
    )
    assert result.returncode == 0, result.stderr
    assert watcher.problems, "le harnais aurait dû voir le plugin fermé à www-data pendant l'ancienne promotion"


def test_promotion_never_exposes_an_incomplete_or_unreadable_plugin(tmp_path):
    staging, live = _build(tmp_path)
    inodes = _inodes(live)

    result, watcher = _promote(staging, live)

    assert result.returncode == 0, result.stderr
    assert "Bascule atomique" in result.stdout, result.stdout + result.stderr
    assert watcher.samples > 10
    assert watcher.problems == [], watcher.problems[:5]
    _assert_promoted(live, inodes)


def test_promotion_keeps_the_previous_tree_until_retained(tmp_path):
    # L'ancien arbre n'est jamais supprimé par la promotion : il attend le
    # contrôle d'après bascule dans le dossier de travail.
    staging, live = _build(tmp_path)
    result, _ = _promote(staging, live)
    assert result.returncode == 0, result.stderr

    work = _previous_work(result)
    assert work.parent == live.parent and work.name.startswith(".jeedom2ha-deploy.")
    old = work / "jeedom2ha"
    assert (old / "core" / "class" / "jeedom2ha.class.php").read_text() == "<?php // v1\n"
    assert (old / "resources" / "daemon" / "obsolete.py").is_file()
    assert not (old / "data").exists(), "data/ doit avoir été déplacé, pas laissé ni copié"


def test_retain_previous_keeps_exactly_one_generation(tmp_path):
    parent = tmp_path / "plugins"
    _write(parent / "jeedom2ha" / "plugin_info" / "info.json", "{}", 0o644)
    names = []
    for gen in ("A", "B"):
        work = parent / f".jeedom2ha-deploy.{gen}"
        _write(work / "jeedom2ha" / "gen.txt", gen, 0o644)
        result = _bash(
            'jeedom2ha_retain_previous "$1" "$2"\nsleep 1.1', str(work), str(parent))
        assert result.returncode == 0, result.stderr
        assert not work.exists()
        names = sorted(x.name for x in parent.iterdir() if x.name.startswith(".jeedom2ha.prev-"))
        assert len(names) == 1, names
    assert (parent / names[0] / "jeedom2ha" / "gen.txt").read_text() == "B"
    assert (parent / "jeedom2ha" / "plugin_info" / "info.json").is_file()


def test_retain_previous_refuses_unexpected_paths(tmp_path):
    parent = tmp_path / "plugins"
    _write(parent / "jeedom2ha" / "plugin_info" / "info.json", "{}", 0o644)
    result = _bash('jeedom2ha_retain_previous "$1" "$2"', str(parent / "jeedom2ha"), str(parent))
    assert result.returncode != 0
    assert (parent / "jeedom2ha" / "plugin_info" / "info.json").is_file()


def test_write_to_data_right_before_the_switch_is_kept(tmp_path):
    # Écritures du démon/de l'utilisateur dans data/ juste avant la bascule,
    # de la même taille et dans la même seconde que le contenu précédent (le
    # cas où une réconciliation taille/date les perdait) :
    #  - l'une par remplacement atomique (tmp + rename, comme
    #    mapping/overrides.py) au chemin du plugin, juste avant le
    #    déplacement de data/ ;
    #  - l'autre au dossier data/ déjà déplacé, juste avant l'échange
    #    (processus qui aurait gardé le dossier ouvert).
    staging, live = _build(tmp_path)
    data = live / "data"
    (data / "decision.json").write_text("AAAA")
    prelude = r"""
_writes=0
_LIVE="$2"
jeedom2ha_daemon_running() {
  if [ "$_writes" = 0 ]; then
    printf '{"user": "NEWCFG"}\n' > "$_LIVE/data/.ov.tmp"; mv "$_LIVE/data/.ov.tmp" "$_LIVE/data/overrides.json"
    _writes=1
  fi
  return 1
}
eval "$(declare -f jeedom2ha_exchange_dirs | sed '1s/jeedom2ha_exchange_dirs/_real_exchange/')"
jeedom2ha_exchange_dirs() {
  case "$1" in
    */.probe-a) ;;
    *) printf 'BBBB' > "$1/data/.d.tmp"; mv "$1/data/.d.tmp" "$1/data/decision.json" ;;
  esac
  _real_exchange "$@"
}
"""
    result, _ = _promote(staging, live, prelude=prelude)

    assert result.returncode == 0, result.stderr
    assert (live / "data" / "overrides.json").read_text() == '{"user": "NEWCFG"}\n'
    assert (live / "data" / "decision.json").read_text() == "BBBB"


def test_running_daemon_blocks_the_switch_and_moves_nothing(tmp_path):
    staging, live = _build(tmp_path)
    inodes = _inodes(live)
    result, _ = _promote(staging, live, prelude="jeedom2ha_daemon_running() { return 0; }")

    assert result.returncode != 0
    assert "le démon jeedom2ha tourne" in result.stderr
    assert (live / "core" / "class" / "jeedom2ha.class.php").read_text() == "<?php // v1\n"
    assert _inodes(live) == inodes
    assert sorted(x.name for x in live.parent.iterdir()) == ["jeedom2ha"]


def test_data_on_another_filesystem_blocks_the_switch(tmp_path):
    staging, live = _build(tmp_path)
    inodes = _inodes(live)
    prelude = r"""
jeedom2ha_fs_id() { case "$1" in */data) echo 999 ;; *) echo 1 ;; esac; }
"""
    result, _ = _promote(staging, live, prelude=prelude)

    assert result.returncode != 0
    assert "pas sur le même système de fichiers" in result.stderr
    assert _inodes(live) == inodes
    assert (live / "core" / "class" / "jeedom2ha.class.php").read_text() == "<?php // v1\n"


def test_failed_exchange_puts_data_back(tmp_path):
    staging, live = _build(tmp_path)
    inodes = _inodes(live)
    prelude = r"""
eval "$(declare -f jeedom2ha_exchange_dirs | sed '1s/jeedom2ha_exchange_dirs/_real_exchange/')"
jeedom2ha_exchange_dirs() { case "$1" in */.probe-a) _real_exchange "$@" ;; *) return 1 ;; esac; }
"""
    result, watcher = _promote(staging, live, prelude=prelude)

    assert result.returncode != 0
    assert "bascule interrompue" in result.stderr
    assert _inodes(live) == inodes
    assert (live / "core" / "class" / "jeedom2ha.class.php").read_text() == "<?php // v1\n"
    assert watcher.problems == []


# --- Interruptions pendant « déplacement → échange » ---------------------
# Le trap EXIT ne doit plus jamais supprimer le dossier de travail une fois
# data/ déplacé, et une coupure SSH (SIGHUP) ne doit pas interrompre la
# section protégée.

_REAL_EXCHANGE = (
    "eval \"$(declare -f jeedom2ha_exchange_dirs | sed '1s/jeedom2ha_exchange_dirs/_real_exchange/')\"\n"
)


def _after_data_move(action: str) -> str:
    """Prélude qui exécute <action> juste après le déplacement de data/ vers
    l'arbre préparé, avant celui du venv."""
    return r"""
eval "$(declare -f sudo | sed '1s/^sudo/_stub_sudo/')"
sudo() {
  _stub_sudo "$@"
  local rc=$?
  if [ "$1" = mv ] && [[ "$3" == */jeedom2ha/data && "$4" == */.jeedom2ha-deploy.*/jeedom2ha/data ]]; then
    %s
  fi
  return $rc
}
""" % action


def _just_before_exchange(action: str) -> str:
    return _REAL_EXCHANGE + r"""
jeedom2ha_exchange_dirs() {
  case "$1" in */.probe-a) _real_exchange "$@"; return ;; esac
  %s
  _real_exchange "$@"
}
""" % action


def _work_dirs(live: Path) -> "list[Path]":
    return [p for p in live.parent.iterdir() if p.name.startswith(".jeedom2ha-deploy.")]


def test_sighup_just_before_exchange_does_not_interrupt_the_switch(tmp_path):
    staging, live = _build(tmp_path)
    inodes = _inodes(live)
    result, watcher = _promote(staging, live, prelude=_just_before_exchange('kill -HUP "$BASHPID"; kill -TERM "$BASHPID"'))

    assert result.returncode == 0, result.stderr
    assert watcher.problems == []
    _assert_promoted(live, inodes)


def test_sighup_between_data_and_venv_moves_does_not_interrupt_the_switch(tmp_path):
    staging, live = _build(tmp_path)
    inodes = _inodes(live)
    result, _ = _promote(staging, live, prelude=_after_data_move('kill -HUP "$BASHPID"; kill -INT "$BASHPID"'))

    assert result.returncode == 0, result.stderr
    _assert_promoted(live, inodes)


def test_abrupt_exit_just_before_exchange_restores_data_and_venv(tmp_path):
    # Sortie brutale à l'instant le plus délicat (tout est déplacé, rien
    # n'est échangé) : le trap remet data/ et le venv, ne supprime rien.
    staging, live = _build(tmp_path)
    inodes = _inodes(live)
    result, watcher = _promote(staging, live, prelude=_just_before_exchange("exit 9"))

    assert result.returncode == 9
    assert "bascule interrompue" in result.stderr
    assert _inodes(live) == inodes
    assert (live / "data" / "overrides.json").read_text() == '{"user": "config"}\n'
    assert (live / "core" / "class" / "jeedom2ha.class.php").read_text() == "<?php // v1\n"
    works = _work_dirs(live)
    assert len(works) == 1 and (works[0] / "jeedom2ha" / "core").is_dir(), "dossier de travail supprimé"
    assert str(works[0]) in result.stderr
    assert watcher.problems == []


def test_abrupt_exit_between_data_and_venv_moves_restores_data(tmp_path):
    staging, live = _build(tmp_path)
    inodes = _inodes(live)
    result, _ = _promote(staging, live, prelude=_after_data_move("exit 9"))

    assert result.returncode == 9
    assert _inodes(live) == inodes
    assert len(_work_dirs(live)) == 1


def test_leftover_with_data_blocks_next_deploy_and_deletes_nothing(tmp_path):
    # Trace d'une bascule tuée net (SIGKILL) : data/ resté dans le dossier
    # de travail, absent du plugin en place.
    staging, live = _build(tmp_path)
    leftover = live.parent / ".jeedom2ha-deploy.abc123"
    (live / "data").rename(tmp_path / "moved-data")
    (leftover / "jeedom2ha").mkdir(parents=True)
    (tmp_path / "moved-data").rename(leftover / "jeedom2ha" / "data")

    result, _ = _promote(staging, live)

    assert result.returncode != 0
    assert "bascule précédente interrompue" in result.stderr
    assert str(leftover / "jeedom2ha" / "data") in result.stderr
    assert (leftover / "jeedom2ha" / "data" / "overrides.json").read_text() == '{"user": "config"}\n'
    assert (live / "core" / "class" / "jeedom2ha.class.php").read_text() == "<?php // v1\n"
    assert _work_dirs(live) == [leftover]


def test_leftover_check_runs_before_the_daemon_is_stopped():
    text = SCRIPT.read_text()
    assert text.index('jeedom2ha_check_leftovers "${V_PLUGIN_PATH}"') \
        < text.index('jeedom2ha_stop_daemon_for_switch "${V_JEEDOM_ROOT}"')


def test_rollback_cleanup_never_removes_the_previous_tree_after_exchange():
    text = SCRIPT.read_text()
    assert 'cleanup() { [[ "${JEEDOM2HA_SWITCH_MODE:-}" == "exchange" ]] || sudo rm -rf "${_work}"; }' in text
    switch = text.index('jeedom2ha_switch_plugin_dir "${_work}/jeedom2ha" "${PLUGIN_PATH}" rollback')
    assert text.rindex("trap '' HUP INT TERM PIPE", 0, switch) > text.index("cleanup() {")


def test_fallback_without_atomic_exchange_leaves_data_in_place(tmp_path):
    # Noyau/FS sans RENAME_EXCHANGE (ou python3 absent) : data/ et venv ne
    # bougent pas, seul le code est mis à jour (rsync --delay-updates depuis
    # l'arbre déjà normalisé).
    staging, live = _build(tmp_path)
    inodes = _inodes(live)

    result, watcher = _promote(staging, live, prelude="jeedom2ha_exchange_dirs() { return 3; }")

    assert result.returncode == 0, result.stderr
    assert "repli" in result.stderr
    assert "__JEEDOM2HA_PREVIOUS_WORK__" not in result.stdout
    assert watcher.problems == [], watcher.problems[:5]
    _assert_promoted(live, inodes)
    assert sorted(x.name for x in live.parent.iterdir()) == ["jeedom2ha"]


def test_incomplete_prepared_tree_is_never_switched(tmp_path):
    staging, live = _build(tmp_path)
    (staging / "core" / "class" / "jeedom2ha.class.php").unlink()
    before = (live / "core" / "class" / "jeedom2ha.class.php").read_text()

    result, watcher = _promote(staging, live)

    assert result.returncode != 0
    assert "core/class/jeedom2ha.class.php absent ou illisible" in result.stderr
    assert watcher.problems == []
    assert (live / "core" / "class" / "jeedom2ha.class.php").read_text() == before
    assert sorted(x.name for x in live.parent.iterdir()) == ["jeedom2ha"]


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignore les permissions")
def test_unreadable_prepared_tree_is_detected(tmp_path):
    tree = tmp_path / "tree"
    _write(tree / "plugin_info" / "info.json", "{}", 0o644)
    _write(tree / "core" / "class" / "jeedom2ha.class.php", "<?php", 0o644)
    _write(tree / "core" / "secret.php", "<?php", 0o000)

    result = _bash('jeedom2ha_check_tree_readable "$1" nobody', str(tree))

    assert result.returncode != 0
    assert "secret.php" in result.stderr


def test_switch_creates_plugin_by_rename_when_absent(tmp_path):
    nxt = tmp_path / "work" / "jeedom2ha"
    _write(nxt / "plugin_info" / "info.json", "{}", 0o644)
    live = tmp_path / "plugins" / "jeedom2ha"
    live.parent.mkdir()

    result = _bash('jeedom2ha_switch_plugin_dir "$1" "$2" rollback', str(nxt), str(live))

    assert result.returncode == 0, result.stderr
    assert (live / "plugin_info" / "info.json").is_file()
    assert not nxt.exists()


# --- Journal `plugin` -------------------------------------------------------

_LOG = """\
[2026-11-15 15:12:59][ERROR] : Plugin introuvable : jeedom2ha
[2026-11-15 15:13:04][ERROR] : Fichier introuvable : /var/www/html/core/php/../../plugins/jeedom2ha/core/class/jeedom2ha.class.php
[2026-11-15 15:13:04][ERROR] : Fichier introuvable : /var/www/html/core/php/../../plugins/otherplugin/core/class/otherplugin.class.php
[2026-11-15 15:13:05][ERROR] : Plugin introuvable : jeedom2ha_other
[2026-11-15 15:13:06][ERROR] : Plugin introuvable (json invalide) : jeedom2ha =>
[2026-11-15 15:13:07][INFO] : rien
continuation : Plugin introuvable : jeedom2ha
"""


def _scan(since: str, log: str) -> "list[str]":
    result = subprocess.run(
        ["bash", "-c", f"source '{LIB}'; jeedom2ha_scan_plugin_log \"$1\"", "bash", since],
        input=log, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    return [line for line in result.stdout.splitlines() if line]


def test_log_scan_only_reports_jeedom2ha_losses_since_deploy_start():
    hits = _scan("2026-11-15 15:13:00", _LOG)
    assert len(hits) == 3, hits
    assert "plugins/jeedom2ha/core/class/jeedom2ha.class.php" in hits[0]
    assert "(json invalide) : jeedom2ha" in hits[1]
    assert hits[2].startswith("continuation")


def test_log_scan_attaches_continuation_lines_to_their_timestamp():
    assert _scan("2026-11-15 15:13:07", _LOG) == ["continuation : Plugin introuvable : jeedom2ha"]
    assert _scan("2026-11-15 15:13:08", _LOG) == []


# --- Contrôle PHP après promotion ------------------------------------------

# Cœur Jeedom minimal : mêmes points d'entrée que le vrai (plugin::byId qui
# force la désactivation si info.json est introuvable, isActive() lu dans la
# config, autoload des classes de plugin actif via include_file qui journalise
# « Fichier introuvable » dans log/plugin).
_FAKE_CORE = r'''<?php
$GLOBALS["J_ROOT"] = dirname(__DIR__, 2);
function j_cfg() { return json_decode(file_get_contents($GLOBALS["J_ROOT"] . "/config.json"), true); }
class plugin {
    public $id;
    public static function getPathById($id) { return $GLOBALS["J_ROOT"] . "/plugins/$id/plugin_info/info.json"; }
    public static function byId($id) {
        if (!file_exists(self::getPathById($id))) {
            file_put_contents($GLOBALS["J_ROOT"] . "/force_disabled", $id);
            throw new Exception("Plugin introuvable : $id");
        }
        $p = new plugin(); $p->id = $id; return $p;
    }
    public function isActive() { return j_cfg()["active"][$this->id] ?? 0; }
}
spl_autoload_register(function ($c) {
    if ((j_cfg()["active"][$c] ?? 0) != 1) { return; }
    $path = $GLOBALS["J_ROOT"] . "/core/php/../../plugins/$c/core/class/$c.class.php";
    if (file_exists($path)) { require_once $path; return; }
    file_put_contents($GLOBALS["J_ROOT"] . "/log/plugin",
        "[" . date("Y-m-d H:i:s") . "][ERROR] : Fichier introuvable : $path\n", FILE_APPEND);
});
'''


def _fake_jeedom(tmp_path: Path, active: int = 1, with_class: bool = True, log: str = "") -> Path:
    root = tmp_path / "jeedom"
    _write(root / "core" / "php" / "core.inc.php", _FAKE_CORE, 0o644)
    _write(root / "config.json", '{"active": {"jeedom2ha": %d}}' % active, 0o644)
    _write(root / "plugins" / "jeedom2ha" / "plugin_info" / "info.json", "{}", 0o644)
    if with_class:
        _write(root / "plugins" / "jeedom2ha" / "core" / "class" / "jeedom2ha.class.php",
               "<?php class jeedom2ha {}\n", 0o644)
    _write(root / "log" / "plugin", log, 0o644)
    return root


def _verify(root: Path, since: str = "2000-01-01 00:00:00") -> subprocess.CompletedProcess:
    return _bash('jeedom2ha_verify_plugin_loaded "$1" "$2"', str(root), since)


needs_php = pytest.mark.skipif(shutil.which("php") is None, reason="php not installed")


@needs_php
def test_verify_passes_when_jeedom_autoloads_the_active_plugin(tmp_path):
    result = _verify(_fake_jeedom(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "__JEEDOM2HA_PLUGIN_CHECK__=OK" in result.stdout


@needs_php
def test_verify_fails_when_jeedom_disabled_the_plugin_and_does_not_reactivate(tmp_path):
    root = _fake_jeedom(tmp_path, active=0)
    result = _verify(root)
    assert result.returncode != 0
    assert "__JEEDOM2HA_PLUGIN_CHECK__=OK" not in result.stdout
    assert "DÉSACTIVÉ" in result.stderr
    assert "ne réactive PAS" in result.stderr
    assert '"jeedom2ha": 0' in (root / "config.json").read_text()


@needs_php
def test_verify_relies_on_core_autoload_not_on_explicit_require(tmp_path):
    # Classe absente : un require_once explicite planterait autrement ; ici
    # c'est l'autoload du cœur qui doit échouer, et sa trace dans le journal.
    result = _verify(_fake_jeedom(tmp_path, with_class=False))
    assert result.returncode != 0
    assert "class_exists" in result.stderr
    assert "Fichier introuvable" in result.stderr


@needs_php
def test_verify_does_not_call_byid_when_info_json_is_missing(tmp_path):
    # plugin::byId() désactiverait lui-même le plugin : le contrôle doit
    # échouer AVANT de l'appeler.
    root = _fake_jeedom(tmp_path)
    (root / "plugins" / "jeedom2ha" / "plugin_info" / "info.json").unlink()
    result = _verify(root)
    assert result.returncode != 0
    assert "info.json absent ou illisible" in result.stderr
    assert not (root / "force_disabled").exists()


@needs_php
def test_verify_fails_on_new_plugin_log_errors_only(tmp_path):
    root = _fake_jeedom(tmp_path, log=_LOG)
    old = _verify(root, since="2026-11-15 15:14:00")
    assert old.returncode == 0, old.stderr

    new = _verify(root, since="2026-11-15 15:13:00")
    assert new.returncode != 0
    assert "Plugin introuvable (json invalide) : jeedom2ha" in new.stderr


# --- Câblage dans deploy-to-box.sh -----------------------------------------

def test_verify_function_never_requires_the_plugin_class_explicitly():
    text = LIB.read_text()
    body = text[text.index("jeedom2ha_verify_plugin_loaded() {"):]
    assert "jeedom2ha.class.php" not in body
    assert "class_exists($id)" in body
    assert "isActive()" in body


def test_deploy_never_reactivates_the_plugin():
    for path in (SCRIPT, LIB, REPO_ROOT / "scripts" / "deploy-rollback-lib.sh"):
        text = path.read_text()
        for forbidden in ('config::save("active"', "config::save('active'", "setIsEnable(1)", "->setIsActive(", "::activate("):
            assert forbidden not in text, (path.name, forbidden)


def test_plugin_check_runs_after_promotion_and_before_the_deploy_tag():
    text = SCRIPT.read_text()
    since = text.index("\njeedom2ha_capture_deploy_since\n")
    stop = text.index('jeedom2ha_stop_daemon_for_switch "${V_JEEDOM_ROOT}"')
    promote = text.index('echo "  1b. promotion atomique')
    version = text.index('echo "  1c. VERSION')
    after_promotion = text.index('jeedom2ha_remote_verify_plugin "après promotion"')
    retain = text.index('jeedom2ha_remote_retain_previous\n', after_promotion)
    relaunch = text.index('[[ "${RESTART_DAEMON}" != "true" && "${DAEMON_WAS_RUNNING}" == "1" ]]')
    restart = text.index('echo "--- [3/5] Restart daemon')
    final = text.index('jeedom2ha_remote_verify_plugin "fin de déploiement"')
    tag = text.index('  jeedom2ha_create_and_push_deploy_tag "${_deploy_sha}"')
    assert since < stop < promote < version < after_promotion < retain < relaunch < restart < final < tag
    # L'ancien rsync en place vers le dossier vu par Jeedom a disparu.
    assert 'rsync -a --delete --exclude \'data/\'' not in text
    assert 'sudo rm -rf "${PLUGIN_PATH}"' not in text
