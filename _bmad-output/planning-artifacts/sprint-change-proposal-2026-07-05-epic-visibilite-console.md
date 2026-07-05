# Sprint Change Proposal — 2026-07-05 — Nouvel epic pe-epic-15 : visibilité console des capacités daemon (Energy, streaming, FAN)

**Workflow :** correct-course (BMAD bmm/4-implementation)
**Scrum Master :** clawcode (Sonnet) pour Alexandre
**Mode :** Batch
**Classification de portée :** Modérée (nouvel epic + stories à créer — réorganisation de backlog, PO/SM)

---

## Section 1 — Issue Summary

Suite à l'audit du 2026-07-05 (cf. `sprint-change-proposal-2026-07-05-gouvernance-epics-13-14.md`), un angle mort produit réel a été confirmé, distinct du manquement de gouvernance déjà traité : la console (`desktop/php`, `desktop/js`) n'a jamais été mise à jour pour exposer les capacités ajoutées par les epics 12, 13 et 14 côté daemon.

Preuve technique (`desktop/js/jeedom2ha_scope_summary.js:209-246`, fonction `buildEquipmentModel`) : le modèle de diagnostic par équipement expose déjà `reason_code`, `detail`, `remediation`, `matched_commands`/`unmatched_commands`, `actions_ha` — mais rien sur :

1. **Epic 13 (Energy HA)** : aucune indication du `state_class` (`measurement` / `total_increasing`) attribué à un sensor power/energy, ni de son unité résolue (W/kW/Wh/kWh).
2. **Epic 12 (state streaming)** : aucun indicateur de statut de streaming runtime (état publié / en attente / en échec) par équipement ou globalement.
3. **Epic 14 (parité FAN_* -> switch)** : aucune indication qu'un équipement a été rattaché à la famille `switch` via le fallback FAN générique, information utile pour le diagnostic terrain (cf. `pe-epic-14-retro-2026-07-05.md`, cas eq67 découvert uniquement en gate terrain).

Ceci n'est pas un oubli de développement : aucun AC des epics 11 à 14 ne portait sur la console. C'est un blind spot structurel identifié pour la première fois lors de cet audit, et la leçon retenue dans les rétrospectives 13/14 établit désormais un principe permanent : réévaluer l'alignement UI/daemon à chaque extension de capacité daemon.

## Section 2 — Impact Analysis

**Epic Impact** : nouvel epic autonome, pas de réouverture des epics 9/11/12/13/14 existants — lecture seule des métadonnées déjà calculées par le daemon, aucun changement de comportement de mapping/publication.

**Story Impact** : aucune story existante modifiée. 3 nouvelles stories à créer (une par capacité : Energy, streaming, FAN).

**Artifact Conflicts** : `epics-projection-engine.md` (nouvelle section epic) ; `sprint-status.yaml` (nouvel epic `backlog`, sans story tant que `create-story` n'a pas tourné, par convention du projet).

**Technical Impact** : lecture seule côté `desktop/php`/`desktop/js` (endpoint diagnostic existant + JS de rendu). Aucun changement daemon Python attendu a priori — à confirmer lors du cadrage de chaque story si les champs `state_class`/streaming/famille FAN doivent être ajoutés au payload diagnostic exposé par le daemon avant de pouvoir être consommés côté console.

## Section 3 — Recommended Approach

**Option retenue : Direct Adjustment (formalisation d'epic) + planification.** Ce SCP ne modifie aucun code produit. Il formalise `pe-epic-15` comme nouvel epic dans `epics-projection-engine.md`, avec 3 stories cadrées, et route l'exécution vers le workflow standard `create-story -> dev-story -> code-review` (BMAD), story par story, avec gate terrain sur box réelle pour chacune (cohérent avec la pratique des epics 11-14).

Alternatives écartées : Rollback (N/A — aucun changement à annuler) ; MVP Review (N/A — pas de réduction de périmètre, ajout d'une capacité de visibilité).

## Section 4 — Detailed Change Proposals

### epics-projection-engine.md — nouvelle section Epic 15

```
## Epic 15 — Visibilité console des capacités daemon (Energy, streaming, FAN)

Epic ajouté par `sprint-change-proposal-2026-07-05-epic-visibilite-console.md`, suite à l'audit de gouvernance du
2026-07-05 (voir `pe-epic-13-retro-2026-07-05.md` et `pe-epic-14-retro-2026-07-05.md`). La console
(`desktop/php`, `desktop/js`) n'expose aucune des capacités ajoutées par les epics 12/13/14 côté daemon. Cet epic
ne rouvre pas ces epics : il ajoute de la visibilité lecture seule dans la console sur des métadonnées déjà
produites (ou à exposer explicitement) par le daemon.

### Story 15.1 — Visibilité Energy state_class en console
Afficher, pour chaque sensor power/energy éligible, son `state_class` (measurement / total_increasing) et son
unité résolue (W/kW/Wh/kWh) dans le panneau de diagnostic équipement (`jeedom2ha_scope_summary.js`,
`buildEquipmentModel`). Lecture seule, aucun changement de mapping.

### Story 15.2 — Visibilité statut du state streaming runtime
Afficher un indicateur de statut de streaming runtime (publié / en attente / en échec) par équipement ou de
manière globale, pour donner une visibilité terrain sur la capacité livrée en epic 12. Lecture seule.

### Story 15.3 — Visibilité parité FAN_* -> switch en console
Indiquer, dans le diagnostic équipement, quand un équipement a été rattaché à la famille `switch` via le
fallback générique FAN (`FAN_STATE`/`FAN_ON`/`FAN_OFF`), pour faciliter le diagnostic terrain de cas similaires à
eq67 (découvert uniquement en gate terrain, cf. retro epic 14). Lecture seule.

### Gates epic-level pe-epic-15
- le workflow BMAD reste strict : `create-story -> dev-story -> code-review` pour chaque story, avec gate
  terrain sur box réelle (192.168.1.21) avant clôture, cohérent avec la pratique des epics 11-14 ;
- aucune story de cet epic ne modifie le comportement de mapping, de validation ou de publication existant :
  lecture seule des métadonnées de diagnostic ;
- si une story nécessite d'ajouter un champ au payload diagnostic daemon (state_class, statut streaming, famille
  FAN) avant de pouvoir le consommer côté console, ce point doit être cadré explicitement dans la story
  correspondante lors de `create-story`, sans réouvrir le mapping des epics 12/13/14 ;
- principe directeur permanent (issu des rétrospectives 13/14) : toujours réévaluer l'alignement UI/daemon à
  chaque nouvelle extension de capacité daemon, même hors AC explicite.
```

### sprint-status.yaml
- Pas d'entrée `pe-epic-15` ajoutée à ce stade : par convention du projet, un epic transite `backlog -> in-progress`
  automatiquement à la création de sa première story (`create-story`). L'entrée sera créée par ce mécanisme lors
  du lancement de la story 15.1, pas par ce SCP.

## Section 5 — Implementation Handoff

**Portée : Modérée** → routée vers Product Owner / Scrum Master (SM = clawcode) pour réorganisation de backlog. Pas de code produit touché par ce SCP.

**Recommandation préventive (cause racine, déjà actée en rétrospective 13/14) :** ce principe est désormais permanent et ne doit plus nécessiter de SCP de rattrapage : toute extension de capacité daemon doit inclure une évaluation explicite de son impact console dans le cadrage de la story correspondante.

**Prochaine action concrète :** lancer `create-story` sur Story 15.1 (visibilité Energy state_class), puis `dev-story`, puis `code-review`, avec gate terrain — story par story, dans l'ordre 15.1 → 15.2 → 15.3.

**Critères de succès :** `pe-epic-15` formalisé dans `epics-projection-engine.md` avec 3 stories cadrées ; aucun changement de comportement daemon existant introduit par ce SCP ; prochaine story exécutable directement via `create-story` sans reclarification supplémentaire.
