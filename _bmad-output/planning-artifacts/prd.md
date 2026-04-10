---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-04-09.md'
  - '_bmad-output/planning-artifacts/architecture-projection-engine.md'
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 0
  projectDocs: 1
workflowType: 'prd'
status: 'complete'
date: '2026-04-09'
lastEdited: '2026-04-10'
editHistory:
  - date: '2026-04-10'
    changes:
      - 'Rendu les exigences non fonctionnelles auditables'
      - 'Rendu FR10, FR31, FR32, FR39, FR40 et FR44 plus observables'
      - 'Complété le frontmatter avec la date documentaire'
classification:
  projectType: 'interoperability_middleware / home_automation_bridge_plugin'
  domain: 'smart_home / home_automation_interoperability'
  complexity: 'high'
  projectContext: 'brownfield_discovery_greenfield_implementation'
---

# Product Requirements Document - jeedom2ha

**Author:** Alexandre
**Date:** 2026-04-09

## Executive Summary

Le cycle **moteur de projection explicable** formalise un changement de paradigme pour jeedom2ha. Le produit ne doit plus être compris comme un bridge à périmètre fermé qui publie ce qu'il sait publier "au mieux", mais comme un moteur de projection déterministe qui décide explicitement, pour chaque équipement Jeedom, s'il peut être projeté proprement vers Home Assistant et pourquoi.

Le cœur du cycle est un pipeline canonique à 5 étapes : **Éligibilité → Mapping candidat → Validation HA → Décision de publication → Publication MQTT**. La validation Home Assistant en étape 3 est obligatoire. Elle devient le verrou qui sépare un mapping plausible d'une projection réellement publiable. Aucun contournement "best effort" n'est autorisé : si la projection n'est pas structurellement valide côté HA, elle ne doit pas être publiée.

Le scope fonctionnel n'est plus borné par une liste fermée de types HA prédéfinis. Il est fondé sur un **registre des composants HA** séparé de la logique de mapping et sur la validité réelle de projection. Tout composant HA dont les contraintes sont connues par le moteur, validées et testables, et pour lequel la projection est structurellement correcte, doit pouvoir être ouvert. À l'inverse, tout cas invalide, ambigu ou hors scope doit être diagnostiqué explicitement.

Le cycle conserve intégralement les acquis V1.1 : Jeedom reste la source de vérité métier, le contrat diagnostic **4D** reste canonique, et la rétrocompatibilité des `reason_code` est préservée par enrichissement additif, notamment pour l'introduction des échecs de validité HA. Le résultat attendu n'est pas seulement plus de couverture. C'est un moteur de projection **explicable, actionnable, testable et extensible**.

### Ce qui rend ce cycle distinctif

La différenciation de jeedom2ha n'est pas de "faire apparaître Jeedom dans HA". Elle est de rendre la projection **compréhensible et maîtrisable**. Chaque équipement doit porter une décision lisible : projeté ou non, étape de blocage, cause principale canonique, et action proposée lorsqu'une remédiation utilisateur existe.

Le produit devient ainsi un système où la couverture large et la fiabilité ne s'opposent pas. Le registre HA ouvre le périmètre, la validation HA filtre les projections invalides, la décision de publication applique les politiques produit, et le diagnostic restitue une cause unique ordonnée par pipeline. Cette combinaison crée un comportement à la fois plus ambitieux que V1.1 et plus strict sur la qualité des décisions.

## Classification du projet

| Dimension | Classification |
|---|---|
| **Type de projet** | `interoperability_middleware / home_automation_bridge_plugin` |
| **Domaine** | `smart_home / home_automation_interoperability` |
| **Complexité** | Élevée |
| **Contexte** | Brownfield discovery / greenfield implementation du cycle moteur de projection explicable |

## Critères de succès

### Succès utilisateur

Le succès utilisateur de ce cycle est atteint quand un utilisateur ne se retrouve plus face à un "non publié" opaque. Pour chaque équipement Jeedom dans le périmètre, le système doit rendre la décision compréhensible : étape de pipeline atteinte, cause principale canonique, et action proposée lorsque la remédiation dépend de l'utilisateur.

Le moment de valeur du cycle n'est pas seulement qu'un équipement apparaisse dans Home Assistant. C'est le passage de **"je ne comprends pas pourquoi cet équipement n'est pas là"** à **"je sais exactement où ça bloque, pourquoi, et quoi faire"**. Le moteur doit donc améliorer simultanément la couverture utile et l'autonomie de diagnostic.

### Succès produit

jeedom2ha étant un plugin open-source communautaire, le succès business du cycle se mesure en soutenabilité produit plutôt qu'en revenu. Le cycle est réussi si la nouvelle architecture réduit les cas opaques, rend les tickets de support plus diagnostiquerables, et ouvre la couverture HA sans créer une dette de maintenance incontrôlée.

À 3 mois, le signal de succès est la capacité à absorber plus de composants HA projetables sans retomber dans une logique de liste fermée codée en dur. À 12 mois, le succès est d'avoir installé un cadre durable où l'ouverture d'un nouveau composant HA devient un travail de registre + mapping + validation + test, plutôt qu'une extension ad hoc risquée.

### Succès technique

Le succès technique du cycle est atteint si le pipeline à 5 étapes est implémenté comme contrat testable en isolation, avec validation HA obligatoire en étape 3, séparation stricte entre mapping et registre HA, et conservation du contrat 4D existant.

Le moteur doit empêcher la publication de projections HA structurellement invalides, préserver la rétrocompatibilité des `reason_code` existants, et introduire les nouvelles classes d'échec de manière additive. L'ordre d'évaluation du pipeline doit rester stable pour garantir une cause principale canonique lisible et déterministe.

### Résultats mesurables

| Résultat | Cible |
|---|---|
| Diagnostic explicable sur équipements non projetés | 100% des équipements non projetés ont une étape de blocage et une cause principale canonique |
| Diagnostic actionnable | 100% des cas avec remédiation utilisateur proposent une action explicite |
| Transformation "structurellement projetable → effectivement projeté" | Tendre vers 100%, hors exclusions utilisateur explicites et incidents d'infrastructure |
| Validation HA avant publication | 100% des publications passent par l'étape 3 de validation |
| Régression contrat 4D | 0 régression fonctionnelle sur le contrat 4D existant |
| Compatibilité `reason_code` | 0 renommage destructif ; migration additive uniquement |
| Testabilité | Chaque étape du pipeline est testable en isolation avec cas nominaux et cas d'échec |

## Scope produit

### MVP - Minimum Viable Product

Le MVP de ce cycle correspond au cœur non négociable du moteur de projection explicable :

- pipeline canonique à 5 étapes formalisé et implémenté ;
- validation structurelle HA obligatoire en étape 3 ;
- registre des composants HA séparé de la logique de mapping ;
- ouverture effective de tous les composants HA proprement projetables au sens du registre et de la validation ;
- diagnostic explicable et actionnable pour chaque équipement ;
- migration additive du contrat 4D et des `reason_code`.

### Fonctionnalités de croissance (post-MVP)

Les fonctionnalités de croissance de ce cycle restent in-scope mais subordonnées au noyau :

- overrides avancés pour forcer un type HA ou publier malgré une confiance insuffisante ;
- externalisation du flux système opérationnel complet (AI-1) ;
- documentation explicite des contraintes plateforme Jeedom affectant la validation terrain (AI-2).

### Vision future

Au-delà du cycle, la vision porte sur l'élargissement maîtrisé du moteur :

- drill-down commande par commande dans l'UI ;
- preview complète de publication avant action ;
- overrides inter-étapes plus fins ;
- intégration continue de composants HA émergents via le registre, sans casser le contrat du pipeline.

## Parcours utilisateurs

### Parcours 1 — Nicolas, chemin nominal : "Ma maison est projetée proprement"

Nicolas utilise déjà jeedom2ha et attend du nouveau cycle qu'il augmente la couverture sans réintroduire d'opacité. Il lance une synchronisation et retrouve ses équipements projetés dans Home Assistant. La nouveauté importante n'est pas visible quand tout va bien : le moteur a effectivement franchi les 5 étapes, validé la projection en étape 3, puis publié.

Le moment de valeur est silencieux mais critique : les équipements structurellement projetables apparaissent, et l'utilisateur n'a pas besoin de se demander si le résultat vient d'un coup de chance, d'une heuristique opaque ou d'un support codé en dur. La confiance vient du fait que la projection a été autorisée parce qu'elle était valide, pas parce que le produit a "essayé quand même".

### Parcours 2 — Nicolas, blocage critique : "Je comprends enfin pourquoi cet équipement n'apparaît pas"

Nicolas constate qu'un équipement Jeedom n'est pas présent dans HA. Dans l'ancien modèle, il voyait un résultat incomplet sans frontière claire entre problème de mapping, limite produit et erreur technique. Dans le nouveau cycle, le diagnostic lui indique la première étape qui bloque, la cause principale canonique, et l'action possible.

Si l'équipement échoue en étape 2, le moteur dit que le mapping est ambigu ou impossible. S'il échoue en étape 3, il dit que la projection HA est structurellement invalide et précise le champ manquant ou la contrainte violée. S'il échoue en étape 4, il explique que la décision finale de publication a été bloquée par une politique produit explicite, une exception de gouvernance ou un override, et non par une projection implicitement "hors liste". Le climax du parcours est le passage de l'opacité à la compréhension actionnable.

### Parcours 3 — Sébastien, utilisateur expert : "Je pilote la projection au lieu de la subir"

Sébastien maîtrise déjà Jeedom et Home Assistant. Une fois le diagnostic compris, il veut ajuster le périmètre, forcer un type HA, ou assumer consciemment un override sur un cas de confiance insuffisante. Il ne veut pas casser le moteur ; il veut reprendre la main dans un cadre explicite.

Le parcours doit donc lui permettre de voir ce que le moteur aurait décidé nativement, ce qu'il a surchargé, et les conséquences de cette surcharge dans le diagnostic. La résolution n'est pas seulement "ça publie". C'est "je publie en connaissance de cause, sans perdre la traçabilité de la décision".

### Parcours 4 — Support implicite / mainteneur : "Je peux expliquer un cas utilisateur sans relire le code"

Le mainteneur reçoit un ticket : un équipement thermostat n'est pas publié alors que l'utilisateur pense le cas valide. Au lieu d'inspecter plusieurs couches de logique implicite, il lit le diagnostic pipeline, la cause principale, et la validité HA associée. Il peut dire si le problème relève d'un manque de mapping, d'une contrainte HA, d'une politique explicite de publication ou d'override, ou d'un incident d'infrastructure.

La valeur du parcours est la réduction du coût cognitif de support. Le moteur doit rendre le système lisible pour l'utilisateur, mais aussi pour le mainteneur qui doit diagnostiquer vite sans dépendre d'une mémoire informelle du code.

### Parcours 5 — Mainteneur produit : "J'ouvre un nouveau composant HA sans régression"

Le mainteneur veut ajouter ou ouvrir un composant HA supplémentaire. Son point de départ n'est plus une condition dispersée dans le code. Il part du registre HA, modélise les contraintes, vérifie la validation étape 3, raccorde le mapping candidat, puis ajoute les tests qui prouvent le comportement nominal et les échecs attendus.

Le climax du parcours est organisationnel : l'ajout d'un composant devient une évolution gouvernée par le contrat du pipeline et par le registre, pas une extension opportuniste. La réussite se mesure par l'absence de régression sur les diagnostics existants et par la possibilité d'expliquer immédiatement pourquoi le composant est ou n'est pas publiable.

### Synthèse des capacités révélées par les parcours

Ces parcours révèlent les capacités indispensables suivantes :

- diagnostic par étape de pipeline avec cause principale canonique ;
- distinction explicite entre échec de mapping, invalidité HA, décision de publication explicite et incident d'infrastructure ;
- traçabilité des overrides utilisateur ;
- registre HA exploitable par le moteur et par le mainteneur ;
- testabilité isolée de chaque étape ;
- conservation du contrat 4D et des `reason_code` existants pendant l'évolution.

## Exigences spécifiques au domaine

### Contraintes normatives et contractuelles

Le cycle ne relève pas d'un domaine réglementé au sens santé, finance ou administration. En revanche, il est soumis à des **contrats externes de plateforme** qui jouent un rôle quasi-normatif dans le produit :

- respect des contraintes structurelles Home Assistant MQTT Discovery pour chaque composant ouvert ;
- compatibilité avec les comportements du core Jeedom et de son modèle `eqLogic/cmd` ;
- maintien du contrat utilisateur 4D déjà livré en V1.1 ;
- préservation des conventions historiques de `reason_code` par ajout pur.

### Contraintes techniques

- **Jeedom reste la seule source de vérité métier**. Aucun état canonique parallèle ne doit être créé dans le moteur.
- **Validation HA obligatoire avant publication**. Une projection plausible n'est pas suffisante ; elle doit être structurellement valide.
- **Ordre strict du pipeline**. La cause principale canonique dépend de l'évaluation ordonnée des 5 étapes.
- **Explicabilité obligatoire**. Toute décision doit pouvoir être restituée sous forme de diagnostic stable, lisible et testable.
- **Rétrocompatibilité additive**. Le cycle ne peut pas casser le contrat 4D ni renommer destructivement les `reason_code`.

### Exigences d'intégration

- lecture fiable de la topologie Jeedom, des commandes et du scope utilisateur ;
- registre HA séparé de la logique de mapping, versionné et exploitable par les tests ;
- production de diagnostics cohérents entre backend, API et UI ;
- conservation de la séparation transport interne / publication MQTT ;
- prise en compte des contraintes terrain Jeedom documentées par AI-2 pour éviter les faux diagnostics.

### Risques et mitigations

- **Risque : confusion entre échec de mapping et invalidité HA.**
  Mitigation : séparation stricte entre étape 2 et étape 3, avec `reason_code` distincts.
- **Risque : ouverture incontrôlée du scope depuis le registre HA.**
  Mitigation : distinction explicite entre composant connu, composant validable et composant ouvert.
- **Risque : rejet silencieux côté HA.**
  Mitigation : interdiction de publication sans validation HA positive.
- **Risque : régression diagnostic V1.1.**
  Mitigation : migration additive uniquement, tests de non-régression sur le contrat 4D.

## Innovation et motifs de nouveauté

### Axes d'innovation identifiés

L'innovation principale du cycle est conceptuelle et architecturale : jeedom2ha cesse d'être défini par une **liste fermée de cas supportés** et devient un **moteur de projection explicable** gouverné par un pipeline canonique. Cette bascule transforme la manière d'ouvrir le produit : on n'ajoute plus des exceptions, on étend un contrat.

Le second point innovant est la place donnée à la validation HA. Dans beaucoup de bridges, la validité côté plateforme cible reste implicite ou tardive. Ici, elle devient une étape autonome, formalisée et testable, située avant toute publication. Le diagnostic utilisateur est donc aligné sur le vrai point de décision, pas sur un symptôme tardif.

### Contexte de marché et différenciation

Le marché des bridges domotiques privilégie souvent le "best effort" : mapper ce qui ressemble à un cas connu, ignorer silencieusement le reste, ou mélanger limites produit et erreurs techniques dans le même résultat. Le positionnement de ce cycle est différent : la valeur n'est pas seulement la compatibilité, mais la **lisibilité de la compatibilité**.

Cette approche crée une différenciation crédible pour jeedom2ha dans un espace où les utilisateurs subissent souvent une boîte noire. Le produit ne promet pas une magie opaque ; il promet une projection ambitieuse mais gouvernée par des règles explicites, testables et actionnables.

### Approche de validation

L'innovation doit être validée par trois angles complémentaires :

- validation produit : l'utilisateur comprend où le pipeline bloque et quoi faire ;
- validation technique : chaque étape est testable en isolation, avec jeux de cas nominaux et d'échec ;
- validation de gouvernance : l'ouverture d'un nouveau composant HA suit le registre, la validation, le mapping et les tests, sans dérogation ad hoc.

### Mitigation des risques

- si l'approche registre + pipeline ajoute trop de rigidité, le fallback n'est pas le "best effort" mais l'amélioration contrôlée du registre et du mapping ;
- si l'ouverture de couverture crée des ambiguïtés, la priorité reste au refus explicable plutôt qu'à la publication hasardeuse ;
- si la richesse diagnostic devient trop technique, la traduction `reason_code → cause_label / cause_action` conserve une sortie orientée utilisateur.

## Exigences spécifiques au middleware d'interopérabilité

### Vue d'ensemble du type de projet

Le projet est un middleware d'interopérabilité embarqué dans un plugin Jeedom avec démon associé. Il ne crée pas un nouveau système domotique ; il arbitre la projection d'un modèle source existant vers un modèle cible externe. Sa responsabilité première n'est donc ni l'exécution métier ni l'interface utilisateur finale, mais la décision de projection, la publication cohérente et le diagnostic.

### Contraintes d'architecture

- séparation explicite entre source de vérité Jeedom, moteur de projection, registre HA, diagnostic et publication MQTT ;
- absence de dépendance circulaire entre le mapping et le registre HA ;
- capacité à faire évoluer le registre HA sans réécrire les couches UI et diagnostic ;
- traçabilité d'une décision de bout en bout : entrée Jeedom, candidat de mapping, validité HA, décision de publication, résultat de publication.

### Surfaces de compatibilité

Le middleware doit rester cohérent sur quatre surfaces simultanées :

- backend moteur de projection ;
- contrat API / AJAX exposé au frontend ;
- rendu diagnostic UI sur le contrat 4D ;
- publication MQTT Discovery et états associés.

Une évolution n'est acceptable que si elle garde ces surfaces alignées. Un changement backend sans traduction diagnostic ou sans cohérence API est considéré incomplet.

### Exigences du contrat de diagnostic

- le backend produit les données de diagnostic, le frontend les affiche sans réinterpréter ;
- la cause principale est unique et ordonnée par le pipeline ;
- `reason_code`, `cause_code`, `cause_label` et `cause_action` restent cohérents entre eux ;
- les nouvelles informations de validité HA s'ajoutent sans casser les consommateurs existants.

### Considérations d'implémentation

- conception orientée fonctions pures pour les étapes 2, 3 et 4 du pipeline ;
- fixtures de tests capables de couvrir les cas Jeedom nominaux, ambigus, incomplets et invalides HA ;
- mécanisme d'extension du registre HA suffisamment simple pour ouvrir un nouveau composant sans effet de bord caché ;
- politique claire de refus explicable quand les données d'entrée ne permettent pas une projection sûre.

## Cadrage projet et développement phasé

### Stratégie et philosophie MVP

**Approche MVP :** MVP de contrat produit. Le but n'est pas de démontrer partiellement le moteur, mais de livrer un noyau complet et crédible du pipeline explicable. Une étape manquante dans le contrat affaiblit toute la promesse ; en particulier, la validation HA étape 3 ne peut pas être reportée.

**Exigences de ressources :** un mainteneur principal capable de toucher backend, diagnostic et publication, avec discipline de tests et gate terrain. Le cycle est compatible avec une exécution lean, mais pas avec une implémentation fragmentée par couches indépendantes.

### Périmètre MVP (phase 1)

**Parcours utilisateurs couverts :**

- projection nominale des équipements structurellement projetables ;
- diagnostic explicable des équipements non projetés ;
- lecture d'un blocage par étape avec cause principale canonique ;
- extension maîtrisée du moteur sans régression sur V1.1.

**Capacités indispensables :**

- pipeline canonique à 5 étapes implémenté de bout en bout ;
- validation HA obligatoire en étape 3 ;
- registre HA servant de fondation du scope ;
- contrat 4D enrichi de façon additive ;
- rétrocompatibilité des `reason_code` ;
- exigences de testabilité par étape ;
- dépendances explicites entre mapping, validation, décision et publication.

### Capacités post-MVP

**Phase 2 (post-MVP) :**

- overrides avancés utilisateur ;
- externalisation du flux système AI-1 ;
- formalisation complète des contraintes plateforme AI-2 ;
- enrichissement de la surface diagnostic quand le noyau est stabilisé.

**Phase 3 (expansion) :**

- preview de publication ;
- drill-down commande par commande ;
- nouvelles classes d'overrides inter-étapes ;
- ouverture continue de composants HA émergents selon le registre.

### Stratégie de mitigation des risques

**Risques techniques :** le principal risque est de recréer une logique implicite sous un habillage de pipeline. La mitigation est d'imposer des fonctions pures, des étapes testables, et des critères d'acceptation ancrés dans la séquence 1→5.

**Risques produit :** le risque principal est que l'utilisateur perçoive peu de différence avec le bridge actuel. La mitigation est de rendre immédiatement visible la valeur du cycle via un diagnostic plus explicite et une couverture élargie mais propre.

**Risques de ressources :** le risque principal est la dispersion entre moteur, registre, diagnostic et UI. La mitigation est de traiter le cycle comme un noyau intégré, de refuser les contournements "best effort", et de reporter tout ce qui n'est pas nécessaire au contrat MVP.

## Exigences fonctionnelles

### Feature 0 — Contrat global du pipeline

- FR1: L'utilisateur peut s'appuyer sur un pipeline canonique à 5 étapes pour toute décision de projection.
- FR2: Le système peut évaluer chaque équipement dans un ordre stable : éligibilité, mapping candidat, validation HA, décision de publication, publication MQTT.
- FR3: Le système peut arrêter l'évaluation à la première étape bloquante et retenir cette étape comme cause principale canonique.
- FR4: Le système peut restituer, pour chaque équipement, l'étape la plus avancée atteinte dans le pipeline.
- FR5: Le mainteneur peut relier une décision de projection à ses entrées source, à son résultat intermédiaire et à son résultat final.

### Feature 1 — Étape 1 : Éligibilité

- FR6: L'utilisateur peut définir le périmètre d'éligibilité via les règles de scope existantes du produit.
- FR7: Le système peut déterminer si un équipement est éligible avant tout mapping.
- FR8: Le système peut distinguer un équipement inéligible d'un équipement éligible mais non projetable.
- FR9: Le système peut classer les causes d'inéligibilité dans des catégories distinctes et stables.
- FR10: L'utilisateur peut consulter, pour tout équipement exclu avant le début du mapping, un diagnostic qui indique l'étape 1 comme point de blocage, le motif d'exclusion canonique et, lorsque l'exclusion relève d'un choix utilisateur, l'action de scope applicable.

### Feature 2 — Étape 2 : Mapping candidat

- FR11: Le système peut produire un candidat de projection HA à partir d'un équipement Jeedom éligible.
- FR12: Le système peut exprimer le niveau de confiance associé à un candidat de mapping.
- FR13: Le système peut signaler qu'aucun mapping exploitable n'a pu être produit pour un équipement pourtant éligible.
- FR14: L'utilisateur peut distinguer un échec de mapping d'un refus ultérieur du pipeline.
- FR15: Le mainteneur peut faire évoluer les règles de mapping sans modifier l'ordre canonique des étapes.

### Feature 3 — Étape 3 : Validation HA obligatoire

- FR16: Le système peut vérifier qu'un candidat de projection satisfait les contraintes structurelles du composant HA cible avant toute publication.
- FR17: Le système peut identifier les informations manquantes ou incompatibles qui empêchent une projection HA valide.
- FR18: L'utilisateur peut voir qu'un équipement a été compris par le moteur mais rejeté parce que la projection HA serait invalide.
- FR19: Le système peut refuser explicitement toute publication lorsque la validation HA échoue.
- FR20: Le mainteneur peut distinguer un composant HA inconnu du moteur d'un composant connu mais mal alimenté par les données Jeedom.

### Feature 4 — Étape 4 : Décision de publication

- FR21: Le système peut prendre une décision de publication uniquement après réussite des étapes 1 à 3.
- FR22: Le système peut porter en étape 4 la décision finale de publication à partir d'une projection déjà modélisée et validée.
- FR23: Le système peut appliquer en étape 4 des politiques produit explicites, des exceptions de gouvernance et des overrides autorisés sans les confondre avec la validité structurelle HA.
- FR24: L'utilisateur peut distinguer un blocage de décision de publication explicite d'un composant HA invalide, inconnu ou d'un échec de mapping.
- FR25: L'utilisateur expert peut appliquer les overrides avancés autorisés par le produit sans effacer la décision native du moteur.

### Feature 5 — Étape 5 : Publication MQTT et résultat de publication

- FR26: Le système peut publier vers Home Assistant uniquement les projections explicitement autorisées par l'étape 4.
- FR27: Le système peut enregistrer séparément le résultat de publication technique et la décision produit qui l'a précédé.
- FR28: L'utilisateur peut distinguer un échec d'infrastructure d'un refus de projection décidé par le moteur.
- FR29: Le système peut enrichir le diagnostic d'un équipement avec le résultat de publication effectif.
- FR30: Le système peut empêcher qu'un échec technique masque la cause principale de décision déjà établie par les étapes amont.

### Feature 6 — Diagnostic explicable et actionnable

- FR31: L'utilisateur peut consulter, pour chaque équipement, un diagnostic de projection comprenant au minimum le statut de projection, l'étape de blocage ou l'étape la plus avancée atteinte, la cause principale canonique et, lorsqu'elle existe, l'action proposée.
- FR32: Le système peut traduire chaque cause moteur canonique en un couple stable `cause_label` / `cause_action`, avec `cause_label` toujours renseigné et `cause_action` renseigné uniquement lorsqu'une remédiation utilisateur existe.
- FR33: Le système peut expliquer explicitement lorsqu'aucune action utilisateur directe n'est possible.
- FR34: Le système peut préserver le contrat 4D existant tout en ajoutant les informations de validité de projection.
- FR35: L'utilisateur peut voir une seule cause principale canonique par équipement à un instant donné.

### Feature 7 — Registre HA et gouvernance du registre

- FR36: Le mainteneur peut gérer un registre des composants HA séparé de la logique de mapping.
- FR37: Le système peut différencier les états "composant connu", "composant validable" et "composant ouvert".
- FR38: Le mainteneur peut ajouter progressivement un composant au registre dans un cadre de gouvernance explicite, sans faire du registre une frontière produit arbitraire.
- FR39: Le système peut considérer comme ouvrable dans le cycle tout composant dont les contraintes sont modélisées dans le registre HA, dont la validation structurelle aboutit sur des cas nominaux représentatifs, et dont l'ouverture ne crée pas de régression sur le diagnostic canonique.
- FR40: Le mainteneur peut vérifier qu'un composant n'est marqué "ouvert" que si trois conditions sont satisfaites simultanément : contraintes présentes dans le registre, mapping candidat défini pour les cas visés, et validation couverte par des cas nominaux et des cas d'échec sans régression sur le contrat 4D.

### Feature 8 — Validation, testabilité et rétrocompatibilité

- FR41: Le mainteneur peut tester chaque étape du pipeline indépendamment.
- FR42: Le mainteneur peut valider l'ouverture d'un composant HA par des cas nominaux et des cas d'échec représentatifs.
- FR43: Le système peut conserver la compatibilité des `reason_code` existants tout en ajoutant de nouveaux motifs liés à la validité HA.
- FR44: Le système peut exposer un contrat de diagnostic dont les champs canoniques (`reason_code`, `cause_code`, `cause_label`, `cause_action`, étape de pipeline, statut`) restent stables d'une version à l'autre, hors ajouts additifs documentés, pour permettre des tests de non-régression.
- FR45: Le mainteneur peut vérifier qu'une évolution du registre, du mapping ou de la validation ne dégrade pas le contrat 4D ni la hiérarchie des causes.

### Dépendances entre features

- **Feature 0** est la fondation de toutes les autres features ; sans ordre canonique, il n'existe ni cause principale stable ni diagnostic fiable.
- **Feature 1** conditionne **Feature 2** ; seuls les équipements éligibles entrent dans le mapping.
- **Feature 2** conditionne **Feature 3** ; la validation HA ne s'applique qu'à un candidat produit.
- **Feature 7** alimente **Feature 3** et **Feature 4** ; le registre HA est une dépendance explicite de la validation et de la décision de publication.
- **Feature 3** conditionne **Feature 4** ; une projection invalide ne peut pas atteindre la décision de publication.
- **Feature 4** conditionne **Feature 5** ; aucune publication ne peut contourner la décision produit.
- **Feature 6** dépend des Features **0 à 5** ; le diagnostic restitue l'état réel du pipeline et du résultat de publication.
- **Feature 8** est transverse ; elle gouverne la capacité à faire évoluer les Features **1 à 7** sans régression.

## Exigences non fonctionnelles

### Fiabilité et déterminisme

- NFR1: À entrées identiques, le moteur doit produire 100% des mêmes décisions de projection, étapes de blocage et causes principales canoniques sur le corpus de non-régression de référence, vérifié par exécution répétée du même jeu de cas.
- NFR2: Le taux de publications autorisées avec une validation HA négative doit être de 0%, vérifié par tests de pipeline couvrant les cas de validation positive et négative.
- NFR3: 100% des équipements traités doivent recevoir un résultat explicite de pipeline, y compris en cas d'échec, vérifié sur le corpus de tests couvrant cas nominaux, ambiguïtés, invalidités HA et incidents d'infrastructure.
- NFR4: Pour 100% des équipements diagnostiqués, une seule classe d'échec canonique doit être exposée comme cause principale à un instant donné, vérifié par tests de non-régression couvrant mapping, validité HA, fermeture de scope et infrastructure.

### Intégration et compatibilité

- NFR5: 100% des composants HA ouverts doivent satisfaire les contraintes structurelles de leur entrée de registre et du contrat MQTT Discovery correspondant sur les cas nominaux couverts, vérifié par validation des payloads de référence.
- NFR6: Le cycle doit introduire 0 source de vérité métier concurrente à Jeedom, vérifié par revue des artefacts livrés et par tests confirmant que les décisions de projection restent calculables à partir des données Jeedom et du cache technique non autoritatif.
- NFR7: Le contrat 4D existant doit rester rétrocompatible à 100% pour les consommateurs actuels sur le corpus de non-régression V1.1, vérifié par comparaison de schéma et de comportement hors ajouts additifs documentés.
- NFR8: 0 `reason_code` historique ne doit être renommé, supprimé ou voir son sens inversé ; toute extension doit être additive et documentée, vérifiée par diff du catalogue des codes et tests de non-régression.

### Maintenabilité et testabilité

- NFR9: Chacune des 5 étapes du pipeline doit disposer d'au moins un cas nominal et un cas d'échec exécutables en isolation dans la suite de tests de référence, vérifié à chaque livraison du cycle.
- NFR10: 100% des ouvertures de nouveaux composants HA doivent être accompagnées, dans le même incrément, d'au moins un cas nominal, un cas d'échec de validation et un test de non-régression diagnostic, vérifié en revue de livraison.
- NFR11: 0 évolution du registre, du mapping ou de la validation ne doit être acceptée si le corpus de non-régression du diagnostic canonique présente une régression, vérifié par passage complet des tests de non-régression avant acceptation.
- NFR12: Les artefacts de décision utilisés par les vérifications automatiques doivent conserver un schéma canonique stable sur 100% des tests de cohérence, hors ajouts additifs documentés, vérifié par contrôles de schéma et tests de cohérence.
