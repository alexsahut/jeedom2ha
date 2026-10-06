# Story 20.2 : Exclusion et forçage depuis la surface (CC-26)

Status: review

## Story

En tant qu'utilisateur du plugin,
je veux exclure un équipement ou une entité Home Assistant, ou forcer sa publication, puis revenir au mode automatique, depuis la surface pièce → équipement → commande,
afin de décider moi-même de ce qui va dans Home Assistant, de façon visible et réversible, sans modifier Jeedom.

**Parcours : complet.** Gate 20-0, déploiement standard, preuve terrain qui écrit, `ready-for-UX-validation`, puis `done`.

## Contexte et périmètre

- 20-1 est `done` : la surface par pièce est le seul point d'édition. Elle affiche les états prête, bloquante, non couverte, exclue et désactivée.
- 20-2 ajoute la pose et le retrait d'un override de publication (exclusion, forçage), sur l'équipement et sur la commande (décision 2 d'Alex du 2026-10-01). La pièce reste gérée par la liste d'exclusions de la configuration.
- 20-2 porte le sort des commandes `ambiguous_skipped` (epic 20, Story 20.2) : CC-26 ne se ferme que si ces cas réels sont traités, soit parce que le forçage les lève, soit par un forçage borné et dit comme tel.
- Le retrait (« revenir au mode automatique ») est prouvé par clic réel (décision d'Alex du 2026-09-29, 08:13) ; le gate 20-0 simule toutes les écritures.
- Hors périmètre : suppression de « Parc global » et jargon (20-3), rescan (20-4), documentation (20-5), exclusions par plugin ou par pièce (configuration).

## Faits relevés le 2026-10-05 (lecture seule, `main` `f05dba5`)

- **F1 — Aujourd'hui, le forçage ne fait publier aucune commande de plus.** `force_publish` n'ignore que le niveau 4b, la politique de confiance (`resources/daemon/models/decide_publication.py:133-146`) ; il change seulement la raison en `publication_forced`. Les refus réels viennent des niveaux 1 (mapping ambigu), 2 (projection invalide) et 3 (type hors périmètre produit), que le forçage ne lève pas. Les mappings « probable » sont publiés (relevé de parité du 2026-10-05) ; la politique active est à relire directement (Task 0.3).
- **F2 — Les 17 commandes `ambiguous_skipped` (8 équipements inclus)**, d'après l'arbre `getMappingOverrides` de chacun :
  - eq 380, 477, 481 : candidat `cover`, causes `state_orphan` (380) et `duplicate_generic_types` (477, 481), **projection valide** ; 5 commandes ;
  - eq 287, 460, 463, 585 : candidats `switch` (287, 585) et `light` (460, 463), cause `name_heuristic_rejection`, **projection invalide** (`ha_missing_command_topic`) ; 11 commandes. Ces quatre équipements ont pourtant des commandes On et Off (`ENERGY_ON`/`ENERGY_OFF` ou `LIGHT_ON`/`LIGHT_OFF`). La projection est invalide parce que le mapper rend son résultat ambigu **avant** de détecter l'ordre On/Off : ses capacités restent vides (`resources/daemon/mapping/switch.py:166-185` avant `:188`, `light.py:203-222` avant `:245`, même schéma dans `cover.py:193`) ;
  - eq 579, commande 5369 : candidat `switch`, cause `switch_state_orphan` (un état sans ordre On/Off), **projection invalide** ; 1 commande.
- **F3 — Un override TYPE ne lève pas l'ambiguïté.** Il ne change que le type HA du résultat (`resources/daemon/mapping/overrides.py:398-402`), sans relancer le mapper (D8) ; la confiance `ambiguous` reste refusée au niveau 1 (`decide_publication.py:94-97`).
- **F4 — Une exclusion utilisateur ne s'affiche pas sur une entité déjà refusée.** L'exclusion est évaluée au niveau 2b, après les niveaux 1 et 2 (`decide_publication.py:94-125`, ordre canonique de l'invariant I4 : `decide_publication.py:14-24`, `_bmad-output/planning-artifacts/pipeline-contract.md:90`). Une entité ambiguë ou à projection invalide que l'utilisateur exclut garde sa cause d'origine et reste « bloquante » dans la surface.
- **F5 — Un override de publication vaut pour toute l'entité HA, pas pour une commande seule.** Il est résolu par mapping : `_resolve_publication_override_for_mapping` parcourt les commandes du mapping et le premier override trouvé l'emporte (`resources/daemon/models/evaluate_equipment.py:165-179`). Exclure une commande d'une lumière exclut toute la lumière ; une exclusion et un forçage posés sur deux commandes d'une même entité se départagent par l'ordre des commandes. Une commande non couverte ne consulte aucun override (`evaluate_equipment.py:459-468`).
- **F6 — Override de type et override de publication s'écrasent.** Ils partagent la même entrée `eq:cmd` : `save_override` la remplace entière (`overrides.py:256`) et `remove_override` la supprime entière (`overrides.py:407-437`). Enregistrer un type efface une exclusion ou un forçage posé sur la même commande, et inversement.
- **F7 — Aucun sync périodique dans le plugin.** Aucune tâche `cron` (`core/class/jeedom2ha.class.php`) ; la seule tâche de fond du démon est le chien de garde de démarrage (`resources/daemon/main.py:216`). Le sync complet a lieu au démarrage du démon (dont chaque déploiement standard, étape 4c du script) et sur l'action de rescan `scanTopology` (`core/ajax/jeedom2ha.ajax.php:594`).
- **F8 — « Publier » par équipement prend la même décision que le sync** et dépublie les candidats refusés (story 19-4, `resources/daemon/transport/http_server.py:3942-3946`).
- **F9 — L'arbre ne porte ni la décision de l'équipement, ni le détail de la cause.** Il n'expose que la décision par commande et `reason_code` (`http_server.py:2561-2598`, `:2860-2958`) : ni décision d'équipement (d'où le constat de 20-1 : un équipement exclu sans commande s'affiche « Aucune commande projetable »), ni `reason_details` (mot du nom écarté, type en double). Le badge « pas encore appliqué » (`override_pending`) ne compare que la décision de l'équipement (`http_server.py:2942-2946`).
- **F10 — Libellé faux pour l'ambiguïté.** `ambiguous_skipped` est toujours rendu « mapping ambigu — précisez les types génériques dans Jeedom » (`desktop/js/jeedom2ha_mapping_override.js:256`), alors qu'aucun type générique ne manque (F2).
- **F11 — Précédence : la docstring et le code divergent.** `resolve_publication_override` applique l'exclusion d'équipement, puis l'override de commande (exclusion ou forçage), puis le forçage d'équipement (`overrides.py:471-516`), mais sa docstring dit « pas de `force_publish` de commande ».
- **F12 — Écritures non atomiques** de `data/ha_overrides.json` (CC-34, `overrides.py:234-315` et `:407-468`). **Le gate n'autorise que deux écritures simulées**, `saveMappingOverride` et `revertMappingOverride` (`tests/e2e/gate/lib/policy.mjs:71`).

## Décisions d'Alex (2026-10-05, 20:26)

Réponse « 1A, 2A, 3A » aux questions posées vers 15:05, sur recommandation de ClaudeBox (voir « Journal des décisions »). Les AC marqués **[Qx]** les appliquent.

- **Q1 — Le forçage lève l'ambiguïté, avec validation.** Le mapper calcule les capacités même quand le nom de l'équipement fait douter (sans override, aucune décision ne change) ; « Forcer » publie une entité `ambiguous` si sa projection est valide et son type dans le périmètre produit ; un aperçu montre d'abord le résultat forcé et les commandes qui recevront les ordres ; le type proposé peut être changé pendant l'aperçu du forçage ou une fois l'entité forcée, sous la même validation. Attendu : 16 commandes sur 17 ; la commande 5369 demande un autre type, à vérifier. L'invariant I3 est amendé pour la seule entité `ambiguous` forcée par l'utilisateur. Option écartée : forçage borné.
- **Q2 — Actions sur l'équipement et sur chaque entité HA**, grisées avec une info-bulle quand elles sont sans effet (comme le sélecteur de type, décision 2A de 20-1) : « Exclure », « Forcer » et « Revenir au mode automatique » dans l'en-tête de l'équipement et sur la première ligne de chaque entité, dont le libellé dit quelles commandes elle regroupe ; pas d'action sur les commandes non couvertes ; confirmation pour exclure une entité publiée. Options écartées : équipement seulement ; exclusion propre à une commande.
- **Q3 — Badge « pas encore appliqué dans Home Assistant » et bouton « Appliquer »** sur l'équipement, qui lance « Publier » pour cet équipement (même décision que le sync). Rien ne change dans HA sans ce clic. Options écartées : attendre le prochain sync ; appliquer dès la pose.

## Acceptance Criteria

**AC1 — Exclure un équipement ou une entité [Q2]**

**Given** un équipement, ou une entité HA affichée par la surface
**When** l'utilisateur choisit « Exclure de Home Assistant » (et confirme pour une entité publiée)
**Then** un override de publication `exclude` est enregistré pour l'équipement, ou pour l'entité, puis l'équipement est relu
**And** la surface dit quelles commandes l'entité regroupe, et l'état affiché vient exclusivement de l'arbre du démon, donc de `evaluate_equipment()`
**And** l'override d'une entité ne touche qu'elle : il est enregistré sur une commande propre à l'entité, ou sous une clé d'entité, jamais sur une commande partagée avec une autre entité (par exemple une commande d'action commune au principal et à un secondaire, `http_server.py:2514-2517`).

**AC2 — L'exclusion de l'utilisateur prime (F4)**

**Given** une entité ambiguë ou à projection invalide
**When** l'utilisateur l'exclut
**Then** ses commandes passent à l'état « exclue » (`publication_excluded_command` ou `publication_excluded_eqlogic`), ne sont plus comptées bloquantes et ne reçoivent plus l'ancre
**And** l'exclusion utilisateur est évaluée après l'éligibilité mais avant les niveaux 1 et 2 ; l'ordre canonique de I4 est amendé dans `decide_publication.py` et `pipeline-contract.md`, avec ses tests
**And** une exclusion ne fait jamais publier quoi que ce soit (I2 et I6 inchangés ; I3 n'est touché que par AC3) ; les écarts de raison attendus sur les exclusions déjà posées sont listés en Task 0.3 et vérifiés par l'outil de parité.

**AC3 — Forcer [Q1, Q2]**

**Given** un équipement ou une entité HA
**When** l'utilisateur force la publication (et confirme)
**Then** l'override `force_publish` est enregistré, et la cause `publication_forced` vient de l'arbre
**And** selon Q1, le forçage lève le niveau 1 pour la seule confiance `ambiguous` (jamais `no_mapping`), si la projection est valide et le type dans le périmètre produit ; une projection invalide ou un type hors périmètre restent refusés, avec leur cause
**And** l'invariant I3 est amendé dans `decide_publication.py` et `pipeline-contract.md` : confiance publiable, ou `ambiguous` forcée par l'utilisateur ; tests d'invariant mis à jour
**And** avant le forçage, un aperçu montre le résultat forcé (type, validité, commandes qui recevront les ordres) ; l'aperçu d'un type sur une entité ambiguë tient compte d'un forçage posé ou proposé
**And** l'action est grisée, avec une info-bulle, là où elle ne change pas la décision.

**AC4 — Capacités calculées malgré le doute sur le nom [Q1] (F2)**

**Given** un équipement dont le nom fait douter le mapper (`name_heuristic_rejection`)
**When** le mapping est calculé
**Then** ses capacités (ordre On/Off, état) sont détectées comme pour un équipement sans doute, et la confiance reste `ambiguous`
**And** les commandes du résultat (`commands`) restent exactement les mêmes : seules les capacités changent
**And** sans override, aucune décision ne change : relevé de parité identique (décisions, `matched_commands`, `unmatched_commands`), décisions par commande et statut de « Parc global » inchangés ; seul le diagnostic de projection devient exact.

**AC5 — Les deux overrides d'une commande coexistent (F6)**

**Given** une commande qui porte un override de type et un override de publication
**When** l'un des deux est enregistré ou retiré
**Then** l'autre est conservé (fusion champ par champ), tests à l'appui.

**AC6 — Revenir au mode automatique (CC-19)**

**Given** un override de publication ou de type
**When** l'utilisateur clique « Revenir au mode automatique » sur une entité ou sur l'équipement
**Then** pour une entité, ses overrides de publication et de type sont retirés ; pour l'équipement, tous ses overrides, ceux de ses commandes compris (CC-19)
**And** le `generic_type` de Jeedom n'est jamais modifié (D10), et l'équipement relu porte l'état automatique.

**AC7 — Après la pose [Q3]**

**Given** un override posé ou retiré, pas encore appliqué
**When** l'équipement est relu
**Then** le badge « pas encore appliqué dans Home Assistant » apparaît dès qu'une entité de l'équipement, principale ou secondaire, a une décision différente de la dernière décision appliquée, ou n'a jamais été synchronisée (F9)
**And** le bouton « Appliquer » lance « Publier » pour ce seul équipement, puis relit l'équipement.

**AC8 — Arbre complet (F9, constat de 20-1)**

**Given** un équipement
**When** son arbre est lu
**Then** il porte la décision de l'équipement, l'override de publication effectif par entité, et le détail utile de la cause (`reason_details`)
**And** un équipement exclu sans commande s'affiche « Exclu », et non « Aucune commande projetable » ; l'interface ne recalcule rien.

**AC9 — Libellés exacts de l'ambiguïté (F10)**

**Given** une commande `ambiguous_skipped`
**When** sa cellule est rendue
**Then** le libellé dit la cause réelle, tirée de l'arbre : un mot du nom de l'équipement écarte ce type, types génériques en double, état sans ordre On/Off
**And** il ne demande jamais de renseigner un type générique déjà présent.

**AC10 — Contrat et routes (F11)**

**Given** une demande de pose ou de retrait d'override de publication
**When** elle traverse le relais PHP puis le démon
**Then** la portée, la valeur et l'existence de l'équipement et de l'entité sont validées, avec des erreurs lisibles
**And** les routes TYPE (aperçu, enregistrement, retrait) gardent leur contrat
**And** à l'intérieur d'une entité, une exclusion l'emporte sur un forçage, quel que soit l'ordre des commandes ; la docstring de `resolve_publication_override` dit la précédence réelle.

**AC11 — Preuve**

**Given** le code fusionné sur `main` et déployé par la procédure standard
**When** le `done` est évalué
**Then** le gate 20-0 passe sur `main` (découverte, référence, et un parcours qui simule la pose et le retrait d'une exclusion, déclarés)
**And** une preuve terrain fait au clic réel la pose, l'application puis le retrait d'une exclusion sur un équipement non publié, avec le témoin `getBridgeStatus` relevé avant et après, et un sync correctif après le retrait si le témoin a bougé ; pose et retrait se terminent avant tout nouveau déploiement (F7)
**And** le forçage d'une entité ambiguë réelle (Q1) n'est fait sur la box qu'avec le GO d'Alex sur l'entité choisie, après lui avoir montré l'aperçu du résultat forcé, et aucun équipement publié n'est exclu sans son GO
**And** la story passe par `ready-for-UX-validation` avant `done`.

## Tasks / Subtasks

- [x] **Task 0 — Relevés, lecture seule (AC: 2, 3, 4, 7, 11)**
  - [x] 0.1 Relire les 17 commandes ambiguës (F2) au SHA courant : pour les quatre équipements On/Off, confirmer les commandes On et Off ; pour 5369, le type qui validerait.
  - [x] 0.1b Relever les commandes partagées entre entités (principal et secondaires) sur les 8 équipements et sur l'eq 579 (AC1).
  - [x] 0.2 Confirmer ce que fait « Publier » par équipement sur une entité exclue (F8).
  - [x] 0.3 Lire la politique de confiance active ; relever les overrides de publication présents (nombre, portée, sans contenu) et ceux posés sur une entité ambiguë ou invalide (écarts attendus d'AC2).
  - [x] 0.4 Choisir un équipement non publié pour la preuve terrain.
- [x] **Task 1 — Décision et mapping (AC: 2, 3, 4, 10)**
  - [x] 1.1 Exclusion utilisateur avant les niveaux 1 et 2 ; amendement d'I4 (code, `pipeline-contract.md`, tests).
  - [x] 1.2 Selon Q1 : capacités calculées malgré l'heuristique de nom (switch, light, cover), commandes inchangées ; forçage qui lève le niveau 1 pour `ambiguous` seulement, niveaux 2 et 3 conservés ; amendement d'I3 (code, `pipeline-contract.md`, tests) ; aperçu du forçage.
  - [x] 1.3 Précédence dans une entité (exclusion avant forçage) ; docstring alignée.
- [x] **Task 2 — Persistance et routes (AC: 1, 3, 5, 6, 10)**
  - [x] 2.1 Fusion champ par champ des overrides de type et de publication.
  - [x] 2.2 Routes démon dédiées (pose, retrait), sans détourner l'API TYPE ; actions AJAX PHP, validation stricte.
  - [x] 2.3 Purge par entité et par équipement (CC-19).
- [x] **Task 3 — Arbre et surface (AC: 1, 3, 6, 7, 8, 9)**
- [x] 3.1 Arbre : décision d'équipement, override effectif par entité, `reason_details`, badge par entité.
  - [x] 3.2 Actions selon Q2, confirmation, état pendant la requête ; badge et « Appliquer » selon Q3.
  - [x] 3.3 Libellés de l'ambiguïté par cause.
- [x] **Task 4 — Tests (AC: 1 à 10)** : Python (précédence, I2, I3 et I4 amendés, capacités, commandes inchangées, parité sans override, fusion, clé d'entité), PHP, Node (actions, libellés, absence de recalcul), non-régression TYPE.
- [ ] **Task 5 — Gate et preuve (AC: 11)**
  - [x] 5.1 Gate : nouvelles écritures autorisées comme écritures simulées déclarées (F12), auto-test local, parcours de pose et de retrait d'une exclusion.
  - [ ] 5.2 Après fusion : déploiement standard, relevés avant et après (parité : `changed_decisions` vide hors écarts listés en 0.3), gate sur `main`.
  - [ ] 5.3 Preuve terrain au clic réel (AC11), passage Chrome par ClaudeBox, `ready-for-UX-validation`, validation UX.

## Dev Notes

### Prérequis

- **CC-34 avant toute preuve qui écrit** (F12) : écritures atomiques de `data/ha_overrides.json` (fichier temporaire puis `os.replace`). Livré le 2026-10-05 : PR #207, fusion `51bc9d9`, déployé à 15:33 sans écart.

### Points de code (SHA `f05dba5`)

- Décision : `resources/daemon/models/decide_publication.py:14-24` (ordre), `:39-43` (invariants), `:94-149`.
- `evaluate_equipment` : `resources/daemon/models/evaluate_equipment.py:112-126` (`CommandDecision`), `:165-179` (override par mapping), `:443-479` (décision par commande).
- Mappers : `resources/daemon/mapping/switch.py:166-188`, `light.py:203-245`, `cover.py:193-203`.
- Overrides : `resources/daemon/mapping/overrides.py:234-315` (écritures), `:344-404` (TYPE), `:407-437` (retrait), `:471-516` (publication).
- Arbre et routes : `resources/daemon/transport/http_server.py:2561-2598`, `:2860-2958`, `:3006-3130` (TYPE), `:3942-3946` (« Publier »), `:4350-4355` (routes).
- Relais : `core/ajax/jeedom2ha.ajax.php:877-918`. Surface : `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/js/jeedom2ha_mapping_override.js:250-293`, `:436-469`.
- Contrat : `_bmad-output/planning-artifacts/pipeline-contract.md:89` (I3) et `:90` (I4).

### Interdits

- Aucun recalcul de décision côté interface ; jamais d'écriture du `generic_type` de Jeedom (D10) ; I2 non négociable ; I3 amendé seulement pour une entité `ambiguous` forcée par l'utilisateur (AC3).
- Pas de modification des exclusions par plugin ou par pièce.
- Preuve terrain : aucun forçage réel sans GO d'Alex sur l'entité ; aucune exclusion d'un équipement publié sans son GO.
- Jamais `git add -A`, jamais `--admin`, aucun force-push ; déploiement standard seulement.

## Définition de done

- Décisions Q1 à Q3 d'Alex (2026-10-05, 20:26) appliquées.
- CC-34 livré avant la preuve terrain (fait le 2026-10-05).
- AC couverts par des tests nommés ou par le gate ; CI verte ; revue Codex sans problème majeur (ou relecture indépendante) ; relecture ClaudeBox.
- Déploiement standard du SHA relu, relevés box et HA sans écart inexpliqué ; gate PASS sur `main` ; preuve terrain au clic réel.
- `ready-for-UX-validation`, validation UX, puis `done`. CC-26 fermé, les 17 commandes ambiguës traitées selon Q1.

## Journal des décisions

- 2026-10-05 — Brouillon `create-story` de clawcode (`acd63c6`), réécrit par ClaudeBox, puis relu par une relecture indépendante : faits F1 à F12 relevés en lecture seule (dont le détail des 17 ambiguës par l'arbre de chaque équipement), portée réelle d'un override (l'entité), coexistence des overrides, précédence de l'exclusion (AC2), amendements d'I3 et d'I4, questions Q1 à Q3 reformulées.
- 2026-10-05, vers 15:05 — Questions Q1 à Q3 posées à Alex, avec recommandation 1A, 2A, 3A.
- 2026-10-05, 20:26 — **Décision d'Alex : « 1A, 2A, 3A ».** Story passée `ready-for-dev`.

## References

- `_bmad-output/planning-artifacts/epics-projection-engine.md`, Epic 20, Story 20.2 ; `sprint-change-proposal-2026-10-01-etape-4-interface.md`, décision 2 et « Risques et suivi ».
- `_bmad-output/implementation-artifacts/20-1-preuve-validation-ux-2026-10-05.md` (constat reporté) ; `16-8-validation-ux-2026-10-05.md` ; `16-8-ac14-validation-2026-10-01.md` (les 17 ambiguës).
- `_bmad-output/implementation-artifacts/16-3-overrides-publication-exclusion-explicite.md` ; `19-3-surface-piece-apercu-contrat-decision-cc03-cc19.md` ; `19-4-publier-mini-sync-contrat-decision-cc18.md`.
- `_bmad-output/implementation-artifacts/20-0-gate-preuve-ux-outille.md`, « Invocation du gate par une story suivante ».

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- 2026-10-05 — Task 0 relevée en lecture seule; Task 1 : veto d'exclusion précoce, forçage `ambiguous` validé, capacités conservées sous heuristique et précédence exclusion > forçage. Tests ciblés : 149 passés.
- 2026-10-05 — Task 2 : fusion des deux champs d'override, routes de publication dédiées avec validation d'ID et refus des commandes partagées; purge CC-19 réutilisée. Tests Python ciblés : 28 passés; Node : 424 passés; flake8 et PHP lint OK.
- 2026-10-05 — Reprise X2c : routes publication couvertes; arbre enrichi sans recalcul UI par `equipment_decision` et `entities[]` (`ha_entity_type`, `publication_override`, `reason_details`, `override_command_id`, `override_pending`). Une commande partagée ne devient jamais clé d'action.
- 2026-10-06 — Reprise X2d : garde-fou de parité amendé pour les ajouts additifs AC8; badge AC7 par entité. La dernière décision appliquée du principal vient de `app["publications"][eq_id]`; celle d'un secondaire vient de la `publication_decision_ref` du secondaire du mapping conservé dans cette même entrée (alimentée par sync et « Publier »). `entities[]` porte `ha_entity_type`, `decision`, `publication_override`, `reason_details`, `override_command_id`, `override_pending`; l'aperçu de forçage porte `command_ids`.
- 2026-10-06 — Reprise X2d : tests AC3 (`ambiguous` forcée, projection/scope/no_mapping/exclusion), aperçu, routes 409 et retrait TYPE ajoutés; statut story conservé `in-progress` (surface, gate et preuve hors unité).
- 2026-10-06 — Reprise X3b : l'arbre ajoute `entities[].command_ids`; la surface lit les entités, leurs commandes, leurs décisions et leur clé d'override depuis le démon. Actions exclusion/forçage/retour, aperçu forcé, badge et application ciblée sont couverts par tests Node; le retour de publication retire type et politique.
- 2026-10-06 — Reprise X3b : le gate simule exclusivement les écritures de publication explicitement déclarées; les écritures non déclarées et « Appliquer » restent bloquées. Auto-test local PASS; 5.2 et 5.3 restent post-fusion et terrain.
- 2026-10-06 — Correction d'attribution (Reprise X4) : les commits `93329f5` à `18e2ce6` (points 1-6, 02:36-02:51) listés ci-dessous comme « travail de X3b » sont en réalité de X3c ; X3b s'est arrêtée bloquée à 01:57 (voir rapport, section « Unité X3 bloquée »).
- 2026-10-06 — Reprise X3c (modèle `claude-sonnet-5`) : 9 points de revue ClaudeBox sur X3b traités, un commit par point. Points 1-6 : exclusions du démon conservées à la lecture, modale Bootbox à la place de `window.confirm`, aperçu riche du forçage (AC3), cause de blocage propre à chaque bouton, libellés d'entités avec vrais noms de commande, badge par entité et erreurs lisibles (AC7). Points 7-9 (gate) : les overrides de publication simulés deviennent visibles à une relecture `getMappingOverrides` (`simulate.mjs`, `interceptor.mjs`, auto-test étendu) ; `declaredPublicationOverrides` devient optionnel dans un parcours (`isValidParcours` extrait et testé) ; test de non-régression prouvant que le sélecteur de type (route TYPE, 16-8) reste actif quel que soit l'override de publication posé. Vérification finale au SHA `cad3a02` : 442 tests Node (`tests/unit/*.node.test.js`), 2048 tests Python (`pytest -m "not load"`), auto-test gate local PASS ; aucun fichier Python/PHP touché par les points 7-9. Écart assumé : les comportements DOM/Bootbox propres à `jeedom2ha_mapping_surface.js` (confirmation, bouton Appliquer, retrait au clic) restent non couverts par un test automatisé faute de harnais DOM dans ce dépôt — vérifiés par lecture de code et par les parcours gate existants, à confirmer en preuve terrain (5.2/5.3).

- 2026-10-06 — Reprise X4 (modèle `claude-sonnet-5`) : 8 points de revue ClaudeBox sur X3c traités, un commit par point, tests avant chaque commit. Points 1-2 déjà faits en amont de ce segment visible. Point 3 : exclusion d'équipement lue depuis l'arbre, deux boutons « Revenir au mode automatique » fusionnés en un (`49b8f60`). Point 4 : `publicationActionState` grise Forcer/Revenir pour une entité héritant du veto d'équipement, avec l'info-bulle dédiée (`e56471c`). Point 5 : capture/restauration exacte de l'état des boutons par `disableButtons`/`restoreButtons` (`.data()`), filet `hidden.bs.modal` sur `confirmPublicationDialog` (`d8ba4f0`). Point 6 : `requestPublication` route l'erreur d'aperçu via `readPublicationRequestError` avant toute lecture `readPreviewOverridden` (`8807542`). Point 7 : harnais `node:vm` dédiés (dialogue de confirmation, état des boutons) dans un nouveau fichier de test, modelés sur `loadConfirmationHarness` de la PR #209 (`876d607`). Point 8 : `derivePublicationOverrideTree` du gate suit l'ordre de précédence du démon — exclusion d'équipement, puis override de commande, puis forçage d'équipement par défaut (`e4c6468`). Fusion de `origin/main` (story 20-4, PR #209) : trois conflits résolus en gardant les deux côtés comme convenu (`interceptor.mjs`, `policy.mjs`, `run-gate.mjs`) — commit `b4fafd9`. Vérification finale à `b4fafd9` : 465 tests Node, 2057 tests Python (8 déselectionnés), auto-test gate local PASS, test PHP de relais 8/8. Statut conservé `review`.

- 2026-10-06 — Reprise X5 (modèle `claude-sonnet-5`) : relecture indépendante de la PR #210, 5 points traités, tests avant chaque commit. Point 1 : le lien ↺ de ligne (`.mo-revert-cmd`) appelait `revertPublication` (retrait complet de publication de l'entité) au lieu de `revertCommand` (retrait du seul override de TYPE, route 16-8, AC5) — corrigé, nouveau harnais `node:vm` dédié à ce lien et au reste du comportement de confirmation (`tests/unit/test_story_20_2_p1_p2_comportement_surface.node.test.js`). Point 2 : `shouldConfirmPublication` ne regardait que l'entité principale pour l'exclusion d'équipement — une entité secondaire déjà publiée (ex. capteur de conso) s'excluait donc sans confirmation (AC5 non respecté) ; ajout de `shouldConfirmEquipmentExclude`/`entitiesLeavingHomeAssistant` (override.js) et de la modale dédiée listant les entités qui quitteraient Home Assistant (surface.js). Point 3 (backend) : l'aperçu de forçage à la portée équipement n'exposait que l'entité principale (`over_target`) — ajout du champ additif `entities[]` dans `_handle_overrides_preview`, même vue que l'arbre (`_decision_view`), consommé par `equipmentForcePreviewState`/`buildEquipmentForcePreviewContent` pour que la modale liste chaque entité touchée par le forçage. Point 5 (backend) : `_handle_mapping_override_revert` (portée commande) sur un équipement devenu inéligible (`evaluation.mapping is None`) construisait `mappings = [None]` puis plantait sur `mapping_cmd_ids(None)` (500) au lieu du 409 « Commande sans entité » attendu (CC-19) — parenthèse de garde corrigée. Nouveaux tests ciblés : `resources/daemon/tests/unit/test_story_20_2_relecture_independante_pr210.py` (3 cas, preview portée équipement/entité, revert 409). Parcours gate `exclusion-publication-non-publiee.mjs` élargi pour couvrir l'absence de confirmation sur équipement non publié puis le retrait (déjà en place, vérifié toujours valide avec ces changements). Vérification finale : 470 tests Node (`tests/unit/*.node.test.js`), 1442 tests Python (`pytest`, 8 déselectionnés). Statut conservé `review`.

- 2026-10-06 — Reprise X5b (session détachée, non visible dans ce journal avant X5c) : a produit les commits `5aa1b16` (démon : `entities[]` dans l'aperçu équipement, 409 sur revert d'équipement inéligible, points 3 et 5 ci-dessus) et `0c9131b` (interface : lien ↺ de ligne sur `revertCommand`, confirmation d'exclusion d'équipement dès qu'une entité secondaire est publiée, points 1/2/4) sans les pousser, et sans écrire le rapport ni lancer la suite Python complète (1442/2060 tests). Ces deux commits sont ceux repris ci-dessus par X5c.
- 2026-10-06 — Reprise X5c (modèle `claude-sonnet-5`, session détachée sans mémoire) : pousse immédiatement les 3 commits locaux laissés par X5b (`5aa1b16`, `0c9131b`, `faaf4a3`). Inventaire des 6 points de la relecture indépendante PR #210 : points 1, 2, 4, 5 entièrement faits par X5b (vérifiés par lecture de code et des tests existants) ; point 3 **en partie fait seulement** — le démon renvoyait bien `entities[]` (commit `5aa1b16`), mais `equipmentForcePreviewState`/`buildEquipmentForcePreviewContent` (override.js/surface.js) n'étaient jamais appelés : `requestPublication` utilisait toujours `forcePreviewState` (entité principale seule) même à la portée équipement, donc la modale de forçage d'équipement ne listait toujours qu'une entité — corrigé (commit `5879d2b`) en branchant les deux fonctions sur `equipment === true`. Point 6 **non fait** (aucun harnais `$.ajax`/`bootbox.dialog` ne couvrait Forcer, ni `applyEquipment`) : 6 nouveaux tests ajoutés dans `test_story_20_2_p1_p2_comportement_surface.node.test.js` (même commit `5879d2b`) — Forcer aux deux portées (paramètres AJAX, aperçu accepté/refusé/erreur démon 409/`.fail` réseau, clic Confirmer déclenchant la pose réelle), et `applyEquipment` (succès avec rechargement, erreur démon sans rechargement). Le test « portée équipement » a d'abord échoué contre le code non corrigé, prouvant le bug avant le fix. Puis fusion de `origin/main` (CC-43, PR #211, déjà fusionnée) : un seul conflit, dans `tests/e2e/gate/interceptor-selftest.mjs`, résolu en gardant `FORBIDDEN_ACTIONS` remontée en tête de fichier par `main` et en y ajoutant `savePublicationOverride`/`revertPublicationOverride` qu'une duplication locale du set portait (commit de fusion `5c67bcd`) ; `run-gate.mjs` et `test_story_20_0_gate_runner.node.test.js` ont fusionné sans conflit. Vérification finale à `5c67bcd` : 478 tests Node (`tests/unit/*.node.test.js`), 2060 tests Python (`pytest -m "not load"`, 8 déselectionnés), test PHP de relais 8/8, auto-test gate local **10/10 PASS (0 échec)**. Statut conservé `review`. Aucun déploiement, sync, « Publier » ni appel box/Jeedom/démon/HA effectué.
- 2026-10-06 — Reprise X5d (modèle `claude-sonnet-5`, session détachée sans mémoire, à partir de `6458d7c`) : relecture indépendante de la PR #210, un dernier point 2 et deux points P3 traités, un commit par point, poussés immédiatement. Point 1 (`b19412d`) : le parcours gate `exclusion-publication-non-publiee.mjs` lisait l'état de l'interface (nombre d'entités, boutons, absence de modale) avant que la relecture asynchrone `getMappingOverrides` déclenchée par le dépliage/rechargement n'ait eu lieu — course contre la vraie page. Remplacé par une attente de la première ligne d'entité (bornée, 10s) puis par `waitForJournal` (séquence ordonnée écriture puis relecture dérivée/plate) et `waitForActionButtonState` (`page.waitForFunction` scopé par `data-eq-id`) avant toute assertion sur les boutons ou l'absence du bouton « Confirmer ». Point 2 (`0f6b158`) : le lien ↺ de ligne (`renderCommandRow` → `revertCommand`) devenait inerte après un échec — `.off('click')` sans jamais être réattaché, et aucun gestionnaire d'erreur sur la requête. Remplacé par `.one('click', ...)` réarmé par une fonction `attachRevertHandler` rappelée en cas d'échec (démon ou réseau), affichage de la cause via un nouveau slot `.mo-revert-error` (réutilise `readPublicationRequestError`), aucun rechargement en cas d'échec. Nouveau harnais `node:vm` dédié (`test_story_20_2_p3_revert_cmd_inerte.node.test.js`) chargeant l'extrait réel du fichier pour cliquer le vrai lien généré par `renderCommandRow` (jamais `revertCommand` appelé directement) — 3 tests : succès, erreur démon avec réessai réussi, erreur réseau. Point 3 (`9782632`) : à la portée équipement, l'aperçu de forçage (`equipmentForcePreviewState`) activait « Confirmer » dès qu'une entité était éligible dans l'aperçu démon, sans jamais comparer à son état déjà publié dans l'arbre reçu — une entité déjà publiée qui le resterait n'est pas un changement dû à CE forçage. Ajout de `findCurrentEntity` (appariement par `command_ids` partagés) ; chaque entité est désormais classée « déjà publiée », « sera publiée » (transition réelle) ou « ne sera pas publiée : cause » ; `can_confirm` n'est vrai que si au moins une entité transite de non publiée à publiée, sinon `refusal_reason` l'indique explicitement. 4 nouveaux tests dans `test_story_20_2_publication_surface.node.test.js` (déjà publiée sans changement, transition réelle, mix sans transition, entité absente de l'arbre courant traitée comme non publiée). Vérification finale à `9782632` : 485 tests Node (`tests/unit/*.node.test.js`), 2060 tests Python (`pytest -m "not load"`, 8 déselectionnés), test PHP de relais 8/8, auto-test gate local **5×5 PASS (0 échec)**. Statut conservé `review`. Aucun déploiement, sync, « Publier » ni appel box/Jeedom/démon/HA effectué.
- 2026-10-06 — Reprise X5e (modèle `claude-sonnet-5`, session détachée sans mémoire, à partir de `3edde11`) : dernier point P3 de la PR #210 puis fusion de `main`. Point P3 (`1743e91`) : `findCurrentEntity` (override.js) associait une entité de l'aperçu de forçage équipement à la PREMIÈRE entité de l'arbre partageant AU MOINS UNE commande — une entité secondaire partageant une commande d'action avec la principale (même ensemble non strictement égal) pouvait donc être lue sur l'état publié de la principale (« sera publiée » affiché à tort, ou « Confirmer » grisé à tort). Appariement réécrit en deux temps : d'abord par ensemble complet de `command_ids` identique (`sameCommandIdSet`, ordre indifférent), puis à défaut par même position + même `ha_entity_type` (le démon rend arbre et aperçu dans le même ordre, principale puis secondaires) ; aucune correspondance sur ces deux critères → entité traitée comme absente de l'arbre (non publiée), comme avant. Nouveau test dans `test_story_20_2_publication_surface.node.test.js` avec une commande d'action partagée entre deux entités de types différents, prouvant l'absence de confusion. Fusion de `origin/main` (`4714216`, PR #212 déjà fusionnée dans `main`) : aucun conflit (la branche ne touche pas `rescan-page-principale.mjs`), aucun marqueur `<<<<<<<`/`>>>>>>>` résiduel. Vérification finale à `4714216` : 486 tests Node (`tests/unit/*.node.test.js`), 2060 tests Python (`pytest -m "not load"`, 8 déselectionnés, `220.35s`), test PHP de relais 8/8, auto-test gate local **5×5 PASS (0 échec)**. Statut conservé `review`. Aucun déploiement, sync, « Publier » ni appel box/Jeedom/démon/HA effectué.
- 2026-10-06 — Reprise X6 (modèle `claude-sonnet-5`, session détachée sans mémoire, à partir de `a7a0c82`) : AC8 non tenu à l'écran, constat de la validation UX ClaudeBox du 06/10 (box en `d2bf697`) sur les eq 588-591 (pièce 0, « Sans pièce ») — un équipement exclu sans commande affichait toujours « Aucune commande projetable en Home Assistant pour cet équipement. » alors que le démon porte déjà la décision (`equipment_decision.publication_reason: "excluded_plugin"`, `should_publish: false`). Cause : `summarizePublication` (override.js) ne compte que les commandes de `tree.commands` ; un arbre sans commande ne pouvait donc jamais déclencher la branche « Exclu »/« Désactivé », même avec une `equipment_decision` qui l'indiquait. Correctif : quand `commands.length === 0`, `summarizePublication` lit `equipment_decision` via les mêmes fonctions déjà utilisées par commande (`isExcludedDiagnostic`, `isDisabledDiagnostic`), sans recalcul — lecture pure de la décision du démon. Nouveau fichier de tests (rouge avant, vert après) : 4 raisons d'exclusion testées (`excluded_plugin`, `excluded_eqlogic`, `excluded_object`, `publication_excluded_eqlogic`) → « Exclu », `disabled_eqlogic` → « Désactivé » (comportement existant), `equipment_decision` absent ou sans exclusion (`no_commands`) → « Aucune commande projetable » inchangé, et non-régression sur des arbres avec commandes (prêtes, bloquantes, exclues). Vérification finale à `a7a0c82` + ce commit : 496 tests Node (`tests/unit/*.node.test.js`), 2060 tests Python (`pytest`, 8 déselectionnés, `222.24s`), auto-test gate local **3×3 PASS (0 échec)**. Statut conservé `review`. Aucun déploiement, sync, « Publier » ni appel box/Jeedom/démon/HA effectué.
- 2026-10-06 — Reprise X6b et X6c (modèle `claude-sonnet-5`, sessions détachées sans mémoire, à partir de `2bc6895` jusqu'à `69885e4`) : relecture indépendante de la PR #215 sur le correctif X6 (AC8), P2 préexistant de 20-2 traité sur deux points. Sur un équipement **inéligible** (ex. eq 588-591, `publication_reason: "excluded_plugin"`, `entities: []`, `commands: []`), « Exclure » restait actif à côté du badge « Exclu » (clic sans effet, `evaluate_equipment` refuse l'inéligible avant toute exclusion) et « Revenir au mode automatique » restait grisé même avec un override d'équipement déjà posé (AC1/AC6 non tenus) ; même trou pour tout équipement éligible sans entité. Point 1 (X6b, `2bc6895`) : le démon ajoute `eligible` et `equipment_publication_override` à la racine de l'arbre GET (`_build_mapping_override_tree`, `http_server.py:3076`), lus dans la même source que `evaluate_equipment` (jamais recalculés) ; 3 tests Python ciblés (inéligible sans override, inéligible avec override d'équipement persisté, éligible avec exclusion d'équipement sans entité) ; garde-fou de parité JSON amendé pour ces deux ajouts additifs. Point 2 (X6b) : relais PHP vérifié — `getMappingOverrides` transmet l'arbre tel quel, aucune clé filtrée, aucun changement nécessaire (8/8 PHP toujours vert). Point 3 (X6c, `69885e4`) : côté interface, `normalizeTree` (override.js) lit les deux champs (repli `eligible: true` et `equipment_publication_override: null` sur un démon plus ancien, énumération stricte `exclude`/`force_publish`) ; nouvelle fonction `equipmentPublicationTarget(tree)` construit la cible équipement en combinant le veto porté par les entités/commandes ET l'override d'équipement persisté ; `publicationActionState` grise « Exclure »/« Forcer » dès que `eligible === false` à la portée équipement (info-bulle dédiée « non éligible »/« sans effet »), tout en gardant « Revenir » actif si un override existe déjà à retirer — la portée entité n'est jamais concernée par ce gate. `renderEquipmentTree` (surface.js) appelle `equipmentPublicationTarget` au lieu de la construction inline historique. 13 nouveaux tests Node (`test_story_20_2_x6b_equipment_eligibility.node.test.js`, écrits avant l'implémentation par X6b). P3 de la même relecture (test X6 `publication_excluded_eqlogic` sans commande) : conservé comme cas défensif — décrit un état que le démon ne produit pas actuellement (une exclusion de commande sans aucune commande dans l'arbre), mais protège contre une régression si cette combinaison apparaissait. Vérification finale à `69885e4` : 508 tests Node (`tests/unit/*.node.test.js`), 2063 tests Python (`pytest`, 8 déselectionnés, `218.79s`), test PHP de relais 8/8, flake8 propre sur les fichiers Python touchés, auto-test gate local **3×3 PASS (0 échec)**. Statut conservé `review`. Aucun déploiement, sync, « Publier » ni appel box/Jeedom/démon/HA effectué.

### File List

- tests/unit/test_story_20_2_publication_surface_ui.node.test.js
- tests/unit/test_story_20_2_php_relay.php
- resources/daemon/models/decide_publication.py
- resources/daemon/models/evaluate_equipment.py
- resources/daemon/mapping/switch.py
- resources/daemon/mapping/light.py
- resources/daemon/mapping/cover.py
- resources/daemon/mapping/overrides.py
- resources/daemon/tests/unit/test_story_16_3_publication_override.py
- _bmad-output/planning-artifacts/pipeline-contract.md
- resources/daemon/transport/http_server.py
- core/ajax/jeedom2ha.ajax.php
- resources/daemon/tests/unit/test_story_20_2_publication_routes.py
- resources/daemon/tests/unit/test_story_19_3_p2_shared_command_priority.py
- resources/daemon/tests/unit/test_story_19_3_ac6_sync_status.py
- resources/daemon/tests/unit/test_story_19_3_guardrail_no_override_json_parity.py
- resources/daemon/tests/unit/test_story_16_5_mapping_override_ui_endpoints.py
- resources/daemon/tests/unit/test_story_16_6_preview_dry_run.py
- desktop/js/jeedom2ha_mapping_override.js
- desktop/js/jeedom2ha_mapping_surface.js
- tests/unit/test_story_20_2_publication_surface.node.test.js
- tests/e2e/gate/lib/policy.mjs
- tests/e2e/gate/lib/interceptor.mjs
- tests/e2e/gate/lib/simulate.mjs
- tests/e2e/gate/interceptor-selftest.mjs
- tests/e2e/gate/run-gate.mjs
- tests/e2e/gate/parcours/decouverte-garage-enphase.mjs
- tests/e2e/gate/parcours/reference-bascule-enphase.mjs
- tests/e2e/gate/parcours/controle-ecriture-non-declaree.mjs
- tests/e2e/gate/parcours/exclusion-publication-non-publiee.mjs
- tests/unit/test_story_20_0_gate_policy.node.test.js
- tests/unit/test_story_20_0_gate_runner.node.test.js
- tests/unit/test_story_20_2_p1_p2_comportement_surface.node.test.js
- resources/daemon/tests/unit/test_story_20_2_relecture_independante_pr210.py
- tests/unit/test_story_20_0_gate_simulate.node.test.js
- tests/unit/test_story_20_2_p3_revert_cmd_inerte.node.test.js
- tests/unit/test_story_20_2_ac8_exclu_sans_commande.node.test.js
- resources/daemon/tests/unit/test_story_20_2_x6b_eligible_equipment_override.py
- tests/unit/test_story_20_2_x6b_equipment_eligibility.node.test.js
