# pe-epic-10 — Préfixe de gel du périmètre Homebridge → HA visé

Date: 2026-06-08
Story: 10.0
Status: done
Source terrain: `homebridge-homekit-vs-ha-delta-2026-06-07.md` (transmis par ClawBox depuis audits 2026-05-18/29/30 et 2026-06-06 — pas de nouveau scan)
Autorité technique HA: `ha-projection-reference.md`
Cadrage sequencing: `sprint-change-proposal-2026-06-07.md` §4.2 et §4.4

---

## Lecture préalable

Cet artefact fige la base de preuve exploitable par toutes les stories `pe-epic-10`. Il ne modifie aucun code, aucun `PRODUCT_SCOPE`, aucun mapper ni publisher. Homebridge sert ici uniquement à dire **quoi couvrir en premier** ; `ha-projection-reference.md` reste la source-of-truth des contraintes HA pour toute ouverture réelle.

Baseline terrain Homebridge : **119 accessories OK** publiés côté HomeKit après cleanup (plateformes annexes exclues), dont **5 scénarios** exposés comme switches HomeKit.

---

## Matrice canonique

| Famille Homebridge | Exemple représentatif | Generic type Jeedom | Composant HA cible | Statut moteur | Source de preuve |
|---|---|---|---|---|---|
| Éclairage | `buffet ikea`, `Spots salon`, `Neons`, `veilleuse` | `Lumière` / Info binaire + Action on/off | `light` | **déjà couvert** (pre-pe-epic-7) | homebridge-homekit-vs-ha-delta §Families Covered › light |
| Volets / stores / motorisations | `Volets`, `store banne`, `store pergola`, `pergola` | `Volet` / Action ouvrir-fermer-stop | `cover` | **déjà couvert** (pre-pe-epic-7) | homebridge-homekit-vs-ha-delta §Families Covered › cover |
| Prises et interrupteurs simples | `prise bureau`, `prise imac salon`, `sèche-serviettes` | `Prise` / Info binaire + Action on/off | `switch` | **déjà couvert** (pre-pe-epic-7) | homebridge-homekit-vs-ha-delta §Families Covered › switch |
| Mesures et télémétrie | `Température RDC`, `Température exterieur`, `Analyse eau piscine`, `Rosée et givre` | `Température` / `Humidité` / Info numérique | `sensor` | **déjà couvert** (pe-epic-9 Story 9.1) | homebridge-homekit-vs-ha-delta §Families Covered › sensor ; ha-projection-reference.md §sensor |
| Ouvertures et états binaires | `Fenêtre Arthur`, `baie gauche/droite cuisine`, `Porte entrée`, `Alerte vent` | `Porte` / `Fenêtre` / Info binaire présence/ouverture | `binary_sensor` | **déjà couvert** (pe-epic-9 Story 9.2) | homebridge-homekit-vs-ha-delta §Families Covered › binary_sensor ; ha-projection-reference.md §binary_sensor |
| Scénarios HomeKit (5 switchs historiques) | `Tout eteindre`, `ambiance cinema`, `ambiance coucher`, `Ambiance lumineuse`, `Lumieres terrasse` | Scénario Jeedom / Action déclenchement unique | `button` | **ouvert mais à vérifier** — `button` ouvert en pe-epic-9 Story 9.3 ; alignement des 5 scénarios à confirmer story 10.1 | homebridge-homekit-vs-ha-delta §Outside Scope › HomeKit scenarios ; ha-projection-reference.md §button |
| Thermostats / chauffage | `Thermostat chambre Arthur`, `Thermostat chambre Margaux`, `Thermostat Galerie`, `Thermostat RDC`, `Thermostat SDB`, `Thermostat SPA` | `Thermostat` / Info température + Action consigne | `climate` | **hors scope** — `climate` connu dans le registre (pe-epic-7 Story 7.2) mais hors `PRODUCT_SCOPE` ; ouverture prévue story 10.2 | homebridge-homekit-vs-ha-delta §Outside Scope › Thermostats ; ha-projection-reference.md §climate (vagues ultérieures) |
| Alarme maison | `Alarme maison` | Virtuel alarme / Info état + Action armer/désarmer | `alarm_control_panel` | **hors scope** — `alarm_control_panel` connu dans le registre mais hors `PRODUCT_SCOPE` ; ouvrabilité à évaluer story 10.3 | homebridge-homekit-vs-ha-delta §Outside Scope › House alarm ; ha-projection-reference.md §alarm_control_panel |
| Composites métier — SPA | `SPA Power`, `Filtration`, `Jets`, `Bulles`, `Electroliseur` + `Thermostat SPA` | Multi-switch virtuel + Thermostat | `switch` (actions) + `sensor` (mesures) + potentiellement `climate` (thermostat) | **ambigu** — actions individuelles couvertes via `switch` existant ; thermostat SPA relève de `climate` (story 10.2) ; équivalence UX composite à cadrer story 10.4 | homebridge-homekit-vs-ha-delta §Composites › SPA |
| Composites métier — IQ EV | `IQ EV` (état + actions charge directe) | Virtuel mixte état/action chargeur | `switch` + `binary_sensor` / `sensor` | **ambigu** — pas de type HA 1:1 évident ; cadrage composite à effectuer story 10.4 avant toute ouverture | homebridge-homekit-vs-ha-delta §Composites › IQ EV |
| Pilotage solaire / priorisation | `Filtration piscine`, `Chauffage piscine`, `Chauffage SPA`, `Charge voiture` | Virtuel on/off priorisation | `switch` | **ambigu / sensible** — logique on/off déjà couvrable via `switch` ; intention produit à valider avant ouverture ; hors pe-epic-10 prioritaire | homebridge-homekit-vs-ha-delta §Composites › switch virtual |
| Portail | `Portail` | Motorisation porte / Action ouvrir-fermer | `cover` (probable) | **ambigu** — probablement `cover` mais autorité de modélisation HA à trancher ; hors séquencing pe-epic-10 immédiat | homebridge-homekit-vs-ha-delta §Ambiguous › Portail |
| Présences | `Présence Alex`, `Présence Arthur`, `Présence Margaux`, `Présence Melanie` | Info binaire présence | `binary_sensor` (probable) | **sensible / hors pe-epic-10** — techniquement proche de `binary_sensor` déjà couvert, mais ouverture uniquement sur intention produit explicite | homebridge-homekit-vs-ha-delta §Ambiguous › Présence |
| Énergie / routage | `Passerelle Enphase`, `Solaire disponible`, `Chauffe-eau / Routage reel` | Info lecture / virtuel outlet | `sensor` ou `switch` selon intention produit | **sensible / hors pe-epic-10** — modélisation dépend d'une décision produit ; reporter à pe-epic-11+ ou correct-course dédié | homebridge-homekit-vs-ha-delta §Ambiguous › énergie/routage |

---

## Exclusions verrouillées pe-epic-10

Les cas suivants sont **définitivement hors périmètre pe-epic-10**. Ils ne peuvent pas servir à justifier une ouverture de type dans cet epic.

### Plateformes annexes Homebridge (hors jeedom2ha)

| Plateforme | Raison d'exclusion |
|---|---|
| `camera-ffmpeg` / caméras RTSP | Plateforme caméra sans lien avec le moteur de projection Jeedom |
| `SamsungTizen` | Écosystème tiers, aucun équipement Jeedom concerné |
| `homebridge-alexa` | Passerelle vocale, hors scope jeedom2ha |
| `homebridge-gsh` | Google Smart Home, hors scope jeedom2ha |

Toute surface Apple dérivée de ces plateformes est également exclue et ne compte pas comme gap jeedom2ha.

### Usages de monitoring faible valeur (déprioritisés pe-epic-10)

- `airport`, `Internet`, `ampli`, `imprimante`
- Monitoring réseau et équipements domotiques de monitoring faible valeur

### Zones sensibles ou à gouvernance produit explicite (reportées)

- `Présence*` : techniquement mappable sur `binary_sensor` existant, mais ouverture uniquement sur décision produit explicite
- Énergie / routage solaire : modélisation ambiguë, reporter à pe-epic-11+ ou correct-course dédié
- `Portail` : probable `cover` mais autorité de modélisation à trancher hors pe-epic-10 immédiat

---

## Séquencing proposé pour pe-epic-10

Le séquencing ci-dessous est dérivé du delta réel Homebridge → HA et du cadrage §4.2 / §4.4 du sprint-change-proposal-2026-06-07.md.

### Story 10.1 — Vérification et complétion du chemin `button` pour les 5 scénarios HomeKit

- **Nature :** vérification avant tout — peut être close comme pure confirmation si le moteur couvre déjà le besoin
- **Cible :** `Tout eteindre`, `ambiance cinema`, `ambiance coucher`, `Ambiance lumineuse`, `Lumieres terrasse`
- **Type HA :** `button` (déjà ouvert pe-epic-9 Story 9.3 — pas de nouveau type à ouvrir dans cette story)
- **Déclencheur d'action :** uniquement si un scénario est classé `partiellement couvert` ou `non couvert`
- **Statut :** backlog

### Story 10.2 — Ouverture gouvernée de `climate` pour les thermostats Homebridge représentatifs

- **Nature :** première vraie ouverture de type nouvelle de pe-epic-10
- **Cible :** 6 thermostats pièce + `Thermostat SPA` (représentatif composite)
- **Type HA :** `climate` (connu dans le registre depuis pe-epic-7 Story 7.2 ; hors `PRODUCT_SCOPE` jusqu'ici)
- **Prérequis :** story 10.0 close + citation ligne de preuve `ha-projection-reference.md §climate`
- **Statut :** backlog

### Story 10.3 — Évaluation puis ouverture ciblée de `alarm_control_panel` pour `Alarme maison`

- **Nature :** story d'évaluation — tranche entre `ouvrable`, `non ouvrable dans cette vague`, `recadrage produit`
- **Cible :** `Alarme maison`
- **Type HA :** `alarm_control_panel` (connu dans le registre ; hors `PRODUCT_SCOPE`)
- **Note :** découplée de `climate` car le risque produit et UX n'est pas du même ordre
- **Statut :** backlog

### Story 10.4 — Cadrage des composites métier `IQ EV` / `SPA` sans ouverture cosmétique

- **Nature :** story de cadrage uniquement — classe chaque composite dans `déjà couvert par composition`, `extension bornée nécessaire`, ou `hors pe-epic-10`
- **Cible :** `IQ EV` (chargeur VE composite), `SPA` (multi-switch + thermostat)
- **Règle :** `number` et `select` n'entrent que si un besoin réel de consigne ou de mode distinct est prouvé ; sinon handoff vers pe-epic-11+
- **Statut :** backlog

---

## Gates epic-level pe-epic-10 (rappel)

1. Story 10.0 obligatoire et close avant toute ouverture de type nouvelle dans l'epic — **satisfait par cet artefact**
2. Chaque nouveau type HA ouvert cite sa ligne source dans `ha-projection-reference.md`
3. Toute ouverture suit la checklist canonique : mapper, publisher, `known_types`, topics, compteurs, diagnostic, golden-file, tests, terrain
4. Gate terrain final = preuve de parité minimale utile sur les familles retenues, avec statut explicite (`couvert`, `couvert via type existant`, `ouvert dans l'epic`, `hors scope`, `reporté`)
5. Aucune plateforme annexe ou surface Apple dérivée d'une plateforme annexe n'est comptabilisée comme gap jeedom2ha dans cet epic
