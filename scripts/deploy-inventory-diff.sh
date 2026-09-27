#!/bin/bash
# =============================================================================
# deploy-inventory-diff.sh
#
# Bibliothèque partagée pour le diff d'inventaire MQTT affiché par
# deploy-to-box.sh (point 8). Cette fonction est pure bash : elle ne fait
# aucun ssh/mosquitto_sub elle-même — le fetch des deux fichiers d'inventaire
# (avant/après) reste dans deploy-to-box.sh via ssh+cat ; seule la logique de
# comptage/diff, qui ne dépend d'aucune box réelle, vit ici. C'est ce qui la
# rend testable localement (tests/unit/test_deploy_inventory_diff.py) sans
# jamais se connecter à un broker MQTT.
# =============================================================================

# jeedom2ha_diff_topic_lists <before_content> <after_content>
# <before_content>/<after_content> : contenu texte (une entrée jeedom2ha_*
# par ligne, déjà trié/dédupliqué par jeedom2ha_inventory_discovery) — chaîne
# vide autorisée (aucun topic, ou fichier introuvable). Affiche sur stdout :
#   - le nombre d'entités avant et après ;
#   - la liste des topics ajoutés (présents après, absents avant) ;
#   - la liste des topics retirés (présents avant, absents après).
jeedom2ha_diff_topic_lists() {
  local before="$1" after="$2"

  local n_before=0 n_after=0
  [[ -n "${before}" ]] && n_before=$(printf '%s\n' "${before}" | grep -c .)
  [[ -n "${after}"  ]] && n_after=$(printf '%s\n'  "${after}"  | grep -c .)
  echo "  Entités avant : ${n_before} | Entités après : ${n_after}"

  local added removed
  added=$(comm -13 <(printf '%s\n' "${before}" | sort) <(printf '%s\n' "${after}" | sort) | grep -v '^$' || true)
  removed=$(comm -23 <(printf '%s\n' "${before}" | sort) <(printf '%s\n' "${after}" | sort) | grep -v '^$' || true)

  if [[ -n "${added}" ]]; then
    echo "  Topics ajoutés :"
    printf '%s\n' "${added}" | sed 's/^/    + /'
  else
    echo "  Topics ajoutés : aucun"
  fi

  if [[ -n "${removed}" ]]; then
    echo "  Topics retirés :"
    printf '%s\n' "${removed}" | sed 's/^/    - /'
  else
    echo "  Topics retirés : aucun"
  fi
}
