#!/bin/bash
# =============================================================================
# deploy-version-file.sh
#
# Bibliothèque partagée pour l'écriture atomique du fichier VERSION à la
# racine du plugin (point 1c). Ce fichier ne contient AUCUN appel
# ssh/scp/rsync : il est sourcé aussi bien
#   - en local par les tests unitaires (tests/unit/test_deploy_version_file.py),
#     avec un répertoire temporaire jouant le rôle de la racine du plugin,
#   - qu'à distance par scripts/deploy-to-box.sh, qui envoie ce fichier sur
#     l'entrée standard d'une commande `ssh ... sudo bash -s` puis appelle la
#     fonction jeedom2ha_write_version_file_atomic.
# C'est exactement la même fonction bash qui s'exécute dans les deux cas —
# seul l'environnement (local vs. distant) change. Cela permet de prouver la
# logique sans jamais se connecter à la box Jeedom réelle.
# =============================================================================

# jeedom2ha_render_version_content <version> <sha> <deployed_at_utc> <git_status>
# Construit le contenu texte du fichier VERSION (format key=value, une entrée
# par ligne), lu par resources/daemon/main.py (_read_deploy_sha).
jeedom2ha_render_version_content() {
  local version="$1" sha="$2" deployed_at="$3" git_status="$4"
  printf 'version=%s\nsha=%s\ndeployed_at=%s\ngit_status=%s\n' \
    "${version}" "${sha}" "${deployed_at}" "${git_status}"
}

# jeedom2ha_write_version_file_atomic <target_dir> <content>
# Écrit <content> dans <target_dir>/VERSION de façon atomique : un fichier
# temporaire "VERSION.tmp.$$" est écrit puis déplacé (mv) sur VERSION, dans
# un seul appel de fonction — aucun état intermédiaire n'est jamais visible
# depuis l'extérieur. Relit ensuite le fichier écrit et l'affiche sur
# stdout, pour vérification par l'appelant.
jeedom2ha_write_version_file_atomic() {
  local target_dir="$1"
  local content="$2"
  local tmp_file="${target_dir}/VERSION.tmp.$$"

  printf '%s' "${content}" > "${tmp_file}"
  mv "${tmp_file}" "${target_dir}/VERSION"
  cat "${target_dir}/VERSION"
}
