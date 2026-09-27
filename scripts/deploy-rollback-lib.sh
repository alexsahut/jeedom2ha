#!/bin/bash
# =============================================================================
# deploy-rollback-lib.sh
#
# Bibliothèque partagée pour le mode --rollback de scripts/deploy-to-box.sh
# (points 5, 6, 7 de la revue P1/demandes terrain). Comme
# scripts/deploy-version-file.sh, ce fichier ne fait AUCUNE hypothèse sur
# ssh/scp : il est sourcé
#   - en local par les tests unitaires (tests/unit/test_deploy_rollback_lib.py),
#     avec `sudo` stubbé en simple passthrough (aucun vrai compte www-data
#     requis) et des fixtures tar.gz / répertoires temporaires locaux,
#   - qu'à distance par deploy-to-box.sh, qui envoie ce fichier sur l'entrée
#     standard d'une commande `ssh ... bash -s -- <args>` (même convention
#     que VERSION_FILE_LIB), avant le script principal qui appelle ces
#     fonctions avec les vrais chemins de la box.
# Les appels sudo restent explicites par commande (pas de `sudo bash -s`
# global) pour rester au plus près du comportement déjà en place.
# =============================================================================

# jeedom2ha_validate_rollback_archive <archive>
# Point 5 — la validation lit la liste des entrées de l'archive UNE SEULE
# FOIS dans une variable, puis teste sur cette valeur déjà capturée : aucun
# pipe direct entre `tar -tzf` et `grep -q` sous pipefail. L'ancien code
# pipait `tar -tzf ... | grep -Eq ...` : si grep trouvait sa correspondance
# sur les toutes premières lignes et sortait avant que tar ait fini d'écrire
# le reste de la liste, tar recevait SIGPIPE et pipefail faisait échouer tout
# le pipeline même quand l'archive était en réalité valide.
jeedom2ha_validate_rollback_archive() {
  local archive="$1"
  local listing
  listing=$(tar -tzf "${archive}") || {
    echo "ERROR: lecture de l'archive impossible: ${archive}" >&2
    return 1
  }
  grep -Eq '^jeedom2ha(/|$)' <<< "${listing}" || {
    echo "ERROR: archive incompatible (racine jeedom2ha/ absente): ${archive}" >&2
    return 1
  }
  if grep -Ev '^jeedom2ha(/|$)' <<< "${listing}" >/dev/null; then
    echo "ERROR: archive incompatible (contenu hors jeedom2ha/): ${archive}" >&2
    return 1
  fi
  return 0
}

# jeedom2ha_backup_plugin_dir <plugin_path> <backup_dir> <owner> <prefix> <required>
# Archive <plugin_path> (code + data/ inclus, aucune exclusion) dans une
# nouvelle archive horodatée sous <backup_dir> — dossier 700, archive 600,
# même format que le backup de pré-déploiement (point 4b). <prefix>
# distingue le type d'archive (ex: "jeedom2ha" vs "jeedom2ha-pre-rollback").
# Si <plugin_path> est absent : échoue (return 1) quand <required>="true",
# sinon se contente d'un avertissement et retourne 0 (rien à perdre).
# En cas de succès, imprime sur stdout une ligne
#   __JEEDOM2HA_BACKUP_ARCHIVE__=<chemin>
# que l'appelant peut extraire de la sortie capturée (même convention que
# le backup de pré-déploiement dans deploy-to-box.sh).
jeedom2ha_backup_plugin_dir() {
  local plugin_path="$1" backup_dir="$2" owner="$3" prefix="$4" required="${5:-true}"

  sudo mkdir -p "${backup_dir}"
  sudo chmod 700 "${backup_dir}"
  sudo chown "${owner}" "${backup_dir}"

  if [[ ! -d "${plugin_path}" ]]; then
    if [[ "${required}" == "true" ]]; then
      echo "ERROR: plugin absent à ${plugin_path}; aucun rollback sûr ne peut être garanti." >&2
      return 1
    fi
    echo "  Aucun plugin en place à ${plugin_path} — backup ignoré (rien à perdre)." >&2
    return 0
  fi

  local archive
  archive=$(sudo mktemp "${backup_dir}/${prefix}-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX.tar.gz")
  sudo tar -czf "${archive}" -C "$(dirname "${plugin_path}")" "$(basename "${plugin_path}")"
  sudo chmod 600 "${archive}"
  sudo chown "${owner}" "${archive}"
  echo "__JEEDOM2HA_BACKUP_ARCHIVE__=${archive}"
  echo "  Backup créé: ${archive} (600, ${owner}) — dossier ${backup_dir} (700, ${owner})."
}

# jeedom2ha_stop_daemon_with_pid_fallback <pid_file>
# Point 6 — le rollback ne doit jamais rester bloqué par un plugin cassé.
# Tente d'abord l'arrêt via jeedom2ha_stop_via_plugin_class (fonction que
# l'appelant doit définir — sur la box réelle, elle enveloppe
# jeedom2ha::deamon_stop(); dans les tests, un stub simule succès/échec).
# Si cet appel échoue, repli sur un arrêt direct du process www-data via son
# PID file (SIGTERM puis SIGKILL après 2s si toujours vivant — même pattern
# que le stop défensif déjà utilisé pour main.py ailleurs dans
# deploy-to-box.sh). Ne retourne jamais un échec : le rollback (restauration
# de l'archive) doit continuer dans tous les cas.
jeedom2ha_stop_daemon_with_pid_fallback() {
  local pid_file="$1"

  if jeedom2ha_stop_via_plugin_class; then
    echo "  Daemon arrêté via jeedom2ha::deamon_stop()."
    return 0
  fi
  echo "  jeedom2ha::deamon_stop() a échoué (plugin probablement cassé) — repli PID file." >&2

  if ! sudo test -f "${pid_file}"; then
    echo "  Aucun PID file (${pid_file}) — aucun processus daemon trouvé, on continue."
    return 0
  fi

  local pid
  pid=$(sudo cat "${pid_file}" 2>/dev/null | tr -d '[:space:]')
  if [[ -z "${pid}" || ! "${pid}" =~ ^[0-9]+$ ]]; then
    echo "  PID file invalide (${pid_file}) — rien à tuer."
    return 0
  fi

  if ! sudo kill -0 "${pid}" 2>/dev/null; then
    echo "  PID file présent (PID ${pid}) mais processus introuvable — rien à tuer."
    return 0
  fi

  echo "  Arrêt via PID file (www-data, PID ${pid}) → SIGTERM"
  sudo kill "${pid}" 2>/dev/null || true
  sleep 2
  if sudo kill -0 "${pid}" 2>/dev/null; then
    echo "  Processus persistant → SIGKILL (PID ${pid})"
    sudo kill -9 "${pid}" 2>/dev/null || true
  fi
  return 0
}
