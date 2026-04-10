# Tests — jeedom2ha Daemon

## Vue d'ensemble

Ce répertoire contient les tests Python du daemon `jeedom2ha`, structurés selon l'architecture validée.

```
tests/
├── conftest.py              # Fixtures partagées (factories)
├── unit/
│   └── test_mapping_engine.py    # Tests unitaires du mapping engine (mockés)
└── integration/
    └── test_lifecycle.py         # Tests du cycle de vie (ajout/renommage/suppression/rescan)
```

## Stack de test

| Composant | Outil |
|---|---|
| Framework | **pytest** |
| Async | `pytest-asyncio` (`asyncio_mode = auto`) |
| Couverture | `pytest-cov` |
| Config | `pyproject.toml` → `[tool.pytest.ini_options]` |

## Lancer les tests

### Pré-requis

```bash
# Créer et activer un venv (recommandé)
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances daemon + test
pip install -e ".[test]"
# Ou si pas encore éditable :
pip install paho-mqtt jeedomdaemon pytest pytest-asyncio pytest-cov
```

### Commandes

```bash
# Tous les tests
pytest

# Tests unitaires uniquement
pytest tests/unit/

# Tests d'intégration uniquement
pytest tests/integration/

# Avec couverture
pytest --cov=resources/daemon --cov-report=term-missing

# Verbose
pytest -v
```

## Architecture de test

### Tests unitaires (`tests/unit/`)
- Communication HTTP/MQTT **entièrement mockée**
- Couvrent : mapping engine, génération des payloads MQTT Discovery, règles d'exclusion, niveaux de confiance
- Rapides, sans dépendance externe

### Tests d'intégration (`tests/integration/`)
- Cycle de vie basique (ajout / renommage / suppression via `dict → MQTT`)
- Rescan avec réconciliation d'état
- Transport (HTTP/MQTT pur) mocké, logique métier réelle

## Conventions

- Structure **Given / When / Then** dans tous les tests
- Identifiants stables : `jeedom2ha_eq_{id}`, jamais basés sur les noms
- Valeurs par défaut **sûres uniquement** — ne jamais publier une valeur mensongère
- Chaque test est indépendant et idempotent

## Variables d'environnement

Copier `.env.example` en `.env` et renseigner les valeurs pour les tests d'intégration :

```bash
cp .env.example .env
```

## Prochaines étapes

1. Implémenter `resources/daemon/mapping/engine.py`
2. Remplacer les assertions scaffold dans les tests par les vrais appels aux modules
3. Exécuter le workflow CI (`bmad-tea-testarch-ci`) pour configurer le pipeline
