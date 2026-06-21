# Story 11.3: IQ EV Charger (eq583) + Pilotage priorisation solaire (eq628) — reconnaissance `SWITCH_*` générique + multi-switch structurel (lecture seule + actionnables)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur familial de Home Assistant,
je veux voir dans HA le détail de mon chargeur de voiture `IQ EV` (eq583 : branché, connecté, charge en cours, puissance/énergie, et les commandes On/Off de charge, charge solaire et charge manuelle) ainsi que les commandes du `Pilotage priorisation solaire` (eq628 : filtration piscine, chauffage piscine, chauffage SPA, charge voiture),
afin de suivre et piloter depuis mon dashboard solaire les charges arbitrées par le routeur, sans ouvrir de nouveau type HA ni de promesse UX cosmétique.

## Acceptance Criteria

1. **Approche GÉNÉRIQUE, sans couplage par ID (Option A).** La story livre un **mécanisme générique** : la reconnaissance des interrupteurs `SWITCH_*` et l'émission multi-switch fonctionnent sur **n'importe quelle** installation Jeedom, pilotées par la **structure / les capacités des commandes** — **jamais** par une liste d'`eq_id` codée en dur. eq583 et eq628 sont les **cibles de validation terrain** (les équipements sur lesquels on prouve le mécanisme), pas un périmètre codé. Le **périmètre publié** (quels équipements atteignent HA) reste gouverné par l'**opérateur** via `published_scope` (include/exclude/inherit, `models/published_scope.py`), pas par le code. Aucune ouverture de type dans `PRODUCT_SCOPE` (`sensor`, `binary_sensor`, `switch`, `button` déjà ouverts — `ha_component_registry.py`).

2. **Inventaire de référence = capture terrain Task 0 (source de vérité), inventaire curate dégradé en indication.** Le mapping traite **toutes** les commandes éligibles réellement présentes selon la capture (`type`/`sub_type`/`generic_type`/`unit` par commande), pas selon l'inventaire curate (`backlog-icebox §4`) qui diverge. Cibles confirmées par le terrain :
   - **IQ EV (eq583)** — `eq_type=null`, `generic_type=null`, 21 commandes :
     - `switch` (**3 trios `SWITCH_*`**, regroupés par préfixe de nom) : **Charge** (`#5987` état / `#5997` On / `#5998` Off), **Charge solaire** (`#6009` état / `#5999` On / `#6001` Off), **Charge manuelle** (`#6010` état / `#6000` On / `#6021` Off).
     - `sensor` (numeric `GENERIC_INFO`) : `#5991` Puissance (W), `#5992` Énergie session (Wh), `#5993` Énergie jour (Wh).
     - `binary_sensor` (`SWITCH_STATE` info **non** consommé par un switch) : `#5986` Branché, `#5988` Connecté. (`#5987`/`#6009`/`#6010` sont les readbacks des 3 switches → **pas** de binary_sensor indépendant, anti-doublon AC#5.)
     - **exclus** : `string GENERIC_INFO` (`#5989`, `#5990`, `#5994`, `#5995`, `#5996`) — non numériques.
     - **actions sans generic_type** (`#6003` action_ev, `#6002` Rafraîchir) → **ignorées** (D4, voir §Décisions de design).
   - **Pilotage priorisation (eq628)** — `eq_type=null`, 13 commandes : **4 switches `SWITCH_*`** (name-grouped) : Filtration piscine (`#5977`/`#5978`/`#5979`), Chauffage piscine (`#5980`/`#5981`/`#5982`), Chauffage SPA (`#5983`/`#5984`/`#5985`), Charge voiture (`#6004`/`#6005`/`#6006`). `#5976` Rafraîchir → **ignorée** (D4). Aucun sensor/binary additionnel.

3. **Reconnaissance `SWITCH_*` générique + grading de confiance (D1 — cœur de la story).** Le `SwitchMapper` reconnaît `SWITCH_STATE`/`SWITCH_ON`/`SWITCH_OFF` **en plus** de `ENERGY_*`, pour **tous** les eqLogics (`switch.py:_SWITCH_GENERIC_TYPES`, l.32-36). Le comportement `ENERGY_*` reste **strictement inchangé** (confiance, reason_codes, device_class). Une signature `SWITCH_*` pure (sans `ENERGY_*`, appariement par nom seul) sort en confiance **`probable`** — donc **bloquée par défaut** sous politique `sure_only` (`decide_publication.py:88`). Conséquence : les **11 autres** eqLogics porteurs de `SWITCH_*` (550, 580, 174, 235, 207, 234, 475, 206, 632, 631, 594) sont **reconnus** mais **ne sont pas auto-publiés en masse** — ils sont gouvernés par la **confiance + le scope opérateur**, jamais par une exclusion codée par ID.

4. **Multi-switch STRUCTUREL (N switches par eqLogic), sans allowlist.** Le `SwitchMapper` expose un `map_all` (multi-entité) qui regroupe les trios état+On+Off d'une **même charge logique** en **N switches distincts** via une **clé structurelle déterministe** : structure Jeedom si disponible (paires On/Off, `logicalId`, sous-groupe), sinon **préfixe de nom documenté** (heuristique d'AC#4 confirmée inévitable par le terrain — eq583/eq628 n'ont ni `logicalId` ni structure). Chaque switch logique tire son identité de l'**ID de commande Jeedom** (`unique_id`/`object_id`/`state_topic` dérivés de la cmd d'état), **jamais** du nom (le nom n'est qu'une **clé de regroupement**, pas un identifiant). Tous rattachés au même device (`identifiers: ["jeedom2ha_583"]` resp. `["jeedom2ha_628"]`). Aucune commande On/Off orpheline publiée comme switch complet. Le `map()` mono-switch historique est préservé pour la back-compat.

5. **Anti-doublon état / binary_sensor (héritage anti-dup 11.2).** Une commande d'état utilisée comme **readback d'un `switch`** (`#5987`/`#6009`/`#6010`) n'est **pas** dupliquée en `binary_sensor` indépendant : la capacité on/off est portée par le `switch` logique correspondant (cf. exclusion `ENERGY_STATE` #5708 du binary_sensor en 11.2). Seules les commandes info binaires **non** consommées par un switch (`#5986` Branché, `#5988` Connecté) deviennent des `binary_sensor`. La décision pour `#5987`/`#6009`/`#6010` (readback switch, pas binary_sensor) est figée par la structure terrain (Task 1).

6. **Restitution de valeur runtime via streaming (12.1 + 12.2, done).** Les `sensor`/`binary_sensor` (eq583) sont alimentés par la vague 1 (Story 12.1) ; les états des `switch` (eq583 ×3, eq628 ×4) sont alimentés par la vague 2 (Story 12.2) sur leur `state_topic` discovery — les switches alimentés par une commande info de readback ne sont **pas** en `unknown`. Chaque switch logique déclare son **propre** `state_topic`, et le périmètre exposé par `list_state_targets()` couvre ces topics (cohérence state ⊆ discovery).

7. **Prédicat STRUCTUREL remplace le gate par ID dans le registry (Option A).** Le routage multi-domaine/multi-entité ne dépend **plus** de l'allowlist `MULTI_DOMAIN_EQ_IDS` (`topology.py:234`, `registry.py:73`). Il est déclenché par un **prédicat structurel** : un eqLogic dont les mappers produisent **plus d'un** `MappingResult` (plusieurs domaines et/ou plusieurs switches) emprunte naturellement le chemin d'agrégation. La règle « premier mapper gagnant » est préservée **au niveau de chaque commande** (une commande → un seul domaine, pas de double-classification light/switch). **eq554 est migré sur ce prédicat** avec parité de comportement testée ; la constante `MULTI_DOMAIN_EQ_IDS` est **retirée** (ou réduite à un artefact de test transitoire, jamais un gate sémantique). Le mono-domaine (un seul résultat) reste inchangé.

8. **Pas de régression — et pas de débordement de publication.** (a) Les mappers `light`, `cover`, `switch` (mono-switch `ENERGY_*` des autres eqLogics), `climate`, `alarm_control_panel`, `presence_switch`, `binary_sensor`, `sensor` (mono + multi-sensor eq553 + multi-domaine eq554), `button`, `fallback` conservent leur comportement. (b) **eq554** : `switch.jeedom2ha_554` et son agrégation multi-domaine restent **identiques** après migration sur le prédicat structurel (parité testée). (c) **Les 11 autres `SWITCH_*`** sont reconnus mais **ne déferlent pas dans HA** : signature `SWITCH_*` pure → `probable` → bloquée sous `sure_only` ; sous `sure_probable`, ce sont le `published_scope` opérateur et la confiance qui gouvernent, **aucune exclusion codée par ID**. (d) Les sensors eq553 (11.1) restent inchangés.

9. **Validation HA obligatoire.** Chaque entité dérivée de eq583/eq628 passe par `validate_projection()` avec les capabilities adaptées (`SwitchCapabilities` par switch logique, `SensorCapabilities(has_state=True)` pour les sensors, capabilities binaires pour les binary_sensors) et ne publie rien si la validation échoue.

10. **Diagnostic, compteurs honnêtes et cycle de vie multi-entité (anti-ghosts).** Les compteurs par domaine (`switches_published`, `sensors_published`, `binary_sensors_published`, `published`) reflètent les entités réellement publiées (N switches > 1 par eqLogic compris) ; un échec de publication d'une entité secondaire ne produit pas un faux succès (héritage 11.1). La dépublication de eq583/eq628 (`unpublish_by_eq_id`, **domain-aware**, tuples `(entity_type, node_id)` hérités de 11.2) nettoie **tous** les topics discovery `homeassistant/<domain>/jeedom2ha_{583|628}_<cmd>/config` (chaque switch logique inclus), sans fantôme HA, avec persistance cross-reboot (`disk_cache`).

11. **Golden corpus, test de généricité et non-régression complète.** Le golden corpus intègre un cas eq583 (multi-domaine + 3 switches) et un cas eq628 (4 switches). **Test de généricité explicite** : un eqLogic `SWITCH_*` **fictif hors eq583/eq628** (≥2 trios) vérifie que le multi-switch s'active par **structure** (pas par ID) ET qu'en signature `SWITCH_*` pure il sort `probable` (donc bloqué sous `sure_only`, non auto-publié). `expected_sync_snapshot.json` n'est régénéré que pour les deltas attendus ; la suite pytest complète reste verte (baseline ≥ 917, Story 11.2 incluse).

12. **Gate terrain.** Sur box réelle DEV/TEST `192.168.1.21`, après `deploy → restart → sync` : les topics discovery des entités eq583 (3 sensors + 2 binary_sensors + **3 switches**) et eq628 (**4 switches**) sont publiés sous leurs devices `jeedom2ha_583` / `jeedom2ha_628` ; les switches alimentés par readback sont **non-`unknown`** (état streamé par 12.2) ; les valeurs sont lisibles dans HA/MQTT. Vérifier en parallèle qu'**aucun des 11 autres `SWITCH_*`** n'apparaît de façon inattendue (selon `published_scope` et `confidence_policy` de la box). Gate documentable avec waiver explicite si l'équipement live est indisponible.

13. **Forward-compat avec l'epic suivant « config par équipement à la Homebridge » (contrainte structurante).** Aucune décision de cette story ne doit devenir un **frein** à un futur epic permettant à l'opérateur de configurer **chaque équipement** individuellement. Concrètement : (a) **aucun `eq_id` codé en dur** comme logique sémantique ou de périmètre (c'est l'objet d'Option A) ; (b) la classification (est-ce un switch ? quel device_class ? combien de switches ?) est **dérivée de données** (structure terrain + capacités), donc **surchargeable par équipement** plus tard sans réécrire le moteur ; (c) le périmètre s'appuie sur `published_scope` (déjà per-équipement) — **graine** de la config par équipement, à enrichir et non à contourner ; (d) `confidence_policy` est aujourd'hui **global** (`http_server.py:1216`) : la story ne doit **rien** coder qui empêche une bascule future vers une politique **per-équipement** (pas de constante globale en dur qui supposerait l'unicité de la politique).

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market) — **EXÉCUTÉE le 2026-06-19 (box `192.168.1.21`, capture read-only `jeedom2ha::getFullTopology()`, aucune mutation HA).**
  - [x] Connexion SSH + sudo box validés (read-only).
  - [x] **Topologie réelle eq583 ET eq628 capturée** → `_bmad-output/terrain-captures/11-3-topology-eq583-eq628-20260619.json`. Voir §Capture terrain Task 0.
  - [x] **Divergences terrain analysées + escalade → décisions de design D1–D4 prises (Option A, 2026-06-19).** Voir §Décisions de design.
  - [x] Déploiement/gate live (`deploy-to-box.sh --cleanup-discovery --restart-daemon`) : **PASS le 2026-06-21** après feu vert utilisateur (box `192.168.1.21`, `Deploy complete.`).

- [x] Task 1 — Figer le besoin multi-domaine + multi-switch et la clé de regroupement structurelle (AC: 2, 3, 4, 5)
  - [x] À partir de la topologie réelle (Task 0), figer pour eq583 et eq628 la liste des commandes éligibles et leur domaine cible (`sensor` info numérique, `binary_sensor` info binaire non consommée par un switch, `switch` logique = trio état+On+Off).
  - [x] **Figer la clé de regroupement structurelle** (AC#4) : préfixe de nom documenté (strip « On »/« Off » → match au nom de l'état `SWITCH_STATE`), avec ses limites explicites. Décrire dans les Dev Notes. Concevoir la règle pour qu'elle soit **générique** (pas spécifique à eq583/eq628).
  - [x] **Figer `#5987`/`#6009`/`#6010`** (AC#5) : readback des 3 switches de charge eq583 (pas de binary_sensor indépendant). `#5986`/`#5988` → binary_sensor.
  - [x] Tests unitaires rouges : eq583 attend 3 `sensor` + 2 `binary_sensor` + **3** `switch` ; eq628 attend **4** `switch` ; tous rattachés à leur device, chacun avec `state_topic` propre. Ajouter un cas **eqLogic `SWITCH_*` fictif** (généricité, AC#11).

- [x] Task 2 — Reconnaissance générique `SWITCH_*` + multi-switch structurel + retrait du gate par ID (AC: 3, 4, 7, 8, 13)
  - [x] Ajouter `SWITCH_STATE`/`SWITCH_ON`/`SWITCH_OFF` à `_SWITCH_GENERIC_TYPES` (`switch.py:32-36`) — **globalement**, pas de scope par ID. Vérifier que les `SWITCH_*` ne figurent pas dans `_ANTI_SWITCH_GENERIC_TYPES`.
  - [x] **Grading de confiance (D1)** : une signature `SWITCH_*` pure (sans `ENERGY_*`, regroupée par nom) sort en `probable`. Préserver à l'identique la confiance/les reason_codes du chemin `ENERGY_*`. Tests : sous `sure_only`, un `SWITCH_*` pur → `probable_skipped` (non publié) ; sous `sure_probable`, publié.
  - [x] Doter `SwitchMapper` d'un `map_all` (multi-entité) produisant **N** `MappingResult` switch (un par charge logique, regroupement structurel Task 1). Réutiliser le patron `map_all` de 11.1/11.2 (Sensor/BinarySensor) — ne pas réinventer. Préserver `map()`/`decide_publication()` mono-switch (back-compat AC#8).
  - [x] **Retirer le gate par ID** : remplacer `registry.py:73` (`if eq.id in MULTI_DOMAIN_EQ_IDS`) par un **prédicat structurel** (eqLogic dont l'ensemble des mappers renvoie >1 résultat → chemin d'agrégation). **Migrer eq554** sur ce prédicat. **Retirer** `MULTI_DOMAIN_EQ_IDS` de `topology.py` (ou la réduire à une fixture de test, jamais un gate). Préserver « premier mapper gagnant » **par commande** (pas de double-classification).
  - [x] Identité par switch logique dérivée des IDs `cmd` : `unique_id=jeedom2ha_eq_{eq}_cmd_{state_cmd}`, `object_id/node_id=jeedom2ha_{eq}_{state_cmd}`, `state_topic=jeedom2ha/{eq}/{state_cmd}/state`. **Jamais** dérivé du nom.
  - [x] Ne pas modifier `PRODUCT_SCOPE`.

- [x] Task 3 — Publier des topics discovery/state distincts par switch logique et par domaine (AC: 6, 9)
  - [x] Vérifier/étendre `DiscoveryPublisher.publish_switch()` et son payload pour gérer **plusieurs** switches par eqLogic (node_id/object_id/state_topic via `reason_details`), à l'image du multi-entité 11.2 (`_build_*_payload`). Réutiliser l'existant.
  - [x] Confirmer que chaque switch logique déclare son propre `state_topic` et que `payload_on=ON`/`payload_off=OFF` restent cohérents (contrat 12.2 `_build_switch_payload`).
  - [x] Tests sur les payloads des switches multiples (eq583 ×3, eq628 ×4), sensors et binary_sensors eq583.

- [x] Task 4 — Diagnostic, compteurs, cycle de vie et streaming sans régression (AC: 6, 10)
  - [x] Vérifier que `switches_published` compte chaque switch logique (eq583 ×3, eq628 ×4) et que les compteurs sensor/binary reflètent eq583.
  - [x] Vérifier la dépublication exhaustive domain-aware (`unpublish_by_eq_id` / `_collect_unpublish_node_ids`, tuples `(entity_type, node_id)`) : chaque switch logique, sensor et binary_sensor effacé dans son domaine ; persistance cross-reboot `disk_cache`. Pas de topic orphelin.
  - [x] Vérifier que `list_state_targets()` / `StateSynchronizer` (12.2) exposent un `state_topic` par switch logique ; cohérence state ⊆ discovery.
  - [x] Vérifier que le diagnostic reste honnête (échec secondaire visible, mécanisme `multi_*_partial_publish_failed` inchangé).

- [x] Task 5 — Golden corpus, généricité, tests complets et gate terrain (AC: 8, 11, 12)
  - [x] Ajouter eq583 (multi-domaine + 3 switches) et eq628 (4 switches) au golden corpus (`sync_payload.json` ; `_assert_corpus_shape` mis à jour).
  - [x] **Parité eq554** : test confirmant que la migration vers le prédicat structurel ne change rien à l'agrégation/au `switch.jeedom2ha_554` (AC#8b).
  - [x] **Généricité + non-débordement** : test avec un eqLogic `SWITCH_*` fictif (≥2 trios) hors eq583/628 → multi-switch déclenché par structure ; en signature `SWITCH_*` pure → `probable`, donc `probable_skipped` sous `sure_only` (AC#8c, AC#11).
  - [x] Régénérer `expected_sync_snapshot.json` (hook `GOLDEN_REGEN=1`) — vérifier l'ordre du registry et les compteurs.
  - [x] Lancer la suite pytest complète (`python3 -m pytest -q`) → unit daemon vert ; suite globale bloquée par dépendance externe `jeedomdaemon` absente (voir §Senior Developer Review).
  - [x] Gate terrain (box 192.168.1.21) : `deploy → restart → sync` ; vérifier les entités eq583/eq628 sous leurs devices, switches non-`unknown` (readback 12.2), et l'absence d'apparition inattendue des 11 autres `SWITCH_*`. **PASS le 2026-06-21** : voir Completion Notes.

## Dev Notes

### Décisions de design (Option A — prises le 2026-06-19, escalade Task 0 résolue)

Suite à la divergence terrain majeure (§Capture terrain Task 0), les 4 décisions de design ont été tranchées par l'utilisateur en faveur d'une **approche générique franche (Option A)** — le plugin doit rester générique et fonctionner sur n'importe quelle installation, et **aucune décision ne doit freiner** le futur epic « config par équipement à la Homebridge ».

- **D1 — Portée de la reconnaissance `SWITCH_*` : GÉNÉRIQUE (pas de scope par ID).** `SwitchMapper` reconnaît `SWITCH_*` globalement, au même titre que `ENERGY_*`. La sécurité contre le débordement sur les 11 autres eqLogics n'est **pas** un allowlist d'ID codé, mais la combinaison : (1) **grading de confiance** — signature `SWITCH_*` pure → `probable` → bloquée sous `sure_only` ; (2) **`published_scope` opérateur** — include/exclude per-équipement, déjà existant. Rationale : séparer la **classification** (générique, dans le code) du **périmètre** (donnée d'installation, pilotée par l'opérateur). Mettre `{583,628}` en dur reviendrait à coder une donnée d'installation dans le plugin — rejeté.
- **D2 — Regroupement par préfixe de nom : CONFIRMÉ (inévitable, documenté).** eq583/eq628 n'ont ni `logicalId` ni structure exploitable. L'appariement état/On/Off se fait par préfixe de nom (strip « On »/« Off » → match au nom du `SWITCH_STATE`). C'est une **clé de regroupement** documentée (AC#4), pas un identifiant d'entité (les IDs d'entité restent les `cmd` IDs). La règle doit être écrite de façon **générique**.
- **D3 — eq583 = 3 switches : PUBLIER LES 3.** Le terrain révèle un trio « Charge » générique (`#5987`/`#5997`/`#5998`) absent du curate, en plus de « Charge solaire » et « Charge manuelle ». La détection structurelle en trouve 3 → on publie 3. Le périmètre final reste de toute façon arbitrable par l'opérateur via `published_scope`.
- **D4 — Commandes action sans generic (`#6003` action_ev, `#6002`/`#5976` Rafraîchir) : IGNORÉES dans cette story.** Pas d'ouverture button supplémentaire ici (scope serré, pas de cosmétique). Réévaluable dans un epic ultérieur si besoin.

### Architecture générique retenue (Option A) — pourquoi elle ne freine pas l'epic suivant

- **Deux couches séparées.** *Classification* (« cet eqLogic / cette commande est-il un switch ? combien ? quel device_class ? ») = **générique, dans le code**, dérivée de la structure terrain et des capacités. *Périmètre* (« cette install expose-t-elle CET équipement ? ») = **donnée opérateur**, via `published_scope`. Le réflexe « scoper par ID » mélangeait les deux couches au mauvais étage.
- **Le périmètre opérateur existe déjà** : `resolve_published_scope()` (`published_scope.py:77`) résout include/exclude/inherit par équipement → pièce → global, alimenté par `payload["published_scope"]` au sync (`http_server.py:1228-1229`), exposé via `GET /system/published_scope` (`http_server.py:2262`). C'est la **graine** de l'epic « config par équipement » : il sera enrichi (override per-eq de la classification/confiance), pas réinventé. **Ne pas le contourner.**
- **Sécurité de rollout générique** : `confidence_policy` (`sure_only`/`sure_probable`) est lu du sync (`http_server.py:1216`) et bloque `probable` (`decide_publication.py:88`). Une signature `SWITCH_*` pure → `probable` ⇒ sous `sure_only`, un nouvel interrupteur détecté **remonte pour revue** au lieu d'inonder HA — vrai sur **toute** install, sans aucun ID.
- **Prédicat structurel, pas allowlist** : le chemin multi-domaine/multi-switch se déclenche quand les mappers d'un eqLogic renvoient >1 résultat (multi-domaine et/ou multi-switch) — propriété **intrinsèque**, valable partout. L'allowlist `MULTI_DOMAIN_EQ_IDS` (`topology.py:234`) est précisément le genre de « frein » par ID que l'epic suivant devrait retirer → on le **retire dès maintenant** et on migre eq554 dessus (parité testée).
- **Forward-compat `confidence_policy`** : aujourd'hui global. La story n'introduit **aucune** hypothèse d'unicité globale qui empêcherait une future politique **per-équipement** (cf. AC#13d).

### Capture terrain Task 0 (2026-06-19, box 192.168.1.21) — divergences décisives (factuel, conservé)

Capture read-only `jeedom2ha::getFullTopology()` (aucune mutation HA). Artefact : `_bmad-output/terrain-captures/11-3-topology-eq583-eq628-20260619.json`.

**eq583 « IQ EV Charger »** — `eq_type=null`, `generic_type=null`, **21 commandes**. Domaines réels :
- **3 switches logiques** (pas 2), `generic_type` `SWITCH_STATE`/`SWITCH_ON`/`SWITCH_OFF`, regroupés par **préfixe de nom** :
  - « Charge » : état `#5987` (SWITCH_STATE) + `#5997` On + `#5998` Off — **absent de l'inventaire curate**.
  - « Charge solaire » : état `#6009` + `#5999` On + `#6001` Off.
  - « Charge manuelle » : état `#6010` + `#6000` On + `#6021` Off.
- **sensor** (numeric `GENERIC_INFO`) : `#5991` Puissance (W), `#5992` Énergie session (Wh), `#5993` Énergie jour (Wh).
- **binary_sensor** (`SWITCH_STATE` info **non** consommé par un switch) : `#5986` Branché, `#5988` Connecté. → `#5987`/`#6009`/`#6010` sont les readbacks des 3 switches (anti-doublon AC#5).
- **exclus** : `string GENERIC_INFO` (`#5989` État connecteur, `#5990` Mode de charge, `#5994` Dernière MAJ, `#5995` Source, `#5996` Diagnostic) — non numériques.
- **action sans generic_type** : `#6003` action_ev, `#6002` Rafraîchir → **ignorées** (D4).

**eq628 « pilotage priorisation solaire »** — `eq_type=null`, **13 commandes**. Conforme au curate (4 charges) :
- **4 switches logiques** (`SWITCH_*`, name-grouped) : Filtration piscine (`#5977`/`#5978`/`#5979`), Chauffage piscine (`#5980`/`#5981`/`#5982`), Chauffage SPA (`#5983`/`#5984`/`#5985`), Charge voiture (`#6004`/`#6005`/`#6006`).
- `#5976` Rafraîchir (action, sans generic) → **ignorée** (D4).
- Aucun sensor, aucun binary_sensor additionnel.

**Divergences vs hypothèses curate / 10.4 (à l'origine du HALT, désormais résolues par Option A) :**
1. **generic types = `SWITCH_*`, PAS `ENERGY_*`.** Le `SwitchMapper` ne connaissait que `ENERGY_*` (`switch.py:32-36`) → il ne captait ni eq583 ni eq628. → **résolu par D1 (reconnaissance générique `SWITCH_*`)**.
2. **eq583 = 3 switches** (curate en listait 2). → **résolu par D3 (publier 3)**.
3. **Regroupement par nom** (aucun `logicalId`/structure). → **résolu par D2 (clé de regroupement par préfixe documentée)**.
4. **Surface de régression : 13 eqLogics** portent des `SWITCH_*` (550 Programme Aspirateur, 580 E-208, 583, 628, 174 Absence, 235/207/234/475/206 Présence×, 632 SPA-Filtre, 631 SPA-Hivernage, 594 SPA_Intex). → **résolu par D1 sans scope ID** : reconnaissance globale + sécurité par confiance (`probable`/`sure_only`) + `published_scope` opérateur. Les 11 autres ne déferlent pas (AC#8c).

### Analyse architecture

- **Pipeline** : `JeedomEqLogic` → `MapperRegistry.map_all` → 1..N `MappingResult` → validation HA → `decide_publication` → publication MQTT. Story 11.1 a introduit le multi-**entité** mono-domaine (eq553 → N sensors) ; 11.2 le multi-**domaine** (eq554 → switch+sensor+binary) via `MULTI_DOMAIN_EQ_IDS = {554}` + `registry._map_multi_domain`. **Story 11.3 généralise** : reconnaissance `SWITCH_*` globale, multi-switch structurel, et **remplacement du gate par ID par un prédicat structurel** (eq554 migré).
- **Reconnaissance (`switch.py:32-36`)** : ajouter `SWITCH_STATE/ON/OFF` à `_SWITCH_GENERIC_TYPES`. Le reste du `SwitchMapper` (anti-affinité `switch.py:116`, heuristique de nom `switch.py:137`, device_class) reste générique et s'applique tel quel — c'est de la **qualité de classification**, pas du périmètre. Si un des 11 autres est un faux positif, on **renforce le garde-fou générique**, on ne code pas un ID.
- **Multi-switch (cœur)** : le `SwitchMapper` actuel indexe `energy_cmds: Dict[str, JeedomCmd]` par `generic_type` → collision de clés pour plusieurs trios. L'extension : `map_all` regroupe par **clé structurelle** (préfixe de nom, D2) et émet un `MappingResult` switch par trio. Identité = `cmd` ID (jamais le nom).
- **Prédicat structurel (`registry.py:73`)** : remplacer `if eq.id in MULTI_DOMAIN_EQ_IDS` par « l'agrégation des mappers de cet eqLogic renvoie >1 résultat ». Concrètement, router **chaque commande** vers son meilleur domaine (premier-mapper-gagnant par commande), puis agréger ; un eqLogic mono-résultat suit le chemin simple. eq554 produit le même résultat qu'avant → parité.
- **Confiance & rollout** : signature `SWITCH_*` pure → `probable`. Sous `sure_only`, `decide_publication` renvoie `probable_skipped` (`decide_publication.py:88`) → non publié. Sous `sure_probable`, publié si `published_scope` l'inclut.
- **Anti-doublon** (`#5987`/`#6009`/`#6010`) : readbacks de switches → exclus du binary_sensor (patron #5708 de 11.2).
- **Streaming (12.2 done)** : chaque switch logique a son `state_topic` → `list_state_targets()` doit tous les exposer (cohérence state ⊆ discovery, AC 12.2#7).

### Code à inspecter / modifier

- `resources/daemon/mapping/switch.py` — `_SWITCH_GENERIC_TYPES` (l.32-36, **ajouter `SWITCH_*`**) ; grading `probable` pour signature `SWITCH_*` pure ; introduire `map_all` multi-switch (regroupement structurel) ; préserver `map()`/`decide_publication()` mono-switch.
- `resources/daemon/mapping/registry.py` — `map_all`/`_map_multi_domain`/`_invoke_mapper` (l.61-103) : **remplacer le gate `if eq.id in MULTI_DOMAIN_EQ_IDS` (l.73) par un prédicat structurel** ; préserver premier-mapper-gagnant par commande.
- `resources/daemon/models/topology.py` — **retirer `MULTI_DOMAIN_EQ_IDS` (l.234)** comme gate sémantique (migrer eq554) ; `MULTI_SENSOR_EQ_TYPES`, `assess_eligibility` inchangés.
- `resources/daemon/mapping/sensor.py`, `resources/daemon/mapping/binary_sensor.py` — `map_all` multi-entité (réutiliser pour eq583 sensors/binaires ; exclusion des commandes consommées par un switch).
- `resources/daemon/models/mapping.py` — `MappingResult` (`ha_unique_id`, `additional_mappings`), `SwitchCapabilities`, `SensorCapabilities`.
- `resources/daemon/models/decide_publication.py` — comportement `sure_only`/`probable_skipped` (l.88) consommé tel quel, **non modifié**.
- `resources/daemon/models/published_scope.py` — **non modifié** (consommé en l'état comme couche périmètre opérateur ; graine de l'epic config par équipement).
- `resources/daemon/discovery/publisher.py` — `publish_switch`/`_build_switch_payload` (multi-entité via `reason_details`).
- `resources/daemon/transport/http_server.py` — orchestration sync, `confidence_policy` (l.1216), `published_scope` (l.1228), boucle de publication (l.1285+), compteurs par domaine, `unpublish_by_eq_id` + `_collect_unpublish_node_ids`.
- `resources/daemon/sync/state.py` — `StateSynchronizer` (12.2) : `list_state_targets()`, gating discovery.
- `resources/daemon/validation/ha_component_registry.py` — `PRODUCT_SCOPE` (**ne pas modifier**).
- `resources/daemon/tests/unit/test_story_11_2_eq554_multi_domain.py` — patron + **parité eq554** après migration prédicat.
- `resources/daemon/tests/unit/test_story_11_1_msunpv_multi_sensor.py` — patron multi-entité.
- `resources/daemon/tests/unit/` — **nouveau test de généricité `SWITCH_*`** (eqLogic fictif, AC#11).
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py` + `tests/fixtures/golden_corpus/` — golden corpus.

### Dev Agent Guardrails

#### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle. Ne jamais improviser de rsync/SSH manuel.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`. Cycle canonique : `main → beta → stable → Jeedom Market`.

#### Garde-fous implémentation (Option A)

- **Aucun `eq_id` codé en dur** comme logique sémantique ou de périmètre. La reconnaissance `SWITCH_*` et le multi-switch sont **génériques** (structure/capacités). C'est l'invariant central de cette story (AC#1, AC#13).
- Ne **pas** introduire ni étendre d'allowlist d'ID ; **retirer** `MULTI_DOMAIN_EQ_IDS` (migrer eq554 sur le prédicat structurel, parité testée).
- Préserver à l'identique le chemin `ENERGY_*` du `SwitchMapper` (confiance, reason_codes, device_class) et le `map()` mono-switch (back-compat).
- Une signature `SWITCH_*` pure sort en `probable` (bloquée sous `sure_only`) — **ne pas** la forcer en `sure`. La sécurité anti-débordement passe par confiance + `published_scope`, **pas** par du code ID.
- Ne pas dupliquer un état de readback en binary_sensor s'il est porté par un switch logique (anti-doublon, AC#5).
- Ne jamais utiliser les noms de commandes comme identifiants stables (toujours les IDs `cmd`). Le préfixe de nom est une **clé de regroupement** documentée, pas un identifiant.
- Ne pas contourner `published_scope` : c'est la couche périmètre opérateur et la graine de l'epic config par équipement.
- Ne pas masquer une publication partielle : un échec secondaire reste visible dans le diagnostic/traces.
- Ne pas ouvrir `number`, `select`, ni aucun type hors `PRODUCT_SCOPE`. Pas d'ouverture cosmétique (cadrage 10.4).
- Ne pas modifier les artefacts `_bmad-output/planning-artifacts/*` (sauf correction documentaire explicitement liée).

### Project Structure Notes

- Worktree/branche dédiés : `story/pe-11.3-iq-ev-pilotage` (worktree `projects/jeedom2ha-pe-11.2`, créé depuis `main` qui porte 11.1/11.1.bis/11.2/12.1/12.2).
- `sprint-status.yaml` : `pe-epic-11` passe `done` ; `11-3-iq-ev-pilotage-priorisation-solaire` passe `done` après gate terrain live PASS le 2026-06-21.
- Filename/key : `11-3-iq-ev-pilotage-priorisation-solaire`.

### References

- `_bmad-output/planning-artifacts/backlog-icebox.md` §4 — inventaire IQ EV eq583 (§4.1) + Pilotage priorisation eq628 (§4.2) (curate, dégradé en indication par le terrain).
- `_bmad-output/implementation-artifacts/10-4-cadrage-des-composites-metier-iq-ev-spa-sans-ouverture-cosmetique.md` — extension multi-switch (la prémisse `ENERGY_*` est invalidée par le terrain ; D1 généralise à `SWITCH_*`).
- `_bmad-output/planning-artifacts/epics-projection-engine.md` — §Epic 11 / Story 11.3, §Epic 12 / Story 12.2.
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-06-18-pe-11.3.md` — séquence et dépendances (12.1 + 12.2 done).
- `_bmad-output/implementation-artifacts/11-2-chauffe-eau-eq554-detail-routage.md` — patron multi-domaine (à généraliser : prédicat structurel remplace `MULTI_DOMAIN_EQ_IDS`).
- `_bmad-output/implementation-artifacts/11-1-msunpv-routeursolaire-sensors-lecture-seule.md` — patron multi-entité (API additive, diagnostic honnête).
- `_bmad-output/implementation-artifacts/12-2-streaming-valeur-switch-button-vague-2.md` — contrat de streaming switch (state_topic, ON/OFF, cohérence state ⊆ discovery).
- `resources/daemon/mapping/switch.py`, `resources/daemon/mapping/registry.py`, `resources/daemon/models/topology.py`, `resources/daemon/models/published_scope.py`, `resources/daemon/models/decide_publication.py`, `resources/daemon/transport/http_server.py`.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (create-story, dev-story Task 0, révision design Option A)

### Debug Log References

- 2026-06-19 dev-story — Task 0 Pre-flight terrain exécutée : capture read-only `jeedom2ha::getFullTopology()` sur box `192.168.1.21` (SSH+sudo OK, aucune mutation HA). Artefact : `_bmad-output/terrain-captures/11-3-topology-eq583-eq628-20260619.json`. Divergence terrain majeure → HALT/escalade.
- 2026-06-19 — Escalade résolue : décisions de design **D1–D4 prises (Option A générique)** après analyse du code (`switch.py`, `registry.py`, `topology.py`, `published_scope.py`, `decide_publication.py`, `http_server.py`). Story révisée (ACs, Tasks, Dev Notes) pour une approche **sans couplage par ID**, forward-compat avec l'epic « config par équipement à la Homebridge ». Aucun code produit, aucune mutation HA.

### Completion Notes List

- Create-story completed : story 11.3 matérialisée à partir de l'inventaire `backlog-icebox.md §4`, du cadrage 10.4, et des patrons 11.1/11.2. Dépendances 12.1 + 12.2 levées (`done`). Contrainte clé : le `SwitchMapper` à dict plat ne produit qu'un switch par eqLogic.
- Dev-story Task 0 exécutée puis **HALT escalade** : la capture terrain contredit l'inventaire curate sur 4 points (generic types `SWITCH_*` ≠ `ENERGY_*` ; eq583 = 3 switches ; regroupement par nom ; 13 eqLogics `SWITCH_*` → surface de régression).
- **2026-06-19 — Décisions de design prises (Option A « générique franc »).** D1 = reconnaissance `SWITCH_*` **globale** (pas de scope par ID) ; sécurité anti-débordement par **grading de confiance** (`SWITCH_*` pur → `probable`, bloqué sous `sure_only`) + **`published_scope` opérateur** (per-équipement, déjà existant). D2 = regroupement par préfixe de nom documenté. D3 = publier les 3 switches eq583. D4 = ignorer les commandes Rafraîchir/action. **Le gate par ID `MULTI_DOMAIN_EQ_IDS` est retiré** et remplacé par un **prédicat structurel** (eq554 migré, parité testée). Justification structurante : séparer **classification** (générique, code) et **périmètre** (donnée opérateur), pour ne pas freiner le futur epic « config par équipement à la Homebridge » — `published_scope` en est la graine. Story révisée en conséquence (ACs 1/3/4/7/8 réécrits, AC#13 forward-compat ajouté, Tasks 1–5 réalignées, Dev Notes refondues). Tasks 1–5 prêtes à coder ; gate live toujours différée au feu vert utilisateur explicite.
- **2026-06-21 — bmad-dev-story reprise.** Code/tests terminés pour Tasks 1–5 hors gate terrain : reconnaissance générique `SWITCH_*`, multi-switch structurel, registry sans `MULTI_DOMAIN_EQ_IDS`, migration eq554 par prédicat structurel, discovery/state/command topics par switch logique, streaming `SWITCH_STATE`, golden corpus eq583/eq628 et tests de généricité/non-débordement. Statut résultant : `in-progress` (gate live terrain pending feu vert utilisateur explicite).
- **2026-06-21 — bmad-code-review.** Review effectuée après suite unit daemon verte (`919 passed`) : aucun finding code Critical/High/Medium retenu. Outcome : **Changes Requested** uniquement parce que l'AC#12 gate terrain (`deploy → restart → sync` sur box `192.168.1.21`) n'a pas été exécuté. Statut résultant : `in-progress`.
- **2026-06-21 — gate terrain exécuté après feu vert utilisateur.** Déploiement depuis le worktree `projects/jeedom2ha-pe-11.2` via `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` → `Deploy complete.` ; sync OK (`total_eq=284`, `eligible=95`, `published=240`, 319 topics discovery). Preuve MQTT/HA Discovery : eq583 publie 8 entités (`sensor` #5991/#5992/#5993, `binary_sensor` #5986/#5988, `switch` #5987/#6009/#6010) sous device `jeedom2ha_583`; eq628 publie 4 switches (#5977/#5980/#5983/#6004) sous device `jeedom2ha_628`. États retenus non-unknown : eq583 `5991=0`, `5992=12109`, `5993=0`, `5986=ON`, `5988=ON`, switches `6010=OFF`, `6009=OFF`, `5987=OFF`; eq628 switches `6004=ON`, `5980=ON`, `5983=OFF`, `5977=ON`. Contrôle des 11 autres `SWITCH_*` : 9 ne deviennent pas des switches (550 exclu par pièce ; 174/235/207/234/475/206/632/631 restent `binary_sensor`), 580 et 594 sont publiés comme `switch` en confiance `Probable` car `published_scope` global les inclut et la box publie les `probable`; ils étaient déjà présents dans le périmètre opérateur et ne constituent pas une apparition inattendue liée à une allowlist cachée. Statut résultant : `done`.

### File List

- `_bmad-output/implementation-artifacts/11-3-iq-ev-pilotage-priorisation-solaire.md` (révisé — Option A)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/terrain-captures/11-3-topology-eq583-eq628-20260619.json` (capture terrain read-only Task 0)
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/mapping/binary_sensor.py`
- `resources/daemon/mapping/registry.py`
- `resources/daemon/mapping/sensor.py`
- `resources/daemon/mapping/switch.py`
- `resources/daemon/models/topology.py`
- `resources/daemon/sync/command.py`
- `resources/daemon/sync/state.py`
- `resources/daemon/transport/http_server.py`
- `resources/daemon/transport/mqtt_client.py`
- `resources/daemon/tests/fixtures/golden_corpus/expected_sync_snapshot.json`
- `resources/daemon/tests/fixtures/golden_corpus/sync_payload.json`
- `resources/daemon/tests/unit/test_story_10_6_fix_scenario_subscription.py`
- `resources/daemon/tests/unit/test_story_11_2_eq554_multi_domain.py`
- `resources/daemon/tests/unit/test_story_11_3_iq_ev_pilotage.py`
- `resources/daemon/tests/unit/test_story_8_4_golden_file.py`

### Change Log

- 2026-06-19 — Story 11.3 créée via create-story (multi-domaine eq583 + multi-switch eq583/eq628, lecture seule discovery + actionnables). Statut `backlog → ready-for-dev`.
- 2026-06-19 — dev-story Task 0 exécutée (capture terrain read-only eq583/eq628). Statut `ready-for-dev → in-progress`. Divergence terrain majeure → **HALT escalade** (Tasks 1–5 suspendues, décisions D1–D4 requises).
- 2026-06-19 — **Décisions D1–D4 prises (Option A générique). Story révisée.** Reconnaissance `SWITCH_*` générique (pas de scope ID), multi-switch structurel, retrait de l'allowlist `MULTI_DOMAIN_EQ_IDS` au profit d'un prédicat structurel (eq554 migré), sécurité par confiance `probable`/`sure_only` + `published_scope` opérateur. AC#13 forward-compat (epic « config par équipement à la Homebridge ») ajouté. Tasks 1–5 réalignées et prêtes à coder. Aucun code produit, aucune mutation HA (gate live différée).
- 2026-06-21 — bmad-dev-story reprise : implémentation code/tests terminée hors gate terrain ; suite unit daemon verte (`919 passed`) ; story maintenue `in-progress` car AC#12 terrain reste ouvert.
- 2026-06-21 — bmad-code-review : outcome **Changes Requested** pour gate terrain non exécuté ; aucun finding code bloquant.
- 2026-06-21 — gate terrain live PASS : deploy/restart/sync sur `192.168.1.21`, preuves HA/MQTT eq583/eq628 et contrôle des 11 autres `SWITCH_*` documentés. Statut `in-progress → done`.

## Senior Developer Review (AI)

### Reviewer

Codex — 2026-06-21

### Outcome

**Approved after terrain gate** : le code et les tests unitaires étaient validés ; le gate terrain AC#12 a été exécuté le 2026-06-21 et la story peut passer `done`.

### Findings

- Aucun finding code Critical/High/Medium. Les changements restent alignés avec Option A : pas d'allowlist `eq_id`, classification structurelle, `SWITCH_*` pur en `probable`, identities/topics dérivés des IDs de commandes.
- Gate terrain exécuté sur `192.168.1.21` : eq583/eq628 publiés et états non-unknown ; aucun des 11 autres `SWITCH_*` n'apparaît de façon inattendue hors gouvernance `published_scope`/`confidence_policy` de la box.

### Validation

- `python3 -m pytest -q resources/daemon/tests/unit/test_story_10_6_fix_scenario_subscription.py resources/daemon/tests/unit/test_story_11_3_iq_ev_pilotage.py` → `9 passed`.
- `python3 -m pytest -q resources/daemon/tests/unit` → `919 passed, 607 warnings`.
- `python3 -m pytest -q` → non vert dans cet environnement : tests legacy daemon startup bloqués par dépendance externe absente `ModuleNotFoundError: No module named 'jeedomdaemon'`.
