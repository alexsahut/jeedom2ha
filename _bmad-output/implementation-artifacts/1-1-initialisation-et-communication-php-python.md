# Story 1.1: Initialisation et Communication PHP ↔ Python

Status: done

## Story

As a utilisateur Jeedom,
I want que le plugin démarre son démon correctement et affiche son statut,
So that je sache que le moteur interne est actif.

## Acceptance Criteria

1. **Given** le plugin est installé **When** je clique sur "Démarrer" le démon **Then** le démon Python démarre dans le venv Jeedom via `system::getCmdPython3(__CLASS__)`
2. **And** l'interface Jeedom affiche le statut du démon (OK)
3. **And** une requête HTTP locale PHP → daemon sur 127.0.0.1 fonctionne (API liée à 127.0.0.1 uniquement)
4. **And** le heartbeat retourne un payload structuré de type statut/version/uptime minimal
5. **And** si le démon ne répond pas, l'état est visible clairement dans l'UI (KO/Erreur)

## Tasks / Subtasks

- [x] **Task 1 — Squelette daemon Python avec `jeedomdaemon`** (AC: #1)
  - [x] 1.1 Créer la classe `Jeedom2haDaemon(BaseDaemon)` dans `resources/daemon/main.py`
  - [x] 1.2 Implémenter `on_start()` : log démarrage, initialiser l'API HTTP locale
  - [x] 1.3 Implémenter `on_stop()` : arrêt propre, libération des ressources
  - [x] 1.4 Implémenter `on_message()` : stub pour les messages PHP → daemon
  - [x] 1.5 Ajouter l'appel `Jeedom2haDaemon().run()` comme point d'entrée

- [x] **Task 2 — API HTTP locale du daemon** (AC: #3, #4)
  - [x] 2.1 Créer `resources/daemon/transport/http_server.py` avec serveur aiohttp sur `127.0.0.1`
  - [x] 2.2 Implémenter endpoint `/system/status` retournant l'enveloppe standard : `{"action": "system.status", "status": "ok", "payload": {"version": "0.1.0", "uptime": <seconds>}, "request_id": "...", "timestamp": "ISO8601"}`
  - [x] 2.3 Implémenter l'authentification par `local_secret` (header ou payload, rejet 401 si absent/invalide)
  - [x] 2.4 Port configurable via argument CLI `--apiport` (défaut suggéré : 55080)

- [x] **Task 3 — Gestion du daemon côté PHP** (AC: #1, #2, #5)
  - [x] 3.1 Implémenter `deamon_start()` dans `jeedom2ha.class.php` : lancer le daemon via `system::getCmdPython3(__CLASS__)` avec les arguments standard
  - [x] 3.2 Implémenter `deamon_stop()` : arrêt propre via PID
  - [x] 3.3 Implémenter `deamon_info()` : retourner le statut du daemon (launchable, state, log)
  - [x] 3.4 Générer un `local_secret` aléatoire s'il n'existe pas encore, le stocker en configuration plugin (`setConfiguration`), le réutiliser aux démarrages suivants, le passer en argument CLI au daemon

- [x] **Task 4 — Healthcheck PHP → daemon** (AC: #3, #4, #5)
  - [x] 4.1 Créer une méthode utilitaire PHP `callDaemon($endpoint, $payload)` qui fait un HTTP GET/POST vers le daemon local avec timeout court (3s) + au plus 1 retry **uniquement sur les appels idempotents** (GET `/system/status`). Les appels non idempotents (POST `/action/*`) ne doivent jamais être retentés automatiquement.
  - [x] 4.2 Intégrer l'appel `/system/status` dans `deamon_info()` pour valider la liveness
  - [x] 4.3 Gérer les cas d'erreur : daemon non joignable → statut KO visible dans l'UI

- [x] **Task 5 — Configuration `packages.json` et dépendances** (AC: #1)
  - [x] 5.1 Créer `plugin_info/packages.json` avec les dépendances pip3 : `jeedomdaemon`, `aiohttp` (paho-mqtt sera ajouté en story 1.2/1.3)
  - [x] 5.2 Vérifier la compatibilité avec le venv Jeedom

- [x] **Task 6 — Tests unitaires daemon** (AC: tous)
  - [x] 6.1 Créer `tests/unit/test_daemon_startup.py` : test de l'instanciation du daemon
  - [x] 6.2 Créer `tests/unit/test_http_server.py` : test de l'endpoint `/system/status`, test du rejet sans `local_secret`

## Dev Notes

### Architecture & Patterns obligatoires

**Transport interne (Architecture Decision):**
- PHP → Daemon : requête HTTP locale sur `127.0.0.1:<port>` protégée par `local_secret`.
- Daemon → PHP : callbacks asynchrones via l'API Jeedom (`jeeApi.php`) avec la clé API du plugin. **Hors scope de cette story** — sera implémenté dans les stories suivantes quand le daemon aura besoin de remonter des événements vers PHP.
- Ces deux canaux sont **indépendants du broker MQTT** — le contrôle fonctionne même si MQTT est en panne.

**Format d'échange (Architecture Decision):**
```json
// Requête
{"action": "string", "payload": {}, "request_id": "string", "timestamp": "ISO8601"}
// Réponse
{"action": "string", "status": "ok|error", "payload": {}, "request_id": "string", "timestamp": "ISO8601", "error_code": "optional", "message": "optional"}
```

**Sécurité API locale:**
- `local_secret` : chaîne aléatoire courte générée par PHP **une seule fois** (si absente), stockée en config plugin, réutilisée aux démarrages suivants, passée au daemon via CLI.
- Toute requête sans `local_secret` valide → rejet 401.
- Écoute strictement sur `127.0.0.1`, jamais `0.0.0.0`.

**Endpoints autorisés V1 (à implémenter progressivement) :**
- `/system/status` — liveness probe (cette story)
- `/action/sync`, `/action/publish`, `/action/remove` — stories ultérieures

**Daemon Python :**
- Hériter de `BaseDaemon` (`jeedomdaemon`).
- Méthodes async : `on_start()`, `on_message()`, `on_stop()`.
- Lancement via `system::getCmdPython3(__CLASS__)` — **OBLIGATOIRE** pour le venv Jeedom.
- Paramètres CLI standard : `--loglevel`, `--sockethost`, `--socketport`, `--callback`, `--apikey`, `--pid`, `--cycle`.
- Ajouter `--apiport` pour le port de l'API HTTP locale.

**PHP daemon management :**
- Méthodes statiques dans `jeedom2ha extends eqLogic` :
  - `deamon_start()` — lance le processus Python.
  - `deamon_stop()` — arrête via PID.
  - `deamon_info()` — retourne `['launchable' => ..., 'state' => ..., 'log' => ...]`.
- Le core Jeedom appelle ces méthodes automatiquement. Ne pas les renommer.
- Orthographe Jeedom : `deamon` (pas `daemon`) dans les noms de méthodes PHP.

**Logs :**
- PHP : `log::add('jeedom2ha', 'debug|info|warning|error', $message)`
- Python : utiliser le logger fourni par `jeedomdaemon` (s'intègre avec le système de logs Jeedom)
- Catégories recommandées : `[DAEMON]`, `[API]`, `[MQTT]` (pour les stories suivantes)

### Project Structure Notes

**Fichiers à créer ou modifier dans cette story :**

```
jeedom2ha/
├── core/class/jeedom2ha.class.php     # MODIFIER: ajouter deamon_start/stop/info, callDaemon()
├── plugin_info/
│   ├── info.json                       # VÉRIFIER: hasOwnDeamon=true, hasDependency=true déjà OK
│   └── packages.json                   # CRÉER: dépendances pip3
├── resources/
│   └── daemon/
│       ├── main.py                     # MODIFIER: implémenter Jeedom2haDaemon(BaseDaemon)
│       └── transport/
│           ├── __init__.py             # CRÉER
│           └── http_server.py          # CRÉER: serveur aiohttp local
└── tests/
    └── unit/
        ├── test_daemon_startup.py      # CRÉER
        └── test_http_server.py         # CRÉER
```

**Fichiers existants à NE PAS toucher :**
- `desktop/php/jeedom2ha.php` — page principale UI (story ultérieure)
- `desktop/js/jeedom2ha.js` — JS frontend (story ultérieure)
- `core/ajax/jeedom2ha.ajax.php` — endpoints AJAX (story ultérieure)
- `resources/demond/` — ancien dossier template, ignoré (le daemon est dans `resources/daemon/`)

### Code existant à réutiliser

Le squelette plugin est déjà bootstrappé (commit `654dedc`):
- `jeedom2ha.class.php` contient les classes vides `jeedom2ha extends eqLogic` et `jeedom2haCmd extends cmd`
- `info.json` a `hasOwnDeamon: true` et `hasDependency: true`
- `resources/daemon/main.py` existe avec un stub vide
- `tests/` structure existe avec `conftest.py`, `unit/`, `integration/`

### Pièges à éviter

- **NE PAS** utiliser `python3` directement → utiliser `system::getCmdPython3(__CLASS__)` pour le venv Jeedom.
- **NE PAS** écouter sur `0.0.0.0` → strictement `127.0.0.1`.
- **NE PAS** hardcoder le port du daemon → le rendre configurable.
- **NE PAS** utiliser `echo`, `var_dump` dans le PHP → uniquement `log::add()`.
- **NE PAS** confondre `deamon` (orthographe Jeedom) et `daemon` (orthographe standard) dans les noms de méthodes PHP.
- **NE PAS** implémenter de logique MQTT dans cette story — c'est story 1.2/1.3.
- **NE PAS** créer de tables DB — utiliser `$this->setConfiguration()` / `$this->getConfiguration()`.
- **NE PAS** créer de fichier `resources/demond/jeedom2had.py` — le daemon vit dans `resources/daemon/main.py` selon l'architecture.

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#API & Internal Communication Patterns]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation Patterns & Consistency Rules]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure & Boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Infrastructure & Deployment]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.1]
- [Source: _bmad-output/project-context.md#Règles Python (Daemon)]
- [Source: _bmad-output/project-context.md#Règles PHP (Plugin Jeedom)]
- [Source: docs Jeedom daemon plugin - system::getCmdPython3]
- [Source: PyPI jeedomdaemon - BaseDaemon async pattern]

## Validation manuelle (instance Jeedom de dev)

- [ ] Démarrer le démon depuis l'UI Jeedom → statut OK
- [ ] Arrêter le démon → statut KO
- [ ] Modifier temporairement le `local_secret` côté PHP → healthcheck en échec
- [ ] Vérifier dans les logs que ni `local_secret` ni `apikey` n'apparaissent en clair
- [ ] Vérifier qu'un appel non idempotent (POST) n'est pas relancé automatiquement

## Senior Developer Review (AI)

**Date :** 2026-03-13
**Reviewer :** Claude Sonnet 4.6 (différent du dev agent Opus 4.6)
**Outcome :** Changes Requested → Applied

### Findings & Resolutions

| # | Sévérité | Description | Fichier | Résolu |
|---|---|---|---|---|
| H1 | 🔴 HIGH | Import `from resources.daemon.transport...` → `ModuleNotFoundError` en production (sys.path script ≠ pytest) | `main.py:11` | ✅ |
| M1 | 🟡 MED | `pyproject.toml` modifié mais absent du File List | File List | ✅ |
| M2 | 🟡 MED | Tests dans `tests/unit/` vs `resources/daemon/tests/` spécifié par l'architecture | Déviation documentée | ⚠️ |
| M3 | 🟡 MED | Timeout effectif `deamon_start()` : jusqu'à 150s (callDaemon 6.5s × 20) au lieu de 20s | `jeedom2ha.class.php` | ✅ |
| M4 | 🟡 MED | `test_on_start_runs_without_error` ouvre un vrai socket port 55080, sans cleanup | `test_daemon_startup.py` | ✅ |
| L1 | 🟢 LOW | `_start_time` global module : uptime en test ≠ uptime serveur | `http_server.py` | ✅ |
| L2 | 🟢 LOW | Imports morts (`AioHTTPTestCase`, `TestClient`, `TestServer`, `json`) | `test_http_server.py` | ✅ |
| L3 | 🟢 LOW | Retry interval 500ms implémenté, architecture spécifie 1s | `jeedom2ha.class.php` | ✅ |

**M2 — Note déviation architecture :** L'architecture spec indique `resources/daemon/tests/`. Les tests sont dans `tests/unit/` (racine repo) car la story 1.1 le spécifiait ainsi et la structure `tests/` pré-existait. À arbitrer en début d'Epic 2 pour aligner la structure de test avec l'archi.

### Post-Review

- 7/8 findings corrigés automatiquement
- Tests : 28/28 passent (dont 1 nouveau test `test_on_start_calls_start_server_with_localhost`)
- Zéro régression

## Change Log

- **2026-03-13**: Implémentation complète de la story 1.1 — daemon Python avec API HTTP locale, gestion PHP du daemon, healthcheck, packages.json, et tests unitaires.
- **2026-03-13**: Fix sécurité — masquage de `local_secret` et `apikey` dans les logs de lancement. Ajout checklist de validation manuelle PHP.
- **2026-03-13**: Code review (Claude Sonnet 4.6) — 7 findings corrigés : import path production (H1), timeout deamon_start() (M3), socket test isolé (M4), uptime global→app state (L1), imports morts (L2), retry interval 1s (L3), pyproject.toml ajouté au File List (M1).

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

Aucun problème bloquant rencontré.

### Completion Notes List

- **Task 1**: Classe `Jeedom2haDaemon(BaseDaemon)` créée avec config custom (`Jeedom2haConfig` ajoutant `--apiport` et `--localsecret`). Callbacks async `on_start`, `on_message`, `on_stop` implémentés. Point d'entrée `if __name__ == "__main__"` en place. `sys.path` fixé pour production.
- **Task 2**: Serveur aiohttp dans `resources/daemon/transport/http_server.py`. Endpoint `/system/status` retourne l'enveloppe JSON standard (action, status, payload avec version/uptime, request_id, timestamp). Authentification par header `X-Local-Secret` avec rejet 401. Port configurable via `--apiport` (défaut 55080). `start_time` stocké dans app state (pas de global).
- **Task 3**: Méthodes statiques PHP `deamon_start()`, `deamon_stop()`, `deamon_info()` dans `jeedom2ha.class.php`. Lancement via `system::getCmdPython3(__CLASS__)`. Génération du `local_secret` via `bin2hex(random_bytes(16))`, stocké en config plugin (`config::byKey/save`). Passage au daemon via CLI `--localsecret`. Timeout deamon_start() basé sur elapsed time (20s réels).
- **Task 4**: Méthode `callDaemon($endpoint, $payload, $method)` avec timeout 3s, retry 1s uniquement sur GET idempotents (max 2 tentatives). Intégrée dans `deamon_info()` pour healthcheck. Erreurs → statut KO.
- **Task 5**: `packages.json` mis à jour avec `jeedomdaemon` et `aiohttp` en pip3. Templates obsolètes (pyserial, requests, npm/composer/yarn) supprimés.
- **Task 6**: 11 tests daemon (`test_daemon_startup.py`) + 6 tests HTTP (`test_http_server.py`) = 17 nouveaux tests. 28 tests au total, zéro régression. `on_start` mocké proprement (pas de socket réel).

- **Correction post-review — stub callback `core/php/jeedom2ha.php` :** `jeedomdaemon` tente de joindre le callback `--callback` au démarrage et s'arrête si le endpoint retourne une réponse non-200. Une première version du stub incluait `require_once core.inc.php`, ce qui provoquait un HTTP 500 sur la box (chemin `core.inc.php` inaccessible dans ce contexte). Corrigé : le stub est désormais un fichier PHP pur sans aucune dépendance Jeedom — réponse HTTP 200 + `Content-Type: application/json; charset=utf-8` + `{"status":"ok"}`, gestion d'erreur via `catch (\Throwable $e)` → HTTP 500. La logique métier complète (remontée d'états, réception d'événements daemon → Jeedom) reste hors scope Story 1.1 et sera implémentée dans une story ultérieure.

- **Note — emplacement des tests (déviation architecture) :** L'architecture spécifie `resources/daemon/tests/` comme emplacement cible des tests Python. Les tests de cette story sont placés dans `tests/unit/` à la racine du repo, où la structure CI (`pyproject.toml`, `.github/workflows/`) était déjà établie avant cette story. Ce choix préserve le fonctionnement CI actuel sans refactor. À arbitrer en début d'Epic 2 : si l'alignement vers `resources/daemon/tests/` est souhaité, cela implique de déplacer les fichiers de test et d'ajuster `pyproject.toml` (`testpaths`).

### File List

- `resources/daemon/main.py` (modifié) — Daemon Python complet avec `Jeedom2haDaemon(BaseDaemon)`, `Jeedom2haConfig`, fix sys.path
- `resources/daemon/transport/__init__.py` (créé) — Package init
- `resources/daemon/transport/http_server.py` (créé) — Serveur aiohttp local avec `/system/status`, auth `local_secret`, uptime via app state
- `core/class/jeedom2ha.class.php` (modifié) — Ajout `deamon_start()`, `deamon_stop()`, `deamon_info()`, `callDaemon()`, timeout elapsed-time, retry 1s
- `plugin_info/packages.json` (modifié) — Dépendances pip3 : jeedomdaemon, aiohttp
- `pyproject.toml` (modifié) — Dépendances de test (pytest-aiohttp ajouté)
- `tests/unit/test_daemon_startup.py` (créé) — 11 tests instanciation/lifecycle daemon, on_start mocké
- `tests/unit/test_http_server.py` (créé) — 6 tests endpoint status + auth
- `core/php/jeedom2ha.php` (créé, corrigé) — Stub callback daemon → Jeedom, HTTP 200 pur sans dépendance Jeedom
