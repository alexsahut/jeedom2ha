---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-07-17
status: approved
scope_classification: moderate
trigger: couverture-generique-des-domaines-ha-manquants-fan-lock-siren-valve-event-media_player
mode: batch
communication_language: french
proposed_by: clawcode
impacts_if_approved:
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
no_change_documented:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/planning-artifacts/ux-spec.md
references:
  - _bmad-output/planning-artifacts/epics-projection-engine.md (Epic 14 FAN_*->switch, Epic 16 overrides, Epic 17 cadrage number/select)
  - _bmad-output/planning-artifacts/ha-projection-reference.md / .yaml
  - resources/daemon/validation/ha_component_registry.py (HA_COMPONENT_REGISTRY vs PRODUCT_SCOPE)
  - resources/daemon/mapping/ (mappers existants : light, cover, switch, sensor, binary_sensor, button, climate, alarm_control_panel, presence_switch, fallback)
  - jeedom/core config/jeedom.config.php (branche develop) : 171 generic_types / 18 familles
  - NebzHB/homebridge-jeedom lib/jeedom-api.js + index.js : superset generic_types HomeKit
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-07-07-cadrage-number-select.md (précédent d'ajout d'epic par correct-course)
---

# Sprint Change Proposal 2026-07-17 - Couverture générique des domaines HA manquants

## 1. Issue Summary

### Trigger

L'investigation de `pe-epic-14` (parité `FAN_*` → `switch`, pompe filtration piscine eq67/cmd382) a révélé un **angle mort systémique** : jeedom2ha ne projette qu'un sous-ensemble des domaines d'entités connus de Home Assistant. Une pompe taguée `generic_type=FAN_STATE` par l'utilisateur (intention « ventilateur ») était projetée en `switch`, faute de mapper `fan`. Le même schéma vaut pour plusieurs autres domaines HA.

Alexandre a demandé (2026-07-17) que le plugin couvre **tous les types connus de HA**, avec « le mapping le plus large et le plus logique possible, sans tenir compte de ce qui existe ou non dans MON installation » — le plugin doit rester **générique**.

### Constat d'audit

État vérifié le 2026-07-17 :

- **Mappers présents** (`resources/daemon/mapping/`) : `light`, `cover`, `switch`, `sensor`, `binary_sensor`, `button`, `climate`, `alarm_control_panel`, `presence_switch`, `fallback`.
- **`HA_COMPONENT_REGISTRY`** (10 composants connus) : `light`, `cover`, `switch`, `sensor`, `binary_sensor`, `button`, `number`, `select`, `climate`, `alarm_control_panel`.
- **`PRODUCT_SCOPE`** (8 ouverts) : `light`, `cover`, `switch`, `sensor`, `binary_sensor`, `button`, `climate`, `alarm_control_panel`.
- `number` / `select` : connus mais non ouverts — **déjà couverts par le cadrage `pe-epic-17`** (hors périmètre de ce SCP).

**Domaines HA manquants** (ni mapper, ni entrée registre) alors qu'un `generic_type` porteur d'intention existe dans le référentiel canonique **core ∪ Homebridge** :

| Domaine HA cible | generic_types source (core ∪ Homebridge) | Comportement actuel |
|---|---|---|
| `fan` | `FAN_STATE/ON/OFF` (Homebridge), `FAN_SPEED*`, `ROTATION*` (core Fan) | projeté en `switch` (pe-epic-14) |
| `lock` | `LOCK_STATE/OPEN/CLOSE` (core Security) | exclu du switch (`_ANTI_SWITCH`) → `fallback` |
| `siren` | `SIREN_STATE/ON/OFF` | exclu du switch (`_ANTI_SWITCH`) → `fallback` |
| `valve` | `VALVE_STATE/ON/OFF`, `FAUCET_*`, `IRRIG_*` (Homebridge) | aucun mapper → `fallback` |
| `event` | `SWITCH_STATELESS_*` (Homebridge) | aucun mapper → `fallback`/`button` |
| `media_player` | `VOLUME`, `SPEAKER_MUTE_*`, `MEDIA_*` (core Multimedia + Homebridge) | aucun mapper → `sensor`/`fallback` |

### Référentiel de conception (invariant durable)

Le référentiel autoritaire du moteur de mapping est **Jeedom core ∪ plugin Homebridge**, PAS core seul. Beaucoup d'installations exécutent les deux plugins. Un `generic_type` posé pour Homebridge est un **signal d'intention utilisateur** sur la nature de l'équipement (ex. filtration taguée `FAN` pour apparaître comme ventilateur dans HomeKit). jeedom2ha doit **consommer** cette intention pour produire la projection HA la plus logique, **sans jamais modifier ni casser** la configuration Homebridge. La couche d'override `pe-epic-16` (`data/ha_overrides.json`) reste le point de contrôle final de l'utilisateur (ex. garder `fan` pour HomeKit tout en forçant `switch` dans HA).

### Category

**Roadmap adjustment — extension gouvernée de `PRODUCT_SCOPE`.** Implique du code réel (nouveaux mappers + entrées registre + `validate_projection` nominal/échec + non-régression 4D) sous FR40/NFR10, épisode par domaine.

## 2. Impact Analysis

### 2.1 Checklist correct-course

| Item | Statut | Notes |
|---|---|---|
| 1.1 Trigger story | [x] | `pe-epic-14` (FAN parity) a révélé la lacune de couverture des domaines. |
| 1.2 Core problem | [x] | jeedom2ha ne couvre que 8 domaines HA ouverts ; ≥6 domaines à `generic_type` porteur d'intention non projetés. |
| 1.3 Evidence | [x] | Audit `mapping/` + `ha_component_registry.py` ; référentiel core (`jeedom.config.php`) ∪ Homebridge (`jeedom-api.js`, `index.js`). |
| 2.1 Current epic | [x] | `pe-epic-16` (overrides) et `pe-epic-17` (cadrage number/select) restent `in-progress` ; aucun rollback. |
| 2.2 Epic-level changes | [x] | Ajouter `pe-epic-18` (couverture domaines HA) ; **modifie la portée de la décision `pe-epic-14`** (FAN par défaut → `fan`, plus `switch`). |
| 2.3 Future epics | [x] | Complémentaire de `pe-epic-16` (overrides finaux) et `pe-epic-17` (number/select) ; pas de conflit. |
| 2.4 New epic needed | [x] | Oui ; numéro 18 libre (grep sprint-status.yaml) ; périmètre distinct des overrides et du cadrage number/select. |
| 2.5 Priority/order | [x] | Non bloquant pour `pe-epic-16`/`17` ; séquence interne 18-0 → 18-1..18-6. |
| 3.1 PRD conflict | [!] | FR40/NFR10 couvrent la gouvernance d'ouverture ; à vérifier si chaque domaine relève d'une Feature PRD existante ou d'un ajout FR. |
| 3.2 Architecture conflict | [x] | Aucun changement structurel : dispatch registry-driven (`pe-epic-8`) absorbe de nouveaux mappers/publishers sans refonte. |
| 3.3 UI/UX conflict | [N/A] | Visibilité console traitée par `pe-epic-15` (lecture seule) ; pas de nouvelle surface exigée ici. |
| 3.4 Other artifacts | [!] | `epics-projection-engine.md` + `sprint-status.yaml` à mettre à jour après approbation. |
| 4.1 Direct adjustment | [x] Viable | Ajouter un epic de couverture, une story d'ouverture gouvernée par domaine. |
| 4.2 Rollback | [x] Not viable | Aucun travail à revertir ; `pe-epic-14` est étendu, pas annulé. |
| 4.3 MVP review | [x] Not needed | MVP du cycle intact ; extension additive. |
| 4.4 Recommended path | [x] | Direct Adjustment : epic `pe-epic-18`, préfixe référentiel + une story d'ouverture FR40/NFR10 par domaine. |
| 5.x Proposal components | [x] | Issue, impact, changements, handoff présents. |
| 6.3 Approval | [x] | Approuvé par Alexandre 2026-07-17 : 5 domaines (fan/lock/siren/valve/event), fan en tête, media_player reporté hors epic. |
| 6.4 Sprint status | [!] | Mise à jour uniquement après ce SCP approuvé. |

### 2.2 Ce qui ne change pas

- Le cycle actif reste **Moteur de projection explicable**.
- L'architecture pipeline 5 étapes et le dispatch registry-driven (`pe-epic-8`) restent inchangés : chaque domaine s'ajoute comme mapper + entrée table de publication.
- `pe-epic-16` (overrides) et `pe-epic-17` (cadrage number/select) restent `in-progress`, non impactés.
- Les `generic_type` Jeedom natifs et la config Homebridge ne sont **jamais** modifiés (lecture seule).

### 2.3 Ce qui change si approuvé

- `pe-epic-18` matérialisé (backlog) : couverture générique des domaines HA manquants.
- Story de **préfixe** `18-0` : gel du référentiel dual-source core ∪ Homebridge et matrice canonique domaine → `generic_type` → contraintes HA (verrouillage du périmètre, modèle Story 10.0).
- Une story d'**ouverture gouvernée** par domaine (`fan`, `lock`, `siren`, `valve`, `event`), chacune livrant dans le même incrément : entrée `HA_COMPONENT_REGISTRY`, mapper dédié, cas nominal + cas d'échec `validate_projection()`, non-régression 4D, gate terrain.
- `media_player` **reporté hors epic** (décision Alexandre 2026-07-17) : candidat d'un epic futur dédié.
- `pe-epic-14` étendu : `FAN_STATE/ON/OFF` projeté par défaut en `fan` ; l'override `pe-epic-16` permet de forcer `switch` dans HA ; non-régression stricte sur `SWITCH_*`/`ENERGY_*`.

### 2.4 Impact technique

| Zone | Impact |
|---|---|
| Code Python | Nouveaux mappers (`fan`, `lock`, `siren`, `valve`, `event`, `media_player`) + entrées table publication ; extension `_ANTI_SWITCH`/routage pour `fan`. |
| Registre HA | Ajout de chaque domaine à `HA_COMPONENT_REGISTRY` (required_fields/capabilities) puis à `PRODUCT_SCOPE` sous FR40/NFR10, incrément par incrément. |
| Validation | Cas nominal + cas d'échec `validate_projection()` par domaine ouvert. |
| Tests | Tests unitaires par mapper + golden corpus étendu + non-régression 4D et `SWITCH_*`/`ENERGY_*`. |
| Diagnostic / MQTT | Nouveaux `ha_entity_type` publiés ; gate terrain par domaine (état MQTT non-unknown, zéro régression). |
| Overrides (pe-epic-16) | Compatibilité : chaque nouveau domaine reste redirigeable par la couche d'override. |

## 3. Path Forward Evaluation

### Option 1 - Direct Adjustment : `pe-epic-18` couverture domaines HA (recommandée)

**Statut : recommandée.** Un epic conteneur, une story d'ouverture gouvernée par domaine, chacune complète FR40/NFR10 dans son incrément. Respecte l'architecture registry-driven et la gouvernance d'ouverture. Permet un séquencement priorisé (fan d'abord — lien pe-epic-14) et des gates terrain isolés.

### Option 2 - Ouvrir tous les domaines en un seul incrément massif

**Statut : non recommandée.** Violerait la discipline FR40/NFR10 « un composant ouvert = un incrément prouvé » et rendrait le gate terrain ininterprétable (régressions difficiles à isoler).

### Option 3 - Cadrage documentaire seul (modèle number/select)

**Statut : non recommandée ici.** Pour `number`/`select` aucun équipement ne prouvait le besoin. Ici le besoin générique est explicite (intention utilisateur portée par `generic_type` core ∪ Homebridge) : la couverture doit être **effective**, pas seulement cadrée. `media_player` seul justifie une story d'évaluation préalable (18-6).

### Selected approach

**Option 1 : `pe-epic-18`, préfixe référentiel (18-0) + une story d'ouverture gouvernée par domaine (18-1..18-5). `media_player` reporté hors epic.**

## 4. Detailed Change Proposals

### 4.1 `epics-projection-engine.md` — Ajouter `pe-epic-18`

**Section :** après le bloc Epic 17 (dernier epic du document).

**NEW :** bloc `### Epic 18 — Couverture générique des domaines HA manquants` avec :

- **Objectif** : projeter tous les domaines HA porteurs d'intention (`fan`, `lock`, `siren`, `valve`, `event`, `media_player`) à partir du référentiel core ∪ Homebridge, sans casser Homebridge, sans dépendre de l'installation d'Alexandre.
- **Invariant** : jeedom2ha consomme les `generic_type` Homebridge en lecture seule ; l'override `pe-epic-16` reste le contrôle final.
- **Stories** :
  - **18-0** Préfixe — gel du référentiel dual-source + matrice canonique domaine → generic_type → contraintes HA (modèle Story 10.0, documentaire).
  - **18-1** Ouverture gouvernée `fan` (`FAN_STATE/ON/OFF` + `FAN_SPEED*`/`ROTATION*`), défaut `switch` → `fan`, override `switch` préservé, non-régression `SWITCH_*`/`ENERGY_*` (étend pe-epic-14).
  - **18-2** Ouverture gouvernée `lock` (`LOCK_STATE/OPEN/CLOSE`).
  - **18-3** Ouverture gouvernée `siren` (`SIREN_STATE/ON/OFF`).
  - **18-4** Ouverture gouvernée `valve` (`VALVE_*`, `FAUCET_*`, `IRRIG_*`).
  - **18-5** Ouverture gouvernée `event` (`SWITCH_STATELESS_*`).
  - *(hors epic — décision Alexandre 2026-07-17)* `media_player` (`VOLUME`, `SPEAKER_MUTE_*`, `MEDIA_*`) est **reporté** vers un epic futur dédié ; capabilities riches (volume, sources, transport) justifient un cadrage séparé.
- **Gate epic-level** : chaque domaine ouvert publie au moins un cas représentatif en MQTT HA, état non-unknown, avec preuve nominal + échec `validate_projection()` et zéro régression 4D/`SWITCH_*`.

**Rationale :** conteneur explicite de couverture, aligné sur la gouvernance d'ouverture existante (pe-epic-7/9/10) et le dispatch registry-driven (pe-epic-8).

### 4.2 `sprint-status.yaml` — Ajout après approbation

**NEW (bloc commentaire + development_status) :**

```yaml
  pe-epic-18: backlog  # couverture generique domaines HA manquants (fan/lock/siren/valve/event) ; cadre par SCP 2026-07-17 ; referentiel core ∪ Homebridge ; une ouverture gouvernee FR40/NFR10 par domaine ; overrides pe-epic-16 preserves ; media_player reporte hors epic
  18-0-prefixe-referentiel-dual-source-et-matrice-domaines: backlog
  18-1-ouverture-gouvernee-fan: backlog
  18-2-ouverture-gouvernee-lock: backlog
  18-3-ouverture-gouvernee-siren: backlog
  18-4-ouverture-gouvernee-valve: backlog
  18-5-ouverture-gouvernee-event: backlog
```

**Rationale :** enregistre l'epic et les stories comme backlog, prêtes pour `create-story` domaine par domaine.

## 5. Recommendation

Approuver un correct-course **modéré** :

- oui à la matérialisation de `pe-epic-18` (couverture domaines HA) ;
- oui à la story préfixe `18-0` (référentiel dual-source gelé) puis une story d'ouverture gouvernée par domaine ;
- ouverture **effective** de `PRODUCT_SCOPE` domaine par domaine, chacune sous FR40/NFR10 (registry + nominal/échec `validate_projection()` + non-régression 4D) dans son propre incrément ;
- non-régression stricte de la config Homebridge (lecture seule) et compatibilité avec la couche d'override `pe-epic-16`.

## 6. Implementation Handoff

### Scope classification

**Moderate.** Réorganisation de backlog + code réel gouverné, plusieurs incréments d'ouverture. Coordination PO/SM requise pour prioriser les domaines.

### Recipients

| Role | Responsabilité |
|---|---|
| Scrum Master | Ajouter `pe-epic-18` + 7 stories au backlog ; séquencer les ouvertures. |
| Dev (create-story → dev-story → code-review) | Produire `18-0` (préfixe) puis les ouvertures domaine par domaine avec preuves FR40/NFR10 et gate terrain. |
| Product Owner | Confirmer la priorité des domaines et fournir les équipements candidats par domaine pour le gate terrain. |

### Success criteria

- `pe-epic-18` et les 7 stories apparaissent en backlog.
- `18-0` gèle le référentiel dual-source et la matrice domaine → generic_type → contraintes HA.
- Chaque domaine ouvert : entrée registre + mapper + validate_projection nominal/échec + non-régression 4D + gate terrain PASS, sans casser Homebridge ni les overrides.

## 7. Decision

**Approved — Alexandre, 2026-07-17.**

Décisions :

1. **Périmètre** : `pe-epic-18` couvre `fan`, `lock`, `siren`, `valve`, `event` (préfixe 18-0 inclus).
2. **Séquencement** : ouverture des domaines en commençant par `18-1 fan` (lien direct pe-epic-14).
3. **`media_player`** : **reporté hors epic** — candidat d'un epic futur dédié.

Actions d'application :

- matérialiser `pe-epic-18` dans `epics-projection-engine.md` ;
- ajouter `pe-epic-18` + `18-0`..`18-5` en `backlog` dans `sprint-status.yaml` ;
- enchaîner `create-story` en commençant par `18-0` (préfixe référentiel), puis `18-1 fan`.
