# Story 19.6: Durée des actions HA bornée pour les grands parcs (CC-32)

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As un utilisateur,
I want que les boutons « Publier » et « Supprimer », sur toutes les portées
(équipement, pièce, global), n'échouent pas côté UI à cause de la taille du
parc, jusqu'à une taille de parc supportée et déclarée,
so that une republication ou une suppression sur un grand parc HA reste
fiable, avec un message juste si elle prend plus longtemps que d'habitude.

**Parcours complet.** GO d'Alexandre le 2026-09-30 à 11:20 (« ok GO » pour
traiter CC-32 jusqu'au bout). Option (a) retenue : `core/ajax/` et
`desktop/js/` sont modifiés (voir « UI Impact »).

## Contexte mesuré (relevé à `07b5ab4`)

- `_action_delay = max(0.1, 10.0 / max(1, len(eq_ids)))`
  (`resources/daemon/transport/http_server.py:3881` pour Publier, `:3724` pour
  Supprimer, Décision 8 de `epic-5-lifecycle-matrix.md:439`). Ce délai est
  dormi à chaque équipement **évalué** (Publier : `:3957` et `:4002` ;
  Supprimer : `:3744`).
- Relais PHP : `jeedom2ha::callDaemon('/action/execute', $params, 'POST', 15)`
  (`core/ajax/jeedom2ha.ajax.php:764`). Si `$result === null` (délai dépassé),
  une `Exception` est levée **avant** l'appel à `jeedom2ha_realign_after_action`
  (réalignement des écouteurs, AC11 de la Story 19.5) — le réalignement est
  alors sauté, même si le démon aboutit côté MQTT.
- Client JS : délai de 20 s (`desktop/js/jeedom2ha.js:343`).
- **Modèle de durée** : t ≈ N évalués × (max(0,1 ; 10/N total) + ~0,017 s de
  travail par équipement). Le délai de 15 s est atteint vers 125-130
  équipements évalués.
- **Mesure réelle** (ClaudeBox, 2026-09-30 11:23, portée `global`, `07b5ab4`) :
  121 équipements inclus, 94 publiés, 27 ignorés ; requête AJAX totale 10,7 s ;
  démon traité de 11:23:12 à 11:23:23 ; succès, écouteurs réalignés (227),
  registres HA inchangés. **CC-32 n'est pas reproduit sur le parc actuel** —
  la mesure reste sous les deux délais.
- Comportement d'aiohttp à la déconnexion du client HTTP (le relais PHP
  abandonne à 15 s, le handler du démon continue-t-il de tourner ?) **non
  vérifié** — `pyproject.toml` ne pin pas de version d'aiohttp. Version
  installée sur la box (relevé ClaudeBox, 30/09) : **3.13.3**
  (`/usr/local/lib/python3.9/dist-packages`).
- Bornes de la pile web de la box (relevé ClaudeBox, 30/09, lecture seule) :
  Apache `Timeout 300` (`/etc/apache2/apache2.conf:92`), PHP
  `max_execution_time = 600` (`/etc/php/7.4/apache2/php.ini:388`). Le plafond
  du budget doit rester sous le `Timeout` d'Apache.
- L'AC11 de la Story 19.5 déclarait déjà ce cas comme préexistant, non traité :
  « Si le relais abandonne sur délai (CC-32), les écouteurs ne sont pas
  réalignés avant le sync suivant : déclaré. »
- Cette story ne modifie ni la Décision 8 (lissage post-redémarrage) ni le
  chemin de republication après reboot — seul le chemin déclenché par un clic
  utilisateur (« Publier »/« Supprimer ») est concerné.

## Options comparées

**(a) Budgets du relais et du client proportionnels au nombre d'équipements,
lissage inchangé.** [Préférence de ClaudeBox]
- Le relais PHP calcule un budget `callDaemon` fonction de `len(eq_ids)`
  (ex. `max(15, N * (0.1 + marge))`), au lieu du 15 s fixe. Le client JS suit
  le même calcul pour son propre timeout (au lieu du 20 s fixe).
- Coût : faible — un calcul de budget en PHP et en JS, pas de changement du
  démon.
- Risque : faible — aucun changement de comportement pour les petits parcs (le
  budget calculé reste ≥ 15 s/20 s) ; pour les grands parcs, l'utilisateur
  attend plus longtemps sans message d'erreur trompeur.
- Effet visible pour l'utilisateur : aucun changement d'UX pour les cas
  actuels ; sur un grand parc, l'attente est simplement plus longue, sans
  changement de flux (toujours un clic bloquant, un seul retour).
- **Changement minimal, aucune UX nouvelle** — c'est l'option recommandée.

**(b) Lissage borné en durée totale pour une action utilisateur.**
- `_action_delay` devient fonction d'un budget total fixe divisé par
  `len(eq_ids)`, sans plancher de 0,1 s (ou avec un plancher plus bas).
- Coût : moyen — touche la Décision 8 (le même code sert le lissage
  post-redémarrage), donc il faut distinguer les deux appelants (redémarrage
  vs clic) ou accepter de changer aussi le comportement post-redémarrage.
- Risque : moyen — un lissage trop court sur un grand parc pourrait
  redevenir une rafale de publications discovery, ce que la Décision 8 visait
  justement à éviter (raison du plancher).
- Effet visible : la durée totale d'un clic reste bornée, mais le lissage
  par équipement diminue quand le parc grandit — pas de nouvelle UX, mais un
  changement de comportement du lissage qui mériterait un test de
  non-régression dédié.

**(c) Action asynchrone suivie par polling.**
- Le clic déclenche l'action en tâche de fond côté démon, répond
  immédiatement, et l'UI interroge périodiquement un endpoint de statut.
- Coût : élevé — nouveau contrat d'API (démarrage, statut, résultat final),
  nouvel état UI (barre de progression ou équivalent), nouveaux tests bout en
  bout.
- Risque : élevé — change fondamentalement le flux (un clic qui ne bloque
  plus la fin de l'action), avec des cas limites nouveaux (fermeture de
  l'onglet pendant l'action, actions concurrentes).
- Effet visible : **UX nouvelle** — le bouton ne resterait plus bloquant
  jusqu'à la fin ; nécessiterait un retour visuel de progression.
- **Décision à Alex si cette option est envisagée** : elle change l'UX au-delà
  du simple délai d'attente technique.

**Recommandation : option (a).** Elle ferme CC-32 sans toucher à la Décision 8
ni introduire de nouvelle UX, avec le risque et le coût les plus faibles.

**Limite assumée (revue Codex P1, PR #188).** Toute option synchrone est bornée
par la pile web de la box (`Timeout 300` d'Apache) : un plafond de budget est
donc inévitable, et un parc assez grand le dépassera. L'option (a) ne promet
pas « jamais » : elle fixe une **taille de parc supportée**, calculée par le
modèle (AC7) à partir du plafond, et la déclare. Au-delà, le message juste
d'AC5 s'applique. Seule l'option (c) lèverait cette limite ; elle changerait
l'UX et reviendrait à Alex si les parcs du Market l'exigent.
L'option (c) n'est pas recommandée pour cette story ; si le volume du Market
la rend nécessaire plus tard, elle mérite sa propre story avec validation UX
préalable.

## Acceptance Criteria

**AC1 — Budget du relais proportionnel au nombre d'équipements (Publier et
Supprimer, 3 portées)**

**Given** un appel `/action/execute` pour `intention = publier` ou
`intention = supprimer`, sur une portée `equipement`, `piece` ou `global`
**When** le relais PHP (`executeHaAction`, `jeedom2ha.ajax.php`) construit
l'appel `callDaemon`
**Then** le budget transmis à `callDaemon` croît avec N, le nombre
d'équipements développés par le relais pour cette portée (au lieu du 15 s
fixe), avec un plancher de 15 s pour ne rien changer aux petits parcs et un
plafond explicite de 240 s au plus (sous le `Timeout 300` d'Apache)
**And** ce plafond définit la taille de parc supportée (nombre d'équipements
traités par le démon dont la durée prévue par le modèle d'AC7, marge comprise,
tient dans le plafond) ; cette taille est calculée, figée par un test et
déclarée dans la story et dans la documentation utilisateur
**And** N vient de la même expansion que la Story 19.5
(`_jeedom2ha_expand_portee_to_eq_ids`), étendue à `supprimer` ; c'est une
borne supérieure du nombre d'équipements que le démon traite (il développe la
portée sur sa propre topologie)
**And** la formule couvre le pire cas du démon : N × max(0,1 ; 10/N) de
lissage, plus le travail par équipement, avec une marge explicite
**And** N et le budget calculé sont journalisés (`info`) à chaque action, pour
la preuve terrain
**And** un test par portée fige la formule du budget.

**AC2 — Budget du client HA proportionnel, aligné sur le relais**

**Given** le même appel `executeHaAction` côté client (`desktop/js/jeedom2ha.js:343`)
**When** l'utilisateur clique sur « Publier » ou « Supprimer »
**Then** le timeout AJAX du client est calculé à partir du même N, lu dans la
synthèse pour la portée cliquée (`counts.total` du global ou de la pièce ; 1
pour un équipement)
**And** il reste strictement supérieur au budget du relais augmenté de la
lecture des valeurs au clic (Story 19.5), du réalignement des écouteurs
(3 s) et d'une marge, pour ne jamais couper la requête avant que le relais
ait pu répondre
**And** un test JS fige la formule et vérifie `client > relais + 3 s + marge`
pour au moins un cas au-delà du plancher.

**AC3 — Aucune régression pour les petites portées**

**Given** une portée `equipement` ou `piece` de petite taille (comme
aujourd'hui, quelques équipements)
**When** « Publier » ou « Supprimer » s'exécute
**Then** le budget calculé reste égal aux valeurs actuelles (15 s PHP,
20 s JS) — aucun changement de comportement observable
**And** un test fige ce cas de non-régression.

**AC4 — Le réalignement des écouteurs a toujours lieu après un « Publier »
qui aboutit**

**Given** un « Publier » dont le démon répond dans le budget calculé (AC1)
**When** le relais reçoit la réponse
**Then** `jeedom2ha_realign_after_action` (AC11 de la Story 19.5) est appelé
comme aujourd'hui, sans changement de son propre budget (3 s, une tentative)
**And** un test couvre un grand parc simulé (budget étendu) où le réalignement
a bien lieu, alors qu'il aurait été sauté avec l'ancien budget fixe de 15 s.

**AC5 — Message juste en cas de vrai dépassement**

**Given** un appel qui dépasse malgré tout le budget calculé (panne réseau,
démon bloqué)
**When** le relais reçoit `null` de `callDaemon`
**Then** le message d'erreur affiché à l'utilisateur ne prétend plus que « le
démon ne répond pas » de façon indifférenciée : il indique que l'action peut
se poursuivre côté démon au-delà du délai d'attente de l'UI (formulation
précise à trancher en dev-story, cohérente avec le vocabulaire existant du
plugin)
**And** un test fige le nouveau message pour ce cas précis, distinct du
message d'un démon réellement injoignable (à distinguer si possible, sinon
déclarer la limitation).

**AC6 — Comportement d'aiohttp à la déconnexion du client, vérifié et testé**

**Given** une requête HTTP du relais PHP vers le démon qui expire côté client
avant que le démon ait terminé (déconnexion TCP par le client PHP)
**When** le handler aiohttp du démon est en cours d'exécution
**Then** le comportement réel (le handler continue-t-il jusqu'au bout, ou
est-il annulé ?) est déterminé par un test d'intégration reproduisant une
déconnexion client pendant un handler long, avec la version d'aiohttp
effectivement installée (`pyproject.toml` ne pin pas de version — noter la
version testée dans le rapport de dev-story)
**And** le résultat (poursuite ou annulation) est documenté dans les Dev
Notes et piloté par ce constat, pas supposé.

**AC7 — Modèle de durée testé en unitaire**

**Given** le modèle t ≈ N évalués × (max(0,1 ; 10/N total) + ~0,017 s)
**When** un test unitaire calcule la durée prévue pour plusieurs valeurs de N
(dont la mesure du 30/09 : N total = 292, N évalués = 94, environ 11 s côté
démon et 10,7 s côté AJAX) et pour un N évalué au-delà du seuil actuel de
15 s (autour de 125-130)
**Then** le test vérifie que le budget calculé par AC1 couvre bien la durée
prévue par le modèle, avec une marge explicite
**And** le test échoue si la marge devient insuffisante (garde-fou pour un
futur changement de `_action_delay`).

## UI Impact

- **UI Impact : Oui** — `desktop/js/jeedom2ha.js` (délai du client) et
  `core/ajax/jeedom2ha.ajax.php` (budget du relais, message de vrai
  dépassement). L'option (a) retenue ne change ni l'apparence ni le flux du
  bouton (aucune barre de progression, aucun nouvel état) ; seul le message du
  cas de vrai dépassement (AC5) change. Passage par `ready-for-UX-validation`
  avant `done` (`docs/bmad-parcours-rapide-complet.md`), avec preuve par clic
  réel.
- Si l'option (c) était retenue en cours de dev-story (changement de flux),
  **halte obligatoire et retour à Alex** avant implémentation : hors périmètre
  de ce cadrage.

## Impact sur la production et retour arrière

- **Aucun changement de comportement pour les parcs actuels** (AC3) : le
  budget calculé reste identique aux valeurs actuelles tant que
  `len(eq_ids)` reste sous le seuil qui aurait de toute façon tenu dans 15 s.
- **Risque principal : un budget mal calculé qui allonge l'attente sans
  limite.** Couvert par AC7 (modèle testé) et par le plafond de 240 s au
  plus (AC1), qui fixe la taille de parc supportée. Au-delà, AC5.
- **Retour arrière** : redéploiement du SHA précédent. Aucune migration,
  aucun état persistant modifié — seuls des délais de requête HTTP et un
  message d'erreur changent.
- **Preuve terrain limitée** : le parc actuel (121 équipements inclus en
  portée globale) ne permet pas de reproduire un dépassement réel (il faudrait
  ~130 équipements évalués). La preuve terrain démontre l'absence de
  régression sur le parc actuel ; le cas de dépassement lui-même est couvert
  uniquement par les tests unitaires (AC7) et d'intégration (AC6), déclaré
  comme limite de la preuve terrain.

## Preuve terrain

**Limite déclarée** : le parc actuel ne dépasse pas le seuil de 130
équipements évalués ; cette preuve ne peut donc pas reproduire un vrai
dépassement de délai. Elle démontre uniquement l'absence de régression.

1. Inventaire avant (registre HA, topics, nombre d'écouteurs).
2. « Republier » en portée `global` : mesurer la durée totale de la requête
   AJAX et la durée de traitement démon (comme la mesure du 30/09 :
   121 inclus, 94 publiés, 10,7 s).
3. « Suppr. » puis « Republier » sur une pièce (comme la preuve de la Story
   19.5) : mesurer les durées.
4. Critères :
   - 0 ERROR dans les journaux du démon et du relais ;
   - registres HA inchangés en nombre et en `entity_id` ;
   - écouteurs réalignés après chaque « Publier » qui aboutit (AC4) ;
   - durées mesurées cohérentes avec le modèle (AC7), avec le nouveau budget
     calculé (AC1) toujours ≥ à la durée mesurée ;
   - la ligne de journal du budget (AC1) montre N et le budget pour la portée
     globale (attendu : N de l'ordre de 292 à ce jour) et pour la pièce, et le délai du
     client relevé dans le navigateur lui est supérieur (AC2).

**Gate d'inventaire obligatoire (convention repo, `sprint-status.yaml`)** :
inventaire avant/après déploiement (0 erreur), en plus de la preuve par clic
réel.

## Invariants concernés

I2, I4, I6, I7 (aucune logique de décision modifiée — seuls des budgets de
requête HTTP et un message d'erreur changent).

## Points visés

- **CC-32** — visé par cette story (AC1 à AC7 et preuve terrain), sous réserve
  de la limite déclarée sur la reproduction terrain d'un vrai dépassement.

## Tasks / Subtasks

<!-- Story terrain : daemon / MQTT / publication / bouton Publier-Supprimer / box réelle → Task 0 Pre-flight terrain injectée. -->

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY)
  - [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run` (CI verte du SHA
    exigée), **avant** tout déploiement réel.
  - [ ] Identifier en lecture seule le nombre d'équipements actuellement
    inclus en portée `global` (mesure du 30/09 : 121 inclus, 94 publiés) pour
    calibrer les tests du modèle de durée (AC7).
  - [ ] **Interdiction explicite (DANGER) :** ne jamais invoquer
    `--cleanup-discovery` ni `--stop-daemon-cleanup`
    (`scripts/deploy-to-box.sh:97,99`) pendant cette recherche ni pendant la
    vérification post-correction — ces flags republient des messages MQTT
    retained **vides** sur les topics discovery, effaçant les entités déjà
    publiées et rendant impossible de distinguer un effet **causé par cette
    story** d'un effet causé par le script lui-même. Déploiement standard
    uniquement.

- [ ] Task 1 — Relais PHP et client JS : budgets proportionnels (AC1, AC2, AC3, AC5)
  - [ ] Fonction pure de calcul de budget (PHP), prenant `len(eq_ids)` en
    entrée, avec le plancher à 15 s (AC3) et le plafond de 240 s au plus
    (AC1) ; taille de parc supportée calculée et déclarée.
  - [ ] Appliquer ce budget à l'appel `callDaemon('/action/execute', …)`
    (`jeedom2ha.ajax.php:764`) pour `intention = publier` et
    `intention = supprimer`.
  - [ ] Message d'erreur distinct en cas de vrai dépassement (AC5), formulé
    en dev-story.
  - [ ] Même formule côté JS (`desktop/js/jeedom2ha.js:343`), strictement
    supérieure au budget PHP (AC2).
  - [ ] Tests PHP (un cas par portée, non-régression petite portée) et JS
    (formule, comparaison client > relais).

- [ ] Task 2 — Vérification du comportement aiohttp à la déconnexion (AC6)
  - [ ] Test d'intégration démon : handler long, déconnexion client simulée
    avant la fin, constat documenté (poursuite ou annulation) avec la version
    d'aiohttp effectivement installée.
  - [ ] Documenter le résultat dans les Dev Notes, sans le supposer au
    préalable.

- [ ] Task 3 — Écouteurs et modèle de durée (AC4, AC7)
  - [ ] Test simulant un grand parc (budget étendu) où le réalignement des
    écouteurs a bien lieu (AC4), contrastant avec l'ancien comportement à
    budget fixe.
  - [ ] Test unitaire du modèle de durée (AC7) : calcul pour plusieurs N,
    dont N=121 (mesure du 30/09) et un N au-delà de 125-130 ; vérifie que le
    budget calculé (AC1) couvre la durée prévue avec une marge explicite.

- [ ] Task 4 — Preuve terrain et gate d'inventaire
  - [ ] Dérouler la section « Preuve terrain » ; documenter la preuve par
    clic réel (« Republier » global, « Suppr. » puis « Republier » sur une
    pièce) et la limite déclarée (pas de reproduction d'un vrai dépassement)
    avant `ready-for-UX-validation` → `done`.

## Dev Notes

### Contexte pipeline

- Cette story ne touche ni `evaluate_equipment()` ni la décision de
  publication : elle ajoute des budgets de requête HTTP proportionnels et un
  message d'erreur plus juste, sans changer le lissage `_action_delay`
  lui-même (Décision 8 inchangée, option (a) retenue).
- L'AC11 de la Story 19.5 avait déjà déclaré ce cas comme préexistant, non
  traité : cette story le ferme.

### Dev Agent Guardrails

- Ne pas toucher à `_action_delay` ni à la Décision 8 (lissage
  post-redémarrage) — seuls les budgets `callDaemon`/timeout JS changent
  (option (a)).
- Ne pas introduire de flux asynchrone/polling (option (c)) sans validation
  explicite d'Alex — hors périmètre de cette story.
- Le budget calculé doit avoir un plancher (≥ 15 s PHP / ≥ 20 s JS, AC3) et un
  plafond explicite de 240 s au plus côté relais (sous le `Timeout 300`
  d'Apache), pour ne jamais devenir illimité. Ce plafond borne la taille de
  parc supportée : la calculer et la déclarer, sans promettre « jamais ».
- Ne pas modifier le budget du réalignement des écouteurs de la Story 19.5
  (3 s, une tentative).

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh`.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.

### Pointeurs (relevés à `07b5ab4`)

- `resources/daemon/transport/http_server.py` : `_action_delay` Publier l.3881,
  `sleep` l.3957 et l.4002 ; `_action_delay` Supprimer l.3724, `sleep` l.3744.
- `core/ajax/jeedom2ha.ajax.php` : `callDaemon('/action/execute', …, 15)`
  l.764, journal ERROR l.766 et exception l.767 si `null`, appel
  `jeedom2ha_realign_after_action` l.772 ; expansion de la portée
  `_jeedom2ha_expand_portee_to_eq_ids` l.338 (Story 19.5, publier seulement).
- `desktop/js/jeedom2ha_scope_summary.js` : `counts.total` du global et des
  pièces (l.164, l.174), source de N côté client.
- `desktop/js/jeedom2ha.js` : timeout AJAX l.343.
- `_bmad-output/planning-artifacts/epic-5-lifecycle-matrix.md` : Décision 8
  (formule du lissage) à partir de l.439.
- `pyproject.toml` : `aiohttp` sans version épinglée (l.11) — vérifier la
  version installée sur la box au moment du test AC6.
- `_bmad-output/implementation-artifacts/19-5-publier-etat-initial-valeur-courante-cc29.md`
  AC11 : déclaration préexistante de CC-32.

### Project Structure Notes

- `core/ajax/jeedom2ha.ajax.php` [À MODIFIER], `desktop/js/jeedom2ha.js`
  [À MODIFIER], tests PHP/JS [NOUVEAU], test d'intégration démon (AC6)
  [NOUVEAU], test unitaire du modèle de durée (AC7) [NOUVEAU].
- `resources/daemon/transport/http_server.py` : pas de modification prévue
  par l'option (a) — à confirmer en dev-story si un point d'ancrage
  supplémentaire est nécessaire pour AC4/AC6.

### References

- [Source: _bmad-output/planning-artifacts/epics-projection-engine.md#Epic-19] —
  Story 19.6 ajoutée par correct-course, CC-32.
- [Source: _bmad-output/planning-artifacts/sprint-change-proposal-2026-09-30-cc32-duree-action-ha.md] —
  issue, options comparées, recommandation.
- [Source: _bmad-output/implementation-artifacts/19-5-publier-etat-initial-valeur-courante-cc29.md] —
  AC11, déclaration préexistante de CC-32 et budget de réalignement (3 s, une
  tentative) laissé inchangé par cette story.

## Dev Agent Record

### Agent Model Used

- (à remplir en dev-story)

### Debug Log References

- (à remplir en dev-story)

### Completion Notes List

- **correct-course + create-story** — 2026-09-30 — statut résultant :
  `ready-for-dev`. Créée par `clawcode` en session détachée, documentation
  seulement, à partir d'une mesure réelle de ClaudeBox (30/09, 11:23, portée
  `global`, 121 inclus / 94 publiés, 10,7 s, succès).
- **Relecture ClaudeBox (30/09)** — décision rendue explicite (GO d'Alex du
  30/09 à 11:20, option (a) retenue), UI Impact tranché (Oui), N défini par
  l'expansion de la portée du relais (étendue à `supprimer`), plafond du
  budget sous le `Timeout 300` d'Apache, budget journalisé pour la preuve,
  délai du client calculé sur `counts.total` de la synthèse et couvrant la
  lecture au clic et le réalignement, chiffres du modèle corrigés (N total 292,
  N évalués 94), version d'aiohttp de la box relevée (3.13.3), pointeurs
  corrigés. Revue Codex (PR #188) intégrée : taille de parc supportée
  déclarée au lieu de « jamais » (P1), marge du client couvrant le
  traitement après le démon (P1), N total et N temporisé distingués (P2),
  décision documentée avant `ready-for-dev` (P2).

### File List

- (à remplir en dev-story)

### Change Log

- 2026-09-30 — `correct-course` (CC-32) + `create-story` — statut
  `ready-for-dev`.
- 2026-09-30 — relecture ClaudeBox (décision, UI Impact, N, plafond, délai du
  client, modèle, pointeurs) et revue Codex PR #188 intégrée.
