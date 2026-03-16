# Story 4.1: Interface de Diagnostic de Couverture

Status: done

## Story

As a utilisateur Jeedom,
I want voir une liste claire de mes équipements avec leur statut de publication,
so that je comprenne instantanément ce qui est visible dans HA.

## Acceptance Criteria

1. **Given** la maison a été scannée (synchronisation `/action/sync` déjà effectuée)
2. **When** j'ouvre l'interface de diagnostic depuis le bureau du plugin
3. **Then** le plugin affiche les statuts harmonisés : **Publié, Partiellement publié, Non publié, Exclu**
4. **And** le niveau de confiance de mapping est affiché : **Sûr / Probable / Ambigu / Ignoré**
5. **And** les badges visuels (Bootstrap 3 labels) sont utilisés pour refléter ces états de manière intuitive
6. **And** les équipements sont regroupés par objet Jeedom (pièce) pour une lecture facilitée

## Tasks / Subtasks

- [x] **Task 0 - Pre-flight Check & Context Loading** (Crucial)
  - [x] 0.1 S'assurer d'être sur la branche Git dédiée : `story/4.1-interface-diagnostic`
  - [x] 0.2 Charger IMPÉRATIVEMENT le fichier de contexte réel `jeedom2ha-test-context-jeedom-reel.md` pour éviter les fausses suppositions lors des tests
- [x] **Task 1 - Backend : Exposer les données de diagnostic via l'API du démon** (AC: #1, #3)
  - [x] 1.1 Ajouter un endpoint `GET /system/diagnostics` dans `resources/daemon/transport/http_server.py`
  - [x] 1.2 Transformer les structures RAM (`app["eligibility"]`, `app["mappings"]`, `app["publications"]`) en un payload JSON structuré
  - [x] 1.3 Inclure les codes de raison (`reason_code`) et les niveaux de confiance pour préparer l'affichage
- [x] **Task 2 - Bridge : Passerelle AJAX Jeedom** (AC: #2)
  - [x] 2.1 Ajouter l'action `getDiagnostics` dans `core/ajax/jeedom2ha.ajax.php`
  - [x] 2.2 Appeler l'API du démon via `jeedom2ha::callDaemon` en gérant proprement le cas où le démon est injoignable
- [x] **Task 3 - Frontend : Interface Utilisateur Jeedom** (AC: #2, #3, #4, #5, #6)
  - [x] 3.1 Ajouter un bouton "Diagnostic de Couverture" dans `desktop/php/jeedom2ha.php`
  - [x] 3.2 Implémenter la logique JS dans `desktop/js/jeedom2ha.js` (charger AJAX, construire tableau HTML)
  - [x] 3.3 Assurer la conformité visuelle via les classes Vanilla Bootstrap 3 exclusives (`label-success`, `label-warning`, etc.)
- [x] **Task 4 - Tests unitaires et intégration**
  - [x] 4.1 Créer `resources/daemon/tests/unit/test_diagnostic_endpoint.py` et valider explicitement la sérialisation JSON correcte du payload de diagnostic
  - [x] 4.2 Vérifier l'intégration complète : de la passerelle AJAX PHP jusqu'au retour de l'endpoint Python
- [x] **Task 5 - Validation Terrain Opérateur (Quality Gate)**
  - [x] 5.1 Exécuter le runbook terrain pas à pas sur la box Jeedom de test.
  - [x] 5.2 Fournir les preuves de passage sans pollution JSON (via l'onglet Network).
  - [x] 5.3 Valider le rendu UI des badges Bootstrap et la gestion des cas négatifs (démon off, restart fresh).

## Validation Terrain Opérateur (Runbook)

**Règle de preuve :** 
- Prouvé par code review : Code frontend Vanilla JS et Bootstrap 3.
- Prouvé automatisé : Endpoint Python.
- **À prouver :** Câblage réel UI -> AJAX -> Daemon sur box, sans pollution de payload PHP, et avec gestion des cas d'erreurs réels.

### Protocole pas à pas à documenter avec l'agent SM lors de l'exécution :

**A. Pre-flight**
1. Vérifier la branche `story/4.1-interface-diagnostic`.
2. Redémarrer le démon `jeedom2ha`.
3. Assurez-vous d'avoir exécuté un évènement qui provoque `/action/sync` (ex: sauvegarde configuration de l'équipement `391`) pour hydrater la RAM du démon.

**B. Validation backend réelle**
4. Optionnel mais recommandé : `curl -sS -H "X-Local-Secret: [VOTRE_SECRET]" http://127.0.0.1:55080/system/diagnostics | jq`. Doit retourner un JSON valide.

**C. Validation AJAX réelle anti-pollution (Leçon Epic 3)**
5. Dans Jeedom, ouvrir F12 -> Onglet **Network**. Cliquer sur le bouton "Diagnostic de Couverture".
6. Cliquer sur la requête de réponse AJAX. La réponse brute doit commencer par `{` (ou `[`). Aucun espace, aucun warning PHP, aucune balise HTML avant le JSON. (Preuve critique à capturer).

**D. Validation UI réelle**
7. Vérifier que la modale respecte le design natif de Jeedom et le regroupement par objets/pièces.
8. Les statuts ("Publié", "Exclu") et confiances ("Sûr", "Ambigu") utilisent bien des étiquettes / badges couleur (classes Bootstrap 3 `label-success`, `label-warning`, etc.).

**E. Tests négatifs**
9. **Démon Injoignable :** Coupez le démon depuis Jeedom et cliquez sur "Diagnostic". Vérifiez que le navigateur ne freeze pas et que l'erreur s'affiche proprement, sans crash JS muet.
10. **RAM vide :** Redémarrez le démon, et *avant tout `/action/sync`*, cliquez sur "Diagnostic". Vérifiez qu'il n'y a pas d'erreur 500 liée à un dictionnaire vide dans Python.

**Preuves obligatoires avant clôture :**
- Captures du Network tab (propreté AJAX).
- Captures de la modale avec les statuts.
- Bilan PASS/FAIL clair donné à l'agent SM.
## Dev Agent Guardrails

### Git & Workspace Governance
- **CRITICAL:** Touts les développements DOIVENT être réalisés sur la branche `story/4.1-interface-diagnostic`. Ne jamais commiter directement sur `main`.

### Architecture Compliance
- **Frontend Stack Strict:** Utilisation exclusive de HTML Vanilla, Vanilla JS (jQuery autorisé vu v4.4) et Bootstrap 3. L'utilisation de React, Vue, ou tout autre framework web moderne est **STRICTEMENT INTERDITE** pour rester compatible avec le core Jeedom.
- **Backend Stack Strict:** Ne rajouter **aucune nouvelle dépendance Python**. Utiliser exclusivement la stack standard asynchrone déjà en place (aiohttp, asyncio).
- **Data Source:** Le diagnostic est basé au runtime sur l'état volatile en RAM du démon (les instances `TopologySnapshot`, `MappingResult`, `EligibilityResult`). Il n'y a pas d'état persistant en base de données Jeedom pour cela.

## Previous Story Intelligence

**Leçons de l'Épique 3 (Pilotage & Synchro) :**
- Le "Pre-flight Check" n'est pas optionnel. Lire la documentation de contexte terrain (`jeedom2ha-test-context-jeedom-reel.md`) empêche de concevoir des heuristiques fausses (ex: inventer des clés d'état inexistantes dans Jeedom).
- Les tests unitaires doivent cibler spécifiquement les `dict` de sérialisation retournés par `aiohttp` pour éviter les surprises au runtime (erreurs de sérialisation d'objets ou de dates ISO).
- `jeedom2ha::callDaemon` côté PHP gère déjà le fallback réseau. Utilisez cette fonction sans réinventer de couche HTTP cURL manuelle.
## Dev Notes

### Contexte architecture et contraintes
- **Données éphémères :** Le diagnostic repose sur l'état en RAM du démon (introduit en Epic 2/3). Il est perdu au redémarrage du démon jusqu'au prochain `/action/sync`.
- **Réutilisation :** Les classes `EligibilityResult`, `MappingResult` et `PublicationDecision` contiennent déjà toute l'information nécessaire. Ne pas redévelopper la logique de décision.
- **UI Jeedom :** Utiliser exclusivement Bootstrap 3 et jQuery comme imposé par le core Jeedom 4.4.

### Composants à modifier
- `resources/daemon/transport/http_server.py` : ajout d'endpoint.
- `core/ajax/jeedom2ha.ajax.php` : passerelle AJAX.
- `desktop/php/jeedom2ha.php` : point d'entrée UI.
- `desktop/js/jeedom2ha.js` : logique d'affichage.

### Standards de test
- Les tests unitaires Python doivent s'exécuter via `pytest`.

### Références
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1: Interface de Diagnostic de Couverture]
- [Source: _bmad-output/planning-artifacts/architecture.md#7. API & Integration Patterns]
- [Source: resources/daemon/models/topology.py]
- [Source: resources/daemon/transport/http_server.py]

## Dev Agent Record

### Agent Model Used
Antigravity (create-story workflow)

### File List
- _bmad-output/implementation-artifacts/4-1-interface-de-diagnostic-de-couverture.md
