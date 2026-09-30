# Sprint Change Proposal — 2026-09-30 — CC-32 : durée des actions HA non bornée pour les grands parcs

## 1. Résumé de l'issue

Le délai de lissage inter-équipement des branches « Publier » et « Supprimer »
(`_action_delay = max(0.1, 10.0/max(1,len(eq_ids)))`,
`resources/daemon/transport/http_server.py:3881` pour Publier et `:3724` pour
Supprimer, `Décision 8` de `epic-5-lifecycle-matrix.md:439`) a un plancher de
0,1 s par équipement évalué, quel que soit `len(eq_ids)`. Pour un parc plus
grand que le parc actuel (mesuré ci-dessous : 94 publiés sur 121 inclus), le
temps total dépasse le délai de 15 s du relais PHP
(`core/ajax/jeedom2ha.ajax.php:764`, `callDaemon('/action/execute', …, 15)`).
Si le délai est dépassé, `callDaemon` rend `null`, le relais journalise une
erreur et lève une exception vers l'UI **avant** d'appeler
`jeedom2ha_realign_after_action` (réalignement des écouteurs, AC11 de la
Story 19.5) — ce réalignement est alors sauté, même si le démon va au bout de
l'action côté MQTT. Le client JS a son propre délai de 20 s
(`desktop/js/jeedom2ha.js:343`).

**Mesure réelle (ClaudeBox, 2026-09-30 11:23, portée `global`, `07b5ab4`)** :
121 équipements inclus, 94 publiés, 27 ignorés ; requête AJAX totale 10,7 s ;
démon traité de 11:23:12 à 11:23:23 ; succès, écouteurs réalignés (227),
registres HA inchangés. **CC-32 n'est donc pas reproduit sur le parc actuel**
— la mesure reste sous les deux délais (15 s PHP, 20 s JS).

Le risque est **latent** : le plugin vise une publication sur le Market, où des
parcs plus grands sont attendus ; le modèle de durée
(t ≈ N évalués × (max(0,1 ; 10/N total) + ~0,017 s)) place le dépassement du
délai de 15 s aux alentours de 125-130 équipements évalués. Au-delà, le
comportement d'aiohttp à la déconnexion du client HTTP (le relais PHP abandonne
au délai, mais le handler du démon continue-t-il ?) n'est pas vérifié.

Cette issue avait déjà été déclarée comme préexistante et non traitée dans
l'AC11 de la Story 19.5 (« Si le relais abandonne sur délai (CC-32), les
écouteurs ne sont pas réalignés avant le sync suivant : déclaré »).

## 2. Décision

Pas de décision d'Alexandre à ce stade — proposition de correct-course
documentaire, à valider avant tout développement. Aucun code n'est modifié par
ce tour (session documentation seulement).

## 3. Impact

- **Epic 19** (`_bmad-output/planning-artifacts/epics-projection-engine.md`) :
  ajout de la Story 19.6, qui ferme CC-32. N'ouvre aucun nouveau FR/NFR PRD, ne
  touche pas `evaluate_equipment()`.
- **Code concerné** : `resources/daemon/transport/http_server.py` (branches
  Publier l.3881/3957/4002, Supprimer l.3724/3744), `core/ajax/jeedom2ha.ajax.php`
  (relais l.764, budget 15 s), `desktop/js/jeedom2ha.js` (délai client l.343).
- **UI Impact** : possible selon l'option retenue — `desktop/` et `core/ajax/`
  pourraient changer, donc `ready-for-UX-validation` avant `done` si c'est le
  cas.
- Pas d'impact PRD/architecture/UX documents existants au-delà de l'ajout de la
  story dans l'epic.

## 4. Approche retenue

**Direct Adjustment** — ajout d'une story (19.6) à l'epic 19 existant. Scope
**minor à moderate** selon l'option choisie (voir story, section « Options »).

Trois options sont comparées dans la story, avec préférence de ClaudeBox pour
l'option (a) : budgets du relais et du client proportionnels au nombre
d'équipements, lissage inchangé — changement minimal, aucune UX nouvelle.

## 5. Changement d'artefact

**Epic 19** (`_bmad-output/planning-artifacts/epics-projection-engine.md`) :
ajout de la Story 19.6 (F) à la liste des stories, et CC-32 aux points visés.

## 6. Handoff

- **Scope : Minor à Moderate** (selon l'option retenue en dev-story ; l'option
  (a) recommandée reste minor). Implémentation directe par le dev, sous
  réserve de la décision d'Alex sur l'option si elle change l'UX au-delà du
  délai d'attente technique.
- Story détaillée :
  `_bmad-output/implementation-artifacts/19-6-duree-action-ha-bornee-cc32.md`.
- `sprint-status.yaml` : `19-6-duree-action-ha-bornee-cc32: ready-for-dev`.

## 7. Complétion

- Issue traitée : CC-32 (durée des actions HA non bornée pour les grands parcs).
- Scope : Minor à Moderate (ajout de story dans l'epic existant, option de mise
  en œuvre à trancher en dev-story ou par Alex si elle a un effet UX).
- Artefacts modifiés : `epics-projection-engine.md`, story 19.6 (nouvelle),
  `sprint-status.yaml`.
- Routé vers : équipe de dev (create-story → dev-story → code-review, puis
  `ready-for-UX-validation` si `desktop/`/`core/ajax/` changent).
