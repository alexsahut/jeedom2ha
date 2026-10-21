# Story 23.2 : Captures et vidéo de promotion rejouables

Status: ready-for-dev

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

- [ ] **Task 0 — Prérequis** : fichier `.env` des comptes `j2ha-captures` présent (D3, clawbox) ; démo VM 122 démarrée (Zone labo).
- [ ] **Task 1 — Démo embellie (D2)** : `populate_demo.py` (icônes, couleurs, parents « Rez-de-chaussée » / « Étage », accents), tests unitaires mis à jour, exécution sur la VM 122 par clawcode.
- [ ] **Task 2 — Parcours de captures** : scénarios Playwright déterministes (attente des rafraîchissements, thème clair, viewport 1280×720), réutilisant l'outillage du gate 20-0 quand c'est possible.
- [ ] **Task 3 — Vidéo** : enregistrement Playwright selon le storyboard vidéo.
- [ ] **Task 4 — Documentation** : remplacement des marqueurs, commande de régénération documentée (`docs/dev-demo-env.md`).
- [ ] **Task 5 — Validation** : ClaudeBox relit les médias (CC-48, concordance) ; Alexandre valide le rendu (`ready-for-UX-validation`).

## Notes

- Un retour au snapshot `demo` de la VM 122 efface les comptes `j2ha-captures` et le mot de passe admin changé par Alexandre le 2026-10-21 : refaire le snapshot `demo` après la Task 1 demande le go d'Alexandre (snapshots `vierge`/`demo` hors Zone labo).
- Le navigateur intégré de ClaudeBox demande une autorisation d'Alexandre à chaque action sur l'adresse de la démo : les captures ne passent donc pas par lui.
