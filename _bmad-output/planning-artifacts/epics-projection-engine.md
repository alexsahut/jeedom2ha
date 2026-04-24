---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture-projection-engine.md'
  - '_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md'
  - '_bmad-output/planning-artifacts/epic-5-lifecycle-matrix.md'
workflowType: 'epic_planning'
workflow: 'create-epics-and-stories'
project: 'jeedom2ha'
phase: 'cycle_moteur_projection_explicable'
date: '2026-04-10'
status: 'complete'
---

# jeedom2ha — Décomposition en Epics et Stories
## Cycle : Moteur de projection explicable

Ce document décompose les exigences du PRD final, de l'architecture du moteur de projection et de la revue de delta en epics et stories. Il constitue le contrat de planification pour le cycle **moteur de projection explicable**.

---

## Inventaire des exigences

### Exigences fonctionnelles

**Feature 0 — Contrat global du pipeline**

FR1: L'utilisateur peut s'appuyer sur un pipeline canonique à 5 étapes pour toute décision de projection.
FR2: Le système peut évaluer chaque équipement dans un ordre stable : éligibilité, mapping candidat, validation HA, décision de publication, publication MQTT.
FR3: Le système peut arrêter l'évaluation à la première étape bloquante et retenir cette étape comme cause principale canonique.
FR4: Le système peut restituer, pour chaque équipement, l'étape la plus avancée atteinte dans le pipeline.
FR5: Le mainteneur peut relier une décision de projection à ses entrées source, à son résultat intermédiaire et à son résultat final.

**Feature 1 — Étape 1 : Éligibilité**

FR6: L'utilisateur peut définir le périmètre d'éligibilité via les règles de scope existantes du produit.
FR7: Le système peut déterminer si un équipement est éligible avant tout mapping.
FR8: Le système peut distinguer un équipement inéligible d'un équipement éligible mais non projetable.
FR9: Le système peut classer les causes d'inéligibilité dans des catégories distinctes et stables.
FR10: L'utilisateur peut consulter, pour tout équipement exclu avant le début du mapping, un diagnostic qui indique l'étape 1 comme point de blocage, le motif d'exclusion canonique et, lorsque l'exclusion relève d'un choix utilisateur, l'action de scope applicable.

**Feature 2 — Étape 2 : Mapping candidat**

FR11: Le système peut produire un candidat de projection HA à partir d'un équipement Jeedom éligible.
FR12: Le système peut exprimer le niveau de confiance associé à un candidat de mapping.
FR13: Le système peut signaler qu'aucun mapping exploitable n'a pu être produit pour un équipement pourtant éligible.
FR14: L'utilisateur peut distinguer un échec de mapping d'un refus ultérieur du pipeline.
FR15: Le mainteneur peut faire évoluer les règles de mapping sans modifier l'ordre canonique des étapes.

**Feature 3 — Étape 3 : Validation HA obligatoire**

FR16: Le système peut vérifier qu'un candidat de projection satisfait les contraintes structurelles du composant HA cible avant toute publication.
FR17: Le système peut identifier les informations manquantes ou incompatibles qui empêchent une projection HA valide.
FR18: L'utilisateur peut voir qu'un équipement a été compris par le moteur mais rejeté parce que la projection HA serait invalide.
FR19: Le système peut refuser explicitement toute publication lorsque la validation HA échoue.
FR20: Le mainteneur peut distinguer un composant HA inconnu du moteur d'un composant connu mais mal alimenté par les données Jeedom.

**Feature 4 — Étape 4 : Décision de publication**

FR21: Le système peut prendre une décision de publication uniquement après réussite des étapes 1 à 3.
FR22: Le système peut porter en étape 4 la décision finale de publication à partir d'une projection déjà modélisée et validée.
FR23: Le système peut appliquer en étape 4 des politiques produit explicites, des exceptions de gouvernance et des overrides autorisés sans les confondre avec la validité structurelle HA.
FR24: L'utilisateur peut distinguer un blocage de décision de publication explicite d'un composant HA invalide, inconnu ou d'un échec de mapping.
FR25: L'utilisateur expert peut appliquer les overrides avancés autorisés par le produit sans effacer la décision native du moteur. _(post-MVP)_

**Feature 5 — Étape 5 : Publication MQTT et résultat**

FR26: Le système peut publier vers Home Assistant uniquement les projections explicitement autorisées par l'étape 4.
FR27: Le système peut enregistrer séparément le résultat de publication technique et la décision produit qui l'a précédé.
FR28: L'utilisateur peut distinguer un échec d'infrastructure d'un refus de projection décidé par le moteur.
FR29: Le système peut enrichir le diagnostic d'un équipement avec le résultat de publication effectif.
FR30: Le système peut empêcher qu'un échec technique masque la cause principale de décision déjà établie par les étapes amont.

**Feature 6 — Diagnostic explicable et actionnable**

FR31: L'utilisateur peut consulter, pour chaque équipement, un diagnostic de projection comprenant au minimum le statut de projection, l'étape de blocage ou l'étape la plus avancée atteinte, la cause principale canonique et, lorsqu'elle existe, l'action proposée.
FR32: Le système peut traduire chaque cause moteur canonique en un couple stable `cause_label` / `cause_action`, avec `cause_label` toujours renseigné et `cause_action` renseigné uniquement lorsqu'une remédiation utilisateur existe.
FR33: Le système peut expliquer explicitement lorsqu'aucune action utilisateur directe n'est possible.
FR34: Le système peut préserver le contrat 4D existant tout en ajoutant les informations de validité de projection.
FR35: L'utilisateur peut voir une seule cause principale canonique par équipement à un instant donné.

**Feature 7 — Registre HA et gouvernance**

FR36: Le mainteneur peut gérer un registre des composants HA séparé de la logique de mapping.
FR37: Le système peut différencier les états « composant connu », « composant validable » et « composant ouvert ».
FR38: Le mainteneur peut ajouter progressivement un composant au registre dans un cadre de gouvernance explicite, sans faire du registre une frontière produit arbitraire.
FR39: Le système peut considérer comme ouvrable dans le cycle tout composant dont les contraintes sont modélisées dans le registre HA, dont la validation structurelle aboutit sur des cas nominaux représentatifs, et dont l'ouverture ne crée pas de régression sur le diagnostic canonique.
FR40: Le mainteneur peut vérifier qu'un composant n'est marqué « ouvert » que si trois conditions sont satisfaites simultanément : contraintes présentes dans le registre, mapping candidat défini pour les cas visés, et validation couverte par des cas nominaux et des cas d'échec sans régression sur le contrat 4D.

**Feature 8 — Validation, testabilité et rétrocompatibilité**

FR41: Le mainteneur peut tester chaque étape du pipeline indépendamment.
FR42: Le mainteneur peut valider l'ouverture d'un composant HA par des cas nominaux et des cas d'échec représentatifs.
FR43: Le système peut conserver la compatibilité des `reason_code` existants tout en ajoutant de nouveaux motifs liés à la validité HA.
FR44: Le système peut exposer un contrat de diagnostic dont les champs canoniques (`reason_code`, `cause_code`, `cause_label`, `cause_action`, étape de pipeline, statut) restent stables d'une version à l'autre, hors ajouts additifs documentés, pour permettre des tests de non-régression.
FR45: Le mainteneur peut vérifier qu'une évolution du registre, du mapping ou de la validation ne dégrade pas le contrat 4D ni la hiérarchie des causes.

---

### Exigences non fonctionnelles

NFR1: À entrées identiques, le moteur doit produire 100% des mêmes décisions de projection, étapes de blocage et causes principales canoniques sur le corpus de non-régression de référence, vérifié par exécution répétée du même jeu de cas.
NFR2: Le taux de publications autorisées avec une validation HA négative doit être de 0%, vérifié par tests de pipeline couvrant les cas de validation positive et négative.
NFR3: 100% des équipements traités doivent recevoir un résultat explicite de pipeline, y compris en cas d'échec, vérifié sur le corpus de tests couvrant cas nominaux, ambiguïtés, invalidités HA et incidents d'infrastructure.
NFR4: Pour 100% des équipements diagnostiqués, une seule classe d'échec canonique doit être exposée comme cause principale à un instant donné.
NFR5: 100% des composants HA ouverts doivent satisfaire les contraintes structurelles de leur entrée de registre et du contrat MQTT Discovery correspondant sur les cas nominaux couverts.
NFR6: Le cycle doit introduire 0 source de vérité métier concurrente à Jeedom.
NFR7: Le contrat 4D existant doit rester rétrocompatible à 100% pour les consommateurs actuels sur le corpus de non-régression V1.1.
NFR8: 0 `reason_code` historique ne doit être renommé, supprimé ou voir son sens inversé ; toute extension doit être additive et documentée.
NFR9: Chacune des 5 étapes du pipeline doit disposer d'au moins un cas nominal et un cas d'échec exécutables en isolation dans la suite de tests de référence.
NFR10: 100% des ouvertures de nouveaux composants HA doivent être accompagnées, dans le même incrément, d'au moins un cas nominal, un cas d'échec de validation et un test de non-régression diagnostic.
NFR11: 0 évolution du registre, du mapping ou de la validation ne doit être acceptée si le corpus de non-régression du diagnostic canonique présente une régression.
NFR12: Les artefacts de décision utilisés par les vérifications automatiques doivent conserver un schéma canonique stable sur 100% des tests de cohérence, hors ajouts additifs documentés.

---

### Exigences additionnelles — Architecture

**Structure du MappingResult (D1)**

AR1: Le `MappingResult` doit contenir trois sous-blocs strictement bornés par étape : `mapping` (étape 2), `projection_validity` (étape 3), `publication_decision` (étape 4). Chaque étape écrit exclusivement dans son sous-bloc.

AR2: Même en cas d'échec d'une étape précédente, les sous-blocs suivants doivent être présents avec un statut explicite (ex. `is_valid: None, reason_code: "skipped_no_mapping_candidate"`). Aucun trou implicite dans le diagnostic.

**Séparation des responsabilités (D2)**

AR3: La validation HA doit résider dans un nouveau module physiquement séparé : `resources/daemon/validation/ha_component_registry.py`. Ce module n'importe pas depuis `mapping/`, `discovery/`, ni `transport/`.

**Registre statique HA (D3)**

AR4: `HA_COMPONENT_REGISTRY` est un dict Python statique listant les composants connus avec leurs `required_fields` et `required_capabilities`. `PRODUCT_SCOPE` est la liste des composants ouverts dans le cycle courant.

AR5: Valeur de départ de `PRODUCT_SCOPE` pour ce cycle : `["light", "cover", "switch"]`. Tout composant `validable` du registre peut y être ajouté si et seulement si FR40 est satisfait dans ce cycle.

**Registre HA — 3 états verrouillés (Delta Point 1)**

AR6: Les trois états du registre sont : `connu` (entrée dans `HA_COMPONENT_REGISTRY`) / `validable` (`validate_projection()` aboutit positivement sur des cas nominaux représentatifs) / `ouvert` (présent dans `PRODUCT_SCOPE` après satisfaction simultanée des 3 conditions de FR40). La séquence est stricte : `connu` → `validable` → `ouvert`.

**Fonction pure de validation (D4)**

AR7: `validate_projection(ha_entity_type: str, capabilities: MappingCapabilities) → ProjectionValidity` est une fonction pure sans effet de bord, testable sans dépendance MQTT, Jeedom ou daemon.

**Migration additive des reason_codes (D5)**

AR8: Nouveaux reason_codes à introduire (classe 2 — validité HA) : `ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`, `ha_component_unknown`. Nouveau reason_code (classe 3 — scope produit) : `ha_component_not_in_product_scope`. Aucun code existant n'est renommé ou supprimé.

**Contrat formel de l'étape 4 (Delta Point 2)**

AR9: L'étape 4 ne revalide pas la projection HA. Elle arbitre uniquement la publication finale à partir de 4 inputs : `projection_validity.is_valid` (hérité de l'étape 3, non réévalué), `confidence_policy` (politique de confiance), `PRODUCT_SCOPE` (gouvernance d'ouverture), overrides autorisés (étape 1 uniquement pour ce cycle). Deux raisons distinctes de `should_publish=False` : `low_confidence` (politique produit) et `ha_component_not_in_product_scope` (gouvernance d'ouverture) — diagnostics utilisateur distincts au sens de FR24.

**Insertion dans le sync handler (D7)**

AR10: Le handler `_do_handle_action_sync()` dans `http_server.py` appelle `validate_projection()` entre `map()` et `decide_publication()`. Le pipeline ne court-circuite jamais : même si `validate_projection` retourne `is_valid=False`, `decide_publication()` est toujours appelée et produit une `PublicationDecision(should_publish=False)` explicite.

**Diagnostic étendu (D8)**

AR11: `_build_traceability()` est enrichi par ajout pur du sous-bloc `projection_validity`. Aucun champ existant n'est supprimé, renommé ou déplacé. Les nouveaux `reason_code` de classe 2 alimentent le contrat 4D via `reason_code_to_cause()` dans `cause_mapping.py`.

**Overrides (D6)**

AR12: Les overrides utilisateur (inclusion/exclusion scope) restent à l'étape 1 pour ce cycle. Les overrides avancés inter-étapes (FR25 — forcer type HA ou publier malgré confiance insuffisante) sont post-MVP, explicitement différés.

**Invariant de gouvernance de cycle (NFR10 — Delta Point 3)**

AR13: Toute modification de `PRODUCT_SCOPE` (ajout d'un composant ouvert) exige, dans le même incrément : tests FR40 (cas nominal + cas d'échec validation + test de non-régression diagnostic). C'est un acceptance criterion obligatoire pour toute story touchant `PRODUCT_SCOPE`.

---

### Exigences UX

_Aucun document UX spécifique au cycle moteur de projection n'a été identifié. Les contraintes UX existantes (contrat 4D, présentation cause principale) sont portées par les FRs ci-dessus. Toute story impactant une surface critique devra inclure un artefact visuel prescriptif et un gate terrain avant "done"._

---

### Carte de couverture des exigences fonctionnelles

| FRs | Epic | Résumé |
|---|---|---|
| FR1-FR5 | Epic 1 | Feature 0 — Contrat global du pipeline à 5 étapes |
| FR6-FR10 | Epic 1 | Feature 1 — Éligibilité formalisée |
| FR11-FR15 | Epic 2 | Feature 2 — Mapping candidat découplé |
| FR16-FR20 | Epic 3 | Feature 3 — Validation HA (sous-capacité A) |
| FR36-FR40 | Epic 3 | Feature 7 — Registre HA et gouvernance (sous-capacité B) |
| FR21-FR24 | Epic 4 | Feature 4 — Décision de publication explicite |
| FR41-FR45 | Epic 4 | Feature 8 — Testabilité et rétrocompatibilité |
| FR25 | _(post-MVP — hors cycle)_ | Overrides avancés inter-étapes |
| FR26-FR30 | Epic 5 | Feature 5 — Publication MQTT orchestrée |
| FR31-FR35 | Epic 6 | Feature 6 — Diagnostic explicable et actionnable |

**NFR coverage :**

| NFR | Epic principal | Note |
|---|---|---|
| NFR1 (déterminisme 100%) | Epic 1 | Pipeline ordonné + fonctions pures |
| NFR2 (0% publication avec validation HA négative) | Epic 3 | Contrat de `validate_projection()` |
| NFR3 (100% résultat explicite) | Epic 1 + Epic 6 | Trace complète (AR2) + diagnostic final |
| NFR4 (cause principale unique) | Epic 1 + Epic 4 | Ordre stable du pipeline |
| NFR5 (composants ouverts = contraintes satisfaites) | Epic 3 | FR40 comme AC obligatoire |
| NFR6 (0 source de vérité concurrente) | Fondation verrouillée V1.1 (hors cycle) | |
| NFR7 (4D rétrocompatible 100%) | Epic 4 + Epic 6 | D5 + P7 |
| NFR8 (0 reason_code renommé) | Epic 4 | Migration additive uniquement |
| NFR9 (min. 1 cas nominal + 1 cas échec par étape) | Epic 4 (gate stories) | AC obligatoire nommé dans chaque story pipeline |
| NFR10 (ouverture composant = même incrément + tests) | Epic 3 | AR13 — AC d'ouverture obligatoire PRODUCT_SCOPE |
| NFR11 (0 régression corpus non-régression) | Epic 4 (gate avant done) | Corpus de non-régression posé dans Epic 4 |
| NFR12 (schéma diagnostic stable) | Epic 4 + Epic 6 | D1 + P7 |

---

## Liste des epics

### Epic 1 — Le pipeline canonique établit un contrat de décision déterministe — l'éligibilité est sa première étape formalisée

**Valeur utilisateur :** L'utilisateur peut s'appuyer sur un moteur de projection déterministe dont l'ordre d'évaluation est stable et testable. L'étape d'éligibilité est la première décision formelle du moteur : tout équipement reçoit un résultat explicite — éligible ou non, avec la cause catégorisée. La structure MappingResult à sous-blocs bornés est le contrat de transport de toutes les décisions du pipeline.

**Résultat observable :** Le contrat du pipeline à 5 étapes est formalisé (Feature 0). L'éligibilité est la première étape : tout équipement reçoit un résultat explicite avec cause catégorisée (Feature 1). La structure MappingResult à sous-blocs strictement bornés est établie comme contrat de transport. Aucun équipement inéligible n'entre dans le mapping. L'étape 1 est testable en isolation.

**FRs couverts :** FR1, FR2, FR3, FR4, FR5 (Feature 0 — contrat global), FR6, FR7, FR8, FR9, FR10 (Feature 1 — éligibilité)

**ARs clés :** AR1 (MappingResult sous-blocs bornés), AR2 (trace complète sans trou implicite — `is_valid: None` si skipped)

**NFRs directement adressés :** NFR1 (déterminisme — pipeline ordonné), NFR3 (100% résultat explicite — fondation posée ici), NFR9 (étape 1 : au moins un cas nominal + un cas d'échec en isolation)

**Invariants à porter en stories :**
- La séquence `connu → validable → ouvert` du registre HA (AR6) est un contexte de contrat pour les stories futures — non implémentée ici
- `projection_validity` avant `publication_decision` : le MappingResult doit le refléter structurellement dès cette fondation

---

### Epic 2 — Le moteur produit un candidat de mapping structuré sans présupposer la validité HA

**Valeur utilisateur :** Le mainteneur peut faire évoluer les règles de mapping sans modifier l'ordre canonique des étapes. Chaque équipement éligible reçoit un candidat de projection annoté (type HA cible, niveau de confiance, raison) dans un sous-bloc borné. L'utilisateur distingue un échec de mapping d'un refus ultérieur du pipeline — ce n'est pas la même cause, ce n'est pas le même diagnostic.

**Résultat observable :** Le mapping s'exécute exclusivement après l'éligibilité, écrit dans son seul sous-bloc, produit un candidat ou un refus catégorisé. Les sous-blocs `projection_validity` et `publication_decision` sont présents mais skipped (AR2). L'étape 2 est testable en isolation.

**FRs couverts :** FR11, FR12, FR13, FR14, FR15 (Feature 2 — mapping candidat)

**ARs clés :** P2 (isolation sous-blocs — lecture seule sur sous-blocs précédents), P3 (nommage reason_codes — convention existante pour classe 1 : `no_mapping`, `ambiguous_skipped`, etc.)

**NFRs directement adressés :** NFR9 (étape 2 : au moins un cas nominal + un cas d'échec en isolation)

**Invariants à porter en stories :**
- Cause principale = mapping si l'échec survient ici — non présupposée par une invalidité HA latente
- Le mapping ne touche pas au registre HA ni à `PRODUCT_SCOPE` (dépendance strictement unidirectionnelle : mapping → registre dans Epic 3)

---

### Epic 3 — Deux sous-capacités distinctes : la validation HA est obligatoire avant publication, et le registre gouverne l'ouverture des composants

**Valeur utilisateur :** L'utilisateur voit qu'un équipement est "compris par le moteur mais invalide côté HA" — ce n'est pas un échec de mapping, c'est une contrainte structurelle externe. Le mainteneur peut modéliser les contraintes de tout composant HA dans un registre gouverné à 3 états (`connu → validable → ouvert`) et ouvrir un composant selon un contrat de gouvernance vérifiable, pas une liste fermée arbitraire.

**Structure interne — deux sous-capacités à décliner en stories séparées :**

**Sous-capacité A — Validation HA (Feature 3) :** `validate_projection()` est une fonction pure testable sans dépendance MQTT/Jeedom. Elle vérifie que le candidat de mapping satisfait les contraintes structurelles du composant HA cible. Un échec produit un reason_code de classe 2 distinct de la classe 1 (mapping). Aucune publication ne peut contourner cette étape.

**Sous-capacité B — Registre HA et gouvernance d'ouverture (Feature 7) :** `HA_COMPONENT_REGISTRY` contient les composants connus avec leurs contraintes. `PRODUCT_SCOPE` liste les composants ouverts. Les 3 états (`connu`, `validable`, `ouvert`) sont strictement distincts des étapes du pipeline et non confondus dans le diagnostic. L'ouverture d'un composant satisfait simultanément les 3 conditions de FR40.

**Résultat observable :** Module `validation/` créé et séparé physiquement. `validate_projection()` testable en isolation. Registre initial populé avec les composants connus de l'architecture. `PRODUCT_SCOPE` de départ = `["light", "cover", "switch"]`. Tout composant `validable` du registre peut être ajouté si FR40 est satisfait dans le cycle courant. Aucune publication ne passe si l'étape 3 est négative.

**FRs couverts :**
- FR16, FR17, FR18, FR19, FR20 (Feature 3 — Validation HA — sous-capacité A)
- FR36, FR37, FR38, FR39, FR40 (Feature 7 — Registre HA et gouvernance — sous-capacité B)

**ARs clés :** AR3 (module `validation/` séparé), AR4 (registre statique), AR5 (PRODUCT_SCOPE de départ), AR6 (3 états verrouillés — delta point 1 — item 14 architecture fermé), AR7 (`validate_projection` fonction pure), AR8 (reason_codes `ha_missing_*` + `ha_component_unknown` — classe 2), AR13 (NFR10 comme AC obligatoire pour toute modification de PRODUCT_SCOPE)

**NFRs directement adressés :** NFR2 (0% publication avec validation négative), NFR5 (composants ouverts = contraintes satisfaites), NFR10 (ouverture = même incrément + tests FR40)

**Invariants à porter en stories :**
- `PRODUCT_SCOPE` part de `["light", "cover", "switch"]` — pas un plafond, frontière `governed-open` (AR6)
- 3 états distincts des étapes du pipeline : un composant peut être `connu` dans le registre sans qu'aucun équipement ait encore passé l'étape 3 (AR6)
- `validate_projection` : `(ha_entity_type, capabilities) → ProjectionValidity` — aucun effet de bord (AR7)
- Toute modification de `PRODUCT_SCOPE` exige les tests FR40 dans le même incrément (AR13)

---

### Epic 4 — La décision de publication est explicite et le contrat de testabilité/rétrocompatibilité est garanti

**Valeur utilisateur :** L'utilisateur distingue deux causes distinctes de non-publication après une projection structurellement valide : politique produit (`low_confidence`) ou gouvernance d'ouverture (`ha_component_not_in_product_scope`) — deux `cause_label` distincts, diagnostics différents. La migration des `reason_code` est additive : aucun code existant n'est cassé. Le mainteneur peut tester chaque étape du pipeline en isolation et vérifier qu'aucune évolution ne régresse le contrat 4D ni la hiérarchie des causes.

**Pourquoi la Feature 8 (testabilité/rétrocompatibilité) est portée ici et non comme transverse faible :** FR41-FR45 ne sont pas des AC génériques applicables de façon diffuse. FR41-FR42 posent le corpus de non-régression de référence — ce corpus doit exister avant que l'orchestration complète du pipeline (Epic 5) et le diagnostic final (Epic 6) soient validés. FR43-FR45 sont le contrat même de la décision de publication : les reason_codes, le contrat 4D et le schéma diagnostic stable sont les invariants que `decide_publication()` et `cause_mapping.py` doivent respecter. Dissocier Feature 8 de Feature 4 créerait le risque que la rétrocompatibilité soit traitée comme un ajout tardif plutôt que comme le contrat de référence qu'elle est.

**Résultat observable :** `decide_publication()` produit toujours un motif explicite. Les nouveaux reason_codes s'ajoutent sans régression. Le corpus de non-régression des 5 étapes est posé et exécutable. Le contrat 4D est rétrocompatible à 100% sur le corpus V1.1. FR25 (overrides avancés) : post-MVP, aucun code dans ce cycle.

**FRs couverts :**
- FR21, FR22, FR23, FR24 (Feature 4 — Décision de publication) — FR25 hors cycle
- FR41, FR42, FR43, FR44, FR45 (Feature 8 — Testabilité et rétrocompatibilité)

**ARs clés :** AR9 (contrat formel étape 4 — delta point 2 fermé : étape 4 ne revalide pas la projection HA), AR12 (overrides à l'éligibilité uniquement)

**NFRs directement adressés :** NFR4 (cause principale unique), NFR7 (4D rétrocompatible), NFR8 (0 reason_code renommé), NFR9 (corpus de non-régression complet sur les 5 étapes), NFR11 (gate avant done — corpus doit passer), NFR12 (schéma diagnostic stable)

**Invariants à porter en stories :**
- L'étape 4 **ne revalide pas** la projection HA — `projection_validity.is_valid` est consommé comme fait établi (AR9)
- Deux `cause_label` distincts : `low_confidence` (politique produit) vs `ha_component_not_in_product_scope` (gouvernance d'ouverture)
- Nouveau reason_code `ha_component_not_in_product_scope` (classe 3) ajouté sans supprimer `no_supported_generic_type` existant (AR8)
- Le corpus de non-régression posé ici est la gate de tous les epics suivants

**Note UX :** Toute story modifiant la présentation du diagnostic (cause_label, cause_action) sur une surface critique requiert un artefact visuel prescriptif et un gate terrain avant done.

---

### Epic 5 — Les projections autorisées sont publiées vers Home Assistant avec un résultat technique traçable

**Valeur utilisateur :** L'utilisateur voit ses équipements structurellement projetables apparaître dans Home Assistant. Un échec d'infrastructure (broker MQTT indisponible) est distingué d'un refus décidé par le moteur : la cause principale canonique établie par les étapes amont n'est jamais masquée par un incident technique. Le résultat de publication est enregistré séparément de la décision produit.

**Résultat observable :** Le sync handler orchestre le pipeline complet à 5 étapes avec `validate_projection()` inséré entre mapping et `decide_publication()` (AR10). Seules les projections autorisées par l'étape 4 sont publiées. Le résultat de publication est enregistré dans `publication_decision.discovery_published`. Aucun court-circuit : le pipeline produit toujours une `PublicationDecision` complète, même en cas d'invalidité HA (AR10).

**FRs couverts :** FR26, FR27, FR28, FR29, FR30 (Feature 5 — Publication MQTT)

**ARs clés :** AR10 (insertion `validate_projection()` dans sync handler — pipeline ne court-circuite jamais)

**NFRs directement adressés :** NFR2 (0 publication sans validation HA positive — gate effective ici), NFR3 (100% résultat explicite — la publication s'ajoute au diagnostic)

**Invariants à porter en stories :**
- Le pipeline ne court-circuite jamais (AR10) : même si l'étape 3 ou 4 est bloquante, la `PublicationDecision(should_publish=False)` est explicite
- Le résultat de publication technique (`discovery_published`) est séparé de la décision produit (`should_publish`)
- Un échec d'infrastructure en étape 5 ne modifie pas la cause principale canonique des étapes amont (FR30)

---

### Epic 6 — Le diagnostic est explicable et actionnable pour chaque équipement

**Valeur utilisateur :** L'utilisateur voit, pour chaque équipement, une seule cause principale canonique ordonnée par pipeline, ordonnée de manière déterministe par l'étape qui a effectivement bloqué. Lorsqu'une remédiation existe, une action est proposée. Lorsqu'aucune action utilisateur n'est possible, le système l'exprime explicitement. Le contrat 4D existant est préservé, enrichi par ajout pur. La valeur du cycle entier devient visible ici : le passage de l'opacité à la compréhension actionnable.

**Résultat observable :** `_build_traceability()` est enrichi par ajout pur du sous-bloc `projection_validity` (AR11). Le diagnostic expose l'étape de pipeline atteinte, la cause principale canonique unique, `cause_label` toujours renseigné, `cause_action` uniquement si une remédiation utilisateur existe. Le contrat 4D est rétrocompatible. Chaque enrichissement est testé contre le corpus de non-régression posé en Epic 4.

**FRs couverts :** FR31, FR32, FR33, FR34, FR35 (Feature 6 — Diagnostic explicable et actionnable)

**ARs clés :** AR11 (diagnostic étendu — `projection_validity` ajouté en enrichissement pur, P7), AR8 + AR9 (reason_codes classe 2 et 3 alimentent `cause_mapping.py`)

**NFRs directement adressés :** NFR3 (100% résultat explicite — le diagnostic est la surface utilisateur), NFR7 (contrat 4D rétrocompatible — enrichi, jamais cassé), NFR12 (schéma diagnostic stable sur le corpus de non-régression)

**Invariants à porter en stories :**
- Enrichissement additif uniquement (AR11) : aucun champ existant supprimé, renommé ou déplacé
- `cause_action` non renseigné lorsqu'aucune remédiation utilisateur n'existe (FR32/FR33 — pas de fausse promesse)
- Contrat 4D strict : backend calcule, frontend affiche sans réinterpréter
- Toute story sur ce diagnostic passe le corpus de non-régression V1.1 + le corpus de non-régression du cycle

**Note UX :** Les stories impactant la présentation de la cause principale, de `cause_label`, de `cause_action` ou de l'étape de pipeline visible requièrent un artefact visuel prescriptif et un gate terrain avant done.

---

### Epic 7 — L'actionnabilite devient une capacite produit reelle par ouverture gouvernee du perimetre HA

**Valeur utilisateur :** L'utilisateur ne voit une action que lorsqu'elle repose sur une surface produit reellement ouverte, supportee et testee. Le diagnostic cesse de promettre "quoi faire" au-dela du produit reellement disponible.

**Résultat observable :** Le contrat 4D est enrichi de facon additive avec `projection_validity` pour rendre visible la realite structurelle. Une premiere vague d'ouverture HA est bornee, rendue validable, puis ouverte sous FR40 / NFR10 dans le meme increment. Les CTA utilisateur ne reapparaissent que sur des surfaces reellement disponibles.

**FRs couverts :** FR34 (visibilite `projection_validity`), FR39, FR40, FR42, avec re-usage borne de FR32 / FR33 sur les surfaces reellement ouvertes

**ARs clés :** AR6 (3 etats `connu -> validable -> ouvert`), AR11 (enrichissement additif), AR13 (ouverture de `PRODUCT_SCOPE` dans le meme increment)

**NFRs directement adressés :** NFR5 (composants ouverts = contraintes satisfaites), NFR10 (ouverture = meme increment + tests), NFR12 (schema diagnostic stable)

**Invariants à porter en stories :**
- aucune story ne modifie `PRODUCT_SCOPE` sans preuves FR40 dans le meme increment
- `projection_validity` est expose par ajout pur, sans regression du contrat 4D
- toute action exposee doit etre traçable jusqu'a une surface produit reelle et testee
- toute story touchant `cause_action` repasse par le gate terrain `no faux CTA`

---

## Epic 1 — Le pipeline canonique établit un contrat de décision déterministe — l'éligibilité est sa première étape formalisée

L'utilisateur peut s'appuyer sur un moteur de projection déterministe dont l'ordre d'évaluation est stable et testable. Le contrat global du pipeline à 5 étapes est formalisé (Feature 0). L'éligibilité est sa première étape formelle : tout équipement reçoit un résultat explicite avec cause catégorisée (Feature 1). La structure MappingResult à sous-blocs bornés est le contrat de transport de toutes les décisions du pipeline.

### Story 1.1 : Contrat du pipeline — MappingResult à sous-blocs bornés et ordre d'évaluation stable

En tant que mainteneur,
je veux que le MappingResult contienne trois sous-blocs strictement bornés (`mapping`, `projection_validity`, `publication_decision`) évalués dans un ordre stable et fixe,
afin que chaque étape soit développable et testable en isolation et que le diagnostic reçoive toujours une trace complète et non ambiguë.

**Acceptance Criteria :**

**Given** le type MappingResult est défini
**When** un équipement traverse le pipeline
**Then** le MappingResult contient toujours les trois sous-blocs : `mapping`, `projection_validity`, `publication_decision`
**And** chaque sous-bloc est écrit exclusivement par l'étape correspondante — aucune autre étape ne le modifie
**And** si une étape précédente a échoué, les sous-blocs suivants sont présents avec un statut explicite (`is_valid: None, reason_code: "skipped_no_mapping_candidate"`) — jamais absents

**Given** le pipeline évalue un équipement
**When** une étape bloque l'évaluation
**Then** le pipeline retient cette étape bloquante comme cause principale canonique
**And** l'évaluation s'arrête à cette étape mais les sous-blocs suivants sont remplis avec un statut skipped explicite

**Given** un jeu de test pour le contrat du pipeline
**When** le test exécute le pipeline deux fois avec des entrées identiques
**Then** la sortie (MappingResult, étape bloquante, cause principale) est identique aux deux passages (NFR1 — déterminisme)

**Dev notes :**
- AR1 : MappingResult 3 sous-blocs ; AR2 : aucun trou implicite — `is_valid: None` si skipped
- NFR1 consigné dès cette story via test de déterminisme sur corpus minimal
- `MappingCapabilities` : type d'entrée de `validate_projection()` — à définir et implémenter dans cette story (point ouvert D4 de l'architecture)
- FR1, FR2, FR3, FR5

---

### Story 1.2 : Étape 1 — L'éligibilité classe chaque équipement Jeedom dans une catégorie stable avant tout mapping

En tant qu'utilisateur,
je veux que le système détermine si chaque équipement est éligible avant tout tentative de mapping, en classant les causes d'inéligibilité dans des catégories distinctes et stables,
afin de savoir précisément quels équipements entrent dans le pipeline et pourquoi les autres n'y entrent pas.

**Acceptance Criteria :**

**Given** un équipement Jeedom satisfaisant toutes les règles de scope
**When** le pipeline évalue l'éligibilité
**Then** l'équipement est classé éligible et transmis à l'étape de mapping
**And** le résultat d'éligibilité porte `status: eligible`

**Given** un équipement exclu par les règles de scope utilisateur
**When** le pipeline évalue l'éligibilité
**Then** l'équipement est classé inéligible avec une cause de catégorie `excluded_*` (par équipement, plugin ou objet Jeedom)
**And** l'équipement n'entre pas dans l'étape de mapping

**Given** un équipement avec `is_enable=false` dans Jeedom
**When** le pipeline évalue l'éligibilité
**Then** l'équipement est classé inéligible avec reason_code `disabled_eqlogic`
**And** l'équipement n'entre pas dans l'étape de mapping

**Given** un équipement sans aucune commande
**When** le pipeline évalue l'éligibilité
**Then** l'équipement est classé inéligible avec reason_code `no_commands`

**Given** un équipement sans generic_type sur aucune de ses commandes
**When** le pipeline évalue l'éligibilité
**Then** l'équipement est classé inéligible avec reason_code `no_generic_type` (ou équivalent existant)
**And** ce cas est distinct d'un équipement éligible pour lequel aucun mapping ne peut être produit (FR8)

**Given** la suite de tests de l'étape 1
**When** les cas de test sont exécutés
**Then** il existe au moins un cas nominal (équipement éligible) et un cas d'échec (inéligible avec cause explicite) exécutables en isolation (NFR9)

**Dev notes :**
- FR6 : règles de scope = mécanisme de scope produit existant, inchangé
- FR8 : distinction explicite entre inéligible (étape 1) et éligible-mais-non-projetable (étapes 2 ou 3)
- FR9 : la taxonomie de catégories doit être stable — pas de chaînes de raison libres
- Ordre d'évaluation de l'éligibilité (fondation V1.1 à conserver) : exclu > désactivé > sans commandes > sans generic_type

---

### Story 1.3 : Diagnostic d'éligibilité — l'utilisateur lit l'étape 1 comme point de blocage avec cause catégorisée et action de scope applicable

En tant qu'utilisateur,
je veux voir, pour tout équipement bloqué à l'étape 1, l'étape de blocage explicitement identifiée et le motif d'exclusion canonique, avec une action de scope proposée lorsque mes propres réglages en sont la cause,
afin de pouvoir agir directement sur le bon levier sans avoir à deviner pourquoi l'équipement est absent de Home Assistant.

**Acceptance Criteria :**

**Given** un équipement inéligible à cause d'une exclusion de scope utilisateur
**When** l'utilisateur consulte le diagnostic
**Then** le diagnostic indique l'étape 1 comme étape de blocage
**And** le `cause_code` est `excluded_*` avec le type d'exclusion applicable
**And** un `cause_action` est fourni pointant vers le réglage de scope concerné

**Given** un équipement inéligible à cause de `is_enable=false`
**When** l'utilisateur consulte le diagnostic
**Then** le diagnostic indique l'étape 1 comme étape de blocage
**And** le `cause_label` indique « Équipement désactivé dans Jeedom »
**And** le `cause_action` propose d'activer l'équipement dans la page de configuration Jeedom

**Given** 100 % des équipements passés dans le pipeline
**When** le diagnostic est consulté
**Then** chaque équipement dispose d'un résultat de pipeline explicite — soit l'étape la plus avancée atteinte, soit l'étape bloquante (NFR3)
**And** aucun équipement ne produit un diagnostic vide ou ambigu

**Given** la suite de tests vérifiant FR4
**When** les tests s'exécutent
**Then** chaque équipement du corpus de test porte dans son MappingResult l'étape la plus avancée atteinte

**Dev notes :**
- FR4 : restitution de l'étape la plus avancée — doit être tracée dans le MappingResult dès cette story
- FR10 : `cause_action` présent si et seulement si l'exclusion relève d'un choix utilisateur
- NFR3 : gate d'acceptance — 100 % de couverture sur le corpus de test

---

## Epic 2 — Le moteur produit un candidat de mapping structuré sans présupposer la validité HA

Le mainteneur peut faire évoluer les règles de mapping sans modifier l'ordre canonique des étapes. Chaque équipement éligible reçoit un candidat de projection annoté (type HA cible, confiance, raison) dans un sous-bloc borné. Un échec de mapping est clairement distingué d'un refus ultérieur du pipeline — ce n'est pas la même cause, ce n'est pas le même diagnostic.

### Story 2.1 : Mapping candidat — le moteur produit un candidat de projection HA annoté avec niveau de confiance dans le sous-bloc mapping borné

En tant qu'utilisateur,
je veux que le système produise, pour chaque équipement éligible, un candidat de projection nommant le type d'entité HA cible et exprimant un niveau de confiance,
afin que chaque équipement qui atteint le pipeline reçoive une intention de mapping structurée et traçable — et non une simple heuristique opaque.

**Acceptance Criteria :**

**Given** un équipement éligible avec des generic_types non ambigus
**When** le pipeline applique l'étape de mapping
**Then** le sous-bloc `mapping` est rempli avec `ha_entity_type`, `confidence` (sure ou probable) et un `reason_code`
**And** les sous-blocs `projection_validity` et `publication_decision` sont présents mais skipped (AR2) avec statut explicite

**Given** le module de mapping
**When** le développeur modifie une règle de mapping
**Then** la modification est circonscrite au module mapping — aucune modification requise dans les modules éligibilité, validation ou publication (FR15 — séparation structurelle)
**And** l'ordre canonique des 5 étapes est inchangé

**Given** un cas de test nominal pour l'étape 2
**When** le test s'exécute en isolation (sans MQTT, sans runtime Jeedom)
**Then** le test passe et produit un MappingCandidate valide avec niveau de confiance

**Dev notes :**
- P2 : isolation des sous-blocs — mapping écrit uniquement dans son sous-bloc
- P3 : conventions de nommage reason_codes existants pour la classe 1 : `no_mapping`, `ambiguous_skipped`, `duplicate_generic_types`, etc.
- FR11, FR12, FR15

---

### Story 2.2 : Échec et ambiguïté de mapping — le moteur signale explicitement un mapping impossible ou ambigu, et les sous-blocs suivants reflètent le skip

En tant qu'utilisateur,
je veux voir, lorsque le système ne peut pas produire un mapping utilisable pour un équipement éligible, un motif d'échec de mapping clair et distinct de tout refus ultérieur du pipeline,
afin de comprendre que l'équipement a été reconnu par Jeedom mais que le système n'a pas pu déterminer quel type d'entité HA il devrait représenter.

**Acceptance Criteria :**

**Given** un équipement éligible avec des generic_types conflictuels (ex. LIGHT_ON + FLAP_UP)
**When** l'étape de mapping s'exécute
**Then** le sous-bloc `mapping` contient `confidence: ambiguous` et un `reason_code` de classe 1 (ex. `conflicting_generic_types`)
**And** le sous-bloc `projection_validity` est présent avec `is_valid: None` et `reason_code: "skipped_no_mapping_candidate"`
**And** le sous-bloc `publication_decision` est présent avec `should_publish: false` et `reason: "no_mapping"`

**Given** un équipement éligible où aucun generic_type ne produit un mapping connu
**When** l'étape de mapping s'exécute
**Then** le sous-bloc `mapping` contient un `reason_code` de classe 1 (ex. `no_mapping`)
**And** le diagnostic présente cette cause comme distincte d'un refus de validation HA (FR14)

**Given** un cas de test d'échec pour l'étape 2 (mapping ambigu ou absent)
**When** le test s'exécute en isolation
**Then** le test passe et vérifie que le reason_code de classe 1 correct est positionné dans le sous-bloc `mapping`
**And** les sous-blocs suivants sont présents avec statut skipped — pas de trou implicite (AR2)

**Dev notes :**
- FR13 / FR14 : le reason_code de classe 1 (mapping) doit être distinguable du reason_code de classe 2 (validité HA) dans le diagnostic
- AR2 : `projection_validity` et `publication_decision` présents mais skipped — jamais absents

---

## Epic 3 — Deux sous-capacités distinctes : la validation HA est obligatoire avant publication, et le registre gouverne l'ouverture des composants

L'utilisateur voit qu'un équipement est "compris par le moteur mais invalide côté HA". Le mainteneur peut modéliser les contraintes de tout composant HA dans un registre à 3 états et ouvrir un composant via un contrat de gouvernance vérifiable.

Les trois stories de cet epic correspondent aux trois sous-capacités demandées : registre HA, validation HA, gouvernance d'ouverture.

### Story 3.1 : Registre HA — le module validation/ définit les composants connus avec leurs contraintes en 3 états distincts

En tant que mainteneur,
je veux un module `validation/` physiquement séparé qui contient le registre statique des composants HA connus avec leurs contraintes structurelles, organisé selon les trois états distincts (connu / validable / ouvert),
afin de pouvoir faire évoluer le registre sans toucher aux modules mapping ou publication, et de ne jamais confondre les états du registre avec les étapes du pipeline.

**Acceptance Criteria :**

**Given** le module `resources/daemon/validation/ha_component_registry.py`
**When** il est importé
**Then** il exporte `HA_COMPONENT_REGISTRY` (dict des composants connus avec `required_fields` et `required_capabilities`) et `PRODUCT_SCOPE` (liste des composants ouverts)
**And** le module n'importe rien depuis `mapping/`, `discovery/` ni `transport/` (AR3 — séparation physique)

**Given** un composant présent dans `HA_COMPONENT_REGISTRY`
**When** son état est évalué
**Then** il est dans l'état `connu` — ses contraintes structurelles sont modélisées (required_fields + required_capabilities)
**And** l'état `connu` est distinct de `validable` (nécessite que `validate_projection()` aboutisse positivement sur des cas nominaux)
**And** l'état `validable` est distinct de `ouvert` (nécessite satisfaction simultanée des 3 conditions de FR40)

**Given** la valeur initiale de `PRODUCT_SCOPE`
**When** le cycle commence
**Then** `PRODUCT_SCOPE = ["light", "cover", "switch"]` (AR5, héritage V1.1)
**And** toute modification de `PRODUCT_SCOPE` sans satisfaire FR40 dans le même incrément est explicitement interdite par contrat documenté (AR6, AR13)

**Given** un test d'intégrité structurelle du registre
**When** le test s'exécute
**Then** chaque composant dans `PRODUCT_SCOPE` est également dans `HA_COMPONENT_REGISTRY`
**And** pour chaque composant dans `HA_COMPONENT_REGISTRY`, au moins un `required_field` ou une `required_capability` est définie

**Dev notes :**
- AR3 : dépendances strictes — `validation/` importe uniquement depuis `models/`
- AR6 : les 3 états sont des propriétés distinctes non confondues avec les étapes du pipeline — un composant peut être `connu` sans qu'aucun équipement ait encore passé l'étape 3
- AR13 : toute modification future de `PRODUCT_SCOPE` exige les tests FR40 dans le même incrément
- FR36, FR37

---

### Story 3.2 : Validation HA — la fonction pure validate_projection() vérifie que le candidat de mapping peut produire un payload structurellement valide pour le composant HA cible

En tant qu'utilisateur,
je veux que le système vérifie, avant toute publication, que le candidat de mapping d'un équipement satisfait les contraintes structurelles du composant HA cible,
afin de voir clairement quand un équipement a été compris par le moteur mais ne peut pas être projeté parce que la projection HA serait structurellement invalide — et non parce que le mapping a échoué.

**Acceptance Criteria :**

**Given** un équipement mappé comme `light` avec `has_command: true` (commandes ON/OFF présentes)
**When** `validate_projection("light", capabilities)` est appelée
**Then** elle retourne `ProjectionValidity(is_valid=True)`
**And** le sous-bloc `projection_validity` dans le MappingResult est rempli avec `is_valid: True`

**Given** un équipement mappé comme `light` sans commande action (`has_command: false`)
**When** `validate_projection("light", capabilities)` est appelée
**Then** elle retourne `ProjectionValidity(is_valid=False, reason_code="ha_missing_command_topic", missing_capabilities=["has_command"])`
**And** aucune publication ne peut suivre (NFR2)

**Given** un équipement mappé comme `cover` sans commande action (cover read-only valide côté HA per architecture)
**When** `validate_projection("cover", capabilities)` est appelée
**Then** elle retourne `ProjectionValidity(is_valid=True)` — le cover en lecture seule est structurellement valide

**Given** un équipement mappé vers un type de composant absent de `HA_COMPONENT_REGISTRY`
**When** `validate_projection(type_inconnu, capabilities)` est appelée
**Then** elle retourne `ProjectionValidity(is_valid=False, reason_code="ha_component_unknown")`

**Given** la suite de tests de l'étape 3
**When** les tests s'exécutent en isolation (sans MQTT, sans Jeedom, sans daemon)
**Then** il existe au moins un cas nominal (projection valide) et un cas d'échec (projection invalide avec reason_code spécifique) pour chaque type de composant ouvert (NFR9)

**Dev notes :**
- AR7 : fonction pure — signature `validate_projection(ha_entity_type: str, capabilities: MappingCapabilities) → ProjectionValidity`
- AR8 : nouveaux reason_codes classe 2 : `ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`, `ha_component_unknown`
- P4 : accès au registre uniquement via import depuis `validation/ha_component_registry.py`
- NFR2 : `is_valid=False` → `should_publish=False` garanti par le contrat d'orchestration (Epic 5)
- FR16, FR17, FR18, FR19, FR20

---

### Story 3.3 : Gouvernance d'ouverture — un composant validable peut être ajouté à PRODUCT_SCOPE si et seulement si les 3 conditions de FR40 sont satisfaites dans le même incrément

En tant que mainteneur,
je veux pouvoir ajouter un composant connu à `PRODUCT_SCOPE` en démontrant dans le même incrément que ses contraintes sont modélisées, que `validate_projection()` aboutit positivement sur des cas nominaux représentatifs et que le contrat 4D n'est pas régressé,
afin que le périmètre du moteur s'élargisse via des ajouts gouvernés, et non via des modifications arbitraires de liste.

**Acceptance Criteria :**

**Given** un composant connu dans `HA_COMPONENT_REGISTRY` (ex. `sensor` ou `binary_sensor`) que je veux ouvrir
**When** je propose son ajout à `PRODUCT_SCOPE`
**Then** la PR ou l'incrément doit fournir simultanément : (1) l'entrée dans `HA_COMPONENT_REGISTRY` avec `required_fields` et `required_capabilities` définis, (2) au moins un cas nominal et un cas d'échec pour `validate_projection()` avec ce type, (3) un test de non-régression sur le contrat 4D qui passe (FR40, AR13)

**Given** le type `sensor` ajouté à `PRODUCT_SCOPE` (exemple d'ajout gouverné)
**When** les conditions de gouvernance sont vérifiées
**Then** `validate_projection("sensor", caps_with_state)` retourne `is_valid=True`
**And** `validate_projection("sensor", caps_without_state)` retourne `is_valid=False, reason_code="ha_missing_state_topic"`
**And** les tests de non-régression existants sur `light`, `cover`, `switch` continuent de passer (NFR10, NFR11)

**Given** une tentative d'ajout à `PRODUCT_SCOPE` sans les tests requis
**When** la revue de code ou la CI s'exécute
**Then** l'ajout est rejeté — le contrat de gouvernance FR40 est documenté comme acceptance criterion obligatoire dans le registre

**Dev notes :**
- AR6 : état `ouvert` = `validable` + FR40 satisfait dans le même incrément
- AR13 : NFR10 comme acceptance criterion obligatoire — toute story future ajoutant à `PRODUCT_SCOPE` doit reproduire ce pattern
- FR38 : le registre ne doit pas devenir une frontière arbitraire — le mécanisme d'ouverture doit rester léger et documenté
- FR39, FR40

---

## Epic 4 — La décision de publication est explicite et le contrat de testabilité/rétrocompatibilité est garanti

L'utilisateur distingue deux causes distinctes de non-publication après une projection structurellement valide : politique produit (`low_confidence`) ou gouvernance d'ouverture (`ha_component_not_in_product_scope`). La migration des reason_codes est additive. Le corpus de non-régression des 5 étapes est posé et constitue la gate de référence pour les Epics 5 et 6.

### Story 4.1 : Étape 4 — decide_publication() arbitre la publication à partir de la projection validée, de la politique de confiance et du PRODUCT_SCOPE

En tant qu'utilisateur,
je veux que le système prenne une décision de publication uniquement une fois la projection structurellement validée, en s'appuyant sur la politique de confiance et le PRODUCT_SCOPE courant, avec un motif toujours explicite,
afin de savoir que la décision de publication est distincte de la validation HA et reflète une politique produit délibérée.

**Acceptance Criteria :**

**Given** un équipement avec `projection_validity.is_valid=True`, confiance `sure` et composant dans `PRODUCT_SCOPE`
**When** `decide_publication()` s'exécute
**Then** elle retourne `PublicationDecision(should_publish=True, reason="sure")`

**Given** un équipement avec `projection_validity.is_valid=True`, confiance `probable` et politique `sure_only`
**When** `decide_publication()` s'exécute
**Then** elle retourne `PublicationDecision(should_publish=False, reason="low_confidence")`

**Given** un équipement avec `projection_validity.is_valid=True`, confiance `sure`, mais composant NON dans `PRODUCT_SCOPE`
**When** `decide_publication()` s'exécute
**Then** elle retourne `PublicationDecision(should_publish=False, reason="ha_component_not_in_product_scope")`

**Given** un équipement avec `projection_validity.is_valid=False`
**When** `decide_publication()` est appelée
**Then** elle retourne `PublicationDecision(should_publish=False)` avec le motif hérité de l'étape amont
**And** `decide_publication()` NE réévalue PAS les contraintes structurelles HA (AR9 — l'étape 4 ne revalide pas)

**Given** tout chemin de code à travers `decide_publication()`
**When** la fonction retourne
**Then** `PublicationDecision.reason` est toujours non-null (P5 — motif toujours explicite)

**Dev notes :**
- AR9 : contrat formel étape 4 — `projection_validity.is_valid` consommé comme fait établi, non réévalué
- AR12 : overrides avancés (FR25) post-MVP — aucun code dans ce cycle
- `decide_publication()` doit accepter `ProjectionValidity` comme input (implicite dans D7 de l'architecture)
- FR21, FR22, FR23

---

### Story 4.2 : Diagnostic de la décision — l'utilisateur distingue un refus de politique produit d'un refus de gouvernance d'ouverture

En tant qu'utilisateur,
je veux voir, lorsque le système décide de ne pas publier un équipement dont la projection était structurellement valide, si c'est à cause de la politique de confiance (mon propre réglage) ou parce que le type de composant n'est pas encore ouvert dans ce cycle,
afin d'agir sur le bon levier — ajuster ma politique de confiance ou attendre l'ouverture du composant — sans confondre les deux causes.

**Acceptance Criteria :**

**Given** un équipement bloqué par `low_confidence` (étape 4, filtre de politique)
**When** l'utilisateur consulte le diagnostic
**Then** `cause_code` est `low_confidence`
**And** `cause_label` indique « Confiance insuffisante pour la politique active »
**And** `cause_action` pointe vers le réglage de politique de confiance

**Given** un équipement bloqué par `ha_component_not_in_product_scope` (étape 4, gouvernance)
**When** l'utilisateur consulte le diagnostic
**Then** `cause_code` est `not_in_product_scope`
**And** `cause_label` indique « Type d'entité non ouvert dans ce cycle »
**And** `cause_action` est null ou indique explicitement qu'aucune action utilisateur directe n'est disponible dans ce cycle (FR33)

**Given** les deux types de refus d'étape 4 présents simultanément dans le même diagnostic
**When** l'utilisateur les lit
**Then** les deux refus produisent des `cause_label` visuellement et sémantiquement distincts — impossibles à confondre (FR24)

**Dev notes :**
- AR9 : deux raisons distinctes → deux `cause_label` distincts
- Mise à jour de `cause_mapping.py` pour les nouveaux reason_codes `low_confidence` et `ha_component_not_in_product_scope`
- Note UX : si cette story modifie la surface diagnostic sur une zone critique, elle requiert un artefact visuel prescriptif et un gate terrain avant done
- FR24

---

### Story 4.3 : Migration additive des reason_codes — les codes de classe 2 et 3 s'ajoutent sans régression sur les codes existants ni sur le contrat 4D

En tant que mainteneur,
je veux que les cinq nouveaux reason_codes (`ha_missing_command_topic`, `ha_missing_state_topic`, `ha_missing_required_option`, `ha_component_unknown`, `ha_component_not_in_product_scope`) soient ajoutés au catalogue sans renommer, supprimer ni inverser aucun code existant, et que le contrat 4D reste rétrocompatible à 100 %,
afin que les consommateurs du contrat de diagnostic existant (tests V1.1, systèmes en aval) ne soient pas cassés par le cycle.

**Acceptance Criteria :**

**Given** le catalogue de reason_codes existants (baseline V1.1)
**When** les nouveaux reason_codes sont ajoutés
**Then** tout reason_code existant conserve son nom exact, sa signification et sa direction (NFR8)
**And** le corpus de non-régression V1.1 passe sans modification

**Given** chaque nouveau reason_code de classe 2 (`ha_missing_*`)
**When** il traverse `reason_code_to_cause()` dans `cause_mapping.py`
**Then** il produit un `cause_code` non-null, un `cause_label` non-null, et un `cause_action` qui est soit une chaîne d'action valide, soit explicitement null (FR32)

**Given** le reason_code de classe 3 (`ha_component_not_in_product_scope`)
**When** il traverse `reason_code_to_cause()`
**Then** il produit `cause_code: "not_in_product_scope"` et un `cause_label` non-null

**Given** le schéma de diagnostic (`reason_code`, `cause_code`, `cause_label`, `cause_action`, étape de pipeline, statut)
**When** un nouveau reason_code est ajouté
**Then** les champs du schéma restent identiques en nom et en type — seules de nouvelles valeurs sont introduites (NFR7, NFR12, FR44)

**Dev notes :**
- AR8 : 5 nouveaux codes additifs — aucun renommage destructif
- `cause_mapping.py` est le seul fichier où la traduction `reason_code → (cause_code, cause_label, cause_action)` est autorisée
- NFR8 : vérifiable par diff du catalogue + exécution du corpus V1.1
- FR43, FR44, FR45

---

### Story 4.4 : Suite de tests de non-régression des 5 étapes — le mainteneur peut tester chaque étape du pipeline en isolation

En tant que mainteneur,
je veux une suite de tests couvrant les cinq étapes du pipeline avec au moins un cas nominal et un cas d'échec par étape, exécutable en isolation sans MQTT, Jeedom ni daemon,
afin de pouvoir faire évoluer n'importe quelle étape en sachant que le corpus de non-régression détectera toute régression.

**Acceptance Criteria :**

**Given** la suite de tests à la fin de cet epic
**When** elle est exécutée
**Then** il existe au moins un cas nominal et un cas d'échec pour chacune des 5 étapes du pipeline (NFR9)
**And** tous les tests s'exécutent sans MQTT, runtime Jeedom ni daemon (isolation)
**And** la suite complète passe

**Given** le corpus de non-régression V1.1
**When** il est exécuté après tous les changements de l'Epic 4
**Then** il passe sans modification — le contrat 4D est intact (NFR11)

**Given** la validation de schéma sur la sortie de diagnostic
**When** le corpus de tests s'exécute
**Then** 100 % des cas de test produisent un diagnostic avec les champs canoniques stables (`reason_code`, `cause_code`, `cause_label`, `cause_action`, étape de pipeline, statut) — hors ajouts additifs documentés (NFR12, FR44)

**Given** une story future qui ouvre un nouveau composant HA (ajout à `PRODUCT_SCOPE`)
**When** elle est revue
**Then** elle doit inclure dans le même incrément : un cas nominal, un cas d'échec et un test de non-régression 4D — ce corpus est la gate obligatoire (FR42, NFR10)

**Dev notes :**
- FR41 : isolation des tests — chaque étape testable sans la pile complète
- FR45 : toute évolution future doit passer ce corpus avant acceptation (NFR11)
- Ce corpus est la gate de référence pour les Epics 5 et 6

---

## Epic 5 — Les projections autorisées sont publiées vers Home Assistant avec un résultat technique traçable

Les projections autorisées par l'étape 4 sont publiées vers Home Assistant. Un échec d'infrastructure est distingué d'une décision produit. La cause principale canonique des étapes amont n'est jamais masquée par un incident technique.

### Story 5.1 : Orchestration des 5 étapes — le sync handler enchaîne éligibilité → mapping → validation HA → décision → publication sans court-circuit

En tant qu'utilisateur,
je veux que l'opération de synchronisation exécute les cinq étapes du pipeline en séquence pour chaque équipement éligible, avec `validate_projection()` appelée entre le mapping et `decide_publication()`, de sorte qu'aucune publication ne puisse contourner la validation structurelle HA,
afin d'avoir la certitude que chaque équipement apparaissant dans Home Assistant a effectivement passé les 5 étapes du pipeline.

**Acceptance Criteria :**

**Given** un équipement éligible avec un mapping valide et une projection HA valide
**When** le sync handler s'exécute
**Then** l'équipement complète les 5 étapes dans l'ordre
**And** l'équipement est publié vers Home Assistant via MQTT

**Given** un équipement pour lequel `validate_projection()` retourne `is_valid=False`
**When** le sync handler s'exécute
**Then** `decide_publication()` est malgré tout appelée (aucun court-circuit — AR10)
**And** `decide_publication()` retourne `should_publish=False`
**And** l'équipement n'est PAS publié en MQTT (NFR2)
**And** le MappingResult contient une trace complète sur ses 3 sous-blocs canoniques (`mapping`, `projection_validity`, `publication_decision`) — le pipeline a 5 étapes, mais le MappingResult n'en porte que 3 sous-blocs

**Given** 100 % des équipements évalués dans une opération de sync
**When** chaque équipement complète le pipeline
**Then** chaque équipement dispose d'un MappingResult avec tous les sous-blocs remplis (valeur explicite ou skip explicite) — aucun trou implicite (AR2, NFR3)

**Given** un test d'intégration du pipeline avec un équipement sans commande action mappé comme `light`
**When** la sync s'exécute
**Then** `reason_code = ha_missing_command_topic` apparaît dans le diagnostic
**And** `publication_decision.should_publish = False`

**Dev notes :**
- AR10 : insertion de `validate_projection()` dans `_do_handle_action_sync()` entre `map()` et `decide_publication()`
- Flux cible : `assess_all → [eligible] map → validate_projection → decide_publication → publish`
- Le pipeline ne court-circuite jamais — même un équipement invalide côté HA produit une `PublicationDecision` explicite
- FR26

---

### Story 5.2 : Résultat de publication traçable — le résultat technique est enregistré séparément de la décision produit et ne masque pas la cause principale canonique

En tant qu'utilisateur,
je veux distinguer un échec d'infrastructure (broker MQTT indisponible) d'une décision produit (le moteur a décidé de ne pas projeter cet équipement), de sorte qu'un incident technique à l'étape 5 ne cache pas la cause principale canonique établie par les étapes amont,
afin que le diagnostic me montre la vraie raison de la décision — et non le symptôme d'un problème d'infrastructure transitoire.

**Acceptance Criteria :**

**Given** un équipement avec `publication_decision.should_publish=True` et le broker MQTT indisponible
**When** la tentative de publication échoue
**Then** l'échec est enregistré avec `reason_code: discovery_publish_failed` (infrastructure — classe 4)
**And** la cause principale canonique reste la raison de décision amont (`should_publish`, `reason`) — non écrasée (FR30)
**And** le diagnostic montre `publication_decision.discovery_published=False` comme champ séparé de la raison de décision

**Given** un équipement avec `publication_decision.should_publish=False`
**When** la publication est explicitement ignorée
**Then** le diagnostic reflète fidèlement que le contournement est une décision produit — et non un échec d'infrastructure (FR28)

**Given** le sous-bloc `publication_decision`
**When** il est lu par la couche de diagnostic
**Then** `should_publish` (décision produit) et `discovery_published` (résultat technique) sont deux champs distincts tous deux présents (FR27)

**Dev notes :**
- FR27 / FR29 / FR30 : séparation décision produit vs résultat technique — contrat de cette story
- Reason_codes de classe 4 : `discovery_publish_failed`, `local_availability_publish_failed` — existants, à intégrer dans le sous-bloc `publication_decision`
- P5 : `reason` toujours non-null dans `PublicationDecision`

---

## Epic 6 — Le diagnostic est explicable et actionnable pour chaque équipement

L'utilisateur voit, pour chaque équipement, une seule cause principale canonique ordonnée par pipeline. Lorsqu'une remédiation existe, une action est proposée. Lorsqu'aucune action n'est possible, le système le dit. Le contrat 4D est préservé par enrichissement pur. C'est ici que la valeur du cycle devient visible : le passage de l'opacité à la compréhension actionnable.

### Story 6.1 : Diagnostic par étape de pipeline — l'utilisateur consulte pour chaque équipement l'étape de blocage et la cause principale canonique unique, ordonnée par pipeline

En tant qu'utilisateur,
je veux voir, pour chaque équipement, l'étape de pipeline la plus avancée atteinte et la cause principale canonique unique lorsque le pipeline a été bloqué, toujours ordonnée par l'étape qui a effectivement bloqué,
afin de savoir exactement où regarder et ce qu'il s'est passé — un équipement, une cause, une étape, une réponse.

**Acceptance Criteria :**

**Given** un équipement bloqué à l'étape 1 (inéligibilité)
**When** l'utilisateur lit le diagnostic
**Then** l'étape de blocage est « Étape 1 — Éligibilité »
**And** seule la cause de l'étape 1 est exposée comme cause principale — aucune cause d'étape aval n'est surfacée (FR3, FR35)

**Given** un équipement bloqué à l'étape 2 (échec de mapping)
**When** l'utilisateur lit le diagnostic
**Then** l'étape de blocage est « Étape 2 — Mapping »
**And** seule la cause de l'étape 2 est la cause principale — les problèmes potentiels d'étapes 3 ou 4 ne sont pas exposés simultanément

**Given** un équipement bloqué à l'étape 3 (invalidité HA)
**When** l'utilisateur lit le diagnostic
**Then** l'étape de blocage est « Étape 3 — Validation HA »
**And** la cause est `ha_missing_*` ou `ha_component_unknown` — distincte d'un échec de mapping

**Given** un équipement ayant complété les 5 étapes avec succès
**When** l'utilisateur lit le diagnostic
**Then** l'étape montrée est « Étape 5 — Publié »
**And** aucune cause de blocage n'est affichée (FR31, FR4)

**Given** le diagnostic complet sur tous les équipements d'une synchronisation
**When** l'utilisateur parcourt la vue globale
**Then** chaque équipement affiche une seule cause principale (NFR4)
**And** aucun équipement n'a un champ de cause vide ou contradictoire

**Dev notes :**
- FR35 : cause principale unique — l'ordre stable du pipeline le garantit (NFR4)
- FR3 / FR4 : cause principale = étape qui a bloqué ; étape la plus avancée = aucun blocage
- Le diagnostic lit les sous-blocs du MappingResult — il restitue, il n'interprète pas

---

### Story 6.2 : Enrichissement additif du contrat 4D — projection_validity est ajouté comme sous-bloc pur sans modifier les champs existants

En tant que mainteneur,
je veux que le sous-bloc `projection_validity` soit ajouté dans `_build_traceability()` par enrichissement pur — aucun champ existant supprimé, renommé ni déplacé — de sorte que les consommateurs V1.1 du contrat 4D continuent de fonctionner sans modification,
afin que le cycle apporte de nouvelles capacités de diagnostic sans casser la rétrocompatibilité.

**Acceptance Criteria :**

**Given** la sortie de diagnostic d'une opération de sync
**When** elle est comparée au schéma baseline V1.1
**Then** tous les champs existants sont présents avec les mêmes noms, types et sémantiques (NFR7)
**And** le corpus de non-régression V1.1 passe sans modification

**Given** la sortie de diagnostic enrichie pour un équipement ayant passé l'étape 3
**When** elle est inspectée
**Then** un sous-bloc `projection_validity` est présent avec `is_valid`, `missing_fields`, `missing_capabilities`, `reason_code` (AR11)

**Given** la sortie de diagnostic enrichie pour un équipement n'ayant pas atteint l'étape 3 (mapping échoué)
**When** elle est inspectée
**Then** le sous-bloc `projection_validity` est présent avec `is_valid: null` et `reason_code: "skipped_no_mapping_candidate"` — il n'est pas absent (AR2, P7)

**Given** un test de diff de schéma
**When** il est exécuté contre le baseline V1.1 et la sortie enrichie
**Then** le diff montre uniquement des champs additifs — aucune suppression, aucun renommage (NFR12, FR44)

**Dev notes :**
- AR11 : `_build_traceability()` enrichit uniquement par ajout — P7
- NFR12 : schéma stable sur 100 % des tests de cohérence hors ajouts additifs documentés
- Le sous-bloc `projection_validity` est toujours présent (même si `is_valid: null`) — garantit la cohérence du schéma
- FR34
- Execution note (correct-course 2026-04-21) : si un gate terrain revele avant 6.3 un echec de semantique honnete `cause_label` / `cause_action`, ne pas transformer 6.2 en gros chantier de rattrapage `projection_validity`. Re-aligner d'abord la promesse story-level, garder 6.2 ouverte, puis faire de 6.3 la prochaine story requise.
- Disposition post-retro 2026-04-22 : l'intention structurelle non livree de 6.2 n'est plus executee dans Epic 6. Elle est re-homee vers `pe-epic-7`. Epic 6 se clot sur l'explicabilite par etape et la semantique honnete ; aucune reprise de developpement ne repart de 6.2.

---

### Story 6.3 : Traduction cause canonique → cause_label / cause_action stables — action proposée uniquement si une remédiation utilisateur existe

En tant qu'utilisateur,
je veux que chaque cause d'échec canonique du moteur soit traduite en un libellé stable et lisible, et qu'une action soit proposée uniquement lorsqu'une remédiation accessible par l'utilisateur existe — et lorsqu'il n'y en a pas, que le système le dise explicitement plutôt que de rester silencieux,
afin que le diagnostic soit toujours actionnable quand quelque chose peut être fait, et honnête quand rien ne peut l'être.

**Acceptance Criteria :**

**Given** un équipement bloqué par un échec de mapping (classe 1)
**When** l'utilisateur lit le diagnostic
**Then** `cause_label` est renseigné (non-null, lisible par un humain)
**And** `cause_action` est renseigné uniquement si l'utilisateur peut corriger le mapping (ex. corriger le generic_type dans Jeedom) — sinon il est explicitement null (FR32)

**Given** un équipement bloqué par une invalidité HA (classe 2, ex. `ha_missing_command_topic`)
**When** l'utilisateur lit le diagnostic
**Then** `cause_label` est « Projection HA incomplète — commande requise absente » (ou équivalent)
**And** `cause_action` est null ou indique explicitement qu'aucune action utilisateur directe n'existe (FR33) — la contrainte structurelle dépend de l'appareil lui-même

**Given** un équipement bloqué par une gouvernance de scope (`ha_component_not_in_product_scope`)
**When** l'utilisateur lit le diagnostic
**Then** `cause_label` est renseigné (non-null)
**And** `cause_action` est null ou indique « non ouvert dans ce cycle » — pas « configurer X » (FR33)

**Given** un équipement bloqué par une exclusion de scope contrôlée par l'utilisateur
**When** l'utilisateur lit le diagnostic
**Then** `cause_action` pointe explicitement vers l'action de scope (ex. « Retirer cet équipement des exclusions »)

**Given** 100 % des équipements dans le diagnostic
**When** le champ `cause_label` est inspecté
**Then** il n'est jamais null — chaque équipement a une explication de cause lisible par un humain (FR32)

**Dev notes :**
- FR32 : `cause_label` toujours renseigné ; `cause_action` uniquement si remédiation utilisateur existe
- FR33 : pas de fausse promesse d'action — si rien n'est actionnable par l'utilisateur, l'exprimer explicitement
- Mise à jour de `cause_mapping.py` pour couvrir tous les nouveaux reason_codes des classes 2 et 3
- Note UX : story qui modifie `cause_label` / `cause_action` sur une surface critique → artefact visuel prescriptif + gate terrain avant done
- Regle d'execution : gate terrain "no faux CTA" obligatoire sur les cas step 2 / step 3 / step 4
- FR32, FR33

---

## Epic 7 — L'actionnabilite devient une capacite produit reelle par ouverture gouvernee du perimetre HA

L'utilisateur ne voit une action que lorsqu'elle repose sur une surface produit reellement ouverte, supportee et testee. Le mainteneur ouvre progressivement le perimetre HA selon FR40 / NFR10, expose `projection_validity` de facon additive, puis n'autorise des CTA utilisateur que pour les remediations effectivement disponibles.

### Story 7.1 : Enrichissement additif du contrat 4D — `projection_validity` est expose de bout en bout sans regression sur le schema canonique

En tant que mainteneur,
je veux exposer le sous-bloc `projection_validity` de bout en bout dans le contrat 4D sans supprimer, renommer ni deplacer aucun champ existant,
afin de rendre visible la realite structurelle de la projection avant toute promesse d'action utilisateur.

**Acceptance Criteria :**

**Given** la sortie de diagnostic d'une operation de sync
**When** elle est comparee au schema baseline du cycle
**Then** tous les champs historiques restent presents avec les memes noms, types et semantiques
**And** le diff ne montre que des ajouts additifs documentes

**Given** un equipement ayant atteint l'etape 3
**When** le diagnostic est inspecte
**Then** `projection_validity` est present avec `is_valid`, `missing_fields`, `missing_capabilities`, `reason_code`

**Given** un equipement n'ayant pas atteint l'etape 3
**When** le diagnostic est inspecte
**Then** `projection_validity` est tout de meme present avec un statut explicite de skip

**Given** une evolution de cette story
**When** elle est revue
**Then** elle ne modifie pas `cause_action` et n'introduit aucun nouveau CTA utilisateur

**Dev notes :**
- reprend l'intention structurelle non livree de la 6.2 initialement planifiee
- AR11 / FR34 / NFR12
- aucun recalibrage UX ni wording opportuniste dans cette story

---

### Story 7.2 : Vague cible HA — les types candidats sont modelises dans le registre comme `connus`, avec contraintes explicites et perimetre borne

En tant que mainteneur,
je veux definir une premiere vague d'ouverture HA explicitement bornee dans le registre, avec contraintes documentees et cas cibles identifies,
afin de preparer une ouverture produit pilotable plutot qu'une extension opportuniste du scope.

**Acceptance Criteria :**

**Given** la vague cible `pe-epic-7`
**When** elle est documentee dans le registre et les artefacts de story
**Then** chaque type vise dispose d'une entree explicite dans `HA_COMPONENT_REGISTRY` avec `required_fields` et `required_capabilities`

**Given** un type hors vague
**When** l'epic est execute
**Then** il n'entre pas implicitement dans la vague cible et ne devient pas ouvrable par effet de bord

**Given** la definition de la vague
**When** elle est relue
**Then** elle reste bornee a un ensemble restreint de types HA testables dans le meme increment

**Dev notes :**
- AR4 / AR6
- cette story construit l'etat `connu`, pas l'etat `ouvert`
- aucun changement de `PRODUCT_SCOPE` dans cette story

---

### Story 7.3 : Validation de projection de la vague cible — cas nominaux et cas d'echec representatifs rendent les types `validables`

En tant que mainteneur,
je veux prouver que les types de la vague cible sont structurellement validables par `validate_projection()`,
afin de satisfaire la condition 2 de FR40 avant toute ouverture produit.

**Acceptance Criteria :**

**Given** chaque type de la vague cible
**When** `validate_projection()` est executee sur un cas nominal representatif
**Then** `is_valid=True` est obtenu sans dependance a la pile complete

**Given** chaque type de la vague cible
**When** `validate_projection()` est executee sur un cas d'echec representatif
**Then** `is_valid=False` est obtenu avec un `reason_code` explicite et stable

**Given** les etats du registre
**When** un type a des preuves nominales et d'echec
**Then** il est traite comme `validable`, distinct de `ouvert`

**Dev notes :**
- FR42 / AR7 / AR6
- tests executables en isolation
- aucun CTA utilisateur nouveau dans cette story

---

### Story 7.4 : Gouvernance d'ouverture de la vague cible — `PRODUCT_SCOPE` n'evolue que sous FR40 / NFR10 dans le meme increment

En tant que mainteneur,
je veux ouvrir les types de la vague cible dans `PRODUCT_SCOPE` uniquement lorsque les trois preuves FR40 sont reunies dans le meme increment,
afin que l'ouverture produit soit gouvernee, testable et non arbitraire.

**Acceptance Criteria :**

**Given** un type de la vague cible propose pour ouverture
**When** son ajout a `PRODUCT_SCOPE` est revu
**Then** l'increment contient simultanement : l'entree de registre, les preuves nominales et d'echec de validation, et un test de non-regression diagnostic

**Given** une tentative d'ajout a `PRODUCT_SCOPE` sans ces preuves
**When** la suite FR40 / NFR10 est executee
**Then** l'ajout est rejete explicitement

**Given** un type ouvert de la vague
**When** le cycle s'execute
**Then** il est distingue des types seulement `connus` ou `validables`

**Dev notes :**
- FR39 / FR40 / NFR10 / AR13
- story unique autorisee a modifier `PRODUCT_SCOPE`
- toute regression du diagnostic bloque la cloture

---

### Story 7.5 : Exposition d'actions utilisateur uniquement sur les surfaces reelles et supportees

En tant qu'utilisateur,
je veux voir une action seulement lorsqu'elle correspond a une remediation reellement disponible dans jeedom2ha ou Jeedom standard,
afin que le diagnostic reste honnete et utile apres l'ouverture produit.

**Acceptance Criteria :**

**Given** un equipement de la vague ouverte avec une remediation effectivement disponible
**When** le diagnostic est affiche
**Then** `cause_action` pointe vers cette action reelle, executable et supportee

**Given** un equipement pour lequel aucune remediation utilisateur directe n'existe
**When** le diagnostic est affiche
**Then** `cause_action` reste `null`
**And** la couche d'affichage conserve le message standardise sans faux CTA

**Given** une story touchant `cause_action` pour la vague ouverte
**When** elle est validee
**Then** elle passe un gate terrain `no faux CTA` sur des cas reels representatifs de la vague

**Dev notes :**
- FR32 / FR33 reappliques uniquement aux surfaces reelles ouvertes par l'epic
- aucun retour a un CTA speculatif du type "choisir manuellement le type"
- la story ne promet pas de remediation generique hors vague cible
