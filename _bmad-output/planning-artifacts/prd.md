---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish']
inputDocuments:
  - 'docs/cadrage_plugin_jeedom_ha_bmad.md'
  - '_bmad-output/brainstorming/brainstorming-session-2026-03-12-001.md'
  - '_bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-03-12.md'
  - '_bmad-output/planning-artifacts/research/domain-jeedom-homeassistant-research-2026-03-12.md'
  - '_bmad-output/planning-artifacts/research/technical-jeedom-plugin-development-research-2026-03-12.md'
documentCounts:
  briefs: 1
  research: 2
  brainstorming: 1
  projectDocs: 1
classification:
  projectType: 'interoperability_middleware / home_automation_bridge_plugin'
  technicalNature: 'Plugin Jeedom + Daemon Python + MQTT-based integration layer'
  domain: 'smart_home / home_automation_interoperability'
  complexity: 'high'
  complexityDetail:
    product_integration: 'high'
    algorithmic: 'medium'
    ecosystem_lifecycle: 'high'
  projectContext: 'brownfield_discovery_greenfield_implementation'
  productNature: 'ecosystem_bridge / coexistence_layer / migration_light_enabler'
workflowType: 'prd'
---

# Product Requirements Document - jeedom2ha

**Author:** Alexandre
**Date:** 2026-03-12

## Executive Summary

**jeedom2ha** est un plugin Jeedom avec démon Python qui projette automatiquement une installation Jeedom existante dans Home Assistant via MQTT Discovery. Il résout un faux dilemme : l'utilisateur Jeedom ne devrait pas avoir à choisir entre protéger son investissement domotique historique et accéder aux capacités modernes de Home Assistant (interfaces, assistants vocaux, IA locale, Matter).

Le produit cible les utilisateurs Jeedom avancés disposant d'une installation riche et stable (60-120+ équipements, scénarios, multi-protocoles) qui veulent exploiter Home Assistant sans migration brutale ni double maintenance. En moins d'une heure, l'utilisateur retrouve dans HA ses usages essentiels — lumières, volets, prises, capteurs — avec des noms cohérents, un contexte spatial exploitable et un pilotage fiable sur le périmètre supporté. Jeedom reste le moteur d'exécution ; Home Assistant devient la couche d'interface, de visualisation et d'interaction moderne.

La promesse V1 est volontairement contenue : retrouver rapidement dans Home Assistant une version utile de sa maison Jeedom, sur un périmètre réduit mais immédiatement exploitable, sans migration lourde ni reconstruction manuelle.

### Ce qui rend ce produit spécial

**Capitaliser plutôt que reconstruire.** Contrairement aux approches existantes qui imposent un choix de plateforme ou un remapping manuel fragile, jeedom2ha transforme un actif Jeedom existant en source d'entités HA natives — sans recoder, sans migrer, sans créer une deuxième maison à maintenir.

**Time to value spectaculaire.** Le moment déclic n'est pas technique : c'est quand l'utilisateur ouvre HA et constate que sa maison est déjà là, exploitable, avec des noms cohérents et un contexte spatial exploitable. Ce moment doit arriver en moins d'une heure après l'installation.

**Réversibilité forte.** Le plugin peut être retiré proprement sans migration irréversible du modèle domotique, ce qui permet d'explorer HA sans s'enfermer dans un tunnel de transition.

**Timing favorable.** Home Assistant se renforce comme plateforme ouverte, notamment avec la certification Matter annoncée en mars 2025, tandis que Jeedom reste un écosystème actif avec des box officielles commercialisées avec Domadoo. Le contexte rend la coexistence plus crédible et plus désirable qu'une migration brutale.

## Classification projet

| Dimension | Classification |
|---|---|
| **Type projet** | Middleware d'interopérabilité / Bridge plugin domotique |
| **Nature technique** | Plugin Jeedom + Démon Python + Couche d'intégration MQTT |
| **Domaine** | Smart Home / Interopérabilité domotique résidentielle |
| **Complexité** | Haute (produit & intégration : haute · algorithmique : moyenne · écosystème & cycle de vie : haute) |
| **Contexte projet** | Brownfield discovery, greenfield implementation |
| **Nature produit** | Pont d'écosystème / couche de coexistence / facilitateur de transition douce |

## Critères de Succès

### Succès Utilisateur

**Le moment déclic :** L'utilisateur installe le plugin, lance la synchro, ouvre Home Assistant et retrouve immédiatement ses usages essentiels du quotidien — lumières, volets, prises, capteurs — avec des noms cohérents et un contexte spatial exploitable, sans reconstruction manuelle.

**Indicateurs de succès utilisateur :**
- **Time to first useful value < 1h** : de l'installation du plugin à une maison exploitable dans HA.
- **Taux de première synchronisation réussie** : l'utilisateur ne doit pas abandonner avant d'avoir vu un premier résultat.
- **Compréhension du périmètre** : l'utilisateur comprend ce qui est publié, ce qui ne l'est pas, et pourquoi (diagnostic intégré).
- **Pilotage fiable** : les commandes simples depuis HA (allumer, éteindre, ouvrir, fermer) fonctionnent de manière cohérente sur le périmètre V1.
- **Pas de remapping manuel récurrent côté HA** : l'utilisateur n'a pas à recréer ou maintenir manuellement équipement par équipement sa maison dans Home Assistant.

### Succès Business / Projet

Le succès à 3 mois ne se mesure pas au volume brut d'installations mais à la viabilité du produit pour un mainteneur solo à ~5h/semaine.

**4 signaux de succès à 3 mois :**

1. **Valeur perçue réelle** : des utilisateurs confirment explicitement que le plugin leur évite une migration ou une reconstruction manuelle.
2. **Noyau d'installations actives** : un nombre limité mais réel d'utilisateurs qui dépassent la première synchro et utilisent le plugin dans la durée.
3. **Charge de support soutenable** : les tickets sont compréhensibles, se regroupent sur des thèmes traitables, et ne saturent pas la capacité du mainteneur.
4. **Perception communautaire positive** : pas de rejet fort, pas de réputation de plugin cassé ou trompeur, quelques retours validant la promesse centrale.

**KPIs concrets :**

| KPI | Cible 3 mois | Mesure |
|---|---|---|
| Installations actives réelles | ≥ 15-20 installations actives (instance ayant réalisé au moins une synchro réussie et toujours activée à J+30) | Télémétrie plugin ou Market |
| Rétention à 30 jours | > 40% des premières synchros réussies | Plugin actif après 30j |
| Au-delà de la première synchro | > 50% des installateurs | Utilisateurs ayant réalisé au moins une action post-synchro significative (filtres, dashboard, commande HA→Jeedom, republication, etc.) |
| Bugs critiques ouverts | < 5 simultanément | Tracker |
| Volume mensuel de support | < 2-3h/semaine de traitement | Tickets/mois |
| Verbatim "évite la migration" | Présent | Forums, Market, retours directs |

### Succès Technique

- **Latence** : cible ≤ 2s (idéal ~1s) pour les commandes simples du périmètre V1 en contexte nominal. Inacceptable ≥ 5s.
- **Fiabilité** : démon stable, reconnexion automatique, cycle de vie propre, pas d'accumulation de fantômes.
- **Diagnostic** : couverture intégrée par équipement (publié / partiel / non publié + raison), logs exploitables.

Les exigences fonctionnelles et non-fonctionnelles formalisent ci-dessous ces objectifs en contrat testable.

### Résultats Mesurables

| Résultat | Critère | Priorité | Référence |
|---|---|---|---|
| Maison exploitable dans HA en < 1h | Lumières, volets, prises, capteurs visibles et pilotables | P0 | FR1, FR10–FR17, NFR1 |
| Diagnostic de couverture clair | Par équipement : publié / partiel / non publié + raison | P0 | FR26–FR30 |
| Latence ≤ 2s sur commandes simples | En contexte nominal sur périmètre V1 | P0 | NFR1 |
| Pas d'accumulation d'entités fantômes | Cycle de vie propre en usage normal | P0 | FR20–FR25, NFR7–NFR10 |
| Support soutenable | < 2-3h/sem de traitement support | P0 | — |
| Rétention 30j > 40% | Utilisateurs au-delà du simple test | P1 | — |

## Périmètre Produit

Le périmètre produit détaillé est défini dans la section **Scoping & Développement Phasé**, qui fait foi pour la distinction MVP / Growth / Vision.

## Parcours Utilisateurs

### Parcours 1 — Nicolas : Happy Path — "Ma maison est déjà là"

**Qui :** Nicolas, 47 ans, utilisateur Jeedom depuis 4 ans. 85 équipements, scénarios complexes, Z-Wave + Zigbee + quelques virtuels. Installation propre, types génériques bien renseignés grâce à son usage de Homebridge.

**Scène d'ouverture :** Nicolas lit un post sur le forum HACF mentionnant un nouveau plugin Jeedom qui projette sa maison dans HA via MQTT Discovery. Il est intrigué — il a installé HA en parallèle il y a 6 mois mais n'a jamais eu le courage de recréer ses équipements un par un.

**Action :**
1. Il installe le plugin depuis le Market Jeedom.
2. Si MQTT Manager est présent, le plugin récupère automatiquement la configuration broker — aucun paramètre MQTT à saisir manuellement.
3. Il lance la première synchronisation depuis l'interface du plugin.
4. Le diagnostic de couverture s'affiche : 62 équipements publiables, 8 partiellement publiables (raison indiquée), 15 non publiables (types génériques manquants ou famille non supportée V1).
5. Il valide et lance la publication.

**Moment déclic :** Il ouvre Home Assistant. L'intégration MQTT affiche "Nouveaux appareils découverts". Il clique. Ses lumières du salon, les volets de la chambre, le capteur de température extérieur — tout est là, avec des noms cohérents et un contexte spatial exploitable. Il allume une lumière depuis HA : elle s'allume. L'état remonte en moins de 2 secondes.

**Résolution :** En 45 minutes, Nicolas a une maison exploitable dans HA. Il commence à créer un dashboard Lovelace. Le soir, il montre à sa conjointe : "Regarde, toute la maison est dans HA maintenant". Il n'a rien recodé.

**Exigences révélées :** Bootstrap automatique, auto-détection MQTT Manager (si présent) + configuration broker manuelle en fallback, diagnostic de couverture P0, mapping types génériques, publication MQTT Discovery, nommage cohérent, contexte spatial exploitable, latence ≤ 2s.

---

### Parcours 2 — Nicolas : Edge Case — "Pourquoi ma maison est à moitié vide ?"

**Qui :** Nicolas, même profil, mais cette fois sur une partie de son installation moins bien typée — des équipements issus de plugins tiers avec des types génériques partiels ou absents.

**Scène d'ouverture :** Nicolas lance la synchro, confiant après avoir lu la promesse du plugin. Il ouvre HA et ne voit que 25 entités sur les 85 équipements qu'il espérait. Pas d'erreur visible. Première réaction : "ça ne marche pas".

**Action :**
1. Il retourne dans l'interface du plugin Jeedom et ouvre le diagnostic de couverture.
2. Le diagnostic lui montre, équipement par équipement : publié / partiellement publié / non publié, avec la raison principale.
3. Il découvre que ses modules Xiaomi (plugin tiers) n'ont aucun type générique renseigné, que ses virtuels agrégés ne correspondent à aucun modèle HA clair, et que 3 capteurs ont un type générique ambigu.
4. Le diagnostic lui suggère : "Cet équipement n'a pas de type générique. Configurez-le dans Jeedom > Outils > Types génériques pour qu'il soit publiable."
5. Il corrige les types génériques de 12 équipements prioritaires dans Jeedom.
6. Il relance un rescan. 15 nouvelles entités apparaissent dans HA.

**Résolution :** Nicolas comprend que le résultat dépend de la qualité de son typage Jeedom. Il n'est pas frustré parce que le diagnostic est clair et actionnable. Il sait exactement quoi faire pour améliorer la couverture.

**Exigences révélées :** Diagnostic par équipement avec raison précise, suggestions de remédiation, rescan manuel post-correction, dégradation élégante (ne pas publier plutôt que publier faux), messages non techniques.

---

### Parcours 3 — Julien : "Je veux juste voir si ça vaut le coup"

**Qui :** Julien, 38 ans, utilisateur Jeedom intermédiaire depuis 2 ans. 40 équipements, installation fonctionnelle mais pas parfaitement typée. Il a installé HA sur un Raspberry Pi par curiosité mais n'a jamais rien configuré dedans.

**Scène d'ouverture :** Julien voit un tuto YouTube sur jeedom2ha. Il se dit "allez, j'essaie, si ça ne marche pas je désinstalle".

**Action :**
1. Il installe le plugin. Il n'a pas MQTT Manager — le plugin le détecte et lui indique clairement qu'un broker MQTT est nécessaire, avec un lien vers le guide d'installation.
2. Il installe MQTT Manager, configure le broker local, revient dans jeedom2ha.
3. Il lance la synchro. Le diagnostic montre : 18 équipements publiables, 22 non publiables.
4. Il ouvre HA : 18 entités apparaissent. Ses lumières Z-Wave sont là. Ses capteurs Xiaomi non.
5. Il allume une lumière depuis HA — ça marche. Il ouvre un volet — ça marche.
6. Il montre ça à son collègue le lendemain : "Regarde, j'ai ma maison dans HA sans avoir rien reconfiguré côté HA."

**Moment de décision :** Julien se demande s'il garde le plugin. 18 entités sur 40 équipements, c'est partiel. Mais ce qu'il a fonctionne, et il voit le potentiel. Il décide de garder le plugin actif et de corriger progressivement ses types génériques quand il a le temps.

**Résolution :** Julien n'a pas migré, il n'a pas reconstruit, et il peut revenir en arrière sans conséquence. Le plugin a gagné son droit de rester installé.

**Exigences révélées :** Détection claire de l'absence de MQTT Manager avec guidance, fonctionnement utile même avec couverture partielle, expérience de valeur immédiate même limitée, faible coût psychologique du test, réversibilité forte.

---

### Parcours 4 — Sébastien : "Je pilote une coexistence choisie"

**Qui :** Sébastien, 45 ans, utilisateur Jeedom confirmé depuis 5 ans. 110 équipements. Il anticipe une transition progressive vers HA comme frontend principal, mais refuse le "big bang" migratoire.

**Scène d'ouverture :** Sébastien utilise jeedom2ha depuis 3 mois. Il a publié 70 équipements dans HA. Sa famille utilise désormais les dashboards HA au quotidien. Jeedom continue de gérer tous les scénarios et automatismes en coulisses.

**Action :**
1. Il décide de migrer son éclairage Zigbee directement dans HA via Zigbee2MQTT, pour bénéficier de la latence native et des groupes HA.
2. Il exclut ces équipements de jeedom2ha (filtres d'exclusion dans le plugin).
3. Il vérifie dans HA que les entités jeedom2ha correspondantes ont bien disparu et que les entités Z2M natives prennent le relais.
4. Il conserve jeedom2ha pour tout le reste : volets, capteurs, prises, et les équipements dont la gestion reste meilleure dans Jeedom.
5. Progressivement, mois après mois, il déplace certains cas unitaires vers HA natif tout en gardant jeedom2ha comme filet de continuité.

**Résolution :** jeedom2ha n'est pas un tunnel de migration — c'est un outil de continuité de service. Sébastien limite les ruptures d'usage et pilote sa transition à son propre rythme.

**Exigences révélées :** Filtres d'exclusion par équipement / famille, suppression propre des entités exclues, coexistence avec d'autres intégrations HA sans conflit, stabilité dans la durée, indépendance des entités jeedom2ha vis-à-vis des entités natives.

---

### Parcours 5 — Nicolas : "Je découvre des doublons non désirés après la première synchro"

**Qui :** Nicolas, même profil. Mais il a déjà dans HA une dizaine d'équipements via Zigbee2MQTT et 5 capteurs via ESPHome. Il installe jeedom2ha en plus.

**Scène d'ouverture :** Après la synchro, Nicolas ouvre HA et constate le problème : sa "Lampe Salon" existe maintenant en double — une entité Z2M native et une entité jeedom2ha. Son assistant vocal ne sait plus laquelle choisir. Trois capteurs de température apparaissent deux fois.

**Action :**
1. Il retourne dans le plugin et ouvre la vue de diagnostic.
2. Il identifie les équipements en doublon potentiel — ceux dont le nom ou la pièce correspond à des entités déjà présentes dans HA.
3. Il utilise les filtres d'exclusion du plugin pour retirer les équipements qu'il gère déjà nativement dans HA.
4. Il relance un rescan. Les doublons disparaissent de la publication jeedom2ha.
5. Il ne reste dans jeedom2ha que les équipements qui n'ont pas d'équivalent natif dans HA.

**Résolution :** Nicolas a un HA propre, sans doublon, où jeedom2ha complète les intégrations natives au lieu de les dupliquer. Il comprend que le plugin ne remplace pas les intégrations HA existantes — il comble les trous.

**Exigences révélées :** Filtres d'exclusion granulaires, namespace MQTT strict (pas de collision avec Z2M, ESPHome, etc.), nommage distinguable, publication conservative et capacité à exclure ce qui fait doublon avec l'existant HA.

---

### Parcours 6 — Nicolas : "Ma maison bouge, est-ce que ça suit ?"

**Qui :** Nicolas, 6 semaines après l'installation initiale. Sa maison évolue.

**Scène d'ouverture :** Nicolas vit avec jeedom2ha au quotidien. Tout fonctionne. Puis sa maison commence à bouger.

**Action — Ajout :**
1. Il ajoute un nouveau module volet dans Jeedom, le configure avec les bons types génériques.
2. Au prochain rescan (ou manuellement), le nouveau volet apparaît dans HA automatiquement, correctement typé et nommé.

**Action — Renommage :**
3. Il renomme "Lampe Bureau" en "Lampe Bureau Alex" dans Jeedom.
4. Dans HA, le nom d'affichage se met à jour. L'entité conserve le même unique_id — pas de doublon, pas de perte d'historique HA, pas de dashboard cassé.

**Action — Suppression :**
5. Il retire un vieux capteur de température de Jeedom (équipement supprimé).
6. Au prochain rescan, le plugin détecte l'absence et publie un payload de suppression MQTT Discovery. L'entité et le device disparaissent de HA. Si l'utilisateur avait des dashboards ou automatisations référençant cette entité, elles devront être ajustées — la suppression est propre techniquement, mais pas neutre côté usage.

**Action — Changement de type :**
7. Il corrige un type générique mal attribué (un switch qui aurait dû être une lumière).
8. Le plugin détecte le changement de mapping, retire l'ancienne représentation et publie la nouvelle. La transition est gérée explicitement, mais peut impliquer une rupture de représentation côté HA (nouvel identifiant logique, historique de l'ancienne entité non transféré, dashboards à ajuster).

**Résolution :** La maison de Nicolas évolue dans Jeedom, et HA suit sans intervention manuelle lourde. Le plugin gère les cas courants de manière prévisible et explicable, même si certains événements de cycle de vie restent visibles côté HA.

**Exigences révélées :** Stabilité des unique_id basés sur les IDs Jeedom (pas les noms), détection d'ajout/renommage/suppression/changement de type, suppression propre via payload vide retained, mise à jour du nom d'affichage sans casser les références, empreinte de configuration pour détecter les changements, rescan automatique ou manuel, comportement prévisible et compréhensible (pas seulement techniquement correct).

---

### Parcours 7 — Alexandre (Mainteneur) : "Un utilisateur remonte un bug"

**Qui :** Alexandre, mainteneur solo du plugin, 5h/semaine.

**Scène d'ouverture :** Un utilisateur ouvre un ticket : "Mon thermostat Netatmo apparaît bizarrement dans HA, je m'attendais à un climate." Alexandre doit comprendre, diagnostiquer et décider.

**Action :**
1. Il demande à l'utilisateur d'exporter le diagnostic de couverture depuis l'interface du plugin.
2. Le diagnostic montre : l'équipement Netatmo a un type générique `THERMOSTAT_SET_SETPOINT` mais pas de `THERMOSTAT_TEMPERATURE` ni de `THERMOSTAT_SET_MODE`. Le profil est trop incomplet pour être exposé comme `climate` en V1.
3. Alexandre vérifie dans le moteur de mapping : selon les commandes réellement disponibles, l'équipement est soit exposé partiellement (les commandes individuelles publiables le sont sous leur forme la plus proche), soit non exposé sur la partie avancée. C'est le comportement attendu de la politique de mapping conservative.
4. Il répond à l'utilisateur : "Les thermostats complets sont prévus pour la V1.1. En V1, le plugin publie les commandes individuellement exploitables quand elles existent, mais ne force pas un modèle climate incomplet."
5. Il tague le ticket "V1.1 - climate" et le ferme.

**Action — Mise à jour du plugin :**
6. Lors d'une nouvelle version, Alexandre ajoute le support des selects (commandes de type liste).
7. Il vérifie que les unique_id restent stables, que le mapping existant n'est pas cassé, et que les nouvelles entités select apparaissent proprement dans HA sans casser les anciennes.
8. Il publie la mise à jour sur le Market.

**Résolution :** Alexandre traite le ticket en 15 minutes grâce au diagnostic exportable. Le périmètre V1 est défendu clairement. La mise à jour du plugin ne casse rien pour les utilisateurs existants.

**Exigences révélées :** Diagnostic exportable pour le support, logs exploitables à distance, stabilité du mapping entre versions, politique de non-régression, documentation claire du périmètre V1 et des exclusions, gestion des attentes utilisateur.

---

### Synthèse des exigences par parcours

| Parcours | Exigences clés révélées |
|---|---|
| 1 — Happy path | Bootstrap auto, auto-détection MQTT (si présent) + config manuelle fallback, diagnostic P0, mapping types génériques, nommage, contexte spatial, latence ≤ 2s |
| 2 — Edge case / diagnostic | Diagnostic par équipement + raison, suggestions de remédiation, rescan post-correction, dégradation élégante |
| 3 — Test rapide | Détection absence MQTT Manager + guidance, valeur même partielle, faible coût du test, réversibilité |
| 4 — Coexistence choisie | Exclusions, suppression propre, coexistence avec intégrations HA natives, stabilité long terme |
| 5 — Doublons non désirés | Filtres granulaires, namespace strict, nommage distinguable, publication conservative |
| 6 — Évolution maison | Unique_id stables, détection ajout/renommage/suppression/changement type, suppression propre, empreinte de config, comportement prévisible |
| 7 — Mainteneur | Diagnostic exportable, logs distants, stabilité inter-versions, non-régression, documentation périmètre |

**Exigence transversale :** Comportement explicable et prévisible, même en cas de couverture partielle, doublon, changement de mapping ou suppression. Le plugin ne doit jamais surprendre l'utilisateur — il doit toujours pouvoir expliquer ce qu'il fait et pourquoi.

## Exigences Spécifiques au Domaine

### Conformité & Cadre Réglementaire

**Licences et distribution :**
- Le plugin sera distribué sous licence GPL v3 (compatibilité écosystème Jeedom). Le code sous Apache 2.0 (HA) peut être intégré dans un projet GPLv3 ; l'inverse n'est pas compatible dans un projet Apache 2.0.
- Distribution via le Jeedom Market. La publication repose sur un dépôt GitHub avec synchronisation Market↔GitHub (automatique quotidienne ou manuelle selon la fiche plugin).

**Protection des données :**
- Le plugin traite les données exclusivement en local (Jeedom → broker MQTT → HA, tout sur le réseau local). Pas de cloud, pas de transfert externe par défaut.
- Architecture favorable à la minimisation des données et à la maîtrise locale des flux. Cependant, dès que des données personnelles sont concernées (noms d'équipements, habitudes de consommation, présence), le RGPD reste applicable. Le traitement local aide mais ne suffit pas à lui seul à garantir la conformité.
- Le plugin s'inscrit dans l'esprit du EU Data Act (en vigueur depuis le 12 septembre 2025) en facilitant l'exploitation locale et la réutilisation des données d'une installation domotique existante. Ce n'est pas un argument juridique direct mais un alignement de philosophie produit.
- Risque spécifique : fuite involontaire d'informations d'installation via logs, exports de diagnostic ou télémétrie. Tout mécanisme d'export ou de partage doit être conçu avec minimisation des données personnelles.

**Cyber Resilience Act :**
- Le CRA est entré en vigueur le 10 décembre 2024, avec obligations principales applicables à partir du 11 décembre 2027 et obligations de reporting à partir du 11 septembre 2026.
- Le CRA distingue le logiciel libre/open source non monétisé de ce qui est "made available on the market" dans le cadre d'une activité commerciale. Si le plugin est gratuit et non monétisé, l'angle exemption est défendable. S'il est vendu sur le Jeedom Market, il ne peut plus être présenté comme hors champ par nature.
- Dans tous les cas, les bonnes pratiques de sécurité (gestion des vulnérabilités, mises à jour, documentation) restent essentielles.

### Contraintes Techniques du Domaine

**Protocole MQTT — contraintes structurantes :**
- Namespace strict obligatoire pour éviter les collisions avec Z2M, ESPHome, Tasmota, Node-RED et autres clients MQTT sur le même broker.
- Stratégie QoS à définir par type de message (discovery, état, commande, availability).
- Politique de retained messages : discovery et availability en retained, commandes non retained.
- Last Will and Testament pour signaler l'indisponibilité du plugin au broker.
- Republication intelligente sur birth message HA (`homeassistant/status = online`), avec gestion de la charge (délai aléatoire recommandé pour les installations larges).
- Client ID MQTT unique pour éviter les conflits de session avec d'autres clients.

**Sécurité broker :**
- Authentification broker obligatoire ou fortement recommandée.
- Support TLS / validation certificat si broker distant.
- Compatibilité broker à cadrer clairement : HA avertit explicitement que certains brokers ou plugins MQTT ne gèrent pas correctement la rétention des messages, ce qui peut casser la discovery.

**MQTT Discovery HA — contraintes du standard :**
- Respect strict du format MQTT Discovery de Home Assistant (topics, payloads, device, origin).
- Les `unique_id` doivent être stables et basés sur les IDs Jeedom (pas les noms) pour survivre aux renommages.
- Les `device_class`, `unit_of_measurement` et `state_class` doivent être conformes aux conventions HA pour un affichage natif correct (graphes, badges, Energy dashboard).
- Support du mécanisme de suppression (payload vide retained sur le topic de config).

**Écosystème Jeedom — contraintes de plateforme :**
- Compatibilité avec les box à ressources limitées (Raspberry Pi, Luna, Atlas) : consommation CPU/RAM/IO maîtrisée.
- Bootstrap progressif pour ne pas saturer une box lors du premier scan complet.
- Republication massive de discovery après redémarrage HA/broker = pic d'I/O et délai de convergence. Prévoir un mécanisme de lissage.
- Dépendance à MQTT Manager comme chemin privilégié (mais pas exclusif) pour la connectivité broker.
- Respect de l'API JSON-RPC Jeedom pour la lecture de l'inventaire et l'exécution des commandes.
- Utilisation de `event::changes` pour la synchronisation incrémentale des états.

**Compatibilité croisée :**
- Matrice de compatibilité minimale supportée à maintenir : versions Jeedom / plugin jeedom2ha / MQTT Manager / Home Assistant.
- C'est un des sujets qui use le plus un mainteneur solo — chaque nouvelle release de HA ou Jeedom peut potentiellement casser le comportement.

**Types génériques Jeedom — contraintes de mapping :**
- Les types génériques sont le moteur principal du mapping, mais leur couverture est hétérogène selon les plugins et les installations.
- Le fallback type/sous-type est un deuxième moteur de mapping, pas un simple secours.
- Le mapping doit porter une métadonnée de confiance (sûr / probable / ambigu) pour piloter la politique d'exposition conservative.

### Patterns et Anti-Patterns du Domaine

**Patterns à suivre :**
- Publication conservative : ne pas publier plutôt que publier faux.
- Dégradation élégante : une couverture partielle mais correcte vaut mieux qu'une couverture large mais bruitée.
- Identifiants stables : les IDs techniques (unique_id) doivent résister aux renommages, déplacements et reconfigurations.
- Séparation claire des 4 cas de cycle de vie : suppression réelle, indisponibilité temporaire, désactivation volontaire, remapping.

**Anti-patterns à éviter :**
- Le plugin trop intelligent : compensation des limites Jeedom par de l'inférence opaque → imprévisible et impossible à debugger.
- La dette d'exceptions : empilement de règles spéciales par plugin source → moteur de mapping impossible à raisonner.
- Le mode optimiste dogmatique : refuser l'optimiste par principe → expérience HA dégradée par rapport aux intégrations natives.
- Le bootstrap qui tue la box : scan complet non progressif → saturation CPU/RAM sur box limitées.

### Risques Domaine et Mitigations

| Risque | Impact | Mitigation |
|---|---|---|
| Types génériques incomplets sur l'installation cible | Couverture faible, déception utilisateur | Diagnostic P0 avec remédiation, fallback type/sous-type |
| Collision MQTT avec autres clients sur le même broker | Perturbation d'autres systèmes, commandes non sollicitées | Namespace strict, préfixe dédié, client ID unique |
| Broker MQTT non conforme aux retained messages | Discovery cassée, entités fantômes | Documentation des brokers supportés, vérification au démarrage |
| Changement de comportement MQTT Discovery entre versions HA | Entités qui disparaissent ou se comportent différemment | Matrice de compatibilité, suivi des releases HA, tests |
| Republication massive post-redémarrage | Pic I/O, saturation box, délai de convergence | Lissage temporel, délai aléatoire, republication progressive |
| Boucle de commande infinie (automation HA → Jeedom → état → automation) | Saturation broker, emballement démon | Mécanisme anti-boucle / debounce |
| Démon en état incohérent silencieux | Plus de publications, cache périmé, pas d'alerte | Heartbeat métier, healthcheck, self-healing |
| Fuite d'informations via logs/diagnostic/télémétrie | Exposition de données personnelles d'installation | Minimisation des données dans les exports, pas de télémétrie sans consentement |
| Compatibilité croisée Jeedom/HA/MQTT Manager | Casse silencieuse après mise à jour | Matrice de compatibilité maintenue, tests multi-versions |
| Perception communautaire négative | Rejet, mauvaise réputation | Positionnement "pont d'interopérabilité", documentation honnête |
| Épuisement du mainteneur par dette de support | Abandon du projet | Périmètre V1 strict, diagnostic clair, FAQ, documentation |

## Exigences Spécifiques au Type de Projet

### Vue d'ensemble — Middleware d'interopérabilité domotique

jeedom2ha est un plugin Jeedom avec démon Python qui agit comme couche d'interopérabilité entre deux écosystèmes domotiques via MQTT. Ce n'est ni un firmware embarqué, ni une API cloud, ni une application mobile : c'est un bridge local, événementiel, qui projette un modèle de données existant (Jeedom) vers un standard de discovery (HA MQTT Discovery).

Les exigences techniques spécifiques découlent de cette nature : architecture plugin Jeedom avec démon Python asynchrone, communication PHP↔Python, publication MQTT conforme au standard HA, et contraintes de déploiement local sur matériel hétérogène.

### Architecture Technique — Démon Python

**Pattern architectural :**
- Démon Python 3 asynchrone, géré par le moteur de démon Jeedom (start/stop/heartbeat).
- Basé sur la bibliothèque `jeedomdaemon` (package PyPI), qui fournit le pattern `BaseDaemon` avec hooks `on_start` / `on_message` / `on_stop`.
- Le démon est le composant actif : il maintient le cache d'état, gère la connexion MQTT, publie les messages discovery et traite les commandes retour HA → Jeedom.

**Communication PHP ↔ Python :**
- Le plugin PHP pilote le démon Python via le pattern standard Jeedom ; le détail du transport interne sera fixé dans le design technique.

**Contraintes de stabilité :**
- Le démon doit tourner en continu sans intervention manuelle en régime nominal.
- Reconnexion automatique au broker MQTT après coupure temporaire.
- Heartbeat métier pour détecter un état incohérent silencieux.
- Gestion propre du Last Will and Testament MQTT pour signaler l'indisponibilité.

### Modèle de Configuration

**3 niveaux de configuration standard Jeedom :**

1. **Configuration plugin** (globale) : connexion broker MQTT (auto-détection MQTT Manager si présent, saisie manuelle en fallback), paramètres globaux de publication, niveau de log, options avancées.
2. **Configuration équipement** (par eqLogic) : inclusion/exclusion de la publication, surcharges de nommage, filtres.
3. **Configuration commande** (par cmd) : pas de configuration manuelle prévue en V1 — le mapping repose sur les types génériques Jeedom.

**Principe :** Pas de base de données custom, pas de modèle de données propriétaire. Le plugin s'appuie sur les structures natives Jeedom (eqLogic, cmd, types génériques) et publie vers MQTT Discovery.

### Baseline de Compatibilité

| Composant | Version minimale supportée |
|---|---|
| **Jeedom** | 4.4.9+ |
| **Debian** | 12 (Bookworm) |
| **Python** | 3.9+ |
| **Home Assistant** | À cadrer au démarrage du dev (version supportant MQTT device discovery avec unique_id, device et origin) |
| **MQTT** | Broker compatible retained messages (Mosquitto recommandé) |

### Stratégie de Mise à Jour et Migration

**Gestion des versions :**
- Versionnement sémantique (semver) pour le plugin.
- Stabilité des `unique_id` entre versions : un upgrade ne doit jamais casser les entités existantes dans HA.
- Empreinte de configuration versionnée pour détecter les changements de mapping entre versions.

**Stratégie hybride :**
- **Partie PHP (plugin)** : mise à jour classique via le Market Jeedom (remplacement de fichiers, migration DB si nécessaire via `install.php`).
- **Partie Python (démon)** : les dépendances sont déclarées dans `plugin_info/packages.json` et gérées par le système de dépendances Jeedom. Le démon est redémarré automatiquement après mise à jour.

**Non-régression :**
- Le mapping existant ne doit pas être cassé par une mise à jour du plugin.
- Les nouvelles entités peuvent apparaître (support de nouveaux types), mais les anciennes ne doivent pas changer de comportement sans raison explicite.

### Modèle de Déploiement — Local-First

**Cible de déploiement :**
- Plugin installé localement sur la box Jeedom (Raspberry Pi, Luna, Atlas, VM, Docker).
- Aucun composant cloud, aucune dépendance externe en fonctionnement normal.
- Le cas nominal recommandé est un broker local ou sur le même réseau local ; les brokers distants restent supportés hors chemin nominal.

**Gestion des dépendances :**
- Dépendances système (bibliothèques C, outils) : installées via `apt` et déclarées dans `plugin_info/packages.json`.
- Dépendances Python (`jeedomdaemon`, `paho-mqtt`, etc.) : installées via `pip3` dans le venv géré par Jeedom.
- Depuis Jeedom 4.4.9+, les dépendances Python sont gérées dans un environnement virtuel (venv). Le plugin doit utiliser `system::getCmdPython3(__CLASS__)` pour obtenir le chemin Python correct du venv, et non un appel direct à `python3`.

**Contraintes matérielles :**
- Consommation CPU/RAM/IO maîtrisée pour fonctionner sur box à ressources limitées.
- Bootstrap progressif pour ne pas saturer la box lors du premier scan.
- Republication post-redémarrage avec lissage temporel.

### Considérations d'Implémentation

**Structure plugin Jeedom :**
- Héritage de classes `eqLogic` et `cmd` pour la partie PHP.
- Fichiers de configuration plugin (`plugin_info/info.json`, `plugin_info/packages.json`, `plugin_info/install.php`).
- Interface de gestion dans `desktop/php/` et `desktop/js/`.
- Démon Python dans `resources/`.
- Données runtime dans `data/` (cache, empreintes, état technique) ; règles de mapping maintenues dans le code du plugin.

**Dépendances clés :**
- `jeedomdaemon` (PyPI) : framework de démon Python pour Jeedom.
- `paho-mqtt` : client MQTT Python.
- Pas de dépendance à des services externes ou à des API cloud.

## Scoping & Développement Phasé

### Philosophie MVP

**Approche : MVP problem-solving.**

Le MVP existe pour résoudre un problème précis : permettre à un utilisateur Jeedom avancé de retrouver ses usages essentiels du quotidien dans Home Assistant, sans migration ni reconstruction manuelle.

**Règle de scoping :**
> Tout ce qui est nécessaire pour créer de la valeur lors de la première semaine est MVP. Tout ce qui est nécessaire pour rendre la coexistence durable sur plusieurs mois est Growth — sauf le strict minimum pour éviter une mauvaise première impression.

**Minimum vital réel :**
Bootstrap automatique + mapping conservative des usages essentiels + round-trip simple + diagnostic P0 + rescan manuel + exclusion minimale du périmètre publié.

**Ressource :** mainteneur solo, ~5h/semaine. Toute feature qui augmente significativement les cas limites, les tickets ou les comportements implicites est suspecte par défaut.

### Parcours Utilisateurs — Couverture par Phase

| Parcours | Phase | Niveau |
|---|---|---|
| 1 — Happy path | MVP | Strict |
| 2 — Diagnostic edge case | MVP | Strict |
| 3 — Test rapide | MVP | Strict |
| 7 — Mainteneur | MVP | Strict (version minimale : diagnostic exportable, logs lisibles, périmètre explicite, comportement explicable) |
| 5 — Doublons | MVP | Partiel (namespace clair, nommage distinguable, exclusions simples, republication propre après exclusion — pas de détection automatique ni rapprochement sémantique) |
| 6 — Évolution maison | MVP | Partiel (ajout, renommage, suppression via rescan manuel — pas de changement de type avancé ni réconciliation automatique) |
| 4 — Coexistence choisie | Growth | Complet (la brique minimale d'exclusion est en MVP ; le parcours complet de transition progressive durable est Growth) |

### MVP — Feature Set (Phase 1)

**Capacités cœur :**
- Bootstrap automatique : lecture inventaire Jeedom, mapping via types génériques, publication MQTT Discovery
- Mapping conservative des usages essentiels : lumières (on/off, dimmer si disponible et correctement mappé), prises/switches, volets/covers (open/close/stop, position si disponible et correctement mappée), capteurs numériques simples (température, humidité, puissance, énergie, batterie), capteurs binaires simples (ouverture, mouvement/présence, fuite, fumée)
- Round-trip simple HA → Jeedom avec retour d'état cohérent sur le périmètre supporté
- Contexte spatial minimal : objet Jeedom → nom d'affichage / area HA (heuristique)
- Diagnostic de couverture intégré (P0) : par équipement, publié / partiellement publié / non publié + raison principale
- Rescan / republication manuelle
- Exclusion minimale du périmètre publié : au moins par équipement, et idéalement par famille en MVP si le coût d'implémentation reste faible
- Politique d'exposition conservative : en cas d'ambiguïté, ne pas publier plutôt que publier faux

**Cycle de vie MVP :**
- Ajout d'équipement détecté au rescan
- Renommage : mise à jour du nom d'affichage sans casser le unique_id
- Suppression : payload vide retained sur le topic de config, avec effet techniquement propre mais potentiellement visible côté usages HA (dashboards / automatisations à ajuster)

**Support mainteneur MVP :**
- Diagnostic exportable pour le support à distance
- Logs exploitables sans expertise MQTT
- Périmètre V1 documenté et défendu clairement
- Comportement explicable et prévisible

**Prérequis :**
- Broker MQTT existant (MQTT Manager ou broker externe)
- Home Assistant avec intégration MQTT activée

**Non-objectif MVP :** représenter exhaustivement la maison Jeedom dans HA ou reproduire parfaitement toute la sémantique Jeedom. L'objectif est de publier rapidement et proprement les usages essentiels du quotidien, pas de viser une couverture totale.

### Post-MVP — Phase 2 (Growth)

**Cycle de vie avancé :**
- Changement de type proprement géré (retrait ancienne représentation, publication nouvelle)
- Réconciliation hybride avancée (event::changes + rescan périodique)

**Couverture étendue :**
- Thermostats / climate (mapping complexe : mesure vs consigne, modes, états composites)
- Scénarios Jeedom exposés proprement (boutons d'action, enable/disable, état)
- Selects et commandes de type liste
- Support élargi des plugins Jeedom atypiques
- Heuristiques de mapping améliorées

**Coexistence avancée :**
- Parcours complet de transition progressive (remplacement progressif par intégrations natives HA)
- Gestion sophistiquée des doublons (détection, rapprochement)

### Post-MVP — Phase 3 (Vision)

- Outil hybride durable : Jeedom = backend robuste, HA = frontend moderne
- Couche de coexistence de référence entre Jeedom et Home Assistant
- Couverture étendue (alarmes simplifiées, multimédia basique)
- Qualité de mapping maximisée pour les capacités IA/voix de HA (Assist, LLM)
- Gestion ultra-propre du cycle de vie (zéro fantôme, zéro doublon en usage normal)

### Risques de Scoping

| Risque | Impact | Mitigation |
|---|---|---|
| **Moteur de mapping** — trop permissif il pollue HA, trop conservateur il déçoit | Risque produit principal : qualité de la première impression et confiance utilisateur | Politique conservative avec diagnostic clair, fallback type/sous-type comme deuxième moteur, métadonnée de confiance |
| **Cycle de vie** — beaucoup de plugins font une belle première synchro, très peu restent propres quand la maison change | Entités fantômes, doublons, perte de confiance dans la durée | Cycle de vie basique en MVP (ajout/renommage/suppression), avancé en Growth |
| **Soutenabilité mainteneur** — 5h/sem contraint fortement l'ambition | Feature creep, dette de support, burnout | Périmètre MVP strict, diagnostic P0 pour réduire les tickets, chaque feature suspecte si elle augmente les cas limites |

## Exigences Fonctionnelles

### Discovery & Publication

- **FR1 :** L'utilisateur peut lancer un bootstrap automatique qui lit l'inventaire Jeedom et publie les équipements exploitables dans Home Assistant via MQTT Discovery.
- **FR2 :** Le système peut mapper automatiquement les commandes Jeedom vers des entités HA en utilisant les types génériques Jeedom comme moteur principal de mapping.
- **FR3 :** Le système peut utiliser le type/sous-type Jeedom comme deuxième moteur de mapping lorsque le type générique est absent ou insuffisant.
- **FR4 :** Le système peut associer une métadonnée de confiance (sûr / probable / ambigu) à chaque mapping pour piloter la politique d'exposition.
- **FR5 :** Le système applique une politique d'exposition conservative : en cas d'ambiguïté de mapping, l'équipement n'est pas publié plutôt que publié avec un mapping potentiellement faux.
- **FR6 :** L'utilisateur peut forcer un rescan / republication manuelle à tout moment pour voir l'effet de ses corrections de typage ou d'ajustements d'installation.
- **FR7 :** Le système peut générer des noms d'affichage construits à partir du contexte Jeedom (nom d'objet parent et nom d'équipement), permettant à l'utilisateur de reconnaître ses équipements dans HA sans ambiguïté.
- **FR8 :** Le système peut associer un contexte spatial utilisable par HA (suggested_area dans la discovery MQTT) lorsque l'objet parent Jeedom est défini.
- **FR9 :** Le système peut republier automatiquement les configurations nécessaires après un redémarrage de HA ou du broker MQTT.

### Équipements Supportés (MVP)

- **FR10 :** Le système peut publier des lumières (on/off, dimmer si disponible et correctement mappé) comme entités HA pilotables.
- **FR11 :** Le système peut publier des prises / switches comme entités HA pilotables.
- **FR12 :** Le système peut publier des volets / covers (open/close/stop, position si disponible et correctement mappée) comme entités HA pilotables.
- **FR13 :** Le système peut publier des capteurs numériques simples (température, humidité, puissance, énergie, batterie) comme entités HA avec métadonnées conformes aux conventions HA lorsque ces métadonnées sont disponibles et pertinentes.
- **FR14 :** Le système peut publier des capteurs binaires simples (ouverture, mouvement/présence, fuite, fumée) comme entités HA avec métadonnées conformes lorsque ces métadonnées sont disponibles et pertinentes.

### Commande & Retour d'État

- **FR15 :** L'utilisateur HA peut piloter les actionneurs publiés (lumières, prises, volets) depuis Home Assistant avec exécution effective dans Jeedom.
- **FR16 :** Le système peut mettre à jour dans HA l'état des équipements pilotés pour refléter l'état Jeedom lorsque cet état est disponible sur le périmètre supporté.
- **FR17 :** Le système peut synchroniser les changements d'état Jeedom vers HA de manière incrémentale (sans rescan complet) en régime nominal.

### Périmètre & Exclusions

- **FR18 :** L'utilisateur peut exclure un équipement spécifique de la publication.
- **FR19 :** Le système peut republier proprement après modification des exclusions (les entités exclues disparaissent de HA, les entités restantes sont inchangées).

### Cycle de Vie des Entités

- **FR20 :** Le système peut détecter l'ajout d'un nouvel équipement dans Jeedom et le publier dans HA au prochain rescan.
- **FR21 :** Le système peut détecter le renommage d'un équipement dans Jeedom et mettre à jour le nom d'affichage dans HA sans changer le unique_id.
- **FR22 :** Le système peut retirer proprement de HA les entités correspondant à des équipements supprimés dans Jeedom.
- **FR23 :** Le système utilise des unique_id stables basés sur les IDs Jeedom (pas les noms) pour que les entités HA survivent aux renommages et déplacements.
- **FR24 :** Le système peut signaler l'indisponibilité du bridge afin que HA reflète correctement l'état global de la publication.
- **FR25 :** Le système peut exposer un état de disponibilité par entité permettant à HA de distinguer un équipement indisponible d'un équipement supprimé.

### Diagnostic & Observabilité

- **FR26 :** L'utilisateur peut consulter un diagnostic de couverture intégré dans l'interface Jeedom montrant, pour chaque équipement : publié / partiellement publié / non publié + raison principale.
- **FR27 :** Le diagnostic peut suggérer des actions de remédiation à l'utilisateur (ex : "configurez le type générique dans Jeedom").
- **FR28 :** L'utilisateur peut exporter le diagnostic de couverture pour le transmettre au support.
- **FR29 :** Le système produit des logs incluant l'identifiant équipement, le résultat de mapping et la raison d'échec le cas échéant, lisibles sans expertise MQTT et utilisables pour le support à distance.
- **FR30 :** Le système documente explicitement le périmètre V1 supporté et les raisons de non-publication dans le diagnostic.

### Configuration & Connexion

- **FR31 :** Le système peut auto-détecter la configuration du broker MQTT via MQTT Manager si celui-ci est présent.
- **FR32 :** L'utilisateur peut configurer manuellement les paramètres de connexion au broker MQTT en l'absence de MQTT Manager.
- **FR33 :** Le système peut détecter l'absence de broker MQTT et guider l'utilisateur clairement vers la configuration nécessaire.
- **FR34 :** L'utilisateur peut configurer les paramètres globaux du plugin (niveau de log, options de publication).
- **FR35 :** Le système supporte l'authentification au broker MQTT.

### Republication & Maintenance

- **FR36 :** L'utilisateur peut déclencher une republication complète propre de la configuration publiée vers HA.

## Exigences Non-Fonctionnelles

### Performance

- **NFR1 :** Pour les commandes simples du périmètre V1, en contexte nominal (réseau local, broker disponible, équipement avec retour d'état compatible), la latence perçue HA → Jeedom → retour d'état doit être ≤ 2s, avec une cible idéale autour de 1s. Une latence ≥ 5s est considérée comme non acceptable.
- **NFR2 :** Le bootstrap initial ne doit pas rendre l'interface Jeedom inutilisable : le temps de réponse de l'interface Jeedom ne doit pas dépasser 10s pendant le bootstrap, et aucune saturation durable des ressources de la box ne doit survenir.
- **NFR3 :** Après redémarrage HA/broker, la republication doit être lissée sur au moins 5s pour les installations de plus de 50 entités, afin d'éviter un pic de charge susceptible de dégrader Jeedom ou le broker.

### Fiabilité

- **NFR4 :** Le démon doit rester opérationnel en régime nominal sans intervention manuelle.
- **NFR5 :** Le démon ne doit pas présenter de dégradation progressive de mémoire ou de stabilité sur une exécution prolongée : la consommation mémoire ne doit pas augmenter de plus de 20% après 72h d'exécution continue par rapport à la valeur stabilisée après démarrage.
- **NFR6 :** Le démon doit se reconnecter automatiquement au broker MQTT en moins de 30s après rétablissement de la connectivité, sans intervention utilisateur.
- **NFR7 :** Pas d'accumulation durable d'entités fantômes dans HA lors d'un usage normal (ajout, renommage, suppression, rescan).
- **NFR8 :** Les transitions d'état du cycle de vie doivent être déterministes, documentées et explicables.
- **NFR9 :** Une mise à jour du plugin ne doit pas provoquer de rupture non documentée du parc d'entités existant.
- **NFR10 :** Après redémarrage de Home Assistant, les entités découvertes doivent redevenir disponibles sans intervention manuelle de l'utilisateur.

### Sécurité

- **NFR11 :** Le plugin doit supporter l'authentification au broker MQTT (utilisateur/mot de passe). Support TLS si broker distant.
- **NFR12 :** Aucune donnée d'installation ne doit être transmise vers l'extérieur du réseau local sans action explicite de l'utilisateur.
- **NFR13 :** Les mécanismes d'export (diagnostic, logs) doivent minimiser les données personnelles incluses. Pas de télémétrie sans consentement explicite ; toute télémétrie éventuelle est désactivée par défaut.
- **NFR14 :** Les identifiants de connexion broker ne doivent pas apparaître en clair dans les logs.

### Intégration

- **NFR15 :** Les messages MQTT Discovery publiés doivent être compatibles avec les exigences documentées par Home Assistant pour unique_id, device, origin, availability, retained config et métadonnées d'entité pertinentes.
- **NFR16 :** Le namespace MQTT du plugin ne doit pas entrer en collision avec les autres clients MQTT courants (Zigbee2MQTT, ESPHome, Tasmota, Node-RED).
- **NFR17 :** Le plugin doit être compatible avec les versions Jeedom 4.4.9+, Debian 12, Python 3.9+. La matrice de compatibilité HA sera cadrée au démarrage du développement.
- **NFR18 :** La politique de retained messages doit être conforme aux attentes HA : discovery et availability en retained, commandes non retained.

### Consommation de Ressources

- **NFR19 :** La consommation CPU/RAM du démon en régime nominal doit rester compatible avec les box à ressources limitées : cible < 5% CPU et < 100 Mo RAM sur Raspberry Pi 4 pour une installation de référence (~80 équipements).
- **NFR20 :** La charge I/O générée par le plugin ne doit pas augmenter la latence des autres plugins Jeedom de plus de 500ms en régime nominal.
- **NFR21 :** Le bootstrap initial doit étaler la publication sur au moins 10s pour les installations de plus de 50 équipements, afin de ne pas saturer les box à ressources limitées lors du premier scan complet.

### Observabilité

- **NFR22 :** En cas d'échec de publication, de reconnexion ou de mapping, le plugin doit produire une information exploitable permettant d'identifier la cause sans analyse MQTT bas niveau.
