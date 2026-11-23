# Story 24.18 : Synchro légère quand seule l'activation d'un scénario publié change

Status: review

> Story de correction rédigée par une session cloud déléguée (2026-11-23), à partir de `origin/main` 85bab95, sans accès à la box ni à Home Assistant. Aucun nom réel, aucune IP (CC-48) : les constats de production ne citent que des identifiants. Le projet est gelé : seuls des défauts sont corrigés. Correction validée par Alexandre (décision « synchro légère », relayée par ClaudeBox le 2026-11-23).

## Story

En tant qu'utilisateur dont un scénario Jeedom active et désactive un autre scénario plusieurs fois par heure,
je veux que jeedom2ha ne relance pas une synchro complète du parc à chaque bascule d'activation d'un scénario publié,
afin que le démon, MQTT et les listeners de Jeedom ne soient pas sollicités des dizaines de fois par jour pour un simple changement de disponibilité de bouton, avec exactement le même résultat dans Home Assistant.

**Parcours : complet** (`docs/bmad-parcours-rapide-complet.md`) : le changement touche le démon et la publication vers Home Assistant (condition 4).

## Constat de production (relevés en lecture seule du 23/11, identifiants seulement)

- Le 23/11 : **62 synchros de service complètes**, par salves de pas consécutifs du cron des 5 minutes, y compris la nuit.
- **Cause prouvée** : le scénario 123 active puis désactive le scénario 129 toutes les 1 à 5 minutes (action `scenario` activate / deactivate). Le 129 est publié (`button.jeedom2ha_scenario_129`, `decision: published`, `reason: scenario_button`).
- `cron5()` → `reevaluateDecisionsIfChanged()` → `jeedom2ha_reevaluation_tick()` (`core/php/jeedom2ha_reevaluation.php`) calcule une empreinte qui contient `isActive` de chaque scénario : chaque bascule change l'empreinte et relance une **synchro complète** (`POST /action/sync`, mode `service`), suivie d'un réalignement des listeners (`syncStateListeners`).
- C'est le comportement voulu par 24.14 (D2 A) pour que la disponibilité du bouton suive l'activation. La PR #421 (story 12.6, réalignement des listeners par différence) supprime déjà les « Listener non trouvé » ; il reste le coût des synchros complètes.

## Ce qu'une bascule `isActive` change aujourd'hui (synchro complète, `origin/main` 85bab95)

Établi dans le code, pour un scénario **publié** (`publication_selected` vrai) :

| Élément | Effet de la synchro complète | Source |
|---|---|---|
| Configuration du bouton `…/button/jeedom2ha_scenario_<id>/config` | Republiée **à l'identique** : la charge ne dépend pas de `is_active` (nom, `unique_id`, `command_topic`, disponibilités) | `mapping/button.py`, `discovery/publisher.py:677-681` |
| Disponibilité retenue `jeedom2ha/scenario_<id>/availability` | `online` / `offline` selon `is_active`, qos 1, retenue — **seul changement visible dans HA** (bouton disponible / indisponible) | `transport/http_server.py` (`_publish_scenario_availability`, boucle des scénarios de `_do_handle_action_sync_body`) |
| `scenario_publications[id].active_or_alive` | Recalculé (`is_active`) ; sert au refus `scenario_inactive` d'un appui et à la republication sur reconnexion du broker / naissance de HA | `sync/command.py:1719-1724`, `_republish_scenarios_from_cache` |
| `app["topology"].scenarios[id].is_active` | Instantané neuf | statut des scénarios (`is_active`), export |
| Export de décision | `active`, `homekit_exposed_effective` (dérivé de `is_active`), `sync_at`, `sync_origin: service` ; `decision` / `reason` inchangés (D1 A) | `export/decision_export.py:_scenario_row` |
| Équipements | Tout le parc est réévalué et republié à l'identique (configurations retenues identiques), mémo et cache disque réécrits | `_do_handle_action_sync_body` |
| Listeners Jeedom | Réalignés après la synchro (`syncStateListeners`) | `jeedom2ha_reevaluation_tick` |
| Empreinte | Mémorisée si la synchro est complète | idem |

Pour un scénario **non publié** (`published: false`) : la synchro complète ne publie rien (retrait déjà confirmé, `_withdraw_unselected_scenario` ne rejoue rien) ; seuls l'instantané, le statut (`is_active`) et l'export (`active`) changent.

Effets « par accident » de la synchro complète : comme elle relit toute la topologie, elle applique aussi ce qui a changé depuis la synchro précédente sans changer l'empreinte (réglages en attente — accepté par Alexandre le 13/11 —, renommages, types génériques, commandes, opérations différées). Voir Dev Notes, « Ce que le chemin léger ne fait pas ».

## Décision d'Alexandre (2026-11-23) : la « synchro légère »

Quand, d'un pas à l'autre, **seule l'activation (`isActive`) d'un ou plusieurs scénarios** a changé, et rien d'autre de l'empreinte, on ne lance pas de synchro complète : on met seulement à jour ce qui dépend de cette activation dans HA (disponibilité des boutons concernés), exactement comme la synchro complète l'aurait fait. Le résultat dans HA doit être **identique**.

Règles posées :
1. Si autre chose a changé en même temps, ou en cas de doute : synchro complète, comme aujourd'hui.
2. Échec du chemin léger : retour à la synchro complète au pas suivant, aucune perte d'état.
3. Pas de réalignement des listeners sur le chemin léger (le parc ne change pas).
4. Un scénario non publié dont l'activation change ne déclenche rien du tout, en tenant compte de l'export de décision.
5. Les deux empreintes sont mémorisées correctement : un pas suivant sans changement ne relance rien.

## Conception

### PHP — empreinte en deux parties (`core/php/jeedom2ha_reevaluation.php`, fonctions pures)

- `jeedom2ha_decision_fingerprint_parts($eqRows, $scenarioRows, $settings, $selfEqType)` rend :
  - `structural` : SHA-256 de tout ce que contenait l'empreinte 24.14 **sauf** l'activation des scénarios : `id:isEnable:exclusion` des équipements, **identifiants** de tous les scénarios, plugins et pièces exclus, choix de publication des scénarios (`publishedScenarios`, `knownScenarioIds`) ;
  - `activation` : SHA-256 de `id:isActive` des seuls scénarios **publiés** (même règle que le démon et l'export : `publishedScenarios` absent → tous publiés ; sinon publié si l'id y figure) ;
  - `states` : `[{id, is_active}]` des scénarios publiés (ce qui sera envoyé au démon) ;
  - `fingerprint` : valeur composite `v2:<structural>:<activation>`, celle qui est mémorisée.
- L'activation d'un scénario **non publié** n'entre dans aucune partie (règle 4) : sa bascule ne change rien, aucun appel au démon. Sa ligne d'export (`active`) et son statut (`is_active`) restent ceux de la dernière synchro complète (le verdict, `not_published` / `scenario_not_selected`, ne dépend pas de l'activation) : conséquence assumée, documentée dans `docs/dev-decision-export.md`.
- Une seule clé de configuration (`decisionFingerprint`) garde la valeur composite : le démarrage, « Relire Jeedom », le choix de publication des scénarios et la tâche périodique la mémorisent / l'invalident **sans changer d'appelant** (`readDecisionFingerprint()` rend la composite). Deux composites égales ⇔ les deux parties égales (règle 5). Une valeur stockée à l'ancien format (24.14, sans `v2:`) n'est pas lisible en deux parties : synchro complète au premier pas, qui mémorise la composite.
- `jeedom2ha_reevaluation_tick()` gagne une dépendance facultative `light` (absente : comportement 24.14 strict) :
  1. composite inchangée → rien (inchangé) ;
  2. démon non prêt → rien (inchangé) ;
  3. parties structurelles égales (stockée et courante, toutes deux au format `v2`), activations différentes → **chemin léger** : empreinte invalidée, `POST /action/scenario_activation` avec `states` ;
     - réponse `applied` ou `unchanged` → composite courante mémorisée, **aucun réalignement des listeners**, statut `light` ;
     - `action_in_progress` (409) → statut `deferred`, empreinte laissée vide (l'opération en cours peut être une relecture qui l'a elle-même invalidée), synchro complète au pas suivant, comme le 409 de 24.14 ;
     - `full_sync_required` (le démon doute) → synchro complète **dans le même pas**, comme aujourd'hui (règle 1) ;
     - tout autre échec (exception, pas de réponse, publication MQTT en échec) → empreinte laissée vide, statut `failed`, **synchro complète au pas suivant** (règle 2) ;
  4. sinon → synchro complète 24.14, inchangée.
- `core/class/jeedom2ha.class.php` : `readDecisionFingerprintParts()` (mêmes deux requêtes que 24.14), `readDecisionFingerprint()` en rend la composite, `reevaluateDecisionsIfChanged()` lit les parties et branche `light`.

### Démon — action minimale `POST /action/scenario_activation`

- Authentifiée (`X-Local-Secret`), sérialisée par `action_lock` comme la synchro (attente 7 s, sinon 409 `action_in_progress`).
- Corps : `payload.scenarios = [{id, is_active}]` (identifiants entiers > 0, booléens). Corps mal formé → 400.
- **Refus « dans le doute »** (`full_sync_required`, aucune écriture) si : aucune synchro complète depuis le démarrage (`topology` ou `sync_at` absents) ; l'ensemble reçu diffère de l'ensemble des scénarios publiés par la dernière synchro (`scenario_publications` en `scenario_button` et `discovery_published`) ; un scénario reçu n'est pas publié ; une publication de scénario ou d'équipement est restée en échec (`scenario_publication_failed_ids`, `publication_result` en échec) ; une dépublication ou un nettoyage de disponibilité est différé ; un réglage en attente existe (overrides courants ≠ overrides appliqués du mémo, la règle `pending_changes` de l'export) — la synchro complète les aurait appliqués (décision du 13/11).
- Broker déconnecté → `broker_unavailable` (échec, synchro complète au pas suivant).
- Pour chaque scénario dont `is_active` diffère de l'instantané : publication de la disponibilité retenue (`_publish_scenario_availability`, mêmes topic, charge, qos et retenue que la synchro complète) ; si elle réussit, mise à jour de `topology.scenarios[id].is_active` et de `scenario_publications[id].active_or_alive`. Un échec arrête l'action : le scénario rejoint `scenario_publication_failed_ids` (statut `ha_pending`), réponse `publish_failed`, la mémoire des scénarios déjà publiés reste alignée sur HA (aucune perte d'état).
- Après au moins une mise à jour : `decision_memo.scenario_activation_at` (champ additif de l'export, remis à `null` par chaque synchro complète), export de décision réécrit, cache des états agrégés invalidé. `sync_at` et `sync_origin` ne changent pas : ils décrivent la dernière synchro complète.
- Aucun changement : `unchanged`, rien écrit.

### Interactions vérifiées

- **Démarrage du démon** : la synchro `boot` mémorise la composite (chemin 24.14 inchangé) ; avant elle, le démon refuse le chemin léger (`no_previous_sync`).
- **Naissance de HA / reconnexion du broker** : `_republish_scenarios_from_cache` republie la disponibilité depuis `active_or_alive`, mis à jour par le chemin léger.
- **« Relire Jeedom » / « Publier » / choix des scénarios** : « Relire Jeedom » et le choix de publication invalident puis mémorisent la composite (inchangé) ; « Publier » ne touche ni l'empreinte ni les scénarios. Le verrou `action_lock` sérialise le chemin léger avec eux.
- **Réévaluation 19.x** (aperçu, « pas encore appliqué ») : ne dépend pas de l'activation des scénarios ; les réglages en attente forcent la synchro complète (refus `pending_overrides`).
- **PR #421 (12.6)** : indépendante ; le chemin léger n'appelle simplement pas `syncStateListeners`.

## Critères d'acceptation

1. **AC1 — Découpage de l'empreinte.** La partie structurelle ne change pas quand seul `isActive` d'un scénario change ; elle change pour tout ce qui changeait l'empreinte 24.14 hormis l'activation (`isEnable`, exclusions, scénario ajouté ou supprimé, choix de publication). La partie activation change quand `isActive` d'un scénario **publié** change ; ni l'une ni l'autre ne change quand `isActive` d'un scénario **non publié** change. Aucun nom n'y entre ; l'ordre de lecture est sans effet.
2. **AC2 — Chemin léger.** Structure égale et activation différente : un seul appel `scenario_activation` avec les états des scénarios publiés, aucune lecture de topologie, aucun `POST /action/sync`, aucun réalignement des listeners ; composite mémorisée après `applied` / `unchanged`.
3. **AC3 — Synchro complète sinon.** Activation et autre chose changées ensemble, ancienne empreinte à l'ancien format, ou aucune empreinte : synchro complète 24.14, listeners réalignés.
4. **AC4 — Doute du démon.** `full_sync_required` : synchro complète dans le même pas.
5. **AC5 — Échec puis retour.** Échec du chemin léger (exception, aucune réponse, `publish_failed`, `broker_unavailable`) : empreinte vide, statut `failed` ; au pas suivant, synchro complète. 409 : statut `deferred`, empreinte vide, synchro complète au pas suivant.
6. **AC6 — Deux pas stables.** Après un chemin léger réussi, un pas sans changement ne contacte pas le démon (`unchanged`).
7. **AC7 — Résultat identique dans HA.** Pour un scénario publié qui bascule, l'action du démon publie exactement les messages que la synchro complète publierait pour lui (disponibilité retenue `online` / `offline`, qos 1) et rien d'autre ; la configuration du bouton n'est pas republiée (charge identique) ; `active_or_alive` et l'instantané sont mis à jour (appui refusé / accepté comme après une synchro complète, republication à la naissance de HA).
8. **AC8 — Refus prudents.** Le démon répond `full_sync_required` sans rien écrire dans chacun des cas de doute listés ci-dessus ; 401 sans secret ; 400 sur corps mal formé ; 409 si une opération est en cours.
9. **AC9 — Export.** `sync_at` et `sync_origin` inchangés par le chemin léger ; `scenario_activation_at` renseigné ; `active` du scénario à jour ; champ additif, `schema_version` reste 1.
10. **AC10 — Non-régression.** pytest complet, flake8, `php -l`, tests PHP autonomes, suite Node (hors les 3 échecs connus `25.4 AC8`), garde 25.4 AC31 verte avec les lignes remplacées déclarées.
11. **AC11 — Preuve terrain (par l'état, pas par le journal).** Voir Task 6.

## UI Impact

- **UI Impact:** Non — aucun fichier `desktop/` ni `core/ajax/` modifié ; le statut des scénarios et la disponibilité des boutons dans HA restent ceux d'aujourd'hui.

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) — à faire par ClaudeBox / l'agent de production, hors session cloud
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
- [x] Task 1 — Tests rouges d'abord (AC1 à AC9)
  - [x] 1.1 PHP `tests/test_php_story_24_18_scenario_activation_light.php` (autonome, sans cœur)
  - [x] 1.2 Python `resources/daemon/tests/unit/test_story_24_18_scenario_activation.py`
- [x] Task 2 — Empreinte en deux parties et pas de la tâche périodique (AC1 à AC6) — `core/php/jeedom2ha_reevaluation.php`
- [x] Task 3 — Branchement PHP (AC2) — `core/class/jeedom2ha.class.php` (`readDecisionFingerprintParts`, `light`)
- [x] Task 4 — Action du démon `/action/scenario_activation` (AC7 à AC9) — `transport/http_server.py`, `export/decision_export.py`
- [x] Task 5 — Documentation et garde 25.4 — `docs/dev-decision-export.md`, lignes remplacées déclarées (`REPLACED_BY_24_18`)
- [ ] Task 6 — Preuve terrain (ClaudeBox / agent de production, après fusion et déploiement par `scripts/deploy-to-box.sh`, lecture seule ; le journal par défaut de la prod n'écrit rien, la preuve se fait par l'état)
  - [ ] 6.1 Avant : relever dans l'export de décision (`getDecisionExport`) `sync_at`, `sync_origin`, `scenario_activation_at` et la ligne `scenario:129` (`active`) ; relever l'état de `button.jeedom2ha_scenario_129` dans HA (disponible / indisponible) ; relever dans la table `listener` de Jeedom les identifiants des listeners du plugin (`class = jeedom2ha`).
  - [ ] 6.2 Pendant une salve du scénario 123 (plusieurs bascules du 129 sur 15 à 30 min) : à chaque pas, `sync_at` et `sync_origin` **ne changent pas**, `scenario_activation_at` avance, `active` de `scenario:129` suit l'activation, et l'état du bouton du 129 dans HA suit (indisponible quand désactivé, disponible quand activé) au plus tard au pas suivant.
  - [ ] 6.3 Aucun réalignement des listeners : identifiants et nombre de listeners du plugin inchangés sur la salve (avec 12.6 fusionnée, les identifiants sont stables même après un réalignement : la preuve repose alors sur `sync_at` inchangé, aucune synchro complète n'ayant eu lieu).
  - [ ] 6.4 Bilan sur 24 h : nombre de synchros complètes (changements de `sync_at`) très inférieur aux 62 du 23/11 ; aucune bascule du 129 manquée dans HA.
  - [ ] 6.5 Contre-épreuve : un changement structurel (activer / désactiver un équipement de test, avec l'accord d'Alexandre) change `sync_at` (synchro complète).

## Dev Notes

### Fichiers

- `core/php/jeedom2ha_reevaluation.php` : ajouts (`jeedom2ha_decision_fingerprint_parts`, lecture de la composite, choix du chemin, branche `light` du pas). `jeedom2ha_decision_fingerprint()` (24.14) est gardée telle quelle (tests 24.14 et Lot 4a).
- `core/class/jeedom2ha.class.php` : `readDecisionFingerprintParts()`, `readDecisionFingerprint()`, `reevaluateDecisionsIfChanged()` (zone 539-602 ; la PR #421 touche 625-695 : pas de recouvrement de bloc attendu).
- `resources/daemon/transport/http_server.py` : nouvelle route, refus, application ; une ligne dans la synchro complète (remise à `null` de `scenario_activation_at`).
- `resources/daemon/export/decision_export.py` : champ `scenario_activation_at` du mémo et de l'export (additif).
- `tests/unit/test_story_25_4_non_regression.node.test.js` : `REPLACED_BY_24_18` (placé à côté de `REPLACED_BY_24_14` pour ne pas recouvrir les blocs modifiés par la PR #421).

### Ce que le chemin léger ne fait pas (risque résiduel, à connaître)

Une synchro complète déclenchée par une bascule appliquait au passage ce qui avait changé hors empreinte depuis la synchro précédente : renommage d'un scénario ou d'un équipement, type générique, commande ajoutée ou supprimée, exposition HomeKit. Avec le chemin léger, ces changements ne sont plus appliqués « par hasard » à la bascule suivante d'un scénario, mais, comme le documentait déjà 24.14, au prochain démarrage, « Relire Jeedom », ou à la prochaine synchro complète (tout changement structurel). Les réglages en attente (types choisis, « Toujours » / « Jamais ») restent appliqués par la tâche périodique : le démon refuse le chemin léger tant qu'il y en a.

### Garde-fous

- Principe de moindre nuisance : dans le doute, synchro complète.
- Aucun nom, aucune IP, aucun secret dans le code, les tests, la doc et les journaux ajoutés (CC-48).
- Pas de table DB : la composite vit dans la clé `decisionFingerprint`.
- PHP compatible 7.4 (matrice CI 7.4 / 8.2).

### Dev Agent Guardrails

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`
- Session cloud : aucun accès box / HA / SSH ; Task 0 et Task 6 à ClaudeBox.

### Retour arrière

Revert du commit de squash. Effet : la tâche périodique revient à la synchro complète à chaque bascule (comportement d'avant). La composite `v2:` stockée n'est pas lisible par l'ancien code comme empreinte 24.14 : une synchro complète au premier pas, puis empreinte 24.14 mémorisée. Aucune donnée persistée à migrer, aucun topic MQTT nouveau.

### References

- Story 24.14 (`24-14-decision-de-publication-stable-entre-deux-synchros.md`) : D1 A, D2 A, revues P2, décision du 13/11 sur les réglages en attente.
- Story 12.6 / PR #421 (réalignement des listeners par différence).
- Front v3 Lot 4a (`core/php/jeedom2ha_scenario_publication.php`) : règle de publication des scénarios.

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée).

### Debug Log References

- Tests rouges constatés avant le code : PHP 24.18 (fonction de découpage absente, 1 échec bloquant) ; Python 24.18 (17 échecs, route absente).

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created (create-story, 2026-11-23).
- Task 2 : `jeedom2ha_decision_fingerprint_parts`, `jeedom2ha_reevaluation_parse_fingerprint`, `jeedom2ha_reevaluation_light_candidate`, `jeedom2ha_reevaluation_light_step` ; `jeedom2ha_reevaluation_tick` accepte une empreinte en parties et une dépendance `light` facultative (absente : 24.14 strict). `jeedom2ha_decision_fingerprint` (24.14) inchangée.
- Task 3 : `readDecisionFingerprintParts()` (mêmes requêtes), `readDecisionFingerprint()` rend la composite `v2:` — le démarrage, « Relire Jeedom » et le choix des scénarios mémorisent donc les deux parties sans changement d'appelant ; branche `light` vers `/action/scenario_activation` (15 s, une tentative).
- Task 4 : route `POST /action/scenario_activation` (secret, `action_lock`, 400 / 409), refus `full_sync_required` (`no_previous_sync`, `scenario_set_mismatch`, `previous_publication_failed`, `deferred_operations`, `pending_overrides`), `broker_unavailable`, `publish_failed` (scénario ajouté à `scenario_publication_failed_ids`) ; mise à jour de l'instantané et de `active_or_alive` après publication seulement ; `scenario_activation_at` (mémo, export, remis à `null` par la synchro complète).
- Task 5 : `docs/dev-decision-export.md`, `docs/fr_FR/index.md`, `docs/fr_FR/changelog_beta.md` ; garde 25.4 : `REPLACED_BY_24_18` (2 lignes de `core/class/jeedom2ha.class.php`).
- Vérifications (2026-11-23) : `python3 -m pytest` 3828 réussis, 37 ignorés (base : 3809) ; `flake8 resources/daemon tests` propre ; `php -l` sur tous les fichiers PHP ; tests PHP autonomes 24 réussis, 3 ignorés (cœur Jeedom requis), 0 échec ; `node --test tests/unit/*.node.test.js` 1649 réussis, 3 échecs connus `25.4 AC8` (identiques à la base, hors périmètre).
- Commandes ciblées : `php tests/test_php_story_24_18_scenario_activation_light.php` (51 vérifications) ; `python3 -m pytest resources/daemon/tests/unit/test_story_24_18_scenario_activation.py` (20 tests) ; `node --test tests/unit/test_story_25_4_non_regression.node.test.js`.
- Tasks 0 et 6 (terrain) : hors session cloud, à ClaudeBox / l'agent de production.

### File List

- `core/php/jeedom2ha_reevaluation.php` (modifié)
- `core/class/jeedom2ha.class.php` (modifié)
- `resources/daemon/transport/http_server.py` (modifié)
- `resources/daemon/export/decision_export.py` (modifié)
- `resources/daemon/tests/unit/test_story_24_18_scenario_activation.py` (nouveau)
- `tests/test_php_story_24_18_scenario_activation_light.php` (nouveau)
- `tests/unit/test_story_25_4_non_regression.node.test.js` (modifié)
- `docs/dev-decision-export.md`, `docs/fr_FR/index.md`, `docs/fr_FR/changelog_beta.md` (modifiés)
- `_bmad-output/implementation-artifacts/24-18-synchro-legere-activation-scenario.md` (nouveau), `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié)

## Senior Developer Review (AI) — auto-revue `bmad-code-review` (2026-11-23)

Revue adversariale du diff (hors `_bmad/` et `_bmad-output/`). File List conforme à `git status`. AC1 à AC10 implémentés et couverts (AC11 : terrain, Task 6). Constats :

- **[HIGH, corrigé] 409 sur le chemin léger.** La première version remettait l'empreinte précédente après un 409. Si l'opération en cours était une « Relire Jeedom » (qui invalide l'empreinte avant d'envoyer sa synchro) et que celle-ci finissait partielle, l'empreinte remise masquait l'échec et le pas suivant prenait le chemin léger au lieu de la synchro complète. Corrigé : rien n'est remis, empreinte vide, synchro complète au pas suivant (comme le 409 de 24.14). Test PHP mis à jour.
- **[MEDIUM, corrigé] Publication d'équipement en échec non vue par le démon.** Le refus ne regardait que les scénarios ; une publication d'équipement restée en échec (que la synchro complète rejouerait) n'empêchait pas le chemin léger quand l'empreinte avait été mémorisée par ailleurs. Ajout de `_has_failed_equipment_publication` au refus `previous_publication_failed`, et d'un test.
- **[MEDIUM, documenté, non corrigé] Changements hors empreinte plus appliqués « par hasard ».** Renommage (y compris du nom du bouton d'un scénario dans HA), type générique, commandes : une bascule d'activation ne les applique plus ; ils le sont au démarrage, à « Relire Jeedom », ou à la prochaine synchro complète (Dev Notes). Les étendre au chemin léger ou à l'empreinte structurelle sortirait de la décision d'Alexandre ; à trancher par lui si besoin.
- **[LOW] Décalage de versions PHP / démon** (route absente : 404) : chaque bascule échoue en léger puis donne une synchro complète au pas suivant. Ne se produit pas avec `deploy-to-box.sh` (plugin et démon déployés ensemble).
- **[LOW] Verdict d'équipement non mémorisé** (exception rattrapée par `_memorize_decision`) avec un override : `pending_overrides` refuse alors le chemin léger à chaque bascule, soit le comportement d'avant 24.18 (sûr).
- **[LOW] `active` d'un scénario non publié** dans l'export et `is_active` du statut : valeur de la dernière synchro complète (règle 4), documenté dans `docs/dev-decision-export.md`.

Statut : `review` maintenu (et non `done`) : la règle du projet exige la preuve terrain (Task 6) pour tout changement de publication vers HA. UI Impact : Non (aucun fichier `desktop/` ni `core/ajax/`).

## Journal

- 2026-11-23 — create-story (session cloud déléguée) : défaut de prod du 23/11 (62 synchros complètes), décision d'Alexandre (synchro légère) ; story `ready-for-dev`.
- 2026-11-23 — dev-story (session cloud déléguée, tests rouges d'abord) : Tasks 1 à 5 ; story `review`. Restent Task 0 et Task 6 (terrain).
- 2026-11-23 — code-review (auto-revue) : 1 HIGH et 1 MEDIUM corrigés, 1 MEDIUM documenté ; story reste `review` jusqu'à la preuve terrain.
