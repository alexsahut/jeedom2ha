# Story 19-4 — mesure terrain (lecture seule), 2026-09-29

Box 192.168.1.21, tête `5b14243`. Captures via `scripts/parity-snapshot.sh capture`
(before) + `GET /system/published_scope` + `GET /system/diagnostics`, aucune écriture.
Fichiers bruts (pas de secret, pas de valeur capteur) :
`/tmp/jeedom2ha-19-4-mesure.json`, `/tmp/jeedom2ha-19-4-scope.json`,
`/tmp/jeedom2ha-19-4-diag.json`.

## Répartition scope explicite (`/system/published_scope`)

292 équipements au total. `decision_source` par niveau :

| niveau | effective_state | count |
|---|---|---|
| global (hérité) | include | 121 |
| pièce | exclude | 69 |
| équipement | exclude | 12 |
| exception équipement | exclude | 90 |

Explicite (pièce + équipement + exception) = 69 + 12 + 90 = **171**.
`published_scope_exceptions` (niveau équipement seul, `equipement` +
`exception_equipement`) = 12 + 90 = **102** — retrouve exactement le total
relevé par la story 19-1, aucun écart.

## A — publié aujourd'hui, topic principal présent, scope=exclude

**A = 0.** Aucun équipement dont le topic discovery principal
(`jeedom2ha_<eq>/config`, sans suffixe `_<cmd>`) est présent alors que
`statut=publie`, avec un scope équipement `effective_state=exclude`.
Cohérent : la décision de publication du **principal** respecte déjà le
scope au moment du calcul (`perimetre` reflète `exclu_par_piece`/
`exclu_par_plugin` avant `statut`). La rupture C1 documentée touche les
secondaires, pas le principal.

## B — secondaires refusés, topic encore présent

**Non mesurable de façon fiable avec les endpoints actuels.** Méthode
tentée : pour chaque équipement, comparer les `cmd_id` des topics
secondaires (`jeedom2ha_<eq>_<cmd>/config`) à `matched_commands` de la
décision principale ; tout `cmd_id` absent de `matched_commands` serait
« refusé ». Vérification sur cas réel (eq 67 « Filtration Piscine »,
statut=publie, matched_commands=[382,388,389]) : les topics secondaires
384/386/395 sont bien présents — mais rien ne prouve qu'ils sont
« refusés » : `/system/diagnostics` n'expose **aucune décision par
secondaire** (limite déjà documentée par `_detect_i11_candidates` dans
`parity_snapshot.py`), donc un topic secondaire présent hors
`matched_commands` peut tout aussi bien être un secondaire publié via
`additional_mappings` que le résidu d'une dépublication ratée. Conclusion :
la mesure B nécessiterait une donnée par-secondaire absente de l'API ;
ne pas produire de chiffre non fiable.

## C — principal refusé, ≥1 secondaire dont le topic est présent

**C = 2**, repris strictement de la détection `i11_candidates` du script
officiel (`_detect_i11_candidates`, corrélation discovery MQTT retained ×
décision principale `statut≠publie`) :

| eq_id | nom | cmd_ids secondaires (topics présents) |
|---|---|---|
| 579 | Enphase | 5369, 5493, 5494, 5689, 5695 |
| 585 | chauffage piscine | 5497, 5504, 5505, 5536, 5537, 5546, 5631 |

## Effet attendu des correctifs 19-4

- **1er sync après 19-4 (C1 corrigé, scope appliqué au sync si option a)** :
  - A restant à 0 : rien à changer côté principal, la garde existe déjà.
  - C (579, 585) : avec la garde per-candidat sur `_publish_additional_sensors`
    et le paramétrage du sync sur le scope, ces 2 cas devraient basculer en
    dépublication effective des secondaires au prochain cycle — plus de
    topics fantômes pour ces eq_id.
  - B reste non quantifiable tant que le diagnostic n'expose pas de décision
    par secondaire ; un correctif de dépublication per-candidat réduirait le
    risque sans qu'on puisse en mesurer l'ampleur actuelle.
- **Clic « Publier »** : mêmes effets pour les eq_id concernés, appliqués
  immédiatement au lieu d'attendre le prochain sync.

## Écarts vs analyse code (rapport `/tmp/jeedom2ha-19-4-design-v2-report.md`)

Aucun écart : le terrain confirme A=0 (garde principale déjà correcte) et
retrouve exactement C=2 via le même détecteur que celui déjà utilisé par le
script officiel. B illustre concrètement la limite d'observabilité déjà
signalée par ClaudeBox (pas de décision par secondaire exposée) — argument
supplémentaire pour l'ajouter aux AC de 19-4 si on veut un jour mesurer B.
