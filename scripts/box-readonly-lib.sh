#!/bin/bash
# Read-only configuration primitives shared by deployment and parity capture.
# Source only: no SSH or other side effects until a function is called.

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

# Génère (stdout) du bash source qui reconstruit MQTT_USER/MQTT_PASS et
# écrit, dans un dossier temporaire chmod 700 supprimé immédiatement après
# usage (trap EXIT), les fichiers de config par défaut de mosquitto_sub et
# mosquitto_pub (chmod 600) — les credentials MQTT ne transitent jamais par
# l'argv de ssh ni de mosquitto_sub/mosquitto_pub, ni localement ni sur la
# box (CC-20).
#
# IMPORTANT : la box cible réelle tourne mosquitto-clients
# 2.0.11-1+deb11u2, qui N'A PAS l'option -o (celle-ci n'existe que depuis
# mosquitto 2.1 — voir mosquitto_sub(1)/mosquitto_pub(1) : "-o config-file
# ... Available from version 2.1", et client/client_shared.c au tag
# eclipse/mosquitto v2.0.11 où -o est absent de client_config_line_proc).
# Sur 2.0.11, le seul mécanisme sans argv est le *fichier de config par
# défaut* : client_config_load() (client/client_shared.c) cherche
# $XDG_CONFIG_HOME/mosquitto_sub ou .../mosquitto_pub (à défaut
# $HOME/.config/mosquitto_sub|mosquitto_pub) et parse chaque ligne via
# strtok(line, " ") pour l'option puis strtok(NULL, "") pour le reste de la
# ligne pris tel quel comme valeur (pas de guillemets ni d'échappement) —
# donc un mot de passe contenant des espaces est transmis correctement,
# tant qu'il ne contient pas de retour à la ligne.
#
# jeedom2ha_mqtt_run() ci-dessous positionne XDG_CONFIG_HOME uniquement le
# temps de l'appel à mosquitto_sub/mosquitto_pub (pas d'export global).
#
# Prévu pour être concaténé en préfixe d'un heredoc distant quoté
# (<<'REMOTE') via :
#   { echo 'set -euo pipefail'; jeedom2ha_mqtt_auth_snippet; cat <<'REMOTE' ... REMOTE; } \
#     | ssh ... bash -s -- <args non secrets>
# printf %q restitue MQTT_USER/MQTT_PASS octet pour octet quels que soient
# les caractères spéciaux qu'ils contiennent (hors retour à la ligne, non
# supporté par le format ligne-par-ligne de mosquitto : on échoue
# explicitement dans ce cas plutôt que de retomber sur l'argv).
jeedom2ha_mqtt_auth_snippet() {
  local _u _pw
  printf -v _u '%q' "${_mqtt_user}"
  printf -v _pw '%q' "${_mqtt_pass}"
  cat <<SNIPPET
MQTT_USER=${_u}
MQTT_PASS=${_pw}
if [[ -n "\${MQTT_USER}" ]]; then
  if [[ "\${MQTT_USER}" == *\$'\n'* || "\${MQTT_PASS}" == *\$'\n'* ]]; then
    echo "ERROR: identifiants MQTT contenant un retour à la ligne — incompatible avec le fichier de config mosquitto (format ligne par ligne, sans échappement). Voir CC-20." >&2
    exit 1
  fi
  _mqtt_auth_dir=\$(mktemp -d)
  chmod 700 "\${_mqtt_auth_dir}"
  trap 'rm -rf "\${_mqtt_auth_dir}"' EXIT
  printf -- '-u %s\n-P %s\n' "\${MQTT_USER}" "\${MQTT_PASS}" > "\${_mqtt_auth_dir}/mosquitto_sub"
  cp "\${_mqtt_auth_dir}/mosquitto_sub" "\${_mqtt_auth_dir}/mosquitto_pub"
  chmod 600 "\${_mqtt_auth_dir}/mosquitto_sub" "\${_mqtt_auth_dir}/mosquitto_pub"
fi
# jeedom2ha_mqtt_run <mosquitto_sub|mosquitto_pub> [args...]
# N'exporte XDG_CONFIG_HOME que pour cette seule invocation (mosquitto
# 2.0.x default config file mechanism — pas d'option -o, absente avant
# mosquitto 2.1).
jeedom2ha_mqtt_run() {
  local _bin="\$1"; shift
  if [[ -n "\${_mqtt_auth_dir:-}" ]]; then
    XDG_CONFIG_HOME="\${_mqtt_auth_dir}" "\${_bin}" "\$@"
  else
    "\${_bin}" "\$@"
  fi
  }
SNIPPET
}
