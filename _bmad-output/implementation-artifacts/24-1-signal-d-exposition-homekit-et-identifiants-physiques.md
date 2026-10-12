# Story 24.1 : Signal d'exposition HomeKit et identifiants physiques

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire (aucun accès box, Home Assistant ni secret). Relecture de ClaudeBox obligatoire, Task 0 faite par ClaudeBox, avant tout `ready-for-dev`. Contexte et décisions : `sprint-change-proposal-2026-10-12-parite-homekit.md` (Q5). Pointeurs `fichier:ligne` pris sur `main` à `b1acad7`. Aucun nom réel d'équipement, de pièce, de scénario ou de personne (CC-48) : identifiants seulement.

## Story

En tant que mainteneur de la parité entre Apple Maison et Assist,
je veux que le démon sache quels équipements Jeedom sont exposés à HomeKit et connaisse les identifiants physiques (`logicalId`) des équipements et des commandes,
afin que les stories suivantes décident, exportent et alignent sans jamais modifier la configuration Homebridge, les types génériques Jeedom ni l'exposition à Assist.

**Parcours : PHP + démon, lecture seule. Aucun changement de comportement, aucun écran.**

## Dépendances et décisions

- Dépend de la **Task 0 de ClaudeBox** (où Homebridge stocke l'exposition). Ne dépend d'aucune autre story.
- Peut démarrer avant le `done` de 22-2 (ne touche ni `http_server.py` ni `desktop/`).
- Q5 de la proposition (contenu de l'export) ne change rien ici : les champs sont portés tels quels, sans nom.

## Faits relevés dans le code (lecture seule, `main` `b1acad7`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | Aucune lecture de `sendToHomebridge`, de `logicalId` ni d'un attribut « HomeKit » dans le plugin (recherche exhaustive hors tests ; seule mention : le docstring de `mapping/button.py:45`). | `core/`, `desktop/`, `plugin_info/`, `resources/daemon/` |
| F2 | Le PHP lit les commandes (id, nom, type générique, type, sous-type, valeur, unité, visibilité, historisation) puis construit l'équipement (id, nom, pièce, activation, visibilité, plugin, type générique, exclusion, statut). | `core/class/jeedom2ha.class.php:759-769`, `:786-796` |
| F3 | Le démon normalise ce payload avec des `.get()` tolérants ; les dataclasses portent des valeurs par défaut, donc un champ optionnel ajouté ne casse aucun payload existant. | `resources/daemon/models/topology.py:74-100`, `:124-190` |
| F4 | `_to_bool(None, default)` renvoie `default` : il ne convient **pas** à un champ à trois états (vrai / faux / inconnu). | `models/topology.py:11-23` |
| F5 | Les scénarios sont lus à part (id, nom, actif) et n'ont aucun attribut d'exposition. | `class.php:661-680`, `models/topology.py:103-108` |
| F6 | Priorité d'exclusion : équipement > plugin > pièce ; `exclusion_source` est déjà transmis. | `class.php:775-784` |

## Critères d'acceptation proposés

- **AC1.** `getFullTopology()` ajoute à chaque équipement `logical_id` (chaîne ou `null`), `homekit_exposed` (`true`, `false` ou `null`) et `homekit_exposed_source` (chaîne ou `null`), et à chaque commande `logical_id`. Lecture seule : `getLogicalId()` et `getConfiguration()` ; aucun `setConfiguration`, `save()` ni écriture sur un équipement, une commande ou un scénario.
- **AC2.** Une valeur absente, vide ou illisible donne `null`, **jamais `false` par défaut**. `homekit_exposed_source` dit d'où vient la valeur (forme proposée : `eqlogic_configuration:<clé>`, `absent`, `unreadable`) ; la clé exacte est fixée par la Task 0.
- **AC3.** Le démon porte ces champs en optionnels additifs (`None` par défaut) sur `JeedomEqLogic` et `JeedomCmd`. `from_jeedom_payload` normalise `0`/`1`/`"0"`/`"1"`/`true`/`false` sans transformer `None` en `False`. Un payload ancien, sans ces champs, produit exactement le même snapshot qu'avant.
- **AC4.** Aucun changement d'éligibilité, de mapping, de décision, de publication, de diagnostic, de cache ni de contrat 4D : golden et contrat 4D **identiques octet pour octet** ; `PRODUCT_SCOPE` inchangé ; `exportDiagnostic` (allowlist) inchangé.
- **AC5.** Les `logicalId` ne sont écrits dans aucun journal de niveau `info` ou supérieur, ni dans le diagnostic existant ni dans son export (ils peuvent contenir des adresses d'appareil).
- **AC6.** Scénarios : aucun champ d'exposition tant que la Task 0 n'a pas trouvé une source ; si elle en trouve une, un AC dédié est écrit avant `ready-for-dev`.
- **AC7.** Tests : extraction PHP de la topologie (cas exposé, non exposé, valeur absente, valeur illisible) ; normalisation Python (trois états, payload ancien) ; recherche dans le diff prouvant l'absence d'écriture sur la configuration Jeedom.
- **AC8.** Aucun nom réel dans le code de test, les fixtures, la story, la PR (CC-48).

## Tâches proposées

- [ ] **Task 0 — Établir (ClaudeBox, lecture seule sur la box)** : sur quatre identifiants (un équipement exposé à HomeKit, un non exposé, un équipement qui produit plusieurs accessoires, un scénario exposé), relever **les clés de configuration liées à Homebridge** (clés et formats seulement, pas de noms) : confirmer `sendToHomebridge`, son niveau (équipement ou commande), ses valeurs (`0`/`1`, vide) ; relever si `logicalId` est vide pour les équipements virtuels et non vide pour les plugins natifs. **Si la clé n'est pas lisible par `getConfiguration()` ou diffère de `sendToHomebridge`, s'arrêter et revenir vers Alexandre avant de coder.**
- [ ] **Task 1 — PHP** : lecture des trois champs d'équipement et du `logical_id` de commande dans `getFullTopology()`, tri-état strict.
- [ ] **Task 2 — Démon** : champs additifs, normalisation à trois états, sans toucher à l'éligibilité.
- [ ] **Task 3 — Tests** : voir AC7 ; golden et contrat 4D inchangés.
- [ ] **Task 4 — Documentation de développement** : ajouter le contrat des champs à la documentation interne (pas à `docs/fr_FR`, aucune visibilité utilisateur).

## Garde-fous

- **Le plugin n'écrit jamais** la configuration Homebridge, les types génériques Jeedom ni l'exposition à Assist (exigence 5).
- Aucun changement de ce qui est publié ; si le golden bouge, la story est refusée.
- Aucun accès SSH, box ou Home Assistant depuis la session cloud ; `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

La clé réelle, son niveau et son format (D1) ; la présence d'un `logicalId` selon les plugins ; l'exposition des scénarios.
