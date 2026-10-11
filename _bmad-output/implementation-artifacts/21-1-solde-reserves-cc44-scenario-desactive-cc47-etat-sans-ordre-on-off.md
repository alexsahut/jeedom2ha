# Story 21.1 : Solde des réserves de l'étape 4 — scénario désactivé (CC-44) et état sans ordre On/Off (CC-47)

Status: backlog

> **Statut : `backlog` — `ready-for-dev` NON accordé** (créée le 2026-10-11 par une session cloud déléguée, lecture seule). Cinq questions (Q0 à Q4, dont un sous-point Q2b) attendent une décision d'Alexandre ; elles sont posées plus bas, chacune avec une recommandation, et **aucune n'est tranchée par ce document**. La numérotation `21.1` / `pe-epic-21` est **provisoire** (Q0). Les AC marqués **[Qx]** dépendent de la réponse et sont rédigés sur la recommandation ; ils sont à figer après décision.

## Story

En tant qu'utilisateur du plugin qui pilote sa maison depuis Home Assistant,
je veux qu'un scénario Jeedom désactivé ne laisse pas un bouton fantôme dans Home Assistant, et que ma commande d'état seule (sans ordre On/Off) soit publiée sous un type qui lui correspond ou, à défaut, expliquée honnêtement,
afin que Home Assistant reflète fidèlement ce que Jeedom permet réellement, et que l'écran ne me demande plus de « préciser des types » qui n'existent pas.

**Parcours : démon + interface.** Le bloc CC-44 est purement démon (sync, discovery MQTT). Le bloc CC-47 touche le mapping du démon et, selon Q3/Q4, des libellés de la surface (`desktop/js/jeedom2ha_mapping_override.js`) : s'il y a un changement visible, la story passe par le gate 20-0 et `ready-for-UX-validation` avant `done`. Preuve terrain obligatoire (publication vers HA) : gate d'inventaire avant/après, 0 erreur.

## Contexte et périmètre

- **Origine.** Rétrospective `pe-epic-20-retro-2026-10-11.md` (« Risques résiduels » : réserve 20-2 / commande 5369, réserve 20-4 AC6). Ordre décidé par Alexandre le 2026-10-11 à 15:48 : 20-5 (fait) → **CC-44 + CC-47** → CC-36 avec CC-51 et la story « compteurs » → epic parité HomeKit (CC-33).
- **CC-44 (réserve AC6 de 20-4).** Un scénario Jeedom désactivé garde son bouton dans HA. Constat de terrain du 2026-10-06 (`20-4-preuve-validation-ux-2026-10-06.md`, « Constats non bloquants ») : scénarios 72 et 2 désactivés (`isActive=0`), retirés de `scenario_publications` en mémoire au rescan, mais leurs topics retenus `homeassistant/button/jeedom2ha_scenario_72/config` et `…_2/config` restent sur le broker. Défaut présent depuis la story 10.1 (PR #119), antérieur à l'epic 20.
- **CC-47 (réserve de 20-2).** Commande 5369 (équipement 579) : un état sans ordre On/Off. Un type seul ne lève pas l'ambiguïté et son forçage est grisé (`20-2-preuve-complement-2026-10-06.md`, « Verdict »). Décision d'Alexandre du 2026-10-06 (~15:09) : 20-2 close avec cette réserve, 5369 reste en mode automatique, story dédiée.
- **Dans le périmètre :**
  - retrait (ou autre traitement décidé en Q2) du bouton HA d'un scénario désactivé, y compris la reprise au redémarrage du démon (Q2b) ;
  - traitement décidé en Q3 pour une commande d'état seule ;
  - correction des libellés trompeurs associés (Q4) ;
  - tests unitaires, mise à jour du golden si le corpus doré contient des scénarios, preuve terrain par l'humain.
- **Hors périmètre :**
  - toute ouverture de `PRODUCT_SCOPE` : `sensor` et `binary_sensor` y sont déjà (`resources/daemon/validation/ha_component_registry.py:70`), donc FR40/NFR10 ne sont pas déclenchés pour CC-47 ;
  - CC-36, CC-51 et la story « compteurs » ; CC-33 ; CC-45, CC-46 (autres reports de 20-2) ;
  - le forçage des 16 autres commandes ambiguës (déjà livré par 20-2, sur demande d'Alexandre équipement par équipement) ;
  - tout accès à la box, à HA, à un secret ; `scripts/deploy-to-box.sh` n'est **jamais** lancé par cette session (la preuve terrain est faite par l'humain).

## Questions pour Alexandre (avec recommandation)

> Chaque question a une recommandation (**R**). Réponse attendue sous la forme « Q0 A, Q1 A, Q2 A, … ». Tant que Q0 à Q2b ne sont pas tranchées, la story reste `backlog`.

### Q0 — Numérotation et rattachement à un epic

La convention du dépôt : un epic `pe-epic-N` clos n'est pas rouvert, une story porte la clé `N-M-slug` et le workflow `create-story` refuse de créer une story dans un epic `done` (« créer un nouvel epic pour le travail additionnel », `workflow.md`, step 1). L'epic 20 est `done` (rétro du 2026-10-11) ; l'epic 18 est `backlog` mais traite d'ouvertures de domaines HA, sans rapport.

- **A (R) — Nouvel `pe-epic-21` « Solde des réserves de l'étape 4 », story `21-1`.** Garde l'epic 20 clos et sa rétrospective intacte ; réserve le numéro suivant à un epic court, `done` dès que 21-1 l'est. Aucun SCP lourd : cadrage documentaire à la demande directe du mainteneur, comme pe-epic-19 (« pas de SCP dédié, aucune ouverture PRODUCT_SCOPE, aucun nouveau FR/NFR »). Conséquence : les epics suivants (compteurs, parité HomeKit) prennent 22 et 23.
- **B — Rouvrir `pe-epic-20` et créer `20-6`.** Rattachement le plus « naturel » (les deux réserves viennent de 20-2 et 20-4) mais contredit la clôture du 2026-10-11 et ses gates epic-level ; à éviter.
- **C — Story hors epic (chantier `fix/` seul, sans clé).** Plus léger, mais perd le suivi BMAD (sprint-status) alors que la story demande un `create-story → dev-story → code-review` complet.

*Inscrit provisoirement selon A* : `pe-epic-21: backlog` et `21-1-…: backlog` dans `sprint-status.yaml`, section « Epic 21 » proposée dans `epics-projection-engine.md`. Si Alexandre choisit B ou C, ces trois fichiers sont à renommer/déplacer (aucun code n'est concerné).

### Q1 — Une story ou deux ?

Les deux réserves n'ont rien en commun techniquement (cycle de vie des scénarios vs. mapping d'un état seul), et les règles Git du dépôt disent « une branche / une PR = un seul sujet ».

- **A (R) — Une story (comme demandé), deux blocs de tâches indépendants, deux PR de développement** (bloc A = CC-44, livrable seul dès Q2 tranchée ; bloc B = CC-47, après Q3/Q4). La story ne passe `done` que lorsque les deux blocs sont prouvés.
- **B — Deux stories `21-1` (CC-44) et `21-2` (CC-47).** Plus propre au suivi, mais CC-44 devient livrable sans attendre CC-47, ce qui est aussi le cas en A.

### Q2 — Scénario désactivé : retirer le bouton HA ou le rendre indisponible ?

Faits : un bouton fantôme est déjà **inerte** (appui rejeté par le démon : `unknown_runtime_entity`, `resources/daemon/sync/command.py:569-574`) ; un équipement désactivé est, lui, dépublié (raison `disabled_eqlogic`). Le publisher sait déjà retirer un scénario (`resources/daemon/discovery/publisher.py:277-296`, payload vide retenu) mais **aucun appelant** ne l'utilise.

- **A (R) — Retirer le bouton** (payload de discovery vide retenu sur le topic du scénario). Cohérent avec les équipements désactivés ; HA ne montre que ce qui fonctionne ; réactiver le scénario le republie au sync suivant (boucle existante, `http_server.py:2081-2099`).
- **B — Le garder, « indisponible »** (disponibilité par entité hors ligne). Garde l'historique et les automations HA qui référencent le bouton, mais exige un mécanisme de disponibilité par scénario qui n'existe pas (la disponibilité actuelle est calculée à partir d'un `eqLogic`, `publisher.py:383-386`, et un scénario n'en a pas) : plus de code, plus de risque, pour un bouton inerte.
- **C — Statu quo documenté.** Rejeté par la décision d'Alexandre du 2026-10-06 (« CC-44 sera traité dans une story dédiée »).

*Effet de bord à connaître* : il n'y a pas de sync périodique (F7 de 20-2 : sync au démarrage du démon et au rescan seulement). Le bouton disparaîtra donc de HA au **prochain rescan ou redémarrage du démon**, pas à l'instant où le scénario est désactivé dans Jeedom.

#### Q2b — Scénario supprimé ou désactivé pendant que le démon est arrêté

Le retrait ne peut se fonder sur la seule mémoire du sync précédent (`scenario_publications` est vide au démarrage, `http_server.py:4555`, et n'est pas persisté). Deux sous-cas : (i) scénario **présent mais inactif** dans le snapshot ; (ii) scénario **absent** du snapshot (supprimé dans Jeedom).

- **A (R) — Traiter (i) sans mémoire** : à chaque sync, publier le payload vide pour tout scénario inactif du snapshot (idempotent, sans effet si le topic n'existe pas) ; **et (ii) par un petit registre persisté des scénarios publiés** (dans `data_dir`, même esprit que le cache de publications, `http_server.py:2117`). Couvre aussi les suppressions et les redémarrages.
- **B — Traiter (i) seul**, laisser (ii) hors périmètre et le consigner. Moins de code ; un scénario supprimé garde son bouton (même défaut, autre cause).

### Q3 — Commande 5369 (état sans ordre On/Off) : quel type HA cible ?

Faits (code au SHA `15576cf`) : `SwitchMapper` classe un `ENERGY_STATE` seul « orphelin » en `ambiguous` avec `reason_code` `switch_state_orphan`, capacités `has_on_off=False` (`resources/daemon/mapping/switch.py:198-207` (classement) et `:214-235` (résultat)) ; `decide_publication` refuse l'`ambiguous` au niveau 1 sauf forçage (`models/decide_publication.py:106-109`) ; le forçage est grisé parce que `validate_projection('switch', …)` exige `has_command` (`validation/ha_component_registry.py:155-160`, `required_capabilities` du `switch`), d'où « Projection invalide pour ce type HA. » (`desktop/js/jeedom2ha_mapping_override.js:209`). Les types `sensor` et `binary_sensor` n'exigent que `has_state` (même fichier) et sont dans `PRODUCT_SCOPE`. `BinarySensorMapper` exclut volontairement les `ENERGY_*` (`mapping/binary_sensor.py:20-24`, `:112`), donc rien ne les reprend aujourd'hui.

- **A (R) — `binary_sensor` pour un état seul.** `ENERGY_STATE` est une information binaire : un `binary_sensor` HA en lecture seule dit exactement « allumé / éteint » sans prétendre piloter quoi que ce soit. Aucune ouverture de périmètre. À réaliser au niveau du mapper : un état orphelin (sans ON/OFF) cesse d'être « ambigu pour le switch » et devient un `binary_sensor` `sure`, sans changer le cas du trio complet ni le cas « prise mesureuse » (`I11`, `19-2`). Impact : tout état orphelin du parc change de type par défaut (à mesurer, Task 1.3), pas seulement 5369.
- **B — `sensor`.** Publie la valeur brute 0/1 ; perd la sémantique binaire de HA (états « allumé/éteint », historique lisible) ; ne se justifie que si la commande n'est pas de sous-type binaire.
- **C — Ne pas publier, mais le dire honnêtement** (cause « état seul, rien à piloter », sans l'invitation trompeuse à « préciser les types »). Aucun changement de publication ; 5369 reste hors de HA.
- **D — Pas de changement de mapper : laisser l'utilisateur choisir** le type `binary_sensor` / `sensor` pour 5369 puis forcer. À **vérifier** avant de la proposer : l'override de type ne relance pas le mapper (D8, `mapping/overrides.py:376-396`) et le publisher `binary_sensor` attend des champs (`state_topic`, `reason_details`) que le mapping `switch` ne porte pas ; ce chemin pourrait être invalide ou publier un payload incomplet (hypothèse non vérifiée en exécution).

*Pas de recommandation faite par défaut en faveur de `sensor`* : si Alexandre préfère un autre type (`switch` en lecture seule n'est pas une option : le registre exige `command_topic`), le préciser en réponse libre.

### Q4 — Libellés trompeurs

L'écran dit « type Home Assistant ambigu — précisez les types génériques dans Jeedom » pour `ambiguous_skipped` (`jeedom2ha_mapping_override.js:588`) alors qu'aucun type générique ne manque (F10 de 20-2), et le démon renvoie la même invitation (`resources/daemon/models/cause_mapping.py:159` et `:169`).

- **A (R) — Corriger dans cette story** les libellés des causes concernées par les deux blocs (état seul : `switch_state_orphan`, libellé existant `jeedom2ha_mapping_override.js:591`) ; le reste de F10 (autres causes d'ambiguïté) reste au backlog.
- **B — Ne corriger aucun libellé ici**, tout renvoyer à la story « compteurs ».

## Faits relevés le 2026-10-11 (lecture seule, `main` `15576cf`)

Pointeurs revérifiés dans le code au moment de l'écriture (les lignes ont bougé depuis le constat du 06/10 et les lignes annoncées du 11/10).

**CC-44 — cycle de vie des scénarios**

- **C1** — Boucle de publication des scénarios : `resources/daemon/transport/http_server.py:2078` (commentaire « Story 10.1 »), `:2081` (boucle sur `snapshot.scenarios`), `:2082-2083` (`if not scenario.is_active: continue` — **les inactifs sont ignorés, jamais dépubliés**), `:2084-2099` (mapping, décision, `publisher_registry.publish`).
- **C2** — Purge **mémoire seulement** : `http_server.py:2100-2105` (`stale_scenario_ids` = ids présents au sync précédent et absents du courant ; `pop` de `request.app["scenario_publications"]` ; seul un `_LOGGER.info` « Purged stale scenario_id » l'accompagne). **Aucun `unpublish` n'est appelé** : c'est le défaut CC-44.
- **C3** — `scenario_publications` n'est pas persisté : initialisé vide à `http_server.py:4555` ; `save_publications_cache` (`:2117`) ne concerne que `publications` (équipements).
- **C4** — Le retrait existe côté publisher mais n'est appelé par personne : `resources/daemon/discovery/publisher.py:277-296` (`unpublish("jeedom2ha_scenario_<id>")` → payload `""`, `qos=1`, `retain=True`) ; topic construit par `_build_topic(0, entity_type="button", node_id=…)`, `publisher.py:352-355` → `<préfixe>/button/jeedom2ha_scenario_<id>/config`.
- **C5** — Les mécanismes de report de dépublication (`pending_discovery_unpublish`, `_defer_discovery_unpublish`, `_replay_deferred_discovery_unpublish`, `http_server.py:985-1018`) sont indexés par **entier `eq_id`** : un id de scénario peut **entrer en collision avec un id d'équipement**. Ne pas y ranger un scénario tel quel ; prévoir un report distinct ou une clé typée.
- **C6** — Le bouton fantôme est inerte : `resources/daemon/sync/command.py:562-574` (`_handle_scenario_command` rejette avec `unknown_runtime_entity` si la décision est absente ou `should_publish` faux). Abonnement MQTT : `transport/mqtt_client.py:32` (`jeedom2ha/+/cmd`).
- **C7** — Source du drapeau : `core/class/jeedom2ha.class.php:799-811` (`is_active => (bool)$sc->getIsActive()`) → `models/topology.py:107` (`is_active: bool = True`) et `:194-200` (parsing, défaut `True`).
- **C8** — Disponibilité d'une entité calculée depuis un `eqLogic` (`publisher.py:383-386`, `availability_from_snapshot(mapping.jeedom_eq_id, …)`) : pour un scénario, `jeedom_eq_id` est l'id du **scénario** (`mapping/button.py:44-64`). À vérifier en Task 1 si l'option B de Q2 est retenue ; **risque de collision d'ids** déjà présent pour un scénario et un équipement de même identifiant (hors périmètre, à consigner).
- **C9** — Aucune interface du plugin ne liste les scénarios (aucune occurrence dans `desktop/`), ni la documentation `docs/fr_FR/index.md` : le seul témoin utilisateur est le bouton dans HA.

**CC-47 — état sans ordre On/Off**

- **C10** — Classement de l'orphelin : `resources/daemon/mapping/switch.py:198-207` (`ENERGY_STATE` seul → `ambiguous`, `reason_code_suffix="state_orphan"`), `:214-235` (résultat `MappingResult` `switch`, `confidence="ambiguous"`, `reason_code="switch_state_orphan"`, capacités `has_on_off=False`, `has_state=True`).
- **C11** — Refus de décision : `resources/daemon/models/decide_publication.py:106-109` (niveau 1 : seul l'`ambiguous` **forcé** passe) ; refus de projection : `validation/ha_component_registry.py:155-160` + `required_capabilities` du `switch` (`has_command`), résolu sur `SwitchCapabilities.has_on_off` (`:100-112`).
- **C12** — Message « Projection invalide pour ce type HA. » : `desktop/js/jeedom2ha_mapping_override.js:209` ; message « Aucune commande clé propre à cette entité. » : `:159` (sur les deux entités de l'équipement qui n'ont pas de commande propre). Libellé de cause `switch_state_orphan` → « état sans ordre On/Off » : `:591` ; liste des causes d'ambiguïté précises : `:639`.
- **C13** — Aucun mapper ne reprend un `ENERGY_STATE` orphelin : `mapping/binary_sensor.py:20-24` (`_SWITCH_OWNED_GENERIC_TYPES` contient `ENERGY_STATE`), `:69-87` (`_is_multi_domain_eq`) et `:112` (le cas multi-domaine ignore les états consommés par un trio switch complet via `_switch_readback_cmd_ids`) ; `mapping/sensor.py:120` (`switch_types`), `:164-169` (`ENERGY_STATE` « consommé » seulement s'il existe `ENERGY_ON`/`ENERGY_OFF`). L'état orphelin tombe donc entre les mappers (à confirmer par test, Task 1.2 : l'équipement 579 expose en plus des mesures numériques, ce qui active le chemin multi-entité de `mapping/registry.py:100-127`).
- **C14** — Un override de type ne relance pas le mapper et laisse les capacités inchangées : `resources/daemon/mapping/overrides.py:376-396` (docstring, D10/D11) et `:413-432` (application). L'ancien relevé de 20-2 (« `overrides.py:398-402`, `decide_publication.py:94-97` ») n'est plus à jour : le forçage de l'`ambiguous` est livré (`decide_publication.py:106-109`).
- **C15** — Données de terrain connues (identifiants seulement, **aucun nom réel** dans cette story) : équipement 579, commandes 5368 (non couverte), **5369 (état orphelin, bloquante)**, 5493, 5494, 5689, 5695 (prêtes) ; `19-1-field-proof-2026-09-28.md`, `20-1-preuve-validation-ux-2026-10-05.md`. Le gate 20-0 simule la bascule de 5369 (« Sera publié dans Home Assistant : 5 commande(s) prête(s). ») sans écriture réelle ; cette simulation **ne prouve pas** la publication.

## Acceptance Criteria

> Rédigés sur les recommandations (A). À figer après réponse d'Alexandre.

### Bloc A — CC-44

1. **[Q2 A] Un scénario inactif n'a plus de bouton dans HA.** À l'issue d'un sync, tout scénario du snapshot avec `is_active=false` voit son topic de discovery vidé (payload vide retenu, `qos=1`) ; le bouton disparaît de HA. Test unitaire : snapshot avec un scénario actif et un inactif, publisher simulé ; seul l'actif est publié, l'inactif reçoit un `unpublish`.
2. **[Q2 A] Réactivation.** Un scénario réactivé est republié au sync suivant, avec son bouton, sans autre action ; son `unique_id` et son `command_topic` sont inchangés.
3. **[Q2b] Reprise sans mémoire et suppression.** Un scénario désactivé alors que le démon était arrêté est retiré au premier sync après le démarrage. **[Q2b A]** Un scénario supprimé de Jeedom est retiré au sync suivant grâce au registre persisté ; le registre est lisible/écrit atomiquement et son absence ou sa corruption ne casse pas le sync (sans bouton publié inconnu, aucun retrait n'est tenté). **[Q2b B]** Le cas « supprimé » est consigné comme limite connue dans la story et le changelog.
4. **Broker déconnecté.** Si MQTT est indisponible au moment du retrait, il est reporté et rejoué à la reconnexion (comme les équipements), **sans collision d'identifiants avec un `eq_id`** (clé typée ou registre séparé, voir C5). Test : scénario d'id N et équipement d'id N, un seul retrait ne touche pas l'autre.
5. **Pas de régression.** Les scénarios actifs, le bouton d'un équipement, `scenario_publications` (appui sur le bouton d'un actif accepté, d'un inactif rejeté) et le golden corpus sont inchangés, ou le golden est réaligné avec justification si le corpus contient des scénarios inactifs. La suite complète (`make test`) et `flake8` sont verts.
6. **Journal.** Chaque retrait est tracé (`[SCENARIO] Unpublished …`), sans nom réel de scénario ni secret.

### Bloc B — CC-47

7. **[Q3 A] L'état seul est publié sous un type cohérent.** Une commande `ENERGY_STATE` sans `ENERGY_ON`/`ENERGY_OFF` est projetée en `binary_sensor` (lecture seule, `device_class` neutre) avec un `unique_id` stable dérivé de l'identifiant de la commande ; elle n'est plus `ambiguous`. Test nominal + test d'échec (`validate_projection`) pour ce chemin, conformément à AR13 même si `PRODUCT_SCOPE` n'est pas modifié.
8. **Non-régression des cas voisins.** Un trio complet `ENERGY_STATE/ON/OFF` reste un switch ; une prise mesureuse (équipement actionnable avec mesures) garde son comportement (invariant I11, story 19-2) ; un `ENERGY_STATE` consommé par un switch n'est jamais dupliqué en `binary_sensor` ; un équipement avec deux états orphelins ne produit pas de collision d'`unique_id`. Contrat 4D et golden verts.
9. **Aucune ouverture de périmètre.** `PRODUCT_SCOPE` est inchangé ; aucun nouveau `reason_code` sans mise à jour de `taxonomy.py` / `cause_mapping.py` et de leurs tests.
10. **[Q3 C]** *(si retenu à la place des AC 7-9)* La cause « état seul » est affichée honnêtement ; aucune publication n'est ajoutée ; la parité d'inventaire MQTT est strictement identique avant/après.
11. **[Q4 A] Libellés.** L'écran et le diagnostic du démon cessent d'inviter à « préciser les types génériques » pour la cause d'état seul ; le message du forçage grisé reste exact vis-à-vis du nouveau comportement (plus de « Projection invalide » pour un état déjà publié).
12. **Parité des états en direct.** La valeur courante de la commande est publiée à l'état initial et suit les changements (story 19-5, `publish_click_states`, écouteurs d'état de 19-2) ; le nombre d'écouteurs attendu est consigné avant/après (équipement 579 : le nombre peut changer, à documenter).

### Transverses

13. **Preuve terrain (humaine).** Gate d'inventaire avant/après (entités HA, topics retenus, écouteurs, 0 erreur), sur le SHA exact déployé (worktree neuf) : (a) un scénario désactivé n'a plus de bouton après rescan, un scénario réactivé le retrouve ; (b) la commande 5369 apparaît dans HA sous le type décidé avec la bonne valeur (ou, en Q3 C, l'écran est conforme). Artefact `21-1-preuve-terrain-<date>.md`, sans nom réel (contrôle par empreintes, CC-48).
14. **Documentation.** `docs/fr_FR/changelog_beta.md` : entrée datée. `docs/fr_FR/index.md` : une phrase sur le moment où le bouton d'un scénario disparaît (au prochain rescan ou redémarrage du démon) et, si Q3 A, la ligne « état seul → capteur binaire ». Le bloc `compteurs` n'est pas touché (CC-51).
15. **Périmètre et gouvernance.** PR de développement vers `main`, titre en Conventional Commits, une PR par bloc (Q1 A) ; aucune modification des fichiers de preuve de 20-x.

## UI Impact

- **UI Impact:** Oui si Q4 A ou si le libellé / l'état du forçage de 5369 change visiblement (bloc B) ; **Non** pour le bloc A (démon seul, aucun écran du plugin ne montre les scénarios). Si Oui : gate 20-0 vert avant déploiement (aucune écriture transmise pendant le gate), puis `ready-for-UX-validation` avant `done`.

## Tasks / Subtasks

- [ ] **Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)**
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`
  - *(Task réservée à l'humain / à une session locale avec accès box ; une session cloud ne l'exécute jamais.)*
- [ ] **Task 1 — Prérequis et relevés (lecture seule) (AC: tous)**
  - [ ] 1.1 Alexandre a répondu à Q0, Q1, Q2, Q2b, Q3, Q4 ; les réponses sont consignées au Journal des décisions et les AC [Qx] figés ; `ready-for-dev` accordé.
  - [ ] 1.2 Rejouer C1 à C15 sur le `main` du moment ; consigner tout écart. Confirmer **par un test de caractérisation** (sans modifier le code de production) que la commande d'état orphelin est aujourd'hui ni switch publiable ni binary_sensor, et quel chemin du registre (`mapping/registry.py:100-127`) la voit.
  - [ ] 1.3 Mesurer à partir de la topologie de test (fixtures `story_19_4_guard`, golden) combien de commandes `ENERGY_STATE` orphelines existent : le changement de type par défaut (Q3 A) concerne-t-il d'autres équipements que le 579 ?
- [ ] **Task 2 — Bloc A : CC-44 (AC: 1-6)**
  - [ ] 2.1 Test d'abord (rouge) : scénario inactif ⇒ `unpublish` appelé ; actif ⇒ publié ; réactivation.
  - [ ] 2.2 Dépublier les scénarios inactifs dans la boucle `http_server.py:2081-2083` (ne plus se contenter du `continue`) en réutilisant `DiscoveryPublisher.unpublish` (`publisher.py:277-296`).
  - [ ] 2.3 Remplacer la purge purement mémoire `http_server.py:2100-2105` par une purge qui dépublie aussi les scénarios disparus (**Q2b**) : registre persisté des scénarios publiés (Q2b A) ou limite documentée (Q2b B).
  - [ ] 2.4 Report si broker déconnecté, **sans** passer par `pending_discovery_unpublish` indexé par `eq_id` (C5) ; rejeu à la reconnexion.
  - [ ] 2.5 Tests de non-régression : appui sur un bouton actif / inactif (`sync/command.py:562-574`), golden, contrat 4D ; `make test`, `flake8`.
- [ ] **Task 3 — Bloc B : CC-47 (AC: 7-12)** *(après Q3 et Q4)*
  - [ ] 3.1 Tests d'abord (rouge) : cas nominal, cas d'échec `validate_projection`, non-régression trio / prise mesureuse / doublon (AC 8).
  - [ ] 3.2 Implémenter le traitement décidé en Q3 (A : état orphelin → `binary_sensor` `sure` dans le chemin de mapping adéquat ; C : cause honnête sans nouvelle publication).
  - [ ] 3.3 Aligner `taxonomy.py`, `cause_mapping.py` (`:159`, `:169`) et `jeedom2ha_mapping_override.js` (`:209`, `:588-591`, `:639`) selon Q4.
  - [ ] 3.4 Réaligner le golden / les fixtures et le décompte des écouteurs (AC 12) ; `make test`, `flake8`.
- [ ] **Task 4 — Gate 20-0 et preuve terrain (humain) (AC: 13)**
  - [ ] 4.1 Si l'interface change : gate 20-0 vert, contrôle négatif attendu, sans écriture transmise.
  - [ ] 4.2 Déploiement standard du SHA exact (Task 0), inventaire avant/après, scénarios 72 et 2 (ou équivalents) et commande 5369 ; artefact de preuve sans nom réel.
- [ ] **Task 5 — Documentation et clôture (AC: 14, 15)**
  - [ ] 5.1 Changelogs, index utilisateur, `sprint-status.yaml`, rétrospective courte de l'epic 21 si celui-ci est ouvert (Q0 A).

## Dev Notes

- **Contexte d'exécution.** Une session cloud n'a pas accès à la box, à HA ni à un secret ; la preuve terrain est faite par l'humain. Respecter `docs/delegation-claude-cloud.md` et `_bmad-output/project-context.md` (règles d'implémentation Python/PHP/JS, anti-patterns : lecture obligatoire avant de coder).
- **Boucle de sync.** Éviter toute lecture de `request.app["scenario_publications"]` hors de la boucle ; c'est l'état des boutons *actifs* seulement, il sert à `sync/command.py:569` pour accepter ou rejeter un appui.
- **Ordre canonique de décision (I4).** Ne pas contourner `decide_publication` pour 5369 : si l'état seul devient un `binary_sensor` `sure`, il passe par la décision normale (aucune exception ad hoc au niveau 1) ; `force_publish` ne contourne jamais `PRODUCT_SCOPE`.
- **Invariants.** I11 (découplage état/commandes, 19-2), I3 amendé (ambiguous forcé par l'utilisateur, 20-2), invariants de non-doublon entre `SwitchMapper`, `SensorMapper`, `BinarySensorMapper` (stories 11.2, 14.1).
- **Noms réels.** Aucun nom d'équipement, de pièce ou de scénario réel dans les fichiers du dépôt (CC-48) : identifiants numériques seulement.
- **Testing standards.** Tests unitaires sous `resources/daemon/tests/unit/` (modèles : `test_story_10_1_button_homekit_scenarios.py`, `test_story_19_2_decouplage_state_command_i11.py`) ; golden corpus `resources/daemon/tests/fixtures/golden_corpus/` ; JS : tests Node du dépôt si le libellé change.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

#### Guardrails de périmètre

- Aucune ouverture de `PRODUCT_SCOPE`, aucun nouveau FR/NFR.
- Un scénario n'est pas un équipement : ne pas mélanger leurs clés (`eq_id`) dans les structures de report (C5).
- Ne rien supprimer des topics autres que `…/button/jeedom2ha_scenario_<id>/config` dans le bloc A.

### Project Structure Notes

- Fichiers vraisemblablement touchés : `resources/daemon/transport/http_server.py`, `resources/daemon/discovery/publisher.py` (réutilisation), un nouveau petit module/cache persisté pour les scénarios publiés (Q2b A), `resources/daemon/mapping/switch.py` et/ou `binary_sensor.py` / `registry.py` (bloc B), `models/cause_mapping.py`, `models/taxonomy.py`, `desktop/js/jeedom2ha_mapping_override.js`, tests et golden, `docs/fr_FR/*`.
- Écart connu de nommage : `pe-epic-21` suit la convention `pe-epic-N` du cycle « Moteur de projection explicable » ; le titre de l'epic reste à confirmer (Q0).

### References

- `_bmad-output/implementation-artifacts/pe-epic-20-retro-2026-10-11.md` (risques résiduels, ordre décidé le 2026-10-11 à 15:48).
- `_bmad-output/implementation-artifacts/20-4-rescan-page-principale-cc04-ui.md` (journal, décision du 06/10) et `20-4-preuve-validation-ux-2026-10-06.md` (constat CC-44).
- `_bmad-output/implementation-artifacts/20-2-exclusion-forcage-depuis-surface-cc26.md` (faits F1 à F12, décisions Q1 à Q3 de cette story-là) et `20-2-preuve-complement-2026-10-06.md` (verdict, réserve CC-47).
- `_bmad-output/planning-artifacts/epics-projection-engine.md` (Epic 20, gates ; Epic 21 proposé), `pipeline-contract.md` (I3, I4, I8, I11), `sprint-status.yaml`.
- Code : voir « Faits relevés ».

## Journal des décisions

- 2026-10-06 — Alexandre : 20-4 close avec réserve CC-44 ; 20-2 close avec réserve CC-47 (5369 en mode automatique, forçage de l'eq 463 gardé) ; stories dédiées.
- 2026-10-11, 15:48 — Alexandre : ordre de la suite = CC-44 + CC-47, puis CC-36 avec CC-51 et « compteurs », puis parité HomeKit (CC-33).
- 2026-10-11 — `create-story` de 21.1 (session cloud déléguée, lecture seule, aucun accès box/HA/secret) : pointeurs relocalisés dans le code à `15576cf` (scénarios `http_server.py:2078-2105`, au lieu de 2080-2105 ; messages `jeedom2ha_mapping_override.js:159` et `:209`), questions Q0 à Q4 posées avec recommandation. **`ready-for-dev` non accordé** ; aucune question n'est tranchée par ce document.

## Dev Agent Record

### Agent Model Used

Agent Claude Code, session cloud déléguée (sans accès box Jeedom, Home Assistant, secrets ni déploiement). Phase `create-story` seulement : aucun code.

### Debug Log References

- Lecture seule du code de `main` `15576cf` ; aucune exécution de test, aucun changement de code.

### Completion Notes List

- Story créée, statut `backlog` (`ready-for-dev` non accordé : Q0 à Q4 à trancher par Alexandre).
- Tâche 0 « Pre-flight terrain » injectée (story terrain : démon, MQTT, discovery HA) ; elle est réservée à l'humain.
- Aucun nom d'équipement, de pièce ou de scénario réel dans cette story.

### File List

- `_bmad-output/implementation-artifacts/21-1-solde-reserves-cc44-scenario-desactive-cc47-etat-sans-ordre-on-off.md` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (inscription provisoire)
- `_bmad-output/planning-artifacts/epics-projection-engine.md` (Epic 21 proposé)
