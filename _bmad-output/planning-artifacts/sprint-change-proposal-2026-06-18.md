---
type: sprint-change-proposal
project: jeedom2ha
phase: cycle_moteur_projection_explicable
date: 2026-06-18
status: approved
scope_classification: moderate
trigger: gate-terrain-revele-entites-publiees-sans-valeur-runtime-et-pe-epic-11-non-formalise
mode: batch
communication_language: french
proposed_by: clawcode
impacts_if_approved:
  - _bmad-output/planning-artifacts/prd.md (Feature 9 + FR46-FR50 + NFR13 — nouveau)
  - _bmad-output/planning-artifacts/epics-projection-engine.md (formalisation pe-epic-11 + ajout pe-epic-12)
  - _bmad-output/implementation-artifacts/sprint-status.yaml (header cycle + bloc pe-epic-12 + story 12-1)
no_change_documented:
  - _bmad-output/planning-artifacts/architecture-projection-engine.md (le streaming runtime est une capacité parallèle au pipeline 5 étapes, pas une modification du contrat de projection)
  - resources/daemon/* (aucun code modifié par cette proposition — implémentation = stories à venir)
references:
  - _bmad-output/planning-artifacts/backlog-icebox.md §3 (inventaire énergie/routage solaire)
  - _bmad-output/planning-artifacts/sprint-change-proposal-2026-06-17.md (Story 11.1 gate terrain + 11.1.bis)
  - _bmad-output/planning-artifacts/epics.md (legacy : FR16 « Retour d'état » / FR17 « Synchro temps réel » de l'Epic 3 d'origine)
  - core/php/jeedom2ha.php L25 (callback stub — « daemon → Jeedom events, state updates out of scope, later story »)
  - session transcript 2026-06-18 (diagnostic « tension réseau » eq553 — capteurs en état inconnu sur la box réelle)
---

# Sprint Change Proposal 2026-06-18 — Restitution d'état runtime (pe-epic-12) + formalisation de pe-epic-11 dans le contrat de planification

## 1. Issue Summary

### Trigger

Deux constats liés, révélés en validation terrain pe-epic-11 :

1. **Entités publiées sans valeur (bug produit révélé).** Dans Home Assistant, l'équipement
   « tension réseau » (msunPV/RouteurSolaire eq553, 65 capteurs publiés par Story 11.1) apparaît
   avec **tous ses capteurs en état « inconnu »**. La discovery MQTT est correcte (les entités
   existent), mais **aucune valeur runtime ne remonte de Jeedom vers HA**.

2. **pe-epic-11 n'est pas clairement identifié dans le contrat de planification.** L'epic
   « Énergie / Routage solaire » est suivi dans `sprint-status.yaml` (in-progress, stories 11.1 et
   11.1.bis) mais **absent de `epics-projection-engine.md`** — ni dans la « Liste des epics »
   (qui s'arrête à `### Epic 10`), ni dans les sections détaillées (qui s'arrêtent à
   `## Epic 10` / `Gates epic-level pe-epic-10`). L'epic existe dans le suivi mais n'a pas de
   définition formelle (valeur utilisateur, FRs couverts, gates).

### Evidence

- **Terrain (2026-06-18).** Sur la box réelle, broker MQTT : les 65 topics discovery
  `homeassistant/sensor/jeedom2ha_553_<cmd>/config` sont présents et retained, mais **0 message**
  sur les `state_topic` `jeedom2ha/553/<cmd>/state` → HA affiche `unknown`.
- **Code.** `resources/daemon/sync/` ne contient que `command.py` (chemin HA → Jeedom) ; **aucun
  `state.py`** (chemin Jeedom → HA). `core/php/jeedom2ha.php` L25 est un stub HTTP 200 dont le
  commentaire dit explicitement : *« Full callback logic (daemon → Jeedom events, state updates) is
  out of scope for Story 1.1 and will be implemented in a later story. »* `http_server.py` n'expose
  aucune route de publication de valeur runtime.
- **Audit BMAD.** La restitution d'état était une exigence produit d'origine — `epics.md` (legacy)
  mappe **FR16 « Retour d'état »** et **FR17 « Synchro temps réel »** sur l'Epic 3 historique. Cette
  capacité a été tentée puis abandonnée au cycle « V1.1 Pilotable » (le `StateSynchronizer` n'existe
  que sous forme de fakes de test), puis **explicitement hors-scope** du cycle « Moteur de projection
  explicable » (dont le contrat s'arrête à l'étape 5 = publication de la **discovery**, pas des
  **valeurs**). Elle n'a été re-planifiée nulle part. La régression est donc **systémique** (toutes
  les entités publiées, pas seulement msunPV) — eq553 l'a simplement rendue visible.

> Note d'attribution importante : la valeur runtime manquante **n'est pas un défaut de Story 11.1**.
> Story 11.1 a correctement publié la discovery (son périmètre). Le streaming de valeur est une
> capacité distincte jamais ouverte dans ce cycle.

## 2. Impact Analysis

### Epic Impact

- **pe-epic-11 (Énergie / Routage solaire)** — non modifié dans son scope, mais **formalisé** dans
  `epics-projection-engine.md` pour combler l'absence de définition (problème 2). Son travail reste
  valide ; il publie de la discovery lecture seule, ce qui est conforme.
- **pe-epic-12 (Restitution d'état runtime Jeedom → HA)** — **NOUVEL epic**. Capacité produit
  manquante qui donne enfin un foyer aux valeurs runtime. Pré-requis : pe-epic-11 (les entités
  cibles doivent exister en discovery avant de pouvoir être alimentées).

### Story Impact

| Story | État avant | État après |
|---|---|---|
| 11.1 — MSunPV sensors lecture seule | review | inchangé (discovery correcte, hors-scope valeur) |
| 11.1.bis — Multi-sensor lifecycle | review | inchangé |
| **12.1 — Streaming valeur sensor / binary_sensor (vague 1)** | n'existe pas | **NOUVELLE** (backlog) via create-story |

### Artifact Conflicts

- **`prd.md`** : aucune FR ne couvre la restitution d'état runtime (FR1-FR45 décrivent le pipeline
  projection → discovery). Ajout d'une **Feature 9** + **FR46-FR50** + **NFR13**.
- **`epics-projection-engine.md`** : ajout de pe-epic-11 (formalisation) et pe-epic-12 (nouveau)
  dans la « Liste des epics », les sections détaillées, la carte de couverture FR, et la note de
  cycle d'en-tête.
- **`sprint-status.yaml`** : header de cycle à étendre (mention pe-epic-12) + bloc pe-epic-12 +
  story 12-1 en backlog. pe-epic-11 y est **déjà** présent (lignes 222-235) — pas de changement de
  statut, on note seulement qu'il est désormais formalisé côté epics.
- **`architecture-projection-engine.md`** : **aucun changement**. Le streaming runtime est une
  capacité parallèle au pipeline de projection (il consomme les `state_topic` déjà déclarés en
  étape 5), il ne modifie pas le contrat des 5 étapes. L'architecture du chemin de valeur sera
  cadrée au démarrage de pe-epic-12 (callback PHP + `sync/state.py` + route daemon).

### Technical Impact

- Aucun code modifié par cette proposition (planification pure).
- Implémentation pressentie pour pe-epic-12 (à cadrer en story, non engagée ici) :
  `core/php/jeedom2ha.php` (callback réel daemon ↔ Jeedom), nouveau `resources/daemon/sync/state.py`,
  route de publication de valeur dans `transport/http_server.py`, publication sur les `state_topic`
  déjà émis par la discovery.

## 3. Recommended Approach

**Direct Adjustment** — pas de rollback, pas de réduction de MVP.

1. **Formaliser pe-epic-11** dans `epics-projection-engine.md` (corrige le déficit de traçabilité :
   l'epic suivi mais non défini). Aucun impact sur le travail déjà livré.
2. **Ouvrir pe-epic-12** comme epic dédié à la restitution d'état runtime, en cohérence avec le choix
   utilisateur : **MVP = `sensor` + `binary_sensor` d'abord, extension par vagues gouvernées ensuite**
   (les domaines actionnables `switch`/`climate` viennent après). C'est la matérialisation de
   l'ancien besoin FR16/FR17 dans le formalisme du cycle courant.
3. **Mettre à jour le PRD** avec une Feature 9 et les FR46-FR50 + NFR13, pour que la capacité ait un
   ancrage d'exigence avant toute story.

- **Effort** : planification = cette proposition. pe-epic-12 story 1 = M/L (chemin de valeur neuf :
  callback PHP + daemon + tests + gate terrain « les capteurs eq553 ne sont plus `unknown` »).
- **Risque** : moyen (nouveau chemin de données bidirectionnel), borné par une vague 1 sensor/binary.
- **Timeline** : aucune dérive sur pe-epic-11 ; pe-epic-12 s'insère après clôture de pe-epic-11.

## 4. Detailed Change Proposals

### 4.1 — `prd.md` : nouvelle Feature 9 (après FR45, avant « Dépendances entre features »)

```
NEW (insérer après la ligne FR45 / fin Feature 8) :

### Feature 9 — Restitution d'état runtime Jeedom → Home Assistant

- FR46: Le système peut publier vers Home Assistant la valeur d'état runtime de chaque commande info d'un équipement publié, sur le `state_topic` déclaré lors de la publication discovery (étape 5).
- FR47: Le système peut alimenter l'état d'une entité HA à sa publication (état initial) puis à chaque changement de valeur côté Jeedom (event-driven), sans dépendre d'un resync complet.
- FR48: L'utilisateur peut distinguer une entité « publiée mais sans valeur » (discovery présente, état `unknown`) d'une entité « publiée et alimentée » dans le diagnostic.
- FR49: Le système peut restituer en priorité l'état des types `sensor` et `binary_sensor` (vague 1) ; les autres domaines (`switch`, `climate`, …) sont ajoutés par vagues ultérieures gouvernées.
- FR50: Le système ne publie une valeur d'état que pour des entités effectivement publiées en discovery (cohérence state ⊆ discovery), sans créer de topic d'état orphelin.
```

```
NEW (ajouter dans « Dépendances entre features », après la ligne Feature 8) :

- **Feature 9** dépend des Features **0 à 5** ; la restitution d'état n'alimente que des `state_topic` déjà déclarés par la publication discovery. Elle est parallèle au pipeline de projection (ne réordonne ni ne revalide les 5 étapes).
```

```
NEW (section « Exigences non fonctionnelles », après NFR12) :

- NFR13: La restitution d'état doit être event-driven et n'introduire aucune source de vérité métier concurrente à Jeedom (cohérent NFR6) ; 100% des valeurs publiées proviennent d'une commande info Jeedom d'une entité déjà publiée en discovery.
```

### 4.2 — `epics-projection-engine.md`

**(a) Carte de couverture FR (après la ligne `| FR31-FR35 | Epic 6 | … |`) :**

```
NEW :
| FR46-FR50 | pe-epic-12 | Feature 9 — Restitution d'état runtime Jeedom → HA |
```

**(b) « Liste des epics » — ajouter après le bloc `### Epic 10 …` (avant le `---` ligne 424) :**

```
NEW :

### Epic 11 — L'énergie et le routage solaire deviennent lisibles dans Home Assistant via une restitution discovery gouvernée

**Valeur utilisateur :** L'utilisateur retrouve dans Home Assistant les équipements de pilotage solaire déjà présents dans Jeedom (MSunPV/RouteurSolaire, chauffe-eau), pour un dashboard énergie famille, sans ouvrir de nouveau type HA ni contourner le moteur.

**Résultat observable :** Les commandes info des équipements énergie/routage (eq553, eq554) sont projetées en `sensor` / `binary_sensor` via le pipeline existant. La priorisation suit le besoin réel (P1 MSunPV, P2 chauffe-eau), pas un type arbitraire.

**FRs couverts :** FR7, FR11, FR16, FR26, FR31, FR39, FR40 (réutilisation du pipeline existant — aucun type nouveau)

**ARs clés :** AR4, AR6, AR13

**NFRs directement adressés :** NFR2, NFR5, NFR10

**Invariants à porter en stories :**
- `sensor`, `binary_sensor`, `button`, `switch` sont déjà dans `PRODUCT_SCOPE` : pe-epic-11 n'ouvre aucun type nouveau ;
- la restitution est en lecture seule (discovery) ; la valeur runtime relève de pe-epic-12 et n'est pas un défaut de cet epic ;
- la dépublication d'un équipement multi-sensor doit nettoyer tous les topics secondaires (cf. Story 11.1.bis) ;
- l'inventaire cible reste borné par `backlog-icebox.md §3` ; aucune ouverture de l'intégration Enphase native HA (hors scope jeedom2ha).

### Epic 12 — Les entités publiées portent leurs valeurs réelles : restitution d'état runtime Jeedom → Home Assistant

**Valeur utilisateur :** L'utilisateur voit dans Home Assistant les valeurs réelles de ses entités (et non « inconnu ») : un capteur publié affiche sa mesure, un binary_sensor son état, mis à jour quand Jeedom change.

**Résultat observable :** Pour les types de la vague 1 (`sensor`, `binary_sensor`), chaque entité publiée en discovery reçoit un état initial puis des mises à jour event-driven sur son `state_topic`. Le diagnostic distingue « publié sans valeur » de « publié et alimenté ».

**FRs couverts :** FR46, FR47, FR48, FR49, FR50

**ARs clés :** à cadrer au démarrage de l'epic (chemin de valeur : callback PHP, `sync/state.py`, route daemon) — additif au contrat des 5 étapes, sans le modifier.

**NFRs directement adressés :** NFR6, NFR13

**Invariants à porter en stories :**
- la restitution n'alimente que des `state_topic` déjà déclarés par la publication discovery (cohérence state ⊆ discovery) ;
- event-driven, sans source de vérité concurrente à Jeedom (NFR6/NFR13) ;
- vague 1 = `sensor` + `binary_sensor` ; les domaines actionnables (`switch`, `climate`, …) sont des vagues ultérieures gouvernées ;
- gate terrain de clôture = les capteurs eq553 (« tension réseau ») ne sont plus en état `unknown` sur la box réelle.
```

**(c) Sections détaillées — ajouter après `### Gates epic-level pe-epic-10` (fin de fichier, après ligne 1788) :**

```
NEW :

---

## Epic 11 — Énergie / Routage solaire : restitution discovery lecture seule des équipements de pilotage solaire

L'utilisateur dispose dans HA des équipements énergie/routage solaire de Jeedom, projetés en lecture seule via le pipeline existant. Priorité : P1 MSunPV/RouteurSolaire (eq553, le « cerveau » du routage), P2 chauffe-eau (eq554). Aucun type HA nouveau : `sensor`/`binary_sensor`/`button`/`switch` sont déjà ouverts. Source d'inventaire : `backlog-icebox.md §3`.

### Story 11.1 — MSunPV / RouteurSolaire : sensors lecture seule
(livrée — multi-sensor eq553, 65 capteurs, gate terrain PASS box 192.168.1.21 ; Fix A éligibilité sans generic_type ; voir record `11-1-...md`)

### Story 11.1.bis — Multi-sensor lifecycle : dépublication exhaustive des sensors secondaires
(livrée — anti-ghosts HA, nettoyage des topics secondaires à la dépublication ; voir SCP 2026-06-17)

### Story 11.2 (réservée) — Chauffe-eau eq554 : détail routage
Réservée (P2). Inventaire `backlog-icebox.md §3.2`. Inclut le diagnostic du `switch.jeedom2ha_554` en état `unknown` — à traiter en lien avec pe-epic-12 (valeur runtime), pas comme une ouverture de type.

### Gates epic-level pe-epic-11
- aucune ouverture de type nouveau dans `PRODUCT_SCOPE` (les 4 types nécessaires sont déjà ouverts) ; toute exception passe FR40/NFR10 dans le même incrément ;
- la dépublication d'un équipement multi-sensor ne laisse aucun topic discovery secondaire orphelin (hérité de Story 11.1.bis) ;
- gate terrain de clôture epic = comptage des équipements énergie publiés sur la box réelle, périmètre conforme à `backlog-icebox.md §3` ;
- la restitution de valeur runtime est explicitement hors-scope de cet epic (relève de pe-epic-12).

---

## Epic 12 — Restitution d'état runtime Jeedom → Home Assistant : les entités publiées portent leurs valeurs réelles

Capacité produit comblant la régression systémique révélée le 2026-06-18 (entités publiées en discovery mais en état `unknown` faute de chemin de valeur Jeedom → HA). Reprend l'intention des anciennes FR16 « Retour d'état » / FR17 « Synchro temps réel » (legacy `epics.md`), abandonnées entre cycles, dans le formalisme courant. Vague 1 bornée : `sensor` + `binary_sensor`.

### Story 12.1 — Streaming de valeur sensor / binary_sensor (vague 1)
À créer (create-story). Brief de scope : établir le chemin de valeur Jeedom → HA (callback PHP réel + `resources/daemon/sync/state.py` + publication sur les `state_topic` déjà émis par la discovery), publier l'état initial à la publication puis les changements event-driven, pour les types `sensor` et `binary_sensor` uniquement. Gate terrain : les capteurs eq553 (« tension réseau ») affichent une valeur réelle dans HA (plus aucun `unknown` pour les commandes info alimentées).

### Gates epic-level pe-epic-12
- cohérence state ⊆ discovery : 0 `state_topic` publié pour une entité non publiée en discovery ;
- event-driven, aucune source de vérité concurrente à Jeedom (NFR6/NFR13) ;
- vague 1 strictement bornée `sensor` + `binary_sensor` ; ouverture des domaines actionnables différée à des vagues ultérieures gouvernées ;
- gate terrain de clôture epic = sur la box réelle, les capteurs eq553 ne sont plus en état `unknown` ; non-régression de la discovery existante.
```

### 4.3 — `sprint-status.yaml`

**(a) Note de cycle (bloc commentaire lignes 42-51) — étendre la portée :**

```
OLD:
#   Epics: pe-epic-1 à pe-epic-11 (post correct-courses 2026-04-30 puis 2026-06-07 :
#          pe-epic-1/2/3/4/5/6/7/8/9/10 done, pe-epic-11 backlog)

NEW:
#   Epics: pe-epic-1 à pe-epic-12 (post correct-courses 2026-04-30, 2026-06-07, 2026-06-18 :
#          pe-epic-1..10 done, pe-epic-11 in-progress, pe-epic-12 backlog)
#          pe-epic-11 formalisé dans epics-projection-engine.md le 2026-06-18 (était suivi ici sans définition d'epic)
#          pe-epic-12 = restitution d'état runtime Jeedom → HA (Feature 9 / FR46-FR50), vague 1 sensor+binary_sensor
```

**(b) Ajouter un bloc pe-epic-12 après la ligne 235 (fin du bloc pe-epic-11) :**

```
NEW:

  # ==============================================================
  # pe-epic-12 — Restitution d'état runtime Jeedom → Home Assistant
  # Ajouté par correct-course 2026-06-18 — comble la régression systémique
  # « entités publiées mais en état unknown » (chemin de valeur Jeedom → HA absent)
  # Reprend l'intention legacy FR16/FR17 dans le formalisme du cycle courant
  # PRD : Feature 9 / FR46-FR50 / NFR13
  # Vague 1 bornée : sensor + binary_sensor (domaines actionnables = vagues ultérieures)
  # Gate terrain de clôture = capteurs eq553 « tension réseau » non plus en état unknown
  # ==============================================================
  pe-epic-12: backlog  # restitution d'état runtime Jeedom → HA — pré-requis pe-epic-11
  12-1-streaming-valeur-sensor-binary-sensor-vague-1: backlog  # create-story à venir — chemin de valeur callback PHP + sync/state.py + state_topic ; gate terrain eq553 non-unknown
```

## 5. Implementation Handoff

- **Scope classification : Moderate** — réorganisation/formalisation du backlog (ajout pe-epic-12,
  formalisation pe-epic-11) + mise à jour PRD additive. Pas de replan fondamental, pas de rollback.
- **Handoff** :
  - PRD / epics → mise à jour documentaire additive (cette proposition, après approbation).
  - Story 12.1 → create-story (SM) puis dev-story, avec cadrage architecture du chemin de valeur au
    démarrage de l'epic.
  - pe-epic-11 → poursuit son cours (11.1 / 11.1.bis en review).
- **Success criteria** :
  - pe-epic-11 dispose d'une définition formelle dans `epics-projection-engine.md` (liste + section
    détaillée + gates + carte FR) ;
  - pe-epic-12 existe avec FRs PRD (FR46-FR50 + NFR13) et une story 12.1 en backlog ;
  - gate terrain pe-epic-12 (futur) : les capteurs eq553 affichent des valeurs réelles dans HA.
