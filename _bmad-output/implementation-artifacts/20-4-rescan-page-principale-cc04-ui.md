# Story 20.4 : Rescan depuis la page principale (CC-04, volet UI)

Status: draft

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
- 20-2 est en cadrage : cette story ne présume ni la sémantique du forçage ni les
  actions retenues. Son seul contrat est d'appliquer les overrides persistés.
- Le rescan est une écriture : il peut publier, dépublier et nettoyer la
  disponibilité (`resources/daemon/transport/http_server.py:1846-1869`,
  `:1892-2020`). Il n'est ni « Republier » ni « Supprimer puis recréer ».

## Acceptance Criteria

**AC1 — Entrée principale et garde-fou** *(dépend de Q1)*

**Given** la page principale du plugin
**When** elle affiche les actions Home Assistant
**Then** elle affiche une action « Rescanner la topologie Jeedom » dans le bloc
« Actions Home Assistant », sans modifier la surface par pièce
**And** l'action réutilise le garde-fou bridge/MQTT existant : elle est inactive
et explique la cause si le daemon est arrêté ou MQTT déconnecté.

**AC2 — Confirmation explicite** *(dépend de Q2)*

**Given** le bridge et MQTT sont disponibles
**When** l'utilisateur clique sur « Rescanner la topologie Jeedom »
**Then** une confirmation explique qu'un sync complet peut publier ou retirer des
entités Home Assistant et applique les overrides persistés
**And** aucun appel n'est effectué si l'utilisateur annule.

**AC3 — Exécution sans calcul local**

**Given** la confirmation validée
**When** le rescan part
**Then** l'interface désactive seulement son bouton et affiche « Rescan en cours… »
**And** elle appelle le contrat existant `scanTopology`, sans reconstruire la
topologie, décider la publication, ni calculer les compteurs côté interface.

**AC4 — Retour lisible et santé rafraîchie**

**Given** un rescan en cours
**When** `scanTopology` répond avec succès
**Then** l'interface affiche un succès à partir du résumé backend retourné, puis
rafraîchit le bandeau santé, dont « Dernière synchro » et « Dernière opération »
**And** elle réactive le bouton.
**When** `scanTopology` échoue ou expire
**Then** elle affiche l'erreur retournée ou une erreur de communication, réactive
le bouton et ne déclare pas de succès.

**AC5 — Configuration conservée, rôle distinct** *(dépend de Q3)*

**Given** la page de configuration
**When** l'utilisateur modifie les filtres puis choisit l'action existante
**Then** « Appliquer les filtres et rescanner » sauvegarde d'abord les filtres,
puis utilise le même `scanTopology`
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
**Then** son parcours déclare le rescan comme écriture et l'intercepte : aucune
écriture n'est transmise à Jeedom, au daemon ni à Home Assistant
**And** le clic réel ultérieur du rescan est prouvé séparément avec relevés avant
et après ; la parité attendue est identique, sauf écart explicitement expliqué.

## UI Impact

- **UI Impact : Oui.** La page principale reçoit une action visible et un retour
  d'exécution. Le statut final exige `ready-for-UX-validation` avant `done`.

## Tasks / Subtasks

- [ ] **Task 0 — Relevés préalables, lecture seule (AC: 1, 4, 7)**
  - [ ] Relever le statut bridge, la dernière synchro, la dernière opération et la
    parité de référence, sans lancer de rescan.
  - [ ] Identifier un moment et un périmètre sûrs pour le clic réel avec Alex ; ne
    pas choisir d'équipement ni de nom dans cette story.
- [ ] **Task 1 — Entrée et garde-fou (AC: 1, 2)**
  - [ ] Ajouter l'action dans le bloc HA existant, avec le même attribut de garde.
  - [ ] Réutiliser la modale de confirmation ; son texte déclare les effets du sync.
- [ ] **Task 2 — Exécution et retour (AC: 3, 4, 6)**
  - [ ] Réutiliser `scanTopology` et son résumé backend. Aucun endpoint daemon neuf.
  - [ ] Gérer attente, succès, échec, expiration, réactivation et
    `refreshBridgeStatus()` sans calcul local.
- [ ] **Task 3 — Configuration (AC: 5)**
  - [ ] Conserver la chaîne sauvegarde puis rescan ; préciser son libellé selon Q3.
- [ ] **Task 4 — Tests et gate (AC: 1-7)**
  - [ ] Tester le garde-fou, annulation, appel unique, retour et erreurs.
  - [ ] Étendre le parcours 20-0 avec une écriture simulée, déclarée « rescan ».
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
- `desktop/php/jeedom2ha.php:70-132` : bandeau santé et bloc HA ;
  `desktop/js/jeedom2ha.js:18-154` : statut et garde-fou bridge/MQTT ;
  `:306-420` : confirmation, attente et rafraîchissement des actions HA.

### Interdits

- Aucun recalcul de topologie, de décision, de publication ou de compteurs en JS.
- Aucun nouveau point d'entrée daemon et aucun changement de la sémantique 20-2.
- Ne pas transformer le rescan en « Republier » ou « Supprimer puis recréer » :
  ces actions appellent `executeHaAction` (`desktop/js/jeedom2ha.js:332-420`) ;
  le rescan appelle `scanTopology` et refait tout le pipeline.
- Déploiement standard seulement ; jamais `--cleanup-discovery` ni
  `--stop-daemon-cleanup`. Jamais `git add -A`, `--admin` ni force-push.

### Fichiers probablement touchés

`desktop/php/jeedom2ha.php`, `desktop/js/jeedom2ha.js`,
`plugin_info/configuration.php` (libellé seulement si Q3 le retient), tests JS et
parcours du gate 20-0. Aucun fichier daemon attendu.

## Questions pour Alex

### Q1 — Place du bouton rescan

1. **Bloc « Actions Home Assistant » (recommandé).** Coût faible : réutilise le
   garde-fou et la proximité des effets HA. Cohérent avec une écriture.
2. **Bloc « Gestion ».** Coût faible, mais mélange navigation/configuration et
   action ayant des effets HA.
3. **Surface par pièce.** Coût moyen et incohérent : le rescan est global, pas
   limité à la pièce ouverte.

**Recommandation : 1.** AC1 est rédigé sur ce choix.

### Q2 — Confirmation avant rescan

1. **Confirmation à chaque clic (recommandé).** Coût faible ; rend visible que le
   sync peut publier ou retirer et que le clic est une écriture.
2. **Aucune confirmation.** Coût nul, mais risque de déclencher par erreur un sync
   global avec effets HA.
3. **Confirmation mémorisable.** Coût moyen ; ajoute une préférence et peut
   masquer un effet qui reste important.

**Recommandation : 1.** AC2 en dépend.

### Q3 — Rescan de la page de configuration

1. **Conserver « Appliquer les filtres et rescanner » (recommandé).** Coût faible :
   son rôle reste distinct, car il sauvegarde les filtres avant le même rescan.
2. **Le supprimer.** Coût moyen : il faut rediriger clairement après sauvegarde ;
   risque de perdre le parcours atomique « modifier puis appliquer ».
3. **Le garder sous son libellé actuel.** Coût nul, mais « Appliquer » est moins
   explicite depuis que le rescan existe aussi sur la page principale.

**Recommandation : 1.** AC5 est rédigé sur ce choix. Le rescan principal ne
sauvegarde jamais les champs de configuration.

## Définition de done

- Les décisions Q1-Q3 sont intégrées ou les AC dépendants sont ajustés et relus.
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
- [Source: `desktop/php/jeedom2ha.php:63-132`]
- [Source: `desktop/js/jeedom2ha.js:18-154`, `:306-420`]
- [Source: `_bmad-output/implementation-artifacts/20-0-gate-preuve-ux-outille.md`]
- [Source: `_bmad-output/implementation-artifacts/20-1-surface-unique-piece-equipement-commande.md`]

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Completion Notes List

- 2026-10-05 — Brouillon create-story non interactif ; confirmations par défaut :
  création seule, statut `draft`, aucune modification de `sprint-status.yaml`.

### File List

- `_bmad-output/implementation-artifacts/20-4-rescan-page-principale-cc04-ui.md`
