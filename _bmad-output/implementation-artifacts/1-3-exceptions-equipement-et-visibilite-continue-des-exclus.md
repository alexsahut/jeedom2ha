# Story 1.3: Exceptions équipement et visibilité continue des exclus

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur Jeedom,  
je veux voir les exceptions locales et les équipements exclus sans disparition silencieuse,  
afin de relire précisément pourquoi un équipement est ou n'est pas dans mon scope.

## Story Context

- Cycle actif obligatoire: **Post-MVP Phase 1 - V1.1 Pilotable**
- Dépendances autorisées: Story 1.1, Story 1.2
- Statut des dépendances: Story 1.1 = done, Story 1.2 = done
- Story productrice backend de référence: `1-1-resolver-canonique-du-perimetre-publie`
- Story productrice UI de référence: `1-2-vue-globale-et-synthese-par-piece-sans-recalcul-frontend`
- Positionnement dans l'epic: Story 1.3 est la suivante dans Epic 1
- Réduction de dette support: permet de reconstruire la source de décision sans inspection de logs bruts
- Rappel de workflow: aucun agent ne doit deviner la source de vérité; la stratégie de test V1.1 fait partie des sources actives

## Acceptance Criteria

1. **AC1 - Visibilité continue d'un équipement exclu**  
   **Given** un équipement exclu volontairement  
   **When** l'utilisateur consulte la pièce correspondante  
   **Then** l'équipement reste visible dans la console  
   **And** son état de décision est affiché explicitement

2. **AC2 - Source lisible pour un héritage de pièce**  
   **Given** un équipement qui hérite de la règle de sa pièce  
   **When** l'utilisateur consulte son détail  
   **Then** la source de décision affichée est `Hérite de la pièce`

3. **AC3 - Source lisible pour une dérogation locale**  
   **Given** un équipement qui déroge à la règle de sa pièce  
   **When** l'utilisateur consulte son détail  
   **Then** la source de décision affichée est `Exception locale`

## Tasks / Subtasks

- [x] Task 1 - Réutiliser le contrat backend canonique existant pour le détail équipement (AC: 1, 2, 3)
  - [x] 1.1 Réutiliser `published_scope` déjà produit par Story 1.1 et déjà relayé par Story 1.2 comme source unique de lecture pour le niveau équipement
  - [x] 1.2 Lire les champs équipement déjà prévus par le contrat backend (`eq_id`, `effective_state`, `decision_source`, `is_exception`, `has_pending_home_assistant_changes`) sans créer de nouveau moteur métier ni de contrat parallèle
  - [x] 1.3 Si le relai UI existant ne transmet pas encore un champ déjà présent côté backend, n'ajouter qu'un passage technique minimal en lecture seule, sans changer la sémantique du contrat ni redériver les décisions depuis des exclusions legacy
  - [x] 1.4 En absence de contrat avant premier sync, conserver l'état explicite de prérequis déjà introduit par Story 1.2, sans inventer de liste équipement locale ni de fallback produit

- [x] Task 2 - Afficher la visibilité continue des équipements exclus au niveau pièce (AC: 1)
  - [x] 2.1 Étendre la vue par pièce pour lister aussi les équipements résolus en `effective_state = exclude`, au lieu de les filtrer ou de les faire disparaître
  - [x] 2.2 Afficher pour chaque équipement au minimum son état de décision explicite (`include` / `exclude`) à partir du contrat backend existant
  - [x] 2.3 Garantir que le rattachement d'un équipement à sa pièce repose uniquement sur la structure de contrat déjà fournie par le backend, pas sur un recalcul frontend de hiérarchie ou d'héritage

- [x] Task 3 - Rendre lisible la source de décision au niveau équipement sans recalcul frontend (AC: 2, 3)
  - [x] 3.1 Traduire les codes backend existants de `decision_source` et `is_exception` en libellés UI purement présentationnels, sans redécider l'état effectif de l'équipement
  - [x] 3.1bis Verrou de portée visible: les seuls outputs UI nouveaux obligatoires de Story 1.3 sont l'état effectif visible de l'équipement dérivé directement de `effective_state`, le libellé `Hérite de la pièce` et le libellé `Exception locale`
  - [x] 3.2 Afficher obligatoirement `Hérite de la pièce` quand le backend indique un héritage depuis la pièce
  - [x] 3.3 Afficher obligatoirement `Exception locale` quand le backend indique une dérogation locale (`decision_source = exception_equipement` et `is_exception = true`)
  - [x] 3.4 Tout autre enrichissement visible de taxonomie, raison ou action recommandée reste hors scope de Story 1.3, sauf stricte projection présentationnelle déjà existante et sans nouvelle sémantique produit

- [x] Task 4 - Préserver la séparation backend-first avec les synthèses existantes et sans dérive vers Story 1.4 (AC: 1, 2, 3)
  - [x] 4.1 Rafraîchir le détail équipement uniquement à partir du payload backend renvoyé après synchronisation ou refresh, sans delta local optimiste
  - [x] 4.2 Garder intacts le résumé global et les synthèses par pièce déjà livrés par Story 1.2; Story 1.3 ajoute le détail explicatif équipement, elle ne redéfinit pas les compteurs
  - [x] 4.3 Ne pas introduire dans cette story de nouveau parcours orienté `changements à appliquer à Home Assistant`, ni de lecture utilisateur nouvelle autour de `has_pending_home_assistant_changes`
  - [x] 4.4 Ne pas confondre affichage console du périmètre publié et opérations effectives Home Assistant

- [x] Task 5 - Ajouter les preuves de test V1.1 ciblées sur l'explicabilité équipement (AC: 1, 2, 3)
  - [x] 5.1 Étendre les tests de contrat et d'intégration backend-relai pour prouver que les équipements exclus restent présents dans le `published_scope` consommé par la console, avec stabilité des champs `eq_id`, `effective_state`, `decision_source`, `is_exception`
  - [x] 5.2 Ajouter des tests UI ciblés sur un cas mixte montrant: équipement exclu toujours visible, libellé `Hérite de la pièce`, libellé `Exception locale`, et absence de recalcul local lors d'un refresh
  - [x] 5.3 Prouver en non-régression que Story 1.3 n'introduit ni moteur de décision frontend, ni confusion avec Story 1.4 sur les changements en attente d'application HA

## Dev Notes

### Contexte actif et contraintes de cadrage

- Le cycle actif de référence est **Post-MVP Phase 1 - V1.1 Pilotable**
- Les sources actives de vérité pour cette story sont:
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Contexte secondaire autorisé et utilisé:
  - `_bmad-output/implementation-artifacts/1-1-resolver-canonique-du-perimetre-publie.md`
  - `_bmad-output/implementation-artifacts/1-2-vue-globale-et-synthese-par-piece-sans-recalcul-frontend.md`
- Aucun agent ne doit deviner la source de vérité
- La stratégie de test V1.1 est une source active, pas un contexte secondaire
- Ne pas rouvrir le cadrage produit, ne pas modifier les epics, ne pas réinterpréter les invariants déjà figés dans le breakdown validé
- Story 1.1 est terminée
- Story 1.2 est terminée
- Story 1.3 est la prochaine story à exécuter dans Epic 1

### Invariants non renégociables à reprendre tels quels

- Le modèle canonique du périmètre publié reste `global -> pièce -> équipement`
- Les états supportés restent `inherit / include / exclude`
- La résolution suit explicitement `équipement > pièce > global`
- Le backend reste l'unique source de calcul de la décision effective et de ses champs d'explicabilité au niveau équipement
- La décision locale de périmètre et l'application effective à Home Assistant restent deux concepts distincts
- La Story 1.3 ne crée pas un nouveau moteur métier: elle exploite le contrat backend existant et ses champs déjà prévus pour l'explicabilité équipement
- Les équipements exclus ne doivent pas disparaître du contrat backend ni de la console simplement parce qu'ils sont hors périmètre voulu
- Aucun calcul de `effective_state`, `decision_source`, `is_exception` ou `has_pending_home_assistant_changes` ne doit être introduit dans `desktop/js/jeedom2ha.js`
- Les frontières hors scope V1.1 restent gelées: pas d'extension fonctionnelle, pas de preview complète, pas de remédiation guidée avancée, pas de santé avancée, pas d'alignement Homebridge

### Dev Agent Guardrails

- Cette story est strictement bornée à l'explicabilité visible au niveau équipement et à la visibilité continue des exclus dans la console
- Cette story consomme le contrat backend canonique de Story 1.1 et le chaînage UI déjà introduit par Story 1.2; elle ne doit pas recréer de contrat concurrent
- Le niveau pièce reste le point d'entrée principal; le niveau équipement ajoute le détail explicatif sans transformer la vue par pièce en unique source de vérité
- La distinction lisible attendue porte sur la règle héritée, l'exclusion visible et l'exception locale; elle doit provenir des champs backend existants, pas d'heuristiques frontend
- Les seuls outputs UI nouveaux obligatoires de Story 1.3 sont:
  - l'état effectif visible de l'équipement, dérivé directement de `effective_state`
  - le libellé `Hérite de la pièce`
  - le libellé `Exception locale`
- Tout autre enrichissement visible de taxonomie, raison principale ou action recommandée reste hors scope 1.3, sauf stricte projection présentationnelle déjà existante et sans nouvelle sémantique produit
- `has_pending_home_assistant_changes` est déjà présent dans le contrat, mais Story 1.3 ne doit pas l'utiliser pour introduire une UX orientée "changements à appliquer à Home Assistant"; ce sujet appartient à Story 1.4
- Ne pas faire dériver Story 1.3 vers le moteur général `statut / raison / action recommandée` de l'Epic 3
- Ne pas confondre affichage console du périmètre publié et opérations effectives Home Assistant
- Toute logique de présentation ajoutée côté JS/PHP doit rester pure, déterministe et testée: traduction de codes backend, ordonnancement ou affichage, aucun recalcul métier

### Contrat backend à consommer pour Story 1.3

Story 1.1 a déjà préparé un mini-contrat backend consommable par les stories suivantes. Story 1.3 doit s'appuyer explicitement sur ce contrat, sans en redéfinir la source de vérité.

- Niveau `global`
  - `counts`: agrégats déterministes issus du resolver backend pour la synthèse globale
  - `has_pending_home_assistant_changes`: présent dans le contrat, mais hors portée UX de Story 1.3
- Niveau `piece`
  - `object_id`: identifiant stable de la pièce / objet Jeedom
  - `object_name`: libellé de la pièce / objet Jeedom
  - `counts`: agrégats déterministes de la pièce issus du resolver backend
  - `has_pending_home_assistant_changes`: présent dans le contrat, mais hors portée UX de Story 1.3
- Niveau `equipement`
  - `eq_id`: identifiant stable de l'équipement Jeedom
  - `effective_state`: décision effective résolue pour l'équipement; c'est la source directe de l'état effectif visible `include / exclude`
  - `decision_source`: code backend stable indiquant l'origine de la décision effective; il permet au minimum de distinguer héritage depuis le global, héritage depuis la pièce, règle équipement explicite et `exception_equipement`
  - `is_exception`: booléen backend permettant à l'UI d'indiquer une exception locale sans recalcul métier
  - `has_pending_home_assistant_changes`: booléen backend déjà présent mais hors périmètre UX de cette story

Notes de contrat:

- Story 1.3 lit l'explicabilité équipement depuis le contrat `published_scope` existant; elle ne redéfinit ni son schéma ni ses règles de précédence
- L'imbrication exacte du payload peut rester celle déjà mise en place par Story 1.1 et Story 1.2; le frontend consomme la structure fournie par le backend, il ne la réinvente pas
- La visibilité continue des exclus est déjà une exigence préparée par Story 1.1: si `effective_state = exclude`, l'équipement doit rester lisible dans la console
- La traduction UI des codes backend doit rester une projection directe de la sémantique déjà figée par le backend
- Les seuls outputs UI nouveaux obligatoires sont l'état effectif visible dérivé de `effective_state`, `Hérite de la pièce` et `Exception locale`
- Toute taxonomie visible plus riche (`statut`, `raison principale`, `action recommandée`) reste hors scope Story 1.3, sauf stricte projection présentationnelle déjà existante et sans nouvelle sémantique produit
- Story 1.4 réutilisera plus tard `has_pending_home_assistant_changes`; Story 1.3 ne doit ni le promouvoir ni le masquer conceptuellement

### Previous Story Intelligence

- Story 1.1 a livré le resolver backend canonique `published_scope` et a figé les champs équipement `eq_id`, `effective_state`, `decision_source`, `is_exception`, `has_pending_home_assistant_changes`
- Story 1.1 a explicitement interdit de supprimer les équipements hors périmètre du contrat backend, précisément pour rendre possible la Story 1.3
- Story 1.1 a fermé le drift legacy `excludedObjects` et a conservé la compatibilité technique historique comme fallback secondaire testé, sans en faire la vérité produit V1.1
- Story 1.2 a déjà branché la console sur le contrat `published_scope` via un relai PHP/AJAX en lecture stricte, avec état explicite avant premier sync
- Story 1.2 a déjà verrouillé qu'aucun compteur ni aucune décision métier ne doivent être recalculés dans le frontend
- Story 1.2 a explicitement borné 1.3: pas de changement en attente HA, pas d'opération HA, pas de confusion entre synthèse de périmètre et application effective
- Les derniers commits du dépôt confirment la séquence récente à prolonger, pas à réinventer:
  - `feat(story-1.1): add canonical published scope resolver`
  - `fix(story-1.1): close legacy excludedObjects published_scope drift`
  - `feat(story-1.2): add backend-driven global and room scope summaries`

### Implementation hints (non-authoritative)

- Les points ci-dessous sont des indices techniques issus de l'état actuel du plugin. Ils n'ont pas autorité et ne remplacent pas les sources documentaires actives du cycle V1.1 Pilotable.
- La chaîne actuelle expose déjà `published_scope` de bout en bout:
  - `resources/daemon/models/published_scope.py`
  - `resources/daemon/transport/http_server.py`
  - `core/class/jeedom2ha.class.php` via `getPublishedScopeForConsole()`
  - `core/ajax/jeedom2ha.ajax.php`
  - `desktop/php/jeedom2ha.php`
  - `desktop/js/jeedom2ha.js`
  - `desktop/js/jeedom2ha_scope_summary.js`
- Le relai actuel renvoie le contrat backend tel quel; Story 1.3 doit de préférence prolonger ce flux de lecture au lieu d'ouvrir un second endpoint ou un second modèle de données
- Si un présentateur dédié au détail équipement devient nécessaire, le garder séparé et pur, dans l'esprit de `desktop/js/jeedom2ha_scope_summary.js`, afin de faciliter des tests JS ciblés
- Les tests déjà en place autour du contrat et du relai constituent la base naturelle à étendre:
  - `tests/unit/test_published_scope.py`
  - `tests/unit/test_published_scope_http.py`
  - `tests/test_php_published_scope_relay.php`
  - `tests/unit/test_scope_summary_presenter.node.test.js`

### Dependencies and Sequencing

- Dépendances autorisées: Story 1.1, Story 1.2
- Dépendances en avant: interdites
- Cette story reste strictement dans le périmètre Epic 1 et ne dépend pas des Epics 2, 3 ou 4 pour fonctionner nominalement
- Story 1.3 prépare la lisibilité nécessaire avant Story 1.4, mais sans implémenter les changements en attente d'application HA

### Risks / Points de vigilance

- Filtrer ou masquer les équipements exclus dans la vue par pièce, ce qui recréerait l'opacité support explicitement rejetée par l'epic
- Recalculer en JS la source de décision ou l'état effectif au lieu de lire `decision_source`, `is_exception` et `effective_state`
- Lire directement des exclusions legacy ou des structures parallèles au lieu de consommer `published_scope`
- Faire glisser Story 1.3 vers une UX de pending changes, qui appartient à Story 1.4
- Faire glisser Story 1.3 vers le moteur général de statuts, raisons lisibles ou actions recommandées, qui appartient à l'Epic 3
- Confondre une règle équipement explicite cohérente avec la pièce et une vraie `exception_equipement`
- Multiplier les transformations UI au point de rendre illisible la frontière entre présentation et logique métier

### Testing Requirements

- Invariants V1.1 explicitement touchés par cette story:
  - modèle canonique `global -> pièce -> équipement`
  - précédence `équipement > pièce > global`
  - backend source unique de la décision effective et de son explicabilité visible
  - séparation entre périmètre local décidé et application effective à Home Assistant
  - absence de recalcul métier frontend
- Contrats MVP explicitement à préserver comme socle de non-régression:
  - extraction topologique et mapping qui alimentent le contrat canonique
  - exclusions, diagnostic, rescan et stabilité des identifiants déjà couverts par le socle existant
  - contrats existants de publication MQTT Discovery et de cycle de vie, qui ne doivent pas régresser du seul fait de l'exposition UI du détail équipement
  - règle produit conservée: mieux vaut ne pas publier que publier faux
- Tests unitaires obligatoires:
  - si un helper ou présentateur JS/PHP est ajouté, prouver qu'il traduit les champs backend en labels visibles sans recalcul métier
  - couvrir explicitement la visibilité d'un équipement exclu, le libellé `Hérite de la pièce` et le libellé `Exception locale`
  - prouver qu'aucun nouveau libellé visible de taxonomie, raison principale ou action recommandée n'est introduit par Story 1.3
- Tests d'intégration backend et relai obligatoires:
  - maintenir ou étendre la couverture du contrat `published_scope` utilisé par la console
  - prouver que le relai UI conserve les entrées équipement exclues au lieu de les tronquer
  - prouver qu'un refresh après nouveau sync remplace le détail équipement par les nouvelles données backend, sans delta local
- Tests de contrat et de non-régression obligatoires:
  - stabilité des champs équipement consommés par l'UI: `eq_id`, `effective_state`, `decision_source`, `is_exception`
  - non-régression des preuves Story 1.1 et Story 1.2 sur `published_scope` et son relai
  - preuve qu'aucune logique de décision, d'agrégat ou de pending changes n'est déplacée du backend vers le frontend
- Tests UI cibles:
  - requis, car la story modifie un contrat visible critique au niveau équipement
  - vérifier un cas mixte avec au moins un équipement hérité de la pièce, un équipement exclu visible, et une exception locale
  - vérifier qu'un refresh remplace le rendu depuis le backend recalculé
  - vérifier que l'UI ne présente pas ce détail comme une opération Home Assistant déjà effectuée
- Pas de campagne E2E exhaustive requise par défaut pour cette story

### Project Structure Notes

- Alignement avec la structure projet existante:
  - backend canonique dans `resources/daemon/models/` et `resources/daemon/transport/`
  - relai Jeedom côté `core/class/` et `core/ajax/`
  - rendu console côté `desktop/php/` et `desktop/js/`
- Points d'ancrage probables:
  - `resources/daemon/models/published_scope.py`
  - `resources/daemon/transport/http_server.py`
  - `core/class/jeedom2ha.class.php`
  - `core/ajax/jeedom2ha.ajax.php`
  - `desktop/php/jeedom2ha.php`
  - `desktop/js/jeedom2ha.js`
  - `desktop/js/jeedom2ha_scope_summary.js`
  - `tests/unit/test_published_scope_http.py`
  - `tests/test_php_published_scope_relay.php`
  - `tests/unit/test_scope_summary_presenter.node.test.js`
- Fichier probable à créer si le détail équipement doit rester proprement isolé du résumé Story 1.2:
  - `desktop/js/jeedom2ha_scope_equipment_details.js` (ou nom équivalent clairement borné au rendu équipement)
- Fichiers à ne pas transformer en moteur métier V1.1:
  - `desktop/js/jeedom2ha.js`
  - `desktop/php/jeedom2ha.php`

### References

- Sources actives de vérité:
  - `_bmad-output/planning-artifacts/active-cycle-manifest.md`
  - `_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md`
  - `_bmad-output/implementation-artifacts/sprint-status.yaml`
- Contexte secondaire autorisé:
  - `_bmad-output/implementation-artifacts/1-1-resolver-canonique-du-perimetre-publie.md`
  - `_bmad-output/implementation-artifacts/1-2-vue-globale-et-synthese-par-piece-sans-recalcul-frontend.md`
- Points d'ancrage codebase utilisés comme contexte d'implémentation secondaire:
  - `resources/daemon/models/published_scope.py`
  - `resources/daemon/transport/http_server.py`
  - `core/class/jeedom2ha.class.php`
  - `core/ajax/jeedom2ha.ajax.php`
  - `desktop/php/jeedom2ha.php`
  - `desktop/js/jeedom2ha.js`
  - `desktop/js/jeedom2ha_scope_summary.js`
  - `tests/unit/test_published_scope_http.py`
  - `tests/test_php_published_scope_relay.php`
  - `tests/unit/test_scope_summary_presenter.node.test.js`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Story context generated from active V1.1 artifacts plus authorized Story 1.1 / Story 1.2 context
- `git log --oneline -5` used only to confirm the immediate implementation sequence Story 1.1 -> Story 1.2
- Worktree dédié créé pour la story: `/tmp/jeedom2ha-story-1-3-equipment-exceptions` sur `codex/story-1-3-equipment-exceptions`
- Tests exécutés: `node --test tests/unit/test_scope_summary_presenter.node.test.js`
- Tests exécutés: `python3 -m pytest tests/unit/test_published_scope.py tests/unit/test_published_scope_http.py`
- Tests exécutés: `python3 -m pytest`
- Tentative de test relai PHP: `php tests/test_php_published_scope_relay.php` impossible localement (`php: command not found`)

### Completion Notes List

- Détail équipement ajouté dans la synthèse `published_scope` existante, sans nouveau contrat ni recalcul frontend
- Les équipements `effective_state = exclude` restent visibles dans chaque pièce avec leur état effectif explicite
- Les seuls libellés d'explicabilité ajoutés sont `Hérite de la pièce` et `Exception locale`, dérivés directement du backend
- Les synthèses globales et par pièce de Story 1.2 sont conservées, le refresh remplace entièrement le rendu avec le payload backend le plus récent
- Couverture de test étendue sur le présentateur UI, la stabilité du contrat backend et le relai PHP prévu pour la console
- Régression Python complète verte; vérification PHP non exécutable dans cet environnement faute de binaire `php`

### File List

- `_bmad-output/implementation-artifacts/1-3-exceptions-equipement-et-visibilite-continue-des-exclus.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `desktop/js/jeedom2ha_scope_summary.js`
- `tests/test_php_published_scope_relay.php`
- `tests/unit/test_published_scope_http.py`
- `tests/unit/test_scope_summary_presenter.node.test.js`

## Change Log

- 2026-03-22: ajout du détail équipement backend-first dans la vue par pièce, avec visibilité continue des exclus et libellés limités à `Hérite de la pièce` / `Exception locale`
- 2026-03-22: extension des preuves Story 1.3 sur le présentateur UI, la stabilité du contrat `published_scope` et le relai PHP consommé par la console
