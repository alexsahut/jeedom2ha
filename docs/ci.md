# Documentation CI/CD - jeedom2ha

## Aperçu
La pipeline CI est configurée via GitHub Actions pour assurer la qualité du code et la stabilité du plugin.

## Pipeline GitHub Actions
Le fichier de configuration se trouve dans `.github/workflows/test.yml`.

### Étapes de la Pipeline
1. **Lint** : Vérification de la syntaxe et du style via `flake8`.
2. **Test** : Exécution des tests unitaires et d'intégration via `pytest`.
   - Génération d'un rapport de couverture (`pytest-cov`).
   - Téléchargement des résultats en cas d'échec.
3. **Burn-In** : Pour les Pull Requests, exécution de 10 itérations des tests pour détecter l'instabilité (flakiness).
4. **Report** : Résumé de l'exécution dans le Step Summary de GitHub.

## Scripts Utilitaires
Des scripts sont disponibles dans le dossier `scripts/` pour faciliter le développement :

- `scripts/test-changed.sh [brance_base]` : Exécute uniquement les tests modifiés par rapport à la branche de base (défaut: `main`).
- `scripts/ci-local.sh` : Simule l'exécution de la CI localement avec les rapports de couverture.

## Secrets Requis
- `CODECOV_TOKEN` (Optionnel) : Pour l'envoi des rapports de couverture à Codecov.

## Comment déclencher la CI
- La CI se lance automatiquement sur chaque `push` et `pull_request` vers les branches `main` et `develop`.
- Une exécution programmée (schedule) tourne chaque dimanche à 2h00 UTC pour un burn-in complet.
