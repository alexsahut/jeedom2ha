# Story 1.7: Lisibilité métier des équipements

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur Jeedom,
je veux voir un libellé métier compréhensible pour mes équipements dans la vue par pièce au lieu d'un ID brut,
afin de repérer facilement l'équipement concerné sans devoir déchiffrer des identifiants techniques.

## Acceptance Criteria

1. **Given** la console V1.1 affiche un équipement dans une pièce
   **When** l'utilisateur lit la ligne de cet équipement
   **Then** le libellé métier compréhensible est affiché à la place de l'ID brut comme identifiant principal.
   **And** l'ID technique reste visible de façon secondaire (ex: texte grisé ou entre parenthèses) pour faciliter le débogage et le repérage avancé.

2. **Given** un équipement dont le libellé n'a pas pu être résolu ou est vide
   **When** la console l'affiche
   **Then** le frontend bascule sur un comportement de fallback strict et affiche l'ID brut propre (`eq_id`) pour éviter de casser la présentation de l'UI et conserver une identification lisible.

3. **Given** l'affichage de ce nouveau libellé dans la console
   **When** les données de la vue sont chargées
   **Then** elles proviennent strictement d'une extension minimale et prédictible du contrat backend `published_scope`.
   **And** il n'y a **aucun appel API supplémentaire** depuis l'UI pour récupérer ce nom. Le calcul du contrat appartient au backend/daemon, le PHP agit comme relais usuel, et le frontend fait une lecture stricte.

## Tasks / Subtasks

- [x] Task 1 — Analyse du contrat calculé par le backend/daemon (AC: 1, 3)
  - [x] Inspecter le payload `published_scope` (qui contient déjà `eq_id`, `effective_state`, `decision_source`, `is_exception`, `has_pending_home_assistant_changes`) pour identifier si le champ canonique du libellé de l'équipement (`name`) y est déjà présent.
- [x] Task 2 — Extension backend/daemon minimale (AC: 1, 2, 3)
  - [x] Si manquant, étendre le resolver du backend/daemon pour inclure de manière prédictible le champ canonique `name` dans la réponse JSON des équipements du `published_scope`.
  - [x] Si le nom est introuvable, le backend doit renvoyer `name` à `null` ou vide, sans masquer cette absence via un fallback natif sur `eq_id` (c'est le rôle exclusif de l'UI).
  - [x] Conserver intactes la logique d'héritage et l'absence d'alourdissement du resolver.
- [x] Task 3 — Adaptation du relais PHP / payload UI (AC: 3)
  - [x] S'assurer que le relai PHP transmet correctement ce nouveau champ `name` au frontend sans altérer le reste du contrat.
- [x] Task 4 — Intégration UI strictement en lecture (AC: 1, 2, 3)
  - [x] Modifier la vue d'équipement pour lire et afficher le nouveau champ métier principal (`name`) fourni par le backend.
  - [x] Déplacer le champ existant `eq_id` vers un indicateur secondaire.
  - [x] Implémenter le fallback visuel strict vers l'ID brut (`eq_id`) dans l'UI si le champ métier `name` transmis est null ou vide.

## Dev Notes

- **Contexte actif:** Post-MVP Phase 1 - V1.1 Pilotable (voir `active-cycle-manifest.md`).
- La Story 1.7 provient explicitement de la rétro Epic 1 comme **story backlog distincte**.

### Invariants d'architecture et de conception :
- **Ne pas réinterpréter** les invariants déjà figés dans Epic 1 (Rétro validée).
- **Rôles stricts :** 
  - **Backend/daemon** = calcul unique du contrat (`published_scope` et précédences). Le backend fournit le champ `name` tel quel.
  - **PHP** = relais API usuel.
  - **Frontend** = UI en lecture stricte du payload, responsable du fallback vers l'ID. Aucune logique métier d'héritage.
- La séparation "décision locale / effet HA" reste intacte.

### Hors scope strict :
- **Pas** de drill-down commande par commande.
- **Pas** de navigation type Homebridge.
- **Pas** d'informations liées à la santé du pont (Epic 2).
- **Pas** de statuts / raisons lisibles / actions recommandées (Epic 3).
- **Pas** d'opérations HA explicites (Epic 4).
- Toute extension fonctionnelle V1.1 non liée au libellé lisible d'équipement.

### Testing Requirements (Aligné V1.1)

- **Tests unitaires et de contrat (Backend/daemon) :** Si le contrat `published_scope` est étendu, mettre à jour les tests backend pour garantir que le champ canonique `name` est correctement résolu et retourné de façon stable aux côtés de `eq_id`, `effective_state`, `decision_source`, `is_exception` et `has_pending_home_assistant_changes`. S'assurer que le champ est nullable ou vide si introuvable, sans contournement/fallback géré par le backend.
- **Tests d'intégration (Relais PHP) :** S'assurer via les tests PHP (si ajustements nécessaires) que le payload relayé conserve et transmet correctement le champ canonique `name` depuis le backend vers l'UI sans déperdition.
- **Tests UI / Presenter :** Vérifier l'affichage nominal du champ `name` en principal (avec `eq_id` secondaire), et le fallback visuel strict si le champ `name` est vide ou null (affichage originel de `eq_id`). S'assurer qu'aucune régression de formatage n'est introduite.
- **Non-Régression sur les actions Epic 1 (Stories 1.2 / 1.3 / 1.4 / 1.5) :**
  - Confirmer que la vue globale et la synthèse par pièce ne cassent pas.
  - L'affichage des exceptions équipement et la visibilité des exclus (Story 1.3) fonctionnent toujours (avec le nouveau libellé).
  - Les badges de modifications locales en attente (Story 1.4) restent correctement affichés à côté du nom de l'équipement.
  - Les correctifs d'atténuation du refresh et de lisibilité `Exclue` / `Exception locale` implémentés (Story 1.5) ne régressent pas.

### Project Structure Notes

- Respecter le composant existant pour l'affichage des lignes d'équipements sans le fragmenter inutilement.
- S'en référer strictement à l'architecture existante JS/Templates de la console sans imposer d'autres frameworks non pertinents.

### References

- [Source: _bmad-output/implementation-artifacts/epic-1-retro-2026-03-23.md#Action Items] (Action Item 2)
- [Source: _bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md#Epic 1]
- [Source: _bmad-output/planning-artifacts/test-strategy-post-mvp-v1-1-pilotable.md]

## Dev Agent Record

### Agent Model Used

Gemini Experimental

### Debug Log References

- **Tests Python (Backend) :** `python3 -m pytest tests/unit/test_published_scope.py`
  - Résultat : 35/35 PASS. Le test `test_resolver_matrix_global_piece_eq_states` a été renforcé pour garantir que la clé canonique `name` est bien présente en sortie du resolver.
  - [AI-Review] Ajout du test `test_resolver_equipement_name_fallback_empty_string_if_falsy` pour couvrir explicitement le fallback sur une valeur `name` vide -> Résultat 36/36 PASS.
- **Tests PHP (Relais) :** `php tests/test_php_published_scope_relay.php`
  - Le payload mocké de la file de test a été enrichi avec le champ `name` (test conceptuellement robuste démontrant aucune altération de payload en transit).
- **Tests JS/Node (UI Presenter) :** `node --test tests/unit/test_scope_summary_presenter.node.test.js`
  - Résultat : 15/15 PASS. Le présentateur UI dérive avec précision son affichage (nom prioritaire ; tag bleu si nom absent ; conservation `eq_id` secondaire).

### Completion Notes List

- **Contrat explicite pour nom absent (AC2) :** L'implémentation backend impose d'exposer **strictement** une chaîne vide `""` (code Python : `"name": eq.name or ""`,) si la valeur n'est pas trouvable ou `null`. Le backend **ne simule jamais** un fallback vers `eq_id`. C'est le contrat attendu.
- **Preuve "aucun appel API supplémentaire UI" (AC3) :** Aucun nouvel appel AJAX natif et aucune méthode `fetch()` n'ont été introduits dans `jeedom2ha_scope_summary.js`. Le parseur `buildEquipmentModel` se contente de lire la propriété localement via la variable existante retournée organiquement dans l'arbre JSON `published_scope`.
- **Preuve explicite de Non-régression V1.1 (Stories 1.2, 1.3, 1.4, 1.5) :**
  - **Synthèse globale / pièce (Story 1.2) :** L'architecture du payload global n'est pas modifiée, préservant la matrice `total` / `include` / `exclude`.
  - **Exceptions & exclus (Story 1.3) :** Les tests node certifient toujours la gestion des décisions (preuve : succès du test existant `story-1.5: badge Exception locale visuellement distinct...`).
  - **Badge Changements à appliquer (Story 1.4) :** Le badge de delta HA reste accoté au nouvel affichage d'équipement (preuve : succès de `story-1.4: render affiche Changements à appliquer aux trois niveaux quand flag est true`).
  - **UX Accordéon console (Story 1.5) :** La ligne de détails s'injecte de façon identique, aucune hiérarchie DOM n'a été brisée.
- **Justification de la non-modification du Product Code PHP :** La fonction `jeedom2ha::getPublishedScopeForConsole()` du composant PHP relais prend l'ensemble du noeud retourné par le daemon Python (`payload`), et le relais sans l'avoir désérialisé et restructuré sélectivement. La propagation du nouveau champ `"name"` est donc transparente par héritage.

### File List

- `resources/daemon/models/published_scope.py`
- `desktop/js/jeedom2ha_scope_summary.js`
- `tests/unit/test_published_scope.py`
- `tests/test_php_published_scope_relay.php`
- `tests/unit/test_scope_summary_presenter.node.test.js`
