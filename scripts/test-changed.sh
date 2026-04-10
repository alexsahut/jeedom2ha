#!/bin/bash
# Detect and run changed tests
set -euo pipefail

BASE_BRANCH=${1:-main}

echo "🔍 Détection des tests modifiés par rapport à $BASE_BRANCH..."

# Récupérer les fichiers de test modifiés
CHANGED_TESTS=$(git diff --name-only origin/$BASE_BRANCH...HEAD | grep "^tests/.*\.py$" || echo "")

if [ -z "$CHANGED_TESTS" ]; then
    echo "✅ Aucun test modifié détecté."
    exit 0
fi

echo "🚀 Exécution des tests modifiés :"
echo "$CHANGED_TESTS"
echo ""

# Exécution avec couverture sur les tests modifiés uniquement
python3 -m pytest --cov=resources/daemon --cov-report=term-missing $CHANGED_TESTS
