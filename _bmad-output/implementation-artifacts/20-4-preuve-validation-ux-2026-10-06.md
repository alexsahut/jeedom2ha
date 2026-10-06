# Story 20-4 — preuve terrain et validation UX du 06/10/2026

Preuve terrain de la story 20-4 (PR #209, fusion `ae9bbbb`) et validation UX, faites le 06/10/2026.

Cadre :
- go d'Alex du 06/10 à 08:01 (« go déploiement 20-4 »), donné pour le déploiement, le gate, le rescan au clic réel et la validation UX ;
- règle 2 d'Alex (28/09) et règle d'autonomie du 30/09 : plugin et HA seulement, déploiement standard, relevés avant et après.

Exécution par clawcode, relecture de chaque étape par ClaudeBox ; clic réel et passage Chrome par ClaudeBox. Heures en heure locale (Paris), sauf mention `Z`.

## Déploiement

| Élément | Valeur |
|---|---|
| SHA déployé | `80f7a05eb0e8f21a98b614c7e1ec2d1b23a6caf0` : fusion de la PR #209 (`ae9bbbb`), puis de la PR #211 (CC-43, outillage du gate, `tests/` seulement, non livré) |
| CI de `main` sur ce SHA | verte : 10 succès, 1 `skipped` (check-runs relus par ClaudeBox) |
| SHA précédent sur la box | `51bc9d9` (déployé le 05/10 à 13:32:57Z) |
| Fichiers livrés qui changent | `core/ajax/jeedom2ha.ajax.php`, `core/class/jeedom2ha.class.php`, `desktop/js/jeedom2ha.js`, `desktop/php/jeedom2ha.php`, `plugin_info/configuration.php`, `resources/daemon/transport/http_server.py` |
| Déploiement | standard (`--restart-daemon`), depuis un worktree neuf détaché sur `origin/main`, à 06:06:12Z ; dry-run préalable sans erreur |
| Archive de retour arrière | `jeedom2ha-20261006T060611Z-1NWZks.tar.gz` (non utilisée) |
| Tag | `deploy-80f7a05eb0e8f21a98b614c7e1ec2d1b23a6caf0-20261006T060621Z` |

Les relevés avant ont été refaits juste avant le déploiement (06:05Z) : ceux de la préparation dataient de 03:31.

## Relevés avant et après le déploiement

- VERSION après : `80f7a05...`, `git_status=clean`.
- Healthcheck : MQTT connecté. Sync du déploiement : 292 équipements, 96 éligibles, 262 publiés.
- Inventaire MQTT : 353 entités avant et après, aucun topic ajouté ni retiré.
- Relevé de parité : diff vide (`is_empty_diff: true`, aucune décision changée, 353 topics avant et après, aucun écouteur ajouté ni retiré).
- Box, `ps -eo pid,user,lstart,comm` : seul le démon jeedom2ha change (PID 2739922 remplacé par 444052, `www-data`, lancé à 08:06:13). Les autres écarts sont transitoires : threads noyau, sessions SSH, processus web du healthcheck et du sync du script.
- Journal du plugin : 0 nouvelle ligne `ERROR` (le total reste à 3016) ; `[STATE-LISTENER] 227 listener(s)` à 08:06:16, comme avant.
- Journal du démon : 0 `ERROR`.
- Les 6 fichiers servis ont le sha256 du worktree.
- `ha_overrides.json` : sha256 inchangé (`083ab5bf88ace22f18376d2c259e66dc87940d8c1b930c1dbd87b9d29621488d`) ; aucun override en attente d'application.

## Gate 20-0

| Fin | Parcours | Code | Verdict | Constat |
|---|---|---|---|---|
| 08:15:48 | découverte, lecture seule | `80f7a05` | PASS | 5 critères PASS, témoin et sonde sans différence, console 0. |
| 08:18:05 | référence (bascule) | `80f7a05` | PASS | Écritures simulées seulement (`saveMappingOverride`, `revertMappingOverride`) ; témoin et sonde sans différence. |
| 08:20:42 | rescan de la page principale | `80f7a05` | FAIL | Défaut du parcours, pas du plugin : il attendait « Synchronisation terminée. » dans `#div_alert`, alors que Jeedom 4.4 affiche les alertes en notification (`jeeDialog.toast`, `#jeeToastContainer`). Les 5 critères étaient PASS ; `scanTopology` simulé, jamais transmis. |
| 08:23:14 | contrôle négatif | `80f7a05` | FAIL attendu | `saveMappingOverride` non déclaré bloqué (`block-fail`) ; critères interception et console en FAIL attendu (la page reçoit `net::ERR_FAILED`) ; témoin et sonde sans différence. |
| 08:47:49 | rescan de la page principale | `cbad379` | PASS | Après la PR #212 (le parcours lit la notification Jeedom ou `#div_alert`) : `confirmation_ouverte: true`, `retour_rescan_zone: toast`, `retour_rescan: succes-simule` ; `scanTopology` simulé (`rescan-declare`, 06:46:15Z), jamais transmis ; fenêtre du démon sans `[TOPOLOGY] Received sync request` ; 0 erreur ; témoin et sonde sans différence. |

Entre `80f7a05` et `cbad379`, seul le parcours `rescan-page-principale.mjs` change : le code servi est celui de la box. Le rapport du gate rappelle que le badge « pas encore appliqué » n'est pas prouvé par le gate. La recherche générique de secrets ne trouve rien dans les journaux et les rapports des cinq exécutions (relevée par clawcode pour les quatre premières, par ClaudeBox pour le rescan relancé).

## Rescan au clic réel (ClaudeBox, Chrome, 09:27-09:28)

Un seul clic réel, hors des fenêtres du gate, depuis la page principale :
- « Rescanner la topologie Jeedom » (`#bt_rescanTopology`), puis la confirmation, puis « Rescanner ».
- Journal du démon : `[TOPOLOGY] Received sync request` à 09:28:00, sync terminé dans la même seconde (96 éligibles, 196 non éligibles), `POST /action/sync` 200.
- Journal du plugin : « Scan complet : 23 objets, 292 eqLogics, 120 scénarios » à 09:28:00, `[STATE-LISTENER] 227 listener(s)` à 09:28:01.
- Bandeau santé après le rescan : « Dernière synchro : 06/10 09:28:00 » ; « Dernière opération : Succès, Synchronisation terminée. ».
- Durée du sync : environ 1 s.

Relevés après le rescan :
- Relevé de parité comparé à celui d'après le déploiement : diff vide (aucune décision changée, 353 topics retenus avant et après).
- Box : même démon (PID 444052), un seul ; 0 nouvelle ligne `ERROR` (plugin 3016, démon 0) ; `ha_overrides.json` inchangé.
- Journal du démon : seulement les 2 avertissements habituels de mapping ambigu, présents à chaque sync (déjà 2 par sync au démarrage et au déploiement de 08:06).
- Home Assistant, en lecture seule (ClaudeBox) :
  - 354 entités jeedom2ha au registre ;
  - dernière modification au registre le 02/10, dernière création le 27/09 : le déploiement et le rescan n'y ont rien changé ;
  - relevé `core.restore_state` de 09:30:11, après le rescan : 341 entités, 7 indisponibles, 113 `unknown`, les mêmes décomptes qu'au relevé de 20-1 le 05/10.
- aiohttp sur la box : 3.13.3 (Task 0).

## Validation UX (Chrome, box en `80f7a05`)

Gestes faits : un clic réel sur le rescan, la lecture de la page principale et de la page de configuration. Gestes exclus : aucun « Republier », aucun « Supprimer puis recréer », aucun clic sur « Appliquer les filtres et rescanner ».

**Conforme :**
- AC1 : « Rescanner la topologie Jeedom » est dans le bloc « Actions Home Assistant », entre « Republier dans Home Assistant » et « Supprimer puis recréer dans Home Assistant » ; bridge actif et MQTT connecté, il est actif ; la surface par pièce ne change pas. L'état inactif (démon arrêté ou MQTT déconnecté) n'a pas été provoqué sur la box : il est couvert par les tests Node.
- AC2 : la confirmation s'intitule « Rescanner la topologie Jeedom » et dit « Un sync complet peut publier ou retirer des entités Home Assistant et applique les overrides persistés. Confirmer ? » ; bouton « Rescanner ». L'annulation (croix, Échap, Annuler) est couverte par les tests Node.
- AC3 et AC4 : le sync passe par `scanTopology` ; succès lisible, puis bandeau santé rafraîchi (« Dernière synchro », « Dernière opération »). L'état « Rescan en cours… » dure moins d'une seconde sur la box ; il est couvert par les tests Node, comme les retours d'échec, d'expiration, de résultat partiel et de 409, qui n'ont pas été provoqués sur la box.
- AC5 : la page de configuration affiche « Appliquer les filtres et rescanner ».
- AC6 : topologie complète relue, décisions, publications, cache, résumé ; écouteurs réalignés après la réponse (227).
- AC7 : rescan déclaré et simulé par le gate (PASS), puis clic réel prouvé à part, parité identique.
- AC8 : le verrou du sync est prouvé par les tests Python (les deux sens, l'attente bornée et son expiration, `shield`). Sur la box, les syncs du démarrage et du déploiement de 08:06 sont passés sans 409.

**Constats non bloquants, reportés :**
- **Scénarios désactivés, boutons gardés dans HA (CC-44, antérieur à 20-4).** Les scénarios 72 et 2 étaient désactivés dans Jeedom (`isActive=0`, relevé par clawbox) au moment du rescan de 09:28. Le rescan ne les publie plus et les retire de `scenario_publications` (« Purged stale scenario_id »), mais en mémoire seulement : leurs topics de discovery retenus `homeassistant/button/jeedom2ha_scenario_72/config` et `…_2/config` restent sur le broker, et HA garde les deux boutons. À traiter dans une story ultérieure.
- **Autres actions HA sous la confirmation (P3 de relecture).** Pendant que la confirmation du rescan est ouverte, « Republier » et « Supprimer puis recréer » ne sont pas encore désactivés ; ils le sont après la confirmation (AC3). Si l'une partait entre-temps, le verrou du démon (AC8) répondrait au rescan par un 409 lisible.

## Verdict

**20-4 est prouvée et validée UX, et passe `done`.** Le rescan du volet UI de CC-04 est livré. CC-40 (sync sans verrou) et CC-41 (faux succès de `scanTopology`) sont fermés.
