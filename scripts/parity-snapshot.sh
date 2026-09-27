#!/bin/bash
# VM -> box, read-only: two HTTP GETs and one MQTT subscription. No deployment.
set +x
set -euo pipefail
umask 077
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${JEEDOM2HA_PARITY_PYTHON:-python3}"
TOOL="${REPO_ROOT}/resources/daemon/tools/parity_snapshot.py"

case "${1:-}" in
  diff) shift; exec "${PYTHON}" "${TOOL}" diff "$@" ;;
  capture) shift ;;
  *) echo "Usage: $0 capture [--label before|after] [--output /tmp/file.json] | diff --before FILE --after FILE" >&2; exit 2 ;;
esac
label=before
output="/tmp/jeedom2ha-parity-probe-$(date -u +%Y%m%dT%H%M%SZ).json"
while (( $# )); do
  case "$1" in
    --label) label="${2:?Missing label}"; shift 2 ;;
    --output) output="${2:?Missing output path}"; shift 2 ;;
    *) echo "Unknown capture option: $1" >&2; exit 2 ;;
  esac
done
[[ "$label" == before || "$label" == after ]] || exit 2
# Actual VM SSH alias; optional override is an alias too, never credentials.
SSH_TARGET="${JEEDOM2HA_PARITY_SSH_TARGET:-jeedom-deploy}"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=10)
JEEDOM_ROOT="${JEEDOM_ROOT:-/var/www/html}"
LOCAL_PORT="${JEEDOM2HA_PARITY_LOCAL_PORT:-15508}"
source "${SCRIPT_DIR}/box-readonly-lib.sh"
work_dir=$(mktemp -d /tmp/jeedom2ha-parity.XXXXXXXX)
chmod 700 "$work_dir"
control_socket="$work_dir/ssh"
cleanup() {
  ssh "${SSH_OPTS[@]}" -S "$control_socket" -O exit "$SSH_TARGET" >/dev/null 2>&1 || true
  rm -rf "$work_dir"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
jeedom2ha_refresh_secret
jeedom2ha_refresh_mqtt_credentials
[[ "$DAEMON_PORT" =~ ^[0-9]+$ && "$LOCAL_PORT" =~ ^[0-9]+$ ]] || exit 2
(( DAEMON_PORT > 0 && DAEMON_PORT < 65536 && LOCAL_PORT > 0 && LOCAL_PORT < 65536 )) || exit 2
[[ -n "$_mqtt_host" ]] || { echo 'MQTT host unavailable' >&2; exit 2; }
ssh "${SSH_OPTS[@]}" -M -S "$control_socket" -fN -o ExitOnForwardFailure=yes \
  -L "127.0.0.1:${LOCAL_PORT}:127.0.0.1:${DAEMON_PORT}" "$SSH_TARGET"
# Exact deploy inventory authentication mechanism, sent through SSH stdin.
# Only temporary auth files on the box; no backup/inventory file is written there.
{
  echo 'set +x; set -euo pipefail; umask 077'
  jeedom2ha_mqtt_auth_snippet
  printf 'MQTT_HOST=%q\nMQTT_PORT=%q\n' "$_mqtt_host" "$_mqtt_port"
  cat <<'REMOTE'
rc=0
jeedom2ha_mqtt_run mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" \
  -W 2 -t 'homeassistant/+/+/config' -F '%t' || rc=$?
# mosquitto_sub 2.0.x returns 27 when the bounded subscription ends.
[[ "$rc" == 0 || "$rc" == 27 ]] || exit "$rc"
REMOTE
} | ssh "${SSH_OPTS[@]}" -S "$control_socket" "$SSH_TARGET" bash -s > "$work_dir/topics"
export JEEDOM2HA_LOCAL_SECRET="$LOCAL_SECRET"
unset JEEDOM2HA_LOCAL_SECRET_FILE
"${PYTHON}" "${TOOL}" capture --base-url "http://127.0.0.1:${LOCAL_PORT}" \
  --mqtt-host "$_mqtt_host" --mqtt-port "$_mqtt_port" \
  --mqtt-inventory-file "$work_dir/topics" --label "$label" --output "$output"
