---
stepsCompleted: [1, 2, 3, 4]
inputDocuments: ['docs/cadrage_plugin_jeedom_ha_bmad.md']
session_topic: 'Challenge du document de cadrage plugin Jeedom -> Home Assistant'
session_goals: 'Identifier les angles morts et hypothèses non vérifiées'
selected_approach: 'ai-recommended'
techniques_used: ['assumption-reversal', 'question-storming', 'reverse-brainstorming']
ideas_generated: [10 hypothèses, 280 questions, 24 scénarios échec]
context_file: 'docs/cadrage_plugin_jeedom_ha_bmad.md'
session_active: false
workflow_completed: true
---

# Brainstorming Session - Challenge du document de cadrage

**Facilitateur :** Alexandre
**Date :** 2026-03-12
**Document analysé :** `docs/cadrage_plugin_jeedom_ha_bmad.md`

## Session Overview

**Sujet :** Challenge du document de cadrage - Plugin Jeedom de publication automatique vers Home Assistant
**Objectif :** Identifier les angles morts, hypothèses non vérifiées et risques sous-estimés
**Approche :** AI-Recommended (Assumption Reversal → Question Storming → Reverse Brainstorming)

---

## Phase 1 : Assumption Reversal - 10 hypothèses challengées

### Hypothèse #1 : Types génériques = couverture suffisante
**Sévérité : HAUTE**

Le document traite les types génériques comme fondation principale du mapping. En réalité, la couverture est très hétérogène selon les installations.

**Constat :**
- Les plugins officiels (Z-Wave, Zigbee) peuplent généralement bien les types génériques ; les plugins tiers ou exotiques beaucoup moins.
- Aucune statistique publique fiable sur le taux d'installations correctement typées.
- Les plugins Homebridge, Google SmartHome et Alexa rappellent eux-mêmes que le bon fonctionnement dépend d'une configuration correcte des types génériques.
- Un utilisateur utilisant déjà Homebridge/Apple Maison est probablement au-dessus de la moyenne sur ce sujet.

**Verdict :** Les types génériques sont un accélérateur, pas une vérité universelle. Le fallback type/sous-type est un deuxième moteur de mapping, pas un simple secours.

**Recommandation :** Le document doit traiter le fallback type/sous-type comme un chemin critique au même niveau que le mapping par types génériques. Prévoir détection secondaire, diagnostic de couverture et overrides manuels.

---

### Hypothèse #2 : 1 eqLogic Jeedom = 1 device Home Assistant
**Sévérité : MOYENNE**

Le document pose cette règle sans mentionner d'exception. Trois cas problématiques identifiés.

**Cas problématiques :**
- **Multi-endpoints :** Un module Z-Wave avec 2 relais indépendants = 1 eqLogic Jeedom mais logiquement 2 sous-devices HA. La doc HA prévoit `via_device` pour ce cas.
- **Virtuels agrégés :** Un virtuel Jeedom mélangeant plusieurs sources n'est pas un "device physique" au sens HA.
- **Scénarios :** Un scénario Jeedom n'est pas un "device" au sens fort. 30 scénarios = 30 devices dans HA, ce qui pollue la vue. Un device logique unique "Jeedom Scénarios" regroupant les entités button/switch serait plus propre.

**Verdict :** Bonne heuristique V1 par défaut, mais pas une règle universelle.

**Recommandation :** Présenter comme heuristique par défaut avec exceptions documentées : possibilité de splitter les multi-endpoints, regroupement des scénarios dans un device logique, traitement spécifique des virtuels.

---

### Hypothèse #3 : MQTT Manager = prérequis transparent
**Sévérité : MOYENNE**

Le document impose MQTT Manager comme prérequis V1 sans évaluer la friction d'adoption.

**Constat :**
- MQTT Manager est techniquement solide : supporte broker local, Docker et distant ; utilisé par Z-Wave JS, Velux MQTT et d'autres plugins officiels.
- Mais sa pénétration réelle chez les utilisateurs Jeedom est inconnue.
- Les utilisateurs "classiques" n'ont probablement pas MQTT Manager installé.
- **Tension directe** avec la promesse "plugin simple, sans configuration lourde" (section 3 du document).

**Verdict :** Choix technique pertinent mais friction d'adoption sous-estimée.

**Recommandation :** Assumer la dépendance comme décision d'architecture, mais prévoir : auto-détection de MQTT Manager, lecture automatique de la config broker, guide d'installation intégré, diagnostic clair si MQTT Manager n'est pas prêt. À moyen terme, abstraire le transport MQTT pour ne pas créer une dépendance structurelle indépassable.

---

### Hypothèse #4 : État réel toujours disponible
**Sévérité : HAUTE**

Le document rejette le mode optimiste quasi par principe ("préférer l'état réel ; éviter le mode optimiste") alors que HA le prévoit nativement.

**Quatre niveaux de confiance identifiés :**
1. **État confirmé quasi instantané :** cas idéal, l'équipement remonte un vrai état rapidement.
2. **État réel mais retardé :** polling ou rafraîchissement différé, latence variable.
3. **Aucun état fiable :** commande envoyée sans possibilité de vérifier le résultat.
4. **Commande sans état par nature :** bouton, impulsion, run scénario, "play" - chercher un état réel n'a pas de sens.

**Verdict :** Préférer l'état réel est une bonne philosophie, mais refuser le mode optimiste est contre-productif. Le mode optimiste est un mode natif légitime dans HA.

**Recommandation :** Le mapping doit porter une métadonnée "niveau de confiance état" par entité. Le moteur de mapping doit supporter les 4 niveaux. Ce n'est pas un risque à "mitiger" mais une décision d'architecture.

---

### Hypothèse #5 : "Corriger ses types génériques" = charge légère
**Sévérité : HAUTE**

Le document présente la configuration des types génériques comme un effort mineur. En réalité, c'est une charge significative pour beaucoup d'utilisateurs.

**Constat :**
- Les types génériques sont une notion interne à Jeedom, pas évidente pour un utilisateur non technique.
- Jeedom fournit des outils (page dédiée, fonction "Types Auto"), mais l'ergonomie reste orientée "configuration domotique".
- Sur une installation riche (50+ équipements, 5-10 commandes chacun), le volume de vérification est conséquent.
- La communauté montre que certains types manquent, certains comportements ont changé, et les virtuels ou modes par liste peuvent être moins évidents à typer.

**Verdict :** Le plugin ne supprime pas la complexité mais en déplace une partie vers Jeedom.

**Recommandation :** Le diagnostic de couverture n'est pas un "nice to have" P1 - c'est un pré-requis fonctionnel P0. Le plugin doit fournir : diagnostic de couverture, vue "bien publié / mal publié / non publié", recommandations ciblées (pas juste "corrigez vos types génériques").

---

### Hypothèse #6 : Transport MQTT fiable implicitement
**Sévérité : HAUTE**

Le document repose entièrement sur MQTT sans formaliser aucune stratégie opérationnelle.

**Lacunes identifiées :**
- Aucune stratégie QoS définie (QoS 0/1/2 selon type de message).
- Aucune politique de retained messages (discovery, availability, états, commandes).
- Pas de gestion de reconnexion du plugin au broker.
- Pas de last will pour signaler l'indisponibilité du plugin.
- Pas de seuil de latence mesurable (P50/P95).
- Pas de gestion du volume continu sur installations larges avec capteurs bavards.

**Stratégie MQTT recommandée pour V1 :**
- Discovery : retained ou republish piloté par birth message.
- Availability : retained + last will.
- États : retained pour les états stables.
- Commandes : non retained.
- QoS : à définir explicitement par type de message.

**Verdict :** MQTT est un bon choix mais seulement si traité comme brique critique avec stratégie explicite.

**Recommandation :** Créer un ADR dédié à la stratégie MQTT couvrant QoS, retained, reconnexion, last will, republication post-coupure, namespace strict et seuils de latence.

---

### Hypothèse #7 : Rescan périodique suffit pour la cohérence
**Sévérité : HAUTE**

Le document présente le rescan périodique comme mécanisme principal de réconciliation. Jeedom fournit pourtant `event::changes` pour le suivi incrémental.

**Constat :**
- `event::changes` retourne les changements depuis un datetime donné (incrémental).
- `jeeObject::full` retourne l'inventaire complet (snapshot).
- Le rescan seul crée une fenêtre d'incohérence entre deux passages.
- Entre deux rescans : entités fantômes, commandes invalides, renommages non reflétés.
- L'empreinte de config n'est pas définie dans le document.

**Verdict :** Le rescan est utile comme filet de sécurité, pas comme mécanisme principal.

**Recommandation :** Architecture hybride : événementiel/incrémental (`event::changes`) quand possible + rescan périodique comme garde-fou + rescan manuel en fallback. Définir précisément l'empreinte de configuration. Remonter la réconciliation (L7-P1) en priorité plus haute. Prévoir un comportement sûr si une entité HA pointe vers une cible Jeedom devenue invalide.

---

### Hypothèse #8 : Planning 80h à 5h/semaine réaliste
**Sévérité : FAIBLE**

**Verdict :** L'estimation est un repère d'ordre de grandeur, pas une contrainte. Le développement sera assisté par agents BMAD, ce qui rend les estimations classiques peu pertinentes. Pas d'angle mort - juste une hypothèse à ne pas sur-interpréter.

---

### Hypothèse #9 : Objets Jeedom = areas Home Assistant
**Sévérité : MOYENNE**

Le document assimile directement les objets Jeedom aux areas HA. Incompatibilité structurelle.

**Problèmes :**
- Objets Jeedom = hiérarchie arborescente. Areas HA = liste plate.
- Pas tous les objets Jeedom sont des pièces physiques (certains sont fonctionnels : "Chauffage", "Sécurité").
- Équipements orphelins (sans objet parent) : quelle area ?
- HA distingue nom de device, nom d'entité et area - le document mélange ces concepts.
- HA prévoit les floors pour les étages, permettant une projection plus fine.

**Verdict :** Les objets Jeedom sont une bonne source de contexte, pas un équivalent direct des areas HA.

**Recommandation :** Définir une stratégie de projection explicite : objet feuille → area, objet parent → floor quand pertinent. Convention pour les objets fonctionnels. Convention pour les orphelins. Séparation claire : nom device / nom entité / area.

---

### Hypothèse #10 : Suppression propre = triviale
**Sévérité : HAUTE**

Le document mentionne la "suppression propre" comme critère d'acceptation sans en détailler la complexité réelle.

**Quatre cas de cycle de vie à distinguer :**
1. **Suppression réelle :** l'objet n'existe plus dans Jeedom → suppression MQTT Discovery (payload vide retained).
2. **Indisponibilité temporaire :** plugin arrêté, équipement injoignable → publication `unavailable`, pas suppression.
3. **Désactivation volontaire :** équipement désactivé dans Jeedom → `unavailable` plutôt que suppression.
4. **Renommage/remapping :** l'objet existe toujours mais a changé → mise à jour sans casser les références HA.

**Risques supplémentaires :**
- Les retained mal nettoyés créent des ghost entities au redémarrage.
- La suppression impacte les automations, dashboards et personnalisations HA de l'utilisateur.
- Un device HA peut rester orphelin si on supprime sa dernière entité sans traitement explicite.

**Verdict :** La suppression est faisable techniquement mais nécessite une vraie politique de cycle de vie.

**Recommandation :** Implémenter une politique de cycle de vie complète couvrant les 4 cas. Privilégier `unavailable` plutôt que suppression en cas de doute. Prévoir le nettoyage des retained et des devices orphelins.

---

## Phase 2 : Question Storming - 280 questions

### Parcours utilisateur et onboarding (~25 questions)

1. Qui est l'utilisateur cible exact ? Power user Jeedom ? Débutant HA ? Utilisateur HA confirmé ?
2. L'utilisateur cible est-il unique, ou y a-t-il plusieurs personas avec des attentes contradictoires ?
3. Le plugin doit-il viser d'abord "je veux voir ma maison dans HA" ou "je veux piloter naturellement via HA" ?
4. Quel est le "time to first value" acceptable après installation ?
5. Quel est le plus petit résultat visible qui doit convaincre l'utilisateur ?
6. Que se passe-t-il au tout premier lancement du plugin ?
7. Comment l'utilisateur sait-il que "ça marche" ?
8. Le plugin doit-il proposer un mode découverte guidée au premier lancement ?
9. Que fait l'utilisateur quand un équipement n'apparaît pas dans HA ?
10. Comment l'utilisateur comprend-il pourquoi un équipement a été publié comme switch et non comme light ?
11. Comment l'utilisateur comprend-il pourquoi un équipement n'est pas publié du tout ?
12. L'utilisateur doit-il avoir des compétences MQTT pour débugger ?
13. Que se passe-t-il si l'utilisateur installe le plugin mais n'a aucun type générique configuré ?
14. Comment l'utilisateur désinstalle-t-il proprement le plugin ?
15. Quel est le parcours exact quand tout se passe bien ?
16. Quel est le parcours exact quand rien n'apparaît dans HA ?
17. Quel est le parcours exact quand certaines entités apparaissent mais sont inutilisables ?
18. Quel niveau de vocabulaire technique peut-on imposer sans perdre l'utilisateur ?
19. Quelle différence d'expérience entre utilisateur novice et avancé ?
20. Le plugin doit-il être utile même si l'utilisateur n'a jamais ouvert HA auparavant ?
21. Comment l'utilisateur sait-il qu'il doit intervenir côté Jeedom ou côté HA ?
22. Qu'est-ce que l'utilisateur doit pouvoir faire sans lire la documentation ?
23. Qu'est-ce que l'utilisateur peut accepter de devoir apprendre une seule fois ?
24. Le plugin doit-il fonctionner de façon "dégradée mais utile" sur une installation peu propre ?
25. Quel est le coût acceptable de remise en ordre avant un résultat satisfaisant ?

### Modèle de données et mapping (~35 questions)

26. Qu'est-ce qui est vraiment dans le périmètre de publication automatique en V1 ?
27. Qu'est-ce qui est explicitement hors périmètre mais fréquent chez les utilisateurs ?
28. Le plugin doit-il publier toutes les commandes visibles ou seulement celles jugées pertinentes ?
29. Qui décide qu'une commande est "pertinente" ?
30. Comment gère-t-on les commandes orphelines (Info sans Action liée, ou l'inverse) ?
31. Que fait-on d'un eqLogic avec 30 commandes ?
32. Comment distingue-t-on "température" de "consigne température" ?
33. Le mapping est-il figé au bootstrap ou évolue-t-il ?
34. Comment gère-t-on les unités ? Jeedom → `unit_of_measurement` HA normalisées.
35. Quid des commandes avec min/max/step pour les sliders HA ?
36. Comment traite-t-on les commandes de type "liste" (select) ?
37. Une commande technique mais visible doit-elle être exposée dans HA ?
38. Une commande historisée mais non actionnable doit-elle toujours devenir une entité HA ?
39. Une commande action sans état associé : button, switch, ou non publiée ?
40. Comment gère-t-on les commandes dupliquées dans un même équipement ?
41. Comment détecte-t-on consigne vs mesure ?
42. Comment détecte-t-on pourcentage vs température vs puissance vs durée vs index ?
43. Que fait-on si l'unité Jeedom est absente, erronée ou non standard ?
44. Que fait-on si plusieurs commandes correspondent au même type HA ?
45. Que fait-on si aucune commande ne correspond clairement à un modèle HA cohérent ?
46. Le plugin doit-il privilégier "juste mais incomplet" ou "large mais parfois faux" ?
47. Quel est le coût d'un faux positif vs faux négatif de mapping ?
48. Comment gère-t-on les virtuels qui mélangent des sources hétérogènes ?
49. Comment gère-t-on les commandes calculées ou dérivées ?
50. Comment gère-t-on les commandes qui changent de type fonctionnel après modification du plugin source ?
51. Quel comportement si un type générique est modifié après publication initiale ?
52. Le plugin doit-il republier automatiquement sous une autre forme si le typage change ?
53. Que devient l'historique HA si une entité change de nature ou de unique_id ?
54. Comment gère-t-on les options d'un select si elles évoluent dans Jeedom ?
55. Comment gère-t-on les min/max/step non fournis par Jeedom ?
56. Comment gère-t-on les commandes texte libres hors modèle HA standard ?
57. Faut-il une notion de confiance dans le mapping (sûr / probable / ambigu) ?
58. Comment gère-t-on les équipements sans objet, sans type générique, mais avec des commandes utiles ?
59. Comment gère-t-on les noms localisés, exotiques ou peu standardisés ?
60. Comment gère-t-on les collisions de noms dans HA ?

### Cycle de vie et réconciliation (~20 questions)

61. Quelle est la source de vérité pour l'inventaire à un instant donné ?
62. Quelle est la source de vérité pour l'état à un instant donné ?
63. Comment gère-t-on les écarts entre cache local, Jeedom, MQTT et HA ?
64. Qu'est-ce qui déclenche une republication de discovery ?
65. Qu'est-ce qui déclenche une republication d'état ?
66. Qu'est-ce qui déclenche une suppression ?
67. Qu'est-ce qui déclenche un simple passage en indisponible ?
68. Comment détecte-t-on qu'un équipement renommé est le même et non un nouveau ?
69. Comment détecte-t-on qu'une suppression + ajout = recréation vs deux objets distincts ?
70. À quel moment un unique_id doit-il rester stable ?
71. À quel moment accepte-t-on de casser la stabilité d'un unique_id ?
72. Comment éviter de republier inutilement une config identique ?
73. Que contient exactement l'empreinte de configuration ?
74. L'empreinte par eqLogic, par commande, par scénario, par device HA, ou par entité HA ?
75. Comment gère-t-on un rescan interrompu au milieu ?
76. Comment gère-t-on un redémarrage du démon pendant une réconciliation ?
77. Comment gère-t-on une commande HA pendant un remapping en cours ?
78. Quelle stratégie de récupération après incohérence détectée ?
79. Le plugin doit-il republier les états inchangés ?
80. Comment gère-t-on les tempêtes d'événements après redémarrage ?

### Robustesse, latence et performance (~25 questions)

81. Que veut dire "latence faible" fonctionnellement ?
82. Que veut dire "latence faible" techniquement ?
83. Latence maximale acceptable pour une commande simple ?
84. Latence maximale acceptable pour une mise à jour d'état ?
85. Latence maximale acceptable pour un changement de topologie ?
86. À partir de quel volume d'équipements la charge devient-elle un sujet ?
87. À partir de quel volume d'événements la publication devient-elle problématique ?
88. Le plugin doit-il limiter, lisser ou agréger certains flux bavards ?
89. Comment mesure-t-on la performance réelle du plugin ?
90. Quel indicateur alerte l'utilisateur d'un problème de performance ?
91. Le plugin doit-il exposer ses propres métriques ?
92. Consommation acceptable en CPU, RAM et I/O sur une box Jeedom ?
93. Que se passe-t-il si deux commandes HA arrivent simultanément pour le même équipement ?
94. Que se passe-t-il si une commande arrive pendant un redémarrage Jeedom ?
95. Que se passe-t-il si le démon traite un rescan pendant un changement d'état ?
96. Que se passe-t-il si l'utilisateur modifie un équipement pendant la publication ?
97. Le démon gère-t-il une file de messages ou traite-t-il tout en temps réel ?
98. Flood de commandes obsolètes à la reconnexion du démon au broker ?
99. Comment gère-t-on l'ordre des messages (OFF puis ON inversés) ?
100. Le démon est-il mono-thread ou multi-thread ? Implications sur les accès concurrents ?
101. Si l'API Jeedom répond lentement, le démon bloque-t-il toutes les publications ?
102. Que se passe-t-il si le démon crashe au milieu d'une publication de discovery ?
103. Comment gère-t-on les tempêtes d'événements après redémarrage Jeedom ou broker ?
104. Le plugin doit-il masquer totalement MQTT à l'utilisateur ?
105. Le plugin doit-il publier par défaut en lecture seule tant que l'écriture n'est pas activée ?

### Scénarios Jeedom (~8 questions)

106. Que veut dire "supporter les scénarios" exactement ?
107. Un scénario : button, switch, binary_sensor, plusieurs entités, ou rien ?
108. Quel état d'un scénario est réellement utile dans HA ?
109. Qu'est-ce qu'un "scénario désactivé" côté HA ?
110. Publier tous les scénarios ou seulement ceux explicitement marqués exposables ?
111. Comment gère-t-on les scénarios sans nom clair ?
112. Faut-il publier les scénarios techniques invisibles ou internes ?
113. Un scénario est-il un "device" ou une entité rattachée à un device logique ?

### Diagnostic, logs et observabilité (~15 questions)

114. Quel est le modèle d'erreur visible pour l'utilisateur ?
115. Comment l'utilisateur distingue-t-il problème de typage / MQTT / Jeedom / HA ?
116. Quels logs produire pour être utile sans noyer l'utilisateur ?
117. Quels logs visibles dans l'interface du plugin vs purement techniques ?
118. Mode diagnostic ou mode verbose temporaire ?
119. Comment l'utilisateur obtient-il une explication quand une commande HA échoue ?
120. Que voit l'utilisateur si le broker est indisponible ?
121. Que voit l'utilisateur si Jeedom répond mais pas HA ?
122. Que voit l'utilisateur si HA découvre partiellement les entités ?
123. Comment différencier indisponibilité temporaire vs problème structurel de mapping ?
124. Le plugin doit-il produire un rapport de santé global ?
125. Le plugin doit-il exposer un endpoint de diagnostic exportable pour le support ?
126. Comment reproduire un bug signalé sans accès à l'installation ?
127. Le plugin doit-il proposer un mode simulation avant publication réelle ?
128. Le plugin doit-il proposer un mode "publier un sous-ensemble seulement" ?

### Sécurité et périmètre d'exposition (~15 questions)

129. Quel est le modèle de sécurité du plugin ?
130. Tout ce qui est publiable doit-il être pilotable ?
131. Faut-il une allowlist d'objets, d'équipements ou de commandes ?
132. Comment empêcher l'exposition accidentelle de commandes sensibles ?
133. Comment gère-t-on les scénarios critiques ou destructifs ?
134. Le plugin doit-il distinguer lecture seule et lecture/écriture ?
135. Comment l'utilisateur sait-il exactement ce qu'il expose à HA ?
136. Que se passe-t-il si HA envoie une commande inattendue mais valide techniquement ?
137. Le plugin transporte-t-il des informations sensibles via MQTT sans conscience de l'utilisateur ?
138. Faut-il exclure certains équipements pour des raisons de confidentialité ?
139. Les noms d'équipements contenant des informations personnelles doivent-ils être filtrés ?
140. Les logs peuvent-ils devenir une source de fuite d'information ?
141. Faut-il une politique de minimisation des données publiées ?
142. Le plugin doit-il distinguer exposition des états / commandes / scénarios comme 3 niveaux d'autorisation ?
143. Le plugin doit-il publier par défaut en lecture seule ?

### Coexistence et doublons (~15 questions)

144. Que se passe-t-il si l'utilisateur a déjà des équipements dans HA via Z2M, Z-Wave JS, Matter, API cloud ?
145. Le plugin doit-il détecter les doublons potentiels côté HA ?
146. Que se passe-t-il si deux chemins aboutissent au même nom d'entité ?
147. Le plugin doit-il permettre d'exclure des familles déjà mieux intégrées nativement ?
148. Que se passe-t-il si deux plugins Jeedom exposent le même équipement physique ?
149. Comment l'utilisateur comprend-il qu'il voit deux représentations du même appareil ?
150. Le plugin peut-il coexister avec d'autres plugins Jeedom publiant sur MQTT ?
151. Le plugin doit-il réserver un namespace MQTT strict ?
152. Que se passe-t-il avec plusieurs instances Jeedom vers le même HA ?
153. Le plugin doit-il intégrer une notion d'instance ID ?
154. Que se passe-t-il si l'utilisateur migre de box Jeedom en gardant le même HA ?
155. Le plugin doit-il permettre une reprise d'identité lors d'un changement de box ?
156. Que se passe-t-il si l'utilisateur a plusieurs brokers dans son environnement ?
157. Que se passe-t-il si l'utilisateur change de broker après installation ?
158. Le plugin doit-il gérer une migration de configuration sans tout republier ?

### Écosystème, communauté, Market, gouvernance (~25 questions)

159. Le plugin sera-t-il open source, source visible non contributif, ou propriétaire ?
160. Si open source, qui décide de la roadmap ?
161. Quel modèle de contribution acceptable ?
162. Le mainteneur unique pourra-t-il absorber le support communautaire ?
163. Quel niveau de support promis sur le Market ?
164. Comment éviter que les demandes de support visent les plugins tiers ?
165. Comment éviter que les demandes de support visent HA lui-même ?
166. Comment cadrer les cas "exotiques" sans usine à exceptions ?
167. Le plugin risque-t-il de susciter des attentes supérieures au périmètre réel ?
168. Le plugin sera-t-il perçu comme concurrent de Homebridge / GSH / Alexa ?
169. Réaction probable de l'équipe core Jeedom ?
170. Mieux accueilli comme "complément de Jeedom" que "passerelle vers HA" ?
171. Faut-il anticiper des réticences "si vous voulez HA, migrez sur HA" ?
172. Le plugin doit-il se positionner explicitement comme pont d'interopérabilité ?
173. Le plugin sera-t-il gratuit, payant, freemium, ou bêta gratuite ?
174. Si payant, quelle promesse implicite de support ?
175. Si gratuit, la maintenance sera-t-elle soutenable ?
176. Quel volume d'utilisateurs pour que la maintenance communautaire soit un sujet ?
177. Projet personnel ouvert au public ou produit communautaire durable ?
178. Quel niveau de documentation pour limiter les tickets répétitifs ?
179. Documentation "installation rapide" et "diagnostic avancé" séparées ?
180. FAQ des cas non couverts dès le départ ?
181. Quel est le vrai périmètre "suffisant pour publier" ?
182. Plugin pour niche experte ou public plus large ?
183. Le plugin doit-il avoir une identité visible côté HA ?

### Compatibilité, versions, évolutions (~15 questions)

184. Version minimale de Jeedom supportée en V1 ?
185. Une seule branche Jeedom ou plusieurs versions simultanément ?
186. Version minimale de Home Assistant supportée en V1 ?
187. Testé contre plusieurs versions de HA ou seulement la plus récente ?
188. Que se passe-t-il si HA modifie MQTT Discovery entre deux versions ?
189. Que se passe-t-il si Jeedom modifie les types génériques dans une future version ?
190. Dépendance explicite à une version minimale de MQTT Manager ?
191. Que se passe-t-il si MQTT Manager change son API interne ?
192. Que se passe-t-il si MQTT Manager est déprécié ou remplacé ?
193. Le plugin doit-il encapsuler suffisamment sa dépendance à MQTT Manager ?
194. Matrice de compatibilité officielle Jeedom / HA / MQTT Manager / plugin ?
195. Qui vérifie cette compatibilité à chaque release ?
196. Coût réel de maintien de la compatibilité croisée ?

### Démon et architecture interne (~20 questions)

197. Langage du démon et pourquoi ce choix est soutenable ?
198. Langage aligné avec l'écosystème Jeedom et les box cibles ?
199. Priorité : simplicité de dev, robustesse runtime, ou maintenabilité ?
200. Consommation mémoire acceptable en régime nominal ?
201. Consommation mémoire pendant bootstrap / rescan complet ?
202. Stratégie si le démon fuit de la mémoire sur plusieurs jours ?
203. Cache disque persisté ou restart de zéro ?
204. Si cache persisté, que contient-il et quel cycle de vie ?
205. Comment le démon détecte-t-il qu'il est bloqué ou incohérent ?
206. Mécanisme de self-healing : redémarrage, purge cache, rescan, mode dégradé ?
207. Que se passe-t-il si le démon plante au milieu d'une discovery massive ?
208. Mono-process, multi-thread, asynchrone, ou file d'événements ?
209. Coût de complexité du modèle d'exécution vs bénéfice réel ?
210. Le démon doit-il fonctionner sans Internet, sans Docker, sur box minimaliste ?
211. Le démon doit-il être stateless au redémarrage ou restaurer un état ?

### Mise à jour, migration, rétrocompatibilité (~12 questions)

212. Que se passe-t-il lors d'une mise à jour du plugin si le mapping change ?
213. Migration automatique du cache et des métadonnées ?
214. Comment sait-on qu'une migration est sûre avant application ?
215. Tout republier, partiellement, ou réinitialisation propre ?
216. Comment éviter de recréer massivement les entités avec de nouveaux unique_id ?
217. Que devient l'historique HA si la structure change ?
218. Mode "prévisualisation de migration" ?
219. Journal de migration pour comprendre les changements entre versions ?
220. Rollback possible après mise à jour ratée ?
221. Que se passe-t-il si mise à jour du plugin avec versions incompatibles de HA/Jeedom/MQTT Manager ?
222. Comment l'utilisateur réinitialise-t-il proprement la publication HA ?
223. Comment l'utilisateur purge-t-il proprement l'existant pour repartir de zéro ?

### Tests et environnement de dev (~10 questions)

224. Quels cas de test indispensables pour une V1 crédible ?
225. Quels types d'installations Jeedom tester ?
226. Tester sur installation "propre" et "bordélique" ?
227. Tester avec et sans types génériques corrects ?
228. Tester avec broker local et externe ?
229. Tester avec équipements événementiels et à polling lent ?
230. Tester suppressions, renommages, désactivations, remplacements ?
231. Quels tests automatisés vs manuels ?
232. Environnement dev Jeedom + HA dockerisé pour tests auto ?
233. Jeu de données mock pour simuler différents profils ?

### Nommage, identité et conventions HA (~10 questions)

234. Les noms Jeedom sont en français, les conventions HA en anglais : comment gère-t-on entity_id ?
235. Assist HA fonctionne-t-il avec friendly_name en français et entity_id en anglais ?
236. Les device_class HA sont en anglais, les types génériques Jeedom aussi ?
237. Accents, emojis, caractères spéciaux dans les noms : quelle normalisation ?
238. Option de langue pour les noms générés côté HA ?
239. Noms orientés lisibilité utilisateur ou traçabilité technique ?
240. Comment éviter qu'un bon nom pour le quotidien soit mauvais pour le debug ?
241. Expérience HA "native" ou pont visible depuis Jeedom ?
242. Quand une divergence de modèle existe, préserver la logique Jeedom ou se conformer à HA ?
243. Qu'est-ce qui ferait dire à un utilisateur HA expérimenté que le plugin "fait sale" ?

### Expérience côté Home Assistant (~12 questions)

244. Entités publiées avec icône pertinente ou générique par défaut ?
245. device_class correcte pour affichage intelligent (graphes, badges batterie) ?
246. Assist comprend-il nativement les entités publiées ?
247. Entités exploitables dans les automations HA sans manipulation ?
248. Entités dans les Energy dashboards si mesures de puissance ?
249. Comment le nom affiché est-il construit ? Risque de nom trop long ?
250. Page "Intégrations" HA : un bloc "Jeedom" unique ou rien de visible ?
251. Entités Jeedom visuellement distinguables des entités natives HA ?
252. Risque de boucle infinie (automation HA → commande Jeedom → état → automation) ?
253. Entités avec attributes utiles au-delà de l'état (batterie, signal, dernière com) ?
254. device_class spécifiques HA sans équivalent dans les types génériques ?
255. Rescan écrase-t-il les personnalisations utilisateur dans HA ?

### Personnalisations HA et cohabitation (~8 questions)

256. Le plugin doit-il respecter un renommage manuel de l'utilisateur dans HA ?
257. Que se passe-t-il si le plugin veut mettre à jour un nom déjà personnalisé ?
258. HA = simple consommateur ou espace où l'utilisateur enrichit le modèle ?
259. Jusqu'où automatiser sans écraser les personnalisations locales ?
260. Comment le plugin sait-il qu'une divergence Jeedom/HA est volontaire ?
261. Le plugin doit-il apprendre des corrections utilisateur ou rester déterministe ?
262. Le plugin doit-il avoir un mode "strict" et un mode "tolérant" ?
263. Le plugin doit-il permettre d'exclure des plugins Jeedom entiers ?

### Périmètre V1 et questions méta (~17 questions)

264. Quel est le "non-objectif" le plus important à poser maintenant ?
265. Qu'est-ce qui ferait qu'on a construit une intégration trop générique ?
266. Qu'est-ce qui ferait qu'on couvre trop de plugins Jeedom ?
267. Quand reporter en V2 plutôt que bricoler en V1 ?
268. Critère exact pour "ce plugin est déjà utile" ?
269. Critère exact pour "ce plugin est publiable" ?
270. Critère exact pour "ce plugin est maintenable par une personne" ?
271. Quel risque sous-estime-t-on encore ?
272. Quelle hypothèse est la plus fragile dans la vraie vie ?
273. Quelle question sur l'adoption communautaire n'a-t-on pas osé poser ?
274. Le plugin doit-il gérer les floors HA ?
275. Le plugin doit-il publier des devices logiques quand la notion de device est artificielle ?
276. Comment gère-t-on les eqLogics multi-canaux → plusieurs devices HA ?
277. Quelle part de la complexité viendra des plugins tiers plutôt que du core ?
278. Le plugin doit-il signaler "support complet / partiel / expérimental" par type ?
279. À combien d'exceptions de mapping pour un plugin source faut-il un traitement dédié ?
280. Comment tester sans installation Jeedom complète + HA en face ?

---

## Phase 3 : Reverse Brainstorming - 24 scénarios d'échec

### Échecs d'expérience utilisateur

**#1 - La vitrine vide :** L'utilisateur installe, synchronise, ouvre HA et voit 3 entités sur 150 équipements. Pas d'erreur, pas de message. Il conclut que ça ne marche pas.
*Cause :* Types génériques mal renseignés + absence de diagnostic P0.

**#3 - Le plugin qui crie au loup :** Le plugin publie tout ce qu'il peut mapper, même approximativement. 500 entités dont la moitié inutilisables. Le bruit noie le signal.
*Cause :* Mapping qui privilégie la couverture plutôt que la précision.

**#4 - Le faux temps réel :** Les commandes partent bien mais l'état remonte avec 2 à 30 secondes de retard. L'utilisateur perd confiance dans l'interface.
*Cause :* Chaîne de latence non maîtrisée + promesse implicite de quasi temps réel.

**#5 - Le mode optimiste honteux :** Le plugin refuse l'optimiste par principe. Pour les équipements sans retour d'état, les commandes semblent ne rien faire. Comparé aux intégrations HA natives, c'est pire.
*Cause :* Position dogmatique sur l'état réel vs pragmatisme de HA.

**#8 - Le diagnostic inutile :** Le diagnostic dit "type générique manquant" ou "mapping ambigu". L'utilisateur ne sait toujours pas quoi faire concrètement.
*Cause :* Messages techniques sans parcours de remédiation.

**#13 - Conventions HA non respectées :** Devices artificiels, noms mal formés, classes incohérentes, unités non standard. Les utilisateurs HA trouvent le plugin "sale".
*Cause :* Approche "bridge technique" sans respect des conventions écosystème.

**#21 - La promesse mal formulée :** "Retrouvez automatiquement toute votre maison". L'utilisateur comprend : tout, proprement, sans effort. La V1 déçoit par définition.
*Cause :* Wording trop ambitieux par rapport à la réalité du produit.

### Échecs techniques

**#2 - Le cimetière d'entités fantômes :** Après 3 mois d'utilisation, 40 entités unavailable, 15 doublons, automations cassées. Le cleanup est pire que tout réinstaller.
*Cause :* Suppression et réconciliation non gérées proprement dans la durée.

**#9 - Le bootstrap qui tue la box :** Premier scan complet sur une grosse installation sature CPU/RAM/IO. Jeedom ralentit, HA découvre partiellement, l'utilisateur désinstalle.
*Cause :* Bootstrap non progressif sur box à ressources limitées.

**#10 - Le démon immortel mais cassé :** Le démon ne crashe pas mais entre dans un état incohérent silencieux. Plus de publications, cache périmé, commandes mal traitées. Jeedom affiche "OK".
*Cause :* Pas de heartbeat métier, pas de healthcheck, pas de self-healing.

**#11 - La migration destructrice :** Nouvelle version du plugin change les unique_id. Historique perdu, dashboards cassés, automations pointent vers d'anciens identifiants.
*Cause :* Pas de politique de stabilité des identifiants entre versions.

**#22 - La boucle de commande infernale :** Automation HA → commande Jeedom → changement état → republication → automation HA → boucle infinie. Broker sature, démon s'emballe.
*Cause :* Pas de mécanisme anti-boucle ou debounce.

**#23 - Le broker partagé empoisonné :** Collision de topics MQTT avec Z2M, Node-RED, Tasmota. Le plugin perturbe d'autres systèmes ou reçoit des commandes non sollicitées.
*Cause :* Pas de namespace MQTT strict.

**#24 - La mise à jour HA qui casse tout :** HA modifie un comportement MQTT Discovery. Les entités disparaissent. L'utilisateur ne sait pas qui est en cause.
*Cause :* Rythme de release HA (mensuel) vs capacité de validation du mainteneur.

### Échecs de sécurité et d'exposition

**#6 - Le pont qui duplique tout :** L'utilisateur a déjà des équipements dans HA via d'autres intégrations. Le plugin crée des doublons. L'assistant vocal ne sait plus lequel choisir.
*Cause :* Pas de stratégie d'exclusion ni de détection de doublons.

**#7 - Le plugin qui casse Apple Maison :** L'utilisateur corrige ses types génériques pour HA et dégrade involontairement Homebridge / Apple Maison.
*Cause :* Tension entre conventions de différentes plateformes consommatrices des types génériques.

**#12 - Le plugin qui expose une bombe :** Commandes sensibles (arrêt alarme, ouverture portail, scénario critique) publiées et pilotables depuis HA ou assistant vocal sans conscience de l'utilisateur.
*Cause :* Publication trop large sans politique d'exclusion de commandes sensibles.

### Échecs de maintenabilité

**#14 - Support déguisé pour tous les plugins Jeedom :** Chaque utilisateur remonte un cas exotique lié à un plugin tiers. Le mainteneur debug l'écosystème Jeedom entier.
*Cause :* Plugin générique = point de convergence des incohérences de tous les autres plugins.

**#15 - La dette des exceptions :** Règles spéciales, heuristiques locales, contournements par plugin. Le moteur de mapping devient un empilement impossible à raisonner.
*Cause :* Ajout de cas particuliers pour satisfaire les retours sans stratégie de cohérence.

**#16 - Le plugin trop intelligent :** Beaucoup d'inférence (noms, regroupement auto, profils dynamiques). Impressionnant en démo, imprévisible en production, impossible à debugger.
*Cause :* Compensation des limites Jeedom par de l'intelligence opaque.

### Échecs humains et communautaires

**#17 - Pas de public réel :** Le segment motivé est plus petit que prévu. Les purs Jeedom n'en veulent pas. Les purs HA préfèrent migrer. Reste une niche insuffisante.
*Cause :* Zone intermédiaire de marché entre deux écosystèmes.

**#18 - Le backlash communautaire :** Le plugin est perçu comme "le plugin qui pousse vers HA". Réaction froide du core Jeedom. Les devs d'autres plugins se sentent contournés.
*Cause :* Positionnement communautaire mal géré.

**#19 - Marche seulement chez son auteur :** Validé sur une installation personnelle bien structurée. Dès qu'il sort sur des installations réelles, beaucoup de promesses ne tiennent plus.
*Cause :* Biais de validation classique des projets nés d'un besoin personnel.

**#20 - L'épuisement du mainteneur :** Tickets, suggestions, cas limites, demandes de support, compatibilité à chaque release. Le mainteneur n'arrive plus à suivre après quelques mois.
*Cause :* Un plugin d'intégration entre deux gros écosystèmes crée une dette de support structurelle.

---

## Synthèse : les 10 recommandations prioritaires pour le cadrage

| # | Recommandation | Empêche | Impact |
|---|---|---|---|
| 1 | **Ajouter le flux d'onboarding comme user story P0** | Scénario #1 (vitrine vide) | Critique |
| 2 | **Remonter le diagnostic de couverture à P0** | Scénarios #1, #8 | Critique |
| 3 | **Définir les 4 niveaux de confiance état** dans l'architecture | Scénarios #4, #5 | Critique |
| 4 | **Créer un ADR stratégie MQTT** (QoS, retained, reconnexion, namespace, anti-boucle) | Scénarios #10, #22, #23 | Haute |
| 5 | **Distinguer les 4 cas de cycle de vie** (suppression, indisponibilité, désactivation, remapping) | Scénarios #2, #11 | Haute |
| 6 | **Reformuler la promesse produit** ("pont d'interopérabilité", prérequis assumés) | Scénarios #18, #21 | Critique |
| 7 | **Définir une politique d'exposition par défaut conservatrice** | Scénarios #3, #12 | Haute |
| 8 | **Concevoir la réconciliation hybride** (event::changes + rescan) | Scénario #2 | Haute |
| 9 | **Lister les plugins Jeedom supportés en V1** avec niveau de support explicite | Scénarios #14, #15 | Haute |
| 10 | **Prévoir une stratégie de test multi-installations** | Scénario #19 | Haute |

---

## Patterns transversaux identifiés

### Pattern 1 : Le document décrit le "quoi" mais pas le "comment"
Le cadrage est solide sur la vision, l'architecture logique et le périmètre. Il est faible sur les parcours utilisateur concrets, les stratégies opérationnelles et les cas dégradés.

### Pattern 2 : Le chemin nominal est bien couvert, les exceptions sont ignorées
Le document décrit le cas où tout va bien. Il ne traite pas les installations hétérogènes, les équipements atypiques, les états manquants, les brokers partagés, les doublons ni les migrations.

### Pattern 3 : Sous-estimation systématique de la friction utilisateur
La promesse "simple" est contredite par : le prérequis MQTT Manager, la charge de typage, l'absence de diagnostic P0, et le fait que la charge de configuration est déplacée vers Jeedom plutôt que supprimée.

### Pattern 4 : Le mainteneur unique est le vrai single point of failure
Le risque principal du projet n'est pas technique mais humain. La dette de support, de compatibilité croisée et d'exceptions de mapping peut rapidement dépasser la capacité d'un mainteneur seul à 5h/semaine.

---

## Prochaines étapes recommandées

1. **Mettre à jour le document de cadrage** en intégrant les 10 recommandations prioritaires.
2. **Rédiger l'ADR stratégie MQTT** comme document d'architecture dédié.
3. **Définir le flux d'onboarding** comme user story P0 avec critères d'acceptation.
4. **Lister les plugins Jeedom supportés V1** avec niveaux de support (complet / partiel / exclu).
5. **Reformuler le positionnement communautaire** : pont d'interopérabilité, pas passerelle de migration.
6. **Planifier des tests sur installations variées** : propre, historique, sans types génériques, avec broker externe.
