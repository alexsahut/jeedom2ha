---
project_name: 'jeedom2ha'
user_name: 'Alexandre'
date: '2026-03-15'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'quality_rules', 'workflow_rules', 'anti_patterns']
status: 'complete'
rule_count: 22
optimized_for_llm: true
---

# Project Context for AI Agents

_Rappels projet compacts pour agents BMAD. Garder ce fichier court, opérationnel et prioritaire sur les habitudes génériques._

---

## Technology Stack & Versions

- PHP 8.x pour le plugin Jeedom (`eqLogic` / `cmd`, AJAX, callback daemon)
- Python 3.9+ async pour le daemon via `jeedomdaemon`
- jQuery + Bootstrap natifs Jeedom, aucun framework frontend externe
- MQTT device discovery + JSON-RPC Jeedom (`/core/api/jeeApi.php`)
- Cible minimale : Jeedom 4.4.9+, Debian 12+, Home Assistant avec MQTT

## Critical Implementation Rules

### Language-Specific Rules

- PHP : conserver les classes plugin/commande sur `eqLogic` / `cmd`, utiliser `log::add(...)`, ne jamais exposer une clé API côté JS.
- Python : conserver un daemon `BaseDaemon`, écoute locale `127.0.0.1`, séparation claire transport HTTP local / JSON-RPC Jeedom / MQTT.

### Framework-Specific Rules

- Mapping Jeedom -> HA : `generic_type` d'abord ; fallback `type` / `subType` uniquement si la représentation reste honnête.
- Les identifiants techniques doivent venir des IDs numériques Jeedom ; les noms sont affichables mais jamais autoritatifs.
- Heuristique par défaut : `1 eqLogic = 1 device HA` ; toute exception doit être explicite.
- Principe de moindre nuisance : en cas d'ambiguïté, d'état douteux ou de mapping faible, ne pas publier ou publier `unknown` / `unavailable`, jamais inventer un état.

### Testing Rules

- Les tests locaux valident le câblage, les payloads et les invariants internes ; ils ne prouvent pas les permissions effectives Jeedom.
- Les tests locaux ne suffisent pas pour valider un changement d'authentification Jeedom.
- Toute nouvelle méthode `jeeApi.php` reste `non démontrée` tant qu'elle n'a pas été validée sur box réelle.
- Si la box réelle contredit code, tests ou documentation, arrêter la story et mettre à jour le contrat d'architecture avant de continuer.

### Code Quality & Style Rules

- Le cache runtime sous `data/` reste technique et non autoritatif ; Jeedom reste la source de vérité pour topologie et état relisible.
- Les erreurs d'auth, sync et transport doivent être explicites, structurées et loggées ; pas de fallback silencieux.
- En cas d'incohérence cache/auth, préférer purge + rescan à une récupération implicite.

### Development Workflow Rules

- Avant toute story touchant `auth`, `state sync`, `command sync` ou `JSON-RPC`, relire `_bmad-output/planning-artifacts/architecture.md` et exécuter le mini preflight de `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.
- Une story touchant ces flux n'est pas "prête" tant que le preflight terrain n'a pas été exécuté ou explicitement replanifié.

### Critical Don't-Miss Rules

- Les trois secrets sont distincts et non interchangeables : `plugin API key`, `core API key`, `local secret`.
- `local secret` protège uniquement l'API HTTP locale du daemon (`X-Local-Secret` sur `/system/status` et `/action/sync`) ; ce n'est jamais une clé JSON-RPC Jeedom.
- Le contrat d'authentification Jeedom est défini par flux et par méthode, jamais par analogie.
- Box réelle = source de vérité pour les permissions effectives et les formats réellement acceptés.
- Aucune hypothèse sur une clé API Jeedom sans validation terrain.
- Contrat terrain actuellement prouvé : `event::changes` utilise la `core API key` ; `cmd::execCmd` utilise aussi la `core API key` sur la box réelle testée ; toute autre conclusion reste non démontrée.
- Mini preflight terrain obligatoire : relire les trois secrets sur la box réelle, vérifier `/system/status` et `/action/sync` avec `X-Local-Secret`, vérifier `event::changes` avec la `core API key`, vérifier `cmd::execCmd` avec clé plugin puis clé core si le flux commande est touché, puis contrôler les logs daemon après une commande HA -> Jeedom.

---

## Usage Guidelines

**Pour les agents IA :**

- Lire ce fichier avant d'implémenter du code.
- En cas de doute, choisir l'option la plus restrictive et documenter l'incertitude.
- Si un nouveau contrat terrain apparaît, mettre à jour d'abord `architecture.md`, puis ce fichier.

**Pour les humains :**

- Garder ce fichier plus court que `architecture.md`.
- Y mettre uniquement les règles projet qu'un agent risque réellement d'oublier.
- Réviser dès qu'un contrat auth/sync/JSON-RPC change sur box réelle.

Last Updated: 2026-03-15
