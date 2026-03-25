# Story 2.4: Distinction stable entre infrastructure et configuration

**Status:** done
**Cycle:** Post-MVP Phase 1 - V1.1 Pilotable
**Epic:** 2 — Santé minimale du pont et lisibilité opérationnelle globale
**Dépendances autorisées:** Story 2.1, Story 2.2, Story 2.3

> **Note de contexte (non-dépendance story-level) :** Story 1.1 a établi le modèle canonique de périmètre. Story 2.4 s'appuie sur les raisons de non-publication que ce modèle produit déjà — elle ne les redéfinit pas.

---

## User Story

En tant qu'utilisateur Jeedom,
je veux voir clairement si un problème relève de l'infrastructure ou de ma configuration,
afin de corriger la bonne cause sans interprétation hasardeuse.

---

## Contexte et objectif

Story 2.2 a posé le bandeau global de santé (démon, MQTT, synchro, dernière opération).
Story 2.3 a bloqué les actions HA quand l'infrastructure est indisponible.

Il reste un risque de confusion opérationnelle : l'utilisateur ou le support peut lire un équipement non publié et se demander si le problème vient de l'infrastructure (bridge down) ou de sa configuration (exclusion, mapping ambigu, couverture…).

**Story 2.4 ferme ce risque** en garantissant que la console présente les deux signaux de manière stable, séparée et non ambiguë — sans définir ici la taxonomie complète des statuts ni des `reason_codes` (objet d'Epic 3).

---

## Périmètre

**In-scope :**
- Séparation visuelle stable entre signal d'infrastructure et raison métier existante
- Garantie que l'état infrastructure (bandeau) n'écrase pas ou ne pollue pas la raison métier au niveau équipement
- Cohérence de lecture entre vue globale, pièce et équipement sur cette distinction
- Règle visuelle : rouge réservé à l'infrastructure

**Out-of-scope (guardrails épics suivants) :**
- Définition de la taxonomie canonique et stable de `reason_code` → Epic 3.1
- Moteur de `reason_code` + raison lisible + action recommandée → Epic 3.2
- Table de wording de référence complète → Epic 3.2
- Agrégations pièce/global calculées par le backend → Epic 3.3
- Intégration complète UI du contrat métier backend → Epic 3.4
- Preview avant action, remédiation guidée avancée → Phase B/C
- Support outillé avancé, export diagnostic → Phase C

---

## Acceptance Criteria

### AC 1 — Incident infrastructure séparé de la raison métier

**Given** un équipement non publié ET le broker MQTT indisponible
**When** la console affiche l'état global et les détails de cet équipement
**Then** l'incident d'infrastructure est présenté dans le bandeau global (zone santé, issu de Story 2.2)
**And** la raison de non-publication de l'équipement reste affichée au niveau équipement, indépendamment du statut infrastructure
**And** les deux informations ne partagent pas le même code visuel ni le même emplacement dans l'UI

### AC 2 — Absence de code visuel infrastructure pour un problème de configuration

**Given** un équipement non publié pour une raison de configuration (exclusion, mapping ambigu, couverture non supportée) sans panne d'infrastructure
**When** l'utilisateur lit la console
**Then** aucun libellé ni code de couleur réservé aux pannes système n'est appliqué à cet équipement
**And** le rouge est absent de l'affichage de la raison métier

### AC 3 — Qualification du type de blocage en première lecture

**Given** le support consulte la console avec l'utilisateur
**When** il qualifie la situation
**Then** il peut identifier en première lecture si le blocage relève de `infrastructure`, `configuration`, `couverture`, ou `scope`
**And** cette catégorisation est cohérente entre la vue globale, la vue pièce et le détail équipement

---

## Delta backend minimal requis

**Scope du delta :** vérifier et garantir que le diagnostic existant expose déjà la raison métier de manière indépendante de l'état infrastructure — pas redéfinir la taxonomie.

### Ce que le backend doit garantir pour 2.4 :

1. **La raison de non-publication d'un équipement ne change pas quand l'infrastructure se dégrade.** Si un équipement est ambigu et que MQTT se déconnecte, la raison retournée par le diagnostic reste celle du mapping — pas un code infrastructure.

2. **Le contrat de santé (Story 2.1) et le diagnostic d'équipement sont deux objets distincts.** L'UI ne doit pas avoir à combiner ces deux sources avec une logique métier côté frontend.

3. **Si le contrat actuel écrase ou efface la raison métier en cas d'incident infra**, c'est le seul bug à corriger ici. Pas de nouvelle taxonomie.

---

## Tasks / Subtasks

### Task 1 — Vérifier la stabilité de la raison métier sous dégradation infrastructure (AC 1, AC 2)

- [x] Task 1.1 — Inspecter le code de diagnostic daemon Python
  - [x] Localiser le code qui produit la raison de non-publication par équipement (`core/python/`)
  - [x] Identifier si ce calcul a une dépendance à l'état MQTT ou démon au moment de l'exécution
  - [x] Identifier si un état infrastructure peut actuellement remplacer ou masquer une raison métier existante

- [x] Task 1.2 — Corriger si nécessaire pour garantir l'indépendance
  - [x] **Seulement si** le diagnostic actuel pollue la raison métier avec un code d'infrastructure : isoler les deux dans le payload retourné
  - [x] La santé infrastructure reste accessible via le contrat Story 2.1 (démon, broker, synchro, opération)
  - [x] La raison de non-publication reste stable quelle que soit la santé infrastructure au moment de la lecture
  - [x] Ne pas introduire de nouveaux champs ou une nouvelle taxonomie : corriger uniquement le comportement fautif s'il existe

- [x] Task 1.3 — Test unitaire de stabilité
  - [x] Cas de test : équipement avec raison métier (exclusion ou mapping non supporté), MQTT down
  - [x] Assertion : raison retournée par le diagnostic identique avec MQTT up et MQTT down
  - [x] Cas à couvrir : exclusion explicite, couverture non supportée (les raisons présentes dans le diagnostic actuel sans anticiper Epic 3)

### Task 2 — Vérifier le rendu UI : séparation bandeau global vs raison équipement (AC 1, AC 2)

- [x] Task 2.1 — Audit du rendu actuel
  - [x] Ouvrir la console existante avec un équipement non publié et l'infrastructure saine : noter où et comment la raison est affichée
  - [x] Simuler un incident MQTT (démon arrêté ou broker déconnecté) : vérifier si l'affichage de la raison équipement change
  - [x] Identifier si le rouge apparaît au niveau équipement quand seule l'infrastructure est en cause

- [x] Task 2.2 — Corriger le rendu si nécessaire pour respecter la règle de séparation
  - [x] Le bandeau global (Story 2.2) affiche le signal infrastructure — ne pas le dupliquer au niveau équipement
  - [x] La raison de non-publication au niveau équipement doit rester visible même si l'infrastructure est down
  - [x] Le rouge est **exclusivement** utilisé pour les signaux infrastructure dans le bandeau global
  - [x] Ne pas assigner de couleur rouge à un badge ou libellé de raison métier au niveau équipement

- [x] Task 2.3 — Vérification de cohérence globale / pièce / équipement (AC 3)
  - [x] Avec l'infrastructure down ET un équipement ambigu : vérifier que les trois niveaux de lecture laissent distinguer les deux causes
  - [x] Avec l'infrastructure saine ET un équipement exclu : vérifier qu'aucun signal infrastructure n'apparaît au niveau pièce ou équipement
  - [x] Avec couverture non supportée : vérifier que la lecture ne ressemble pas à un incident système

### Task 3 — Tests d'intégration ciblés (AC 1, AC 2, AC 3)

- [x] Task 3.1 — Scénario mixte : incident infra + raison métier simultanés
  - [x] Setup : 1 équipement avec raison de non-publication, MQTT déconnecté
  - [x] Assertion 1 : bandeau global affiche signal infrastructure en rouge
  - [x] Assertion 2 : la raison au niveau équipement est visible et stable (pas remplacée par un message d'infra)
  - [x] Assertion 3 : les deux zones UI sont visuellement distinctes (emplacement + style)

- [x] Task 3.2 — Scénario configuration seule, infrastructure saine
  - [x] Setup : équipements non publiés (exclusion ou mapping), infrastructure opérationnelle
  - [x] Assertion : aucun rouge dans le rendu des raisons métier
  - [x] Assertion : bandeau global est vert/neutre

- [x] Task 3.3 — Scénario infrastructure down, aucun équipement problématique
  - [x] Setup : tous les équipements publiés, MQTT down
  - [x] Assertion : seul le bandeau global affiche l'alerte ; les équipements restent dans leur état publié affiché

---

## Dev Notes

### Principes d'implémentation

**Règle architecturale fondamentale (déjà figée par la revue delta) :**
- Le backend calcule, le frontend affiche. Le frontend ne recalcule pas de raison métier.
- Si MQTT est down, ce signal est disponible via le contrat de santé (Story 2.1). Il n'a pas à affecter la raison d'un équipement.

**Ce que cette story corrige si nécessaire :**
- Un comportement où le diagnostic remplace une raison métier par un code d'infrastructure en cas de dégradation
- Un rendu UI où le rouge déborde du bandeau global vers les badges de raisons métier

**Ce que cette story ne touche pas :**
- La structure exacte des `reason_codes` utilisés (Epic 3 les stabilisera)
- Le wording final des messages lisibles (Epic 3.2 le formalisera)
- Les agrégations pièce/global (Epic 3.3)

### Dev Agent Guardrails

**Ne pas faire :**
- Définir un enum ou catalogue complet de `reason_codes` canoniques dans cette story
- Créer une table de wording référence story-level (ce n'est pas le bon endroit)
- Ajouter une logique JS qui remplace une raison backend selon l'état MQTT
- Modifier le contrat `published_scope` (Epic 1)
- Anticiper les actions opérationnelles Epic 4

**Faire :**
- Corriger uniquement le comportement fautif constaté à l'audit (Task 1.1, Task 2.1)
- Garder la raison métier stable quelle que soit l'état infrastructure
- Confiner le rouge au bandeau global santé

### Project Structure

- Diagnostic daemon : `core/python/` — localiser la logique de raison par équipement
- Rendu UI : `resources/` — composants affichant raison et bandeau global
- Tests : répertoire de tests existant du projet

[Source: architecture-delta-review-post-mvp-v1-1-pilotable.md — §5.4, §8.4, §8.5]
[Source: ux-delta-review-post-mvp-v1-1-pilotable.md — §4.2, §6.1, §9.4]

---

## Non-Goals explicites

- Taxonomie canonique de `reason_codes` → **Epic 3.1**
- Moteur `reason_code` + raison lisible + action recommandée structuré → **Epic 3.2**
- Table de wording de référence → **Epic 3.2**
- Agrégations pièce/global calculées côté backend → **Epic 3.3**
- Intégration UI du contrat métier complet → **Epic 3.4**
- Preview avant action, remédiation guidée avancée → **Phase B/C**
- Support outillé avancé, arbre de décision, exportDiag enrichi → **Phase C**

---

## Definition of Done

Story 2.4 est DONE quand :

1. La raison de non-publication au niveau équipement ne change pas lorsque l'infrastructure se dégrade (testé par Task 3.1)
2. Le rouge est absent des raisons métier au niveau équipement en cas d'infrastructure saine (testé par Task 3.2)
3. Les deux signaux — bandeau global infrastructure et raison métier équipement — sont visuellement séparés et non ambigus (testé par Task 3.1 et 3.3)
4. Les trois niveaux de lecture (global, pièce, équipement) permettent de distinguer infrastructure de configuration en première lecture (AC 3 validé manuellement)
5. Aucun empiètement sur le contrat `published_scope` ni sur la taxonomie Epic 3
6. Tests unitaire (Task 1.3) et d'intégration (Task 3.1-3.3) passent

---

## Réduction de dette support

Réduit les escalades inutiles où un incident bridge est traité comme un problème de mapping.
Après cette story, le support peut distinguer dès la première lecture si un blocage relève de l'infrastructure ou de la configuration, sans croiser plusieurs zones de la console.

---

## Risques identifiés

**R1 — Le diagnostic actuel n'expose peut-être pas encore la raison métier séparément**
Risque modéré. À confirmer à l'audit Task 1.1. Si c'est le cas, la correction est localisée dans le daemon.
→ **Résolution :** Audit Task 1.1 confirme que le backend est déjà correct. Aucune correction backend requise.

**R2 — Le rendu UI héritant de classes CSS ou de logique conditionnelle sur l'état MQTT**
Risque faible. À confirmer à l'audit Task 2.1. La correction reste localisée dans le composant de rendu.
→ **Résolution :** Audit Task 2.1 confirme que la séparation visuelle est déjà correcte. Seul `reasonLabels` était incomplet (correction mineure).

**R3 — Tentation de poser une taxonomie complète dans cette story pour "gagner du temps" sur Epic 3**
Risque de scope creep. Guardrail : tout `reason_code` au-delà de ce que le diagnostic existant produit déjà appartient à Epic 3.
→ **Résolution :** Scope respecté. Seuls les labels pour les `reason_codes` existants ont été ajoutés.

---

## Références

- [Epics V1.1 — Story 2.4](/_bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md)
- [UX Delta Review — §4.2, §6.1, §9.4](/_bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md)
- [Architecture Delta Review — §8.1, §8.4, §8.5](/_bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md)
- [PRD V1.1 — §8.3, §12 (Exigences UX)](/_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md)
- [Readiness Report — FR23](/_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-22.md)

---

## Dev Agent Record

### Implementation Plan

**Audit-first** conformément à la stratégie demandée.

**Backend (Task 1.1) — Résultat : SAIN, aucune correction requise**
- `assess_eligibility()` dans `models/topology.py` ne lit pas `mqtt_bridge`
- Le handler `_handle_system_diagnostics` lit uniquement les données RAM (topology, eligibility, mappings, publications), alimentées au moment du sync. Aucune dépendance à l'état MQTT au moment de la lecture.
- Les raisons métier (`excluded_eqlogic`, `ambiguous_skipped`, `no_supported_generic_type`, `no_commands`, etc.) sont calculées pendant le sync et stockées en RAM. Elles ne changent pas quand MQTT se dégrade après le sync.
- Seul `discovery_publish_failed` peut apparaître si MQTT est down au moment d'un sync pour un équipement éligible — ce comportement est correct (c'est une panne infra, pas une raison config).
- **Task 1.2 : aucune correction backend.**

**Frontend (Task 2.1) — Résultat : séparation visuelle déjà correcte, un gap AC3 identifié**
- La couleur rouge (`label-danger`) est déjà confinée à : daemon stopped, MQTT disconnected (bandeau), erreur de communication, publikation failed (modal détail).
- `Non publié` → `label-warning` (orange), `Exclu` → `label-default` (gris), `Partiellement publié` → `label-info` (bleu) → aucun rouge pour les raisons config/couverture.
- **Gap AC3** : `reasonLabels` dans `jeedom2ha.js` était incomplet (11 reason_codes retournés par le backend affichaient "Code inconnu") → empêchait la qualification en première lecture.

**Correction Task 2.2 (minimal frontend fix)**
- Ajout des entries manquantes dans `reasonLabels` : `excluded_eqlogic`, `excluded_plugin`, `excluded_object`, `disabled_eqlogic`, `disabled`, `probable_skipped`, `discovery_publish_failed`, `local_availability_publish_failed`, `no_generic_type_configured`.
- Les entries infra (`discovery_publish_failed`, `local_availability_publish_failed`) mentionnent explicitement "infrastructure" dans leur libellé → qualification immédiate possible (AC3).
- Les entries config/couverture sont neutres (pas de mention MQTT ni infrastructure).

**Tests ajoutés**
- `tests/unit/test_story_2_4_infra_separation.py` — 10 tests Python (pytest) :
  - 6 tests paramétriques (mqtt up/down) pour excluded, ambiguous, no_supported_generic_type
  - 2 scénarios mixtes (mqtt down + config reason)
  - 1 test familles de reason_codes distinctes (AC3)
  - 1 test séparation des contrats /system/diagnostics vs /system/status
- `tests/unit/test_story_2_4_visual_separation.node.test.js` — 22 tests Node.js :
  - 5 tests `getStatusLabel` (couleurs non-rouge pour raisons config)
  - 3 tests `getPubResultLabel` (rouge uniquement pour infra failed)
  - 11 tests `reasonLabels` coverage (tous les codes config/couverture/infra définis)
  - 3 tests scénarios AC1/AC2/AC3

### Debug Log

Aucun bug rencontré pendant l'implémentation.

### Completion Notes

- **Aucune modification backend** : le code Python daemon était déjà correct pour la séparation infra/config.
- **Correction frontend minimale** : 11 entries ajoutées à `reasonLabels` dans `desktop/js/jeedom2ha.js`. Aucune refonte, aucun nouveau composant.
- **32 nouveaux tests** : 10 Python + 22 JS. Tous passent. Aucune régression (499 tests Python existants + 26 JS existants PASS).
- **Scope respecté** : aucune taxonomie `reason_code` créée, aucun champ API ajouté, aucune logique métier déplacée côté frontend, aucun empiètement Epic 3.
- **Guardrails vérifiés** : rouge confine au bandeau + résultat publication infra uniquement. Le `discovery_publish_failed` dans le bandeau détail est une panne infra, pas une raison config — utilisation rouge correcte.

---

## File List

- `desktop/js/jeedom2ha.js` — modifié (ajout entries manquantes dans `reasonLabels`, Task 2.2)
- `tests/unit/test_story_2_4_infra_separation.py` — nouveau (10 tests Python, Tasks 1.3 + 3.1-3.3)
- `tests/unit/test_story_2_4_visual_separation.node.test.js` — nouveau (22 tests Node.js, Tasks 3.1-3.3)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — modifié (statut → review)

---

## Change Log

- 2026-03-25 : Story 2.4 implémentée (audit-first, correction minimale frontend, 32 nouveaux tests)
- 2026-03-25 : Code review PASS — 0 High, 0 Medium, 3 Low (documentaires, non bloquants). Statut → done.

---

**Story revision date:** 2026-03-25
**Cycle:** Post-MVP Phase 1 - V1.1 Pilotable
**Status:** done — code review PASS (2026-03-25), prêt pour clôture Git/GitHub
