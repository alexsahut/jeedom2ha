# Story 20.2 : Exclusion et forçage depuis la surface (CC-26)

Status: draft

## Story

En tant qu'utilisateur du plugin,
je veux exclure, forcer ou retirer un override de publication depuis la surface pièce → équipement → commande,
afin de reprendre la main de façon visible, réversible et sans modifier Jeedom.

**Parcours : complet.** Gate 20-0, déploiement standard, preuve terrain qui écrit, `ready-for-UX-validation`, puis `done`.

## Contexte et périmètre

- 20-1 est `done`. La surface par pièce est le seul point d'édition.
- L'action porte l'exclusion et le forçage sur un équipement ou une commande. La pièce reste dans la liste d'exclusions de la configuration.
- Le retour au mode automatique est une vraie purge, prouvée par clic réel ; le gate 20-0 simule toutes les écritures.
- CC-26 n'est fermé que si les cas réels `ambiguous_skipped` sont traités selon une décision d'Alex.
- Hors périmètre : suppression de « Parc global » et jargon (20-3), rescan (20-4), documentation utilisateur finale (20-5).

## Décisions attendues d'Alex

Les AC marqués **[Dépend de Qx]** appliquent la recommandation ci-dessous. Ils seront confirmés avant `dev-story`.

### Q1 — Cas `ambiguous_skipped` (17 connus au 2026-10-01)

1. **Évolution de sémantique.** Le forçage peut lever le niveau 1 `ambiguous_skipped`, après validation HA. Coût : changer l'ordre de décision et les invariants ; risque le plus élevé de publier une mauvaise entité. Tests : ambigu forcé valide/invalide, scope, exclusion, régression I2/I4.
2. **Forçage borné.** Le forçage reste après le niveau 1. L'interface dit explicitement qu'il ne traite pas les mappings ambigus. Coût réduit ; aucun risque nouveau pour ces 17 cas ; CC-26 les traite par refus explicite et action orientée type.
3. **Override TYPE d'abord.** L'utilisateur choisit un type HA ; si le mapping devient non ambigu, la décision habituelle ou le forçage s'applique. Coût : vérifier si le mapper peut réellement lever l'ambiguïté, sinon aucun bénéfice ; risque borné par validation HA.

**Recommandation : 2 maintenant, avec 3 seulement si un relevé démontre un effet réel.** Le code actuel refuse l'ambiguïté avant `force_publish` (`decide_publication.py:94-97`, `:134-143`) ; changer cela serait une évolution de sûreté à isoler et faire valider.

### Q2 — Forme des actions

1. **Actions au niveau de l'équipement et de chaque ligne de commande, confirmation pour forcer.** Coût : boutons, états et confirmations. Précis et lisible.
2. **Menu unique dans l'en-tête d'équipement.** Coût faible, mais la portée commande devient moins visible.
3. **Actions sans confirmation.** Coût faible ; risque de modification involontaire.

**Recommandation : 1.** Exclusion et forçage sont portés aux deux granularités demandées ; confirmer le forçage et l'exclusion d'un équipement, afficher la portée dans le libellé.

### Q3 — Après la pose

1. **Attendre le prochain sync, avec badge « pas encore appliqué ».** Coût faible, cohérent avec `sync_status`.
2. **Déclencher une application immédiate.** Coût et risque supérieurs : effet HA, concurrence, preuves terrain plus larges.

**Recommandation : 1.** La pose relit l'arbre et explique l'attente ; elle ne publie ni ne dépublie directement.

## Acceptance Criteria

1. **AC1 — Exclure à la portée choisie [Dépend de Q2]**
   - **Given** un équipement ou une commande affiché(e) par la surface
   - **When** l'utilisateur confirme « Exclure de Home Assistant » à cette portée
   - **Then** un override de publication `exclude` est persisté à cette seule portée et l'arbre est relu
   - **And** le diagnostic vient exclusivement de `evaluate_equipment()` ; aucun calcul de décision n'est ajouté au navigateur.

2. **AC2 — Forcer à la portée choisie [Dépend de Q1, Q2]**
   - **Given** une décision refusée mais forçable selon la politique choisie en Q1
   - **When** l'utilisateur confirme « Forcer la publication »
   - **Then** l'override `force_publish` est persisté et la cause `publication_forced` est rendue depuis l'arbre
   - **And** une projection invalide ou un type hors `PRODUCT_SCOPE` reste refusé.

3. **AC3 — Retour au mode automatique, à la bonne portée**
   - **Given** un override de publication ou de type est présent
   - **When** l'utilisateur clique « Revenir au mode automatique » sur la commande ou l'équipement
   - **Then** les overrides concernés sont retirés, sans toucher au `generic_type` Jeedom
   - **And** le clic équipement enlève aussi les overrides de type par commande, conformément à CC-19 ; aucune persistance d'override de publication ne survit à une purge totale.
   - **And** l'arbre relu porte l'état automatique issu de `evaluate_equipment()`.

4. **AC4 — `ambiguous_skipped` est traité explicitement [Dépend de Q1]**
   - **Given** les commandes réelles classées `ambiguous_skipped`
   - **When** la surface propose une action de publication
   - **Then** son texte et son activation respectent la décision Q1
   - **And** le relevé de développement recompte les cas et documente les écarts avec les 17 connus au 2026-10-01
   - **And** aucune voie ne fait passer une projection invalide ni un composant hors scope.

5. **AC5 — Diagnostics d'équipement sans commande**
   - **Given** un équipement exclu dont l'arbre ne contient aucune commande
   - **When** la surface rend cet équipement
   - **Then** elle affiche « Exclu » à partir de la décision d'équipement fournie par le démon, et non « Aucune commande projetable »
   - **And** l'interface ne déduit pas elle-même cet état des commandes.

6. **AC6 — Libellé honnête pour un mapping ambigu**
   - **Given** une commande `ambiguous_skipped` avec un `generic_type` Jeedom renseigné
   - **When** son diagnostic est rendu
   - **Then** le libellé ne dit pas de renseigner un type déjà présent
   - **And** il décrit l'ambiguïté réelle et l'action disponible selon Q1.

7. **AC7 — Routes, validations et contrat d'arbre**
   - **Given** une demande de pose ou retrait de publication
   - **When** elle traverse le relais PHP puis le démon
   - **Then** la portée, la valeur autorisée et l'existence de l'équipement/commande sont validées
   - **And** le GET d'arbre renvoie la décision équipement et les données d'override nécessaires au rendu
   - **And** preview, save et revert de TYPE gardent leur contrat.

8. **AC8 — Preuve et états BMAD**
   - **Given** le code fusionné sur `main` et déployé par la procédure standard
   - **When** le `done` est évalué
   - **Then** le gate 20-0 passe sur `main`, avec découverte et parcours déclaré qui simule pose et retrait d'un override de publication
   - **And** une preuve terrain distincte fait un clic réel de purge sur un équipement non publié, relève `getBridgeStatus` avant/après, et lance un sync correctif après retrait si le témoin a bougé
   - **And** elle n'exclut jamais un équipement publié sans GO explicite d'Alex
   - **And** la story passe par `ready-for-UX-validation` avant `done`.

## Tasks / Subtasks

- [ ] **Task 0 — Relevés préalables, lecture seule (AC: 2, 4, 5, 6)**
  - [ ] 0.1 Recompter les `ambiguous_skipped` réels et relever pour chacun la commande, le type générique et la décision ; comparer aux 17 du 2026-10-01.
  - [ ] 0.2 Relever un équipement non publié qui convient à la preuve de purge, sans poser d'override.
  - [ ] 0.3 Vérifier les textes rendus pour l'ambiguïté et l'équipement exclu sans commande.
- [ ] **Task 1 — Décision et contrat de données (AC: 2, 4, 5, 6, 7)**
  - [ ] 1.1 Appliquer Q1 dans `decide_publication()` et `evaluate_equipment()`, avec les invariants I2/I4 et le scope.
  - [ ] 1.2 Étendre l'arbre démon avec la décision équipement, la portée et l'override de publication effectif.
  - [ ] 1.3 Corriger le libellé `ambiguous_skipped` à partir de sa cause réelle, jamais d'une supposition sur `generic_type`.

- [ ] **Task 2 — Écriture et routes (AC: 1, 2, 3, 7)**
  - [ ] 2.1 Ajouter des routes démon dédiées à la publication, sans détourner silencieusement l'API TYPE.
  - [ ] 2.2 Réutiliser les CRUD publication existants et définir une purge cohérente à la commande et à l'équipement.
  - [ ] 2.3 Ajouter les actions AJAX PHP, validation stricte et erreurs lisibles.
- [ ] **Task 3 — Surface (AC: 1, 2, 3, 4, 5, 6)**
  - [ ] 3.1 Rendre les actions à la portée équipement et commande selon Q2, avec confirmation et état pendant requête.
  - [ ] 3.2 Après succès, relire seulement l'équipement ; afficher l'attente du sync selon Q3.
  - [ ] 3.3 Afficher la décision équipement de l'arbre si aucune commande n'est disponible.
- [ ] **Task 4 — Tests (AC: 1 à 7)**
  - [ ] 4.1 Tests Python : précédence, valeurs invalides, purge, Q1, I2, I4, scope et contrat d'arbre.
  - [ ] 4.2 Tests PHP/relais et Node : actions, confirmations, libellés, absence de recalcul et CC-19.
  - [ ] 4.3 Régression des routes TYPE et des commandes non couvertes/désactivées/exclues.
- [ ] **Task 5 — Gate et preuve (AC: 8)**
  - [ ] 5.1 Étendre un parcours 20-0 déclaré (`declaredBascules`, `declaredEquipments`) : pose et retrait simulés, puis DOM et journal d'interception.
  - [ ] 5.2 Après fusion : déploiement standard du SHA exact ; gate PASS sur `main`.
  - [ ] 5.3 Preuve terrain discriminante : clic réel de pose puis purge sur l'équipement non publié relevé en Task 0, témoins avant/après, et sync correctif conditionnel.
  - [ ] 5.4 Consigner le passage `ready-for-UX-validation`, la validation UX et les preuves avant `done`.

## Dev Notes

### Contrats et points de code relevés au SHA `f05dba5`

- `resources/daemon/models/decide_publication.py:94-97` refuse toute confiance hors `sure`/`probable`/`sure_mapping` ; `ambiguous` donne `ambiguous_skipped`. Le forçage actuel n'arrive qu'en `:134-143`.
- `resources/daemon/models/decide_publication.py:99-131` protège la validité projection et le scope. I2/I3/I4/I6/I7 sont documentés en `:39-43`.
- `resources/daemon/models/evaluate_equipment.py:112-126` définit `CommandDecision`. `:291-304` reçoit les calques persistés/proposés ; `:443-479` construit une décision par commande, y compris non couverte.
- `resources/daemon/mapping/overrides.py:471-516` résout déjà exclusion équipement, exclusion commande, puis forçage commande/équipement. Sa doc annonce pourtant le forçage commande ; elle doit être vérifiée et clarifiée pendant Task 1.
- `resources/daemon/mapping/overrides.py:234-315` et `:407-468` écrivent par ouverture `"w"`. Les écritures sont non atomiques.
- `resources/daemon/transport/http_server.py:2860-2958` construit le GET arbre avec `evaluate_equipment()`, mais retourne seulement commandes, `mapped` et `sync_status`, pas la décision équipement.
- `resources/daemon/transport/http_server.py:3006-3072` ne sauvegarde que le TYPE ; `:3075-3130` purge les overrides TYPE existants. Les routes enregistrées sont `:4350-4355`.
- `core/ajax/jeedom2ha.ajax.php:877-918` relaie seulement preview, sauvegarde TYPE et purge TYPE.
- `desktop/js/jeedom2ha_mapping_surface.js:97-223` rend et relit les commandes, et `:302-323` décide aujourd'hui l'affichage vide avant la synthèse.
- `desktop/js/jeedom2ha_mapping_override.js:250-293` associe `ambiguous_skipped` au texte erroné observé ; `:436-469` synthétise à partir des commandes.
- `desktop/php/jeedom2ha.php:1-57` fournit l'arbre pièce/équipement ; il ne porte aucune décision de publication.

### Garde-fous

- Consommer exclusivement la décision de `evaluate_equipment()`. Aucun recalcul de publication dans PHP ou JavaScript.
- Ne jamais écrire le `generic_type` natif de Jeedom (D10).
- Ne pas rendre le forçage comme une promesse de publication avant sync. Ne pas contourner I2, I3 ou I4.
- Préserver la précédence documentée : exclusion équipement, commande, puis forçage. Toute modification est couverte par des tests de conflit.
- Le gate 20-0 ne transmet aucune écriture. Le parcours de cette story déclare ses bascules et équipements.
- Preuve terrain : pas d'exclusion d'un équipement publié sans GO d'Alex. Témoin `getBridgeStatus` avant/après ; sync correctif après retrait si le témoin change.
- Ne pas modifier la liste d'exclusions de pièce ; elle est hors cette surface.
- Ne pas modifier `sprint-status.yaml` pendant `create-story` : ce brouillon attend la relecture ClaudeBox et le choix d'Alex.

### CC-19 et CC-34 : rattachement

- **CC-19 appartient à 20-2.** Le clic « tout l'équipement » appelle déjà le revert, mais la story doit vérifier qu'il retire également les overrides de publication ajoutés ici et tous les overrides TYPE par commande. C'est le même geste et le même contrat de purge.
- **CC-34 est une story/PR séparée et doit précéder toute preuve qui écrit.** Les quatre écritures `open(..., "w")` peuvent laisser `data/ha_overrides.json` vide à un lecteur concurrent. 20-2 augmente ces écritures depuis l'interface. Le correctif atomique doit être livré et prouvé avant la pose/purge terrain de 20-2 ; il ne doit pas être mélangé au comportement UI/CC-26.

### Project Structure Notes

- Fichiers susceptibles d'être modifiés : `resources/daemon/models/decide_publication.py`, `resources/daemon/models/evaluate_equipment.py`, `resources/daemon/mapping/overrides.py`, `resources/daemon/transport/http_server.py`, `core/ajax/jeedom2ha.ajax.php`, `desktop/js/jeedom2ha_mapping_surface.js`, `desktop/js/jeedom2ha_mapping_override.js`, CSS et tests ciblés.
- Le statut final de l'override vient du démon. Le navigateur déclenche, attend la réponse puis recharge l'équipement.
- Les routes actuellement disponibles ne posent qu'un TYPE. La forme exacte des nouvelles routes est à choisir dans l'implémentation, sous tests, sans casser les trois routes existantes.
- Non trouvé dans les routes actuelles : endpoint qui persiste un override de publication depuis la surface.

## Définition de done

- Questions Q1 à Q3 tranchées par Alex et décisions recopiées dans cette story.
- CC-34 atomique est intégré avant toute écriture terrain de cette story.
- Tous les AC et les tests ciblés sont verts ; la File List et les notes de clôture sont exactes.
- Le gate 20-0 est PASS sur le SHA de `main` et son parcours publication est déclaré.
- Le déploiement standard porte le SHA relu. La preuve terrain de pose/retrait et du clic de purge respecte les témoins et la règle d'Alex.
- La story passe par revue, `ready-for-UX-validation`, validation UX, puis seulement `done`.

## References

- [Source : Epic 20, Story 20.2 et gates] `_bmad-output/planning-artifacts/epics-projection-engine.md:2410-2449`
- [Source : décisions, risques et règle d'écriture] `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-01-etape-4-interface.md:38, 56-69`
- [Source : constat exclu sans commande] `_bmad-output/implementation-artifacts/20-1-preuve-validation-ux-2026-10-05.md:79`
- [Source : ambiguïté et 17 cas] `_bmad-output/implementation-artifacts/16-8-validation-ux-2026-10-05.md:33` ; `_bmad-output/implementation-artifacts/16-8-ac14-validation-2026-10-01.md:74-80`
- [Source : gate simulé] `_bmad-output/implementation-artifacts/20-0-gate-preuve-ux-outille.md`, « Invocation du gate par une story suivante ».
- [Source : précédent] `_bmad-output/implementation-artifacts/16-3-overrides-publication-exclusion-explicite.md` ; `_bmad-output/implementation-artifacts/19-3-surface-piece-apercu-contrat-decision-cc03-cc19.md`.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- Rapport de création : `/tmp/jeedom2ha-20-2-story-report.md`.

### Completion Notes List

- 2026-10-05 — Brouillon BMAD `create-story` produit en mode non interactif. Confirmation de finalisation du workflow : valeur par défaut appliquée et consignée au rapport.
- Le statut est volontairement `draft` et `sprint-status.yaml` est inchangé, sur instruction : relecture ClaudeBox et décisions d'Alex requises avant développement.
- Aucun code, test, gate, déploiement ou accès Jeedom/HA exécuté dans cette unité.

### File List

- `_bmad-output/implementation-artifacts/20-2-exclusion-forcage-depuis-surface-cc26.md`
