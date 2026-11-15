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
#   1. un arbre complet est préparé à côté (même système de fichiers), dans un
#      dossier caché plugins/.jeedom2ha-deploy.XXXXXX/jeedom2ha — le cœur
#      Jeedom liste plugins/* avec glob('*'), qui ignore les noms en « . », et
#      n'y trouve de toute façon pas de plugin_info/info.json à la racine ;
#   2. data/ et resources/python_venv/ y sont repris par liens physiques
#      (cp -al : aucune copie de contenu, aucune perte possible — les fichiers
#      restent les mêmes inodes) ;
#   3. propriétaire www-data et modes 755/644 sont posés sur CET arbre, puis
#      vérifiés en lisant l'arbre en tant que www-data ;
#   4. bascule en une seule opération atomique : renameat2(RENAME_EXCHANGE)
#      échange les deux dossiers (aucun instant où plugins/jeedom2ha est
#      absent, incomplet ou illisible) ;
#   5. repli si l'échange atomique est impossible (noyau/FS sans
#      RENAME_EXCHANGE, python3 absent) : rsync depuis l'arbre préparé, qui
#      porte déjà propriétaire et modes www-data (-a les recopie tels quels),
#      avec --delay-updates/--delete-delay (fichiers mis à jour renommés en
#      fin de transfert, suppressions en fin de transfert).
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

# jeedom2ha_switch_plugin_dir <next> <live> <mode>
# Rend <next> (arbre complet, déjà normalisé et vérifié) visible à la place
# de <live>. <mode> = deploy (le repli rsync préserve data/ et le venv en
# place) ou rollback (le repli rsync restaure l'archive à l'identique).
# Après un échange réussi, l'ancien arbre se trouve à l'emplacement <next>.
jeedom2ha_switch_plugin_dir() {
  local next="$1" live="$2" mode="$3" rc=0
  local -a excludes=()
  [[ "${mode}" == "deploy" ]] && excludes=(--exclude '/data/' --exclude '/resources/python_venv/')

  if ! sudo test -e "${live}"; then
    # Rien en place : un rename simple crée le dossier d'un coup.
    sudo mv -T "${next}" "${live}" || return 1
    echo "  Bascule : ${live} créé par rename atomique."
    return 0
  fi

  jeedom2ha_exchange_dirs "${next}" "${live}" || rc=$?
  if [[ "${rc}" -eq 0 ]]; then
    echo "  Bascule atomique (renameat2 RENAME_EXCHANGE) : ${live} remplacé d'un seul coup."
    return 0
  fi
  echo "WARNING: échange atomique impossible (code ${rc}) — repli rsync --delay-updates depuis l'arbre préparé (déjà www-data, 755/644)." >&2
  # --checksum : ne pas se fier à taille+date (un fichier modifié de même
  # taille dans la même seconde serait sauté).
  sudo rsync -a --checksum --delete --delete-delay --delay-updates "${excludes[@]}" "${next}/" "${live}/" || return 1
  echo "  Bascule (repli) : rsync --delay-updates terminé."
}

# jeedom2ha_promote_plugin_dir <staging> <live> <owner>
# Étape 1b de deploy-to-box.sh. Le plugin en place est un prérequis (l'étape
# 1a-bis refuse déjà de déployer sans lui, faute de rollback sûr).
# Chaque étape porte son propre `|| exit 1` : le résultat ne dépend pas de
# `set -e`, que bash neutralise si l'appelant écrit `… || …`.
jeedom2ha_promote_plugin_dir() {
  local staging="$1" live="$2" owner="$3"
  local user="${owner%%:*}"
  (
    set -euo pipefail
    sudo test -d "${live}" || { echo "ERROR: plugin absent à ${live}." >&2; exit 1; }
    sudo test -d "${staging}" || { echo "ERROR: staging absent à ${staging}." >&2; exit 1; }
    local parent work next
    parent=$(dirname "${live}")
    work=$(sudo mktemp -d "${parent}/.jeedom2ha-deploy.XXXXXX") || exit 1
    # Nettoyage dans tous les cas : avant bascule, <work> ne contient que
    # l'arbre préparé ; après échange, il contient l'ANCIEN arbre (dont
    # data/ et le venv partagent les inodes du nouveau : rm ne retire que
    # des noms, jamais le contenu encore référencé par le plugin en place).
    trap 'sudo rm -rf -- "${work}"' EXIT
    # 711 : www-data peut traverser (contrôle de lisibilité ci-dessous) sans
    # pouvoir lister.
    sudo chmod 711 "${work}" || exit 1
    next="${work}/jeedom2ha"

    # Code : copie complète du staging (data/ et venv n'en font pas partie).
    sudo rsync -a --exclude '/data/' --exclude '/resources/python_venv/' "${staging}/" "${next}/" || exit 1

    # Données d'exécution : reprises par liens physiques (même FS garanti,
    # <work> est dans le dossier parent du plugin).
    local rel
    for rel in data resources/python_venv; do
      if sudo test -e "${live}/${rel}"; then
        sudo mkdir -p "$(dirname "${next}/${rel}")" || exit 1
        sudo cp -al "${live}/${rel}" "${next}/${rel}" || exit 1
      fi
    done

    jeedom2ha_normalize_plugin_tree "${next}" "${owner}" || exit 1
    jeedom2ha_check_tree_readable "${next}" "${user}" || exit 1
    echo "  Arbre préparé : ${next} (${owner}, 755/644, lisible par ${user})."

    jeedom2ha_switch_plugin_dir "${next}" "${live}" deploy || exit 1

    # Après un échange, l'ancien arbre est à ${next}. Un fichier de data/
    # remplacé (écriture tmp + rename) par le démon entre le cp -al et la
    # bascule n'existe que dans l'ancien arbre : on le rapatrie s'il est plus
    # récent (--update ne recule jamais un fichier du plugin en place).
    if sudo test -d "${next}/data" && sudo test -d "${live}/data"; then
      sudo rsync -a --update "${next}/data/" "${live}/data/" || exit 1
    fi
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
