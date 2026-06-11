---
document_type: backlog_icebox
project: jeedom2ha
status: future_backlog
lastEdited: 2026-06-09
---

# Backlog Futur & Icebox

Ce document trace les sujets qualifiés par le PM qui sont explicitement HORS SCOPE du cycle actif. Ils ne doivent donner lieu à aucune story ni développement tant qu'ils n'ont pas été réévalués lors d'un futur planning d'epic.

## 1. Transparence et observabilité du mapping (Niveau Commande)

* **Intitulé :** Drill-down commande par commande
* **Résumé produit :** Permettre à l'utilisateur de déplier un équipement publié pour consulter, en lecture seule, les commandes sous-jacentes retenues et rejetées par le modèle de mapping, afin de fiabiliser le diagnostic local. Révèle la composition fine de l'équipement HA.
* **Horizon recommandé :** Post-V1.1 (Maturité produit avancée - Frontière C du PRD)
* **Conteneur recommandé :** Futur epic dédié
* **Owner logique :** Product Manager (pour cadrage futur) -> Architect
* **Garde-fous de non-empiètement :** 
  - Ne doit pas polluer l'Epic 2 (Santé du pont) avec des détails de niveau commande.
  - Ne doit pas modifier les statuts principaux de l'Epic 3, qui restent au niveau équipement.
  - Aucune opération HA partielle/unitaire de niveau commande n'est autorisée par l'Epic 4. La granularité managériale reste l'équipement.
* **Condition de réactivation future :** Nécessitera une phase d'architecture propre car cela introduit un niveau 4 structurant (`global -> pièce -> équipement -> commande`) dans la hiérarchie de la donnée et du frontend.

## 2. Alignement ciblé de la navigation sur les patterns Homebridge

* **Intitulé :** Navigation type Homebridge
* **Résumé produit :** Étudier la pertinence d'intégrer ponctuellement des patterns UX d'outils existants (comme Homebridge) pour réduire la friction d'adoption des migrants, uniquement si ces patterns n'entrent pas en conflit avec nos invariants propres à Home Assistant (ex: hiérarchie par pièce).
* **Horizon recommandé :** Icebox / Alignements optionnels tardifs (Frontière D du PRD)
* **Conteneur recommandé :** Backlog futur documenté (Icebox)
* **Owner logique :** UX Designer / Product Manager
* **Garde-fous de non-empiètement :**
  - Ne doit pas interférer avec la dette UX traitée dans l'Epic 1 (corrections de lisibilité). L'Epic 1 optimise notre UX, il ne la pivote pas.
  - Le vocabulaire et la philosophie des opérations restent centrés sur Home Assistant (Epic 3 et 4), pas de renaming des actions par mimétisme avec d'autres écosystèmes.
  - Pas de convergence implicite immédiate pour résoudre des bugs UI.
* **Condition de réactivation future :** Phase très ultérieure conditionnée par une validation stricte d'absence de conflit (conceptuel ou technique) avec le modèle core Jeedom2HA.

---

## 3. Énergie / Routage solaire — pe-epic-11 candidat

> Source : inventaire ClawBox (agent main, 2026-06-09), demande d'Alex pour dashboard solaire HA tablette famille.
> Classé "sensible / hors pe-epic-10" dans la matrice Story 10.0 (pe-epic-10-perimetre-prefixe-2026-06-08.md §Énergie / routage).

### 3.1 MSunPV / RouteurSolaire (eq Jeedom 553)

Absent de HA aujourd'hui (`update.msunpv_update` présent mais aucune valeur de routage exposée).

| Cmd Jeedom | Nom | Unité | Type HA cible |
|---|---|---|---|
| #5138 | Puissance panneaux | W | sensor |
| #5137 | Puissance réseau | W | sensor |
| #5139 | Routage cumulus | % | sensor |
| #5140 | Routage radiateur | % | sensor |
| #5177 | Etat sortie 1 (CE %) | % | sensor |
| #5171 | Production panneaux journalière | Wh | sensor |
| #5170 | Production injectée journalière | Wh | sensor |
| #5169 | Consommation réseau journalière | Wh | sensor |

Domaine HA : `sensor` pur (lecture seule). Pas de nouveau type HA à ouvrir si `sensor` est en PRODUCT_SCOPE.

### 3.2 Chauffe-eau — détail routage (eq Jeedom 554)

`switch.jeedom2ha_554` présent dans HA mais état "unknown". Valeurs de routage absentes.

| Cmd Jeedom | Nom | Unité | Type HA cible |
|---|---|---|---|
| #5530 | Routage réel | % | sensor |
| #5206 | Puissance | W | sensor |
| #5489 | Etat (on/off) | — | binary_sensor |
| #5510 | Chauffe complète dans la journée | — | binary_sensor |
| #5538 | Équivalent H de chauffe aujourd'hui | H | sensor |
| #5527 | kWh depuis hier | kWh | sensor |
| #5708 | Activé | — | binary_sensor |
| #5490 | Manu | — | button/switch |
| #5491 | Auto | — | button/switch |
| #5372 | Absence | — | button |

Domaine HA : `sensor` + `binary_sensor` + `button`/`switch` — tous déjà en PRODUCT_SCOPE si Story 9.x done. Problème probable : switch.jeedom2ha_554 en état "unknown" → à diagnostiquer (problème de mapping commande d'état, pas forcément d'ouverture de type).

* **Priorité suggérée par Alex :** P1 (MSunPV) → P2 (chauffe-eau)
* **Horizon recommandé :** pe-epic-11 (vague énergie/routage solaire)
* **Conteneur recommandé :** Un epic dédié "énergie/routage" avec correction du switch chauffe-eau (état unknown) en story préalable
* **Owner logique :** Architect → SM → Dev
* **Garde-fous de non-empiètement :**
  - Ne pas ouvrir de nouveau type HA pour cette vague : `sensor`, `binary_sensor`, `button`, `switch` couvrent le besoin si PRODUCT_SCOPE est à jour.
  - Distinguer le bug "état unknown" (chauffe-eau switch) d'une vraie ouverture de type — traiter séparément.
  - L'intégration Enphase native HA est hors scope jeedom2ha (déjà couverte côté HA).
* **Condition de réactivation :** pe-epic-10 clos + évaluation architecture pe-epic-11 lors du prochain planning.

---

## 4. IQ EV Charger + Pilotage priorisation solaire — enrichissement Story 10.4

> Note : ces équipements sont déjà dans le scope de Story 10.4 (`cadrage des composites métier IQ EV, SPA`).
> L'inventaire ci-dessous est fourni par ClawBox (2026-06-09) pour informer le PM/Architect lors du cadrage 10.4.

### 4.1 IQ EV Charger (eq Jeedom 583)

Seul `button.iq_ev_charger_iq_ev_charger` présent dans HA, état unknown.

| Cmd Jeedom | Nom | Unité | Type HA cible |
|---|---|---|---|
| #5986 | Branché | — | binary_sensor |
| #5987 | Charge | — | binary_sensor |
| #5991 | Puissance | W | sensor |
| #5992 | Énergie session | Wh | sensor |
| #5993 | Énergie jour | Wh | sensor |
| #6009 | Charge solaire (état) | — | binary_sensor |
| #6010 | Charge manuelle (état) | — | binary_sensor |
| #5999 | Charge solaire On | — | switch/button |
| #6001 | Charge solaire Off | — | switch/button |
| #6000 | Charge manuelle On | — | switch/button |
| #6021 | Charge manuelle Off | — | switch/button |

Composite On/Off dissociés (solar On ≠ solar Off) → à cadrer dans 10.4 (pas d'ouverture cosmétique).

### 4.2 Pilotage priorisation solaire (eq Jeedom 628)

Virtuel centralisant le pilotage des charges. Rien dans HA.

| Cmd info | Cmd On | Cmd Off | Nom | Type HA cible |
|---|---|---|---|---|
| #5977 | #5978 | #5979 | Filtration piscine | switch |
| #5980 | #5981 | #5982 | Chauffage piscine | switch |
| #5983 | #5984 | #5985 | Chauffage SPA | switch |
| #6004 | #6005 | #6006 | Charge voiture | switch |

Pattern info+on+off → `switch` bidirectionnel, déjà dans PRODUCT_SCOPE. Vérifier que le MapperRegistry gère ce pattern triple-commande (info état + cmd on + cmd off) avant d'ouvrir. Peut relever d'une simple configuration mapping si le moteur le supporte, ou d'une mini-story 10.4b.

* **Note Story 10.4 :** utiliser cet inventaire pour guider le cadrage composite IQ EV. Pilotage priorisation est probablement gérable hors cadrage composite si le moteur switch supporte le pattern triple-commande.
* **Condition d'ouverture :** validation architecture 10.4 que le composite On/Off dissociés est modélisable dans le registre actuel.
