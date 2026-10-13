# Installer depuis GitHub (beta)

Cette page décrit l'installation de jeedom2ha **à partir d'une archive GitHub**, sans passer par le Market Jeedom. Elle s'adresse aux bêta-testeurs qui souhaitent essayer le plugin avant (ou en dehors) d'une publication sur le Market.

Pour une installation depuis le Market, voir [Prérequis et installation](index.md#prérequis-et-installation).

---

## Quelle branche télécharger ?

À la date de rédaction de cette page (octobre 2026), c'est la branche **`main`** qui fait référence pour cette installation. La branche `beta` ne deviendra la branche de référence qu'**une fois qu'elle aura été livrée** ; tant que ce n'est pas annoncé, utilisez `main`. Cette page sera alors mise à jour.

---

## Prérequis

- Jeedom en version 4.4 ou supérieure, sur Debian 12.
- Un **broker MQTT** : un Mosquitto local ou un broker déjà en service. Les réglages de connexion sont décrits dans la section [Connexion au broker MQTT](index.md#connexion-au-broker-mqtt) du guide.
- **Home Assistant** avec l'intégration MQTT en service et la découverte automatique (*discovery*) activée.
- Un accès en ligne de commande à la machine Jeedom, avec les droits d'administration (`sudo`).

---

## Installation

### 1. Récupérer l'archive

Téléchargez l'archive de la branche `main` à cette adresse :

`https://github.com/alexsahut/jeedom2ha/archive/refs/heads/main.zip`

### 2. Extraire et placer le plugin

L'archive GitHub contient un dossier nommé **`jeedom2ha-main`**. Il faut le renommer en **`jeedom2ha`** et le placer sous `/var/www/html/plugins/`.

```bash
unzip main.zip
sudo mv jeedom2ha-main /var/www/html/plugins/jeedom2ha
sudo chown -R www-data:www-data /var/www/html/plugins/jeedom2ha
```

Le nom du dossier compte : Jeedom ne reconnaît le plugin que s'il se trouve dans `plugins/jeedom2ha`.

L'archive contient aussi des dossiers de développement (`tests/`, `scripts/`, `_bmad-output/`, `docs/`) qui n'ont aucun effet sur Jeedom : vous pouvez les laisser en place. Un paquet épuré de ces dossiers sera fourni par les releases.

### 3. Activer le plugin

Dans Jeedom : **Plugins → Gestion des plugins → jeedom2ha → Activer**.

### 4. Installer les dépendances

Si l'activation demande d'installer les dépendances, cliquez sur le bouton **« Relancer »** de la zone « Dépendances » et attendez la fin de l'opération (suivie dans le journal `jeedom2ha`).

### 5. Configurer le broker MQTT

Saisissez l'hôte et le port du broker, puis cliquez sur « Sauvegarder » et démarrez (ou redémarrez) le démon. Tous les champs sont décrits dans [Configuration](index.md#configuration).

### 6. Vérifier le démon

- Sur la page du plugin, le démon doit être **« OK »**.
- Le statut du pont `jeedom2ha/bridge/status` doit être publié sur le broker. Le bandeau de santé de la page principale doit alors afficher « Bridge » : « Actif » et « MQTT » : « Connecté ».

---

## Contrôle de réussite

L'installation est réussie lorsque la page du plugin dans Jeedom **liste les équipements découverts** et propose le bouton **« Rescanner la topologie Jeedom »**. Dans Home Assistant, ouvrez ensuite **Paramètres → Appareils et services → MQTT** pour retrouver vos équipements (voir [Première synchronisation](index.md#première-synchronisation)).

---

## Mise à niveau et retour arrière

> Cette procédure est décrite ici ; elle n'a pas fait l'objet d'un test sur une installation réelle à la date de rédaction.

**Avant toute mise à niveau, conservez une copie de l'ancien dossier en dehors de `/var/www/html/plugins/`** (par exemple dans votre dossier personnel), pour que Jeedom ne la prenne pas pour un plugin :

```bash
sudo cp -a /var/www/html/plugins/jeedom2ha ~/jeedom2ha.sauvegarde
```

**Mise à niveau** : retéléchargez l'archive, extrayez-la, puis copiez son contenu **par-dessus** le dossier existant. N'utilisez pas `mv` vers un dossier qui existe déjà : le nouveau dossier se retrouverait imbriqué dans l'ancien et Jeedom continuerait d'exécuter l'ancienne version.

```bash
unzip main.zip
sudo cp -a jeedom2ha-main/. /var/www/html/plugins/jeedom2ha/
sudo chown -R www-data:www-data /var/www/html/plugins/jeedom2ha
```

Relancez ensuite les dépendances si Jeedom le demande, puis redémarrez le démon. Les fichiers de l'ancienne version qui n'existent plus dans la nouvelle ne sont pas supprimés par cette copie ; en cas de doute, repartez d'une installation propre (retour arrière ci-dessous, puis installation initiale).

**Retour arrière** : restaurez l'archive ou le dossier précédemment conservé à la place du dossier `plugins/jeedom2ha`, rétablissez les droits (`chown -R www-data:www-data`) puis redémarrez le démon.

---

## Ce qui n'est pas nécessaire

- **Docker** : il sert uniquement d'outil de démonstration pour le développement. Il n'est pas requis pour une installation réelle.
- **Le plugin Virtuel** : il n'est utilisé que par l'environnement de démonstration. Une installation réelle n'en a pas besoin.

---

## Un problème ?

Consultez la section [Dépannage](index.md#dépannage) du guide, ou ouvrez un ticket sur la page [Issues](https://github.com/alexsahut/jeedom2ha/issues) du projet, en joignant si possible un extrait du journal `jeedom2ha`.
