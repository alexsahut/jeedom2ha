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

- **Idempotent** : pièces/scénarios retrouvés par nom, équipements par clé `jeedom2ha_demo_key`, commandes
  par (équipement, nom) ; les équipements créés portent un marqueur de propriété (`configuration.jeedom2ha_demo_key`), un équipement existant au nom du jeu mais sans marqueur est refusé, jamais réutilisé ; une dérive de type/sous-type/unité/type générique est réparée, jamais
  dupliquée.
- **Renommage sans doublon (23.2)** : les équipements sont retrouvés par leur seule clé `jeedom2ha_demo_key`
  (donc renommés, déplacés de pièce ou réparés sur place), les commandes par leur nom ou, à défaut, par leur ancien
  nom sans accent (`ascii_fold`), les scénarios de même. Les identifiants, donc les `unique_id` MQTT/Home Assistant,
  ne changent pas. Une démo 23.1 déjà peuplée est migrée par un simple second passage : pièces mises à jour
  (parent, icône, couleur), parents créés, renommages en `updated`, `--dry-run` en `would_update`/`would_create`.
  Les champs `father_id` et `display` de `jeeObject::save` sont **vérifiés dans les sources, non démontrés** sur
  la VM 122 : sur écart, corriger uniquement `_room_payload`.
- **Garde-fous** : `JEEDOM_DEMO_TARGET=demo` obligatoire ; abandon si la box contient des
  équipements hors jeu de démo (`--allow-non-empty` pour forcer) ; aucune URL, clé ni
  identifiant interne dans les sorties.
- **Sortie** : inventaire JSON anonymisé sur stdout (statuts `planned`, `would_create`,
  `exists`, `created`, `updated`, plus un résumé) ; erreurs sur stderr, code retour 1.

### Jeu de données

2 objets parents (« Rez-de-chaussée » : Salon, Cuisine, Garage ; « Étage » : Chambre, Bureau), 5 pièces
portant chacune une icône et une couleur Jeedom (`display.icon`, `display.tagColor`, `display.tagTextColor`),
16 Virtuel, 3 scénarios, tous nommés en français accentué (Story 23.2, décision D2) :
lumières on/off (`LIGHT_*`), lumières variables (`LIGHT_BRIGHTNESS`/`LIGHT_SLIDER`), volets
positionnables (`FLAP_*`), prises avec puissance (`ENERGY_*` + `POWER`, W), température/humidité,
ouvertures (`OPENING`, `OPENING_WINDOW`), présence (`PRESENCE`), compteur cumulatif kWh
(`CONSUMPTION`). Cas d'écran : « Équipement Libre Bureau » **sans type générique**
(« Ne sera pas publié — et pourquoi ») et « Lumière Garage Exclue » (`jeedom2ha_excluded=1`,
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
| Champ Jeedom `unite` (pas `unit`) | `cmd.class.php` déclare `protected $unite` (`getUnite()`/`setUnite()`) ; l'ancienne clé `unit` était silencieusement ignorée par `utils::a2o`, cause du fil P2 de la PR #270 (2e passage non idempotent). Sans lien avec `models/topology.py` : la traduction côté plugin (`jeedom2ha.class.php`) expose déjà `unite` sous la clé `unit` pour le snapshot démon, qui reste correct. |
| Création d'un scénario vierge (sans éléments) via `scenario::save` | **Vérifiée dans les sources**, à prouver sur VM 122. |
| Action Virtuel liée à son info | `configuration.infoName` est le nom d'une info du même équipement ; `configuration.value` est l'expression/valeur à lui appliquer ; `virtualCmd::preSave()` renseigne `infoId`. **Vérifié dans les sources**, à prouver sur VM 122. |

Les tests unitaires utilisent un faux serveur qui implémente **ce contrat présumé** : ils
prouvent l'idempotence et le dry-run, pas la compatibilité avec Jeedom. Sur écart constaté à la
première exécution (après GO), corriger uniquement l'adaptateur ; si `scenario::save` est absent,
créer les 3 scénarios (vides) via l'UI avant relance — le script les reconnaît par nom.

> **Erratum v1.7** — lors d'une exécution sur VM, conserver la profondeur
> `<racine>/scripts/demo/` ; la racine calculée par le script ne doit pas contenir le fichier
> `.env` hors dépôt.

## Captures et vidéo de promotion (Story 23.2)

Outillage dans `tests/e2e/captures/`, **à exécuter par un humain** (ClaudeBox/clawcode) sur un poste ayant accès à
la VM de démo : le cloud n'a ni la box, ni Home Assistant, ni le `.env`. Le parcours réutilise la résolution de
Playwright du gate 20-0 (`tests/e2e/gate/lib/playwright.mjs`, variable `JEEDOM2HA_GATE_TOOLS`) ; il n'utilise pas
l'intercepteur en lecture seule du gate, car « Relire Jeedom » et le pilotage d'une lumière depuis Home Assistant
sont des écritures voulues, réservées aux comptes dédiés `j2ha-captures` (D3) sur la démo synthétique.

Prérequis : démo VM 122 démarrée et peuplée (`populate_demo.py` rejoué avec la version D2, puis scan jeedom2ha),
comptes `j2ha-captures` Jeedom et Home Assistant créés par clawbox.

Fichier `.env` **hors dépôt** (refusé s'il est dans le dépôt) ; noms de clés à confirmer avec clawbox :

```
JEEDOM_URL=<url de la démo Jeedom>
JEEDOM_USER=<compte j2ha-captures>
JEEDOM_PASSWORD=<…>
HA_URL=<url de la démo Home Assistant>
HA_USER=<compte j2ha-captures>
HA_PASSWORD=<…>
JEEDOM_DEMO_TARGET=demo
```

Commande de régénération (depuis la racine du dépôt) :

```sh
node tests/e2e/captures/run-captures.mjs --plan                      # plan hors-ligne, sans navigateur
node tests/e2e/captures/run-captures.mjs --env-file <chemin-hors-depot> \
     --out docs/fr_FR/images --video-out <dossier-hors-depot>      # captures + vidéo
node tests/e2e/captures/run-captures.mjs --env-file <chemin-hors-depot> --only shots   # captures seules
```

`--only shots|video` limite le parcours ; `--skip-ha` retire la capture 9 et les étapes vidéo Home Assistant (dont le retour d'état), et rend les clés `HA_*` facultatives. Aucun identifiant n'est passé en argument.

### Ce que garantit le parcours

- Fenêtre 1280×720, `fr-FR`, fuseau Europe/Paris, animations coupées, attente des rafraîchissements par sélecteur.
- **Thème clair forcé** (D1) quel que soit le thème du compte : `colorScheme: light`, sélection du thème clair dans le profil
  Jeedom et réglage clair côté navigateur pour Home Assistant (**non démontrés**, à ajuster au premier passage), puis contrôle
  du fond effectif avant chaque capture et à chaque écran de la vidéo ; un fond sombre ou illisible interrompt le parcours.
- **CC-48** : dès la création de chaque page (captures **et** vidéo, donc avant le premier rendu enregistré), les champs du
  broker (hôte, port, utilisateur, mot de passe, indications) et la note « broker » de la barre d'état sont masqués ; avant
  chaque capture, le texte visible est refusé s'il contient une adresse IP, un nom d'hôte
  local, une URL, un jeton long ou une valeur du `.env` ; les erreurs ne citent jamais de valeur.
- **Vidéo** ≤ 2 min (échec au-delà), étapes : page Plugins, dépendances/démon, « Relire Jeedom », pièce,
  équipement, Home Assistant (mêmes équipements et pièces), pilotage d'une lumière, retour d'état dans Jeedom.

### Captures produites (`docs/fr_FR/images/`)

| # | Fichier | Marqueur à remplacer après validation |
|---|---|---|
| 1 | `page-principale.png` | `index.md` « page principale du plugin » |
| 2 | `cartes-de-piece.png` (+ `cartes-de-piece-garage.png`, complément) | `index.md` « cartes de pièce » |
| 3 | `vue-de-travail.png` | `index.md` « vue de travail » |
| 4 | `detail-equipement.png` | `index.md` « détail d'un équipement » |
| 5 | `tableau-des-commandes.png` | `index.md` « tableau des commandes » |
| 6 | `compteurs-detail-piece.png` | `compteurs.md` « compteurs du détail de pièce » |
| 7 | `compteurs-equipement-deplie.png` | `compteurs.md` « ligne de compteurs d'un équipement déplié » |
| 8 | `configuration.png` | `index.md` « page de configuration » |
| 9 | `home-assistant-appareils.png` | aucun (site et fiche Market) |

Le parcours écrit `docs/fr_FR/images/captures-manifest.json`, y compris pour `--only video` (une section non régénérée est conservée avec sa propre version et sa propre date) (version du plugin, commit source, date, viewport,
langue, thème, empreinte SHA-256 de chaque fichier, commande de régénération ; aucune URL ni identifiant). La
vidéo (`jeedom2ha-presentation.webm`) est écrite dans `--video-out` et **n'est pas versionnée** : l'hébergement
du lien « vidéo » de la fiche Market est choisi par Alexandre ; consigner ici l'emplacement retenu.

### Règle de remplacement des marqueurs

Les marqueurs `<!-- CAPTURE-A-PRENDRE: … -->` de `docs/fr_FR/` ne sont remplacés (par `![…](images/<fichier>)`)
qu'**après** la relecture de ClaudeBox (CC-48, concordance média / version du plugin / texte de la documentation)
et la validation d'Alexandre. Un test (`test_story_23_2_captures.node.test.js`) garantit que chaque ligne du
storyboard correspond à un marqueur existant.

### État de la preuve

Médias non produits à ce jour : l'exécution terrain (Task 0, Task 1 sur la VM, Task 5) reste à faire. Les sélecteurs
du parcours viennent du DOM du plugin et du gate 20-0 mais sont non démontrés sur la VM ; les ajuster à la
première exécution, sans toucher au plugin.
