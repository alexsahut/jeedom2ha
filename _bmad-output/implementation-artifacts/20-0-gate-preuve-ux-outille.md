# Story 20.0: Gate de preuve UX outillé

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un mainteneur,
I want un gate de preuve UX outillé (Playwright, compte Jeedom dédié, écritures simulées et jamais transmises à la box) exécutable avant tout `done` d'interface,
so that les stories 20.1 et suivantes puissent prouver leurs parcours réels par clic (navigation et lectures réelles, aperçus réels sauf simulation déclarée) sans qu'aucune écriture n'atteigne la maison, et sans dépendre à chaque fois d'un clic manuel long (plan d'action d'Alex du 2026-09-26, étape 4 : « d'abord un gate de preuve UX outillé »).

**Parcours : complet.** Story bloquante, sans valeur utilisateur directe : aucune interface n'est modifiée par cette story.

## Acceptance Criteria

**AC1 — Interception par défaut : aucune écriture n'atteint la box**

**Given** une page du plugin `jeedom2ha` ouverte via Playwright sur la VM openclaw, authentifiée avec le compte Jeedom dédié, dans un contexte navigateur aux service workers bloqués (`serviceWorkers: 'block'`) et intercepté au niveau du contexte (`context.route`, onglets, popups et iframes compris)
**When** un parcours est exécuté
**Then** toute requête émise par le navigateur est bloquée par défaut, quel que soit son point d'entrée (`core/ajax/*.ajax.php`, `plugins/*/core/ajax/*.ajax.php`, `core/api/jeeApi.php` ou tout autre), sauf : les GET de ressources statiques (scripts, feuilles de style, images, polices), de la page de connexion et de la page du plugin servis par la box, les couples (point d'entrée, `action`) de la liste des lectures autorisées, la requête de connexion (liste d'authentification), et les actions auxquelles le gate répond lui-même (réponse simulée déclarée par le parcours, section « Mécanisme d'interception des écritures »)
**And** hors la requête de connexion, aucune action d'écriture n'est transmise à Jeedom ni au démon, en particulier `scanTopology` (synchronisation complète vers HA), `executeHaAction` (« Publier » / « Suppr. »), `saveFilteringConfig`, `forceMqttManagerImport`, `testMqttConnection`, `saveMappingOverride` et `revertMappingOverride` : le gate ne pose, ne retire ni ne restaure jamais rien sur la box
**And** chaque requête interceptée est journalisée avec son verdict (lecture autorisée / authentification / simulée / bloquée), sans aucune valeur sensible.

**AC2 — Écritures simulées et vérifiées, état de la box inchangé**

**Given** un parcours qui déclenche une écriture (enregistrement automatique d'un override après un aperçu valide, retour au mode automatique, et en 20.2 exclusion ou forçage), sur des équipements qu'il déclare dans une liste fermée et qui n'ont aucun override (ni par commande, ni d'équipement) dans `data/ha_overrides.json` au relevé initial (sinon le gate refuse de lancer le parcours)
**When** l'interface émet la requête d'écriture
**Then** le gate vérifie l'action et sa charge utile (`eqId` dans la liste fermée ; pour `saveMappingOverride`, `cmdId` commande de cet équipement et `haEntityType` égal au type dont l'aperçu vient d'être rendu ; pour `revertMappingOverride`, `cmdId` absent ou commande de cet équipement), puis répond à sa place (`route.fulfill`) avec la réponse que renverrait le plugin ; toute écriture non déclarée ou non conforme est bloquée, journalisée, et fait échouer le gate
**And** la relecture de l'équipement qui suit une écriture simulée (`getMappingOverrides` sur cet `eqId`) reçoit une réponse simulée, dérivée à l'exécution de la réponse réelle de `getMappingOverrides` et des aperçus (`previewMappingOverride`) des écritures simulées encore en vigueur sur cet équipement, selon une transformation fixée par le test et marquée « simulée » au rapport ; quand il n'en reste aucune (par exemple après le retour au mode automatique de tout l'équipement), la relecture est réelle ; l'aperçu est réel, sauf réponse simulée déclarée par le parcours, dérivée de la réponse réelle et marquée « simulée » au rapport (cas de la bascule « bloquante → prête », non démontrable par override TYPE sur les données réelles : constat du 2026-10-01 au soir dans `16-8-ac14-validation-2026-10-01.md`)
**And** avant et après le parcours, le gate relève en lecture seule, par SSH, le sha256 et le contenu JSON de `data/ha_overrides.json` (ou son absence), et le témoin d'activité du démon, lu par une requête `getBridgeStatus` du gate (`demon.uptime`, `derniere_synchro_terminee`, horodatage de `derniere_operation_resultat`) ; un contenu différent, un témoin illisible, un `uptime` inférieur au relevé initial (redémarrage) ou un horodatage changé (synchronisation, « Publier » ou « Suppr. » survenus pendant le parcours) fait échouer le gate (« activité sur la box pendant le parcours : parcours non concluant »), écrit en tête de son rapport
**And** la preuve d'une écriture réelle (persistance, purge par clic réel exigée par la décision d'Alex du 2026-09-29) relève de la preuve terrain de la story concernée, jamais du gate.

**AC3 — Vérifications minimales avant tout `done` d'interface**

**Given** une story d'interface de l'epic 20 (20.1 et suivantes) arrivée à `ready-for-UX-validation`
**When** le gate 20.0 est exécuté sur cette story
**Then** il vérifie au minimum : aucune requête nécessaire au parcours bloquée sans réponse simulée déclarée, aucune écriture transmise à la box (AC1), écritures simulées conformes et état de la box inchangé (AC2), aucune erreur JavaScript en console pendant le parcours, et aucune ligne `ERROR` dans les journaux `jeedom2ha_daemon` et `jeedom2ha` pendant la fenêtre du parcours
**And** le gate produit un rapport exploitable (liste des vérifications, verdict pass/fail par vérification), joint à la story testée.

**AC4 — Lecture des identifiants hors dépôt, jamais journalisée**

**Given** le fichier d'identifiants `/home/asahut/.config/jeedom2ha-gate/jeedom.env` sur la VM openclaw (dossier en 700, fichier en 600, clés `JEEDOM_USER` et `JEEDOM_PASSWORD`), déposé par Alex
**When** le gate démarre un parcours Playwright
**Then** il lit ce fichier à l'exécution (chemin surchargeable par la variable `JEEDOM2HA_GATE_CREDENTIALS`), et refuse de démarrer si le fichier manque ou si ses droits ne sont pas 600
**And** aucune valeur lue n'est copiée dans le dépôt, un journal, une capture, une trace ou un rapport ; l'état de session du navigateur (cookies) reste en mémoire et n'est jamais écrit sur disque
**And** un test dédié vérifie qu'aucune valeur lue depuis ce fichier n'apparaît dans les journaux, traces et rapports produits par le gate.

**AC5 — Gate bloquant, pas de `done` d'interface sans lui**

**Given** une story d'interface de l'epic 20
**When** sa Definition of Done est évaluée
**Then** le passage du gate 20.0 (AC1-AC4 verts) est une condition explicite de son `done`
**And** aucune story d'interface de l'epic 20 ne peut passer `ready-for-UX-validation` → `done` sans un rapport de gate vert joint.

## UI Impact

- **UI Impact :** Non — aucune interface livrée par cette story. Le gate observe et instrumente l'UI existante (16.8), il ne la modifie pas.

## Impact sur la production et retour arrière

Le compte dédié `clawcode` est un compte de la vraie box Jeedom. Le plugin exige un compte administrateur (`isConnect('admin')` dans `core/ajax/jeedom2ha.ajax.php` et `desktop/php/jeedom2ha.php`) : le compte n'isole donc rien, ni côté Jeedom ni côté démon. L'absence d'impact repose entièrement sur l'interception par défaut : aucune écriture n'est transmise à la box, toute écriture reçoit une réponse simulée (AC1, AC2). Le relevé avant/après de `data/ha_overrides.json` et du témoin du démon (AC2) le vérifie à chaque parcours.

Aucun code de production (`desktop/`, `resources/daemon/`, `core/`) n'est modifié. Retour arrière : retrait de l'outillage de test, sans migration de données. Le gate n'écrivant rien sur la box, aucune donnée de la box n'est à remettre en état, y compris si un parcours échoue ou si son processus est tué.

## Preuve terrain

Aucune preuve terrain au sens « déploiement sur la box » : cette story outille la preuve des stories suivantes, elle ne modifie rien de déployé. Sa propre preuve est l'exécution réussie du gate lui-même (AC1-AC4 ; AC5 est porté par la documentation de Task 6) sur un parcours de référence contre l'UI réelle via le compte dédié, journalisée dans un artefact de cette story.

## Task 0 — Pré-flight (bloquant, avant tout développement)

- [x] **Compte Jeedom dédié** : `clawcode`, créé par Alex le 2026-10-01 (16:22).
- [ ] **Droits du compte** : vérifier qu'il ouvre la page du plugin sans erreur 401. S'il n'est pas administrateur, s'arrêter et le signaler à Alex : le plugin exige `isConnect('admin')`.
- [ ] **Playwright et Chromium** : GO d'Alex le 2026-10-01 (16:22). Installation par clawcode sous `asahut` dans `/home/asahut/.openclaw/tools/jeedom2ha-gate` (navigateurs dans `~/.cache/ms-playwright`), sans `sudo` ni dépendance système. Relancer son test de fumée avant Task 1.
- [ ] **Fichier d'identifiants** : vérifier sa présence et ses droits par `ls -l` seulement (chemin d'AC4). S'il manque, s'arrêter et le signaler.
- [ ] **Accès en lecture de la VM vers la box** : le gate lit `data/ha_overrides.json` (sha256 et contenu) et les journaux `jeedom2ha_daemon` et `jeedom2ha` par SSH. Vérifier ce chemin avec les seules commandes `sha256sum`, `cat` sur ce fichier et `tail` sur ces journaux ; consigner le compte utilisé. Sa clé SSH suit les mêmes règles qu'AC4 (jamais affichée, jamais copiée). Le gate n'envoie jamais d'autre commande à la box.

## Vérifications minimales du gate (AC3)

1. Aucune requête nécessaire au parcours bloquée sans réponse simulée déclarée, et aucune écriture transmise à Jeedom ou au démon pendant tout le parcours (AC1).
2. Écritures du parcours simulées et conformes (action, équipements déclarés, charge utile), et état de la box inchangé : `data/ha_overrides.json` (sha256 et contenu JSON) et témoin du démon (`getBridgeStatus` : `demon.uptime`, `derniere_synchro_terminee`, horodatage de `derniere_operation_resultat`) identiques avant et après le parcours, sauf `demon.uptime` qui doit seulement avoir augmenté (AC2).
3. Aucune erreur JavaScript dans la console du navigateur pendant le parcours.
4. Aucune ligne `ERROR` dans les journaux `jeedom2ha_daemon` et `jeedom2ha` pendant la fenêtre du parcours.
5. Rapport du gate généré et lisible (verdict par vérification), joint à la story testée.

## Mécanisme d'interception des écritures

Le plugin expose ses actions via `core/ajax/jeedom2ha.ajax.php`, dispatché par le paramètre `action`. Le gate intercepte côté navigateur, au niveau du contexte Playwright (`context.route`, service workers bloqués), toutes les requêtes émises, quel que soit leur point d'entrée, et applique un refus par défaut (AC1). Classement des actions du plugin, relevé dans `core/ajax/jeedom2ha.ajax.php` :

- **Lectures, autorisées** : `getMqttConfig`, `getBridgeStatus` (aussi lu par le gate lui-même pour le témoin d'activité du démon, AC2), `getDiagnostics`, `getPublishedScopeForConsole`, `getMappingOverrides`, `previewMappingOverride` (aperçu à blanc, lecture seule par contrat, story 16.6), `exportDiagnostic` (lecture ; autorisée seulement si le parcours en a besoin).
- **Effets de bord, jamais transmis** (bloqués, ou simulés si le parcours le déclare) :
  - `scanTopology` : POST `/action/sync` vers le démon, qui publie les découvertes et les états MQTT et réaligne les écouteurs ;
  - `executeHaAction` : « Publier » / « Suppr. » (POST `/action/execute`) ;
  - `saveFilteringConfig`, `forceMqttManagerImport` : écrivent la configuration du plugin (`config::save`) ;
  - `testMqttConnection` : ouvre une connexion au broker MQTT.
- **Authentification** : la requête de connexion du cœur Jeedom (`core/ajax/user.ajax.php`, action de login), avec les identifiants d'AC4 ; aucune autre action de `user.ajax.php`.
- **Écritures d'override, jamais transmises (AC2)** : `saveMappingOverride` et `revertMappingOverride` reçoivent une réponse simulée après vérification de l'action et de la charge utile, limitée aux équipements déclarés par le parcours ; toute écriture hors de ces conditions est bloquée et fait échouer le gate.
- **Réponse simulée** : quand un parcours a besoin d'une action d'écriture (par exemple l'enregistrement d'un override, ou le rescan `scanTopology` de la story 20.4), le gate répond à sa place (`route.fulfill`) avec une réponse fixée par le test, après avoir vérifié l'action et sa charge utile ; le rapport la marque « simulée ». L'effet réel d'une telle action est prouvé séparément, par la preuve terrain de la story (règle permanente d'Alex du 2026-09-28 sur les preuves terrain, plugin et HA seulement : déploiement standard, relevés avant/après, retour arrière si panne). Une preuve terrain qui écrit réellement (par exemple la bascule d'AC14 de 16.8 ou la purge par clic réel de 20.2) vise un équipement non publié, relève le témoin `getBridgeStatus` avant et après, et lance une synchronisation corrective, après le retrait de l'override, si le témoin a bougé ; elle ne pose jamais d'exclusion sur un équipement publié sans GO d'Alex (revue Codex du 2026-10-01, voir `sprint-change-proposal-2026-10-01-etape-4-interface.md`, « Risques et suivi »).
- **Extension des écritures simulées** : une story qui ajoute une action d'écriture (par exemple la pose d'une exclusion ou d'un forçage en 20.2) l'ajoute aux écritures simulées aux mêmes conditions qu'AC2 (équipements déclarés, charge utile vérifiée, relecture dérivée des réponses réelles), jamais en passage réel, et cette extension est relue par ClaudeBox.
- **Toute autre requête** (actions inconnues du plugin, points d'entrée du cœur Jeedom, dont `core/api/jeeApi.php`) : bloquée et journalisée. Une lecture du cœur nécessaire au chargement de la page n'est autorisée qu'après inscription explicite du couple (point d'entrée, `action`) en Task 1, revue par ClaudeBox.

Le gate relit `data/ha_overrides.json` sur la box en lecture seule (sha256 et contenu, par SSH) et le témoin du démon (`getBridgeStatus`) avant et après chaque parcours (AC2) ; il n'écrit jamais rien sur la box, ni directement ni par une route du plugin.

## Lecture des identifiants

Voir AC4. Le fichier `/home/asahut/.config/jeedom2ha-gate/jeedom.env` est déposé par Alex lui-même sur la VM openclaw ; personne d'autre ne le crée ni ne le modifie. Le gate le lit à l'exécution, ne l'affiche jamais, et échoue explicitement s'il est absent ou mal protégé.

## Invariants concernés

Aucun invariant I1-I11 du pipeline n'est concerné : cette story est un outillage de test, sans branchement dans le pipeline de décision.

## Points fermés

Aucun CC-xx fermé par cette story : elle est le préalable outillé des stories qui ferment CC-25 (20.1) et CC-26 (20.2).

## Tasks / Subtasks

- [ ] Task 0 — Pré-flight (voir section dédiée ci-dessus) — bloquant
- [ ] Task 1 — Relire `core/ajax/jeedom2ha.ajax.php` en entier pour confirmer le classement ci-dessus, et relever les requêtes du cœur Jeedom émises au chargement de la page du plugin (tout bloqué, journal seulement), pour inscrire explicitement les seules lectures nécessaires (AC1)
- [ ] Task 2 — Mettre en place Playwright contre une page du plugin, authentification avec le compte dédié, lecture des identifiants selon AC4
- [ ] Task 3 — Implémenter l'interception par défaut au niveau du contexte (service workers bloqués), la liste d'authentification, les écritures simulées limitées aux équipements déclarés avec vérification de la charge utile, la relecture dérivée et la réponse simulée (AC1, AC2)
- [ ] Task 4 — Implémenter les vérifications minimales (console JS, lignes `ERROR` des journaux `jeedom2ha_daemon` et `jeedom2ha`, relevé avant/après de `data/ha_overrides.json` et du témoin `getBridgeStatus`) et le rapport de gate (AC2, AC3)
- [ ] Task 5 — Exécuter un parcours de référence de bout en bout (navigation, ouverture d'un équipement sans override dans `data/ha_overrides.json`, aperçu d'un changement de type, réel, puis simulé et déclaré pour la bascule « bloquante → prête », enregistrement et retour au mode automatique simulés, bascule rendue dans le diagnostic et la synthèse), puis un parcours de contrôle où une écriture non déclarée est émise : elle doit être bloquée et faire échouer le gate ; dans les deux cas, `data/ha_overrides.json` et le témoin du démon restent inchangés ; consigner les deux dans un artefact de cette story
- [ ] Task 6 — Documenter dans cette story comment une story suivante invoque le gate et où elle joint son rapport avant `done` (AC5)

## Dev Notes

- Source : plan d'action d'Alex du 2026-09-26 (étape 4 : gate de preuve UX outillé d'abord), repris dans la conclusion de `pe-epic-19-retro-2026-10-01.md`.
- Décisions d'Alex du 2026-10-01 (16:22 et 17:58) : compte `clawcode` créé, GO pour l'installation de Playwright, emplacement du fichier d'identifiants (voir `sprint-change-proposal-2026-10-01-etape-4-interface.md`, « Décisions d'Alex »).
- Cette story n'ouvre aucun `PRODUCT_SCOPE`, n'ajoute aucun FR/NFR : c'est un outillage de test interne au dépôt.
- Revue Codex du 2026-10-01 (P1, PR #193) : un override réellement posé par le gate pouvait être lu par une synchronisation concurrente, indépendante du gate (`/action/sync` relit `data/ha_overrides.json` : rescan depuis un autre navigateur, synchronisation de démarrage après tout redémarrage du démon, `scripts/deploy-to-box.sh` ; « Publier » le relit aussi), et publié dans HA avant son retrait. Le gate ne transmet donc plus aucune écriture (AC1, AC2) ; les écritures réelles relèvent des preuves terrain, avec la règle de la section « Mécanisme d'interception des écritures ».
