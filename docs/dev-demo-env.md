# Environnement de démonstration rejouable (Story 23.1)

Jeu de démonstration **synthétique** (aucune donnée de la maison, CC-48) servant aux captures
et preuves Market. Cible : VM 122 (Debian 12, unité A66), jamais la box de production.

> **Statut** : livrables de code uniquement. **Aucune exécution sur VM tant que clawbox n'a pas
> reçu le GO d'Alex.** Le contrat JSON-RPC d'écriture ci-dessous est **non démontré terrain**.

## Responsabilités

| Acteur | Responsabilité |
| --- | --- |
| **clawbox** | VM 122, snapshots (`vierge`, `demo`), clé SSH de déploiement, Mosquitto local, RAM de la VM |
| **clawcode** | Déploiement du plugin (`scripts/deploy-to-box.sh`), HA Docker, exécution de `populate_demo.py` |
| **ClaudeBox** | Revue de la topologie/méthode snapshot, captures via Chrome |
| **Alex** | GO avant toute exécution VM ; comptes de démo et URL (hors dépôt) |

## Ordre des opérations (VM 122)

1. **Snapshot `vierge`** pris par clawbox (prérequis A66 ; ne rien créer avant sa confirmation).
2. **Plugin déployé** : `scripts/deploy-to-box.sh` avec `JEEDOM_BOX_HOST` / `JEEDOM_BOX_USER`
   de la VM 122 dans un `.env` hors dépôt (voir `docs/dev-deploy.md`). Le plugin Virtuel
   doit être installé et activé dans Jeedom.
3. **Home Assistant** : copier `scripts/demo/docker-compose.ha.yml` sur la VM, puis
   `HA_IMAGE_TAG=<version-épinglée> docker compose -f docker-compose.ha.yml up -d`
   (`HA_IMAGE_TAG` est obligatoire, jamais `stable`). Dans HA, ajouter l'intégration MQTT vers
   le Mosquitto local (`127.0.0.1:1883`) ; identifiants saisis dans l'UI uniquement.
   Si 2 Go de RAM ne suffisent pas : proposer 3 Go à clawbox/Alex avant d'agir.
4. **Populate** (voir ci-dessous) : d'abord `--dry-run`, puis exécution réelle, puis relance
   pour constater l'idempotence (tout en `exists`).
5. **Scan** : lancer le scan/sync jeedom2ha, vérifier Jeedom → MQTT → HA.
6. **Snapshot `demo`** par clawbox, puis captures par ClaudeBox.

## `scripts/demo/populate_demo.py`

Python 3 sans dépendance (stdlib). Fichier `.env` **hors dépôt** (refusé s'il est dans le dépôt),
jamais d'argument de ligne de commande pour un secret :

```
JEEDOM_API_URL=http://<hôte-de-la-vm>/core/api/jeeApi.php
JEEDOM_API_KEY=<clé API core de la box de démo>
JEEDOM_DEMO_TARGET=demo
```

```sh
python3 scripts/demo/populate_demo.py --dry-run                              # plan hors-ligne
python3 scripts/demo/populate_demo.py --env-file ~/.jeedom2ha-demo.env --dry-run   # lectures seules
python3 scripts/demo/populate_demo.py --env-file ~/.jeedom2ha-demo.env             # applique
```

- **Idempotent** : pièces/scénarios retrouvés par nom, équipements par (pièce, nom), commandes
  par (équipement, nom) ; les équipements créés portent un marqueur de propriété (`configuration.jeedom2ha_demo_key`), un équipement existant au nom du jeu mais sans marqueur est refusé, jamais réutilisé ; une dérive de type/sous-type/unité/type générique est réparée, jamais
  dupliquée.
- **Garde-fous** : `JEEDOM_DEMO_TARGET=demo` obligatoire ; abandon si la box contient des
  équipements hors jeu de démo (`--allow-non-empty` pour forcer) ; aucune URL, clé ni
  identifiant interne dans les sorties.
- **Sortie** : inventaire JSON anonymisé sur stdout (statuts `planned`, `would_create`,
  `exists`, `created`, `updated`, plus un résumé) ; erreurs sur stderr, code retour 1.

### Jeu de données

5 pièces (Salon, Cuisine, Chambre, Bureau, Garage), 16 Virtuel, 3 scénarios :
lumières on/off (`LIGHT_*`), lumières variables (`LIGHT_BRIGHTNESS`/`LIGHT_SLIDER`), volets
positionnables (`FLAP_*`), prises avec puissance (`ENERGY_*` + `POWER`, W), température/humidité,
ouvertures (`OPENING`, `OPENING_WINDOW`), présence (`PRESENCE`), compteur cumulatif kWh
(`CONSUMPTION`). Cas d'écran : « Equipement Libre Bureau » **sans type générique**
(« Ne sera pas publié — et pourquoi ») et « Lumiere Garage Exclue » (`jeedom2ha_excluded=1`,
« Exclu »).

## Contrat API (à valider sur VM 122)

Tout est isolé dans `JsonRpcContract` / `JeedomAdapter` (`populate_demo.py`).

| Élément | Statut |
| --- | --- |
| Transport `POST core/api/jeeApi.php`, JSON-RPC 2.0, `params.apikey` | Prouvé par le projet (`event::changes`, `cmd::execCmd`) |
| Clé requise : clé **core** (la clé plugin est refusée pour `cmd::execCmd`) | Prouvé sur la box testée ; supposé identique pour les écritures |
| Méthodes de lecture/écriture `jeeObject::all/save`, `eqLogic::all/save`, `cmd::byEqLogicId/save`, `scenario::all/save` | **Non démontrées** (documentation Jeedom 4.x, de mémoire) |
| Noms de champs (`eqType_name`, `object_id`, `eqLogic_id`, `generic_type`, `configuration.jeedom2ha_excluded`) | **Non démontrés** par appel réel |
| Création d'un scénario vierge (sans éléments) via `scenario::save` | **Incertain** : la méthode peut ne pas exister selon la version |
| Action Virtuel liée à son info via `configuration.infoName` + valeur `configuration.value` (1/0) | **Incertain** (selon la version : `value` = id de la commande info, valeur à poser à la main) |

Les tests unitaires utilisent un faux serveur qui implémente **ce contrat présumé** : ils
prouvent l'idempotence et le dry-run, pas la compatibilité avec Jeedom. Sur écart constaté à la
première exécution (après GO), corriger uniquement l'adaptateur ; si `scenario::save` est absent,
créer les 3 scénarios (vides) via l'UI avant relance — le script les reconnaît par nom.
