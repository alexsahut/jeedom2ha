# Story 17.1: Cadrage de l'ouverture de `number` (consigne) sans ouverture effective

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

En tant que mainteneur de jeedom2ha,
je veux déterminer si un besoin réel de consigne isolée justifie l'ouverture gouvernée de `number`, en identifiant les équipements Jeedom et `generic_type` candidats et en précisant les preuves FR40/NFR10 nécessaires,
afin de ne pas ouvrir un composant HA à vide et de ne pas confondre parité technique et promesse produit.

## Acceptance Criteria

1. **Given** le registre HA — où `number` est déjà `connu` et `validable` (`required_fields = ["command_topic", "platform", "availability"]` ; `required_capabilities = ["has_command"]`, cf. `resources/daemon/validation/ha_component_registry.py:52-55`) mais **absent de `PRODUCT_SCOPE`** (8 composants ouverts : `light, cover, switch, sensor, binary_sensor, button, climate, alarm_control_panel`, cf. `ha_component_registry.py:70`) — **When** la story est exécutée — **Then** chaque cas candidat « consigne » — recensé depuis la **taxonomie `generic_type` Jeedom** (catalogue universel `resources/daemon/mapping/registry.py`, indépendant du corpus d'une box donnée : jeedom2ha est distribué sur le Jeedom Market) — est classé dans l'une des trois catégories : `déjà suffisamment couvert par composition de types existants` / `justifie une ouverture gouvernée number` / `pas de besoin réel prouvé → report`.

2. **Given** un cas classé `déjà suffisamment couvert` — **When** la story est close — **Then** la justification cite les entités HA déjà suffisantes (ex. `climate` pour une consigne de thermostat, `sensor` pour une valeur en lecture seule, `switch` pour un actionneur binaire) **And** aucune nouvelle promesse UX n'est ajoutée **And** `PRODUCT_SCOPE` n'est pas modifié.

3. **Given** un cas classé `justifie une ouverture gouvernée number` — **When** la story est close — **Then** elle **ne force pas** cette ouverture dans `pe-epic-17` **And** elle produit un handoff clair vers une future story d'ouverture (ou un `correct-course`), précisant : le **`generic_type` Jeedom cible** (source de vérité universelle), le cas nominal + le cas d'échec `validate_projection()` à écrire, et le test de non-régression du contrat 4D — c'est-à-dire les 3 conditions AR13/FR40/NFR10 à livrer **dans le même incrément** **And** ces 3 preuves s'écrivent sur **fixtures synthétiques** : la présence de l'équipement sur une box réelle n'est **pas** requise pour ouvrir le composant.

4. **Given** un cas classé `pas de besoin réel prouvé` — **When** la story est close — **Then** la justification cite l'absence de **`generic_type` Jeedom** (catalogue universel) portant une consigne isolée (température de consigne autonome, niveau, volume, position numérique) non déjà couverte par un type ouvert — et non l'absence sur une box particulière.

5. **Given** l'ensemble des cas traités — **When** la story est close — **Then** elle se conclut par un **statut explicite de classement par cas** (tableau : cas candidat → catégorie → justification/handoff) **And** ne modifie ni `PRODUCT_SCOPE`, ni le mapping, ni la validation, ni la publication, ni aucun `generic_type` Jeedom natif.

## Tasks / Subtasks

- [x] Task 1 — Recenser les cas candidats « consigne » (AC: #1)
  - [x] Inventorier, en lecture seule, le **catalogue `generic_type` Jeedom** (`resources/daemon/mapping/registry.py`, universel — pas seulement les types présents sur une box) pouvant porter une consigne numérique isolée (température de consigne, niveau, volume, position numérique)
  - [x] Pour chaque `generic_type`, noter comment il est aujourd'hui projeté (type HA actuel via le mapping existant)
- [x] Task 2 — Classer chaque cas dans les 3 catégories (AC: #1, #2, #3, #4)
  - [x] `déjà suffisamment couvert` : citer les entités HA existantes suffisantes (`climate`, `sensor`, `switch`)
  - [x] `justifie une ouverture gouvernée number` : marquer sans ouvrir → **aucun cas** dans cette catégorie (voir tableau AC5)
  - [x] `pas de besoin réel prouvé → report` : justifier l'absence d'équipement réel
- [x] Task 3 — Produire le handoff FR40/NFR10 pour tout cas justifiant une ouverture (AC: #3)
  - [x] Équipement Jeedom cible + `generic_type` source → **sans objet** : aucun cas classé « justifie ouverture number »
  - [x] Cas nominal + cas d'échec `validate_projection()` à écrire → sans objet (aucune ouverture)
  - [x] Test de non-régression du contrat 4D à écrire → sans objet (aucune ouverture)
  - [x] Rappeler que les 3 preuves sont livrées dans le **même incrément** séparé (AR13) → rappel consigné pour toute ouverture future
- [x] Task 4 — Conclure par le tableau de classement par cas (AC: #5)
  - [x] Vérifier qu'aucune modification de `PRODUCT_SCOPE`/mapping/validation/publication/`generic_type` n'a été faite

## Dev Notes

- **Story de cadrage documentaire** — modèle Story 10.4. Aucune ouverture automatique, aucune modification de code de scope/mapping/validation/publication.
- **Driver de classement = taxonomie `generic_type` Jeedom (universelle)**, source `resources/daemon/mapping/registry.py` — pas le corpus d'une box particulière. jeedom2ha est distribué sur le Jeedom Market : un `generic_type` réel du catalogue qui mappe vers une consigne et n'est pas déjà couvert justifie l'ouverture **même si aucune box locale ne le porte**. Le garde-fou 10.4 interdit l'ouverture *cosmétique* (aucun `generic_type` réel), pas l'ouverture *anticipée* d'un type réel absent de la box du mainteneur.
- **Preuves d'ouverture sur fixtures synthétiques** : cas nominal + échec `validate_projection()` + non-régression 4D s'écrivent sur fixtures ; la box réelle n'est **pas** requise pour franchir le gate FR40/NFR10.
- `number` est **déjà présent** dans `HA_COMPONENT_REGISTRY` (`connu`/`validable`) : une ouverture éventuelle ne rejoue que les preuves FR40/NFR10, pas la définition du composant.
- **Garde-fou Story 10.4** (`epics-projection-engine.md`, Dev notes) : `number`/`select` ne s'introduisent que si un besoin réel de consigne/mode distinct est prouvé sur un équipement Jeedom concret non déjà couvert par un type ouvert.
- Gouvernance à 3 états (AR6) : `connu` (dans `HA_COMPONENT_REGISTRY`) / `validable` (`validate_projection()` passe) / `ouvert` (dans `PRODUCT_SCOPE` sous FR40/NFR10).
- AR13 : toute modification de `PRODUCT_SCOPE` exige simultanément, dans le même incrément : (1) entrée `HA_COMPONENT_REGISTRY` (déjà là), (2) cas nominal + cas d'échec `validate_projection()`, (3) non-régression du contrat 4D.
- Source des contraintes HA : `ha-projection-reference.md` / `.yaml` — jamais une table dupliquée.
- **Produit du PO attendu en `dev-story`** : la liste des équipements Jeedom candidats (consignes réelles) pour trancher le classement.

### Project Structure Notes

- Livrables = artefacts documentaires dans `_bmad-output/` (cette story + son classement). Pas de fichier code touché.
- Registre de référence (lecture seule) : `resources/daemon/validation/ha_component_registry.py` (`number` lignes 52-55 ; `PRODUCT_SCOPE` ligne 70).
- Aucune surface UI ajoutée ; aucun gate terrain disruptif requis (inspection du corpus réel en lecture seule uniquement).

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic 17 — Story 17.1]
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07-cadrage-number-select.md]
- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Story 10.4 (Dev notes — garde-fou number/select)]
- [Source: resources/daemon/validation/ha_component_registry.py#HA_COMPONENT_REGISTRY (number 52-55), PRODUCT_SCOPE (70), AR13 (71-73)]
- [Source: resources/daemon/mapping/registry.py#catalogue generic_type Jeedom (taxonomie universelle, driver de classement)]
- [Source: _bmad-output/planning-artifacts/ha-projection-reference.md / .yaml (source-of-truth contraintes HA)]

## Dev Agent Record

### Agent Model Used

claude-cli/claude-opus-4-8

### Debug Log References

### Completion Notes List

**dev-story lancé 2026-07-17 — statut résultant : `review`.** Story de cadrage documentaire (modèle Story 10.4), aucun code touché.

#### Classement par cas (livrable AC5)

Inventaire, en lecture seule, des `generic_type` du catalogue Jeedom (universel) pouvant porter une **consigne numérique isolée**, avec projection HA actuelle et classement :

| `generic_type` candidat | Nature Jeedom | Projeté aujourd'hui | Catégorie | Justification / handoff |
|---|---|---|---|---|
| `THERMOSTAT_SET_SETPOINT` | action/slider (consigne °C) | `climate` (target_temperature) — `climate.py` | **déjà suffisamment couvert** | La consigne EST la cible du domaine `climate` (déjà ouvert). Un `number` isolé perdrait la sémantique thermostat (modes, temp courante). |
| `THERMOSTAT_SETPOINT` | info numérique | `sensor` temperature °C — `sensor.py:47` | **déjà suffisamment couvert** | Valeur en lecture seule → `sensor`. Pas une consigne réglable. |
| `LIGHT_SLIDER` / `LIGHT_BRIGHTNESS` | action/info (luminosité) | `light` (brightness) — `light.py:36,367` | **déjà suffisamment couvert** | La luminosité est un attribut natif du domaine `light` (déjà ouvert). |
| `FLAP_SLIDER` | action (position volet) | `cover` (position) — `cover.py:345` | **déjà suffisamment couvert** | La position est un attribut natif du domaine `cover` (déjà ouvert). |
| `FAN_SPEED_STATE` | info (rpm, lecture seule) | `sensor` rpm — `sensor.py:50` | **report** (autre domaine) | Vitesse en lecture seule → `sensor`. Une *consigne* de vitesse relève du domaine `fan` (percentage), traité en **pe-epic-18 (18-1)**, pas de `number`. |
| `ROTATION_STATE` | info (rpm, lecture seule) | `sensor` rpm — `sensor.py:51` | **report** (lecture seule) | Info rpm → `sensor`. Aucune consigne réglable. |
| `VOLUME` | info | `sensor` (sans device_class) — `sensor.py:38` | **report** (autre domaine) | Un *réglage* de volume relève de `media_player` (reporté hors pe-epic-18 par SCP 2026-07-17), pas de `number`. |

**Synthèse :** aucun `generic_type` du catalogue Jeedom ne porte une **consigne numérique isolée** qui ne soit pas déjà absorbée par un domaine HA plus riche et sémantique **déjà ouvert** (`climate`, `light`, `cover`), ou qui n'appartienne à un domaine ouvert **séparément** (`fan` → pe-epic-18 ; `media_player` → reporté).

**Décision de cadrage :** **aucun cas ne justifie l'ouverture de `number` aujourd'hui** (garde-fou Story 10.4 respecté : pas de besoin réel de consigne isolée prouvé). `PRODUCT_SCOPE` reste inchangé (8 composants). Toute ouverture future de `number` resterait un incrément séparé sous AR13/FR40/NFR10 (registry `number` déjà présent lignes 52-55 + cas nominal/échec `validate_projection()` + non-régression contrat 4D, sur fixtures synthétiques).

**Vérification AC5 :** aucune modification de `PRODUCT_SCOPE`, du mapping, de la validation, de la publication, ni d'aucun `generic_type` Jeedom natif.

### File List

_Aucun fichier de code modifié._ Story de cadrage documentaire ; seul cet artefact (`17-1-cadrage-ouverture-number-consigne.md`) est rempli. `sprint-status.yaml` mis à jour hors story (statut).

### Change Log

- 2026-07-17 — dev-story : inventaire du catalogue `generic_type` (consigne numérique), classement par cas (AC5), décision de non-ouverture de `number`. Status `ready-for-dev` → `review`. Aucun code touché.
- 2026-07-17 — code-review : PASS, aucun finding. Status `review` → `done`.

## Senior Developer Review (AI)

- **Reviewer :** clawcode (claude-opus-4-8)
- **Date :** 2026-07-17
- **Outcome :** **Approve** (0 High / 0 Medium / 0 Low)

### Vérifications

- **AC1–AC5 satisfaits** : chaque `generic_type` porteur de consigne numérique est recensé, sa projection HA actuelle citée (références de lignes), et classé dans l'une des 3 catégories. Le tableau de classement par cas est présent (AC5).
- **Invariant de cadrage respecté** : `git diff` confirme qu'aucun fichier de code n'est touché (seuls `17-1-*.md` et `sprint-status.yaml` modifiés). `PRODUCT_SCOPE`, mapping, validation, publication et `generic_type` natifs inchangés.
- **Garde-fou Story 10.4 respecté** : décision de non-ouverture justifiée par l'absence de consigne numérique isolée non déjà absorbée par un domaine plus riche déjà ouvert (`climate`/`light`/`cover`) ou ouvert séparément (`fan`/`media_player`).
- **Handoff AR13/FR40/NFR10** correctement décrit comme condition d'un incrément futur séparé (registry déjà présent + nominal/échec `validate_projection()` + non-régression 4D sur fixtures).

### Action Items

_Aucun._
