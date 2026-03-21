# Story 5.1-bis: Bugfix — création automatique du répertoire data

Status: done  # terrain validé 2026-03-21, tous les AC PASS

## Story

As a **utilisateur installant le plugin jeedom2ha pour la première fois** (ou mettant à jour),
I want **que le répertoire `data/` du plugin soit créé automatiquement avec les bons droits**,
so that **le cache disque (story 5.1) fonctionne dès le premier démarrage sans intervention manuelle**.

## Contexte

Bug terrain identifié lors de la validation de la story 5.1 : le répertoire `/var/www/html/plugins/jeedom2ha/data` n'est pas créé automatiquement par le plugin. Sans ce dossier, le daemon logge un WARNING (`data_dir introuvable`) et le cache disque ne peut pas être écrit. Un contournement manuel (`mkdir -p` + `chown www-data:www-data`) a été nécessaire en terrain.

Ce bug relève du lifecycle d'installation/activation du plugin (`plugin_info/install.php`), pas de la logique runtime de persistance couverte par 5.1.

## Acceptance Criteria

### Groupe A — Création du répertoire

1. **AC #1 — Installation fraîche** : Après une installation fraîche du plugin via le Market ou manuellement, le répertoire `data/` existe sous la racine du plugin (`/var/www/html/plugins/jeedom2ha/data/`).

2. **AC #2 — Mise à jour du plugin** : Après une mise à jour du plugin (passage de version), le répertoire `data/` existe s'il n'existait pas déjà. Si le répertoire existait déjà, il n'est pas modifié (contenu préservé).

3. **AC #3 — Permissions compatibles** : Le répertoire `data/` a des permissions compatibles avec l'exécution du daemon Python (lecture + écriture). L'ownership est hérité de l'utilisateur d'exécution Jeedom (`www-data`) — aucun `chown` explicite n'est nécessaire.

### Groupe B — Non-régression

4. **AC #4 — Installation existante inchangée** : Sur une installation existante où le répertoire `data/` est déjà présent avec un cache valide, aucun changement de comportement. Le contenu du cache n'est ni supprimé ni altéré.

5. **AC #5 — Aucun warning data_dir au premier sync** : Après installation fraîche + premier démarrage du daemon + premier `/action/sync`, aucun warning `data_dir introuvable` ou `Impossible de sauvegarder le cache` n'apparaît dans les logs.

6. **AC #6 — Pas de modification runtime** : La logique métier du cache disque (`disk_cache.py`), du lifecycle MQTT, du reboot et de la republication n'est pas modifiée.

7. **AC #7 — Échec de création observable** : Si la création du répertoire `data/` échoue (permissions filesystem, partition read-only, etc.), un log `ERROR` explicite est émis via `log::add('jeedom2ha', 'error', ...)`. Il ne doit jamais y avoir d'échec silencieux — le comportement doit être observable et diagnosticable.

## Tasks / Subtasks

- [x] Task 0 — Pre-flight terrain (AC: tous)
  - [x] 0.1 Vérifier accès SSH à la box Jeedom de test
  - [x] 0.2 Identifier le chemin exact de `install.php` sur la box (`/var/www/html/plugins/jeedom2ha/plugin_info/install.php`)
  - [x] 0.3 Confirmer que le dossier `data/` n'est PAS créé actuellement lors d'une installation fraîche (reproduction du bug)

- [x] Task 1 — Implémentation dans install.php (AC: #1, #2, #3)
  - [x] 1.1 Dans `jeedom2ha_install()`, ajouter la création idempotente du répertoire `data/` avec `mkdir($dir, 0775, true)` si absent (ownership hérité du contexte `www-data`, pas de `chown` explicite)
  - [x] 1.2 Dans `jeedom2ha_update()`, ajouter la même logique de création conditionnelle (idempotente) pour couvrir les mises à jour sur installations existantes sans le dossier
  - [x] 1.3 Utiliser les fonctions PHP standard (`mkdir()`, permissions `0775`) et vérifier l'existence préalable (`is_dir()`) pour l'idempotence
  - [x] 1.4 Logger via `log::add('jeedom2ha', 'info', ...)` la création effective du dossier
  - [x] 1.5 En cas d'échec de `mkdir()`, logger un `ERROR` explicite via `log::add('jeedom2ha', 'error', ...)` — jamais d'échec silencieux (AC #7)

- [x] Task 2 — Tests unitaires PHP (AC: #1, #2, #4)
  - [x] 2.1 Évaluer la testabilité de `install.php` dans le contexte Jeedom (fonctions globales, dépendance `core.inc.php`)
  - [ ] 2.2 Si testable : écrire un test vérifiant la création du dossier et l'idempotence
  - [x] 2.3 Si non testable unitairement (probable) : documenter la raison et s'appuyer sur la validation terrain

- [x] Task 3 — Validation terrain (AC: #1, #2, #3, #4, #5, #7)
  - [x] 3.1 Supprimer manuellement le dossier `data/` sur la box de test
  - [x] 3.2 Simuler une installation/activation du plugin (appel à `jeedom2ha_install()` ou réinstallation complète)
  - [x] 3.3 Vérifier que `data/` est recréé avec les bons droits (`ls -la`)
  - [x] 3.4 Démarrer le daemon et exécuter un premier sync
  - [x] 3.5 Vérifier absence de warning `data_dir` dans les logs
  - [x] 3.6 Vérifier qu'une installation existante avec cache n'est pas altérée (AC #4)

## Dev Notes

### Fichier cible principal

- `plugin_info/install.php` — seul fichier à modifier

### Pattern Jeedom standard

La convention Jeedom pour la création de répertoires dans `install.php` est :

```php
function jeedom2ha_install() {
    $dataDir = __DIR__ . '/../data';
    if (!is_dir($dataDir)) {
        if (!mkdir($dataDir, 0775, true)) {
            log::add('jeedom2ha', 'error', 'Impossible de créer le répertoire data/ : ' . $dataDir);
        } else {
            log::add('jeedom2ha', 'info', 'Répertoire data/ créé automatiquement');
        }
    }
}
```

**Ownership** : Le core Jeedom exécute `install.php` sous l'utilisateur `www-data`. Le `mkdir()` PHP hérite automatiquement l'ownership de l'utilisateur d'exécution. Un `chown` explicite n'est ni nécessaire ni souhaitable — il ajouterait de la fragilité sans valeur.

### Périmètre strict

- **NE PAS** modifier `resources/daemon/cache/disk_cache.py`
- **NE PAS** modifier `resources/daemon/main.py`
- **NE PAS** modifier `resources/daemon/transport/http_server.py`
- **NE PAS** modifier la logique MQTT / reboot / republish
- **NE PAS** ajouter de logique de création de dossier dans le daemon Python — le daemon doit rester consommateur passif du dossier `data/`

### Dev Agent Guardrails

- **TERRAIN** : Cette story nécessite une validation sur box réelle Jeedom.
- Le test terrain consiste à vérifier que le hook `install.php` crée effectivement le dossier lors d'une installation/mise à jour.
- Consulter `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md` pour le contexte de test terrain.
- Ne pas exécuter de tests terrain automatiquement — attendre la validation manuelle par l'utilisateur.

### Project Structure Notes

- `plugin_info/install.php` : hooks lifecycle standard Jeedom (`_install`, `_update`, `_remove`)
- `data/` : répertoire runtime pour le cache disque, déjà dans `.gitignore`
- Aucun conflit de structure détecté

### References

- [Source: `plugin_info/install.php`] — hooks actuels vides
- [Source: `resources/daemon/cache/disk_cache.py`] — `save_publications_cache()` vérifie `os.path.isdir(data_dir)` avant écriture
- [Source: `resources/daemon/main.py`] — `_DAEMON_DATA_DIR` résolu vers `../../data` relatif au daemon
- [Source: `_bmad-output/implementation-artifacts/5-1-persistance-et-republication-post-reboot.md`] — story parent, follow-up identifié
- [Source: `_bmad-output/planning-artifacts/architecture.md#Technical Constraints`] — données runtime stockées dans `data/`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (2026-03-20)

### Debug Log References

Aucun blocage. Implémentation directe selon le pattern de la story Dev Notes.

### Completion Notes List

- ✅ Task 1 : `jeedom2ha_install()` et `jeedom2ha_update()` modifiées avec création idempotente de `data/` (pattern `is_dir` + `mkdir` 0775 + logs info/error)
- ✅ Task 2.1 / 2.3 : `install.php` non testable unitairement — nécessite `core/php/core.inc.php` Jeedom et `log::add()` (méthode statique Jeedom). Le projet n'utilise pas PHPUnit. Validation terrain (Task 3) est le seul test réaliste.
- ✅ Task 3 : validation terrain complète sur box réelle (2026-03-21) — tous les AC PASS :
  - AC #1 : `jeedom2ha_install()` recrée `data/` après suppression — log INFO confirmé
  - AC #2 : `jeedom2ha_update()` recrée `data/` si absent — testé explicitement (rm + update + ls)
  - AC #3 : permissions `drwxr-xr-x www-data:www-data` — owner a rwx, daemon peut écrire (umask 0022 attendu)
  - AC #4 : cache `publications_cache.json` intact après `jeedom2ha_update()` — contenu préservé
  - AC #5 : `grep data_dir /var/www/html/log/jeedom2ha_daemon` vide après restart + sync
  - AC #6 : périmètre strict respecté — seul `install.php` modifié
  - AC #7 : branche `!mkdir → log::error` présente dans le code — validée par inspection

### File List

- `plugin_info/install.php` — modifié (Tasks 1.1–1.5)

### Change Log

- 2026-03-20 : Implémentation story 5.1-bis — création idempotente de `data/` dans `jeedom2ha_install()` et `jeedom2ha_update()`, avec log INFO si créé et log ERROR si échec mkdir
