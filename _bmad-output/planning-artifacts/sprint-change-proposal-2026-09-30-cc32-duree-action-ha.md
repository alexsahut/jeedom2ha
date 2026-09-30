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

**GO d'Alexandre le 2026-09-30 à 11:20** (« ok GO »), sur la proposition de
ClaudeBox de trier puis traiter CC-32 jusqu'au bout. **Option (b′) retenue**
par ClaudeBox (lissage borné par une échéance donnée au démon, voir §4), après
l'abandon de l'option (a) : aucune UX nouvelle ; seul le message du cas de
vrai dépassement change, et il passe par la validation UX d'Alex avant
`done`.
L'option (c) (asynchrone) reste hors périmètre : elle changerait l'UX et
reviendrait à Alex.

## 3. Impact

- **Epic 19** (`_bmad-output/planning-artifacts/epics-projection-engine.md`) :
  ajout de la Story 19.6, qui ferme CC-32. N'ouvre aucun nouveau FR/NFR PRD, ne
  touche pas `evaluate_equipment()`.
- **Code concerné** : `resources/daemon/transport/http_server.py` (branches
  Publier l.3881/3957/4002, Supprimer l.3724/3744), `core/ajax/jeedom2ha.ajax.php`
  (relais l.764, budget 15 s), `desktop/js/jeedom2ha.js` (délai client l.343).
- **UI Impact** : oui — `desktop/js/` et `core/ajax/` changent (option (b′)),
  donc `ready-for-UX-validation` avant `done`.
- Pas d'impact PRD/architecture/UX documents existants au-delà de l'ajout de la
  story dans l'epic.

## 4. Approche retenue

**Direct Adjustment** — ajout d'une story (19.6) à l'epic 19 existant. Scope
**moderate** : option (b′) (voir story, section « Options »).

Trois options sont comparées dans la story. L'option (a) (budgets du relais et
du client proportionnels au nombre d'équipements) a été **abandonnée** après
quatre tours de revue Codex (PR #188) qui ont chacun rouvert un nouveau trou
dans la lecture externe de N. **Option (b′) retenue** par ClaudeBox : un
lissage borné par une échéance donnée au démon — budget fixe côté
relais/client, `deadline_s` transmis au démon, qui comprime son propre
lissage à partir du travail qu'il mesure lui-même. Aucune UX nouvelle,
décision prise dans le cadre du GO d'Alex du 30/09 (pas de nouveau retour à
Alex).

## 5. Changement d'artefact

**Epic 19** (`_bmad-output/planning-artifacts/epics-projection-engine.md`) :
ajout de la Story 19.6 (F) à la liste des stories, et CC-32 aux points visés.

## 6. Handoff

- **Scope : Minor à Moderate** — option (b′) retenue (lissage borné par une
  échéance donnée au démon), touche `http_server.py` en plus du relais/client.
  Implémentation directe par le dev ; l'option (c), seule à changer l'UX,
  reste hors périmètre et reviendrait à Alex si nécessaire.
- Story détaillée :
  `_bmad-output/implementation-artifacts/19-6-duree-action-ha-bornee-cc32.md`.
- `sprint-status.yaml` : `19-6-duree-action-ha-bornee-cc32: ready-for-dev`.

## 7. Complétion

- Issue traitée : CC-32 (durée des actions HA non bornée pour les grands parcs).
- Scope : Moderate (ajout de story dans l'epic existant, option (b′) retenue ;
  l'option (c), seule à changer l'UX, reviendrait à Alex).
- Artefacts modifiés : `epics-projection-engine.md`, story 19.6 (nouvelle),
  `sprint-status.yaml`.
- Routé vers : équipe de dev (create-story → dev-story → code-review, puis
  `ready-for-UX-validation`, `desktop/` et `core/ajax/` changeant).
