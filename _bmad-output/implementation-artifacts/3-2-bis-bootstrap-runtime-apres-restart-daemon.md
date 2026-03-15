# Story 3.2-bis: Bootstrap runtime apres restart daemon

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a utilisateur Home Assistant,  
I want que les entites `jeedom2ha` deja publiees redeviennent pilotables automatiquement apres restart daemon,  
so that le pont retrouve un comportement nominal sans necessiter de `/action/sync` manuel.

## Acceptance Criteria

1. **Given** des entites `jeedom2ha` ont deja ete publiees dans HA **When** le daemon redemarre et que les prerequis minimums du pont sont reunis **Then** un bootstrap runtime one-shot rehydrate automatiquement le registre runtime necessaire au gating commande sans action manuelle utilisateur
2. **And** tant que ce bootstrap n'est pas termine ou a echoue explicitement, toute commande HA reste rejetee proprement avec trace runtime exploitable dans les logs
3. **And** une fois le bootstrap termine, une commande valide sur une entite precedemment publiee/vivante s'execute dans Jeedom sans `/action/sync` manuel
4. **And** le bootstrap reutilise les mecanismes existants de topologie/sync et n'introduit ni purge globale broker, ni boucle de resync implicite, ni reactivation d'entite retiree
5. **And** le mecanisme reste strictement borne au startup daemon et n'etend pas le perimetre Epic 5

## Scope Guardrails (non negociable)

- Perimetre strictement borne au **startup runtime bootstrap apres restart daemon**.
- **Ne pas** transformer cette story en moteur de persistance/republication post-reboot global de type Epic 5.
- Gating runtime existant obligatoire: `app["publications"]` + `active_or_alive` restent la source de verite avant toute commande.
- Reutiliser le pipeline existant `getFullTopology()` + `POST /action/sync` si cela suffit; ne pas creer un second chemin de mapping/publication.
- Aucun cache en `data/` ne devient autoritatif dans cette story.
- Aucun rescan periodique, aucune reconciliation avancee, aucune republication sur toute reconnexion MQTT.
- Aucun assouplissement du namespace MQTT: zero interaction hors `jeedom2ha`.
- En cas d'incertitude ou d'echec du bootstrap: comportement safe = rejet explicite + log exploitable, jamais pilotage implicite.

## Tasks / Subtasks

- [x] **Task 1 - Orchestrer un bootstrap runtime one-shot dans le chemin de demarrage existant** (AC: #1, #2, #3, #5)
  - [x] 1.1 Reutiliser en priorite `core/class/jeedom2ha.class.php::deamon_start()` comme point d'orchestration du bootstrap, car ce chemin possede deja le healthcheck daemon, l'init MQTT, `getFullTopology()` et `callDaemon()`.
  - [x] 1.2 Apres healthcheck daemon OK et initiation de `/action/mqtt_connect`, attendre dans une fenetre bornee le signal exact suivant de `GET /system/status` avant de lancer le bootstrap runtime: `status == "ok"`, `payload.mqtt.connected == true` et `payload.mqtt.state == "connected"`.
  - [x] 1.3 Une fois ce signal obtenu, construire la topologie via `jeedom2ha::getFullTopology()` puis appeler **une seule fois** `jeedom2ha::callDaemon('/action/sync', $topology, 'POST', 15)`; le bootstrap doit reutiliser ce chemin PHP existant et donc son enveloppe deja supportee (`action`, `payload`, `request_id`, `timestamp`), sans envoi d'une topologie brute avec un schema alternatif.
  - [x] 1.4 En cas d'expiration de la fenetre de readiness, d'erreur API ou d'echec de sync, journaliser explicitement l'echec/le skip de bootstrap, laisser le daemon demarre, conserver les commandes rejetees par le gating runtime existant, et sortir proprement sans boucle infinie ni tempete de retries.

- [x] **Task 2 - Preserver strictement le gating runtime et le non-scope Epic 5** (AC: #2, #4, #5)
  - [x] 2.1 Ne jamais autoriser une commande tant que le registre runtime actif n'est pas rehydrate; le bootstrap ne doit pas contourner `CommandSynchronizer`.
  - [x] 2.2 Si un marqueur runtime minimal est ajoute pour distinguer "bootstrap pending/failed" de "entite vraiment inconnue", le garder local au startup et purement diagnostique.
  - [x] 2.3 Ne pas ajouter de persistance de session/cache autoritative en `data/`.
  - [x] 2.4 Ne pas etendre le comportement aux reconnexions generales broker/HA/Jeedom, ni a la republication lifecycle complete.

- [x] **Task 3 - Reutiliser le pipeline topologie/sync existant sans le dupliquer** (AC: #1, #3, #4)
  - [x] 3.1 S'appuyer sur `jeedom2ha::getFullTopology()` pour la source de verite Jeedom et sur le handler existant `/action/sync` pour reconstruire `app["mappings"]` et `app["publications"]`.
  - [x] 3.2 Conserver le contrat d'enveloppe PHP -> daemon (`action`, `payload`, `request_id`, `timestamp`) et l'auth locale `X-Local-Secret`.
  - [x] 3.3 Preserver l'idempotence au niveau startup: pas de double sync concurrent pour un meme redemarrage.
  - [x] 3.4 Preserver les mecanismes existants de cleanup exact discovery et l'absence totale de wildcard/purge globale broker.

- [x] **Task 4 - Ajouter une couverture automatisee locale ciblee** (AC: #1, #2, #4, #5)
  - [x] 4.1 Ajouter un test de regression sur la sequence de startup choisie, au plus pres du point d'orchestration reel.
  - [x] 4.2 Si l'orchestration reste en PHP, preferer extraire la logique dans un helper testable et ajouter un script/regression cible dans `tests/` a cote des checks PHP existants, plutot que dupliquer la logique ailleurs juste pour tester.
  - [x] 4.3 Ajouter/etendre les tests autour de la readiness MQTT (`/system/status`) si cette readiness conditionne l'appel de bootstrap.
  - [x] 4.4 Verifier qu'aucun bootstrap ne rend une entite commandable tant que `app["publications"]` n'est pas effectivement rehydrate.
  - [x] 4.5 Jouer les non-regressions sur les suites deja sensibles au runtime et au lifecycle.

- [ ] **Task 5 - Executer les tests reels minimum obligatoires** (AC: #1, #2, #3, #4, #5)
  - [ ] 5.1 Test reel 3.2b-A: restart daemon, sans `/action/sync` manuel, puis commande HA valide sur `eq_id=391` -> execution Jeedom + confirmation coherente.
  - [ ] 5.2 Test reel 3.2b-B: restart daemon puis commande sur entite retiree/non publiee -> rejet propre + aucun effet Jeedom.
  - [ ] 5.3 Test reel 3.2b-C: coexistence autre publisher MQTT pendant bootstrap -> aucun topic hors namespace `jeedom2ha` touche.
  - [ ] 5.4 Capturer pour chaque test la preuve standard complete: preconditions, redemarrage, observation `/system/status`, commande injectee, logs runtime, observation broker, observation Jeedom/HA, verdict.

## Plan de tests reels minimum (obligatoire)

- [ ] **Test reel 3.2b-A (happy path apres restart):**
  - [ ] redemarrer le daemon via le chemin normal Jeedom
  - [ ] ne pas lancer `/action/sync` manuellement
  - [ ] verifier que `/system/status` retourne `status == "ok"`, `payload.mqtt.connected == true` et `payload.mqtt.state == "connected"`
  - [ ] publier une commande sur `jeedom2ha/391/set`
  - [ ] verifier execution Jeedom + confirmation coherente

- [ ] **Test reel 3.2b-B (anti-ghost apres restart):**
  - [ ] redemarrer le daemon
  - [ ] tester une entite retiree/non publiee
  - [ ] verifier rejet propre + zero effet Jeedom

- [ ] **Test reel 3.2b-C (coexistence namespace):**
  - [ ] maintenir au moins un autre publisher MQTT actif sur le broker
  - [ ] redemarrer le daemon puis laisser le bootstrap se produire
  - [ ] verifier qu'aucun topic externe n'est publie, purge ou consomme par `jeedom2ha`

- [ ] **Contexte terrain obligatoire:**
  - [ ] relire `plugin API key`, `core API key` et `local secret` depuis la box reelle
  - [ ] verifier `/system/status` et `/action/sync` avec `X-Local-Secret`
  - [ ] conserver la box reelle comme source de verite si le comportement contredit le code local
  - [ ] archiver les extraits logs `[DAEMON]`, `[MQTT]`, `[SYNC]`, `[SYNC-CMD]` utiles

## Risques / Pieges a eviter

- Lancer le bootstrap avant que MQTT soit vraiment connecte, ce qui ferait echouer la publication discovery puis laisserait `active_or_alive=false`.
- Dupliquer la logique de topologie/mapping au lieu de reutiliser `getFullTopology()` + `/action/sync`.
- Introduire un retry infini au demarrage ou sur chaque reconnect MQTT.
- Basculer involontairement vers une persistance/republication avancee de type Epic 5.
- Rehabiliter des ghost entities parce qu'un bootstrap contourne le registre runtime courant.
- Masquer un echec de bootstrap par un fallback silencieux.

## Dev Notes

### Story Foundation

- Cette story vient du follow-up approuve dans `_bmad-output/planning-artifacts/sprint-change-proposal-2026-03-15-startup-runtime-bootstrap-follow-up.md`.
- Le probleme prouve n'est pas le flux commande/auth, mais l'absence de rehydratation du registre runtime apres restart daemon.
- Le positionnement produit recommande est **avant Story 3.3**, sans reouvrir Story 3.2 et sans basculer en Epic 5.

### Contexte code existant a reutiliser

- `core/class/jeedom2ha.class.php`
  - `deamon_start()` orchestre deja le demarrage daemon + l'init MQTT.
  - `callDaemon()` gere deja l'auth locale, l'enveloppe POST et la politique de retry.
  - `getFullTopology()` fournit deja la topologie complete Jeedom en lecture seule.
- `core/ajax/jeedom2ha.ajax.php`
  - `scanTopology` fournit la reference du chemin manuel actuel: `getFullTopology()` puis `callDaemon('/action/sync', ...)`.
- `resources/daemon/transport/http_server.py`
  - `/action/sync` reconstruit `app["mappings"]` et `app["publications"]`.
  - `create_app()` initialise ces registres vides au demarrage.
- `resources/daemon/sync/command.py`
  - le gating runtime actuel est correct et doit rester la frontiere obligatoire.
- `resources/daemon/main.py`
  - initialise `CommandSynchronizer`, `StateSynchronizer` et le serveur HTTP, mais ne rehydrate pas le runtime par lui-meme.
- `resources/daemon/transport/mqtt_client.py`
  - `connect_async()` est non bloquant; il ne faut donc pas supposer que MQTT est pret juste apres `/action/mqtt_connect`.
  - Pour cette story, "MQTT pret" signifie strictement le retour `GET /system/status` avec `status == "ok"`, `payload.mqtt.connected == true` et `payload.mqtt.state == "connected"`.

### Implementation recommandee (chemin prefere)

**Chemin prefere pour eviter les erreurs de conception:**

1. garder l'orchestration de bootstrap dans `jeedom2ha::deamon_start()`;
2. reutiliser `/system/status` pour attendre le signal exact `status == "ok"`, `payload.mqtt.connected == true`, `payload.mqtt.state == "connected"`;
3. une fois ce signal obtenu, reutiliser `jeedom2ha::getFullTopology()` puis `jeedom2ha::callDaemon('/action/sync', $topology, 'POST', 15)` et uniquement ce chemin PHP enveloppe deja supporte;
4. journaliser le resultat (`success`, `skipped`, `failed`) et sortir.

**Pourquoi ce chemin est prefere:**

- il reutilise le chemin manuel deja prouve en production;
- il ne demande ni nouveau callback daemon -> PHP, ni nouveau contrat JSON-RPC Jeedom;
- il limite le changement a l'orchestration startup, donc au vrai perimetre du bug;
- il laisse intacte la source de verite runtime cote daemon.

### Contrat bootstrap startup a respecter

- Le bootstrap vise uniquement le **restart daemon**.
- Il doit etre **one-shot** par cycle de demarrage.
- Il doit etre **borne dans le temps**: pas d'attente infinie de MQTT, pas de retry tempete.
- Il doit etre **idempotent**: deux declenchements concurrents du meme startup sont interdits.
- Il ne doit pas relaxer les rejets commande avant rehydratation effective.
- Le bootstrap startup doit reutiliser le chemin PHP existant `jeedom2ha::callDaemon('/action/sync', $topology, 'POST', 15)`; il ne doit pas fabriquer un autre contrat de requete pour `/action/sync`.
- En cas d'echec de bootstrap, le daemon reste demarre du point de vue process/healthcheck, mais le runtime ne doit pas etre considere comme nominal: les commandes restent rejetees tant qu'un bootstrap ou un `/action/sync` ulterieur n'a pas effectivement rehydrate `app["publications"]`.
- Interdiction d'emettre un signal implicite de "bridge nominal" ou de completion bootstrap si la sync de startup n'a pas effectivement reussi.

### Architecture Compliance

- `event::changes` reste reserve aux etats incrementaux; les changements de topologie exigent toujours un rescan/reconciliation.
- Le cache runtime sous `data/` reste technique et non autoritatif; Jeedom reste la source de verite pour la topologie.
- Les erreurs d'auth, sync et transport doivent rester explicites, structurees et loggees.
- En cas d'incoherence startup/auth/cache, preferer un echec explicite a une recuperation implicite mensongere.
- Regle de dernier recours: publier moins mais correctement.

### Exigences techniques et garde-fous de dev

- Si vous avez besoin d'un marqueur "bootstrap pending/failed", gardez-le local au startup et ne l'etendez pas a un nouveau modele de disponibilite.
- Ne changez pas la definition "autorise au pilotage" de Story 3.2.
- Ne faites aucune supposition nouvelle sur les permissions Jeedom: la `core API key` reste le contrat prouve pour `event::changes` et `cmd::execCmd` sur la box testee.
- Ne creez pas de nouvel endpoint daemon si le couple `/system/status` + `/action/sync` suffit.
- Ne dupliquez pas la topologie Jeedom dans un autre payload/schema local.
- Ne traitez jamais un echec de bootstrap comme un succes degrade: daemon vivant != runtime commande nominal.

### File Structure Requirements

- Changement principal attendu: `core/class/jeedom2ha.class.php`.
- Changements daemon eventuels uniquement si necessaires pour une trace runtime plus explicite:
  - `resources/daemon/main.py`
  - `resources/daemon/sync/command.py`
  - `resources/daemon/transport/http_server.py`
- Cibles de tests probables:
  - `tests/unit/test_daemon_startup.py`
  - `tests/unit/test_mqtt_bridge.py`
  - `tests/unit/test_http_server.py`
  - `resources/daemon/tests/unit/test_command_sync.py`
  - `resources/daemon/tests/unit/test_state_sync_lifecycle.py`
  - eventuellement un script/regression PHP sous `tests/` si la logique startup PHP est factorisee.

### Testing Requirements

- Priorite aux tests de non-regression sur le runtime gating et la sequence de startup.
- Si l'implementation reste cote PHP, ne deplacez pas artificiellement la logique dans Python uniquement pour beneficier d'un test plus facile.
- Suites locales minimales a viser apres implementation:
  - `python3 -m pytest -q tests/unit/test_daemon_startup.py tests/unit/test_mqtt_bridge.py tests/unit/test_http_server.py`
  - `python3 -m pytest -q resources/daemon/tests/unit/test_command_sync.py resources/daemon/tests/unit/test_state_sync_lifecycle.py`
  - `python3 -m pytest -q resources/daemon/tests/integration/test_command_sync_coexistence.py resources/daemon/tests/integration/test_state_sync_cleanup_runtime_flow.py`
- Si un check PHP dedie est ajoute, documenter clairement comment l'executer et quel verdict en attendre.

### Previous Story Intelligence (Story 3.2 + Story 3.1)

- Story 3.2 a valide le gating runtime commande; ce n'est **pas** la piece a assouplir.
- Story 3.1 a etabli que le registre runtime enrichi (`state_topic`, `active_or_alive`) est la source de verite pour les flux incrementaux.
- Le bug observe apres restart prouve que ce registre est vide au demarrage jusqu'a `/action/sync`.
- Les blocages terrain deja resolus sur auth Jeedom (`cmd::execCmd` -> `core API key`) doivent rester intacts.
- Les entites en echec discovery doivent rester non publiees/non vivantes; le bootstrap ne doit pas renverser ce garde-fou.

### Git Intelligence Summary

- Le pattern recent du repo reste incremental: modifications ciblees des composants de transport/orchestration, renforcement des tests locaux, puis mise a jour des artefacts BMAD.
- Pour cette story, eviter une "grande refonte lifecycle"; preferer un changement chirurgical du chemin de demarrage et des preuves associees.

### Latest Technical Information (veille ciblee)

- La documentation officielle Home Assistant continue de distinguer les commandes via `command_topic`, `brightness_command_topic` et `set_position_topic`; cette story ne doit introduire aucun nouveau schema de topics pendant le bootstrap.
- Les docs MQTT Home Assistant confirment aussi que l'etat/availability depend des topics et du retained existants; le bootstrap startup doit donc rester compatible avec la discovery deja publiee, pas la redefinition.
- La page officielle PyPI `paho-mqtt` rappelle deux points importants pour cette story:
  - la ligne 2.x a introduit un changement de callbacks;
  - quand le client est redemarre, la session n'est pas persistee en memoire du client recree.
- Consequence pratique: ne pas essayer de "deduire" le runtime actif a partir d'une pseudo session MQTT survivee au restart process; il faut rehydrater proprement le registre runtime cote application.
- Aucune mise a jour de dependance n'est requise pour cette story; conserver la compatibilite actuelle `paho-mqtt` deja geree dans le code.

### Project Structure Notes

- Aucun changement UX obligatoire: pas de nouveau bouton, pas de nouveau parcours utilisateur.
- Le bug est de type orchestration startup/runtime, pas de type diagnostic UX.
- Si vous ajoutez des logs de bootstrap, gardez-les coherents avec les prefixes existants (`[DAEMON]`, `[MQTT]`, `[SYNC]`, `[API]`) et sans fuite de secrets.
- Ne touchez pas a `core/php/jeedom2ha.php` sauf besoin prouve; ce callback n'est pas le bon point d'entree du correctif minimal.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 3: Synchronisation & Pilotage]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2: Pilotage HA -> Jeedom avec confirmation honnete d'etat]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2-bis: Bootstrap runtime apres restart daemon]
- [Source: _bmad-output/planning-artifacts/prd.md#Commande & Retour d'Etat]
- [Source: _bmad-output/planning-artifacts/prd.md#Cycle de Vie des Entites]
- [Source: _bmad-output/planning-artifacts/prd.md#Exigences Non-Fonctionnelles]
- [Source: _bmad-output/planning-artifacts/architecture.md#2. Format Patterns & Internal API Contracts (PHP ↔ Daemon)]
- [Source: _bmad-output/planning-artifacts/architecture.md#4. Process Patterns, Fallbacks & State Safety]
- [Source: _bmad-output/planning-artifacts/architecture.md#6. Lifecycle Consistency Rules]
- [Source: _bmad-output/project-context.md#Code Quality & Style Rules]
- [Source: _bmad-output/project-context.md#Critical Don't-Miss Rules]
- [Source: _bmad-output/implementation-artifacts/3-2-pilotage-ha-jeedom-avec-confirmation-honnete-detat.md]
- [Source: _bmad-output/implementation-artifacts/3-1-synchronisation-incrementale-des-etats-jeedom-ha.md]
- [Source: _bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-03-15-startup-runtime-bootstrap-follow-up.md]
- [Source: core/class/jeedom2ha.class.php]
- [Source: core/ajax/jeedom2ha.ajax.php]
- [Source: resources/daemon/main.py]
- [Source: resources/daemon/transport/http_server.py]
- [Source: resources/daemon/sync/command.py]
- [Source: tests/unit/test_daemon_startup.py]
- [Source: tests/unit/test_mqtt_bridge.py]
- [Source: tests/unit/test_http_server.py]
- [Source: https://www.home-assistant.io/integrations/light.mqtt/]
- [Source: https://www.home-assistant.io/integrations/cover.mqtt/]
- [Source: https://www.home-assistant.io/integrations/switch.mqtt/]
- [Source: https://pypi.org/project/paho-mqtt/]

## Dev Agent Record

### Agent Model Used

Codex GPT-5 (create-story workflow)

### Debug Log References

- Story creee depuis la Sprint Change Proposal approuvee du 2026-03-15.
- Positionnement conserve entre Story 3.2 et Story 3.3.
- Perimetre volontairement borne au startup bootstrap runtime; aucune extension Epic 5 n'a ete introduite dans cette story.
- Helper PHP `bootstrapRuntimeAfterDaemonStart()` ajoute dans `core/class/jeedom2ha.class.php` et branche uniquement depuis `deamon_start()` apres succes de `/action/mqtt_connect`.
- Readiness MQTT figee en helper `isDaemonMqttReady()` avec la triple condition `status == ok`, `payload.mqtt.connected == true`, `payload.mqtt.state == connected`.
- Regression locale ajoutee dans `tests/test_runtime_bootstrap_startup.php`; execution impossible ici faute de binaire PHP disponible (`php`, `php-cgi`, `php-fpm` absents).
- Packaging de validation ajoute sans changer le scope: commandes exactes d'execution du script PHP sur box reelle, verdicts attendus par assertion, preflight obligatoire et protocole terrain compact 3.2b-A/B/C documentes dans `jeedom2ha-test-context-jeedom-reel.md`.
- Non-regressions Python executees:
  - `python3 -m pytest -q tests/unit/test_daemon_startup.py tests/unit/test_mqtt_bridge.py tests/unit/test_http_server.py` -> `59 passed`
  - `python3 -m pytest -q resources/daemon/tests/unit/test_command_sync.py resources/daemon/tests/unit/test_state_sync_lifecycle.py` -> `19 passed`
  - `python3 -m pytest -q resources/daemon/tests/integration/test_command_sync_coexistence.py resources/daemon/tests/integration/test_state_sync_cleanup_runtime_flow.py` -> `3 passed`

### Completion Notes List

- Story de follow-up creee pour combler le trou de rehydratation runtime apres restart daemon.
- Le chemin recommande privilegie la reutilisation de `getFullTopology()` + `/action/sync` dans le startup PHP existant.
- Les garde-fous de Story 3.2 sont explicitement conserves.
- Les tests reels minimum approuves ont ete integres tels quels.
- Le bootstrap startup reste one-shot et strictement borne au chemin `deamon_start()` deja existant; aucun endpoint, schema ou moteur parallele n'a ete introduit.
- Le daemon attend explicitement le retour `/system/status` compatible avec la definition figee de "MQTT pret", puis relance une seule sync via `jeedom2ha::callDaemon('/action/sync', $topology, 'POST', 15)`.
- En cas de timeout readiness, d'erreur `/system/status` ou d'echec `/action/sync`, le daemon reste demarre mais journalise un resultat `skipped`/`failed`; aucune rehydratation implicite ni assouplissement du gating runtime n'est ajoute.
- Le gating runtime Python reste la source de verite: un test unitaire complete `CommandSynchronizer` pour confirmer qu'une commande est toujours rejetee tant que `app["publications"]` est vide.
- Validation locale automatisee disponible pour le runtime gating et les non-regressions Python; le script PHP cible de bootstrap a ete ajoute mais n'a pas pu etre execute sur cette machine faute d'interpreteur PHP.
- Le script PHP de regression est maintenant documente pour execution directe sur box reelle (`cd /var/www/html/plugins/jeedom2ha && php tests/test_runtime_bootstrap_startup.php`) avec verdict global attendu `exit 0`, `All runtime bootstrap assertions passed.` et zero ligne `FAIL:`.
- Le contexte de test reel centralise maintenant les verdicts attendus de chaque assertion du script et un protocole terrain compact, copiable, pour 3.2b-A, 3.2b-B, 3.2b-C sans elargir le perimetre au-dela du bootstrap runtime apres restart daemon.
- Les tests reels 3.2b-A/B/C et le preflight box reelle restent non executes pour cette cloture; la story est closee en `done` par decision produit/projet avec risque accepte et sans revendiquer de preuve terrain.

### File List

- `_bmad-output/implementation-artifacts/3-2-bis-bootstrap-runtime-apres-restart-daemon.md`
- `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `core/class/jeedom2ha.class.php`
- `resources/daemon/tests/unit/test_command_sync.py`
- `tests/test_runtime_bootstrap_startup.php`

### Change Log

- 2026-03-15: Story 3.2-bis creee en `ready-for-dev` avec contexte complet, garde-fous de scope et protocole terrain obligatoire.
- 2026-03-15: Implémentation locale du bootstrap runtime startup bornee a `deamon_start()` avec attente stricte de readiness MQTT, rehydratation one-shot via `getFullTopology()` + `callDaemon('/action/sync', ..., 'POST', 15)` et logs explicites sur succes/skip/echec.
- 2026-03-15: Ajout de la couverture locale ciblee (`tests/test_runtime_bootstrap_startup.php` + test runtime gating dans `resources/daemon/tests/unit/test_command_sync.py`) et execution des suites Python startup/runtime/lifecycle (`59 + 19 + 3` tests verts).
- 2026-03-15: Packaging de validation complete sans changement de scope: chemin d'execution sur box reelle du script PHP, verdicts attendus par cas, preflight secrets/status/sync et protocole terrain compact 3.2b-A/B/C documentes dans le contexte de test reel.
- 2026-03-15: Cloture documentaire en `done` par decision produit/projet pour preparation du merge; validation terrain 3.2b-A/B/C differee et non executee, risque accepte, protocole terrain conserve comme reference de reouverture.

## Decision de cloture

### Decision de cloture

- Story `3.2-bis` closee en `done` par decision produit/projet pour cette iteration.
- La validation terrain 3.2b-A / 3.2b-B / 3.2b-C est differee et non executee; aucune preuve terrain n'est revendiquee dans cette cloture.

### Risques acceptes

- Le bootstrap runtime apres restart daemon n'est pas prouve sur box reelle dans cet etat documentaire.
- Un ecart reste possible entre la couverture locale automatisee et le comportement reel Jeedom / MQTT / Home Assistant apres restart daemon.

### Ce qui n'a PAS ete prouve

- Qu'une entite deja publiee redevient pilotable apres restart daemon sans `/action/sync` manuel sur box reelle.
- Que le rejet anti-ghost apres restart est correct sur box reelle.
- Que la coexistence namespace reste propre avec un autre publisher MQTT pendant le bootstrap reel.

### Impact attendu si regression

- Les commandes HA peuvent rester rejetees apres restart daemon tant qu'un `/action/sync` manuel n'a pas ete relance.
- Une regression terrain peut se traduire par un bootstrap incomplet, un rejet commande inattendu ou un incident de coexistence namespace.

### Conditions de reouverture

- Toute anomalie terrain post-merge sur bootstrap runtime, anti-ghost ou coexistence namespace.
- Toute execution ulterieure du protocole 3.2b-A / 3.2b-B / 3.2b-C qui contredit les AC ou le comportement attendu.
- Toute divergence constatee entre les logs runtime, le comportement Jeedom / HA et le contrat documentaire de cette story.
