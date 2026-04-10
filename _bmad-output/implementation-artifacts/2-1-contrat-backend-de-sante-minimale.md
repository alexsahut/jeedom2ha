# Story 2.1: Contrat backend de santé minimale

Status: done

## Story

En tant qu'utilisateur de la console,
je veux un contrat backend unique de santé du pont,
afin de savoir si les actions Home Assistant sont réellement exécutables.

## Acceptance Criteria

1. **Given** le daemon est actif
   **When** le backend expose l'état du pont
   **Then** il retourne les champs `demon`, `broker`, `derniere_synchro_terminee`, `derniere_operation_resultat`

2. **Given** qu'aucune opération n'a encore été exécutée depuis le démarrage
   **When** l'état du pont est demandé
   **Then** `derniere_operation_resultat` est présent avec une valeur explicite cohérente avec cet état initial
   **And** il n'est jamais omis du contrat

3. **Given** une erreur pendant une opération de maintenance
   **When** le contrat de santé est rafraîchi
   **Then** le résultat de dernière opération reflète explicitement `echec` ou `partiel`

## Tasks / Subtasks

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [ ] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [ ] Sélectionner le mode selon l'objectif de la story :
    - Vérification disparition entités HA sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [ ] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [ ] Task 1 — Extension de l'état du daemon (AC: 1, 2)
  - [ ] Ajouter les variables d'état `derniere_synchro_terminee` (timestamp ou isoformat ISO 8601) et `derniere_operation_resultat` (ex: "aucun", "succes", "partiel", "echec") au niveau du contexte applicatif (ex: `request.app` dans `http_server.py` ou globalement dans `main.py`).
  - [ ] S'assurer que `derniere_operation_resultat` est initialisé à une valeur explicite (ex: "aucun") au paramétrage initial, afin de satisfaire l'AC2.

- [ ] Task 2 — Mise à jour de la mécanique de suivi des opérations de maintenance (AC: 3)
  - [ ] Intercepter le succès/d'une commande de synchronisation (`/action/sync` dans `http_server.py`) pour enregistrer l'horodatage de `derniere_synchro_terminee` et statut de conclusion.
  - [ ] Modifier l'état `derniere_operation_resultat` pour le refléter explicitement (succes/partiel/echec) lors du résultat des publications MQTT, et si le payload MQTT échoue.

- [ ] Task 3 — Exposition dans `/system/status` (AC: 1, 2, 3)
  - [ ] Dans `resources/daemon/transport/http_server.py`, mettre à jour le dict `payload` de la réponse `_handle_system_status` pour exposer les nouveaux attributs sous un format propre. Unifier l'attente du contrat: `demon` (existant: `uptime`, `version`, `python_version`), `broker` (existant: `mqtt`), `derniere_synchro_terminee`, `derniere_operation_resultat`. Ne pas supprimer l'existant.

- [ ] Task 4 — Transmission PHP (si nécessaire)
  - [ ] Vérifier que la classe `jeedom2ha.class.php` (méthode `/system/status` ou équivalente de polling daemon) laisse transiter le contrat inchangé jusqu'à l'Ajax / Frontend. S'il existe un validateur ou filtre restrictif, lui adjoindre les variables en whitelist (généralement aucune modification de PHP requise, le relais étant passif).

## Dev Notes

- **Contexte actif:** Post-MVP Phase 1 - V1.1 Pilotable (`_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md`).
- **Focus :** La requête porte EXCLUSIVEMENT sur la création et l'exposition du contrat backend via des endpoints. Ne surtout pas entamer l'UX (Epic 2.2).
- Ne pas dupliquer `_handle_system_status`, enrichir le payload existant dans `http_server.py`.

### Dev Agent Guardrails

- **Séparation Stricte :** La santé du pont est un contrat séparé de `published_scope`. Ne pas mélanger un appel santé infra à la topologie Jeedom.
- **Invariants V1.1 (Ne pas dévier) :** La santé minimale V1.1 reste strictement limitée aux champs explicités (`demon`, `broker`, `derniere_synchro_terminee`, `derniere_operation_resultat`). Ne PAS construire d'observabilité complexe, historique de requêtes, de metrics ou de bus d'événements.
- **Indépendance Epics :** Ne jamais introduire les statuts et raisons d'équipements applicatifs (C'est réservé à l'Epic 3), ni réviser les opérations HA elles-mêmes (Epic 4).
- **Réduction de dette support (Objectif business) :** Le payload json résultant doit permettre en première intention de savoir si des erreurs HA proviennent de l'infrastructure ou du JSON payload, l'utilisateur n'aura pas à lire le daemon.log pour évaluer le broker ou la run time `derniere_operation_resultat`.

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

- Ne pas créer de nouveau endpoint. `/system/status` centralisé dans `resources/daemon/transport/http_server.py` correspond au contrat `demon` et `broker` existant (au sein de `mqtt_section` et `uptime`). Intégrer les variables `derniere_operation_resultat` et `derniere_synchro_terminee` directement dedans.

#### Fichiers potentiellement touchés explicitement :
- `resources/daemon/transport/http_server.py`
- `core/class/jeedom2ha.class.php` (Uniquement si filtre payload explicite dans le call API)
- Fichiers de backend testing associés (`tests/unit/test_diagnostic_endpoint.py` ou similaire, possible création de `tests/unit/test_system_status.py`) à utiliser par l'Agent dev QA.

### Testing Requirements

- **Tests unitaires de l'endpoint :** Écrire un test vérifiant que le dictionnaire ou json de retour de `/system/status` dispose impérativement de l'existence des clés `derniere_operation_resultat` & `derniere_synchro_terminee`, indépendamment de la complexité ou de la nature de MQTT.
- **Tests d'intégration :** Démontrer le fonctionnement en déclenchant localement le callback simulé pour un endpoint de `/action/sync` suivi d'une vérification de la mutation de `derniere_operation_resultat` à `'succes'`, et via une exception mockée pour `echec` / `partiel`.
- **Non-Régression MVP :** Conserver la lisibilité du bloc existant de diagnostic et les appels du statut de service.

### References

- [Source: _bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md]
- [Source: _bmad-output/planning-artifacts/architecture-delta-review-post-mvp-v1-1-pilotable.md#Epic 2]
- [Source: _bmad-output/planning-artifacts/epics-post-mvp-v1-1-pilotable.md]

## Dev Agent Record

### Agent Model Used
bmad-dev-story (Gemini Antigravity)

### Debug Log References
- All API and unit tests passed via `pytest tests/unit/test_http_server.py`.

### Completion Notes List
- **Task 1 & 3**: Contextualisation de `derniere_synchro_terminee` et `derniere_operation_resultat` à `"aucun"` au start, et ajout dans le json de `/system/status` tout en respectant l'organisation demandée (`demon` + `broker` isolés des anciens contrats racines pour les clients natifs).
- **Task 2**: Interception de `/action/sync` configurée pour muter l'état à `succes`, `partiel`, ou `echec` en fonction des exceptions et statuts de publishing captés.
- **Task 4**: Revu `jeedom2ha.class.php` — Aucune modification nécessaire, le plugin relaie `/system/status` passivement.
- **Validations**: `TestHealthCheckContract` rajouté dans `tests/unit/test_http_server.py` confirmant la bonne structure et réactivité des stats de santé.
- **Deploy**: Script testé via dry-run local.

### File List
- `resources/daemon/transport/http_server.py`
- `tests/unit/test_http_server.py`
