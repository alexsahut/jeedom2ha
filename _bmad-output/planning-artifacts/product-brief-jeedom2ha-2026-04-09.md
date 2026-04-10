---
stepsCompleted: [1, 2, 3, 4, 5, 6]
status: complete
inputDocuments:
  - _bmad-output/planning-artifacts/architecture-projection-engine.md
  - _bmad-output/project-context.md
  - _bmad-output/implementation-artifacts/epic-5-retro-2026-04-09.md
  - _bmad-output/planning-artifacts/backlog-icebox.md
date: 2026-04-09
author: Alexandre
---

# Product Brief: jeedom2ha — Moteur de projection explicable

## Executive Summary

jeedom2ha entre dans un nouveau cycle produit qui ne prolonge pas V1.1 Pilotable. V1.1 a stabilisé un pont fiable : exécution déterministe des opérations HA, diagnostic 4D, gate terrain systématique. Ces acquis sont verrouillés et non rouverts.

Le cycle post-V1.1 formalise un **changement de positionnement produit explicite** par rapport au cadrage précédent. Le modèle V1.1 bornait la couverture par une liste de types HA prévus par version — un choix délibéré et adapté à la phase de stabilisation. Ce modèle est désormais dépassé. Le nouveau cycle assume une **réorientation** : passage d'un bridge pilotable à périmètre borné par version à un **moteur de projection explicable à couverture large, bornée par la validité réelle de projection vers Home Assistant**.

Si une projection est structurellement possible et valide côté HA, le produit doit viser sa prise en charge. La couverture n'est plus une liste fermée décidée au développement — elle est la conséquence directe de la capacité du moteur à valider la projection.

Le moteur rend chaque décision de projection **explicite, déterministe, configurable et testable**. Pour chaque équipement Jeedom, le système explique ce qui a été projeté ou non, à quelle étape du pipeline la décision s'est arrêtée, pourquoi, et ce que l'utilisateur peut faire pour permettre la projection quand c'est possible.

---

## Core Vision

### Problem Statement

Le pont jeedom2ha V1.1 fonctionne — il publie et supprime des entités HA de manière fiable. Mais il ne sait pas **expliquer ses décisions de projection**. La logique qui détermine quoi projeter, pourquoi, avec quelles contraintes, vit dans le code sans être formalisée comme contrat explicite.

Conséquence directe : lorsqu'un équipement Jeedom n'apparaît pas dans Home Assistant, l'utilisateur fait face à un résultat opaque sans levier d'action. Il voit "non publié" sans comprendre à quelle étape la décision a été prise, pour quelle raison, ni ce qu'il peut faire pour corriger la situation.

### Problem Impact

- **Utilisateur bloqué sans recours** : un équipement non projeté génère de la frustration et des tickets de support, alors que la cause est souvent corrigible (generic_type manquant, commande absente, scope produit fermé).
- **Élargissement impossible** : ouvrir de nouveaux types HA (sensor, binary_sensor, button, number, select, climate...) sans modèle explicite de décision produirait des projections non maîtrisées — exactement l'anti-pattern "best effort" que le projet refuse.
- **Maintenabilité dégradée** : sans modèle canonique externalisé, chaque ajout de règle de mapping risque d'introduire des effets de bord non testables sur les décisions existantes.
- **Projections rejetées silencieusement** : l'absence de validation structurelle HA avant publication signifie que des entités peuvent être envoyées à HA et rejetées sans que l'utilisateur en soit informé.

### Why Existing Solutions Fall Short

Les bridges entre systèmes domotiques fonctionnent le plus souvent selon un modèle "best effort" : mapper ce qu'on sait mapper, ignorer le reste. Ce modèle a servi — y compris dans jeedom2ha V1.1 — mais il rend difficile la montée en couverture et en fiabilité :

1. **Décision de projection peu lisible** — beaucoup de bridges rendent difficile la compréhension fine de pourquoi un équipement est ou n'est pas projeté. Le diagnostic, quand il existe, reste souvent un libellé technique sans action possible pour l'utilisateur.
2. **Périmètre souvent figé par version** — les types supportés sont fréquemment une liste fermée décidée au développement. Un équipement parfaitement projetable peut être bloqué parce que son type HA n'est pas encore couvert dans la version courante.
3. **Validation avant publication rare** — le payload est généralement construit et envoyé. S'il est structurellement invalide côté plateforme cible, l'entité peut disparaître silencieusement.

### Proposed Solution

Un **moteur de projection explicable** organisé en pipeline à 5 étapes canoniques : Éligibilité → Mapping candidat → Validation HA → Décision de publication → Publication MQTT.

Chaque étape produit un résultat explicite. Le premier échec rencontré dans l'ordre du pipeline devient la **cause principale canonique** — une seule cause lisible, à l'étape identifiée, avec une action possible.

Le registre des composants HA est séparé de la logique de mapping, versionné, et ouvert largement : tout composant HA dont le moteur connaît les contraintes structurelles et pour lequel la projection est valide peut être publié. Le scope produit n'est plus une liste arbitraire fermée — il est borné par la validité réelle de projection.

La configurabilité utilisateur opère sur le périmètre d'éligibilité (inclusion/exclusion), avec des overrides avancés (forcer un type HA, publier malgré confiance insuffisante) comme leviers du cycle.

### Key Differentiators

**Projection explicable, déterministe et maîtrisée.** Le différenciateur de jeedom2ha n'est pas de faire un bridge vers Home Assistant. C'est de projeter de façon explicable, déterministe et maîtrisée tout ce qui peut l'être proprement dans HA, tout en disant clairement pourquoi le reste ne l'est pas et comment agir dessus.

Concrètement :

- **Explicabilité** — chaque équipement porte une trace de décision : projeté ou non, à quelle étape, pourquoi, action possible.
- **Couverture large par design** — le moteur projette tout ce qui est structurellement valide côté HA, au lieu de borner par une liste fermée de types "prévus".
- **Validation structurelle avant publication** — le moteur valide la projection avant de publier, avec l'objectif d'empêcher l'envoi de payloads HA invalides et d'expliciter les cas non projetables.
- **Déterminisme testable** — le pipeline de décision est un contrat formel, testable en isolation, pas un ensemble de règles implicites dispersées dans le code.

---

## Target Users

### Utilisateur primaire

**Profil unique : le propriétaire Jeedom qui cohabite avec Home Assistant.**

Il n'existe pas de segmentation par niveau d'expertise. L'utilisateur est un seul profil qui traverse trois situations d'usage distinctes, chacune avec ses attentes propres.

#### Situation 1 — Nominale

L'utilisateur veut voir ses équipements Jeedom projetés dans Home Assistant. Il n'a pas besoin de comprendre le moteur de projection. La valeur est : **"ça marche"**.

- Il active le plugin, lance une synchronisation, retrouve ses équipements dans HA.
- Le moteur est transparent — il produit le bon résultat sans demander d'attention.
- Le diagnostic existe mais n'est pas sollicité.

#### Situation 2 — Blocage (moment critique)

L'utilisateur constate qu'un équipement n'est pas projeté dans Home Assistant. C'est le **point de friction principal** aujourd'hui et le cœur du produit.

La valeur attendue :
- comprendre **à quelle étape** du pipeline la décision s'est arrêtée ;
- comprendre **pourquoi** ;
- savoir **quoi faire** pour corriger.

C'est le principal moment "aha" du produit : **l'utilisateur passe de "ça ne marche pas" à "je comprends pourquoi et je sais quoi faire"**.

#### Situation 3 — Maîtrise

Une fois la compréhension acquise, l'utilisateur peut vouloir aller plus loin :
- ajuster le périmètre de projection (inclure/exclure) ;
- forcer un type HA sur un équipement ;
- publier malgré une confiance insuffisante du moteur.

La valeur devient : **"je pilote la projection, elle n'est plus opaque"**.

### Utilisateurs secondaires

**Support implicite, pas cible primaire.** Un utilisateur qui diagnostique pour un autre existe mais n'est pas une cible produit. Le moteur explicable doit réduire le besoin de support en rendant l'utilisateur autonome face à ses blocages.

### Parcours utilisateur

Le parcours n'est pas linéaire mais cyclique — l'utilisateur revient en situation 2 chaque fois qu'un nouvel équipement pose problème.

1. **Découverte** — l'utilisateur installe le plugin, configure le broker MQTT, lance la première synchronisation. Situation 1.
2. **Premier blocage** — un ou plusieurs équipements n'apparaissent pas dans HA. L'utilisateur consulte le diagnostic. Transition vers situation 2.
3. **Compréhension** — le diagnostic indique l'étape de blocage, la cause, et l'action possible. L'utilisateur corrige (ajoute un generic_type, ajuste le scope). **Moment "aha".**
4. **Confiance acquise** — l'utilisateur comprend le modèle de décision. Il commence à utiliser les overrides avancés. Situation 3.
5. **Routine** — chaque nouvel équipement ou changement de configuration repasse par le pipeline. L'utilisateur sait lire le diagnostic et agir. Le cycle situation 1 → 2 → 1 devient naturel et rapide.

---

## Success Metrics

### Métriques utilisateur — par situation d'usage

#### Situation 1 — Couverture de projection

La couverture se mesure en 4 niveaux distincts, pas en ratio brut :

| Niveau | Définition |
|--------|-----------|
| Équipements totaux | Tous les eqLogic Jeedom dans le périmètre (non exclus par l'utilisateur) |
| Interprétables | Le moteur a pu analyser l'équipement et produire un candidat de mapping (même invalide ou ambigu) |
| Structurellement projetables | Le candidat passe la validation HA (étape 3 franchie) |
| Effectivement projetés | La publication a été exécutée avec succès (étape 5 franchie) |

**Métrique de succès :** la part des équipements structurellement projetables qui sont effectivement projetés doit tendre vers 100%. L'écart entre ces deux niveaux ne doit refléter que des décisions utilisateur explicites (exclusion de scope) ou des échecs d'infrastructure transitoires — jamais une défaillance silencieuse du moteur.

**KPI principal du cycle :** maximiser la transformation "structurellement projetable → effectivement projeté", jusqu'à tendre vers 100%, hors décisions utilisateur explicites et aléas d'infrastructure.

#### Situation 2 — Explicabilité du diagnostic

Pour chaque équipement non projeté :
- **100%** portent une cause lisible (cause_label métier, pas un code technique) ;
- **100%** identifient l'étape du pipeline à laquelle la décision s'est arrêtée ;
- une **action possible est proposée** quand une remédiation utilisateur existe ;
- une **explicitation claire** est fournie quand aucune action utilisateur directe n'est possible.

Le diagnostic est toujours explicable. Il est actionnable quand le cas le permet.

#### Situation 3 — Maîtrise et configurabilité

- Les overrides avancés (forcer un type HA, publier malgré confiance insuffisante) sont fonctionnels et documentés.
- L'utilisateur peut ajuster le périmètre de projection et constater l'effet immédiatement dans le diagnostic.

### Objectifs produit du cycle

#### Ouverture du scope composants HA

L'objectif est d'absorber tout ce qui est projetable proprement dans Home Assistant. Le moteur est conçu pour ouvrir largement la couverture dès lors que la projection est structurellement valide.

Concrètement, le cycle vise l'ouverture la plus large possible sur les composants HA connus du moteur (light, cover, switch, sensor, binary_sensor, button, number, select, climate). L'engagement n'est pas une liste rigide de 9 composants, mais un objectif de couverture : tout composant dont le moteur connaît les contraintes et pour lequel la projection est valide doit être ouvert.

#### Qualité du moteur de projection

- Pipeline à 5 étapes entièrement implémenté et testable en isolation.
- Validation structurelle HA avant toute publication — objectif d'empêcher l'envoi de payloads invalides et de rendre explicites les cas non projetables.
- Registre des composants HA séparé, versionné, vérifiable contre la spec HA externe.
- Contrat 4D existant enrichi par ajout pur — aucune régression sur le diagnostic V1.1.

### Business Objectives

N/A — jeedom2ha est un plugin open-source communautaire. Les objectifs sont la qualité produit, la couverture fonctionnelle et l'autonomie utilisateur, pas des métriques commerciales.

---

## Scope du cycle

### Coeur non négociable

Les 5 livrables suivants constituent le noyau du cycle. Aucun ne peut être différé ou réduit sans invalider la promesse produit.

**1. Pipeline de projection à 5 étapes formalisé**

Éligibilité → Mapping candidat → Validation HA → Décision de publication → Publication MQTT. Chaque étape produit un résultat explicite. Le pipeline est un contrat testable en isolation, pas une description du code existant.

**2. Validation structurelle HA (étape 3 — nouvelle)**

Fonction pure qui vérifie que le candidat de mapping peut produire un payload structurellement valide pour le composant HA cible. Objectif : empêcher l'envoi de payloads invalides et rendre explicites les cas non projetables.

**3. Registre des composants HA construit depuis la spec de référence**

Le registre encode les contraintes structurelles de chaque composant HA pertinent pour le moteur. Il est physiquement séparé de la logique de mapping et du publisher. Le cycle construit ce registre à partir du fichier de référence HA (`docs/jeedom_homebridge_homeassistant_optionB_reference.xlsx`) et de la documentation MQTT Discovery Home Assistant — pas depuis une liste fermée prédéfinie.

La distinction "composant connu / composant ouvert" est conservée comme garde-fou d'architecture : elle permet d'ajouter un composant au registre (contraintes modélisées) sans l'ouvrir automatiquement à la publication tant que la chaîne complète (mapping + validation + publication) n'est pas opérationnelle. Dans le cadre de ce cycle, tout composant dont les contraintes sont modélisées, validées et projetables proprement est ouvert.

**4. Ouverture effective de tous les composants HA projetables proprement**

Le cycle ne vise pas l'ouverture d'une liste fermée de composants. Il vise la couverture la plus large possible de l'univers des composants HA MQTT Discovery, bornée par la capacité du moteur à modéliser les contraintes, valider la projection et publier proprement. Tout composant dont le registre encode les contraintes et pour lequel la projection est structurellement valide doit être ouvert.

**5. Diagnostic explicable et actionnable**

Pour chaque équipement, le système explique ce qui a été projeté ou non, à quelle étape du pipeline la décision s'est arrêtée, pourquoi, et ce que l'utilisateur peut faire quand une remédiation existe. Quand aucune action utilisateur directe n'est possible, le diagnostic l'explicite clairement.

### Engagements secondaires (in-scope, second rang)

Ces livrables font partie du cycle. Ils ne sont pas le cœur du premier incrément mais ne peuvent pas être repoussés hors cycle.

**6. Overrides avancés**

Forcer un type HA sur un équipement. Publier malgré une confiance insuffisante du moteur. Livrables de second rang — peuvent être livrés plus tard dans le cycle que le cœur.

**7. AI-1 — Flux système opérationnel externalisé**

Externaliser le modèle du flux opérationnel sous forme d'artefact partageable : chaîne complète User Action → Backend → Résultat → Stockage → API → JS → UI. Livrable de solidification et de soutenabilité du moteur, subordonné au cœur du cycle.

**8. AI-2 — Contraintes plateforme Jeedom documentées**

Recenser les comportements Jeedom hors périmètre story qui affectent la validation terrain (auto-sync daemon, délais event::changes). Les rendre explicites comme contraintes de test intégrées au cadrage des stories. Livrable de solidification, subordonné au cœur du cycle.

**9. Migration additive des reason_code et enrichissement du contrat 4D**

Nouveaux reason_code pour la classe d'échec 2 (validité HA). Ajout pur de `projection_validity` dans la trace diagnostic. Rétrocompatibilité totale — aucun code existant renommé ou supprimé. La classe d'échec 3 (scope produit) est conservée comme mécanisme résiduel de future-proofing — elle protège le pipeline si de nouveaux composants sont ajoutés au registre sans être immédiatement projetables proprement.

### Hors scope

Les sujets suivants sont explicitement exclus de ce cycle. Ils ne doivent donner lieu à aucune story ni développement.

- **Drill-down niveau commande dans l'UI** — requiert un niveau 4 structurant dans la hiérarchie données/frontend (backlog icebox).
- **Alignement navigation Homebridge** — frontière D, pas de convergence UX avec d'autres écosystèmes.
- **Réconciliation sophistiquée / détection automatique de doublons** — hors périmètre post-V1.1.
- **Preview complète de publication avant action** — frontière C, maturité produit avancée.

### Critère de succès du cycle

Le cycle est réussi quand :
- le moteur de projection explicable est formalisé, implémenté et testable ;
- le registre HA couvre l'ensemble des composants pertinents identifiés depuis la spec de référence ;
- tout composant dont les contraintes sont modélisées et la projection valide est effectivement ouvert ;
- chaque équipement porte un diagnostic explicable avec cause, étape et action possible ;
- les acquis V1.1 sont intacts — aucune régression sur le contrat 4D, les opérations HA, le diagnostic existant.

### Vision future (au-delà de ce cycle)

- **Drill-down commande par commande** — exposer la composition fine de l'équipement HA en lecture seule (backlog icebox, futur epic dédié).
- **Preview de publication** — permettre à l'utilisateur de visualiser le résultat de projection avant de déclencher la publication effective.
- **Overrides inter-étapes** — intervenir entre les étapes 2 et 4 du pipeline (forcer un mapping, surcharger la validation).
- **Composants HA émergents** — intégrer de nouveaux composants MQTT Discovery au registre à mesure que Home Assistant les stabilise ou que de nouveaux besoins utilisateur les justifient.
