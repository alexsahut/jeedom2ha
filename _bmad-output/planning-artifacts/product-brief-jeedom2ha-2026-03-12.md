---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: [
  'docs/cadrage_plugin_jeedom_ha_bmad.md',
  '_bmad-output/brainstorming/brainstorming-session-2026-03-12-001.md',
  '_bmad-output/planning-artifacts/research/domain-jeedom-homeassistant-research-2026-03-12.md',
  '_bmad-output/planning-artifacts/research/technical-jeedom-plugin-development-research-2026-03-12.md'
]
date: 2026-03-12
author: Alexandre
---

# Product Brief: jeedom2ha

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

**jeedom2ha** est un plugin conçu pour offrir le meilleur des deux mondes aux utilisateurs avancés de Jeedom : la robustesse de leur installation domotique historique (logique métier, scénarios) et la richesse de l'écosystème Home Assistant (interfaces modernes, intégrations IA, assistants vocaux). Plutôt que d'imposer une migration complète, lourde et risquée, le produit agit comme une couche d'interopérabilité fluide. Avec un très faible coût d'entrée, il permet de retrouver rapidement et de manière cohérente sa maison Jeedom dans Home Assistant, sans recoder les équipements ni casser l'existant.

---

## Core Vision

### Problem Statement
Aujourd'hui, un utilisateur Jeedom ayant construit une installation domotique riche et stable se retrouve face à un choix frustrant : rester exclusivement sur Jeedom en se privant des innovations de Home Assistant, ou entamer une migration complète et chronophage. Le vrai problème à résoudre est d'éliminer le coût mental, technique et temporel imposé par la double maintenance, le remapping manuel et la migration forcée.

### Problem Impact
Ce dilemme affecte particulièrement les utilisateurs Jeedom expérimentés qui valorisent leur installation existante mais sont tentés par les capacités modernes de Home Assistant. S'ils ne trouvent pas de pont robuste, ces utilisateurs stagnent technologiquement ou s'engagent dans des chantiers de migration très lourds qui menacent la stabilité de leur foyer. Le manque d'interopérabilité transforme un actif précieux en frustration technique.

### Why Existing Solutions Fall Short
Les approches habituelles sur le marché de la domotique opposent les écosystèmes : il faut généralement "choisir son camp" et tout reconstruire de zéro, ou bien bricoler des ponts manuels fragiles nécessitant une maintenance en double. Les solutions actuelles ignorent la valeur de l'historique de l'utilisateur et transforment une installation stable en dette technique à migrer.

### Proposed Solution
**jeedom2ha** rend une installation Jeedom existante interopérable, exploitable et durable dans Home Assistant, avec un coût de mise en place minimal. L'utilisateur installe le plugin, se connecte au broker MQTT et lance la synchronisation : en moins d'une heure, il retrouve ses équipements essentiels publiés, bien nommés et pilotables de manière fiable dans Home Assistant, tout en conservant Jeedom comme moteur backend principal.

### Key Differentiators
Le produit se distingue par son approche pragmatique : capitaliser sur l'existant au lieu de le jeter. Sa valeur unique réside dans la rapidité spectaculaire du "time to value" (une maison exploitable dans HA en moins d'une heure), sa réversibilité totale, et sa promesse de fournir le meilleur des capacités modernes de restitution sans exiger aucune migration.

---

## Target Users

### Primary Users

**Nicolas, "Le meilleur des deux mondes" (42-50 ans)**
*   **Contexte:** Utilisateur Jeedom avancé depuis 4 ans. Possède une installation riche, stable et très peaufinée (60-120 équipements, scénarios complexes, multi-protocoles). Son système domotique est crucial au quotidien.
*   **Problème & Frustrations:** Il perçoit la valeur de Home Assistant (interfaces, IA, intégrations) mais refuse de détruire son investissement Jeedom pour en profiter. L'idée de remapper manuellement, de maintenir deux modèles ou de bricoler des ponts instables est sa plus grande frustration.
*   **Motivations & Peurs:** Il veut protéger son investissement passé tout en réduisant le coût d'exploration de HA. Il redoute que le plugin ne crée une "usine à gaz" (doublons, fantômes, instabilité dans HA).
*   **Critères de Succès:** En moins d'une heure, il retrouve une maison exploitable dans HA (pièces, équipements, noms propres). Il bénéficie immédiatement des atouts de HA sans reconstruire la logique métier.

### Secondary Users

**Julien, "Le curieux qui expérimente" (35-45 ans)**
*   **Contexte:** Utilisateur Jeedom intermédiaire (1-4 ans d'usage). Installation fonctionnelle mais moins complexe. Attiré par HA mais effrayé par le mur technique d'une migration.
*   **Motivations:** Cherche un droit à l'expérimentation à faible coût et faible risque. Veut tester l'interface et les nouveautés de HA sans s'engager.
*   **Aha! Moment:** Lorsqu'il réalise qu'il peut jouer avec sa "vraie" maison dans HA en quelques clics, et surtout, qu'il peut tout annuler sans rien casser.

**Sébastien, "Le stratège en transition" (38-52 ans)**
*   **Contexte:** Utilisateur Jeedom confirmé, anticipant une évolution de son architecture vers un modèle hybride ou vers HA à terme.
*   **Motivations:** Il cherche une trajectoire de transition douce, réversible et contrôlée. Il refuse le "big bang" migratoire.
*   **Succès:** Le plugin devient son outil de continuité de service, lui permettant de déplacer progressivement des cas unitairement vers HA tout en gardant Jeedom comme filet de sécurité.

**Autres intervenants indirects:**
*   **Le Foyer (Conjoint(e), enfants):** Bénéficiaires ultimes de la solution. Ils cherchent la simplicité et la fiabilité. Une belle interface HA générée par le plugin améliore directement leur expérience quotidienne.
*   **Intégrateurs / Installateurs (V2+):** Profils professionnels cherchant à moderniser des installations Jeedom existantes chez leurs clients avec une couche HA moderne, de manière rentable et industrialisable.

### User Journey (Persona: Nicolas)

*   **Discovery:** Nicolas lit un sujet sur la communauté Jeedom ou HACF concernant un nouveau plugin "jeedom2ha" qui promet une intégration *MQTT Discovery* native sans effort.
*   **Onboarding (The First Hour):**
    *   Il achète/télécharge le plugin sur le Market Jeedom.
    *   Il renseigne les identifiants de son broker MQTT existant.
    *   Il valide la synchronisation de ses premiers équipements.
*   **Success Moment (The "Aha!" Moment):** Il ouvre son application Home Assistant. L'intégration MQTT affiche "Nouveaux appareils découverts". Il clique, et voit ses volets, lumières, et capteurs Jeedom apparaître avec leurs vrais noms et répartis dans les bonnes pièces. "Ma maison est déjà là."
*   **Core Usage:** Il commence à créer ses premiers dashboards Lovelace et à connecter ses équipements Jeedom aux assistants vocaux natifs de Home Assistant sans aucune configuration supplémentaire.
*   **Long-term:** **jeedom2ha** devient le pont invisible de sa domotique. Jeedom gère les automatismes complexes en coulisses, tandis que toute l'interaction familiale et l'exposition moderne se fait via Home Assistant.

---

## 5. Success Metrics

### User Success

Le succès utilisateur se mesure d'abord par un "time to first useful value" rapide, puis par l'adoption durable du produit comme brique du quotidien.

**Court Terme (Valeur Initiale < 7 jours) :**
*   **Installation sans friction :** L'utilisateur configure le plugin et lance sa première synchronisation sans abandonner.
*   **Maison exploitable (Time to Value) :** Ses équipements essentiels apparaissent correctement dans HA, sans avoir à reconstruire la logique métier.
*   **Premiers usages concrets :** L'utilisateur pilote un équipement, crée un dashboard ou l'expose à un assistant vocal depuis HA dans les premiers jours.
*   **Lisibilité :** Il comprend ce qui est publié, ce qui ne l'est pas, et pourquoi (diagnostic clair).

**Long Terme (Adoption Durable) :**
*   **Plugin indispensable :** Le bridge reste activé dans la durée. Ce n'est plus un test, c'est une composante de la maison.
*   **Évolution sans dette :** Il ajoute/modifie des équipements Jeedom sans que la synchronisation ne casse ou ne génère une dette de maintenance dans HA.
*   **Facilitateur stratégique :** Il utilise HA comme point d'entrée Frontend/IA tout en gardant Jeedom en Backend, évitant ainsi la migration forcée.

### Business Objectives

**Objectifs à 3 mois (Validation du Product-Market Fit) :**
L'objectif est de prouver que le produit résout réellement le problème pour la cible principale, sans générer une dette de support ingérable.
*   Valider que le produit répond aux cas "Meilleur des deux mondes" et "Test de HA sans migration".
*   Obtenir une V1 crédible (synchro utile, diagnostic clair, pas d'effets de bord graves, cycle de vie sain).
*   Identifier les cas d'usage dominants (Dashboards ? Assistants IA ? Transition ?).
*   Vérifier que le coût de maintenance (support/bugs) reste soutenable pour un mainteneur.

**Objectifs à 12 mois (Brique d'écosystème) :**
L'objectif est d'exister durablement dans l'écosystème domotique.
*   Devenir la solution de référence recommandée pour faire coexister Jeedom et HA.
*   Construire une base installée active et stable.
*   Maîtriser la dette technique pour préparer sereinement les évolutions futures.

### Key Performance Indicators (KPIs)

Pour vérifier que le pari est gagné, les indicateurs prioritaires à suivre sont :

**KPIs Produit / Utilisateur :**
- Taux de première synchronisation réussie (mesure la friction).
- Délai médian jusqu'à la première valeur utile (Time to Value).
- Taux de rétention à 30 jours et 90 jours (différencie l'adoption pérenne du test curieux).

**KPIs Qualité / Fiabilité :**
- Nombre de bugs critiques / bloquants ouverts et temps de résolution.
- Taux de régressions par release.
- Absence d'anomalies de cycle de vie dans HA (ex: pas d'explosion d'entités fantômes).

**KPIs Adoption / Perception :**
- Nombre d'installations réellement actives.
- Note moyenne / Sentiment global sur le Market et les forums.
- Taux de verbatim utilisateur confirmant l'atteinte de la promesse (ex: "J'ai le meilleur de HA sans avoir eu à migrer mon Jeedom").

---

## 6. MVP Scope

Le principe directeur du MVP est de privilégier la valeur rapide, la fiabilité et la compréhension claire de la donnée publiée, plutôt que l'exhaustivité totale. Le but est de créer le moment "Aha!" en moins d'une heure.

### Core Features (Le noyau V1 indispensable)

1.  **Bootstrap Automatique :** Lecture de l'inventaire Jeedom, détection des équipements exploitables et publication automatique dans HA sans recréation manuelle.
2.  **Mapping Automatique "Generic-Type First" :** Priorité absolue aux types génériques Jeedom pour mapper les entités. Zéro typage manuel dans HA. Si ambiguïté : on ne publie pas.
3.  **Support des Actionneurs du Quotidien :**
    *   Lumières
    *   Prises / Switchs
    *   Volets / Covers
4.  **Support des Capteurs à Forte Valeur :**
    *   Capteurs numériques (Température, Humidité, Puissance, Énergie, Batterie).
    *   Capteurs binaires (Ouverture porte/fenêtre, Mouvement/Présence, Fuite, Fumée).
5.  **Round-trip Minimum (HA → Jeedom) :** Possibilité de piloter les actionneurs supportés depuis HA avec retour d'état cohérent.
6.  **Contexte Spatial Minimal :** Utilisation de l'Objet/Pièce Jeedom pour enrichir les noms d'affichage et/ou l'assignation spatiale dans HA.
7.  **Diagnostic Intégré :** Interface Jeedom expliquant pourquoi un équipement n'est pas publié (type générique manquant, non supporté, etc.).
8.  **Rescan / Republication manuelle :** Possibilité pour l'utilisateur de forcer la mise à jour de la topologie.

### Out of Scope for MVP

1.  **Infrastructure MQTT :** Le plugin ne déploie pas de broker. Il requiert un broker MQTT existant (ex: via MQTT Manager).
2.  **Thermostats et "Climate" complexes :** Exclus de la V1 stricte (périmètre *stretch* V1.1) à cause de la complexité de mapping.
3.  **Équipements complexes :** Alarmes, caméras, lecteurs multimédias, équipements audio/vidéo.
4.  **Scénarios Jeedom en tant que scripts HA :** Pas de synchronisation avancée de la logique métier (au mieux, exposition très simple de quelques actions plus tard).
5.  **Reproduction parfaite de l'arborescence :** Pas de miroir hiérarchique complexe, juste le contexte de la pièce parente.
6.  **Synchronisation bidirectionnelle des métadonnées :** Pas d'import de l'historique Jeedom ni d'export de dashboards HA.
7.  **Déduplication Intelligente :** Pas de gestion complexe des périphériques existant déjà dans HA via d'autres intégrations natives.

### MVP Success Criteria

Le MVP sera considéré comme validé (« go/no-go » pour poursuivre) si :
*   Les utilisateurs avec une installation "standard" voient leurs lumières/volets/prises apparaître dans HA sans effort.
*   Aucune configuration manuelle du type n'est requise dans HA.
*   Les actions de base depuis HA fonctionnent sans latence excessive ou asynchronisme grave.
*   Le volume d'incidents techniques bloquants liés au mapping reste très faible (le diagnostic explique l'essentiel des cas de "non-publication").

### Future Vision (Objectif à 2-3 ans)

Si le succès est total, la vision n'est *pas* la "synchronisation 100% transparente". C'est de devenir **la couche de coexistence de référence** entre Jeedom et HA.
*   **Couverture étendue :** Ajout des Thermostats (Climate), d'une gestion intelligente des scénarios (ex: boutons d'action locaux) et de périphériques plus spécialisés.
*   **Support IA / Voix Facilité :** Maximiser la qualité du mapping pour que les entités Jeedom bénéficient nativement, et sans configuration, des capacités conversationnelles et IA de Home Assistant.
*   **Robuste et Résilient :** Gestion extrêmement propre du cycle de vie (suppressions, renommages), sans aucune entité fantôme.
*   **Un Outil Hybride :** Le plugin permettra à un foyer de tourner durablement avec Jeedom comme robuste moteur backend et Home Assistant comme couche frontend, IA et interactive de pointe, sans heurts.
