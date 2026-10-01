# Story 20.0: Gate de preuve UX outillé

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un mainteneur,
I want un gate de preuve UX outillé (Playwright, compte Jeedom dédié, écritures interceptées) exécutable avant tout `done` d'interface,
so that les stories 20.1 et suivantes puissent prouver leurs parcours réels par clic sans risque d'écrire dans la maison, et sans dépendre à chaque fois d'un clic manuel long (plan d'action d'Alex du 2026-09-26, étape 4 : « d'abord un gate de preuve UX outillé »).

**Parcours : complet.** Story bloquante, sans valeur utilisateur directe : aucune interface n'est modifiée par cette story.

## Acceptance Criteria

**AC1 — Interception par défaut : aucune écriture non maîtrisée**

**Given** une page du plugin `jeedom2ha` ouverte via Playwright sur la VM openclaw, authentifiée avec le compte Jeedom dédié
**When** un parcours est exécuté
**Then** toute requête vers `core/ajax/*.ajax.php` ou `plugins/*/core/ajax/*.ajax.php` est bloquée par défaut, sauf si le couple (point d'entrée, `action`) figure dans la liste des lectures autorisées, dans la liste d'authentification, dans la liste blanche d'override (uniquement dans les conditions d'AC2), ou s'il fait l'objet d'une réponse simulée déclarée par le parcours (section « Mécanisme d'interception des écritures »)
**And** aucune action à effet de bord n'aboutit, en particulier `scanTopology` (synchronisation complète vers HA), `executeHaAction` (« Publier » / « Suppr. »), `saveFilteringConfig`, `forceMqttManagerImport` et `testMqttConnection`
**And** chaque requête interceptée est journalisée avec son verdict (lecture autorisée / authentification / liste blanche / simulée / bloquée), sans aucune valeur sensible.

**AC2 — Liste blanche des parcours d'override, avec restauration garantie même en cas d'échec**

**Given** un parcours de preuve inscrit explicitement en liste blanche, qui pose puis retire un override (`saveMappingOverride`, `revertMappingOverride`)
**When** il s'exécute
**Then** le parcours déclare la liste fermée des équipements qu'il vise ; une requête `saveMappingOverride` ou `revertMappingOverride` n'est laissée passer que si son `eqId` appartient à cette liste (et, pour `saveMappingOverride`, si son `cmdId` est une commande de cet équipement) ; toute autre est bloquée, journalisée, et fait échouer le gate
**And** avant le parcours, le gate lit `data/ha_overrides.json` sur la box (lecture seule) : il exige que le fichier existe, relève son sha256 et son contenu JSON, et vérifie que chaque équipement visé n'a **aucun** override dans cet état de référence ; sinon, il refuse de lancer le parcours
**And** la restauration s'exécute dans un bloc de nettoyage garanti (`finally` / teardown), y compris si Playwright, le navigateur ou une vérification échoue : purge « tout l'équipement » (`revertMappingOverride` sans `cmdId`) pour chaque équipement visé, puis relecture du fichier (contenu JSON et sha256) ; si le navigateur est tombé, la purge passe par une nouvelle session authentifiée (liste d'authentification)
**And** le gate échoue si le contenu JSON final diffère de la référence (comparaison du JSON parsé ; les sha256 avant et après figurent au rapport), et l'écrit en tête de son rapport
**And** une commande de restauration autonome, idempotente, rejoue la même purge et la même vérification si le processus du gate a été tué avant son nettoyage ; elle ouvre pour cela une nouvelle session authentifiée (liste d'authentification), car la session du navigateur n'est jamais conservée sur disque.

**AC3 — Vérifications minimales avant tout `done` d'interface**

**Given** une story d'interface de l'epic 20 (20.1 et suivantes) arrivée à `ready-for-UX-validation`
**When** le gate 20.0 est exécuté sur cette story
**Then** il vérifie au minimum : aucune requête nécessaire au parcours bloquée sans réponse simulée déclarée, aucune écriture non maîtrisée (AC1), restauration vérifiée de `data/ha_overrides.json` pour les parcours d'override (AC2), aucune erreur JavaScript en console pendant le parcours, aucune ligne `ERROR` dans les journaux du démon pendant la fenêtre du parcours, et, pendant la fenêtre d'un parcours d'override, aucune ligne `DISCOVERY`, `Unpublishing`, `[SYNC]` ni `POST /action/sync` (une synchronisation pendant cette fenêtre publierait l'override temporaire dans HA : le gate est alors rouge et le signale, même si le fichier est restauré)
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

Le compte dédié `clawcode` est un compte de la vraie box Jeedom. Le plugin exige un compte administrateur (`isConnect('admin')` dans `core/ajax/jeedom2ha.ajax.php` et `desktop/php/jeedom2ha.php`) : le compte n'isole donc rien, ni côté Jeedom ni côté démon. L'absence d'impact repose entièrement sur l'interception par défaut (AC1) et sur la restauration garantie et vérifiée (AC2).

Aucun code de production (`desktop/`, `resources/daemon/`, `core/`) n'est modifié. Retour arrière : retrait de l'outillage de test, sans migration de données. En cas d'échec d'un parcours d'override, la commande de restauration autonome (AC2) remet `data/ha_overrides.json` dans son état de référence et le vérifie.

## Preuve terrain

Aucune preuve terrain au sens « déploiement sur la box » : cette story outille la preuve des stories suivantes, elle ne modifie rien de déployé. Sa propre preuve est l'exécution réussie du gate lui-même (AC1-AC5) sur un parcours de référence contre l'UI réelle via le compte dédié, journalisée dans un artefact de cette story.

## Task 0 — Pré-flight (bloquant, avant tout développement)

- [x] **Compte Jeedom dédié** : `clawcode`, créé par Alex le 2026-10-01 (16:22).
- [ ] **Droits du compte** : vérifier qu'il ouvre la page du plugin sans erreur 401. S'il n'est pas administrateur, s'arrêter et le signaler à Alex : le plugin exige `isConnect('admin')`.
- [ ] **Playwright et Chromium** : GO d'Alex le 2026-10-01 (16:22). Installation par clawcode sous `asahut` dans `/home/asahut/.openclaw/tools/jeedom2ha-gate` (navigateurs dans `~/.cache/ms-playwright`), sans `sudo` ni dépendance système. Relancer son test de fumée avant Task 1.
- [ ] **Fichier d'identifiants** : vérifier sa présence et ses droits par `ls -l` seulement (chemin d'AC4). S'il manque, s'arrêter et le signaler.
- [ ] **Accès en lecture de la VM vers la box** : le gate lit `data/ha_overrides.json` (sha256 et contenu) et les journaux du démon par SSH. Vérifier ce chemin avec les seules commandes `sha256sum`, `cat` sur ce fichier et `tail` sur les journaux ; consigner le compte utilisé. Sa clé SSH suit les mêmes règles qu'AC4 (jamais affichée, jamais copiée). Le gate n'envoie jamais d'autre commande à la box.

## Vérifications minimales du gate (AC3)

1. Aucune requête nécessaire au parcours bloquée sans réponse simulée déclarée, et aucune écriture non maîtrisée vers Jeedom ou le démon pendant tout le parcours (AC1).
2. Pour un parcours d'override en liste blanche : requêtes limitées aux équipements déclarés, et `data/ha_overrides.json` restauré à un contenu JSON identique à la référence, y compris après un échec (AC2).
3. Aucune erreur JavaScript dans la console du navigateur pendant le parcours.
4. Aucune ligne `ERROR` dans les journaux du démon pendant la fenêtre du parcours ; pendant la fenêtre d'un parcours d'override, aucune ligne `DISCOVERY`, `Unpublishing`, `[SYNC]` ni `POST /action/sync`.
5. Rapport du gate généré et lisible (verdict par vérification), joint à la story testée.

## Mécanisme d'interception des écritures

Le plugin expose ses actions via `core/ajax/jeedom2ha.ajax.php`, dispatché par le paramètre `action`. Le gate intercepte côté navigateur (routes Playwright) toutes les requêtes vers `core/ajax/*.ajax.php` et `plugins/*/core/ajax/*.ajax.php`, et applique un refus par défaut. Classement des actions du plugin, relevé dans `core/ajax/jeedom2ha.ajax.php` :

- **Lectures, autorisées** : `getMqttConfig`, `getBridgeStatus`, `getDiagnostics`, `getPublishedScopeForConsole`, `getMappingOverrides`, `previewMappingOverride` (aperçu à blanc, lecture seule par contrat, story 16.6), `exportDiagnostic` (lecture ; autorisée seulement si le parcours en a besoin).
- **Effets de bord, toujours bloqués** :
  - `scanTopology` : POST `/action/sync` vers le démon, qui publie les découvertes et les états MQTT et réaligne les écouteurs ;
  - `executeHaAction` : « Publier » / « Suppr. » (POST `/action/execute`) ;
  - `saveFilteringConfig`, `forceMqttManagerImport` : écrivent la configuration du plugin (`config::save`) ;
  - `testMqttConnection` : ouvre une connexion au broker MQTT.
- **Authentification** : la requête de connexion du cœur Jeedom (`core/ajax/user.ajax.php`, action de login), avec les identifiants d'AC4 ; aucune autre action de `user.ajax.php`.
- **Liste blanche des seuls parcours d'override (AC2)** : `saveMappingOverride`, `revertMappingOverride`, limitées aux équipements déclarés par le parcours.
- **Réponse simulée** : quand un parcours a besoin d'une action toujours bloquée (par exemple le rescan `scanTopology` de la story 20.4), le gate répond à sa place (`route.fulfill`) avec une réponse fixée par le test, après avoir vérifié l'action et sa charge utile ; le rapport la marque « simulée ». L'effet réel d'une telle action est prouvé séparément, par la preuve terrain de la story (règle permanente d'Alex du 2026-09-28 sur les preuves terrain, plugin et HA seulement : déploiement standard, relevés avant/après, retour arrière si panne).
- **Extension de la liste blanche** : une story qui ajoute une action d'écriture (par exemple la pose d'une exclusion ou d'un forçage en 20.2) l'inscrit dans le gate aux mêmes conditions qu'AC2 (limitée aux équipements déclarés, restaurée par la route de purge, vérifiée), et cette extension est relue par ClaudeBox.
- **Toute autre requête** (actions inconnues du plugin, points d'entrée du cœur Jeedom) : bloquée et journalisée. Une lecture du cœur nécessaire au chargement de la page n'est autorisée qu'après inscription explicite du couple (point d'entrée, `action`) en Task 1, revue par ClaudeBox.

Le gate lit l'état de `data/ha_overrides.json` sur la box en lecture seule (sha256 et contenu, par SSH) ; il n'écrit jamais ce fichier directement. La restauration passe uniquement par la route de purge du plugin.

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
- [ ] Task 3 — Implémenter l'interception par défaut, la liste d'authentification, la liste blanche d'override limitée aux équipements déclarés, la réponse simulée, la restauration garantie (`finally`) et la commande de restauration autonome (AC1, AC2)
- [ ] Task 4 — Implémenter les vérifications minimales (console JS, journaux démon `ERROR`) et le rapport de gate (AC3)
- [ ] Task 5 — Exécuter un parcours de référence de bout en bout (navigation, ouverture d'un équipement sans override dans l'état de référence, pose puis purge d'un override) et un parcours d'échec provoqué après la pose, pour prouver la restauration garantie ; consigner les deux dans un artefact de cette story
- [ ] Task 6 — Documenter dans cette story comment une story suivante invoque le gate et où elle joint son rapport avant `done` (AC5)

## Dev Notes

- Source : plan d'action d'Alex du 2026-09-26 (étape 4 : gate de preuve UX outillé d'abord), repris dans la conclusion de `pe-epic-19-retro-2026-10-01.md`.
- Décisions d'Alex du 2026-10-01 (16:22 et 17:58) : compte `clawcode` créé, GO pour l'installation de Playwright, emplacement du fichier d'identifiants (voir `sprint-change-proposal-2026-10-01-etape-4-interface.md`, « Décisions d'Alex »).
- Cette story n'ouvre aucun `PRODUCT_SCOPE`, n'ajoute aucun FR/NFR : c'est un outillage de test interne au dépôt.
