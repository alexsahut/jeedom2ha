# Story A1 : Budget fixe et échéance transmise pour les 5 relais PHP restants (E4)

Status: done

Epic: (Chantier Market 2026-10)

Story Key (sprint-status): `a1-limite-de-performance-relais-15s`

## Story

En tant que mainteneur,  
je veux appliquer aux cinq relais PHP restants le motif déjà retenu et prouvé en story 19-6 (budget fixe du relais, échéance transmise au démon, plafond de lissage côté démon),  
afin d'éliminer le faux « Le démon ne répond pas » qui apparaît sur des parcs de taille importante alors que le démon travaille toujours.

## Description

### Le problème réel (pas « des pauses de 15 s »)

Les cinq relais ci-dessous passent un timeout HTTP **fixe de 15 s** à `jeedom2ha::callDaemon(...)`. Quand le démon met plus de 15 s à répondre (parc de grande taille), le relais **abandonne** et affiche « Le démon ne répond pas (timeout API) » — alors que le démon est vivant et termine son traitement. C'est exactement le défaut CC-32, déjà diagnostiqué et corrigé pour les actions Publier/Supprimer en story 19-6 (`challenges/2026-09-30-tri-cc32.md` côté ClawBox ; PLAN-ACTION l. ~1208) : au-delà de ~125-130 équipements évalués, le budget de 15 s est dépassé.

### Le motif déjà prouvé (story 19-6, PR #188/#189, commit `95d3059`)

Ce n'est PAS une file asynchrone ni Redis. C'est l'option **(b′)**, validée par Alex le 2026-09-30 11:20 :

- Côté relais PHP (`resources`/`core/php/jeedom2ha_action_budget.php`) : budget fixe `R = 60 s`, réserve `reserve_s = 5 s`, échéance `deadline_s = R - reserve_s = 55 s` **transmise au démon** dans le corps de la requête (`$params['deadline_s']`).
- Côté démon (`resources/daemon/transport/action_pacing.py`) : le démon reçoit `deadline_s` et plafonne son propre lissage de publications MQTT avec `plafond_pauses(deadline_s) = min(P_MAX_S=15, deadline_s/2)` ; `budget_travail = deadline_s - plafond_pauses - MARGE_REVEIL_S(1s)`.
- Le budget est fixe et indépendant de la taille du parc : pas d'estimation du nombre d'équipements, pas de file, pas d'asyncio supplémentaire.

### Application aux 5 relais — analyse par relais (à vérifier/affiner en dev, prérequis obligatoire avant toute AC)

| Relais | Ligne actuelle | Dépend du nb d'équipements ? | Timeout actuel | Action proposée |
|---|---|---|---|---|
| `testMqttConnection` | ~596 | Non (test de connexion simple) | 15 s fixe | Garder un budget court fixe (ex. 15–20 s), pas de `deadline_s` nécessaire — à confirmer en dev |
| `scanTopology` | ~632 | **Oui** (sync complet du parc) | 15 s fixe | Appliquer le motif complet : budget R dédié + `deadline_s` transmis au démon + plafond de lissage si le scan publie en boucle |
| `getDiagnostics` | ~648 | Probable (diagnostics globaux) | 15 s fixe | Vérifier en dev si la taille du payload dépend du parc ; si oui, motif complet |
| `exportDiagnostic` | ~727 | **Oui** (lit `/system/diagnostics`, mêmes données que scan) | 15 s fixe | Même traitement que `getDiagnostics` |
| `getMappingOverrides` | ~910 | **Non** (lecture d'un seul `eqId`) | 15 s fixe | Garder un budget court fixe, pas de motif (b′) nécessaire |

Cette analyse est une hypothèse de départ basée sur une lecture du code — **chaque ligne doit être revérifiée en dev** avant implémentation, pas supposée acquise.

## Acceptance Criteria

1. **Given** chacun des 5 relais listés  
   **When** son traitement démon dépend du nombre d'équipements du parc  
   **Then** il reçoit le motif complet (budget R dédié au relais, `deadline_s` transmis, plafond de lissage côté démon si le relais publie en boucle), sur le modèle exact de `jeedom2ha_action_budget.php` / `action_pacing.py`.

2. **Given** un relais qui ne dépend pas de la taille du parc (`testMqttConnection`, `getMappingOverrides`)  
   **When** il est audité  
   **Then** son budget fixe actuel est conservé ou ajusté sans ajout du mécanisme `deadline_s`/plafond — la décision et sa justification sont documentées inline.

3. **Given** un test de charge réel (300 équipements, environnement de test, pas un simulateur du relais)  
   **When** `scanTopology` ou `exportDiagnostic` est déclenché  
   **Then** le relais ne retombe jamais sur le message « Le démon ne répond pas » tant que le démon travaille dans le budget `R`, et le dépassement réel du budget produit le message distinct attendu (sur le modèle `jeedom2ha_action_timeout_message()`).

4. **Given** la suite de tests PHP/JS du relais modifié  
   **When** elle est exécutée  
   **Then** les tests exercent le relais réel (pas un mock qui simule son comportement — leçon story 20-2 : un test qui simule le relais ne prouve rien), sur le modèle `tests/unit/test_story_19_6_php_relay.php`.

5. **Given** le test de charge sur Jeedom vierge (gate, pas une tâche de cette story)  
   **When** clawbox l'exécute en VM sur `pve` (décision Alex 2026-10-11 21:12, pas en LXC) après son go Telegram  
   **Then** le comportement observé en charge réelle confirme les AC1-AC4 avant passage à `done`.

   Amendé par décision Alex 2026-10-12 15:17 (D8 = a) : la charge réelle est prouvée sur la box (292 équipements réels, box en `69a4b47`, `[RELAY-BUDGET] relais=TOPOLOGY R=60 duration_s=1.811`) et en CI par `test_story_a1_parc_300_load.py` (300 équipements, vrai serveur HTTP). Le gate A4 sur Jeedom vierge couvre l'installation, les dépendances et le démon.

## Tasks / Subtasks

- [x] T1 — Auditer précisément chacun des 5 relais (confirmer/corriger le tableau ci-dessus)
  - [x] Vérifier si `scanTopology` publie en boucle (nécessitant un plafond de lissage) ou fait un appel unique (budget seul suffit)
  - [x] Idem pour `getDiagnostics` et `exportDiagnostic`
  - [x] Confirmer que `testMqttConnection` et `getMappingOverrides` n'ont aucune dépendance au nombre d'équipements

- [x] T2 — Implémenter le motif (b′) pour les relais dépendants de la taille du parc
  - [x] Réutiliser/étendre `core/php/jeedom2ha_action_budget.php` (budget R, reserve_s, deadline_s) pour ces relais, ou créer un budget dédié par relais si R=60s ne convient pas
  - [x] Transmettre `deadline_s` au démon via le payload de la requête
  - [x] Côté démon, réutiliser `resources/daemon/transport/action_pacing.py` (`plafond_pauses`, `budget_travail`) si le relais publie en boucle MQTT

- [x] T3 — Conserver/ajuster le budget fixe des relais non dépendants
  - [x] `testMqttConnection`, `getMappingOverrides` : documenter la décision inline (pas de changement de mécanisme, timeout éventuellement ajusté)

- [x] T4 — Tests réels (pas de simulation du relais)
  - [x] Ajouter/étendre des tests PHP sur le modèle `test_story_19_6_php_relay.php` pour chaque relais modifié
  - [x] Ajouter un test de charge à N équipements (ex. 300) reproduisant le comportement réel du démon
  - [x] Vérifier le message d'erreur correct en cas de dépassement réel du budget

- [x] T5 — Gate terrain (hors story, exécuté par clawbox)
  - [x] Preuve terrain du 2026-10-12 09:38 (box en `69a4b47`, Rescanner (Chrome) → succès, synchro 09:38:05, journal `[RELAY-BUDGET] relais=TOPOLOGY R=60 duration_s=1.811`, 292 eqLogics) + AC5 amendé par décision Alex 2026-10-12 15:17 (D8 = a) : charge réelle acceptée sur la box de production et en CI (`test_story_a1_parc_300_load.py`, 300 équipements), le gate A4 Jeedom vierge couvrant installation/dépendances/démon

## Impact Produit

- **Si non fait** : sur un parc de grande taille (>~125-130 équipements selon la mesure CC-32), scan topologie, diagnostics et export resteront sujets au faux « démon ne répond pas », masquant un démon fonctionnel.
- **Si fait** : alignement complet avec le motif déjà validé par Alex en story 19-6, cohérence de design, réduction du risque de régression de type CC-32 sur les relais restants.

## Rollback / Plan de Retour Arrière

1. Revert des commits touchant `core/ajax/jeedom2ha.ajax.php` et, si créés, les fichiers budget dédiés
2. Revert des changements côté démon (`action_pacing.py` reste inchangé s'il est seulement réutilisé, pas modifié)
3. Relancer le daemon jeedom2ha
4. Les relais reviennent aux timeouts fixes de 15 s d'origine

## Notes

- Aucun parcours alternatif : cette story est en **parcours complet uniquement** (règle CC-10 — la méthode proportionnée à l'enjeu a déjà tranché, pas de choix rapide/complet laissé à l'implémentation).
- Source de référence obligatoire avant tout code : `core/php/jeedom2ha_action_budget.php`, `resources/daemon/transport/action_pacing.py`, `tests/unit/test_story_19_6_php_relay.php`, commit `95d3059` (PR #189), `challenges/2026-09-30-tri-cc32.md` (côté ClawBox, à demander si inaccessible).
- Ordre / parallélisme : **A1 peut être menée en parallèle de A3** (conformité Market), aucune dépendance dure entre les deux.

## Dev Agent Record (session cloud 11/10)

Audit confirmé/affiné par lecture du code démon (`resources/daemon/transport/http_server.py`) :

| Relais | Dépend du parc ? | Pauses de lissage côté démon ? | Décision |
|---|---|---|---|
| `testMqttConnection` | Non (connexion broker, borne démon 5 s) | Non | Budget court fixe 15 s conservé (`JEEDOM2HA_RELAY_BUDGET_SHORT_S`), décision inline |
| `scanTopology` | Oui (`/action/sync`) | **Non** : aucun `asyncio.sleep` dans le sync ; les pauses n'existent que dans `/action/execute` et le republish broker/HA (hors relais) | Budget fixe R = 60 s via `jeedom2ha_dispatch_parc_relay`, 1 tentative ; `deadline_s` **non transmis** (le démon l'ignorerait), `action_pacing.py` inchangé |
| `getDiagnostics` | Oui (payload ∝ parc) | Non | Idem scan (aucun appelant JS aujourd'hui, relais traité par cohérence) |
| `exportDiagnostic` | Oui (mêmes données) | Non | Idem scan |
| `getMappingOverrides` | Non (un seul `eqId`) | Non | Budget court fixe 15 s conservé, décision inline |

Le faux « ne répond pas » avait une 2ᵉ cause côté client : délais JS de 20 s (rescan console + configuration) et 30 s (export). Alignés sur `CLIENT_TIMEOUT_MS` (90 s > R + sonde).
Messages : démon injoignable (sonde de statut en échec) / erreur démon immédiate (durée < R − 1) / dépassement réel de R (`jeedom2ha_relay_timeout_message()`).

Tests : `tests/unit/test_story_a1_php_relay.php`, `test_story_a1_client_timeout.node.test.js`, `test_story_a1_parc_300_load.py` (vrai serveur HTTP, 300 équipements, zéro pause de lissage) ; `test_story_20_4_rescan_ui.node.test.js` mis à jour (délai 20 s → budget relais).
