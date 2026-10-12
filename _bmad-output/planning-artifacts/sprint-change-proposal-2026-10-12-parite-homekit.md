---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-10-12
status: decided
decided_at: 2026-10-12T13:22:00+02:00
decision_note: Q1 modifiee (semantique « exclu par plugin » conservee) ; Q2 a Q11 sur les options recommandees ; relayees par ClaudeBox ; aucune fusion
scope_classification: major
trigger: parite-homekit-assist-cc33
mode: batch
communication_language: french
proposed_by: session cloud deleguee (documentaire, sans acces box, Home Assistant ni secret)
impacts_if_approved:
  - _bmad-output/planning-artifacts/epics-projection-engine.md (Epic 24)
  - _bmad-output/implementation-artifacts/sprint-status.yaml (pe-epic-24 et stories 24-1 a 24-10, toutes draft)
  - _bmad-output/implementation-artifacts/24-*.md (dix brouillons de story)
no_change_documented:
  - _bmad-output/planning-artifacts/prd.md (aucun FR/NFR ajoute par cette PR : voir D9)
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - resources/, core/, desktop/, tests/ (aucun code, aucun test)
references:
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-10-01-etape-4-interface.md (modele)
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-17-couverture-domaines-ha.md (epic 18, recoupement)
  - _bmad-output/implementation-artifacts/22-1-noms-home-assistant-egaux-noms-jeedom-cc36.md (style des questions)
  - _bmad-output/implementation-artifacts/23-3-remontee-d-etat-lumieres-et-volets.md (recoupement)
  - _bmad-output/planning-artifacts/ha-projection-reference.md (composants MQTT et types generiques)
---

# Sprint Change Proposal 2026-10-12 : parité HomeKit (CC-33), epic 24

> **Statut : décidé le 12/10 à 13:22 par Alexandre (relayé par ClaudeBox), PR #260 toujours sans fusion.** Voir « Décisions d'Alexandre » ci-dessous et la section 14 (R2). Cette proposition, la section de l'epic 24 et les dix brouillons de story sont **documentaires**. Toutes les stories sont `draft` ; aucune n'est `ready-for-dev`. Chaque décision de comportement en production a été posée en question à Alexandre (section 8), avec options, conséquences et recommandation ; ses réponses sont consignées, les options non retenues sont marquées « écartée ». Depuis la R2, seules 24-1 et 24-2 sont `ready-for-dev` (accordé par ClaudeBox au nom de ces décisions) ; 24-3 à 24-10 restent `draft` jusqu'à leur `create-story`, après la baseline. Les pointeurs `fichier:ligne` sont pris sur `main` à `b1acad7` (12/10/2026). Aucun nom réel d'équipement, de pièce, de scénario ou de personne (CC-48) : identifiants seulement.
>
> **R1 intégrée (ClaudeBox, 12/10).** Les vérifications en lecture seule faites par ClaudeBox le 12/10 sont intégrées et marquées « *établi par ClaudeBox le 12/10* » : règle d'exposition de Homebridge (T3, 24-1), cause des 5 scénarios (section 6), chiffrage de Q3 et de Q7, types génériques des équipements restants (24-6 à 24-10). Le détail est en section 13.

## Décisions d'Alexandre (12/10 à 13:22, relayées par ClaudeBox)

- **Q1 : on garde la sémantique « exclu par plugin ».** Pas de raison `voie_native`, pas de relibellé : la liste `excludedPlugins`, le code `excluded_plugin` et le périmètre `exclu_par_plugin` restent **tels quels**. L'export porte toujours les `logicalId` d'équipement et de commande (alignement hors plugin). Les options A, B et C de Q1 sont **écartées**.
- **Q2 B** (liste « plugins en test », vide par défaut), **Q3 A**, **Q4 A**, **Q5 A**, **Q6 A**, **Q7 A**, **Q8 A**, **Q9 A** (version ajustée par la R1 : l'epic 24 absorbe 18-2 et 18-4, l'epic 18 garde 18-1), **Q10 A** : les options recommandées sont retenues, les autres **écartées**.
- **Q11** (ajoutée par ClaudeBox dans la fiche remise à Alexandre) : exposer à Assist les 5 boutons de scénario (20, 38, 50, 57, 150), geste côté HA, hors plugin : **oui**, fait par ClaudeBox à 13:30.
- `ready-for-dev` pour 24-1 et 24-2 est accordé par ClaudeBox au nom de ces décisions (Task 0 de 24-1 faite, Q5 et Q6 tranchées). `pe-epic-24` passe `in-progress`.

**Conséquences** : (1) 24-3 perd la raison `voie_native` et, avec elle, la modification des artefacts figés (`taxonomy.py`, `cause_mapping.py`, `ui_contract_4d.py`) et des tables de libellés ; il ne reste que le mode « plugins en test » (Q2 B), à justifier au `create-story` (sinon la story est abandonnée) ; (2) 24-4 suit alors directement la baseline si 24-3 disparaît ; (3) les plugins natifs restent « exclus par plugin ».

## 1. Déclencheur

Ordre d'Alexandre du 11/10 à 15:48 : CC-44 + CC-47 (epic 21, `done`), puis CC-36 avec CC-51 et « compteurs » (epic 22, 22-1 `done`, 22-2 `ready-for-UX-validation`), puis la parité HomeKit (CC-33). L'epic 23 est pris par le chantier Market ; la parité prend donc le numéro **24**.

## 2. Exigence (décision d'Alexandre du 01/10, amendée le même jour)

1. Tout ce qui est piloté ou consulté par la voix dans Apple Maison (via le plugin Homebridge de Jeedom) l'est par Assist dans HA, sans configurer la maison deux fois. Jeedom reste la source de vérité ; une seule voie par équipement.
2. **Plugins que HA intègre nativement** (liste configurable, aujourd'hui la liste `excludedPlugins`) : non publiés, sauf un mode « test du plugin » explicite, désactivé par défaut. Décision « non publié », raison canonique **`voie_native`**, avec `logicalId` d'équipement et de commande dans l'export pour l'alignement hors plugin (référentiel de parité tenu par ClaudeBox).
   **Décision du 12/10 (Q1) : la raison `voie_native` n'est pas créée ; les plugins natifs restent « exclus par plugin » (`excluded_plugin`, `exclu_par_plugin`), l'export portant les `logicalId`.** Le reste de cet alinéa est conservé comme exigence d'origine.
3. **Tout le reste** : projeté par défaut dès que l'équipement est exposé à HomeKit (`homekit_exposed`), jamais écarté par l'exclusion de pièce ; seule une exclusion explicite de l'équipement ou une impossibilité technique l'écarte, avec une raison canonique. Aucune commande HomeKit sans raison.
4. **Export JSON versionné** du contrat de décision (équipement et commande), pour mesurer la parité sans SSH.
5. Le plugin ne modifie jamais la configuration Homebridge, les types génériques Jeedom ni l'exposition à Assist dans HA.

## 3. Mesure du 10/10 (référentiel ClaudeBox, lecture seule) et lecture par story

118 équipements exposés à HomeKit + 5 accessoires de scénario. 110 sont dans HA par une voie ou l'autre (93 %), 99 exposés à Assist (84 %), 68 passent par jeedom2ha. Le calcul interne : 110 − 68 = **42 équipements** arrivent dans HA par une autre voie que le plugin (candidats naturels à `voie_native`) ; 118 − 110 = 8 équipements absents de HA ; 110 − 99 = 11 présents mais non exposés à Assist (côté HA, **hors plugin**). Les 15 écarts de type peuvent se trouver dans l'un ou l'autre ensemble : le recoupement n'est pas donné, l'export (24-2) le donnera.

| Écart mesuré | Nombre | Traité par | Remarque |
|---|---|---|---|
| Scénarios non projetés | 5 | 24-2 (mesure), 24-5 | Le plugin publie déjà un bouton par scénario actif. *Établi par ClaudeBox le 12/10* : les cinq boutons existent dans HA mais ne sont pas exposés à Assist ; l'écart est un artefact de mesure et un geste côté HA (section 6) |
| Types manquants ou remplacés | 15 | 24-6 à 24-10 | Ventilateurs/aspirateurs en `switch` (24-6, *établi par ClaudeBox le 12/10* : 8 équipements `FAN_*`, aucune vitesse, donc équivalents fonctionnels), portail/garage `GB_*`/`BARRIER_STATE`/`GARAGE_STATE` en `button` (24-7), deux vannes `IRRIG_*` (24-8), serrure `LOCK_*` (24-9), prise `ENERGY_*` et capteur `WEATHER_*` + `SIREN_STATE` (24-10) |
| Sous-accessoires Homebridge sans eqLogic propre | 2 | Hors plugin | Aucun eqLogic Jeedom à projeter : à classer par le référentiel (D7) |
| Alignement et exposition à Assist | ≈ 11 + | Hors plugin | « Le reste se règle côté HA » ; le plugin ne touche jamais à l'exposition (exigence 5) |
| Équipements exposés écartés par la pièce, par plugin ou par absence de type | inconnu | 24-3, 24-4 | La baseline de 24-2 donnera le nombre exact ; il n'est pas dérivable du dépôt |

## 4. Faits techniques revérifiés sur `main` (`b1acad7`)

Verdict : **C** = confirmé, **N** = nuancé, **M** = modifié depuis les réponses de clawcode du 01/10.

| # | Fait (réponse de clawcode) | Verdict | Pointeurs et précisions |
|---|---|---|---|
| T1 | Le plugin ne lit ni `sendToHomebridge` ni les `logicalId`. | **C** | Aucune occurrence de `sendToHomebridge`, `logicalId` ni `getLogicalId` dans `core/`, `desktop/`, `plugin_info/`, `resources/daemon/` hors tests, et aucune lecture d'un attribut « HomeKit » (seule mention : le docstring de `mapping/button.py:45`). La lecture des commandes se fait en `core/class/jeedom2ha.class.php:759-769` (id, nom, type générique, type, sous-type, valeur, unité, visibilité, historisation) ; celle de l'équipement en `:786-796`. |
| T2 | Ajout de bout en bout `getFullTopology()` → `models/topology.py` → éligibilité → `evaluate_equipment()`, champs optionnels additifs. | **C** | `getFullTopology()` `core/class/jeedom2ha.class.php:687` ; `JeedomCmd` `models/topology.py:74`, `JeedomEqLogic` `:86`, `from_jeedom_payload` `:124` (lecture tolérante par `.get`, valeurs par défaut sur les dataclasses) ; `assess_eligibility` `:301` ; `evaluate_equipment` `models/evaluate_equipment.py:309` (reçoit l'éligibilité déjà calculée, ne la recalcule jamais). **Ajout** : `resolve_published_scope` (`models/published_scope.py:93-122`) et `_scope_entry_is_included` (`transport/http_server.py:419`) relisent aussi `is_excluded`/`exclusion_source` : toute règle « la pièce n'écarte pas » doit y être répercutée (24-4). |
| T3 | `homekit_exposed` : attribut d'équipement hérité par ses commandes. | **C** (conception), règle **établie** | *Établi par ClaudeBox le 12/10 (lecture du plugin Homebridge, `plugins/homebridge/core/class/homebridge.class.php:2680-2710`, `discovery_cmd_eqlogics`)* : un équipement est exposé s'il appartient à un plugin actif (sauf `mobile` et `homebridge`), **dans une pièce dont `configuration.sendToHomebridge` vaut 1**, et si `configuration.sendToHomebridge` (entier) de l'équipement vaut 1 ; clé absente sur l'équipement : valeur par défaut du plugin Homebridge (`config::byKey`, clé `sendToHomebridgeDefault`, défaut 1) ; l'API écarte `sendToHomebridge == 0` (`core/api/homebridge.api.php:44`). **Scénarios** : `configuration.sendToHomebridge` du scénario **présent et différent de « 0 »** ; **clé absente = non exposé** (`discovery_scenario()`, `homebridge.class.php:3119`) — *corrigé par ClaudeBox le 12/10 (R1 de #261) : la version précédente disait « absent = exposé »*. **Aucun drapeau par commande** : les commandes héritent de l'équipement. Cache Homebridge : 123 accessoires, tous à 1 ; `logicalId` non vide pour 58, **vide pour 65** (l'export porte donc aussi `eq_id` et `cmd_id`). 24-1 combine pièce, équipement et valeur par défaut, en lecture seule ; `null` si le plugin Homebridge est absent ou une valeur illisible ; la provenance dit laquelle des trois a décidé. Deux cas restent à confirmer (D1) : équipement sans pièce, pièce sans clé. |
| T4 | Le démon n'a aucun client HA ; un indicateur « Assist » ne peut être que déclaratif. | **C**, **N** sur `published_in_ha` | Seul `transport/mqtt_client.py` parle au broker. `published_in_ha` (`transport/http_server.py:470-482`, exposé `:3177`/`:3256`) signifie « publié par le plugin et non en attente de dépublication », **pas** « présent dans le registre de HA » : l'export ne doit jamais l'appeler « présent dans HA » (champ `discovery_published`). Aucun champ Assist dans l'export : l'exposition à Assist reste celle du référentiel (exigence 5). |
| T5 | `jeedom2ha_cache.json` est conservé ; l'export va dans `data/jeedom2ha_decision_export.json` (`schema_version: 1`). | **C**, **N** sur la forme | Le cache (`cache/disk_cache.py:29,107-152`) est indexé par `eq_id`, ne contient que les équipements présents dans `publications` (ni inéligibles, ni commandes, ni scénarios) et s'écrit **sans écriture atomique** (`open(…, "w")`, `:148`). Le motif atomique existe (`mapping/overrides.py:64`, `_write_raw_atomically`, CC-34) : l'export doit l'employer. Le cache n'est donc pas extensible à ce besoin ; second fichier confirmé. |
| T6 | `models/cause_mapping.py` et `models/ui_contract_4d.py` sont figés. | **C** et **M** | Les deux sont figés (`cause_mapping.py:1`, `ui_contract_4d.py:1`). **`models/taxonomy.py` l'est aussi** (« ARTEFACT FIGÉ — Story 3.1 », `:1`) et n'était pas cité : un code inconnu y tombe en « Non supporté » (`get_primary_status`, `:34-40`), ce qui afficherait `voie_native` comme un équipement non supporté. Trois tables non figées doivent aussi suivre : `_DIAGNOSTIC_MESSAGES` (`http_server.py:2274`), `_CLOSED_REASON_MAP` (`:2410`), libellés de `desktop/js/jeedom2ha_mapping_override.js:640-650`. Un code absent de `_EXCLUSION_REASON_TO_PERIMETRE` (`ui_contract_4d.py:15-19`) devient **« inclus »**, donc un faux écart de direction 1 (`compute_ecart`, `:32-44`) : 24-3 doit le traiter. *(R2 : la partie « ajouter `voie_native` aux artefacts figés » est **sans objet** depuis la décision Q1 ; le constat sur `taxonomy.py` reste exact.)* |
| T7 | (non cité) Deux voies d'exclusion de pièce. | **Ajout** | (a) `excludedObjects` : `core/class/jeedom2ha.class.php:702-703,783-784`, étape 1 de l'éligibilité (`topology.py:220-223,307-310`, code `excluded_object`) ; (b) états de pièce du périmètre publié (`publishedScopeObjectsStates`, `class.php:711`) et règle historique `legacy_excluded_pieces` (`published_scope.py:93`). Priorité des exclusions : équipement > plugin > pièce (`class.php:775-784`). |
| T8 | (non cité) « Exclusion explicite de l'équipement ». | **Ajout** | En pratique : (a) l'override de publication `exclude_eqlogic`, posable depuis l'écran depuis 20-2 (`models/decide_publication.py:95-103`, route `/action/publication_override`, `http_server.py:4746`) ; (b) le drapeau `jeedom2ha_excluded` et l'état `jeedom2ha_scope_state` (`class.php:775,810`). **Aucun code du dépôt n'écrit (b)** ni `publishedScope*States` : ils ne sont que lus. Définition retenue pour « explicite » : (a) + (b). |
| T9 | (non cité) Les plugins exclus aujourd'hui. | **Ajout** | Saisie libre, séparée par des virgules (`plugin_info/configuration.php:118-124`), enregistrée par `saveFilteringConfig` (`core/ajax/jeedom2ha.ajax.php:812-826`), comparée à `getEqType_name()` (`class.php:778`), code `excluded_plugin` (`topology.py:222`), périmètre `exclu_par_plugin` (`ui_contract_4d.py:17`). |
| T10 | (non cité) Les scénarios sont hors du contrat de décision. | **Ajout** | Boucle propre dans le sync (`http_server.py:2129-2190`) : pas d'`evaluate_equipment`, pas de périmètre publié, pas d'override, entrées dans `app["scenario_publications"]` seulement (`:2160-2164`, `:4716`) : **absents** de `/system/diagnostics`, de `/system/published_scope`, du cache disque et de l'outil de parité (`tools/parity_snapshot.py`, aucune occurrence de « scenario »). Les identifiants de scénario recoupent des identifiants d'équipement (15 cas, preuve 21-1) : l'export doit porter un genre (`kind`) et une clé unique. |
| T11 | (non cité) Couverture des types. | **Ajout** | `PRODUCT_SCOPE` = 8 composants (`validation/ha_component_registry.py:70`), ni `fan`, `lock`, `valve` ni `scene`. Chaîne de mappers `mapping/registry.py:24-35`. `CoverMapper` ne reconnaît que `FLAP_*` (`mapping/cover.py:31`) ; aucun `GB_*` dans le code du démon ; `BARRIER_STATE`/`GARAGE_STATE` → `binary_sensor` (`mapping/binary_sensor.py:41`) ; toute action `other` typée → `button` (`mapping/button.py:12-35`). `LOCK_*`/`SIREN_*` ne servent que de listes « anti » (`switch.py:52-54`, `cover.py:42-43`) et `LOCK_STATE` → `binary_sensor` (`:40`). `FAN_*` → `switch` depuis 14-1 (`switch.py:64`, `binary_sensor.py:21-26`). `VALVE_*`, `FAUCET_*`, `IRRIG_*` : aucun mapper (reste le repli `fallback.py`). |
| T12 | (non cité) Remontée d'état. | **Ajout** | `_STREAMED_TYPES` = `sensor`, `binary_sensor`, `switch` (`sync/state.py:33-36`) ; `_READBACK_KEYS` connaît déjà `light` et `cover` (`:44-48`) sans les streamer. C'est le périmètre de 23-3. |

## 5. Ce qui a changé depuis le 01/10 (epics 20 à 22 livrés)

| Quoi | Où | Conséquence pour l'epic 24 |
|---|---|---|
| **20-x** : surface unique pièce → équipement → commande, exclusion/forçage depuis l'écran, purge, rescan, documentation `docs/fr_FR` | `desktop/js/jeedom2ha_mapping_surface.js`, `jeedom2ha_mapping_override.js` ; routes `/action/publication_override*` (`http_server.py:4746-4747`) | L'« exclusion explicite de l'équipement » est maintenant un geste d'écran (override). `voie_native` et « exposé HomeKit » doivent apparaître dans cette surface (libellé, cause) sans nouveau recalcul côté interface : la surface ne consomme que `evaluate_equipment()`. Toute modification de libellé exige le gate 20-0. *(R2 : `voie_native` n'est plus créée ; seul le signal « exposé HomeKit » peut apparaître à l'écran.)* |
| **21-1** : bouton d'un scénario inactif retiré (CC-44) ; résolution par commande (CC-47) | `http_server.py:2129-2190` ; `evaluate_equipment.py:295` (`select_covering_decision`) ; `class.php:832` (`scenarios_complete`) | Un scénario inactif **n'a plus de bouton** : c'est une cause possible de l'écart des 5 scénarios (section 6). La décision par commande a un résolveur unique : l'export le réutilise. |
| **22-1** : un seul nom d'appareil par équipement ; `default_entity_id` sur tous les types | `discovery/publisher.py:405-412` (+ appels `:476…:747`), `:414-445` | L'`entity_id` « attendu » d'une entité nouvelle ou recréée est calculable : `<domaine>.<object_id>`. Les entités existantes (dont 306 à `entity_id` dérivé des noms, H6 de 22-1) gardent leur `entity_id` : la **jointure avec le registre de HA se fait sur `unique_id`**, pas sur `entity_id`. |
| **22-2** : compteurs « publiés / en attente / non pris en charge » | `http_server.py:470` (`_is_currently_published_in_ha`), `:3177`, `:3800` | Les compteurs doivent classer `voie_native` comme « exclu » (24-3). Mesure du 12/10 sur la box : `total_eq=292 eligible=96 published=263` (preuve 22-2) : seuls 96 équipements sur 292 sont éligibles aujourd'hui. *(R2 : sans objet pour `voie_native` ; `excluded_plugin` reste compté « exclu ».)* |
| **A1** : budget de relais fixe (60 s) | `core/ajax/jeedom2ha.ajax.php:27` (`_jeedom2ha_run_parc_relay`) | Le relais de l'export (24-2) suit ce motif. |
| **A2/A3** : paquet Market épuré, conformité | `scripts/build-market-package.sh`, `docs/release-market.md` | Le fichier d'export vit dans `data/` (runtime) : à vérifier hors du paquet (test de 24-2). |
| **CC-34** : écriture atomique des overrides | `mapping/overrides.py:64` | Motif à reprendre pour l'export. Le cache disque, lui, n'est pas atomique (`disk_cache.py:148`) : hors périmètre (signalé en D8). |
| **Inchangé depuis le 01/10** | T1, T3, T10, T11, T12 | Aucun signal HomeKit, aucun `logicalId`, aucun fan/lock/valve, aucun streaming lumière/volet. |

## 6. Les 5 scénarios : pourquoi « non projetés » alors que le plugin publie un bouton par scénario actif

Fait établi par le code : depuis la story 10-1, tout scénario **actif** reçoit un bouton `homeassistant/button/jeedom2ha_scenario_<id>/config` (`http_server.py:2134-2158`, `mapping/button.py:44-65`). Les cinq scénarios HomeKit sont les identifiants 20, 38, 50, 57 et 150 (story 10-1) ; aucun ne figure parmi les 15 identifiants qui recoupent un équipement (preuve 21-1 : 15, 18, 21, 81, 82, 83, 85, 109, 110, 112, 113, 120, 160, 179, 180). Le relevé du 12/10 compte **84 boutons de scénario** dans HA.

Cette session ne pouvait pas conclure sans la box ; voici les causes plausibles qu'elle avait classées, avec la vérification de chacune (le verdict de ClaudeBox est en 6.1).

| Rang | Hypothèse | Fondement dans le code | Vérification (ClaudeBox, lecture seule) |
|---|---|---|---|
| H-a | **Confirmée.** Artefact de mesure : les scénarios n'existent dans aucune sortie que le référentiel sait lire (diagnostic, périmètre publié, cache, outil de parité) ; seule la souscription MQTT les montre | T10 | Chercher `unique_id = jeedom2ha_scenario_20 / _38 / _50 / _57 / _150` dans le registre des entités de HA et `homeassistant/button/jeedom2ha_scenario_<id>/config` dans l'inventaire MQTT |
| H-b | **Écartée.** Un ou plusieurs des cinq sont **inactifs** : pas de bouton (10-1) et, depuis 21-1, un bouton existant est retiré | `http_server.py:2135-2142` | État `is_active` des cinq dans Jeedom |
| H-c | **Écartée.** Les accessoires HomeKit de scénario sont des **interrupteurs** (« HomeKit switches », delta du 07/06) et le référentiel attend un `switch`/`scene` ; un `button` ne compte pas comme projection du même objet | décision 10-1 AC2/AC4 : `button` | Règle du référentiel pour le type attendu ; question 8 |
| H-d | **Confirmée.** Les cinq sont projetés, mais **non exposés à Assist** (côté HA, hors plugin) et comptés « non projetés » faute de distinction | exigence 5 | Exposition Assist des cinq boutons dans HA |
| H-e | **Écartée.** Jointure par numéro seul : un identifiant de scénario est pris pour un identifiant d'équipement | 15 collisions mesurées, **aucune** sur les cinq | Clé de jointure du référentiel (le champ `kind` de l'export la supprime) |

### 6.1 Cause établie (*établi par ClaudeBox le 12/10*)

Les cinq scénarios 20, 38, 50, 57 et 150 sont **actifs** dans Jeedom et **leurs boutons existent dans le registre de HA**, mais ils sont **non exposés à Assist** (`should_expose: false`) ; l'outil de parité de ClaudeBox ne lit pas les boutons de scénario. Verdict : **H-a et H-d confirmées** ; **H-b, H-c et H-e écartées**. L'exposition à Assist est un geste côté HA, hors plugin (exigence 5). Q8 A est confirmée par les faits. **Q11 (Alexandre, 12/10) : oui, exposer les 5 boutons à Assist ; fait par ClaudeBox à 13:30.** Le reste de cette section est conservé comme historique du raisonnement.

Ce que l'epic en tire : le premier gain n'est pas un type, c'est **faire entrer les scénarios dans le contrat de décision et dans l'export** (24-2), puis seulement décider d'un éventuel changement de type (24-5, question 8).

## 7. Découpage proposé, tailles, dépendances, ordre

Tailles : **S** = une PR, un module, preuve légère ; **M** = une PR, plusieurs modules, preuve terrain ; **L** = une PR large ou un gate lourd. Estimations relatives, à confirmer à la relecture de ClaudeBox.

| Story | Objet | Taille | Dépend de | Change la production ? | Décisions |
|---|---|---|---|---|---|
| **24-1** | Signal `homekit_exposed` (pièce + équipement + valeur par défaut de Homebridge, provenance) et `logicalId` d'équipement/commande/scénario, de bout en bout, additif | S à M | Task 0 **faite** par ClaudeBox le 12/10 (deux cas à confirmer) | Non | Q5 (contenu) |
| **24-2** | Export JSON versionné `schema_version: 1`, fichier `data/jeedom2ha_decision_export.json`, route du démon, relais PHP, scénarios compris | L | 24-1 | Non | Q5, Q6 |
| *Baseline* | Capture « avant » par ClaudeBox (sans SSH), hors dépôt | — | 24-2 déployée | Non | — |
| **24-3** | ~~Raison `voie_native`~~ (écartée, Q1). Reste le mode « plugins en test » (Q2 B), **à justifier au `create-story` : retirer un plugin de la liste suffit déjà** ; sinon la story est abandonnée | S (si maintenue) | 24-2 + baseline | Non, sauf le mode test | Q1 (écartée), Q2 B |
| **24-4** | Projection par défaut des équipements exposés à HomeKit : la pièce n'écarte plus ; raison pour chaque commande | M à L | 24-1, 24-2 + baseline (et 24-3 si elle est maintenue) | **Oui** (équipements nouvellement publiés) | Q3, Q4 |
| **24-5** | Scénarios : se réduit aux scénarios dans l'export (24-2) ; cause de l'écart établie (section 6.1), pas de changement de type | S (documentaire) | 24-2 | Non (Q8 A) | Q8 |
| **24-6** | Ventilateurs (et aspirateurs) : classés « équivalents fonctionnels » dans l'export ; `fan` n'est ouvert que si un ventilateur à vitesse apparaît (aucun parmi les 8 mesurés) | S (documentaire) | 24-2 ; 24-4 | Non (Q7 A) | Q7, Q9 |
| **24-7** | Portail et garage : `cover` (`GB_*`, `BARRIER_STATE`) | M à L | 24-4 ; **23-3** pour l'état | **Oui** (`button`/`binary_sensor` → `cover`) | Q10 |
| **24-8** | Vanne d'arrosage : `valve` | M | 24-4 ; recoupe 18-4 | **Oui** | Q9, Q10 |
| **24-9** | Serrure : `lock` | M | 24-4 ; recoupe 18-2 | **Oui** | Q9, Q10 |
| **24-10** | Écarts résiduels après mesure : prise `ENERGY_ON/OFF`, capteur sans température ni humidité | S à M, **portée à fixer** | 24-2 + baseline + 24-4 | À établir | — |

**Ordre** (obligatoire pour le lot 1, recommandé pour le lot 2) :

```
24-1 → 24-2 → [baseline ClaudeBox] → 24-4 → 24-5   (24-3, si maintenue, se place avant 24-4)
                                                 ↘ types, une story à la fois : 24-6 → 24-7 → 24-8 → 24-9 → 24-10
```

- **L'export avant tout changement de comportement.** La baseline « avant » rend les stories 24-3 et 24-4 mesurables (nombre d'équipements nouvellement projetés, relibellés). Sans elle, le gate de 24-4 n'a pas de dénominateur.
- **24-3 (si elle est maintenue) puis 24-4**, jamais en parallèle : elles modifient `assess_eligibility` (`topology.py:301`) et la configuration du filtrage. Depuis Q1, la table de statuts figée n'est plus touchée ; 24-4 modifie `assess_eligibility` et `published_scope.py`.
- **Une story de type à la fois** : toutes touchent `validation/ha_component_registry.py`, `mapping/registry.py`, `discovery/registry.py`, `sync/command.py` et `sync/state.py`. L'ordre des types suit la liste d'Alexandre ; 24-7 attend 23-3 (voir ci-dessous).
- **Après l'epic 22** : 24-1 ne touche ni l'écran ni `http_server.py` ; elle peut démarrer dès les décisions prises, avant le `done` de 22-2. 24-2 et suivantes attendent 22-2 `done` (même fichier `http_server.py`, mêmes compteurs).
- Workflow BMAD complet par story (`create-story → dev-story → code-review`) ; toute story qui touche l'écran passe en plus par `ready-for-UX-validation` et le gate 20-0 ; preuve terrain par ClaudeBox ; aucune session cloud n'a d'accès box ni HA.

### 7.1 Recoupement avec la story 23-3 (remontée d'état des lumières et volets) et comment éviter le doublon

23-3 modifie le mécanisme de remontée d'état : `_STREAMED_TYPES` et `_READBACK_KEYS` (`sync/state.py:33-48`), les constructeurs `light` et `cover` (`optimistic`, `discovery/publisher.py`), la confirmation par état réel (`sync/command.py`, `_has_reliable_state`) et la section « Limites » de la documentation. L'epic 24 touche les **mêmes constantes** pour ses nouveaux domaines. Règles proposées :

1. **23-3 est propriétaire de la mécanique de streaming et des lignes `light` et `cover`.** Aucune story 24 ne modifie ces lignes ni la confirmation d'un `light` ou d'un `cover` existant.
2. **Chaque story de type ajoute une seule entrée pour son domaine** (une ligne dans `_READBACK_KEYS`, un élément dans `_STREAMED_TYPES`), dans sa propre PR, **après** la fusion de 23-3 (rebase). Si l'état réel n'est pas encore disponible, le domaine est publié **optimiste** et la limite est écrite dans « Limites ».
3. **Règle de 23-3 reprise telle quelle** (AC6 de 23-3) : `optimistic: false` seulement quand un état réel existe. Les stories 24-6 à 24-9 la citent, ne la redéfinissent pas.
4. **24-7 (portail et garage) dépend de 23-3** pour l'état d'un `cover` : elle ajoute `BARRIER_STATE`/`GARAGE_STATE` comme clé de relecture du `cover`, elle ne réimplémente pas le streaming. Alexandre a **écarté** l'option de livrer un `cover` optimiste (Q10 C, décision du 12/10) : 24-7 attend 23-3.
5. **L'export (24-2) reflète le streaming sans le construire** : il lit `StateSynchronizer.list_state_targets()` (déjà lu par le diagnostic, `http_server.py:3563`) et expose `state_source` = `streamed` / `optimistic` / `none` par entité. La couverture de 23-3 devient mesurable dès sa livraison, sans code de plus.
6. **Documentation « Limites »** : chaque story ne modifie que sa propre puce ; la phrase de 23-3 est la référence.
7. **Preuve** : les fixtures synthétiques de 23-1 (CC-48) servent aux preuves automatisées de 24-6 à 24-9 ; la preuve de parité sur la vraie box reste la comparaison d'exports par ClaudeBox.

### 7.2 Recoupement avec l'epic 18 (backlog depuis le 17/07)

L'epic 18 prévoit déjà `fan` (18-1), `lock` (18-2), `siren` (18-3), `valve` (18-4) et `event` (18-5). Les stories 24-8 et 24-9 recouvrent 18-4 et 18-2 ; 24-6 recouvrait 18-1, mais depuis la R1 elle n'ouvre plus `fan` (aucune vitesse mesurée). Ouvrir les deux ferait des doublons sur les mêmes fichiers. **Recommandation** (question 9) : l'epic 24 absorbe 18-2 et 18-4 (mêmes gates FR40/NFR10, mêmes sources `ha-projection-reference`) ; l'epic 18 garde 18-0, 18-1, 18-3 et 18-5. Le rattachement est noté dans `sprint-status.yaml` par un commentaire, sans changer le statut des entrées de l'epic 18 tant qu'Alexandre n'a pas tranché.

## 8. Décisions d'Alexandre : questions

Chaque question donne les options, leurs conséquences et une recommandation. **Aucune n'est tranchée.** Les options non retenues devront être marquées « écartée » après décision, comme en 22-1.

### Q1 : la liste des plugins natifs, et son vocabulaire

**Décision d'Alexandre (12/10 à 13:22) : la sémantique « exclu par plugin » est conservée ; options A, B et C écartées (pas de `voie_native`, pas de relibellé, pas de nouvelle clé). L'export porte toujours les `logicalId`.**

- **A (écartée).** Réutiliser `excludedPlugins`, relue comme « plugins gérés nativement par Home Assistant ». Libellés de la configuration changés ; pas de liste livrée par défaut ; pas de migration. Le plugin n'émet plus `excluded_plugin` mais `voie_native` (le code `excluded_plugin` reste accepté en entrée, pour d'anciens diagnostics). Conséquence : les équipements aujourd'hui « exclus par plugin » deviennent « voie native » à l'identique côté publication ; tout utilisateur qui avait mis un plugin dans cette liste pour une **autre** raison verrait un libellé inexact (risque faible : la bêta Market n'est pas encore publiée).
- **B (écartée).** Nouvelle clé `nativePlugins`, distincte de `excludedPlugins` (qui garde « exclusion voulue par l'utilisateur », `excluded_plugin`). Conséquence : deux listes, deux raisons, plus fidèle sémantiquement ; Alexandre déplace ses entrées une fois ; 24-3 grossit (config, ajax, UI, deux raisons).
- **C (écartée).** A + une liste de plugins natifs livrée par défaut. Conséquence : une liste à maintenir et à tenir juste en face de HA ; aucun plugin n'est choisi à la place de l'utilisateur dans A.

### Q2 : le mode « test du plugin »

**Décision d'Alexandre (12/10 à 13:22) : option B (liste « plugins en test », vide par défaut), sous réserve du `create-story` de 24-3 : puisque « exclu par plugin » est conservé, retirer un plugin de la liste suffit déjà à le tester ; le mode n'est maintenu que s'il apporte une garantie en plus.**

- **A (écartée).** Un interrupteur global : tous les plugins de la liste sont publiés. Conséquence : des dizaines d'entités en doublon avec les entités natives, noms identiques, ambiguïté pour Assist ; test lourd à défaire.
- **B (retenue).** Une liste « plugins en test » (vide par défaut) : un plugin à la fois sort de la liste des plugins exclus (depuis Q1 : équivalent à le retirer de `excludedPlugins`). Conséquence : un test borné et réversible ; une clé de configuration de plus ; l'export marque `native_test_mode: true` par équipement concerné.
- **C (écartée).** Par équipement, via le forçage existant. Conséquence : impossible en l'état, `excluded_plugin` est une inéligibilité d'étape 1 que `force_publish` ne lève pas (I1, `evaluate_equipment.py:362`) ; il faudrait changer ce contrat.

### Q3 : une pièce exclue n'écarte plus un équipement exposé à HomeKit

**Décision d'Alexandre (12/10 à 13:22) : option A.**

Visée : `excludedObjects` (`excluded_object`) **et** l'état « exclure » hérité d'une pièce dans le périmètre publié. Non visé : l'exclusion explicite de l'équipement (T8), l'état global « exclure ».

- **A (retenue).** Un équipement `homekit_exposed = true` n'est jamais écarté par sa pièce ; l'exclusion explicite de l'équipement l'emporte toujours. L'état global « exclure » reste respecté (ce n'est pas une exclusion de pièce). La configuration « Pièces exclues » dit « sauf équipements exposés à HomeKit ». Conséquence : des équipements aujourd'hui `excluded_object` seront **publiés au sync suivant**, donc des entités nouvelles dans HA ; leur nombre est **établi par ClaudeBox le 12/10 : 3 équipements** (virtuels, dans deux pièces exclues), d'après la configuration actuelle du plugin (inchangée depuis le 04/10) et le référentiel du 10/10 ; les 42 équipements exposés des plugins natifs ne sont pas publiés aujourd'hui (ils relèvent de 24-3, relibellé seul). L'effet est donc faible et l'option C ne se justifie plus ; la baseline de 24-2 le confirmera ; gate : liste préalable des équipements concernés par ClaudeBox, inventaire avant/après, retour arrière par « Supprimer de Home Assistant » (22-2) puis exclusion explicite.
- **B (écartée).** Ne rien changer, signaler l'écart : l'export garde `reason = excluded_object` pour ces équipements. Conséquence : exigence 3 non tenue ; zéro risque de production.
- **C (écartée).** A, mais derrière une clé de configuration « projection HomeKit par défaut », désactivée au premier déploiement et activée après relecture de la baseline. Conséquence : montée en charge maîtrisée ; une option de configuration de plus (à retirer après).

### Q4 : un équipement exposé à HomeKit au mapping ambigu ou probable

**Décision d'Alexandre (12/10 à 13:22) : option A.**

Le principe de moindre nuisance (`project-context.md`) interdit de publier ce que le plugin ne sait pas typer honnêtement. 17 commandes `ambiguous_skipped` étaient connues au 01/10.

- **A (retenue).** L'exposition HomeKit ne change pas la politique de confiance : un mapping ambigu ou refusé reste « impossibilité technique », avec sa raison canonique (`ambiguous_skipped`, `probable_skipped`, `no_generic_type_configured`…) dans l'export ; le forçage (20-2) reste le levier. Conséquence : l'écart apparaît dans l'export, avec sa cause, sans entité douteuse dans HA.
- **B (écartée).** L'exposition HomeKit force la publication des mappings ambigus. Conséquence : parité maximale, entités potentiellement fausses dans HA, contraire à l'anti-pattern « NE JAMAIS créer un type incorrect ».

### Q5 : contenu de l'export (confidentialité et périmètre)

**Décision d'Alexandre (12/10 à 13:22) : option A.**

- **A (retenue).** Identifiants seulement : `eq_id`, `logicalId`, `piece_id`, plugin (`eq_type`), types génériques, `unique_id`, `entity_id` attendu, raison, overrides ; **aucun nom** d'équipement, de pièce, de commande ni de scénario ; tous les équipements (exposés ou non) et tous les scénarios, pour mesurer aussi ce qui n'est pas exposé. Conséquence : fichier plus léger et sans nom ; la jointure se fait sur les identifiants (le référentiel de ClaudeBox a les noms par ailleurs). Les `logicalId` bruts restent nécessaires et peuvent contenir des adresses d'appareil : fichier lisible par l'administrateur seulement, jamais versé au dépôt ni écrit au journal.
- **B (écartée).** Ajouter les noms. Conséquence : lecture humaine plus simple, contraire à la minimisation (`project-context.md`, « Télémétrie et Logs ») et à CC-48 dès qu'un fichier est partagé.
- **C (écartée).** Limiter aux équipements exposés à HomeKit et aux plugins natifs. Conséquence : plus petit, mais un équipement mal détecté comme « non exposé » devient invisible.

### Q6 : lire l'export sans SSH

**Décision d'Alexandre (12/10 à 13:22) : option A.**

La route HTTP du démon n'est ouverte qu'en local (`127.0.0.1`, règle de sécurité du projet) ; la lire exige donc le tunnel SSH que l'on veut éviter.

- **A (retenue).** Une action AJAX d'administrateur (`getDecisionExport`), qui relaie la route du démon et renvoie le JSON (même motif que `exportDiagnostic`, budget fixe), plus un bouton « Télécharger l'export » dans la page du plugin ; ClaudeBox le lit par sa session Jeedom (compte dédié, gate 20-0 déjà en place). Conséquence : un point d'entrée PHP de plus, protégé par `isConnect('admin')`.
- **B (écartée).** Route du démon seule. Conséquence : exigence « sans SSH » non tenue.
- **C (écartée).** A + écriture périodique du fichier dans `data/` (déjà prévue) ; le fichier sert de repli si le démon est arrêté. Conséquence : un export potentiellement périmé ; l'horodatage de génération le dit.

### Q7 : ventilateurs et aspirateurs, changer de domaine ?

**Décision d'Alexandre (12/10 à 13:22) : option A.**

`FAN_*` est projeté en `switch` depuis 14-1 : l'allumage/extinction fonctionne déjà par la voix. Passer en `fan` change le **domaine** des entités déjà publiées (donc leur `entity_id`, ex. `switch.…` → `fan.…`), mais seul `fan` porte une vitesse.

- **A (retenue).** `fan` seulement quand un ordre de vitesse existe (`FAN_SPEED`/`ROTATION`) ; un `FAN_*` marche/arrêt seul reste `switch`. Conséquence : pas de changement de domaine inutile ; l'export classe ces cas « équivalents fonctionnels » plutôt qu'« écart de type ». *Établi par ClaudeBox le 12/10* : 8 équipements exposés portent `FAN_*` (marche, arrêt, état ; 5 aspirateurs compris), **aucun** n'a de commande de vitesse. Avec A, aucun ne change de type : 24-6 se réduit à un classement « équivalent fonctionnel » dans l'export, sauf apparition d'un ventilateur à vitesse.
- **B (écartée).** Tout `FAN_*` en `fan` (comportement prévu par 18-1). Conséquence : parité de type complète, tous les `entity_id` concernés changent, automatisations et cartes à retoucher.
- **C (écartée).** Ne rien changer. Conséquence : écart de type maintenu dans la mesure.

Aspirateurs : *établi par ClaudeBox le 12/10*, les 5 aspirateurs exposés portent des types `FAN_*` (marche, arrêt, état) : ils suivent la réponse choisie ; la famille « Robot » (`DOCK_STATE`, `DOCK`), mappée nulle part, n'est pas en cause et `vacuum` reste hors de cet epic.

### Q8 : type Home Assistant des scénarios

**Décision d'Alexandre (12/10 à 13:22) : option A.**

- **A (retenue).** Garder `button` (84 boutons existants inchangés) jusqu'à ce que la baseline établisse l'écart des cinq (section 6). Conséquence : aucun changement de production ; 24-5 peut se terminer en simple correction de mesure.
- **B (écartée).** `scene` (composant MQTT documenté, `ha-projection-reference.md`) pour les scénarios exposés à HomeKit. Conséquence : ouverture de `scene` dans `PRODUCT_SCOPE` (FR40/NFR10), nouvelle entité en plus du bouton, donc deux voies pour un scénario (contraire à « une seule voie ») sauf remplacement.
- **C (écartée).** `scene` pour tous les scénarios, en remplacement du bouton. Conséquence : 84 entités changent de domaine, `entity_id` modifiés.

*Établi par ClaudeBox le 12/10* : les cinq boutons existent et ne sont simplement pas exposés à Assist ; A est confirmée par les faits (section 6.1). Non vérifié : la manière dont Assist traite un `button` ou une `scene` (D4), seulement utile si B ou C est un jour envisagée.

### Q9 : l'epic 18 (fan, lock, valve)

**Décision d'Alexandre (12/10 à 13:22) : option A, dans sa version ajustée par la R1.**

- **A (retenue).** L'epic 24 absorbe 18-2 (`lock`) et 18-4 (`valve`) ; 18 garde 18-0, 18-1 (`fan`, sans demande réelle aujourd'hui), 18-3 et 18-5. Conséquence : une seule implémentation par domaine, l'ordre de 24 s'applique ; `sprint-status.yaml` annoté.
- **B (écartée).** Terminer 18-x avant 24-x. Conséquence : contredit l'ordre voulu (parité d'abord) et ouvre des domaines sans lien avec HomeKit.
- **C (écartée).** Deux voies parallèles. Conséquence : conflits garantis, déconseillé.

### Q10 : quand le type d'un équipement existant change (portail, garage, ventilateur selon Q7, vanne, serrure)

**Décision d'Alexandre (12/10 à 13:22) : option A.**

Le changement de domaine remplace l'entité : l'ancienne est dépubliée, la nouvelle créée, l'`entity_id` change. C'est la conséquence normale d'un type « remplacé » et le contraire du principe de 22-1/22-2 (aucun `entity_id` existant ne change), qui ne s'applique pas ici.

- **A (retenue).** Remplacement, une seule voie par équipement. Gate de chaque story : liste préalable des équipements concernés (identifiants), inventaire des registres avant/après, relevé par ClaudeBox des automatisations, scripts et cartes qui citent l'ancien `entity_id` ; l'`unique_id` change avec le type. Aucun remplacement sans cet inventaire.
- **B (écartée).** Coexistence de l'ancienne et de la nouvelle entité. Conséquence : deux voies et deux entités par équipement, ambiguïté pour Assist ; écartée par l'exigence 1.
- **C (écartée).** Pour le portail/garage uniquement : si l'état fiable n'est pas encore disponible (23-3 non livrée), livrer un `cover` **optimiste** plutôt qu'attendre. Conséquence : honnête (« optimiste » documenté), mais un volet/portail peut afficher un état faux jusqu'à la remontée d'état.

### Q11 : exposer à Assist les 5 boutons de scénario (ajoutée par ClaudeBox)

Geste côté Home Assistant, hors plugin (exigence 5) : le plugin ne l'exécute ni ne le configure.

- **A (retenue).** Oui : exposer les boutons des scénarios 20, 38, 50, 57 et 150 à Assist. **Décision d'Alexandre (12/10 à 13:22) : oui ; fait par ClaudeBox à 13:30.** Conséquence : l'écart des 5 scénarios est fermé côté HA ; 24-5 n'a plus qu'à vérifier leur présence dans l'export.
- **B (écartée).** Laisser les boutons non exposés. Conséquence : écart maintenu.

## 9. Hors périmètre et non retenu

- Modifier la configuration Homebridge, les types génériques Jeedom ou l'exposition à Assist dans HA (exigence 5).
- Un indicateur « exposé à Assist » dans le plugin (déclaratif, jamais lu) : non proposé ; le référentiel de ClaudeBox le tient.
- Les 2 sous-accessoires Homebridge sans eqLogic et l'alignement/exposition côté HA : hors plugin.
- `media_player`, `siren`, `event`, `vacuum` : hors de cet epic (reports de l'epic 18 et décision du 17/07).
- Rendre atomique `jeedom2ha_cache.json` : signalé (D8), pas traité.
- Toute modification du code, des tests, de `PRODUCT_SCOPE` : cette PR est documentaire. Les ouvertures `valve` et `lock` se feront sous FR40/NFR10 dans les stories 24-8 et 24-9 (`fan` seulement si un ventilateur à vitesse apparaît, `scene` seulement si Q8 B ou C est un jour retenue), jamais ici.

## 10. Risques et suivi

- **Publication de masse non maîtrisée (24-4).** Gate : liste d'équipements concernés avant déploiement, inventaire avant/après, option C de Q3 si Alexandre veut un déclenchement manuel.
- ~~**Faux écart « inclus mais non publié » pour `voie_native`**~~ : risque supprimé par la décision Q1 (`voie_native` n'est pas créée, `excluded_plugin` reste couvert par les tables existantes).
- **Changement de domaine d'entités existantes** (24-6 à 24-9) : inventaire des références avant/après (Q10).
- **Sécurité de la serrure (24-9)** : exposer `LOCK_OPEN` à une commande vocale est un risque de sécurité ; la story ne configure pas l'exposition à Assist (exigence 5), mais documente le risque et vérifie qu'aucune commande de déverrouillage n'est publiée sans `LOCK_STATE` ni confirmation d'état.
- **Conflits de fichiers** avec 22-2 (`http_server.py`, `desktop/js`) et 23-3 (`sync/state.py`) : ordre de la section 7 et règles de 7.1.
- **Export et vie privée** : voir Q5 ; test explicite « aucun nom, aucun secret, aucun identifiant MQTT » (AC de 24-2).
- **Coût de génération** : 292 équipements évalués à chaque export s'ils ne sont pas mémorisés ; 24-2 mémorise les décisions par commande au sync au lieu de les recalculer.

## 11. Doutes et points non vérifiés par cette session

- **D1.** *Levé en grande partie par ClaudeBox le 12/10* (T3). Restent deux cas à confirmer : le comportement de Homebridge pour un **équipement sans pièce** et pour une **pièce sans clé `sendToHomebridge`** ; Task 0 bis de 24-1. La provenance de l'exposition est lue sur un autre plugin : son comportement peut changer avec ses versions.
- **D2.** *Levé par ClaudeBox le 12/10* : cause des 5 scénarios établie (section 6.1).
- **D3.** *Partiellement levé le 12/10* : 3 équipements nouvellement publiés par 24-4 (Q3), 42 équipements exposés de plugins natifs déjà non publiés (restent « exclus par plugin »). Restent inconnus : le détail des 196 équipements inéligibles (292 − 96) par cause et la liste exacte des plugins saisis ; la baseline de 24-2 les donnera.
- **D4.** Le traitement par Assist d'un `button` ou d'une `scene`, et les champs exacts de découverte MQTT de HA 2026.9.4 pour `fan`, `valve`, `lock`, `cover` (`gate`, `garage`) : à lire dans la documentation officielle au début de chaque story de type (Task 0), en s'appuyant sur `ha-projection-reference.md` qui donne les champs obligatoires mais pas le comportement d'Assist.
- **D5.** *Partiellement levé le 12/10* : types génériques connus (24-7) ; le chemin de mappage actuel de chaque équipement (`binary_sensor` ou `button`) reste à lire dans l'export. La polarité de `BARRIER_STATE` / `GARAGE_STATE` reste à établir.
- **D6.** *Levé par ClaudeBox le 12/10* : les aspirateurs portent des types `FAN_*` sans vitesse.
- **D7.** Ce que sont exactement les « 2 sous-accessoires Homebridge sans eqLogic propre ».
- **D8.** `disk_cache.py:148` n'est pas atomique : un arrêt pendant l'écriture peut laisser un cache tronqué (lu comme « cold start », `disk_cache.py:155-205`). Ni nouveau, ni traité ici.
- **D9.** La proposition n'ajoute aucun FR/NFR au PRD. Si Alexandre veut que « voie native », « projection par défaut » et « export de décision » soient des exigences numérotées (FR40/NFR10 jouent pour l'ouverture de composants), il faudra une modification de PRD distincte.
- **D10.** Les tailles sont des ordres de grandeur ; la relecture de ClaudeBox peut les réviser, surtout 24-4 (surface de `published_scope.py` et de la surface de l'écran) et 24-6/24-7.

## 12. Critères de fin de l'epic (gates epic-level)

- L'export `schema_version: 1` est livré et lisible sans SSH ; une capture « avant » (baseline) et une capture « après » existent pour chaque story qui change la production ; elles sont conservées hors du dépôt.
- Tout équipement exposé à HomeKit a une décision et une raison canonique ; **chaque commande** d'un équipement exposé a une ligne avec sa raison dans l'export (aucune commande HomeKit sans raison).
- Les plugins natifs restent « exclus par plugin » (`excluded_plugin`, `exclu_par_plugin`), sans changement de libellé ni de contrat ; l'export porte leurs `logicalId` ; le mode « plugins en test », s'il est maintenu au `create-story` de 24-3, est vide par défaut et marqué dans l'export.
- Un équipement exposé à HomeKit n'est jamais écarté par sa pièce ; seules l'exclusion explicite de l'équipement et une impossibilité technique (raison canonique) l'écartent.
- Le plugin n'a écrit ni la configuration Homebridge, ni un type générique Jeedom, ni une exposition Assist (vérifié par recherche dans le diff et par la lecture seule des `getConfiguration`).
- Pour chaque type ouvert : entrée de registre, mapper, cas nominal et d'échec de `validate_projection()`, contrat 4D non régressé, inventaire avant/après, liste des références à l'ancien `entity_id` (Q10).
- Gate 20-0 vert avant chaque `done` qui touche l'écran ; golden et contrat 4D verts (champs additifs justifiés) ; aucun nom réel dans le dépôt (CC-48).
- Parité mesurée par l'export sur les mêmes 118 équipements et 5 scénarios, écarts restants classés : plugin / HA / hors périmètre.

## 13. R1 (ClaudeBox, 12/10) : ce qui a été établi et intégré

Relecture R1 de la PR #260 (tête `87e480f`) : cadrage jugé de grande qualité, pas de fusion. Vérifications en lecture seule faites par ClaudeBox le 12/10 vers midi, intégrées ci-dessus et dans les stories.

| # | Établi par ClaudeBox le 12/10 | Intégré dans |
|---|---|---|
| 1 | Règle d'exposition de Homebridge (pièce + équipement + valeur par défaut `sendToHomebridgeDefault`, scénarios `!= "0"`, aucun drapeau par commande) ; cache Homebridge de 123 accessoires, `logicalId` vide pour 65 | T3, §7, D1 ; 24-1 (AC1, AC2, AC6, Task 0), 24-2 |
| 2 | Cause des 5 scénarios : boutons présents dans HA, non exposés à Assist, outil de parité aveugle aux boutons de scénario | §3, §6.1, Q8, D2 ; 24-5 |
| 3 | Q3 : 3 équipements virtuels nouvellement publiés ; 42 équipements exposés de plugins natifs non publiés aujourd'hui | Q3, D3 ; 24-3, 24-4 |
| 4 | Q7 : 8 équipements `FAN_*` (5 aspirateurs), aucune vitesse | §3, §7, §7.2, Q7, Q9, D6 ; 24-6 réduite |
| 5 | Types génériques des équipements restants (portail, garage, vannes, serrure, prise, capteur) | §3, D5 ; 24-7 à 24-10 |
| 6 | Doutes mis à jour, section R1 ajoutée | §11, présente section, description de la PR |

Conséquences sur le découpage : 24-5 et 24-6 deviennent des stories documentaires (S) ; l'epic 18 garde 18-1 ; 24-7 se vérifie sur le cas « garage = bascule seule + état » ; 24-8 doit trancher le cas de la vanne d'un plugin Z-Wave (voir 24-8) ; 24-10 a une hypothèse de cause pour le capteur.

## 14. R2 (ClaudeBox, 12/10) : décisions consignées

Relecture R2 de la PR #260 (tête `4564e1d`) : R1 bien intégrée ; Alexandre a tranché le 12/10 à 13:22 (relayé par ClaudeBox). Aucune fusion.

| Décision | Effet sur le dépôt |
|---|---|
| Q1 : « exclu par plugin » conservé | 24-3 perd `voie_native` et la modification des artefacts figés ; l'export garde les `logicalId` ; exigence 2 annotée |
| Q2 B, Q3 A, Q4 A, Q5 A, Q6 A, Q7 A, Q8 A, Q9 A (ajustée R1), Q10 A | Options recommandées retenues, les autres « écartée » ; critères d'acceptation des stories figés sur ces choix |
| Q11 oui (boutons de scénario exposés à Assist, ClaudeBox 13:30) | Section 6.1 et 24-5 |
| `ready-for-dev` 24-1 et 24-2 ; `pe-epic-24` `in-progress` | `sprint-status.yaml`, epic, stories |

**Points que cette session signale sans les décider** :
- 24-3 n'est maintenue que si le mode « plugins en test » apporte plus que « retirer le plugin de la liste » ; le `create-story` le justifie ou abandonne la story.
- 24-2 touche `http_server.py` comme 22-2 (`ready-for-UX-validation`) : la note « démarrage après 22-2 `done` » est conservée dans la story ; ClaudeBox peut la lever.
- La baseline reste une étape de ClaudeBox après le déploiement de 24-2 ; 24-4 à 24-10 restent `draft` jusqu'à leur `create-story`.

### Journal des décisions

- 2026-10-12 — Cadrage documentaire (cette PR) : stories `draft`, questions Q1 à Q10.
- 2026-10-12, midi — **R1 (ClaudeBox)** : vérifications en lecture seule intégrées (section 13).
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q1 modifiée (« exclu par plugin » conservé), Q2 B, Q3 A, Q4 A, Q5 A, Q6 A, Q7 A, Q8 A, Q9 A (ajustée R1), Q10 A, Q11 oui.
- 2026-10-12, 13:30 — ClaudeBox expose à Assist les 5 boutons de scénario.
- 2026-10-12 — **R2** : décisions consignées ; `ready-for-dev` accordé à 24-1 et 24-2 par ClaudeBox ; `pe-epic-24` `in-progress`.

## Notes

- Aucune ouverture de `PRODUCT_SCOPE` n'est faite ou décidée par cette PR.
- Aucun code, test, script, déploiement ni fusion n'a été modifié par cette unité : documentation seulement. Aucun accès à la box, à Home Assistant ni à un secret.
