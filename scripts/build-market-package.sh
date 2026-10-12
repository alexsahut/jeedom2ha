#!/usr/bin/env bash
# Construit le paquet Market épuré de jeedom2ha (story A2, décision D2).
#
# Deux modes, AUCUN ne pousse quoi que ce soit (aucun `git push`, jamais vers beta/stable) :
#
#   build   <sha> --output DIR [--tarball FILE]
#       Arbre épuré = SHA de main filtré par .github/market-package/manifest.txt
#       (docs/fr_FR/ inclus). Déterministe : même SHA + même manifeste => même arbre.
#
#   release <vX.Y.Z> --source <sha> [--base-ref beta] [--branch release/vX.Y.Z] [--allow-untagged]
#       Crée en LOCAL la branche release/vX.Y.Z depuis --base-ref (défaut origin/beta, sinon
#       beta), remplace son contenu par le paquet épuré (+ fichiers `retain` du manifeste,
#       option 1) et crée un commit unique « release vX.Y.Z (source <sha>) ».
#       Le push et la PR restent des actions humaines (commandes affichées en fin de script).
#
# Le SHA source doit porter un tag deploy-* (déjà déployé/validé sur la box), sauf
# --allow-untagged (tests à blanc uniquement).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${MARKET_PACKAGE_REPO:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
PY="$(cd "${SCRIPT_DIR}/.." && pwd)/.github/market-package/market_package.py"

usage() { sed -n '2,19p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }
die() { echo "ERREUR: $*" >&2; exit 1; }

[ $# -ge 1 ] || { usage; exit 2; }
MODE="$1"; shift

case "${MODE}" in
  -h|--help) usage; exit 0 ;;
  build)
    SHA_ARG="${1:?SHA source requis}"; shift
    OUTPUT=""; TARBALL=()
    while [ $# -gt 0 ]; do
      case "$1" in
        --output) OUTPUT="${2:?}"; shift 2 ;;
        --tarball) TARBALL=(--tarball "${2:?}"); shift 2 ;;
        *) die "option inconnue: $1" ;;
      esac
    done
    [ -n "${OUTPUT}" ] || die "--output DIR requis"
    SHA="$(git -C "${REPO_ROOT}" rev-parse --verify "${SHA_ARG}^{commit}")" || die "SHA introuvable: ${SHA_ARG}"
    python3 "${PY}" build "${SHA}" "${OUTPUT}" --repo "${REPO_ROOT}" ${TARBALL[@]+"${TARBALL[@]}"}
    python3 "${PY}" check "${OUTPUT}"
    ;;
  release)
    VERSION="${1:?version vX.Y.Z requise}"; shift
    SOURCE=""; BASE_REF=""; BRANCH=""; ALLOW_UNTAGGED=0
    while [ $# -gt 0 ]; do
      case "$1" in
        --source) SOURCE="${2:?}"; shift 2 ;;
        --base-ref) BASE_REF="${2:?}"; shift 2 ;;
        --branch) BRANCH="${2:?}"; shift 2 ;;
        --allow-untagged) ALLOW_UNTAGGED=1; shift ;;
        *) die "option inconnue: $1" ;;
      esac
    done
    [[ "${VERSION}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "version invalide (attendu vX.Y.Z): ${VERSION}"
    [ -n "${SOURCE}" ] || die "--source <sha> requis"
    BRANCH="${BRANCH:-release/${VERSION}}"
    case "${BRANCH}" in
      main|beta|stable|origin/*) die "branche de release interdite: ${BRANCH}" ;;
    esac
    SHA="$(git -C "${REPO_ROOT}" rev-parse --verify "${SOURCE}^{commit}")" || die "SHA source introuvable: ${SOURCE}"
    if [ -z "${BASE_REF}" ]; then
      if git -C "${REPO_ROOT}" rev-parse --verify -q "origin/beta^{commit}" >/dev/null; then
        BASE_REF="origin/beta"
      else
        BASE_REF="beta"
      fi
    fi
    BASE_SHA="$(git -C "${REPO_ROOT}" rev-parse --verify "${BASE_REF}^{commit}")" || die "base-ref introuvable: ${BASE_REF}"
    if [ "${ALLOW_UNTAGGED}" -ne 1 ]; then
      git -C "${REPO_ROOT}" tag --points-at "${SHA}" 'deploy-*' | grep -q . \
        || die "le SHA ${SHA} ne porte aucun tag deploy-* (SHA non déployé/validé sur la box)"
    fi
    if git -C "${REPO_ROOT}" rev-parse --verify -q "refs/heads/${BRANCH}" >/dev/null; then
      die "la branche locale ${BRANCH} existe déjà (supprime-la ou choisis --branch)"
    fi

    WORK="$(mktemp -d)"
    CREATED=0
    cleanup() {
      git -C "${REPO_ROOT}" worktree remove --force "${WORK}/wt" >/dev/null 2>&1 || true
      # Échec en cours de route : ne laisse pas de branche locale à moitié construite.
      [ "${CREATED}" -eq 1 ] || git -C "${REPO_ROOT}" branch -D "${BRANCH}" >/dev/null 2>&1 || true
      rm -rf "${WORK}"
    }
    trap cleanup EXIT

    python3 "${PY}" build "${SHA}" "${WORK}/pkg" --repo "${REPO_ROOT}" --with-retained
    python3 "${PY}" check "${WORK}/pkg" --release-tree

    git -C "${REPO_ROOT}" worktree add -q -b "${BRANCH}" "${WORK}/wt" "${BASE_SHA}"

    # Remplacement contrôlé du contenu : on vide l'arbre de beta puis on pose le paquet.
    git -C "${WORK}/wt" rm -r -q --ignore-unmatch . >/dev/null
    find "${WORK}/wt" -mindepth 1 -maxdepth 1 -not -name .git -exec rm -rf {} +
    cp -a "${WORK}/pkg/." "${WORK}/wt/"
    git -C "${WORK}/wt" add -A
    git -C "${WORK}/wt" -c user.name="${GIT_AUTHOR_NAME:-jeedom2ha release}" \
      -c user.email="${GIT_AUTHOR_EMAIL:-release@jeedom2ha.invalid}" \
      commit -q --allow-empty -m "release ${VERSION} (source ${SHA})"
    # La worktree temporaire disparaît (trap) ; la branche locale reste.
    CREATED=1
    NEW="$(git -C "${WORK}/wt" rev-parse HEAD)"
    echo "Branche locale ${BRANCH} créée: ${NEW}"
    echo "  base : ${BASE_REF} (${BASE_SHA})"
    echo "  commit : release ${VERSION} (source ${SHA})"
    TARGET="${BASE_REF#origin/}"
    case "${TARGET}" in beta|stable) ;; *) TARGET="<beta|stable>" ;; esac
    cat <<MSG

Aucun push effectué. Étapes suivantes (HUMAINES, après go explicite) :
  git push -u origin ${BRANCH}
  # PR ${BRANCH} -> ${TARGET}, à fusionner par MERGE COMMIT (jamais squash, jamais fast-forward) :
  #   gh pr create --base ${TARGET} --head ${BRANCH} --title "release ${VERSION} (source ${SHA:0:7})"
  #   gh pr merge --merge
MSG
    ;;
  *) usage; exit 2 ;;
esac
