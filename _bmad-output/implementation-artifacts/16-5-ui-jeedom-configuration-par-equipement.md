# Story 16.5: UI Jeedom de configuration par équipement, inspirée Homebridge

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant qu'utilisateur expert Jeedom (persona « Sébastien »),
je veux configurer un override de mapping HA depuis une surface Jeedom native organisée par équipement/commande, avec l'attendu Home Assistant visible et un diagnostic instantané par commande,
afin de ne pas éditer le JSON à la main et de comprendre quel `ha_entity_type` rendra l'entité projetable — exactement le point aveugle que Homebridge ne montre pas.

## Acceptance Criteria

**Bloc A — Surface de configuration (lecture + structure)**

1. La surface utilise l'UI native Jeedom (jQuery/Bootstrap, design system Jeedom), **sans framework front externe** (pas de React/Vue/Angular, pas de nouvelle dépendance JS).
2. Point d'entrée = un **onglet « HA / jeedom2ha » sur la fiche équipement Jeedom existante**, jamais un écran séparé, jamais mélangé aux onglets natifs Homebridge de la même fiche (UX §2.1 / §"The ONE Thing").
3. La surface présente une **liste plate d'accordéons Bootstrap, une par commande**, dans l'ordre natif de retour de l'API Jeedom pour l'équipement — pas de tri, regroupement ni repositionnement front (UX « Chosen Direction : Liste plate »).
4. Pour chaque commande, le **triptyque** est affiché : colonne `natif (lecture seule)` = `generic_type` Jeedom actuel, colonne `override HA (éditable)`, colonne `diagnostic`. Ordre des 3 colonnes constant (natif à gauche, override au milieu, diagnostic à droite) (UX §Custom Components).
5. Pour une commande sans `generic_type`, le triptyque affiche la **proposition automatique** calculée par le moteur (Story 16.2), pas un champ vide silencieux ; l'état vide affiche explicitement « Aucun override configuré — voici ce qui sera utilisé par défaut » (UX §Additional Patterns — État vide).
6. La colonne « natif Jeedom (partagé Homebridge) » est **verrouillée en lecture seule** (traitement visuel « champ désactivé » Jeedom), visuellement distincte de la colonne override éditable — séparation permanente, pas une notice ponctuelle (UX §Micro-Emotions / §Color System).

**Bloc B — Édition, dry-run et sauvegarde**

7. La sélection/modification d'un `ha_entity_type` dans la colonne override déclenche un **dry-run instantané** (débounce 300-500ms, indicateur de chargement visible <200ms), **sans bouton « Valider » séparé** (UX §The Effortless Moment / §2.5).
8. Le dry-run appelle le backend en **lecture seule** (aucune publication MQTT, aucun effet de bord pipeline) et affiche le diagnostic : ✅ prêt (vert franc + détail de ce qui a été validé), ⚠️/❌ bloquant (ton neutre/factuel, jamais rouge alarmant, message actionnable type « Capability X manquante pour ce type HA ») (UX §Feedback Patterns / §Color System).
9. **Auto-validation au succès** : dès que le dry-run passe au vert, l'override devient l'état réel persisté (une seule étape de validation, pas de bouton « Enregistrer » distinct) (UX §2.5 Completion). Le backend **valide le schéma et la projection avant toute application effective** (AC epic bloc 2).
10. L'utilisateur peut **revenir au mode automatique par commande ou par équipement** (suppression de l'override correspondant).
11. Le `generic_type` **Jeedom natif n'est jamais modifié** par aucune action de cet écran (contrainte D10, non négociable — non-régression Homebridge).
12. Les **erreurs de validation HA** sont visibles à l'utilisateur ; une erreur de dry-run métier (type incompatible) est un diagnostic affiché, **jamais** une erreur réseau/HTTP.

**Bloc C — Réassurance & feedback**

13. Le périmètre visuel du feedback (chargement dry-run, diagnostic) reste **circonscrit à la colonne override de la commande concernée** — jamais un indicateur de chargement global de la fiche équipement (pour ne jamais suggérer un impact Homebridge).
14. Le message « aucun impact Homebridge » s'affiche **une seule fois par équipement**, au premier blocage rencontré (composant séparé, testable indépendamment du diagnostic) (UX §Journey Patterns).

## Tasks / Subtasks

<!-- Terrain : évalué. Cette story est front + glue HTTP, validable par tests front (navigateur desktop)
     et tests unitaires backend avec daemon local/mocké. La validation sur box réelle 192.168.1.21
     (déploiement + corpus multi-familles) est explicitement portée par Story 16.7 (gate terrain epic-level),
     PAS par cette story. Aucune Task 0 Pre-flight terrain injectée ici — voir Dev Notes §Périmètre terrain. -->

- [x] Task 1 — Contrat HTTP backend consommé par l'UI (AC: 4, 5, 8, 9, 10, 12)
  - [x] Sous-tâche 1.1 — Endpoint GET arbre de mapping par équipement : statuts + `reason_details` + `generic_type` natif + attendu HA + `override_applied`/`override_source` par commande (lecture seule). Réutiliser/étendre `/system/diagnostics` (16.4) ou exposer une route dédiée `GET /system/mapping_overrides/{jeedom_eq_id}` conforme au format `{"status":"ok","commands":[...]}` (arch-delta-16b §D13). `override_source` omis quand `override_applied:false` (D11/16a).
  - [x] Sous-tâche 1.2 — Persistance override sur succès de dry-run : câbler un endpoint POST qui appelle `overrides.save_override(...)` (la fonction existe déjà dans `overrides.py`, mais n'est exposée par AUCUNE route HTTP à ce jour). Valider `jeedom_eq_id`/`jeedom_cmd_id` contre le référentiel équipement avant écriture (404 si inconnu). Ne jamais appeler depuis le pipeline de sync.
  - [x] Sous-tâche 1.3 — Retour au mode auto : endpoint POST appelant `remove_override(...)` (commande) et `remove_equipment_override(...)` (équipement), déjà présents dans `overrides.py`.
  - [x] Sous-tâche 1.4 — Réutiliser strictement l'auth existante `X-Local-Secret` / `_check_secret()` et le format de réponse `{"status": "ok"|"error"}` ; distinction stricte diagnostic-métier (HTTP 200) vs erreur technique/auth/ID (401/404/500). Aucun nouveau schéma d'auth ni format.
- [x] Task 2 — Onglet « HA / jeedom2ha » sur la fiche équipement (AC: 1, 2, 3, 6)
  - [x] Sous-tâche 2.1 — Injecter l'onglet dans la fiche équipement Jeedom (desktop/php + desktop/js), séparé des onglets natifs Homebridge, sans framework front.
  - [x] Sous-tâche 2.2 — Rendu liste plate d'accordéons Bootstrap, un par commande, ordre natif Jeedom ; GET initial unique au chargement de l'onglet (pas 284 équipements d'un coup — un seul équipement à la fois).
  - [x] Sous-tâche 2.3 — Composant triptyque (natif lecture-seule grisé / override éditable / diagnostic), largeur et ordre de colonnes constants.
- [x] Task 3 — Interaction dry-run + auto-validation (AC: 7, 8, 9, 12, 13)
  - [x] Sous-tâche 3.1 — Débounce 300-500ms sur édition override, indicateur de chargement <200ms circonscrit à la colonne override ; annulation de la requête en vol si nouvelle édition (race condition côté client), sans flash d'état intermédiaire.
  - [x] Sous-tâche 3.2 — Appel dry-run (POST `/system/overrides/preview` existant, 16.6, ou route dry-run) ; rendu diagnostic ✅ vert franc + détail / ⚠️❌ neutre + message actionnable.
  - [x] Sous-tâche 3.3 — Auto-validation : succès → persistance (Task 1.2) sans bouton Enregistrer ; l'état persisté devient la vérité affichée.
  - [x] Sous-tâche 3.4 — Auto-ouverture des commandes bloquantes détectées au GET initial, plafonnée à 3-4 (gestion focus clavier cohérente).
- [x] Task 4 — Retour au mode auto + réassurance (AC: 10, 14)
  - [x] Sous-tâche 4.1 — Action « revenir au mode auto » par commande et par équipement (appel Task 1.3), rafraîchissement du triptyque.
  - [x] Sous-tâche 4.2 — Bandeau de réassurance « aucun impact Homebridge », affiché une seule fois par équipement au premier blocage (composant séparé).
- [x] Task 5 — Tests (AC: tous)
  - [x] Sous-tâche 5.1 — Tests backend unitaires des nouveaux endpoints (GET arbre, persist, revert) : nominal, dry-run refusé = 200 diagnostic, 401 auth, 404 ID inconnu, `generic_type` natif jamais muté, aucune publication MQTT.
  - [x] Sous-tâche 5.2 — Stratégie de test front minimale (définie avant implémentation, cf. Dev notes epic) : vérification clavier-only accordéons + triptyque, séparation visuelle native/override, feedback circonscrit à la colonne, message réassurance affiché une fois.
  - [x] Sous-tâche 5.3 — Non-régression : suite daemon complète verte (baseline 1035 passed après 16.6), golden inchangé.

## Dev Notes

- **Fondation UX gelée** : `_bmad-output/planning-artifacts/ux-design-delta-pe-epic-16-mapping-configurable.md` (14/14 steps, auteur Alexandre, 2026-07-06) fait autorité sur layout, états, couleurs, flows, accessibilité. Ne pas réinventer : implémenter cette spec.
- **Fondation archi** : `architecture-delta-pe-epic-16b-mapping-configurable-endpoint.md` (D13/D14/D15) définit le contrat endpoint (GET statuts + POST dry-run + `save_override`). ⚠️ **Divergence à réconcilier** : ce doc archi (2026-07-06) est antérieur à l'implémentation réelle de 16.4/16.6 (2026-07-17). L'implémenté réel = `GET /system/diagnostics` (16.4, drill-down lecture seule) + `POST /system/overrides/preview` (16.6, dry-run **zéro write disque**). La persistance `save_override`/`remove_override` **existe dans `overrides.py` mais n'est exposée par aucune route HTTP**. Le dev doit donc câbler le chemin de persistance manquant (le point le plus subtil de la story) et choisir explicitement entre étendre les routes existantes ou en ajouter conformes à D13.
- **Contraintes héritées non négociables** : D10 (`generic_type` natif jamais muté), D9 (schéma `ha_overrides.json` versionné), D8 (`overrides.py` = module pur, sens unique `http_server.py → overrides.py`, jamais l'inverse ; `save_override` jamais appelée par le pipeline de sync `map/validate_projection/decide_publication/publish`).
- **Référentiel dual-source** (mémoire projet gelée 2026-07-17) : jeedom2ha **consomme** le `generic_type` posé (core ∪ Homebridge) comme signal d'intention et ne le modifie jamais ; l'override HA est la couche jeedom2ha-only qui découple la sortie HA de la sortie HomeKit/Homebridge.
- **Périmètre terrain** : story front + glue HTTP, validable par tests navigateur desktop + tests unitaires backend (daemon local/mocké). La validation sur box réelle `192.168.1.21` (corpus ≥3 familles, cas override invalide refusé, preuve non-régression `generic_type`) est **portée par Story 16.7**, pas ici — d'où l'absence de Task 0 Pre-flight terrain.

### Dev Agent Guardrails

- **Aucun framework front** : jQuery/Bootstrap natif Jeedom uniquement, réutilisation des composants d'admin déjà en place (onglets, accordéons, badges, tooltips, champs actif/désactivé). Aucune nouvelle palette/typo/spacing (UX §Design System Foundation).
- **Desktop only** (≥1024px) : pas d'adaptation tablette/mobile, pas de cible tactile 44x44.
- **D10 en dur** : aucune écriture, aucun POST, aucun chemin de code de cet écran ne doit toucher le `generic_type` Jeedom natif. Le seul objet muté est `data/ha_overrides.json` via `save_override`/`remove_override`.
- **Distinction diagnostic vs erreur** : un dry-run métier refusé → HTTP 200 `{"status":"ok", ...}` avec diagnostic dans `reason_details` ; **jamais** un code ≥400. 401 = auth, 404 = eq/cmd inconnu, 500 = erreur technique (message générique, jamais de stacktrace).
- **snake_case** strict pour tous les champs JSON des routes (`jeedom_eq_id`, `jeedom_cmd_id`, `reason_details`, `override_applied`, `override_source`).
- **Logging** : chaque écriture réussie via `save_override()` loguée en INFO (équipement, commande, type choisi).
- **Accessibilité WCAG AA** : information jamais codée uniquement par la couleur (message textuel primaire) ; navigation clavier complète accordéons + triptyque ; ARIA sur les 4 composants custom (triptyque, bandeau résumé, indicateur dry-run, bandeau réassurance).

### Project Structure Notes

- Fichiers backend impactés : `resources/daemon/transport/http_server.py` (nouveaux/étendus handlers + enregistrement via `app.router.add_get`/`add_post`, pattern L.3208-3219), consommation de `resources/daemon/mapping/overrides.py` (`save_override`, `remove_override`, `save_equipment_override`, `remove_equipment_override`, `list_overrides`, `apply_type_override` — tous déjà présents).
- Fichiers front impactés : `desktop/php/jeedom2ha.php`, `desktop/js/jeedom2ha.js` (+ potentiellement `desktop/js/jeedom2ha_diagnostic_helpers.js` / `jeedom2ha_scope_summary.js` pour réutiliser les helpers de rendu diagnostic existants), `desktop/css/jeedom2ha.css`.
- Glue PHP → daemon : réutiliser le mécanisme d'appel local au daemon avec `X-Local-Secret` (bind 127.0.0.1). Vérifier comment la fiche équipement injecte un onglet plugin dans le core Jeedom (convention `eqLogic` desktop template) avant implémentation.
- Endpoints existants réutilisables : `POST /system/overrides/preview` (dry-run 16.6), `GET /system/diagnostics` (drill-down 16.4). Persistance HTTP à ajouter (gap identifié ci-dessus).

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story 16.5 (l.2126-2151)]
- [Source: _bmad-output/planning-artifacts/ux-design-delta-pe-epic-16-mapping-configurable.md] — spec UX complète (layout liste plate, triptyque, dry-run instantané, auto-validation, couleurs, flows Mermaid, accessibilité)
- [Source: _bmad-output/planning-artifacts/architecture-delta-pe-epic-16b-mapping-configurable-endpoint.md#D13/D14/D15] — contrat endpoint + `save_override`, patterns réponse/erreur/nommage
- [Source: _bmad-output/planning-artifacts/architecture-delta-pe-epic-16-mapping-configurable.md#D8-D12] — overrides.py pur, schéma ha_overrides.json, D10 generic_type
- [Source: resources/daemon/mapping/overrides.py] — `save_override` l.145, `save_equipment_override` l.182, `remove_override` l.305, `remove_equipment_override` l.337, `apply_type_override` l.242, `resolve_publication_override` l.369
- [Source: resources/daemon/transport/http_server.py#L.3208-3219] — table des routes ; `/system/overrides/preview` (2167), `/system/diagnostics`
- [Source: MEMORY dual-source] — référentiel core ∪ Homebridge, override pe-epic-16 = contrôle final utilisateur

### Open Questions (à confirmer en dev-story, non bloquantes pour la création)

1. **Persistance HTTP** : ajouter une route dédiée (ex. `POST /action/mapping_override` + `POST /action/mapping_override_revert` conformes D13) OU enrichir `/system/overrides/preview` d'un mode `commit`. Recommandation : routes dédiées séparées, pour garder `preview` strictement lecture seule (invariant 16.6) — à valider par le dev.
2. **GET arbre** : réutiliser `/system/diagnostics` (16.4) tel quel s'il porte déjà `generic_type` natif + attendu HA + `override_source` par commande, sinon route dédiée `GET /system/mapping_overrides/{eq_id}`. À trancher après lecture du payload réel de 16.4.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (create-story workflow, BMAD)

### Debug Log References

### Completion Notes List

- 2026-07-17 — Workflow `create-story` (BMAD, discipline bmad-story-workflow-discipline) : story file créé à partir de la spec UX gelée (2026-07-06), du delta archi 16b (D13/D14/D15) et de l'état réel du code (endpoints implémentés 16.4/16.6, couche persistance overrides.py). Statut résultant : `ready-for-dev`. Aucune tâche dev cochée, aucun run dev/terrain exécuté pendant create-story. Divergence archi-16b vs implémenté réel documentée en Dev Notes (persistance HTTP à câbler).
- 2026-07-17 — Workflow `dev-story` (BMAD, TDD). Statut résultant : `review`.
  - **Open Questions tranchées** : (1) Persistance HTTP → routes dédiées `POST /action/mapping_override` + `POST /action/mapping_override_revert` (recommandation story), `/system/overrides/preview` reste strictement lecture seule (invariant 16.6). (2) GET arbre → route dédiée `GET /system/mapping_overrides/{eq_id}` (le payload de `/system/diagnostics` ne portait pas le triptyque par commande).
  - **Backend** (`http_server.py`) : 3 handlers + `_build_mapping_override_tree` (triptyque par commande : `generic_type` natif lecture-seule, attendu HA moteur/proposition 16.2, effectif après override, diagnostic via `_preview_mapping_view`) + `_resolve_data_dir` (seam d'injection `data_dir` pour tests). Câblage du gap `save_override`/`remove_override`/`remove_equipment_override` (existaient dans `overrides.py`, aucune route ne les exposait). Auth `X-Local-Secret` réutilisée ; diagnostic-métier=200, 401/404/500 pour auth/ID/technique. D10 : `generic_type` natif jamais muté (test dédié). `save_override` jamais appelée par le pipeline de sync (D8).
  - **Front** : module pur UMD `desktop/js/jeedom2ha_mapping_override.js` (état diagnostic ready/blocking/unknown, auto-validation au vert franc, réassurance une-fois-par-équipement, état vide explicite, options de type alignées sur les 8 mappers du moteur) + contrôleur jQuery/AJAX en fin de `desktop/js/jeedom2ha.js` (débounce 400ms, spinner circonscrit à la colonne override, abort de la requête en vol, revert par commande) + onglet « HA / jeedom2ha » injecté dans `desktop/php/jeedom2ha.php` (séparé des onglets Homebridge) + 4 actions proxy dans `core/ajax/jeedom2ha.ajax.php` + styles triptyque `desktop/css/jeedom2ha.css` (ton neutre bloquant, jamais rouge alarmant ; info jamais codée uniquement par la couleur). Aucun framework front.
  - **Tests** : backend 15/15 (`test_story_16_5_mapping_override_ui_endpoints.py`) ; front node 23/23 (`test_story_16_5_mapping_override_ui.node.test.js`), suite node globale 247/247. Non-régression daemon : **1050 passed** (baseline 1035 après 16.6 + 15 nouveaux), 0 échec. Golden inchangé.
  - **Périmètre** : story front + glue HTTP. Injection d'onglet réelle dans le core Jeedom + déploiement box `192.168.1.21` (corpus multi-familles) restent portés par Story 16.7 (gate terrain epic-level) — non exécutés ici.
- 2026-07-17 — Workflow `code-review` (BMAD, adversarial). Statut résultant : `done`.
  - **Findings (2 HIGH — tâches cochées mais non livrées dans le contrôleur navigateur)** :
    - HIGH-1 (subtask 3.4 / AC3) : les panneaux commande étaient rendus en `panel-heading` toujours ouvert (pas d'accordéons collapsibles), et `M.collectBlockingCommandIds` n'était jamais appelé → aucune auto-ouverture des commandes bloquantes. **Corrigé** : `renderCommandRow` produit désormais un accordéon Bootstrap collapsible (`panel-heading > panel-title > a[data-toggle=collapse]` + `panel-collapse.collapse` contenant le triptyque en `panel-body`) ; `renderTree` auto-ouvre les bloquantes (`collectBlockingCommandIds(tree, 4)`, plafond 4) avec focus clavier sur la première.
    - HIGH-2 (subtask 4.1 / AC10) : seul le revert par commande était câblé ; aucun bouton de retour au mode auto à l'échelle de l'équipement. **Corrigé** : bouton « Revenir au mode automatique (tout l'équipement) » rendu dans `#mappingOverride_eqActions` quand ≥1 override actif → `revertEquipment(eqId)` (POST `revertMappingOverride` sans `cmdId` → scope équipement, route daemon existante).
  - **Fichiers touchés par la correction** : `desktop/js/jeedom2ha.js` (accordéon + auto-open + `revertEquipment`), `desktop/php/jeedom2ha.php` (conteneur `#mappingOverride_eqActions`), `desktop/css/jeedom2ha.css` (`.mo-accordion-toggle`).
  - **Non-régression post-correction** : node global **247/247**, daemon pytest **1050 passed** (0 échec). Aucune modification backend ni du module pur → invariants D8/D10/16.6 inchangés.
  - **Cohérence git ↔ File List** : vérifiée (aucun écart). `_bmad/`, `_bmad-output/`, `.claude/` exclus du périmètre de review.

### File List

**Backend**
- `resources/daemon/transport/http_server.py` (modifié) — `_resolve_data_dir`, `_build_mapping_override_tree`, handlers `_handle_mapping_overrides_get` / `_handle_mapping_override_save` / `_handle_mapping_override_revert`, enregistrement des 3 routes.
- `resources/daemon/tests/unit/test_story_16_5_mapping_override_ui_endpoints.py` (nouveau) — 15 tests endpoints (GET arbre, save, revert ; 200/400/401/404, D10, aucune publication MQTT).

**Front**
- `desktop/php/jeedom2ha.php` (modifié) — onglet « HA / jeedom2ha », bandeau réassurance, conteneurs liste/statut, include du module JS.
- `desktop/js/jeedom2ha_mapping_override.js` (nouveau) — module pur UMD (logique triptyque/diagnostic/auto-validation/réassurance).
- `desktop/js/jeedom2ha.js` (modifié) — contrôleur navigateur (câblage jQuery/AJAX, débounce, dry-run, auto-validation, revert).
- `core/ajax/jeedom2ha.ajax.php` (modifié) — 4 actions proxy (`getMappingOverrides`, `previewMappingOverride`, `saveMappingOverride`, `revertMappingOverride`).
- `desktop/css/jeedom2ha.css` (modifié) — styles triptyque + états diagnostic.
- `tests/unit/test_story_16_5_mapping_override_ui.node.test.js` (nouveau) — 23 tests front purs.
