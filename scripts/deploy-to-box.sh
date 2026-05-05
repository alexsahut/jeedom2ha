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
# JEEDOM_ROOT est utilisé par PHP via getenv("JEEDOM_ROOT") sur la box
JEEDOM_ROOT="${JEEDOM_ROOT:-/var/www/html}"

# Initialisés par jeedom2ha_refresh_secret
LOCAL_SECRET=""
DAEMON_PORT="55080"
DAEMON_API="http://127.0.0.1:55080"

# MQTT credentials pour cleanup — initialisés par la section cleanup
_mqtt_host=""; _mqtt_port="1883"; _mqtt_user=""; _mqtt_pass=""

DRY_RUN=false
RESTART_DAEMON=false
CLEANUP_DISCOVERY=false
SKIP_POST_DEPLOY=false
STOP_DAEMON_CLEANUP=false

# --- Parse args ---
for arg in "$@"; do
  case "$arg" in
    --dry-run)            DRY_RUN=true ;;
    --restart-daemon)     RESTART_DAEMON=true ;;
    --cleanup-discovery)  CLEANUP_DISCOVERY=true ;;
    --skip-post-deploy)    SKIP_POST_DEPLOY=true ;;
    --stop-daemon-cleanup) STOP_DAEMON_CLEANUP=true ;;
    *) echo "ERROR: Unknown argument: $arg" >&2
       echo "Usage: $0 [--dry-run] [--restart-daemon] [--cleanup-discovery] [--skip-post-deploy]" >&2
       echo "       $0 --stop-daemon-cleanup  (mode dédié — incompatible avec les autres options)" >&2
       exit 1 ;;
  esac
done

# =============================================================================
# GUARDRAILS
# =============================================================================

_fail() { echo "ERROR: $*" >&2; exit 1; }

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
sudo env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
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

# =============================================================================
# STEP 1 — déploiement en 2 étapes (user SSH non-root + sudo)
#
# Étape 1a : rsync local → staging (accessible en écriture par JEEDOM_BOX_USER)
# Étape 1b : sudo promotion staging → plugin dir + permissions www-data
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

echo "--- [1/5] Deploy (staging + sudo promotion)..."

# 1a — rsync vers staging (pas de sudo requis)
echo "  1a. rsync → ${JEEDOM_STAGING_DIR}/"
ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "mkdir -p '${JEEDOM_STAGING_DIR}'"
rsync "${RSYNC_OPTS[@]}" "${REPO_ROOT}/" "${SSH_TARGET}:${JEEDOM_STAGING_DIR}/"

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

  # deamon_start() génère localSecret si absent — lire le secret APRÈS l'appel
  # set -e : fail-fast si deamon_start() retourne false ou si PHP fatal
  ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" bash <<REMOTE
set -e
sudo env JEEDOM_ROOT="${JEEDOM_ROOT}" php -r '
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

echo "======================================================================="
echo "  Deploy complete."
echo "======================================================================="
