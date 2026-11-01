# Story 23.5 : Choix et cohérence de la licence

Status: done

> Décision écrite d'Alexandre reçue le 2026-10-12 à 19:21 : AGPL-3.0-or-later. Alignement soumis à relecture.

## Story

En tant que responsable du plugin, je veux choisir une licence compatible avec la diffusion et le Market, afin que le dépôt et les versions publiées ne se contredisent plus.

## Critères d'acceptation proposés

1. Une fiche compare AGPL-3.0 et alternatives pertinentes: obligations, Market payant, versions déjà publiées.
2. Elle constate `LICENSE` GPL-2.0 contre AGPL dans `plugin_info/info.json` et README, sans avis juridique définitif.
3. Après décision explicite seulement, LICENSE, info, README, documentation et métadonnées sont alignés avec un test de cohérence.
4. Si consultation juridique ou action historique est requise, la story s'arrête avec action attribuée à Alexandre.

## Tâches proposées

- [x] **Prérequis :** décision d'Alexandre reçue le 2026-10-12 à 19:21 : AGPL-3.0-or-later.
- [x] Inventorier licences, tags/releases et conditions Market avec sources datées.
- [x] Rédiger fiche d'arbitrage et demander décision Alexandre.
- [x] Après décision, appliquer l'alignement minimal : LICENSE, en-têtes PHP et JS, README et changelog beta.

## Décision Alexandre — 2026-10-12 19:21

Le plugin est publié sous **AGPL-3.0-or-later**. `LICENSE` contient le texte intégral
d'AGPL-3.0 et les en-têtes des 12 fichiers du gabarit (11 PHP + `desktop/js/jeedom2ha.js`) portent l'identifiant SPDX
`AGPL-3.0-or-later`.

Le Market Jeedom attend et a déjà validé la chaîne `AGPL` : `plugin_info/info.json` la
conserve, avec cette décision consignée pour lever toute ambiguïté avec la licence complète.

### Change Log

- 2026-11-01 — Story clôturée : alignement AGPL-3.0-or-later fusionné par PR #273.
