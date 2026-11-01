# Story 23.2 : Captures et vidéo de promotion rejouables

Status: ready-for-UX-validation

> `ready-for-dev` accordé par ClaudeBox le 2026-10-21 après revue de la démo avec Alexandre (VM 122, plugin `68560b7`, Jeedom 4.6.1). Dépendances levées : 23.1 `done`, 22.2 `done` (superseded par l'epic 25, clos le 2026-10-21).

## Story

En tant que mainteneur, je veux générer les visuels depuis la démo synthétique, afin que docs, forum et bêta Market montrent le produit livré.

## Décisions d'Alexandre (2026-10-21 09:34)

- **D1 — Thème clair** pour toutes les captures et la vidéo.
- **D2 — Démo embellie avant capture** : chaque pièce porte une icône et une couleur Jeedom ; les pièces sont rangées sous deux objets parents « Rez-de-chaussée » et « Étage » ; les noms d'équipements, de commandes et de scénarios prennent leurs accents français.
- **D3 — Comptes dédiés créés par clawbox** (Zone labo, VM 122) : un compte Jeedom et un compte Home Assistant `j2ha-captures`. Leurs identifiants sont dans un fichier `.env` sur la VM openclaw, hors de tout dépôt (chemin et noms de clés communiqués par clawbox, jamais les valeurs). Le script les lit ; aucun identifiant n'est écrit dans le dépôt, les journaux ni les PR.

## Storyboard figé (ClaudeBox + Alexandre, 2026-10-21)

Fenêtre 1280×720, interface française, thème clair, démo synthétique 23.1 seulement (CC-48).

| # | Écran | Marqueur remplacé | Contenu attendu |
|---|---|---|---|
| 1 | Page principale (B) | `index.md` « page principale du plugin » | bandeau d'état (démon, MQTT, dernière synchro), jauge maison, cartes de pièce groupées par étage |
| 2 | Cartes de pièce | `index.md` « cartes de pièce » | gros plan : une pièce complète, « Bureau » (1 bloqué), « Garage » (1 exclu) |
| 3 | Vue de travail (C) | `index.md` « vue de travail » | arbre filtré sur « Salon », équipement sélectionné |
| 4 | Détail d'un équipement | `index.md` « détail d'un équipement » | équipement publié, état et réglage Automatique/Toujours/Jamais |
| 5 | Tableau des commandes | `index.md` « tableau des commandes » | commandes de l'équipement 4 et leur projection |
| 6 | Compteurs du détail de pièce | `compteurs.md` « compteurs du détail de pièce » | compteurs d'une pièce avec un bloqué |
| 7 | Ligne de compteurs dépliée | `compteurs.md` « ligne de compteurs d'un équipement déplié » | équipement bloqué « Bureau » : pourquoi et quoi faire |
| 8 | Configuration | `index.md` « page de configuration » | MQTT et plugins exclus à cocher, sans aucune valeur de broker sensible visible |

En plus, hors marqueurs : une capture Home Assistant (appareils jeedom2ha rangés par pièce) pour le site et la fiche Market.

**Vidéo (≤ 2 min, 1280×720, webm ou mp4)** : installation (page Plugins, dépendances, démon OK), « Relire Jeedom », ouverture d'une pièce et d'un équipement, puis Home Assistant (mêmes équipements, mêmes pièces), pilotage d'une lumière depuis HA avec retour d'état dans Jeedom.

## Critères d'acceptation

1. Un parcours Playwright sur la démo 23.1 prend une capture pour chaque ligne 1 à 8 du storyboard, plus la capture Home Assistant.
2. Il produit une vidéo ≤ 2 min suivant le storyboard vidéo.
3. Médias, métadonnées (version du plugin, date, viewport) et commande de régénération sont versionnés ; aucun secret ni donnée maison n'est rendu accessible (identifiants lus dans le `.env` hors dépôt de D3).
4. Les marqueurs `CAPTURE-A-PRENDRE` ne sont remplacés qu'après validation que média, version et documentation concordent.
5. CC-48 : seuls les contenus synthétiques de 23.1 sont visibles (aucune IP privée, aucun nom de la maison, aucune valeur de broker sensible).
6. Captures dans `docs/fr_FR/images/`, vidéo exploitable comme lien « vidéo » de la fiche Market (hébergement choisi par Alexandre plus tard ; la vidéo n'est pas forcément versionnée si trop lourde : documenter où elle est).
7. D2 : `scripts/demo/populate_demo.py` porte les icônes, couleurs, objets parents et accents ; il reste idempotent et rejouable sur une démo déjà peuplée (renommage des équipements existants par leur clé `jeedom2ha_demo_key`, pas de doublon).
8. Thème clair forcé par le script (D1), quel que soit le thème par défaut du compte.

## Tâches

- [x] **Task 0 — Prérequis** : fichier `.env` des comptes `j2ha-captures` présent (D3, clawbox) ; démo VM 122 démarrée (Zone labo).
- [x] **Task 1 — Démo embellie (D2)** : `populate_demo.py` (icônes, couleurs, parents « Rez-de-chaussée » / « Étage », accents), tests unitaires mis à jour, exécution sur la VM 122 par clawcode.
  - [x] 1.1 `populate_demo.py` : parents, icônes, couleurs, accents, renommage idempotent par `jeedom2ha_demo_key` (code livré)
  - [x] 1.2 Tests unitaires : enrichissements D2, migration d'une démo 23.1, dérive de pièce, idempotence (34 tests verts)
  - [x] 1.3 Exécution sur la VM 122 par clawcode : second passage entièrement `exists` (2026-10-31)
- [x] **Task 2 — Parcours de captures** : scénarios Playwright déterministes (attente des rafraîchissements, thème clair, viewport 1280×720), réutilisant l'outillage du gate 20-0 quand c'est possible.
  - [x] 2.1 `tests/e2e/captures/run-captures.mjs` + `lib/` : captures 1 à 8 + Home Assistant, thème clair prouvé (D1), contrôle CC-48, manifeste (réutilise `gate/lib/playwright.mjs`)
  - [x] 2.2 Tests Node de la logique pure (storyboard ↔ marqueurs, config, CC-48, thème, manifeste, plan hors-ligne)
  - [x] 2.3 Première exécution réelle et ajustement des sélecteurs (2026-10-31, #336 à #350)
- [x] **Task 3 — Vidéo** : enregistrement Playwright selon le storyboard vidéo.
  - [x] 3.1 Étapes vidéo du storyboard, durée contrôlée ≤ 2 min, fichier hors dépôt (code livré)
  - [x] 3.2 Enregistrement réel (109 s) et relecture ClaudeBox (2026-11-01)
- [ ] **Task 4 — Documentation** : remplacement des marqueurs, commande de régénération documentée (`docs/dev-demo-env.md`).
  - [x] 4.1 Section « Captures et vidéo de promotion » de `docs/dev-demo-env.md` : commande, `.env`, garanties, métadonnées, protection des secrets
  - [x] 4.2 Remplacement des marqueurs `CAPTURE-A-PRENDRE` (2026-11-01, à la demande d'Alexandre, pour valider le rendu en ligne) : images r9 dans `docs/fr_FR/images/`
- [ ] **Task 5 — Validation** : ClaudeBox relit les médias (CC-48, concordance) ; Alexandre valide le rendu (`ready-for-UX-validation`).
  - [x] 5.1 Relecture ClaudeBox (2026-11-01), voir « Exécution terrain du 2026-10-31 »
  - [ ] 5.2 Validation du rendu par Alexandre, puis Task 4.2 (marqueurs) et choix de l'hébergement de la vidéo

## Notes

- Un retour au snapshot `demo` de la VM 122 efface les comptes `j2ha-captures` et le mot de passe admin changé par Alexandre le 2026-10-21 : refaire le snapshot `demo` après la Task 1 demande le go d'Alexandre (snapshots `vierge`/`demo` hors Zone labo).
- Le navigateur intégré de ClaudeBox demande une autorisation d'Alexandre à chaque action sur l'adresse de la démo : les captures ne passent donc pas par lui.

## Dev Agent Record

### Agent Model Used

Session cloud déléguée (Claude Code), branche `story/23-2-captures-video`.

### Implementation Plan

- Task 1 : `populate_demo.py` porte `PARENTS`/`ROOMS` (icône `<i class="fas fa-…"></i>`, `tagColor`, `tagTextColor`, parent), noms accentués, `ascii_fold()` pour retrouver les objets 23.1. Équipements retrouvés par la seule clé `jeedom2ha_demo_key` (renommage et déplacement sur place), commandes par nom puis ancien nom ASCII (la dérive `infoName` des actions est réparée), scénarios idem. Pièces en deux passes : parents puis pièces (`father_id`).
- Tasks 2-3 : outillage séparé du gate 20-0 (l'intercepteur en lecture seule bloquerait « Relire Jeedom » et le pilotage HA), mais `loadPlaywright` est réutilisé. Logique pure isolée dans `lib/` pour être testable sans navigateur.
- Task 4 : documentation de régénération dans `docs/dev-demo-env.md`.

### Completion Notes

- Tests exécutés : `python3 -m pytest tests/unit` → 784 passed, 5 skipped (dont 34 dans `test_populate_demo.py`, 11 nouveaux D2) ; `flake8` propre ; `node --test tests/unit/*.node.test.js` : 8 nouveaux tests verts (`test_story_23_2_captures.node.test.js`), 3 échecs préexistants et sans lien (25.4/AC31, 25.4/AC32, 25.8/AC6), identiques sans les changements de cette story.
- **Non exécuté (cloud sans VM, ni Jeedom, ni HA, ni `.env`)** : exécution de `populate_demo.py` sur la VM 122, parcours Playwright, captures, vidéo. Les contrats `father_id`/`display` de `jeeObject::save` et tous les sélecteurs du parcours sont donc NON DÉMONTRÉS. Aucun média n'a été produit ni inventé ; aucun marqueur `CAPTURE-A-PRENDRE` n'est remplacé.
- Points à trancher/valider : (a) noms de clés du `.env` de D3 (JEEDOM_URL, HA_URL, HA_USER, HA_PASSWORD proposés, à confirmer par clawbox) ; (b) « équipement 4 » du storyboard (ligne 5) lu comme le 4e équipement de l'arbre filtré sur « Salon » = « Climat Salon » ; (c) ligne 2 : capture de la carte « Bureau » plus complément « Garage » (`cartes-de-piece-garage.png`).
- Statut laissé à `in-progress` : AC1, AC2, AC4, AC5, AC6 et AC8 (preuve réelle) dépendent de l'exécution terrain ; le passage à `review` n'est pas honnête avant.

### File List

- `scripts/demo/populate_demo.py` (modifié)
- `tests/unit/test_populate_demo.py` (modifié)
- `tests/e2e/captures/run-captures.mjs` (nouveau)
- `tests/e2e/captures/lib/storyboard.mjs` (nouveau)
- `tests/e2e/captures/lib/config.mjs` (nouveau)
- `tests/e2e/captures/lib/safety.mjs` (nouveau)
- `tests/unit/test_story_23_2_captures.node.test.js` (nouveau)
- `docs/dev-demo-env.md` (modifié)
- `_bmad-output/implementation-artifacts/23-2-captures-et-video-de-promotion-rejouables.md` (modifié)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié)
- `docs/operations/delegations.md` (modifié)

### Change Log

- 2026-10-21 — dev-story cloud : démo embellie D2 (code + tests), outillage de captures et vidéo, documentation de régénération ; terrain et marqueurs reportés.

## Exécution terrain du 2026-10-31

Exécutée par clawcode sur la VM 122 (mandat de nuit NUIT-20261031), relue par ClaudeBox.

- **Médias retenus** : passage r9, plugin `2a247c5`, version 1.2.0, viewport 1280×720, fr-FR, thème clair.
  - Ils comprennent 10 PNG, `captures-manifest.json` et `jeedom2ha-presentation.webm` (109 s, 4,7 Mo, non versionnée).
  - Ils se trouvent sur la branche de relecture `chore/23-2-captures-relecture`, dossier `_bmad-output/review/23-2-captures-20261031-r9/` (sans PR). Ce dossier n'est pas destiné à `main`.
- **Correctifs nés du terrain**, tous sur `main`, chacun avec son test Node :
  - #336 : bouton de connexion du cœur 4.6.1 ;
  - #339 : pas de gel des animations sur la page de connexion, sinon la connexion n'aboutit pas ;
  - #340 et #342 : thème clair sans bascule automatique du soir (`theme_changeAccordingTime=0`) ;
  - #343 : connexion à HA, avec formulaire différé et validation par Entrée ;
  - #344, #345 et #346 : cadrage (page entière, grille des cartes, captures 3 et 4 distinctes) et capture HA filtrée sur Jeedom ;
  - #347 : `settle` borné à 3 s, car `networkidle` n'arrive jamais dans Jeedom ;
  - #348 et #350 : pilotage HA par `ha-entity-toggle` ;
  - #349 : pauses de la vidéo raccourcies.
- **Comptes `j2ha-captures`** : mots de passe changés par clawbox le 31/10 à 22:32, sur go d'Alexandre. HA a ensuite été redémarré : il gardait en mémoire l'ancien mot de passe.
- **Relecture ClaudeBox (CC-48)**
  - Aucune IP privée, aucun nom de la maison, aucune donnée de la maison, champs du broker masqués sur les captures. Compteurs à 0 pour « 192.168. », « famille-sahut » et « asahut » sur les 10 PNG, le manifeste et la vidéo.
  - La vidéo suit le storyboard : connexion, Plugins, dépendances et démon, « Relire Jeedom », pièce, équipement, appareils HA rangés par pièce, pilotage d'une lumière, retour dans Jeedom.
- **Réserves pour la validation d'Alexandre**
  1. Dans la vidéo, page Plugins, la valeur « Hôte MQTT » de la démo (`127.0.0.1`) reste visible : le masquage CC-48 n'y est pas appliqué. La valeur n'est pas sensible ici, mais le masquage est à corriger avant toute régénération ailleurs que sur la démo.
  2. Dans HA, l'appareil est « Connecté via 127.0.0.1 » : le pont MQTT porte le nom d'hôte du broker. Chez un utilisateur, ce serait son IP ou son nom d'hôte (point produit).
  3. Un badge rouge « 1 » (message Jeedom de la démo) apparaît dans la barre de navigation.
  4. `cartes-de-piece-garage.png` (2b) reste une carte seule de 130×180 px, hors documentation.

- **2026-11-01** : à la demande d'Alexandre (« les mettre en ligne directement pour voir »), les captures r9 sont versionnées dans `docs/fr_FR/images/` et les marqueurs remplacés. La vidéo (MP4 de 1 Mo, réencodé depuis le webm r9) est confiée au site jeedom2ha (NanoCorp). La validation du rendu se fait en ligne.
