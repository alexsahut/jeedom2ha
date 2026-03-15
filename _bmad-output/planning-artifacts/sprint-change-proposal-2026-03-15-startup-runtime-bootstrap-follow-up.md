# Sprint Change Proposal - Follow-up startup runtime sync apres restart daemon

- Projet: `jeedom2ha`
- Date: `2026-03-15`
- Auteur: `Codex (Scrum Master)`
- Mode: `Batch`
- Declencheur: validation terrain post-Story 3.2 sur restart daemon
- Portee recommandee: `Epic 3` uniquement, via nouveau follow-up cible

---

## Section 1 - Issue Summary

### Probleme identifie

Apres redemarrage du daemon `jeedom2ha`, des entites deja presentes et commandables dans Home Assistant peuvent devenir temporairement non pilotables jusqu'a execution manuelle de `POST /action/sync`.

### Ce qui est prouve

**Prouve par validation terrain fournie:**

- avant resync runtime apres restart daemon sur `eq_id=391`, une commande HA produit un rejet runtime avec `reason_code=unknown_runtime_entity action=reject_command`;
- apres execution manuelle de `/action/sync`, la meme commande produit `reason_code=command_executed action=execute_command`, puis `reason_code=real_state_confirmation action=select_confirmation_policy`;
- le flux MQTT HA -> daemon -> Jeedom fonctionne donc bien une fois le registre runtime correctement alimente;
- le contrat d'authentification reel n'est pas le probleme principal du follow-up: le protocole terrain prouve deja `cmd::execCmd` via `core API key` sur la box testee.

**Prouve par lecture du code et des artefacts:**

- le registre runtime `app["publications"]` et `app["mappings"]` est initialise vide au demarrage du daemon, puis rempli par `/action/sync` seulement;
- le `CommandSynchronizer` rejette toute commande dont la cible n'est pas retrouvee dans ce registre runtime actif;
- `deamon_start()` connecte le daemon et initie MQTT, mais ne declenche aucun `/action/sync` automatique.

### Ce qui est infere

- le comportement observe n'est pas un defaut du gating Story 3.2; c'est au contraire ce gating qui revele un trou de bootstrap runtime au demarrage;
- la cause la plus probable est l'absence de rehydratation initiale du registre runtime apres restart daemon;
- un simple auto-resync one-shot apres startup devrait suffire a retablir la pilotabilite nominale sans introduire de persistance lifecycle avancee.

### Ce qui reste a confirmer

- faut-il declencher le bootstrap uniquement au premier `connect` MQTT apres demarrage du daemon, ou aussi sur certaines reconnexions ulterieures;
- quel niveau de republication effective est acceptable lors de ce bootstrap (rehydratation seule si possible, sinon reuse controle de `/action/sync`);
- la latence et la charge d'un bootstrap automatique sur une installation plus grande que la box testee.

### Qualification du probleme

Ce sujet est qualifie comme:

- **bug startup/lifecycle a perimetre strict** dans l'implementation actuelle;
- plus precisement, **manque de bootstrap runtime** apres redemarrage du daemon;
- avec **besoin probable de resync automatique au demarrage**, mais **pas** de resync lifecycle avance sur toute reconnexion par defaut dans ce follow-up.

---

## Section 2 - Impact Analysis

### Impact Epic

- **Epic impacte:** `Epic 3`.
- **Story declencheuse:** `Story 3.2`.
- **Conclusion BMAD:** ne pas rouvrir abusivement Story 3.2, mais ajouter un follow-up dedie dans Epic 3 avant de considerer l'axe runtime/stability comme suffisamment consolide.

### Pourquoi ce n'est pas Epic 5

Le comportement observe est plus etroit que `Story 5.1`:

- `Story 5.1` parle de persistance, recharge du cache technique, revalidation complete, republication post-reboot multi-cas (daemon, Jeedom, broker, HA) et lissage de charge;
- le cas prouve ici est strictement: **apres restart daemon, le registre runtime actif n'est pas rehydrate, donc le gating commande rejette une entite pourtant deja exposee**;
- le follow-up necessaire peut rester borne a un **bootstrap one-shot** utilisant les mecanismes existants, sans introduire persistance `data/`, revalidation lifecycle avancee, ni politique globale de reprise post-reboot.

### Impact stories / backlog

- `3.2` peut rester **fonctionnellement valide sur runtime hydrate**, mais ne doit pas etre marquee "terminee sans reserve produit" tant que le trou startup n'est pas explicitement trace;
- `3.3` depend indirectement du meme registre runtime actif pour exposer une disponibilite coherente; il est donc sain de traiter ce follow-up **avant** ou **en prealable immediat** a `3.3`;
- `Epic 5` reste **inchange en perimetre**.

### Impact artefacts

- **Epics:** ajout d'une story follow-up dans `Epic 3`.
- **Architecture:** clarification utile sur le bootstrap runtime one-shot apres demarrage, comme usage borne du mecanisme de rescan existant.
- **Project context:** ajout d'un garde-fou sur restart daemon -> verification sans `/action/sync` manuel.
- **Protocole de test reel:** ajout d'un cas de preuve "restart daemon puis commande avant sync manuel".
- **UX:** aucun changement de parcours requis.

### Impact technique

- orchestration de startup a completer pour reconstituer le registre runtime avant usage nominal des commandes;
- risque principal: declencher le bootstrap trop tot (avant MQTT connecte) ou trop souvent (surpublication / charge / doublons de sync);
- exigence de surete: en cas d'echec du bootstrap, conserver le rejet explicite des commandes plutot qu'un pilotage aveugle.

---

## Section 3 - Recommended Approach

### Option retenue

`Option 1 - Direct Adjustment`

Ajouter un **nouveau follow-up cible dans Epic 3**, sans reouvrir Story 3.2 et sans deplacer le sujet dans Epic 5.

### Formulation courte de la recommandation

Creer une story de type:

- **startup runtime bootstrap**
- declenchee **une seule fois apres demarrage du daemon**, une fois les prerequis minimums atteints;
- bornee a la **rehydratation du registre runtime actif** des entites `jeedom2ha`;
- sans persistance avancee, sans nouveau moteur lifecycle, sans resync generique sur toutes les reconnexions.

### Rationale

- **Effort:** `Low-Medium`
- **Risque:** `Medium`
- **Impact planning:** ajuste le sequencing d'Epic 3, sans replan global
- **Valeur:** supprime une friction terrain forte sur un comportement nominal apres restart
- **Protection de perimetre:** traite le bug produit reel sans aspirer trop tot les responsabilites d'Epic 5

### Alternatives ecartees

- **Rouvrir Story 3.2**: non recommande; le coeur commande/auth/gating est valide et le trou est un sujet de startup bootstrap distinct.
- **Basculer directement en Epic 5**: trop large et premature pour ce qui est actuellement prouve.
- **Ne rien faire et documenter `/action/sync` manuel**: non recommande pour le nominal; trop fragile pour un pont cense redevenir operationnel apres restart.

---

## Section 4 - Detailed Change Proposals

### 4.1 Proposition backlog - ajouter une story follow-up dans Epic 3

**Artifact:** `planning-artifacts/epics.md`

OLD:

```md
### Story 3.2: Pilotage HA -> Jeedom avec confirmation honnete d'etat
...
### Story 3.3: Disponibilite du pont et des entites quand l'information est fiable
```

NEW:

```md
### Story 3.2: Pilotage HA -> Jeedom avec confirmation honnete d'etat
...

### Story 3.2b: Bootstrap runtime apres restart daemon

As a utilisateur Home Assistant,
I want que les entites deja publiees redeviennent pilotables apres restart daemon sans `/action/sync` manuel,
So that le pont retrouve un comportement nominal explicable apres demarrage.

**Acceptance Criteria:**

**Given** un daemon `jeedom2ha` redemarre alors que des entites `jeedom2ha` existent deja dans HA
**When** le demarrage est termine et que les prerequis techniques minimaux du pont sont reunis
**Then** le registre runtime necessaire au gating commande est rehydrate automatiquement sans action manuelle utilisateur
**And** une commande HA sur une entite precedemment publiee/vivante reste rejetee tant que ce bootstrap n'est pas termine ou a echoue explicitement
**And** une fois le bootstrap termine, une commande valide sur une entite `jeedom2ha` execute bien Jeedom sans `/action/sync` manuel
**And** le bootstrap n'introduit ni purge globale broker, ni creation hors namespace, ni reactivation d'entite retiree
**And** le mecanisme reste borne au cas startup daemon et n'etend pas Epic 5

**Dev Notes (garde-fous):**

- Reutiliser les mecanismes existants de topologie/sync autant que possible; ne pas introduire de persistance lifecycle avancee.
- Le cache runtime sous `data/` reste technique et non autoritatif; Jeedom reste la source de verite.
- Le bootstrap doit etre idempotent et ne pas tourner en boucle sur chaque reconnect MQTT.
- En cas d'echec, comportement safe = rejet explicite + log runtime exploitable.

**Tests minimum (reels + tracabilite homogene):**

- Test reel 3.2b-A : restart daemon -> aucune action manuelle -> commande HA valide sur `eq_id=391` -> execution Jeedom + confirmation coherente.
- Test reel 3.2b-B : restart daemon -> entite retiree/non publiee -> rejet propre + aucun effet Jeedom.
- Test reel 3.2b-C : coexistence avec autre publisher MQTT pendant le bootstrap -> aucun topic hors namespace `jeedom2ha` touche.
```

**Rationale:**

- garde Story 3.2 intacte;
- rend explicite le trou startup/lifecycle strictement necessaire au nominal Epic 3;
- protege Story 3.3 d'un prerequis runtime encore implicite.

### 4.2 Positionnement roadmap / sprint

**Artifact:** `implementation-artifacts/sprint-status.yaml`

OLD:

```yaml
3-2-pilotage-ha-jeedom-avec-confirmation-honnete-detat: review
3-3-disponibilite-du-pont-et-des-entites-quand-linformation-est-fiable: backlog
```

NEW:

```yaml
3-2-pilotage-ha-jeedom-avec-confirmation-honnete-detat: review
3-2b-bootstrap-runtime-apres-restart-daemon: backlog
3-3-disponibilite-du-pont-et-des-entites-quand-linformation-est-fiable: backlog
```

**Rationale:**

- changement de sprint **modere mais cible**;
- pas de nouvel epic;
- simple insertion d'un bloqueur produit avant `3.3`.

### 4.3 Clarification architecture

**Artifact:** `planning-artifacts/architecture.md`

OLD:

```md
- `event::changes` sert aux etats incrementaux ; les changements de topologie exigent toujours une reconciliation / rescan.
```

NEW:

```md
- `event::changes` sert aux etats incrementaux ; les changements de topologie exigent toujours une reconciliation / rescan.
- Apres restart daemon, un bootstrap runtime one-shot peut reutiliser le mecanisme de reconciliation existant pour rehydrater le registre actif avant reprise nominale des commandes, sans introduire pour autant la persistance/republication avancee d'Epic 5.
```

**Rationale:**

- ancre explicitement le follow-up comme pont de startup borne;
- evite l'amalgame "startup bootstrap" = "Epic 5 complet".

### 4.4 Clarification project context / protocole reel

**Artifacts:** `project-context.md`, `jeedom2ha-test-context-jeedom-reel.md`

Ajouts recommandes:

- preflight reel additionnel: "restart daemon, ne pas lancer `/action/sync`, puis verifier qu'une commande HA valide sur l'entite de test reussit ou que l'echec est explicitement qualifie en attente bootstrap";
- preuve obligatoire avec logs `[SYNC-CMD]` et sequence absolue des etapes:
  1. restart daemon
  2. attendre status daemon + MQTT pret
  3. envoyer commande HA
  4. verifier log/Jeedom/HA

---

## Section 5 - Follow-up prete a transformer en story

### Titre recommande

`Bootstrap runtime apres restart daemon pour restaurer le pilotage sans sync manuel`

### Objectif

Garantir qu'apres redemarrage du daemon, le pont retrouve un registre runtime coherent pour les entites deja publiees, afin que le pilotage HA -> Jeedom redevienne nominal sans intervention manuelle `/action/sync`.

### Perimetre exact

- restaurer automatiquement le registre runtime necessaire au gating commande apres startup daemon;
- reutiliser autant que possible la topologie et le pipeline de sync existants;
- borner le comportement au **startup daemon** et, si necessaire, au **premier connect MQTT associe a ce startup**.

### Hors perimetre explicite

- persistance durable ou cache autoritatif en `data/`;
- republication lifecycle complete post-reboot daemon/HA/broker/Jeedom;
- lissage de charge evolue;
- renommage, remapping, reconciliation avancee, detection intelligente des ecarts;
- auto-resync sur chaque reconnexion MQTT en regime nominal.

### Acceptance Criteria minimales

1. **Given** le daemon redemarre et le pont retrouve ses prerequis minimaux, **When** le cycle de startup se termine, **Then** le registre runtime requis pour le gating commande est rehydrate automatiquement sans `/action/sync` manuel.
2. **Given** une entite `jeedom2ha` precedemment publiee et vivante, **When** une commande HA valide est envoyee apres restart daemon, **Then** elle est executee dans Jeedom avec la meme politique de confirmation honnete qu'en Story 3.2.
3. **Given** une entite retiree, inconnue ou non publiee, **When** une commande est envoyee apres restart, **Then** elle reste rejetee proprement sans effet Jeedom ni reactivation de ghost entity.
4. **Given** le bootstrap runtime n'est pas encore termine ou a echoue, **When** une commande arrive, **Then** le rejet est explicite et tracable, sans comportement implicite ni etat mensonger.
5. **Given** un autre publisher MQTT coexiste sur le broker, **When** le bootstrap s'execute, **Then** aucun topic hors namespace `jeedom2ha` n'est publie, supprime ou consomme.

### Garde-fous recommandes

- ne jamais contourner le gating `app["publications"]` + `active_or_alive`;
- ne jamais transformer ce follow-up en moteur de persistance Epic 5;
- ne pas lancer des bootstraps concurrents ou infinis;
- si le bootstrap reutilise `/action/sync`, le faire seulement dans une fenetre de startup bien bornee et idempotente;
- conserver la regle "publier moins mais correctement" en cas d'incertitude.

### Tests reels minimum

- **Test reel FU-A:** restart daemon, attendre reprise nominale, envoyer `ON` sur `jeedom2ha/391/set`, verifier `command_executed` puis confirmation coherente, sans `/action/sync` manuel.
- **Test reel FU-B:** restart daemon avec entite retiree/non publiee, verifier rejet propre et absence d'effet Jeedom.
- **Test reel FU-C:** restart daemon avec coexistence d'au moins un autre publisher MQTT, verifier qu'aucun topic externe n'est touche pendant bootstrap + commande.
- **Trace obligatoire:** preconditions, horodatage des etapes, logs runtime, observation broker, observation Jeedom, verdict.

### Risques de bord a surveiller

- bootstrap declenche avant MQTT connecte -> registre non hydrate ou non publiable;
- surpublication discovery inutile au demarrage;
- collisions ou consommation non voulue si le bootstrap elargit les topics/subscriptions;
- reactivation involontaire d'entites sorties du registre actif;
- masquage d'erreur par auto-retry silencieux.

---

## Section 6 - Qualification finale BMAD

### Diagnostic du probleme

Le probleme n'est pas une regression auth/commande de Story 3.2. C'est un **trou de bootstrap runtime post-restart daemon**: le gating commande est correct, mais il s'appuie sur un registre RAM alimente par `/action/sync` et non rehydrate au demarrage.

### Qualification de perimetre

- **Type:** bug follow-up cible
- **Epic:** `Epic 3`
- **Story map:** nouvelle story intermediaire `3.2b` (ou equivalent) avant `3.3`
- **Sprint change:** oui, mais **modere** et borne a un resequencement/backlog insertion; pas de replan majeur
- **Epic 5:** non, sauf si l'analyse d'implementation revele qu'on ne peut pas corriger sans persistance/republication avancee

### Recommandation BMAD nette

Traiter ce sujet comme un **follow-up produit/architecture de startup runtime dans Epic 3**, en creant une story dediee de bootstrap one-shot apres restart daemon. Ne pas reouvrir Story 3.2. Ne pas deplacer le sujet dans Epic 5 tant qu'aucune preuve n'impose une vraie persistance lifecycle avancee.

---

## Section 7 - Checklist de navigation (statut synthese)

### 1) Trigger & contexte

- [x] 1.1 Trigger identifie: validation terrain post-Story 3.2 sur restart daemon.
- [x] 1.2 Probleme defini: trou de bootstrap runtime au startup.
- [x] 1.3 Evidence: logs terrain + lecture code + artefacts projet.

### 2) Impact epics

- [x] 2.1 Epic courant encore viable avec follow-up cible.
- [x] 2.2 Changement epic: ajout d'une story dans Epic 3.
- [x] 2.3 Epic 5 examine: impact indirect seulement, pas de bascule necessaire.
- [x] 2.4 Pas de nouvel epic requis.
- [x] 2.5 Resequencement recommande: follow-up avant 3.3.

### 3) Conflits artefacts

- [x] 3.1 PRD: pas de conflit de fond; le follow-up reste compatible avec FR15/16/17 et n'anticipe pas abusivement FR9/Story 5.1.
- [x] 3.2 Architecture: clarification utile sur startup bootstrap borne.
- [N/A] 3.3 UX: pas de changement de parcours.
- [x] 3.4 Artefacts secondaires: protocole terrain et sprint-status a mettre a jour apres approbation.

### 4) Path forward

- [x] 4.1 Option 1 viable.
- [N/A] 4.2 Rollback non pertinent.
- [N/A] 4.3 MVP review non necessaire.
- [x] 4.4 Approche retenue: Option 1 (Direct Adjustment).

### 5) Proposal components

- [x] 5.1 Issue summary formalise.
- [x] 5.2 Epic impact et ajustements artefacts identifies.
- [x] 5.3 Recommandation et rationale formules.
- [x] 5.4 Action plan et dependances decrits.
- [!] 5.5 Handoff a confirmer apres validation utilisateur.

### 6) Final review

- [x] 6.1 Analyse complete et actionnable.
- [x] 6.2 Proposition coherente avec les artefacts existants.
- [!] 6.3 Approbation utilisateur a obtenir.
- [N/A] 6.4 `sprint-status.yaml` non modifie a ce stade (en attente d'approbation).
