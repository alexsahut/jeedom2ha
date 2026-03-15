# Stratégie Git, Commit et Release de jeedom2ha

## Objectif

Ce document définit la politique Git unique de `jeedom2ha`.
Il s'applique aux mainteneurs du dépôt, aux contributeurs humains, aux agents IA BMAD, Codex, Claude Code et Antigravity, ainsi qu'aux automatisations de contribution et de release.

`jeedom2ha` est un plugin Jeedom avec daemon Python et logique de publication vers Home Assistant.
Le projet a une contrainte forte de fiabilité, de traçabilité et de gouvernance de release.
La politique Git doit donc être compatible avec un cycle de publication Jeedom Market en canaux `beta` et `stable`.

Ce document fait autorité.
Toute documentation, CI, automatisation ou pratique contradictoire doit être réalignée sur cette politique.

## Modèle canonique de branches

Le modèle canonique du projet est :

`story branch -> main -> beta -> stable`

Les rôles des branches sont figés :

- `main` est la branche d'intégration canonique.
- `beta` est la branche de release candidate et de publication Jeedom Market beta.
- `stable` est la branche de release de production et de publication Jeedom Market stable.
- `develop` n'est pas canonique et ne doit plus apparaître dans la gouvernance cible du projet.

Les automatisations de contribution, y compris Dependabot, doivent cibler `main` par défaut.
Une exception ne doit exister que si elle est explicitement justifiée et documentée.

## Règles de création de branches

- Tout développement doit partir d'une branche courte créée depuis `main`.
- Une branche de travail doit porter un seul objectif livrable.
- Une branche de travail doit correspondre à une story, un fix ou un changement documentaire clairement identifié.
- Le nom de branche doit décrire explicitement l'objectif traité.
- Une branche de travail ne doit pas être créée depuis `beta`.
- Une branche de travail ne doit pas être créée depuis `stable`.
- `beta` ne doit avancer que depuis `main`.
- `stable` ne doit avancer que depuis `beta`.

## Règles de commit

- Tous les messages de commit doivent suivre Conventional Commits.
- Un commit doit représenter un changement logique cohérent.
- Un commit ne doit pas mélanger plusieurs objectifs sans lien direct.
- Le message de commit doit être lisible sans contexte implicite.
- Les commits intermédiaires sont autorisés uniquement sur une branche de travail.
- Un commit local ne constitue pas une publication.
- Tant qu'un changement n'est pas poussé sur la branche distante prévue, il n'est pas gouverné par le flux collaboratif du dépôt.

## Règles de push

- Un contributeur humain ou un agent IA doit pousser uniquement sa branche de travail.
- Un agent IA ne doit jamais pousser directement sur `main`.
- Un agent IA ne doit jamais pousser directement sur `beta`.
- Un agent IA ne doit jamais pousser directement sur `stable`.
- Un push direct sur une branche protégée ne doit pas être utilisé comme mode normal d'intégration.
- `beta` et `stable` ne doivent avancer que par un flux de promotion contrôlé.
- Un historique local en avance sur l'origine ne doit pas être confondu avec une intégration publiée.

## Règles de pull request

- Toute branche de travail doit ouvrir une pull request vers `main`.
- Une pull request doit avoir un seul objectif explicite.
- Une pull request doit identifier clairement la story ou le fix traité.
- Une pull request de développement ne doit jamais cibler `beta`.
- Une pull request de développement ne doit jamais cibler `stable`.
- La promotion de `main` vers `beta` doit passer par une pull request dédiée de promotion.
- La promotion de `beta` vers `stable` doit passer par une pull request dédiée de promotion.
- Aucune pull request ne doit cibler `develop`.

## Règles de merge

- Le merge canonique d'une branche de travail vers `main` est le squash merge.
- Le squash merge vers `main` est la forme normale d'intégration des stories et des fixes.
- La promotion de `main` vers `beta` doit se faire par merge commit de promotion.
- La promotion de `beta` vers `stable` doit se faire par merge commit de promotion.
- Une promotion de release ne doit pas utiliser squash merge.
- Une promotion de release ne doit pas utiliser cherry-pick comme méthode normale.
- Une story ne doit jamais être mergée directement vers `beta`.
- Une story ne doit jamais être mergée directement vers `stable`.
- `stable` ne doit jamais être promue directement depuis `main`.

## Politique de promotion `main -> beta -> stable`

- `beta` ne reçoit que des changements déjà intégrés sur `main`.
- `stable` ne reçoit que des changements déjà intégrés sur `beta`.
- `beta` est le canal de validation de release candidate du projet.
- `beta` est le canal de publication Jeedom Market beta.
- `stable` est le canal de publication de production du projet.
- `stable` est le canal de publication Jeedom Market stable.
- Une correction détectée en `beta` doit repartir sur une nouvelle branche de travail créée depuis `main`.
- Cette correction doit revenir dans `main` avant toute nouvelle promotion vers `beta`.
- Cette correction doit passer par `beta` avant toute promotion vers `stable`.
- `beta` et `stable` ne doivent pas recevoir de correctif direct hors de ce flux.

## Règles spécifiques pour les agents IA multi-IDE

- L'outil utilisé ne change pas la politique Git du projet.
- Un agent IA doit se comporter comme un contributeur sur branche courte.
- Un agent IA doit travailler sur une branche dédiée à l'objectif courant.
- Un agent IA ne doit pas réutiliser une branche active pour un autre objectif.
- Un agent IA ne doit pas prendre pour cible une branche contenant déjà un travail non validé sur un sujet distinct.
- Si plusieurs agents IA interviennent sur le même sujet, un humain doit désigner une branche de référence unique.
- Un agent IA peut créer des commits locaux de jalon sur sa branche de travail.
- Un agent IA ne doit jamais supposer qu'un commit local est visible sur GitHub.
- Un agent IA ne doit jamais auto-pousser vers `main`, `beta` ou `stable`.
- Si le contexte Git est incohérent avec l'objectif demandé, l'agent IA doit s'arrêter et demander un réalignement humain avant de poursuivre.

## Traitement du baseline historique pré-gouvernance

Le dépôt contient actuellement `27` commits locaux en avance sur `origin/main`.
Ces commits constituent le baseline d'intégration pré-gouvernance.

Les règles applicables sont :

- Ce baseline doit être traité comme un lot d'intégration historique.
- Ce baseline ne doit pas être réécrit rétroactivement pour "faire propre".
- Ce baseline ne doit pas être rebasé, re-squashé ou re-découpé a posteriori comme politique de normalisation.
- La normalisation doit conserver un repère explicite de ce baseline historique.
- Une fois ce baseline normalisé et publié sur `origin/main`, toute nouvelle évolution doit suivre strictement la présente politique.

## Ce qui est interdit

- Travailler directement sur `main` pour développer une story ou un fix.
- Travailler directement sur `beta` pour développer une story ou un fix.
- Travailler directement sur `stable` pour développer une story ou un fix.
- Utiliser `develop` comme branche cible, branche d'intégration ou branche documentée.
- Merger une branche de travail directement dans `beta`.
- Merger une branche de travail directement dans `stable`.
- Promouvoir `stable` directement depuis `main`.
- Publier dans `beta` un changement qui n'est pas déjà passé par `main`.
- Publier dans `stable` un changement qui n'est pas déjà passé par `beta`.
- Corriger `beta` ou `stable` par un correctif direct hors du flux canonique.
- Utiliser le push direct comme mécanisme normal de release.
- Laisser Dependabot cibler une autre branche que `main` sans justification explicite.
- Réécrire rétroactivement le baseline historique pré-gouvernance de `27` commits.

## Résumé opérationnel

1. Toute évolution part d'une branche courte créée depuis `main`.
2. Une branche de travail porte un seul objectif livrable.
3. Tous les commits suivent Conventional Commits.
4. `main` est la seule branche d'intégration canonique.
5. Les branches de travail sont mergées vers `main` par squash merge.
6. `beta` ne reçoit que des changements déjà passés par `main`.
7. `stable` ne reçoit que des changements déjà passés par `beta`.
8. Toute correction détectée en `beta` repart sur une nouvelle branche depuis `main`.
9. Aucun agent IA ne pousse directement sur `main`, `beta` ou `stable`.
10. Le baseline historique de `27` commits sur `main` est conservé comme baseline pré-gouvernance non réécrit.
