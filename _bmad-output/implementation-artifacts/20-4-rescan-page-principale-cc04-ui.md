# Story 20.4 : Rescan depuis la page principale (CC-04, volet UI)

Status: review

## Story

En tant qu'utilisateur du plugin,
je veux lancer un rescan depuis la page principale,
afin de relire la topologie Jeedom et de synchroniser Home Assistant sans passer
par la configuration.

**Parcours : complet.** Story d'interface : gate 20-0, déploiement standard,
preuve terrain, puis `ready-for-UX-validation` avant `done`.

## Contexte et périmètre

- 20-4 dépend de 20-1 `done`. Elle ferme le rescan du volet UI de CC-04.
- Le rescan actuel est `scanTopology` : topologie complète, `POST /action/sync`,
  puis réalignement des écouteurs d'état (`core/ajax/jeedom2ha.ajax.php:592-605`).
- Le sync relit une fois les overrides de type et les overrides de publication
  (`resources/daemon/transport/http_server.py:1797-1802`). Ainsi, les overrides
  posés par 20-2 mais encore non appliqués le seront au prochain rescan.
- 20-2 est décidée (2026-10-05) et développée à part : cette story ne touche pas à
  la sémantique du forçage. Son seul contrat est d'appliquer les overrides persistés.
  20-2 ajoute un bouton « Appliquer » par équipement ; le rescan reste l'action
  globale : il applique en une fois les overrides en attente de tous les équipements.
- Le rescan est une écriture : il peut publier, dépublier et nettoyer la
  disponibilité (`resources/daemon/transport/http_server.py:1846-1869`,
  `:1892-2020`). Il n'est ni « Republier » ni « Supprimer puis recréer ».
- **Défaut existant, révélé par le cadrage : le sync n'a aucun verrou.** Seules les
  actions « Publier » et « Supprimer » prennent `action_lock` et répondent 409 quand il
  est pris (`http_server.py:3739-3761`, verrou créé `:4340`) ; `_do_handle_action_sync`
  (`:1706`) n'en prend aucun. Un rescan peut donc s'entrelacer, à chaque `await`, avec
  un « Publier », un autre rescan, ou le sync du démarrage ou d'un déploiement, qui
  modifient tous les publications et le cache. 20-4 rend le rescan accessible à côté de
  « Republier » : elle corrige ce défaut (AC8).
- `scanTopology` renvoie un succès AJAX dès que le démon répond, même si la réponse
  porte `status: "error"`, et réaligne alors les écouteurs (`core/ajax/jeedom2ha.ajax.php:594-605`).
  Le bouton de la configuration ne teste que `state` (`plugin_info/configuration.php:323-341`).

## Acceptance Criteria

**AC1 — Entrée principale et garde-fou** *(décision R1)*

**Given** la page principale du plugin
**When** elle affiche les actions Home Assistant
**Then** elle affiche une action « Rescanner la topologie Jeedom » dans le bloc
« Actions Home Assistant », sans modifier la surface par pièce
**And** l'action réutilise le garde-fou bridge/MQTT existant : elle est inactive
et explique la cause si le daemon est arrêté ou MQTT déconnecté.

**AC2 — Confirmation explicite** *(décision R2)*

**Given** le bridge et MQTT sont disponibles
**When** l'utilisateur clique sur « Rescanner la topologie Jeedom »
**Then** une confirmation explique qu'un sync complet peut publier ou retirer des
entités Home Assistant et applique les overrides persistés
**And** aucun appel n'est effectué si l'utilisateur annule.

**AC3 — Exécution sans calcul local**

**Given** la confirmation validée
**When** le rescan part
**Then** l'interface désactive le rescan et les autres actions Home Assistant, et
affiche « Rescan en cours… » ; aucun rafraîchissement (par exemple « Rafraîchir » de la
synthèse, qui rappelle le garde-fou `applyHAGating`, `desktop/js/jeedom2ha.js:136-154`
et `:466`) ne les réactive tant que le rescan est en cours
**And** elle appelle le contrat existant `scanTopology`, sans reconstruire la
topologie, décider la publication, ni calculer les compteurs côté interface.

**AC4 — Retour lisible et santé rafraîchie**

**Given** un rescan en cours
**When** `scanTopology` répond avec succès, c'est-à-dire `state === 'ok'`,
`result.status === 'ok'` et un résultat d'opération `succes`
**Then** l'interface affiche un succès à partir du résumé backend retourné, puis
rafraîchit le bandeau santé, dont « Dernière synchro » et « Dernière opération »
**And** elle réactive le bouton.
**When** `scanTopology` échoue, expire, ou répond avec un statut ou un résultat
d'opération autre que le succès (`partiel`, `echec`)
**Then** elle affiche l'erreur ou le résultat partiel retourné, ou une erreur de
communication, réactive le bouton et ne déclare pas de succès
**And** le résultat d'opération vient de la réponse même du sync : aujourd'hui, le
démon le calcule (`succes`, `partiel`, `echec`) mais ne le range que dans l'état de
santé global (`resources/daemon/transport/http_server.py:2097-2120`), et sa réponse
ne porte que `status: "ok"` et le résumé (`:2122-2128`). Le démon ajoute donc à cette
réponse le résultat et le message de l'opération qu'il vient de terminer, en champ
additif ; le relais et l'interface décident sur ce champ, jamais sur le bandeau santé
relu après coup, qu'une autre opération a pu réécrire. Si le champ manque (démon plus
ancien), l'interface affiche « résultat inconnu, relire Dernière opération » et ne
déclare ni succès ni échec
**And** côté relais, les écouteurs d'état sont réalignés dès que le sync est allé au
bout (`status: "ok"`), quel que soit le résultat d'opération, car un sync `partiel`
a publié des entités ; jamais sur une erreur ni une expiration. Le bouton de la
configuration applique la même définition du succès
**And** en cas d'expiration, le message invite à relire « Dernière synchro » plutôt
qu'à relancer aussitôt ; le sync est protégé contre l'annulation à la déconnexion du
relais, comme « Publier » (`asyncio.shield`, `http_server.py:4252-4262`).

**AC5 — Configuration conservée, rôle distinct** *(décision R3)*

**Given** la page de configuration
**When** l'utilisateur modifie les filtres puis choisit l'action existante
« Appliquer et Rescanner » (`#bt_applyAndRescan`, `plugin_info/configuration.php:150`)
**Then** elle sauvegarde d'abord les filtres, puis utilise le même `scanTopology` ;
son libellé devient « Appliquer les filtres et rescanner » (R3)
**And** le rescan de la page principale ne sauvegarde aucun champ de configuration.

**AC6 — Contrat complet du rescan**

**Given** le daemon reçoit `POST /action/sync`
**When** il traite la topologie Jeedom complète
**Then** il normalise et mémorise le snapshot, évalue l'éligibilité, les mappings,
les overrides et les décisions, puis applique les publications ou retraits requis
**And** il persiste le cache de publication et retourne le résumé backend
**And** après la réponse, Jeedom réaligne les écouteurs d'état sur le périmètre
publié ; un échec de réalignement est journalisé mais ne renverse pas le succès du
sync (`core/ajax/jeedom2ha.ajax.php:599-605`).

**AC7 — Preuve d'une écriture déclarée**

**Given** le code fusionné sur `main` et déployé par le chemin standard
**When** le gate 20-0 est exécuté
**Then** son parcours déclare le rescan comme écriture et le simule : aucune
écriture n'est transmise à Jeedom, au daemon ni à Home Assistant. Aujourd'hui,
`scanTopology` est un effet de bord bloqué qui fait échouer le gate
(`tests/e2e/gate/lib/policy.mjs:61-62`, `:241-243`) : le simuler demande d'étendre la
politique du gate, une réponse de sync simulée, l'auto-test local et une relecture
ClaudeBox (règle de 20-0 sur l'extension des écritures simulées)
**And** le clic réel ultérieur du rescan est prouvé séparément avec relevés avant
et après ; la parité attendue est identique, sauf écart explicitement expliqué.

**AC8 — Un seul sync ou une seule action à la fois (défaut existant)**

**Given** un sync ou une action « Publier » / « Supprimer » en cours
**When** un rescan est demandé
**Then** le démon le refuse avec un 409 et un message lisible, que l'interface affiche
(« une opération est déjà en cours ») ; inversement, une action demandée pendant un
sync est refusée de la même façon
**And** les syncs du démarrage du démon et du déploiement attendent la fin de
l'opération en cours, avec un délai borné, au lieu d'échouer aussitôt. L'attente et
le sync doivent tenir ensemble dans le délai de l'appelant (15 s au démarrage,
`core/class/jeedom2ha.class.php:302` ; 20 s au déploiement, `scripts/deploy-to-box.sh:324` ;
un sync dure environ 2 s) : l'attente est donc d'au plus 7 s. À expiration, le démon
répond 409 avec le même message lisible. Au déploiement, ce 409 compte comme un échec
de l'étape 4c, comme tout sync en échec aujourd'hui ; le risque est faible, le démon
vient de redémarrer, et le cas réel attendu est l'inverse : le sync du déploiement
attend la fin du sync du démarrage au lieu de s'entrelacer avec lui. Les tests
couvrent les deux sens, l'attente et son expiration.
**And** les trois appelants envoient aujourd'hui le même `POST /action/sync`
(`core/ajax/jeedom2ha.ajax.php:594`, `core/class/jeedom2ha.class.php:301-303`,
`scripts/deploy-to-box.sh:321-325`) : le rescan y ajoute un mode explicite (un champ
du corps ou un en-tête de la requête existante, documenté dans le Dev Agent Record)
qui demande le refus immédiat par 409 ; sans ce mode, le démon attend le verrou avec
le délai borné. Le démarrage et le déploiement restent donc inchangés, y compris un
script de déploiement plus ancien. Si le mode passe par un en-tête, `callDaemon` doit
accepter des en-têtes en paramètre optionnel, sans changer ses autres appels.

## UI Impact

- **UI Impact : Oui.** La page principale reçoit une action visible et un retour
  d'exécution. Le statut final exige `ready-for-UX-validation` avant `done`.

## Tasks / Subtasks

- [x] **Task 0 — Relevés préalables, lecture seule (AC: 1, 4, 7)**
  - [ ] Relever le statut bridge, la dernière synchro, la dernière opération et la
    parité de référence, sans lancer de rescan ; vérifier qu'aucun override n'est en
    attente d'application (sinon la parité changera légitimement au clic réel).
  - [ ] Relever la version d'aiohttp installée sur la box (comportement à la
    déconnexion du client).
  - [ ] Durée d'un sync complet : environ 2 s au démarrage du 2026-10-05 (11:36:50 →
    11:36:52, journal du plugin), à confirmer ; le délai de 15 s de `scanTopology`
    (`core/ajax/jeedom2ha.ajax.php:594`) est donc confortable.
  - [ ] Le clic réel de la preuve est fait par ClaudeBox dans Chrome (règle 2 d'Alex
    du 2026-09-28 : preuves qui ne touchent que le plugin et HA), hors des fenêtres du
    gate ; aucun équipement ni nom n'est choisi dans cette story.
- [x] **Task 1 — Entrée et garde-fou (AC: 1, 2)**
  - [x] Ajouter l'action dans le bloc HA existant, avec le même attribut de garde.
  - [x] Réutiliser la modale de confirmation ; son texte déclare les effets du sync.
- [x] **Task 2 — Exécution et retour (AC: 3, 4, 6, 8)**
  - [x] Réutiliser `scanTopology` et son résumé backend. Aucun endpoint daemon neuf.
  - [x] Démon : le sync prend `action_lock` (409 immédiat pour le mode rescan,
    attente d'au plus 7 s sans ce mode, puis 409), est protégé par `asyncio.shield`,
    et sa réponse porte le résultat et le message de l'opération (AC4).
  - [x] Relais : succès défini par AC4 ; écouteurs réalignés dès que le sync est allé
    au bout (`status: "ok"`), jamais sur une erreur ou une expiration.
  - [x] Gérer attente, succès, échec, expiration, réactivation et
    `refreshBridgeStatus()` sans calcul local.
- [x] **Task 3 — Configuration (AC: 5)**
  - [x] Conserver la chaîne sauvegarde puis rescan ; renommer selon R3.
- [x] **Task 4 — Tests et gate (AC: 1-8)**
  - [x] Tester le garde-fou, annulation, appel unique, retour et erreurs.
  - [x] Étendre la politique du gate (`tests/e2e/gate/lib/policy.mjs`) pour simuler
    `scanTopology` déclaré, avec une réponse de sync simulée qui porte le résultat
    d'opération ; auto-test local ; relecture ClaudeBox ; puis le parcours.
  - [x] Tests Python du verrou (deux sens, attente bornée) et du `shield`.
- [ ] **Task 5 — Déploiement et preuve terrain (AC: 7)**
  - [ ] Déployer le SHA exact par le chemin standard, après CI et revue.
  - [ ] Relever avant/après, cliquer réellement une fois, consigner durée, résumé,
    statut et parité ; corriger tout écart avant la validation UX.

## Dev Notes

### Contrats réutilisés

- `plugin_info/configuration.php:287-353` : chaîne configuration sauvegardée puis
  `scanTopology`, bouton désactivé et retours succès/erreur ; l'action principale
  ne doit pas recopier la sauvegarde.
- `core/ajax/jeedom2ha.ajax.php:592-605` : `getFullTopology()`, appel
  `/action/sync` avec timeout 15 s et réalignement des écouteurs après la réponse.
- `resources/daemon/transport/http_server.py:1706-2128` : contrat du sync,
  publications/retraits, résumé, dernière opération et date de fin.
- `core/class/jeedom2ha.class.php:397-451` : réalignement sûr des écouteurs ; sur
  réponse invalide ou erreur, les écouteurs existants sont conservés.
- `desktop/php/jeedom2ha.php:71-132` : bandeau santé (l. 71) et bloc HA ;
  `desktop/js/jeedom2ha.js:18-154` : statut et garde-fou bridge/MQTT ;
  `:306-420` : confirmation, attente et rafraîchissement des actions HA.

### Interdits

- Aucun recalcul de topologie, de décision, de publication ou de compteurs en JS.
- Aucun nouveau point d'entrée daemon et aucun changement de la sémantique 20-2 ; le
  seul changement du démon est le verrou, la protection du sync et le résultat
  d'opération ajouté à sa réponse (AC8, AC4).
- Ne pas transformer le rescan en « Republier » ou « Supprimer puis recréer » :
  ces actions appellent `executeHaAction` (`desktop/js/jeedom2ha.js:332-420`) ;
  le rescan appelle `scanTopology` et refait tout le pipeline.
- Déploiement standard seulement ; jamais `--cleanup-discovery` ni
  `--stop-daemon-cleanup`. Jamais `git add -A`, `--admin` ni force-push.

### Fichiers probablement touchés

`desktop/php/jeedom2ha.php`, `desktop/js/jeedom2ha.js`,
`plugin_info/configuration.php` (libellé et définition du succès),
`core/ajax/jeedom2ha.ajax.php` (mode rescan, écouteurs après succès seulement),
`resources/daemon/transport/http_server.py` (verrou, `shield` et résultat d'opération
du sync), tests et politique du gate 20-0. `scripts/deploy-to-box.sh` et le démarrage
du démon ne changent pas (AC8).

## Décisions d'Alex (2026-10-05, 20:26)

Réponse « R1A, R2A, R3A », sur recommandation de ClaudeBox.

- **R1 — Bouton dans le bloc « Actions Home Assistant »**, à côté de « Republier », avec le même garde-fou bridge/MQTT (AC1). Options écartées : bloc « Gestion » ; surface par pièce.
- **R2 — Confirmation à chaque clic**, qui dit qu'un sync complet peut publier ou retirer des entités et applique les overrides en attente (AC2). Options écartées : aucune confirmation ; confirmation mémorisable.
- **R3 — Le bouton « Appliquer et Rescanner » de la configuration est gardé et renommé « Appliquer les filtres et rescanner »** (AC5). Options écartées : le supprimer ; le garder tel quel.

## Journal des décisions

- 2026-10-05 — Brouillon `create-story` de clawcode (`19c0afe`), retouché par ClaudeBox puis relu par une relecture indépendante (AC8 verrou du sync, AC4 définition du succès et écouteurs, AC3 bouton pendant le rescan, AC7 gate à étendre).
- 2026-10-05 — Questions R1 à R3 posées à Alex, avec recommandation R1A, R2A, R3A.
- 2026-10-05, 20:26 — **Décision d'Alex : « R1A, R2A, R3A ».** Story passée `ready-for-dev`.
- 2026-10-05 — Revue Codex de la PR #208 : le résultat d'opération est ajouté à la
  réponse du sync (AC4), et le rescan porte un mode explicite qui seul reçoit le 409
  (AC8). Relecture indépendante du correctif : attente d'au plus 7 s puis 409, effet
  sur le déploiement dit (AC8) ; écouteurs réalignés aussi après un sync `partiel`,
  champ absent d'un démon plus ancien (AC4) ; réponse simulée du gate (Task 4).

## Définition de done

- Décisions R1 à R3 d'Alex (2026-10-05, 20:26) appliquées.
- Tous les AC ont des tests nommés ou un contrôle de gate ; aucun calcul local
  n'est ajouté pour le résultat du sync.
- CI verte, revue indépendante et File List complète.
- Déploiement standard du SHA exact ; relevés avant/après consignés sans écart
  inexpliqué ; clic réel unique de rescan, durée et résumé consignés.
- Le gate 20-0 passe avec rescan simulé et déclaré comme écriture, sans transfert.
- Passage par `ready-for-UX-validation`, puis validation UX avant `done`.

## References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md`, Epic 20]
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-10-01-etape-4-interface.md`]
- [Source: `core/ajax/jeedom2ha.ajax.php:592-605`]
- [Source: `resources/daemon/transport/http_server.py:1706-2128`]
- [Source: `desktop/php/jeedom2ha.php:71-132`]
- [Source: `desktop/js/jeedom2ha.js:18-154`, `:306-420`]
- [Source: `_bmad-output/implementation-artifacts/20-0-gate-preuve-ux-outille.md`]
- [Source: `_bmad-output/implementation-artifacts/20-1-surface-unique-piece-equipement-commande.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- 2026-10-06 — R6 code-review : `confirmHaPublishAction` rattache désormais
  l'annulation du rescan à `onEscape` et à `hidden.bs.modal`, avec une annulation
  idempotente. Après confirmation, la fermeture de la modale ne libère pas la
  réservation : seule la fin de la requête propriétaire le fait. Les confirmations
  « Republier » et « Supprimer puis recréer » ne reçoivent aucun nouveau gestionnaire.
  Les tests Node couvrent croix, Échap, Annuler, fermeture après confirmation et les
  autres appelants. Aucun déploiement, rescan réel ou gate contre la box.

- 2026-10-06 — R5 dev-story : corrections des deux constats Codex PR #209.
  `99a3315` cible le bouton primaire exact « Rescanner » du parcours gate.
  `4748847` réserve le rescan dès l'ouverture de sa confirmation, interdit une
  seconde modale/requête et donne à sa requête propriétaire seule le droit de
  libérer le garde-fou. Les retours `echec` sont rouges (`danger`), les
  `partiel` restent en avertissement ; tests Node ajoutés pour le garde, les
  résultats et le succès de la configuration. `74e9fc0` couvre l'AC8 : action
  pendant sync, attente service, expiration 409 et réponse sync `echec` avec
  résultat/message. `d2e7a34` vérifie aussi que la déconnexion du client laisse
  le sync protégé finir puis libérer le verrou. Aucun déploiement, rescan réel
  ou gate contre la box.

- 2026-10-05 — R3 dev-story : revue corrigée et tests locaux verts. AC8 distingue
  l'appelant rescan par l'en-tête `X-Jeedom2ha-Sync-Mode: rescan`; le rescan reçoit
  409 immédiatement, les autres syncs attendent au plus 7 s. Gate local étendu :
  `scanTopology` est simulé seulement avec `declaredRescan: true` et seulement en POST.
- 2026-10-05 — R2 dev-story : Tasks 0 à 3 implémentées, HEAD `70b105e`.
- 2026-10-05 — R dev-story : décisions R1A/R2A/R3A appliquées.

- 2026-10-05 — Brouillon create-story non interactif ; confirmations par défaut :
  création seule, statut `draft`, aucune modification de `sprint-status.yaml`.
- 2026-10-05 — Relu par ClaudeBox puis par une relecture indépendante : sync sans
  verrou (AC8, défaut existant), définition du succès et écouteurs (AC4), protection
  contre l'annulation, bouton qui ne doit pas se réactiver pendant le rescan (AC3), gate
  à étendre pour simuler `scanTopology` (AC7), libellé de R3, auteur du clic réel.

### File List

- `_bmad-output/implementation-artifacts/20-4-rescan-page-principale-cc04-ui.md`
- `resources/daemon/transport/http_server.py`
- `core/ajax/jeedom2ha.ajax.php`
- `core/class/jeedom2ha.class.php`
- `desktop/php/jeedom2ha.php`
- `desktop/js/jeedom2ha.js`
- `plugin_info/configuration.php`
- `tests/unit/test_http_server.py`
- `tests/unit/test_story_20_0_gate_policy.node.test.js`
- `tests/e2e/gate/lib/policy.mjs`
- `tests/e2e/gate/lib/interceptor.mjs`
- `tests/e2e/gate/interceptor-selftest.mjs`
- `tests/e2e/gate/run-gate.mjs`
- `tests/e2e/gate/parcours/rescan-page-principale.mjs`
- `tests/unit/test_story_20_4_rescan_ui.node.test.js`
