# Documentation CI/CD - jeedom2ha

## Aperçu
La pipeline CI est configurée via GitHub Actions pour assurer la qualité du code et la stabilité du plugin.
La gouvernance Git de référence est définie dans `docs/git-strategy.md`.

## Pipeline GitHub Actions
Les fichiers de configuration se trouvent dans :

- `.github/workflows/test.yml` pour les checks d'intégration et de promotion
- `.github/workflows/pr-governance.yml` pour les contrôles de cible de PR, de promotion et de métadonnées
- `.github/workflows/work.yml` pour le workflow Jeedom aligné sur les branches de release `beta` et `stable`

### Étapes de la Pipeline
1. **Lint** : Vérification de la syntaxe et du style via `flake8`.
2. **Test** : Exécution de la suite `pytest` complète définie par `pyproject.toml`.
   - Génération d'un rapport de couverture (`pytest-cov`).
   - Téléchargement des résultats en cas d'échec.
3. **Burn-In** : Pour les Pull Requests, exécution de 10 itérations des tests pour détecter l'instabilité (flakiness).
4. **Report** : Résumé de l'exécution dans le Step Summary de GitHub.

## Contrôles de gouvernance

- **PR Routing Policy** : vérifie que les PR de développement ciblent `main`, que les promotions vers `beta` viennent de `main`, et que les promotions vers `stable` viennent de `beta`.
- **PR Metadata Policy** : vérifie qu'une PR de développement vers `main` utilise un titre compatible Conventional Commits.
- **Cohérence minimale des branches source** : les PR vers `main` refusent les branches protégées comme source et valident un format simple pour les branches nommées avec préfixe.
- **Précondition locale hors CI** : la CI ne remplace pas le préflight Git local obligatoire défini dans `docs/git-strategy.md`.
- **Attendu d'entrée** : une PR de développement valide provient d'une branche dédiée portée par un worktree dédié, créée depuis un clone principal local propre.

## Scripts Utilitaires
Des scripts sont disponibles dans le dossier `scripts/` pour faciliter le développement :

- `scripts/test-changed.sh [brance_base]` : Exécute uniquement les tests modifiés par rapport à la branche de base (défaut: `main`).
- `scripts/ci-local.sh` : Simule l'exécution de la CI localement avec les rapports de couverture.

## Secrets Requis
- `CODECOV_TOKEN` (Optionnel) : Pour l'envoi des rapports de couverture à Codecov.

## Comment déclencher la CI
- Les branches de travail ouvrent leurs pull requests uniquement vers `main`.
- Les promotions de release passent par `main -> beta -> stable`.
- La CI se lance automatiquement sur chaque `push` et `pull_request` vers `main`, `beta` et `stable`.
- Les événements sur `beta` et `stable` correspondent aux promotions de release, pas à des branches de développement parallèles.
- Une exécution programmée (schedule) tourne chaque dimanche à 2h00 UTC pour un burn-in complet.

## Réglages GitHub à faire hors repo

- Activer les protections de branches sur `main`, `beta` et `stable`.
- Déclarer comme required checks au minimum :
  - `PR Routing Policy`
  - `PR Metadata Policy`
  - `Lint (Python 3.9)`
  - `Test Report`
- Autoriser le squash merge sur `main`.
- Réserver les merges vers `beta` et `stable` aux promotions contrôlées.
