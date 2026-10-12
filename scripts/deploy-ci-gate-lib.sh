#!/bin/bash
# =============================================================================
# deploy-ci-gate-lib.sh
#
# Garde-fou CI de scripts/deploy-to-box.sh (CC-50). Bibliothèque sans effet de
# bord hormis les appels `gh api` (mockables en testant avec une fonction `gh`
# shell) ; testée par tests/unit/test_deploy_ci_gate_lib.py.
#
# Pourquoi : l'endpoint commits/<sha>/check-runs renvoie les check-runs de
# TOUTES les check-suites du SHA, y compris celles déclenchées par un
# événement `schedule` (nightly/cron), dont l'état n'a rien à voir avec la
# qualité du commit. On ne retient donc que les workflow runs d'événement
# push / pull_request / workflow_dispatch, puis les check-runs de leurs
# check-suites.
#
# CC-59 : on ne juge QUE les runs de la branche déployée (head_branch), `main`
# par défaut, surchargeable via JEEDOM2HA_DEPLOY_CI_BRANCH. Plusieurs branches
# (ex. claude/..., fix/...) peuvent pointer sur le même SHA ; l'annulation du
# run de push de l'une d'elles ne doit pas bloquer le déploiement depuis main.
# Pour chaque workflow, seule la dernière tentative (run_number, puis
# run_attempt, puis id) compte : un run annulé puis relancé en vert est vert.
# =============================================================================

# jeedom2ha_verify_ci_green <owner/repo> <sha>
# Code 0 si la CI pertinente est verte ; sinon message sur stderr et code 1.
# Une absence de check-run pertinent est un REFUS, jamais un succès implicite.
# Branche jugée : ${JEEDOM2HA_DEPLOY_CI_BRANCH:-main}.
jeedom2ha_verify_ci_green() {
  local repo="$1" sha="$2" branch="${JEEDOM2HA_DEPLOY_CI_BRANCH:-main}"
  local runs latest_runs run_lines suite_ids check_runs check_lines status conclusion

  runs=$(gh api --paginate -H "Accept: application/vnd.github+json" \
    "repos/${repo}/actions/runs?head_sha=${sha}&per_page=100") \
    || { echo "ERROR: Impossible de lire les workflow runs GitHub pour ${sha}." >&2; return 1; }
  # --paginate concatène une réponse JSON par page : jq les traite une à une.
  # Par workflow, on ne garde que la dernière tentative sur la branche jugée.
  latest_runs=$(printf '%s' "${runs}" | jq -c -s --arg branch "${branch}" '
    [ .[].workflow_runs[]?
      | select(.head_branch == $branch)
      | select(.event == "push" or .event == "pull_request" or .event == "workflow_dispatch")
      | select(.check_suite_id != null) ]
    | group_by(.workflow_id)
    | map(max_by([(.run_number // 0), (.run_attempt // 1), (.id // 0)]))') \
    || { echo "ERROR: Réponse actions/runs illisible pour ${sha}." >&2; return 1; }
  if [[ "${latest_runs}" == "[]" ]]; then
    echo "ERROR: Refus de déployer ${sha} : aucun workflow run push/pull_request/workflow_dispatch trouvé sur la branche ${branch}." >&2
    return 1
  fi
  # Statut/conclusion du run lui-même (si fournis) : en cours ou non vert = refus.
  run_lines=$(printf '%s' "${latest_runs}" | jq -r '.[] | [(.status // "completed"), (.conclusion // "success")] | @tsv') \
    || { echo "ERROR: Réponse actions/runs illisible pour ${sha}." >&2; return 1; }
  while IFS=$'\t' read -r status conclusion; do
    if [[ "${status}" != "completed" ]]; then
      echo "ERROR: Refus de déployer ${sha} : workflow run non terminé sur ${branch} (${status})." >&2
      return 1
    fi
    case "${conclusion}" in
      success|skipped|neutral) ;;
      *) echo "ERROR: Refus de déployer ${sha} : CI non verte (${status}/${conclusion})." >&2
         return 1 ;;
    esac
  done <<< "${run_lines}"
  suite_ids=$(printf '%s' "${latest_runs}" | jq -c '[.[].check_suite_id] | unique')

  check_runs=$(gh api --paginate -H "Accept: application/vnd.github+json" \
    "repos/${repo}/commits/${sha}/check-runs?per_page=100") \
    || { echo "ERROR: Impossible de lire les check-runs GitHub pour ${sha}." >&2; return 1; }
  check_lines=$(printf '%s' "${check_runs}" | jq -r -s --argjson ids "${suite_ids}" '
    .[].check_runs[]?
    | select(.check_suite.id as $id | $ids | index($id))
    | [.status, .conclusion] | @tsv') \
    || { echo "ERROR: Réponse check-runs illisible pour ${sha}." >&2; return 1; }
  if [[ -z "${check_lines}" ]]; then
    echo "ERROR: Refus de déployer ${sha} : aucun check-run GitHub trouvé pour les workflow runs push/pull_request/workflow_dispatch." >&2
    return 1
  fi

  # Un check-run encore en cours (in_progress/queued) doit être un refus, pas
  # un succès implicite — on ne l'accepte donc que si status="completed".
  # Une fois "completed", seules success/skipped/neutral sont des conclusions
  # valides (ex: Burn-In "skipped" hors planning burn-in) ; tout le reste
  # (failure, cancelled, timed_out, action_required, stale, ...) est refusé.
  while IFS=$'\t' read -r status conclusion; do
    if [[ "${status}" != "completed" ]]; then
      echo "ERROR: Refus de déployer ${sha} : check-run non terminé (${status}/${conclusion})." >&2
      return 1
    fi
    case "${conclusion}" in
      success|skipped|neutral) ;;
      *) echo "ERROR: Refus de déployer ${sha} : CI non verte (${status}/${conclusion})." >&2
         return 1 ;;
    esac
  done <<< "${check_lines}"
  return 0
}
