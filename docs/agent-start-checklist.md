# Agent Start Checklist

1. Ne jamais développer dans le clone principal.
2. Toujours partir d’un `main` propre et aligné sur `origin/main`.
3. Toujours créer une branche et un worktree dédiés via `scripts/start-story-worktree.sh`.
4. Toujours exécuter `scripts/git-preflight.sh` avant toute implémentation.
5. S’arrêter immédiatement si la branche est protégée ou si l’arbre Git est sale.
6. Ouvrir les PR de développement uniquement vers `main`.
