---
status: approved
date: 2026-06-30
project: jeedom2ha
workflow: bmad-correct-course
scope: moderate
trigger: Correct-course pour dashboard Energy dans HA
---

# Sprint Change Proposal — Dashboard Energie HA / capteurs puissance et energie

## 1. Trigger et contexte

Alex veut un suivi energie avance dans Home Assistant : ventiler la consommation maison par gros consommateurs en W et kWh, avec un reste "non identifie", en s'appuyant sur les capteurs de puissance deja presents dans Jeedom, sans casser Jeedom, les entites HA existantes ni les automatismes.

Le besoin revele un ecart entre les epics livres et l'objectif HA Energy :

- `pe-epic-9` a ouvert `sensor` et `binary_sensor`.
- `pe-epic-11` a publie les equipements energie/routage solaire cibles : MSunPV eq553, chauffe-eau eq554, IQ EV eq583, pilotage eq628.
- `pe-epic-12` a livre le streaming runtime Jeedom -> HA.
- Mais les capteurs `sensor` publies ne portent pas encore les metadonnees statistiques HA necessaires au dashboard Energie, et l'auto-decouverte massive des commandes W/kWh reste incomplete.

Constats verifies sur `main` au 2026-06-30 :

- Blocage principal confirme : `DiscoveryPublisher._build_sensor_payload()` publie `device_class` et `unit_of_measurement`, mais jamais `state_class`. Un capteur `power` ne peut donc pas devenir une source statistique long-terme HA Energy.
- Mapping par `generic_type` confirme pour le mono-sensor : `_map_single()` ignore les commandes sans `generic_type`, meme si leur unite est `W`, `Wh` ou `kWh`.
- Fallback par unite existe dans `SensorMapper._derive_sensor_metadata()`, mais seulement dans le chemin multi-sensor.
- Allowlist MSunPV encore presente pour l'eligibilite sans `generic_type` : `MULTI_SENSOR_EQ_TYPES = {"msunpv"}`. Cette limite bloque les commandes W/kWh non taguees hors MSunPV quand l'equipement n'a aucun generic_type.
- Nuance importante par rapport au constat initial : le `main` actuel n'est plus strictement verrouille par `MULTI_DOMAIN_EQ_IDS={554}`. La story 11.3 a remplace cette logique par une detection structurelle multi-entite pour certains cas switch/sensor/binary_sensor. En revanche, cette detection ne couvre pas encore le cas simple "prise commandable + une seule mesure W" : le test de non-regression existant conserve volontairement ce comportement en switch mono-entite.
- Ordre des mappers confirme : `Light -> Cover -> Switch -> Climate -> Alarm -> PresenceSwitch -> BinarySensor -> Sensor -> Button -> Fallback`. Une prise mesureuse reconnue comme `switch` reste donc capturee avant que sa mesure W ne soit exposee, sauf si elle passe par le chemin structurel multi-entite.
- Versions/documentation a recaler : `plugin_info/info.json` indique `0.1`, `discovery/publisher.py` annonce `_SW_VERSION = "0.2.0"`, `main.py` annonce `_VERSION = "0.1.0"`, et le README dit encore que les capteurs `POWER` / `sensor` ne sont pas implementes.

## 2. Impact Analysis

### Epic Impact

Recommandation : creer un nouvel epic produit, par exemple `pe-epic-13 — Energie HA exploitable : statistiques, prises mesureuses et auto-decouverte W/kWh`.

Ce changement ne doit pas etre rattache au `pe-epic-12` historique "mapping configurable" :

- Le cadrage historique `mapping configurable` etait un sujet d'overrides manuels utilisateur, deja signale comme stale et a renumeroter.
- Le besoin actuel est une capacite automatique et systemique : publier les commandes W/kWh detectees ou taguees avec les bonnes metadonnees HA, et exposer les mesures secondaires des prises.
- Les overrides manuels restent le futur sujet configurable ; ils ne doivent pas servir de prerequis a l'objectif energie d'Alex.

Impacts par epic livre :

- `pe-epic-9` : extension additive de la qualite des payloads `sensor`, pas de reouverture de type HA.
- `pe-epic-11` : complete la valeur des capteurs energie deja exposes, sans revenir sur les gates eq553/eq554/eq583/eq628.
- `pe-epic-12` : reutilise le streaming state existant ; ne change pas le contrat "state subset discovery".
- Futur mapping configurable : reste separe. Il pourra ajouter des overrides, pas remplacer l'auto-decouverte W/kWh.

### Artifact Impact

- PRD : ajouter une Feature "Energie HA exploitable" ou etendre Feature 9 avec exigences statistiques HA. Les exigences doivent mentionner `state_class`, detection par unite, et absence de conversion W -> kWh dans le daemon.
- Epics : ajouter `pe-epic-13` et ses stories ; ne pas modifier retroactivement les stories done sauf references de contexte.
- Architecture : documenter la regle de metadonnees HA Energy dans le publisher `sensor`, et la separation "puissance instantanee brute" vs "energie integree cote HA".
- README : retirer les mentions "POWER/sensor non implementes", documenter les capteurs supportes et la limite volontaire : pas de conversion W->kWh dans jeedom2ha.
- Versions : aligner les trois surfaces de version dans une story de release hygiene.

### Technical Impact

Le changement est additif mais touche une surface partagee :

- `resources/daemon/mapping/sensor.py` : metadata power/energy, detection par unite hors multi-sensor, choix `state_class`.
- `resources/daemon/discovery/publisher.py` : publication du champ `state_class` pour les sensors eligibles.
- `resources/daemon/models/topology.py` : eligibilite des commandes info numeric par unite W/Wh/kWh, sans exiger un `generic_type` global.
- `resources/daemon/mapping/registry.py` : exposition de capteurs secondaires pour les prises mesureuses sans changer le `unique_id` du switch primaire.
- Tests/golden corpus : augmentation du nombre d'entites publiees attendues pour les prises mesureuses ; verification anti-regression des `unique_id` historiques.

## 3. Recommended Approach

Approche recommandee : Direct Adjustment via nouvel epic `pe-epic-13`.

Effort estime : moyen. Risque : moyen, principalement a cause de l'augmentation du nombre d'entites sensor publiees et de la necessite de conserver les identifiants existants.

Alternatives ecartees :

- Rollback : non justifie. Les epics 9/11/12 fournissent le socle necessaire.
- MVP review / reduction de scope : non justifie. L'objectif energie est atteignable par stories additives.
- Attendre le mapping configurable : mauvais rattachement. Le besoin courant doit fonctionner automatiquement pour les donnees Jeedom deja presentes.

Sequence proposee :

1. Story 13.1 — HA Energy metadata pour sensors power/energy.
2. Story 13.2 — Auto-decouverte par unite W/Wh/kWh hors MSunPV.
3. Story 13.3 — Capteurs secondaires pour prises mesureuses commandables.
4. Story 13.4 — Documentation, versions et handoff produit/terrain.

## 4. Detailed Change Proposals

### Story 13.1 — `state_class` HA Energy pour sensors power/energy

Objectif : rendre les sensors puissance/energie deja publies eligibles aux statistiques long-terme HA.

Edits precis :

- `resources/daemon/mapping/sensor.py`
  - Etendre les metadata sensor pour porter `state_class` dans `reason_details`.
  - Regle : `device_class == "power"` -> `state_class = "measurement"`.
  - Regle : `device_class == "energy"` avec unite `Wh` ou `kWh` et valeur cumulative Jeedom -> `state_class = "total_increasing"`.
  - Ne pas convertir les valeurs. Conserver la valeur brute et l'unite Jeedom.
- `resources/daemon/discovery/publisher.py`
  - Lire `reason_details["state_class"]`.
  - Ajouter `payload["state_class"]` seulement si non `None`.
  - Ne jamais ajouter `state_class` aux sensors non numeriques ou aux classes incertaines.
- Tests
  - Unit test : capteur `POWER` -> payload `device_class=power`, `unit_of_measurement=W`, `state_class=measurement`.
  - Unit test : capteur `CONSUMPTION` / unite `kWh` -> payload `device_class=energy`, `unit_of_measurement=kWh`, `state_class=total_increasing`.
  - Regression : temperature/humidity gardent leur payload actuel ou recoivent seulement un `state_class` si explicitement decide dans la story ; l'objectif energy ne depend pas d'eux.

Acceptance criteria testables :

- Given une commande Jeedom `POWER` info numeric, When discovery est publie, Then le payload MQTT contient `device_class: "power"` et `state_class: "measurement"`.
- Given une commande energie cumulative en `kWh`, When discovery est publie, Then le payload contient `device_class: "energy"` et `state_class: "total_increasing"`.
- Given Home Assistant apres rescan, Then un capteur power publie apparait dans les statistiques long-terme et peut etre utilise comme source pour une integration Riemann.

### Story 13.2 — Detection par unite W/Wh/kWh pour commandes non taguees

Objectif : publier les commandes de puissance/energie deja presentes dans Jeedom meme sans `generic_type`, quand l'unite suffit a etablir une classe HA fiable.

Edits precis :

- `resources/daemon/mapping/sensor.py`
  - Extraire la logique `_derive_sensor_metadata()` pour l'utiliser en mono-sensor et multi-sensor.
  - Autoriser `_map_single()` a prendre une commande info numeric avec unite connue (`W`, `kW`, `Wh`, `kWh`) meme sans `generic_type`.
  - Ajouter une reason_code explicite, par exemple `sensor_unit_power` / `sensor_unit_energy`, distincte de `sensor_power`.
  - Conserver une seule entite principale en mono-sensor si l'equipement n'a qu'une mesure exploitable.
- `resources/daemon/models/topology.py`
  - Remplacer l'exception "sans generic_type seulement pour MSunPV" par une eligibilite additive : un eqLogic sans generic_type devient eligible s'il porte au moins une commande info numeric avec unite energie fiable.
  - Garder les exclusions Jeedom, plugin et objet prioritaires.
  - Ne pas rendre eligible les unites non fiables (`%`, `H`, texte libre) par ce chemin.
- Tests
  - EqLogic sans generic_type, une commande info numeric `unit="W"` -> eligible + sensor power.
  - EqLogic sans generic_type, une commande info numeric `unit="%"` -> reste non eligible ou fallback existant selon regle actuelle, mais pas `device_class` invente.
  - MSunPV reste couvert et non regresse.

Acceptance criteria testables :

- Given une commande Jeedom info numeric non taguee avec unite `W`, When sync s'execute, Then un `sensor` HA est publie avec `device_class=power`, `unit_of_measurement=W`, `state_class=measurement`.
- Given une commande non taguee avec unite inconnue, Then jeedom2ha ne publie pas de classe power/energy inventee.
- Given les exclusions existantes, Then aucun equipement exclu ne devient eligible par unite.

### Story 13.3 — Mesures secondaires sur prises mesureuses

Objectif : conserver le switch/light/cover primaire existant et publier les mesures W/kWh de la meme prise en sensors secondaires.

Edits precis :

- `resources/daemon/mapping/registry.py`
  - Adapter l'agregation structurelle pour ajouter des `sensor` secondaires quand un mapper primaire actionnable (`switch`, et si applicable `light`/`cover`) reconnait l'equipement et que des commandes info numeric W/Wh/kWh sont disponibles.
  - Ne pas exiger `secondary_count > 1` pour les prises mesureuses : une seule mesure W doit suffire a creer un sensor secondaire.
  - Conserver l'ordre primaire : l'entite actionnable reste `results[0]`.
- `resources/daemon/mapping/sensor.py`
  - Garantir que les sensors secondaires utilisent `ha_unique_id = jeedom2ha_eq_{eq_id}_cmd_{cmd_id}`, `object_id = jeedom2ha_{eq_id}_{cmd_id}`, `node_id = jeedom2ha_{eq_id}_{cmd_id}` et `state_topic = jeedom2ha/{eq_id}/{cmd_id}/state`.
  - Exclure les commandes de readback deja consommees par le switch (`ENERGY_STATE`, `SWITCH_STATE`) pour eviter les doublons.
- `resources/daemon/discovery/publisher.py`
  - Aucun changement structurel attendu si Story 13.1 a ajoute `state_class`.
  - Verifier que le device commun reste `identifiers: ["jeedom2ha_{eq_id}"]`.
- Tests
  - Modifier ou completer le test existant "Prise garage" : `ENERGY_ON/OFF/STATE + Conso W` doit retourner deux mappings : switch primaire historique + sensor secondaire.
  - Regression : `ha_unique_id` du switch reste `jeedom2ha_eq_{eq_id}`.
  - Regression : aucune duplication de la commande readback switch en sensor.

Acceptance criteria testables :

- Given une prise Jeedom commandable avec une mesure `W`, When sync s'execute, Then HA conserve le `switch.jeedom2ha_{eq}` existant et ajoute un `sensor.jeedom2ha_{eq}_{cmd}`.
- Given une automatisation HA existante cible le switch, Then son `entity_id`/`unique_id` historique n'est pas modifie.
- Given le sensor secondaire de puissance, Then il est eligible a l'integration Riemann HA ; la production de kWh reste cote HA, pas dans le daemon.

### Story 13.4 — Documentation, versions et handoff terrain

Objectif : aligner les surfaces produit avec le comportement reel.

Edits precis :

- `README.md`
  - Remplacer "Capteurs numeriques POWER prevus, non implementes" par le perimetre reel : sensors, binary_sensors, state streaming, power/energy metadata.
  - Documenter explicitement : `W` reste une puissance instantanee ; pour obtenir des `kWh`, utiliser l'integration Riemann ou le dashboard Energy HA.
  - Ajouter une note de prudence : jeedom2ha ne modifie pas Jeedom, ne convertit pas les valeurs et ne cree pas d'historique retroactif.
- `plugin_info/info.json`
  - Recaler `pluginVersion` avec la version release cible.
- `resources/daemon/discovery/publisher.py`
  - Recaler `_SW_VERSION`.
- `resources/daemon/main.py`
  - Recaler `_VERSION`.
- `_bmad-output/planning-artifacts/epics-projection-engine.md`
  - Ajouter `pe-epic-13` propose et ses stories.
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
  - Ajouter `pe-epic-13: backlog` apres approbation explicite du SCP.

Acceptance criteria testables :

- Given les trois surfaces de version, Then elles annoncent la meme version release cible ou une convention documentee justifie leur difference.
- Given le README, Then il ne contient plus l'affirmation obsolete "POWER non implemente".
- Given le handoff dev, Then les stories 13.1 a 13.4 sont creables via workflow BMAD `create-story -> dev-story -> code-review`.

## 5. Implementation Handoff

Scope classification : Moderate.

Routage recommande :

- PO/SM : approuver le SCP, creer `pe-epic-13` dans les artefacts BMAD, puis creer Story 13.1 seulement.
- Dev : implementer par stories sequencees, sans sauter `create-story -> dev-story -> code-review`.
- Produit / terrain : valider sur HA que les capteurs power sont visibles comme sources statistiques, puis configurer l'integration Riemann et le dashboard Energie.

Plan de validation terrain minimal :

- Box Jeedom reelle : deploy/restart/sync sans modification de scenarios Jeedom.
- MQTT discovery : verifier au moins un payload `sensor` power avec `state_class=measurement`.
- Home Assistant : verifier que le capteur est visible dans les statistiques long-terme ou exploitable par l'integration Riemann.
- Non-regression : switchs eq554/eq583/eq628 restent non-unknown ; capteurs eq553 restent publies ; aucun `unique_id` primaire historique ne change.

Garde-fous de handoff :

- Pas de conversion W -> kWh dans le daemon.
- Pas de modification Jeedom ni des scenarios.
- Pas de renommage d'entite primaire existante.
- Nettoyage retained discovery a prevoir si un test terrain cree des entites secondaires temporaires, en utilisant les chemins de depublication existants.

## 6. Checklist correct-course

- 1.1 Trigger : [x] besoin dashboard Energie HA, revele apres livraison energie/runtime.
- 1.2 Probleme : [x] limitation technique + nouveau besoin produit d'exploitation statistique HA.
- 1.3 Evidence : [x] code `sensor.py`, `publisher.py`, `topology.py`, `registry.py`, README et versions verifies.
- 2.x Epic impact : [x] nouvel epic recommande, `pe-epic-12` historique non reutilise.
- 3.x Artifact impact : [x] PRD, epics, architecture, README, versions identifies.
- 4.x Path forward : [x] direct adjustment via nouvel epic.
- 5.x SCP components : [x] inclus.
- 6.3 Approval : [x] approuve via Workboard card "Appliquer le Sprint Change Proposal" le 2026-06-30.
- 6.4 sprint-status : [x] `pe-epic-13: backlog` ajoute apres approbation.

## 7. Decision appliquee

Decision appliquee : SCP approuve et `pe-epic-13` cree comme nouvel epic energie HA, distinct du futur mapping configurable.

Premiere action apres approbation : lancer `create-story` pour Story 13.1 uniquement.
