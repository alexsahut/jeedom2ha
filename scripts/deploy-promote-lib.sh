#!/bin/bash
# =============================================================================
# deploy-promote-lib.sh
#
# Promotion du plugin sur la box (étape 1b de deploy-to-box.sh, et restauration
# du mode --rollback) + contrôle « Jeedom voit-il encore le plugin ? » après
# promotion.
#
# Incident du 15/11/2026 (box de production) : pendant l'ancien
#   sudo rsync -a --delete … staging/ → plugins/jeedom2ha/
# suivi APRÈS COUP de chown -R www-data / chmod 755-644, le cœur Jeedom
# (PHP sous www-data) a journalisé « Fichier introuvable : …/core/class/
# jeedom2ha.class.php » puis « Plugin introuvable : jeedom2ha », et
# plugin::byId() → plugin::forceDisablePlugin() a mis le plugin à active=0.
# `rsync -a` recopie propriétaire ET mode du staging (compte SSH, modes du
# poste de déploiement) sur chaque dossier du plugin au fil du transfert :
# tant que le chown/chmod de rattrapage n'est pas passé, un dossier en 700/750
# n'est plus traversable par www-data, et file_exists() renvoie false
# (Jeedom : include_file() → « Fichier introuvable », plugin::byId() →
# « Plugin introuvable » + forceDisablePlugin).
#
# Principe retenu ici : le dossier vu par Jeedom n'est JAMAIS modifié en place.
#   1. le code est préparé à côté (même système de fichiers), dans un dossier
#      caché plugins/.jeedom2ha-deploy.XXXXXX/jeedom2ha — le cœur Jeedom liste
#      plugins/* avec glob('*'), qui ignore les noms en « . », et n'y trouve de
#      toute façon pas de plugin_info/info.json à la racine ;
#   2. propriétaire www-data et modes 755/644 sont posés sur CET arbre, puis
#      vérifiés en lisant l'arbre en tant que www-data ;
#   3. le démon est arrêté (deploy-to-box.sh) et son absence revérifiée juste
#      avant la bascule ; data/ (choix de l'utilisateur : overrides…) et
#      resources/python_venv/ sont DÉPLACÉS (rename, même système de
#      fichiers vérifié) de l'ancien arbre vers le nouveau : aucune copie,
#      aucune comparaison taille/date, donc aucune écriture perdue ;
#   4. bascule en une seule opération atomique : renameat2(RENAME_EXCHANGE)
#      échange les deux dossiers (aucun instant où plugins/jeedom2ha est
#      absent, incomplet ou illisible) ; en cas d'échec, data/ et le venv
#      reviennent à leur place ;
#   5. l'ancien arbre n'est JAMAIS supprimé par la promotion : il reste dans
#      le dossier de travail jusqu'au contrôle d'après bascule, puis est
#      conservé en plugins/.jeedom2ha.prev-<horodatage>/jeedom2ha (une seule
#      génération, la précédente n'est supprimée qu'en étant remplacée) ;
#   6. repli si l'échange atomique est impossible sur la box (sonde
#      préalable : noyau/FS sans RENAME_EXCHANGE, python3 absent) : data/ et
#      le venv ne bougent pas, et seul le code est mis à jour par rsync
#      depuis l'arbre préparé, qui porte déjà propriétaire et modes www-data
#      (-a les recopie tels quels), avec --checksum, --delay-updates et
#      --delete-delay.
#
# Comme deploy-rollback-lib.sh, ce fichier ne fait AUCUN appel ssh : il est
# sourcé en local par les tests (tests/unit/test_deploy_promote_lib.py, avec
# `sudo` stubbé) et concaténé devant le script distant par deploy-to-box.sh.
# Chaque opération sur un chemin de la box passe par `sudo` explicite (le
# compte SSH n'a pas de droit direct sur /var/www/html ni sur le dossier de
# travail créé par `sudo mktemp -d`).
#
# Le script ne RÉACTIVE JAMAIS le plugin : si le contrôle échoue, il s'arrête
# en erreur et le dit.
# =============================================================================

# jeedom2ha_exchange_dirs <a> <b>
# Échange atomiquement deux chemins du même système de fichiers via
# renameat2(RENAME_EXCHANGE) (Linux ≥ 3.15, glibc ≥ 2.28 ; ext4, xfs, btrfs,
# tmpfs). coreutils n'expose `mv --exchange` qu'à partir de 9.5 (absent de
# Debian 11/12) : on passe donc par python3 + ctypes, présent sur une box
# Jeedom (le démon du plugin en dépend).
# Retour : 0 échangé ; 3 échange non supporté ici (rien n'a bougé) ;
# autre : échec (rien n'a bougé non plus — l'appel système est atomique).
jeedom2ha_exchange_dirs() {
  local a="$1" b="$2"
  command -v python3 >/dev/null 2>&1 || {
    echo "  python3 absent : échange atomique indisponible." >&2
    return 3
  }
  sudo python3 -c '
import ctypes, errno, os, sys
libc = ctypes.CDLL(None, use_errno=True)
fn = getattr(libc, "renameat2", None)
if fn is None:
    sys.stderr.write("  renameat2 absent de la libc : échange atomique indisponible.\n")
    sys.exit(3)
fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
AT_FDCWD, RENAME_EXCHANGE = -100, 2
if fn(AT_FDCWD, os.fsencode(sys.argv[1]), AT_FDCWD, os.fsencode(sys.argv[2]), RENAME_EXCHANGE) != 0:
    err = ctypes.get_errno()
    sys.stderr.write("  renameat2(RENAME_EXCHANGE) : %s\n" % os.strerror(err))
    sys.exit(3 if err in (errno.EINVAL, errno.ENOSYS, errno.EOPNOTSUPP) else 1)
' "${a}" "${b}"
}

# jeedom2ha_normalize_plugin_tree <tree> <owner>
# Pose propriétaire et modes attendus par Jeedom sur un arbre qui n'est PAS
# encore visible par Jeedom : mêmes règles que l'ancienne étape 1b
# (www-data, dossiers 755, fichiers 644, main.py exécutable), venv exclu du
# chmod (le cœur Jeedom le gère, ses binaires doivent rester exécutables).
jeedom2ha_normalize_plugin_tree() {
  local tree="$1" owner="$2"
  sudo chown -R "${owner}" "${tree}" || return 1
  sudo find "${tree}" -path "${tree}/resources/python_venv" -prune -o -type d -exec chmod 755 {} + || return 1
  sudo find "${tree}" -path "${tree}/resources/python_venv" -prune -o -type f -exec chmod 644 {} + || return 1
  if sudo test -f "${tree}/resources/daemon/main.py"; then
    sudo chmod 755 "${tree}/resources/daemon/main.py" || return 1
  fi
}

# jeedom2ha_check_tree_readable <tree> <user>
# Lit l'arbre EN TANT QUE <user> (www-data) avant la bascule : tout dossier
# non traversable/illisible ou fichier illisible fait échouer (rc 1), avec la
# liste des chemins fautifs. data/ et le venv sont exclus (contenu géré au
# fil de l'eau par le démon / le cœur Jeedom, repris tel quel). Vérifie en
# plus explicitement les deux fichiers dont l'absence désactive le plugin.
jeedom2ha_check_tree_readable() {
  local tree="$1" user="$2" bad rel
  for rel in plugin_info/info.json core/class/jeedom2ha.class.php; do
    sudo -u "${user}" test -r "${tree}/${rel}" || {
      echo "ERROR: ${rel} absent ou illisible par ${user} dans l'arbre préparé (${tree})." >&2
      return 1
    }
  done
  bad=$(sudo -u "${user}" find "${tree}" \
          \( -path "${tree}/data" -o -path "${tree}/resources/python_venv" \) -prune \
          -o \( -type d \( ! -readable -o ! -executable \) -print \) \
          -o \( ! -type d ! -readable -print \) 2>&1 | head -20) || true
  if [[ -n "${bad}" ]]; then
    echo "ERROR: arbre préparé non lisible par ${user} — bascule annulée, plugin en place inchangé :" >&2
    printf '%s\n' "${bad}" | sed 's/^/    /' >&2
    return 1
  fi
}

# jeedom2ha_exchange_supported <dir>
# Sonde sans effet sur le plugin : échange deux dossiers vides créés dans
# <dir> (même système de fichiers que le plugin). rc 0 si RENAME_EXCHANGE
# fonctionne ici.
jeedom2ha_exchange_supported() {
  local dir="$1" rc=0
  sudo mkdir "${dir}/.probe-a" "${dir}/.probe-b" || return 1
  jeedom2ha_exchange_dirs "${dir}/.probe-a" "${dir}/.probe-b" 2>/dev/null || rc=$?
  sudo rmdir "${dir}/.probe-a" "${dir}/.probe-b" || true
  return "${rc}"
}

# jeedom2ha_fs_id <path> — identifiant du système de fichiers (st_dev).
jeedom2ha_fs_id() {
  sudo stat -c %d "$1"
}

# jeedom2ha_daemon_running — rc 0 si un main.py du plugin tourne encore.
jeedom2ha_daemon_running() {
  pgrep -f 'plugins/jeedom2ha/.*resources/daemon/main.py' >/dev/null 2>&1
}

# jeedom2ha_stop_daemon_for_switch <jeedom_root>
# Arrête le démon AVANT la bascule (ses écritures dans data/ ne doivent pas
# croiser le déplacement de data/). Imprime
#   __JEEDOM2HA_DAEMON_WAS_RUNNING__=0|1
# pour que deploy-to-box.sh le relance ensuite s'il tournait. rc ≠ 0 si un
# main.py survit (rien n'a encore été touché au plugin).
jeedom2ha_stop_daemon_for_switch() {
  local jeedom_root="$1" was=0 i
  if jeedom2ha_daemon_running; then
    was=1
    sudo -u www-data env JEEDOM_ROOT="${jeedom_root}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
require_once getenv("JEEDOM_ROOT") . "/plugins/jeedom2ha/core/class/jeedom2ha.class.php";
jeedom2ha::deamon_stop();
' || true
    for i in $(seq 1 20); do
      jeedom2ha_daemon_running || break
      sleep 1
    done
    if jeedom2ha_daemon_running; then
      sudo pkill -TERM -f 'plugins/jeedom2ha/.*resources/daemon/main.py' || true
      sleep 2
      jeedom2ha_daemon_running && sudo pkill -KILL -f 'plugins/jeedom2ha/.*resources/daemon/main.py' || true
      sleep 1
    fi
    if jeedom2ha_daemon_running; then
      echo "ERROR: le démon jeedom2ha tourne encore : bascule annulée (plugin non modifié)." >&2
      echo "__JEEDOM2HA_DAEMON_WAS_RUNNING__=${was}"
      return 1
    fi
    echo "  Démon arrêté pour la bascule (il sera relancé)."
  else
    echo "  Démon non démarré : rien à arrêter."
  fi
  echo "__JEEDOM2HA_DAEMON_WAS_RUNNING__=${was}"
}

# jeedom2ha_switch_plugin_dir <next> <live> <mode>
# Rend <next> (arbre complet, déjà normalisé et vérifié) visible à la place
# de <live>. Utilisée telle quelle par --rollback (l'archive restaure aussi
# data/). Positionne JEEDOM2HA_SWITCH_MODE = create | exchange | rsync.
# Après un échange, l'ancien arbre se trouve à l'emplacement <next> : c'est
# à l'appelant de le conserver.
JEEDOM2HA_SWITCH_MODE=""
jeedom2ha_switch_plugin_dir() {
  local next="$1" live="$2" mode="$3" rc=0
  local -a excludes=()
  [[ "${mode}" == "deploy" ]] && excludes=(--exclude '/data/' --exclude '/resources/python_venv/')

  if ! sudo test -e "${live}"; then
    # Rien en place : un rename simple crée le dossier d'un coup.
    sudo mv -T "${next}" "${live}" || return 1
    JEEDOM2HA_SWITCH_MODE=create
    echo "  Bascule : ${live} créé par rename atomique."
    return 0
  fi

  jeedom2ha_exchange_dirs "${next}" "${live}" || rc=$?
  if [[ "${rc}" -eq 0 ]]; then
    JEEDOM2HA_SWITCH_MODE=exchange
    echo "  Bascule atomique (renameat2 RENAME_EXCHANGE) : ${live} remplacé d'un seul coup."
    return 0
  fi
  echo "WARNING: échange atomique impossible (code ${rc}) — repli rsync --delay-updates depuis l'arbre préparé (déjà www-data, 755/644)." >&2
  jeedom2ha_rsync_code "${next}" "${live}" "${excludes[@]}" || return 1
  JEEDOM2HA_SWITCH_MODE=rsync
  echo "  Bascule (repli) : rsync --delay-updates terminé."
}

# jeedom2ha_rsync_code <src> <dst> [excludes...] — repli sans échange
# atomique. --checksum : ne pas se fier à taille+date ; --delay-updates /
# --delete-delay : fichiers remplacés et supprimés en fin de transfert ; -a
# recopie propriétaire et modes déjà corrects de l'arbre préparé.
jeedom2ha_rsync_code() {
  local src="$1" dst="$2"
  shift 2
  sudo rsync -a --checksum --delete --delete-delay --delay-updates "$@" "${src}/" "${dst}/"
}

# jeedom2ha_retain_previous <work> <parent>
# Après un contrôle d'après bascule réussi : l'ancien arbre (dans <work>)
# est conservé en <parent>/.jeedom2ha.prev-<horodatage>/jeedom2ha. Une seule
# génération : les .jeedom2ha.prev-* plus anciennes ne sont supprimées
# qu'APRÈS que la nouvelle a pris leur place.
jeedom2ha_retain_previous() {
  local work="$1" parent="$2" dest old
  case "$(basename "${work}")" in
    .jeedom2ha-deploy.*|.jeedom2ha-rollback.*) ;;
    *) echo "ERROR: dossier de travail inattendu : ${work}" >&2; return 1 ;;
  esac
  [[ "$(dirname "${work}")" == "${parent}" ]] || { echo "ERROR: ${work} hors de ${parent}" >&2; return 1; }
  sudo test -d "${work}/jeedom2ha" || { echo "ERROR: ancien arbre absent de ${work}" >&2; return 1; }
  dest="${parent}/.jeedom2ha.prev-$(date -u +%Y%m%dT%H%M%SZ)"
  sudo test -e "${dest}" && dest="${dest}-$$"
  sudo mv -T "${work}" "${dest}" || return 1
  sudo chmod 700 "${dest}" || true
  for old in $(sudo find "${parent}" -mindepth 1 -maxdepth 1 -type d -name '.jeedom2ha.prev-*' ! -path "${dest}"); do
    sudo rm -rf -- "${old}"
  done
  echo "  Ancienne version conservée : ${dest}/jeedom2ha (une seule génération)."
}

# jeedom2ha_promote_plugin_dir <staging> <live> <owner>
# Étape 1b de deploy-to-box.sh. Le plugin en place est un prérequis (l'étape
# 1a-bis refuse déjà de déployer sans lui, faute de rollback sûr), et le
# démon doit être arrêté (jeedom2ha_stop_daemon_for_switch).
# Chaque étape porte son propre `|| exit 1` : le résultat ne dépend pas de
# `set -e`, que bash neutralise si l'appelant écrit `… || …`.
# Après un échange, imprime __JEEDOM2HA_PREVIOUS_WORK__=<work> : l'ancien
# arbre y reste (jamais supprimé ici) jusqu'à jeedom2ha_retain_previous.
jeedom2ha_promote_plugin_dir() {
  local staging="$1" live="$2" owner="$3"
  local user="${owner%%:*}"
  (
    set -euo pipefail
    sudo test -d "${live}" || { echo "ERROR: plugin absent à ${live}." >&2; exit 1; }
    sudo test -d "${staging}" || { echo "ERROR: staging absent à ${staging}." >&2; exit 1; }
    local parent work next rel fs_live fs
    local -a moved=()
    parent=$(dirname "${live}")
    work=$(sudo mktemp -d "${parent}/.jeedom2ha-deploy.XXXXXX") || exit 1
    # Tant que rien n'a basculé, <work> ne contient que le code préparé.
    trap 'sudo rm -rf -- "${work}"' EXIT
    # 711 : www-data peut traverser (contrôle de lisibilité ci-dessous) sans
    # pouvoir lister.
    sudo chmod 711 "${work}" || exit 1
    next="${work}/jeedom2ha"

    # Code seul : data/ et le venv ne sont jamais copiés.
    sudo rsync -a --exclude '/data/' --exclude '/resources/python_venv/' "${staging}/" "${next}/" || exit 1
    jeedom2ha_normalize_plugin_tree "${next}" "${owner}" || exit 1
    jeedom2ha_check_tree_readable "${next}" "${user}" || exit 1
    echo "  Arbre préparé : ${next} (${owner}, 755/644, lisible par ${user})."

    if ! jeedom2ha_exchange_supported "${work}"; then
      echo "WARNING: échange atomique indisponible sur cette box — repli : code mis à jour par rsync --delay-updates, data/ et venv laissés en place." >&2
      jeedom2ha_rsync_code "${next}" "${live}" --exclude '/data/' --exclude '/resources/python_venv/' || exit 1
      echo "  Bascule (repli) : rsync --delay-updates terminé."
      echo "  Permissions OK (www-data, 755/644, main.py +x)."
      exit 0
    fi

    # Même système de fichiers partout : un mv entre deux FS deviendrait une
    # copie suivie d'une suppression.
    fs_live=$(jeedom2ha_fs_id "${live}") || exit 1
    for rel in "${work}" "${live}/data" "${live}/resources/python_venv"; do
      sudo test -e "${rel}" || continue
      fs=$(jeedom2ha_fs_id "${rel}") || exit 1
      if [[ "${fs}" != "${fs_live}" ]]; then
        echo "ERROR: ${rel} n'est pas sur le même système de fichiers que ${live} — bascule annulée (aucun déplacement de données)." >&2
        exit 1
      fi
    done

    if jeedom2ha_daemon_running; then
      echo "ERROR: le démon jeedom2ha tourne : bascule annulée pour ne pas croiser ses écritures dans data/." >&2
      exit 1
    fi

    # Retour arrière des déplacements si la bascule n'a pas lieu.
    jeedom2ha__restore_moved() {
      local r i
      for (( i=${#moved[@]}-1; i>=0; i-- )); do
        r="${moved[$i]}"
        sudo mv -T "${next}/${r}" "${live}/${r}" \
          || echo "ERROR: impossible de remettre ${r} : il est dans ${next}/${r}" >&2
      done
    }
    for rel in data resources/python_venv; do
      sudo test -e "${live}/${rel}" || continue
      sudo mkdir -p "$(dirname "${next}/${rel}")" || { jeedom2ha__restore_moved; trap - EXIT; exit 1; }
      if ! sudo mv -T "${live}/${rel}" "${next}/${rel}"; then
        jeedom2ha__restore_moved; trap - EXIT
        echo "ERROR: déplacement de ${rel} impossible — bascule annulée." >&2
        exit 1
      fi
      moved+=("${rel}")
    done

    if ! jeedom2ha_exchange_dirs "${next}" "${live}"; then
      jeedom2ha__restore_moved
      # Les données sont revenues (ou le message ci-dessus dit où elles
      # sont) : on ne supprime pas <work> par précaution.
      trap - EXIT
      echo "ERROR: échange atomique en échec — plugin en place inchangé, dossier de travail conservé : ${work}" >&2
      exit 1
    fi
    # L'ancien arbre est désormais dans <work> : plus jamais supprimé ici.
    trap - EXIT
    echo "  Bascule atomique (renameat2 RENAME_EXCHANGE) : ${live} remplacé d'un seul coup ; data/ et venv déplacés (rename), jamais copiés."
    echo "__JEEDOM2HA_PREVIOUS_WORK__=${work}"
    echo "  Permissions OK (www-data, 755/644, main.py +x)."
  )
}

# jeedom2ha_box_now
# Horodatage courant au format des journaux Jeedom ([Y-m-d H:i:s]), calculé
# par PHP avec la configuration Jeedom chargée (même fuseau que log::add).
# À appeler AVANT toute modification du plugin : sert de borne basse au
# contrôle du journal `plugin`.
jeedom2ha_box_now() {
  local jeedom_root="$1" user="${2:-www-data}"
  sudo -u "${user}" env JEEDOM_ROOT="${jeedom_root}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
echo date("Y-m-d H:i:s");
'
}

# jeedom2ha_scan_plugin_log <since>  (journal sur stdin)
# Imprime les lignes du journal `plugin` horodatées à partir de <since>
# (« YYYY-MM-DD HH:MM:SS », comparaison lexicale) qui signalent que Jeedom a
# perdu le plugin : « Plugin introuvable : jeedom2ha » (y compris « json
# invalide ») ou « Fichier introuvable » sur un chemin plugins/jeedom2ha/.
# Les lignes de continuation (sans horodatage) héritent de la ligne qui les
# précède. Un horodatage plutôt qu'un décalage en octets : log::chunk()
# tronque le fichier en place, un décalage deviendrait faux.
jeedom2ha_scan_plugin_log() {
  local since="$1"
  awk -v since="${since}" '
    /^\[[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]\]/ {
      in_window = (substr($0, 2, 19) >= since)
    }
    in_window && (/Plugin introuvable[^:]*: jeedom2ha([^A-Za-z0-9_]|$)/ ||
                  (/Fichier introuvable/ && /plugins\/jeedom2ha\//)) { print }
  '
}

# jeedom2ha_verify_plugin_loaded <jeedom_root> <since> [user] [log_file]
# Contrôle après promotion, exécuté SOUS www-data et SANS require_once de la
# classe du plugin (c'est ce require_once explicite qui avait masqué
# l'incident du 15/11/2026 : seul l'autoload du cœur reflète ce que voit
# Jeedom) :
#   - plugin_info/info.json lisible (testé AVANT plugin::byId, qui
#     désactiverait lui-même le plugin s'il ne le trouvait pas) ;
#   - plugin::byId("jeedom2ha")->isActive() vrai ;
#   - class_exists("jeedom2ha") vrai par l'autoload du cœur ;
#   - aucune ligne « Plugin introuvable : jeedom2ha » / « Fichier
#     introuvable … plugins/jeedom2ha/ » dans le journal `plugin` depuis <since>.
# Ne réactive JAMAIS le plugin. Imprime __JEEDOM2HA_PLUGIN_CHECK__=OK et
# retourne 0 si tout est bon ; sinon message explicite et retour ≠ 0.
jeedom2ha_verify_plugin_loaded() {
  local jeedom_root="$1" since="$2" user="${3:-www-data}"
  local log_file="${4:-${jeedom_root}/log/plugin}"
  local php_rc=0 php_out hits=""

  php_out=$(sudo -u "${user}" env JEEDOM_ROOT="${jeedom_root}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
$id = "jeedom2ha";
if (!is_readable(plugin::getPathById($id))) {
    fwrite(STDERR, "plugin_info/info.json absent ou illisible pour l utilisateur PHP\n");
    exit(2);
}
$plugin = plugin::byId($id);
if (!$plugin->isActive()) {
    fwrite(STDERR, "plugin::byId(\"jeedom2ha\")->isActive() est faux : le plugin est DÉSACTIVÉ dans Jeedom\n");
    exit(3);
}
if (!class_exists($id)) {
    fwrite(STDERR, "class_exists(\"jeedom2ha\") est faux par l autoload du cœur Jeedom\n");
    exit(4);
}
echo "php-ok";
' 2>&1) || php_rc=$?

  if sudo test -f "${log_file}"; then
    hits=$(sudo -u "${user}" cat "${log_file}" | jeedom2ha_scan_plugin_log "${since}") || true
  fi

  if [[ "${php_rc}" -ne 0 || "${php_out}" != *php-ok* || -n "${hits}" ]]; then
    echo "ERROR: Jeedom ne voit plus correctement le plugin jeedom2ha après promotion." >&2
    if [[ "${php_rc}" -ne 0 || "${php_out}" != *php-ok* ]]; then
      echo "  Contrôle PHP (sous ${user}, autoload du cœur, code ${php_rc}) :" >&2
      printf '%s\n' "${php_out}" | sed 's/^/    /' >&2
    fi
    if [[ -n "${hits}" ]]; then
      echo "  Journal ${log_file} depuis ${since} :" >&2
      printf '%s\n' "${hits}" | sed 's/^/    /' >&2
    fi
    echo "  Le script ne réactive PAS le plugin. Vérifier l'état dans Jeedom (Plugins > Gestion des plugins)," >&2
    echo "  le réactiver à la main si nécessaire, puis relancer le démon." >&2
    return 1
  fi
  echo "__JEEDOM2HA_PLUGIN_CHECK__=OK"
  echo "  Plugin vu par Jeedom (www-data, autoload) : actif, classe chargée, journal plugin propre depuis ${since}."
}
