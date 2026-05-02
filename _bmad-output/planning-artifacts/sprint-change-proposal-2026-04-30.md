---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-04-30
status: approved
scope_classification: moderate_to_major
trigger: drift-de-sequencing-publication-reelle-non-livree-pe-epic-7
mode: incremental
communication_language: french
approved_by: Alexandre
approved_on: 2026-04-30
impacts:
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/planning-artifacts/active-cycle-manifest.md
  - _bmad-output/planning-artifacts/ha-projection-reference.md
no_change_documented:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-04-09.md
  - _bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md
new_epics:
  - pe-epic-8 (refactor dispatch + registry-driven)
  - pe-epic-9 (vague 1 d'extension reelle + FallbackMapper §11)
re_homed_stories:
  - story-7-5 -> pe-epic-9 story-9-5
references:
  - docs/cadrage_plugin_jeedom_ha_bmad.md
  - docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-22.md
---

# Sprint Change Proposal 2026-04-30 — Drift de sequencing revele par la cloture de pe-epic-7

## 1. Issue Summary

### Trigger

La cloture imminente de `pe-epic-7` (4/5 stories `done`, story 7.5 `backlog`) revele un **drift de sequencing cumule** entre la vision produit du cadrage initial (`docs/cadrage_plugin_jeedom_ha_bmad.md` §5, §6, §11) et l'execution effective : Epic 7 a livre la **gouvernance** d'ouverture (`HA_COMPONENT_REGISTRY` + `validate_projection()` + `PRODUCT_SCOPE` etendu a `["light", "cover", "switch", "sensor", "binary_sensor"]` sous gate FR40 / NFR10) mais **aucune publication reelle** de `sensor` / `binary_sensor` n'est livree dans Home Assistant.

### Problem statement

Le probleme identifie n'est :

- ni un bug du moteur de projection (le pipeline 5 etapes fonctionne) ;
- ni un defaut du PRD actif (FR36-FR45 couvrent correctement la gouvernance) ;
- ni un manque d'architecture (`architecture-projection-engine.md` cite deja l'Excel et pose la separation registre / mapping / discovery) ;
- ni un simple sujet de wording UX.

Le probleme est un **defaut de sequencing cumule** sur trois plans :

1. **Plan vision -> backlog** : la regle §11 du cadrage initial — *« degradation elegante : sensor/button par defaut plutot qu'un type 'riche' incorrect »* — n'a jamais ete traduite en story executable. Aucune story de Epic 7 (ni du cadrage V1.1 anterieur) n'instancie cette regle ; le code fait `continue` silencieux a la place (`resources/daemon/transport/http_server.py:1047`).

2. **Plan brief V1.1 -> cycle Moteur** : la formulation produit *« publier moins, expliquer mieux »* (`prd-post-mvp-v1-1-pilotable.md` §7) a ete **sur-appliquee** par les agents BMAD ulterieurs comme « couvrir moins de types HA » alors que sa formulation correcte aurait du etre :
   > « publier en degradation elegante plutot qu'en skip silencieux ; n'omettre que quand aucune projection structurellement valide n'existe ».

   Cette sur-application a glisse dans le brief refresh (`product-brief-jeedom2ha-post-mvp-refresh.md` §4 « pas plus d'entites », §10 « non-objectif couverture exhaustive ») et dans l'axe d'extension ordonne du PRD V1.1 (§11 axe 6 cite `button → number → select → climate` mais oublie `sensor` / `binary_sensor`, alors que le cadrage §5 les promettait explicitement).

3. **Plan epic-level Epic 7** : le correct-course du 2026-04-22 a re-frame Epic 7 sur l'**actionnabilite** (CTA utilisateur) plutot que sur l'**ouverture produit reelle**. Les 5 stories 7.1-7.5 livrent toutes de la gouvernance ou du contrat d'affichage, **aucune** ne livre un mapper, un publisher ou un dispatch capable de publier reellement un equipement Jeedom de type `sensor` ou `binary_sensor`.

### Evidence

| Evidence | Constat | Lecture |
|---|---|---|
| `docs/cadrage_plugin_jeedom_ha_bmad.md` §11 | « degradation elegante : sensor/button plutot qu'un type 'riche' incorrect ; exposer un diagnostic clair » | Regle promesse-cadrage non traduite en backlog |
| `docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx` | 31 composants HA officiels MQTT, 163 types generiques Jeedom Core 4.2, 77 champs structurellement requis | Reference operationnelle existante mais non promue dans le sequencing BMAD avant 2026-04-30 |
| `_bmad-output/planning-artifacts/ha-projection-reference.md` (cree 2026-04-30) | Extraction markdown de l'Excel realisee le jour du correct-course | Source-of-truth disponible mais non encore actee |
| `_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md` §7 + §11 axe 6 | « publier moins, expliquer mieux » + axe d'extension `button → number → select → climate` (sans `sensor`/`binary_sensor`) | Sur-application identifiee — formulation corrigee actee dans cette section |
| `_bmad-output/planning-artifacts/product-brief-jeedom2ha-post-mvp-refresh.md` §4 + §10 | « pas plus d'entites » + « non-objectif couverture exhaustive » | Drift cumule du brief refresh — secondaire selon manifest |
| `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-22.md` §5.3 | Stories 7.1 a 7.5 toutes orientees registre / validation / scope / CTA | Aucune story sur publication reelle — Epic 7 framing actionnabilite plutot que ouverture produit |
| `_bmad-output/planning-artifacts/epics-projection-engine.md:982-1124` | Epic 7 redige sur la gouvernance ; 7.5 sur les CTA | Pas de mapper, pas de publisher, pas de dispatch — produit non livrable |
| `resources/daemon/validation/ha_component_registry.py:64` | `PRODUCT_SCOPE = ["light", "cover", "switch", "sensor", "binary_sensor"]` | Gouvernance ouverte — mais sans surface code |
| `resources/daemon/mapping/` | 3 fichiers seulement : `light.py`, `cover.py`, `switch.py` | Aucun `SensorMapper`, `BinarySensorMapper`, `ButtonMapper`, `FallbackMapper` |
| `resources/daemon/transport/http_server.py:1031-1224` | Cascade `LightMapper -> CoverMapper -> SwitchMapper` + 3 elif hardcodes (~50 lignes / type) + `continue` ligne 1047 | Architecture code interdit l'extension structurelle ; skip silencieux contredit §11 cadrage |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | `pe-epic-7: in-progress` ; 7.1 a 7.4 done ; 7.5 backlog | Epic non clos ; 7.5 sans pre-requis publiable |

### Category

**Misunderstanding of original requirements** combinee a **failed sequencing cumule sur trois cycles** (cadrage initial -> V1.1 Pilotable -> Moteur de projection).

Le bon traitement n'est pas de « finir 7.5 dans Epic 7 », mais de :

- **clore proprement Epic 7** sur sa valeur reellement livree (gouvernance d'ouverture + `projection_validity`) ;
- **re-homer 7.5** vers un epic ou la publication reelle existe ;
- **ouvrir deux nouveaux epics** dont le scope porte enfin la dette structurelle (refactor dispatch puis vague 1 reelle + degradation elegante) ;
- **acter `ha-projection-reference.md`** comme source-of-truth officielle pour empecher la repetition du drift sur les vagues ulterieures.

---

## 2. Impact Analysis

### 2.1 Impact sur pe-epic-7

`pe-epic-7` reste valide sur la valeur reellement livree :

- Story 7.1 : `projection_validity` expose dans le contrat 4D sans regression (done).
- Story 7.2 : `HA_COMPONENT_REGISTRY` modelise 9 composants HA `connus` (done, PR #103).
- Story 7.3 : `validate_projection()` couvre cas nominaux et cas d'echec sur la vague cible (done, PR #104).
- Story 7.4 : `PRODUCT_SCOPE` etendu sous gate FR40 / NFR10 (done, code review PASS 2026-04-28).

Ce qui ne peut pas etre maintenu :

- l'idee que Story 7.5 (CTA) puisse etre executee tant qu'aucune surface produit reellement publiable n'existe ;
- l'idee qu'Epic 7 soit ferme honnetement sans documenter la dette structurelle (mappers + publishers + dispatch + degradation §11) qui aurait du etre dans son scope ou immediatement apres.

### 2.2 Required epic-level changes

1. Cloturer `pe-epic-7` sur 7.1-7.4 avec note de disposition documentant la dette re-homee.
2. Re-homer Story 7.5 vers `pe-epic-9` Story 9.5 comme artefact historique.
3. Ajouter `pe-epic-8` — refactor pur du dispatch (`MapperRegistry` + `PublisherRegistry` + slot `FallbackMapper` no-op + golden-file gate).
4. Ajouter `pe-epic-9` — vague 1 d'extension reelle (`SensorMapper` + `BinarySensorMapper` + `ButtonMapper` + `FallbackMapper` §11 + ex-7.5 reformulee).
5. Promouvoir `ha-projection-reference.md` en source-of-truth active dans le manifest.

### 2.3 Remaining epic review

Aucun autre epic actif. Les 22 stories des cycles V1.1 Pilotable et Moteur de Projection (epics 1-7) sont done. Aucun epic futur planifie au-dela de Epic 7 dans `epics-projection-engine.md`. `pe-epic-8` et `pe-epic-9` deviennent les **prochains epics requis**, dans cet ordre obligatoire (`pe-epic-9` bloque tant que `pe-epic-8` Story 8.4 golden-file n'est pas vert).

### 2.4 New epic requirement

**Oui — deux epics requis.**

Sans `pe-epic-8` :
- toute extension de type oblige a dupliquer ~50 lignes par type dans `http_server.py`,
- la promesse §11 du cadrage reste impossible a cabler sans patcher chaque elif.

Sans `pe-epic-9` :
- `PRODUCT_SCOPE` reste gouverne ouvert sur `sensor` / `binary_sensor` sans publication reelle (etat incoherent),
- la regle §11 du cadrage reste lettre morte,
- Story 7.5 (CTA) n'a aucune surface produit pour s'executer honnetement.

### 2.5 Order / priority changes

Ordre obligatoire post correct-course :
1. Promotion `ha-projection-reference.md` (immediat, change proposal 5.6 + 5.7).
2. Cloture `pe-epic-7` (change proposal 5.1 + 5.4a + 5.5b).
3. Demarrage `pe-epic-8` Story 8.1 (`MapperRegistry`).
4. Cloture `pe-epic-8` (gate golden-file 8.4 vert).
5. Demarrage `pe-epic-9` Story 9.1 (`SensorMapper`).
6. Stories 9.1 -> 9.4 dans l'ordre du dispatch (Sensor / BinarySensor / Button / Fallback).
7. Story 9.5 (ex-7.5) en cloture epic, conditionnee gate terrain PASS.

---

## 3. Artifact Conflict and Impact Analysis

### 3.1 PRD actif (`prd.md`)

**Aucun conflit.** FR11-FR15 (mapping candidat), FR26-FR30 (publication separee), FR36-FR45 (registre + gouvernance) couvrent deja les exigences. La regle §11 cadrage est cablee story-level (`pe-epic-9` Story 9.4), pas par un FR additif. Voir change proposal 5.8a.

### 3.2 PRD V1.1 Pilotable (`prd-post-mvp-v1-1-pilotable.md`)

**Drift identifie sur §7 + §11 axe 6 — non modifie.** Artefact secondaire selon manifest section 5. Sur-application documentee dans la presente Section 1 avec formulation corrigee. Voir change proposal 5.8d.

### 3.3 Architecture (`architecture-projection-engine.md`)

**Aucun conflit.** Cite deja l'Excel comme source-of-truth (3 mentions). Pose AR3 (separation registre / mapping / discovery), AR13 (gouvernance scope), 2 niveaux d'abstraction. Voir change proposal 5.8b.

### 3.4 Product Brief (`product-brief-jeedom2ha-2026-04-09.md`)

**Aucun conflit.** Cite l'Excel, pose l'ouverture progressive comme posture produit. Voir change proposal 5.8c.

### 3.5 Brief refresh V1.1 (`product-brief-jeedom2ha-post-mvp-refresh.md`)

**Drift identifie §4 / §10 — non modifie.** Artefact secondaire selon manifest. La sur-application de « pas plus d'entites » et « non-objectif couverture exhaustive » est tracee en evidence Section 1, pas reecrite (meme rationale que 5.8d).

### 3.6 UI / UX

**Aucun nouveau recadrage UX requis.** La regle UX utile est deja tranchee (Story 6.3 « no faux CTA »). Story 9.5 (ex-7.5) re-applique cette regle aux surfaces de la vague 1 sans changer la posture.

### 3.7 Other artifacts impacted

| Artefact | Impact | Change proposal |
|---|---|---|
| `epics-projection-engine.md` | Critique | 5.1 + 5.2 + 5.3 + 5.4 |
| `sprint-status.yaml` | Critique | 5.5 |
| `active-cycle-manifest.md` | Significatif | 5.6 |
| `ha-projection-reference.md` | Promotion | 5.7 |
| Code production (`mapping/`, `transport/http_server.py`, `discovery/`) | Critique apres approbation | story-level dans `pe-epic-8` et `pe-epic-9` |

---

## 4. Path Forward Evaluation

### Option 1 — Direct Adjustment

**Statut : Not viable.**

Pourquoi : reframer 7.5 dans Epic 7 ne suffit pas — la dette structurelle (3 elif + skip silencieux + regle §11 absente) reste intacte et empeche toute extension scalable.

**Effort :** Medium — **Risk :** High si tente seul.

### Option 2 — Potential Rollback

**Statut : Not viable.**

Pourquoi : revenir sur `PRODUCT_SCOPE = ["light", "cover", "switch"]` detruit la valeur livree par 7.2-7.4 et la gouvernance FR40 / NFR10. Aucune simplification durable n'en resulterait.

**Effort :** High — **Risk :** High.

### Option 3 — PRD MVP Review

**Statut : Not viable.**

Pourquoi : le PRD actif n'est pas faux. Refondre le PRD reviendrait a sur-corriger un probleme de sequencing par une revision de cadrage.

**Effort :** High — **Risk :** Medium.

### Option 4 — Hybrid (selectionnee)

Description :
- cloture propre pe-epic-7 sur 7.1-7.4,
- re-homing 7.5 vers pe-epic-9 Story 9.5,
- creation pe-epic-8 (refactor pur dispatch + registry-driven, gate golden-file 30 equipements),
- creation pe-epic-9 (vague 1 reelle + FallbackMapper §11 terminal, gate terrain comptage nouveaux publies),
- promotion `ha-projection-reference.md` en source-of-truth active,
- aucune reecriture PRD / architecture / brief.

**Effort :** Moderate-to-Major (~9 stories pe-epic-8 + pe-epic-9, refactor + 4 nouveaux mappers + 4 nouveaux publishers + 5 nouveaux cause_codes).
**Risk :** Low si sequence respectee (golden-file 8.4 garantit la non-regression). High si pe-epic-9 demarre avant cloture pe-epic-8.

### Rationale

Cette approche :
- preserve la valeur deja livree (Stories 7.1 a 7.4) ;
- restaure la promesse §11 du cadrage initial sans detruire la gouvernance Epic 7 ;
- aligne enfin le code sur la reference projection extraite (`ha-projection-reference.md`, 31/163/77) ;
- pose une infrastructure dispatch / registry / golden-file reutilisable pour les vagues ulterieures (`pe-epic-10+`) ;
- conserve la posture Epic 6 « no faux CTA » et la convention `cause_mapping.py` Epic 4 V1.1 ;
- documente formellement chaque non-modification (5.8a/b/c/d/e) pour empecher le drift de se repeter.

---

## 5. Detailed Change Proposals

### 5.1 — Note de cloture officielle pe-epic-7

**Artifact** : `_bmad-output/planning-artifacts/epics-projection-engine.md`
**Section** : `## Epic 7 — L'actionnabilite devient une capacite produit reelle...`, juste apres la description d'epic, avant `### Story 7.1`

**OLD** (lignes 982-985 actuelles)

```md
## Epic 7 — L'actionnabilite devient une capacite produit reelle par ouverture gouvernee du perimetre HA

L'utilisateur ne voit une action que lorsqu'elle repose sur une surface produit reellement ouverte, supportee et testee. Le mainteneur ouvre progressivement le perimetre HA selon FR40 / NFR10, expose `projection_validity` de facon additive, puis n'autorise des CTA utilisateur que pour les remediations effectivement disponibles.

### Story 7.1 : Enrichissement additif du contrat 4D — `projection_validity` est expose de bout en bout sans regression sur le schema canonique
```

**NEW**

```md
## Epic 7 — L'actionnabilite devient une capacite produit reelle par ouverture gouvernee du perimetre HA

L'utilisateur ne voit une action que lorsqu'elle repose sur une surface produit reellement ouverte, supportee et testee. Le mainteneur ouvre progressivement le perimetre HA selon FR40 / NFR10, expose `projection_validity` de facon additive, puis n'autorise des CTA utilisateur que pour les remediations effectivement disponibles.

### Disposition de cloture 2026-04-30 — correct-course

**Statut** : Epic clos sur la valeur reellement livree par les stories 7.1, 7.2, 7.3 et 7.4.

**Valeur livree** :
- `projection_validity` expose de bout en bout dans le contrat 4D sans regression (Story 7.1)
- `HA_COMPONENT_REGISTRY` modelise 9 composants HA `connus` avec contraintes structurelles (Story 7.2)
- `validate_projection()` couvre cas nominaux et cas d'echec representatifs sur les types de la vague cible (Story 7.3)
- `PRODUCT_SCOPE` etendu de `["light", "cover", "switch"]` a `["light", "cover", "switch", "sensor", "binary_sensor"]` sous gate FR40 / NFR10 (Story 7.4)
- Gates CI verrouilles : aucun ajout futur a `PRODUCT_SCOPE` sans entree registre + cas nominaux + cas d'echec dans le meme increment

**Re-homing de la story 7.5** : la story 7.5 « Exposition d'actions utilisateur uniquement sur les surfaces reelles et supportees » est re-homee vers `pe-epic-9` car son intention CTA n'a de sens qu'apres existence d'une surface produit reellement publiable. Voir change proposal 5.4 du SCP du 2026-04-30.

**Dette structurelle non livree, re-homee explicitement** : `PRODUCT_SCOPE` est gouverne comme ouvert sur `sensor` et `binary_sensor`, mais le pipeline complet ne publie aucun equipement de ces types vers HA. Causes confirmees par audit code (correct-course du 2026-04-30) :
- aucun `SensorMapper` ni `BinarySensorMapper` dans `resources/daemon/mapping/` (3 mappers seulement : light, cover, switch)
- aucune methode `publish_sensor` / `publish_binary_sensor` cote publisher
- dispatch `resources/daemon/transport/http_server.py:1031-1224` = 3 elif hardcodes par type, avec skip silencieux ligne 1047 si aucun mapper ne matche
- la regle §11 du cadrage initial (« degradation elegante : publier en sensor/button par defaut plutot que skip silencieux quand le typage Jeedom permet une projection structurellement valide ») n'a jamais ete cablee

Cette dette est traitee dans deux nouveaux epics ouverts par le SCP du 2026-04-30 :
- `pe-epic-8` — refactor dispatch + registry-driven (zero nouveau comportement, gate golden-file)
- `pe-epic-9` — vague 1 d'extension reelle (mappers + publishers + `FallbackMapper` §11 terminal)

**Regle de fond reaffirmee** : « publier en degradation elegante plutot qu'en skip silencieux ; n'omettre que quand aucune projection structurellement valide n'existe » (cadrage `docs/cadrage_plugin_jeedom_ha_bmad.md` §11). Cette regle n'etait pas une option — c'etait une promesse cadrage non traduite en backlog. Elle devient story-level dans `pe-epic-9`.

**Aucune reprise de developpement ne repart d'Epic 7.** Les stories 7.1-7.4 restent done. La story 7.5 ne s'execute plus dans cet epic.

### Story 7.1 : Enrichissement additif du contrat 4D — `projection_validity` est expose de bout en bout sans regression sur le schema canonique
```

**Rationale** : acte la cloture officielle d'Epic 7 sur ce qu'il a reellement livre (gouvernance + `projection_validity`), sans falsifier le tracker. Documente la dette structurelle (3 elif hardcodes + skip silencieux + regle §11 absente) et la re-home explicitement vers pe-epic-8/pe-epic-9, plutot que de la masquer. Calque le pattern precedent (correct-course 2026-04-22 sur Epic 6) : note de disposition en HEAD d'epic, tracabilite audit. Reintroduit la regle §11 du cadrage initial comme principe de fond. Empeche un futur agent BMAD de relancer 7.5 dans Epic 7 ou de recommencer une story de gouvernance deja livree.

---

### 5.2 — Ajout pe-epic-8 « Refactor dispatch + registry-driven »

**Artifact** : `_bmad-output/planning-artifacts/epics-projection-engine.md`
**Section** : nouvelle section apres les Dev notes de Story 7.5 (fin actuelle de l'Epic 7)

**OLD** (lignes 1120-1123 actuelles, fin de l'Epic 7)

```md
**Dev notes :**
- FR32 / FR33 reappliques uniquement aux surfaces reelles ouvertes par l'epic
- aucun retour a un CTA speculatif du type "choisir manuellement le type"
- la story ne promet pas de remediation generique hors vague cible
```

**NEW**

```md
**Dev notes :**
- FR32 / FR33 reappliques uniquement aux surfaces reelles ouvertes par l'epic
- aucun retour a un CTA speculatif du type "choisir manuellement le type"
- la story ne promet pas de remediation generique hors vague cible

---

## Epic 8 — Refactor dispatch et registry-driven publishers (zero nouveau comportement)

Le pipeline actuel hardcode la cascade `LightMapper -> CoverMapper -> SwitchMapper` et trois elif de publication par type dans `resources/daemon/transport/http_server.py:1031-1224`. Cette structure interdit toute extension a sensor/binary_sensor (deja gouvernes dans `PRODUCT_SCOPE` apres Story 7.4) et a tout type futur sans dupliquer ~50 lignes par ajout. Cet epic refactore le dispatch en registry-driven, conserve strictement le comportement 1:1 sur les types existants, et reserve un slot terminal `FallbackMapper` cable mais no-op pour que `pe-epic-9` n'ait qu'a y brancher la regle §11 du cadrage initial sans retoucher la chaine.

**Cadre de garantie** : aucune story de cet epic n'introduit un nouveau type publie, n'ouvre `PRODUCT_SCOPE`, ni ne modifie `cause_action` / `cause_label` / `reason_code`. Le diagnostic, le contrat 4D, les counters et les decisions de publication doivent rester strictement identiques sur les 30 equipements de reference (gate golden-file Story 8.4). Si un test golden-file revele un drift, le refactor revient en arriere ; il n'est pas autorise a "ameliorer" accidentellement un comportement existant.

### Story 8.1 : MapperRegistry — dispatch deterministe et slot terminal reserve

En tant que mainteneur,
je veux un `MapperRegistry` qui enregistre les mappers HA dans un ordre deterministe et reserve explicitement un slot terminal pour un futur `FallbackMapper`,
afin de remplacer la cascade hardcodee `LightMapper -> CoverMapper -> SwitchMapper` par une iteration registry-driven sans introduire de nouveau comportement.

**Acceptance Criteria :**

**Given** le registre des mappers
**When** il est inspecte au demarrage du daemon
**Then** il contient dans cet ordre exact : `LightMapper`, `CoverMapper`, `SwitchMapper`, `FallbackMapper` (terminal)

**Given** le `FallbackMapper` est appele dans cet epic
**When** son resultat est inspecte
**Then** il retourne `None` systematiquement (slot cable, comportement reel ouvert dans `pe-epic-9`)

**Given** une iteration registry-driven sur un equipement eligible
**When** elle est comparee a la cascade hardcodee actuelle sur les 30 equipements de reference
**Then** le mapper qui produit un mapping non-`None` est strictement le meme dans les deux paths

**Dev notes :**
- AR3 / FR15 (faire evoluer les regles de mapping sans modifier l'ordre canonique des etapes)
- aucun changement comportemental cote light, cover, switch
- le slot `FallbackMapper` est cable dans le registre mais retourne `None` ; toute logique reelle appartient a `pe-epic-9`
- pas de modification de `PRODUCT_SCOPE` ni de `HA_COMPONENT_REGISTRY` dans cette story

---

### Story 8.2 : PublisherRegistry — dispatch table `ha_entity_type` -> methode publish

En tant que mainteneur,
je veux un `PublisherRegistry` qui mappe un `ha_entity_type` vers la methode `publish_*` correspondante du `DiscoveryPublisher`,
afin de remplacer les trois elif hardcodes de `_run_sync` par une dispatch table extensible.

**Acceptance Criteria :**

**Given** le registre des publishers
**When** il est inspecte au demarrage du daemon
**Then** il contient au moins les entrees `light -> publish_light`, `cover -> publish_cover`, `switch -> publish_switch`

**Given** un `mapping.ha_entity_type` connu
**When** la methode publish correspondante est resolue via le registre
**Then** elle est strictement la meme que celle invoquee par la branche elif actuelle pour ce type

**Given** un `mapping.ha_entity_type` inconnu du registre
**When** la resolution est tentee
**Then** elle echoue de facon explicite et non silencieuse, et la non-publication est tracee comme un defaut de couverture publisher (pas comme un skip silencieux)

**Dev notes :**
- AR3 / FR27 (resultat publication separe de la decision)
- aucun nouveau publisher cree dans cette story
- l'echec sur type inconnu doit produire un log d'erreur clair et un `publication_result` non-`success`, pas un `continue` discret
- les types `sensor` / `binary_sensor` (deja dans `PRODUCT_SCOPE`) ne sont pas ajoutes dans cette story ; ils seront ajoutes par `pe-epic-9` au moment ou les publishers correspondants existeront

---

### Story 8.3 : Refactor `http_server._run_sync` — boucle dispatch unique et compteurs generiques

En tant que mainteneur,
je veux une boucle de dispatch unique dans `_run_sync` qui delegue mapping et publication aux deux registries,
afin que l'ajout d'un nouveau type HA ne necessite plus de modifier `http_server.py`.

**Acceptance Criteria :**

**Given** la fonction `_run_sync` apres refactor
**When** son code est inspecte
**Then** la cascade `LightMapper -> CoverMapper -> SwitchMapper` (lignes 1040-1047 actuelles) est remplacee par une iteration `mapper_registry`
**And** les trois branches `elif mapping.ha_entity_type == "light" / "cover" / "switch"` (lignes 1072 / 1124 / 1175 actuelles) sont remplacees par une seule branche generique qui resout publish via `publisher_registry`

**Given** la structure `mapping_counters`
**When** elle est inspectee apres refactor
**Then** elle est generee dynamiquement par `ha_entity_type` (un quadruplet `<type>_sure / probable / ambiguous / published / skipped` par type connu du registre) au lieu d'etre hardcodee sur `lights_*` / `covers_*` / `switches_*`

**Given** les 30 equipements de reference (snapshot pre-refactor)
**When** une sync est executee post-refactor
**Then** chaque equipement a strictement le meme `mapping`, `decision`, `publication_result`, `cause_label`, `cause_action`, `reason_code`, et la meme entree dans `mapping_counters`

**Dev notes :**
- aucune modification de `decide_publication` (etape 4)
- aucune modification de `validate_projection` (etape 3)
- aucune modification de `cause_mapping`
- les counters sont alimentes par le meme enum d'`ha_entity_type` que le registry, pas par des cles hardcodees
- la cascade est remplacee, pas etendue : si un nouveau mapper est ajoute, il l'est par le registre, pas par modification de cette boucle

---

### Story 8.4 : Gate golden-file de non-regression sur 30 equipements de reference

En tant que mainteneur,
je veux un test golden-file qui compare snapshot publication + diagnostic avant et apres refactor sur un corpus reproductible de 30 equipements,
afin que `pe-epic-8` ne puisse cloturer que si la parite comportementale est strictement preservee.

**Acceptance Criteria :**

**Given** un corpus reproductible de 30 equipements de reference (light, cover, switch + cas ambigus + cas non-eligibles + cas eligibles bloques par scope ou par validation HA)
**When** une sync complete est executee sur ce corpus avant et apres le refactor
**Then** la sortie diagnostic complete (mapping, decision, publication_result, contrat 4D, counters) est strictement identique entre les deux runs

**Given** un drift est detecte par le golden-file
**When** la story 8.4 est revue
**Then** la cloture de l'epic est bloquee tant que la parite n'est pas restauree
**And** aucune justification de type "amelioration accidentelle" n'est acceptable dans cet epic

**Given** le test golden-file
**When** il est ajoute a la suite CI
**Then** il s'execute sur chaque PR future qui touche `mapping/`, `transport/`, `discovery/` ou `validation/`
**And** il devient la baseline de regression-control utilisee par toutes les stories de `pe-epic-9`

**Dev notes :**
- gate de cloture epic-level
- corpus de 30 equipements stocke comme fixture deterministe sous `resources/daemon/tests/fixtures/golden_corpus/` (pas de mock random)
- la fixture inclut au minimum : 10 lights, 8 covers, 5 switches, 3 ambigus, 2 non-eligibles, 2 valides bloques par scope

---

### Gates epic-level pe-epic-8

- aucune story ne modifie `PRODUCT_SCOPE` ;
- aucune story n'introduit un nouveau type publie cote HA ;
- aucune story ne modifie `cause_label`, `cause_action`, `reason_code` ou la hierarchie des causes ;
- toute story qui touche au dispatch est gardee par le golden-file 8.4 ;
- la cloture epic exige que les 30 equipements de reference produisent une sortie strictement identique avant et apres refactor.
```

**Rationale** : refactor PUR, 4 stories scopees au minimum operable, aucune n'ouvre de comportement. Slot `FallbackMapper` terminal reserve mais retourne `None` (pe-epic-8 prevoit le slot, pe-epic-9 le remplit). Gate golden-file Story 8.4 = gate de cloture epic + baseline regression reutilisee par pe-epic-9. Counters dynamiques (Story 8.3) necessaire pour eviter de patcher http_server.py en pe-epic-9. Mention explicite que sensor/binary_sensor (deja dans PRODUCT_SCOPE apres 7.4) ne sont pas ajoutes dans pe-epic-8 → pas de drift de scope.

---

### 5.3 — Ajout pe-epic-9 « Vague 1 d'extension reelle + FallbackMapper §11 »

**Artifact** : `_bmad-output/planning-artifacts/epics-projection-engine.md`
**Section** : nouvelle section apres les Gates epic-level pe-epic-8

**OLD** (dernier bloc ajoute par 5.2)

```md
### Gates epic-level pe-epic-8

- aucune story ne modifie `PRODUCT_SCOPE` ;
- aucune story n'introduit un nouveau type publie cote HA ;
- aucune story ne modifie `cause_label`, `cause_action`, `reason_code` ou la hierarchie des causes ;
- toute story qui touche au dispatch est gardee par le golden-file 8.4 ;
- la cloture epic exige que les 30 equipements de reference produisent une sortie strictement identique avant et apres refactor.
```

**NEW**

```md
### Gates epic-level pe-epic-8

- aucune story ne modifie `PRODUCT_SCOPE` ;
- aucune story n'introduit un nouveau type publie cote HA ;
- aucune story ne modifie `cause_label`, `cause_action`, `reason_code` ou la hierarchie des causes ;
- toute story qui touche au dispatch est gardee par le golden-file 8.4 ;
- la cloture epic exige que les 30 equipements de reference produisent une sortie strictement identique avant et apres refactor.

---

## Epic 9 — Vague 1 d'extension reelle : sensor / binary_sensor / button + degradation elegante terminale

`PRODUCT_SCOPE` etait gouverne ouvert sur `sensor` et `binary_sensor` depuis Story 7.4, mais aucun equipement de ces types n'arrivait reellement dans Home Assistant car ni mappers ni publishers correspondants n'existaient. Cet epic livre la **premiere vague de publication reelle** alimentee par `_bmad-output/planning-artifacts/ha-projection-reference.md` (extraction officielle de `docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx`, 2026-04-30) et cable enfin la regle §11 du cadrage initial : « degradation elegante en sensor/button par defaut plutot que skip silencieux quand le typage Jeedom permet une projection structurellement valide ». La vague est volontairement bornee : seuls `sensor`, `binary_sensor` et `button` sont introduits ici ; `number`, `select`, `climate` et le reste des 31 composants HA documentes par l'Excel restent hors-vague.

**Pre-requis** : `pe-epic-8` clos (`MapperRegistry` + `PublisherRegistry` + slot `FallbackMapper` no-op + golden-file 8.4 verts sur 30 equipements de reference).

**Source de verite** : `_bmad-output/planning-artifacts/ha-projection-reference.md`. Les `required_fields` de `sensor.mqtt`, `binary_sensor.mqtt` et `button.mqtt` extraits du fichier `HA_MQTT_Required_Fields` (77 contraintes au total) servent de contrat operationnel pour les nouveaux mappers et la validation projection deja gouvernee en Story 7.3.

**Cadre** : aucune story de cet epic n'ouvre `PRODUCT_SCOPE` au-dela de `["light", "cover", "switch", "sensor", "binary_sensor", "button"]`. L'ajout de `button` dans `PRODUCT_SCOPE` se fait dans Story 9.3 sous gate FR40 / NFR10 conformement a la regle de gouvernance posee par Story 7.4. Les counters golden-file de Story 8.4 sont etendus aux nouveaux types ; la non-regression sur le corpus initial reste exigee.

### Story 9.1 : SensorMapper + publish_sensor — Info numeric et capteurs simples

En tant que mainteneur,
je veux un `SensorMapper` qui projette les commandes Jeedom de type `Info` numeric (temperature, humidite, puissance, luminosite, etc.) en entite HA `sensor`,
afin que les capteurs simples deja typés correctement dans Jeedom apparaissent automatiquement dans Home Assistant.

**Acceptance Criteria :**

**Given** un eqLogic Jeedom avec au moins une commande Info numeric typee (TEMPERATURE, HUMIDITY, POWER, ENERGY, etc.)
**When** le `SensorMapper` est invoque dans la cascade registry-driven
**Then** un `MappingResult` non-`None` est produit avec `ha_entity_type = "sensor"`, `state_topic` derive de la commande source, `device_class` resolu par le type generique, et `unit_of_measurement` resolu par le sous-type

**Given** le mapping issu de `SensorMapper`
**When** il passe par `validate_projection()` (Story 3.2 + Story 7.3)
**Then** `is_valid = True` sur les cas nominaux derives de `ha-projection-reference.md` (required_fields = `availability > keys > topic`, `platform`, `state_topic`)

**Given** la methode `publish_sensor` du `DiscoveryPublisher`
**When** elle est appelee sur un mapping sensor valide
**Then** elle produit un payload MQTT Discovery conforme a la documentation officielle HA (`sensor.mqtt`)
**And** elle est enregistree dans `PublisherRegistry` sous la cle `sensor`

**Given** le golden-file 8.4
**When** il est etendu avec 5 equipements sensor representatifs
**Then** la non-regression du corpus initial (30 equipements) reste verte

**Dev notes :**
- AR3 / AR4 / FR11 / FR16 / FR26
- mapping des types generiques Jeedom Info numeric -> HA `device_class` est table-driven, derive de `Jeedom_Generic_Types` de l'Excel reference
- aucun `cause_action` introduit dans cette story (la story 9.5 re-homee depuis 7.5 traite les CTA)

---

### Story 9.2 : BinarySensorMapper + publish_binary_sensor — Info binary (presence, ouverture, fuite, ...)

En tant que mainteneur,
je veux un `BinarySensorMapper` qui projette les commandes Jeedom de type `Info` binary (presence, ouverture, fuite, mouvement, etc.) en entite HA `binary_sensor`,
afin que les capteurs binaires correctement typés en Jeedom apparaissent automatiquement dans Home Assistant.

**Acceptance Criteria :**

**Given** un eqLogic Jeedom avec au moins une commande Info dont le sous-type est `binary` (PRESENCE, OPENING, SMOKE, FLOOD, MOTION, etc.)
**When** le `BinarySensorMapper` est invoque dans la cascade
**Then** un `MappingResult` non-`None` est produit avec `ha_entity_type = "binary_sensor"`, `state_topic` derive, `device_class` resolu par le type generique

**Given** le mapping issu de `BinarySensorMapper`
**When** il passe par `validate_projection()`
**Then** `is_valid = True` sur cas nominaux conformes a `ha-projection-reference.md` (required_fields = `availability > keys > topic`, `platform`, `state_topic`)

**Given** la methode `publish_binary_sensor` du `DiscoveryPublisher`
**When** elle est appelee sur un mapping valide
**Then** elle produit un payload MQTT Discovery conforme a `binary_sensor.mqtt`
**And** elle est enregistree dans `PublisherRegistry` sous la cle `binary_sensor`

**Given** un equipement portant a la fois des Info numeric et des Info binary
**When** la cascade registry-driven est executee
**Then** l'ordre `BinarySensorMapper` < `SensorMapper` est determine de facon deterministe par le contenu du registre (decision documentee story-level en consensation avec l'architecte avant implementation)

**Dev notes :**
- AR3 / AR4 / FR11 / FR16 / FR26
- 5 equipements binary_sensor representatifs ajoutes au golden-file 8.4
- la coexistence Info numeric + Info binary sur un meme equipement releve d'une regle de priorite story-level a documenter dans la story file (pas hardcodee)

---

### Story 9.3 : ButtonMapper + publish_button + ouverture `button` dans PRODUCT_SCOPE sous FR40 / NFR10

En tant que mainteneur,
je veux un `ButtonMapper` qui projette les commandes Jeedom Action ponctuelles (sans etat persistent, ex. scenarios run, commandes one-shot) en entite HA `button`,
afin que les actions discretes Jeedom soient declenchables depuis Home Assistant.

**Acceptance Criteria :**

**Given** un eqLogic Jeedom avec au moins une commande Action ponctuelle non couverte par light/cover/switch (ex. scenario, action one-shot)
**When** le `ButtonMapper` est invoque dans la cascade
**Then** un `MappingResult` non-`None` est produit avec `ha_entity_type = "button"`, `command_topic` derive

**Given** la methode `publish_button` du `DiscoveryPublisher`
**When** elle est appelee sur un mapping valide
**Then** elle produit un payload MQTT Discovery conforme a `button.mqtt`
**And** elle est enregistree dans `PublisherRegistry` sous la cle `button`

**Given** la modification `PRODUCT_SCOPE += ["button"]`
**When** elle est revue par les gates FR40 / NFR10
**Then** elle inclut dans le meme increment : entree `button` deja presente dans `HA_COMPONENT_REGISTRY` (Story 7.2), preuves nominales et d'echec `validate_projection()` pour `button`, test de non-regression diagnostic, golden-file 8.4 etendu

**Given** une tentative d'ajout a `PRODUCT_SCOPE` sans ces preuves dans le meme increment
**When** la suite FR40 / NFR10 est executee
**Then** l'ajout est rejete (regle de gouvernance posee par Story 7.4)

**Dev notes :**
- AR13 / FR39 / FR40 / NFR10
- story unique de pe-epic-9 autorisee a modifier `PRODUCT_SCOPE`
- 3 equipements button representatifs ajoutes au golden-file 8.4 (incluant scenario Jeedom)
- la decision d'inclure `button` dans la vague 1 (vs la repousser) est arbitree par le besoin de couverture des scenarios cite dans cadrage §5

---

### Story 9.4 : FallbackMapper §11 — degradation elegante terminale (publier sensor/button par defaut plutot que skip silencieux)

En tant qu'utilisateur,
je veux que les equipements Jeedom dont le typage permet une projection structurellement valide (au moins une commande Info ou une commande Action) soient publies par defaut en `sensor` ou `button` plutot qu'omis silencieusement,
afin de tenir la promesse §11 du cadrage initial : « degradation elegante : sensor/button plutot qu'un type 'riche' incorrect ».

**Acceptance Criteria :**

**Given** un eqLogic Jeedom eligible
**When** aucun mapper specifique (Light, Cover, Switch, BinarySensor, Sensor, Button) n'a produit de `MappingResult` non-`None`
**Then** le `FallbackMapper` (slot terminal cable en Story 8.1) est invoque

**Given** un eqLogic Jeedom avec au moins une commande `Info` non typee specifiquement
**When** le `FallbackMapper` est invoque
**Then** il produit un `MappingResult` `ha_entity_type = "sensor"` avec `confidence = "ambiguous"`, `state_topic` derive de la commande Info la plus exploitable, `cause_code = "fallback_sensor_default"`

**Given** un eqLogic Jeedom avec au moins une commande `Action` non typee specifiquement et sans Info exploitable
**When** le `FallbackMapper` est invoque
**Then** il produit un `MappingResult` `ha_entity_type = "button"` avec `confidence = "ambiguous"`, `command_topic` derive de la commande Action la plus exploitable, `cause_code = "fallback_button_default"`

**Given** un eqLogic Jeedom sans aucune commande Info ni Action exploitable
**When** le `FallbackMapper` est invoque
**Then** il retourne `None`
**And** le diagnostic expose `cause_code = "no_projection_possible"` (pas un skip silencieux)

**Given** tout `MappingResult` produit par le `FallbackMapper` (sensor, button, ou retour `None`)
**When** son `cause_action` est inspecte
**Then** `cause_action = None` strictement, sans exception
**And** aucun CTA utilisateur n'est expose pour les equipements degrades en fallback (regle Epic 6 « no faux CTA » verrouillee Story 6.3)

**Given** un mapping issu du `FallbackMapper`
**When** il passe par `validate_projection()`
**Then** `is_valid` reflete fidelement la realite structurelle (un fallback peut etre invalide HA et c'est traitable explicitement, pas masque)

**Given** le diagnostic d'un equipement projete par `FallbackMapper`
**When** il est inspecte
**Then** `cause_label` indique clairement « projection en degradation elegante » et la confiance reste `ambiguous` pour signaler a l'utilisateur que le typage Jeedom pourrait etre ameliore

**Dev notes :**
- regle §11 du cadrage initial (`docs/cadrage_plugin_jeedom_ha_bmad.md`) enfin cablee story-level
- aucun retour au skip silencieux ligne 1047 du `_run_sync` historique
- 5 equipements de fallback ajoutes au golden-file 8.4 (cas Info sans typage, cas Action sans typage, cas rien d'exploitable)
- le `FallbackMapper` n'ouvre pas de nouveau type cote `PRODUCT_SCOPE` : il s'appuie uniquement sur `sensor` et `button` deja ouverts (Stories 7.4 et 9.3)
- la confiance `ambiguous` permet de filtrer ces cas en diagnostic et d'indiquer une remediation utilisateur via la story 9.5 (« completer le typage Jeedom ») seulement quand cette remediation est reellement actionnable — par defaut, `cause_action = None`
- conformite stricte avec la regle Epic 6 « no faux CTA » (Story 6.3) : aucun cause_action expose tant qu'aucune surface reelle ne le justifie ; cette story ne change pas cette posture, elle l'applique a la nouvelle classe d'equipements degrades
- les trois nouveaux cause_codes (`fallback_sensor_default`, `fallback_button_default`, `no_projection_possible`) sont ajoutes a `cause_mapping.py` selon la convention de centralisation introduite par Epic 4 du cycle V1.1 Pilotable et reaffirmee Story 6.3 (cause_code -> cause_label / cause_action canoniques) ; aucun string literal cause_code disperse dans le code des mappers ou du publisher
- ces trois cause_codes restent stables dans le contrat backend (`reason_code` / `cause_code`) et leur traduction UI (`cause_label`) suit la regle FR32 etablie par Epic 6 (cause_label toujours non-null)

---

### Gates epic-level pe-epic-9

- chaque ouverture de type dans `PRODUCT_SCOPE` (Story 9.3 pour `button`) respecte FR40 / NFR10 dans le meme increment ;
- le golden-file 8.4 reste vert sur le corpus initial de 30 equipements + s'etend aux nouveaux equipements de la vague 1 ;
- gate terrain de cloture epic = comptage des **nouveaux equipements publies** sur la box reelle d'Alexandre, decompose par type (`sensor`, `binary_sensor`, `button`) et par mapper d'origine (specifique vs `FallbackMapper`), avec ratio « publie / eligible » document story-par-story ;
- aucune story n'introduit `number`, `select`, `climate` ou tout autre type hors vague 1 ;
- la regle §11 du cadrage est verrouillee dans Story 9.4 et ne peut plus etre re-introduite sous forme de skip silencieux ;
- la story 9.5 (re-homee depuis 7.5, voir change proposal 5.4 du SCP du 2026-04-30) cloture l'epic sur l'exposition de CTA limites aux surfaces reellement ouvertes par cette vague.

---

### Note sur les vagues suivantes (hors scope pe-epic-9)

`ha-projection-reference.md` documente 31 composants HA officiels au total ; la vague 1 en couvre 3 nouveaux (`sensor`, `binary_sensor`, `button`), les 3 historiques restant (`light`, `cover`, `switch`). Les 25 composants restants — dont `number`, `select`, `climate` cites dans le PRD V1.1 axe 6 — relevent de **vagues ulterieures** (`pe-epic-10+`) qui s'appuieront sur la meme infrastructure dispatch + registry + golden-file mise en place par `pe-epic-8` et alimentees par le meme `ha-projection-reference.md`. L'ouverture sequentielle reste gouvernee story-par-story sous FR40 / NFR10.
```

**Rationale** : 4 stories produit dans pe-epic-9 + une 5eme (re-homed 7.5) introduite par la proposition 5.4 separee. Ordre de cascade dans le `MapperRegistry` apres vague 1 : `Light → Cover → Switch → BinarySensor → Sensor → Button → Fallback` (deterministe). `BinarySensor < Sensor` car les commandes Info binary doivent matcher avant les Info numeriques. Le `FallbackMapper` reste **terminal** comme demande. Story 9.4 cable enfin la regle §11 du cadrage avec contrat clair (Info → sensor ambigu, Action → button ambigu, rien → None avec `no_projection_possible`). Story 9.3 est la **seule** story autorisee a modifier `PRODUCT_SCOPE`. Note explicite sur les vagues suivantes (25 composants restants) pour empecher tout drift de scope opportuniste. Gate terrain = comptage nouveaux publies. Aucune story n'introduit de CTA dans pe-epic-9 hors la 9.5 re-homee — la regle « no faux CTA » de Story 6.3 reste verrouillee.

---

### 5.4 — Re-homing Story 7.5 → pe-epic-9 Story 9.5

**Artifact** : `_bmad-output/planning-artifacts/epics-projection-engine.md`

Cette proposition modifie deux sections du meme fichier.

#### 5.4a — Modifier la disposition de Story 7.5 (la marquer re-homed)

**Section** : `### Story 7.5 : Exposition d'actions utilisateur uniquement sur les surfaces reelles et supportees`

**OLD** (lignes 1099-1123 actuelles)

```md
### Story 7.5 : Exposition d'actions utilisateur uniquement sur les surfaces reelles et supportees

En tant qu'utilisateur,
je veux voir une action seulement lorsqu'elle correspond a une remediation reellement disponible dans jeedom2ha ou Jeedom standard,
afin que le diagnostic reste honnete et utile apres l'ouverture produit.

**Acceptance Criteria :**

**Given** un equipement de la vague ouverte avec une remediation effectivement disponible
**When** le diagnostic est affiche
**Then** `cause_action` pointe vers cette action reelle, executable et supportee

**Given** un equipement pour lequel aucune remediation utilisateur directe n'existe
**When** le diagnostic est affiche
**Then** `cause_action` reste `null`
**And** la couche d'affichage conserve le message standardise sans faux CTA

**Given** une story touchant `cause_action` pour la vague ouverte
**When** elle est validee
**Then** elle passe un gate terrain `no faux CTA` sur des cas reels representatifs de la vague

**Dev notes :**
- FR32 / FR33 reappliques uniquement aux surfaces reelles ouvertes par l'epic
- aucun retour a un CTA speculatif du type "choisir manuellement le type"
- la story ne promet pas de remediation generique hors vague cible
```

**NEW**

```md
### Story 7.5 (re-homee 2026-04-30 vers `pe-epic-9` Story 9.5) — artefact historique

**Statut** : `historical-artifact-rehomed`
**Epic d'origine** : `pe-epic-7` — L'actionnabilite devient une capacite produit reelle par ouverture gouvernee
**Disposition BMAD** : story re-homee vers `pe-epic-9` Story 9.5

#### Correct-course 2026-04-30 — Disposition opposable

- Cette story n'est plus un item executable du backlog actif de `pe-epic-7`.
- L'audit du correct-course du 2026-04-30 a montre que sa promesse — exposer des CTA seulement sur des surfaces reelles — ne pouvait pas etre tenue dans `pe-epic-7` car aucune publication reelle de `sensor` / `binary_sensor` n'existait : le `PRODUCT_SCOPE` etait gouverne ouvert mais aucun mapper ni publisher ne livrait d'equipement de ces types.
- La capacite est re-homee vers `pe-epic-9` sous forme de **Story 9.5 — Exposition d'actions utilisateur sur les surfaces reellement ouvertes par la vague 1**, executee apres livraison effective des Stories 9.1 a 9.4 (`SensorMapper` + `BinarySensorMapper` + `ButtonMapper` + `FallbackMapper`).
- Aucun developpement supplementaire ne doit repartir de cette section.
- Le contenu original (acceptance criteria + dev notes) est conserve sous forme historique ci-dessous comme reference de l'intention initiale ; il n'est pas le contrat actif.

##### Contenu original (reference historique uniquement)

> En tant qu'utilisateur,
> je voulais voir une action seulement lorsqu'elle correspond a une remediation reellement disponible dans jeedom2ha ou Jeedom standard,
> afin que le diagnostic reste honnete et utile apres l'ouverture produit.
>
> AC originaux : `cause_action` pointe vers une remediation reelle si elle existe, `null` sinon ; gate terrain `no faux CTA` ; FR32 / FR33 reappliques uniquement aux surfaces reelles ouvertes ; aucun CTA speculatif.
>
> Ces criteres restent valides en intention et sont repris explicitement dans Story 9.5 de `pe-epic-9`, mais pour la vague 1 effectivement ouverte (sensor / binary_sensor / button) plutot qu'une vague abstraite.
```

#### 5.4b — Ajouter Story 9.5 dans pe-epic-9 (juste apres Story 9.4)

**Section** : `## Epic 9 — ...`, juste apres les Dev notes de Story 9.4 et avant `### Gates epic-level pe-epic-9`

**OLD** (derniere partie de Story 9.4 introduite par change proposal 5.3)

```md
- les trois nouveaux cause_codes (`fallback_sensor_default`, `fallback_button_default`, `no_projection_possible`) sont ajoutes a `cause_mapping.py` selon la convention de centralisation introduite par Epic 4 du cycle V1.1 Pilotable et reaffirmee Story 6.3 (cause_code -> cause_label / cause_action canoniques) ; aucun string literal cause_code disperse dans le code des mappers ou du publisher
- ces trois cause_codes restent stables dans le contrat backend (`reason_code` / `cause_code`) et leur traduction UI (`cause_label`) suit la regle FR32 etablie par Epic 6 (cause_label toujours non-null)

---

### Gates epic-level pe-epic-9
```

**NEW**

```md
- les trois nouveaux cause_codes (`fallback_sensor_default`, `fallback_button_default`, `no_projection_possible`) sont ajoutes a `cause_mapping.py` selon la convention de centralisation introduite par Epic 4 du cycle V1.1 Pilotable et reaffirmee Story 6.3 (cause_code -> cause_label / cause_action canoniques) ; aucun string literal cause_code disperse dans le code des mappers ou du publisher
- ces trois cause_codes restent stables dans le contrat backend (`reason_code` / `cause_code`) et leur traduction UI (`cause_label`) suit la regle FR32 etablie par Epic 6 (cause_label toujours non-null)

---

### Story 9.5 (re-homee depuis Story 7.5 le 2026-04-30) : Exposition d'actions utilisateur sur les surfaces reellement ouvertes par la vague 1

En tant qu'utilisateur,
je veux voir une action seulement lorsqu'elle correspond a une remediation reellement disponible apres l'ouverture de la vague 1 (`sensor`, `binary_sensor`, `button`),
afin que le diagnostic reste honnete et utile une fois que la vague 1 est en production.

**Pre-requis story-level** : Stories 9.1, 9.2, 9.3 et 9.4 closes ; le golden-file 8.4 reste vert ; la vague 1 est effectivement publiee sur la box reelle d'Alexandre (gate terrain comptage epic-level 9 atteint).

**Acceptance Criteria :**

**Given** un equipement publie en `sensor` / `binary_sensor` / `button` par un mapper specifique (Stories 9.1, 9.2, 9.3) avec une remediation reellement disponible (ex. corriger un `device_class` errone, completer un sous-type Jeedom)
**When** le diagnostic est affiche
**Then** `cause_action` pointe vers cette remediation reelle, executable et supportee
**And** `cause_label` decrit la cause en langage produit conforme FR32

**Given** un equipement publie en `sensor` ou `button` par le `FallbackMapper` (Story 9.4) avec une remediation reellement disponible (« completer le typage generique Jeedom »)
**When** le diagnostic est affiche
**Then** `cause_action` pointe vers la remediation explicite « completer le typage Jeedom » (single specific action)
**And** la confiance reste `ambiguous`

**Given** un equipement de la vague 1 pour lequel aucune remediation utilisateur directe n'existe (ex. limitation HA externe, contrainte structurelle non remediable)
**When** le diagnostic est affiche
**Then** `cause_action` reste `null`
**And** `cause_label` est non-null et explicite (FR32) — la couche d'affichage conserve le message standardise sans faux CTA

**Given** un equipement hors vague 1 (type non encore ouvert dans `PRODUCT_SCOPE`)
**When** le diagnostic est affiche
**Then** la story 9.5 ne modifie ni `cause_label` ni `cause_action` pour cet equipement
**And** la regle « no faux CTA » de Story 6.3 reste verrouillee

**Given** un changement story-level touchant `cause_action` pour la vague 1
**When** la story est validee
**Then** elle passe un gate terrain `no faux CTA` sur des cas reels representatifs de la vague 1 (au minimum 5 sensor, 5 binary_sensor, 3 button, 5 fallback) sur la box reelle d'Alexandre

**Dev notes :**
- FR32 / FR33 appliques uniquement aux surfaces reelles ouvertes par la vague 1 (Stories 9.1, 9.2, 9.3, 9.4)
- aucune extension a `number`, `select`, `climate` ou aux types hors vague 1
- aucun retour a un CTA speculatif du type « choisir manuellement le type »
- conservation stricte de la posture Epic 6 « no faux CTA » : tout doute sur la reelle disponibilite d'une remediation entraine `cause_action = null`
- les nouveaux cause_action introduits dans cette story (typiquement « completer le typage Jeedom ») sont centralises dans `cause_mapping.py` selon la convention Epic 4 V1.1 et Story 6.3
- cloture epic-level pe-epic-9 conditionnee a la cloture de cette story apres gate terrain PASS

---

### Gates epic-level pe-epic-9
```

**Rationale** : 5.4a marque 7.5 comme `historical-artifact-rehomed` selon le pattern du SCP 2026-04-22 (re-homing 6.2). Conserve l'intention historique mais retire la story du backlog executable. 5.4b ajoute Story 9.5 dans pe-epic-9 comme **derniere story de l'epic** (cloture conditionnee). Reformule l'intention sur la **vague 1 effectivement ouverte** plutot qu'une vague abstraite. Pre-requis story-level explicite (9.1-9.4 closes avant demarrage). Verrouillage Epic 6 « no faux CTA ». Gate terrain 5+5+3+5 = 18 cas reels minimum. Centralisation cause_action dans `cause_mapping.py`.

---

### 5.5 — Mise a jour `sprint-status.yaml`

**Artifact** : `_bmad-output/implementation-artifacts/sprint-status.yaml`

#### 5.5a — Mise a jour du commentaire de tete `# CYCLES:`

**OLD**

```yaml
# Cycle Moteur de Projection Explicable — CYCLE COURANT
#   Source: epics-projection-engine.md | Démarré: 2026-04-10
#   Epics: pe-epic-1 à pe-epic-7 (22 stories — pe-epic-1/2/3/4/5/6 done, pe-epic-7 backlog)
#   Objectif: Pipeline canonique à 5 étapes, moteur de projection explicable,
#             registre HA gouverné à 3 états, diagnostic explicable et actionnable,
#             puis actionnabilite produit ouverte de facon gouvernee
```

**NEW**

```yaml
# Cycle Moteur de Projection Explicable — CYCLE COURANT
#   Source: epics-projection-engine.md | Démarré: 2026-04-10
#   Epics: pe-epic-1 à pe-epic-9 (post correct-course 2026-04-30 :
#          pe-epic-1/2/3/4/5/6/7 done, pe-epic-8/9 backlog)
#   Objectif: Pipeline canonique à 5 étapes, moteur de projection explicable,
#             registre HA gouverné à 3 états, diagnostic explicable et actionnable,
#             actionnabilite produit gouvernee, refactor dispatch registry-driven,
#             premiere vague d'extension reelle (sensor / binary_sensor / button)
#             alimentee par ha-projection-reference.md et degradation elegante §11
```

#### 5.5b — Mise a jour du bloc pe-epic-7 + ajout pe-epic-8 + pe-epic-9

**OLD**

```yaml
  pe-epic-7: in-progress  # story 7.1 creee ready-for-dev le 2026-04-23 ; epic actif selon le sequencing approuve du 2026-04-22
  7-1-enrichissement-additif-du-contrat-4d-projection-validity-est-expose-de-bout-en-bout-sans-regression-sur-le-schema-canonique: done
  7-2-vague-cible-ha-les-types-candidats-sont-modelises-dans-le-registre-comme-connus-avec-contraintes-explicites-et-perimetre-borne: done  # PR #103 mergée 2026-04-27 (065df16)
  7-3-validation-de-projection-de-la-vague-cible-cas-nominaux-et-cas-d-echec-representatifs-rendent-les-types-validables: done  # PR #104 mergée 2026-04-27 (5cc7f83)
  7-4-gouvernance-d-ouverture-de-la-vague-cible-product-scope-n-evolue-que-sous-fr40-nfr10-dans-le-meme-increment: done  # code review PASS 2026-04-28 — 0 finding HIGH, M1/L1/L2/L3 fixes tests-only, 1177 passed corpus
  7-5-exposition-d-actions-utilisateur-uniquement-sur-les-surfaces-reelles-et-supportees: backlog
  pe-epic-7-retrospective: optional
```

**NEW**

```yaml
  pe-epic-7: done  # cloture propre apres correct-course 2026-04-30 ; valeur livree = 7.1 + 7.2 + 7.3 + 7.4 (gouvernance d'ouverture + projection_validity) ; 7.5 re-homee vers pe-epic-9 Story 9.5 ; dette structurelle (mappers + publishers + dispatch + degradation §11) re-homee vers pe-epic-8 et pe-epic-9
  7-1-enrichissement-additif-du-contrat-4d-projection-validity-est-expose-de-bout-en-bout-sans-regression-sur-le-schema-canonique: done
  7-2-vague-cible-ha-les-types-candidats-sont-modelises-dans-le-registre-comme-connus-avec-contraintes-explicites-et-perimetre-borne: done  # PR #103 mergée 2026-04-27 (065df16)
  7-3-validation-de-projection-de-la-vague-cible-cas-nominaux-et-cas-d-echec-representatifs-rendent-les-types-validables: done  # PR #104 mergée 2026-04-27 (5cc7f83)
  7-4-gouvernance-d-ouverture-de-la-vague-cible-product-scope-n-evolue-que-sous-fr40-nfr10-dans-le-meme-increment: done  # code review PASS 2026-04-28 — 0 finding HIGH, M1/L1/L2/L3 fixes tests-only, 1177 passed corpus
  # 7-5 re-homee vers pe-epic-9 Story 9.5 le 2026-04-30 (correct-course) — non executable ici, voir bloc pe-epic-9 ci-dessous et SCP 2026-04-30 §5.4
  pe-epic-7-retrospective: optional

  # ==============================================================
  # pe-epic-8 — Refactor dispatch et registry-driven publishers
  # Ajoute par correct-course 2026-04-30 — refactor PUR sans nouveau comportement
  # Gate de cloture epic-level = golden-file 8.4 vert sur 30 equipements de reference
  # ==============================================================
  pe-epic-8: backlog
  8-1-mapper-registry-dispatch-deterministe-et-slot-terminal-reserve: backlog
  8-2-publisher-registry-dispatch-table-ha-entity-type-vers-methode-publish: backlog
  8-3-refactor-http-server-run-sync-boucle-dispatch-unique-et-compteurs-generiques: backlog
  8-4-gate-golden-file-de-non-regression-sur-30-equipements-de-reference: backlog
  pe-epic-8-retrospective: optional

  # ==============================================================
  # pe-epic-9 — Vague 1 d'extension reelle : sensor / binary_sensor / button
  #             + FallbackMapper §11 (degradation elegante terminale)
  # Ajoute par correct-course 2026-04-30 — pre-requis pe-epic-8 clos
  # Source de verite : _bmad-output/planning-artifacts/ha-projection-reference.md
  # Gate terrain de cloture epic-level = comptage nouveaux publies sur box reelle
  # ==============================================================
  pe-epic-9: backlog
  9-1-sensor-mapper-publish-sensor-info-numeric-et-capteurs-simples: backlog
  9-2-binary-sensor-mapper-publish-binary-sensor-info-binary-presence-ouverture-fuite: backlog
  9-3-button-mapper-publish-button-ouverture-button-dans-product-scope-sous-fr40-nfr10: backlog
  9-4-fallback-mapper-degradation-elegante-terminale-publier-sensor-button-par-defaut-plutot-que-skip-silencieux: backlog
  9-5-exposition-d-actions-utilisateur-sur-les-surfaces-reellement-ouvertes-par-la-vague-1-re-homee-depuis-7-5: backlog  # pre-requis : 9.1 + 9.2 + 9.3 + 9.4 done + gate terrain PASS
  pe-epic-9-retrospective: optional
```

**Rationale** : `pe-epic-7 → done` avec note explicite de la valeur livree et de la dette re-homee. Ligne `7-5: backlog` retiree, remplacee par commentaire de re-homing. Ajout des 2 sections pe-epic-8 et pe-epic-9 avec en-tetes commentaires explicites, statut `backlog`, retrospectives optional. Stories nommees selon la convention BMAD du fichier (kebab-case du titre tronque). Pre-requis 9.5 note en commentaire YAML.

---

### 5.6 — Promotion `ha-projection-reference.md` dans `active-cycle-manifest.md`

**Artifact** : `_bmad-output/planning-artifacts/active-cycle-manifest.md`

#### 5.6a — Ajout dans la table des sources de verite (section 4)

**OLD**

```md
## 4. Sources de verite actives par categorie

| Categorie | Fichier actif |
| --- | --- |
| Product Brief | `_bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-04-09.md` |
| PRD | `_bmad-output/planning-artifacts/prd.md` |
| Architecture | `_bmad-output/planning-artifacts/architecture-projection-engine.md` |
| Reconciliation PRD / Architecture | `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md` |
| Epics / story breakdown | `_bmad-output/planning-artifacts/epics-projection-engine.md` |
| UX / gates de surface critique | Portees par `epics-projection-engine.md` et les gates terrain story-level |
| Sprint status | `_bmad-output/implementation-artifacts/sprint-status.yaml` |
| Readiness report | `_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-10.md` |
| Backlog futur (Icebox) | `_bmad-output/planning-artifacts/backlog-icebox.md` |
```

**NEW**

```md
## 4. Sources de verite actives par categorie

| Categorie | Fichier actif |
| --- | --- |
| Product Brief | `_bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-04-09.md` |
| PRD | `_bmad-output/planning-artifacts/prd.md` |
| Architecture | `_bmad-output/planning-artifacts/architecture-projection-engine.md` |
| Reconciliation PRD / Architecture | `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md` |
| Epics / story breakdown | `_bmad-output/planning-artifacts/epics-projection-engine.md` |
| UX / gates de surface critique | Portees par `epics-projection-engine.md` et les gates terrain story-level |
| Sprint status | `_bmad-output/implementation-artifacts/sprint-status.yaml` |
| Readiness report | `_bmad-output/planning-artifacts/implementation-readiness-report-2026-04-10.md` |
| Backlog futur (Icebox) | `_bmad-output/planning-artifacts/backlog-icebox.md` |
| Reference projection HA (types Jeedom + composants HA + champs requis) | `_bmad-output/planning-artifacts/ha-projection-reference.md` (extrait de `docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx`) |
| Sprint Change Proposal le plus recent | `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md` |

**Note source projection HA** : `ha-projection-reference.md` documente 31 composants HA officiels MQTT, 163 types generiques Jeedom Core 4.2, et 77 champs structurellement requis. Toute extension du perimetre publie (ouverture de nouveau type dans `PRODUCT_SCOPE`, ajout de mapper, ajout de publisher, ajout de contrainte au registre HA) **doit** etre derivee de cette reference. Les artefacts code (`ha_component_registry.py`, mappers/, discovery/) sont derives, pas l'inverse. Cette reference est le contrat operationnel pour `validate_projection()` et le sequencing des vagues d'ouverture (`pe-epic-9`, `pe-epic-10+`).
```

#### 5.6b — Mise a jour des regles d'usage pour les prompts agents (section 7)

**OLD**

```md
## 7. Regles d'usage pour les prochains prompts agents

- Nommer explicitement le cycle actif : **Moteur de projection explicable**.
- Citer explicitement les fichiers actifs utilises.
- Mentionner explicitement que `_bmad-output/implementation-artifacts/sprint-status.yaml` est le fichier de suivi actif.
- Si un prompt reference un artefact `V1.1 Pilotable`, le traiter comme contexte secondaire uniquement.
- Aucun agent ne doit deviner la source de verite. En cas d'ambiguite, il doit se referer a ce manifeste.
```

**NEW**

```md
## 7. Regles d'usage pour les prochains prompts agents

- Nommer explicitement le cycle actif : **Moteur de projection explicable**.
- Citer explicitement les fichiers actifs utilises.
- Mentionner explicitement que `_bmad-output/implementation-artifacts/sprint-status.yaml` est le fichier de suivi actif.
- Si un prompt reference un artefact `V1.1 Pilotable`, le traiter comme contexte secondaire uniquement.
- Aucun agent ne doit deviner la source de verite. En cas d'ambiguite, il doit se referer a ce manifeste.
- Pour toute story touchant `HA_COMPONENT_REGISTRY`, `PRODUCT_SCOPE`, un mapper, un publisher ou la validation projection : citer explicitement `_bmad-output/planning-artifacts/ha-projection-reference.md` comme source-of-truth des contraintes HA et des types Jeedom. Les contraintes story-level doivent etre tracables jusqu'a une ligne de cette reference.
- Pour toute story touchant le dispatch, le `MapperRegistry` ou le `PublisherRegistry` introduits par `pe-epic-8` : citer le golden-file de Story 8.4 comme baseline de regression-control.
- Pour toute story exposant un `cause_action` : appliquer la regle Epic 6 « no faux CTA » (Story 6.3) et centraliser le `cause_code -> cause_label / cause_action` dans `cause_mapping.py` selon la convention Epic 4 V1.1.
```

#### 5.6c — Mise a jour du resume ultra court (section 10)

**OLD**

```md
## 10. Resume ultra court a copier dans les prompts

Cycle actif = **Moteur de projection explicable**. Sources de verite actives = `product-brief-jeedom2ha-2026-04-09.md`, `prd.md`, `architecture-projection-engine.md`, `architecture-delta-review-prd-final.md`, `epics-projection-engine.md`, `implementation-readiness-report-2026-04-10.md`, `sprint-status.yaml`, `backlog-icebox.md`. Les artefacts `V1.1 Pilotable` sont du contexte secondaire uniquement. Aucun agent ne doit deviner la source de verite.
```

**NEW**

```md
## 10. Resume ultra court a copier dans les prompts

Cycle actif = **Moteur de projection explicable**. Sources de verite actives = `product-brief-jeedom2ha-2026-04-09.md`, `prd.md`, `architecture-projection-engine.md`, `architecture-delta-review-prd-final.md`, `epics-projection-engine.md`, `implementation-readiness-report-2026-04-10.md`, `sprint-status.yaml`, `backlog-icebox.md`, `ha-projection-reference.md` (extrait de `docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx` — source-of-truth pour les contraintes HA et les types Jeedom), `sprint-change-proposal-2026-04-30.md` (dernier correct-course : cloture pe-epic-7, ajout pe-epic-8 refactor dispatch + pe-epic-9 vague 1 reelle). Les artefacts `V1.1 Pilotable` sont du contexte secondaire uniquement. Aucun agent ne doit deviner la source de verite.
```

#### 5.6d — Mise a jour de la section « Prochaine etape BMAD attendue » (section 9)

**OLD**

```md
## 9. Prochaine etape BMAD attendue

Utiliser ce manifeste comme point d'entree avant tout workflow BMAD d'execution, puis s'appuyer sur `epics-projection-engine.md` et `sprint-status.yaml` pour la suite.  
Apres le correct-course du `2026-04-22`, la prochaine etape attendue est la preparation de `pe-epic-7`, en commencant par la story `7.1`.
```

**NEW**

```md
## 9. Prochaine etape BMAD attendue

Utiliser ce manifeste comme point d'entree avant tout workflow BMAD d'execution, puis s'appuyer sur `epics-projection-engine.md` et `sprint-status.yaml` pour la suite.  
Apres le correct-course du `2026-04-30` (`sprint-change-proposal-2026-04-30.md`), la prochaine etape attendue est la preparation de `pe-epic-8`, en commencant par la story `8.1` (`MapperRegistry`). `pe-epic-9` reste bloque tant que le golden-file de Story 8.4 n'est pas vert.
```

**Rationale** : promotion explicite de `ha-projection-reference.md` en source-of-truth active. Note prescriptive « toute extension doit etre derivee de cette reference ». 3 nouvelles regles prescriptives pour les prompts agents (registre/scope/mappers, dispatch/golden-file, no faux CTA + cause_mapping.py). Resume ultra-court etendu — empeche les futurs agents d'oublier l'Excel. Section 9 pointe vers la prochaine etape reelle (pe-epic-8 Story 8.1) avec note de blocage pe-epic-9.

---

### 5.7 — Section « Statut BMAD » dans `ha-projection-reference.md`

**Artifact** : `_bmad-output/planning-artifacts/ha-projection-reference.md`
**Section** : nouvelle section inseree entre le paragraphe d'introduction (ligne 21) et la section `## Meta-referentiel`

**OLD** (lignes 21-23 actuelles)

```md
Toute extension du perimetre publie dans HA derive de ce document. Les artefacts code (`ha_component_registry.py`, mappers, publishers) doivent rester **derives** de cette reference - pas l'inverse.

## Meta-referentiel (onglet README)
```

**NEW**

```md
Toute extension du perimetre publie dans HA derive de ce document. Les artefacts code (`ha_component_registry.py`, mappers, publishers) doivent rester **derives** de cette reference - pas l'inverse.

## Statut BMAD et regles d'evolution

### Statut

Cette reference est **source-of-truth officielle** du cycle `Moteur de projection explicable` depuis le correct-course du 2026-04-30 (voir `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md`). Elle est inscrite a ce titre dans `_bmad-output/planning-artifacts/active-cycle-manifest.md` section 4.

### Usages BMAD obligatoires

| Surface produit | Usage prescriptif de cette reference |
|---|---|
| `resources/daemon/validation/ha_component_registry.py` (`HA_COMPONENT_REGISTRY`) | Les `required_fields` de chaque entree doivent correspondre aux `explicit_required_fields` de la section 1 de cette reference (composants HA MQTT). Toute divergence doit etre justifiee story-level. |
| `resources/daemon/validation/ha_component_registry.py` (`PRODUCT_SCOPE`) | Aucun composant ne peut entrer dans `PRODUCT_SCOPE` s'il n'est pas reference en section 1. La gouvernance FR40 / NFR10 (Story 7.4) prend appui sur cette reference. |
| `resources/daemon/mapping/*.py` | Tout mapper specifique doit produire un `MappingResult` dont les champs satisfont au minimum les `explicit_required_fields` du composant HA cible declare dans cette reference. |
| `resources/daemon/discovery/*.py` (publishers) | Les payloads MQTT Discovery emis par les `publish_*` methodes doivent inclure les `explicit_required_fields` de cette reference et **uniquement** des champs documentes par cette reference (pas de champ "creatif" hors documentation HA officielle). |
| `validate_projection()` (`pe-epic-7` Story 7.3) | Les cas nominaux et cas d'echec testes doivent porter sur les contraintes listees en section 2 de cette reference (champs structurellement requis par composant). |
| Sequencing des vagues d'ouverture (`pe-epic-9`, `pe-epic-10+`) | Le decoupage des vagues d'extension produit derive de la liste des 31 composants HA documentes en section 1 et des 163 types generiques Jeedom de la section dediee. |
| Stories qui ouvrent un nouveau type | Doivent citer explicitement la ligne correspondante de cette reference dans leurs Acceptance Criteria et Dev notes. |

### Regles d'evolution

- Cette reference est **derivee mecaniquement** de `docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx` lui-meme construit depuis les sources officielles (Jeedom Core 4.2, HAP-NodeJS, Home Assistant MQTT Discovery). Elle n'est **jamais** editee a la main.
- Toute mise a jour de cette reference passe par une re-extraction de l'Excel source. Le commit qui modifie ce `.md` doit aussi modifier le `.xlsx` source ou indiquer la nouvelle version source en frontmatter.
- L'extension du fichier Excel source (ajout de composants HA, evolution de la documentation HA officielle) declenche une re-extraction puis une revue d'impact sur `HA_COMPONENT_REGISTRY` et le sequencing des vagues. Aucune modification arbitraire.
- Les onglets `HomeKit_*` de l'Excel source ne sont pas extraits ici (voir `skipped_sheets` en frontmatter) car Homebridge / HAP-NodeJS reste un ecosysteme parallele non utilise par jeedom2ha. Toute decision de les integrer un jour passe par un correct-course explicite.

### Niveaux d'abstraction

`ha-projection-reference.md` et `ha_component_registry.py` operent a **deux niveaux d'abstraction differents** (regle posee par `architecture-projection-engine.md`) :

- **Niveau 1 — Spec HA officielle (cette reference)** : champs MQTT Discovery requis par composant tels que documentes par Home Assistant. Cle JSON littérale (`command_topic`, `state_topic`, `options`, `platform`, `availability > keys > topic`).
- **Niveau 2 — Contrat moteur de projection (`HA_COMPONENT_REGISTRY`)** : capabilities abstraites resolues a runtime (`has_command`, `has_state`, `has_options`) qui se traduisent en champs Niveau 1 via `_CAPABILITY_TO_REASON`.

La verification de coherence entre Niveau 1 et Niveau 2 est tracable story-level mais reste deux representations distinctes ; ce fichier est la source-of-truth du Niveau 1.

### Sequencing d'ouverture documente

A ce jour (post correct-course 2026-04-30) :

| Composant HA | Etat (Story 7.4) | Vague d'ouverture |
|---|---|---|
| `light` | ouvert (pre-pe-epic-7) | historique |
| `cover` | ouvert (pre-pe-epic-7) | historique |
| `switch` | ouvert (pre-pe-epic-7) | historique |
| `sensor` | ouvert (`PRODUCT_SCOPE` post 7.4) | publication reelle ouverte par `pe-epic-9` Story 9.1 |
| `binary_sensor` | ouvert (`PRODUCT_SCOPE` post 7.4) | publication reelle ouverte par `pe-epic-9` Story 9.2 |
| `button` | connu (registre 7.2) | ouverture `PRODUCT_SCOPE` + publication par `pe-epic-9` Story 9.3 |
| `number`, `select`, `climate` | connus (registre 7.2) | vagues ulterieures (`pe-epic-10+`) |
| 22 autres composants HA officiels | non encore connus (registre fermé sur 9 entrees) | vagues ulterieures gouvernees |

L'existence d'un composant en section 1 de cette reference **n'est pas** un engagement produit a l'ouvrir. Elle est seulement une garantie que sa modelisation future suivra les contraintes officielles HA documentees ici.

## Meta-referentiel (onglet README)
```

**Rationale** : statut source-of-truth officielle dans le corps du document (le frontmatter est invisible aux lecteurs humains du `.md` rendu). Table d'usages BMAD obligatoires (7 lignes) institutionnalise les obligations prescriptives. Regles d'evolution empechent l'edition manuelle. Niveaux d'abstraction reprend la regle d'`architecture-projection-engine.md`. Tableau de sequencing d'ouverture = photo claire de l'etat post 2026-04-30. Mention finale « l'existence en section 1 n'est PAS un engagement produit a ouvrir » = verrou anti-scope-creep.

---

### 5.8 — Decisions no-change documentees

#### 5.8a — `_bmad-output/planning-artifacts/prd.md` (PRD actif du cycle)

**Decision** : aucune modification.

**Etat actuel** : FR36-FR45 (Features 7-8) couvrent la gouvernance du registre HA. FR11-FR15 (Feature 2) couvrent le mapping candidat et FR15 garantit la non-modification de l'ordre canonique des etapes. FR26-FR30 (Feature 5) couvrent la separation decision / publication.

**Dette traitee ailleurs** :
- Regle §11 cadrage : cablee story-level dans `pe-epic-9` Story 9.4 plutot que par un FR additif. Justification : un FR « le systeme doit publier en sensor/button par defaut » serait trop prescriptif au niveau PRD ; story 9.4 est le bon niveau d'expression.
- Refactor dispatch : implementation detail, pas une exigence produit — n'a aucune raison d'etre dans le PRD.

**Consequence** : aucune reecriture du PRD ne s'impose.

#### 5.8b — `_bmad-output/planning-artifacts/architecture-projection-engine.md`

**Decision** : aucune modification.

**Etat actuel** : cite deja l'Excel a 3 reprises comme source-of-truth. Pose la regle des 2 niveaux d'abstraction. Pose AR3 (separation registre / mapping / discovery) qui rend possible le `MapperRegistry` + `PublisherRegistry` sans contradiction architecturale. Pose AR13 (gouvernance FR40 / NFR10).

**Dette traitee ailleurs** :
- Reference a `ha-projection-reference.md` : ajoutee par 5.6 + 5.7. L'architecture continue de citer l'Excel source (canonique) — le `.md` est derive.
- Pattern `MapperRegistry` / `PublisherRegistry` : implementation detail story-level pe-epic-8.
- Pattern `FallbackMapper` terminal : implementation detail story-level pe-epic-9 Story 9.4.

**Consequence** : aucune mise a jour d'architecture ne s'impose.

#### 5.8c — `_bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-04-09.md`

**Decision** : aucune modification.

**Etat actuel** : cite l'Excel comme source-of-truth pour la construction du registre HA. Pose la distinction « composant connu / composant ouvert ». Affirme que l'ouverture progressive est une posture produit — coherent avec le decoupage pe-epic-9 vague 1 / pe-epic-10+ vagues ulterieures.

**Dette traitee ailleurs** : le brief est deja aligne sur la strategie d'ouverture gouvernee. Le correct-course du 2026-04-30 ne revise pas la strategie produit.

**Consequence** : aucun ajustement produit-niveau ne s'impose.

#### 5.8d — `_bmad-output/planning-artifacts/prd-post-mvp-v1-1-pilotable.md` (artefact secondaire)

**Decision** : aucune modification.

**Etat actuel** : artefact **secondaire** selon `active-cycle-manifest.md` section 5 — n'est plus source-of-truth depuis 2026-04-22.

**Dette traitee ailleurs** :
- La sur-application de §7 « publier moins, expliquer mieux » est documentee dans la **section 1 du present SCP** avec la formulation corrigee actee :
  > « publier en degradation elegante plutot qu'en skip silencieux ; n'omettre que quand aucune projection structurellement valide n'existe »
- La regle corrective vit story-level (pe-epic-9 Story 9.4) et architecture-level (manifest section 7 nouvelle regle prescriptive — change proposal 5.6b).

**Consequence** : artefact laisse tel quel. Reste lisible comme **trace historique** d'une posture produit qui etait saine a l'origine (V1.1 Pilotable centre sur la pilotabilite plutot que la breadth) mais qui a ete surinterpretee par les agents BMAD ulterieurs. La regle de gouvernance posee par le manifest interdit desormais a un futur agent BMAD d'utiliser ce PRD V1.1 pour redefinir le scope du cycle actif.

#### 5.8e — `_bmad-output/planning-artifacts/epics-projection-engine.md` — sections non touchees

**Decision** : aucune modification des sections Epic 1 a Epic 6 ni des stories 7.1 a 7.4.

**Etat actuel** : Epics 1 a 6 integralement done, valeur livree intacte. Stories 7.1 a 7.4 done, valeur livree intacte (gouvernance d'ouverture + projection_validity).

**Dette traitee ailleurs** : les seules modifications de cet artefact sont introduites par les change proposals 5.1, 5.2, 5.3, 5.4a, 5.4b. Aucune autre section n'est modifiee.

**Consequence** : integrite historique du fichier preservee.

---

## 6. Recommended Approach and High-Level Action Plan

### MVP impact

**Aucun impact negatif sur le cycle Moteur de projection explicable.**

La proposition :
- ne reduit pas le scope produit ;
- ne remet pas en cause les FR du PRD actif ;
- restaure la promesse §11 du cadrage initial sans toucher au cadrage produit existant ;
- pose enfin l'infrastructure dispatch reutilisable pour les vagues ulterieures.

### High-level action plan

1. Mettre a jour `active-cycle-manifest.md` (sections 4 + 7 + 9 + 10) — change proposal 5.6.
2. Ajouter section « Statut BMAD » dans `ha-projection-reference.md` — change proposal 5.7.
3. Modifier `epics-projection-engine.md` :
   - note de cloture HEAD pe-epic-7 (5.1) ;
   - ajout pe-epic-8 (5.2) ;
   - ajout pe-epic-9 stories 9.1-9.4 (5.3) ;
   - re-homing 7.5 + ajout 9.5 (5.4).
4. Mettre a jour `sprint-status.yaml` (5.5).
5. Lancer `bmad-create-story` sur Story 8.1 (`MapperRegistry`).
6. Aucun developpement ne demarre tant que Story 8.1 n'est pas creee, scoped et `ready-for-dev`.
7. Story 8.4 (golden-file gate) bloque la cloture de pe-epic-8.
8. Aucune story de pe-epic-9 ne demarre tant que pe-epic-8 n'est pas clos.
9. Story 9.5 ne demarre qu'apres cloture des stories 9.1 a 9.4 + gate terrain PASS.

### Dependencies and sequencing

- **Precondition absolue** : approbation explicite de cette proposition.
- **Precondition d'execution** : mise a jour des artefacts BMAD (manifest, ha-projection-reference, epics, sprint-status) avant toute creation de story.
- **Gate de reprise dev** : aucune implementation avant creation de la story 8.1.
- **Gate de demarrage pe-epic-9** : golden-file 8.4 vert sur 30 equipements de reference.
- **Gate de cloture pe-epic-9** : gate terrain PASS sur box reelle (comptage nouveaux publies decompose par type et par mapper d'origine, minimum 5+5+3+5 cas pour Story 9.5).

---

## 7. Implementation Handoff

### Scope classification

**Moderate-to-Major.**

Pourquoi Moderate-to-Major plutot que Major :
- aucune reecriture PRD / architecture / brief ;
- aucune redefinition de cycle ;
- mais : ajout de 2 epics, refactor structurel du dispatch, 4 nouveaux mappers + 4 nouveaux publishers, 5 nouveaux cause_codes, reorganisation backlog complete sur la suite du cycle.

### Handoff recipients

| Responsabilite | Role / workflow |
|---|---|
| Mettre a jour `active-cycle-manifest.md` (5.6) | Scrum Master |
| Mettre a jour `ha-projection-reference.md` (5.7) | Scrum Master |
| Mettre a jour `epics-projection-engine.md` (5.1, 5.2, 5.3, 5.4) | Product Owner avec revue Architect (verification coherence dispatch / registry / FallbackMapper) |
| Mettre a jour `sprint-status.yaml` (5.5) | Scrum Master |
| Verifier coherence sequencing pe-epic-8 -> pe-epic-9 | Architect |
| Preparer la premiere story executable (`bmad-create-story` sur 8.1) | Scrum Master |
| Implementer Story 8.1 a 8.4 | Dev team apres validation story-level |
| Implementer Stories 9.1 a 9.4 | Dev team apres cloture pe-epic-8 |
| Gate terrain de cloture pe-epic-9 | Alexandre (box reelle) |

### Success criteria

1. `active-cycle-manifest.md` cite `ha-projection-reference.md` en source-of-truth + cite SCP 2026-04-30.
2. `ha-projection-reference.md` contient une section « Statut BMAD » avec table d'usages obligatoires et table de sequencing d'ouverture.
3. `pe-epic-7` est `done` dans le tracker, sans faux `done` (la dette est documentee et re-homee).
4. Story 7.5 n'est plus un item de backlog actif ; elle existe comme artefact historique pointant vers Story 9.5.
5. `pe-epic-8` et `pe-epic-9` existent explicitement dans `epics-projection-engine.md` et `sprint-status.yaml`.
6. La premiere story de reprise est `8.1` (`MapperRegistry`).
7. Le golden-file 8.4 est implemente et vert avant le demarrage de pe-epic-9.
8. La regle §11 du cadrage initial est cablee par Story 9.4 et verifiable par les AC explicites.
9. `cause_action = None` strictement sur tous les chemins du `FallbackMapper` (verrou Epic 6 « no faux CTA »).
10. Toute future action utilisateur reste liee a une surface produit reelle et testee.

---

## 8. Checklist Summary

| Item | Status | Note |
|---|---|---|
| 1.1 Trigger story identifiee | [x] Done | Drift de sequencing cumule revele par cloture pe-epic-7 |
| 1.2 Core problem defini | [x] Done | Defaut sequencing cumule sur 3 plans (vision -> backlog ; brief V1.1 -> cycle Moteur ; epic-level Epic 7) |
| 1.3 Evidence gathered | [x] Done | Cadrage §11, Excel 31/163/77, ha-projection-reference, PRD V1.1 §7 / §11 axe 6, brief refresh §4 / §10, SCP 2026-04-22, code http_server / mapping / registry |
| 2.1 Current epic assessed | [x] Done | pe-epic-7 sain sur 7.1-7.4, mais non clos correctement |
| 2.2 Epic-level changes determined | [x] Done | Cloture pe-epic-7 + ajout pe-epic-8 + ajout pe-epic-9 + re-homing 7.5 + promotion ha-projection-reference |
| 2.3 Future epics reviewed | [x] Done | Aucun epic > 7 dans le plan actuel ; pe-epic-8 et pe-epic-9 deviennent les prochains requis |
| 2.4 New epics needed | [x] Done | pe-epic-8 (refactor pur) + pe-epic-9 (vague 1 reelle + FallbackMapper §11) |
| 2.5 Order / priority change | [x] Done | pe-epic-8 avant pe-epic-9 ; gate golden-file 8.4 bloque demarrage pe-epic-9 |
| 3.1 PRD conflict check | [x] Done | Aucun conflit prd.md ; PRD V1.1 secondaire — sur-application documentee Section 1 |
| 3.2 Architecture conflict check | [x] Done | Aucun conflit ; AR3 / AR13 + 2 niveaux d'abstraction suffisants |
| 3.3 UX conflict check | [x] Done | Aucun nouveau recadrage ; Story 9.5 re-applique « no faux CTA » Epic 6 |
| 3.4 Other artifacts impact | [x] Done | epics-projection-engine, sprint-status, manifest, ha-projection-reference, code production (story-level) |
| 4.1 Option 1 direct adjustment | [ ] Not viable | Trop etroit — laisse les 3 elif et la regle §11 absentes |
| 4.2 Option 2 rollback | [ ] Not viable | Detruit la valeur livree par 7.2-7.4 |
| 4.3 Option 3 PRD MVP review | [ ] Not viable | PRD actif correct, pas de cadrage a refondre |
| 4.4 Recommended path selected | [x] Done | Hybrid Option 4 |
| 5.1 Issue summary created | [x] Done | Section 1 avec formulation corrigee Alexandre |
| 5.2 Impact documented | [x] Done | Sections 2 et 3 |
| 5.3 Recommended path documented | [x] Done | Section 4 |
| 5.4 High-level action plan defined | [x] Done | Section 6 |
| 5.5 Agent handoff established | [x] Done | Section 7 |
| 5.6 Detailed change proposals validated | [x] Done | 5.1 a 5.8 approuvees individuellement par Alexandre en mode Incremental |
| 6.1 Checklist reviewed | [x] Done | Cette section |
| 6.2 Proposal accuracy reviewed | [x] Done | Coherence verifiee avec artefacts du cycle Moteur de Projection |
| 6.3 User approval | [x] Done | Approbation explicite Alexandre 2026-04-30 |
| 6.4 sprint-status update | [ ] Pending | Sera execute apres approbation finale — change proposal 5.5 |
| 6.5 Next steps confirmed | [ ] Pending | Sera confirme apres execution — preparation Story 8.1 |

---

## 9. Approval Request

Cette proposition recommande de :

- **clore proprement `pe-epic-7`** sur sa valeur reellement livree (gouvernance d'ouverture + `projection_validity`) ;
- **re-homer Story 7.5** vers `pe-epic-9` Story 9.5 ;
- **ouvrir `pe-epic-8`** (refactor pur dispatch + registry-driven, gate golden-file 30 equipements) ;
- **ouvrir `pe-epic-9`** (vague 1 reelle sensor / binary_sensor / button + `FallbackMapper` §11 terminal) ;
- **promouvoir `ha-projection-reference.md`** en source-of-truth officielle dans `active-cycle-manifest.md` ;
- **documenter formellement** les non-modifications de `prd.md`, `architecture-projection-engine.md`, `product-brief-jeedom2ha-2026-04-09.md`, `prd-post-mvp-v1-1-pilotable.md` ;
- **acter la formulation corrigee** de la regle « publier moins, expliquer mieux » :
  > « publier en degradation elegante plutot qu'en skip silencieux ; n'omettre que quand aucune projection structurellement valide n'existe ».

**Decision recueillie** : `yes` — proposition approuvee le `2026-04-30` par Alexandre via correct-course incremental (validations sequentielles 5.1 a 5.8 puis approbation finale du document complet).
