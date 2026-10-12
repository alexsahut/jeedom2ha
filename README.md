# Jeedom2HA

**Retrouvez vos équipements Jeedom dans Home Assistant, sans les reconfigurer à la main.**

Jeedom2HA est un plugin Jeedom qui publie vos équipements dans Home Assistant par l'intermédiaire d'un broker MQTT, grâce à la découverte automatique (*MQTT Discovery*). Jeedom reste le moteur qui exécute vos scénarios et vos commandes ; Home Assistant devient une interface supplémentaire pour voir et piloter votre maison.

## À quoi sert-il ?

- Vos équipements Jeedom apparaissent dans Home Assistant comme des appareils natifs, rangés dans les mêmes pièces.
- Les états remontent en continu de Jeedom vers Home Assistant.
- Les lumières (état, luminosité) et les volets (ouvert/fermé, position) remontent leur état réel dès que l'équipement Jeedom a une commande d'information ; sans elle, Home Assistant affiche un état supposé. Détail dans la section « Limites » de la [documentation](docs/fr_FR/index.md#limites--état-réel-des-lumières-et-des-volets).
- Vous pilotez ces équipements depuis Home Assistant, et c'est Jeedom qui exécute l'ordre.
- Pour chaque équipement, le plugin indique s'il sera publié dans Home Assistant et, sinon, pourquoi, avec la piste pour y remédier.
- Vous gardez la main : vous pouvez exclure un équipement ou une pièce, ou forcer le type d'un équipement.

## Prérequis

- Jeedom en version **4.4 ou supérieure**.
- Un système **Debian 11 ou 12**.
- Un **broker MQTT** accessible depuis Jeedom : le plugin MQTT Manager (recommandé) ou un broker externe (Mosquitto, par exemple).
- **Home Assistant** avec l'intégration **MQTT** en service et la découverte automatique (*discovery*) activée.

## Installation en bref

1. Installez le plugin depuis le Market Jeedom.
2. Sur la page du plugin, lancez l'installation des dépendances et attendez la fin de l'opération.
3. Saisissez et sauvegardez la connexion au broker MQTT, puis démarrez (ou redémarrez) le démon.
4. Dans Home Assistant, ouvrez **Paramètres → Appareils et services → MQTT** : vos équipements apparaissent.

## Documentation détaillée

Le guide complet (configuration, lecture de l'écran, causes de non-publication, dépannage) est ici : [docs/fr_FR/index.md](docs/fr_FR/index.md). L'historique des versions est dans le [changelog](docs/fr_FR/changelog.md).

## Un problème, une question ?

Ouvrez un ticket sur la page [Issues](https://github.com/alexsahut/jeedom2ha/issues) du projet, en joignant si possible un extrait du journal `jeedom2ha` (Jeedom → Analyse → Logs).

## Licence

AGPL. Auteur : Alexandre SAHUT.
