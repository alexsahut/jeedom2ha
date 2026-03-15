# Sprint Change Proposal - Mise à jour ciblée Epic 3 (suite rétro Epic 2)

- Projet: `jeedom2ha`
- Date: `2026-03-14`
- Auteur: `Bob (Scrum Master)`
- Portée: `Stories 3.1 / 3.2 / 3.3 uniquement`
- Mode: `Batch`
- Déclencheur: rétro Epic 2 clôturée (`epic-2-retro-2026-03-14.md`)

---

## Section 1 - Issue Summary

### Problème identifié

La rétro Epic 2 confirme que le socle mapping/discovery est robuste, mais que le démarrage Epic 3 doit intégrer des garde-fous pour éviter d'amplifier en runtime:

- les faux positifs de publication;
- les doublons/collisions en environnement HA déjà peuplé;
- les ghost entities liées au cycle retained/discovery;
- les incohérences de disponibilité bridge vs entités.

### Contrainte de navigation

- Ne pas changer le périmètre fonctionnel d'Epic 3.
- Ne pas déplacer dans Epic 3 les sujets explicitement cadrés Epic 4:
  - exclusions multicritères;
  - politique de confiance configurable.

---

## Section 2 - Impact Analysis

### Impact Epic

- Epic impacté: `Epic 3` (3 stories).
- Épics non impactés en périmètre: Epic 1/2 (historique), Epic 4 (reste propriétaire des évolutions diagnostic/exclusions/politique configurable), Epic 5 inchangé.

### Impact artefacts

- **À mettre à jour**: `planning-artifacts/epics.md` (sections Story 3.1, 3.2, 3.3).
- **Pas de conflit bloquant PRD**: aligné avec FR15/16/17/20/22/24/25, NFR1/7/8/10/15/16/18.
- **Architecture**: renforcement des règles déjà présentes (namespace strict, lifecycle propre, `event::changes` pour l'incrémental, suppression exacte discovery).
- **UX**: pas de changement de parcours; seulement ajout de traçabilité test/diagnostic runtime.

### Impact technique

- Ajout de garde-fous d'exécution (gating sur entités publiées/vivantes, cleanup topic exact).
- Renforcement des tests d'intégration réels (box Jeedom + broker MQTT + HA).
- Uniformisation de la preuve de validation story par story.

---

## Section 3 - Recommended Approach

### Option retenue

`Option 1 - Direct Adjustment` (modification ciblée des AC + ajout Dev Notes + ajout tests minimum sur 3.1/3.2/3.3).

### Rationale

- Effort: `Medium`
- Risque: `Low-Medium`
- Impact planning: limité, sans replan global
- Bénéfice: sécurise le runtime Epic 3 sans glisser les responsabilités Epic 4.

### Alternatives écartées

- Rollback Epic 2: non pertinent (le socle est valide).
- MVP review/réduction: non nécessaire, le périmètre reste inchangé.

---

## Section 4 - Detailed Change Proposals

## 4.1 Story 3.1 - Synchronisation incrémentale des états Jeedom -> HA

### Diff fonctionnelle (OLD -> NEW)

**Section: Acceptance Criteria**

OLD:
- **Given** des équipements sont déjà publiés dans HA
- **When** un changement d'état survient dans Jeedom (via `event::changes`)
- **Then** le démon Python détecte le changement pour la commande mappée
- **And** le démon déclenche une publication MQTT vers le `state_topic` correspondant
- **And** la latence cible est proche de 1s, et acceptable ≤ 2s en contexte nominal sur le périmètre V1

NEW:
- **Given** des équipements sont publiés dans HA par `jeedom2ha` et marqués vivants dans le registre runtime
- **When** un changement d'état survient dans Jeedom (via `event::changes`)
- **Then** le démon ne traite que les commandes reliées à des entités réellement publiées et vivantes
- **And** le démon ignore (avec trace runtime exploitable dans les logs) tout événement lié à une entité non publiée, exclue, supprimée ou non vivante
- **And** le démon publie l'état uniquement sur le `state_topic` de l'entité `jeedom2ha` correspondante, sans interaction avec les topics d'autres publishers
- **And** la latence cible reste proche de 1s, acceptable ≤ 2s en contexte nominal sur le périmètre V1
- **And** la synchro incrémentale n'amplifie pas les faux positifs de mapping: aucune nouvelle entité n'est créée par le flux d'état
- **And** lorsqu'une entité sort du registre actif via un mécanisme existant, le cleanup discovery est fait via payload vide retained sur le topic discovery exact de l'entité concernée (pas de purge globale broker)

**Section: Dev Notes (NEW)**

- Source de vérité runtime obligatoire: registre des entités publiées/vivantes avant toute publication d'état.
- `event::changes` sert à synchroniser des entités déjà valides, jamais à inférer/créer de nouvelles entités.
- Toute publication d'état doit rester strictement dans le namespace `jeedom2ha`.
- Cleanup lifecycle: suppression ciblée par topic discovery exact (`homeassistant/<entity_type>/jeedom2ha_<id>/config`), jamais "vider le broker".

**Section: Tests minimum (NEW)**

- Test réel 3.1-A: box Jeedom + broker + HA avec coexistence d'au moins un autre publisher MQTT; vérifier qu'aucun topic externe n'est touché.
- Test réel 3.1-B: événement sur entité non publiée/non vivante -> aucun publish `state_topic`, trace runtime exploitable dans les logs.
- Test réel 3.1-C: retrait d'une entité publiée -> payload vide retained sur topic discovery exact, disparition HA sans ghost.
- Traçabilité homogène: preuves obligatoires par story (commande lancée, extraits logs, topics observés, verdict).

**Justification courte**

Empêche que la synchro temps réel propage du bruit (faux positifs/ghosts) et garantit une coexistence propre en environnement HA hétérogène.

---

## 4.2 Story 3.2 - Pilotage HA -> Jeedom avec confirmation honnête d'état

### Diff fonctionnelle (OLD -> NEW)

**Section: Acceptance Criteria**

OLD:
- **Given** un actionneur est disponible dans HA
- **When** j'envoie une commande (ON/OFF, position, niveau, etc.) depuis HA
- **Then** le démon écoute le `command_topic` MQTT et traduit l'ordre
- **And** l'ordre est transmis à Jeedom via l'interface standard retenue par l'architecture (API Jeedom)
- **And** le plugin privilégie la confirmation par état réel quand elle existe
- **And** pour les commandes sans retour fiable, il applique la politique prévue (optimiste contrôlé ou action stateless), sans comportement mensonger

NEW:
- **Given** un actionneur est publié par `jeedom2ha`, vivant, et autorisé au pilotage
- **When** une commande (ON/OFF, position, niveau, etc.) est reçue sur son `command_topic`
- **Then** le démon traduit l'ordre et l'exécute via l'interface Jeedom standard
- **And** le démon rejette (avec trace runtime exploitable dans les logs) toute commande visant une entité non publiée, non vivante, inconnue ou retirée
- **And** le plugin privilégie la confirmation par état réel quand elle existe, sans publier d'état mensonger
- **And** pour les commandes sans retour fiable, il applique la politique prévue (optimiste contrôlé/stateless) de manière explicable et traçable
- **And** le traitement des commandes reste strictement borné aux topics `jeedom2ha`, sans collision avec d'autres publishers/integrations HA
- **And** aucune commande ne réactive une ghost entity: une entité retirée doit rester non pilotable tant qu'elle n'est pas republiée proprement

**Section: Dev Notes (NEW)**

- Gating commande: résolution `entity_id/topic -> publication registry` avant exécution.
- Rejet explicite des commandes hors registre actif avec code raison runtime dans les logs.
- Anti-boucle: séparer clairement flux commande et flux confirmation d'état.
- Ne jamais créer/modifier des entités discovery depuis le flux de commande.

**Section: Tests minimum (NEW)**

- Test réel 3.2-A: commande HA valide sur entité publiée/vivante -> exécution Jeedom + confirmation cohérente.
- Test réel 3.2-B: commande vers entité supprimée/non publiée -> rejet propre + aucun effet Jeedom + preuve log.
- Test réel 3.2-C: coexistence avec autre publisher (topic voisin) -> aucune consommation/effet hors namespace `jeedom2ha`.
- Traçabilité homogène: matrice preuve standard (préconditions, commande, observation broker, observation Jeedom, verdict).

**Justification courte**

Évite les effets de bord et protège la cohérence runtime: seules les entités réellement vivantes peuvent être pilotées.

---

## 4.3 Story 3.3 - Disponibilité du pont et des entités quand l'information est fiable

### Diff fonctionnelle (OLD -> NEW)

**Section: Acceptance Criteria**

OLD:
- **Given** le pont est en service
- **When** l'état de connectivité change (pont ou équipement)
- **Then** le plugin expose une disponibilité cohérente pour le pont via le LWT global
- **And** le plugin expose une disponibilité pour les entités quand une information fiable d'indisponibilité existe côté Jeedom
- **And** en cas d'arrêt du pont ou de perte de connectivité broker, les entités concernées sont marquées indisponibles
- **And** le plugin distingue l'indisponibilité du pont (problème global) d'une indisponibilité propre à un équipement (problème local) quand l'info est disponible

NEW:
- **Given** le pont `jeedom2ha` est en service avec LWT global actif
- **When** l'état de connectivité change (bridge, broker, ou équipement)
- **Then** le plugin expose une disponibilité bridge cohérente via LWT global et la reflète sur les entités gérées
- **And** la disponibilité entité est publiée uniquement pour des entités réellement publiées et vivantes
- **And** en cas d'arrêt du pont ou de perte broker, les entités `jeedom2ha` concernées passent indisponibles de manière cohérente
- **And** le plugin distingue indisponibilité globale (bridge) et locale (entité) quand l'information fiable existe
- **And** la gestion lifecycle évite les ghost entities: lorsqu'une entité sort du registre actif via un mécanisme existant, un payload vide retained est publié sur son topic discovery exact
- **And** le plugin n'altère jamais les retained discovery d'autres intégrations/publishers MQTT

**Section: Dev Notes (NEW)**

- Disponibilité = combinaison de l'état bridge + état registre entités vivantes.
- Cleanup lifecycle strict: suppression ciblée par topic exact, jamais purge générique.
- Conserver séparation explicite entre "indisponible" et "supprimé".

**Section: Tests minimum (NEW)**

- Test réel 3.3-A: arrêt/redémarrage bridge -> transitions availability bridge + entités conformes.
- Test réel 3.3-B: perte/rétablissement broker -> comportement availability cohérent sans créations fantômes.
- Test réel 3.3-C: suppression d'une entité publiée -> cleanup topic exact retained + disparition HA sans toucher aux entités non-jeedom2ha.
- Traçabilité homogène: même format de preuve que 3.1/3.2, archivé dans les stories.

**Justification courte**

Garantit un lifecycle propre et évite les ghost entities, tout en rendant la disponibilité fiable et compréhensible.

---

## Section 5 - Implementation Handoff

### Classification de scope

`Moderate` (réécriture ciblée des stories + validations runtime réelles + ajustements backlog Epic 3).

### Handoff recommandé

- **PO/SM**: intégrer les reformulations AC/Dev Notes/Tests dans Epic 3.
- **Dev**: implémenter les garde-fous runtime sans élargir le périmètre fonctionnel.
- **QA**: exécuter et tracer les tests réels homogènes (box Jeedom + broker + HA).
- **Architect**: valider l'alignement lifecycle retained/coexistence avec l'architecture existante.

### Critères de succès d'implémentation

1. Aucune interaction hors namespace/topics `jeedom2ha`.
2. Aucune commande/synchro sur entité non publiée/non vivante.
3. Cleanup discovery uniquement par topic exact, sans purge globale broker.
4. Zéro ghost entity en scénarios de suppression/exclusion/republication.
5. Dossier de preuves homogène sur 3.1/3.2/3.3.

---

## Checklist de navigation (statut synthèse)

### 1) Trigger & contexte

- [x] 1.1 Trigger identifié: rétro Epic 2 clôturée.
- [x] 1.2 Problème défini: garde-fous runtime manquants avant Epic 3.
- [x] 1.3 Évidence: constats rétro + validations terrain + risques résiduels documentés.

### 2) Impact épics

- [x] 2.1 Epic courant peut être mené avec ajustements ciblés.
- [x] 2.2 Changement épic: modification de contenu stories 3.1/3.2/3.3 uniquement.
- [x] 2.3 Épics futurs revus: Epic 4 inchangé sur ses responsabilités.
- [x] 2.4 Pas de nouvel epic requis.
- [x] 2.5 Ordonnancement global inchangé.

### 3) Conflits artefacts

- [x] 3.1 PRD: aligné, pas de conflit de fond.
- [x] 3.2 Architecture: renforcement de règles existantes.
- [x] 3.3 UX: impact mineur, pas de redesign.
- [x] 3.4 Artefacts secondaires: stratégie de test et traçabilité à homogénéiser.

### 4) Path forward

- [x] 4.1 Option 1 viable.
- [N/A] 4.2 Rollback non pertinent.
- [N/A] 4.3 PRD MVP review non nécessaire.
- [x] 4.4 Approche retenue: Option 1 (Direct Adjustment).

### 5) Proposal components

- [x] 5.1 Issue summary
- [x] 5.2 Impact analysis
- [x] 5.3 Recommended path
- [x] 5.4 Action plan
- [x] 5.5 Handoff plan

### 6) Final review & handoff

- [x] 6.1 Checklist complétée
- [x] 6.2 Proposition cohérente
- [!] 6.3 Approbation explicite utilisateur requise avant application dans `epics.md`
- [N/A] 6.4 `sprint-status.yaml` inchangé (aucun ajout/suppression/renumérotation approuvés à ce stade)
- [x] 6.5 Plan de handoff défini

---

## Résumé exécution

- Issue traitée: sécurisation Epic 3 suite rétro Epic 2
- Scope: `Moderate`
- Artefacts à modifier après approbation: `planning-artifacts/epics.md` (stories 3.1/3.2/3.3)
- Routage: PO/SM + Dev + QA + Architect
