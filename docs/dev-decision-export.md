# Export de décision : schéma `schema_version: 1` (story 24.2)

Documentation de développement (interne). L'export rend lisible, sans SSH, **ce que le plugin a décidé** pour chaque équipement, chaque commande et chaque scénario, afin de mesurer la parité avec Apple Maison et Assist avant et après chaque changement de comportement. Il est en **lecture seule** : il ne change ni ce qui est publié, ni le cache, ni les overrides.

## Où le trouver

| Quoi | Où |
|---|---|
| Fichier | `data/jeedom2ha_decision_export.json` (dossier `data/` du plugin, mode 600), réécrit **atomiquement** (fichier temporaire, `fsync`, `os.replace`) après chaque sync complet, chaque « Publier » et chaque « Supprimer ». Absent du dépôt et du paquet Market. |
| Route du démon (interne) | `GET /system/decision_export`, secret local requis, démon limité à `127.0.0.1`. Même document, construit depuis la mémoire ; sans sync préalable, erreur explicite (même motif que `/system/diagnostics`). |
| Action AJAX (administrateur) | `getDecisionExport` : relais de la route avec le budget fixe R des relais de parc (motif A1), une seule tentative. |
| Bouton | Page du plugin, menu « ⋯ » du bandeau : « Télécharger l'export de décision… », juste après « Télécharger le diagnostic… ». Le fichier téléchargé s'appelle `jeedom2ha-decision-export-AAAA-MM-JJ.json`. |

`jeedom2ha_cache.json` (cache disque d'amorçage) et `ha_overrides.json` ne sont ni lus différemment ni écrits par l'export.

## Confidentialité

- **Identifiants seulement** (Q5 A) : aucun nom d'équipement, de pièce, de commande ni de scénario ; aucun secret (clé API, secret local, identifiants MQTT, jeton).
- Les `logical_id` sont **bruts** (nécessaires à l'alignement hors plugin) : le fichier est réservé à l'administrateur, jamais versé au dépôt ni écrit au journal (le journal ne reçoit que des compteurs et le chemin).
- `logical_id` est vide pour beaucoup d'accessoires : il est écrit `null` et **ne sert jamais de clé unique**. La jointure se fait sur `eq_id`, `cmd_id`, `scenario_id` et `unique_id`.

## Forme du document

```json
{
  "schema_version": 1,
  "generated_at": "2026-10-20T10:00:00Z",
  "sync_at": "2026-10-20T09:58:11Z",
  "producer": { "plugin_version": "x.y.z", "confidence_policy": "sure_probable" },
  "config": { "excluded_plugins": ["<plugin>"], "excluded_piece_ids": [12] },
  "totals": { "equipments": 0, "commands": 0, "scenarios": 0 },
  "equipments": [{
    "kind": "equipment", "key": "eq:67", "eq_id": 67, "logical_id": null,
    "plugin": "<eq_type>", "piece_id": 12, "enabled": true, "generic_type": null,
    "homekit_exposed": true, "homekit_exposed_source": "equipement",
    "homekit_exposed_effective": true, "parity_class": null,
    "decision": "published", "reason": "sure", "step": "4",
    "exclusion_source": null,
    "overrides": { "publication": null, "types": {} },
    "pending_changes": false,
    "entities": [{ "unique_id": "jeedom2ha_eq_67", "ha_type": "light", "role": "primary",
                   "entity_id_expected": "light.jeedom2ha_67",
                   "discovery_published": true, "state_source": "optimistic" }],
    "commands": [{ "cmd_id": 1, "logical_id": null, "generic_type": "LIGHT_ON",
                   "type": "action", "sub_type": "other", "covered": true,
                   "decision": "published", "reason": "sure", "step": "4",
                   "entity_unique_id": "jeedom2ha_eq_67", "ha_type": "light", "override": null }]
  }],
  "scenarios": [{ "kind": "scenario", "key": "scenario:20", "scenario_id": 20, "active": true,
                  "homekit_exposed": true, "homekit_exposed_source": "scenario_configuration",
                  "decision": "published", "reason": "scenario_button",
                  "entity": { "unique_id": "jeedom2ha_scenario_20", "ha_type": "button",
                              "entity_id_expected": "button.jeedom2ha_scenario_20",
                              "discovery_published": true, "state_source": "none" } }]
}
```

Les clés sont toujours présentes (jamais omises) ; une valeur inconnue est `null`. **Seule exception** : `parity_alert` (story 24.6), présent uniquement quand l'alerte est levée.

### En-tête

| Champ | Sens |
|---|---|
| `generated_at` | Instant de génération du document (UTC). Seule valeur qui change entre deux exports du même état. Horodatage **en tête seulement**, pas par ligne. |
| `sync_at` | Instant de fin du dernier sync complet dont les décisions sont mémorisées (`null` seulement si le document est lu pendant le tout premier sync). |
| `producer` | `plugin_version` (lue dans `plugin_info/info.json`, `"inconnu"` si illisible) et `confidence_policy` appliquée au dernier sync. |
| `config` | Réglages de filtrage du dernier sync, **identifiants seulement** : `excluded_plugins` (identifiants de plugins, triés) et `excluded_piece_ids` (identifiants de `excludedObjects`, triés). Vides si le payload du sync ne les porte pas. |
| `totals` | Nombre d'équipements, de commandes (toutes) et de scénarios du document. |

### Équipement (`equipments[]`, trié par `eq_id`)

| Champ | Sens |
|---|---|
| `kind`, `key` | `"equipment"` et `"eq:<eq_id>"`. `key` est unique dans tout le document (un équipement et un scénario de même numéro ne se confondent jamais). |
| `eq_id`, `logical_id`, `plugin`, `piece_id`, `enabled`, `generic_type` | Lus dans le snapshot de topologie (`plugin` = `eq_type`, identifiant de plugin ; `piece_id` `null` sans pièce). |
| `homekit_exposed`, `homekit_exposed_source` | Signal de la story 24.1 (tri-état : `true`, `false`, `null` inconnu). |
| `homekit_exposed_effective` | Story 24.4 (champ additif, `schema_version` reste 1) : `homekit_exposed` ET `enabled`. `enabled=false` ⇒ `false` ; `enabled=true` ⇒ le réglage (`true`, `false`, `null` inconnu, jamais traité comme exposé). Sur un scénario : même règle avec `active`. |
| `parity_class` | Story 24.6 (champ additif, `schema_version` reste 1) : `"functional_equivalent"` ou `null`. Vaut `"functional_equivalent"` quand `homekit_exposed_effective` est `true` ET qu'au moins une commande `FAN_STATE`, `FAN_ON` ou `FAN_OFF` a `decision: "published"` et `ha_type: "switch"` ET qu'aucune commande ne porte `FAN_SPEED`, `FAN_SPEED_STATE`, `ROTATION` ni `ROTATION_STATE`. `null` sinon : non exposé, exposition inconnue ou non effective (équipement désactivé), non publié, autre famille, ou présence d'un type de vitesse. Calcul pur (`compute_parity_class`, `export/decision_export.py`) sur les lignes `commands[]` du même équipement ; lecture seule, aucune décision n'en dépend. Absent des scénarios. |
| `parity_alert` | Story 24.6 (champ additif, **absent sinon**) : `"fan_speed_present"` quand `homekit_exposed_effective` est `true` et qu'une commande de l'équipement porte `FAN_SPEED`, `FAN_SPEED_STATE`, `ROTATION` ou `ROTATION_STATE`, publiée ou non. `parity_class` vaut alors `null`. Voir « Ventilateurs et aspirateurs » ci-dessous. |
| `decision` | `published` : le principal est à publier. `partial` : principal refusé mais au moins un secondaire à publier (forme 579/585). `not_published` sinon. C'est le **verdict** (étapes 1 à 4 et périmètre), pas l'exécution : voir `discovery_published`. |
| `reason`, `step` | Code canonique tel que produit, sans traduction (`excluded_plugin`, `disabled_eqlogic`, `no_mapping`, `ambiguous_skipped`, `publication_excluded_eqlogic`, `sure`…) et niveau du premier échec : `"1"` éligibilité, `"2"` mapping, `"2b"` override d'exclusion, `"3"` projection HA, `"4"` périmètre produit, politique de confiance ou nominal, `"scope"` filtre de périmètre publié (alors `reason: "excluded"`). `reason: "no_sync_decision"` et `step: null` : équipement sans verdict mémorisé (jamais synchronisé). |
| `exclusion_source` | `eqlogic`, `plugin`, `object` ou `null` (priorité eqlogic > plugin > object, inchangée ; pas de raison `voie_native`). |
| `overrides` | Overrides **appliqués au dernier sync** (ou « Publier » de cet équipement) : `publication` (`exclude`, `force_publish` ou `null`) et `types` (`{"<cmd_id>": "<ha_type>"}`). |
| `pending_changes` | `true` quand les overrides enregistrés sur disque diffèrent de ceux appliqués (deux temporalités de 19-3 : enregistré, puis appliqué par un sync ou « Publier »). |
| `entities[]` | Entités mappées pour cet équipement (principale, puis secondaires multi-sensor), triées par `unique_id`. Vide si l'équipement n'est pas mappé. |
| `commands[]` | **Toutes** les commandes de l'équipement, triées par `cmd_id`, y compris non couvertes. |

### Entité (`equipments[].entities[]` et `scenarios[].entity`)

| Champ | Sens |
|---|---|
| `unique_id` | Exactement le `unique_id` du payload de découverte (lu dans le payload réel construit par le publisher, pas recalculé). |
| `ha_type` | Domaine HA. |
| `role` | `primary` ou `secondary` (absent pour un scénario). |
| `entity_id_expected` | Exactement le `default_entity_id` du payload (`<domaine>.<object_id>`, story 22-1). **Valeur attendue à la création** : une entité existante garde son `entity_id` ; la jointure avec le registre de HA se fait sur `unique_id`. |
| `discovery_published` | Le plugin a publié la découverte et ne l'a pas retirée. **Ne dit pas** que l'entité est présente dans le registre de HA (le démon n'a pas de client HA). |
| `state_source` | `streamed` (retour d'état en streaming effectif, lu sur `StateSynchronizer.list_state_targets()`), `optimistic` (entité à commande publiée sans retour d'état en streaming) ou `none` (pas d'état : bouton, capteur non écouté, entité non publiée). |

### Commande (`equipments[].commands[]`)

| Champ | Sens |
|---|---|
| `cmd_id`, `logical_id`, `generic_type`, `type`, `sub_type` | Lus dans le snapshot. |
| `covered` | Une entité mappée porte la commande. |
| `decision`, `reason`, `step` | Décision par commande d'`evaluate_equipment()` (`CommandDecision`) : `command_not_covered` (étape `"2"`) pour une commande non couverte, raison d'éligibilité (étape `"1"`) pour un équipement inéligible. Sous un équipement refusé par le périmètre publié : `not_published`, `excluded`, `"scope"`. |
| `entity_unique_id`, `ha_type` | Entité retenue par `select_covering_decision` (la première entité **publiée** qui porte la commande, sinon la première, CC-47). `null` si non couverte. |
| `override` | `{"ha_type", "publication"}` appliqués à cette commande, ou `null`. |

### Scénario (`scenarios[]`, trié par `scenario_id`)

`equipments` et `scenarios` sont les deux seuls tableaux de premier niveau.

Tous les scénarios, actifs et inactifs. `kind` `"scenario"`, `key` `"scenario:<scenario_id>"`, `scenario_id`, `active`. `entity` : le bouton HA du scénario (mêmes champs qu'une entité, sans `role`, `state_source` toujours `none`), décrit même pour un scénario inactif. `decision` `published` et `reason` `scenario_button` pour un scénario actif ; `not_published` et `scenario_inactive` pour un inactif (aucun bouton dans HA). `homekit_exposed` vient de la story 24.1.

**Scénarios « non projetés » : un artefact de mesure (story 24.5).** Avant 24.2, la mesure de parité HomeKit comptait comme non projetés les scénarios déclenchés à la voix dans Apple Maison. Cet écart venait de l'outil de mesure, pas du plugin : il ne lisait pas les boutons de scénario. Ces scénarios restaient en plus hors du contrat de décision. Un scénario **actif** est toujours projeté en `button` (`jeedom2ha_scenario_<id>`). Pour comparer avec Home Assistant, on joint sur `kind` + `key` (`scenario:<id>`) ou sur `unique_id`, jamais sur le nom. L'exposition d'un de ces boutons à Assist se règle dans Home Assistant : le plugin n'y touche pas.

### Ventilateurs et aspirateurs : équivalents fonctionnels (story 24.6)

Un équipement `FAN_*` sans ordre de vitesse (marche, arrêt, état ; aspirateurs compris) **reste publié en `switch`** : il est fonctionnellement équivalent à ce qu'expose HomeKit, d'où `parity_class: "functional_equivalent"`. Le plugin n'ouvre ni `fan` ni `vacuum` pour ces équipements, et aucun `entity_id` ni `unique_id` ne change.

La présence de `FAN_SPEED`, `FAN_SPEED_STATE`, `ROTATION` ou `ROTATION_STATE` sur un équipement exposé (effectif) est **le seul déclencheur** d'une nouvelle story : l'ouverture gouvernée du composant `fan` (story 18-1). L'export la signale par `parity_alert: "fan_speed_present"`, visible sans lire le code ; le classement ne change rien à la publication.

## D'où viennent les décisions

- Le sync et « Publier » **mémorisent** le verdict d'`evaluate_equipment()` (RAM, `DecisionMemo`) au moment où ils décident ; l'export ne recalcule rien. Après « Publier », seuls les équipements traités voient leur verdict renouvelé ; les autres gardent celui du dernier sync (c'est ce que `pending_changes` rend visible).
- Les équipements inéligibles passent par le chemin I1 d'`evaluate_equipment()` (l'éligibilité est consommée telle quelle).
- Seul l'état d'exécution (`discovery_published`, `state_source`) est lu en direct à chaque export.
- « Supprimer » ne change pas le verdict : `decision` reste celui du sync, `discovery_published` passe à `false`.

## Déterminisme

Tous les tableaux sont triés (`eq_id`, `cmd_id`, `scenario_id`, `unique_id`) et les clés ont un ordre fixe : deux exports du même état sont identiques à `generated_at` près, et se comparent par `diff`.

## Politique de version

- Un champ **ajouté** ne change pas `schema_version` (par exemple un horodatage par ligne, ou un champ `native_test_mode` si le mode « plugins en test » de 24.3 est maintenu).
- Un champ **renommé, retiré, ou dont le sens change** porte `schema_version` à `2`.
- Une valeur ajoutée à un champ à valeurs fermées (`decision`, `step`, `state_source`) est un ajout.

## Taille et coût

Mesure sur un parc synthétique de 295 équipements, 870 commandes et 120 scénarios (corpus doré répété) : fichier de 694 572 octets (JSON indenté), 480 196 octets compact ; construction du document 9 ms ; mémorisation des décisions : une entrée par équipement (dictionnaire de décisions de commandes), sans objet du pipeline conservé. La taille réelle sur la box (292 équipements) est mesurée par ClaudeBox lors de la baseline. L'export est une route et un fichier séparés : la liste blanche de `getEquipmentStates` et son budget sont inchangés.
