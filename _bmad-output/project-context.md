---
project_name: 'jeedom2ha'
user_name: 'Alexandre'
date: '2026-03-15'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'quality_rules', 'workflow_rules', 'anti_patterns']
status: 'complete'
rule_count: 58
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- **PHP 8.x** (OOP) — Plugin Jeedom, classes `eqLogic` / `cmd`, endpoints AJAX, callbacks daemon
- **Python 3.9+** + **asyncio** — Daemon du plugin, via bibliothèque `jeedomdaemon` (Mips2648)
- **JavaScript** (jQuery) — Frontend plugin, interactions UI, pas de framework JS externe
- **HTML5 / CSS3** — Interface native Jeedom Core v4.4+, Bootstrap pour le layout
- **MQTT** (paho-mqtt) — Transport MQTT, compatible MQTT Manager ou broker externe
- **MySQL / MariaDB** — Persistance (via classes core Jeedom, pas de tables custom)
- **JSON-RPC 2.0** — API principale Jeedom (`jeeApi.php`)

### Dépendances clés
- `jeedomdaemon` (pip3) — Bibliothèque daemon Python async
- `paho-mqtt` (pip3) — Client MQTT Python
- `mqtt2` (plugin Jeedom) — MQTT Manager, chemin privilégié mais non exclusif (broker externe supporté)

### Plateformes cibles (baseline)
- Jeedom Core **v4.4.9+** (PHP 8.x)
- **Debian 12+** / Raspberry Pi OS
- **Python 3.9+**
- Home Assistant avec intégration MQTT activée, supportant le device discovery

## Critical Implementation Rules

### Règles PHP (Plugin Jeedom)

- **Héritage obligatoire** : la classe plugin DOIT hériter de `eqLogic`, la classe commandes DOIT hériter de `cmd`. Ne jamais contourner ce pattern.
- **Nommage des fichiers** : `jeedom2ha.class.php`, `jeedom2ha.ajax.php`, `jeedom2ha.php` (callback daemon) — toujours préfixé par l'ID du plugin.
- **Pas de tables DB custom** : utiliser `setConfiguration()` / `getConfiguration()` sur les objets `eqLogic` et `cmd` pour stocker les données spécifiques au plugin (champ JSON `configuration`).
- **Logs** : utiliser `log::add('jeedom2ha', 'debug|info|warning|error', $message)` — jamais de `echo`, `var_dump` ou `error_log`.
- **AJAX** : les endpoints AJAX doivent inclure `ajax::init()` et vérifier les droits. Retour via `ajax::success()` / `ajax::error()`.
- **Clé API** : chaque plugin a sa propre clé API. Ne jamais exposer la clé côté client JS.

### Règles Python (Daemon)

- **Hériter de `BaseDaemon`** (`jeedomdaemon`) : implémenter `on_start()`, `on_message()`, `on_stop()` en async.
- **Communication bidirectionnelle** : le daemon et le plugin PHP communiquent dans les deux sens. Le mécanisme de transport interne (socket TCP, HTTP callback, ou autre) sera défini dans l'architecture détaillée — ne pas figer prématurément.
- **Paramètres standard** : `--loglevel`, `--sockethost`, `--socketport`, `--callback`, `--apikey`, `--pid`, `--cycle` — respecter cette convention.
- **Écoute localhost uniquement** : le daemon écoute sur `127.0.0.1` par défaut, ne jamais ouvrir sur `0.0.0.0`.
- **Validation API key** : `jeedomdaemon` valide automatiquement la clé API dans les messages entrants — ne pas désactiver cette vérification.

### Règles JavaScript (Frontend)

- **jQuery uniquement** : pas de React, Vue, Angular ni autre framework JS. Vanilla JS acceptable pour les interactions simples.
- **Fichier JS principal** : `desktop/js/jeedom2ha.js` — respecter la convention de nommage.
- **Appels AJAX Jeedom** : utiliser les helpers Jeedom natifs pour les appels AJAX, pas de `fetch()` ou `$.ajax()` direct sauf nécessité absolue.

### Architecture Plugin Jeedom

- **Hiérarchie de données** : `jeeObject` (pièce) → `eqLogic` (équipement) → `cmd` (commande). Toujours respecter cette hiérarchie, ne jamais l'aplatir.
- **1 eqLogic Jeedom = 1 device HA (heuristique par défaut)** : c'est le mapping par défaut pour les équipements standards. Prévoir des exceptions pour les cas multi-canaux, les virtuels agrégés et les scénarios, qui peuvent nécessiter un mapping différent.
- **`generic_type` comme pivot de mapping** : c'est la clé primaire pour déterminer le type d'entité HA (ex: `LIGHT_STATE` → `light`, `TEMPERATURE` → `sensor`). Fallback sur `type`/`subType` uniquement si `generic_type` absent.
- **Identifiants basés sur IDs Jeedom** : utiliser les IDs numériques Jeedom (stables), jamais les noms d'équipements (renommables par l'utilisateur).
- **Objets Jeedom → Areas HA** : les objets Jeedom servent de source de contexte spatial et de base au `suggested_area`, comme heuristique, pas comme équivalence stricte.
- **Cron hooks** : déclarer les méthodes cron nécessaires (`cron()`, `cron5()`, etc.) dans la classe plugin et activer dans `info.json`. Minimiser les requêtes DB dans les crons fréquents.

### MQTT Discovery Home Assistant

- **Mode de discovery principal** : le plugin cible en priorité absolue le **device discovery** (`homeassistant/device/...`).
- **Mode de discovery secondaire** : le single-component discovery ne doit être utilisé que comme exception justifiée pour des entités ne pouvant logiquement pas appartenir à un équipement. Les deux modes impliquent des structures de topics et payloads différentes — l'harmonisation de l'implémentation doit se faire autour du device discovery.
- **Payload device-based** : chaque payload de discovery DOIT inclure un bloc `device` avec `identifiers` (basé sur l'ID Jeedom) pour regrouper les entités d'un même équipement.
- **Bloc `origin`** : inclure `"origin": {"name": "jeedom2ha", "sw_version": "X.X.X"}` dans chaque payload de discovery.
- **State/Command topics** : séparer les topics d'état (`state_topic`) et de commande (`command_topic`). Le daemon publie les états, écoute les commandes.
- **Suppression propre** : publier un payload vide sur le topic de config pour retirer une entité de HA. Ne jamais laisser d'orphelins.
- **Birth message HA** : réémettre toute la discovery quand `homeassistant/status` = `online` (redémarrage HA).
- **Availability** : configurer `availability_topic` pour que HA sache quand le pont est hors ligne.

### Communication Daemon ↔ Plugin PHP

- **Bidirectionnelle** : le daemon et le plugin PHP échangent des données dans les deux sens. Le mécanisme de transport exact sera défini dans l'architecture détaillée.
- **`event::changes`** : mécanisme clé pour la synchronisation **incrémentale des états** Jeedom → HA en temps réel. Le daemon poll les changements depuis un timestamp. Attention : les changements de topologie (ajout, suppression, renommage, changement de mapping) nécessitent toujours une logique de réconciliation / rescan complète, et ne sont pas couverts par `event::changes` seul.
- **`cmd::execCmd`** : pour exécuter une commande Jeedom depuis le daemon (commande retour HA → Jeedom).

### Règles de Test

- **Pas de framework de test intégré à Jeedom** : le core ne fournit pas de test runner pour les plugins. Les tests se structurent autour de deux axes indépendants.
- **Daemon Python testable isolément** : utiliser `pytest` pour tester le daemon Python indépendamment du core Jeedom. Mocker l'API JSON-RPC Jeedom pour les tests unitaires du daemon.
- **Tests d'intégration via Docker** : utiliser un environnement Docker Compose (Jeedom + Mosquitto + Home Assistant) pour les tests d'intégration end-to-end.
- **Tests manuels plugin PHP** : tester via l'interface Jeedom sur une instance de développement. Analyser les logs (`log::add`) pour valider le comportement.
- **Scénarios de test critiques** : toujours valider ces cas —
  - Renommage d'équipement Jeedom → pas de doublon dans HA
  - Suppression d'équipement Jeedom → suppression propre dans HA
  - Commande HA → exécution correcte dans Jeedom + retour d'état cohérent
  - Redémarrage HA → réémission automatique de la discovery
  - Broker MQTT indisponible → reconnexion automatique du daemon
  - Équipement sans `generic_type` → ne pas publier par défaut ; fallback raisonné uniquement quand une représentation honnête reste possible (pas de sensor/button systématique)

### Qualité de Code & Style

#### Structure de fichiers du plugin
```
jeedom2ha/
├── core/
│   ├── ajax/jeedom2ha.ajax.php
│   ├── class/jeedom2ha.class.php
│   └── php/jeedom2ha.php              # Callback daemon
├── desktop/
│   ├── css/jeedom2ha.css
│   ├── js/jeedom2ha.js
│   └── php/jeedom2ha.php              # Page principale
├── plugin_info/
│   ├── info.json                       # Métadonnées (OBLIGATOIRE)
│   ├── install.php                     # Scripts install/update/remove
│   ├── configuration.php               # Configuration globale
│   └── packages.json                   # Dépendances apt/pip/plugin
├── data/                                # Cache runtime, empreintes de config (PAS de règles métier de mapping)
├── resources/
│   └── jeedom2had/                     # Daemon Python
│       └── jeedom2had.py
└── docs/fr_FR/                         # Documentation auto-publiée
```

#### Conventions de nommage
- **Fichiers PHP** : `jeedom2ha.*` — toujours l'ID du plugin en préfixe
- **Daemon** : dossier `jeedom2had/`, fichier principal `jeedom2had.py` (convention `<plugin_id>d`)
- **Classes PHP** : `jeedom2ha extends eqLogic`, `jeedom2haCmd extends cmd`
- **Variables de configuration** : clés descriptives en camelCase dans `setConfiguration()`

#### UI / Frontend
- **Desktop-first**, composants natifs Jeedom (Bootstrap), variables CSS sémantiques du Core (thème clair/sombre compatible)
- **Rouge réservé aux pannes d'infrastructure** (broker down, daemon stoppé) — jamais pour les erreurs de configuration

### MVP Scope Guardrails

- **Périmètre V1** : lumières, prises/switches, volets/covers, capteurs numériques simples, capteurs binaires simples.
- **Exclusions V1 (NE PAS implémenter en première passe)** : thermostats/climate, scénarios riches, selects avancés, réconciliation sophistiquée, détection automatique des doublons.
- **En cas de doute** : rester toujours dans le périmètre MVP le plus strict.

### Workflow de Développement

#### Structure du projet
- **Fork du plugin-template** : point de départ depuis `jeedom/plugin-template`, renommer `template` → `jeedom2ha` dans tous les fichiers
- **Modèle Git canonique** : `story branch -> main -> beta -> stable`
- **Branche d'intégration** : `main` est la seule branche d'intégration canonique du projet
- **Clone principal local** : le clone principal local doit rester un miroir propre de `origin/main` et servir uniquement à la synchronisation, à la review et à la création des branches et worktrees de travail
- **Branches de publication** : `beta` et `stable` sont les branches de publication Jeedom Market ; `beta` reçoit uniquement des changements déjà intégrés sur `main`, `stable` uniquement des changements déjà passés par `beta`
- **Branches non canoniques** : `develop` n'est pas une branche canonique et ne doit plus apparaître dans la gouvernance cible
- **Développement local obligatoire** : aucune story, aucun fix et aucun sujet équivalent ne doivent être développés dans le clone principal local
- **Branche + worktree dédiés** : toute story ou tout fix doit être traité dans une branche dédiée créée depuis `main` et dans un worktree dédié attaché à cette branche
- **Préflight Git bloquant** : avant toute modification, vérifier que la branche courante n'est pas protégée, que le working tree est propre, que la branche est cohérente avec le sujet demandé et qu'elle ne contient pas déjà un autre sujet non validé ; si un contrôle échoue, l'agent doit s'arrêter
- **Règle agents IA** : les agents IA ne doivent jamais pousser directement sur `main`, `beta` ou `stable`
- **Référence de gouvernance** : voir `docs/git-strategy.md` pour la politique Git, commit, PR, merge et release
- **`info.json`** : fichier obligatoire dans `plugin_info/` — contient l'ID, le nom, la version, les `require` (version min Jeedom), les fonctionnalités activées (hasOwnDeamon, hasDependency, etc.)

#### Gestion des dépendances
- **`packages.json`** dans `plugin_info/` : déclarer les dépendances apt, pip3 et plugins
- **apt pour les dépendances système**, pip pour les libs Python applicatives (`jeedomdaemon`, `paho-mqtt`)
- **MQTT Manager (`mqtt2`)** : chemin privilégié (détection auto du broker), mais le plugin doit aussi supporter un broker MQTT externe configuré manuellement. Ne pas coder une dépendance structurelle à MQTT Manager.

#### Déploiement
- **Publication Market** : via token GitHub, synchronisation automatique branche → Market
- **Environnement de test** : instance Jeedom de dev avec le plugin installé en mode développeur
- **Logs exploitables** : niveaux debug/info/warning/error, toujours via `log::add()` côté PHP et le logger `jeedomdaemon` côté Python

### Règles Critiques — Anti-Patterns & Edge Cases

#### Principe produit fondamental
- **Principe de moindre nuisance** : dans le doute, ne rien publier vers HA plutôt que polluer avec des entités cassées, redondantes ou inutiles.
- **Prévisible plutôt que magique** : le plugin doit toujours pouvoir expliquer ce qu'il fait, ce qu'il ne fait pas, et pourquoi.
- **Validation explicite du périmètre** : le système prépare automatiquement, mais l'utilisateur garde une validation consciente de ce qui est publié. L'exclusion par équipement (au minimum) doit être prévue dans le MVP pour permettre un contrôle fin (l'exclusion par famille est un plus si peu coûteux, mais non bloquante).

#### Anti-patterns interdits
- **NE JAMAIS** créer un type HA "riche" incorrect (ex: `climate`) si la structure Jeedom est insuffisante → publier seulement les commandes individuelles honnêtes (sensor / binary_sensor / switch / number / button / select selon les cas) ou ne pas publier.
- **NE JAMAIS** utiliser les noms d'équipements comme identifiants → toujours les IDs numériques Jeedom
- **NE JAMAIS** publier automatiquement sans que l'utilisateur ait validé le périmètre
- **NE JAMAIS** laisser d'entités orphelines dans HA après suppression côté Jeedom
- **Préférer l'état réel** relu depuis Jeedom, mais accepter le mode optimiste ou stateless quand aucun retour d'état fiable n'existe. Ne jamais mentir sur l'état — signaler clairement l'absence de retour plutôt que simuler un état faux.
- **NE JAMAIS** exposer la clé API dans le code côté client JavaScript
- **NE JAMAIS** créer de tables DB custom → utiliser `configuration` JSON des classes core

#### Edge cases critiques
- **Équipements sans `generic_type`** : ne pas publier par défaut. Diagnostic clair "pourquoi non publié" avec piste de remédiation. Fallback raisonné uniquement si une représentation honnête existe.
- **Commandes atypiques de plugins exotiques** : exclure en V1, documenter les exclusions
- **État Jeedom non immédiatement relisible** : écart momentané action/état → gérer le délai sans mentir sur l'état
- **Volume important de discovery au redémarrage HA** : throttler les réémissions, respecter le birth message
- **Renommage d'objet Jeedom** : mettre à jour le `suggested_area` HA sans créer de doublon device
- **Conflits de versions pip entre plugins** : minimiser les dépendances pip applicatives, utiliser apt pour les dépendances système

#### Sécurité
- **Daemon localhost only** : écoute `127.0.0.1`, jamais `0.0.0.0`
- **Comparaison stricte `===`** pour les clés API (cf. CVE-2021-42557)
- **Validation des entrées** côté PHP pour toutes les données utilisateur
- **HTTPS** pour les communications API non-locales
- **Authentification Broker** : obligatoire pour un broker distant, fortement recommandée en local.
- **Protocoles Broker** : TLS + validation certificat requis hors du LAN nominal.

#### Télémétrie et Logs
- **Minimisation des données** : pas de télémétrie activée par défaut.
- **Diagnostics** : pas d'export de diagnostic contenant plus de données que strictement nécessaire pour le debug.
- **Confidentialité** : masquer ou minimiser les informations sensibles dans les logs et exports.

---

## Usage Guidelines

**Pour les agents IA :**

- Lire ce fichier avant d'implémenter du code
- Suivre TOUTES les règles exactement comme documentées
- En cas de doute, préférer l'option la plus restrictive
- Ne jamais développer dans le clone principal local
- Ne jamais démarrer un travail si le préflight Git bloque
- Mettre à jour ce fichier si de nouveaux patterns émergent

**Pour les humains :**

- Garder ce fichier concis et focalisé sur les besoins des agents
- Mettre à jour quand la stack technologique change
- Réviser périodiquement pour retirer les règles devenues évidentes
- Ajouter les nouvelles conventions découvertes en cours de développement

Last Updated: 2026-03-15
