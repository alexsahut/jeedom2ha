# Story 10.4: Cadrage des composites métier `IQ EV` / `SPA` sans ouverture cosmétique

Status: done

## Story

En tant que mainteneur,
je veux expliciter si `IQ EV` et `SPA` relèvent d'un simple assemblage de types HA déjà ouverts ou d'une vraie équivalence UX/métier supplémentaire,
afin de ne pas confondre parité technique minimale et promesse produit excessive.

## Acceptance Criteria

1. **AC1 — Classification tripartite exhaustive**
   **Given** les cas `IQ EV` (eq583) et `SPA` (multi-switch + thermostat) issus de l'audit Homebridge Story 10.0
   **When** la story est exécutée
   **Then** chaque composite est classé dans exactement l'une de ces catégories :
   - `déjà couvert par composition` — les types HA existants couvrent le besoin sans ouverture nouvelle
   - `extension bornée nécessaire` — un gap réel est identifié avec handoff pe-epic-11+ ou correct-course futur
   - `hors pe-epic-10` — explicitement exclu par la matrice 10.0 ou règle produit

2. **AC2 — Justification pour chaque composite classé `déjà couvert`**
   **Given** un composite classé `déjà couvert par composition`
   **When** la story est close
   **Then** la justification cite les entités HA suffisantes (switch, sensor, binary_sensor, climate selon le cas)
   **And** aucune promesse UX supplémentaire n'est ajoutée

3. **AC3 — Handoff clair pour tout composite classé `extension bornée` ou `hors pe-epic-10`**
   **Given** un composite classé `extension bornée nécessaire` ou `hors pe-epic-10`
   **When** la story est close
   **Then** une note de handoff documentée pointe vers pe-epic-11+ ou un correct-course dédié
   **And** aucune ouverture de PRODUCT_SCOPE ne se produit dans cette story

## Tasks / Subtasks

- [x] Task 1 — Analyser le composite IQ EV (eq583) face au PRODUCT_SCOPE et au moteur de mapping (AC: #1, #2)
  - [x] Lister les commandes eq583 par domaine HA cible : binary_sensor (états), sensor (mesures), switch (actions On/Off)
  - [x] Vérifier que `binary_sensor` et `sensor` sont en PRODUCT_SCOPE (Oui — PRODUCT_SCOPE = ["light","cover","switch","sensor","binary_sensor","button","climate","alarm_control_panel"] — ha_component_registry.py l.70)
  - [x] Lire `resources/daemon/mapping/switch.py` : le mapper switch collecte les ENERGY_* dans un **dict plat** `{generic_type → JeedomCmd}` — une seule entrée par clé (ENERGY_STATE, ENERGY_ON, ENERGY_OFF) — pas de différenciation info vs action
  - [x] Vérifier les charges dissociées : IQ EV possède DEUX trios logiques (charge solaire : #6009/#5999/#6001 ; charge manuelle : #6010/#6000/#6021) — les deux ne peuvent PAS coexister dans le dict plat ENERGY_* sans collision de clés → **un seul switch par équipement supporté**
  - [x] Verdict IQ EV charge actions : **`extension bornée nécessaire`** — la limite structurelle (dict plat) empêche deux logical switches par équipement sous le moteur actuel ; les états/mesures restent couverts par composition

- [x] Task 2 — Analyser le composite SPA face au PRODUCT_SCOPE (AC: #1, #2)
  - [x] Vérifier que les actions individuelles SPA (Power, Filtration, Jets, Bulles, Electroliseur) sont mappées comme `switch` existant en PRODUCT_SCOPE — Oui, chacune est un équipement Jeedom distinct avec ENERGY_ON/ENERGY_OFF/ENERGY_STATE → switch individuel
  - [x] Confirmer que `Thermostat SPA` est couvert par `climate` ouvert en Story 10.2 — Oui, Story 10.2 done avec 7 climates publiés incluant Thermostat SPA
  - [x] Évaluer promesse UX composite supplémentaire : la parité minimale utile Homebridge → HA est atteinte par la composition individuelle ; aucun type HA "spa composite" n'existe ; pas de gap UX métier réel identifié dans cette vague
  - [x] Verdict SPA : **`déjà couvert par composition`** — switch individuels (Power, Filtration, Jets, Bulles, Electroliseur) + climate (Thermostat SPA) suffisent à la parité minimale utile

- [x] Task 3 — Statuer sur le Pilotage priorisation solaire (eq628) — hors pe-epic-10 (AC: #1, #3)
  - [x] Rappeler verdict matrice 10.0 : eq628 classé "ambigu / sensible — logique on/off déjà couvrable via switch ; intention produit à valider avant ouverture ; **hors pe-epic-10 prioritaire**"
  - [x] Confirmer que eq628 est `hors pe-epic-10` — backlog-icebox §4.2 le range explicitement en pe-epic-11 candidat ; condition d'ouverture : validation architecture + intention produit
  - [x] Note de handoff documentée : "eq628 Pilotage priorisation — pattern triple-commande switch (4 switchs × info+on+off) techniquement couvrable si generic types ENERGY_*, mais intention produit requise et ouverture hors pe-epic-10 — reporter pe-epic-11 énergie/routage"

- [x] Task 4 — Produire l'artefact de cadrage story-level (AC: #1, #2, #3)
  - [x] Tableau de classification tripartite rédigé (voir Completion Notes)
  - [x] Justifications `déjà couvert` avec entités HA citées (SPA)
  - [x] Notes de handoff pe-epic-11+ rédigées (IQ EV charge actions, eq628)
  - [x] Confirmé : aucun `number`, `select`, ni nouveau type HA introduit dans cette story
  - [x] Confirmé : aucune ouverture PRODUCT_SCOPE dans cette story (classification uniquement)

- [x] Task 5 — Mettre à jour sprint-status.yaml (hors AC — clôture story)
  - [x] Statut passé à `review` dans `sprint-status.yaml`
  - [x] `last_updated` mis à jour au 2026-06-09

## Dev Notes

- Cette story est **uniquement analytique** : pas de modification de code, pas d'ouverture de PRODUCT_SCOPE, pas de mapper/publisher nouveau. Elle produit une classification documentée.
- La décision clé est : le moteur switch courant gère-t-il le pattern `info_cmd + on_cmd + off_cmd` avec 3 commandes Jeedom distinctes sur une même entité logique ? C'est la question blocante pour IQ EV.
- Le Pilotage priorisation (eq628) est déjà décidé `hors pe-epic-10` par la matrice 10.0 — ne pas remettre ce choix en question dans cette story.
- `number` et `select` n'entrent que si un besoin réel de consigne ou mode distinct est prouvé — non applicable ici (aucun cas IQ EV / SPA ne l'exige).
- Référence croisée : si le moteur switch ne gère PAS le triple-commande, la note de handoff indiquera que Story 10.4b (correction moteur triple-commande) devra précéder toute ouverture IQ EV.

### Inventaire de référence

**IQ EV (eq583) — commandes cibles :**

| Cmd Jeedom | Nom | Type HA cible | Pattern |
|---|---|---|---|
| #5986 | Branché | binary_sensor | info seule |
| #5987 | Charge | binary_sensor | info seule |
| #5991 | Puissance | sensor (W) | info seule |
| #5992 | Énergie session | sensor (Wh) | info seule |
| #5993 | Énergie jour | sensor (Wh) | info seule |
| #6009 | Charge solaire (état) | binary_sensor info | triple-commande #1 |
| #5999 | Charge solaire On | switch.on | triple-commande #1 |
| #6001 | Charge solaire Off | switch.off | triple-commande #1 |
| #6010 | Charge manuelle (état) | binary_sensor info | triple-commande #2 |
| #6000 | Charge manuelle On | switch.on | triple-commande #2 |
| #6021 | Charge manuelle Off | switch.off | triple-commande #2 |

**SPA — composants cibles :**

| Équipement Jeedom | Type HA cible | Couvert par |
|---|---|---|
| SPA Power | switch | pe-epic-8 / switch déjà en PRODUCT_SCOPE |
| Filtration | switch | idem |
| Jets | switch | idem |
| Bulles | switch | idem |
| Electroliseur | switch | idem |
| Thermostat SPA | climate | Story 10.2 |

### Dev Agent Guardrails

- Cette story NE modifie PAS le code source — aucune édition de `resources/daemon/`.
- Toute la "mise en œuvre" consiste à lire le code existant pour répondre à la question du triple-commande, puis à documenter le verdict dans ce fichier story.
- Ne pas créer de fichier artefact externe : le tableau de classification va dans la section "Completion Notes" de cette story.
- Le moteur à inspecter : `resources/daemon/mapping/` (fichier switch mapper) et `resources/daemon/mapping/registry.py` pour vérifier l'ordre de dispatch.

### Project Structure Notes

- Ne pas modifier `_bmad/` pendant l'implémentation.
- Le seul fichier modifié est `sprint-status.yaml` (Task 5) et ce fichier story lui-même (checkboxes + record).
- Respecter la convention : aucune story terrain (pas de déploiement box réelle requis pour une story de cadrage).

### References

- `_bmad-output/planning-artifacts/pe-epic-10-perimetre-prefixe-2026-06-08.md` (matrice canonique §Composites SPA et IQ EV, §Exclusions)
- `_bmad-output/planning-artifacts/backlog-icebox.md` (§4.1 IQ EV eq583, §4.2 Pilotage priorisation eq628)
- `_bmad-output/planning-artifacts/epics-projection-engine.md` (Story 10.4 — AC et Dev Notes)
- `_bmad-output/planning-artifacts/ha-projection-reference.md` (switch.mqtt, sensor.mqtt, binary_sensor.mqtt — champs requis)
- `resources/daemon/mapping/` (switch mapper — pattern triple-commande à vérifier)
- `resources/daemon/mapping/registry.py` (ordre de dispatch MapperRegistry)
- `resources/daemon/validation/ha_component_registry.py` (PRODUCT_SCOPE courant)

## Dev Agent Record

### Agent Model Used

claude-cli/claude-sonnet-4-6

### Debug Log References

### Completion Notes List

**Artefact de cadrage Story 10.4 — Classification tripartite des composites métier**

#### Tableau de classification

| Composite | Sous-composant | Type HA cible | Verdict | Justification |
|---|---|---|---|---|
| **IQ EV (eq583)** | États (Branché #5986, Charge #5987) | `binary_sensor` | ✅ déjà couvert par composition | binary_sensor en PRODUCT_SCOPE (pe-epic-9) |
| **IQ EV (eq583)** | États charge (#6009 solaire, #6010 manuelle) | `binary_sensor` | ✅ déjà couvert par composition | idem |
| **IQ EV (eq583)** | Mesures (Puissance #5991, Énergie session #5992, Énergie jour #5993) | `sensor` | ✅ déjà couvert par composition | sensor en PRODUCT_SCOPE (pe-epic-9) |
| **IQ EV (eq583)** | Charge solaire On/Off (#5999/#6001) + charge manuelle On/Off (#6000/#6021) | `switch` × 2 | ⚠️ extension bornée nécessaire | Le SwitchMapper utilise un dict plat ENERGY_* (1 entrée/clé) → impossibilité de modéliser 2 logical switches (solaire + manuel) sur le même équipement sans extension du moteur |
| **SPA** | Power, Filtration, Jets, Bulles, Electroliseur | `switch` | ✅ déjà couvert par composition | Chacun est un équipement Jeedom distinct → switch individuel ; PRODUCT_SCOPE ouvert |
| **SPA** | Thermostat SPA | `climate` | ✅ déjà couvert par composition | climate ouvert en Story 10.2 (7 climates publiés) |
| **eq628** | Filtration piscine, Chauffage piscine, Chauffage SPA, Charge voiture | `switch` × 4 | 🚫 hors pe-epic-10 | Matrice 10.0 : "intention produit à valider — hors pe-epic-10 prioritaire" ; reporter pe-epic-11 |

#### Synthèse story-level

- **Aucune ouverture de PRODUCT_SCOPE dans cette story.**
- **Aucun `number`, `select`, ni nouveau type HA introduit.**
- SPA est entièrement couvert par composition (5 switchs individuels + 1 climate).
- IQ EV (eq583) : états/mesures couverts ; les actions charge (2 modes On/Off dissociés) requièrent une **extension bornée** du moteur switch pour supporter plusieurs logical switches par équipement.
- eq628 reste hors pe-epic-10 par décision de la matrice 10.0.

#### Notes de handoff

**IQ EV charge actions → pe-epic-11 ou correct-course dédié**

> La limite identifiée : `SwitchMapper._extract_commands()` collecte les ENERGY_* dans un dict plat `{generic_type: JeedomCmd}` — une seule valeur par clé. Deux trios logiques (charge solaire : ENERGY_STATE/#6009 + ENERGY_ON/#5999 + ENERGY_OFF/#6001 ; charge manuelle : ENERGY_STATE/#6010 + ENERGY_ON/#6000 + ENERGY_OFF/#6021) ne peuvent coexister sans collision.
>
> **Condition de levée de cette extension** : si les modes charge solaire et charge manuelle étaient exposés comme deux équipements Jeedom distincts (chacun avec ses propres ENERGY_STATE/ON/OFF), le SwitchMapper existant suffirait sans modification. L'extension n'est nécessaire que parce que les deux modes sont sur le même équipement eq583.
>
> Extension bornée candidate : permettre au SwitchMapper de produire plusieurs `MappingResult` switch par équipement (multi-switch pattern), ou introduire un `ChargeModeMapper` dédié. Décision d'architecture à prendre en pe-epic-11 ou via correct-course.
>
> Source : `resources/daemon/mapping/switch.py` (dict plat ENERGY_* l.96–103) + `resources/daemon/mapping/models/mapping.py` (SwitchCapabilities l.46–54).

**eq628 Pilotage priorisation → pe-epic-11 énergie/routage**

> Pattern triple-commande (info+on+off × 4 switchs) techniquement couvrable si les generic types sont ENERGY_* et si le moteur supporte le multi-switch pattern. Condition préalable : intention produit explicite + validation architecture. Voir backlog-icebox §4.2.

### File List

- `_bmad-output/implementation-artifacts/10-4-cadrage-des-composites-metier-iq-ev-spa-sans-ouverture-cosmetique.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Senior Developer Review (AI)

**Date :** 2026-06-09  
**Reviewer :** claude-cli/claude-sonnet-4-6  
**Verdict : PASS — 0 HIGH, 0 MEDIUM, 1 LOW (non bloquant)**

- AC1 ✓ classification tripartite exhaustive présente pour IQ EV (eq583), SPA, eq628 — 7 lignes de tableau
- AC2 ✓ SPA `déjà couvert par composition` justifié avec entités HA citées (switch individuel × 5 + climate Story 10.2)
- AC3 ✓ IQ EV charge actions et eq628 ont des notes de handoff pe-epic-11+ avec détails techniques et conditions de levée
- Aucune ouverture PRODUCT_SCOPE — confirmé
- Aucun `number`, `select`, ni nouveau type HA — confirmé

**Finding LOW (amélioré, non bloquant) :** Note de handoff IQ EV enrichie avec la condition de levée de l'extension (si les modes charge étaient des équipements Jeedom distincts, le switch mapper suffirait).

**Note de campagne :** Story de cadrage pur — aucune modification de code source ; les seuls fichiers modifiés sont le story file et sprint-status.yaml.

### Change Log

- 2026-06-09 — BMAD create: story 10.4 créée en `ready-for-dev` (inventaire IQ EV eq583 + eq628 intégré).
- 2026-06-09 — BMAD dev: analyse switch mapper (triple-commande), classification tripartite IQ EV/SPA/eq628 produite.
- 2026-06-09 — BMAD review: audit adversarial PASS (0 HIGH/MEDIUM, 1 LOW corrigé) ; statut final `done`.
