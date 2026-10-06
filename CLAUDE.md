# CLAUDE.md — jeedom2ha

Plugin Jeedom (PHP + JS) avec daemon Python asyncio qui publie les équipements Jeedom vers Home Assistant via MQTT discovery.

## Sources de vérité (à lire avant de coder)
- `_bmad-output/project-context.md` — règles d'implémentation PHP/Python/JS, anti-patterns (**lecture obligatoire**).
- `docs/git-strategy.md` — gouvernance Git (fait autorité).
- `docs/agent-start-checklist.md` — checklist de démarrage des agents.
- `docs/ci.md` — pipeline CI et contrôles de gouvernance.
- `_bmad-output/implementation-artifacts/` — stories et specs ; `_bmad-output/planning-artifacts/` — PRD, architecture, epics.

## Structure
- `core/`, `desktop/`, `plugin_info/` — plugin Jeedom (PHP/JS).
- `resources/daemon/` — daemon Python (`discovery`, `mapping`, `models`, `sync`, `transport`, `cache`).
- `tests/` — `unit/`, `integration/`, `e2e/`, tests PHP `test_php_*.php`.

## Commandes
- Dépendances : `pip install -e ".[test]"` (voir `scripts/setup-test-env.sh`)
- Tests : `make test` / `make test-unit` / `make test-integration`
- Reproduire la CI en local : `scripts/ci-local.sh`
- Lint Python : `flake8`

## Règles Git
- Les PR de développement ciblent **`main`** uniquement ; jamais de push direct sur `main`, `beta`, `stable`.
- Titre de PR et commits en **Conventional Commits** (`feat|fix|docs|chore|refactor|test|ci|perf|build|revert(scope): ...`). La CI ne contrôle que le **titre de la PR**, pas les messages de commit : respecte la convention sur les commits sans compter sur la CI.
- Une branche / une PR = un seul sujet.
- Préfixes de branche acceptés par la CI : `story/`, `fix/`, `docs/`, `chore/`, `refactor/`, `ci/`, `test/`, `hotfix/`, `claude/` (sessions cloud déléguées).

## Sessions Claude Code cloud (déléguées)
Une session cloud n'a **pas** de worktree local ni accès à la box Jeedom réelle :
- Travaille sur la branche qui t'est assignée (ou celle demandée dans le prompt) ; ignore `scripts/start-story-worktree.sh` et `scripts/git-preflight.sh`.
- N'utilise **jamais** `scripts/deploy-to-box.sh` ni aucun accès SSH/box/Home Assistant : les tests terrain sont faits par l'humain.
- Avant de pousser : lance les tests concernés (`make test`) et `flake8`. Ne pousse pas de code rouge.
- Respecte strictement le périmètre du prompt ; si la demande est ambiguë ou bloquée, arrête-toi et explique-le dans la PR.
- Ne mets jamais de secrets, tokens ou IP privées dans le code, les commits ou la PR.
- Détails : `docs/delegation-claude-cloud.md`.
