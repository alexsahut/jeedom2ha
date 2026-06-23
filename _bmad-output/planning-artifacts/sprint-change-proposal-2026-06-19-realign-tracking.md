# Sprint Change Proposal — 2026-06-19 — Réalignement du tracking (sprint-status ↔ réalité)

**Workflow :** correct-course (BMAD bmm/4-implementation)
**Scrum Master :** clawcode (Opus) pour Alexandre
**Mode :** Batch
**Classification de portée :** Mineure (bookkeeping — aucun changement de code produit, aucune story ni epic créés/supprimés)

---

## Section 1 — Issue Summary

`sprint-status.yaml` et les en-têtes `Status:` de plusieurs stories étaient **désynchronisés de la réalité mergée dans `main`** :

| Story | Tracking (avant) | Réalité (git/main) |
|---|---|---|
| 11.1 | `review` | done — gate terrain PASS, mergée PR #123 (`ce2b5b7`) |
| 11.1-bis | `review` | code done (PR #123) ; gate terrain AC6 jamais exécuté |
| 12.1 | `ready-for-dev` | done — dev + gate terrain PASS 2026-06-18, mergée PR #123 |
| pe-epic-12 | `in-progress` | gate epic-level atteint (eq553 non-unknown via 12.1) |

**Découverte :** lors du choix de « la story suivante » après merge de la 12.2 (PR #125), la recommandation initiale (« développer la 12.1, jamais faite ») s'appuyait sur le `sprint-status.yaml` périmé. Alexandre a signalé que 12.1 / 11.1 / 11.1-bis étaient en réalité faites.

## Section 2 — Cause racine

1. **Gate terrain manuel hors BMAD (cause #1).** Ce projet ajoute une validation terrain sur box réelle APRÈS `code-review`. Le passage à `done` est commité à la main (`chore(bmad): close … gate terrain PASS`) et ces commits manuels **oublient le flip de `development_status`** dans `sprint-status.yaml` et/ou l'en-tête de story. Preuve : `ce2b5b7` « close 11.1 gate terrain PASS » a laissé 11.1 à `review`.
2. **`code-review` BMAD non rejoué.** 12.1 développée + gate terrain PASS mais `code-review` jamais relancé → restée `ready-for-dev` (le workflow `code-review` est le seul à écrire `done`).
3. **Multi-worktrees** (`-pe-11.1`, `-pe-12.1`, …) partageant le même fichier tracké : les flips faits sur une branche forkée tôt sont noyés au merge ; la passe 12.2 n'a touché que sa propre ligne.
4. **`bmad-sprint-status` est read-only** (résumé) — aucun workflow ne réconcilie automatiquement tracking ↔ réalité.

## Section 3 — Recommended Approach

**Option retenue : Direct Adjustment** (effort Low, risque Low). Réaligner le tracking sur la réalité de `main`, exécuter le seul reliquat réel (gate terrain AC6 de 11.1-bis), et clôturer pe-epic-12 dont le gate epic-level est atteint.

Alternatives écartées : Rollback (N/A — le code est bon et mergé) ; MVP Review (N/A — pas de changement de périmètre produit).

## Section 4 — Detailed Change Proposals

### Gate terrain 11.1-bis (AC6) — exécuté, PASS
Box 192.168.1.21, 2026-06-19. `POST /action/execute {intention:"supprimer", portee:"equipement", selection:[553]}` → `succes`. `mosquitto_sub homeassistant/+/+/config` : eq553 **65 → 0** topics `config` retained, **zéro ghost** (dépublication multi-sensor exhaustive prouvée sur 65 capteurs réels). Restauration via `getFullTopology()` + `callDaemon('/action/sync')` (284 eq_logics) → eq553 **revenu à 65**.

### sprint-status.yaml
- `11-1-msunpv-…` : `review` → **`done`**
- `11-1-bis-…` : `review` → **`done`** (gate AC6 PASS ci-dessus)
- `12-1-streaming-…` : `ready-for-dev` → **`done`**
- `pe-epic-12` : `in-progress` → **`done`** (gate epic-level = eq553 non-unknown, atteint via 12.1 ; vague 2 actionnable bonus 12.2 done)
- `pe-epic-11` : reste **`in-progress`** (11.2 chauffe-eau eq554 non créée, 11.3 IQ EV backlog)
- `last_updated` → 2026-06-19 + note de réalignement

### En-têtes de stories
- 11.1, 11.1-bis, 12.1 : `Status:` → `done` ; AC6 de 11.1-bis cochée avec preuve terrain.

## Section 5 — Implementation Handoff

**Portée : Mineure** → exécutée directement (dev/SM). Pas d'escalade PO/PM/Architecte.

**Recommandation préventive (cause racine) :** intégrer le flip `done` (sprint-status + en-tête) dans le commit de close gate terrain — idéalement un mini-checklist de close, ou rejouer `bmad-code-review` qui écrit `done` automatiquement. À défaut, passer `correct-course` en réconciliation périodique.

**Critères de succès :** `git` ↔ `sprint-status.yaml` ↔ en-têtes cohérents ; pe-epic-12 clôturé ; reliquats réels = 11.2 (à créer) + 11.3 (backlog) sous pe-epic-11.
