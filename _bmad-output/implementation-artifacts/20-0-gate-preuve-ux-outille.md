# Story 20.0: Gate de preuve UX outillé

Status: review

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
**And** chaque requête interceptée est journalisée avec son verdict (lecture autorisée / authentification / simulée / bloquée), sans aucune valeur sensible
**And** un test dédié de l'intercepteur émet chacune de ces actions d'écriture et vérifie qu'aucune n'est transmise (bloquée ou simulée), pour qu'une régression de l'intercepteur fasse échouer ce test avant tout parcours sur la box.

**AC2 — Écritures simulées et vérifiées, état de la box inchangé**

**Given** un parcours qui déclenche une écriture (enregistrement automatique d'un override après un aperçu valide, retour au mode automatique, et en 20.2 exclusion ou forçage), sur des équipements qu'il déclare dans une liste fermée et qui n'ont aucun override (ni par commande, ni d'équipement) dans `data/ha_overrides.json` au relevé initial (sinon le gate refuse de lancer le parcours)
**When** l'interface émet la requête d'écriture
**Then** le gate vérifie l'action et sa charge utile (`eqId` dans la liste fermée ; pour `saveMappingOverride`, `cmdId` commande de cet équipement et `haEntityType` égal au type dont l'aperçu vient d'être rendu ; pour `revertMappingOverride`, `cmdId` absent ou commande de cet équipement), puis répond à sa place (`route.fulfill`) avec la réponse que renverrait le plugin ; toute écriture non déclarée ou non conforme est bloquée, journalisée, et fait échouer le gate
**And** la relecture de l'équipement qui suit une écriture simulée (`getMappingOverrides` sur cet `eqId`) reçoit une réponse simulée, dérivée à l'exécution de la réponse réelle de `getMappingOverrides` et des aperçus (`previewMappingOverride`) des écritures simulées encore en vigueur sur cet équipement, selon une transformation fixée par le test et marquée « simulée » au rapport ; quand il n'en reste aucune (par exemple après le retour au mode automatique de tout l'équipement), la relecture est réelle ; l'aperçu est réel, sauf réponse simulée déclarée par le parcours, dérivée de la réponse réelle et marquée « simulée » au rapport (cas de la bascule « bloquante → prête », non démontrable par override TYPE sur les données réelles : constat du 2026-10-01 au soir dans `16-8-ac14-validation-2026-10-01.md`)
**And** avant et après le parcours, le gate relève en lecture seule, par SSH, le sha256, la date de modification (`stat -c %y`, à la nanoseconde) et le contenu JSON de `data/ha_overrides.json` (ou son absence), le processus du démon (PID trouvé par `pgrep -u www-data -f '[j]eedom2ha/.*resources/daemon/main\.py'`, qui doit renvoyer exactement un PID — zéro ou plusieurs correspondances rend le témoin illisible et fait échouer le gate —, heure de démarrage et arguments par `ps -o lstart=,args= -p <pid>`, dont seule l'option `--loglevel` est conservée *(amendé le 2026-10-02, constat clawcode sur la box 192.168.1.21 : le fichier PID n'est pas lisible par le compte SSH `asahut` — Permission non accordée — ; texte d'origine : « PID lu dans `/tmp/jeedom/jeedom2ha/deamon.pid`, heure de démarrage et arguments par `ps -o lstart=,args= -p <pid>`, dont seule l'option `--loglevel` est conservée »)*), le témoin d'activité du démon, lu par une requête `getBridgeStatus` du gate (`derniere_synchro_terminee`, horodatage de `derniere_operation_resultat`), et l'empreinte sha256, jamais la valeur, de la configuration du plugin écrite par `saveFilteringConfig` et `forceMqttManagerImport` (clés `excludedPlugins`, `excludedObjects`, `confidencePolicy`, `mqttHost`, `mqttPort`, `mqttUser`, `mqttTls`, `mqttPassword` : `core/ajax/jeedom2ha.ajax.php:522-527` et `:760-762` ; la valeur de `mqttPassword` n'est lue qu'en mémoire pour calculer l'empreinte, jamais journalisée, affichée ni conservée), lue par la lecture de configuration du cœur Jeedom (`core/ajax/config.ajax.php`, action `getKey`, limitée à ces clés et inscrite en Task 1) ; le relevé final n'a lieu qu'une fois terminée toute requête en cours du navigateur, et au moins 90 s après la dernière requête du parcours (requête du navigateur, transmise ou simulée) ; les sondes du relevé lui-même (`getBridgeStatus`, `getKey`, lectures SSH) n'entrent pas dans ce décompte et ne sont émises qu'une fois ce délai écoulé : au-delà du budget d'une action du plugin (60 s, `core/php/jeedom2ha_action_budget.php:27`), une opération du démon déclenchée à tort, dont l'issue n'est écrite qu'à la fin (`resources/daemon/transport/http_server.py:3909-3922` et `4214-4227`), a ainsi abouti avant le relevé, ou a déjà écrit ses lignes `[DISCOVERY]`, émises au fil de la publication (AC3) ; un contenu ou une date de modification différents (toute écriture du fichier, même restaurée à l'identique), une empreinte de configuration différente, un témoin illisible (PID ou processus introuvable, `getBridgeStatus` répondant `daemon: false` ou sans ces champs), un PID ou une heure de démarrage du processus différents (redémarrage pendant le parcours, constaté sur l'horloge de la box seule) ou un horodatage changé (synchronisation, « Publier » ou « Suppr. » survenus pendant le parcours) fait échouer le gate (« activité sur la box pendant le parcours : parcours non concluant »), écrit en tête de son rapport
**And** la preuve d'une écriture réelle (persistance, purge par clic réel exigée par la décision d'Alex du 2026-09-29) relève de la preuve terrain de la story concernée, jamais du gate.

**AC3 — Vérifications minimales avant tout `done` d'interface**

**Given** une story d'interface de l'epic 20 (20.1 et suivantes) arrivée à `ready-for-UX-validation`
**When** le gate 20.0 est exécuté sur cette story
**Then** il vérifie au minimum : aucune requête nécessaire au parcours bloquée sans réponse simulée déclarée, aucune écriture transmise à la box (AC1), écritures simulées conformes et état de la box inchangé (AC2), aucune erreur JavaScript en console pendant le parcours, aucune ligne `ERROR` dans les journaux `jeedom2ha_daemon` et `jeedom2ha` pendant la fenêtre du parcours, et aucune trace d'écriture reçue par la box pendant cette fenêtre : dans `jeedom2ha_daemon`, aucune ligne `[OVERRIDES] Override HA sauvegardé via UI` ni `[OVERRIDES] Retour mode auto via UI` (`resources/daemon/transport/http_server.py:3060-3063` et `3134-3137`), `[TOPOLOGY] Received sync request` (`:1728`), `[ACTION] intention=`, `[DISCOVERY]` ni `[MQTT] Testing connection` ; ces lignes étant au niveau INFO, le gate vérifie avant le parcours que le démon en cours tourne au niveau `info` ou `debug` (option `--loglevel` de ses arguments, relevés selon AC2), sinon le témoin est illisible et le gate échoue ; les écritures faites par le PHP seul (`saveFilteringConfig`, `forceMqttManagerImport`), que ce niveau ne couvre pas, sont prouvées par l'empreinte de configuration d'AC2, indépendante de tout niveau de journal
**And** le gate produit un rapport exploitable (liste des vérifications, verdict pass/fail par vérification), joint à la story testée.

**AC4 — Lecture des identifiants hors dépôt, jamais journalisée**

**Given** le fichier d'identifiants `/home/asahut/.config/jeedom2ha-gate/jeedom.env` sur la VM openclaw (dossier en 700, fichier en 600, clés `JEEDOM_USER` et `JEEDOM_PASSWORD`), déposé par Alex
**When** le gate démarre un parcours Playwright
**Then** il lit ce fichier à l'exécution (chemin surchargeable par la variable `JEEDOM2HA_GATE_CREDENTIALS`), et refuse de démarrer si le fichier manque ou si ses droits ne sont pas 600
**And** aucune valeur lue n'est copiée dans le dépôt, un journal, une capture, une trace ou un rapport ; l'état de session du navigateur (cookies) reste en mémoire et n'est jamais écrit sur disque *(amendé le 2026-10-04 : le périmètre du contrôle automatique se limite aux deux valeurs du fichier d'identifiants et à `mqttPassword` (AC2) ; les autres clés ne sont pas des secrets, `mqttUser` apparaissant légitimement dans les chemins du plugin ; texte d'origine : « aucune valeur lue n'est copiée dans le dépôt, un journal, une capture, une trace ou un rapport ; l'état de session du navigateur (cookies) reste en mémoire et n'est jamais écrit sur disque »)*
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
- [x] **Droits du compte** : vérifié le 2026-10-02 — login `core/ajax/user.ajax.php` (`action=login`) réussi, page du plugin accessible (`contains_jeedom2ha=true`, pas de marqueur de refus), `getKey confidencePolicy` répond `state=ok`. Aucune erreur 401 : le compte est administrateur.
- [x] **Playwright et Chromium** : GO d'Alex le 2026-10-01 (16:22). Installation déjà présente sous `asahut` dans `/home/asahut/.openclaw/tools/jeedom2ha-gate` (`node_modules/`, Chromium `chromium-1243` en cache). Test de fumée relancé le 2026-10-02 (`node smoke.mjs`) : version Chromium puis `ok-jeedom2ha-gate`.
- [x] **Fichier d'identifiants** : vérifié le 2026-10-02 par `ls -l` seulement (chemin d'AC4) : dossier `drwx------`, fichier `-rw-------`, propriétaire `asahut`. Conforme.
- [x] **Accès en lecture de la VM vers la box** : le gate lit `data/ha_overrides.json` (sha256, date de modification et contenu), le processus du démon (PID, heure de démarrage et niveau de journal), et les journaux `jeedom2ha_daemon` et `jeedom2ha` par SSH. Vérifié le 2026-10-02 avec les commandes `sha256sum`, `stat -c %y` et `cat` sur ce fichier, `pgrep -u www-data -f '[j]eedom2ha/.*resources/daemon/main\.py'` (exactement un PID attendu) *(amendé le 2026-10-02, constat clawcode : le fichier `/tmp/jeedom/jeedom2ha/deamon.pid` n'est pas lisible par le compte SSH `asahut` — Permission non accordée ; texte d'origine : « `cat` sur `/tmp/jeedom/jeedom2ha/deamon.pid` »)*, puis `ps -o lstart=,args= -p <pid>` sur le PID trouvé, et `tail`/`grep` sur ces journaux ; compte utilisé : `asahut@192.168.1.21` (clé SSH jamais affichée, jamais copiée). Résultat consigné dans `jeedom2ha-200-t0-report.md` (hors dépôt) : sha256 de `ha_overrides.json` conforme à l'attendu, 1 PID stable (démon démarré le 2026-10-01 18:03:02, `--loglevel info`), les deux journaux lisibles par `asahut` (`jeedom2ha_daemon` : 0 ligne `ERROR` ; `jeedom2ha` : 3016 lignes `ERROR`, la dernière datée du 2026-09-27 à 02:15, aucune le 2026-10-02). Le gate n'envoie jamais d'autre commande à la box.

## Vérifications minimales du gate (AC3)

1. Aucune requête nécessaire au parcours bloquée sans réponse simulée déclarée, et aucune écriture transmise à Jeedom ou au démon pendant tout le parcours (AC1).
2. Écritures du parcours simulées et conformes (action, équipements déclarés, charge utile), et état de la box inchangé : `data/ha_overrides.json` (sha256, date de modification et contenu JSON) témoin du démon (`getBridgeStatus` : `derniere_synchro_terminee`, horodatage de `derniere_operation_resultat`) et empreinte de la configuration du plugin identiques avant et après le parcours, relevé final au moins 90 s après la dernière requête du parcours (sondes du relevé exclues), ainsi que le PID et l'heure de démarrage du processus du démon, lus sur la box (AC2).
3. Aucune erreur JavaScript dans la console du navigateur pendant le parcours.
4. Aucune ligne `ERROR` dans les journaux `jeedom2ha_daemon` et `jeedom2ha` pendant la fenêtre du parcours, et aucune des lignes d'écriture listées en AC3 (`[OVERRIDES]` d'enregistrement et de retour, `[TOPOLOGY] Received sync request`, `[ACTION] intention=`, `[DISCOVERY]`, `[MQTT] Testing connection` dans `jeedom2ha_daemon`) pendant cette fenêtre, le démon tournant au niveau `info` ou `debug` (AC3) : preuve indépendante qu'aucune écriture n'a atteint la box, même si une écriture suivie de sa purge laissait le contenu du fichier inchangé.
5. Rapport du gate généré et lisible (verdict par vérification), joint à la story testée.

## Mécanisme d'interception des écritures

Le plugin expose ses actions via `core/ajax/jeedom2ha.ajax.php`, dispatché par le paramètre `action`. Le gate intercepte côté navigateur, au niveau du contexte Playwright (`context.route`, service workers bloqués), toutes les requêtes émises, quel que soit leur point d'entrée, et applique un refus par défaut (AC1). Classement des actions du plugin, relevé dans `core/ajax/jeedom2ha.ajax.php` :

- **Lectures, autorisées** : `getMqttConfig`, `getBridgeStatus` (aussi lu par le gate lui-même pour le témoin d'activité du démon, AC2), `getDiagnostics`, `getPublishedScopeForConsole`, `getMappingOverrides`, `previewMappingOverride` (aperçu à blanc, lecture seule par contrat, story 16.6), `exportDiagnostic` (lecture ; autorisée seulement si le parcours en a besoin).
- **Lectures du cœur Jeedom, nécessaires au chargement de la page du plugin**, relevées à l'exécution le 2026-10-02 (second passage, 13 lectures, aucun blocage, témoins avant/après identiques) : `core/ajax/eqLogic.ajax.php`, action `listByType` ; `core/ajax/event.ajax.php`, action `changes`, reçoit une réponse simulée déclarée après 5 s, `{"state":"ok","result":{"datetime":<microtime>,"result":[]}}`, afin de couper les événements de la maison et leur réaction cœur `toHtml`, constatée au premier parcours réel du 2026-10-04 *(amendé le 2026-10-04 : le gate ferme toutes les pages avant l'attente de 90 s, mais conserve le contexte ; les sondes finales `getBridgeStatus` et `getKey` passent ainsi dans la même session, sans seconde connexion, conformément à l'unique essai de connexion par exécution ; texte d'origine : « attente longue côté cœur Jeedom — le gate ferme le contexte du navigateur en fin de parcours, puis attend les 90 s, puis prend le témoin final, pour qu'aucune requête ne reste en cours »)*. Toutes ces lectures, ainsi que celles du plugin ci-dessus, sont autorisées en POST seulement, à correspondance exacte du chemin et de la valeur d'`action` ; une action présente plus d'une fois (dans l'URL et/ou dans le corps) est bloquée, même si l'une des valeurs est par ailleurs autorisée.
- **Lecture de configuration propre au gate** : `core/ajax/config.ajax.php`, action `getKey`, `plugin=jeedom2ha`, limitée aux 8 clés d'AC2 (`excludedPlugins`, `excludedObjects`, `confidencePolicy`, `mqttHost`, `mqttPort`, `mqttUser`, `mqttTls`, `mqttPassword`). C'est une sonde du relevé, émise par le gate lui-même (empreinte de configuration avant/après, AC2) et non par la page : elle ne passe donc pas par l'intercepteur du navigateur, et doit être bornée dans le code du gate, pas dans `ALLOWED_READS`.
- **Effets de bord, jamais transmis** (bloqués, ou simulés si le parcours le déclare) :
  - `scanTopology` : POST `/action/sync` vers le démon, qui publie les découvertes et les états MQTT et réaligne les écouteurs ;
  - `executeHaAction` : « Publier » / « Suppr. » (POST `/action/execute`) ;
  - `saveFilteringConfig`, `forceMqttManagerImport` : écrivent la configuration du plugin (`config::save`) ;
  - `testMqttConnection` : ouvre une connexion au broker MQTT.
- **Authentification** : le lanceur seul se connecte hors intercepteur par `context.request`, en un essai, avec les identifiants d'AC4 ; les parcours ne saisissent aucun identifiant. Toute connexion émise par une page (`core/ajax/user.ajax.php`, `action=login`, champs `username`, `password`, `twoFactorCode` et `storeConnection`, confirmés par lecture de `core/ajax/user.ajax.php` le 2026-10-02 : test de l'action ligne 24, champs lignes 50/51/54/60/87) est refusée et fait échouer le gate ; aucune autre action de `user.ajax.php`. Un échec du seul essai du lanceur arrête tout le parcours sans nouvelle tentative — le cœur Jeedom bannit une IP après plusieurs échecs, et l'IP de la VM openclaw sert aussi à ClawBox pour piloter la maison.
- **Écritures d'override, jamais transmises (AC2)** : `saveMappingOverride` et `revertMappingOverride` reçoivent une réponse simulée après vérification de l'action et de la charge utile, limitée aux équipements déclarés par le parcours ; toute écriture hors de ces conditions est bloquée et fait échouer le gate.
- **Réponse simulée** : quand un parcours a besoin d'une action d'écriture (par exemple l'enregistrement d'un override, ou le rescan `scanTopology` de la story 20.4), le gate répond à sa place (`route.fulfill`) avec une réponse fixée par le test, après avoir vérifié l'action et sa charge utile ; le rapport la marque « simulée ». L'effet réel d'une telle action est prouvé séparément, par la preuve terrain de la story (règle permanente d'Alex du 2026-09-28 sur les preuves terrain, plugin et HA seulement : déploiement standard, relevés avant/après, retour arrière si panne). Une preuve terrain qui écrit réellement (par exemple la purge par clic réel de 20.2) vise un équipement non publié, relève le témoin `getBridgeStatus` avant et après, et lance une synchronisation corrective, après le retrait de l'override, si le témoin a bougé ; elle ne pose jamais d'exclusion sur un équipement publié sans GO d'Alex (revue Codex du 2026-10-01, voir `sprint-change-proposal-2026-10-01-etape-4-interface.md`, « Risques et suivi »).
- **Extension des écritures simulées** : une story qui ajoute une action d'écriture (par exemple la pose d'une exclusion ou d'un forçage en 20.2) l'ajoute aux écritures simulées aux mêmes conditions qu'AC2 (équipements déclarés, charge utile vérifiée, relecture dérivée des réponses réelles), jamais en passage réel, et cette extension est relue par ClaudeBox.
- **Toute autre requête** (actions inconnues du plugin, points d'entrée du cœur Jeedom, dont `core/api/jeeApi.php`) : bloquée et journalisée. Une lecture du cœur nécessaire au chargement de la page n'est autorisée qu'après inscription explicite du couple (point d'entrée, `action`) en Task 1, revue par ClaudeBox.
- **Règles pour Task 3** : un GET « statique » n'est autorisé que sans paramètre `action`, et hors des chemins `*/ajax/*` et `/core/api/*` (le type de ressource seul ne suffit pas). Le gate ne sert jamais de redirection au navigateur : toute requête transmise passe par `route.fetch({ maxRedirects: 0 })`, et une redirection est refusée avant le `fulfill` et fait échouer le gate ; le garde sur les requêtes redirigées (vérification de l'URL finale après navigation) reste en filet.
- **Règle pour Task 4** : les lignes du journal du démon à vérifier (absence des marqueurs d'écriture, AC3) sont sélectionnées par horodatage, dans la fenêtre du parcours, sur l'horloge de la box — jamais par une simple différence de nombre de lignes. Le témoin est illisible si le journal a été tronqué pendant la fenêtre (troncature en place constatée le 2026-10-02, sans fichiers de rotation numérotés), c'est-à-dire si sa taille a baissé, ou si l'horodatage de sa première ligne datée a changé entre avant et après.
- **Amendement 2026-10-04 — Règle pour Task 4** : le texte d'origine ci-dessus est conservé pour l'historique. Les compteurs AC3 utilisent désormais exclusivement les octets ajoutés entre les témoins : `tail -c +<taille_avant+1> <fichier> | head -c <taille_après-taille_avant>`. Les tailles sont des entiers validés; une baisse de taille, ou un changement de la première ligne datée, rend toujours le témoin illisible. La sélection par horodatage disparaît : les traces Python sans horodatage sont donc comptées.

Le gate relit `data/ha_overrides.json` sur la box en lecture seule (sha256, date de modification et contenu, par SSH), le processus du démon (PID — trouvé par `pgrep -u www-data -f '[j]eedom2ha/.*resources/daemon/main\.py'`, exactement un PID attendu *(amendé le 2026-10-02 ; texte d'origine : « PID »)* —, heure de démarrage, niveau de journal, par SSH), le témoin du démon (`getBridgeStatus`) et l'empreinte de la configuration du plugin (`getKey` du cœur) avant et après chaque parcours (AC2) ; il n'écrit jamais rien sur la box, ni directement ni par une route du plugin.

## Lecture des identifiants

Voir AC4. Le fichier `/home/asahut/.config/jeedom2ha-gate/jeedom.env` est déposé par Alex lui-même sur la VM openclaw ; personne d'autre ne le crée ni ne le modifie. Le gate le lit à l'exécution, ne l'affiche jamais, et échoue explicitement s'il est absent ou mal protégé.

## Invocation du gate par une story suivante

- **Prérequis** : le fichier d'identifiants est en mode `600` ; Playwright est présent dans le dossier indiqué par `JEEDOM2HA_GATE_TOOLS`.
- **Module de parcours** : il exporte `name`, `declaredEquipments`, `declaredBascules` et `run(page, { helpers })`. Le parcours consigne ses seuls constats bornés avec `helpers.record` : clé `[a-z][a-z0-9_-]{0,79}`, nombre fini, booléen, ou chaîne de 80 caractères au plus sans `?` ni `=`.
- **Commande** : `node tests/e2e/gate/run-gate.mjs --parcours <module-parcours.mjs> --report <dossier-rapport>`.
- **Artefact de story** : le dossier de rapport contient `gate-report.md` et `gate-report.json`. La story joint un artefact `_bmad-output/implementation-artifacts/<story>-gate-<date>.md` qui reprend le verdict, les vérifications, les réponses simulées et les constats du parcours.
- **Lecture et relance** : un `PASS` avec toutes les vérifications vertes est la preuve du parcours. Un témoin illisible seulement parce que le journal a été tronqué se relance ; tout autre `FAIL` s'analyse avant toute relance.
- **Limites connues** : le badge « pas encore appliqué » n'est pas prouvé ; `serviceWorkers: 'block'` neutralise `register()` sans le faire échouer ; les événements du cœur sont simulés vides et `toHtml` reste bloquée ; les écritures réelles relèvent de la preuve terrain de chaque story.

## Invariants concernés

Aucun invariant I1-I11 du pipeline n'est concerné : cette story est un outillage de test, sans branchement dans le pipeline de décision.

## Points fermés

Aucun CC-xx fermé par cette story : elle est le préalable outillé des stories qui ferment CC-25 (20.1) et CC-26 (20.2).

## Tasks / Subtasks

- [x] Task 0 — Pré-flight (voir section dédiée ci-dessus) — bloquant — *terminée le 2026-10-02 (4 sous-points verts) ; AC2/Task 0/mécanisme amendés le même jour sur le PID du démon (`pgrep`, pas le fichier PID illisible)*
- [x] Task 1 — Relire `core/ajax/jeedom2ha.ajax.php` en entier pour confirmer le classement ci-dessus, et relever les requêtes du cœur Jeedom émises au chargement de la page du plugin (tout bloqué, journal seulement), pour inscrire explicitement les seules lectures nécessaires (AC1), dont la lecture de configuration `getKey` limitée aux clés d'AC2 — *relecture statique de `core/ajax/jeedom2ha.ajax.php` terminée le 2026-10-02 (14 actions, aucun écart avec cette section, relevé indépendant par ClaudeBox), suivie de deux passages d'exécution du script de relevé le même jour (premier passage sans lecture autorisée, confirmant l'arrêt précoce du chargement ; second passage avec la liste fermée `ALLOWED_READS`, 13 lectures du cœur et du plugin, aucun blocage, témoins avant/après SSH identiques aux deux passages) — les lectures nécessaires au chargement sont inscrites explicitement ci-dessus, section « Mécanisme d'interception des écritures ».*
- [x] Task 2 — Mettre en place Playwright contre une page du plugin, authentification avec le compte dédié, lecture des identifiants selon AC4 — *réalisée le 2026-10-04 : `run-gate.mjs` et `lib/playwright.mjs`, vérifiés par les tests unitaires 20-0 et le self-test local.*
- [x] Task 3 — Implémenter l'interception par défaut au niveau du contexte (service workers bloqués), la liste d'authentification, les écritures simulées limitées aux équipements déclarés avec vérification de la charge utile, la relecture dérivée, la réponse simulée et le test dédié de l'intercepteur (AC1, AC2) — *réalisée le 2026-10-04 : `lib/policy.mjs`, `lib/interceptor.mjs`, `lib/simulate.mjs` et `interceptor-selftest.mjs`, vérifiés par le self-test et les tests unitaires 20-0.*
- [x] Task 4 — Implémenter les vérifications minimales (console JS, lignes `ERROR` des journaux `jeedom2ha_daemon` et `jeedom2ha`, absence des lignes d'écriture listées en AC3 et niveau de journal du démon, relevé avant/après de `data/ha_overrides.json` avec sa date de modification, du processus du démon (PID, heure de démarrage), du témoin `getBridgeStatus` et de l'empreinte de configuration, relevé final au moins 90 s après la dernière requête du parcours (sondes du relevé exclues)) et le rapport de gate (AC2, AC3) — *réalisée le 2026-10-04 : `lib/box-witness.mjs`, `lib/report.mjs` et `run-gate.mjs`, vérifiés par les tests unitaires 20-0.*
- [x] Task 5 — Exécuter un parcours de référence de bout en bout (navigation, ouverture d'un équipement sans override dans `data/ha_overrides.json`, aperçu d'un changement de type, réel, puis simulé et déclaré pour la bascule « bloquante → prête », enregistrement et retour au mode automatique simulés, bascule rendue dans le diagnostic et la synthèse, qui porte aussi la vue au clic de la bascule d'AC14 de 16.8, amendé le 2026-10-02, condition du `done` de 16.8), puis un parcours de contrôle où une écriture non déclarée est émise : elle doit être bloquée et faire échouer le gate ; dans les deux cas, `data/ha_overrides.json` et le témoin du démon restent inchangés ; consigner les deux dans un artefact de cette story — *réalisée le 2026-10-04 : parcours référence PASS et contrôle FAIL attendu, consignés dans `20-0-gate-2026-10-04.md`.*
- [x] Task 6 — Documenter dans cette story comment une story suivante invoque le gate et où elle joint son rapport avant `done` (AC5) — *réalisée le 2026-10-04 : section « Invocation du gate par une story suivante », avec le contrat de parcours, la commande, l'artefact attendu, la lecture du verdict et les limites connues.*

## Dev Notes

- Source : plan d'action d'Alex du 2026-09-26 (étape 4 : gate de preuve UX outillé d'abord), repris dans la conclusion de `pe-epic-19-retro-2026-10-01.md`.
- Décisions d'Alex du 2026-10-01 (16:22 et 17:58) : compte `clawcode` créé, GO pour l'installation de Playwright, emplacement du fichier d'identifiants (voir `sprint-change-proposal-2026-10-01-etape-4-interface.md`, « Décisions d'Alex »).
- Cette story n'ouvre aucun `PRODUCT_SCOPE`, n'ajoute aucun FR/NFR : c'est un outillage de test interne au dépôt.
- Revue Codex du 2026-10-01 (P1, PR #193) : un override réellement posé par le gate pouvait être lu par une synchronisation concurrente, indépendante du gate (`/action/sync` relit `data/ha_overrides.json` : rescan depuis un autre navigateur, synchronisation de démarrage après tout redémarrage du démon, `scripts/deploy-to-box.sh` ; « Publier » le relit aussi), et publié dans HA avant son retrait. Le gate ne transmet donc plus aucune écriture (AC1, AC2) ; les écritures réelles relèvent des preuves terrain, avec la règle de la section « Mécanisme d'interception des écritures ».
- Revue Codex du 2026-10-02 (PR #193, sur `95fc370`) : (P1) une écriture transmise par erreur puis purgée laisserait le contenu de `data/ha_overrides.json` inchangé sans toucher au témoin `getBridgeStatus` ; le gate exige donc aussi une date de modification inchangée et l'absence des lignes d'écriture de chaque action du plugin dans les journaux (niveau `info` vérifié sur le processus du démon) ; (P2) un redémarrage se détecte par le PID et l'heure de démarrage du processus, lus sur la box, pas par un `uptime` inférieur ni par une heure déduite sur l'horloge de la VM.
- Revue Codex du 2026-10-02 (PR #193, sur `f26b1e9`) : (P1) une action du démon transmise à tort n'écrit son issue qu'à la fin : le relevé final attend au moins 90 s après la dernière requête du parcours (sondes du relevé exclues) ; (P2) l'option `--loglevel` du démon ne prouve rien sur le journal PHP : les écritures de configuration du PHP sont prouvées par une empreinte de configuration avant/après ; le contrôle principal reste l'intercepteur, couvert par un test dédié (AC1).
- Modèle de menace retenu (2026-10-02) : la garantie « aucune écriture sur la box » repose sur l'intercepteur à refus par défaut, testé par AC1 avant tout parcours ; les témoins côté box (AC2, AC3) sont une détection complémentaire au mieux, non exhaustive par construction. Un angle mort de témoin découvert plus tard est une amélioration de la détection, traitée hors de cette story, et ne remet pas en cause la garantie.
- 2026-10-04 — La garantie du gate porte sur les requêtes émises par la page ; un parcours est du code du dépôt, relu par ClaudeBox avant exécution, qui tourne dans le processus du lanceur avec ses privilèges. Le filtrage du source est un garde-fou, pas un isolement. Un isolement réel (processus séparé sans réseau ni clé SSH) serait une évolution hors de 20-0 (revue Codex PR #196).

## Dev Agent Record

### Completion Notes List

- 2026-10-04 — troisième tour de Codex (PR #197) traité par `156f7f7` ; preuve refaite à ce head. Statut inchangé.
- 2026-10-04 — Second tour de Codex traité par `ba02b1f` et `0ba76d8` ; preuve refaite au head `0ba76d8`. Statut inchangé.
- 2026-10-04 après-midi — Preuve finale au head `3db15e5` : référence PASS et contrôle d'écriture non déclarée en FAIL attendu ; artefact `20-0-gate-2026-10-04.md` mis à jour. Statut inchangé.
- 2026-10-04 — Workflow `dev-story` : Tasks 2 à 6 terminées ; le parcours de référence est PASS et le contrôle produit le `block-fail` attendu, documentés dans `20-0-gate-2026-10-04.md`. Statut résultant : `review` ; le code review est le prochain jalon BMAD.
- 2026-10-04 — Amendement H2 : lanceur durci (navigations, console contexte, AC4, garde-fou de parcours, fenêtres de journaux par octets et délais); validation locale requise avant toute nouvelle exécution terrain. Statut inchangé : `review`.
- 2026-10-04 — quatrième tour de Codex (PR #197) traité par `dd03c63`, `5f0e72c` et `35e7ca3` ; preuve refaite à ce head.

### File List

- `_bmad-output/implementation-artifacts/16-8-surface-navigation-piece-equipement-commande-homebridge.md`
- `_bmad-output/implementation-artifacts/20-0-gate-2026-10-04.md`
- `_bmad-output/implementation-artifacts/20-0-gate-preuve-ux-outille.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `tests/e2e/gate/interceptor-selftest.mjs`
- `tests/e2e/gate/lib/box-witness.mjs`
- `tests/e2e/gate/lib/interceptor.mjs`
- `tests/e2e/gate/lib/playwright.mjs`
- `tests/e2e/gate/lib/policy.mjs`
- `tests/e2e/gate/lib/report.mjs`
- `tests/e2e/gate/lib/simulate.mjs`
- `tests/e2e/gate/page-load-request-inventory.mjs`
- `tests/e2e/gate/parcours/controle-ecriture-non-declaree.mjs`
- `tests/e2e/gate/parcours/decouverte-garage-enphase.mjs`
- `tests/e2e/gate/parcours/reference-bascule-enphase.mjs`
- `tests/e2e/gate/run-gate.mjs`
- `tests/unit/test_story_20_0_gate_policy.node.test.js`
- `tests/unit/test_story_20_0_gate_runner.node.test.js`
- `tests/unit/test_story_20_0_gate_simulate.node.test.js`
- `tests/unit/test_story_20_0_gate_witness.node.test.js`

### Change Log

- 2026-10-04 — Tasks 2 à 6 clôturées ; AC4 précisé sans affaiblir son exigence, artefact des sept exécutions joint, statut `in-progress` → `review`.
