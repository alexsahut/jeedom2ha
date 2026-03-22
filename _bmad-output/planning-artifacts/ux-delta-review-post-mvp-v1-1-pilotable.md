# Revue UX Delta - Post-MVP V1.1 Pilotable

## 1. Executive summary

La base UX du MVP reste solide et ne doit pas être refondue. En revanche, la V1.1 Pilotable change la nature de l'écran principal: on ne parle plus seulement d'un écran de diagnostic/publication, mais d'une **console de pilotage du périmètre publié**.

La décision UX centrale est la suivante:
- **Oui, la vue par pièce est le bon point d'entrée opérationnel**, parce qu'elle correspond à la hiérarchie Jeedom et au besoin de maîtrise du parc.
- **Non, elle ne doit pas devenir l'unique modèle de lecture**, sinon l'utilisateur perd la vision globale, mélange les statuts et ne comprend plus les impacts HA.

La console V1.1 doit donc être structurée en **trois niveaux explicites**:
1. **Global**: santé minimale du pont, compteurs, actions globales.
2. **Pièce**: inclusion/exclusion, synthèse des statuts, actions de maintenance de portée pièce.
3. **Équipement**: exception locale, raison principale, action recommandée, actions de maintenance fines.

Le principal risque UX de V1.1 n'est pas le manque de fonctionnalités. C'est la **confusion**:
- confusion entre état du bridge et état de configuration,
- confusion entre ce qui est publié et pourquoi cela ne l'est pas,
- confusion entre action sûre de mise à jour et action destructrice côté Home Assistant.

Conclusion de la revue: **l'UX est suffisamment cadrée pour lancer l'epic planning**, à condition de figer immédiatement:
- la hiérarchie `global -> pièce -> équipement`,
- le modèle de vocabulaire et de statuts,
- la gradation des confirmations,
- le placement de la santé minimale du pont,
- la distinction nette entre configuration locale et action appliquée à Home Assistant.

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
- **séparer visuellement l'état, la cause et l'action possible**.

### 4.3 Le statut `Partiel` trop général

Risque:
- `Partiel` ne dit pas si le problème vient d'une couverture limitée, d'un mapping ambigu ou d'une exclusion.

Conséquence:
- badge peu actionnable,
- mauvaise compréhension du risque réel.

Décision:
- **ne pas utiliser `Partiel` comme statut principal de lecture au niveau équipement**.
- Le réserver à une synthèse agrégée pièce/global ou à un détail explicatif.

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
  - exceptions,
  - raisons,
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
- cohérent avec l'épique attendu "pilotage par pièce + exceptions équipement".

### 5.2 Adopter une console en trois couches

Structure recommandée:

| Couche | Rôle UX | Contenu visible par défaut |
|---|---|---|
| Global | Comprendre l'état global et lancer les actions globales | santé du pont, compteurs, filtres globaux, actions globales |
| Pièce | Piloter le périmètre à la bonne granularité | nom pièce, inclusion/exclusion, compteurs par statut, exceptions, actions pièce |
| Équipement | Expliquer et corriger | exception locale, état, raison principale, action recommandée, actions équipement |

Décision:
- **pas d'écran flat "100 équipements + 12 actions" comme vue primaire**.
- **pas de navigation séparée par onglets globaux/pièces/équipements** qui casserait la relation d'héritage.

### 5.3 Rendre visible l'héritage de décision

Recommandation:
- Chaque équipement doit indiquer clairement s'il:
  - **hérite de la règle de la pièce**,
  - ou fait l'objet d'une **exception locale**.

Pourquoi:
- sinon l'utilisateur ne comprend pas pourquoi un équipement reste publié dans une pièce exclue, ou inversement.

Décision:
- Introduire un indicateur simple de source de décision:
  - `Hérite de la pièce`
  - `Exception locale`

### 5.4 Séparer configuration locale et application à HA

Recommandation:
- Les changements d'inclusion/exclusion doivent être compris comme des **décisions de périmètre**.
- Leur effet sur Home Assistant doit être **annoncé explicitement**, pas exécuté de manière ambiguë.

Décision:
- Après modification locale, afficher un état du type:
  - `Changements à appliquer à Home Assistant`
- Éviter qu'un simple toggle donne l'impression d'une suppression immédiate côté HA.

### 5.5 Limiter le nombre d'éléments visibles par niveau

Règle de densité recommandée:
- **Global**: 4 indicateurs santé compacts et obligatoires max + compteurs + 2 actions majeures visibles.
- **Pièce**: nom, inclusion, 3-4 compteurs, 1 indicateur de mixité, 1-2 actions.
- **Équipement**: état, raison principale, exception oui/non, action recommandée, 1 menu d'actions.

Décision:
- Tout le reste doit être au niveau détail, accordéon ou panneau secondaire.

## 6. Recommandations de vocabulaire / statuts / messages

### 6.1 Ne pas faire porter tout le sens par un seul badge

Le modèle recommandé distingue **quatre dimensions**:

| Dimension | Question utilisateur | Recommandation |
|---|---|---|
| Périmètre | "Cet élément est-il inclus dans mon scope ?" | `Incluse`, `Exclue`, `Exception locale`, `Hérite de la pièce` |
| État de projection | "Est-il présent ou non dans HA ?" | `Publié`, `Non publié`, `Mise à jour en cours`, `Échec bridge` |
| Raison principale | "Pourquoi ?" | `Exclusion volontaire`, `Couverture limitée`, `Mapping ambigu`, `Configuration incomplète`, `Incident bridge` |
| Impact en attente | "Y a-t-il un changement non appliqué ?" | `Changements à appliquer` |

Ce découpage est plus clair qu'un unique catalogue de statuts hétérogènes.

### 6.2 Vocabulaire recommandé

Libellés à privilégier:
- **Action**:
  - `Republier dans Home Assistant`
  - `Supprimer puis recréer dans Home Assistant`
- **Portée**:
  - `Global`
  - `Pièce`
  - `Équipement`
- **Santé**:
  - `Bridge`
  - `MQTT`
  - `Dernière synchro`

Libellés à éviter en premier niveau:
- `Discovery`
- `Rescan` comme libellé principal utilisateur
- `Partiel` sans explication
- `Erreur` si la situation est en réalité une action de configuration requise

Le mot `discovery` peut rester présent dans un niveau expert ou support, mais **pas comme libellé d'action primaire**.

### 6.3 Structure standard de message par équipement

Structure recommandée:
1. **État court**
2. **Raison principale**
3. **Action recommandée**
4. **Impact HA** si pertinent

Exemples:

**Exclusion volontaire**
- État: `Non publié`
- Raison principale: `Équipement exclu par votre configuration.`
- Action recommandée: `Réinclure cet équipement si vous voulez le republier.`
- Impact HA: `Le retrait effectif dépendra de la prochaine application des changements.`

**Couverture limitée**
- État: `Non publié`
- Raison principale: `Ce type d'équipement n'est pas couvert en V1.1.`
- Action recommandée: `Aucune action immédiate. Cette limite relève du périmètre produit.`

**Mapping ambigu**
- État: `Non publié`
- Raison principale: `Le mapping est ambigu et la publication est bloquée par sécurité.`
- Action recommandée: `Vérifier le type générique ou la structure des commandes dans Jeedom.`

**Incident bridge**
- État: `Échec bridge`
- Raison principale: `Le bridge ne peut pas publier car la connexion MQTT est indisponible.`
- Action recommandée: `Vérifier MQTT puis relancer l'opération.`

### 6.4 Règle de formulation critique

Quand la limite vient de Home Assistant, le message doit le dire explicitement.  
Formulation recommandée:
- `Limitation Home Assistant: ...`

Exemples:
- `Limitation Home Assistant: la suppression/recréation peut casser l'historique des entités.`
- `Limitation Home Assistant: l'entity_id final peut évoluer selon les règles de déduplication de HA.`

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
- `Combien d'éléments sont publiés, non publiés, à revoir ?`
- `Quelle action globale puis-je lancer ?`

Contenu recommandé:
- bandeau santé minimal,
- compteurs globaux,
- filtres globaux,
- actions globales de maintenance.

### 8.2 Niveau pièce

Doit répondre à:
- `Cette pièce est-elle incluse dans le périmètre ?`
- `Quel est son état global ?`
- `Y a-t-il des exceptions ou des problèmes ?`

Contenu recommandé:
- nom pièce,
- état d'inclusion,
- compteurs:
  - publiés,
  - non publiés,
  - exceptions,
  - problèmes à revoir,
- action `Republier la pièce`,
- accès aux détails équipements.

### 8.3 Niveau équipement

Doit répondre à:
- `Cet équipement est-il publié ?`
- `Pourquoi ?`
- `Est-ce un cas hérité ou une exception ?`
- `Quelle action simple est pertinente ?`

Contenu recommandé:
- état de projection,
- raison principale,
- source de décision (`hérite` / `exception locale`),
- action recommandée,
- menu d'actions.

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

2. **Modèle d'héritage**
   - un équipement hérite de la pièce ou passe en exception locale

3. **Séparation des dimensions**
   - périmètre
   - état de projection
   - raison principale
   - santé du bridge

4. **Vocabulaire des actions**
   - `Republier dans Home Assistant`
   - `Supprimer puis recréer dans Home Assistant`

5. **Matrice de sécurité**
   - quel niveau de confirmation selon action et portée

6. **Placement de la santé minimale**
   - bandeau global distinct, toujours visible

7. **Traitement des changements de périmètre**
   - distinguer clairement la décision locale et son application à HA

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

La V1.1 Pilotable n'a pas besoin d'une refonte complète de l'UX spec. Elle a besoin d'un **addendum de clarification opérationnelle**. Le cœur de ce cadrage tient en une idée simple: **ne pas demander à un seul écran, à un seul badge ou à un seul bouton d'expliquer à la fois le périmètre, l'état réel, la cause, l'impact et la maintenance**.

Si la planification des epics respecte:
- la hiérarchie `global -> pièce -> équipement`,
- la séparation entre état, cause et santé du bridge,
- la différenciation forte `Republier` vs `Supprimer/Recréer`,
- et la visibilité explicite des impacts Home Assistant,

alors la V1.1 dispose d'un cadrage UX suffisamment clair, prédictible, explicable et sûr pour passer en epic planning.
