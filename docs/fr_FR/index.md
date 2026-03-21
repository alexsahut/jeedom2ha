# Jeedom2HA — Documentation

**Plugin de pont Jeedom → Home Assistant via MQTT Discovery**

Ce plugin expose automatiquement vos équipements Jeedom comme des entités natives Home Assistant, sans migration ni reconstruction manuelle.

---

## Table des matières

- [Présentation](#présentation)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Première synchronisation](#première-synchronisation)
- [Diagnostic](#diagnostic)
- [Comportement des pièces (suggested_area)](#comportement-des-pièces-suggested_area)
- [Nommage des équipements](#nommage-des-équipements)
- [Troubleshooting](#troubleshooting)
- [Changelog](changelog.md)

---

## Présentation

jeedom2ha fonctionne comme un pont local : le démon Python scrute votre installation Jeedom via l'API JSON-RPC, construit un mapping `generic_type → entité HA`, et publie le résultat vers Home Assistant via MQTT Discovery.

**Jeedom reste le moteur d'exécution.** Home Assistant voit les entités comme des appareils natifs, avec états, disponibilité et suggested_area (depuis vos pièces Jeedom).

### Périmètre V1

| Type | Entité HA | Conditions |
|---|---|---|
| Lumières on/off | `light` | `LIGHT_STATE` + `LIGHT_ON`/`LIGHT_OFF` |
| Lumières dimmables | `light` | + `LIGHT_SLIDER` |
| Lumières RGB | `light` | + `LIGHT_COLOR` |
| Volets / stores | `cover` | `FLAP_STATE` + commandes |
| Prises / switches | `switch` | `ENERGY_STATE` + `ENERGY_ON`/`ENERGY_OFF` |
**Hors périmètre V1 (non encore implémenté) :** capteurs numériques (`sensor`), capteurs binaires (`binary_sensor`), thermostats, scénarios, équipements sans `generic_type`.

> Les capteurs figurent dans le diagnostic avec un statut "type V1 compatible" mais ne sont pas publiés dans cette version.

---

## Prérequis

- Jeedom Core **v4.4.9+** (PHP 8.x)
- Debian **12+** ou Raspberry Pi OS récent
- Python **3.9+**
- Broker MQTT — MQTT Manager (mqtt2, recommandé) ou broker externe (Mosquitto, etc.)
- Home Assistant avec intégration MQTT activée et device discovery actif

---

## Installation

1. Installez le plugin depuis le Market Jeedom ou depuis GitHub (branche `beta`).
2. Sur la page du plugin, cliquez **"Installer les dépendances"**.
3. Attendez la fin de l'installation (suivi dans les logs `jeedom2ha`).
4. Démarrez le démon.

---

## Configuration

Accédez à la configuration via : **Plugins → Jeedom2HA → icône Configuration (roue dentée)**.

### Broker MQTT

Si MQTT Manager est installé et actif, les paramètres broker sont pré-remplis automatiquement. Utilisez **"Tester la connexion"** pour valider.

Sans MQTT Manager :

| Champ | Valeur |
|---|---|
| Hôte MQTT | Adresse IP ou hostname du broker |
| Port | 1883 (standard) ou 8883 (TLS) |
| Utilisateur | Si authentification requise |
| Mot de passe | Si authentification requise |
| TLS | Cocher pour connexion chiffrée |

### Filtrage & Publication

| Option | Description |
|---|---|
| Plugins exclus | Noms de plugins à ne pas publier (ex: `virtual,zwave`) |
| Pièces exclues | IDs numériques des objets Jeedom à exclure |
| Politique de publication | `Sûr + Probable` (recommandé) ou `Sûr uniquement` |

Après modification, cliquez **"Appliquer et Rescanner"** pour propager vers HA.

---

## Première synchronisation

1. Configurez le broker MQTT et testez la connexion.
2. Ajustez les filtres si nécessaire.
3. Cliquez **"Appliquer et Rescanner"**.
4. Dans Home Assistant → **Paramètres → Appareils & Services → MQTT**, vos équipements apparaissent.

> Si des équipements n'apparaissent pas, consultez le **Diagnostic** depuis la page principale du plugin.

> **Après un redémarrage du démon** (sans redémarrage de Jeedom) : les entités redeviennent pilotables automatiquement.
> **Après un redémarrage du broker MQTT** : le comportement dépend de la configuration de persistance du broker. Si les messages retained sont conservés, Home Assistant retrouve les entités sans action. Sinon, relancez un rescan depuis la configuration.

---

## Diagnostic

Depuis la page principale : bouton **"Diagnostic"**.

L'interface affiche pour chaque équipement Jeedom :
- **Statut** : publié / non publié / ambigu
- **Raison** : generic_type manquant, structure incomplète, exclu manuellement…
- **Suggestion** : action corrective proposée

### Logs

**Jeedom → Analyse → Logs → `jeedom2ha`**

Niveaux recommandés :
- `info` : synchronisation, connexion, publication discovery
- `debug` : détail MQTT, mapping équipement par équipement

---

## Comportement des pièces (suggested_area)

Le plugin publie le champ `suggested_area` dans le payload MQTT Discovery à chaque synchronisation. Ce champ correspond à la **pièce Jeedom** (objet parent) de l'équipement.

### Ce que le plugin fait

- Lors de la première publication, `suggested_area` indique à Home Assistant dans quelle pièce placer le device.
- Si vous renommez la pièce Jeedom, le plugin met à jour `suggested_area` dans le payload et journalise le changement (`[LIFECYCLE] area change`).

### Ce que Home Assistant ne fait PAS

Home Assistant utilise `suggested_area` **uniquement à la création** du device. Pour les devices déjà enregistrés, HA **ignore** les changements de `suggested_area` dans les messages discovery suivants. C'est un comportement normal documenté dans la spécification MQTT Discovery de HA.

Concrètement : si vous déplacez un équipement d'une pièce à l'autre dans Jeedom, le device reste dans son ancienne zone dans HA.

### Comment déplacer un device vers sa nouvelle pièce

**Option 1 — Cleanup discovery** (réinitialise l'enregistrement HA)

Exécutez depuis le serveur Jeedom :

```bash
./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon
```

> Cette opération supprime puis recrée les entités HA. Les personnalisations manuelles (icônes, alias) sont perdues.

**Option 2 — Déplacement manuel dans HA**

Dans Home Assistant : **Paramètres → Appareils et services** → trouvez le device → modifiez la zone.

---

## Nommage des équipements

Le plugin détermine le type d'entité HA (`light`, `switch`, `cover`) en combinant le `generic_type` des commandes Jeedom et le **nom de l'équipement**. Certains mots-clés dans le nom peuvent bloquer ou modifier le mapping attendu.

### Logique de priorité

1. Le `generic_type` des commandes Jeedom est le critère principal.
2. Quand le `generic_type` est ambigu (ex. `LIGHT_STATE` utilisé pour une prise), le plugin analyse le nom de l'équipement pour trancher.
3. Si le nom contient un mot-clé contradictoire, l'équipement est marqué **ambiguous** dans le diagnostic.

### Mots-clés par type

**Lumières (`light`)** — mots-clés qui **bloquent** le mapping light :

| Catégorie | Mots-clés |
|---|---|
| Chauffage | `chauffage`, `radiateur`, `thermostat`, `heater`, `chaudiere`, `chaudière`, `poele`, `poêle` |
| Eau | `chauffe-eau`, `eau`, `water`, `cumulus`, `ballon` |
| Piscine | `piscine`, `pool`, `filtration`, `filtre`, `pompe` |
| Prises | `prise`, `plug`, `socket` |
| Sécurité | `fumée`, `smoke`, `incendie`, `feu`, `fire`, `alarme`, `sirene`, `sirène` |
| Volets | `volet`, `store`, `cover`, `blind`, `shutter`, `garage`, `portail` |

**Switches (`switch`)** — mots-clés qui **bloquent** le mapping switch :

| Catégorie | Mots-clés |
|---|---|
| Lumières | `lumière`, `lumiere`, `light`, `lampe`, `ampoule` |
| Volets | `volet`, `store`, `cover`, `blind`, `shutter`, `portail`, `garage` |
| Chauffage | `chauffage`, `radiateur`, `thermostat`, `heater` |
| Sécurité | `fumée`, `smoke`, `alarme`, `sirene` |

**Volets (`cover`)** — mots-clés qui **bloquent** le mapping cover :

| Catégorie | Mots-clés |
|---|---|
| Lumières | `lumière`, `lumiere`, `light`, `lampe`, `ampoule` |
| Chauffage | `chauffage`, `radiateur`, `thermostat`, `heater` |
| Prises | `prise`, `plug`, `socket` |
| Sécurité | `fumée`, `smoke`, `alarme`, `sirene` |

### Piège : le matching par sous-chaîne

Le plugin recherche les mots-clés **à l'intérieur** du nom (matching substring). Un mot-clé présent comme sous-chaîne d'un autre mot provoque un faux positif.

Exemples de noms problématiques :

| Nom de l'équipement | Sous-chaîne détectée | Conséquence |
|---|---|---|
| `lampe bureau (ex-chevet)` | `eau` dans "bur**eau**" | Bloque le mapping light → ambiguous |
| `lampe (ex-chevet)` | `lampe` | Bloque le mapping switch (si `generic_type` ambigu) |

### Recommandations

- Vérifiez le diagnostic après chaque rescan pour repérer les équipements marqués **ambiguous**.
- Évitez les noms contenant involontairement un mot-clé listé ci-dessus.
- En cas d'ambiguïté, renommez l'équipement dans Jeedom puis relancez un rescan.

---

## Troubleshooting

| Symptôme | Cause probable | Action |
|---|---|---|
| Démon ne démarre pas | Dépendances manquantes | Relancer l'installation des dépendances |
| Broker non joignable | Mauvais paramètres | Tester connexion depuis la configuration |
| Équipements absents dans HA | `generic_type` non assigné | Diagnostic → colonne Raison |
| États non mis à jour | Démon stoppé ou broker coupé | Vérifier statut démon + logs |
| Entités dupliquées dans HA | Rescan après changement d'ID | Supprimer orphelins dans HA → rescanner |

---

Pour signaler un problème : [github.com/alexsahut/jeedom2ha/issues](https://github.com/alexsahut/jeedom2ha/issues)
