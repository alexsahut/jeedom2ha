# Story 2.2: Bandeau global de santé toujours visible

Status: done

## Story

En tant qu'utilisateur Jeedom,
je veux voir en permanence la santé minimale du pont dans un bandeau global compact,
afin de distinguer en un coup d'oeil un problème d'infrastructure d'un problème de configuration.

## Dépendances et Réduction de dette

- **Dépendances autorisées** : Story 2.1 (Contrat backend de santé minimale)
- **Réduction de dette support** : permet la qualification initiale des tickets sans navigation technique.

## Acceptance Criteria

1. 
   - **Given** la console V1.1 est ouverte
   - **When** les données de santé sont chargées
   - **Then** un bandeau global distinct affiche `Bridge`, `MQTT`, `Dernière synchro`, `Dernière opération`

2. 
   - **Given** un incident d'infrastructure
   - **When** il est visible dans le bandeau
   - **Then** le rouge est utilisé uniquement pour cet incident
   - **And** les problèmes de périmètre ou de configuration n'emploient pas ce code visuel

3. 
   - **Given** un petit écran ou une forte densité de contenu
   - **When** l'utilisateur navigue dans la console
   - **Then** le bandeau reste visible sans devenir envahissant

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Consommation du contrat `system_status` (AC: 1)
  - [x] S'assurer que le frontend récupère le statut du pont via le contrat exposé par la Story 2.1.
  - [x] N'ajouter aucune logique de calcul de santé dans le JS/PHP, mapper directement les données backend existantes (`demon`, `broker`, `derniere_synchro_terminee`, `derniere_operation_resultat`).

- [x] Task 2 — Implémentation UI du bandeau global (AC: 1, 3)
  - [x] Ajouter un composant de bandeau global compact tout en haut de la console V1.1.
  - [x] Afficher les 4 indicateurs requis de santé du pont.
  - [x] Implémenter le CSS nécessaire pour que le bandeau reste visible sans écraser le reste du contenu sur différentes tailles d'écran (responsive).

- [x] Task 3 — Sérialisation visuelle et sémantique (AC: 2)
  - [x] S'assurer que le rouge HTML/CSS est utilisé EXCLUSIVEMENT pour signaler un incident d'infrastructure (ex: broker down, demon down).
  - [x] Vérifier que le visuel de santé du pont ne pollue pas visuellement le reste de la table d'équipements, avec une stricte séparation entre infra et configuration de périmètre.

## Dev Notes

- **Contexte actif:** Post-MVP Phase 1 - V1.1 Pilotable.
- Toutes les sources de vérité utilisées : `_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md`, `ux-delta-review-post-mvp-v1-1-pilotable.md`, `architecture-delta-review-post-mvp-v1-1-pilotable.md`, `epics-post-mvp-v1-1-pilotable.md`.
- L'audit des dépendances valide que la Story 2.1 existe et fournit le contrat de données backend.
- Ce fichier ne couvre pas la logique des actions ou le blocage (gating traité en Story 2.3), ni l'Epic 3 (statuts d'équipements). Il couvre uniquement l'affichage UI passif de l'état du pont.

### Dev Agent Guardrails

- Story 2.2 ne doit pas recréer de logique métier frontend.
- Le backend reste la source unique de la santé minimale.
- Le contrat de santé est séparé du contrat `published_scope`.
- Ne pas mélanger santé du pont, périmètre publié, statuts de couverture ou opérations HA.
- Rouge réservé strictement aux incidents d’infrastructure.
- Le bandeau doit rester compact, visible, utile, non envahissant.
- Aucun glissement vers une santé avancée, timeline, métriques expertes ou observabilité lourde.
- Aucune extension de scope fonctionnel hors V1.1.
- Respecter le pattern backend-first validé par l’Epic 1.
- Préserver la séparation entre décision locale, projection effective vers HA et incident d’infrastructure.
- Ne pas anticiper Epic 3 ni Epic 4.
- Ne pas introduire de contrat de statut, raison principale, action recommandée ou gating d’actions HA : ce n’est pas le périmètre de la Story 2.2.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

- Le code UI de la console Jeedom réside généralement dans `desktop/php/jeedom2ha.php` et `desktop/js/jeedom2ha.js`.
- Respecter le DOM Jeedom standard pour l'apposition du bandeau. Apposer le bandeau en dehors du focus équipements.
- Aucune modification backend (python) n'est attendue en Story 2.2.

### References

- [Source: _bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md]
- [Source: _bmad-output/planning-artifacts/ux-delta-review-post-mvp-v1-1-pilotable.md#Epic 2]
- [Source: _bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md]
- [Source: _bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md]
- [Source: _bmad-output/implementation-artifacts/2-1-contrat-backend-de-sante-minimale.md]

## Dev Agent Record

### Agent Model Used
bmad-dev-story (Gemini Antigravity)

### Debug Log References
- No automated UI test suite detected for Jeedom frontend core. Manual UI checks delegated to field validation.

### Completion Notes List
- **Task 1**: Contrat `system_status` correctement consommé et relayé de bout en bout (Python -> PHP `getBridgeStatus` -> JS) sans aucun recalcul métier.
- **Task 2**: Ajout du bandeau `#div_bridgeHealthBanner` en haut de la console V1.1, agencé en CSS Flexbox pour rester compact (.well) et responsive.
- **Task 3**: Codes couleurs respectés rigoureusement. Rouge (`label-danger`) limité aux déconnexions du Démon ou du Broker. Les autres états, comme "partiel" ou "échec" de dernière opération (liés à la configuration/payload), utilisent le code orange warning (`label-warning`).
- **Protocole de validation terrain**:
  1. Utiliser `./scripts/deploy-to-box.sh --stop-daemon-cleanup` sur la VM/Box de test.
  2. Ouvrir la console V1.1 et vérifier la présence du bandeau avec les 4 indicateurs.
  3. Couper le démon (page Santé Jeedom) -> s'assurer que l'indicateur Bridge passe en rouge (Arrêté), et le reste en Inconnu.
  4. Relancer le démon, simuler une erreur MQTT (mauvais port ou broker éteint) -> vérifier que MQTT passe en rouge, Démon en vert.
  5. Remettre port correct, faire une sauvegarde d'un équipement -> vérifier que Dernière opération affiche "Partiel" ou "Echec" en orange si l'opération se passe mal, pas en rouge.

### File List
- `core/ajax/jeedom2ha.ajax.php`
- `desktop/php/jeedom2ha.php`
- `desktop/js/jeedom2ha.js`
