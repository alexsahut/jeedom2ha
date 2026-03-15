## Type de changement

- [ ] Feature
- [ ] Fix
- [ ] Documentation
- [ ] Release promotion
- [ ] Autre changement de gouvernance

## Story ou fix ciblé

Référence story, fix ou objectif unique de cette PR :

## Branche source / branche cible

- Branche source :
- Branche cible :

Rappels obligatoires :

- une PR de développement doit cibler `main`
- une PR de promotion peut cibler `beta` depuis `main`
- une PR de promotion peut cibler `stable` depuis `beta`
- aucune PR de développement ne doit cibler `beta` ou `stable`

## Description

Décris le problème traité, le résultat attendu et le périmètre réel de cette PR.

## Changelog suggéré

Entrée courte proposée pour le changelog :

## Références

Issues, stories, documents ou références externes :

## Checklist de validation

- [ ] Cette PR porte un seul objectif explicite
- [ ] La branche source est une branche courte dédiée à ce changement
- [ ] La branche cible respecte la gouvernance définie dans `docs/git-strategy.md`
- [ ] Aucun changement de développement n'est envoyé directement vers `beta` ou `stable`
- [ ] Les tests et vérifications applicables ont été exécutés
- [ ] La documentation a été mise à jour si nécessaire
- [ ] Les changements hors repo éventuels sont signalés dans la description
