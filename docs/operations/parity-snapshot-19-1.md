# Relevé de parité Story 19.1

Depuis la VM, `scripts/parity-snapshot.sh` relève l’état du démon avec uniquement
GET `/system/diagnostics`, GET `/system/published_scope` et une souscription MQTT.
Aucun `/action/*`, publication, redémarrage ou déploiement. La topologie doit déjà
être disponible dans le démon ; un relevé vide échoue sans déclencher de sync.

## Capture depuis la VM

Prérequis VM : Bash, SSH, jq et Python 3 (bibliothèque standard uniquement).
Pas de `mosquitto_sub` ni de sudo nécessaires sur la VM. L’alias SSH réel est
`jeedom-deploy` (`asahut@192.168.1.21`), avec accès PHP CLI via sudo sur la box.

```bash
scripts/parity-snapshot.sh capture
```

Le chemin par défaut est `/tmp/jeedom2ha-parity-probe-<UTC>.json` (mode **600**,
création exclusive : une preuve existante ne sera pas écrasée). Pour choisir
le libellé et le chemin :

```bash
scripts/parity-snapshot.sh capture --label before --output /tmp/jeedom2ha-parity-before.json
scripts/parity-snapshot.sh capture --label after --output /tmp/jeedom2ha-parity-after.json
scripts/parity-snapshot.sh diff --before /tmp/jeedom2ha-parity-before.json --after /tmp/jeedom2ha-parity-after.json
```

Les deux captures encadrent un changement autorisé séparément ; ce wrapper ne
réalise jamais ce changement. Pour vérifier seulement la chaîne de capture,
comparer le fichier obtenu à lui-même avec `diff`.

## Transport et secrets

Le wrapper réutilise `jeedom2ha_refresh_secret`,
`jeedom2ha_refresh_mqtt_credentials` et `jeedom2ha_mqtt_auth_snippet`, primitives
partagées avec `deploy-to-box.sh` dans `scripts/box-readonly-lib.sh`.
Il lit `localSecret`, `daemonApiPort` et la configuration MQTT par PHP CLI sur
la box. Ne jamais copier le secret manuellement : il reste en mémoire, puis
passe à Python uniquement par l’environnement `JEEDOM2HA_LOCAL_SECRET`.
Les identifiants MQTT transitent dans stdin SSH, jamais dans argv ou les logs.

Le tunnel HTTP local est ouvert puis fermé automatiquement (trap EXIT), avec
un socket de contrôle dédié. Il correspond, pour le port habituel 55080, à :

```bash
ssh -N -L 127.0.0.1:15508:127.0.0.1:55080 jeedom-deploy
```

Ne pas ouvrir ce tunnel manuellement avant le wrapper. Celui-ci obtient le port
réel depuis Jeedom. `JEEDOM2HA_PARITY_LOCAL_PORT` permet de remplacer 15508 s’il
est occupé ; `JEEDOM2HA_PARITY_SSH_TARGET` permet de sélectionner un autre alias.

MQTT est inventorié **sur la box**, sans tunnel MQTT, par `mosquitto_sub -W 2`
avec exactement le mécanisme d’authentification de l’inventaire de déploiement :
répertoire temporaire mode 700, configuration `mosquitto_sub` mode 600,
`XDG_CONFIG_HOME` limité à l’appel, nettoyage par trap EXIT, sans option `-o`.
Seuls ces fichiers temporaires sont écrits sur la box puis supprimés ; aucun
inventaire ni backup n’y est conservé. Le flux de topics est transmis au tool
par un fichier temporaire protégé sur la VM, également supprimé à la sortie.

## Résultats

Une capture réussie retourne `0` et affiche les nombres de décisions et topics.
Une erreur SSH/MQTT est propagée ; un inventaire ou un ensemble de décisions vide
échoue explicitement. Le timeout normal de `mosquitto_sub` (code 27) est accepté,
mais son résultat doit être non vide. Le tool retourne `2` pour une capture ou
donnée invalide ; `diff` retourne `0` pour une parité stricte, `1` pour un écart.
Les champs `i11_candidates`, `explicit_scope_entries` et
`published_scope_exceptions` restent des observations sans correction.
Conserver les captures hors du dépôt : elles décrivent l’installation réelle.
