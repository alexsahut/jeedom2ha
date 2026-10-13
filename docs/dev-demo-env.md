# Environnement de démonstration rejouable (Story 23.1)

Jeu de démonstration **synthétique** (aucune donnée de la maison, CC-48) servant aux captures
et preuves Market. Cible : VM 122 (Debian 12, unité A66), jamais la box de production.

> **Statut** : procédure exécutée et validée le 2026-10-13 sur l'environnement de démonstration synthétique. Les secrets, URL et comptes restent hors dépôt (CC-48).

## Responsabilités

| Acteur | Responsabilité |
| --- | --- |
| **clawbox** | VM 122, snapshots (`vierge`, `demo`), clé SSH de déploiement, Mosquitto local, RAM de la VM |
| **clawcode** | Installation/mise à jour du plugin selon la procédure ci-dessous, exécution de `populate_demo.py` |
| **ClaudeBox** | Revue de la topologie/méthode snapshot, captures via Chrome |
| **Alex** | GO avant toute exécution VM ; comptes de démo et URL (hors dépôt) |

## Ordre des opérations (VM 122)

1. **Snapshot `vierge`** pris par clawbox (prérequis A66 ; ne rien créer avant sa confirmation).
2. **Première installation du plugin** : construire le paquet Market avec
   `scripts/build-market-package.sh`, le copier dans `/var/www/html/plugins/jeedom2ha` puis
   appliquer le propriétaire `www-data`. La preuve du 13/10 a utilisé le paquet construit à
   `e94b01d` (77 fichiers, manifeste respecté, version 1.2.0). `scripts/deploy-to-box.sh`
   est réservé aux **mises à jour** d'un plugin déjà installé. Utiliser la branche `master` du
   plugin Virtuel : il n'existe pas de branche `stable`.
3. **Home Assistant** : Docker CE depuis le dépôt officiel est requis pour l'image Home
   Assistant 2026.9.4 : Docker.io 20.10 ne lit pas ses couches zstd. La procédure prouvée
   utilise `docker run` avec une image explicitement épinglée. Après onboarding, ajouter
   l'intégration MQTT vers le Mosquitto local (`127.0.0.1:1883`) sans identifiant, puis ignorer
   les découvertes LAN non pertinentes.
   Si 2 Go de RAM ne suffisent pas : proposer 3 Go à clawbox/Alex avant d'agir.
4. **Populate** (voir ci-dessous) : exécuter depuis `<racine>/scripts/demo/`, dont la racine ne
   contient pas le `.env`, puis d'abord `--dry-run`, exécution réelle, puis relance
   pour constater l'idempotence (tout en `exists`).
5. **Scan** : lancer le scan/sync jeedom2ha, vérifier Jeedom → MQTT → HA.
6. **Snapshot `demo`** par clawbox, puis captures par ClaudeBox. Le snapshot `demo` est pris en
   laissant la VM allumée.

## `scripts/demo/populate_demo.py`

Python 3 sans dépendance (stdlib). Fichier `.env` **hors dépôt** (refusé s'il est dans le dépôt),
jamais d'argument de ligne de commande pour un secret :

```
JEEDOM_API_URL=http://<hôte-de-la-vm>/core/api/jeeApi.php
JEEDOM_API_KEY=<clé API core de la box de démo>
JEEDOM_DEMO_TARGET=demo
```

```sh
python3 <racine>/scripts/demo/populate_demo.py --dry-run                              # plan hors-ligne
python3 <racine>/scripts/demo/populate_demo.py --env-file <chemin-hors-depot> --dry-run # lectures seules
python3 <racine>/scripts/demo/populate_demo.py --env-file <chemin-hors-depot>           # applique
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
| Méthodes de lecture/écriture `jeeObject::all/save`, `eqLogic::all/save`, `cmd::byEqLogicId`, `scenario::all/save` | **Vérifiées dans les sources** `jeeApi.php`/`virtual.class.php` `master`, 12/10 — à prouver sur VM 122 (Jeedom 4.6.1) |
| Réponse vide | Chaîne `ok` produite par `jsonrpc.class.php` `makeSuccess()` ; normalisée en liste vide par l'adaptateur pour les lectures. |
| Création Virtuel et commandes | `eqLogic::save` avec `eqType_name=virtual` et la liste `cmd` complète. Les commandes existantes sont relues par nom et renvoyées avec leur `id`, sinon Jeedom les retire ; `Rafraichir` est conservée par `dontRemoveCmd`. **Vérifié dans les sources**, à prouver sur VM 122. |
| Noms de champs (`eqType_name`, `object_id`, `eqLogic_id`, `generic_type`, `configuration.jeedom2ha_excluded`) | **Vérifiés dans les sources** — à prouver sur VM 122. |
| Création d'un scénario vierge (sans éléments) via `scenario::save` | **Vérifiée dans les sources**, à prouver sur VM 122. |
| Action Virtuel liée à son info | `configuration.infoName` est le nom d'une info du même équipement ; `configuration.value` est l'expression/valeur à lui appliquer ; `virtualCmd::preSave()` renseigne `infoId`. **Vérifié dans les sources**, à prouver sur VM 122. |

Les tests unitaires utilisent un faux serveur qui implémente **ce contrat présumé** : ils
prouvent l'idempotence et le dry-run, pas la compatibilité avec Jeedom. Sur écart constaté à la
première exécution (après GO), corriger uniquement l'adaptateur ; si `scenario::save` est absent,
créer les 3 scénarios (vides) via l'UI avant relance — le script les reconnaît par nom.

> **Erratum v1.7** — lors d'une exécution sur VM, conserver la profondeur
> `<racine>/scripts/demo/` ; la racine calculée par le script ne doit pas contenir le fichier
> `.env` hors dépôt.
