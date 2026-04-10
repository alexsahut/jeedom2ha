# Contexte de test reel Jeedom - Contrat d'authentification API

## Objet

Capitaliser la verite terrain sur le contrat d'authentification API Jeedom du projet `jeedom2ha`, afin d'eviter de nouvelles regressions de conception sur les stories daemon.

## Etat de verite actuel

### Prouve

- Home Assistant publie bien sur `jeedom2ha/391/set`.
- Le daemon recoit la commande et tente `cmd::execCmd`.
- Les commandes Jeedom `3267` (`LIGHT_ON`) et `3269` (`LIGHT_OFF`) fonctionnent en PHP direct via `cmd->execCmd()`.
- `cmd::execCmd` via `jeeApi.php` avec la cle plugin `config::byKey("api","jeedom2ha")` echoue avec `Vous n'etes pas autorise a effectuer cette action`.
- Le meme `cmd::execCmd` via `jeeApi.php` avec la cle core globale `config::byKey("api")` reussit avec `result: "ok"`.
- Le plugin PHP injecte deja deux cles distinctes au daemon :
  - `--apikey`
  - `--jeedomcoreapikey`
- L'API HTTP locale du daemon utilise `X-Local-Secret` pour `/system/status` et `/action/sync`.
- `event::changes` est deja cable avec la `core API key` dans le code et couvert par tests locaux, puis valide sur box reelle en Story 3.1.

### Probable

- La separation plugin/core des permissions Jeedom peut dependre de la methode et du contexte Jeedom exact ; elle doit donc etre revalidee des qu'une story touche l'authentification ou un nouveau flux JSON-RPC.

### Non demontre

- Le contrat d'authentification exact du callback daemon -> plugin `core/php/jeedom2ha.php`.
- Le caractere universel du resultat `cmd::execCmd -> core API key` au-dela de la box reelle deja testee.
- L'acceptation ou le refus de la `plugin API key` pour toutes les autres methodes `jeeApi.php` non encore testees terrain.

## Contrat projet a retenir

| Flux / methode | Cle a utiliser | Statut projet |
| --- | --- | --- |
| `GET /system/status` | `local secret` | Prouve |
| `POST /action/sync` | `local secret` | Prouve |
| `event::changes` via `/core/api/jeeApi.php` | `core API key` | Prouve |
| `cmd::execCmd` via `/core/api/jeeApi.php` | `core API key` sur la box testee | Prouve sur box testee |

## Regle de verite

- La box reelle prevaut sur les tests locaux, le code local et la documentation officielle lorsqu'il s'agit de permissions effectives.
- Une documentation officielle Jeedom reste utile pour le format d'appel, mais ne suffit pas a figer un contrat d'autorisation pour `jeedom2ha`.
- Une story auth n'est pas "prete" tant que le mini preflight terrain ci-dessous n'a pas ete execute ou explicitement replanifie.

## Note de tracabilite - Story 3.2-bis

- Le protocole terrain 3.2b-A / 3.2b-B / 3.2b-C reste la reference de verification reelle du bootstrap runtime apres restart daemon.
- Ce protocole n'a pas ete execute pour la cloture documentaire de Story 3.2-bis; aucune preuve terrain n'est revendiquee dans cet etat `done`.
- Toute anomalie terrain post-merge sur bootstrap runtime, anti-ghost ou coexistence namespace doit rouvrir Story 3.2-bis ou un follow-up equivalent avant nouvelle cloture.

## Mini protocole de verification terrain

Utiliser une box Jeedom de test et un actionneur jetable. Les exemples ci-dessous reprennent la box deja validee ; adapter `EQ_ID_TEST`, `CMD_ON` et `CMD_OFF` si besoin.

### 0. Variables

```sh
export JEEDOM_ROOT=/var/www/html
export DAEMON_API=http://127.0.0.1:55080
export JEEDOM_RPC=http://127.0.0.1/core/api/jeeApi.php
export EQ_ID_TEST=391
export CMD_ON=3267
export CMD_OFF=3269

export PLUGIN_API_KEY="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; echo jeedom::getApiKey("jeedom2ha");')"
export CORE_API_KEY="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; echo config::byKey("api");')"
export LOCAL_SECRET="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; echo config::byKey("localSecret", "jeedom2ha");')"

# Credentials broker MQTT (extraites de la config mqtt2 / MQTT Manager)
export MQTT_USER="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; $raw = config::byKey("mqtt::password","mqtt2",""); $line = explode("\n",$raw)[0]; if(strpos($line,":")!==false){list($u,$p)=explode(":",$line,2); echo $u;} else {echo $line;}')"
export MQTT_PASS="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; $raw = config::byKey("mqtt::password","mqtt2",""); $line = explode("\n",$raw)[0]; if(strpos($line,":")!==false){list($u,$p)=explode(":",$line,2); echo $p;} else {echo "";}')"
```

### 1. Verifier le demarrage daemon et l'auth locale

```sh
curl -s -o /dev/null -w '%{http_code}\n' "$DAEMON_API/system/status"
curl -sS -H "X-Local-Secret: $LOCAL_SECRET" "$DAEMON_API/system/status" | jq
```

Attendu :
- sans header : `401`
- avec `X-Local-Secret` : JSON avec `"status": "ok"`

### 2. Verifier `/action/sync` avec la vraie topologie Jeedom

```sh
php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; require_once getenv("JEEDOM_ROOT") . "/plugins/jeedom2ha/core/class/jeedom2ha.class.php"; echo json_encode(array("payload" => jeedom2ha::getFullTopology()), JSON_UNESCAPED_SLASHES);' > /tmp/jeedom2ha-topology.json
curl -sS -X POST \
  -H "X-Local-Secret: $LOCAL_SECRET" \
  -H 'Content-Type: application/json' \
  "$DAEMON_API/action/sync" \
  --data-binary @/tmp/jeedom2ha-topology.json | jq
```

Attendu :
- HTTP `200`
- payload de synthese present
- aucun `401 Unauthorized`

### 3. Verifier `event::changes` avec la core API key

```sh
export CURSOR="$(php -r 'printf("%.6f", microtime(true)-10);')"
curl -sS -X POST \
  -H 'Content-Type: application/json' \
  "$JEEDOM_RPC" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":\"event-core\",\"method\":\"event::changes\",\"params\":{\"apikey\":\"$CORE_API_KEY\",\"datetime\":\"$CURSOR\"}}" | jq
```

Attendu :
- pas de message d'autorisation refusee
- retour JSON-RPC exploitable (`result` ou liste d'evenements)

### 4. Verifier `cmd::execCmd` avec les deux cles

```sh
curl -sS -X POST \
  -H 'Content-Type: application/json' \
  "$JEEDOM_RPC" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":\"cmd-plugin\",\"method\":\"cmd::execCmd\",\"params\":{\"apikey\":\"$PLUGIN_API_KEY\",\"id\":$CMD_ON,\"options\":{}}}" | jq

curl -sS -X POST \
  -H 'Content-Type: application/json' \
  "$JEEDOM_RPC" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":\"cmd-core\",\"method\":\"cmd::execCmd\",\"params\":{\"apikey\":\"$CORE_API_KEY\",\"id\":$CMD_ON,\"options\":{}}}" | jq
```

Attendu sur la box deja validee :
- cle plugin : erreur d'autorisation
- cle core : `result: "ok"`

### 5. Si la story touche le flux commande HA -> Jeedom

```sh
mosquitto_pub -t "jeedom2ha/$EQ_ID_TEST/set" -m ON
grep -E '\[SYNC-CMD\]|cmd::execCmd|reason_code=' /var/www/html/log/jeedom2ha_daemon | tail -n 50
```

Attendu :
- le daemon consomme le topic `jeedom2ha/<eq_id>/set`
- le log permet d'identifier la methode appelee, la decision prise et le resultat

### 6. Executer le script PHP de regression startup bootstrap (Story 3.2-bis)

```sh
cd "$JEEDOM_ROOT/plugins/jeedom2ha"
php tests/test_runtime_bootstrap_startup.php
echo $?
```

Attendu :
- sortie `0`
- presence de `All runtime bootstrap assertions passed.`
- aucune ligne `FAIL:`

Verdicts attendus par cas couvert :
- `jeedom2ha::isDaemonMqttReady exists` -> `PASS`
- `jeedom2ha::bootstrapRuntimeAfterDaemonStart exists` -> `PASS`
- `Strict MQTT readiness accepts only the exact connected status` -> `PASS`
- `Strict MQTT readiness rejects disconnected payloads` -> `PASS`
- `Strict MQTT readiness rejects non-connected MQTT states` -> `PASS`
- `Strict MQTT readiness requires global status ok` -> `PASS`
- `Bootstrap succeeds when MQTT becomes ready` -> `PASS`
- `Bootstrap success reason is explicit` -> `PASS`
- `Bootstrap polls /system/status until readiness is observed` -> `PASS`
- `Bootstrap fetches topology exactly once on success` -> `PASS`
- `Bootstrap triggers one sync exactly once per startup path` -> `PASS`
- `Bootstrap reuses the existing topology payload for /action/sync` -> `PASS`
- `Bootstrap skips cleanly when MQTT readiness times out` -> `PASS`
- `Bootstrap timeout reason is explicit` -> `PASS`
- `No topology extraction happens before MQTT readiness` -> `PASS`
- `No sync call happens before MQTT readiness` -> `PASS`
- `Bootstrap fails explicitly when /system/status is unavailable` -> `PASS`
- `Bootstrap surfaces /system/status failure reason` -> `PASS`
- `No topology extraction happens when status fetch fails` -> `PASS`
- `No sync call happens when status fetch fails` -> `PASS`
- `Bootstrap fails explicitly when /action/sync fails` -> `PASS`
- `Bootstrap surfaces /action/sync failure reason` -> `PASS`

### 7. Preflight obligatoire Story 3.2-bis

Relire les secrets actifs :

```sh
export JEEDOM_ROOT=/var/www/html
export DAEMON_API=http://127.0.0.1:55080
export JEEDOM_RPC=http://127.0.0.1/core/api/jeeApi.php
export EQ_ID_TEST=391
export CMD_ON=3267
export CMD_OFF=3269

export PLUGIN_API_KEY="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; echo jeedom::getApiKey("jeedom2ha");')"
export CORE_API_KEY="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; echo config::byKey("api");')"
export LOCAL_SECRET="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; echo config::byKey("localSecret", "jeedom2ha");')"

# Credentials broker MQTT (extraites de la config mqtt2 / MQTT Manager)
export MQTT_USER="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; $raw = config::byKey("mqtt::password","mqtt2",""); $line = explode("\n",$raw)[0]; if(strpos($line,":")!==false){list($u,$p)=explode(":",$line,2); echo $u;} else {echo $line;}')"
export MQTT_PASS="$(php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; $raw = config::byKey("mqtt::password","mqtt2",""); $line = explode("\n",$raw)[0]; if(strpos($line,":")!==false){list($u,$p)=explode(":",$line,2); echo $p;} else {echo "";}')"

printf 'PLUGIN_API_KEY=%s\nCORE_API_KEY=%s\nLOCAL_SECRET=%s\nMQTT_USER=%s\nMQTT_PASS_LEN=%d\n' "$PLUGIN_API_KEY" "$CORE_API_KEY" "$LOCAL_SECRET" "$MQTT_USER" "${#MQTT_PASS}"
```

Verifier `/system/status` :

```sh
curl -s -o /dev/null -w '%{http_code}\n' "$DAEMON_API/system/status"
curl -sS -H "X-Local-Secret: $LOCAL_SECRET" "$DAEMON_API/system/status" | jq
```

Verifier `/action/sync` :

```sh
php -r 'require_once getenv("JEEDOM_ROOT") . "/core/php/core.inc.php"; require_once getenv("JEEDOM_ROOT") . "/plugins/jeedom2ha/core/class/jeedom2ha.class.php"; echo json_encode(array("payload" => jeedom2ha::getFullTopology()), JSON_UNESCAPED_SLASHES);' > /tmp/jeedom2ha-topology.json
curl -sS -X POST \
  -H "X-Local-Secret: $LOCAL_SECRET" \
  -H 'Content-Type: application/json' \
  "$DAEMON_API/action/sync" \
  --data-binary @/tmp/jeedom2ha-topology.json | jq
```

Attendu :
- `/system/status` sans header -> `401`
- `/system/status` avec `X-Local-Secret` -> JSON avec `"status": "ok"`
- `/action/sync` -> HTTP `200`, payload de synthese present, aucun `401`

### 8. Protocole terrain compact Story 3.2-bis

#### 3.2b-A - Happy path apres restart daemon

```sh
cd "$JEEDOM_ROOT"
php -r 'require_once "/var/www/html/core/php/core.inc.php"; jeedom::startDaemon("jeedom2ha");'
until curl -sS -H "X-Local-Secret: $LOCAL_SECRET" "$DAEMON_API/system/status" \
  | jq -e '.status == "ok" and .payload.mqtt.connected == true and .payload.mqtt.state == "connected"' >/dev/null; do
  sleep 1
done
mosquitto_pub -t "jeedom2ha/$EQ_ID_TEST/set" -m ON
grep -E '\[DAEMON\]|\[MQTT\]|\[SYNC\]|\[SYNC-CMD\]|reason_code=' /var/www/html/log/jeedom2ha_daemon | tail -n 100
```

Verdict attendu :
- le log montre l'attente de readiness MQTT puis un bootstrap startup `sync succeeded`
- la commande `jeedom2ha/$EQ_ID_TEST/set` n'est plus bloquee par registre runtime vide
- Jeedom execute la commande cible et HA recoit un comportement coherent avec le retour d'etat habituel

#### 3.2b-B - Anti-ghost apres restart

```sh
php -r 'require_once "/var/www/html/core/php/core.inc.php"; jeedom::startDaemon("jeedom2ha");'
until curl -sS -H "X-Local-Secret: $LOCAL_SECRET" "$DAEMON_API/system/status" \
  | jq -e '.status == "ok" and .payload.mqtt.connected == true and .payload.mqtt.state == "connected"' >/dev/null; do
  sleep 1
done
mosquitto_pub -t "jeedom2ha/999999/set" -m ON
grep -E '\[SYNC-CMD\]|reason_code=' /var/www/html/log/jeedom2ha_daemon | tail -n 50
```

Verdict attendu :
- rejet explicite avec `reason_code=unknown_runtime_entity` ou equivalent de registre runtime non rehydrate pour cette entite
- aucun effet Jeedom
- aucune recreation implicite d'entite

#### 3.2b-C - Coexistence namespace

```sh
mosquitto_sub -v -t '#' -W 10 > /tmp/jeedom2ha-bootstrap-broker.log &
SUB_PID=$!
php -r 'require_once "/var/www/html/core/php/core.inc.php"; jeedom::startDaemon("jeedom2ha");'
wait $SUB_PID || true
grep -Ev '^(jeedom2ha/|homeassistant/)' /tmp/jeedom2ha-bootstrap-broker.log
```

Verdict attendu :
- aucun topic tiers externe aux namespaces attendus `jeedom2ha/` et `homeassistant/` n'est publie, purge ou consomme pendant le bootstrap
- aucune trace de wildcard/global cleanup
- seuls les topics `jeedom2ha/` et les topics discovery Home Assistant deja attendus peuvent apparaitre

## Regles de blocage BMAD

- Si le resultat terrain contredit `architecture.md`, la story doit s'arreter et le contrat documentaire doit etre mis a jour avant toute suite.
- Si seuls les tests locaux sont verts, le sujet auth Jeedom reste **non valide**.
- Toute nouvelle methode `jeeApi.php` introduite dans une story doit etre marquee `non demontree` tant qu'un test reel n'a pas ete capture.

## Script de Déploiement Local vers Box de Test

> **DEV/TEST ONLY** — Ce script n'est **pas** la procédure de release du projet.
> Cycle de distribution canonique : `main → beta → stable → Jeedom Market`.

Le script de référence pour tout déploiement terrain est : **`scripts/deploy-to-box.sh`**

Il remplace toute procédure rsync manuelle, copie SSH ad hoc ou improvisation de déploiement. Ce script est la seule interface de déploiement terrain autorisée pour les agents BMAD.

### Guardrail — Règle absolue

> Pour toute story nécessitant un test terrain sur la box Jeedom réelle, utiliser **exclusivement** `scripts/deploy-to-box.sh`.
> Ne pas improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle.

### Prérequis

- Connexion SSH configurée pour l'utilisateur `asahut` (sudo NOPASSWD requis)
- Variable `JEEDOM_BOX_HOST` définie dans `.env` (voir `.env.example`)
- `jq` installé localement (`brew install jq`)

### Modes d'utilisation

| Mode | Commande | Quand l'utiliser |
|------|----------|-----------------|
| **Dry-run** | `./scripts/deploy-to-box.sh --dry-run` | Vérifier ce qui sera transféré sans rien déployer |
| **Stop + cleanup** | `./scripts/deploy-to-box.sh --stop-daemon-cleanup` | Arrêter le daemon + purger les retained discovery HA sans republier — vérifier que les entités disparaissent proprement de HA |
| **Deploy nominal** | `./scripts/deploy-to-box.sh` | Déployer sans restart ni cleanup (daemon doit être actif) |
| **Deploy + cleanup + restart** | `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` | Cycle complet : deploy → cleanup → restart daemon → readiness MQTT → sync → vérification discovery |
| **Deploy + skip post-deploy** | `./scripts/deploy-to-box.sh --skip-post-deploy` | Déployer sans healthcheck ni sync (daemon non démarré) |

### Cycle complet validé terrain

Le script orchestre dans l'ordre (selon les flags activés) :

1. Pré-checks SSH + sudo
2. Rsync local → staging (`/home/asahut/jeedom2ha-staging/`)
3. Sudo promotion staging → `/var/www/html/plugins/jeedom2ha/` + permissions `www-data`
4. Cleanup retained MQTT discovery (`homeassistant/+/jeedom2ha_*/config`) si `--cleanup-discovery`
5. Restart daemon (`jeedom2ha::deamon_start`) + boucle readiness MQTT (condition terrain 3.2b-A) si `--restart-daemon`
6. Healthcheck `GET /system/status` avec `X-Local-Secret`
7. Build sync body (`jeedom2ha::getFullTopology`)
8. `POST /action/sync`
9. Vérification post-sync des topics discovery (si cleanup actif)

### Distinction distribution canonique vs déploiement local

| Dimension | Distribution canonique | Déploiement local DEV/TEST |
|-----------|----------------------|---------------------------|
| Chemin | `main → beta → stable → Jeedom Market` | `scripts/deploy-to-box.sh` |
| Destination | Jeedom Market (utilisateurs finaux) | Box de test (`asahut@<JEEDOM_BOX_HOST>`) |
| Finalité | Release utilisateur final | Validation terrain d'une story |
| Permanence | Définitive | Éphémère, remplaçable à tout moment |
| Droits requis | Token GitHub Market | SSH `asahut` + sudo NOPASSWD |

## Proposition d'artefact de preflight

Script propose : `scripts/check_jeedom_api_contract.sh`

Responsabilites attendues :
- relire `plugin API key`, `core API key` et `local secret` depuis Jeedom ;
- verifier `/system/status` et `/action/sync` avec et sans `X-Local-Secret` ;
- tester `event::changes` avec la `core API key` ;
- tester `cmd::execCmd` avec `plugin API key` puis `core API key` ;
- produire une matrice courte `methode -> cle testee -> resultat -> verdict` ;
- sortir en erreur si le resultat ne correspond pas au contrat d'architecture en vigueur.

## Template Task 0 — Pre-flight terrain (à injecter dans les stories)

Modèle de première tâche à insérer dans toute story nécessitant un test terrain sur la box Jeedom réelle.

---

**Task 0 — Pre-flight terrain**

> Déployer la branche de travail sur la box de test avant tout test métier.

1. Vérification sans transfert (dry-run) :
   ```sh
   ./scripts/deploy-to-box.sh --dry-run
   ```
2. Choisir le mode selon l'objectif de la story :
   - Pour vérifier que les entités HA disparaissent sans republier :
     ```sh
     ./scripts/deploy-to-box.sh --stop-daemon-cleanup
     ```
   - Pour republier et valider le cycle complet (cas nominal) :
     ```sh
     ./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon
     ```
3. Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

> **Règle** : ne jamais improviser de rsync, copie SSH ou procédure alternative. `scripts/deploy-to-box.sh` est l'unique interface de déploiement terrain DEV/TEST.

---

**Prompt court réutilisable pour agents dev-story :**

```
Avant tout test terrain, utiliser scripts/deploy-to-box.sh (DEV/TEST ONLY — pas la release Market).
Dry-run d'abord, puis choisir :
  - stop-daemon-cleanup : vérifier disparition entités HA sans republier
  - cleanup-discovery + restart-daemon : cycle complet republication et validation
Ne jamais improviser de rsync ou copie SSH manuelle.
```
