---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-06-07
status: proposed
scope_classification: moderate
trigger: cadrage-pe-epic-10-compatibilite-minimale-homebridge-sans-plateformes-annexes
mode: incremental
communication_language: french
proposed_by: clawcode
impacts_if_approved:
  - _bmad-output/planning-artifacts/epics-projection-engine.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/planning-artifacts/active-cycle-manifest.md
no_change_documented:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-04-09.md
references:
  - _bmad-output/implementation-artifacts/pe-epic-9-retro-2026-06-06.md
  - _bmad-output/planning-artifacts/ha-projection-reference.md
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-04-30.md
  - docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx
---

# Sprint Change Proposal 2026-06-07 - Cadrage pe-epic-10 sur la compatibilite minimale Homebridge

## 1. Issue Summary

### Trigger

Apres cloture de `pe-epic-9` le `2026-06-05` et retrospective le `2026-06-06`, le repo confirme qu'il n'existe **aucun `pe-epic-10` materialise** dans le backlog actif. La prochaine etape attendue est un correct-course pour choisir la vague suivante.

En parallele, l'orientation produit exprimee par Alexandre pour `pe-epic-10` est plus precise que la simple formule "ouvrir un nouveau composant HA" :

- objectif minimum : **publier dans Home Assistant tout ce qui est deja publie depuis Jeedom vers HomeKit via Homebridge** ;
- limite explicite : **hors plateformes annexes** ou ecosytemes specifiques (`camera`, `samsung`, etc.) ;
- consequence : la prochaine vague doit viser une **parite de compatibilite utile** avec le perimetre equipements deja prouve cote Homebridge, pas une extension opportuniste type-par-type.

### Problem statement

Le probleme a traiter n'est pas technique au sens "le moteur ne peut pas evoluer". `pe-epic-8` et `pe-epic-9` ont justement pose une base extensible.

Le vrai probleme est un **ecart de cadrage entre trois niveaux** :

1. la source active actuelle (`ha-projection-reference.md`) gouverne correctement les **contraintes HA** et le sequencing des vagues, mais elle **exclut explicitement les onglets `HomeKit_*`** comme source de priorisation active ;
2. l'intention produit `pe-epic-10` formulee par Alexandre introduit au contraire un **critere de priorisation externe utile** : la compatibilite deja publiee via Homebridge ;
3. le workspace ne contient pas aujourd'hui d'artefact terrain `clawbox` exploitable permettant de lister proprement ce perimetre publie Homebridge.

Conclusion : on ne peut pas ouvrir honnetement `pe-epic-10` comme simple story de dev, ni pretendre que l'inventaire Homebridge est deja fige dans le repo. Il faut un epic qui commence par **figer l'inventaire de compatibilite minimale visee**, puis derive la vague HA correspondante sans casser les guardrails FR40 / NFR10.

### Evidence

| Evidence | Constat | Lecture |
|---|---|---|
| `_bmad-output/implementation-artifacts/pe-epic-9-retro-2026-06-06.md` | `PE9-AI-01` demande un correct-course `pe-epic-10+` depuis la reference HA | La suite attendue est bien un recadrage, pas une story isolee |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | `pe-epic-9-retrospective: done` et "next step = correct-course pe-epic-10+" | Aucun `pe-epic-10` executable n'existe encore |
| `_bmad-output/planning-artifacts/ha-projection-reference.md` | `number`, `select`, `climate` sont connus mais hors vague ; `HomeKit_*` est explicitement exclu des sources actives | La priorisation Homebridge n'est pas encore branchee au process |
| `resources/daemon/validation/ha_component_registry.py` | `number`, `select`, `climate` sont deja modelises dans `HA_COMPONENT_REGISTRY` mais hors `PRODUCT_SCOPE` | Le moteur est pret pour une vague suivante gouvernee |
| Workspace courant | aucun artefact `clawbox` ou inventaire Homebridge publie n'a ete retrouve | Il faut formaliser une etape d'inventaire avant de figer le scope exact |

### Category

**Need for roadmap adjustment** sans rollback technique ni reecriture du PRD.

Le correct-course doit ajouter un critere de priorisation produit : **parite minimale avec le perimetre deja publie via Homebridge**, tout en conservant la regle existante : les payloads et ouvertures reelles vers HA restent derives de `ha-projection-reference.md` et gouvernes story-par-story.

## 2. Impact Analysis

### 2.1 Ce qui ne change pas

- Le cycle actif reste **Moteur de projection explicable**.
- `ha-projection-reference.md` reste la **source-of-truth des contraintes HA**.
- Les guardrails `FR40` / `NFR10` restent obligatoires pour toute ouverture de `PRODUCT_SCOPE`.
- `pe-epic-9` reste ferme ; aucun retour arriere sur `sensor`, `binary_sensor`, `button` n'est propose.

### 2.2 Ce qui change si la proposition est approuvee

- `pe-epic-10` n'est plus cadre comme "prochaine vague HA arbitraire".
- `pe-epic-10` devient un epic de **parite de compatibilite minimale Homebridge -> HA**.
- La priorisation de la vague suivante ne part plus seulement de la liste des composants HA connus ; elle part d'abord d'un **inventaire des equipements deja publies via Homebridge** puis les projette vers les composants HA pertinents et deja modelises.

### 2.3 Impact sur le sequencing

Ordre recommande post-approbation :

1. story prefixe d'inventaire et de gel du perimetre cible ;
2. story prefixe checklist canonique "nouveau type HA / nouvelle vague" ;
3. ouverture effective des composants HA requis par l'inventaire fige ;
4. gate terrain de parite minimale sur box reelle ;
5. seulement ensuite, cadrage `pe-epic-11+` pour d'autres vagues.

## 3. Path Forward Evaluation

### Option 1 - Ouvrir directement `number`, `select`, `climate`

**Statut : insuffisant seul.**

Cette option colle aux composants deja connus dans le registre, mais elle ne prouve pas qu'on couvre bien le perimetre Homebridge reellement publie aujourd'hui. Elle risque de rater des cas importants ou d'ouvrir des types inutiles.

### Option 2 - Integrer integralement `HomeKit_*` comme nouvelle source-of-truth active

**Statut : trop large pour maintenant.**

Cela melangerait priorisation produit et contrat technique HA. Ce n'est pas necessaire pour `pe-epic-10`, et cela rouvrirait un chantier de gouvernance documentaire plus grand que le besoin.

### Option 3 - Hybrid ciblee (selectionnee)

**Statut : recommandee.**

On garde `ha-projection-reference.md` comme contrat HA, mais on ajoute pour `pe-epic-10` une etape prefixe qui fige le **perimetre Homebridge minimal vise** comme source de priorisation de la vague.

Autrement dit :

- **Homebridge sert a choisir quoi couvrir en premier** ;
- **HA reference sert a definir comment l'ouvrir proprement**.

## 4. Detailed Change Proposal

### 4.1 Nouveau cadrage epic-level

Creer `pe-epic-10` avec une promesse produit explicite :

> Elargir la compatibilite de `jeedom2ha` jusqu'a couvrir a minima les equipements deja publies de Jeedom vers HomeKit via Homebridge, hors plateformes annexes et sans ouverture opportuniste non justifiee.

### 4.2 Prefixe obligatoire de `pe-epic-10`

Avant toute story de mapper/publisher, ajouter une story prefixe de cadrage executable qui :

- collecte l'inventaire terrain cible depuis les artefacts disponibles ou l'audit `clawbox` quand il sera materialise ;
- exclut explicitement les plateformes annexes hors demande (`camera`, `samsung`, etc.) ;
- produit une table de correspondance :
  `usage/equipement publie Homebridge -> generic types Jeedom -> composant HA cible -> ecart actuel du moteur` ;
- fige la liste des composants HA effectivement requis pour la vague.

### 4.3 Vague recommandee a ce stade

Sous reserve de confirmation par l'inventaire prefixe, la vague la plus probable est centree sur les composants deja connus dans `HA_COMPONENT_REGISTRY` et fortement coherents avec une logique de parite Homebridge :

- `number`
- `select`
- `climate`

Cette proposition reste volontairement prudente :

- elle **n'affirme pas** que ces trois composants suffisent a eux seuls ;
- elle affirme seulement qu'ils sont les **meilleurs candidats initiaux** deja visibles dans le repo.

### 4.4 Acceptance criteria epic-level recommandes

Si `pe-epic-10` est approuve, ses AC epic-level doivent inclure au minimum :

1. le perimetre Homebridge minimal vise est fige dans un artefact lisible et cite dans les stories ;
2. chaque nouveau type HA ouvert cite sa ligne source dans `ha-projection-reference.md` ;
3. toute ouverture suit la checklist canonique : mapper, publisher, `known_types`, topics, compteurs, diagnostic, golden-file, tests, terrain ;
4. un gate terrain final prouve la parite minimale sur les equipements retenus par l'inventaire prefixe ;
5. aucun glissement vers des plateformes annexes n'est accepte dans `pe-epic-10`.

## 5. Artifact Changes If Approved

| Artefact | Changement requis |
|---|---|
| `_bmad-output/planning-artifacts/epics-projection-engine.md` | Ajouter `pe-epic-10` et ses stories prefixe + vague |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Materialiser `pe-epic-10` en backlog actif |
| `_bmad-output/planning-artifacts/active-cycle-manifest.md` | Mettre a jour la "prochaine etape BMAD attendue" et la reference du dernier correct-course |

## 6. Recommendation

Approuver un correct-course **cible et incremental** :

- pas de reecriture du PRD ;
- pas de promotion globale des onglets `HomeKit_*` en source-of-truth active ;
- oui a un `pe-epic-10` cadre par la **parite minimale Homebridge** ;
- oui a une story prefixe obligatoire de gel d'inventaire avant toute ouverture technique.

## 7. Decision Requested

Decision demandee a Alexandre :

- **yes** -> appliquer ce correct-course et materialiser `pe-epic-10` dans les artefacts actifs ;
- **revise** -> garder l'idee de parite Homebridge mais ajuster le perimeter exact de la vague ;
- **no** -> revenir a une priorisation purement HA-first sans critere Homebridge.
