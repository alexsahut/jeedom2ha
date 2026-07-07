---
artifact_type: sprint-change-proposal
project: jeedom2ha
date: '2026-07-07'
workflow: correct-course
author: clawcode (Scrum Master)
trigger_story: 16.2
status: approved
mode: batch
decision_method: ADR multi-persona (5 sous-agents parallèles)
---

# Sprint Change Proposal — 2026-07-07

**Déclencheur :** Story 16.2 (Epic 16 — mapping configurable). Conflit source-de-vérité "attendu HA par commande".
**Méthode de décision :** débat ADR à 5 personas en sous-agents parallèles (Données, Pipeline, Produit/UX, Avocat du diable/YAGNI, Test/Maintenance).

---

## Section 1 — Résumé du problème

Pendant `create-story` de la Story 16.2, un conflit a été découvert entre la documentation d'architecture et la réalité du code :

- **Ce que disent les docs** (delta archi epic-16, epic, UX 16b) : la source de vérité de "l'attendu HA par commande" est `_bmad-output/planning-artifacts/ha-projection-reference.yaml`.
- **Ce que fait le code (vérifié)** : ce YAML (1814 lignes) **n'est chargé nulle part par le daemon**. La vérité runtime effective est le dict Python codé en dur `resources/daemon/validation/ha_component_registry.py::HA_COMPONENT_REGISTRY` (8 composants du `PRODUCT_SCOPE`) + les allowlists `generic_type` codées dans chaque mapper (`_LIGHT_GENERIC_TYPES`, etc.) et la logique de `resources/daemon/mapping/registry.py`.
- **Le YAML ne fait même pas le mapping demandé** : ses 2 sections (`ha_components` descriptif + catalogue `jeedom_generic_types`) sont **indépendantes** et ne relient jamais `generic_type → composant HA`.

**Type d'issue :** malentendu/écart de spec découvert à l'implémentation (le doc pointe un artefact non branché).

**Évidence clé — le pivot :** l'en-tête `_meta.note` du YAML lui-même énonce : _« Derive ha_component_registry.yaml (consumed by daemon) from this reference. Do not edit by hand: regenerate from ha-projection-reference.xlsx. »_ → l'intention documentée a **toujours** été une **dérivation** vers un artefact runtime, jamais un chargement direct du YAML de planning. La chaîne prévue `xlsx → ha-projection-reference.yaml (planning) → ha_component_registry.yaml (runtime dérivé) → daemon` n'a jamais eu son maillon intermédiaire généré : le daemon a dérivé "à la main" vers un dict Python. C'est cohérent avec l'esprit "dérivation", pas avec un chargement YAML runtime.

---

## Section 2 — Analyse d'impact (checklist correct-course)

**§1 Trigger** — Story 16.2, AC1. Problème : source de vérité runtime ambiguë. [Done]

**§2 Impact Epic**
- 2.1 : Epic 16 **reste réalisable tel quel**. Aucune story rendue obsolète. [Done]
- 2.2-2.5 : pas de nouvel epic, pas de resequencing. Un **pré-requis de frontière** émerge pour les stories 16b (16.5-16.7) — voir angle mort produit. [Action-needed → tracé en Section 4]

**§3 Conflits artefacts**
- 3.1 PRD : aucun conflit. FR23-25/FR31 satisfaits par Option 1 (l'attendu = ce que `validate_projection` applique réellement). [N/A]
- 3.2 Architecture : **conflit réel** — `architecture-delta-pe-epic-16-mapping-configurable.md` désigne le YAML comme source de vérité sans acter qu'il n'est pas chargé. À corriger (dérivation runtime). [Action-needed]
- 3.3 UX : le design 16b suppose un sélecteur d'override avec labels FR / familles / subtypes — données présentes **uniquement** dans la section `jeedom_generic_types` du YAML, absentes du registry runtime. Frontière à acter. [Action-needed]
- 3.4 Autres (tests, golden corpus) : Option 1 = golden corpus inchangé. [Done]

**§4 Chemin — évaluation**
- **Option 1 (Direct Adjustment)** : dériver l'attendu HA du runtime existant (registry + mappers). Effort **Low**, Risque **Low**. **VIABLE.**
- **Option 2 (brancher le YAML runtime)** : nouveau loader + cohérence registry↔YAML. Effort **High**, Risque **High** (double source de vérité, faux-vert, vocabulaire divergent, 31 composants YAML vs 8 scope). **Non viable pour 16.2.**
- **Rollback** : sans objet (rien à annuler). **N/A.**

---

## Section 3 — Approche recommandée

### Verdict du débat ADR (5 personas)

| Persona | Verdict | Argument dominant |
|---|---|---|
| Architecte Données | **Option 1** | Option 2 = triple source (code/yaml/allowlists), drift garanti ; le YAML ne fait pas le mapping AC1 |
| Architecte Pipeline | **Option 1** | Cohérence `validate_projection` ↔ attendu : une seule vérité ; YAML runtime = point de défaillance + coût parsing |
| Architecte Produit/UX | **Hybride** (16.2 en Opt.1 + frontière 16b) | Les labels FR/familles pour le sélecteur override vivent dans `jeedom_generic_types` → à acter pour 16b |
| Avocat du diable / YAGNI | **Option 1** | Loader pour un client fantôme (UI 16b inexistante) ; "l'intention documentée" est une erreur de doc à corriger |
| Test / Maintenance | **Option 1** | Opt.1 ≈ 6-10 tests, golden inchangé ; Opt.2 ≈ 20-30 tests + cohérence bidirectionnelle fragile (faux-vert) |

**Décision retenue : Option 1 pour la Story 16.2, en mode Hybride borné** (Direct Adjustment).

- **16.2 backend** dérive l'attendu HA de la source runtime existante : `HA_COMPONENT_REGISTRY` **+ la logique des mappers** (pas le registry seul — voir angle mort granularité). Aucun loader YAML, aucune 2e source de vérité runtime.
- **Le YAML reste un artefact de planning**, conforme à son propre `_meta.note` (dérivation, pas chargement).
- **Frontière 16b actée** : les labels FR / familles / subtypes du sélecteur d'override proviendront de `jeedom_generic_types` (via un chargeur/export dédié dans le scope 16b), jamais inventés. La lecture 16.2 expose une **structure ouverte à enrichissement** (champs label nullable en 16a).

### Angles morts remontés par le débat (à intégrer, sinon bugs latents)

1. **Granularité (Données + Pipeline)** — "l'attendu HA par commande" dépend des **allowlists par mapper** (`_LIGHT_GENERIC_TYPES`, `registry.py`), PAS du seul `HA_COMPONENT_REGISTRY`. Une Option 1 naïve limitée au registry serait **incomplète**. Gérer aussi `FallbackMapper` et le multi-entités (`map_all`) : ce n'est pas toujours 1 commande → 1 composant.
2. **Séquencement produit (Produit/UX)** — piège du "faux découplage inversé" : si 16.2 dérive du registry sans acter d'où viendront les labels FR, **16b reproduit la frustration Homebridge** (choisir un type à l'aveugle). L'échec produit se matérialiserait en 16b, pas en 16.2.
3. **Cohérence validate↔attendu (Pipeline)** — l'attendu exposé DOIT être celui que `validate_projection()` applique, sinon on annonce "HA attend X" alors que la validation impose Y.
4. **Faux-vert de test (Test/Maintenance)** — deux sources = un test peut valider le YAML pendant que le mapper diverge → vert mais faux. Option 1 rend le drift structurellement impossible.
5. **Dette de gouvernance révélée (mais hors 16.2)** — le `ha_component_registry.yaml` "dérivé, consommé par le daemon" prévu par le `_meta.note` n'a jamais été généré ; le daemon utilise un dict à la main. À noter comme concern séparé, **pas** un blocage de 16.2.

---

## Section 4 — Propositions de changement détaillées

### 4.1 — Story 16.2 (`16-2-attendu-ha-application-overrides-mapping-candidat.md`)

**Task 5 (AC1) — OLD :**
> Ajouter une fonction de lecture `resolve_*` … exposant, pour une commande, le(s) composant(s) HA et `generic_type` compatibles. … Dériver l'attendu depuis cette source runtime (registry).

**NEW :**
> Ajouter une fonction de lecture `resolve_*` (ex. `resolve_expected_ha(...)`) dérivant l'attendu HA d'une commande de la **source runtime = `HA_COMPONENT_REGISTRY` + logique des mappers** (`registry.py` + allowlists par mapper), **pas du registry seul**. Couvrir explicitement `FallbackMapper` et le multi-entités (`map_all`) — l'attendu n'est pas toujours 1 commande → 1 composant. La structure de retour prévoit des champs d'enrichissement label FR / famille / subtype **nullable** (remplis en 16b, absents en 16a). Documenter dans les Dev Notes que le YAML reste un artefact de planning (conforme à son `_meta.note` : dérivation, pas chargement runtime).

**Résolution du "conflit source de vérité" (Project Structure Notes) — OLD :** décision "à trancher en dev-story".
**NEW :** **TRANCHÉ (SCP 2026-07-07, Option 1)** — source runtime = registry + mappers ; YAML = planning. Ajout d'une **frontière 16b** : labels FR/familles/subtypes du sélecteur override viendront de `jeedom_generic_types` via chargeur/export dédié en 16b ; interdiction de démarrer 16b sans cette source.

### 4.2 — Delta architecture (`architecture-delta-pe-epic-16-mapping-configurable.md`)

**Ajout d'une note de correction** (section "Gap Analysis" ou nouvelle sous-section) :
> **Correction 2026-07-07 (SCP)** : la "source de vérité pour l'attendu HA" au **runtime** est le registre runtime dérivé (`HA_COMPONENT_REGISTRY` + mappers), conforme au `_meta.note` de `ha-projection-reference.yaml` qui prescrit une **dérivation** vers l'artefact consommé par le daemon, non un chargement direct du YAML de planning. Le YAML demeure la source de vérité **documentaire/de planning**. Concern séparé (hors epic 16) : le `ha_component_registry.yaml` dérivé prévu par le `_meta.note` n'a jamais été généré ; le daemon maintient un dict Python à la main — dette de gouvernance à cadrer indépendamment.

### 4.3 — Epic 16 / stories 16b (16.5-16.7)

**Ajout d'un pré-requis bloquant** (à reporter lors de leur `create-story`) :
> Le sélecteur d'override par commande consommera les labels FR / familles / subtypes de la section `jeedom_generic_types` de `ha-projection-reference.yaml` (chargeur ou export dédié, cadré en 16b). Ne pas livrer un sélecteur affichant des identifiants HA crus (anti-régression Homebridge).

---

## Section 5 — Handoff & classification

**Classification de portée : Moderate** (réorganisation légère + correction d'artefacts, pas de replan fondamental, pas de rollback, MVP inchangé).

**Handoff :**
- **Dev (clawcode)** : appliquer 4.1 (Story 16.2) puis enchaîner `dev-story` en Option 1.
- **SM/PO (clawcode)** : appliquer 4.2 (note archi) et 4.3 (pré-requis 16b), aligner `sprint-status.yaml`.
- **Concern séparé** (dette `ha_component_registry.yaml` dérivé non généré) : backlog gouvernance, hors Epic 16.

**Critères de succès :** Story 16.2 implémentable sans ambiguïté de source ; `validate_projection` et l'attendu exposé partagent la même vérité ; 16b a une source actée pour ses labels ; 0 régression golden.

**MVP impact :** aucun.

---

## Approbation

- [x] **Alexandre approuve ce Sprint Change Proposal (2026-07-07)** → changements 4.1 (Story 16.2 Task 5 + Project Structure Notes), 4.2 (note archi delta), 4.3 (frontière 16b) appliqués + `sprint-status.yaml` MAJ. Enchaînement `dev-story` Story 16.2 (Option 1).
