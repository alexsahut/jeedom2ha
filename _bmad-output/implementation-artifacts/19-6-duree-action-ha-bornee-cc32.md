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
traiter CC-32 jusqu'au bout). Option (a) abandonnée après quatre tours de
revue Codex (PR #188) ; **option (b′) retenue** par ClaudeBox (décision prise
dans le cadre du GO d'Alex, sans nouveau retour à Alex — l'UX ne change pas) :
un lissage borné par une échéance donnée au démon, plutôt qu'un budget deviné
depuis l'extérieur. `core/ajax/`, `desktop/js/` et
`resources/daemon/transport/http_server.py` sont modifiés (voir « UI
Impact »).

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
- `published_scope` (le contrat lu par l'option (a) pour deviner N) n'est
  **pas affecté atomiquement avec `topology`** : `request.app["topology"] =
  snapshot` (`http_server.py:1733`) précède de plusieurs dizaines de lignes
  `request.app["published_scope"] = _apply_pending_scope_flags(...)`
  (`http_server.py:2053`). Une lecture externe entre ces deux affectations, ou
  après un sync partiellement traité, peut donc renvoyer un N désynchronisé
  de la topologie que le démon parcourt réellement. C'est le trou de fond
  qui a motivé l'abandon de l'option (a) (voir « Options »).

## Options comparées

**(a) Budgets du relais et du client proportionnels au nombre d'équipements,
lissage inchangé.** [Abandonnée — voir « Pourquoi (a) est abandonnée »]
- Le relais PHP devine un budget `callDaemon` fonction de N, lu dans le
  contrat `published_scope` du démon, avant l'action.
- Coût : faible en apparence — mais quatre tours de revue Codex (PR #188,
  commits `c123d33`, `786751d`, `ec50615`, puis la relecture qui a mené à ce
  commit) ont chacun trouvé un nouveau trou dans cette lecture externe de N,
  sans jamais la fermer complètement (voir ci-dessous).
- **Abandonnée.**

**Pourquoi (a) est abandonnée.** Elle devine N depuis l'extérieur au lieu de
laisser le démon, qui connaît sa propre charge, borner lui-même son lissage.
Quatre tours de revue Codex ont chacun ouvert un nouveau trou en corrigeant le
précédent :
1. N désynchronisé de la topologie que le démon parcourt réellement :
   `published_scope` n'est pas affecté atomiquement avec `topology`
   (`http_server.py:1733` puis `:2053`, deux affectations séparées).
2. Travail par équipement variable, non couvert par un N unique : équipements
   secondaires, nombre de `node_id` dépubliés par équipement (ligne 143 de
   l'ancienne AC1, jamais totalement close).
3. N lu dans la page (synthèse affichée) potentiellement périmé par rapport à
   la topologie du démon.
4. Lecture des valeurs au clic sans échéance propre, qui allongeait le pire
   cas sans borne claire.
Chaque correction déplaçait le problème plutôt que de le fermer : deviner un
budget externe pour un travail interne au démon est structurellement fragile.

**(b′) Lissage borné par une échéance donnée au démon.** [Retenue]
- Le relais transmet au démon une **échéance** (`deadline_s`) dérivée d'un
  budget **fixe** (pas fonction de N). Le démon comprime son propre lissage
  pour tenir cette échéance, à partir du travail qu'il mesure lui-même en
  temps réel (durée moyenne par équipement observée depuis le début de
  l'action × équipements restants) — il n'a pas besoin qu'on lui dise N à
  l'avance, ni que ce N soit exact.
- Coût : moyen — touche `http_server.py` (lecture de `deadline_s`, calcul du
  délai restant par équipement dans les deux branches Publier/Supprimer), en
  plus du relais et du client. Ne touche pas la Décision 8 : l'appelant
  redémarrage ne transmet jamais `deadline_s`, donc son comportement est
  inchangé par construction (pas de branchement à distinguer, juste un
  paramètre optionnel).
- Risque : faible à moyen — le lissage ne descend jamais en dessous de 0 (pas
  de rafale plus dense que « tout de suite »), et seulement quand l'échéance
  approche réellement ; sur les petits parcs, l'échéance est loin et le délai
  d'origine (10/N) reste intact.
- Effet visible : aucun changement d'UX — toujours un clic bloquant, un seul
  retour ; l'attente reste bornée par un budget fixe, indépendamment de N,
  puisque c'est le démon qui adapte son propre rythme.
- **Ferme le trou de fond (source unique de vérité : le démon mesure son
  propre travail) plutôt que de le contourner.**

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

**(c) Action asynchrone suivie par polling.** [Hors périmètre]
- Le clic déclenche l'action en tâche de fond côté démon, répond
  immédiatement, et l'UI interroge périodiquement un endpoint de statut.
- Effet visible : **UX nouvelle** — le bouton ne resterait plus bloquant
  jusqu'à la fin ; nécessiterait un retour visuel de progression.
- **Décision à Alex si cette option est envisagée** : elle change l'UX
  au-delà du simple délai d'attente technique. Reste hors périmètre de cette
  story.

**Recommandation : option (b′).** Elle ferme CC-32 à la racine (le démon
adapte son propre lissage à une échéance donnée, sans deviner N depuis
l'extérieur), sans toucher à la Décision 8 (l'appelant redémarrage ne
transmet jamais `deadline_s`) ni introduire de nouvelle UX. Décision prise par
ClaudeBox, dans le cadre du GO d'Alex du 30/09 à 11:20 (l'UX ne change pas,
donc pas de nouveau retour à Alex nécessaire).

**Limite assumée (revue Codex P1, PR #188, maintenue sous (b′)).** Toute
option synchrone est bornée par la pile web de la box (`Timeout 300`
d'Apache) : un budget fixe est donc inévitable, et un parc dont le travail
pur dépasse ce budget le dépassera malgré la compression du lissage (AC5).
L'option (b′) ne promet pas « jamais » : elle fixe une **taille de parc
supportée**, mesurée par un test de charge (AC7) et déclarée en nombre de
publications MQTT (candidats et `node_id`), pas en N d'équipements — cela
répond au P2 de Codex sur le travail par équipement variable. Au-delà, le
message juste d'AC5 s'applique. Seule l'option (c) lèverait cette limite ;
elle changerait l'UX et reviendrait à Alex si les parcs du Market
l'exigent. L'option (c) n'est pas recommandée pour cette story ; si le
volume du Market la rend nécessaire plus tard, elle mérite sa propre story
avec validation UX préalable.

## Acceptance Criteria

**AC1 — Budget fixe du relais, échéance transmise au démon (Publier et
Supprimer, 3 portées)**

**Given** un appel `/action/execute` pour `intention = publier` ou
`intention = supprimer`, sur une portée `equipement`, `piece` ou `global`
**When** le relais PHP (`executeHaAction`, `jeedom2ha.ajax.php`) construit
l'appel `callDaemon`
**Then** le budget transmis à `callDaemon` est **fixe** : `R = 60 s`
(constante nommée), quelle que soit la taille de la portée — plus aucune
lecture de `published_scope` pour dimensionner ce budget, et donc plus aucune
dépendance à un N deviné depuis l'extérieur
**And** le relais transmet au démon, dans le corps de `/action/execute`, un
paramètre `deadline_s = R - reserve_s` (`reserve_s = 5 s`, constante nommée,
couvrant la sérialisation de la réponse et le trajet retour)
**And** ce budget reste sous le `Timeout 300` d'Apache par construction (60 s
≪ 300 s), sans calcul dépendant de N
**And** `R` et `reserve_s` sont journalisées (`info`) à chaque action, pour la
preuve terrain
**And** un test par portée (publier, supprimer) fige `R` et `deadline_s`.

**AC1bis — Le démon comprime son lissage pour tenir l'échéance transmise**

**Given** une action (`publier` ou `supprimer`) qui porte `deadline_s`
**When** le démon traite les équipements de la portée un par un
**Then** le délai entre deux équipements devient
`min(_action_delay, max(0, (deadline_s - écoulé - reserve_travail) /
équipements_restants))`, où `_action_delay` est la formule actuelle (Décision
8) et `écoulé` le temps déjà passé depuis le début de l'action
**And** `reserve_travail` est estimée en continu à partir du travail
réellement mesuré depuis le début de l'action (durée moyenne par équipement
observée × équipements restants) — une mesure, pas un coefficient fixe
(répond au P2 de Codex sur le travail par équipement variable : secondaires,
`node_id` de dépublication)
**And** sans `deadline_s` (appelant redémarrage, ou tout autre appelant qui
ne le transmet pas), le comportement actuel de `_action_delay` est
**inchangé** — la Décision 8 n'est pas touchée
**And** le démon **n'interrompt jamais** une action en cours : si le travail
pur dépasse à lui seul `deadline_s`, il va au bout sans pause et répond en
retard (cas de l'AC5)
**And** un test couvre la compression du lissage à l'approche de l'échéance,
pour publier et pour supprimer, et un test couvre le comportement inchangé
sans `deadline_s`.

**AC2 — Délai fixe du client, indépendant de N**

**Given** le même appel `executeHaAction` côté client (`desktop/js/jeedom2ha.js:343`)
**When** l'utilisateur clique sur « Publier » ou « Supprimer »
**Then** le timeout AJAX du client est un délai **fixe**, indépendant de N :
`R` + échéance de la lecture des valeurs au clic (voir ci-dessous, 10 s au
plus) + réalignement des écouteurs (3 s) + marge de réalignement (3 s), et
reste sous le `Timeout 300` d'Apache
**And** la lecture des valeurs au clic de la Story 19.5
(`_jeedom2ha_collect_click_values`, `jeedom2ha.ajax.php:382`) reçoit une
**échéance explicite** (10 s au plus, horloge injectable pour le test) :
passé ce délai, elle s'arrête, transmet les valeurs déjà lues et journalise
un WARNING avec le nombre de commandes lues. Les commandes non lues ne
reçoivent aucun état au clic, comme une valeur absente (AC7 de la Story 19.5).
Un test couvre l'échéance atteinte (revue Codex P1, PR #188, `786751d`,
inchangé par (b′))
**And** ce délai ne dépend d'aucun N — ni celui de la page, ni celui du
démon : c'est `R` (constante fixe, AC1) qui borne réellement la durée du
relais et rend la main (succès ou message d'AC5)
**And** un test JS fige ce délai fixe à partir des mêmes constantes que le
relais (`R`, échéance de lecture au clic, réalignement, marge).

**AC3 — Non-régression détectée en quelques secondes, pas au bout de `R`**

**Given** un appel `/action/execute` (n'importe quelle portée)
**When** le relais PHP s'apprête à appeler `callDaemon`
**Then** il fait d'abord un `GET /system/status` (3 s, une tentative) : un
démon injoignable est ainsi signalé en quelques secondes, avec le message
actuel, sans attendre `R` (60 s)
**And** écart déclaré : un démon qui répond au statut mais se bloque ensuite
n'est signalé qu'au bout de `R` (couvert par AC5)
**And** pour un petit parc, le comportement observable reste inchangé
(succès rapide, même flux qu'aujourd'hui) ; un test fige ce cas.

**AC4 — Le réalignement des écouteurs a toujours lieu après un « Publier »
qui aboutit**

**Given** un « Publier » dont le démon répond dans le budget fixe `R` (AC1)
**When** le relais reçoit la réponse
**Then** `jeedom2ha_realign_after_action` (AC11 de la Story 19.5) est appelé
comme aujourd'hui, sans changement de son propre budget (3 s, une tentative)
**And** un test couvre un grand parc simulé où le lissage du démon s'est
comprimé pour tenir `deadline_s` (AC1 du démon) et où le réalignement a bien
lieu, alors qu'il aurait été sauté avec l'ancien lissage non borné.

**AC5 — Message juste en cas de vrai dépassement**

**Given** un appel qui dépasse malgré tout le budget fixe `R` (panne réseau,
démon bloqué, ou travail pur du démon supérieur à `deadline_s` — le démon ne
s'interrompt jamais en cours d'action, voir Dev Notes)
**When** le relais reçoit `null` de `callDaemon`
**Then** le message d'erreur distingue deux cas, à partir du `GET
/system/status` d'AC3 : démon injoignable (message actuel), ou démon
joignable mais qui n'a pas répondu dans `R` — dans ce second cas le message
indique que l'action peut se poursuivre côté démon au-delà du délai
d'attente de l'UI, et le relais **ne réaligne pas** les écouteurs (formulation
précise à trancher en dev-story, cohérente avec le vocabulaire existant)
**And** un test fige les deux messages distincts.

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

**AC7 — Taille de parc supportée mesurée, en publications MQTT**

**Given** le démon comprime son lissage pour tenir `deadline_s`, mais ne peut
pas comprimer le travail pur (publication MQTT elle-même)
**When** un test de charge du démon simule un parc avec un faux MQTT à
latence réaliste et des équipements multi-candidats (secondaires, plusieurs
`node_id` par équipement)
**Then** le test mesure la taille de parc supportée en **nombre de
publications MQTT** (candidats et `node_id` traités), pas en nombre
d'équipements — cela répond au P2 de Codex sur le travail par équipement
variable
**And** cette taille est figée par le test avec une marge explicite, et
déclarée dans la story et dans la documentation utilisateur
**And** le test rejoue la mesure du 30/09 (N total = 292, N évalués = 94,
environ 11 s) et vérifie qu'elle tient bien sous `R` (60 s)
**And** un test simule un grand parc (par exemple 1 000 équipements
multi-capteurs) et vérifie que la réponse arrive avant `R`.

## UI Impact

- **UI Impact : Oui** — `desktop/js/jeedom2ha.js` (délai fixe du client) et
  `core/ajax/jeedom2ha.ajax.php` (budget fixe du relais, transmission de
  `deadline_s`, message de vrai dépassement). L'option (b′) retenue ne
  change ni l'apparence ni le flux du bouton (aucune barre de progression,
  aucun nouvel état) ; seul le message du cas de vrai dépassement (AC5)
  change. Passage par `ready-for-UX-validation` avant `done`
  (`docs/bmad-parcours-rapide-complet.md`), avec preuve par clic réel.
- Si l'option (c) était retenue en cours de dev-story (changement de flux),
  **halte obligatoire et retour à Alex** avant implémentation : hors périmètre
  de ce cadrage.

## Impact sur la production et retour arrière

- **Aucun changement de comportement pour les parcs actuels** (AC3) : le
  parc actuel (292 équipements, 94 évalués, ~11 s) tient très largement sous
  `R` (60 s), lissage non comprimé.
- **Risque principal : un lissage trop comprimé qui redevient une rafale.**
  Couvert par AC1bis (la compression ne descend jamais sous 0, et seulement
  quand l'échéance approche réellement) et par le test de non-régression sur
  petite portée.
- **Retour arrière** : redéploiement du SHA précédent. Aucune migration,
  aucun état persistant modifié — seuls des délais de requête HTTP, un
  paramètre `deadline_s` optionnel et un message d'erreur changent.
- **Preuve terrain limitée** : le parc actuel ne permet pas de reproduire un
  vrai dépassement de `R` (60 s), ni une compression significative du
  lissage. La preuve terrain démontre l'absence de régression sur le parc
  actuel ; la compression et le cas de dépassement sont couverts uniquement
  par les tests unitaires (AC1bis, AC7) et d'intégration (AC6), déclaré comme
  limite de la preuve terrain.

## Preuve terrain

**Limite déclarée** : le parc actuel (292 équipements, 94 évalués) tient très
largement sous `R` (60 s) ; cette preuve ne peut donc reproduire ni un vrai
dépassement de délai, ni une compression significative du lissage du démon.
Elle démontre uniquement l'absence de régression.

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
   - durées mesurées cohérentes avec le modèle des Dev Notes, largement sous
     `R` (AC1) ;
   - la ligne de journal du budget (AC1) montre `R`, `deadline_s` et la durée
     de traitement pour la portée globale et pour la pièce, et le délai fixe
     du client relevé dans le navigateur lui est supérieur (AC2).

**Gate d'inventaire obligatoire (convention repo, `sprint-status.yaml`)** :
inventaire avant/après déploiement (0 erreur), en plus de la preuve par clic
réel.

## Invariants concernés

I2, I4, I6, I7 (aucune logique de décision modifiée — seuls des budgets de
requête HTTP, un lissage borné par échéance et un message d'erreur
changent).

## Points visés

- **CC-32** — visé par cette story (AC1, AC1bis, AC2 à AC7 et preuve
  terrain), sous réserve de la limite déclarée sur la reproduction terrain
  d'un vrai dépassement.

## Tasks / Subtasks

<!-- Story terrain : daemon / MQTT / publication / bouton Publier-Supprimer / box réelle → Task 0 Pre-flight terrain injectée. -->

- [ ] Task 0 — Pre-flight terrain (DEV/TEST ONLY)
  - [ ] Dry-run : `./scripts/deploy-to-box.sh --dry-run` (CI verte du SHA
    exigée), **avant** tout déploiement réel.
  - [ ] Identifier en lecture seule le nombre d'équipements actuellement
    inclus en portée `global` (mesure du 30/09 : 121 inclus, 94 publiés) pour
    calibrer les tests de charge (AC7).
  - [ ] **Interdiction explicite (DANGER) :** ne jamais invoquer
    `--cleanup-discovery` ni `--stop-daemon-cleanup`
    (`scripts/deploy-to-box.sh:97,99`) pendant cette recherche ni pendant la
    vérification post-correction — ces flags republient des messages MQTT
    retained **vides** sur les topics discovery, effaçant les entités déjà
    publiées et rendant impossible de distinguer un effet **causé par cette
    story** d'un effet causé par le script lui-même. Déploiement standard
    uniquement.

- [ ] Task 1 — Relais PHP, client JS et démon : budget fixe + échéance (AC1,
  AC1bis, AC2, AC3, AC5)
  - [ ] Constantes `R = 60 s` et `reserve_s = 5 s` (PHP), budget fixe pour
    `callDaemon`, `deadline_s = R - reserve_s` transmis au démon.
  - [ ] Appliquer ce budget à l'appel `callDaemon('/action/execute', …)`
    (`jeedom2ha.ajax.php:764`) pour `intention = publier` et
    `intention = supprimer`, avec `deadline_s` dans le corps de la requête.
  - [ ] Pré-vérification `GET /system/status` (3 s, une tentative) avant
    l'action (AC3), pour distinguer démon injoignable / vrai dépassement.
  - [ ] Démon : lecture de `deadline_s` sur `/action/execute`, calcul du
    délai comprimé par équipement (AC1bis) dans les deux branches Publier
    (`:3881`) et Supprimer (`:3724`), sans changer le comportement sans
    `deadline_s`.
  - [ ] Message d'erreur distinct en cas de vrai dépassement (AC5), formulé
    en dev-story.
  - [ ] Délai fixe côté JS (`desktop/js/jeedom2ha.js:343`), indépendant de N
    (AC2).
  - [ ] Échéance explicite de la lecture des valeurs au clic (AC2), testée.
  - [ ] Tests PHP (un cas par portée, statut, non-régression petite
    portée), démon (compression AC1bis, non-régression sans `deadline_s`) et
    JS (délai fixe).

- [ ] Task 2 — Vérification du comportement aiohttp à la déconnexion (AC6)
  - [ ] Test d'intégration démon : handler long, déconnexion client simulée
    avant la fin, constat documenté (poursuite ou annulation) avec la version
    d'aiohttp effectivement installée.
  - [ ] Documenter le résultat dans les Dev Notes, sans le supposer au
    préalable.

- [ ] Task 3 — Écouteurs et test de charge (AC4, AC7)
  - [ ] Test simulant un grand parc où le lissage s'est comprimé (AC1bis) et
    où le réalignement des écouteurs a bien lieu (AC4), contrastant avec
    l'ancien comportement à budget fixe non borné.
  - [ ] Test de charge du démon (AC7), faux MQTT à latence réaliste,
    équipements multi-candidats ; rejoue le couple mesuré (292, 94, ~11 s) et
    un grand parc simulé (par exemple 1 000 équipements) ; déclare la taille
    de parc supportée en publications MQTT, avec une marge explicite.

- [ ] Task 4 — Preuve terrain et gate d'inventaire
  - [ ] Dérouler la section « Preuve terrain » ; documenter la preuve par
    clic réel (« Republier » global, « Suppr. » puis « Republier » sur une
    pièce) et la limite déclarée (pas de reproduction d'un vrai dépassement)
    avant `ready-for-UX-validation` → `done`.

## Dev Notes

### Contexte pipeline

- Cette story ne touche ni `evaluate_equipment()` ni la décision de
  publication : elle ajoute un budget fixe côté relais/client et une échéance
  transmise au démon, qui comprime son propre lissage `_action_delay` pour la
  tenir (Décision 8 inchangée pour l'appelant redémarrage, option (b′)
  retenue après abandon de l'option (a), quatre tours de revue Codex).
- L'AC11 de la Story 19.5 avait déjà déclaré ce cas comme préexistant, non
  traité : cette story le ferme.

### Dev Agent Guardrails

- La Décision 8 (lissage post-redémarrage) reste inchangée par construction :
  l'appelant redémarrage ne transmet jamais `deadline_s`.
- Ne pas introduire de flux asynchrone/polling (option (c)) sans validation
  explicite d'Alex — hors périmètre de cette story.
- Le démon **n'interrompt jamais** une action en cours pour tenir
  `deadline_s` : il comprime uniquement le délai *entre* deux équipements,
  jamais le travail lui-même (AC1bis).
- Le budget du relais (`R`) et la réserve (`reserve_s`) sont des constantes
  fixes, indépendantes de N — ne pas réintroduire de lecture de
  `published_scope`/`topology` pour dimensionner un budget (c'est le trou
  qui a fait abandonner l'option (a)).
- Ne pas modifier le budget du réalignement des écouteurs de la Story 19.5
  (3 s, une tentative).

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh`.
- Référence : `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`.

### Pointeurs (relevés à `07b5ab4`)

- `resources/daemon/transport/http_server.py` : `_action_delay` Publier l.3881,
  `sleep` l.3957 et l.4002 ; `_action_delay` Supprimer l.3724, `sleep` l.3744
  (points d'ancrage de la compression AC1bis).
- `core/ajax/jeedom2ha.ajax.php` : `callDaemon('/action/execute', …, 15)`
  l.764, journal ERROR l.766 et exception l.767 si `null`, appel
  `jeedom2ha_realign_after_action` l.772 ; expansion de la portée
  `_jeedom2ha_expand_portee_to_eq_ids` l.338 (Story 19.5, publier seulement).
- `resources/daemon/transport/http_server.py` : `request.app["topology"] =
  snapshot` l.1733 et `request.app["published_scope"] = …` l.2053 — deux
  affectations séparées, non atomiques : source du trou qui a fait abandonner
  l'option (a) (N désynchronisé de la topologie). `_resolve_eq_ids_for_portee`
  l.371 ; `GET /system/published_scope` l.3447 (n'est plus utilisé pour
  dimensionner un budget sous (b′)).
- `desktop/js/jeedom2ha.js` : timeout AJAX l.343.
- `_bmad-output/planning-artifacts/epic-5-lifecycle-matrix.md` : Décision 8
  (formule du lissage) à partir de l.439.
- `pyproject.toml` : `aiohttp` sans version épinglée (l.11) — vérifier la
  version installée sur la box au moment du test AC6.
- `_bmad-output/implementation-artifacts/19-5-publier-etat-initial-valeur-courante-cc29.md`
  AC11 : déclaration préexistante de CC-32.

### Project Structure Notes

- `core/ajax/jeedom2ha.ajax.php` [À MODIFIER], `desktop/js/jeedom2ha.js`
  [À MODIFIER], `resources/daemon/transport/http_server.py` [À MODIFIER —
  lecture de `deadline_s`, compression du lissage AC1bis], tests PHP/JS/démon
  [NOUVEAU], test d'intégration démon (AC6) [NOUVEAU], test de charge (AC7)
  [NOUVEAU].

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
  décision documentée avant `ready-for-dev` (P2). Second tour Codex (PR
  #188, `c123d33`) : N lu dans la topologie du démon (`published_scope`) et
  non dans l'inventaire Jeedom courant, repli sur le plafond (P1) ; délai du
  client fixe couvrant le pire cas du relais, indépendant de la page (P1).
  Troisième tour (`786751d`) : échéance explicite de la lecture au clic (P1) ;
  Task 3 alignée sur le couple (N total, N évalués) = (292, 94) (P2).
- **Conception (b′), décision ClaudeBox après 4 tours Codex** — 2026-09-30 —
  option (a) abandonnée : quatre tours de revue Codex (`c123d33`, `786751d`,
  `ec50615`, puis cette relecture) ont chacun rouvert un nouveau trou dans la
  lecture externe de N (désynchronisation `topology`/`published_scope`
  l.1733/2053, travail par équipement variable, N périmé côté page, lecture
  au clic sans échéance). Passage à l'option **(b′)** : budget fixe `R = 60 s`
  côté relais/client, échéance `deadline_s` transmise au démon, qui comprime
  son propre lissage à partir du travail qu'il mesure lui-même (AC1bis).
  Décision prise par ClaudeBox, dans le cadre du GO d'Alex du 30/09 à 11:20
  (UX inchangée, pas de nouveau retour à Alex). Taille de parc supportée
  redéclarée en publications MQTT (candidats et `node_id`), mesurée par un
  test de charge (AC7), plutôt qu'en N d'équipements. AC1 à AC7 réécrits,
  AC1bis ajouté, Tasks 1 et 3 réécrites, Dev Notes et pointeurs mis à jour.

### File List

- (à remplir en dev-story)

### Change Log

- 2026-09-30 — `correct-course` (CC-32) + `create-story` — statut
  `ready-for-dev`.
- 2026-09-30 — relecture ClaudeBox (décision, UI Impact, N, plafond, délai du
  client, modèle, pointeurs) et revue Codex PR #188 intégrée.
- 2026-09-30 — conception (b′), décision ClaudeBox après 4 tours Codex :
  lissage borné par une échéance donnée au démon, option (a) abandonnée.
