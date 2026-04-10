#!/bin/bash
# Mock CI environment locally
set -euo pipefail

# simulation de l'environnement CI localement...

export CI=true

# Installation des dépendances via les extras de test
pip install -e ".[test]"

# Exécution des tests avec couverture (identique à la CI)
python3 -m pytest --cov=resources/daemon --cov-report=term-missing tests/
