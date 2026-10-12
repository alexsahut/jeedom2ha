# Story 24-1 — preuve terrain (non-régression), 12/10/2026

> **Statut de ce document.** Rédigé par ClaudeBox le 12/10/2026 vers 15:40, à verser au dépôt avec la clôture de la story 24-1. Identifiants seulement : aucun nom d’équipement, de pièce, de scénario ni de personne (règle CC-48). Toutes les vérifications ont été faites en lecture seule (registres de HA, journaux du plugin et du démon, processus) ; seul le déploiement a écrit, et il a été fait par clawcode.

## Ce que la preuve couvre

24-1 ajoute au payload de topologie le signal `homekit_exposed` (avec sa provenance) et les `logical_id`, sans rien changer à ce qui est publié. Le signal n’est visible nulle part avant l’export de 24-2. Cette preuve est donc une **non-régression** : rien ne doit changer dans HA ni dans l’inventaire MQTT. La comparaison du signal au cache de Homebridge (123 accessoires, 5 scénarios) est reportée au premier export de 24-2, dont elle devient un critère de baseline (AC11 bis de 24-2).

## Relecture (R1 de ClaudeBox)

Relecture du code de Homebridge et du cœur Jeedom sur la box, en lecture seule. Trois écarts à la règle réelle, corrigés dans `867eec6` :
- B1 : un scénario **sans clé** `sendToHomebridge` n’est **pas** exposé (`homebridge.class.php:3119`). La R1 de #260 était incomplète sur ce point.
- B2 : lecture de la configuration brute, comme Homebridge : `isset` puis `intval`, exposé si différent de 0 ; pièce `getConfiguration("sendToHomebridge", 0) == 1`. `getConfiguration(clé, défaut)` confond clé absente et chaîne vide (`utils.class.php:252`).
- B3 : la liste `plugin::listPlugin(true, false, true, true)` est une liste d’identifiants lue en base (`plugin.class.php:208-221`), la même que celle de Homebridge : plus de repli par plugin.

PR #261 fusionnée en squash (`a64b924`, tête `867eec6`), CI verte, fil Codex résolu.

## Déploiement

| Élément | Valeur |
|---|---|
| SHA déployé | `45ab5d7` (`main`, contient #261 ; #254 et #252, documentaires, fusionnées juste après par l’autre chantier, ont annulé la CI de `a64b924`) |
| Garde-fou CI | CI de `45ab5d7` entièrement verte avant le lancement |
| Commande | `./scripts/deploy-to-box.sh --sha 45ab5d7… --restart-daemon`, worktree neuf en HEAD détaché, sans option de nettoyage ; aucun autre déploiement ni gate en cours (vérifié) |
| Durée | 13:33:05Z → 13:33:25Z, code de sortie 0 ; tag `deploy-45ab5d7…-20261012T133323Z` |
| Sync | `total_eq=292 eligible=96 published=263` (identique à la preuve de 22-2) |

## Inventaire MQTT (script de déploiement)

348 → 348 entités ; aucun topic ajouté, aucun retiré.

## Registres de HA

| Contrôle | Avant (15:22) | Après (15:36) |
|---|---|---|
| Entités jeedom2ha | 348 | 348 |
| Entités créées ou modifiées depuis le déploiement | — | **0** |
| Appareils jeedom2ha | 177 | 177 |
| Appareils modifiés depuis le déploiement | — | **0** |

## Démon et topologie

- Démon redémarré à 15:33:12 (heure de Paris), MQTT connecté à 15:33:14, abonnements aux topics de commande en place.
- Topologie acceptée : « Scan complet : 23 objets, 292 eqLogics, 120 scénarios », synchronisation de démarrage réussie, 227 écouteurs d’état réenregistrés.
- 0 ligne `ERROR` ; 6 `WARNING` préexistants (un override sans type, deux équipements à commandes en double), les mêmes qu’à la preuve de 22-2.
- Aucun autre démon touché (processus Python des autres plugins inchangés).

## Garde-fous de la story

- `logicalId` jamais journalisé : 0 occurrence de `logical_id`, `logicalId` ou `homekit` dans le journal du démon, celui du plugin et `http.error`.
- Aucune écriture dans la configuration de Jeedom ou de Homebridge (recherche dans le diff citée dans la PR, test `test_php_additions_are_read_only`).
- Ni `transport/http_server.py` ni `desktop/` modifiés.

## Verdict

Non-régression prouvée : 24-1 peut passer `done`. Reste porté par 24-2 : comparaison de `homekit_exposed` au cache de Homebridge sur le premier export.
