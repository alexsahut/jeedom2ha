# Revue UX Delta - Post-MVP V1.1 Pilotable

## 1. Executive summary

La base UX du MVP reste solide et ne doit pas être refondue. En revanche, la V1.1 Pilotable change la nature de l'écran principal: on ne parle plus seulement d'un écran de diagnostic/publication, mais d'une **console de pilotage du périmètre publié**.

La décision UX centrale est la suivante:
- **Oui, la vue par pièce est le bon point d'entrée opérationnel**, parce qu'elle correspond à la hiérarchie Jeedom et au besoin de maîtrise du parc.
- **Non, elle ne doit pas devenir l'unique modèle de lecture**, sinon l'utilisateur perd la vision globale, mélange les statuts et ne comprend plus les impacts HA.

La console V1.1 doit donc être structurée en **trois niveaux explicites**:
1. **Global**: santé minimale du pont, compteurs (Total, Inclus, Exclus, Écarts), actions globales.
2. **Pièce**: inclusion/exclusion, compteurs, actions de maintenance de portée pièce.
3. **Équipement**: périmètre par source d'exclusion, statut binaire (Publié / Non publié), écart, cause métier, action recommandée.

Le principal risque UX de V1.1 n'est pas le manque de fonctionnalités. C'est la **confusion**:
- confusion entre état du bridge et état de configuration,
- confusion entre ce qui est publié et pourquoi cela ne l'est pas,
- confusion entre action sûre de mise à jour et action destructrice côté Home Assistant.

Conclusion de la revue: **l'UX est suffisamment cadrée pour lancer l'epic planning**, à condition de figer immédiatement:
- la hiérarchie `global -> pièce -> équipement`,
- le modèle utilisateur **Périmètre → Statut → Écart → Cause**,
- les compteurs (Total, Inclus, Exclus, Écarts) comme lecture principale pièce/global,
- la disparition du concept d'exception au profit d'exclusions par source,
- le diagnostic utilisateur centré sur les équipements in-scope,
- la confiance visible uniquement en diagnostic technique,
- la gradation des confirmations,
- le placement de la santé minimale du pont,
- la distinction nette entre décision locale et application à Home Assistant.

## 2. Ce qui reste valide dans l'UX actuelle

Les fondations MVP restent pertinentes et doivent être conservées:
- **Onboarding pédagogique**: la promesse produit reste "coexistence pilotable", pas magie opaque.
- **Diagnostic actionnable**: un problème doit toujours déboucher sur une explication et une action simple.
- **Contrôle de l'exposition**: l'utilisateur doit garder la main sur ce qui franchit le pont.
- **Principe de moindre nuisance**: mieux vaut ne pas publier que publier faux ou polluant.
- **Desktop-first**: le produit reste une console d'administration, pas une UI mobile-first.
- **Détail à la demande**: les informations techniques doivent rester proches, mais non visibles par défaut.
- **Rouge réservé à l'infrastructure**: à conserver strictement.
- **Sobriété visuelle native Jeedom**: pas de refonte graphique lourde nécessaire.

En synthèse, la V1.1 n'invalide pas l'UX actuelle. Elle impose surtout de la **structurer davantage autour de la maîtrise opérationnelle**.

## 3. Ce que V1.1 change dans l'expérience produit

La V1.1 fait évoluer l'expérience de quatre manières structurantes:

### 3.1 Passage d'une logique "équipement publiable" à une logique "périmètre pilotable"

Le MVP aidait surtout à comprendre ce qui pouvait être publié.  
La V1.1 doit aider à **choisir, maintenir et sécuriser** ce qui reste publié dans le temps.

### 3.2 Introduction d'une hiérarchie d'action

Le produit doit maintenant faire exister clairement trois portées:
- action globale,
- action pièce,
- action équipement.

Cette hiérarchie n'était pas structurante dans le MVP. Elle devient centrale en V1.1.

### 3.3 Apparition d'un enjeu de maintenance explicite

Le produit n'est plus seulement évalué sur sa capacité à publier. Il l'est aussi sur sa capacité à:
- republier sans inquiéter,
- reconstruire sans tromper,
- montrer l'impact réel sur Home Assistant.

### 3.4 Visibilité minimale de l'état du bridge

L'utilisateur doit pouvoir distinguer immédiatement:
- un problème de publication lié à son périmètre,
- un problème de bridge lié au démon, au MQTT ou à la synchronisation.

Sans cette séparation, la console devient anxiogène et coûteuse à supporter.

## 4. Points de friction UX majeurs à anticiper

### 4.1 Vue par pièce utilisée comme unique vue de vérité

Risque:
- l'utilisateur comprend la structure spatiale, mais ne voit plus facilement les équipements problématiques dispersés dans plusieurs pièces.

Conséquence:
- perte de lisibilité transversale,
- traitement lent des ambiguïtés,
- sensation de console lourde.

Décision:
- **garder la pièce comme point d'entrée par défaut**, mais avec des filtres globaux et des compteurs transverses.

### 4.2 Un seul "statut" qui essaie de tout dire

Risque:
- mélanger dans un même badge:
  - état de publication,
  - cause du non-publié,
  - incident d'infrastructure,
  - choix utilisateur.

Conséquence:
- modèle mental confus,
- difficulté à expliquer le produit,
- tickets de support évitables.

Décision:
- **séparer visuellement le périmètre, le statut, l'écart et la cause** (modèle à 4 dimensions validé en §6.1).

### 4.3 Le statut `Partiel` trop général

Risque:
- `Partiel` ne dit pas si le problème vient d'une couverture limitée, d'un mapping ambigu ou d'une exclusion.

Conséquence:
- badge peu actionnable,
- mauvaise compréhension du risque réel.

Décision:
- **ne pas utiliser `Partiel` comme statut principal de lecture au niveau équipement**.
- Le statut est strictement binaire: `Publié` / `Non publié`. Le détail vit dans la cause et le diagnostic.

### 4.4 `Republier` vs `Supprimer/Recréer` insuffisamment différenciés

Risque:
- deux actions proches visuellement mais très différentes en impact.

Conséquence:
- peur de casser HA,
- clics évités par prudence,
- ou clics dangereux mal compris.

Décision:
- **sortir clairement `Supprimer/Recréer` du flux normal** et le traiter comme une action de maintenance lourde.

### 4.5 Confusion entre problème produit et limitation Home Assistant

Risque:
- attribuer au plugin des effets qui relèvent du cycle de vie HA:
  - changement d'`entity_id`,
  - perte d'historique,
  - références cassées dans dashboards ou automatisations.

Conséquence:
- perte de confiance injustifiée,
- mauvaise promesse produit.

Décision:
- **afficher explicitement quand une limite vient de Home Assistant et non du plugin**.

### 4.6 Surcharge visuelle

Risque:
- vouloir tout montrer en même temps:
  - état bridge,
  - compteurs,
  - inclusion,
  - exclusions par source,
  - causes,
  - actions.

Conséquence:
- écran dense,
- faible scannabilité,
- produit perçu comme "outil expert".

Décision:
- **progressive disclosure stricte** avec densité maîtrisée par niveau.

## 5. Recommandations UX structurantes

### 5.1 Faire de la pièce le niveau de pilotage, pas le seul niveau d'analyse

Recommandation:
- La vue principale doit être organisée **par pièce**, car c'est le bon niveau de décision pour inclure/exclure un sous-ensemble cohérent du parc.
- Cette vue doit être précédée d'un **résumé global** permettant de comprendre l'état d'ensemble sans ouvrir chaque pièce.

Pourquoi:
- cohérent avec `jeeObject -> eqLogic -> cmd`,
- cohérent avec le besoin utilisateur "je veux une maison HA propre par zones",
- cohérent avec l'épique attendu "pilotage par pièce + exclusions par source au niveau équipement".

### 5.2 Adopter une console en trois couches

Structure recommandée:

| Couche | Rôle UX | Contenu visible par défaut |
|---|---|---|
| Global | Comprendre l'état global et lancer les actions globales | santé du pont, compteurs, filtres globaux, actions globales |
| Pièce | Piloter le périmètre à la bonne granularité | nom pièce, inclusion/exclusion, compteurs (Total/Inclus/Exclus/Écarts), actions pièce |
| Équipement | Expliquer et corriger | périmètre par source, statut binaire, écart, cause métier, action recommandée, actions équipement |

Décision:
- **pas d'écran flat "100 équipements + 12 actions" comme vue primaire**.
- **pas de navigation séparée par onglets globaux/pièces/équipements** qui casserait la relation d'héritage.

### 5.3 Exprimer les exclusions par leur source

Recommandation:
- Le concept d'**exception** disparaît de l'interface utilisateur.
- Chaque exclusion est exprimée par sa **source**, dans un vocabulaire métier immédiatement compréhensible:
  - `Exclu par la pièce`
  - `Exclu par le plugin`
  - `Exclu sur cet équipement`
- Un équipement inclus est simplement `Inclus` — sans mention d'héritage.

Pourquoi:
- Le vocabulaire `Hérite de la pièce` / `Exception locale` reflète le modèle d'implémentation, pas le modèle mental utilisateur.
- L'utilisateur ne raisonne pas en termes d'héritage ni de déviation par rapport à une règle parent.
- Il raisonne en termes de **source de la décision** : "Qui a exclu cet équipement ?"

Décision:
- Supprimer les termes `Hérite de la pièce`, `Exception locale`, le compteur `Exceptions`.
- Le détail par source d'exclusion est accessible en niveau secondaire (synthèse de périmètre).

### 5.4 Séparer configuration locale et application à HA

Recommandation:
- Les changements d'inclusion/exclusion doivent être compris comme des **décisions de périmètre**.
- Leur effet sur Home Assistant doit être **annoncé explicitement**, pas exécuté de manière ambiguë.

Décision:
- Après modification locale, signaler l'écart créé via le modèle standard:
  - Écart = Oui, Cause = `Changement en attente d'application à Home Assistant`
- Le signal est porté par le modèle existant (dimension Écart + Cause), pas par un badge générique additionnel.
- Éviter qu'un simple toggle donne l'impression d'une suppression immédiate côté HA.

### 5.5 Limiter le nombre d'éléments visibles par niveau

Règle de densité recommandée:
- **Global**: 4 indicateurs santé compacts et obligatoires max + compteurs + 2 actions majeures visibles.
- **Pièce**: nom, inclusion, 4 compteurs (Total/Inclus/Exclus/Écarts), 1-2 actions.
- **Équipement**: périmètre par source, statut binaire, indicateur d'écart, cause (si écart), action recommandée, 1 menu d'actions.

Décision:
- Tout le reste doit être au niveau détail, accordéon ou panneau secondaire.

### 5.6 Distinguer le rôle de la console et du diagnostic

Recommandation:
- La **console** est la surface de pilotage lisible. Elle permet de comprendre le périmètre, d'identifier les écarts et d'agir.
- Le **diagnostic** est la surface d'explicabilité détaillée. Il fournit les détails techniques pour comprendre *pourquoi* un écart existe.

| Surface | Rôle | Population | Contenu principal |
|---|---|---|---|
| **Console principale** | Pilotage et action | Tous les équipements (in-scope + exclus via synthèse de périmètre) | Compteurs, périmètre par source, statut, écart, cause métier, actions |
| **Diagnostic utilisateur** | Explicabilité in-scope | Équipements in-scope uniquement (`périmètre = Inclus`) | Statut, écart, cause, détails commandes/typage, confiance |
| **Export support complet** | Support technique | Tous les équipements | Vue technique exhaustive (confiance, commandes, typage, reason_code) |

Décision:
- La console et le diagnostic partagent la même taxonomie de base (Périmètre/Statut/Écart/Cause).
- Le diagnostic ajoute un niveau de détail supplémentaire (confiance, commandes observées, typage Jeedom).
- La **confiance** (`Sûr` / `Probable` / `Ambigu`) n'est jamais visible en console. Elle est réservée au diagnostic technique.
- Les équipements **exclus** restent visibles dans la synthèse de périmètre (console) avec leur source d'exclusion, mais ne produisent pas d'entrée diagnostic détaillée.

## 6. Recommandations de vocabulaire / statuts / messages

### 6.1 Modèle utilisateur à 4 dimensions : Périmètre → Statut → Écart → Cause

Le modèle utilisateur de la console V1.1 repose sur **quatre dimensions**, lues dans cet ordre:

| Dimension | Question utilisateur | Valeurs / Libellés | Niveau de lecture |
|---|---|---|---|
| **Périmètre** | "Cet équipement fait-il partie de mon scope ?" | `Inclus` · `Exclu par la pièce` · `Exclu par le plugin` · `Exclu sur cet équipement` | Équipement, pièce (compteurs), global (compteurs) |
| **Statut** | "Est-il projeté dans Home Assistant ?" | `Publié` · `Non publié` | Équipement uniquement (binaire) |
| **Écart** | "Y a-t-il un désalignement ?" | Oui / Non (bidirectionnel) | Équipement, pièce (compteur), global (compteur) |
| **Cause** | "Pourquoi ce statut ou cet écart ?" | Libellés métier explicites (`cause_label`) | Équipement uniquement (si écart = Oui) |

Ce modèle remplace le découpage précédent (Périmètre / État de projection / Raison principale / Impact en attente) et unifie la lecture console et diagnostic.

Changements clés par rapport à la version précédente:
- `État de projection` → `Statut` : strictement binaire (`Publié` / `Non publié`), n'existe qu'au niveau équipement.
- `Raison principale` → `Cause` : libellé métier explicite, dérivé du `reason_code` backend via le contrat `cause_code`/`cause_label`.
- `Impact en attente` → absorbé par `Écart` : un exclu encore publié est un écart avec cause "Changement en attente d'application".
- `Exception locale` / `Hérite de la pièce` → supprimés : remplacés par l'expression du périmètre par source.

L'écart est **bidirectionnel**:

| Décision locale | État projeté | Écart | Cause type |
|---|---|---|---|
| Inclus | Publié | Non | — |
| Inclus | Non publié | **Oui** | Mapping ambigu, Type non supporté, Bridge indisponible… |
| Exclu | Non publié | Non | — |
| Exclu | Publié | **Oui** | Changement en attente d'application |

### 6.2 Vocabulaire recommandé

#### Libellés du modèle utilisateur

**Périmètre:**
- `Inclus`
- `Exclu par la pièce`
- `Exclu par le plugin`
- `Exclu sur cet équipement`

**Statut (niveau équipement uniquement):**
- `Publié`
- `Non publié`

**Compteurs (niveaux pièce et global):**
- `Total`
- `Inclus`
- `Exclus`
- `Écarts`

**Actions:**
- `Republier dans Home Assistant`
- `Supprimer puis recréer dans Home Assistant`

**Portée:**
- `Global`
- `Pièce`
- `Équipement`

**Santé:**
- `Bridge`
- `MQTT`
- `Dernière synchro`

#### Termes interdits en interface utilisateur

Les termes suivants ne doivent jamais apparaître dans la console ni dans le diagnostic utilisateur:

| Terme interdit | Remplacement | Raison |
|---|---|---|
| `Hérite de la pièce` | `Inclus` ou `Exclu par la pièce` | Concept d'implémentation, pas modèle utilisateur |
| `Exception locale` | `Exclu sur cet équipement` | Même raison |
| `is_exception` | *(supprimé)* | Concept interne |
| `decision_source` | *(supprimé)* | Concept interne |
| `inherit` | *(supprimé)* | Concept interne |
| `include` / `exclude` (anglais) | `Inclus` / `Exclu par [source]` | Langue et abstraction techniques |
| `Partiellement publié` | `Publié` + diagnostic détaillé | Statut fourre-tout anxiogène |
| `Ambigu` (comme statut) | `Non publié`, Cause = `Mapping ambigu` | Mélange état et cause |
| `Non supporté` (comme statut) | `Non publié`, Cause = `Type non supporté en V1` | Mélange état et cause |
| `Exceptions` (compteur) | `Exclus` + détail par source en secondaire | Le terme ne correspond pas au vécu utilisateur |

Le mot `discovery` peut rester présent dans un niveau expert ou support, mais **pas comme libellé d'action primaire**.

### 6.3 Structure standard de message par équipement

Structure recommandée pour chaque équipement in-scope en écart:
1. **Statut** (binaire)
2. **Cause** (libellé métier)
3. **Action recommandée** (si remédiation simple)
4. **Impact HA** (si pertinent)

Exemples alignés sur le modèle Périmètre/Statut/Écart/Cause:

**Inclus, Non publié — Mapping ambigu**
- Statut: `Non publié`
- Cause: `Mapping ambigu — plusieurs types possibles`
- Action recommandée: `Vérifier le type générique ou la structure des commandes dans Jeedom.`

**Inclus, Non publié — Type non supporté**
- Statut: `Non publié`
- Cause: `Type non supporté en V1`
- Action recommandée: `Aucune action immédiate. Cette limite relève du périmètre produit.`

**Inclus, Non publié — Bridge indisponible**
- Statut: `Non publié`
- Cause: `Bridge indisponible`
- Action recommandée: `Vérifier MQTT puis relancer l'opération.`

**Exclu mais encore publié — Changement en attente**
- Statut: `Publié` *(écart)*
- Cause: `Changement en attente d'application`
- Action recommandée: `Republier pour appliquer le changement.`
- Impact HA: `Le retrait effectif dépendra de la prochaine application des changements.`

### 6.4 Règle de formulation critique

Quand la limite vient de Home Assistant, le message doit le dire explicitement.  
Formulation recommandée:
- `Limitation Home Assistant: ...`

Exemples:
- `Limitation Home Assistant: la suppression/recréation peut casser l'historique des entités.`
- `Limitation Home Assistant: l'entity_id final peut évoluer selon les règles de déduplication de HA.`

### 6.5 Table de mapping ancien → nouveau modèle

Cette table formalise la correspondance entre l'ancien modèle de statuts (Epic 3) et le nouveau modèle à 4 dimensions:

| Ancien statut (Epic 3) | Périmètre | Statut | Écart | Cause |
|---|---|---|---|---|
| `Publié` | Inclus | Publié | Non | — |
| `Partiellement publié` | Inclus | Publié | Non | *(détail en diagnostic)* |
| `Exclu` | Exclu par [source] | Non publié | Non | — |
| `Ambigu` | Inclus | Non publié | **Oui** | Mapping ambigu |
| `Non supporté` | Inclus | Non publié | **Oui** | Type non supporté en V1 |
| `Incident infrastructure` | *(inchangé)* | Non publié | **Oui** | Bridge indisponible |

Cas d'écart bidirectionnel ajouté:

| Situation | Périmètre | Statut | Écart | Cause |
|---|---|---|---|---|
| Exclu mais encore publié | Exclu par [source] | Publié | **Oui** | Changement en attente d'application |

Règle: le frontend ne fait aucun mapping. Le backend fournit les 4 dimensions déjà résolues.

## 7. Recommandations sur confirmations et sécurité d'usage

### 7.1 Principe directeur

La sécurité d'usage doit être **graduée selon l'impact réel**, pas selon la complexité perçue du terme technique.

### 7.2 Matrice recommandée

| Action | Portée | Niveau de sécurité recommandé |
|---|---|---|
| Inclure / Exclure | Pièce / équipement | pas de modale bloquante; feedback immédiat + signal `changements à appliquer` |
| Republier | Équipement | pas de modale obligatoire si le scope est explicite dans le contexte |
| Republier | Pièce | confirmation légère avec rappel du nombre d'équipements impactés |
| Republier | Global | confirmation explicite avec portée et compteurs |
| Supprimer puis recréer | Équipement | modale de confirmation forte |
| Supprimer puis recréer | Pièce | modale de confirmation forte avec rappel des impacts HA |
| Supprimer puis recréer | Global | modale forte + case de compréhension recommandée |

### 7.3 Règles de présentation

Règles à figer:
- `Supprimer puis recréer` ne doit jamais être présenté comme une variation visuelle mineure de `Republier`.
- L'action destructrice doit être placée dans une zone de maintenance secondaire ou un menu avancé.
- Le bouton de confirmation doit reprendre l'action et la portée:
  - `Supprimer puis recréer 12 équipements`
  - pas `Confirmer`

### 7.4 Contenu minimum d'une confirmation à impact fort

Une confirmation `Supprimer puis recréer` doit toujours rappeler:
- la portée réelle,
- le nombre d'équipements concernés,
- que l'action est destinée à reconstruire la représentation HA,
- que certaines conséquences relèvent de Home Assistant:
  - historique potentiellement perdu,
  - dashboards/automatisations potentiellement impactés,
  - `entity_id` potentiellement modifié selon les règles HA.

### 7.5 Gating par l'état du bridge

Recommandation:
- Si le démon ou MQTT est indisponible, les **actions de maintenance HA** doivent être désactivées ou bloquées avec raison visible.
- Les **décisions de périmètre locales** peuvent rester modifiables.

Cela évite de faire croire à l'utilisateur qu'une action sera appliquée alors que l'infrastructure ne le permet pas.

## 8. Recommandations sur la hiérarchie global / pièce / équipement

### 8.1 Niveau global

Doit répondre à:
- `Le bridge fonctionne-t-il ?`
- `Combien d'équipements sont inclus, exclus, en écart ?`
- `Quelle action globale puis-je lancer ?`

Contenu recommandé:
- bandeau santé minimal,
- compteurs globaux,
- filtres globaux,
- actions globales de maintenance.

### 8.2 Niveau pièce

Doit répondre à:
- `Cette pièce est-elle incluse dans le périmètre ?`
- `Combien d'équipements sont inclus, exclus, en écart ?`
- `Quelle action de portée pièce puis-je lancer ?`

Contenu recommandé:
- nom pièce,
- état d'inclusion,
- **compteurs** (lecture principale à ce niveau):
  - Total,
  - Inclus,
  - Exclus,
  - Écarts,
- action `Republier la pièce`,
- accès aux détails équipements.

Il n'y a **pas de statut agrégé** pièce réutilisant le champ `Publié`/`Non publié` du niveau équipement. Si un indicateur visuel synthétique est conservé (badge d'alerte quand `Écarts > 0`), il doit être défini comme dérivé des compteurs et nommé différemment.

### 8.3 Niveau équipement

Doit répondre à:
- `Cet équipement fait-il partie de mon scope ?` → **Périmètre**
- `Est-il projeté dans HA ?` → **Statut** (Publié / Non publié)
- `Y a-t-il un désalignement ?` → **Écart**
- `Pourquoi ?` → **Cause** (si écart)
- `Quelle action simple est pertinente ?`

Contenu recommandé:
- périmètre par source (`Inclus` / `Exclu par [source]`),
- statut binaire (`Publié` / `Non publié`) — seul niveau où ce statut existe,
- indicateur d'écart,
- cause métier lisible (si écart = Oui),
- action recommandée,
- menu d'actions.

La confiance (`Sûr` / `Probable` / `Ambigu`) n'apparaît pas à ce niveau. Elle est accessible uniquement dans le diagnostic technique détaillé.

### 8.4 Règle structurante

Une action doit toujours vivre au niveau où son impact est lisible:
- action globale dans l'en-tête global,
- action pièce dans la ligne ou le panneau pièce,
- action équipement dans le détail équipement.

Éviter absolument:
- le même bouton destructif visible à trois endroits simultanément,
- une pièce qui ouvre directement sur un mur d'équipements sans synthèse intermédiaire.

## 9. Placement recommandé de la santé minimale du pont

### 9.1 Placement

Placement recommandé:
- **tout en haut de la console**, dans un bandeau compact distinct des compteurs de publication.

Pourquoi:
- c'est une information transversale,
- elle explique la disponibilité des actions,
- elle doit être visible sans transformer l'écran en tableau technique.

### 9.2 Contenu minimal

Quatre indicateurs compacts sont requis en V1.1:
- `Bridge`
- `MQTT`
- `Dernière synchro`
- `Dernière opération` avec résultat court: `succès`, `partiel`, `échec`

### 9.3 Traduction UX recommandée

Libellés visibles:
- `Bridge actif` / `Bridge indisponible`
- `MQTT connecté` / `MQTT indisponible`
- `Dernière synchro il y a 2 min`
- `Dernière opération : succès`

Le détail technique peut rester accessible derrière un lien ou un panneau secondaire:
- nom du broker,
- horodatage absolu,
- message d'erreur détaillé.

### 9.4 Règle visuelle

- Rouge uniquement pour un incident d'infrastructure.
- Pas de mélange visuel entre "bridge down" et "mapping ambigu".
- Si un incident bridge bloque les actions HA, un message persistant doit l'indiquer clairement.

## 10. Ce qu'il faut figer avant epic planning

Les décisions suivantes doivent être figées maintenant:

1. **Architecture d'information**
   - console en trois niveaux `global -> pièce -> équipement`

2. **Modèle utilisateur à 4 dimensions**
   - Périmètre → Statut → Écart → Cause
   - Le statut binaire `Publié`/`Non publié` n'existe qu'au niveau équipement
   - Les niveaux pièce/global sont lus par compteurs (Total, Inclus, Exclus, Écarts)

3. **Disparition du concept d'exception**
   - Toute exclusion est exprimée par sa source (pièce, plugin, équipement)
   - Le compteur `Exceptions` est remplacé par `Exclus`

4. **Diagnostic centré in-scope**
   - Le diagnostic utilisateur ne porte que sur les équipements inclus
   - Les exclus restent visibles en synthèse de périmètre

5. **Placement de la confiance**
   - `Sûr` / `Probable` / `Ambigu` visible uniquement en diagnostic technique, jamais en console

6. **Vocabulaire des actions**
   - `Republier dans Home Assistant`
   - `Supprimer puis recréer dans Home Assistant`

7. **Matrice de sécurité**
   - quel niveau de confirmation selon action et portée

8. **Placement de la santé minimale**
   - bandeau global distinct, toujours visible

9. **Traitement des changements de périmètre**
   - distinguer clairement la décision locale et son application à HA

10. **Rôle console vs diagnostic**
    - console = pilotage lisible, diagnostic = explicabilité détaillée
    - même taxonomie de base, le diagnostic ajoute la confiance et les détails techniques

11. **Contrat backend → UI**
    - le frontend ne fait aucune interprétation, le backend fournit les 4 dimensions résolues
    - distinction `reason_code` (backend stable) / `cause_code`+`cause_label` (contrat UI)

Sans ces points, les epics risquent de mélanger architecture UX, wording, sécurité d'usage et logique d'exploitation.

## 11. Ce qui peut rester ouvert jusqu'aux stories

Peut rester ouvert sans bloquer l'epic planning:
- accordéon, panneau latéral ou sous-tableau pour le détail pièce/équipement;
- formulation exacte de certains micro-textes secondaires;
- choix fin entre compteurs en badges, chips ou texte synthétique;
- détail du feedback de succès après une opération;
- degré précis de densité visuelle sur tablette/mobile;
- présence ou non d'une vue transversale secondaire "tous les équipements" si les filtres pièce suffisent.

Ces sujets relèvent de l'affinage story-level ou d'une mini-maquette basse fidélité, pas d'un arbitrage produit structurant.

## 12. Vérification de non-empiètement sur les phases suivantes

Les recommandations ci-dessus **n'empiètent pas prématurément** sur les phases ultérieures:

### 12.1 Preview complète

Non empiétement:
- on recommande seulement des compteurs d'impact et des messages de conséquence,
- pas une simulation détaillée avant/après de toutes les entités.

### 12.2 Remédiation guidée avancée

Non empiétement:
- on recommande une **action recommandée simple**,
- pas un assistant multi-étapes ni une correction automatisée.

### 12.3 Santé avancée

Non empiétement:
- on limite la santé à `Bridge`, `MQTT`, `Dernière synchro`, `Dernière opération`,
- pas de timeline, pas de métriques détaillées, pas d'écran d'observabilité expert.

### 12.4 Support outillé avancé

Non empiétement:
- on recommande des raisons lisibles et des détails copiables,
- pas d'export support avancé, pas de pack diagnostic riche.

### 12.5 Extension de scope fonctionnel

Non empiétement:
- aucune recommandation n'exige d'ajouter `button`, `number`, `select`, `climate` ou d'autres familles,
- la revue porte uniquement sur le pilotage du périmètre déjà concerné.

## 13. Verdict final

**Verdict: UX suffisamment cadrée pour lancer l'epic planning, sous réserve de figer les décisions structurantes listées en section 10.**

La V1.1 Pilotable n'a pas besoin d'une refonte complète de l'UX spec. Elle a besoin d'un **addendum de clarification opérationnelle**, centré sur le modèle utilisateur **Périmètre → Statut → Écart → Cause**. Le cœur de ce cadrage tient en une idée simple: **ne pas demander à un seul écran, à un seul badge ou à un seul bouton d'expliquer à la fois le périmètre, l'état réel, la cause, l'impact et la maintenance**.

Si la planification des epics respecte:
- la hiérarchie `global -> pièce -> équipement`,
- le modèle à 4 dimensions Périmètre/Statut/Écart/Cause,
- les compteurs (Total, Inclus, Exclus, Écarts) comme lecture principale pièce/global,
- la disparition du concept d'exception au profit d'exclusions par source,
- le diagnostic centré in-scope avec confiance en diagnostic technique uniquement,
- la distinction entre `reason_code` (backend) et `cause_code`/`cause_label` (contrat UI),
- la différenciation forte `Republier` vs `Supprimer/Recréer`,
- et la visibilité explicite des impacts Home Assistant,

alors la V1.1 dispose d'un cadrage UX suffisamment clair, prédictible, explicable et sûr pour passer en epic planning.
