# Story H5 : Appareil « Santé de Jeedom » en lecture seule (option, désactivée par défaut)

Status: done

Epic: (Chantier hors cycle BMAD 2026-11, rattachement rétrospectif)

Story Key (sprint-status): `h5-appareil-sante-de-jeedom`

> **Story rédigée après coup le 23/11/2026 : le développement n'a pas suivi le cycle BMAD.**
> Sources : la PR #414 (fusion `5f25cdb`), sa description, ses commits et ses fils de revue, lus par l'API REST GitHub ; pour la production, seuls les faits transmis le 23/11 (voir « Faits de production »). Aucun accès à la box ni à Home Assistant pour cette rédaction. Ce qui ne se déduit pas de ces sources est écrit « non établi ».

## Story

En tant qu'utilisateur qui surveille sa domotique depuis Home Assistant,
je veux un appareil « Santé de Jeedom » qui montre l'état des démons des plugins, les mises à jour disponibles, le nombre de messages et la version du cœur,
afin de voir dans HA qu'un démon Jeedom est arrêté, sans ouvrir Jeedom.

**Parcours : PHP (relevé, cron, configuration) + démon (route, mapper, discovery).** Fonction générique, utile à toute installation. Désactivée par défaut.

## Critères d'acceptation (tels que livrés)

1. **AC1 — Entités.** Appareil `jeedom2ha_system` « Santé de Jeedom », rattaché au pont (`via_device: jeedom2ha_bridge`). Toutes les entités en `entity_category: diagnostic`, **sans aucun `command_topic`**, avec la disponibilité du pont :
   - un `binary_sensor` `running` par plugin actif à démon propre (`hasOwnDeamon`), `jeedom2ha_system_daemon_<plugin>` : `ON` si `deamon_info()['state'] === 'ok'`, sinon `OFF` (état illisible → `OFF`) ;
   - `sensor` « Démons en service » et « Démons arrêtés » (`state_class: measurement`), calculés par le démon sur la même liste que les `binary_sensor` ;
   - `sensor` « Mises à jour disponibles » (`update::nbNeedUpdate()`), « Messages » (`message::nbMessage()`, le nombre seulement, jamais le texte), « Version du cœur » (`jeedom::version()`).
2. **AC2 — Périmètre.** Un plugin sans démon ne produit rien ; jeedom2ha n'y figure pas (déjà « État du pont ») ; aucun compteur propre à un protocole.
3. **AC3 — Pas de valeur inventée.** Un compteur ou une version illisible garde son entité sans publier d'état.
4. **AC4 — Désactivé par défaut.** Case « Publier la santé de Jeedom » (`publishSystemHealth`), bloc « Santé de Jeedom » de la configuration. Décochée : le cron ne lit rien et n'appelle pas le démon, et la trace MQTT est strictement identique à `main` (`0b826bb`, 186 messages, 125 entités de la scène de test).
5. **AC5 — Décocher purge.** Une seule demande de purge ; configurations retenues relues sur le broker (qui fait foi), puis vidées avec leurs états ; seul le motif strict `<prefix>/(binary_sensor|sensor)/jeedom2ha_system_<clé>/config` est touché ; purge incomplète réessayée.
6. **AC6 — Envoi sur changement.** `jeedom2ha::cron5()` (dans un `try` séparé) n'envoie le relevé que si son empreinte SHA-256 (indépendante de l'ordre) change ; un envoi échoué ou partiel efface l'empreinte ; le démarrage du démon l'oublie ; `postSaveConfiguration` applique la case sans jamais bloquer l'enregistrement.
7. **AC7 — Démon.** Route `POST /action/system_health` protégée par le secret, corps validé, 503 si le broker est indisponible ; mapper hors du circuit des équipements (ni `publications`, ni `mappings`, ni compteurs) ; retrait d'un plugin disparu ; republication du dernier relevé à chaque connexion au broker et au retour de HA ; un retrait incomplet répond `status: error`.
8. **AC8 — Aucune collision d'espace de noms** avec les équipements, les `select`, les capteurs « État » des portails, les scénarios et le pont ; aucune commande exécutable sur ces topics (testé).
9. **AC9 — Ajouts seulement** dans `resources/daemon/`, `core/ajax/` et `core/class/` ; compatible Jeedom 4.4, 4.5 et 4.6 (`class_exists`, `method_exists`, un `try` par plugin).

## UI Impact

- **UI Impact:** Oui (case et bloc « Santé de Jeedom » dans la configuration du plugin)

## Tâches

- [x] T1 — Relevé PHP pur `core/php/jeedom2ha_system_health.php` (lectures, appel au démon et journal injectés) ; câblage dans `core/class/jeedom2ha.class.php` (`cron5`, `postSaveConfiguration`, `deamon_start`).
- [x] T2 — Case de configuration (`plugin_info/configuration.php`).
- [x] T3 — Démon : `mapping/system_health.py`, `discovery/system_health.py`, route dans `transport/http_server.py`.
- [x] T4 — Revue Codex traitée (`757bf22`) : retrait incomplet compté en échec ; empreinte effacée après un envoi échoué. Puis `53757a2` (republication après redémarrage du broker, une seule collecte par envoi) et `a3f3c4d` (décocher oublie le relevé même broker absent).
- [x] T5 — Tests et documentation (`docs/fr_FR/index.md`, section « Santé de Jeedom » ; `changelog_beta.md`).
- [x] T6 — Validation sur la démo avant la production : faite ; elle a révélé un 400 sur `/action/system_health`, cause de la story H6 (#415).
- [x] T7 — Mise en production (avec H6) : `c015cc9`, 22/11/2026 à 12:13.

## Dev Agent Record

### Agent Model Used

Session Claude Code (signature de la PR) ; modèle exact : non établi.

### Fusion

- PR #414, branche `story/system-health`, tête `a3f3c4d`, fusionnée le 20/11/2026 à 06:19 UTC : `5f25cdbd12c615dd9bb7a7e40a664e0980250e00`.
- Commits : `2e34e9d`, `757bf22`, `53757a2`, `a3f3c4d`.
- CI de la tête : verte.

### Fichiers

- PHP : `core/class/jeedom2ha.class.php`, `core/php/jeedom2ha_system_health.php` (nouveau), `plugin_info/configuration.php`.
- Démon : `resources/daemon/mapping/system_health.py`, `discovery/system_health.py` (nouveaux), `transport/http_server.py`.
- Documentation : `docs/fr_FR/index.md`, `docs/fr_FR/changelog_beta.md`.
- Fixtures : `tests/fixtures/system_health/projection_baseline.json` (nouveau).

### Tests

- `resources/daemon/tests/unit/test_story_system_health.py` (54 tests d'après la PR).
- `tests/test_php_story_system_health.php` (58 vérifications).
- `tests/unit/test_story_25_9_configuration.node.test.js` (case décochée par défaut, info-bulle, Chromium réel).
- Résultat annoncé par la PR : `make test` 827 passés ; démon 2737 passés ; `flake8` vert ; Node 1628 passés, 0 échec ; PHP vert. Rejouer : `make test`, `flake8`, `node --test tests/unit/*.node.test.js`, `php tests/test_php_story_system_health.php`.
- Limite : les tests de #414 postaient le corps nu à la route, pas l'enveloppe réelle de `callDaemon` ; d'où le 400 vu sur la démo (H6).

### Faits de production

- Démo validée avant la production (avec H6) ; le 400 trouvé sur la démo est la cause de H6.
- `c015cc9` (contient `5f25cdb`) déployé en production le 22/11/2026 à 12:13.
- Appareil « Santé de Jeedom » actif en production ; 427 entités (relevé transmis ; périmètre exact du décompte : non établi).
- Inventaire détaillé avant / après et relevé d'erreurs du démon : non établi.

## Change Log

- 2026-11-20 — PR #414 ouverte (`2e34e9d`) ; revue Codex (2 × P2) traitée (`757bf22`) ; `53757a2`, `a3f3c4d`.
- 2026-11-20 — Fusion dans `main` (`5f25cdb`).
- Avant le 20/11 06:42 UTC (ouverture de #415 ; heure exacte de l'essai non établie) — Essai sur la démo : 400 sur `/action/system_health` → H6 (#415).
- 2026-11-22 — En production avec `c015cc9` (12:13) ; appareil actif.
- 2026-11-23 — Story rédigée après coup (backfill BMAD), statut `done`.
