# Délégation à Claude Code cloud

Ce document décrit comment un agent de codage local (ex. OpenClaw sur la VM) délègue des tâches à des sessions Claude Code exécutées dans le cloud (budget de crédits limité).
Il complète `docs/git-strategy.md` (qui reste l'autorité Git) et `CLAUDE.md` (lu automatiquement par les sessions cloud).

## Prérequis (une seule fois)
1. Installer la CLI sur la VM (`npm i -g @anthropic-ai/claude-code` ou `claude install`) et la garder à jour : `claude --version`, `claude doctor`. Une CLI ancienne (testé : 2.1.137) refuse le lancement ; la version 2.1.291 fonctionne.
2. S'authentifier avec le **compte claude.ai** (`claude` puis `/login`), pas avec une clé API : les crédits des sessions cloud sont liés au compte.
3. L'app GitHub Claude doit être installée sur `alexsahut/jeedom2ha`.
4. Configurer l'environnement cloud sur claude.ai/code (accès réseau, script de setup installant `pip install -e ".[test]"`).

## Bloc d'instructions pour l'agent local

```markdown
## Délégation à Claude Code cloud (jeedom2ha)

Tu peux déléguer des tâches à des sessions Claude Code exécutées dans le cloud.
Elles consomment un budget limité (crédits) : utilise-les avec discernement.

### Quand déléguer
- Tâches autonomes et bien bornées : story/feature isolée, bugfix reproductible,
  écriture de tests, refactoring localisé, revue de code, documentation.
- Tâches longues ou parallélisables (plusieurs stories indépendantes).

### Quand NE PAS déléguer (fais-le toi-même)
- Modifications triviales (< 10 lignes), renommages, ajustements de config.
- Tâches nécessitant la VM, la box Jeedom, Home Assistant ou des secrets locaux
  (le cloud n'y a pas accès) : tests terrain, `scripts/deploy-to-box.sh`.
- Tâches floues : clarifie d'abord, puis délègue.
- Jamais plus de 3 sessions en parallèle sans accord de l'utilisateur.

### Lancer une session
Depuis le clone du dépôt, sur une branche **propre et poussée** sur GitHub (la session part du dernier commit connu de GitHub : les modifications locales non commitées et les commits non poussés ne sont pas vus) :

    claude --cloud "<PROMPT>"

(`--remote` fonctionne encore comme alias déprécié de `--cloud`.)
La commande affiche « Created cloud session », l'URL `https://claude.ai/code/session_...` et la commande `claude --teleport <id>`. Note l'ID/URL dans `docs/operations/delegations.md`.
Le lancement affiche un suivi en direct : exécute-le avec un timeout et récupère l'ID dans la sortie. Pour envoyer un complément à une session existante : `claude -p --cloud <session-id> "message"`.
Ne lance jamais `claude` en `sudo`.

Si le lancement est refusé, relève le message exact avant de conclure à une « procédure obsolète » : `Unable to get organization UUID` (connexion par clé API : `claude auth login`, pas de `ANTHROPIC_API_KEY`), fournisseur tiers configuré (`CLAUDE_CODE_USE_*`), dépôt sans remote GitHub, CLI trop ancienne.

### Format obligatoire du prompt
1. **Contexte** : une phrase + renvoi vers les fichiers utiles (story, spec) plutôt que de les recopier.
2. **Objectif** : un résultat précis et vérifiable.
3. **Périmètre** : fichiers/dossiers autorisés ; ce qu'il ne faut PAS toucher.
4. **Critères d'acceptation** : tests à faire passer, comportements attendus.
5. **Livrable** : « Branche nommée `story/<sujet>` ou `fix/<sujet>`, PR vers `main`,
   titre Conventional Commits, résumé des changements et des tests lancés. »
6. **Limites** : « Si tu es bloqué ou si la demande est ambiguë, arrête-toi et
   explique ce qui manque dans la PR plutôt que de deviner. Aucun changement hors périmètre. »

### Suivi
- Vérifie la PR et la CI toutes les 10-15 min (pas de polling plus rapproché).
- CI verte et critères remplis : récupère explicitement la branche de la PR (`git fetch origin <branche-pr> && git checkout <branche-pr>`, ou `gh pr checkout <n°>`) ; un simple `git pull` ne la récupère pas. Relis le diff, teste en local si besoin,
  puis signale à l'utilisateur que la PR est prête. Ne merge pas sans son accord.
- CI rouge ou PR incomplète : au plus UNE session de correction, avec les logs
  d'erreur dans le prompt. Au deuxième échec, reprends la main ou préviens l'utilisateur.
- Mets à jour `docs/operations/delegations.md` à chaque changement de statut.

### Garde-fous
- Jamais de secrets (tokens, mots de passe, IP privées) dans un prompt.
- Une session = une tâche. Pas de prompts fourre-tout.
- Si une session dérive ou boucle, interromps-la et préviens l'utilisateur.
- Signale toute délégation qui semble coûteuse avant de la lancer.
```

## Nom de branche et CI de gouvernance
Les sessions cloud créent par défaut des branches `claude/...`. Le préfixe `claude/` est autorisé dans `.github/workflows/pr-governance.yml` pour les PR de développement vers `main` (décision du mainteneur), au même titre que `story/`, `fix/`, `docs/`, `chore/`, `refactor/`, `ci/`, `test/`, `hotfix/`.
Les autres règles de routage restent inchangées (cible `main`, titre en Conventional Commits).

## Suivi des délégations
Voir `docs/operations/delegations.md`.
