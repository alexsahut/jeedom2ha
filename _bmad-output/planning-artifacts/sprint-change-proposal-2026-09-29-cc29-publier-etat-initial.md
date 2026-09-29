# Sprint Change Proposal — 2026-09-29 — CC-29 : « Publier » ne publie pas l'état initial

## 1. Résumé de l'issue

Une entité publiée pour la première fois par un clic « Publier » reste `unknown` dans
Home Assistant jusqu'à son premier changement d'état. Le sync publie l'état initial
(Story 12.1, `StateSynchronizer.publish_initial_states`, appelé après
`apply_publication_decision` dans `_do_handle_action_sync`,
`resources/daemon/transport/http_server.py:1868`) ; « Publier » ne le fait pas
(vérifié : aucun appel à `publish_initial_states` dans la branche « Publier »,
`resources/daemon/transport/http_server.py:3837-3951`). C'était un choix documenté
dans la Story 19.4 (« mieux vaut `unknown` explicite qu'une valeur silencieusement
obsolète »). Cas terrain typique : « Suppr. » puis « Republier » sur une pièce —
constaté par Alexandre.

## 2. Décision

Alexandre, le 2026-09-29 à 23:46 : « ok pour envoyer la valeur actuelle ; si c'est
une nouvelle fonctionnalité, fais-le dans les règles de la méthode BMAD ». C'est un
changement de comportement volontaire, pas un simple bugfix — il modifie le payload
que le relais PHP envoie au démon (`core/ajax/jeedom2ha.ajax.php`), donc un parcours
BMAD complet (`docs/bmad-parcours-rapide-complet.md`).

## 3. Impact

- **Epic 19** (contrat de décision unifié, `_bmad-output/planning-artifacts/epics-projection-engine.md`) :
  ajout de la Story 19.5, qui ferme CC-29. N'ouvre aucun nouveau FR/NFR PRD, ne
  touche pas `evaluate_equipment()`.
- **Code concerné** : `core/ajax/jeedom2ha.ajax.php` (action `executeHaAction`,
  aujourd'hui un relais strict sans calcul local, Story 5.1) et
  `resources/daemon/transport/http_server.py` (branche « Publier »,
  ligne ~3837).
- **UI Impact** : oui — `core/ajax/` est modifié, donc `ready-for-UX-validation`
  avant `done`.
- Pas d'impact PRD/architecture/UX documents existants au-delà de l'ajout de la
  story dans l'epic.

## 4. Approche retenue

**Direct Adjustment** — ajout d'une story (19.5) à l'epic 19 existant. Scope
**minor** : implémentation directe par l'équipe de dev, sans réorganisation de
backlog ni replan PM/Architecte.

Conception (proposée par ClaudeBox, à challenger en dev-story si besoin) :
- Le relais PHP lit les valeurs au clic (`$cmd->getCache('value', null)`, motif
  déjà utilisé par `getFullTopology`, `core/class/jeedom2ha.class.php:729`) et les
  ajoute au payload sous `current_values: {cmd_id: valeur}`. Aucune logique de
  décision en PHP.
- Le démon publie l'état initial pour « Publier », en réutilisant
  `publish_initial_states()` après la discovery, avec le même garde par candidat
  que le sync.
- Une commande sans valeur fraîche au clic ne reçoit aucun état (pas de valeur
  périmée).

## 5. Changement d'artefact

**Epic 19** (`_bmad-output/planning-artifacts/epics-projection-engine.md`) :
ajout de la Story 19.5 (E) à la liste des stories, et CC-29 aux points fermés visés.

## 6. Handoff

- **Scope : Minor.** Implémentation directe par le dev.
- Story détaillée : `_bmad-output/implementation-artifacts/19-5-publier-etat-initial-valeur-courante-cc29.md`.
- `sprint-status.yaml` : `19-5-publier-etat-initial-valeur-courante-cc29: ready-for-dev`.

## 7. Complétion

- Issue traitée : CC-29 (« Publier » ne publie pas l'état initial).
- Scope : Minor (ajout de story dans l'epic existant).
- Artefacts modifiés : `epics-projection-engine.md`, story 19.5 (nouvelle),
  `sprint-status.yaml`.
- Routé vers : équipe de dev (create-story → dev-story → code-review, puis
  ready-for-UX-validation).
