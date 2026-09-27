#!/bin/bash
# =============================================================================
# DEV/TEST ONLY — deploy-to-box.sh
#
# Utilitaire de déploiement LOCAL → box Jeedom de test.
# Ce script N'EST PAS la procédure de release du projet.
# Distribution canonique : main → beta → stable → Jeedom Market.
#
# Les primitives jeedom2ha_* et les patterns de commandes sont calés sur
# le contrat terrain documenté dans :
#   _bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FILTER_FILE="${REPO_ROOT}/.rsync-plugin-deploy.filter"
ENV_FILE="${REPO_ROOT}/.env"
VERSION_FILE_LIB="${SCRIPT_DIR}/deploy-version-file.sh"
ROLLBACK_LIB="${SCRIPT_DIR}/deploy-rollback-lib.sh"
INVENTORY_DIFF_LIB="${SCRIPT_DIR}/deploy-inventory-diff.sh"

# jeedom2ha_render_version_content / jeedom2ha_write_version_file_atomic —
# testées sans ssh dans tests/unit/test_deploy_version_file.py.
# jeedom2ha_diff_topic_lists (diff d'inventaire MQTT, point 8) — testée sans
# ssh dans tests/unit/test_deploy_inventory_diff.py ; exécutée en LOCAL ici
# (le contenu avant/après est rapatrié par ssh+cat, mais le diff lui-même ne
# touche à aucune box).
# shellcheck disable=SC1090
source "${VERSION_FILE_LIB}"
# shellcheck disable=SC1090
source "${INVENTORY_DIFF_LIB}"

# ROLLBACK_LIB (jeedom2ha_validate_rollback_archive / jeedom2ha_backup_plugin_dir /
# jeedom2ha_stop_daemon_with_pid_fallback — points 5, 6, 7) n'est PAS sourcée
# ici : ses fonctions ne s'exécutent que sur la box, via
# jeedom2ha_rollback_archive qui concatène ce fichier devant le script
# distant (même convention que VERSION_FILE_LIB plus bas pour l'écriture du
# fichier VERSION). Testée sans ssh dans tests/unit/test_deploy_rollback_lib.py.

# Load .env if present
if [[ -f "${ENV_FILE}" ]]; then
  set -o allexport
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +o allexport
fi

# --- Defaults ---
JEEDOM_BOX_HOST="${JEEDOM_BOX_HOST:-}"
# Utilisateur SSH : pas de connexion root directe sur Jeedom standard.
# Utiliser un user avec sudo NOPASSWD (ex: asahut).
JEEDOM_BOX_USER="${JEEDOM_BOX_USER:-asahut}"
JEEDOM_BOX_PORT="${JEEDOM_BOX_PORT:-22}"
JEEDOM_BOX_PATH="${JEEDOM_BOX_PATH:-/var/www/html/plugins/jeedom2ha}"
# Répertoire de staging sur la box (accessible en écriture par JEEDOM_BOX_USER).
# Le déploiement est en 2 étapes : rsync → staging, puis sudo → plugin dir.
JEEDOM_STAGING_DIR="${JEEDOM_STAGING_DIR:-/home/${JEEDOM_BOX_USER}/jeedom2ha-staging}"
# Répertoire d'archives (backup du plugin existant avant écrasement).
# Dossier en 700, chaque archive tar.gz en 600 (point 4b — hygiène des permissions).
JEEDOM_BACKUP_DIR="${JEEDOM_BACKUP_DIR:-/home/${JEEDOM_BOX_USER}/jeedom2ha-backups}"
# JEEDOM_ROOT est utilisé par PHP via getenv("JEEDOM_ROOT") sur la box
JEEDOM_ROOT="${JEEDOM_ROOT:-/var/www/html}"

# Initialisés par jeedom2ha_refresh_secret
LOCAL_SECRET=""
DAEMON_PORT="55080"
DAEMON_API="http://127.0.0.1:55080"

# MQTT credentials pour cleanup — initialisés par la section cleanup
_mqtt_host=""; _mqtt_port="1883"; _mqtt_user=""; _mqtt_pass=""

# Chemins des fichiers d'inventaire MQTT avant/après — initialisés par
# jeedom2ha_inventory_discovery (point 8, diff affiché en fin de déploiement).
INVENTORY_BEFORE_FILE=""
INVENTORY_AFTER_FILE=""

# Archive de sauvegarde créée par --rollback avant d'écraser le plugin en
# place (point 7, rollback réversible) — initialisée par jeedom2ha_rollback_archive.
PRE_ROLLBACK_BACKUP_ARCHIVE=""

DRY_RUN=false
RESTART_DAEMON=false
CLEANUP_DISCOVERY=false
SKIP_POST_DEPLOY=false
STOP_DAEMON_CLEANUP=false
ROLLBACK_ARCHIVE=""

# --- Parse args ---
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --dry-run)            DRY_RUN=true ;;
    --restart-daemon)     RESTART_DAEMON=true ;;
    --cleanup-discovery)  CLEANUP_DISCOVERY=true ;;
    --skip-post-deploy)    SKIP_POST_DEPLOY=true ;;
    --stop-daemon-cleanup) STOP_DAEMON_CLEANUP=true ;;
    --rollback)
       [[ "$#" -ge 2 && -n "$2" && "${2:0:2}" != "--" ]] || {
         echo "ERROR: --rollback requires a remote .tar.gz archive path." >&2; exit 1;
       }
       ROLLBACK_ARCHIVE="$2"
       shift ;;
    *) echo "ERROR: Unknown argument: $1" >&2
       echo "Usage: $0 [--dry-run] [--restart-daemon] [--cleanup-discovery] [--skip-post-deploy]" >&2
       echo "       $0 --rollback <remote-archive.tar.gz>" >&2
       echo "       $0 --stop-daemon-cleanup  (mode dédié — incompatible avec les autres options)" >&2
       exit 1 ;;
  esac
  shift
done

# =============================================================================
# GUARDRAILS
# =============================================================================

_fail() { echo "ERROR: $*" >&2; exit 1; }

# Normal deploys must be reproducible from a committed, CI-validated SHA.  We
# query the GitHub check-runs endpoint directly rather than `gh pr checks`:
# a commit can be deployable even when it has no open PR, and this endpoint is
# explicitly scoped to the exact SHA that is copied by rsync below.
jeedom2ha_verify_deploy_source() {
  _deploy_sha=$(git -C "${REPO_ROOT}" rev-parse HEAD)
  [[ -z "$(git -C "${REPO_ROOT}" status --porcelain)" ]] \
    || _fail "Refus de déployer : l'arbre Git local est sale (fichiers non suivis inclus)."

  _origin_url=$(git -C "${REPO_ROOT}" config --get remote.origin.url 2>/dev/null || true)
  _github_repo=$(sed -E -n 's#^(git@github\.com:|https://github\.com/)([^/]+/[^/.]+)(\.git)?$#\2#p' <<< "${_origin_url}")
  [[ -n "${_github_repo}" ]] || _fail "Impossible de déterminer le dépôt GitHub depuis origin (${_origin_url:-absent})."

  _check_runs=$(gh api --paginate -H "Accept: application/vnd.github+json" \
    "repos/${_github_repo}/commits/${_deploy_sha}/check-runs?per_page=100") \
    || _fail "Impossible de lire les check-runs GitHub pour ${_deploy_sha}."
  _check_lines=$(printf '%s' "${_check_runs}" | jq -r '.check_runs[]? | [.status, .conclusion] | @tsv')
  [[ -n "${_check_lines}" ]] || _fail "Refus de déployer ${_deploy_sha} : aucun check-run GitHub trouvé."
  # Un check-run encore en cours (in_progress/queued) doit être un refus, pas
  # un succès implicite — on ne l'accepte donc que si status="completed".
  # Une fois "completed", seules success/skipped/neutral sont des conclusions
  # valides (ex: Burn-In "skipped" hors planning burn-in) ; tout le reste
  # (failure, cancelled, timed_out, action_required, stale, ...) est refusé.
  while IFS=$'\t' read -r _check_status _check_conclusion; do
    [[ "${_check_status}" == "completed" ]] \
      || _fail "Refus de déployer ${_deploy_sha} : check-run non terminé (${_check_status}/${_check_conclusion})."
    case "${_check_conclusion}" in
      success|skipped|neutral) ;;
      *) _fail "Refus de déployer ${_deploy_sha} : CI non verte (${_check_status}/${_check_conclusion})." ;;
    esac
  done <<< "${_check_lines}"
  echo "  Source Git validée : ${_deploy_sha} (arbre propre, check-runs GitHub verts)."
}

# Point 9 — un tag resté local ne sert à rien pour la traçabilité partagée :
# on le pousse vers origin après l'avoir créé en local. Non bloquant : le
# déploiement a déjà réussi à ce stade (fichiers en place, healthcheck OK) ;
# un souci réseau ponctuel sur le push ne doit pas faire échouer le script
# après coup — juste avertir, le tag local reste disponible pour un push
# manuel ultérieur. Extraite en fonction (pure git, aucun ssh) pour être
# testable unitairement sans dérouler tout le flux de déploiement.
jeedom2ha_create_and_push_deploy_tag() {
  local _sha="$1" _ts="$2"
  local _tag="deploy-${_sha}-$(date -u +%Y%m%dT%H%M%SZ)"
  GIT_COMMITTER_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    git -C "${REPO_ROOT}" tag -a "${_tag}" "${_sha}" \
      -m "DEV/TEST box deploy ${_sha} (${_ts})"
  echo "  Tag annoté créé : ${_tag}"
  if git -C "${REPO_ROOT}" push origin "${_tag}"; then
    echo "  Tag poussé vers origin : ${_tag}"
  else
    echo "WARNING: push du tag ${_tag} vers origin a échoué (tag local conservé)." >&2
  fi
}

# --stop-daemon-cleanup est un mode dédié, incompatible avec les autres options opérationnelles.
if [[ "${STOP_DAEMON_CLEANUP}" == "true" ]]; then
  _conflicts=()
  [[ "${DRY_RUN}"           == "true" ]] && _conflicts+=(--dry-run)
  [[ "${RESTART_DAEMON}"    == "true" ]] && _conflicts+=(--restart-daemon)
  [[ "${CLEANUP_DISCOVERY}" == "true" ]] && _conflicts+=(--cleanup-discovery)
  [[ "${SKIP_POST_DEPLOY}"  == "true" ]] && _conflicts+=(--skip-post-deploy)
  if [[ "${#_conflicts[@]}" -gt 0 ]]; then
    _fail "--stop-daemon-cleanup est un mode stop+cleanup dédié.
       Il est incompatible avec : ${_conflicts[*]}
       Utilisez --stop-daemon-cleanup seul, ou --cleanup-discovery [--restart-daemon] pour le mode nominal."
  fi
fi

if [[ -n "${ROLLBACK_ARCHIVE}" ]]; then
  [[ "${DRY_RUN}" == "false" && "${RESTART_DAEMON}" == "false" \
     && "${CLEANUP_DISCOVERY}" == "false" && "${SKIP_POST_DEPLOY}" == "false" \
     && "${STOP_DAEMON_CLEANUP}" == "false" ]] \
    || _fail "--rollback est un mode dédié et ne peut pas être combiné avec d'autres options."
  [[ "${ROLLBACK_ARCHIVE}" == /* && "${ROLLBACK_ARCHIVE}" == *.tar.gz ]] \
    || _fail "--rollback attend un chemin absolu vers une archive .tar.gz distante."
fi

[[ -z "${JEEDOM_BOX_HOST}" ]]                         && _fail "JEEDOM_BOX_HOST is not set."
[[ -z "${JEEDOM_BOX_PATH}" ]]                         && _fail "JEEDOM_BOX_PATH is empty."
[[ "${JEEDOM_BOX_PATH:0:1}" != "/" ]]                 && _fail "JEEDOM_BOX_PATH must be absolute."
[[ "${JEEDOM_BOX_PATH}" != */plugins/jeedom2ha ]]     && \
  _fail "JEEDOM_BOX_PATH='${JEEDOM_BOX_PATH}' must end with /plugins/jeedom2ha."
_depth=$(awk -F'/' '{print NF-1}' <<< "${JEEDOM_BOX_PATH}")
[[ "${_depth}" -lt 4 ]]                               && _fail "JEEDOM_BOX_PATH too shallow (depth=${_depth})."

# jq requis localement pour le parsing JSON.
# Le script ne l'utilise pas sur la box distante.
command -v jq &>/dev/null || _fail "jq is required locally. Install: brew install jq"

# This is deliberately before the first ssh/rsync invocation.  A rejected
# source must leave the test box entirely untouched.
if [[ -z "${ROLLBACK_ARCHIVE}" && "${STOP_DAEMON_CLEANUP}" == "false" ]]; then
  echo "--- Garde-fous source..."
  jeedom2ha_verify_deploy_source
  echo ""
fi

SSH_TARGET="${JEEDOM_BOX_USER}@${JEEDOM_BOX_HOST}"
SSH_OPTS=(-p "${JEEDOM_BOX_PORT}" -o "BatchMode=yes" -o "StrictHostKeyChecking=accept-new")

# =============================================================================
# PRÉ-CHECKS CONNEXION
# Effectués avant toute opération, y compris dry-run.
# =============================================================================

echo "--- Pré-checks..."
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" true 2>/dev/null \
  || _fail "Connexion SSH impossible pour ${SSH_TARGET}. Vérifiez clé SSH et accès."

ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "sudo -n true" 2>/dev/null \
  || _fail "sudo -n true échoué pour ${JEEDOM_BOX_USER}@${JEEDOM_BOX_HOST}.
       Sans sudo NOPASSWD, le déploiement vers ${JEEDOM_BOX_PATH} est impossible.
       Ajoutez dans /etc/sudoers: ${JEEDOM_BOX_USER} ALL=(ALL) NOPASSWD: ALL"
echo "  SSH OK | sudo OK"
echo ""

# =============================================================================
# PRIMITIVES TERRAIN
# Patterns calés sur jeedom2ha-test-context-jeedom-reel.md, section 0 et 2.
# =============================================================================

# Lit localSecret et daemonApiPort depuis la BDD Jeedom via PHP CLI.
# Met à jour: LOCAL_SECRET, DAEMON_PORT, DAEMON_API.
jeedom2ha_refresh_secret() {
  local _json
  _json=$(ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
sudo env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
echo json_encode([
  "local_secret" => config::byKey("localSecret", "jeedom2ha"),
  "daemon_port"  => config::byKey("daemonApiPort", "jeedom2ha", "55080"),
]);
'
REMOTE
  )
  LOCAL_SECRET=$(echo "${_json}" | jq -r '.local_secret // empty')
  DAEMON_PORT=$(echo "${_json}"  | jq -r '.daemon_port  // "55080"')
  DAEMON_API="http://127.0.0.1:${DAEMON_PORT}"

  if [[ -z "${LOCAL_SECRET}" ]]; then
    echo "WARNING: localSecret vide — daemon jamais démarré sur cette box." >&2
    echo "         Utilisez --restart-daemon ou démarrez depuis l'UI Jeedom." >&2
    return 1
  fi
}

# Construit /tmp/jeedom2ha-sync-body.json sur la box (fichier canonique du contrat terrain).
# Format: {"payload": <topology>} — identique à la section 2 du terrain doc.
# Requiert jeedom2ha.class.php explicitement (pattern terrain, pas d'autoload CLI implicite).
jeedom2ha_build_sync_body() {
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
sudo rm -f /tmp/jeedom2ha-sync-body.json
sudo env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
require_once getenv("JEEDOM_ROOT") . "/plugins/jeedom2ha/core/class/jeedom2ha.class.php";
echo json_encode(["payload" => jeedom2ha::getFullTopology()], JSON_UNESCAPED_SLASHES);
' | sudo tee /tmp/jeedom2ha-sync-body.json >/dev/null
echo "  sync-body: \$(wc -c < /tmp/jeedom2ha-sync-body.json) bytes → /tmp/jeedom2ha-sync-body.json"
REMOTE
}

# GET /system/status sur la box (daemon 127.0.0.1 seulement, X-Local-Secret).
# Pattern terrain doc section 1.
jeedom2ha_status() {
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" \
    "curl -sS --max-time 5 -H 'X-Local-Secret: ${LOCAL_SECRET}' ${DAEMON_API}/system/status"
}

# Arrête le daemon via jeedom2ha::deamon_stop() (SIGTERM + SIGKILL fallback après 10s).
# Pattern aligné avec le contrat plugin — arrêt par PID file, pas via jeeApi.php.
jeedom2ha_stop_daemon() {
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
sudo -u www-data env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
require_once getenv("JEEDOM_ROOT") . "/plugins/jeedom2ha/core/class/jeedom2ha.class.php";
jeedom2ha::deamon_stop();
'
echo "  jeedom2ha::deamon_stop() appelé."
REMOTE
}

# POST /action/sync en utilisant /tmp/jeedom2ha-sync-body.json sur la box.
# Pattern terrain doc section 2.
jeedom2ha_sync() {
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" \
    "curl -sS -X POST --max-time 20 \
     -H 'X-Local-Secret: ${LOCAL_SECRET}' \
     -H 'Content-Type: application/json' \
     ${DAEMON_API}/action/sync \
     --data-binary @/tmp/jeedom2ha-sync-body.json"
}

# Source unique des credentials MQTT, également utilisée par --cleanup-discovery.
jeedom2ha_refresh_mqtt_credentials() {
  local _mqtt_json
  _mqtt_json=$(ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
sudo env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
\$mode = config::byKey("mode", "mqtt2", "local");
\$host = (\$mode === "remote") ? config::byKey("remote::ip", "mqtt2", "") : "127.0.0.1";
\$port = (\$mode === "remote") ? intval(config::byKey("remote::port", "mqtt2", 1883)) : 1883;
\$raw = config::byKey("mqtt::password", "mqtt2", "");
\$line = explode("\\n", \$raw)[0]; \$user = ""; \$pass = "";
if (strpos(\$line, ":") !== false) { list(\$user, \$pass) = explode(":", \$line, 2); }
echo json_encode(["host"=>\$host, "port"=>\$port, "user"=>\$user, "pass"=>\$pass]);
'
REMOTE
  )
  _mqtt_host=$(echo "${_mqtt_json}" | jq -r '.host // empty')
  _mqtt_port=$(echo "${_mqtt_json}" | jq -r '.port // "1883"')
  _mqtt_user=$(echo "${_mqtt_json}" | jq -r '.user // empty')
  _mqtt_pass=$(echo "${_mqtt_json}" | jq -r '.pass // empty')
}

# Snapshot retained topics on the box next to deploy backups for manual diffs.
jeedom2ha_inventory_discovery() {
  local _phase="$1"
  [[ -n "${_mqtt_host}" ]] || { echo "WARNING: mqtt2 host introuvable — inventaire ${_phase} ignoré." >&2; return 0; }
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash -s -- \
    "${_mqtt_host}" "${_mqtt_port}" "${_mqtt_user}" "${_mqtt_pass}" "${JEEDOM_BACKUP_DIR}" "${_phase}" <<'REMOTE'
set -euo pipefail
MQTT_HOST="$1"; MQTT_PORT="$2"; MQTT_USER="$3"; MQTT_PASS="$4"; BACKUP_DIR="$5"; PHASE="$6"
command -v mosquitto_sub &>/dev/null || { echo "WARNING: mosquitto_sub absent — inventaire ignoré." >&2; exit 0; }
_auth=(-h "${MQTT_HOST}" -p "${MQTT_PORT}")
[[ -n "${MQTT_USER}" ]] && _auth+=(-u "${MQTT_USER}" -P "${MQTT_PASS}")
sudo mkdir -p "${BACKUP_DIR}/inventory"
sudo chmod 700 "${BACKUP_DIR}/inventory"
_file="${BACKUP_DIR}/inventory/jeedom2ha-discovery-${PHASE}-$(date -u +%Y%m%dT%H%M%SZ).txt"
TOPICS=$(mosquitto_sub "${_auth[@]}" -W 2 -t 'homeassistant/+/+/config' -F '%t' 2>/dev/null || true)
printf '%s\n' "${TOPICS}" | grep '/jeedom2ha_' | sort -u | sudo tee "${_file}" >/dev/null || true
sudo chmod 600 "${_file}"
sudo chown "$(id -un):$(id -gn)" "${_file}"
echo "__JEEDOM2HA_INVENTORY_FILE__=${_file}"
echo "  Inventaire ${PHASE}: ${_file}"
REMOTE
}

# jeedom2ha_fetch_inventory_content <remote_file>
# Rapatrie localement le contenu d'un fichier d'inventaire écrit par
# jeedom2ha_inventory_discovery, pour que jeedom2ha_diff_topic_lists
# (bibliothèque pure bash, point 8) puisse calculer le diff. Chaîne vide si
# <remote_file> est vide ou introuvable — jeedom2ha_diff_topic_lists gère
# ce cas sans erreur.
jeedom2ha_fetch_inventory_content() {
  local _remote_file="$1"
  [[ -n "${_remote_file}" ]] || { echo ""; return 0; }
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "sudo cat '${_remote_file}'" 2>/dev/null || echo ""
}

jeedom2ha_rollback_archive() {
  local _archive="$1"
  echo "--- Rollback archive → ${JEEDOM_BOX_PATH}/"
  local _remote_output
  local _remote_status=0
  if _remote_output=$(
    { cat "${ROLLBACK_LIB}"
      cat <<'REMOTE'
ARCHIVE="$1"; PLUGIN_PATH="$2"; JEEDOM_ROOT="$3"; BACKUP_DIR="$4"; BOX_USER="$5"
set -euo pipefail
[[ -r "${ARCHIVE}" ]] || { echo "ERROR: archive inaccessible: ${ARCHIVE}" >&2; exit 1; }

# Point 5 — validation sans pipe direct tar|grep sous pipefail (voir
# jeedom2ha_validate_rollback_archive, ROLLBACK_LIB ci-dessus).
jeedom2ha_validate_rollback_archive "${ARCHIVE}"

_parent=$(dirname "${PLUGIN_PATH}")
_work=$(sudo mktemp -d "${_parent}/.jeedom2ha-rollback.XXXXXX")
cleanup() { sudo rm -rf "${_work}"; }
trap cleanup EXIT
sudo tar -xzf "${ARCHIVE}" -C "${_work}"
[[ -d "${_work}/jeedom2ha" ]] || { echo "ERROR: jeedom2ha/ absente après extraction." >&2; exit 1; }

# Point 7 — rollback réversible : archive l'état COURANT du plugin en place
# (code + data/, aucune exclusion) AVANT de l'écraser, même format 700/600
# que les archives de pré-déploiement, sous un préfixe distinct pour ne
# jamais les confondre. Non bloquant si aucun plugin n'est en place (rien à
# perdre) : le rollback doit pouvoir s'appliquer même sur une box vierge.
jeedom2ha_backup_plugin_dir "${PLUGIN_PATH}" "${BACKUP_DIR}" "${BOX_USER}:${BOX_USER}" \
  "jeedom2ha-pre-rollback" "false"

# Point 6 — le plugin en place peut être cassé (c'est le scénario même du
# rollback) : jeedom2ha::deamon_stop() peut donc échouer. On tente d'abord
# la voie normale (classe PHP du plugin), puis on replie sur un arrêt direct
# via le PID file si besoin — la restauration ci-dessous doit avoir lieu
# dans tous les cas, que l'arrêt ait réussi ou non.
jeedom2ha_stop_via_plugin_class() {
  sudo -u www-data env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
require_once getenv("JEEDOM_ROOT") . "/plugins/jeedom2ha/core/class/jeedom2ha.class.php";
jeedom2ha::deamon_stop();
'
}
jeedom2ha_stop_daemon_with_pid_fallback "/tmp/jeedom/jeedom2ha/deamon.pid"

sudo rm -rf "${PLUGIN_PATH}"
sudo mv "${_work}/jeedom2ha" "${PLUGIN_PATH}"
sudo chown -R www-data:www-data "${PLUGIN_PATH}"
sudo -u www-data env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
require_once getenv("JEEDOM_ROOT") . "/plugins/jeedom2ha/core/class/jeedom2ha.class.php";
if (!jeedom2ha::deamon_start()) { fwrite(STDERR, "deamon_start() returned false\\n"); exit(1); }
'
echo "  Rollback restauré et daemon redémarré sous www-data."
REMOTE
    } | ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash -s -- \
        "${_archive}" "${JEEDOM_BOX_PATH}" "${JEEDOM_ROOT}" "${JEEDOM_BACKUP_DIR}" "${JEEDOM_BOX_USER}" 2>&1
  ); then
    _remote_status=0
  else
    _remote_status=$?
  fi
  echo "${_remote_output}"
  PRE_ROLLBACK_BACKUP_ARCHIVE=$(sed -n 's/^__JEEDOM2HA_BACKUP_ARCHIVE__=//p' <<< "${_remote_output}")
  if [[ -n "${PRE_ROLLBACK_BACKUP_ARCHIVE}" ]]; then
    echo ""
    echo "  Ce rollback est lui-même réversible :"
    printf '    ./scripts/deploy-to-box.sh --rollback %q\n' "${PRE_ROLLBACK_BACKUP_ARCHIVE}"
  fi
  if [[ "${_remote_status}" -ne 0 ]]; then
    echo "ERROR: rollback distant échoué (code ${_remote_status})." >&2
    if [[ -n "${PRE_ROLLBACK_BACKUP_ARCHIVE}" ]]; then
      echo "       Archive de sauvegarde pré-rollback : ${PRE_ROLLBACK_BACKUP_ARCHIVE}" >&2
    fi
    return "${_remote_status}"
  fi
}

# =============================================================================
echo "======================================================================="
echo "  DEV/TEST DEPLOY — jeedom2ha"
echo "  [NOT the canonical release path — for local test box only]"
echo "======================================================================="
echo "  User    : ${SSH_TARGET}"
echo "  Staging : ${JEEDOM_STAGING_DIR}/"
echo "  Target  : ${JEEDOM_BOX_PATH}/ (via sudo)"
[[ "${DRY_RUN}" == "true" ]] && echo "  Mode    : DRY-RUN"
echo ""

if [[ -n "${ROLLBACK_ARCHIVE}" ]]; then
  if jeedom2ha_rollback_archive "${ROLLBACK_ARCHIVE}"; then
    :
  else
    _rollback_exit=$?
    exit "${_rollback_exit}"
  fi
  jeedom2ha_refresh_secret || _fail "Rollback effectué mais localSecret indisponible après redémarrage."
  _rollback_status=$(jeedom2ha_status 2>&1) || _fail "Daemon injoignable après rollback."
  [[ "$(echo "${_rollback_status}" | jq -r '.status // empty')" == "ok" ]] \
    || _fail "Healthcheck échoué après rollback: ${_rollback_status}"
  echo "======================================================================="
  echo "  Rollback complete."
  echo "======================================================================="
  exit 0
fi

# =============================================================================
# STEP 1 — déploiement (user SSH non-root + sudo)
#
# Étape 1a      : rsync local → staging (accessible en écriture par JEEDOM_BOX_USER)
# Étape 1a-bis  : backup archive (700/600) du plugin existant, avant écrasement
# Étape 1b      : sudo promotion staging → plugin dir + permissions www-data
# Étape 1c      : écriture atomique du fichier VERSION (version + sha + date)
#
# Pattern terrain doc "Sur la box Jeedom de test" adapté pour user non-root.
# Toutes les opérations sur /var/www/html passent par sudo.
# =============================================================================

RSYNC_OPTS=(-avz --delete --delete-excluded --filter="merge ${FILTER_FILE}" -e "ssh -p ${JEEDOM_BOX_PORT}")

if [[ "${DRY_RUN}" == "true" ]]; then
  echo "[DRY-RUN] Rsync simulation → staging (${SSH_TARGET}:${JEEDOM_STAGING_DIR}/):"
  rsync --dry-run "${RSYNC_OPTS[@]}" "${REPO_ROOT}/" "${SSH_TARGET}:${JEEDOM_STAGING_DIR}/"
  echo ""
  echo "[DRY-RUN] Simulation complete — no files transferred, no sudo operations."
  exit 0
fi

# =============================================================================
# MODE stop-daemon-cleanup — arrêt daemon + cleanup discovery uniquement.
# Permet de vérifier dans HA que les entités disparaissent sans republication.
# Pas de déploiement, pas de restart, pas de sync.
# =============================================================================

if [[ "${STOP_DAEMON_CLEANUP}" == "true" ]]; then
  echo "--- [stop] Mode stop-daemon-cleanup : arrêt daemon + cleanup discovery..."
  echo "    (Pas de déploiement, pas de restart, pas de sync)"
  echo ""

  # Credentials MQTT — même extraction que step 2
  _mqtt_json=$(ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
sudo env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
\$mode = config::byKey("mode", "mqtt2", "local");
\$host = (\$mode === "remote") ? config::byKey("remote::ip", "mqtt2", "") : "127.0.0.1";
\$port = (\$mode === "remote") ? intval(config::byKey("remote::port", "mqtt2", 1883)) : 1883;
\$raw  = config::byKey("mqtt::password", "mqtt2", "");
\$line = explode("\n", \$raw)[0];
\$user = ""; \$pass = "";
if (strpos(\$line, ":") !== false) { list(\$user, \$pass) = explode(":", \$line, 2); }
echo json_encode(["host"=>\$host, "port"=>\$port, "user"=>\$user, "pass"=>\$pass]);
'
REMOTE
  )
  _mqtt_host=$(echo "${_mqtt_json}" | jq -r '.host // empty')
  _mqtt_port=$(echo "${_mqtt_json}" | jq -r '.port // "1883"')
  _mqtt_user=$(echo "${_mqtt_json}" | jq -r '.user // empty')
  _mqtt_pass=$(echo "${_mqtt_json}" | jq -r '.pass // empty')

  # Lire le vrai daemonApiPort depuis la config Jeedom (ne pas supposer 55080)
  _real_port=$(ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
sudo env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
echo config::byKey("daemonApiPort", "jeedom2ha", "55080");
'
REMOTE
  )
  _real_port=$(echo "${_real_port}" | tr -d '[:space:]')
  [[ "${_real_port}" =~ ^[0-9]+$ ]] && DAEMON_PORT="${_real_port}"
  echo "  daemonApiPort: ${DAEMON_PORT}"

  # Arrêt daemon
  echo "--- [stop-1/2] Arrêt daemon (jeedom2ha::deamon_stop)..."
  jeedom2ha_stop_daemon
  echo ""

  # Vérification arrêt : poll curl jusqu'à connection refused ou timeout
  echo "  Vérification arrêt daemon (max 30s)..."
  _wait=0; _max=30
  until ! ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" \
      "curl -sS --max-time 2 http://127.0.0.1:${DAEMON_PORT}/system/status" \
    >/dev/null 2>&1; do
    sleep 1; _wait=$((_wait + 1))
    [[ "${_wait}" -ge "${_max}" ]] && {
      echo "WARNING: daemon encore actif après ${_max}s — cleanup lancé quand même." >&2
      break
    }
  done
  [[ "${_wait}" -lt "${_max}" ]] && echo "  Daemon arrêté (${_wait}s)."
  echo ""

  # Cleanup MQTT retained
  if [[ -z "${_mqtt_host}" ]]; then
    echo "WARNING: mqtt2 host introuvable — cleanup ignoré."
    echo "         Vérifiez que MQTT Manager (mqtt2) est installé et configuré."
  else
    echo "--- [stop-2/2] Cleanup retained jeedom2ha discovery topics..."
    echo "    Scope: homeassistant/{light,cover,switch}/jeedom2ha_*/config"
    echo "    Broker: ${_mqtt_host}:${_mqtt_port}"
    ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash -s -- \
      "${_mqtt_host}" "${_mqtt_port}" "${_mqtt_user}" "${_mqtt_pass}" <<'REMOTE'
set -euo pipefail
MQTT_HOST="$1"; MQTT_PORT="$2"; MQTT_USER="$3"; MQTT_PASS="$4"
command -v mosquitto_sub &>/dev/null && command -v mosquitto_pub &>/dev/null || {
  echo "  ERROR: mosquitto_sub/pub introuvables. apt-get install mosquitto-clients" >&2; exit 1
}
_auth=(-h "${MQTT_HOST}" -p "${MQTT_PORT}")
[[ -n "${MQTT_USER}" ]] && _auth+=(-u "${MQTT_USER}" -P "${MQTT_PASS}")
echo "  Énumération des topics retained (fenêtre 2s)..."
TOPICS=$(mosquitto_sub "${_auth[@]}" -W 2 \
  -t 'homeassistant/+/+/config' \
  -F '%t' 2>/dev/null || true)
TOPICS=$(echo "${TOPICS}" | grep '/jeedom2ha_' || true)
[[ -z "${TOPICS}" ]] && { echo "  Aucun topic trouvé — rien à nettoyer."; exit 0; }
_n=0
while IFS= read -r _t; do
  [[ -z "${_t}" ]] && continue
  mosquitto_pub "${_auth[@]}" -t "${_t}" -r -n
  echo "  Cleared: ${_t}"; _n=$((_n + 1))
done <<< "${TOPICS}"
echo "  ${_n} topic(s) nettoyé(s)."
REMOTE
  fi
  echo ""
  echo "======================================================================="
  echo "  Stop+cleanup terminé. Les entités jeedom2ha devraient disparaître de HA."
  echo "  Pour republier : ./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon"
  echo "======================================================================="
  exit 0
fi

echo "--- Inventaire MQTT avant déploiement..."
jeedom2ha_refresh_mqtt_credentials
_inv_before_output=$(jeedom2ha_inventory_discovery "before")
echo "${_inv_before_output}"
INVENTORY_BEFORE_FILE=$(sed -n 's/^__JEEDOM2HA_INVENTORY_FILE__=//p' <<< "${_inv_before_output}")
echo ""

echo "--- [1/5] Deploy (staging + sudo promotion)..."

# 1a — rsync vers staging (pas de sudo requis)
echo "  1a. rsync → ${JEEDOM_STAGING_DIR}/"
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "mkdir -p '${JEEDOM_STAGING_DIR}'"
rsync "${RSYNC_OPTS[@]}" "${REPO_ROOT}/" "${SSH_TARGET}:${JEEDOM_STAGING_DIR}/"

# 1a-bis — sauvegarde du plugin existant avant écrasement (point 4b).
# Ne touche à aucune archive déjà existante — crée uniquement le dossier
# d'archives (700) et, si un plugin est déjà déployé, une nouvelle archive
# horodatée (600) avant que le rsync --delete de l'étape 1b ne l'écrase.
echo "  1a-bis. Backup ${JEEDOM_BOX_PATH}/ → ${JEEDOM_BACKUP_DIR}/ (si plugin déjà déployé)"
_backup_output=$(ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
set -e
sudo mkdir -p "${JEEDOM_BACKUP_DIR}"
sudo chmod 700 "${JEEDOM_BACKUP_DIR}"
sudo chown "${JEEDOM_BOX_USER}:${JEEDOM_BOX_USER}" "${JEEDOM_BACKUP_DIR}"
if [[ -d "${JEEDOM_BOX_PATH}" ]]; then
  # mktemp réserve le nom de fichier de façon atomique avant que tar n'y
  # écrive : deux déploiements dans la même seconde ne peuvent donc jamais
  # calculer/écraser le même chemin d'archive (contrairement à un nom
  # construit uniquement à partir de la date).
  _archive=\$(sudo mktemp "${JEEDOM_BACKUP_DIR}/jeedom2ha-\$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX.tar.gz")
  sudo tar -czf "\${_archive}" -C "$(dirname "${JEEDOM_BOX_PATH}")" "$(basename "${JEEDOM_BOX_PATH}")"
  sudo chmod 600 "\${_archive}"
  sudo chown "${JEEDOM_BOX_USER}:${JEEDOM_BOX_USER}" "\${_archive}"
  echo "__JEEDOM2HA_BACKUP_ARCHIVE__=\${_archive}"
  echo "  Backup créé: \${_archive} (600, ${JEEDOM_BOX_USER}) — dossier ${JEEDOM_BACKUP_DIR} (700, ${JEEDOM_BOX_USER})."
else
  echo "ERROR: plugin absent à ${JEEDOM_BOX_PATH}; aucun rollback sûr ne peut être garanti." >&2
  exit 1
fi
REMOTE
)
echo "${_backup_output}"
BACKUP_ARCHIVE=$(sed -n 's/^__JEEDOM2HA_BACKUP_ARCHIVE__=//p' <<< "${_backup_output}")
[[ -n "${BACKUP_ARCHIVE}" ]] || _fail "Backup absent : le déploiement est annulé pour préserver un rollback sûr."
echo ""

# 1b — promotion staging → plugin dir + permissions (sudo requis)
echo "  1b. sudo promote → ${JEEDOM_BOX_PATH}/"
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
set -e
sudo mkdir -p "${JEEDOM_BOX_PATH}"
sudo rsync -a --delete --exclude 'data/' "${JEEDOM_STAGING_DIR}/" "${JEEDOM_BOX_PATH}/"
sudo chown -R www-data:www-data "${JEEDOM_BOX_PATH}"
sudo find "${JEEDOM_BOX_PATH}" -type d -exec chmod 755 {} \;
sudo find "${JEEDOM_BOX_PATH}" -type f -exec chmod 644 {} \;
sudo chmod +x "${JEEDOM_BOX_PATH}/resources/daemon/main.py"
echo "  Permissions OK (www-data, 755/644, main.py +x)."
REMOTE
echo ""

# 1c — écrire un fichier VERSION à la racine du plugin (hors data/), APRÈS le
# rsync --delete ci-dessus pour ne pas en être la victime. Écriture atomique
# + relecture immédiate via scripts/deploy-version-file.sh (point 1c) —
# la même fonction est testée sans ssh dans tests/unit/test_deploy_version_file.py.
echo "  1c. VERSION → ${JEEDOM_BOX_PATH}/VERSION"
_plugin_version=$(jq -r '.pluginVersion' "${REPO_ROOT}/plugin_info/info.json")
_deploy_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
_deploy_git_status="clean"
_version_content=$(jeedom2ha_render_version_content \
  "${_plugin_version}" "${_deploy_sha}" "${_deploy_ts}" "${_deploy_git_status}")

_remote_version_readback=$(
  { cat "${VERSION_FILE_LIB}"
    printf 'jeedom2ha_write_version_file_atomic %q %q %q\n' "${JEEDOM_BOX_PATH}" "${_version_content}" "www-data:www-data"
  } | ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "sudo bash -s"
)

if [[ "${_remote_version_readback}" == "${_version_content}" ]]; then
  echo "  VERSION vérifié après écriture (relecture identique au contenu attendu) :"
  echo "${_version_content}" | sed 's/^/    /'
else
  _fail "VERSION mismatch après écriture sur la box ${JEEDOM_BOX_PATH}/VERSION.
Attendu:
${_version_content}
Obtenu:
${_remote_version_readback}"
fi
echo ""

# =============================================================================
# STEP 2 — Cleanup HA discovery (avant restart/sync)
# Topics : homeassistant/{light,cover,switch}/jeedom2ha_*/config
#   - light et cover : terrain-validés (Story 3.1 / 3.2-bis)
#   - switch : inclus par couverture code (non encore terrain-validé)
# Credentials MQTT : lus depuis la config mqtt2 — source terrain prouvée
#   (section 0 du terrain doc, même extraction que getMqttManagerConfig())
# =============================================================================

if [[ "${CLEANUP_DISCOVERY}" == "true" ]]; then
  echo "--- [2/5] Cleanup retained jeedom2ha discovery topics..."
  echo "    Scope: homeassistant/{light,cover}/jeedom2ha_*/config (terrain-validés)"
  echo "           homeassistant/switch/jeedom2ha_*/config (code-only, non terrain-validé)"
  echo ""

  # Credentials MQTT depuis mqtt2 — même extraction que la section 0 du terrain doc
  _mqtt_json=$(ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
sudo env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
\$mode = config::byKey("mode", "mqtt2", "local");
\$host = (\$mode === "remote") ? config::byKey("remote::ip", "mqtt2", "") : "127.0.0.1";
\$port = (\$mode === "remote") ? intval(config::byKey("remote::port", "mqtt2", 1883)) : 1883;
\$raw  = config::byKey("mqtt::password", "mqtt2", "");
\$line = explode("\n", \$raw)[0];
\$user = ""; \$pass = "";
if (strpos(\$line, ":") !== false) { list(\$user, \$pass) = explode(":", \$line, 2); }
echo json_encode(["host"=>\$host, "port"=>\$port, "user"=>\$user, "pass"=>\$pass]);
'
REMOTE
  )

  _mqtt_host=$(echo "${_mqtt_json}" | jq -r '.host // empty')
  _mqtt_port=$(echo "${_mqtt_json}" | jq -r '.port // "1883"')
  _mqtt_user=$(echo "${_mqtt_json}" | jq -r '.user // empty')
  _mqtt_pass=$(echo "${_mqtt_json}" | jq -r '.pass // empty')

  if [[ -z "${_mqtt_host}" ]]; then
    echo "WARNING: mqtt2 host introuvable — cleanup ignoré."
    echo "         Vérifiez que MQTT Manager (mqtt2) est installé et configuré."
  else
    echo "  Broker: ${_mqtt_host}:${_mqtt_port}"
    # Credentials passés en args positionnels pour éviter l'injection dans le heredoc
    ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash -s -- \
      "${_mqtt_host}" "${_mqtt_port}" "${_mqtt_user}" "${_mqtt_pass}" <<'REMOTE'
set -euo pipefail
MQTT_HOST="$1"; MQTT_PORT="$2"; MQTT_USER="$3"; MQTT_PASS="$4"

command -v mosquitto_sub &>/dev/null && command -v mosquitto_pub &>/dev/null || {
  echo "  ERROR: mosquitto_sub/pub introuvables. apt-get install mosquitto-clients" >&2; exit 1
}

_auth=(-h "${MQTT_HOST}" -p "${MQTT_PORT}")
[[ -n "${MQTT_USER}" ]] && _auth+=(-u "${MQTT_USER}" -P "${MQTT_PASS}")

echo "  Énumération des topics retained (fenêtre 2s)..."
TOPICS=$(mosquitto_sub "${_auth[@]}" -W 2 \
  -t 'homeassistant/+/+/config' \
  -F '%t' 2>/dev/null || true)
TOPICS=$(echo "${TOPICS}" | grep '/jeedom2ha_' || true)

[[ -z "${TOPICS}" ]] && { echo "  Aucun topic trouvé — rien à nettoyer."; exit 0; }

_n=0
while IFS= read -r _t; do
  [[ -z "${_t}" ]] && continue
  mosquitto_pub "${_auth[@]}" -t "${_t}" -r -n
  echo "  Cleared: ${_t}"; _n=$((_n + 1))
done <<< "${TOPICS}"
echo "  ${_n} topic(s) nettoyé(s)."
REMOTE
  fi
  echo ""
fi

# =============================================================================
# STEP 3 — Restart daemon (optionnel)
# Utilise jeedom2ha::deamon_start() — jeedom::startDaemon() absent sur certaines boxes.
# Boucle readiness : condition identique au protocole terrain 3.2b-A.
# Le curl s'exécute sur la box (daemon 127.0.0.1 seulement) et le JSON
# est rapatrié localement pour être évalué par jq local — pas de jq distant requis.
# =============================================================================

if [[ "${RESTART_DAEMON}" == "true" ]]; then
  echo "--- [3/5] Restart daemon (jeedom2ha::deamon_start + boucle readiness MQTT)..."

  # 3a. Stop défensif AVANT start. deamon_start() échoue sur « address already in use »
  # si un daemon orphelin subsiste — PID file vidé (Jeedom le croit arrêté) mais process
  # toujours vivant tenant les ports API/socket. Cas observé 2026-06-19 : 1er restart
  # KO, entités discovery wipées et non republiées. On stoppe d'abord proprement via le
  # contrat plugin (PID file), puis on force-libère tout main.py résiduel (port-agnostic,
  # ne suppose pas la relation apiport/socketport). || true partout : best-effort, ne doit
  # jamais faire échouer le deploy si rien à tuer.
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
sudo -u www-data env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
require_once getenv("JEEDOM_ROOT") . "/plugins/jeedom2ha/core/class/jeedom2ha.class.php";
jeedom2ha::deamon_stop();
' || true
_orphans=\$(pgrep -f 'plugins/jeedom2ha/.*resources/daemon/main.py' 2>/dev/null || true)
if [[ -n "\${_orphans}" ]]; then
  echo "  Daemon orphelin résiduel (PID \${_orphans}) → SIGTERM"
  sudo kill \${_orphans} 2>/dev/null || true
  sleep 2
  _orphans=\$(pgrep -f 'plugins/jeedom2ha/.*resources/daemon/main.py' 2>/dev/null || true)
  if [[ -n "\${_orphans}" ]]; then
    echo "  Orphelin persistant → SIGKILL \${_orphans}"
    sudo kill -9 \${_orphans} 2>/dev/null || true
    sleep 1
  fi
fi
echo "  Stop défensif OK (ports daemon libérés)."
REMOTE

  # deamon_start() génère localSecret si absent — lire le secret APRÈS l'appel
  # set -e : fail-fast si deamon_start() retourne false ou si PHP fatal
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
set -e
sudo -u www-data env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php";
require_once getenv("JEEDOM_ROOT") . "/plugins/jeedom2ha/core/class/jeedom2ha.class.php";
\$ok = jeedom2ha::deamon_start();
if (!\$ok) { fwrite(STDERR, "deamon_start() returned false\n"); exit(1); }
'
echo "  deamon_start() OK."
REMOTE

  # Lire le secret généré/lu par deamon_start
  jeedom2ha_refresh_secret || _fail "localSecret toujours vide après deamon_start."

  echo "  Attente readiness daemon + MQTT (condition identique au protocole terrain 3.2b-A)..."
  _wait=0; _max=60
  until ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" \
      "curl -sS --max-time 3 \
       -H 'X-Local-Secret: ${LOCAL_SECRET}' \
       ${DAEMON_API}/system/status" \
    2>/dev/null \
    | jq -e '.status == "ok" and .payload.mqtt.connected == true and .payload.mqtt.state == "connected"' \
    >/dev/null 2>&1; do
    sleep 1; _wait=$((_wait + 1))
    [[ "${_wait}" -ge "${_max}" ]] && _fail "Timeout readiness (${_max}s). Consultez les logs Jeedom."
  done
  echo "  Daemon prêt, MQTT connecté (${_wait}s)."
  echo ""

fi

# =============================================================================
# STEP 4 — Healthcheck + Sync
# Utilise les primitives jeedom2ha_* calées sur le terrain doc.
# =============================================================================

if [[ "${SKIP_POST_DEPLOY}" == "true" ]]; then
  echo "--- [4/5] Post-deploy ignoré (--skip-post-deploy)."
else
  # Refresh secret sauf si déjà fait par l'étape restart
  if [[ -z "${LOCAL_SECRET}" ]]; then
    jeedom2ha_refresh_secret || {
      echo "WARNING: daemon inaccessible — post-deploy ignoré." >&2
      echo "         Démarrez le daemon depuis l'UI Jeedom ou utilisez --restart-daemon." >&2
      exit 0
    }
  fi
  echo "  daemonApiPort: ${DAEMON_PORT} | localSecret: ${#LOCAL_SECRET} chars"
  echo ""

  echo "--- [4a/5] Healthcheck (jeedom2ha_status)..."
  _status_raw=$(jeedom2ha_status 2>&1) || _fail "Daemon injoignable sur ${DAEMON_API}."
  _status_ok=$(echo "${_status_raw}" | jq -r '.status // empty' 2>/dev/null || echo "")
  [[ "${_status_ok}" != "ok" ]] && _fail "status != ok : ${_status_raw}"
  _mqtt_state=$(echo "${_status_raw}" | jq -r '.payload.mqtt.state // "unknown"')
  echo "  OK — mqtt.state=${_mqtt_state}"
  echo ""

  echo "--- [4b/5] Build sync body (jeedom2ha_build_sync_body)..."
  jeedom2ha_build_sync_body
  echo ""

  echo "--- [4c/5] Sync (jeedom2ha_sync)..."
  _sync_raw=$(jeedom2ha_sync 2>&1) || _fail "Appel /action/sync échoué."
  _sync_ok=$(echo "${_sync_raw}" | jq -r '.status // empty' 2>/dev/null || echo "")
  if [[ "${_sync_ok}" != "ok" ]]; then
    echo "WARNING: sync status != ok : ${_sync_raw}" >&2
  else
    _summary=$(echo "${_sync_raw}" | jq -r '
      .payload |
      "total_eq=\(.total_eq_logics) eligible=\(.eligible_count) published=\(
        ([ (.mapping_summary // {}) | to_entries[] | select(.key | endswith("_published")) | .value | tonumber? ] | add // 0)
      )"' 2>/dev/null || echo "ok")
    echo "  OK — ${_summary}"
    # Sync republie les entités retained : l'inventaire « après » ne doit
    # être pris qu'une fois cet appel confirmé, sinon le diff est trompeur.
    if [[ "${RESTART_DAEMON}" == "true" ]]; then
      echo ""
      echo "--- Inventaire MQTT après sync confirmé..."
      _inv_after_output=$(jeedom2ha_inventory_discovery "after")
      echo "${_inv_after_output}"
      INVENTORY_AFTER_FILE=$(sed -n 's/^__JEEDOM2HA_INVENTORY_FILE__=//p' <<< "${_inv_after_output}")
      echo ""
      echo "--- Diff inventaire MQTT (avant/après)..."
      jeedom2ha_diff_topic_lists \
        "$(jeedom2ha_fetch_inventory_content "${INVENTORY_BEFORE_FILE}")" \
        "$(jeedom2ha_fetch_inventory_content "${INVENTORY_AFTER_FILE}")"
      echo ""
    fi
  fi
  echo ""
fi

# =============================================================================
# STEP 5 — Vérification discovery post-sync (si cleanup actif)
# =============================================================================

if [[ "${CLEANUP_DISCOVERY}" == "true" && "${SKIP_POST_DEPLOY}" == "false" \
      && -n "${_mqtt_host}" ]]; then
  echo "--- [5/5] Vérification topics discovery post-sync..."
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash -s -- \
    "${_mqtt_host}" "${_mqtt_port}" "${_mqtt_user}" "${_mqtt_pass}" <<'REMOTE'
set -euo pipefail
MQTT_HOST="$1"; MQTT_PORT="$2"; MQTT_USER="$3"; MQTT_PASS="$4"
_auth=(-h "${MQTT_HOST}" -p "${MQTT_PORT}")
[[ -n "${MQTT_USER}" ]] && _auth+=(-u "${MQTT_USER}" -P "${MQTT_PASS}")
command -v mosquitto_sub &>/dev/null || { echo "  mosquitto_sub absent — skip."; exit 0; }
FOUND=$(mosquitto_sub "${_auth[@]}" -W 2 \
  -t 'homeassistant/+/+/config' \
  -F '%t' 2>/dev/null || true)
FOUND=$(echo "${FOUND}" | grep '/jeedom2ha_' || true)
_n=$(echo "${FOUND}" | grep -c 'jeedom2ha_' 2>/dev/null || echo 0)
echo "  ${_n} topic(s) présent(s) sur le broker après sync."
echo "${FOUND}" | while IFS= read -r _t; do [[ -n "${_t}" ]] && echo "    + ${_t}"; done
REMOTE
  echo ""
fi

if [[ "${SKIP_POST_DEPLOY}" == "true" ]]; then
  echo "WARNING: aucun tag de déploiement créé : --skip-post-deploy ne confirme pas le healthcheck." >&2
else
  jeedom2ha_create_and_push_deploy_tag "${_deploy_sha}" "${_deploy_ts}"
fi
echo ""
echo "  Commande de rollback prête :"
printf '    ./scripts/deploy-to-box.sh --rollback %q\n' "${BACKUP_ARCHIVE}"
echo "======================================================================="
echo "  Deploy complete."
echo "======================================================================="
