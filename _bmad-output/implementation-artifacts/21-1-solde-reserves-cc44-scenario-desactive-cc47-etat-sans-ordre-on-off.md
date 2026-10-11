# Story 21.1 : Solde des réserves de l'étape 4 — scénario désactivé (CC-44) et affichage d'un état sans ordre On/Off (CC-47)

Status: ready-for-dev

> **Statut : `ready-for-dev`** (2026-10-11). Alexandre a tranché les questions Q0 à Q4 le 2026-10-11 vers 20:35, relayé par ClaudeBox : **Q0 A, Q1 A, Q2 A, Q2b C, Q3 C, Q4 A** — toutes les recommandations sont retenues (voir « Décisions d'Alexandre » et le Journal des décisions). `ready-for-dev` est accordé par ClaudeBox au nom de cette décision. Créée par une session cloud déléguée (lecture seule), relue trois fois par ClaudeBox (R1, R2, puis consignation des décisions). Numérotation retenue : `pe-epic-21` / story `21-1`.
>
> **Nature du bloc B (R2).** Un relevé de terrain du 2026-10-11 montre que **la commande 5369 est déjà publiée dans Home Assistant**. CC-47 n'est donc **pas un défaut de publication** mais un **défaut d'affichage et de décompte** : l'écran dit « Ne sera pas publié » et compte 5369 « bloquante » alors qu'une entité la publie. Le bloc B corrige cet affichage ; il ne change **aucune publication**.

## Story

En tant qu'utilisateur du plugin qui pilote sa maison depuis Home Assistant,
je veux qu'un scénario Jeedom désactivé ne laisse pas un bouton fantôme dans Home Assistant, et que l'écran du plugin dise vrai sur une commande d'état déjà publiée (au lieu de l'annoncer « non publiée » et de la compter bloquante),
afin que Home Assistant et l'écran reflètent fidèlement ce que Jeedom permet et ce qui est réellement publié.

**Parcours : démon + interface.** Le bloc A (CC-44) est purement démon (sync, discovery MQTT) : aucun écran du plugin ne montre les scénarios. Le bloc B (CC-47) touche la résolution des décisions par commande dans le démon (arbre `mapping_overrides`) et l'écran (`desktop/js/jeedom2ha_mapping_override.js`) : il passe par le gate 20-0 et `ready-for-UX-validation` avant `done`. Preuve terrain obligatoire : gate d'inventaire avant/après, 0 erreur ; pour le bloc B, **inventaire MQTT et registre HA strictement identiques** (aucune publication ne change).

## Contexte et périmètre

- **Origine.** Rétrospective `pe-epic-20-retro-2026-10-11.md` (« Risques résiduels » : réserve 20-2 / commande 5369, réserve 20-4 AC6). Ordre décidé par Alexandre le 2026-10-11 à 15:48 : 20-5 (fait) → **CC-44 + CC-47** → CC-36 avec CC-51 et la story « compteurs » → epic parité HomeKit (CC-33).
- **CC-44 (réserve AC6 de 20-4).** Un scénario Jeedom désactivé garde son bouton dans HA. Constat de terrain du 2026-10-06 (`20-4-preuve-validation-ux-2026-10-06.md`, « Constats non bloquants ») : scénarios 72 et 2 désactivés (`isActive=0`), retirés de `scenario_publications` en mémoire au rescan, mais leurs topics retenus `homeassistant/button/jeedom2ha_scenario_72/config` et `…_2/config` restent sur le broker. Défaut présent depuis la story 10.1 (PR #119), antérieur à l'epic 20. Mesure du 11/10 : 7 fantômes dans HA (voir Q2b).
- **CC-47 (réserve de 20-2) — recadré par le relevé du 2026-10-11 (ClaudeBox, lecture seule : `GET /system/mapping_overrides/579` via la page du plugin, registre des entités de HA, écran du plugin ; non rejoué par cette session).**
  - L'état 5369 **est déjà publié dans HA** : `binary_sensor`, `unique_id` `jeedom2ha_eq_579_cmd_5369`, présent dans le registre de HA **depuis le 21/06/2026**, avec un état valide (on/off). Le démon déclare 6 entités pour l'équipement 579 ; l'entité `binary_sensor` [5369] est `sure`, `should_publish=true` ; le principal `switch` [5369] est `ambiguous` / `switch_state_orphan`, refusé ; `sync_status.published_in_ha=true`.
  - L'écran affiche pourtant, sur la ligne de 5369 : « Ne sera pas publié — état sans ordre On/Off ». La ligne d'une commande ne reflète que l'**entité principale**. Parmi les 7 équipements `ambiguous_skipped` du parc, 5369 est la **seule** commande dans ce cas (portée par un principal refusé **et** par un secondaire publié).
  - **Conséquence : CC-47 est un défaut d'affichage et de décompte** (5369 est comptée « bloquante », la synthèse de l'équipement est fausse), pas un défaut de publication.
  - **Erratum.** Le constat du 2026-10-06 (`20-2-preuve-complement-2026-10-06.md`, « Verdict » : « la commande 5369 n'est pas débloquée … aucun type valide … son forçage est grisé ») **n'avait pas vu l'entité `binary_sensor`** qui la publiait déjà. Ses observations sur l'écran restent exactes (forçage grisé, ligne « bloquante ») ; sa conclusion « ne peut pas être publiée » ne l'est pas. Le fichier de preuve n'est **pas modifié** ; cet erratum le corrige ici. De même, la décision d'Alexandre du 2026-10-06 (« 5369 reste en mode automatique ») reste exacte : elle est en mode automatique **et** publiée.
- **Dans le périmètre :**
  - bloc A : retrait (ou autre traitement décidé en Q2) du bouton HA d'un scénario désactivé, y compris les fantômes déjà présents (Q2b) ; correction de la disponibilité des boutons de scénario (pont seul, C8) ;
  - bloc B : la ligne d'une commande, la synthèse de l'équipement et les compteurs qui en dérivent tiennent compte de **toutes les entités qui portent la commande** ; libellé honnête de la cause « état sans ordre On/Off » pour un équipement à une seule entité (Q4) ;
  - tests unitaires (démon), tests Node (écran), mise à jour du golden si besoin, preuve terrain par l'humain.
- **Frontière avec la story des compteurs (CC-36 / CC-51).**
  - *Revient à cette story :* faire que la **donnée de base** soit juste — la décision par commande et la ligne affichée (« Sera publié : binary_sensor »), et, par construction, ce qui en est dérivé tel qu'il existe aujourd'hui : la synthèse de l'équipement (« prêtes / bloquantes ») et les totaux de pièce calculés à partir des lignes (`jeedom2ha_mapping_override.js:790-826` et `:925-940`).
  - *Revient à CC-51 :* **redéfinir la sémantique** des compteurs (« publiés » = présents dans HA, « en attente d'application », « non pris en charge »), leur libellé et leur source (présence réelle dans HA), ainsi que le bloc `compteurs` de la documentation. Cette story ne touche ni cette sémantique, ni ce bloc.
- **Hors périmètre :**
  - toute **modification du mapper** pour publier un état seul (voir Q3 : rien dans cette story) ; toute ouverture de `PRODUCT_SCOPE` (`sensor` et `binary_sensor` y sont déjà, `resources/daemon/validation/ha_component_registry.py:70`) ;
  - CC-36, CC-51 et la story « compteurs » ; CC-33 ; CC-45, CC-46 (autres reports de 20-2) ;
  - le forçage des 16 autres commandes ambiguës (déjà livré par 20-2, sur demande d'Alexandre équipement par équipement) ;
  - tout accès à la box, à HA, à un secret ; `scripts/deploy-to-box.sh` n'est **jamais** lancé par cette session (la preuve terrain est faite par l'humain).

## Décisions d'Alexandre (2026-10-11, vers 20:35, relayées par ClaudeBox)

Réponse : **Q0 A, Q1 A, Q2 A, Q2b C, Q3 C, Q4 A.** Les variantes non retenues sont retirées de ce document ; elles restent lisibles dans l'historique de la PR #234 (commits `704f1c9`, `91ebf4a`, `b8be826`). Les faits utiles au dev sont conservés ci-dessous.

### Q0 — A : nouvel `pe-epic-21`, story `21-1`

L'epic 20 est `done` et ne se rouvre pas (le workflow `create-story` refuse une story dans un epic `done`). `pe-epic-21` « Solde des réserves de l'étape 4 » est ouvert, `in-progress`, cadrage documentaire comme pe-epic-19 (pas de SCP, aucune ouverture `PRODUCT_SCOPE`, aucun nouveau FR/NFR). Les epics suivants (compteurs, parité HomeKit) prennent 22 et 23. Inscrit dans `sprint-status.yaml` et `epics-projection-engine.md`.

### Q1 — A : une story, deux blocs indépendants, deux PR de développement

Bloc A (CC-44) et bloc B (CC-47) sont livrables séparément (une branche / une PR = un seul sujet). La story ne passe `done` que lorsque les deux sont prouvés.

### Q2 — A : retirer le bouton HA d'un scénario désactivé

Un bouton fantôme est déjà **inerte** : un appui est rejeté par le démon (`unknown_runtime_entity`, `resources/daemon/sync/command.py:569-574`). Le publisher sait déjà retirer un scénario (`resources/daemon/discovery/publisher.py:277-296`, payload vide retenu) mais aucun appelant ne l'utilise. Cohérent avec les équipements désactivés (dépubliés, raison `disabled_eqlogic`). Aucun écran du plugin ne liste les scénarios.

- *Dans HA :* le bouton **disparaît** au prochain rescan ou redémarrage du démon (il n'y a pas de sync périodique, F7 de 20-2) ; les automatisations, scripts et tableaux de bord qui le citent ne fonctionnent plus tant que le scénario est désactivé. À la réactivation, l'entité revient avec le même `unique_id`.
- *Dans l'écran du plugin :* rien.

**Encadré — réglages de l'entité après retrait puis republication (formulation prudente).** Vider la configuration de discovery supprime l'entité de HA. Les réglages faits dans HA (nom, identifiant d'entité, pièce, icône, étiquettes) **ne sont pas forcément perdus** : ClaudeBox a relevé le 2026-10-11, en lecture seule, dans le registre des entités de la box HA (`core.entity_registry`, version 1.23), que les entités supprimées y sont **conservées dans `deleted_entities`** (335 aujourd'hui), avec `entity_id`, `name`, `area_id`, `icon`, `labels`, `aliases` et `options`. Un bouton retiré puis republié avec le même `unique_id` **devrait** donc retrouver ses réglages. Ce n'est **ni garanti ni vérifié** (relevé non rejoué par cette session, et la documentation de HA n'est pas accessible d'ici) : la preuve de terrain le vérifiera (AC 13).

### Q2b — C : le broker fait foi

**Mesure du 2026-10-11 (ClaudeBox, lecture seule, non rejouée par cette session) :** le registre des entités de HA compte **92 boutons de scénario**, dont 72 et 2. Le démon en publie **85** actifs (journal du démon depuis son redémarrage du 11/10 à 16:20). HA en garde donc **7 de plus, qui ne sont plus publiés : 2, 32, 33, 39, 40, 72, 129**. 72 et 2 sont inactifs (constat de 20-4) ; pour les 5 autres, inactifs ou supprimés, **à établir en Task 1.4**. Aucun scénario publié ne manque dans HA.

À chaque sync, le démon lit les topics retenus `<préfixe>/button/jeedom2ha_scenario_+/config` et vide ceux dont l'identifiant n'est pas celui d'un scénario **actif** du snapshot. Cela couvre les scénarios inactifs, les scénarios supprimés **et les 7 fantômes déjà présents**, sans fichier persisté ni amorçage manuel. Risques à encadrer (exigés par les AC) :
- *fenêtre de collecte* : les messages retenus arrivent après l'abonnement, sans signal de fin ; fenêtre bornée. Une collecte trop courte ne fait que **retarder** le nettoyage d'un fantôme au sync suivant ; elle ne doit jamais provoquer de suppression à tort (on ne vide que ce qu'on a lu) ;
- *périmètre strict* : ne toucher **aucun** topic hors du motif `<préfixe>/button/jeedom2ha_scenario_<entier>/config` ;
- *snapshot incomplet* : si la section `scenarios` manque ou si le scan a échoué, le défaut actuel est une liste vide (`models/topology.py:193-200`) ; cela viderait **tous** les boutons. Garde-fou obligatoire : ne purger que si la section `scenarios` est présente dans la charge utile du scan, et journaliser le nombre de topics vidés ;
- *broker déconnecté* : pas de purge, reprise au sync suivant (rien à reporter).

### Q3 — C : pas de changement de mapper dans cette story

Pour 5369, le type HA est **déjà réglé dans les faits** : l'état est publié en `binary_sensor` par le chemin multi-entité (équipement 579 : 6 entités). Ne reste que le cas d'un **équipement à une seule entité dont la seule commande est un état sans ordre On/Off** : aucun mapper ne le reprend (`mapping/registry.py:100-127`), il reste « ambigu » (`switch_state_orphan`, `mapping/switch.py:198-207`) et n'est pas publié.

**Mesure du 2026-10-11 (ClaudeBox, journal du démon, non rejouée par cette session) :** le parc actif n'a **aucun** tel équipement ; l'équipement **559**, seul autre état seul du parc, est **exclu par le plugin**. Le cas reste donc théorique aujourd'hui.

- *Dans HA :* rien ne change pour le parc actuel.
- *Dans l'écran du plugin :* seule la cause « état sans ordre On/Off » est reformulée (Q4).
- *Au cas par cas :* l'utilisateur peut déjà choisir le type `binary_sensor` pour la commande puis « Forcer » (chemin « D »). **Vérifié par un test de caractérisation de la session** (jetable, non commité, équipement synthétique sans nom réel) : forçage seul (type `switch`) refusé, `ha_missing_command_topic`, niveau 3 ; type `binary_sensor` seul refusé, `ambiguous_skipped`, niveau 2 ; type `binary_sensor` **puis** forçage : **publié** (`publication_forced`), `unique_id` `jeedom2ha_eq_<id>`, payload de discovery **complet** (`state_topic`, `unique_id`, `object_id`, appareil, disponibilité). Ce chemin est couvert par un test de non-régression (AC 10). Une publication automatique de tout état seul par le mapper est **hors de cette story** (backlog).

### Q4 — A : corriger le libellé de la cause « état sans ordre On/Off » (équipement à une seule entité)

La ligne de 5369 ne doit plus dire « Ne sera pas publié » : c'est réglé par le bloc B. Reste le cas d'un équipement à une seule entité dont l'état est seul, où « Ne sera pas publié — état sans ordre On/Off » est vrai mais incomplet, et où l'écran dit aussi « précisez les types génériques dans Jeedom » (`jeedom2ha_mapping_override.js:588`) alors qu'aucun type générique ne manque (F10 de 20-2) ; le démon renvoie la même invitation (`resources/daemon/models/cause_mapping.py:159` et `:169`). Le libellé dit l'essentiel : état seul, rien à piloter ; type `binary_sensor` puis « Forcer » possibles (action réelle de l'écran, donc compatible avec la règle « pas de faux CTA »). Le reste de F10 (autres causes d'ambiguïté) reste au backlog.

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
- **C8** — Disponibilité et appareil d'un bouton de scénario calculés depuis un `eqLogic` de **même identifiant** : `resources/daemon/discovery/publisher.py:383-386` (`_build_availability_fields` → `availability_from_snapshot(mapping.jeedom_eq_id, snapshot)`) puis `resources/daemon/models/availability.py:58-65` (`eq_logics.get(eq_id)`) et `:33-55` (`availability_from_eqlogic`) ; pour un scénario, `jeedom_eq_id` est l'id du **scénario** (`mapping/button.py:44-64`). Si un équipement a le même identifiant, le bouton suit sa disponibilité locale (topic `jeedom2ha/<id>/availability`). Même mécanisme pour l'appareil : `publisher.py:359-361` et `:372-376` (fabricant et modèle repris de `eq_type_name` de l'équipement homonyme). **Mesure du 2026-10-11 (ClaudeBox, non rejouée ici) : au moins 3 scénarios partagent leur id avec un équipement publié (109, 110, 113).** Corrigé **dans le bloc A** (AC 6 bis), plus renvoyé hors périmètre.
- **C9** — Aucune interface du plugin ne liste les scénarios (aucune occurrence dans `desktop/`), ni la documentation `docs/fr_FR/index.md` : le seul témoin utilisateur est le bouton dans HA.

**CC-47 — état sans ordre On/Off : un défaut d'affichage et de décompte**

- **C10** — *Relevé de terrain du 2026-10-11 (ClaudeBox, lecture seule, non rejoué par cette session)* : 5369 est déjà publiée en `binary_sensor` (`jeedom2ha_eq_579_cmd_5369`, registre HA depuis le 2026-06-21, état on/off valide) ; l'équipement 579 déclare 6 entités ; `binary_sensor` [5369] `sure` / `should_publish=true` ; principal `switch` [5369] `ambiguous` / `switch_state_orphan` refusé ; `sync_status.published_in_ha=true` ; l'écran affiche « Ne sera pas publié — état sans ordre On/Off » sur la ligne de 5369 ; 5369 est la seule commande de ce cas parmi les 7 équipements `ambiguous_skipped`.
- **C11** — Cause racine côté démon : `resources/daemon/models/evaluate_equipment.py:447-453` (`covered.setdefault` : le **primaire d'abord**, puis les secondaires) fait que la `CommandDecision` d'une commande portée par plusieurs entités est celle du **principal**, même refusé. `resources/daemon/transport/http_server.py:2592-2616` (`_resolve_command_mapping`, docstring : « le primaire gagne toujours ») applique la même priorité à l'arbre et à l'aperçu. L'arbre `GET /system/mapping_overrides/<eq_id>` : `http_server.py:2999` (`command_decision_by_cmd`), `:3007-3025` (`diag_mapping`, `attendu_ha`, `effective_ha`, `diagnostic` par commande) ; il expose déjà les entités `entities[]` (`:3064-3092`, avec `command_ids` et `decision` par entité) et `sync_status.published_in_ha` (`:3094-3099`).
- **C12** — Consommateurs de `command_decisions` hors tests : uniquement l'arbre et l'aperçu (`http_server.py:2690`, `:2999`) ; le sync publie à partir de `equipment_decision` et `secondary_decisions` (`evaluate_equipment.py:482`). Changer la résolution par commande n'agit donc **que sur la surface**, jamais sur ce qui est publié.
- **C13** — Côté écran, tout est dérivé de la ligne de commande (`row.diagnostic`) : `diagnosticState` (`desktop/js/jeedom2ha_mapping_override.js:514-520`), `buildBlockingReason` (`:633-657`), `buildPublishCellLabel` (`:660-672`, « Sera publié : <type> » / « Ne sera pas publié — <raison> »), libellés de cause (`REASON_LABELS`, `:588-591`, `switch_state_orphan` → « état sans ordre On/Off »), décompte prêtes/bloquantes de l'équipement (`:790-826`) et libellé de synthèse (`:837-857`), totaux de pièce (`:925-940`). Une ligne fausse rend donc fausse la synthèse (preuve historique : « Partiellement publié : 4 prête(s), 1 bloquante(s). » pour l'équipement 579, `16-8-cc37-preuve-2026-10-04.md:43`).
- **C14** — Pourquoi l'orphelin est publié sur 579 : l'équipement a plusieurs entités, donc le registre prend le chemin multi-entité (`mapping/registry.py:100-127` : retourne les résultats si plusieurs primaires, plusieurs secondaires ou un capteur power/energy) ; `BinarySensorMapper._map_multi_domain` (`mapping/binary_sensor.py:~105-137`, après `_is_multi_domain_eq` `:69-87`) crée un `binary_sensor` par commande binaire non consommée par un trio switch (`_switch_readback_cmd_ids`, `:112`) — un `ENERGY_STATE` sans ON/OFF n'est pas consommé. **Sans ce chemin** (équipement à une seule entité), rien ne reprend l'état seul : `SwitchMapper` le classe `ambiguous` (`mapping/switch.py:198-207`, résultat `:214-235`), `decide_publication` le refuse au niveau 1 sauf forçage (`models/decide_publication.py:106-109`), `validate_projection('switch', …)` exige `has_command` (`validation/ha_component_registry.py:155-160`), d'où « Projection invalide pour ce type HA. » (`jeedom2ha_mapping_override.js:209`) et « Aucune commande clé propre à cette entité. » (`:159`).
- **C15** — Un override de type ne relance pas le mapper et laisse les capacités inchangées : `resources/daemon/mapping/overrides.py:376-396` (docstring, D10/D11) et `:413-432` (application) ; la clé `eq:cmd` est **partagée par toutes les entités qui portent la commande** : **un type posé sur une commande portée par deux entités s'applique à la première entité qui la porte dans l'ordre des mappings** (F5/F6 de 20-2, `models/evaluate_equipment.py:166-179`). À garder en tête pour la ligne de 5369 : son sélecteur de type ne doit pas être présenté comme réglant l'entité qui publie, sans vérification en Task 1.
- **C16** — Cas à une seule entité, état seul : voir Q3 (aucun équipement actif concerné ; 559 exclu ; option D viable, vérifiée).
- **C17** — Données de terrain connues (identifiants seulement, **aucun nom réel**) : équipement 579, commandes 5368 (non couverte), **5369 (état, déjà publié)**, 5493, 5494, 5689, 5695 (prêtes) ; `19-1-field-proof-2026-09-28.md`, `20-1-preuve-validation-ux-2026-10-05.md`. La bascule simulée de 5369 par le gate 20-0 (« Sera publié dans Home Assistant : 5 commande(s) prête(s). ») donne l'affichage attendu *après* correction.

## Acceptance Criteria

> Figés le 2026-10-11 sur les décisions d'Alexandre (Q0 A, Q1 A, Q2 A, Q2b C, Q3 C, Q4 A).

### Bloc A — CC-44

1. **[Q2 A] Un scénario inactif n'a plus de bouton dans HA.** À l'issue d'un sync, tout scénario du snapshot avec `is_active=false` voit son topic de discovery vidé (payload vide retenu, `qos=1`) ; le bouton disparaît de HA. Test unitaire : snapshot avec un scénario actif et un inactif, publisher simulé ; seul l'actif est publié, l'inactif reçoit un `unpublish`.
2. **[Q2 A] Réactivation.** Un scénario réactivé est republié au sync suivant, avec son bouton, sans autre action ; son `unique_id` et son `command_topic` sont inchangés.
3. **[Q2b C] Le broker fait foi : fantômes déjà présents, suppressions, redémarrages.** À chaque sync où la section `scenarios` est présente dans la charge utile du scan, le démon lit les topics retenus du motif `<préfixe>/button/jeedom2ha_scenario_<entier>/config` (fenêtre de collecte bornée) et vide ceux dont l'identifiant n'est pas celui d'un scénario **actif** du snapshot. Les 7 fantômes mesurés le 11/10 (2, 32, 33, 39, 40, 72, 129) sont retirés au premier sync après la livraison, sans fichier persisté ni amorçage. Tests : (a) un topic de scénario inactif ou inconnu est vidé, un actif ne l'est pas ; (b) **aucun topic hors motif n'est touché** (boutons d'équipement, autres préfixes, `…/config` d'autres types) ; (c) section `scenarios` absente ou scan en échec : **aucune purge** ; (d) fenêtre de collecte vide ou interrompue : aucune suppression à tort.
4. **[Q2b C] Broker déconnecté.** Pas de purge tant que le broker est injoignable ; reprise au sync suivant, rien à reporter. Ne pas passer par `pending_discovery_unpublish`, indexé par `eq_id` (C5) : un scénario d'id N et un équipement d'id N ne se gênent pas (test).
5. **Pas de régression.** Les scénarios actifs, le bouton d'un équipement, `scenario_publications` (appui sur le bouton d'un actif accepté, d'un inactif rejeté) et le golden corpus sont inchangés, ou le golden est réaligné avec justification si le corpus contient des scénarios inactifs. La suite complète (`make test`) et `flake8` sont verts.
6. **Journal.** Chaque retrait est tracé (`[SCENARIO] Unpublished …`) avec le nombre de topics vidés par sync, sans nom réel de scénario ni secret.
6 bis. **Disponibilité et appareil du bouton de scénario : pont seul (C8).** Le bouton d'un scénario n'hérite plus de la disponibilité locale ni du fabricant/modèle d'un équipement de même identifiant : sa disponibilité est celle du **pont seul** (`availability_topic` du pont, aucune entrée `availability` locale), son appareil porte des valeurs neutres. Test : un scénario et un équipement d'id N, ce dernier avec disponibilité locale supportée et hors ligne ; la charge utile du bouton ne contient ni `jeedom2ha/N/availability` ni le type de l'équipement. Un scénario sans équipement homonyme garde une charge utile **identique** à l'actuelle (golden inchangé hors cas de collision). Effet à connaître : les boutons concernés (au moins 109, 110 et 113) voient leur configuration retenue changer au prochain sync (même `unique_id`).

### Bloc B — CC-47 (affichage et décompte d'une commande portée par plusieurs entités)

7. **Résolution par commande : une entité publiée qui porte la commande l'emporte sur un principal refusé.** Si au moins une entité qui porte une commande est publiée (`should_publish=true`, projection valide), la décision de **cette commande** est « publiée », avec le type HA de l'entité qui la publie ; le principal refusé ne la rend pas bloquante. Si aucune entité qui la porte n'est publiée : comportement actuel inchangé (la cause du principal est affichée). Si plusieurs sont publiées : le principal garde la priorité (type affiché inchangé). Une commande non couverte reste « non couverte ». Tests démon sur la **forme de 579** (principal `switch` `ambiguous` / `switch_state_orphan` refusé + secondaire `binary_sensor` `sure` publié, sur la même commande), plus les cas voisins ci-dessus. La résolution reste produite par le démon (source unique `evaluate_equipment()` ; aucune recomposition de décision côté écran, gate epic-level 20) ; mécanisme au choix du dev (priorité des entités publiées dans `evaluate_equipment.py:447-453` et `http_server.py:2592-2616`, ou champ additif sur la décision de commande), dans tous les cas cohérent entre l'arbre, `attendu_ha` / `effective_ha` et l'aperçu.
8. **Ligne, synthèse et totaux de pièce.** Sur la forme de 579, la ligne de 5369 affiche **« Sera publié : binary_sensor »** (jamais « Ne sera pas publié ») ; 5369 n'est plus comptée « bloquante » ; la synthèse de l'équipement et les totaux de pièce, **tels qu'ils sont calculés aujourd'hui à partir des lignes**, la comptent « prête » (pour 579 : 5 prêtes, 0 bloquante, 5368 toujours « non couverte »). L'entité principale refusée ne se présente pas comme un blocage de la commande (comment la surface la rend, à établir en Task 1.5). **Tests Node** (`tests/unit/*.node.test.js`, modèle `test_story_19_3_p1_uncovered_diagnostic.node.test.js`) sur un arbre de la forme de 579 : principal refusé et secondaire publié sur la même commande ; ligne, synthèse, totaux de pièce, absence de « Ne sera pas publié » sur cette ligne.
9. **Aucune publication ne change.** Inventaire MQTT retenu et registre HA **strictement identiques** avant/après sur la box (diff vide) ; golden corpus et parité d'inventaire inchangés, ou réalignés avec justification pour les seuls arbres où un principal refusé et un secondaire publié partagent une commande (mesure en Task 1.3). `PRODUCT_SCOPE` inchangé, aucun nouveau `reason_code` sans mise à jour de `taxonomy.py` / `cause_mapping.py` et de leurs tests.
10. **[Q3 C] Aucun changement de mapper ; le chemin « type puis forçage » reste couvert.** Le test de caractérisation décrit en Q3 est commité comme test de non-régression : forçage seul refusé ; type seul refusé ; type puis forçage publié avec un payload `binary_sensor` complet. Pour un équipement à une seule entité dont l'état est seul, rien n'est publié de plus.
11. **[Q4 A] Libellé de la cause d'état seul (équipement à une seule entité).** L'écran et le diagnostic du démon disent honnêtement la cause (état seul, rien à piloter ; type `binary_sensor` puis « Forcer » possibles), sans l'invitation à « préciser les types génériques » pour cette cause (`jeedom2ha_mapping_override.js:588-591`, `:639` ; `cause_mapping.py:159`, `:169`). Test Node sur le libellé. Si l'équipement a aussi une entité publiée qui porte la commande, c'est la ligne « Sera publié : <type> » de l'AC 8 qui prévaut.
12. **Pas de régression de la surface.** Équipements à une seule entité, commandes non couvertes, exclus, désactivés, forcés : lignes, synthèses, badges inchangés ; gate 20-0 vert (parcours de référence, contrôle négatif attendu).

### Transverses

13. **Preuve terrain (humaine).** Gate d'inventaire avant/après (entités HA, topics retenus, écouteurs, 0 erreur), sur le SHA exact déployé (worktree neuf) : (a) bloc A : un scénario désactivé n'a plus de bouton après rescan, un scénario réactivé le retrouve, les 7 fantômes ont disparu, les boutons dont l'id est partagé avec un équipement ne suivent plus sa disponibilité ; **un bouton retiré puis republié avec le même `unique_id` (scénario de test, désactivation/réactivation faites par l'humain) retrouve ses réglages dans HA — nom, identifiant d'entité, pièce, icône — ou, sinon, l'écart est consigné tel quel** (voir l'encadré de Q2) ; (b) bloc B : la ligne de 5369 affiche « Sera publié : binary_sensor », la synthèse de 579 ne compte plus de bloquante ; **inventaire MQTT et registre HA identiques**. Artefact `21-1-preuve-terrain-<date>.md`, sans nom réel (contrôle par empreintes, CC-48).
14. **Documentation.** `docs/fr_FR/changelog_beta.md` : entrée datée. `docs/fr_FR/index.md` : une phrase sur le moment où le bouton d'un scénario disparaît (au prochain rescan ou redémarrage du démon), et, si l'écran change de façon visible, la ligne correspondante. Le bloc `compteurs` n'est pas touché (CC-51).
15. **Périmètre et gouvernance.** PR de développement vers `main`, titre en Conventional Commits, une PR par bloc (Q1 A) ; aucune modification des fichiers de preuve de 20-x (y compris `20-2-preuve-complement-2026-10-06.md`, corrigé par erratum dans cette story).

## UI Impact

- **UI Impact:** **Oui** pour le bloc B (ligne de commande, synthèse, totaux de pièce, libellé de cause) ; **Non** pour le bloc A (démon seul, aucun écran du plugin ne montre les scénarios). Gate 20-0 vert avant déploiement (aucune écriture transmise pendant le gate), puis `ready-for-UX-validation` avant `done`.

## Tasks / Subtasks

- [ ] **Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)**
  - [ ] Déploiement standard uniquement, fait par clawcode, du SHA exact (garde-fou CI) ; jamais `--cleanup-discovery` ni `--stop-daemon-cleanup`.
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --sha "$(git rev-parse HEAD)" --dry-run` (le script exige `--sha <HEAD>`, PR #235, garde-fou CC-56)
  - [ ] Vérifier que le script se termine avec `Deploy complete.`
  - *(Task réservée à l'humain / à clawcode avec accès box ; une session cloud ne l'exécute jamais. Le nettoyage des fantômes de scénarios est fait par le démon lui-même au sync (Q2b C), pas par un mode du script.)*
- [ ] **Task 1 — Prérequis et relevés (lecture seule) (AC: tous)**
  - [x] 1.1 *(fait le 2026-10-11, ~20:35)* Alexandre a répondu : Q0 A, Q1 A, Q2 A, Q2b C, Q3 C, Q4 A ; consigné au Journal des décisions, AC [Qx] figés, `ready-for-dev` accordé par ClaudeBox au nom de cette décision.
  - [ ] 1.2 Rejouer C1 à C17 sur le `main` du moment ; consigner tout écart. Rejouer en lecture seule le relevé du 11/10 sur 579 (arbre, `entities[]`, `sync_status`) pour confirmer que la forme réelle est « principal refusé + secondaire publié sur 5369 ».
  - [ ] 1.3 Mesurer, sur le corpus doré et les fixtures (`story_19_4_guard`, golden), **tous** les arbres où un principal refusé et un secondaire publié partagent une commande : ce sont les seuls dont la décision par commande change (AC 7, 9).
  - [ ] 1.4 Établir, en lecture seule sur la topologie et sur le registre HA, l'état des 7 fantômes de scénario (2, 32, 33, 39, 40, 72, 129) : inactif ou supprimé dans Jeedom ; et confirmer les identifiants partagés entre scénarios et équipements publiés (109, 110, 113 et tout autre).
  - [ ] 1.5 Établir comment la surface rend aujourd'hui l'**entité principale refusée** et le sélecteur de type d'une commande portée par deux entités (C15) sur la forme de 579, avant de fixer le libellé de l'AC 8.
- [ ] **Task 2 — Bloc A : CC-44 (AC: 1-6, 6 bis)**
  - [ ] 2.1 Test d'abord (rouge) : scénario inactif ⇒ `unpublish` appelé ; actif ⇒ publié ; réactivation.
  - [ ] 2.2 Dépublier les scénarios inactifs dans la boucle `http_server.py:2081-2083` (ne plus se contenter du `continue`) en réutilisant `DiscoveryPublisher.unpublish` (`publisher.py:277-296`).
  - [ ] 2.3 Remplacer la purge purement mémoire `http_server.py:2100-2105` selon **Q2b C** : lecture des topics retenus du motif strict et vidage de ceux qui ne sont pas actifs, avec garde-fous (section `scenarios` présente, fenêtre bornée, journal du nombre de topics vidés). Aucun registre persisté.
  - [ ] 2.4 Aucun report en cas de broker déconnecté (Q2b C) ; ne **pas** utiliser `pending_discovery_unpublish`, indexé par `eq_id` (C5).
  - [ ] 2.4 bis Corriger la disponibilité et l'appareil du bouton de scénario (pont seul, valeurs neutres) dans `publisher.py` (`_build_availability_fields`, `_build_device_block`) pour `source_kind == "scenario"` ; test de collision d'id (AC 6 bis).
  - [ ] 2.5 Tests de non-régression : appui sur un bouton actif / inactif (`sync/command.py:562-574`), golden, contrat 4D ; `make test`, `flake8`.
- [ ] **Task 3 — Bloc B : CC-47, affichage et décompte (AC: 7-12)**
  - [ ] 3.1 Tests d'abord (rouge), démon : forme de 579 (principal `switch` `ambiguous` refusé + secondaire `binary_sensor` publié sur la même commande) ⇒ décision de commande « publiée » avec le type du secondaire ; cas voisins (aucune entité publiée, plusieurs publiées, commande non couverte, entité unique).
  - [ ] 3.2 Corriger la résolution par commande dans le démon (`evaluate_equipment.py:447-453`, `http_server.py:2592-2616`, `:3007-3025`) sans toucher à ce qui est publié (C12) ; arbre, aperçu et `attendu_ha` / `effective_ha` cohérents.
  - [ ] 3.3 Tests d'abord (rouge), Node, sur un arbre de la forme de 579 : ligne « Sera publié : binary_sensor », synthèse « 5 prêtes, 0 bloquante », totaux de pièce, absence de « Ne sera pas publié ».
  - [ ] 3.4 Écran (`jeedom2ha_mapping_override.js:514-520`, `:633-672`, `:790-857`, `:925-940`) : consommer la décision corrigée, sans recalcul propre à l'UI ; libellé de la cause d'état seul (Q4 A) dans `REASON_LABELS` et `cause_mapping.py`.
  - [ ] 3.5 Commiter le test de caractérisation du chemin « type puis forçage » (AC 10).
  - [ ] 3.6 Réaligner golden / fixtures pour les seuls arbres identifiés en 1.3 ; `make test`, `flake8`.
- [ ] **Task 4 — Gate 20-0 et preuve terrain (humain) (AC: 13)**
  - [ ] 4.1 Gate 20-0 vert (l'interface change, bloc B), contrôle négatif attendu, sans écriture transmise.
  - [ ] 4.2 Déploiement standard du SHA exact (Task 0), inventaire avant/après : les 7 fantômes retirés de HA et du broker sans mode de nettoyage du script, scénarios actifs inchangés (85 attendus, à rejouer), boutons 109/110/113 sans disponibilité locale ; bloc B : ligne de 5369 « Sera publié : binary_sensor », synthèse de 579 sans bloquante, **inventaire MQTT et registre HA identiques** ; artefact de preuve sans nom réel.
- [ ] **Task 5 — Documentation et clôture (AC: 14, 15)**
  - [ ] 5.1 Changelogs, index utilisateur, `sprint-status.yaml`, rétrospective courte de l'epic 21 et passage de `pe-epic-21` à `done` quand la story l'est.

## Dev Notes

- **Contexte d'exécution.** Une session cloud n'a pas accès à la box, à HA ni à un secret ; la preuve terrain est faite par l'humain. Respecter `docs/delegation-claude-cloud.md` et `_bmad-output/project-context.md` (règles d'implémentation Python/PHP/JS, anti-patterns : lecture obligatoire avant de coder).
- **Boucle de sync.** Éviter toute lecture de `request.app["scenario_publications"]` hors de la boucle ; c'est l'état des boutons *actifs* seulement, il sert à `sync/command.py:569` pour accepter ou rejeter un appui.
- **Source unique de décision (gate epic-level 20).** La surface consomme exclusivement `evaluate_equipment()` ; le bloc B corrige la **résolution par commande** dans le démon, pas un recalcul côté écran. Ne jamais changer ce qui est publié : le sync ne lit pas `command_decisions` (C12), `equipment_decision` et `secondary_decisions` restent inchangés.
- **Commande portée par deux entités.** Un override posé sur sa clé `eq:cmd` vaut pour la première entité qui la porte (C15) ; ne pas laisser le sélecteur de type de la ligne laisser croire qu'il règle l'entité qui publie sans l'avoir vérifié (Task 1.5).
- **Invariants.** I11 (découplage état/commandes, 19-2), I3 amendé (ambiguous forcé par l'utilisateur, 20-2) ; aucun changement de mapper dans cette story, donc les invariants de non-doublon entre `SwitchMapper`, `SensorMapper`, `BinarySensorMapper` (stories 11.2, 14.1) ne sont pas touchés.
- **Noms réels.** Aucun nom d'équipement, de pièce ou de scénario réel dans les fichiers du dépôt (CC-48) : identifiants numériques seulement.
- **Testing standards.** Tests unitaires sous `resources/daemon/tests/unit/` (modèles : `test_story_10_1_button_homekit_scenarios.py`, `test_story_19_2_decouplage_state_command_i11.py`) ; golden corpus `resources/daemon/tests/fixtures/golden_corpus/` ; JS : tests Node `tests/unit/*.node.test.js` (obligatoires pour le bloc B).

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh --sha "$(git rev-parse HEAD)"`, en **déploiement standard uniquement** (jamais `--cleanup-discovery` ni `--stop-daemon-cleanup`), pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

#### Guardrails de périmètre

- Aucune ouverture de `PRODUCT_SCOPE`, aucun nouveau FR/NFR.
- Un scénario n'est pas un équipement : ne pas mélanger leurs clés (`eq_id`) dans les structures de report (C5).
- Ne rien supprimer des topics autres que `…/button/jeedom2ha_scenario_<id>/config` dans le bloc A.

### Project Structure Notes

- Fichiers vraisemblablement touchés : `resources/daemon/transport/http_server.py`, `resources/daemon/discovery/publisher.py` (retrait, disponibilité et appareil du scénario), `resources/daemon/transport/mqtt_client.py` (lecture des topics retenus, Q2b C), `resources/daemon/models/evaluate_equipment.py` et `resources/daemon/transport/http_server.py` (résolution par commande, bloc B), `models/cause_mapping.py`, `models/taxonomy.py`, `desktop/js/jeedom2ha_mapping_override.js`, tests et golden, `docs/fr_FR/*`.
- Nommage : `pe-epic-21` suit la convention `pe-epic-N` du cycle « Moteur de projection explicable » (Q0 A).

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
- 2026-10-11 — Relecture R1 (ClaudeBox, PR #234) : pointeurs C1 à C14 confirmés exacts ; cinq corrections appliquées (Task 0 déploiement standard seul ; Q2b révisée avec les chiffres de terrain et option C ; implications HA du retrait dans Q2 ; Q3 avec mesure et vérification de D ; disponibilité des boutons de scénario intégrée au bloc A). Rien n'est tranché par ce document.
- 2026-10-11 — Relecture R2 (ClaudeBox, PR #234, tête `91ebf4a`) : relevé de terrain montrant que 5369 est **déjà publiée** en `binary_sensor` (CC-47 = défaut d'affichage et de décompte, pas de publication). Story recadrée : bloc B refait (résolution par commande, ligne, synthèse, totaux), erratum sur le verdict du 06/10, Q3 réduite à l'équipement à une seule entité (recommandation C), Q4 réduite au libellé de ce cas, section « Questions » réécrite pour se lire seule. Rien n'est tranché par ce document.
- 2026-10-11, vers 20:35 — **Décisions d'Alexandre** (relayées par ClaudeBox) : **Q0 A** (nouvel `pe-epic-21`, story `21-1`), **Q1 A** (une story, deux blocs, deux PR), **Q2 A** (retirer le bouton HA d'un scénario désactivé), **Q2b C** (le broker fait foi), **Q3 C** (pas de changement de mapper ; le chemin « type puis forçage » reste couvert par un test), **Q4 A** (libellé de la cause d'état seul). Toutes les recommandations sont retenues.
- 2026-10-11 — **`ready-for-dev` accordé** par ClaudeBox au nom de cette décision. AC [Qx] figés, variantes non retenues retirées, `sprint-status.yaml` mis en cohérence (`pe-epic-21: in-progress`, story `ready-for-dev`). Faits ajoutés : réglages des entités supprimées conservés dans `deleted_entities` du registre HA (encadré de Q2, à vérifier en AC 13) ; commande de dry-run avec `--sha` (Task 0).

## Dev Agent Record

### Agent Model Used

Agent Claude Code, session cloud déléguée (sans accès box Jeedom, Home Assistant, secrets ni déploiement). Phase `create-story` seulement : aucun code.

### Debug Log References

- Lecture seule du code de `main` `15576cf` ; aucune exécution de test, aucun changement de code.

### Completion Notes List

- Story créée le 2026-10-11 en `backlog`, puis passée `ready-for-dev` le même jour après les décisions d'Alexandre (Q0 A, Q1 A, Q2 A, Q2b C, Q3 C, Q4 A) ; voir R3.
- Tâche 0 « Pre-flight terrain » injectée (story terrain : démon, MQTT, discovery HA) ; elle est réservée à l'humain.
- Aucun nom d'équipement, de pièce ou de scénario réel dans cette story.

### R1 — Relecture ClaudeBox (2026-10-11)

> *Historique : le point 4 ci-dessous (Q3, recommandations D/A) est **remplacé par R2** ; la vérification de l'option D reste valable.*

Cinq points repris, sur la même PR, sans code modifié :

1. **(P1) Task 0 et Task 4.2.** Les modes `--stop-daemon-cleanup` et `--cleanup-discovery --restart-daemon` sont retirés (ils découlaient du bloc injecté par défaut par `create-story`, contraire à la règle d'Alexandre). Remplacés par : « Déploiement standard uniquement, fait par clawcode, du SHA exact (garde-fou CI) ; jamais `--cleanup-discovery` ni `--stop-daemon-cleanup`. » Le guardrail de déploiement est aligné.
2. **(P1) Q2b.** Un registre persisté qui démarre vide ne retire pas les boutons déjà orphelins. Chiffres de ClaudeBox intégrés (92 boutons de scénario dans HA, 85 publiés, 7 fantômes : 2, 32, 33, 39, 40, 72, 129 ; aucun scénario publié absent de HA). Pour chaque option, le sort de ces fantômes est dit. Option C « le broker fait foi » ajoutée, avec ses risques (fenêtre de collecte, motif strict, et un risque supplémentaire relevé : le défaut actuel d'une section `scenarios` absente est une liste vide, `models/topology.py:193-200`, ce qui viderait tous les boutons sans garde-fou). Recommandation révisée en faveur de C. Task 1.4 ajoutée pour établir l'état exact des 5 fantômes inconnus.
3. **(P2) Q2 A.** Implications du retrait dans HA expliquées (automatisations, scripts et tableaux de bord cassés ; personnalisations pouvant ne pas revenir à la réactivation). **Non vérifié dans la documentation de HA** : cette session n'y accède pas (hôte injoignable), la formulation reste prudente et le point est à confirmer avant engagement.
4. **(P2) Q3.** Mesure intégrée (579 et 559 exclu : A ne change aujourd'hui que 5369). Option D vérifiée par un test de caractérisation exécuté dans la session (script jetable dans le répertoire temporaire de session, hors dépôt, non commité, équipement synthétique sans nom réel) : forçage seul refusé (`ha_missing_command_topic`) ; type seul refusé (`ambiguous_skipped`) ; type puis forçage publié avec un payload `binary_sensor` complet. D est donc viable. Un point reste ouvert et signalé : sur un équipement synthétique de forme « prise mesureuse », le registre produit déjà un `binary_sensor` secondaire pour l'état, alors que la décision par commande reste attribuée au principal ; à lever en Task 1 sur la topologie réelle. Recommandation fixée après la vérification : D pour débloquer 5369 sans changer le défaut du parc, A pour publier tout état seul sans geste.
5. **(P2) Bloc A.** La correction de disponibilité des boutons de scénario (pont seul) est intégrée au bloc A (AC 6 bis, Task 2.4 bis) au lieu d'être renvoyée hors périmètre (C8). Le même mécanisme fait reprendre à l'appareil le fabricant et le modèle de l'équipement homonyme (`publisher.py:359-361`, `:372-376`) ; inclus dans la correction.

Vérifications de la session : lecture de `models/availability.py:33-65` et de `discovery/publisher.py:357-386` ; script de caractérisation exécuté en lecture seule. Aucun test du dépôt exécuté, aucun fichier de code modifié.

### R2 — Relecture ClaudeBox (2026-10-11, tête `91ebf4a`)

Fait nouveau (relevé de terrain de ClaudeBox, lecture seule, non rejoué par cette session) : 5369 est déjà publiée en `binary_sensor` ; le principal `switch` est refusé ; l'écran n'affiche que le principal. Cinq points repris, sur la même PR, sans code modifié :

1. **Contexte et erratum.** CC-47 est dit en tête du bloc B et dans le contexte comme un défaut d'affichage et de décompte, avec les faits du relevé (C10). Erratum ajouté : le verdict de `20-2-preuve-complement-2026-10-06.md` n'avait pas vu l'entité `binary_sensor` ; le fichier de preuve n'est pas modifié.
2. **Bloc B recentré.** Résolution par commande (cause racine : `evaluate_equipment.py:447-453`, `covered.setdefault` primaire d'abord ; `http_server.py:2592-2616`), ligne « Sera publié : binary_sensor », synthèse et totaux de pièce, tests démon et tests Node sur la forme de 579 (AC 7-9, Task 3). Constat vérifié dans le code : `command_decisions` n'est lu que par l'arbre et l'aperçu (C12), donc le changement n'agit jamais sur ce qui est publié. Frontière avec CC-51 : cette story corrige la donnée de base et ce qui en est dérivé tel qu'il existe ; la redéfinition de la sémantique des compteurs et le bloc `compteurs` de la documentation restent à CC-51.
3. **Q3 réduite** au cas d'un équipement à une seule entité dont l'état est seul (parc actif : aucun ; 559 exclu). Recommandation : pas de changement de mapper (C) ; D reste possible au cas par cas (vérification de la session conservée) ; A au backlog. AC 7 à 12 réécrits.
4. **Q4** réduite au libellé de la cause d'état seul pour un équipement à une seule entité (la ligne de 5369 est réglée par le bloc B).
5. **Section « Questions pour Alexandre »** réécrite pour se lire seule : pour chaque option, ce qui change dans HA et dans l'écran du plugin.

La remarque de R1 sur ce « point d'attention » (forme de prise mesureuse) est confirmée par le terrain : c'est bien le chemin multi-entité qui publie l'état de 579 (C14). Point de vigilance ajouté : un override de type posé sur une commande portée par deux entités s'applique à la première (C15, Task 1.5).

Vérifications de la session : lecture de `models/evaluate_equipment.py:447-482`, `transport/http_server.py:2592-2616` et `:2999-3099`, `desktop/js/jeedom2ha_mapping_override.js:514-672` et `:790-940`. Aucun test du dépôt exécuté, aucun fichier de code modifié.

### R3 — Consignation des décisions (2026-10-11)

1. Décisions Q0 A, Q1 A, Q2 A, Q2b C, Q3 C, Q4 A consignées au Journal ; AC [Qx] figés ; variantes non retenues retirées (Q2b A et B, Q3 A et D, hors le test de non-régression du chemin « type puis forçage », AC 10) ; story en `ready-for-dev`.
2. Encadré de Q2 complété avec le relevé de ClaudeBox (`core.entity_registry` v1.23, 335 `deleted_entities` conservées avec `entity_id`, `name`, `area_id`, `icon`, `labels`, `aliases`, `options`), formulé prudemment (« devrait », ni garanti ni vérifié) ; vérification ajoutée à l'AC 13.
3. Task 0 : `./scripts/deploy-to-box.sh --sha "$(git rev-parse HEAD)" --dry-run` (PR #235, garde-fou CC-56). Guardrail de déploiement aligné.
4. `sprint-status.yaml` : `pe-epic-21: in-progress`, `21-1-…: ready-for-dev` ; mention « provisoire » retirée de la numérotation (story, `sprint-status.yaml`, `epics-projection-engine.md`).

Aucun code modifié, aucun test exécuté, aucun nom réel.

### Bloc A (CC-44) — Dev Agent (session cloud déléguée, 2026-10-11)

Périmètre : AC 1 à 6 et 6 bis, démon seul. Aucun fichier du bloc B touché ; statut de la story inchangé (`ready-for-dev`) ; cases des Tasks non cochées (clôture par l'humain après preuve terrain, Task 4).

**Branche.** Travail sur `claude/scenario-inactive-button-unpublish-5nokct` (branche assignée par la session, préfixe `claude/` accepté par la CI), au lieu de `story/21-1-cc44-bloc-a-dev-story` ; les deux partent du même SHA `078416a`.

**Task 1 (lecture seule) — relevés rejoués sur `main` `078416a`.**
- C1, C2, C3, C4, C6, C7, C8, C9 : confirmés (C7 : `jeedom2ha.class.php:807`, dans la fourchette annoncée 799-811).
- C5 : mécanisme confirmé, mais les lignes ont bougé (`pending_discovery_unpublish` apparaît à `http_server.py:472`, `:685`, `:696`, plus que `:985-1018`) ; non utilisé par le bloc A.
- **Écart 1 — motif de souscription.** Le motif `<préfixe>/button/jeedom2ha_scenario_+/config` cité par Q2b/AC 3 n'est **pas un filtre MQTT valide** (un joker `+` doit occuper un niveau entier). Le démon s'abonne donc à `<préfixe>/button/+/config` et ne retient que les topics qui satisfont l'expression stricte `^<préfixe>/button/(jeedom2ha_scenario_([0-9]+))/config$` ; tout le reste est ignoré (AC 3 b).
- **Écart 2 — `scenarios` non-liste.** `TopologySnapshot.from_jeedom_payload` plantait (HTTP 500) si `scenarios` valait `null` ; rendu tolérant (traité comme absent), nécessaire au garde-fou AC 3 c.
- 1.2 (rejeu du relevé sur 579) et 1.4 (état des 7 fantômes 2/32/33/39/40/72/129, identifiants partagés 109/110/113) : **non vérifiables depuis la session** (pas de box ni de HA) ; non inventés. Le comportement est prouvé par des tests sur identifiants synthétiques.

**Implémentation.**
- `http_server.py` (boucle scénarios) : un scénario inactif reçoit `DiscoveryPublisher.unpublish` si le broker est connecté ; sinon rien n'est reporté (AC 4), la purge reprend au sync suivant. Aucun passage par `pending_discovery_unpublish`.
- `publisher.py` : `purge_orphan_scenario_buttons(active_ids, already_unpublished)` lit les topics retenus via le bridge, vide ceux dont l'id n'est pas actif (jamais deux fois le même, jamais hors motif). `_build_device_block` / `_build_availability_fields` : pour `source_kind == "scenario"`, pont seul et fabricant/modèle neutres (AC 6 bis).
- `mqtt_client.py` : `MqttBridge.collect_retained_topics(filter, window_s=1.5)` — abonnement, fenêtre bornée, désabonnement ; ne rapporte que des messages **retenus et non vides** ; renvoie `None` si non connecté, collecte déjà en cours ou abonnement refusé. Une fenêtre trop courte ne fait que sous-déclarer.
- Garde-fous de purge : broker connecté ; `scenarios` présent **et** liste **et** toutes les entrées lues (sinon aucune purge, journalisé) ; exception ou résultat invalide de la collecte ⇒ aucune purge. Section présente mais vide ⇒ les fantômes sont retirés (plus aucun scénario).
- Journal : `[SCENARIO] Unpublished N scenario button(s) (a inactive, b from broker)` — compteurs seulement, aucun nom.

**Revue Codex (PR #237) — scan PHP partiel.** `core/class/jeedom2ha.class.php` ignorait silencieusement un scénario illisible tout en envoyant une liste valide ; la comparaison de longueurs côté démon ne suffisait donc pas. Le PHP envoie maintenant `scenarios_complete` (faux si la classe `scenario` est absente ou si un scénario a été ignoré) et le démon n'autorise la purge que si `scenarios_complete is True` (un payload sans ce drapeau ne purge pas). Écart ajouté à la story : AC 3 c étendu par ce drapeau, 2 tests de plus (23 au total).

**Tests ajoutés** : `tests/unit/test_story_21_1_cc44_scenario_lifecycle.py` (21 tests, écrits rouges avant le code) : inactif dépublié / actif publié / réactivation (même `unique_id` et `command_topic`) ; purge fantômes avec actif conservé et pas de double vidage ; topics hors motif intacts (9 variantes) ; collecte vide / `None` / invalide / en exception ; `scenarios` absent, non-liste, entrée illisible ⇒ aucune purge ; section vide ⇒ purge ; broker déconnecté ⇒ rien publié ni reporté ; collision d'id scénario/équipement 10 (le report de l'équipement est rejoué indépendamment) ; appui actif accepté / inactif absent de `scenario_publications` ; AC 6 bis avec collision d'id 110 (ni `jeedom2ha/110/availability` ni le type de l'équipement) ; charge utile identique sans homonyme ; bouton d'équipement inchangé ; `collect_retained_topics` (déconnecté, filtrage retenu/non vide, échec d'abonnement).

**Vérifications** : `python3 -m pytest` (suite complète `tests/` + `resources/daemon/tests`) 2095 passés, 1 ignoré ; `make test` 645 passés ; `flake8` propre ; 28 fichiers `tests/unit/*.node.test.js` verts. Golden corpus **non modifié** (aucun scénario inactif ni homonyme dans le corpus).

**Docs (AC 14, part bloc A)** : entrée `changelog_beta.md` et une phrase dans `docs/fr_FR/index.md` (section « Rescanner la topologie Jeedom »).

**Reste pour l'humain (AC 13, bloc A)** : preuve terrain (7 fantômes retirés, réactivation, 109/110/113 sans disponibilité locale, réglages HA conservés ou écart consigné).

### File List

- `_bmad-output/implementation-artifacts/21-1-solde-reserves-cc44-scenario-desactive-cc47-etat-sans-ordre-on-off.md` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (inscription provisoire)
- `_bmad-output/planning-artifacts/epics-projection-engine.md` (Epic 21 proposé)
