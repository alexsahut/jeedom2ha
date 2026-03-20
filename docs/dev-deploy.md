# Dev Deploy — utilitaire local de test

> **DEV/TEST ONLY.** Distribution canonique : `main → beta → stable → Jeedom Market`.

Les primitives et les patterns de commandes sont calés sur le contrat terrain documenté dans
`_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.

---

## Prérequis

| Où | Quoi |
|---|---|
| Mac local | `rsync`, `jq` (`brew install jq`) — `jq` n'est **pas** requis sur la box |
| Box Jeedom | Plugin installé depuis le Market au moins une fois |
| Box Jeedom | `mosquitto-clients` pour `--cleanup-discovery` (`apt-get install mosquitto-clients`) |
| Box Jeedom | MQTT Manager (`mqtt2`) installé — source des credentials MQTT |
| SSH | Accès avec un user non-root (ex: `asahut`) + clé SSH sans mot de passe |
| Sudo | `sudo NOPASSWD` configuré pour `JEEDOM_BOX_USER` sur la box |

### Cas selon le user SSH

| Cas | Comportement |
|---|---|
| User `root` direct | Changer `JEEDOM_BOX_USER=root` et `JEEDOM_STAGING_DIR` inutile — mais rare sur Jeedom standard |
| User non-root + sudo NOPASSWD | Cas nominal (ex: `asahut`). Rsync → staging, puis sudo promotion |
| User non-root sans sudo | **Déploiement impossible** vers `/var/www/html/plugins/`. Le script sort avec un message explicite |

Le script vérifie `sudo -n true` au démarrage et échoue proprement si sudo n'est pas disponible.

### Configuration sudo sur la box (une seule fois)
```bash
# Sur la box, en root :
echo "asahut ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers.d/jeedom-dev
chmod 440 /etc/sudoers.d/jeedom-dev
```

## Configuration

```bash
cp .env.example .env
# Renseigner: JEEDOM_BOX_HOST, JEEDOM_BOX_USER, JEEDOM_STAGING_DIR
# JEEDOM_BOX_PATH et JEEDOM_ROOT ont des valeurs par défaut correctes
```

---

## Usage pas à pas

### 1. Simulation
```bash
make deploy-dry
```
Montre les fichiers qui seraient transférés. Aucun accès daemon.

### 2. Déploiement simple
```bash
make deploy
```
1. `rsync` avec filtre → `${JEEDOM_BOX_PATH}/`
2. `chown -R www-data:www-data` + `chmod 755/644` + `chmod +x main.py`
3. `jeedom2ha_refresh_secret` — lit `localSecret` et `daemonApiPort` via PHP CLI sur la box
4. `jeedom2ha_status` — `GET /system/status` avec `X-Local-Secret`
5. `jeedom2ha_build_sync_body` — PHP CLI → `/tmp/jeedom2ha-sync-body.json` sur la box
6. `jeedom2ha_sync` — `POST /action/sync --data-binary @/tmp/jeedom2ha-sync-body.json`

### 3. Nettoyage HA discovery avant test
```bash
make deploy-clean
# ou: ./scripts/deploy-to-box.sh --cleanup-discovery
```
- Lit les credentials MQTT depuis la config `mqtt2` sur la box (source terrain prouvée)
- `mosquitto_sub -W 2` sur `homeassistant/{light,cover,switch}/jeedom2ha_+/config`
- Pour chaque topic trouvé : `mosquitto_pub -r -n` (payload vide retained)
- Ne touche jamais les topics d'autres plugins

**Scope switch** : light et cover sont terrain-validés (Story 3.1 / 3.2-bis). Switch est inclus
par couverture code uniquement — non encore validé sur box réelle.

### 4. Redémarrage daemon + vérification readiness
```bash
make deploy-restart
# ou: ./scripts/deploy-to-box.sh --restart-daemon
```
- `jeedom::startDaemon("jeedom2ha")` via PHP CLI — chemin terrain prouvé (protocole 3.2b-A)
- Lit `localSecret` après le démarrage (généré si absent)
- Boucle `jq -e '.status == "ok" and .payload.mqtt.connected == true and .payload.mqtt.state == "connected"'` jusqu'à readiness ou timeout 60s

### 5. Cycle complet (déploiement frais avec reset HA) — mode nominal
```bash
./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon
```
Ordre d'exécution : cleanup → restart → healthcheck → sync → vérification topics.

### 6. Vérification « HA propre » sans republier
```bash
./scripts/deploy-to-box.sh --stop-daemon-cleanup
```
Arrête explicitement le daemon, attend qu'il soit bien arrêté, puis nettoie les topics retained.
Permet de vérifier visuellement dans HA que les entités jeedom2ha ont disparu, sans republication automatique.

Ordre d'exécution : arrêt daemon → attente arrêt (max 30s) → cleanup MQTT retained.

Pour republier après vérification :
```bash
./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon
```

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `JEEDOM_BOX_HOST` | *(requis)* | IP ou hostname de la box |
| `JEEDOM_BOX_USER` | `asahut` | Utilisateur SSH (non-root avec sudo NOPASSWD) |
| `JEEDOM_BOX_PORT` | `22` | Port SSH |
| `JEEDOM_BOX_PATH` | `/var/www/html/plugins/jeedom2ha` | Doit finir par `/plugins/jeedom2ha` |
| `JEEDOM_STAGING_DIR` | `/home/asahut/jeedom2ha-staging` | Répertoire de staging writable par `JEEDOM_BOX_USER` |
| `JEEDOM_ROOT` | `/var/www/html` | Chemin Jeedom sur la box (override si install non standard) |

---

## Hypothèses terrain non confirmées

| Hypothèse | Risque |
|---|---|
| `sudo php` via SSH lit bien `/var/www/html/core/config/common.config.php` (DB credentials) | Moyen — nécessite sudo fonctionnel |
| `jeedom::startDaemon("jeedom2ha")` via `sudo php` CLI fonctionne (exec fork en background) | Moyen — non testé en SSH CLI |
| `mosquitto_pub`/`sub` disponibles sur la box | Dépend de MQTT Manager |
| Broker MQTT joignable depuis la box (mode local) | Standard, à vérifier si broker externe |

---

## Ce que ce script ne fait pas

- Ne remplace pas le cycle Market (`main → beta → stable`)
- Ne gère pas `pip install` des dépendances Python
- Ne modifie pas la configuration plugin dans Jeedom
