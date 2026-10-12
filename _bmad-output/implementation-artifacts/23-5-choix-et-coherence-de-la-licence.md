# Story 23.5 : Choix et cohérence de la licence

Status: draft

> Brouillon. Aucune licence, métadonnée Market ou README ne change avant décision écrite d'Alexandre.

## Story

En tant que responsable du plugin, je veux choisir une licence compatible avec la diffusion et le Market, afin que le dépôt et les versions publiées ne se contredisent plus.

## Critères d'acceptation proposés

1. Une fiche compare AGPL-3.0 et alternatives pertinentes: obligations, Market payant, versions déjà publiées.
2. Elle constate `LICENSE` GPL-2.0 contre AGPL dans `plugin_info/info.json` et README, sans avis juridique définitif.
3. Après décision explicite seulement, LICENSE, info, README, documentation et métadonnées sont alignés avec un test de cohérence.
4. Si consultation juridique ou action historique est requise, la story s'arrête avec action attribuée à Alexandre.

## Tâches proposées

- [ ] **Prérequis :** la question de licence est soumise à Alexandre; commencer uniquement par la fiche d'options, sans modifier le dépôt.
- [ ] Inventorier licences, tags/releases et conditions Market avec sources datées.
- [ ] Rédiger fiche d'arbitrage et demander décision Alexandre.
- [ ] Après décision, appliquer alignement minimal et contrôle automatisé.
