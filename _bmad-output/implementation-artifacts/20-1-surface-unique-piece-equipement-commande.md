# Story 20.1 : Surface unique pièce → équipement → commande

Status: draft

## Story

En tant qu'utilisateur du plugin,
je veux une surface unique pièce → équipement → commande,
afin de lire et régler le mapping HA sans navigations concurrentes.

## Contexte et périmètre

- Cette story remplace l'affichage de navigation 16-8 et celui de la synthèse « Parc global » ; la suppression effective de cette synthèse et de la modale diagnostic reste à 20-3.
- L'exclusion et le forçage restent à 20-2. Le rescan reste à 20-4.
- La forme retenue par défaut est une surface en page, organisée par pièce, équipement puis commande. Cette recommandation reste à valider par Alex (voir Questions UX).
- Les décisions viennent exclusivement de `evaluate_equipment()` via l'arbre déjà construit par le démon. L'UI ne réévalue aucune décision de publication.

## Acceptance Criteria

1. **Surface unique (dépend de Q1).**
   - **Given** la page principale du plugin ouverte
   - **When** l'utilisateur consulte le mapping HA
   - **Then** une seule surface en page présente pièce → équipement → commande, sans renvoyer vers une autre navigation pour ce même affichage.
   - **And** la navigation par cartes/modale de 16-8 n'est plus l'affichage de référence.
   - **And** la synthèse « Parc global » et la modale diagnostic distincte restent présentes jusqu'à 20-3, sans être supprimées par cette story.

2. **Organisation du bloc Gestion.**
   - **Given** la surface est rendue dans la page principale
   - **When** l'utilisateur atteint le bloc « Gestion »
   - **Then** « Ajouter », « Configuration » et « Diagnostic » restent groupés sous son titre, avant ou après la surface selon Q1, jamais séparés de ce titre.

3. **Pièces et équipements complets (dépend de Q3 et Q4).**
   - **Given** l'arbre Jeedom est disponible
   - **When** la surface liste les pièces
   - **Then** elle conserve l'ordre natif, sauf choix UX explicite contraire.
   - **And** elle rend tous les équipements non-`jeedom2ha`, actifs comme désactivés.
   - **And** les équipements sans pièce sont rendus sous « Sans pièce », dernier élément de la liste.

4. **Diagnostic borné.**
   - **Given** aucune pièce n'est ouverte
   - **When** la page s'affiche
   - **Then** aucun diagnostic de tous les équipements n'est chargé.
   - **When** l'utilisateur ouvre une pièce
   - **Then** un arbre de mapping est lu pour chacun de ses équipements seulement, afin d'afficher leurs états sans dépliage supplémentaire.

5. **États par commande, sans recalcul UI.**
   - **Given** l'arbre de mapping d'un équipement reçu
   - **When** une commande est rendue
   - **Then** son état provient exclusivement de la décision fournie par le démon : prête, bloquante avec le pourquoi, non couverte grisée et jamais bloquante, ou exclue grise et jamais bloquante.
   - **And** l'UI ne refait aucun calcul de publication, de couverture ou de priorité.
   - **And** une commande non couverte ou exclue ne propose pas de sélecteur de type, ou présente un sélecteur désactivé avec une explication claire (dépend de Q2).

6. **Édition du type HA sans régression.**
   - **Given** une commande couverte et non exclue
   - **When** l'utilisateur choisit un type HA
   - **Then** un aperçu sans persistance est demandé.
   - **And** si l'aperçu est vert, l'override est enregistré automatiquement puis l'équipement est relu.
   - **And** l'utilisateur peut revenir au mode automatique par commande et par équipement.
   - **And** aucun chemin ne modifie le `generic_type` natif Jeedom.

7. **Limites de périmètre.**
   - **Given** l'interface 20-1 livrée
   - **When** l'utilisateur cherche une exclusion, un forçage ou un rescan
   - **Then** aucune nouvelle action de ce type n'est ajoutée par cette story.
   - **And** aucune suppression effective de la synthèse « Parc global » ou de la modale diagnostic distincte n'est faite avant 20-3.

8. **Preuve de fin.**
   - **Given** l'implémentation terminée et prête à validation UX
   - **When** son `done` est évalué
   - **Then** les parcours `decouverte-garage-enphase.mjs` (lecture seule) et `reference-bascule-enphase.mjs` (bascule simulée) du gate 20-0 passent sur le code de `main`.
   - **And** un déploiement standard et une preuve terrain discriminante sont consignés pour le SHA exact déployé.
   - **And** le statut passe par `ready-for-UX-validation` avant `done`.

## UI Impact

- **UI Impact : Oui.** Cette story modifie la page principale, le rendu de la navigation et les interactions visibles.

## Tasks / Subtasks

- [ ] Task 1 — Cadrer puis remplacer la structure de surface (AC: 1, 2, 3, 7)
  - [ ] 1.1 — Obtenir la décision Alex pour Q1 à Q4 ; reporter les choix dans la story avant développement.
  - [ ] 1.2 — Réorganiser la page pour ne plus séparer le titre « Gestion » de ses trois actions.
  - [ ] 1.3 — Remplacer la navigation cartes/modale de 16-8 par la surface unique retenue, sans retirer la synthèse ou la modale réservées à 20-3.
  - [ ] 1.4 — Inclure actifs, désactivés et « Sans pièce » selon les règles validées.

- [ ] Task 2 — Rendre l'arbre de décision (AC: 3, 4, 5)
  - [ ] 2.1 — Préserver l'ordre validé, puis charger le diagnostic uniquement à l'ouverture d'une pièce.
  - [ ] 2.2 — Consommer l'arbre `GET /system/mapping_overrides/{eq_id}` et ses décisions ; ne créer aucun recalcul UI.
  - [ ] 2.3 — Conserver exactement les quatre états et leurs exclusions de compte/ancre.

- [ ] Task 3 — Préserver l'édition HA (AC: 5, 6)
  - [ ] 3.1 — Réutiliser le contrôleur et le module pur d'override, avec aperçu, enregistrement automatique et retours au mode automatique existants.
  - [ ] 3.2 — Désactiver ou ne pas rendre le sélecteur sans effet des commandes exclues ou non couvertes, avec explication conforme à Q2.
  - [ ] 3.3 — Ajouter les tests ciblés des quatre états, du contrôle d'édition et de l'absence de mutation du type natif.

- [ ] Task 4 — Vérifier la source des équipements désactivés (AC: 3)
  - [ ] 4.1 — Vérifier par test que l'appel actuel `eqLogic::byObjectId($object->getId())` inclut les équipements désactivés ; le code lu ne passe aucun paramètre d'inclusion explicite.
  - [ ] 4.2 — Si cet appel les écarte, appliquer le contrat Jeedom approprié et couvrir le cas par test. Si non, documenter la preuve de non-régression.

- [ ] Task 5 — Prouver la surface (AC: 8)
  - [ ] 5.1 — Exécuter les parcours 20-0 lecture seule et bascule simulée après intégration sur `main`, conformément au gate.
  - [ ] 5.2 — Déployer par le flux standard le SHA relu, puis relever une preuve terrain discriminante avant/après.
  - [ ] 5.3 — Obtenir la validation UX et enregistrer `ready-for-UX-validation` avant toute clôture `done`.

## Dev Notes

### Contrats à réutiliser

- `desktop/php/jeedom2ha.php:14-36` construit `j2haRoomsTree` depuis `jeeObject::buildTree(null, false)` et `eqLogic::byObjectId(...)`, exclut le type `jeedom2ha`, et transmet `enabled`. L'appel lu ne précise pas si les désactivés sont inclus : à vérifier (Task 4).
- `desktop/js/jeedom2ha_mapping_surface.js:328-345` lit un équipement avec l'action AJAX `getMappingOverrides`; `:437-446` limite la lecture aux équipements de la pièce ouverte.
- `core/ajax/jeedom2ha.ajax.php:864-875` relaie cette action sur `GET /system/mapping_overrides/{eq_id}` ; la route est déclarée dans `resources/daemon/transport/http_server.py:4351-4355`.
- L'arbre démon appelle `evaluate_equipment()` à `resources/daemon/transport/http_server.py:2900-2907` et porte `covered` par commande aux lignes `2927-2940`. Réutiliser cette sortie ; interdiction de rejouer la décision côté JS.
- Les états non couvert/exclu sont déjà distingués dans `desktop/js/jeedom2ha_mapping_override.js:400-509` et stylés dans `desktop/css/jeedom2ha.css:131-139, 168-187`.
- L'aperçu, la persistance automatique et les retours existants sont dans `desktop/js/jeedom2ha_mapping_surface.js:141-210`; les routes AJAX correspondantes sont dans `core/ajax/jeedom2ha.ajax.php:877-918`.

### Fichiers probablement touchés

- `desktop/php/jeedom2ha.php` — structure, arbre pièces et position du bloc Gestion.
- `desktop/js/jeedom2ha_mapping_surface.js` — rendu de la surface, chargement borné et contrôle de sélecteur.
- `desktop/js/jeedom2ha_mapping_override.js` — seulement si une normalisation/règle d'affichage manque ; pas de décision de publication.
- `desktop/css/jeedom2ha.css` — styles de la nouvelle structure et des contrôles désactivés.
- `tests/unit/test_story_16_8_mapping_surface.node.test.js` et tests ciblés nouveaux si nécessaires.
- `tests/e2e/gate/parcours/decouverte-garage-enphase.mjs` et `reference-bascule-enphase.mjs` — adapter les attentes au parcours retenu.

### Interdits et garde-fous

- Ne pas modifier `generic_type` : le type natif reste en lecture seule.
- Ne pas ajouter exclusion, forçage, rescan, ni suppression effective de la synthèse/modale : ces périmètres sont affectés aux stories 20-2, 20-4 et 20-3.
- Ne pas charger les diagnostics de tout le parc.
- Ne pas remplacer `evaluate_equipment()` par une agrégation ou une règle de décision côté UI.
- Conserver les contrats AJAX et démon existants sauf nécessité démontrée par un test ; aucun nouveau backend override n'est prévu.

## Questions UX pour Alex

**Q1 — Forme et place de la surface (AC 1, 2).**

1. Arbre en page, sous le bloc Gestion complet — coût faible, navigation continue, recommandation : évite la modale et corrige directement la coupure du bloc Gestion.
2. Arbre en page, après la synthèse temporaire — coût faible, mais deux lectures de parc concurrentes jusqu'à 20-3.
3. Modale par pièce conservée — coût faible, mais ne répond pas clairement à « une seule surface » et garde le changement de contexte.

**Recommandation : option 1.** Les actions de Gestion restent près de leur titre ; la surface devient l'entrée de lecture principale.

**Q2 — Sélecteur sur commande exclue ou non couverte (AC 5).**

1. Ne pas afficher le sélecteur — coût moyen, état le plus clair, mais colonnes visuellement hétérogènes.
2. Afficher un sélecteur désactivé avec la raison — coût faible, table stable et explique pourquoi l'action est sans effet.
3. Garder le sélecteur actif — coût nul, mais reproduit le constat UX du 05/10.

**Recommandation : option 2.** Le contrôle reste reconnaissable sans suggérer une action inopérante.

**Q3 — Compteurs qui remplacent à terme « Parc global » (AC 1, 3).**

1. Compteurs par pièce dans l'arbre, calculés à partir des décisions déjà reçues — coût moyen, contextualisés ; recommandation.
2. Un bandeau global au-dessus de l'arbre — coût moyen, compact, mais réintroduit une mini-synthèse concurrente.
3. Aucun compteur avant 20-3 — coût faible, mais perte de repère pendant la transition.

**Recommandation : option 1.** Elle prépare le remplacement de 20-3 sans créer une seconde vue globale.

**Q4 — Présentation des désactivés et ordre (AC 3).**

1. Garder l'ordre natif, afficher « désactivé » et un style atténué — coût faible, recommandation ; cohérent avec les données actuelles.
2. Regrouper les désactivés en fin de chaque pièce — coût moyen ; plus lisible mais modifie l'ordre natif.
3. Masquer les désactivés — hors périmètre : contredit CC-25.

**Recommandation : option 1.** Elle rend le parc fidèle sans imposer une hiérarchie supplémentaire.

## Définition de done

- Prérequis : 20-0 et 16-8 sont `done`.
- Les AC sont vérifiés par tests ciblés et la File List est complète.
- Les deux parcours obligatoires du gate 20-0 passent sur le code de `main` : découverte lecture seule et bascule simulée.
- Le déploiement standard porte le SHA exact relu ; la preuve terrain est discriminante et consigne les relevés avant/après.
- Une validation UX est obtenue dans l'environnement concerné ; la story passe par `ready-for-UX-validation` avant `done`.
- Le passage `done` consigne SHA, CI, commandes de tests nommées, validation UX et environnement, conformément à la rétrospective epic 19.

## References

- [Source : `_bmad-output/planning-artifacts/epics-projection-engine.md`, Epic 20, lignes 2410-2455]
- [Source : `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-01-etape-4-interface.md`, décisions 1 à 7 et « Risques et suivi », lignes 32-72]
- [Source : `_bmad-output/implementation-artifacts/16-8-surface-navigation-piece-equipement-commande-homebridge.md`, AC et File List, lignes 21-80 et 146-206]
- [Source : `_bmad-output/implementation-artifacts/16-8-validation-ux-2026-10-05.md`, constats reportés, lignes 30-33]
- [Source : `_bmad-output/implementation-artifacts/20-0-gate-preuve-ux-outille.md`, AC3 et AC5]
- [Source : `_bmad-output/implementation-artifacts/20-0-gate-2026-10-04.md`, preuve retenue et parcours]
- [Source : `_bmad-output/implementation-artifacts/pe-epic-19-retro-2026-10-01.md`, leçons, lignes 73-84]

## Dev Agent Record

### Agent Model Used

Codex (création documentaire).

### Completion Notes List

- 2026-10-05 — `create-story` exécuté en mode non interactif. Statut volontairement `draft` pour relecture ClaudeBox. Aucune tâche de développement, test, gate, déploiement ni modification de `sprint-status.yaml` n'a été exécuté par cette unité.

### File List

- `_bmad-output/implementation-artifacts/20-1-surface-unique-piece-equipement-commande.md`
