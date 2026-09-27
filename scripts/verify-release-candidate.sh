#!/usr/bin/env bash
# =============================================================================
# verify-release-candidate.sh
#
# Vérification à blanc (lecture seule) avant publication Market — voir
# docs/release-market.md §6. Ne crée aucun tag, ne pousse aucune branche, ne
# touche ni au Market ni à la box (une seule commande SSH en lecture, `cat`
# du fichier VERSION).
#
# Cible SSH configurable par variable d'environnement, même mécanisme que
# scripts/deploy-to-box.sh : JEEDOM_BOX_HOST (obligatoire), JEEDOM_BOX_USER
# (défaut : asahut), JEEDOM_BOX_PORT (défaut : 22), JEEDOM_BOX_PATH (défaut :
# /var/www/html/plugins/jeedom2ha). Un `.env` à la racine du repo est chargé
# s'il existe, comme dans deploy-to-box.sh.
#
# La logique de comparaison (tag <-> commit, candidat <-> box) vit dans
# verify-release-candidate-lib.sh, testée sans ssh dans
# tests/unit/test_verify_release_candidate.py.
#
# Usage: scripts/verify-release-candidate.sh <candidat-git-ref-ou-sha>
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
LIB="${SCRIPT_DIR}/verify-release-candidate-lib.sh"
# shellcheck disable=SC1090
source "${LIB}"

if [[ -f "${ENV_FILE}" ]]; then
  set -o allexport
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +o allexport
fi

JEEDOM_BOX_HOST="${JEEDOM_BOX_HOST:-}"
JEEDOM_BOX_USER="${JEEDOM_BOX_USER:-asahut}"
JEEDOM_BOX_PORT="${JEEDOM_BOX_PORT:-22}"
JEEDOM_BOX_PATH="${JEEDOM_BOX_PATH:-/var/www/html/plugins/jeedom2ha}"

CANDIDATE_REF="${1:?candidat requis : SHA ou ref à vérifier, ex. \$(git rev-parse HEAD)}"
[[ -z "${JEEDOM_BOX_HOST}" ]] && { echo "ERROR: JEEDOM_BOX_HOST is not set." >&2; exit 1; }

# Toujours déréférencer en commit, même pour le candidat : accepte aussi bien
# un SHA de commit qu'une ref de tag annoté passée par erreur en candidat.
CANDIDATE_SHA="$(git -C "${REPO_ROOT}" rev-parse "${CANDIDATE_REF}^{commit}")"
echo "SHA candidat : ${CANDIDATE_SHA}"

PLUGIN_VERSION="$(git -C "${REPO_ROOT}" show "${CANDIDATE_SHA}:plugin_info/info.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["pluginVersion"])')"
echo "pluginVersion du candidat : ${PLUGIN_VERSION}"

jeedom2ha_check_tag_matches_candidate "${REPO_ROOT}" "${CANDIDATE_SHA}" "v${PLUGIN_VERSION}"

SSH_OPTS=(-p "${JEEDOM_BOX_PORT}" -o "BatchMode=yes" -o "ConnectTimeout=5" -o "StrictHostKeyChecking=accept-new")
SSH_TARGET="${JEEDOM_BOX_USER}@${JEEDOM_BOX_HOST}"

BOX_VERSION_RAW="$(ssh "${SSH_OPTS[@]}" "${SSH_TARGET}" "cat '${JEEDOM_BOX_PATH}/VERSION'" 2>/dev/null || true)"
echo "--- Lecture VERSION sur la box (${SSH_TARGET}, lecture seule) ---"

jeedom2ha_check_box_sha_matches_candidate "${CANDIDATE_SHA}" "${BOX_VERSION_RAW}"

echo "Vérification à blanc terminée : candidat conforme, strictement identique à la box."
