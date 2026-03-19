# Jeedom2HA

**Projetez votre installation Jeedom dans Home Assistant via MQTT Discovery — sans migration, sans reconstruction manuelle.**

jeedom2ha est un plugin Jeedom avec démon Python qui expose automatiquement vos équipements Jeedom comme des entités natives Home Assistant. Jeedom reste le moteur d'exécution et la source de vérité ; Home Assistant devient la couche d'interface, de visualisation et d'interaction moderne.

---

## Ce que fait le plugin

- **Discovery automatique** : publie vos équipements Jeedom vers Home Assistant via MQTT Discovery (device discovery mode). Home Assistant les intègre sans configuration manuelle.
- **Synchronisation des états en temps réel** : les changements d'état Jeedom (allumage, position volet, état switch…) remontent dans HA en continu, sur le périmètre publié (lumières, volets, prises).
- **Pilotage bidirectionnel** : les commandes HA (allumer une lumière, fermer un volet, activer une prise) sont exécutées dans Jeedom avec retour d'état honnête.
- **Diagnostic intégré** : l'interface explique pourquoi un équipement est publié, non publié, ou ambigu — avec des pistes de remédiation.
- **Filtrage et exclusions** : excluez des plugins entiers, des pièces Jeedom, ou des équipements individuels. Politique de confiance configurable (sûr uniquement / sûr + probable).
- **Auto-détection MQTT Manager** : si le plugin MQTT Manager (mqtt2) est installé, la configuration broker est pré-remplie automatiquement.

## Périmètre V1 supporté

| Type d'équipement | Jeedom `generic_type` | Entité HA |
|---|---|---|
| Lumières on/off | `LIGHT_STATE` + `LIGHT_ON`/`LIGHT_OFF` | `light` |
| Lumières dimmables | + `LIGHT_SLIDER` | `light` (avec brightness) |
| Lumières couleur RGB | + `LIGHT_COLOR` | `light` (avec color) |
| Volets / stores | `FLAP_STATE` + commandes | `cover` |
| Prises / interrupteurs | `ENERGY_STATE` + `ENERGY_ON`/`ENERGY_OFF` | `switch` |
**Ce que le plugin ne fait pas encore :**
- Capteurs numériques (`TEMPERATURE`, `HUMIDITY`, `POWER`…) → `sensor` : prévu, non implémenté
- Capteurs binaires (`DOOR_STATE`, `MOTION_STATE`…) → `binary_sensor` : prévu, non implémenté
- Thermostats / climate
- Scénarios Jeedom → HA
- Équipements sans `generic_type` assigné (non publiés, signalés dans le diagnostic)
- Republication automatique si le broker MQTT est redémarré (les messages retain sont perdus — rescan manuel nécessaire)
- Export de diagnostic

---

## Architecture

```
Jeedom (PHP + UI)
    │  Configuration, démarrage/arrêt daemon, API JSON-RPC
    ▼
Daemon Python (asyncio)
    │  Scraping topologie Jeedom, moteur de mapping generic_type → HA
    │  Synchronisation incrémentale des états (event::changes)
    │  Pilotage Jeedom ← commandes HA
    ▼
Broker MQTT (MQTT Manager ou broker externe)
    │  Topics homeassistant/device/... (MQTT Discovery)
    │  Topics état et commande par entité
    ▼
Home Assistant
    │  Entités natives, availability, suggested_area (depuis les pièces Jeedom)
```

Le mapping repose sur les `generic_type` Jeedom. Un équipement sans `generic_type` n'est pas publié ; le diagnostic explique pourquoi et suggère la correction.

---

## Prérequis

- **Jeedom Core v4.4.9+** (PHP 8.x)
- **Debian 12+** ou Raspberry Pi OS récent
- **Python 3.9+** (installé avec le plugin)
- **Broker MQTT** : MQTT Manager (plugin mqtt2, recommandé) ou broker externe (Mosquitto, etc.)
- **Home Assistant** avec l'intégration MQTT activée et le device discovery activé
- Dépendances Python installées automatiquement : `paho-mqtt`, `jeedomdaemon`

---

## Installation

1. Installer le plugin depuis le Jeedom Market ou depuis GitHub (branche `beta` pour les dernières fonctionnalités).
2. Depuis la page plugin Jeedom, lancer l'installation des dépendances.
3. Une fois les dépendances installées, démarrer le démon.

---

## Configuration

### Accéder à la configuration

Jeedom → Plugins → Jeedom2HA → icône de roue dentée (Configuration).

### Broker MQTT

Si MQTT Manager est installé et actif, la configuration broker est pré-remplie automatiquement au chargement de la page. Vérifiez les paramètres et utilisez **"Tester la connexion"** pour valider.

Sans MQTT Manager, renseignez manuellement :
- **Hôte MQTT** : adresse IP ou hostname de votre broker
- **Port** : 1883 (standard) ou 8883 (TLS)
- **Utilisateur / Mot de passe** : si votre broker exige une authentification
- **TLS** : cocher si votre broker utilise le chiffrement (recommandé hors réseau local)

### Filtrage & Publication

- **Plugins exclus** : noms de plugins séparés par des virgules (`virtual,zwave`) — laissez vide pour tout inclure
- **Pièces exclues** : IDs numériques des objets Jeedom à ne pas publier
- **Politique de publication** :
  - *Sûr + Probable* (recommandé) : publie les équipements bien identifiés et ceux probablement bien typés
  - *Sûr uniquement* : plus restrictif, ne publie que les mappings certains

Cliquez **"Appliquer et Rescanner"** après chaque modification pour propager les changements vers Home Assistant.

---

## Première synchronisation

1. Configurez le broker MQTT et testez la connexion.
2. Ajustez les filtres si nécessaire.
3. Cliquez **"Appliquer et Rescanner"** sur la page de configuration.
4. Ouvrez Home Assistant → Paramètres → Appareils & Services → MQTT.
5. Vos équipements Jeedom apparaissent comme appareils natifs HA, avec les pièces Jeedom comme `suggested_area`.

Si des équipements n'apparaissent pas, consultez le **Diagnostic** depuis la page principale du plugin.

---

## Diagnostic & Troubleshooting

### Interface de diagnostic

Depuis la page principale du plugin, cliquez **"Diagnostic"** pour afficher :
- La liste de vos équipements avec leur statut de publication (publié / non publié / ambigu)
- La raison précise en cas de non-publication (generic_type manquant, structure incomplète, exclu manuellement…)
- Des suggestions de remédiation

### Logs

Les logs du plugin sont disponibles dans Jeedom → Analyse → Logs → `jeedom2ha`.

Niveaux utiles :
- `info` : events de synchronisation, connexion broker, publication discovery
- `debug` : détail des messages MQTT, mapping équipement par équipement

### Problèmes courants

| Symptôme | Cause probable | Action |
|---|---|---|
| Daemon ne démarre pas | Dépendances Python manquantes | Relancer l'installation des dépendances |
| Broker MQTT non joignable | Mauvaise adresse / port / credentials | Tester la connexion depuis la configuration |
| Équipements absents dans HA | `generic_type` non assigné dans Jeedom | Consulter le diagnostic → colonne "Raison" |
| États non mis à jour | Daemon stoppé ou broker coupé | Vérifier statut daemon + logs |
| Entités dupliquées dans HA | Rescan après changement d'ID | Supprimer les entités orphelines dans HA puis rescanner |

---

## Statut du projet & compatibilité

| Dimension | État |
|---|---|
| Jeedom Core | v4.4.9+ (PHP 8.x) |
| Debian | 12+ |
| Python | 3.9+ |
| Licence | AGPL |
| Statut | Beta — fonctionnel sur périmètre V1, en développement actif |
| Auteur | Alexandre SAHUT |

Le plugin est en développement actif. Le mapping des capteurs (sensor / binary_sensor), l'export de diagnostic et la republication automatique après redémarrage broker sont prévus dans les prochaines versions.

> **Note restart** : après un redémarrage du démon jeedom2ha (sans redémarrage de Jeedom), les entités redeviennent pilotables automatiquement. Après un redémarrage du broker MQTT, le comportement dépend de la configuration de persistance du broker : si les messages retained sont conservés, Home Assistant retrouve les entités sans action ; sinon, un rescan manuel depuis la configuration est nécessaire.

---

## Contribuer / Signaler un problème

- Issues GitHub : [github.com/alexsahut/jeedom2ha/issues](https://github.com/alexsahut/jeedom2ha/issues)
- Documentation complète : [docs/fr\_FR/](docs/fr_FR/index.md)
- Changelog : [docs/fr\_FR/changelog.md](docs/fr_FR/changelog.md)
