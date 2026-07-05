# Sprint Change Proposal — 2026-07-05 — Réalignement gouvernance pe-epic-13 / pe-epic-14

**Workflow :** correct-course (BMAD bmm/4-implementation)
**Scrum Master :** clawcode (Sonnet) pour Alexandre
**Mode :** Batch
**Classification de portée :** Mineure (bookkeeping — aucun changement de code produit, aucune story créée/supprimée)

---

## Section 1 — Issue Summary

Audit demandé par Alexandre sur l'alignement des interfaces jeedom2ha (`desktop/php`, `desktop/js`) avec les epics 11 à 14, en signalant explicitement que 13 et 14 n'étaient pas clôturées. L'audit a confirmé deux écarts de gouvernance BMAD, distincts de la question initiale sur les interfaces :

1. **`pe-epic-13`** restait `in-progress` dans `sprint-status.yaml` alors que ses 4 stories (13.1 à 13.4) étaient toutes `done` depuis le 2026-07-03. Le flip epic-level n'avait jamais été fait. Aucune retrospective (`pe-epic-13-retrospective`) n'existait, contrairement aux epics 11 et 12.
2. **`pe-epic-14`** était `done` dans `sprint-status.yaml` mais **n'existait dans aucun document d'epics** (`epics-projection-engine.md`) — il avait été traité entièrement via SCP Minor/Direct Adjustment (`sprint-change-proposal-2026-07-04-fan-switch-parity.md`) sans jamais passer par une formalisation epic, et sans retrospective. Alexandre avait explicitement demandé le respect strict de la méthode BMAD ; ce contournement constitue un manquement direct à cette consigne.

Côté interfaces (question initiale d'Alexandre) : aucun AC des epics 11-14 ne touchait `desktop/*` (confirmé par `git log`, zéro commit sur la console depuis l'epic 6 / 2026-04-25). Ce n'est pas un oubli de dev, mais un angle mort produit réel : la console n'expose rien sur les nouvelles capacités Energy (`state_class`), le state-streaming, ni la parité FAN_STATE.

## Section 2 — Cause racine

1. **Flip epic-level manuel oublié à la clôture de la dernière story.** Comme déjà identifié dans le SCP du 2026-06-19 (cause #1 récurrente), le passage `done` d'un epic dépend d'une action manuelle après le `code-review` de la dernière story ; rien ne la force.
2. **Absence de garde-fou sur les changements Minor/Direct Adjustment.** Le classement "Minor" d'un SCP a été interprété comme dispensant de toute formalisation epic, alors qu'il ne dispense que de la gouvernance FR/NFR — pas de la traçabilité BMAD (epic + retrospective).
3. **Aucune checklist de clôture d'epic exécutée systématiquement** avant de considérer un epic terminé (flip + retro), malgré son existence pour les epics 11/12.

## Section 3 — Recommended Approach

**Option retenue : Direct Adjustment.** Réaligner `sprint-status.yaml` sur la réalité (flip `pe-epic-13` → `done`), matérialiser les deux retrospectives manquantes (`pe-epic-13-retro-2026-07-05.md`, `pe-epic-14-retro-2026-07-05.md`), et formaliser rétroactivement `pe-epic-14` dans `epics-projection-engine.md`.

Alternatives écartées : Rollback (N/A — le code des deux epics est bon, revu, et gate terrain PASS) ; MVP Review (N/A — aucun changement de périmètre produit).

## Section 4 — Detailed Change Proposals

### Retrospectives (BMAD workflow `retrospective`)
- `pe-epic-13-retro-2026-07-05.md` créé : valeur livrée, preuves gate terrain (dont limitation HA UI/registry non prouvée par manque de token), et deux leçons retenues — (1) gouvernance de clôture manquante, (2) angle mort UI/daemon jamais scopé mais réel, à corriger par principe permanent d'alignement UI/daemon.
- `pe-epic-14-retro-2026-07-05.md` créé : valeur livrée, préreuves gate terrain (correctif fallback single-trio-per-family découvert en conditions réelles), et deux leçons retenues — (1) manquement direct à la consigne BMAD explicite d'Alexandre (epic jamais formalisé), (2) le gate terrain a de nouveau révélé un cas non testable unitairement.

### sprint-status.yaml
- `pe-epic-13` : `in-progress` → **`done`**
- `pe-epic-13-retrospective` : ajouté, **`done`**
- `pe-epic-14-retrospective` : ajouté, **`done`**
- `last_updated` → 2026-07-05
- Commentaire d'en-tête de section « Cycle Moteur de Projection Explicable » mis à jour pour refléter pe-epic-1..14 done et le statut de formalisation de pe-epic-14.

### epics-projection-engine.md
- Nouvelle entrée dans le tableau FR coverage : `pe-epic-14` référencé pour la parité FAN_* → switch.
- Nouvelle section `## Epic 14 — Parité générique FAN_* -> switch` ajoutée rétroactivement, avec sa story 14.1 et ses gates epic-level, y compris l'enseignement de gouvernance explicite.

## Section 5 — Implementation Handoff

**Portée : Mineure** → exécutée directement (SM/dev). Pas d'escalade PO/PM/Architecte.

**Recommandation préventive (cause racine), formalisée comme règle permanente :**
1. Aucun epic — y compris un changement scope Minor/Direct Adjustment traité par SCP — ne doit être considéré clos sans (a) une entrée epic formalisée dans le document de référence et (b) une retrospective matérialisée.
2. Le flip epic-level `done` doit être vérifié et exécuté explicitement dans le même geste que la clôture de la dernière story de l'epic, pas différé.
3. Un futur epic de visibilité console (Energy `state_class`, statut streaming, parité FAN) doit être cadré par un SCP dédié, avec comme principe directeur permanent : toujours réévaluer l'alignement UI/daemon à chaque extension de capacité daemon, même hors AC explicite.

**Critères de succès :** `sprint-status.yaml` cohérent avec la réalité des stories ; `pe-epic-13` et `pe-epic-14` tous deux `done` avec retrospective matérialisée ; `pe-epic-14` traçable dans `epics-projection-engine.md` ; règle de non-bypass de la formalisation epic documentée pour les futurs SCP Minor/Direct Adjustment.
