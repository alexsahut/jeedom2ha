# Story 20.1 : Surface unique pièce → équipement → commande

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur du plugin (persona « Sébastien », modèle Homebridge),
je veux une seule surface pièce → équipement → commande, complète (équipements désactivés et sans pièce compris) et fidèle à l'état réel de publication,
afin de voir pièce par pièce ce qui est publié, exclu, désactivé ou à corriger, et de régler le type HA d'une commande sans passer par une autre vue.

**Parcours : complet.** Story d'interface : gate 20-0, déploiement standard, preuve terrain, puis `ready-for-UX-validation` avant `done`.

## Contexte et périmètre

- La surface de 16-8 (cartes de pièces, modale par pièce, accordéon des équipements, table des commandes) devient la **surface unique** d'édition par pièce. Elle reste au modèle Homebridge, validé à la validation UX de 16-8 (Q1).
- 20-1 la complète : pièce « Sans pièce », équipements désactivés (ferme CC-25) dans un état neutre, sélecteur de type inactif là où il n'a aucun effet, bloc « Gestion » d'un seul tenant.
- Hors périmètre :
  - compteurs par pièce et remplacement de la synthèse « Parc global » : décidés en 20-3, qui la supprime (Q3) ;
  - suppression de la synthèse « Parc global » et de la modale diagnostic : 20-3 ;
  - exclusion et forçage : 20-2 ; rescan : 20-4.
- Les états par commande viennent exclusivement de `evaluate_equipment()`, via l'arbre renvoyé par le démon (`GET /system/mapping_overrides/{eq_id}`). L'interface ne recalcule aucune décision : elle classe seulement l'affichage selon `publication_reason`, comme en 16-8.

## Décisions UX (2026-10-05)

Décidées par Alex le 2026-10-05 à 10:43 (« 1A 2A 3C 4A »), sur recommandation de ClaudeBox ; voir « Journal des décisions ».

- **Q1 — Forme : modèle Homebridge conservé** (cartes de pièces, puis modale par pièce).
- **Q2 — Sélecteur de type d'une commande exclue, non couverte ou désactivée : affiché, désactivé, avec la raison en info-bulle.**
- **Q3 — Pas de compteurs par pièce en 20-1.** « Parc global » reste affiché jusqu'à 20-3, qui décidera de son remplacement. Faits à reprendre en 20-3 : la lecture de « Parc global » (`getPublishedScopeForConsole`) charge aussi le diagnostic de tout le parc (`/system/diagnostics`) ; ses compteurs (contrat 4D) comptent des équipements, pas des commandes, et ne comptent pas les exclusions manuelles comme « exclues ».
- **Q4 — Équipement désactivé : à sa place dans l'ordre natif, grisé, état neutre « désactivé », jamais compté bloquant, sans ancre, sélecteur désactivé.**

## Acceptance Criteria

**AC1 — Surface unique d'édition par pièce**

**Given** la page principale du plugin
**When** l'utilisateur consulte le mapping HA
**Then** une seule surface d'édition par pièce existe : cartes de pièces, modale de la pièce, accordéon des équipements, table des commandes (comportement de 16-8 conservé)
**And** la synthèse « Parc global » et la modale diagnostic restent présentes et inchangées jusqu'à 20-3.

**AC2 — Bloc « Gestion » d'un seul tenant**

**Given** la page principale
**When** elle s'affiche
**Then** les actions « Ajouter », « Configuration » et « Diagnostic » sont rendues directement sous le titre « Gestion », avant le bandeau de santé du bridge
**And** la surface par pièce n'est plus suivie de ces actions
**And** le bloc garde sa classe `eqLogicThumbnailContainer` et les attributs `eqLogicAction` / `data-action` dont dépend le cœur Jeedom.

**AC3 — Pièce « Sans pièce »**

**Given** des équipements sans pièce côté Jeedom (objet nul ou `-1`), hors type `jeedom2ha`
**When** la page s'affiche
**Then** une carte « Sans pièce » apparaît en dernière position, avec l'identifiant de pièce `0` (convention du démon pour « aucune pièce »), et le même comportement qu'une pièce
**And** les équipements d'objet `-1` y sont regroupés avec ceux d'objet nul
**And** la carte n'apparaît pas s'il n'y a aucun équipement sans pièce.

**AC4 — Équipements désactivés inclus, état neutre (Q4, ferme CC-25)**

**Given** une pièce qui contient des équipements désactivés dans Jeedom
**When** la page s'affiche puis que l'utilisateur ouvre la pièce
**Then** le compte d'équipements de la carte les inclut, et ils apparaissent dans l'ordre natif, grisés (`j2ha-eq-disabled`), avec la mention « désactivé dans Jeedom »
**And** leur arbre est lu comme celui des autres (AC5)
**And** une commande dont `publication_reason` vaut `disabled_eqlogic` prend un état neutre « désactivée » (classe dédiée, gris, icône Font Awesome 5), avec le libellé « Ne sera pas publié — équipement désactivé dans Jeedom »
**And** cet état n'est jamais compté prêt ni bloquant et ne reçoit jamais l'ancre
**And** un équipement sans commande prête ni bloquante, avec au moins une commande désactivée, affiche le badge neutre « Désactivé dans Jeedom : ne sera pas publié dans Home Assistant. »
**And** si un équipement a à la fois des commandes exclues et désactivées, et aucune prête ni bloquante, le badge « Exclu » l'emporte.

**AC5 — Diagnostic borné (AC5 amendé de 16-8, inchangé)**

**Given** aucune pièce ouverte
**When** la page s'affiche
**Then** aucun `getMappingOverrides` n'est lu
**When** l'utilisateur ouvre une pièce
**Then** l'arbre de mapping est lu pour les seuls équipements de cette pièce.

**AC6 — États par commande, sans recalcul**

**Given** l'arbre de mapping d'un équipement
**When** ses commandes sont rendues
**Then** chaque cellule a exactement l'un des cinq états : prête, bloquante (avec le pourquoi), non couverte (CC-37), exclue (CC-38), désactivée (AC4)
**And** la synthèse, les comptes et l'ancre suivent les règles de 16-8, étendues à l'état désactivé
**And** l'interface ne recalcule aucune décision de publication.

**AC7 — Sélecteur de type inactif là où il n'a aucun effet (Q2)**

**Given** une commande non couverte, exclue ou désactivée
**When** sa ligne est rendue
**Then** son sélecteur de type est affiché mais désactivé, avec une info-bulle :
- non couverte : « Aucun mapping ne couvre cette commande : son type HA ne peut pas être réglé ici. » ;
- exclue : « Commande exclue de Jeedom2HA : son type HA ne peut pas être réglé ici. » ;
- désactivée : « Équipement désactivé dans Jeedom : son type HA ne peut pas être réglé ici. »
**And** aucun aperçu ni enregistrement ne peut partir de ce sélecteur
**And** les commandes prêtes ou bloquantes gardent un sélecteur actif
**And** sur une ligne dont le sélecteur est désactivé mais qui porte un override, le lien de retour au mode automatique de la commande (`.mo-revert-cmd`) reste actif.

**AC8 — Édition du type HA sans régression**

**Given** une commande prête ou bloquante
**When** l'utilisateur choisit un type HA
**Then** l'aperçu est demandé, l'override est enregistré automatiquement si l'aperçu est vert, puis l'équipement est relu
**And** le retour au mode automatique reste possible par commande et par équipement
**And** aucun chemin ne modifie le `generic_type` natif de Jeedom (D10).

**AC9 — Limites de périmètre (vérifiées à la revue)**

**Given** la story livrée
**Then** aucune action d'exclusion, de forçage ou de rescan n'est ajoutée, et aucun nouveau point d'entrée du démon n'est créé.

**AC10 — Preuve**

**Given** le code fusionné sur `main` et déployé
**When** le `done` est évalué
**Then** les parcours du gate 20-0 passent sur le code de `main` :
- découverte (lecture seule), étendue pour relever :
  - l'ordre du DOM : actions de « Gestion » avant la surface (AC2) ;
  - aucune entrée `getMappingOverrides` au journal avant l'ouverture d'une pièce (AC5) ;
  - la présence de la carte « Sans pièce » et son nombre d'équipements, ou son absence ;
  - dans le Garage, l'équipement désactivé eq 279 : l'état `desactive` de son badge et de ses cellules ;
  - les états déjà relevés (Enphase, badges du Garage) ;
- référence (bascule simulée de 5369), adaptée au DOM si nécessaire ;
**And** le filtre des cartes du gate reste exact : le `span.name` d'une carte ne contient que le nom de la pièce
**And** un déploiement standard du SHA exact, avec relevés avant et après (box et HA), est consigné
**And** un passage dans Chrome en lecture seule par ClaudeBox est consigné
**And** la story passe par `ready-for-UX-validation` avant `done`.

## Tasks / Subtasks

- [x] **Task 0 — Relevés préalables, lecture seule (AC: 3, 4)**
  - [x] 0.0 — `epics-projection-engine.md` (Story 20.1 et 20.3) porte le déplacement des compteurs vers 20.3 (décision Q3 d'Alex, 2026-10-05).
  - [x] 0.1 — Lecture seule le 2026-10-05 : `eqLogic.class.php:116` : `public static function byObjectId($_object_id, $_onlyEnable = true, $_onlyVisible = false, $_eqType_name = null, $_logicalId = null, $_orderByName = false, $_onlyHasCmds = false)` ; accepte donc `null` et `-1` avec `$_onlyEnable = false`.
  - [x] 0.2 — Relevé par ClaudeBox le 2026-10-05 vers 10:40, en lecture seule depuis la page du plugin (`getPublishedScopeForConsole`, déjà lue par la page) :
    - 20 équipements sans pièce (pièce `0`, « Aucun » dans la synthèse), dont 2 désactivés, 13 exclus par plugin et 1 publié ;
    - 7 équipements désactivés au total : Garage 1 (eq 279), bureau 1, exterieur 3, sans pièce 2 ;
    - **pièce désignée pour le gate : Garage**, avec l'eq 279.
  - [x] 0.3 — Relevé par ClaudeBox le 2026-10-05, en lecture seule (`getMappingOverrides`, eq 279) : 4 commandes, toutes `publication_reason: disabled_eqlogic` et `covered: false`.
- [x] **Task 1 — Données Jeedom (AC: 3, 4)**
  - [x] 1.1 — `desktop/php/jeedom2ha.php` appelle `eqLogic::byObjectId($object->getId(), false)`.
  - [x] 1.2 — « Sans pièce » : `eqLogic::byObjectId(null, false)`, hors type `jeedom2ha`, identifiant `0`, en dernier ; `normalizeRoomsTree` n'écarte qu'un `object_id` nul : avec `0`, aucun changement n'y est nécessaire.
  - [x] 1.3 — Tests node de la normalisation : « Sans pièce » en dernier, désactivés conservés dans l'ordre natif.
- [x] **Task 2 — Bloc « Gestion » (AC: 2)**
  - [x] 2.1 — Bloc des trois actions déplacé sous le titre « Gestion », classes et attributs conservés.
- [x] **Task 3 — État désactivé (AC: 4, 6)**
  - [x] 3.1 — Module pur : `isDisabledDiagnostic`, libellé, `disabled_count` dans `summarizePublication`, état `disabled` de la synthèse, `collectBlockingCommandIds` aligné ; tests node.
  - [x] 3.2 — Rendu : cellule et badge neutres, mention « désactivé dans Jeedom » sur l'en-tête ; CSS.
- [x] **Task 4 — Sélecteur inactif (AC: 7)**
  - [x] 4.1 — Fonction pure qui dit si le sélecteur d'une ligne est actif et donne la raison sinon ; tests node.
  - [x] 4.2 — `renderCommandRow` : `disabled` + `title`, aucun gestionnaire d'aperçu attaché.
- [x] **Task 5 — Non-régression (AC: 1, 5, 6, 8)**
  - [x] 5.1 — Chargement toujours borné à la pièce ouverte (`desktop/js/jeedom2ha_mapping_surface.js:437-446`).
  - [x] 5.2 — Suite node complète verte ; aucune modification de `diagnosticState`, `shouldAutoValidate`, ni des routes preview, save et revert.
- [ ] **Task 6 — Gate et preuve (AC: 10)**
  - [x] 6.1 — Parcours de découverte étendu (lecture seule, aucun nom d'équipement relevé, aucune écriture) ; parcours de référence inchangé, le DOM de ses cibles ne change pas.
  - [ ] 6.2 — Après fusion : déploiement standard, relevés, parcours du gate, passage Chrome par ClaudeBox, puis `ready-for-UX-validation`.

## Dev Notes

### Contrats réutilisés (lignes au SHA `b4ce7b2`)

- `desktop/php/jeedom2ha.php:14-36` : `j2haRoomsTree` (`jeeObject::buildTree(null, false)`, `eqLogic::byObjectId(...)`, exclusion du type `jeedom2ha`, drapeau `enabled`).
- `desktop/php/jeedom2ha.php:42` (titre « Gestion »), `:122-144` (surface), `:146-163` (les trois actions).
- `desktop/js/jeedom2ha_mapping_surface.js:370-381` : rendu déjà prévu de `j2ha-eq-disabled` et de « (désactivé) » ; `:141-210` (aperçu, enregistrement, retours ; un override sur une commande non couverte n'est jamais persisté, branche `!covered` de `runDryRun`) ; `:328-345` (lecture `getMappingOverrides`) ; `:437-446` (chargement borné).
- `desktop/js/jeedom2ha_mapping_override.js` : état exclu (CC-38, l. 334 et suivantes), synthèse et ancre ; `:389-392` (`normalizeRoomsTree`).
- `resources/daemon/models/topology.py:312` : éligibilité `disabled_eqlogic` d'un équipement désactivé.
- `resources/daemon/transport/http_server.py:2900-2940` : l'arbre appelle `evaluate_equipment()` et porte `covered` ; route `:4351-4355`.
- Démon : « aucune pièce » est l'identifiant `0` (`resources/daemon/models/published_scope.py:105` ; `desktop/js/jeedom2ha_scope_summary.js:308`).

### Interdits

- Ne jamais écrire `generic_type` (D10). Aucun recalcul de décision côté interface. Aucun nouveau point d'entrée du démon.
- Ne pas charger les arbres de tout le parc. Ne pas toucher à la synthèse « Parc global » ni à la modale diagnostic.
- Jamais `git add -A`, jamais `--admin`, aucun force-push. Déploiement standard seulement, jamais `--cleanup-discovery` ni `--stop-daemon-cleanup`.

### Fichiers probablement touchés

`desktop/php/jeedom2ha.php`, `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/js/jeedom2ha_mapping_override.js`, `desktop/css/jeedom2ha.css`, tests node (16-8 et nouveaux), `tests/e2e/gate/parcours/decouverte-garage-enphase.mjs` (et `reference-bascule-enphase.mjs` si le DOM change).

## Définition de done

- 20-0 et 16-8 sont `done` (tenu).
- Tous les AC sont couverts par des tests nommés ou par le gate ; la File List est complète.
- CI verte ; revue Codex sans problème majeur (ou relecture indépendante si Codex est indisponible) ; relecture ClaudeBox.
- Déploiement standard du SHA exact relu, relevés avant et après sans écart inexpliqué (box et HA).
- Parcours de découverte et de référence du gate 20-0 PASS sur le code de `main`.
- Passage Chrome de ClaudeBox consigné, puis `ready-for-UX-validation`, puis validation UX.
- Au `done` : SHA, CI, commandes de tests, preuves et validation UX consignés (rétrospective pe-epic-19).

## Journal des décisions

- 2026-10-05 — Brouillon `create-story` de clawcode (`debc77c`), relu et réécrit par ClaudeBox, puis relu par une relecture indépendante (prémisse fausse sur les compteurs corrigée, état désactivé précisé, identifiant « Sans pièce » fixé, vérifications du gate ajoutées).
- 2026-10-05 — Questions Q1 à Q4 posées à Alex, avec recommandation 1A, 2A, 3C, 4A (Q3 et Q4 corrigées dans un second message).
- 2026-10-05, 10:43 — **Décision d'Alex : « 1A 2A 3C 4A ».** Le déplacement des compteurs vers 20.3 est porté dans `epics-projection-engine.md` (Story 20.1 et 20.3). Story passée `ready-for-dev`.

## References

- `_bmad-output/planning-artifacts/epics-projection-engine.md`, Epic 20 ; `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-01-etape-4-interface.md`, décisions 1 à 7.
- `_bmad-output/implementation-artifacts/16-8-surface-navigation-piece-equipement-commande-homebridge.md` et `16-8-validation-ux-2026-10-05.md`.
- `_bmad-output/implementation-artifacts/20-0-gate-preuve-ux-outille.md` et `20-0-gate-2026-10-04.md`.
- `_bmad-output/implementation-artifacts/pe-epic-19-retro-2026-10-01.md`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- 2026-10-05 — BMAD `dev-story` non interactif terminé pour les Tasks 0 à 5 et 6.1 ; confirmations par défaut consignées au rapport externe.
- 2026-10-05 — 424 tests node verts ; `php -l` et `node --check` verts ; auto-test local de l'intercepteur PASS (0 échec).
- 2026-10-05 — 6.2 reste explicitement hors unité : déploiement, gate sur box et passage Chrome seront faits après fusion.
- 2026-10-05 — Signature box lue : `byObjectId($_object_id, $_onlyEnable = true, $_onlyVisible = false, $_eqType_name = null, $_logicalId = null, $_orderByName = false, $_onlyHasCmds = false)`.

### File List

- `desktop/php/jeedom2ha.php`
- `desktop/js/jeedom2ha_mapping_override.js`
- `desktop/js/jeedom2ha_mapping_surface.js`
- `desktop/css/jeedom2ha.css`
- `tests/unit/test_story_16_8_mapping_surface.node.test.js`
- `tests/e2e/gate/parcours/decouverte-garage-enphase.mjs`
- `_bmad-output/implementation-artifacts/20-1-surface-unique-piece-equipement-commande.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-10-05 — Surface unique complétée : Sans pièce, désactivés neutres, sélecteurs inactifs et découverte gate étendue.
