# Sprint Change Proposal — 2026-06-21 — Réalignement 11.3 et artefacts actifs

**Workflow :** correct-course (BMAD bmm/4-implementation)  
**Scrum Master :** Bob / clawcode pour Alexandre  
**Mode :** Batch  
**Classification de portée :** Mineure (bookkeeping + closeout dev-story ; aucun changement de périmètre produit)

---

## Section 1 — Issue Summary

La story 11.3 était réellement en cours d'implémentation dans le worktree `projects/jeedom2ha-pe-12.1`, mais plusieurs artefacts de pilotage restaient sur des états antérieurs :

- `active-cycle-manifest.md` pointait encore vers le correct-course du 2026-06-07 et `pe-epic-10 / 10.0` comme prochaine étape.
- `epics-projection-engine.md` décrivait encore 11.3 comme backlog différé, 12.1 comme "à créer" et 12.2 comme réservée.
- `sprint-status.yaml` marquait 11.3 `in-progress`, mais les tests locaux de closeout dev-story n'étaient pas consignés dans la story.

Déclencheur : demande Alexandre du 2026-06-21 de clore 11.3 côté BMAD-SM et d'aligner les artefacts, avec clarification de 11.2 et du séquencement 11.3 avant 11.2.

## Section 2 — Impact Analysis

### Epic Impact

- `pe-epic-11` reste `in-progress` : 11.1 et 11.1-bis sont done ; 11.3 passe en review ; 11.2 reste réservée/non créée.
- `pe-epic-12` reste `done` : 12.1 et 12.2 sont livrées, et 12.2 a levé la dépendance actionnable qui bloquait 11.3.

### Story Impact

| Story | Avant | Après |
| --- | --- | --- |
| 11.2 — Chauffe-eau eq554 | réservée, non créée | inchangé ; prochaine story candidate après 11.3 |
| 11.3 — IQ EV + pilotage priorisation | in-progress | review après closeout dev-story local |

### Artifact Conflicts

- PRD : aucun changement requis.
- Architecture : aucun changement requis.
- Epics / manifeste / sprint-status : réalignement documentaire requis.
- Story 11.3 : record dev-story à compléter avec preuves de tests et statut `review`.

## Section 3 — Recommended Approach

**Direct Adjustment.** Réaligner les artefacts actifs sur la réalité du travail, sans rollback ni changement de MVP.

Rationale :

- Le séquencement 11.3 avant 11.2 est explicable par dépendance : 11.3 attendait 12.2 pour les états actionnables `switch/button`, et cette dépendance est désormais levée.
- 11.2 est le chauffe-eau eq554, P2, non encore créé ; sa partie `switch.554` dépendait aussi de 12.2 mais n'était pas la story déjà prête dans le workboard.
- Le code 11.3 est prêt pour review locale : tests ciblés 6/6 et suite daemon 903/903.
- Le gate terrain eq583/eq628 reste à exécuter avant `done`.

## Section 4 — Detailed Change Proposals

### `sprint-status.yaml`

- `last_updated` → 2026-06-21.
- 11.3 : `in-progress` → `review`.
- Commentaire `pe-epic-11` mis à jour : 11.3 en review, 11.2 toujours réservée/non créée.

### `11-3-iq-ev-pilotage-priorisation-solaire.md`

- `Status: in-progress` → `Status: review`.
- Tasks 1 à 4 cochées ; Task 5 partiellement faite, gate terrain restant.
- Ajout des preuves :
  - `python3 -m pytest resources/daemon/tests/unit/test_story_11_3_iq_ev_priorisation.py -q` → 6 passed.
  - `python3 -m pytest resources/daemon/tests -q` → 903 passed.
- File List complétée.

### `epics-projection-engine.md`

- 11.3 décrite comme `review`, non plus backlog différé.
- 12.1 et 12.2 décrites comme `done`.
- Séquencement 11.2/11.3 explicité.

### `active-cycle-manifest.md`

- SCP le plus récent → présent document.
- Prochaine étape BMAD → `code-review` 11.3, puis gate terrain / décision `done`; ensuite création de 11.2 si Alexandre confirme la priorité chauffe-eau.

## Section 5 — Implementation Handoff

Portée mineure : exécution directe par dev/SM.

Prochaines responsabilités :

- Dev/QA : lancer `code-review` 11.3.
- Terrain : exécuter le gate DEV/TEST eq583/eq628 via `scripts/deploy-to-box.sh` ou déléguer à ClawBox si validation maison.
- SM : après review + gate, seulement alors passer 11.3 à `done`.
- SM/PO : créer 11.2 si la priorité redevient chauffe-eau eq554.

Succès : `sprint-status.yaml`, story 11.3, manifeste actif et epics actifs racontent la même histoire ; aucun `done` prématuré.
