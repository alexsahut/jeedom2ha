---
artifact_type: sprint-change-proposal
project: jeedom2ha
date: '2026-07-07'
workflow: correct-course
author: clawcode (Scrum Master)
trigger_story: 16.3
status: approved
mode: batch
decision_method: ADR multi-persona (3 sous-agents parallèles : Pipeline/Runtime, Données/Schéma, Produit/UX-Diagnostics)
---

# Sprint Change Proposal — 2026-07-07 (16.3)

**Déclencheur :** Story 16.3 (Epic 16 — mapping configurable), Task 1 — question ouverte de cadrage identifiée dès `create-story` : le schéma de persistance des overrides (v1, Story 16.1/16.2, déjà en prod) ne supporte nativement ni l'exclusion au niveau équipement seul, ni un champ `publication_override`.
**Méthode de décision :** débat ADR à 3 personas en sous-agents parallèles (Pipeline/Runtime Architect, Données/Schéma Architect, Produit/UX & Diagnostics Architect), chacune analysant la question indépendamment sans se consulter, pour éviter les angles morts.

---

## Section 1 — Résumé du problème

Le fichier `data/ha_overrides.json` (schéma v1, `resources/daemon/mapping/overrides.py`) ne connaît qu'une clé composite `<eq_id>:<cmd_id>` portant un seul champ exploité, `ha_entity_type`. La Story 16.3 exige deux capacités nouvelles côté override :

1. **Exclusion explicite** d'un équipement entier OU d'une commande seule — l'utilisateur veut le plus souvent dire "j'exclus tout cet équipement", pas lister chaque `cmd_id`.
2. **Forçage de publication** (`force_publish`) d'un mapping dont la projection est valide (`is_valid == True`) mais bloqué par la politique produit (`confidence_policy`/`product_scope`) — jamais si `is_valid == False` (I2 non négociable, absolu).

Le schéma v1 actuel ne porte ni la granularité équipement-seul, ni un champ dédié à cette nouvelle décision (`publication_override`), sans risquer une confusion structurelle avec `ha_entity_type` (Story 16.1/16.2) ou avec le mécanisme d'exclusion natif Story 4.3 (`JeedomEqLogic.is_excluded`/`exclusion_source`, évalué à l'étape 1, reason_codes `excluded_eqlogic`/`excluded_plugin`/`excluded_object`).

**Type d'issue :** trou de conception identifié en `create-story`, avant tout code — pas un bug, pas un écart doc/code (contrairement au SCP du 07-07 précédent sur la Story 16.2).

---

## Section 2 — Analyse d'impact (checklist correct-course)

**§1 Trigger** — Story 16.3, Task 1. Problème : granularité de persistance insuffisante pour AC1/AC2. [Done]

**§2 Impact Epic**
- Epic 16 reste réalisable tel quel, aucune story rendue obsolète. [Done]
- Aucun resequencing. Décision structurante pour 16.4 (diagnostic override-aware) qui devra consommer les mêmes reason_codes — alignement nécessaire dès maintenant. [Action-needed → tracé Section 4]

**§3 Conflits artefacts**
- 3.1 PRD : aucun conflit, FR couverts par les deux options envisagées. [N/A]
- 3.2 Architecture : `architecture-delta-pe-epic-16-mapping-configurable.md` ne documente que le cas type-override (D8-D12) ; silence total sur la granularité équipement/commande pour la publication — à compléter. [Action-needed]
- 3.3 Autres (tests, golden corpus) : nouveau test file prévu par la story (`test_story_16_3_publication_override.py`), aucun impact golden hors nouveaux topics/diagnostics attendus. [Done]

**§4 Chemin — évaluation**
- **Option 1 (Direct Adjustment — section dédiée `equipment_overrides` + bump `schema_version: 2`)** : Effort **Low-Medium**, Risque **Low**. **VIABLE, recommandée.**
- **Option 2 (dict unique `overrides` avec discriminant `scope` + clés eq_id-only mêlées aux clés composites)** : Effort **Low**, Risque **Medium** (ambiguïté de parsing, deux personas sur trois l'écartent explicitement). **Viable mais non retenue.**
- **Rollback** : sans objet, rien à annuler (aucun code 16.3 encore écrit). **N/A.**

---

## Section 3 — Approche recommandée

### Verdict du débat ADR (3 personas)

| Persona | Verdict | Argument dominant |
|---|---|---|
| Pipeline/Runtime Architect | **Option 1** (section séparée `equipment_overrides`) | Résolution pure (`resolve_publication_override`) sans dépendance mapper (D8) ; `overrides_cache` réutilisé tel quel aux 2 call-sites, zéro re-IO ; précédence explicite : exclusion équipement = veto absolu > override commande > force_publish équipement en défaut |
| Données/Schéma Architect | **Option 1** (bump `schema_version: 2`, section `equipment_overrides` séparée) | Mélanger clés `eq_id` seules et `eq_id:cmd_id` dans un même dict est fragile à parser et rompt la garantie D9 (la version doit refléter fidèlement la structure) ; migration v1→v2 transparente en mémoire, réécriture disque différée au prochain save |
| Produit/UX & Diagnostics Architect | **Option 2** initialement (dict unique + `scope`), mais accepte Option 1 si les reason_codes restent ceux proposés | Le point dur n'est pas la forme de la clé mais la **clarté diagnostique** : reason_codes `publication_excluded_eqlogic` / `publication_excluded_command` / `publication_forced`, jamais confondus avec Story 4.3 (`excluded_eqlogic`/...) ; `force_publish` ne doit jamais réécrire le `reason` "nominal" (I6/D11) |

**Décision retenue : Option 1** — 2 personas sur 3 la recommandent directement pour des raisons de robustesse de parsing/validation (D9), et le désaccord de la 3e persona porte sur la forme de la clé, pas sur le vocabulaire diagnostique (repris intégralement dans la décision). Aucun conflit réel entre les 3 avis sur les invariants I2/D8/D10/D11.

### Décision détaillée

**Schéma (`resources/daemon/mapping/overrides.py`, `data/ha_overrides.json`) :**

```json
{
  "schema_version": 2,
  "overrides": {
    "<eq_id>:<cmd_id>": {"source": "user", "ha_entity_type": "...", "publication_override": "exclude" | "force_publish" | null}
  },
  "equipment_overrides": {
    "<eq_id>": {"source": "user", "publication_override": "exclude" | "force_publish"}
  }
}
```

- `_load_raw` accepte désormais `schema_version ∈ {1, 2}` ; toute autre valeur reste un refus explicite loggé (D9 inchangé dans son principe).
- Un fichier v1 existant (déjà en prod, Story 16.1/16.2) se charge sans action utilisateur : `equipment_overrides` défaut `{}` en mémoire, jamais de réécriture disque depuis un chemin de lecture pure (`list_overrides`) — la réécriture n'a lieu qu'au prochain `save_override`/nouvelle fonction `save_equipment_override`.
- Nouvelles fonctions additives dans `overrides.py` (aucune signature existante brisée) : `list_equipment_overrides(data_dir)`, `save_equipment_override(eq_id, override, data_dir)`, `remove_equipment_override(eq_id, data_dir)`, et surtout `resolve_publication_override(eq_id, cmd_id, overrides, equipment_overrides) -> Optional[str]` — fonction **pure**, aucune I/O, ne dépend d'aucun mapper concret (D8).

**Règle de précédence (identique dans les 3 avis, formulée par Pipeline + confirmée Produit/UX) :**

1. `equipment_overrides[eq_id].publication_override == "exclude"` → exclusion immédiate, veto absolu, quel que soit l'override de commande.
2. Sinon, override de **commande** (le plus spécifique) prime — `exclude` ou `force_publish`.
3. Sinon, `force_publish` équipement s'applique comme défaut à toutes ses commandes.
4. Sinon, comportement `decide_publication` inchangé.

**Intégration pipeline (`resources/daemon/models/decide_publication.py`, `http_server.py` L.1344 primaire / L.223 secondaire) :**

- `http_server.py` résout l'override AVANT l'appel (`pub_override = resolve_publication_override(eq_id, cmd_id, overrides_cache, equipment_overrides_cache)`) et le passe en paramètre optionnel à `decide_publication(mapping, confidence_policy=..., product_scope=..., publication_override=pub_override)`.
- Dans `decide_publication.py` : si `not projection_validity.is_valid` → `should_publish=False` sur la cause amont, `publication_override` totalement ignoré (I2/I4/D11 intacts) ; sinon `exclude` → `should_publish=False, reason="publication_excluded_eqlogic"` ou `"publication_excluded_command"` selon l'origine ; sinon `force_publish` → `should_publish=True, reason="publication_forced"` (jamais réécrit en `"sure"`/`"probable"`) avec `reason_details.underlying_confidence` conservant la vraie raison métier sous-jacente ; sinon logique `confidence_policy`/`product_scope` actuelle inchangée. Aucune logique MQTT/broker introduite (I7 intact).

**Reason_codes (jamais confondus avec Story 4.3) :** `publication_excluded_eqlogic`, `publication_excluded_command`, `publication_forced` — préfixe `publication_` distinct de `excluded_eqlogic`/`excluded_plugin`/`excluded_object` (Story 4.3, étape 1, exclusion native Jeedom) tout en restant de la même famille lexicale pour la lisibilité humaine (I6).

### Angles morts remontés par le débat

1. **Ambiguïté de parsing (Données)** — si la clé `equipment_overrides` n'existait pas et qu'on avait mêlé eq_id-only et eq_id:cmd_id dans le même dict `overrides`, un `eq_id` pourrait un jour coïncider avec un fragment mal parsé d'une clé composite. Tranché par la section séparée.
2. **Confusion diagnostique avec Story 4.3 (Produit/UX)** — sans préfixe `publication_` explicite, un `grep excluded_` future confondrait exclusion native (config Jeedom, étape 1) et exclusion volontaire HA (étape 4). Tranché par le vocabulaire dédié.
3. **`force_publish` masquant une réussite normale (Produit/UX, D11)** — le `reason` ne doit jamais rester `"sure"`/`"probable"` quand un forçage a eu lieu ; `reason_details.underlying_confidence` préserve la traçabilité sans réintroduire un bypass silencieux.
4. **Story 16.4 (diagnostic override-aware)** — devra consommer exactement ces reason_codes (`publication_excluded_eqlogic`/`publication_excluded_command`/`publication_forced`) ; à rappeler explicitement dans son `create-story` pour éviter une re-divergence de vocabulaire.

---

## Section 4 — Propositions de changement détaillées

### 4.1 — Story 16.3 (`16-3-overrides-publication-exclusion-explicite.md`)

**Task 1 — OLD :** flaguée "question ouverte", schéma non tranché.

**NEW :** **TRANCHÉ (SCP 2026-07-07, Option 1)** — `schema_version: 2`, section `equipment_overrides` séparée de `overrides` (clé composite inchangée), champ `publication_override` ajouté aux deux niveaux, précédence exclusion-équipement > commande > force_publish-équipement > nominal, reason_codes `publication_excluded_eqlogic`/`publication_excluded_command`/`publication_forced`. Nouvelles fonctions additives : `list_equipment_overrides`, `save_equipment_override`, `remove_equipment_override`, `resolve_publication_override` (pure, D8).

**Task 3 — précision ajoutée :** `resolve_publication_override` est appelée côté `http_server.py` (pas dans `decide_publication.py`), le résultat est passé en paramètre — `decide_publication.py` reste une fonction de décision pure, sans dépendance cache/overrides (cohérent avec I7 et le principe déjà appliqué à `confidence_policy`).

### 4.2 — Delta architecture (`architecture-delta-pe-epic-16-mapping-configurable.md`)

**Ajout d'une note de correction** (section D8-D12 ou nouvelle sous-section) :
> **Correction 2026-07-07 (SCP, Story 16.3)** : le schéma de persistance des overrides passe en `schema_version: 2` avec une section `equipment_overrides` dédiée à la granularité équipement (distincte de `overrides`, clé composite `eq_id:cmd_id`). Migration v1→v2 transparente en mémoire, jamais de réécriture disque au chemin de lecture. `resolve_publication_override` reste pure et sans dépendance mapper (D8 étendu à ce nouveau besoin).

### 4.3 — Story 16.4 (préparation, non bloquante pour 16.3)

**Ajout d'un rappel** à intégrer lors du `create-story` de 16.4 :
> Le diagnostic override-aware doit consommer exactement les reason_codes actés en 16.3 (`publication_excluded_eqlogic`/`publication_excluded_command`/`publication_forced`), sans en introduire de nouveaux qui recouvriraient la même sémantique.

---

## Section 5 — Handoff & classification

**Classification de portée : Minor** (cadrage pré-code, aucune ligne de production encore écrite pour 16.3 ; ajustement direct de la story avant `dev-story`).

**Handoff :**
- **Dev (clawcode)** : appliquer 4.1 (Story 16.3 Task 1 + Task 3), puis enchaîner `dev-story` sur la base de cette décision.
- **SM/PO (clawcode)** : appliquer 4.2 (note archi) et 4.3 (rappel 16.4), aligner `sprint-status.yaml`.

**Critères de succès :** Story 16.3 implémentable sans ambiguïté de schéma ; I2/I4/I6/I7/D8/D10/D11 tous respectés par construction ; aucune confusion de reason_code possible avec Story 4.3 ; migration v1→v2 sans perte de données pour les fichiers déjà en prod.

**MVP impact :** aucun.

---

## Approbation

- [x] **Alexandre approuve ce Sprint Change Proposal (2026-07-07, 16.3)** → changements 4.1 (Story 16.3 Task 1 + Task 3), 4.2 (note archi delta), 4.3 (rappel 16.4) appliqués + `sprint-status.yaml` mis à jour. Enchaînement `dev-story` Story 16.3 sur la base de l'Option 1.
