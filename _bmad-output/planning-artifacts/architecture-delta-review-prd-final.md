---
type: architecture-delta-review
date: '2026-04-10'
author: Alexandre
sourceArchitecture: _bmad-output/planning-artifacts/architecture-projection-engine.md
sourcePRD: _bmad-output/planning-artifacts/prd.md
verdict: delta-mineur
blocksEpics: false
---

# Revue d'alignement PRD final → Architecture du moteur de projection

_Ce document est une revue de delta ciblée. Il ne réécrit pas l'architecture. Il identifie les décisions nouvelles ou les précisions introduites par le PRD final (2026-04-10) qui ne sont pas explicitement capturées dans `architecture-projection-engine.md` (2026-04-09)._

---

## Périmètre et méthode

**Documents analysés :**
- `architecture-projection-engine.md` — architecture complète du moteur de projection, statut `complete`, 8 décisions (D1–D8), 8 patterns (P1–P8).
- `prd.md` — PRD final cycle moteur de projection explicable, statut `complete`, dernière édition 2026-04-10 (NFR rendues auditables, FR10/FR31/FR32/FR39/FR40/FR44 précisées).

**Méthode :** lecture comparée sur les quatre points demandés, identification des tensions ou absences, classification du delta.

---

## Point 1 — Réalignement du registre HA avec le PRD final

### Ce que dit l'architecture

Le registre HA (`D3`) a deux niveaux :
- **composant connu** : présent dans `HA_COMPONENT_REGISTRY` avec ses contraintes structurelles décrites ;
- **composant ouvert** : présent dans `PRODUCT_SCOPE`, liste `["light", "cover", "switch"]` pour V1.x.

La formulation est : "Le fichier Excel HA est la source de vérité pour alimenter ce registre et ses tests, pas un engagement produit. L'existence d'un composant dans l'Excel ne crée aucune obligation de l'ouvrir dans le scope produit." La décision ouverte item 14 reconnaît que "quels composants ouvrir, dans quel ordre, avec quelles conditions" n'est pas encore arrêtée.

### Ce que dit le PRD

- **FR37** introduit un **troisième état explicite** : "composant connu", "composant validable", "composant ouvert".
- **FR39** pose le critère d'ouverture comme une conséquence de trois conditions vérifiables : contraintes modélisées dans le registre + validation structurelle aboutissant sur des cas nominaux représentatifs + absence de régression sur le contrat 4D.
- **FR40** reformule FR39 comme contrat de gouvernance : les trois conditions doivent être satisfaites *simultanément* avant de marquer un composant comme ouvert.
- L'Executive Summary pose la règle générale : "Tout composant HA dont les contraintes sont connues par le moteur, validées et testables, et pour lequel la projection est structurellement correcte, doit pouvoir être ouvert."
- **FR38** précise explicitement que le registre ne doit pas devenir "une frontière produit arbitraire".

### Delta

| Aspect | Architecture | PRD | Statut |
|---|---|---|---|
| Niveaux du registre | 2 (connu / ouvert) | 3 (connu / validable / ouvert) | Précision requise |
| Critère d'ouverture | Décision ouverte (item 14) — non arrêtée | FR39/FR40 — critère explicite en 3 conditions | Décision close |
| Nature du PRODUCT_SCOPE | Liste fixe V1.x `["light", "cover", "switch"]` | Résultat dynamique de l'application de FR39-FR40 au cycle courant | Tension à clarifier |

### Modèle verrouillé : 3 états du registre HA

Les trois états suivants sont le contrat de référence pour toutes les stories du cycle. Ils sont distincts, non substituables, et ne doivent pas être confondus avec les étapes du pipeline ni avec le statut produit d'un équipement.

| État | Définition | Mécanisme technique |
|---|---|---|
| **connu** | Composant présent dans `HA_COMPONENT_REGISTRY` avec ses contraintes structurelles modélisées. Le moteur connaît les champs requis et les capabilities nécessaires pour ce composant. | Entrée dans `HA_COMPONENT_REGISTRY` |
| **validable** | Composant `connu` pour lequel `validate_projection()` aboutit positivement sur des cas nominaux représentatifs. La projection est structurellement correcte au sens HA. L'état `validable` est une propriété du composant, vérifiable hors runtime et indépendamment de tout équipement particulier. | Résultat de `validate_projection()` sur les cas de test requis, exécutable en isolation |
| **ouvert** | Composant `validable` autorisé à la publication dans le cycle courant par décision de gouvernance explicite. L'ouverture exige la satisfaction simultanée des 3 conditions de FR40 : contraintes modélisées dans le registre + validation positive sur des cas nominaux + tests de non-régression dans le même incrément. | Présence dans `PRODUCT_SCOPE` après satisfaction de FR40 |

**Règle de séquence :** `connu` → `validable` → `ouvert`. Un composant ne peut pas être `ouvert` sans être `validable`, ni `validable` sans être `connu`.

**Frontières de non-confusion :**
- L'état du registre (`connu` / `validable` / `ouvert`) est distinct de l'état du pipeline (étapes 1–5). Un composant peut être `connu` dans le registre sans qu'un équipement particulier ait encore passé l'étape 3.
- L'état `validable` est une propriété statique du composant (vérifiable en isolation, hors d'un cycle de synchronisation), pas un résultat calculé pour un équipement.
- L'état `ouvert` est une décision de gouvernance de cycle, pas un résultat produit par le pipeline à l'exécution.

**Sur `PRODUCT_SCOPE` :** sa valeur de départ pour le cycle est `["light", "cover", "switch"]` (héritage V1.1). Ce n'est pas un plafond : tout composant du registre satisfaisant les 3 conditions de FR40 dans le cycle courant peut y être ajouté. Le `PRODUCT_SCOPE` est un artefact mutable de cycle, gouverné par FR40.

**Sur l'item 14 de l'architecture — statut : FERMÉ.** L'item 14 ("Extension du registre scope produit — quels composants ouvrir, dans quel ordre, avec quelles conditions") est **fermé** par FR39/FR40. La condition d'ouverture est un contrat explicite et vérifiable. Il n'est pas seulement recadré — la décision est close et son contenu est FR40. Toute histoire qui ouvre un composant doit vérifier FR40 comme acceptance criterion obligatoire.

**Pas de refonte architecturale requise.** D3 reste valide. Impact attendu sur les acceptance criteria des stories de gouvernance du registre (critère d'ouverture = FR40), sur les invariants de contrat (les 3 états doivent être testables en isolation), et sur le mécanisme de gouvernance (toute modification de `PRODUCT_SCOPE` exige les tests FR40 dans le même incrément).

---

## Point 2 — Clarification de l'étape 4 "Décision de publication"

### Ce que dit l'architecture

L'étape 4 dans le pipeline est décrite comme :
> "Décision de publication — Entrée : MappingCandidate validé + confidence_policy + registre scope produit — Sortie : PublicationDecision (should_publish, reason) — Échecs : low_confidence (policy filter), ha_component_not_in_product_scope"

`D6` dit que les overrides inter-étapes sont "non engagés pour le prochain cycle". Les overrides utilisateur existants (inclusion/exclusion de périmètre) restent en étape 1.

### Ce que dit le PRD

**FR22** : "Le système peut porter en étape 4 la décision finale de publication à partir d'une projection déjà modélisée et validée."

**FR23** : "Le système peut appliquer en étape 4 des **politiques produit explicites, des exceptions de gouvernance et des overrides autorisés** sans les confondre avec la validité structurelle HA."

**FR24** : distinguer blocage de décision explicite d'un composant HA invalide, inconnu, ou d'un échec de mapping.

**FR25** : overrides avancés — classifier post-MVP dans le scope.

**Parcours 2** : "S'il échoue en étape 4, il explique que la décision finale de publication a été bloquée par une **politique produit explicite, une exception de gouvernance ou un override**, et non par une projection implicitement 'hors liste'."

### Analyse de la composition décisionnelle de l'étape 4

Le PRD nomme trois sous-critères que l'architecture n'articule pas explicitement :

| Sous-critère PRD | Correspondance architecture | Statut |
|---|---|---|
| Validité HA | Héritée de l'étape 3 — `projection_validity.is_valid` | Déjà capturé (D1, D7) |
| Politiques produit | `confidence_policy` + `PRODUCT_SCOPE` | Partiellement capturé (D3, D4) |
| Gouvernance | *(non nommée explicitement dans l'architecture)* | Absent de la terminologie |
| Overrides autorisés | D6 : portée étape 1 ; inter-étapes différés | Partiellement capturé |

**Qu'est-ce que "gouvernance" au sens du PRD ?**

En lisant FR23 et le Parcours 2, la "gouvernance" désigne des décisions explicites de produit qui bloquent la publication d'un composant pourtant techniquement valide au sens de l'étape 3 — par exemple, un composant `sensor` dont la validation HA est positive mais que le cycle courant a décidé de ne pas ouvrir encore. C'est exactement ce que `ha_component_not_in_product_scope` modélise déjà dans l'architecture.

**La gouvernance est donc déjà dans l'architecture**, mais elle n'est pas nommée et ses contours ne sont pas distingués de la "politique produit" (confidence). La distinction FR23 demande est :
- `low_confidence` → politique produit (filtrage par confiance du mapping)
- `ha_component_not_in_product_scope` → gouvernance (composant volontairement non ouvert)

Ces deux raisons sont déjà distinctes dans le pipeline — `low_confidence` filtre sur la confiance du mapping (input venant de l'étape 2), et `ha_component_not_in_product_scope` filtre sur l'appartenance au `PRODUCT_SCOPE` (input venant du registre). La distinction existe ; elle n'est pas articulée comme "politique" vs "gouvernance".

**Concernant les overrides FR25 :**
FR25 (overrides avancés) est explicitement dans les capacités post-MVP du PRD. Il ne crée pas de delta bloquant pour le MVP.

### Contrat formel de l'étape 4 — hiérarchie et périmètre

**Hiérarchie stricte des responsabilités :**

1. **La validité HA appartient exclusivement à l'étape 3.** L'étape 4 consomme `projection_validity.is_valid` comme un fait établi. Elle ne remappe pas, ne revalide pas, ne réévalue aucune contrainte structurelle HA.
2. **L'étape 4 arbitre uniquement la publication finale**, à partir de quatre inputs dont un seul est la projection validée :
   - la projection déjà validée (`projection_validity.is_valid == True`) — héritée de l'étape 3, non réévaluée ;
   - la politique produit (`confidence_policy` — filtrage sur la confiance du mapping issu de l'étape 2) ;
   - la gouvernance d'ouverture (`PRODUCT_SCOPE` — filtrage sur l'état `ouvert` du composant) ;
   - les overrides autorisés (portée étape 1 pour le MVP ; overrides inter-étapes différés post-MVP, D6).

**Deux raisons distinctes de `should_publish=False` en étape 4 :**

| Raison | `reason_code` | Source de la décision | Ce que l'utilisateur voit (FR24) |
|---|---|---|---|
| Politique de confiance | `low_confidence` | `confidence_policy` — confiance du mapping (étape 2) insuffisante | "Le mapping n'est pas assez certain pour publier" |
| Gouvernance d'ouverture | `ha_component_not_in_product_scope` | `PRODUCT_SCOPE` — composant `validable` mais pas encore `ouvert` dans ce cycle | "Ce type d'entité n'est pas ouvert dans ce cycle" |

Ces deux reason_codes sont déjà dans l'architecture. Le contrat ci-dessus les nomme et les distingue explicitement pour les stories et les tests.

**Formulation de contrat courte, directement exploitable pour les stories :**
> L'étape 4 reçoit une projection déjà valide au sens HA (étape 3 passée positivement). Elle pose une seule question : "La politique produit et la gouvernance autorisent-elles la publication de cette projection dans ce cycle ?" Elle ne repose aucune question de validité HA — cette question a déjà une réponse définitive à l'issue de l'étape 3.

**Pas de refonte architecturale requise.** Les reason_codes existent. Impact attendu sur la design note de la story "Étape 4 — Décision de publication" (hiérarchie à documenter dans le code et dans les commentaires de la fonction `decide_publication`), sur le critère d'acceptation FR24 (l'utilisateur distinguish les deux raisons dans le diagnostic), et sur les invariants de test du pipeline (étape 3 et étape 4 ne doivent pas être fusionnées dans les assertions).

---

## Point 3 — NFR auditables : nouveaux invariants ou précisions architecturales ?

### Les NFR éditées (2026-04-10)

Les NFR ont été rendues auditables avec des critères de vérification explicites ("vérifié par..."). Les NFR pertinentes pour l'architecture :

| NFR | Correspondance architecture | Nouveau invariant ? |
|---|---|---|
| NFR1 (déterminisme 100%) | Pipeline ordonné, étapes pures → D4 | Non — déjà garanti par les fonctions pures |
| NFR2 (0% publication avec validation HA négative) | Invariant D7, P1 | Non — déjà le contrat de D7 |
| NFR3 (100% équipements avec résultat explicite) | Pattern P1 trace complète | Non — déjà P1, aucun trou implicite |
| NFR4 (cause principale unique) | Invariant d'évaluation ordonnée | Non — déjà dans le pipeline 5 étapes |
| NFR5 (composants ouverts satisfont les contraintes structurelles) | D3 + étape 3 | Non — déjà le contrat de la validation |
| NFR6 (0 source de vérité concurrente) | Fondation V1.1 héritée | Non — verrouillé dans l'architecture |
| NFR7 (4D rétrocompatible 100%) | D5 + P7 enrichissement additif | Non — déjà D5/P7 |
| NFR8 (0 reason_code renommé/supprimé) | D5 migration additive | Non — déjà D5 |
| NFR9 (5 étapes × cas nominal + cas d'échec) | Structure de tests prévue | Non — pas un invariant code |
| NFR10 (ouverture composant = même incrément avec tests) | Non modélisé dans l'architecture | **Oui — invariant de cycle** |
| NFR11 (0 régression corpus non-régression) | D5 + approche additive | Non — applicable via tests |
| NFR12 (schéma diagnostic stable) | D1 + P7 | Non — déjà D1/P7 |

**NFR10 — seul invariant nouveau :**

NFR10 pose un contrat de cycle : "l'ouverture d'un composant HA doit être accompagnée, dans le même incrément, d'au moins un cas nominal, un cas d'échec de validation et un test de non-régression diagnostic."

Ce n'est pas un invariant de code (aucune API à modifier). C'est un **invariant de gouvernance de cycle** : il conditionne dans quels incréments une ligne `PRODUCT_SCOPE` peut être éditée. Il est cohérent avec FR39/FR40 du Point 1 — c'est la même règle d'ouverture gouvernée. L'architecture peut le noter comme règle de gouvernance associée à D3, sans créer de nouvelle décision architecturale.

**Conclusion Point 3 : aucun nouveau invariant de code.**  
NFR10 crée un invariant de processus (story acceptance criteria), déjà implicitement couvert par FR39/FR40. Il renforce la règle existante, ne l'infléchit pas.

---

## Point 4 — Classe "scope produit" : mécanisme résiduel ou frontière active ?

### Ce que dit l'architecture

Le `PRODUCT_SCOPE` est :
- une liste statique `["light", "cover", "switch"]` pour V1.x ;
- une frontière active de l'étape 4 : un composant non listé produit `ha_component_not_in_product_scope` ;
- distinct du registre des composants "connus" (qui contient aussi `sensor`, `binary_sensor`, `button`, `number`, `select`, `climate`).

La nature de cette frontière est de limiter les publications aux composants "ouverts" pour le cycle courant.

### Ce que dit le PRD

L'Executive Summary est explicite : "Le scope fonctionnel n'est plus borné par une liste fermée de types HA prédéfinis."

FR39 pose que tout composant satisfaisant les 3 conditions doit *pouvoir être ouvert* — pas "sera ouvert dans un futur cycle", mais "peut être ouvert dans le cycle courant si les conditions sont satisfaites".

FR38 : "sans faire du registre une frontière produit arbitraire".

### Tension identifiée

L'architecture présente le `PRODUCT_SCOPE` comme une liste fixe établie avant le cycle. Le PRD le repositionne comme une conséquence de l'application de critères pendant le cycle. Ce ne sont pas des positions incompatibles techniquement, mais leur lecture crée une ambiguïté sur la question : "est-ce que `sensor` et `binary_sensor` peuvent être ouverts dans ce cycle ?"

Réponse: oui, selon FR39/FR40, si le registre les couvre (D3 les inclut déjà), si la validation étape 3 aboutit (D4 peut le faire), et si les tests requis par NFR10 sont fournis. Le mécanisme `PRODUCT_SCOPE` reste valide — mais son contenu n'est pas préfixé à [light, cover, switch] pour la durée du cycle.

**Le scope produit reste un mécanisme de frontière active dans le pipeline** (étape 4, reason_code `ha_component_not_in_product_scope` valide). Mais il n'est pas une frontière "closed-by-default" — c'est une frontière "governed-open" : tout composant du registre peut franchir la frontière si et seulement si les conditions de FR39/FR40 sont remplies.

**Précision requise :**

La description de `PRODUCT_SCOPE` dans D3 doit être accompagnée d'une note : "Sa valeur de départ pour le cycle est `["light", "cover", "switch"]` (héritage V1.1). L'objectif du cycle est d'y ajouter tous les composants du registre satisfaisant FR39/FR40. Le reason_code `ha_component_not_in_product_scope` reste valide pour les composants intentionnellement non ouverts dans l'incrément courant."

**Pas de refonte architecturale requise.** Le mécanisme `PRODUCT_SCOPE` et son implémentation D3 sont conservés. Impact attendu sur les stories : acceptance criteria de la story "Gouvernance registre" (valeur de départ + règle de mutation via FR40), et sur les invariants de contrat (tout test concernant le scope produit doit explicitement distinguer les composants `connus`, `validables` et `ouverts`).

---

## Synthèse des deltas

| Point | Sujet | Nature du delta | Bloquant pour epics ? |
|---|---|---|---|
| 1 | Registre HA : 3 états verrouillés (connu/validable/ouvert) + item 14 fermé par FR39/FR40 | Contrat de référence verrouillé — acceptance criteria, invariants de test, mécanisme de gouvernance | Non — précisions portées dans les stories |
| 2 | Étape 4 : hiérarchie formelle (validité HA = étape 3 exclusive ; étape 4 = arbitrage publication) | Contrat formel court — design note, critère FR24, invariants de test pipeline | Non — précisions portées dans les stories |
| 3 | NFR auditables : NFR10 seul invariant nouveau, de cycle (pas de code) | Invariant de processus — acceptance criteria obligatoire pour toute ouverture de composant | Non — déjà couvert par FR39/FR40 |
| 4 | PRODUCT_SCOPE : frontière governed-open, valeur de départ non plafond | Acceptance criteria story + invariants de contrat | Non — précisions portées dans les stories |

---

## Verdict

**Delta mineur — non bloquant pour le découpage en epics/stories.**

L'architecture `architecture-projection-engine.md` est **structurellement et techniquement valide** pour fonder le découpage en epics. Les décisions D1–D8 et les patterns P1–P8 restent inchangés. Aucune refonte architecturale n'est requise.

Les précisions apportées par cette revue sont de nature contractuelle et de gouvernance, pas de nature architecturale :

1. **Modèle du registre HA verrouillé en 3 états** (`connu` / `validable` / `ouvert`) — contrat de référence pour les stories. Item 14 de l'architecture : **fermé** par FR39/FR40, pas seulement recadré.

2. **Contrat formel de l'étape 4** — hiérarchie explicitée : validité HA = étape 3 exclusive et définitive ; étape 4 = arbitrage publication uniquement. Deux raisons distinctes de refus nommées et distinguables dans le diagnostic (FR24).

3. **NFR10** — invariant de processus de cycle (pas de code) : toute ouverture de composant dans `PRODUCT_SCOPE` exige les tests FR40 dans le même incrément.

4. **`PRODUCT_SCOPE`** — frontière `governed-open`, valeur de départ non plafond : tout composant `validable` satisfaisant FR40 peut être ouvert dans ce cycle.

Ces quatre précisions sont des **acceptance criteria et invariants de contrat** à porter dans les stories correspondantes. Elles ne modifient pas `architecture-projection-engine.md`.

**Le cycle peut avancer vers `bmad-create-epics` sans condition préalable.**

---

## Précisions concrètes à porter dans les stories

Ces éléments n'exigent pas de modifier `architecture-projection-engine.md`. Ils doivent figurer explicitement dans les stories et epics correspondants pour éviter toute ambiguïté d'implémentation.

### Pour la story "Registre HA et validation" (Feature 7)

- Les trois états `connu` / `validable` / `ouvert` sont le contrat de référence (voir section Point 1). Toute assertion de test doit les distinguer explicitement.
- Acceptance criteria d'ouverture d'un composant (FR40 — obligatoire) : contraintes dans `HA_COMPONENT_REGISTRY` + cas nominaux et cas d'échec dans `test_ha_component_registry.py` + test de non-régression sur le contrat 4D, dans le même incrément.
- Le `PRODUCT_SCOPE` part de `["light", "cover", "switch"]`. Tout composant `validable` du registre peut y être ajouté si FR40 est satisfait dans ce cycle.
- **Item 14 de l'architecture : fermé.** Les conditions d'ouverture sont FR40. Ce n'est pas un critère à définir lors du découpage — il est défini ici et s'applique immédiatement.

### Pour la story "Étape 4 — Décision de publication" (Feature 4)

- L'étape 4 ne revalide pas la projection HA. Invariant de test : toute assertion sur `should_publish` en étape 4 doit partir d'un `projection_validity.is_valid == True` (étape 3 déjà passée).
- Documenter dans le code les deux raisons distinctes de `should_publish=False` : `low_confidence` (politique produit) et `ha_component_not_in_product_scope` (gouvernance d'ouverture). Voir le contrat formel au Point 2.
- Acceptance criteria FR24 : le diagnostic permet à l'utilisateur de distinguer un refus de politique et un refus de gouvernance — les deux doivent produire un `cause_label` différent.
- Les overrides avancés (FR25) sont post-MVP — aucun code dans ce cycle.

### Pour la story "Diagnostic explicable" (Feature 6, FR32/FR44)

- Les champs canoniques du contrat diagnostic (`reason_code`, `cause_code`, `cause_label`, `cause_action`, étape de pipeline, statut) sont stables par construction additive — aucune migration destructive.
- NFR12 : le schéma doit rester stable sur 100% des tests de cohérence hors ajouts additifs documentés. Critère de vérification : diff de schéma automatisé sur le corpus de non-régression V1.1.
