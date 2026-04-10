# Agent Start Checklist

1. Ne jamais développer dans le clone principal.
2. Toujours partir d’un `main` propre et aligné sur `origin/main`.
3. Toujours créer une branche et un worktree dédiés via `scripts/start-story-worktree.sh`.
4. Toujours exécuter `scripts/git-preflight.sh` avant toute implémentation.
5. S’arrêter immédiatement si la branche est protégée ou si l’arbre Git est sale.
6. Ouvrir les PR de développement uniquement vers `main`.
7. Pour tout test terrain sur la box Jeedom réelle, utiliser **exclusivement** `scripts/deploy-to-box.sh` (DEV/TEST ONLY — ce n’est pas la procédure de release Market).
8. Ne jamais improviser de rsync, copie SSH manuelle ou procédure de déploiement ad hoc vers la box. Voir `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md` pour les modes disponibles et le template Task 0 Pre-flight terrain.
