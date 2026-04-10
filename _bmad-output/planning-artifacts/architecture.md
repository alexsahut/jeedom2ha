---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/planning-artifacts/research/domain-jeedom-homeassistant-research-2026-03-12.md
  - _bmad-output/planning-artifacts/research/technical-jeedom-plugin-development-research-2026-03-12.md
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-03-12.md
  - docs/cadrage_plugin_jeedom_ha_bmad.md
  - _bmad-output/project-context.md
workflowType: 'architecture'
project_name: 'jeedom2ha'
user_name: 'Alexandre'
date: '2026-03-12'
lastStep: 8
status: 'complete'
completedAt: '2026-03-12'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
Le système doit agir comme une projection Jeedom → Home Assistant pour la découverte, les métadonnées et les états ; et permettre des commandes Home Assistant → Jeedom pour le pilotage. L'architecture doit supporter un "généric-type first" mapping engine capable de décider quoi publier avec un niveau de confiance (sûr/ambigu/ignorer). Il inclut un cycle de vie robuste (détectant ajout, renommage avec IDs stables, suppression via payload MQTT retenu vide) et un moteur de filtrage/exclusion granulaire. Un sous-système de diagnostic métier est également vital pour remonter de manière transparente les raisons d'une non-publication à l'utilisateur.

**Non-Functional Requirements:**
Fiabilité et latence (idéalement ~1s, max 2s) sont les moteurs principaux. L'approche est purement locale (aucune fuite de télémétrie spontanée) et suit des recommandations de sécurité conformes (namespace MQTT isolé, mot de passe). L'architecture doit rester compatible avec un MVP volontairement contenu : lumières, prises/switches, volets/covers, capteurs simples, diagnostic P0, exclusions minimales et cycle de vie basique via rescan.

**Scale & Complexity:**
L'évaluation de la complexité est haute du fait de la synchronisation continue et croisée de deux écosystèmes asynchrones.
- Primary domain: Plugin domotique hybride (PHP Backend/UI + Daemon asynchrone Python + intégration MQTT)
- Complexity level: High (intégration, cycle de vie, compatibilité, soutenabilité) ; Medium (algorithmique pure).
- Estimated architectural components: ~5 (UI / Config PHP, Mapping & Publication Engine, State & Lifecycle Sync Engine, MQTT Transport Layer, Diagnostic & Observability Layer).

### Technical Constraints & Dependencies

- Démon Python 3.9+ basé sur `jeedomdaemon`, géré par le core Jeedom via le pattern standard plugin + daemon.
- Le plugin s’appuie sur les mécanismes standards de configuration Jeedom et sur les structures natives eqLogic / cmd, sans table SQL custom en V1.
- Les données runtime (cache, empreintes, état technique) sont stockées dans `data/`.
- Compatibilité minimale cible : Jeedom 4.4.9+, Debian 12.
- Interface utilisateur strictement basée sur les composants standards Jeedom (Bootstrap / jQuery) ; pas de framework frontend lourd en V1.
- Respect strict du standard Home Assistant MQTT device discovery.
- Architecture local-first, avec support de brokers distants hors chemin nominal.

### Cross-Cutting Concerns Identified

- **Cycle de Vie et Cohérence d'État (State Reconciliation):** Résoudre la gestion des dérives potentielles entre la base Jeedom, le cache du Daemon et l'état final HA, via des requêtes étalées, les "Last Will Testaments" MQTT et le "birth message" HA.
- **Heuristique de Traduction Sémantique (Mapping Engine):** Un composant hautement critique et centralisé qui devra extrapoler des entités propres (HA) depuis de multiples structures atomiques hétérogènes (Jeedom) sans produire de "faux-positifs".
- **UX du Débogage (Diagnostic & Observability):** Traçabilité de bout-en-bout nécessaire pour encapsuler facilement une complexité technique latente (Python/MQTT) sous la forme d'un diagnostic d'interface métier explicite, "actionnable" et non-intimidant côté PHP.
- **Maîtrise de charge et de volumétrie sur box à ressources limitées:** Mécanismes transverses (throttling / batching / smoothing) requis pour limiter toute vague de publications I/O subites de provoquer la saturation de la box Jeedom hôte.

## Starter Template Evaluation

### Primary Technology Domain

Plugin Jeedom hybride (PHP Backend/UI + Daemon asynchrone Python)

### Starter Options Considered

Dans l'écosystème Jeedom, il n'existe qu'un seul standard officiel et maintenu pour le développement de plugins : le **Jeedom Plugin Template** officiel fourni par l'équipe Jeedom sur GitHub (`jeedom/plugin-template`). L'utilisation de boilerplate alternatifs n'est pas recommandée car elle complique la validation sur le Market et s'éloigne des standards du core.

### Selected Starter: jeedom/plugin-template

**Rationale for Selection:**
C'est le standard de facto obligatoire pour garantir la compatibilité maximale avec Jeedom v4.4+, faciliter la publication sur le Market, et s'assurer que l'arborescence (core/desktop/plugin_info/resources) correspond aux attentes du moteur de plugins Jeedom.

Pour la partie Python (Daemon), le standard moderne et asynchrone est d'utiliser la bibliothèque `jeedomdaemon` (gérée par Mips2648) qui s'intègre naturellement dans l'arborescence `resources/` du template plugin.

**Initialization Command:**

```bash
# 1. Cloner le template officiel dans le dossier des plugins Jeedom
git clone https://github.com/jeedom/plugin-template.git plugins/jeedom2ha

# 2. Renommer les fichiers et classes selon la convention (template -> jeedom2ha)
# (Prévoir un script d'initialisation dédié pour renommer classes, fichiers et identifiants du template vers jeedom2ha)
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- PHP 8.x pour la logique d'interface, la gestion des requêtes AJAX, et les callbacks du daemon.
- Python 3.9+ encapsulé dans un environnement virtuel (venv) géré par Jeedom.

**Styling Solution:**
- HTML5 / CSS3 / Bootstrap natif de Jeedom.
- Utilisation stricte des classes et variables CSS du core pour la compatibilité thème clair/sombre.

**Build Tooling:**
- Pas de build step complexe (pas de Webpack/Vite pour le frontend). Gestion standard via le core Jeedom.

**Testing Framework:**
- Tests Python isolés : possibilité d'utiliser `pytest` en local (à configurer).
- Intégration / E2E : Docker compose (à configurer ultérieurement).

**Code Organization:**
- Pattern Modèle-Vue de Jeedom :
  - `core/class/` : Classes PHP (eqLogic, cmd).
  - `core/ajax/` : Endpoints AJAX.
  - `desktop/php/` & `desktop/js/` : Vues et interactions UI utilisateur.
  - `plugin_info/` : Configuration, dépendances (info.json, packages.json).
  - Un daemon Python sous `resources/` selon les conventions Jeedom.

**Development Experience:**
- Structure pré-approuvée facilitant la revue Market.
- Gestion native des processus daemon par le core (PID, logs, start/stop).

**MVP Guardrail:**
Le starter template fournit l’ossature, pas l’architecture métier ; le MVP reste volontairement limité et ne doit pas dériver vers un plugin Jeedom générique ou un framework de synchronisation complet.

## Core Architectural Decisions

### Priority Analysis

**Critical Decisions (Block Implementation):**
- **State Management:** Cache hybride RAM/Disque (Jeedom = source de vérité).
- **Transport Interne:** HTTP local + callbacks API Jeedom.
- **Core Persistence:** Natif Jeedom (JSON in `eqLogic`/`cmd` tables), aucune DB externe.

**Important Decisions (Shape Architecture):**
- **Daemon Lifecycle:** Géré via le framework officiel `jeedomdaemon`.
- **UI Framework:** Vanilla Jeedom (Bootstrap + jQuery) étendu par des variables CSS Core (thème jour/nuit).

**Deferred Decisions (Post-MVP):**
- **Stockage avancé (SQLite):** Évalué post-V1 si les calculs de deltas sur le volume du parc induisent des goulots d'étranglement (latence > 2s).

### Data Architecture

**State management du daemon : Cache hybride RAM + disque**
- Modèle hybride in-memory + disk cache (JSON / compression si nécessaire).
- Cache disque *technique* et *non autoritatif* (empreintes, dernier inventaire, versionnement du schéma) agissant comme accélérateur de bootstrap.
- Jeedom reste la seule source de vérité.
- Revalidation systématique au boot par comparaison avec Jeedom.
- Écriture atomique du cache. Schéma de cache versionné.
- Mécanisme de fallback radical : En cas de doute ou incohérence : purge cache + rescan complet.
- Ne *pas* utiliser SQLite ou autre base de données custom en V1.

### API & Internal Communication Patterns

**Transport de contrôle (PHP ↔ Python) : HTTP Local + Callbacks API Jeedom**
- PHP → Daemon : Requêtes gérées via l'API HTTP locale exposée par le daemon asynchrone sur `127.0.0.1` (pas exposée sur le LAN).
- Daemon → PHP : Callbacks asynchrones transmis via l'API Jeedom sécurisée par la clé API du plugin (`jeeApi.php`).
- Aucune dépendance du transport interne au broker MQTT, garantissant le maintien d'un canal de diagnostic et de contrôle même si la liaison MQTT est rompue.

*Guardrails :* Surface HTTP minimale avec messages structurés/idempotents. Timeouts courts. Gestion explicite des erreurs et codes de retour.
*Rôle des Callbacks :* Réservés aux événements utiles (état daemon, état broker, résultats de rescan, diagnostic métier et événements asynchrones utiles).

### Infrastructure & Deployment

**Environnement cible & Exécution**
- Plugin installé via le Market Jeedom sur une base Debian 12 (Core v4.4.9+) minimale.
- Exécution du daemon Python sous environnement virtuel (`venv`) isolé géré par Jeedom. Installation et résolution de dépendances limitées à `apt` pour les lib système, dépendances Python applicatives limitées au strict nécessaire (`paho-mqtt`, `jeedomdaemon`).

**Stratégie de Tests Minimale V1 :**
- **Emplacement :** Les tests Python vivront dans `resources/daemon/tests/` et utiliseront `pytest`.
- **Tests Unitaires Obligatoires (Mockés) :**
  - Validation du Mapping Engine (les conversions génériques vers payload de base).
  - Validation du générateur de payloads MQTT Discovery.
  - Règles d'exclusion et niveaux de confiance.
- **Tests d'Intégration Obligatoires :**
  - Cycle de vie basique (Ajout / Renommage / Suppression d'un objet fictif dict→MQTT).
  - Traitement d'un rescan avec réconciliation d'état.
  - La communication HTTP/MQTT pure est principalement mockée en V1 pour isoler la logique métier.

**Sécurité et Contrat API Locale (HTTP 127.0.0.1) :**
- L'API exposée par le Daemon sur 127.0.0.1 est strictement réservée au core PHP de la machine locale.
- **Authentification :** L'API attend systématiquement une clé de sécurité locale courte (générée aléatoirement par PHP au démarrage et passée via la configuration CLI/env du daemon). Toute requête sans ce `local_secret` dans les headers ou le payload est refusée (401 Unauthorized).
- **Endpoints Autorisés V1 :**
  - `/action/sync` (déclenche un rescan/sync complet)
  - `/action/publish` (publier un eqLogic spécifique)
  - `/action/remove` (retirer du broker MQTT)
  - `/system/status` (liveness probe)
- **Gestion des erreurs :** Application stricte des codes HTTP normés (400 Bad Request pour payload invalide, 500 pour erreur interne Python). Les requêtes depuis le PHP doivent implémenter un timeout court (ex: 3s) et jusqu'à 2 retries espacés d'une seconde.

## Implementation Patterns & Consistency Rules

### 1. Naming Patterns & Stable Identifiers

**Règle directrice :**
- Toujours distinguer explicitement les identifiants d’origine Jeedom, les identifiants internes du daemon et les identifiants exposés à Home Assistant.
- Ne jamais utiliser un nom générique ambigu comme `deviceId` s’il peut désigner autre chose selon le contexte.

**Convention recommandée :**
- Jeedom eqLogic ID : `jeedom_eq_id`
- Jeedom cmd ID : `jeedom_cmd_id`
- Objet/zone Jeedom : `jeedom_object_id`
- Home Assistant `unique_id` : chaîne stable dérivée des IDs Jeedom
- Home Assistant `object_id` : dérivé lisible, non autoritatif
- Nom d’affichage : mutable, non utilisé comme identifiant technique

**Règles :**
- Les `unique_id` MQTT doivent toujours être stables, préfixés par le plugin et basés sur les IDs Jeedom, jamais sur les noms (ex: `jeedom2ha_eq_123`, `jeedom2ha_cmd_456`).
- Les noms affichés peuvent changer ; les identifiants techniques ne doivent pas changer à cause d’un renommage.
- Ne pas réutiliser `device_id` comme synonyme de `eqLogic_id` dans le code interne.
- Utiliser `snake_case` pour les noms internes Python, les DTO JSON internes, et les clés techniques du plugin.
- Si certaines clés de configuration UI Jeedom doivent rester en `camelCase` pour cohérence frontend existante, le faire uniquement à la frontière UI, pas dans le modèle interne.

### 2. Format Patterns & Internal API Contracts (PHP ↔ Daemon)

**Règle directrice :**
- Tous les échanges structurés entre PHP et daemon doivent suivre une enveloppe uniforme, versionnable et facilement déboguable.

**Envelope standard recommandée :**
```json
{
  "action": "string",
  "payload": {},
  "request_id": "string",
  "timestamp": "2026-03-12T12:34:56Z"
}
```

**Réponses / callbacks :**
```json
{
  "action": "string",
  "status": "ok|error",
  "payload": {},
  "request_id": "string",
  "timestamp": "2026-03-12T12:34:56Z",
  "error_code": "optional_string",
  "message": "optional_human_readable_message"
}
```

**Règles :**
- Utiliser ISO 8601 UTC pour tous les timestamps. Pas de timestamps locaux implicites.
- Pas de booléens 1/0 dans les payloads internes Python ↔ PHP : caster explicitement en `true/false`.
- Tous les payloads doivent être tolérants aux champs inconnus mais stricts sur les champs requis.
- Les commandes doivent être idempotentes quand c’est possible (ex : rescan demandé plusieurs fois).
- Les erreurs doivent toujours être explicites et structurées ; jamais de simple "fail" silencieux.

### 3. File, Module & Log Structure

**Règle directrice :**
- L’organisation du code doit refléter les responsabilités métier, pas seulement les types techniques.

**Organisation Python recommandée :**
- `mapping/` : logique de traduction Jeedom → HA (un mapper par grand domaine : `light.py`, `cover.py`). Noms de classes en PascalCase (`LightMapper`). Noms de fichiers en `snake_case`.
- `discovery/` : génération des payloads MQTT Discovery.
- `sync/` : états, commandes, réconciliation.
- `diagnostic/` : couverture, raisons de non-publication, export support.
- `transport/` : MQTT, API locale, callbacks Jeedom.
- `models/` : structures de données / DTO / dataclasses.

**Logging :**
- Utiliser des niveaux de logs standard (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
- Ajouter des catégories lisibles pour le filtrage : `[MQTT]`, `[MAPPING]`, `[DISCOVERY]`, `[SYNC]`, `[API]`, `[DIAG]`.
- Séparer strictement : logs techniques (détails techniques pour dev) vs diagnostic métier (explication métier actionnable pour l'utilisateur).

### 4. Process Patterns, Fallbacks & State Safety

**Règle directrice :**
- Ne jamais inventer un état ou une représentation qui pourrait induire l’utilisateur en erreur.
- En cas de doute, préférer "ne pas publier" ou "ne pas mettre à jour cet état" plutôt que publier une valeur fausse.

**Règles de fallback :**
- Pour une valeur Jeedom inattendue ou invalide :
  - ne pas crasher ; logger un `WARNING` ;
  - ne pas publier une valeur mensongère par défaut. Conserver le dernier état valide connu si possible, sinon publier `unknown` / `unavailable` selon le modèle HA. Ne rien publier si aucun comportement honnête n’existe.
- Ne jamais convertir arbitrairement `null` en `0` ou `false` si cela change le sens métier.
- Les valeurs par défaut "safe" ne sont autorisées que si elles sont sémantiquement neutres et n’introduisent aucune interprétation fausse.

**Débounce / throttling :**
- Débouncer / regrouper les rafales d’états issues de `event::changes`.
- Ne jamais dé-bouncer au point de perdre un dernier état pertinent.
- Les commandes utilisateur HA → Jeedom ne doivent pas être mangées par un debounce prévu pour les états.
- Séparer strictement les flux : flux commandes / flux états / flux réconciliation.

### 5. Mapping Consistency Rules

**Règle directrice :**
- Le mapping doit être centralisé, explicable et déterministe.

**Règles :**
- Le mapping commence toujours par les types génériques Jeedom. Le fallback type/sous-type est un second moteur centralisé, pas une heuristique dispersée.
- Chaque décision de mapping doit produire :
  1. une représentation cible ;
  2. un niveau de confiance (`sure`, `probable`, `ambiguous`, `ignore`) ;
  3. une raison explorable dans le diagnostic.
- Ne jamais implémenter des règles de mapping "magiques" cachées dans plusieurs modules.
- Toute exception plugin-spécifique doit être explicitement documentée et isolée.

### 6. Lifecycle Consistency Rules

**Règle directrice :**
- Toute transition de cycle de vie doit être prévisible, idempotente et explicable.

**Règles :**
- Ajout, renommage, suppression et remapping sont 4 cas distincts.
- Un renommage ne doit jamais casser le `unique_id`.
- Une suppression doit utiliser le mécanisme MQTT Discovery approprié et être techniquement propre.
- Un remapping fonctionnel (ex : switch → light) doit être traité comme une rupture explicite de représentation, et non un simple renommage.
- `event::changes` sert aux états incrémentaux ; les changements de topologie exigent toujours une réconciliation / rescan.

### 7. MVP Guardrails for Implementers

**Règle directrice :**
- Ne pas sur-implémenter le post-MVP.

**V1 autorisé :**
lights, switches / prises, covers / volets, capteurs numériques simples, capteurs binaires simples, diagnostic de couverture, exclusion minimale par équipement, rescan manuel, ajout / renommage / suppression basiques.

**V1 à ne pas implémenter :**
climate / thermostats riches, scénarios riches, détection intelligente des doublons, réconciliation sophistiquée, heuristiques opaques, migration complexe de type fonctionnel.

### 8. Safety Rule of Last Resort

Si une décision d’implémentation hésite entre "publier plus" ou "publier moins mais correctement", la règle par défaut est : **publier moins ; expliquer pourquoi ; permettre à l’utilisateur ou à une future version d’aller plus loin**.

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
jeedom2ha/
├── plugin_info/
│   ├── info.json
│   ├── install.php
│   ├── configuration.php
│   └── packages.json
├── core/
│   ├── class/
│   │   ├── jeedom2ha.class.php
│   │   └── jeedom2haCmd.class.php        # optionnel si nécessaire
│   ├── ajax/
│   │   └── jeedom2ha.ajax.php
│   └── php/
│       └── jeedom2ha.php                 # callback daemon → Jeedom
├── desktop/
│   ├── php/
│   │   └── jeedom2ha.php
│   ├── js/
│   │   └── jeedom2ha.js
│   ├── css/
│   │   └── jeedom2ha.css                 # seulement si besoin réel
│   └── modal/
│       └── health.php
├── resources/
│   ├── install_apt.sh
│   └── daemon/                           # Daemon asynchrone Python
│       ├── main.py
│       ├── config.py
│       ├── transport/
│       ├── discovery/
│       ├── sync/
│       ├── mapping/
│       ├── models/
│       ├── diagnostic/
│       ├── tests/                        # Tests unitaires et d'intégration via pytest
│       └── utils/
└── data/                                 # runtime, non versionné
    ├── cache/
    ├── fingerprints/
    └── state.json
```

### Architectural Boundaries

**1. PHP Core (`core/class/jeedom2ha.class.php`)**
- Le core PHP gère l'interface Jeedom, la configuration, les actions utilisateur, et l'orchestration du daemon.

**2. Local HTTP API (`transport/http_server.py`)**
- Canal de contrôle PHP → daemon. C'est le moyen pour le PHP de demander une commande au Python (ex: "Publie cet équipement", "Fais un rescan").

**3. Jeedom Callback API (`core/php/jeedom2ha.php`)**
- Le callback Jeedom est le mécanisme standard retenu pour les remontées asynchrones du daemon vers Jeedom (ex: réception d'un ordre HA On, notification de diagnostic, log utile).

**4. Mapping Engine (`mapping/engine.py`)**
- Centralise TOUTE la logique de traduction des "Generic Types" Jeedom vers les entités HA. Les autres composants, en particulier ceux situés dans `sync/`, ne doivent faire aucune supposition sémantique. Ils se contentent de router les états traduits par ce mapping central.nv`) isolé géré par Jeedom. Installation et résolution de dépendances limitées à `apt` pour les lib système, `pip` applicatif minimisé strict (`paho-mqtt`, `jeedomdaemon`).
