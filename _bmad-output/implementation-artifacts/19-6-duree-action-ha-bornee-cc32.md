# Story 19.6: Durée des actions HA bornée pour les grands parcs (CC-32)

Status: review

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
  budget **fixe** (pas fonction de N). Le démon **plafonne** le total de ses
  pauses de lissage (`P_max`, AC1bis) : la durée de l'action est alors
  bornée par son travail pur plus ce plafond, sans deviner N ni estimer le
  travail restant.
- Coût : moyen — touche `http_server.py` (lecture de `deadline_s`, calcul du
  plafond des pauses dans les deux branches Publier/Supprimer), en
  plus du relais et du client. Ne touche pas la Décision 8 : l'appelant
  redémarrage ne transmet jamais `deadline_s`, donc son comportement est
  inchangé par construction (pas de branchement à distinguer, juste un
  paramètre optionnel).
- Risque : faible à moyen — le lissage ne descend jamais en dessous de 0 (pas
  de rafale plus dense que « tout de suite »), et seulement quand les pauses
  cumulées atteindraient `P_max` (au-delà de 150 équipements évalués) ; sur
  les petits parcs, le délai d'origine (10/N) reste intact.
- Effet visible : aucun changement d'UX — toujours un clic bloquant, un seul
  retour ; l'attente reste bornée par un budget fixe, indépendamment de N,
  puisque c'est le démon qui adapte son propre rythme.
- **Ferme le trou de fond (le démon borne lui-même la seule part qu'il
  maîtrise, ses pauses) plutôt que de le contourner.**

**(c) Action asynchrone suivie par polling.** [Hors périmètre]
- Le clic déclenche l'action en tâche de fond côté démon, répond
  immédiatement, et l'UI interroge périodiquement un endpoint de statut.
- Effet visible : **UX nouvelle** — le bouton ne resterait plus bloquant
  jusqu'à la fin ; nécessiterait un retour visuel de progression.
- **Décision à Alex si cette option est envisagée** : elle change l'UX
  au-delà du simple délai d'attente technique. Reste hors périmètre de cette
  story.

**Recommandation : option (b′).** Dans l'enveloppe de taille supportée
(AC7), elle ferme CC-32 à la racine (le démon
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
supportée**, celle dont le travail pur tient dans `budget_travail`
(AC1bis), mesurée par un test de charge (AC7) et déclarée
comme une enveloppe conjointe en appels MQTT de l'action (tous chemins) et
en nombre d'équipements — cela répond au P2 de Codex sur le travail par
équipement variable. Au-delà, le
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
**And** à chaque action, le relais journalise (`info`) une ligne donnant
l'intention, la portée, `R`, `reserve_s`, `deadline_s` et la durée mesurée de
l'appel au démon ; le démon journalise sa durée de traitement et le total de
ses pauses. Un test fige le contenu de ces lignes, nécessaires à la preuve
terrain (revue Codex P2, `3dcdb54`)
**And** un test par portée (publier, supprimer) fige `R` et `deadline_s`.

**AC1bis — Le démon plafonne son lissage pour tenir l'échéance transmise**

**Given** une action (`publier` ou `supprimer`) qui porte `deadline_s`
**When** le démon traite les équipements de la portée un par un
**Then** le total des pauses de lissage de l'action est plafonné à
`plafond_pauses = min(P_max, deadline_s / 2)`, avec `P_max = 15 s`
(constante nommée) : la pause qui suit un équipement devient
`min(_action_delay, max(0, (plafond_pauses - pauses_faites) /
pauses_restantes))`, où `_action_delay` est la formule actuelle (Décision 8),
`pauses_faites` la durée réellement dormie jusque-là (mesurée, pas
nominale) et `pauses_restantes` le nombre de pauses encore à faire, **y
compris celle-ci** (toujours ≥ 1)
**And** aucune pause n'est faite après le dernier équipement traité : la
dernière itération ne divise jamais par zéro (revue Codex P2, `472c372`) ;
un test couvre explicitement la dernière itération, pour publier et pour
supprimer
**And** la garantie ne repose sur **aucune estimation** du travail restant :
la durée de l'action est au plus son travail pur plus `plafond_pauses`, au
retard de réveil des pauses près. Ce retard (`asyncio.sleep` qui rend la main
après la durée demandée, sur une boucle chargée) est couvert par une marge
nommée `marge_reveil` (1 s par exemple ; revue Codex P2, `dfc651e`) : la
réponse arrive avant `deadline_s` dès que le travail pur tient dans
`budget_travail = deadline_s - plafond_pauses - marge_reveil` (39 s avec ces
constantes) ; un test simule un sommeil qui rend la main en retard. C'est ce
travail pur que mesure la taille supportée d'AC7. Le précompte des appels
MQTT restants, essayé aux tours Codex 6 à 12, est **abandonné** : chaque tour
y trouvait un chemin non compté (secondaires, états au clic, dépublications
de repli, nettoyages différés, évaluation des ignorés, puis dépublications
immédiates de retypage, revue Codex P1, `ecce1dc`)
**And** pour une portée dont le lissage actuel totalise au plus `P_max`
(portée d'au plus 100 équipements, ou d'au plus 150 équipements évalués
au-delà), les pauses sont identiques à aujourd'hui, hormis la pause finale
supprimée ; un test le vérifie, dont la mesure du 30/09 (N total 292,
N évalués 94)
**And** sans `deadline_s` (appelant redémarrage, ou tout autre appelant qui
ne le transmet pas), le comportement actuel de `_action_delay` est
**inchangé** — la Décision 8 n'est pas touchée
**And** le démon **n'interrompt jamais** une action en cours : si le travail
pur dépasse à lui seul `budget_travail`, il va au bout et
répond en retard (cas de l'AC5)
**And** un test couvre le plafond atteint (total des pauses au plus
`plafond_pauses`), pour publier et pour supprimer, et un test couvre le
comportement inchangé sans `deadline_s`.

**AC2 — Délai fixe du client, indépendant de N**

**Given** le même appel `executeHaAction` côté client (`desktop/js/jeedom2ha.js:343`)
**When** l'utilisateur clique sur « Publier » ou « Supprimer »
**Then** le timeout AJAX du client est un délai **fixe**, indépendant de N :
le pire des deux chemins de la requête PHP, plus une marge. Chemin qui
aboutit : statut préalable (3 s, AC3) + échéance de la lecture des valeurs au
clic (voir ci-dessous, 10 s au plus) + `R` + réalignement des écouteurs
(3 s). Chemin en échec : statut préalable (3 s) + lecture au clic (10 s) +
`R` + second statut de diagnostic (3 s, AC5). Le délai reste sous le
`Timeout 300` d'Apache
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
relais (`R`, statuts, échéance de lecture au clic, réalignement, marge) et
vérifie qu'il dépasse strictement le pire des deux chemins.

**AC3 — Non-régression détectée en quelques secondes, pas au bout de `R`**

**Given** un appel `/action/execute` (n'importe quelle portée)
**When** le relais PHP traite le clic, **avant** la lecture des valeurs au
clic (`_jeedom2ha_collect_click_values`)
**Then** il fait d'abord un `GET /system/status` (3 s, une tentative) : un
démon injoignable est ainsi signalé en quelques secondes, avec le message
actuel, sans attendre `R` (60 s)
**And** l'ordre est imposé : statut, puis lecture au clic, puis `callDaemon`.
La sonde ne s'intercale jamais entre la lecture et l'action : un évènement
Jeedom reçu pendant la sonde serait antérieur à `fresh_since`
(`http_server.py:3573-3576`, `sync/state.py:245-248`) et la valeur lue au
clic, plus ancienne, l'écraserait dans HA (revue Codex P1, `2cd9428`). Un
test PHP vérifie cet ordre. La fenêtre résiduelle reste celle de l'AC8 de la
Story 19.5 (entre la lecture au clic et la réception de la requête par le
démon), bornée par la durée de la lecture (quelques millisecondes en temps
normal, 10 s au plus, AC2) : déclarée, non traitée
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
comprimé pour tenir `deadline_s` (AC1bis) et où le réalignement a bien
lieu, alors qu'il aurait été sauté avec l'ancien lissage non borné.
Résiduel déclaré (revue Codex P2, PR #189, 7e tour) : la création/suppression
des écouteurs en base (`core/class/jeedom2ha.class.php:419-440`) n'est pas
bornée par les 3 s de `GET /system/state_listeners` — voir Dev Notes.

**AC5 — Message juste en cas de vrai dépassement**

**Given** un appel qui dépasse malgré tout le budget fixe `R` (panne réseau,
démon bloqué, ou travail pur du démon supérieur à `budget_travail` (AC1bis)
— le démon ne
s'interrompt jamais en cours d'action, voir Dev Notes)
**When** le relais reçoit `null` de `callDaemon`
**Then** le message d'erreur distingue deux cas, à partir d'un **second**
`GET /system/status` fait après l'échec (3 s, une tentative ; celui d'AC3
précède l'action et ne dit rien de son issue) : démon injoignable (message
actuel), ou démon
joignable mais qui n'a pas répondu dans `R` — dans ce second cas le message
indique que l'action peut se poursuivre côté démon au-delà du délai
d'attente de l'UI, et le relais **ne réaligne pas** les écouteurs (formulation
précise à trancher en dev-story, cohérente avec le vocabulaire existant)
**And** un test fige les deux messages distincts.

**AC6 — Action protégée contre la déconnexion du client, testée**

**Given** une requête HTTP du relais PHP vers le démon qui expire côté client
avant que le démon ait terminé (déconnexion TCP par le client PHP)
**When** le handler aiohttp du démon est en cours d'exécution
**Then** l'exécution de l'action est **toujours protégée** : elle est portée
par une tâche unique protégée de l'annulation du handler (par exemple
`asyncio.shield`), **quel que soit** le comportement d'aiohttp à la
déconnexion — `pyproject.toml` n'épingle pas aiohttp, et une installation
Market ou une mise à jour peut changer ce comportement (revue Codex P1,
`71097f6`)
**And** un test d'intégration reproduit une déconnexion client pendant un
handler long, avec la version d'aiohttp installée (notée dans le rapport de
dev-story ; box : 3.13.3), et vérifie qu'une action dont le client s'est
déconnecté publie bien tous ses équipements, conformément à AC1bis et à AC5
(revue Codex P1, `472c372`). L'état partiel n'est pas un résultat acceptable
**And** le comportement brut du handler observé par ce test (poursuite ou
annulation) est documenté dans les Dev Notes, pour information : il ne
conditionne plus la protection.

**AC8 — Une seule action HA à la fois**

**Given** une action `publier` ou `supprimer` encore en cours dans le démon,
par exemple une action qui a survécu au délai du relais (AC5, AC6)
**When** une nouvelle requête `/action/execute` arrive, quelle que soit sa
portée ou son intention
**Then** le démon la **refuse immédiatement**, avec un statut explicite (par
exemple HTTP 409) et un message « une action Home Assistant est déjà en
cours » ; il ne lance jamais deux actions concurrentes sur `publications`,
`mappings` et les files de dépublication (revue Codex P1, `5570532`)
**And** le relais transmet ce message à l'interface tel quel, sans le
confondre avec un démon injoignable ni avec un dépassement
**And** le verrou est libéré dans tous les cas (succès, exception, action
protégée terminée après déconnexion) ; un test couvre un nouvel essai pendant
une action en cours, puis après sa fin
**And** la concurrence entre une action et le sync périodique existe déjà
aujourd'hui ; elle n'est pas traitée ici et reste déclarée comme résiduel.

**AC7 — Taille de parc supportée mesurée, enveloppe conjointe**

**Given** le démon plafonne son lissage pour tenir `deadline_s`, mais ne
peut pas comprimer le travail pur (publication MQTT et évaluation des
équipements)
**When** un test de charge du démon simule des parcs avec un faux MQTT à
latence réaliste
**Then** le test mesure deux coûts unitaires, chacun retenu comme le maximum
observé majoré d'une marge explicite :
- `c_mqtt`, le coût d'un appel MQTT de l'action (`publish_message`, sur tous
  les chemins : discovery des candidats, état au clic, disponibilité,
  dépublication de chaque `node_id` ou de repli, dépublications de retypage,
  nettoyages rejoués, comptés sur le faux MQTT ; revue Codex P1, `a1a8514`),
  mesuré sur un parc multi-candidats, multi-`node_id` et retypé ;
- `c_eq`, le coût d'évaluation d'un équipement de la portée, ignorés compris,
  mesuré sur une portée surtout ignorée (exclus, sans mapping) et presque
  sans appel MQTT (revue Codex P1, `99f2450`), composée de la forme
  d'équipement la plus coûteuse à évaluer (nombre maximal de commandes et de
  mappings secondaires, déclaré) : l'évaluation a lieu avant le filtre de
  portée (`http_server.py:3883-3898`) et parcourt toutes les commandes et
  tous les mappings (`models/evaluate_equipment.py:341-420` ; revue Codex P1,
  `3dcdb54`). Un équipement qui dépasse cette forme compte au prorata de ses
  commandes ;
- `c_parc`, le coût, par équipement du **parc entier**, du travail de fin
  d'action qui ne dépend pas de la portée : `_apply_pending_scope_flags` sur
  tout `published_scope` et `save_publications_cache` sur toutes les
  `publications` (`http_server.py:3819-3824` et `4058-4063`,
  `disk_cache.py:117-149` ; revue Codex P1, `dfc651e`), mesuré par une action
  sur un seul équipement d'un très grand inventaire dont les publications
  portent le nombre maximal de secondaires et de `node_id` (déclaré) : la
  sérialisation du cache parcourt tous les `additional_mappings` de chaque
  publication (`disk_cache.py:56-76` ; revue Codex P1, `5f3cc0c`). Une
  publication qui dépasse cette forme compte au prorata de ses candidats

**And** la taille supportée est une **enveloppe conjointe**, pas des maxima
indépendants (revue Codex P1, `55be1a1`) : un parc est supporté si
`appels_MQTT × c_mqtt + équipements_portée × c_eq + équipements_parc × c_parc
≤ budget_travail` (AC1bis)
**And** l'enveloppe est une borne supérieure : chaque coût unitaire est
mesuré sur la forme la plus coûteuse de son chemin
**And** l'enveloppe est un modèle linéaire mesuré : tout autre terme de coût
découvert en dev-story ou en revue de code s'y ajoute sous la même forme,
mesuré par le test de charge ; la durée **de bout en bout** de chaque
scénario est comparée à `deadline_s`, ce qui fait apparaître un terme oublié
**And** deux scénarios placés sur la frontière de l'enveloppe vérifient que
la réponse du démon arrive avant `deadline_s` : un scénario **mixte**
(beaucoup d'équipements ignorés et beaucoup d'appels MQTT à la fois) et une
**petite portée sur un très grand inventaire**
**And** l'enveloppe, ses constantes et leur marge sont figées par le test et
déclarées dans la story et dans la documentation utilisateur
(`docs/fr_FR/index.md`), traduites en ordres de grandeur lisibles pour un
utilisateur (par exemple un nombre d'équipements typiques)
**And** les assertions de durée côté démon portent sur `deadline_s`, pas sur
`R` : `reserve_s` couvre la sérialisation et le trajet retour (revue Codex
P2, `55be1a1`). Le test rejoue la mesure du 30/09 (N total = 292,
N évalués = 94, environ 11 s) et un grand parc simulé dans l'enveloppe (visé :
1 000 équipements multi-capteurs ; si l'enveloppe mesurée est plus petite,
le rapport le dit et la story le déclare), et vérifie que la réponse du
démon arrive avant `deadline_s`. Le relais est testé séparément contre `R`
(AC1, AC5).

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
  quand les pauses cumulées atteindraient `P_max`, au-delà de 150
  équipements évalués) et par le test de non-régression sur petite portée.
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

- [x] Task 1 — Relais PHP, client JS et démon : budget fixe + échéance (AC1,
  AC1bis, AC2, AC3, AC5)
  - [x] Constantes `R = 60 s` et `reserve_s = 5 s` (PHP), budget fixe pour
    `callDaemon`, `deadline_s = R - reserve_s` transmis au démon.
  - [x] Journalisation d'AC1 (relais : intention, portée, `R`, `reserve_s`,
    `deadline_s`, durée de l'appel ; démon : durée de traitement, total des
    pauses), testée.
  - [x] Appliquer ce budget à l'appel `callDaemon('/action/execute', …)`
    (`jeedom2ha.ajax.php:764`) pour `intention = publier` et
    `intention = supprimer`, avec `deadline_s` dans le corps de la requête.
  - [x] Pré-vérification `GET /system/status` (3 s, une tentative) avant
    la lecture au clic (AC3, ordre testé), pour signaler vite un démon
    injoignable.
  - [x] Démon : lecture de `deadline_s` sur `/action/execute`, plafond des
    pauses cumulées (AC1bis) dans les deux branches Publier
    (`:3881`) et Supprimer (`:3724`), sans changer le comportement sans
    `deadline_s`.
  - [x] Message d'erreur distinct en cas de vrai dépassement (AC5), formulé
    en dev-story.
  - [x] Délai fixe côté JS (`desktop/js/jeedom2ha.js:343`), indépendant de N
    (AC2).
  - [x] Échéance explicite de la lecture des valeurs au clic (AC2), testée.
  - [x] Tests PHP (un cas par portée, statut, non-régression petite
    portée), démon (compression AC1bis, non-régression sans `deadline_s`) et
    JS (délai fixe).

- [x] Task 2 — Action protégée contre la déconnexion du client (AC6)
  - [x] Protection systématique de l'exécution (tâche unique protégée), sans
    condition sur la version d'aiohttp.
  - [x] Test d'intégration démon : handler long, déconnexion client simulée
    avant la fin, action complète vérifiée ; version d'aiohttp testée et
    comportement brut observé documentés dans les Dev Notes.

- [x] Task 3 — Écouteurs et test de charge (AC4, AC7)
  - [x] Test simulant un grand parc où le lissage s'est comprimé (AC1bis) et
    où le réalignement des écouteurs a bien lieu (AC4), contrastant avec
    l'ancien comportement à budget fixe non borné.
  - [x] Test de charge du démon (AC7), faux MQTT à latence réaliste :
    `c_mqtt` mesuré sur un parc multi-candidats, retypé et multi-`node_id` ;
    `c_eq` mesuré sur une portée surtout ignorée, presque sans appel MQTT,
    faite de la forme d'équipement la plus coûteuse à évaluer (revue Codex,
    `ecce1dc`, `3dcdb54`) ; `c_parc` mesuré par une action sur un seul
    équipement d'un très grand inventaire (revue Codex P1, `dfc651e`) ;
    enveloppe conjointe vérifiée sur sa frontière par le scénario mixte et
    par la petite portée sur grand inventaire (revue Codex P1, `55be1a1`).
    Rejoue le
    couple mesuré (292, 94, ~11 s) et un grand parc simulé dans l'enveloppe ;
    assertions sur `deadline_s`. Déclare l'enveloppe, avec une marge
    explicite.
  - [x] Documentation utilisateur : ajouter la taille supportée et le message
    d'AC5 dans `docs/fr_FR/index.md` (revue Codex P2, `a1a8514`).

- [x] Task 3bis — Sérialisation des actions (AC8)
  - [x] Verrou unique des actions `publier`/`supprimer` dans le démon, refus
    immédiat et explicite d'une seconde action, libération garantie.
  - [x] Relais : message du refus transmis tel quel ; tests démon et PHP (nouvel
    essai pendant, puis après l'action).

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
- Résiduel déclaré (AC2, revue Codex P2, PR #189, 3e tour) : un appel individuel au cœur
  Jeedom (`cmd::byEqLogicId`, `getCache`) est synchrone et non interruptible en PHP sans
  refonte — l'échéance de `_jeedom2ha_collect_click_values` n'est vérifiée qu'entre deux
  appels, et la marge du délai client (14 s, 90 s contre un pire chemin de 76 s) couvre ce
  résidu.
- Résiduel déclaré (AC4, revue Codex P2, PR #189, 7e tour) : les 3 s de
  `GET /system/state_listeners` bornent la lecture, mais pas la création/suppression des
  écouteurs en base (`core/class/jeedom2ha.class.php:419-440`) — la même marge du délai
  client (14 s, 90 s contre 76 s) couvre ce résidu ; au-delà, l'AJAX peut expirer après une
  action réussie (entités publiées, message d'échec faux), à mesurer par la preuve terrain.
- Ne pas introduire de flux asynchrone/polling (option (c)) sans validation
  explicite d'Alex — hors périmètre de cette story.
- Le démon **n'interrompt jamais** une action en cours pour tenir
  `deadline_s` : il comprime uniquement le délai *entre* deux équipements,
  jamais le travail lui-même (AC1bis).
- Le budget du relais (`R`) et la réserve (`reserve_s`) sont des constantes
  fixes, indépendantes de N — ne pas réintroduire de lecture de
  `published_scope`/`topology` pour dimensionner un budget (c'est le trou
  qui a fait abandonner l'option (a)).
- Ne pas réintroduire d'estimation du travail restant pour tenir
  l'échéance : le plafond des pauses (AC1bis) suffit et ne dépend d'aucun
  précompte (abandonné après la revue Codex, `ecce1dc`).
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
  [NOUVEAU], `docs/fr_FR/index.md` [À MODIFIER — taille supportée, message
  d'AC5].

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

- `clawcode` — Claude (claude-sonnet-5), sessions détachées « unités » A à D,
  worktree `story/19-6-duree-action-ha`.

### Debug Log References

- Unité B (démon, AC6/AC8) : aiohttp `3.8.4` testé sur la VM de développement
  (pas la box de terrain), déconnexion simulée par l'annulation du handler —
  le comportement brut d'aiohttp sans `asyncio.shield` n'a **pas été observé**
  (la protection systématique de la tâche d'action reste indépendante de la
  version d'aiohttp). Version d'aiohttp installée sur la box de terrain,
  relevée par ClaudeBox le 30/09 : `3.13.3`.
- Unité D/E (bloc D, AC4/AC7) : enveloppe mesurée sur cette VM de développement
  (pas la box de terrain) — voir « Enveloppe AC7 » ci-dessous pour les
  constantes, marges et facteur machine déclarés à cette fin. Revue PR #189
  (Unité E, 2026-09-30) : coûts unitaires recalculés sur maximum mesuré
  (`MARGE_MESURE=1.5` × `MACHINE_FACTOR=3.0`), MQTT et `c_eq`/`c_parc` mesurés
  dans le chemin réel (vrai `DiscoveryPublisher`, vrai `MapperRegistry`) ;
  `N_max` (parc typique multi-capteurs, 90% de l'enveloppe) mesuré à 513.
  2e tour de revue (Codex P1, PR #189, 2026-09-30) : le vrai « Publier »
  exécute aussi `publish_click_states()` (état au clic, un appel MQTT par
  candidat streamé) — coût désormais mesuré dans le chemin réel via un vrai
  `StateSynchronizer` branché sur le faux pont MQTT à latence, avec
  `current_values` transmis comme le relais PHP. Appels MQTT par équipement
  multi-capteurs mesurés : 3 discovery + 2 état = 5 (la disponibilité locale
  n'ajoute aucun appel dans ce fixture). `N_max` recalculé à ~301-309
  (mesures 2026-09-30, variance de mesure entre `test_ac7_couts_mesures_et_enveloppe_respectee`
  et `test_ac7_parc_typique_90_pct_enveloppe_sous_deadline`).
  4e tour de revue (Codex P2, PR #189, 2026-09-30) : `c_parc` ne chronométrait
  que `save_publications_cache()`, alors que la fin de l'action parcourt aussi
  tout `published_scope` via `_apply_pending_scope_flags()`. `c_parc` est
  désormais mesuré de bout en bout par le handler réel « Publier » (1 seul
  équipement ciblé), en pente entre deux tailles d'inventaire (N=1000 et
  N=5000, 3 essais chacune) : `c_parc_mesure≈0.000004s`, `c_parc≈0.000018s`
  après marge (`×1.5`) et facteur machine (`×3`). `N_max` recalculé à
  ~301-309 (inchangé à l'échelle). Nouveau scénario « petite portée sur grand
  inventaire » à la frontière
  (`test_ac7_petite_portee_grand_inventaire_frontiere_sous_deadline`) :
  `N_parc` théorique à 90% de l'enveloppe ≈ 1 990 773, plafonné à 50 000 ;
  durée mesurée à `N_parc=50000` ≈ 0,24 s, largement sous `deadline_s=55s`.

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
- **Relecture ClaudeBox de (b′)** — 2026-09-30 — doublon de l'option (c)
  retiré ; AC1bis : estimation du travail restant bornée par une valeur a
  priori prudente au démarrage (objection clawcode) ; AC2 : délai du client
  couvrant le pire des deux chemins (statut préalable, lecture au clic, `R`,
  puis réalignement ou second statut) ; AC5 : second `GET /system/status`
  après l'échec pour le diagnostic.
- **Revue Codex, 6e tour (`472c372`)** — pause finale supprimée et
  dénominateur = pauses restantes (P2) ; travail restant précompté en
  publications MQTT à coût unitaire non décroissant, test avec les
  équipements lourds en fin de portée (P1) ; exécution protégée si aiohttp
  annule le handler, état partiel refusé (P1).
- **Revue Codex, 7e tour (`5570532`)** — précompte du travail sur une borne
  supérieure indépendante du dernier mapping (commandes de l'équipement) (P1) ;
  AC8 ajouté : une seule action HA à la fois, refus explicite d'une seconde
  (P1). Concurrence action/sync périodique : préexistante, déclarée.
- **Revue Codex, 8e tour (`17f8892`)** — précompte majoré par une borne
  multiplicative (discovery, état au clic, disponibilité) plus les nettoyages
  différés connus, avec un test qui compare le précompte aux appels MQTT réels
  (P1).
- **Revue Codex, 9e tour (`f378ceb`)** — supprimer compte max(1, `node_id`)
  (dépublication mono-entité de repli) ; règle générale : précompte ≥ appels
  réels sur chaque chemin, vérifiée par le test du faux MQTT (P1).
- **Revue Codex, 10e tour (`a1a8514`)** — taille supportée mesurée en appels
  MQTT totaux, même unité que le précompte (P1) ; documentation utilisateur
  `docs/fr_FR/index.md` planifiée (P2).
- **Revue Codex, 11e tour (`99f2450`)** — coût d'évaluation par équipement
  (y compris ignorés) ajouté à la réserve, et seconde borne de taille
  supportée en nombre d'équipements, testée sur une portée surtout ignorée
  (P1).
- **Revue Codex, 12e tour (`71097f6`)** — AC6 : exécution de l'action
  toujours protégée contre l'annulation du handler, sans condition sur la
  version d'aiohttp (non épinglée) ; le test vérifie l'action complète (P1).
- **Revue Codex, 13e tour (`ecce1dc`), décision ClaudeBox** — le précompte
  des appels MQTT restants manquait encore un chemin (dépublications
  immédiates de retypage, P1), après les tours 7, 8, 9 et 11 : il est
  abandonné. AC1bis plafonne désormais le total des pauses
  (`min(P_max, deadline_s / 2)`, `P_max = 15 s`), ce qui borne la durée par
  le travail pur plus ce plafond sans aucune estimation ; AC7 mesure ce
  travail pur. Task 3 : scénario presque sans MQTT et déclaration des deux
  bornes (P2).
- **Revue Codex, 14e tour (`55be1a1`)** — taille supportée déclarée comme une
  enveloppe conjointe (`appels_MQTT × c_mqtt + équipements × c_eq`), vérifiée
  par un scénario mixte, au lieu de deux maxima indépendants (P1) ;
  assertions du test de charge sur `deadline_s`, relais testé contre `R`
  (P2) ; la garantie du budget fixe est bornée à l'enveloppe dans l'epic et
  la proposition (P2).
- **Revue Codex, 15e tour (`dfc651e`)** — terme `c_parc` (travail de fin
  d'action proportionnel au parc entier : drapeaux de portée, cache des
  publications) ajouté à l'enveloppe, avec un scénario petite portée sur très
  grand inventaire ; clause générale : tout terme découvert plus tard s'ajoute
  à l'enveloppe, et chaque scénario est comparé de bout en bout à
  `deadline_s` (P1) ; marge de réveil des pauses `marge_reveil` et
  `budget_travail = deadline_s - plafond_pauses - marge_reveil`, testée par
  un sommeil en retard (P2).
- **Revue Codex, 16e tour (`2cd9428`)** — AC3 : la sonde de statut précède
  la lecture au clic (ordre testé), pour qu'un évènement reçu pendant la
  sonde ne soit pas écrasé par une valeur plus ancienne (P1) ; fenêtre
  résiduelle de l'AC8 de 19.5 bornée par la durée de la lecture, déclarée.
- **Revue Codex, 17e tour (`3dcdb54`)** — `c_eq` mesuré sur la forme
  d'équipement la plus coûteuse à évaluer (commandes, mappings secondaires),
  au prorata au-delà ; l'enveloppe est une borne supérieure, chaque coût
  étant mesuré sur la forme la plus coûteuse de son chemin (P1) ;
  journalisation d'AC1 complétée (`deadline_s`, durées, pauses) et testée (P2).
- **Revue Codex, 18e tour (`5f3cc0c`)** — `c_parc` mesuré sur un inventaire
  dont les publications portent le nombre maximal de secondaires et de
  `node_id`, au prorata des candidats au-delà (P1). AC5 aligné sur
  `budget_travail`.
- **Unité C, corrections de revue** — 2026-09-30 — quatre corrections sur le
  relais/client : ordre de chargement JS garanti (`jeedom2ha_action_budget.js`
  avant `jeedom2ha.js`), délai client lu depuis `Jeedom2haActionBudget.CLIENT_TIMEOUT_MS`
  (repli 90000) ; échéance de lecture au clic démarrée au début de
  `_jeedom2ha_collect_click_values` et vérifiée aussi pendant la liste des
  commandes (pas seulement la lecture des valeurs) ; niveaux de journal portés
  par l'appelant (`error` démon injoignable, `warning` dépassement AC5/refus
  409, `info` ligne de budget AC1) ; message AC5 corrigé (démon du plugin, pas
  Home Assistant). Commit `21c357c`.
- **Unité D, bloc D (AC4, AC7, documentation, story)** — 2026-09-30 — test de
  charge AC7 (`test_story_19_6_load_ac7.py`, marqueur pytest `load` dédié,
  exclu par défaut via `addopts = "-m 'not load'"`) : mesure réelle de
  `c_eq` (`evaluate_equipment()` sur un équipement à 20 commandes,
  multi-domaine switch+sensor+binary_sensor, overrides) et de `c_parc`
  (`save_publications_cache()` sur 500 publications de cette même forme
  coûteuse) via `time.perf_counter`, minimum sur 20/5 itérations, facteur
  machine ×3 déclaré (box de terrain non mesurée directement dans cette
  session) ; `c_mqtt` déclaré (pas de broker réel disponible) à 5 ms par appel
  `publish_message`, ×3 également. Enveloppe
  `appels_MQTT × c_mqtt + eq_portée × c_eq + eq_parc × c_parc ≤ budget_travail`
  (39 s) vérifiée sur le scénario mixte (94, 94, 1000) et sur une petite
  portée sur très grand inventaire (1, 1, 5000). Deux tests bout-en-bout
  (aiohttp réel, `DiscoveryPublisher` mocké faute de broker) : rejeu du couple
  mesuré du 30/09 (292 total, 94 évalués/publiés) et un parc cible de 1000
  équipements multi-capteurs sur la portée globale entière — les deux
  terminent sous `deadline_s` (55 s), en ~0,01 s chacun (pas de MQTT réel,
  seul le travail CPU du démon est mesuré). AC4 : réalignement après succès
  déjà couvert côté relais par le test PHP existant (`test_story_19_6_php_relay.php`,
  bloc « AC4 — réalignement après succès seulement ») ; côté démon, le test
  du grand parc (1000) démontre qu'un succès sur un parc volumineux précède
  bien l'échéance, condition du réalignement. Documentation utilisateur
  ajoutée (`docs/fr_FR/index.md`, section « Durée des actions Publier /
  Supprimer ») : taille supportée en ordre de grandeur (centaines à ~1000
  équipements) et message AC5 exact avec conduite à tenir. Suite par défaut :
  2014 passed, 3 deselected (inchangé), 217,7 s (pas de croissance mesurable
  due au bloc D, conforme à la contrainte des ~30 s). Déviation documentée :
  faute d'accès à la box de terrain dans cette session, le facteur machine
  (×3) et `c_mqtt` (5 ms/appel) sont déclarés par prudence plutôt que
  mesurés en conditions réelles — à confronter à la preuve terrain (Task 4,
  hors scope de cette session).
- **Unité G (3e tour de revue PR #189, Codex)** — 2026-09-30 — trois points :
  (1) cession de la main (`asyncio.sleep(0)`) ajoutée en tête de chaque
  itération des boucles Publier/Supprimer, y compris les équipements sautés
  (ignorés, inclus non mappables, ou non publiés), pour qu'un grand parc
  surtout ignoré ne monopolise pas la boucle aiohttp ; deux nouveaux tests
  d'intégration vérifient qu'un `GET /system/status` concurrent est servi
  avant la fin d'une action sur une portée à 499/500 équipements ignorés
  (P2). (2) deux scénarios de charge ajoutés à `test_story_19_6_load_ac7.py` :
  « Supprimer » sur des équipements multi-`node_id` (94 équipements, mesuré
  3,00 appels MQTT/équipement) et « Publier » avec retypage du principal et
  des secondaires (94 équipements, mesuré 10,00 appels MQTT/équipement, deux
  fois le coût d'une publication initiale) — les deux sous `deadline_s` ;
  documentation utilisateur corrigée pour exprimer la taille supportée en
  appels MQTT par action d'abord, puis en équipements typiques, avec les
  coûts mesurés du retypage et de la suppression multi-entités (P1). (3)
  résiduel PHP déclaré (AC2, sans code) : un appel individuel au cœur Jeedom
  reste non interruptible en synchrone, couvert par la marge du délai client
  (14 s) (P2).
- **Unité I (5e tour de revue PR #189, Codex + ClaudeBox)** — 2026-09-30 —
  deux points. (1, ClaudeBox) `_measure_c_parc_e2e` peuplait un inventaire
  publié à presque rien (`_build_app(n, 1, …)` : une seule publication),
  minorant `c_parc` (pente mesurée 4 µs/équipement au lieu des 18 µs
  attendus). Corrigé : `_build_app(n, n, …)` peuple les publications
  multi-capteurs de tout le parc, l'action réelle ciblant désormais un seul
  équipement (`portee: equipement`, nouvel helper `_run_publier_equipement`)
  pour isoler le coût du parc de celui de la portée traitée.
  `c_parc_mesure` mesuré à `0.000075s` (vs `0.000004s` avant correction),
  `c_parc≈0.000336s` après marge/facteur machine ; `N_max` toujours ~301-309
  (dominé par `c_mqtt`, variation négligeable à cette échelle). (2, Codex P1)
  la capacité annoncée (« environ 300 équipements ») n'était pas protégée par
  la CI (`assert n_max > 0` seulement), trop proche du `n_max` mesuré pour
  servir de seuil stable sur des runners plus lents. Doc corrigée : « environ
  250 équipements typiques » ; constante `CAPACITE_DOCUMENTEE = 250` ajoutée
  au test de charge, `assert n_max >= CAPACITE_DOCUMENTEE` dans
  `test_ac7_couts_mesures_et_enveloppe_respectee` et
  `test_ac7_parc_typique_90_pct_enveloppe_sous_deadline` ; ce dernier exerce
  désormais réellement `N = CAPACITE_DOCUMENTEE` (250), pas seulement le
  `n_max` recalculé sur la VM de mesure. Suites : pytest racine 2021
  passed/8 deselected (217,8 s, inchangé) ; `-m load` 8 passed (84,0 s) ;
  node 311 pass ; PHP (CI) 5 passed/3 skipped ; flake8 propre sur le fichier
  touché.

### File List

- `desktop/php/jeedom2ha.php` — inclusion de `jeedom2ha_action_budget.js`
  avant `jeedom2ha.js`.
- `desktop/js/jeedom2ha.js` — `executeHaAction()` lit
  `Jeedom2haActionBudget.CLIENT_TIMEOUT_MS` (repli 90000).
- `desktop/js/jeedom2ha_action_budget.js` — module de constantes partagées
  (lecture seule cette session).
- `core/ajax/jeedom2ha.ajax.php` — `_jeedom2ha_collect_click_values()`
  (horloge démarrée avant l'expansion de portée, échéance vérifiée pendant
  la liste des commandes) ; niveau de journal transmis à
  `jeedom2ha_dispatch_action_relay()`.
- `core/php/jeedom2ha_action_budget.php` — `jeedom2ha_dispatch_action_relay()`
  (paramètre `$log(level, message)`), `jeedom2ha_action_timeout_message()`
  (message AC5 corrigé).
- `tests/unit/test_story_19_6_php_relay.php` — test de l'échéance pendant la
  liste des commandes ; assertions de niveau de journal (AC1/AC3/AC5/AC8).
- `tests/unit/test_story_19_6_client_timeout.node.test.js` — test de
  référence `CLIENT_TIMEOUT_MS` et de l'ordre d'inclusion JS.
- `resources/daemon/tests/unit/test_story_19_6_load_ac7.py` — nouveau,
  test de charge AC7 (marqueur `load`).
- `pyproject.toml` — marqueur pytest `load` déclaré, exclu par défaut.
- `docs/fr_FR/index.md` — section « Durée des actions Publier / Supprimer ».
- `_bmad-output/implementation-artifacts/19-6-duree-action-ha-bornee-cc32.md`
  — Tasks 1-3bis cochées, statut `review`, Dev Agent Record complété.
- `_bmad-output/sprint-status.yaml` — statut de la story 19.6 → `review`.

### Change Log

- 2026-09-30 — `correct-course` (CC-32) + `create-story` — statut
  `ready-for-dev`.
- 2026-09-30 — relecture ClaudeBox (décision, UI Impact, N, plafond, délai du
  client, modèle, pointeurs) et revue Codex PR #188 intégrée.
- 2026-09-30 — conception (b′), décision ClaudeBox après 4 tours Codex :
  lissage borné par une échéance donnée au démon, option (a) abandonnée.
- 2026-09-30 — relecture ClaudeBox de (b′) (doublon (c), estimation au
  démarrage, délai du client sur le pire chemin, second statut en AC5).
- 2026-09-30 — revue Codex 6e tour (pause finale, précompte du travail,
  exécution protégée).
- 2026-09-30 — revue Codex 7e tour (borne du précompte, AC8 sérialisation).
- 2026-09-30 — revue Codex 8e tour (précompte de tous les appels MQTT).
- 2026-09-30 — revue Codex 9e tour (max(1, node_id), règle générale du précompte).
- 2026-09-30 — revue Codex 10e tour (unité de la taille supportée, doc utilisateur).
- 2026-09-30 — revue Codex 11e tour (coût d'évaluation, seconde borne).
- 2026-09-30 — revue Codex 12e tour (AC6 : protection systématique).
- 2026-09-30 — revue Codex 13e tour : précompte abandonné, plafond des
  pauses (AC1bis) ; deux scénarios de charge (Task 3).
- 2026-09-30 — revue Codex 14e tour (enveloppe conjointe, assertions sur
  `deadline_s`, garantie bornée à l'enveloppe).
- 2026-09-30 — revue Codex 15e tour (coût du parc entier, marge de réveil).
- 2026-09-30 — revue Codex 16e tour (AC3 : sonde avant la lecture au clic).
- 2026-09-30 — revue Codex 17e tour (forme la plus coûteuse, journalisation).
- 2026-09-30 — revue Codex 18e tour (`c_parc` sur les secondaires du parc).
- 2026-09-30 — unité C : corrections de revue relais/client (ordre JS,
  échéance de lecture au clic, niveaux de journal, message AC5).
- 2026-09-30 — unité D : test de charge AC7 (marqueur `load`), citation du
  test AC4 existant, documentation utilisateur, Tasks 1-3bis cochées,
  statut `review`.
- 2026-09-30 — unité E (revue PR #189, Codex + ClaudeBox) : test de charge
  AC7 refondu (coûts au maximum mesuré, MQTT et `c_eq`/`c_parc` mesurés dans
  le chemin réel, cache en `tmp_path`, `N_max=513` mesuré) ; pause de
  lissage « Publier » déplacée avant le travail (plus de pause finale
  superflue) ; documentation utilisateur corrigée (le démon ne s'arrête
  jamais, message AC8, taille supportée `N_max`) ; Debug Log Reference AC6
  corrigée (aiohttp `3.8.4` testé sur la VM, comportement brut non observé).
- 2026-09-30 — unité F (2e tour de revue PR #189, Codex) : cession de la
  main via `asyncio.sleep(0)` quand la pause de lissage vaut 0 (plafond
  consommé), pour ne plus bloquer `/system/status` pendant une longue
  action ; test de charge AC7 exerce désormais `publish_click_states()`
  (vrai `StateSynchronizer`, `current_values` transmis) ; `N_max` recalculé
  à ~301-309 (5 appels MQTT/équipement au lieu de 3).
- 2026-09-30 — unité G (3e tour de revue PR #189, Codex) : cession de la
  main aussi sur les itérations sautées (ignorées/non mappables/non
  publiées) ; deux scénarios de charge mesurant les chemins MQTT plus
  coûteux (suppression multi-`node_id` : 3,00 appels/équipement ; publier
  avec retypage : 10,00 appels/équipement) et documentation utilisateur
  corrigée en conséquence ; résiduel PHP (AC2) déclaré sans code.
- 2026-09-30 — unité K (7e tour de revue PR #189, Codex) : référence forte
  `app["action_tasks"]` sur la tâche protégée par `asyncio.shield` (AC6),
  évitant une collecte prématurée par le garbage collector si le handler est
  annulé ; résiduel AC4 (écouteurs en base non bornés par les 3 s de
  `GET /system/state_listeners`) déclaré sans code.
