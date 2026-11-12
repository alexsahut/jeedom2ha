# Story 24.14 : Décision de publication stable entre deux synchros (scénarios, raison des équipements)

Status: review

> Analyse et story rédigées par une session cloud déléguée (2026-11-12), en lecture seule du code (`origin/main` e78f727), sans accès à la box ni à Home Assistant. Aucun nom réel, aucune IP, aucune marque (CC-48) : les constats de production ne citent que des identifiants. **Draft** : la cause est établie dans le code avec une forte confiance, mais l'origine des changements d'état côté Jeedom reste à confirmer sur la box (Task 0), et deux décisions d'Alexandre sont requises (D1, D2) avant tout `ready-for-dev`.

## Story

En tant qu'utilisateur qui pilote sa maison depuis Home Assistant,
je veux que l'ensemble des entités publiées par jeedom2ha et la raison affichée pour un équipement non publié ne dépendent pas du moment où le démon a redémarré,
afin que mes boutons, automatisations et tableaux de bord ne changent pas sans intervention de ma part, et que le diagnostic dise toujours la même chose pour le même équipement.

**Parcours : démon + plugin PHP.** Comportement standard attendu chez tout utilisateur (aucun cas propre à une installation).

## Constat de production (12/11, heures UTC du journal du démon, identifiants seulement)

**A — Boutons de scénario.** Six redémarrages du démon dans la journée, sans intervention sur Jeedom :

| Démarrage | Version | Effet observé sur le broker |
|---|---|---|
| 06:53 | 91705da | scénarios 2, 72, 147 publiés (absents juste avant) |
| 07:24 | 91705da | 129 et 39 ajoutés, 72 retiré |
| 08:38 | a6d8e95 | 2 et 39 retirés |
| 19:08:12 | e78f727 | « Unpublishing scenario » pour 39, 129, 72, 2 ; 147 publié |
| 19:09:04 | a6d8e95 (retour arrière) | 129 publié ; 39, 72, 2 dépubliés |
| 19:42:40 | e78f727 | 129 publié ; 39, 72, 2 dépubliés |

Le même code donne des ensembles différents, et deux versions différentes donnent le même ensemble : la variation ne vient pas du code déployé. Vérifié : entre 91705da et e78f727, aucune ligne ne change dans `core/`, ni dans la boucle de publication des scénarios, ni dans l'éligibilité (`git diff 91705da e78f727 -- core resources/daemon` : serrure, journal d'échec RPC, registres de types seulement).

**B — Raison de l'équipement 408.** L'export de décision (`getDecisionExport`) le donne en `not_published` / `no_generic_type_configured` juste avant un redémarrage et en `not_published` / `disabled_eqlogic` juste après. Reproduit deux fois (19:08, puis 19:42).

## Faits établis dans le code (`origin/main` e78f727)

### A. Éligibilité d'un scénario à la publication

1. **Source PHP** — `core/class/jeedom2ha.class.php:664-692` (`buildScenariosPayload`) : pour chaque scénario de `scenario::all()` (appel `:921`), le démon reçoit `id`, `name`, `is_active` (`(bool)$sc->getIsActive()`, `:682`), `homekit_exposed`, `homekit_exposed_source`. Aucun autre champ du scénario (état d'exécution, visibilité, dernière exécution, programmation, mode) n'est transmis. `scenarios_complete` (`:924`) vaut faux si un scénario n'a pas pu être lu.
2. **Modèle démon** — `resources/daemon/models/topology.py:198-205` (`JeedomScenario` : `is_active` défaut `True`) et `:302-315` (lecture du payload).
3. **Seul critère de décision : `is_active`** — `resources/daemon/transport/http_server.py:2325-2349` : `if not scenario.is_active:` → `publisher.unpublish("jeedom2ha_scenario_<id>")` (`:2326-2333`) ; sinon bouton publié sans autre condition (`:2334-2349`). `homekit_exposed` n'intervient pas dans la décision.
4. **Purge « le broker fait foi »** (21-1) — `http_server.py:2357-2381` et `discovery/publisher.py:423-466` : les topics retenus `…/button/jeedom2ha_scenario_<id>/config` dont l'id n'est pas un scénario actif sont vidés, seulement si la liste est complète (`:2362-2367`). Elle ne retire que des inactifs ou des supprimés ; elle ne peut pas publier.
5. **Journal** — `publisher.py:363-369` écrit `[DISCOVERY] Unpublishing scenario` à **chaque** synchro pour **chaque** scénario inactif, qu'il soit ou non sur le broker (vidage idempotent). Une ligne « Unpublishing » ne prouve donc pas un changement ; seul le passage d'un id de la liste des inactifs à celle des publiés (ou l'inverse) en est un.
6. **Quand la décision est prise** — uniquement à une synchro complète : démarrage du démon (`jeedom2ha.class.php:287-372`, `bootstrapRuntimeAfterDaemonStart`) et « Relire Jeedom » (`core/ajax/jeedom2ha.ajax.php:674-679`). Il n'existe ni synchro périodique ni écoute des changements de scénario (constat F7 de 20-2, repris en 21-1). Entre deux synchros, le broker garde la décision de la synchro précédente.
7. **Export** — `export/decision_export.py:388-414` : `active`, `decision` et `reason` (`scenario_button` / `scenario_inactive`) sont recalculés depuis `is_active` du dernier instantané ; cohérent avec la publication.
8. **Appui sur un bouton** — `sync/command.py:1101-1124` : un scénario absent de `scenario_publications` (donc inactif à la dernière synchro) est rejeté `unknown_runtime_entity` sans appel à Jeedom.

**Champ volatil : `isActive` du scénario Jeedom.** C'est le seul champ lu, et il est lu frais à chaque synchro complète. Dans Jeedom, il change par l'interface, mais aussi par l'action de scénario « activer / désactiver un scénario », par du code dans un bloc de scénario, ou par un plugin qui pilote des scénarios.

### B. Calcul de `disabled_eqlogic` et `no_generic_type_configured`

1. **Source PHP** — `jeedom2ha.class.php:879` : `is_enable => (bool)$eq->getIsEnable()` ; `:828` : `generic_type` de chaque commande. Seule source de l'état actif d'un équipement (aucun autre `getIsEnable` dans `core/` ni `desktop/`).
2. **Un seul calcul, ordre fixe** — `models/topology.py:412-451` (`assess_eligibility`), docstring `:415` : Exclu (`:424-427`) > Désactivé (`:429-430`, `disabled_eqlogic`) > Sans commandes (`:432-433`) > Sans type générique (`:436-449`, `no_supported_generic_type`). Un équipement désactivé ne peut **jamais** recevoir `no_supported_generic_type` sur ce chemin.
3. **Alias** — `models/evaluate_equipment.py:88-90` puis `:370-394` (chemin I1) : `no_supported_generic_type` → `no_generic_type_configured`, la raison d'éligibilité est consommée telle quelle, jamais recalculée. Même alias dans le diagnostic : `http_server.py:2611-2622` (`_CLOSED_REASON_MAP`).
4. **Mémorisation** — `http_server.py:2091-2100` (inéligibles, `make_ineligible_record`) ; `:2396-2399` : `decision_memo.equipments` est **remplacé en bloc** à chaque synchro complète. « Publier » (`:4908-4928`, `_evaluate_for_action` `:4386-4405`) ne touche pas un inéligible (retour `None`, rien mémorisé) et réutilise l'instantané du dernier sync.
5. **Export** — `http_server.py:480-508` : le document est construit depuis le mémo, jamais recalculé. `export/decision_export.py:369` (`enabled` = `eq.is_enable` de `app["topology"]`) et `:376` (`reason` = mémo). Les deux viennent du même instantané **si** la synchro est allée au bout.
6. **Fenêtre d'incohérence possible** — `http_server.py:2011` : `app["topology"]` est remplacé au **début** de la synchro, le mémo à la **fin** (`:2396-2399`). Une synchro qui lève entre les deux (`:1968-1972`, réponse d'échec) laisse un instantané neuf et un mémo ancien : l'export peut alors afficher `enabled` du nouvel instantané avec la raison de l'ancien.
7. **Figée entre deux synchros** — même déclencheurs qu'en A6 : la raison n'est réévaluée qu'au démarrage du démon ou à « Relire Jeedom ».

## Causes les plus probables

**A — confiance forte sur le mécanisme, moyenne à forte sur l'origine.** Le code ne publie un bouton de scénario que si `isActive=1` au moment de la synchro (A3), et ne relit cette valeur qu'au démarrage ou au rescan (A6). Les écarts observés sont donc des changements de `isActive` côté Jeedom **entre** les démarrages, captés au hasard des redémarrages. Le rythme (plusieurs bascules en quelques heures, dont 129 inactif à 19:08:12 puis actif à 19:09:04) désigne des activations / désactivations automatiques (action de scénario, bloc code, plugin), pas des gestes manuels. Les scénarios 2 et 72 étaient déjà relevés inactifs le 2026-10-06 (21-1, CC-44) : leur état bascule dans le temps. Hypothèses écartées par le code : dépendance à l'état d'exécution, à la visibilité, à la dernière exécution ou à la programmation (non transmis, A1) ; dépendance à la version (A et diff ci-dessus) ; purge qui publierait (A4).

**B — confiance forte que ce n'est pas un ordre différent entre deux chemins ; moyenne sur la cause exacte.** Il n'y a qu'un calcul de la raison, avec Désactivé avant Sans type générique (B2, B3). Une raison `no_generic_type_configured` dans un export pris juste avant redémarrage signifie que, lors de la synchro qui a produit ce mémo, l'équipement était lu **actif**. Deux explications compatibles :
- **B-1 (la plus probable)** : `isEnable` de l'équipement bascule dans Jeedom (action de scénario « activer / désactiver un équipement », plugin qui désactive un module injoignable…) et la raison reste figée sur la valeur lue à la synchro précédente (B4, B7). Le redémarrage ne « change » pas la raison : il la relit.
- **B-2 (secondaire)** : la synchro précédente a échoué entre `:2011` et `:2396`, laissant un export qui mêle deux instantanés (B6).

L'hypothèse « désactivé depuis longtemps, réévalué seulement au boot » n'explique pas à elle seule la reproduction : l'export pris avant le redémarrage de 19:42 vient de la synchro de 19:09:04, qui aurait alors lu l'équipement désactivé. Il faut donc que l'équipement ait été lu actif à 19:09:04 (B-1) ou que cette synchro n'ait pas abouti (B-2).

## Comportement attendu (standard)

1. **Décision de publication stable** : l'ensemble des entités publiées ne change que par une action de l'utilisateur sur son périmètre (Jeedom ou jeedom2ha), une modification de structure (ajout, suppression, type) ou une décision explicite du plugin ; jamais par un état passager lu au hasard d'un redémarrage.
2. **Même entrée, même résultat** : deux synchros successives sur le même état Jeedom donnent le même ensemble de topics de découverte, au caractère près.
3. **Raison cohérente quel que soit le chemin** : synchro au démarrage, « Relire Jeedom », « Publier », diagnostic, états agrégés et export de décision donnent la même raison pour le même équipement et le même état Jeedom, dans l'ordre documenté (Exclu > Désactivé > Sans commandes > Sans type générique).
4. **Pas de vérité périmée silencieuse** : si l'état Jeedom a changé depuis la dernière évaluation, soit la décision est réévaluée sans redémarrage, soit l'export dit sur quel instantané il repose.

## Décisions d'Alexandre (2026-11-12 21:41, relayées par ClaudeBox)

- **D1 A** : un scénario reste toujours publié en bouton ; inactif, son bouton est **grisé** (indisponible) et l'appui est refusé (`scenario_inactive`). Cette décision remplace celle de 21-1 (Q2 A, CC-44) pour les scénarios.
- **D2 A** (conséquence de D1 A, posée par ClaudeBox) : le grisé doit suivre l'état réel sans attendre de redémarrage. Il faut donc réévaluer quand `isActive`, `isEnable` ou une exclusion change (tâche périodique et empreinte).
- **D3** : hors périmètre. Un équipement désactivé reste non publié ; la Task 0 montre qu'un équipement peut basculer automatiquement par planning. Si le besoin se confirme, une autre story s'en chargera.

## Résultat de la Task 0 (ClaudeBox, 2026-11-12, lecture seule via l'agent d'exploitation)

Toutes les bascules viennent de la configuration Jeedom de l'installation : agenda, modes, action sur valeur d'une commande, autre scénario. Aucun bloc code n'appelle `setIsActive` / `setIsEnable`.
- Les scénarios 2 et 72 sont activés puis désactivés par des événements d'agenda, en semaine et en début de matinée.
- Le scénario 147 est actif sur une plage quotidienne fixée par un agenda, lui-même lié au mode « absent ».
- Le scénario 129 est activé et désactivé par un autre scénario (présence), plusieurs fois par heure.
- Le scénario 39 est activé par l'action sur valeur d'une commande de puissance ; il se désactive lui-même.
- L'équipement 408 est désactivé puis réactivé par un événement d'agenda hebdomadaire et par un mode.
- Les exports de décision confirment B-1 : le champ `enabled` de 408 vaut true, puis false, puis true selon le moment de la synchro.

Conclusion : `isActive` / `isEnable` servent ici de **planning** et non d'état « hors service ». Une décision lue seulement au démarrage dépend donc de l'heure du dernier redémarrage.

## Décisions demandées (historique de l'analyse)

- **D1 — Scénario désactivé.** La règle actuelle (21-1, Q2 A, CC-44 : « un scénario inactif n'a plus de bouton dans HA ») fait apparaître et disparaître l'entité à chaque bascule de `isActive`.
  - **A (recommandée)** : le bouton existe pour tout scénario lisible, quel que soit `isActive` ; `isActive` est porté par la **disponibilité** de l'entité (bouton « indisponible » dans HA quand le scénario est désactivé) et un appui sur un scénario désactivé est refusé par le démon avec un motif explicite, sans appel à Jeedom. L'entité, son `entity_id` et ses réglages HA ne bougent plus. Revient sur 21-1 Q2 A (le bouton ne disparaît plus) : décision explicite requise.
  - **B** : garder la règle de 21-1, mais réévaluer dès que `isActive` change (voir D2). L'état devient juste à tout instant, l'entité continue d'apparaître et de disparaître.
  - **C** : statu quo, documenter que la liste des boutons reflète l'état au dernier démarrage ou rescan.
- **D2 — Fraîcheur entre deux synchros.**
  - **A (recommandée)** : une tâche périodique du plugin PHP (cron à créer, fréquence à fixer, défaut 5 min) calcule une empreinte légère de l'état qui pilote les décisions (ids des équipements avec `isEnable`, ids des scénarios avec `isActive`, réglages d'exclusion) et lance une synchro de service (pas un rescan) seulement si l'empreinte a changé et si le démon est prêt.
  - **B** : synchro complète périodique sans empreinte (plus simple, plus coûteuse).
  - **C** : rien ; l'export indique seulement l'instant et l'instantané de la décision (AC 9) et l'utilisateur relit Jeedom.
- **D3 — Équipement désactivé** (pour mémoire, hors périmètre sauf décision contraire) : la règle « désactivé → non publié » reste. Si la Task 0 montre qu'un équipement bascule automatiquement, la même question que D1 se pose pour les équipements ; elle ferait l'objet d'une autre story.

## Critères d'acceptation

Les AC marqués **[D1 A]** ou **[D2 A]** suivent les recommandations ; ils sont réécrits si Alexandre retient une autre option.

1. **AC1 — Déterminisme.** Deux synchros successives sur un même payload produisent la même liste de topics de découverte et des charges identiques (scénarios et équipements), et le même export de décision hors horodatages.
2. **AC2 — [D1 A] Bouton stable.** Pour tout scénario lisible, la configuration `…/button/jeedom2ha_scenario_<id>/config` est publiée, que `is_active` soit vrai ou faux ; le passage actif ↔ inactif ne vide jamais ce topic et ne change ni `unique_id`, ni `default_entity_id`, ni `command_topic`.
3. **AC3 — [D1 A] Disponibilité.** La charge d'un bouton de scénario porte, en plus de la disponibilité du pont, une disponibilité propre au scénario (`availability_mode: all`) ; elle vaut `online` si le scénario est actif et `offline` sinon, est publiée retenue à chaque synchro, et n'emprunte jamais la disponibilité d'un équipement de même id (garde 21-1 C8).
4. **AC4 — [D1 A] Appui refusé.** Un appui sur le bouton d'un scénario inactif à la dernière évaluation est rejeté avec `reason_code=scenario_inactive`, une ligne `[SYNC-CMD]` au niveau INFO, et aucun appel JSON-RPC.
5. **AC5 — Purge préservée.** Un scénario supprimé de Jeedom voit son bouton retiré (21-1, AC « le broker fait foi ») ; une liste incomplète (`scenarios_complete` faux) n'entraîne aucun retrait.
6. **AC6 — Export des scénarios.** **[D1 A]** `decision=published`, `reason=scenario_button` pour tout scénario lisible ; `active` reflète `is_active` ; `entity.discovery_published` reflète la publication effective. Le contrat `schema_version` reste 1 (champs inchangés, seules les valeurs changent pour les inactifs) ou passe à 2 si un champ est retiré : à trancher à l'implémentation, documenté dans `docs/dev-decision-export.md`.
7. **AC7 — Une seule raison.** Pour un même instantané, la raison d'un équipement est identique dans : le mémo de la synchro, l'export de décision, le diagnostic (`/system/diagnostics`), les états agrégés (`/system/equipment_states`) et la réponse de « Publier ». L'ordre Exclu > Désactivé > Sans commandes > Sans type générique est documenté en un seul endroit et testé.
8. **AC8 — Instantané et mémo indissociables.** `app["topology"]`, le mémo de décision, `mappings`, `publications` et `scenario_publications` sont remplacés ensemble à la fin d'une synchro réussie ; une synchro en échec laisse l'ensemble précédent intact. Invariant vérifiable sur tout export : `enabled == false` ⇒ `reason ∈ {excluded_eqlogic, excluded_plugin, excluded_object, disabled_eqlogic}`.
9. **AC9 — Instantané daté.** L'export porte déjà `sync_at` ; il porte en plus l'origine de la synchro (`boot`, `rescan`, `service`) pour que l'on sache sur quelle lecture de Jeedom repose chaque raison (champ additif).
10. **AC10 — [D2 A] Réévaluation sans redémarrage.** Quand `isEnable` d'un équipement, `isActive` d'un scénario ou un réglage d'exclusion change dans Jeedom, une synchro de service a lieu au plus tard à l'échéance suivante de la tâche périodique ; sans changement, aucune synchro n'est lancée. Aucune synchro n'est lancée si le démon n'est pas prêt ou si une opération est en cours (verrou `action_lock` respecté, pas de 409 journalisé en erreur).
11. **AC11 — Non-régression.** Les suites `make test`, les tests PHP et le gate 20-0 restent verts ; aucun nom, aucune IP, aucune marque dans les tests, la doc ou les journaux ajoutés (CC-48).
12. **AC12 — Preuve terrain (ClaudeBox).** Sur la box, avec l'accord d'Alexandre : deux redémarrages successifs sans changement Jeedom donnent le même inventaire MQTT ; **[D1 A]** la bascule d'un scénario de test change seulement la disponibilité de son bouton ; **[D2 A]** la désactivation d'un équipement de test change sa raison dans l'export sans redémarrage.

## Tâches

- [x] **Task 0 — Confirmer la cause sur la box (ClaudeBox, lecture seule, avant tout dev).** Faite par ClaudeBox (voir « Résultat de la Task 0 »). Heures du journal du démon en UTC, journaux de scénarios en heure locale.
  - [ ] 0.1 Scénarios 2, 39, 72, 129, 147 : dans la table `scenario`, relever `isActive`, `mode`, `schedule`, `state`, `lastLaunch`, `isVisible` et `configuration` (bloc JSON, sans le recopier dans le dépôt).
  - [ ] 0.2 Trouver qui bascule `isActive` : dans `scenarioExpression`, les actions `scenario` dont les options visent ces ids avec `activate` / `deactivate` ; les blocs `code` qui appellent `setIsActive` ou `changeState` ; les plugins qui pilotent des scénarios (agenda, modes…). Lire les journaux de ces scénarios et des scénarios appelants autour de 06:53, 07:24, 08:38, 19:08, 19:09 et 19:42 UTC (lignes d'activation / désactivation).
  - [ ] 0.3 Dans le journal du démon, pour chaque démarrage : `[SCENARIO] Unpublished N scenario button(s) (x inactive, y from broker): ids=[…]`, `[SCENARIO] Scenario purge skipped`, `[SCENARIO] Failed to publish`, et dans le journal du plugin `[TOPOLOGY] Scan complet : … scénarios`. Vérifier que l'ensemble des inactifs de chaque démarrage explique exactement le tableau A.
  - [ ] 0.4 Équipement 408 : dans `eqLogic`, relever `isEnable`, `eqType_name`, `isVisible`, `configuration.updatetime`, `status` ; dans `cmd`, le nombre de commandes et leurs `generic_type` (attendu : aucun).
  - [ ] 0.5 Dans les deux exports conservés (avant / après chaque redémarrage), ligne `eq:408` : `enabled`, `reason`, `step`, et `sync_at` du document. **`enabled=true` avant** → B-1 confirmée (l'équipement était lu actif). **`enabled=false` avec `no_generic_type_configured`** → B-2 : chercher un échec de synchro (réponse d'échec, `[SYNC]`, `Runtime bootstrap failed`) entre 19:09 et 19:42.
  - [ ] 0.6 Trouver qui bascule `isEnable` de 408 : actions `equipement` (activer / désactiver) visant cet équipement dans `scenarioExpression`, comportement de son plugin, journaux autour des heures ci-dessus. Relever aussi tout « Relire Jeedom » entre 19:09 et 19:42 (journal du plugin, `scanTopology`).
  - [ ] 0.7 Consigner le résultat dans un fichier `24-14-task0-releves-<date>.md` (identifiants seulement), puis faire trancher D1, D2 (et D3 si un équipement bascule) par Alexandre.
- [x] **Task 1 — Instantané atomique (AC7, AC8, AC9).** Construire la nouvelle topologie, les décisions et le mémo dans des variables locales, les publier dans `app` en une seule étape à la fin de `_do_handle_action_sync_body` ; ajouter l'origine de la synchro à l'export (en-tête `X-Jeedom2ha-Sync-Mode` déjà présent pour le rescan, à étendre au démarrage et au service).
- [x] **Task 2 — [D1 A] Boutons de scénario stables (AC2 à AC6).** Publier tout scénario lisible ; disponibilité propre au scénario (topic dédié, retenu) via `_build_availability_fields` ; refus `scenario_inactive` dans `sync/command.py` ; export ; la purge ne retire plus que les supprimés. Mettre à jour `docs/dev-decision-export.md` et la doc utilisateur (`docs/fr_FR`) sur le comportement d'un scénario désactivé.
- [x] **Task 3 — [D2 A] Réévaluation sur changement (AC10).** Fonction PHP pure d'empreinte (testable sans le cœur), branchement dans un cron à créer (le plugin n'en déclare aucun aujourd'hui : ni méthode `cron*()` dans la classe, ni entrée dans `plugin_info/info.json`), requêtes DB minimales, appel `/action/sync` en mode service quand l'empreinte change ; empreinte gardée en `config` du plugin (pas de table).
- [x] **Task 4 — Tests (voir ci-dessous).**
- [ ] **Task 5 — Preuve terrain (AC12, ClaudeBox) après fusion et déploiement par `scripts/deploy-to-box.sh`.** À faire par ClaudeBox (hors session cloud).

## Tests à écrire

Démon (`resources/daemon/tests/unit/test_story_24_14_*.py`, données synthétiques, aucun nom réel) :
- **Déterminisme** : même payload deux fois → mêmes appels au publisher (topics et charges), même export hors horodatages (AC1).
- **[D1 A]** scénario actif puis inactif puis actif : topic de configuration jamais vidé, `unique_id` constant, disponibilité `online` → `offline` → `online` (AC2, AC3) ; charge du bouton : deux entrées de disponibilité, jamais celle d'un équipement de même id.
- **[D1 A]** appui sur un scénario inactif : `scenario_inactive`, aucun appel JSON-RPC (AC4) ; appui sur un actif inchangé.
- **Purge** : scénario supprimé retiré ; `scenarios_complete` faux → rien retiré (AC5, non-régression 21-1).
- **Matrice de raison** : toutes les combinaisons (exclusion équipement / plugin / pièce / aucune) × (`is_enable` vrai / faux) × (sans commande / avec) × (avec / sans type générique, avec unité fiable, eqType multi-capteurs) → raison attendue selon l'ordre documenté ; la même raison sort d'`assess_eligibility`, d'`evaluate_equipment`, du mémo, de l'export, du diagnostic et des états agrégés (AC7).
- **Atomicité** : une exception injectée au milieu de la synchro laisse topologie, mémo, `mappings`, `publications`, `scenario_publications` à leur valeur précédente ; invariant `enabled == false` ⇒ raison d'exclusion ou `disabled_eqlogic` vérifié sur tout export (AC8).
- **Bascule entre deux synchros** : équipement actif sans type générique (`no_generic_type_configured`) puis désactivé → après la synchro suivante, `disabled_eqlogic`, quel que soit le déclencheur (démarrage, rescan, service) (AC7, AC9).

PHP (`tests/test_php_24_14_*.php`) :
- **[D2 A]** empreinte : inchangée si rien ne change ; change si un `isEnable`, un `isActive`, un réglage d'exclusion change ; indépendante de l'ordre de lecture ; ne contient aucun nom.
- **[D2 A]** déclenchement : appel de synchro seulement sur changement, jamais si le démon n'est pas prêt ; un refus 409 (opération en cours) n'est pas une erreur et l'empreinte n'est pas mémorisée (nouvel essai à l'échéance suivante).
- `buildScenariosPayload` : inchangé (non-régression 21-1 / 24-1).

## Garde-fous

- Principe de moindre nuisance : en cas de lecture incomplète des scénarios, ne rien retirer (21-1).
- Aucun nom d'équipement, de scénario ou de pièce dans le code, les tests, la doc ou les journaux ajoutés (CC-48).
- Pas de table DB : l'empreinte vit dans la configuration du plugin.
- Garde 25.4 (lignes retirées dans `resources/daemon/`) et garde 24.2 (`desktop/js/jeedom2ha_mapping_override.js`) : déclarer toute ligne retirée dans la PR.
- Ne pas toucher l'ordre de priorité de l'éligibilité : il est déjà juste ; la story le fige par les tests.

## Dev Notes

- Fichiers concernés : `core/class/jeedom2ha.class.php` (scénarios `:664-692`, topologie `:744-937`, bootstrap `:287-372`), `core/ajax/jeedom2ha.ajax.php` (`:674-679`, `:699-706`), `resources/daemon/transport/http_server.py` (synchro `:1951-2399`, export `:480-508`, « Publier » `:4386-4405`, `:4823-4970`), `resources/daemon/discovery/publisher.py` (`:352-369`, `:423-466`, `:605-611`), `resources/daemon/models/topology.py` (`:198-210`, `:302-315`, `:412-455`), `resources/daemon/models/evaluate_equipment.py` (`:88-90`, `:370-394`), `resources/daemon/export/decision_export.py` (`:327-414`), `resources/daemon/sync/command.py` (`:1101-1124`).
- Stories liées : 10.1 (boutons de scénario), 21-1 (CC-44, purge « le broker fait foi », réserve CC-61), 24-2 (export de décision), 24-5 (scénarios exposés), 25-2 (états agrégés, invalidation à la synchro), 25-7 (« Désactivé prime » côté interface).
- HA garde dans `deleted_entities` les réglages d'une entité retirée et les lui rend si elle revient avec le même `unique_id` (constat 21-1) : c'est ce qui masque aujourd'hui une partie de l'effet des bascules, mais les automatisations qui citent le bouton échouent pendant l'absence.
- Comportement de Jeedom lors du lancement d'un scénario désactivé par `scenario::changeState` : à vérifier dans le cœur à l'implémentation (le refus côté démon, AC4, ne dépend pas de cette réponse).

## Dev Agent Record (session cloud déléguée, 2026-11-12)

Branche `story/analyse-reevaluation-au-demarrage` (PR #376), `origin/main` ecedde5 fusionné. Aucun accès box ni HA.

### Ce qui est livré

- **Task 2 — D1 A.** `transport/http_server.py` : tout scénario lisible est publié en bouton, actif ou non ; `PublicationDecision.active_or_alive` porte `is_active` ; après une configuration publiée, la disponibilité retenue `jeedom2ha/scenario_<id>/availability` (`online` / `offline`, qos 1) est publiée à chaque synchro. `discovery/publisher.py` : la charge d'un bouton de scénario porte `availability: [pont, scenario_<id>]`, `availability_mode: all`, `payload_available` / `payload_not_available` ; le topic vient de `models/availability.py` (`build_scenario_availability_topic`) et n'est jamais celui d'un équipement de même id (garde 21-1 C8 conservée : appareil et fabricant neutres). La purge « le broker fait foi » reçoit tous les scénarios lisibles et ne retire donc plus que les supprimés ; un retrait vide aussi la disponibilité retenue du scénario (aucun orphelin). Garde-fous 21-1 inchangés (liste complète, motif strict, broker déconnecté : rien). `sync/command.py` : appui sur un scénario inactif refusé `reason_code=scenario_inactive`, ligne `[SYNC-CMD]` INFO, aucun JSON-RPC. `export/decision_export.py` : `decision=published`, `reason=scenario_button` pour tout scénario lisible, `active` = `is_active`, `discovery_published` = publication effective ; **`schema_version` reste 1** (aucun champ retiré, sens des champs inchangé, seule la règle de publication change), documenté dans `docs/dev-decision-export.md`. Doc utilisateur `docs/fr_FR/index.md` et `changelog_beta.md`.
- **Task 3 — D2 A.** `core/php/jeedom2ha_reevaluation.php` (fonctions pures, sans cœur) : `jeedom2ha_decision_fingerprint()` (SHA-256 de `id:isEnable:source d'exclusion effective` par équipement, `id:isActive` par scénario, plugins et pièces exclus triés ; aucun nom ; indépendante de l'ordre ; équipements du plugin ignorés) et `jeedom2ha_reevaluation_tick()` (empreinte lue avant la topologie ; inchangée → aucun appel au démon ; démon non prêt → rien ; sinon synchro de service ; `action_in_progress` (409) → INFO, empreinte non mémorisée ; succès → empreinte mémorisée puis listeners réalignés). `core/class/jeedom2ha.class.php` : `cron5()` (Jeedom 4.5 détecte la méthode `cron5` de la classe du plugin ; la fonctionnalité apparaît dans la page du plugin et peut y être désactivée ; aucune clé `info.json` n'existe pour cela, donc `info.json` n'est pas modifié), `reevaluateDecisionsIfChanged()`, `readDecisionFingerprint()` (deux requêtes : `SELECT id, isEnable, eqType_name, object_id, configuration FROM eqLogic` et `SELECT id, isActive FROM scenario`, aucune colonne de nom), empreinte gardée en configuration du plugin (`decisionFingerprint`, pas de table). Le démarrage du démon mémorise l'empreinte lue avant sa topologie quand sa synchro réussit : le cron ne relance rien tant que l'état ne change pas.
- **Task 1 — AC7, AC8, AC9.** `app["topology"]`, `app["eligibility"]`, le nettoyage de `mappings` / `publications`, `scenario_publications` et le mémo sont remplacés ensemble en fin de `_do_handle_action_sync_body`, après tout ce qui peut lever (dont la purge des scénarios) : une synchro en échec laisse l'ensemble précédent intact (les effets MQTT déjà émis restent, idempotents, et sont rejoués à la synchro suivante). Origine de la synchro (`boot`, `rescan`, `service`, défaut `service`) lue dans `X-Jeedom2ha-Sync-Mode`, mémorisée et exportée en `sync_origin` (champ additif) ; la synchro de démarrage envoie désormais `boot`. AC7 : l'ordre Exclu > Désactivé > Sans commandes > Sans type générique n'est pas touché ; il est figé par une matrice de tests sur toutes les vues.

### Tests

- Démon : `resources/daemon/tests/unit/test_story_24_14_decision_stable.py` (15 tests : déterminisme AC1, bascule actif/inactif AC2-AC3, charge à deux disponibilités sans homonyme, appui refusé sans RPC AC4, purge des seuls supprimés et liste incomplète AC5, export AC6, matrice de raison sur `assess_eligibility`, mémo, export, diagnostic, états agrégés AC7, bascule entre deux synchros pour chaque origine AC7/AC9, en-tête absent ou inconnu, échec injecté au milieu de la synchro AC8, invariant `enabled == false` AC8).
- PHP : `tests/test_php_story_24_14_reevaluation.php` (44 vérifications, sans cœur Jeedom : empreinte, pas de la tâche, 409, câblage du cron, `buildScenariosPayload` identique à `origin/main`).

### Tests et listes figées mis à jour (D1 A), justification

- `tests/unit/test_story_21_1_cc44_scenario_lifecycle.py` : la règle 21-1 Q2 A (« un inactif n'a plus de bouton ») est remplacée par D1 A. Réécrits : retrait d'un inactif → bouton conservé et grisé ; réactivation → bascule sans vidage, identité constante ; référence figée de la charge du bouton → pont + disponibilité propre (`availability_mode: all`), seul écart admis ; homonyme → toujours jamais la disponibilité ni l'appareil de l'équipement ; les attentes de purge comptent aussi le vidage de la disponibilité du supprimé ; le test d'homonymie de purge utilise un scénario supprimé. **Aucun garde-fou de sécurité affaibli** : liste incomplète, section absente ou mal formée, entrée illisible, motif strict des topics, broker déconnecté, absence de report par `eq_id` et collecte en échec restent testés à l'identique.
- `tests/unit/test_story_24_2_decision_export.py` : la ligne du scénario inactif attend `published` / `scenario_button` / `discovery_published: true`.
- `tests/unit/test_story_25_4_non_regression.node.test.js` : liste `REPLACED_BY_24_14` (« fichier::ligne ») des lignes remplacées dans `resources/daemon/` et `core/class/` par rapport à `origin/main`.
- Golden 8.4 : inchangé (le corpus doré ne contient aucun scénario). `desktop/js/jeedom2ha_mapping_override.js` : non modifié (garde 24.2).

### Points ouverts

- Preuve terrain AC12 (Task 5) à faire par ClaudeBox après fusion et déploiement.
- Dans le diagnostic, `traceability.decision_trace.reason_code` nomme `excluded` pour toute exclusion (le `reason_code` du diagnostic, l'export et les états agrégés portent la source exacte) : vocabulaire de trace antérieur, laissé tel quel et documenté par le test AC7.
- Ce qui reste hors empreinte, donc toujours appliqué au prochain démarrage ou « Relire Jeedom » seulement : périmètre publié (« Toujours » / « Jamais », appliqué par l'interface), types génériques, ajout ou suppression de commandes, renommages, exemption HomeKit d'une pièce exclue (24.4).
- D3 (équipement désactivé publié grisé) reste hors périmètre, comme décidé.

## Journal

- 2026-11-12 — Analyse et story en draft par une session cloud déléguée (lecture seule du code, aucun accès à la box). Task 0 et décisions D1, D2 à faire avant `ready-for-dev`.
- 2026-11-12 21:41 — Task 0 faite par ClaudeBox ; décisions d'Alexandre D1 A (toujours publié, grisé si inactif) et D2 A ; story `ready-for-dev`.
- 2026-11-12 — Tasks 1 à 4 livrées par une session cloud déléguée (PR #376) ; story en `review`. Reste la preuve terrain (Task 5, ClaudeBox).
