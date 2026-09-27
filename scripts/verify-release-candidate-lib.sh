#!/bin/bash
# =============================================================================
# verify-release-candidate-lib.sh
#
# Bibliothèque partagée pour scripts/verify-release-candidate.sh. Aucun appel
# ssh/scp ici : ces fonctions reçoivent soit un dépôt git local déjà
# fetché, soit le contenu déjà lu du fichier VERSION de la box comme simple
# chaîne — jamais une connexion SSH elle-même. C'est ce qui permet de les
# tester sans jamais se connecter à la box réelle
# (tests/unit/test_verify_release_candidate.py), exactement comme
# deploy-version-file.sh pour l'écriture du fichier VERSION.
# =============================================================================

# jeedom2ha_tag_commit_sha <repo_root> <tag_ref>
# Résout <tag_ref> en SHA de COMMIT, jamais en SHA de l'objet tag lui-même.
# Un tag annoté (`git tag -a`) crée un objet tag distinct : `git rev-parse
# <tag>` seul rend le SHA de cet objet tag, pas celui du commit pointé.
# Comparer ce SHA brut à un SHA de commit échoue TOUJOURS pour un tag annoté,
# même quand le tag pointe correctement sur le bon commit (bug constaté en
# terrain : `git rev-parse v1.1.0` -> e1325f0... alors que le commit réel
# pointé est 166cb7b...). Le suffixe `^{commit}` déréférence l'objet tag
# jusqu'au commit qu'il désigne.
jeedom2ha_tag_commit_sha() {
  local repo_root="$1" tag_ref="$2"
  git -C "${repo_root}" rev-parse "${tag_ref}^{commit}"
}

# jeedom2ha_check_tag_matches_candidate <repo_root> <candidate_sha> <expected_tag>
# Si <expected_tag> n'existe pas encore, c'est informatif (attendu avant la
# 1ère publication de cette version), pas un échec. S'il existe, vérifie
# qu'il pointe, une fois déréférencé en commit via jeedom2ha_tag_commit_sha,
# exactement sur <candidate_sha> (qui doit lui aussi déjà être un SHA de
# commit, jamais un SHA de tag).
jeedom2ha_check_tag_matches_candidate() {
  local repo_root="$1" candidate_sha="$2" expected_tag="$3"
  if ! git -C "${repo_root}" rev-parse "${expected_tag}" >/dev/null 2>&1; then
    echo "[INFO] le tag ${expected_tag} n'existe pas encore (attendu avant la 1ère publication de cette version)"
    return 0
  fi
  local tag_commit_sha
  tag_commit_sha="$(jeedom2ha_tag_commit_sha "${repo_root}" "${expected_tag}")"
  if [ "${tag_commit_sha}" = "${candidate_sha}" ]; then
    echo "[OK] le tag ${expected_tag} existe déjà et pointe (une fois déréférencé en commit) exactement sur le candidat"
    return 0
  fi
  echo "[ECHEC] le tag ${expected_tag} existe mais pointe sur le commit ${tag_commit_sha} (candidat = ${candidate_sha})" >&2
  return 1
}

# jeedom2ha_box_sha_from_version_content <version_file_content>
# Extrait la valeur "sha=" du contenu du fichier VERSION (déjà lu par
# l'appelant, par ex. via `ssh ... cat VERSION`). N'exécute jamais elle-même
# de commande ssh.
jeedom2ha_box_sha_from_version_content() {
  local content="$1"
  printf '%s' "${content}" | sed -n 's/^sha=//p'
}

# jeedom2ha_box_git_status_from_version_content <version_file_content>
# Extrait la valeur "git_status=" du contenu du fichier VERSION (écrite par
# deploy-version-file.sh, cf. jeedom2ha_render_version_content). Rend une
# chaîne vide si le champ est absent (VERSION d'un ancien format).
jeedom2ha_box_git_status_from_version_content() {
  local content="$1"
  printf '%s' "${content}" | sed -n 's/^git_status=//p'
}

# jeedom2ha_check_box_sha_matches_candidate <candidate_sha> <box_version_content>
# Compare strictement <candidate_sha> au SHA extrait de <box_version_content>,
# ET exige que <box_version_content> porte git_status=clean. Un SHA committé
# identique ne suffit pas : un déploiement fait depuis un arbre de travail
# sale (git_status=dirty) peut committer le bon SHA tout en déployant un
# contenu différent de ce commit (fichiers modifiés non commités déployés
# par-dessus, jamais capturés par la comparaison de SHA seule). Échoue si le
# contenu est vide (VERSION illisible/absent sur la box, ou SSH en échec côté
# appelant), si les deux SHA diffèrent, ou si git_status n'est pas
# exactement "clean" (y compris absent) — avec un message distinct pour
# chaque cas d'échec.
jeedom2ha_check_box_sha_matches_candidate() {
  local candidate_sha="$1" box_version_content="$2"
  if [ -z "${box_version_content}" ]; then
    echo "[ECHEC] impossible de lire VERSION sur la box (SSH ou fichier absent)" >&2
    return 1
  fi
  echo "--- VERSION lu sur la box ---"
  echo "${box_version_content}"
  local box_sha
  box_sha="$(jeedom2ha_box_sha_from_version_content "${box_version_content}")"
  echo "SHA réellement déployé sur la box (source de vérité) : ${box_sha}"
  if [ "${candidate_sha}" != "${box_sha}" ]; then
    echo "[ECHEC] candidat (${candidate_sha}) différent du SHA déployé sur la box (${box_sha})" >&2
    return 1
  fi
  echo "[OK] candidat strictement identique au SHA déployé sur la box"
  local box_git_status
  box_git_status="$(jeedom2ha_box_git_status_from_version_content "${box_version_content}")"
  if [ "${box_git_status}" != "clean" ]; then
    echo "[ECHEC] arbre de travail sale au moment du déploiement (git_status=${box_git_status:-absent}, attendu clean) : le SHA committé peut ne pas refléter le contenu réellement déployé sur la box (fichiers modifiés non commités déployés par-dessus)" >&2
    return 1
  fi
  echo "[OK] git_status=clean confirmé : le contenu déployé correspond exactement au commit ${box_sha}, sans modification locale non commitée"
  return 0
}
