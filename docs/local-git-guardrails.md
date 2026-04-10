# Garde-fous Git locaux

## Objectif

Ces outils versionnés rendent le flux local attendu simple à suivre :

- le clone principal local reste un miroir propre de `origin/main`
- chaque story, fix ou changement documentaire part d'une branche dédiée
- chaque branche de travail vit dans un worktree dédié
- un préflight Git bloque tout démarrage dans un contexte incohérent

## Activation des hooks versionnés

Activez les hooks versionnés une fois dans le dépôt :

```bash
git config core.hooksPath .githooks
```

## Démarrer une story proprement

Depuis le clone principal propre, sur `main` :

```bash
scripts/start-story-worktree.sh codex/story/mon-sujet
```

Le script :

- récupère `origin`
- vérifie que `main` local est propre et aligné sur `origin/main`
- crée la branche demandée depuis `main`
- crée un worktree dédié
- affiche le chemin du worktree créé

## Vérifier le contexte Git avant de lancer un agent

Depuis le worktree dédié :

```bash
scripts/git-preflight.sh --expect-branch codex/story/mon-sujet
```

Le préflight échoue si :

- la branche courante est `main`, `beta` ou `stable`
- le working tree est sale
- la branche courante ne correspond pas à la branche attendue

En cas d'échec, il faut s'arrêter et réaligner le contexte Git avant de continuer.

## Hooks fournis

- `.githooks/pre-commit` bloque les commits sur `main`, `beta` et `stable`
- `.githooks/pre-push` bloque les push directs vers `main`, `beta` et `stable`
