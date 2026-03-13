---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
  - '_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-12.md'
---

# jeedom2ha - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for jeedom2ha, decomposing the requirements from the PRD, UX Design, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: Bootstrap automatique (lecture inventaire Jeedom, mapping via types génériques, publication MQTT Discovery)
FR2: Mapping automatique via types génériques Jeedom
FR3: Fallback sur type/sous-type Jeedom si type générique absent
FR4: Métadonnée de confiance (sûr / probable / ambigu) associée au mapping
FR5: Politique d'exposition conservative (ne pas publier en cas d'ambiguïté)
FR6: Rescan / republication manuelle post-correction
FR7: Noms d'affichage cohérents basés sur le contexte Jeedom
FR8: Contexte spatial (suggested_area) transmis à HA
FR9: Republication automatique après redémarrage HA/Broker
FR10: Support Lumières (on/off, dimmer)
FR11: Support Prises / Switches
FR12: Support Volets / Covers (open/close/stop, position)
FR13: Support Capteurs numériques (temp, hum, puissance, énergie, batterie)
FR14: Support Capteurs binaires (ouverture, mouvement, fuite, fumée)
FR15: Pilotage HA -> Jeedom (actionneurs)
FR16: Retour d'état Jeedom -> HA
FR17: Synchronisation incrémentale d'état (event::changes)
FR18: Exclusion d'équipement spécifique
FR19: Republication propre après modification des exclusions
FR20: Détection ajout équipement via rescan
FR21: Détection renommage (unique_id stables)
FR22: Retrait propre des équipements supprimés
FR23: unique_id stables basés sur IDs Jeedom
FR24: Signalement indisponibilité du bridge (LWT)
FR25: État de disponibilité par entité
FR26: Diagnostic de couverture intégré (publié/partiel/ko + raison)
FR27: Suggestions de remédiation dans le diagnostic
FR28: Export du diagnostic pour support
FR29: Logs lisibles et catégorisés
FR30: Documentation du périmètre V1 dans le diagnostic
FR31: Auto-détection MQTT via MQTT Manager
FR32: Configuration manuelle MQTT fallback
FR33: Guidance en cas d'absence de Broker MQTT
FR34: Configuration globale du plugin (logs, etc.)
FR35: Support authentification MQTT Broker
FR36: Déclenchement manuel de republication complète

### NonFunctional Requirements

NFR1: Latence cible ≤ 1s, max 2s (inacceptable ≥ 5s)
NFR2: Bootstrap non bloquant pour l'UI Jeedom (< 10s réponse)
NFR3: Lissage de la republication post-redémarrage (> 5s)
NFR4: Stabilité du démon sans intervention manuelle
NFR5: Absence de fuite mémoire (< 20% augmentation après 72h)
NFR6: Reconnexion automatique MQTT < 30s
NFR7: Pas d'accumulation d'entités fantômes
NFR8: Transitions de cycle de vie déterministes et documentées
NFR9: Pas de rupture non documentée lors des mises à jour
NFR10: Persistance de la disponibilité HA après redémarrage
NFR11: Support Authentification MQTT (User/Pass) et TLS
NFR12: Local-First (aucune donnée vers l'extérieur sans action)
NFR13: Minimisation des données personnelles dans les exports/logs
NFR14: Secrets absents des logs
NFR15: Conformité stricte MQTT Discovery HA
NFR16: Namespace MQTT isolé (pas de collision)
NFR17: Compatibilité Jeedom 4.4.9+, Debian 12, Python 3.9+
NFR18: Politique retained messages (config/availability = yes, cmd = no)
NFR19: Consommation ressources masterisée (Pi 4: < 5% CPU, < 100 Mo RAM)
NFR20: Charge I/O transparente pour Jeedom (< 500ms impact latence)
NFR21: Bootstrap étalé sur > 10s (lissage)
NFR22: Diagnostic métier clair sans expertise MQTT requise

### Additional Requirements

- **Starter Template**: Utilisation de `jeedom/plugin-template` officiel [Architecture]
- **Framework Daemon**: Utilisation de `jeedomdaemon` asynchrone [Architecture]
- **Transport Interne**: HTTP Local (PHP -> Python) et Callbacks API Jeedom (Python -> PHP) [Architecture]
- **Sécurité API**: API 127.0.0.1 protégée par un `local_secret` [Architecture]
- **Cache**: RAM + Disque (non autoritatif, resetable) [Architecture]
- **Tests**: Framework `pytest` dans `resources/daemon/tests/` [Architecture]
- **Stratégie UI**: Desktop-first, Vanilla Jeedom (Bootstrap 3 / jQuery) [UX]
- **Patterns UI**: Status Badges riches, Sticky Control Header, Accordéon pour diagnostic [UX]
- **Accessibilité**: Redondance visuelle (icônes + texte), support thèmes clair/sombre [UX]
- **Licences** : GPL v3 pour le plugin Jeedom [Readiness Report]
- **Distribution** : Jeedom Market via GitHub [Readiness Report]
- **Conformité** : RGPD (minimisation, local), Cyber Resilience Act (reporting vulnérabilités) [Readiness Report]
- **Compatibilité venv** : Utilisation impérative de `system::getCmdPython3(__CLASS__)` pour l'environnement virtuel Jeedom [Readiness Report]

### FR Coverage Map

FR1: Epic 2 - Bootstrap automatique
FR2: Epic 2 - Mapping générique
FR3: Epic 2 - Fallback type/sous-type
FR4: Epic 2 - Métadonnée de confiance
FR5: Epic 2 - Politique conservative
FR6: Epic 4 - Rescan manuel
FR7: Epic 2 - Noms cohérents
FR8: Epic 2 - Contexte spatial
FR9: Epic 5 - Republication auto reboot
FR10: Epic 2 - Support Lumières
FR11: Epic 2 - Support Prises
FR12: Epic 2 - Support Volets
FR13: Epic 2 - Support Capteurs numériques
FR14: Epic 2 - Support Capteurs binaires
FR15: Epic 3 - Pilotage HA -> Jeedom
FR16: Epic 3 - Retour d'état
FR17: Epic 3 - Synchro temps réel
FR18: Epic 4 - Exclusion équipement
FR19: Epic 4 - Republication après exclusion
FR20: Epic 5 - Détection ajout rescan
FR21: Epic 5 - Détection renommage
FR22: Epic 5 - Retrait équipements supprimés
FR23: Epic 5 - IDs stables
FR24: Epic 1 - LWT bridge
FR25: Epic 3 - Disponibilité entités
FR26: Epic 4 - Diagnostic UI
FR27: Epic 4 - Suggestions remédiation
FR28: Epic 4 - Export diagnostic
FR29: Epic 1 - Logs lisibles
FR30: Epic 4 - Documentation périmètre
FR31: Epic 1 - Auto-détection MQTT
FR32: Epic 1 - Config manuelle MQTT
FR33: Epic 1 - Guidance MQTT
FR34: Epic 1 - Config globale
FR35: Epic 1 - Auth MQTT
FR36: Epic 4 - Republication manuelle

## Epic List

### Epic 1: Connectivité & Onboarding du Pont
Objectif : L'utilisateur installe le plugin, connecte son broker MQTT (auto/manuel) avec guidage, et voit le statut du pont (En ligne).
**FRs covered:** FR24, FR29, FR31, FR32, FR33, FR34, FR35

### Epic 2: Découverte & Mapping Intelligent
Objectif : L'utilisateur scanne sa maison Jeedom et voit apparaître ses équipements dans HA avec un typage correct (ou un diagnostic clair si KO).
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR7, FR8, FR10, FR11, FR12, FR13, FR14

### Epic 3: Synchronisation & Pilotage
Objectif : L'utilisateur pilote ses équipements depuis HA et voit les retours d'état en temps réel (< 2s).
**FRs covered:** FR15, FR16, FR17, FR25

### Epic 4: Maîtrise du Périmètre & Diagnostic
Objectif : L'utilisateur affine ce qui est publié (exclusions) et résout les problèmes via l'interface de diagnostic.
**FRs covered:** FR6, FR18, FR19, FR26, FR27, FR28, FR30, FR36

### Epic 5: Fiabilité & Cycle de Vie
Objectif : Le système gère les redémarrages, les renommages et les suppressions sans créer d'entités fantômes dans le cas nominal.
**FRs covered:** FR9, FR20, FR21, FR22, FR23

---

## Epic 1: Connectivité & Onboarding du Pont

Objectif : L'utilisateur installe le plugin, connecte son broker MQTT (auto/manuel) avec guidage, et voit le statut du pont (En ligne).

### Story 1.1: Initialisation et Communication PHP ↔ Python

As a utilisateur Jeedom,
I want que le plugin démarre son démon correctement et affiche son statut,
So that je sache que le moteur interne est actif.

**Acceptance Criteria:**

**Given** le plugin est installé
**When** je clique sur "Démarrer" le démon
**Then** le démon Python démarre dans le venv Jeedom via `system::getCmdPython3`
**And** l'interface Jeedom affiche le statut du démon (OK)
**And** une requête HTTP locale PHP → daemon sur 127.0.0.1 fonctionne (API liée à 127.0.0.1 uniquement)
**And** le heartbeat retourne un payload structuré de type statut/version/uptime minimal
**And** si le démon ne répond pas, l'état est visible clairement dans l'UI (KO/Erreur)

### Story 1.2: Configuration et Onboarding MQTT (Auto & Manuel)

As a utilisateur Jeedom,
I want que le plugin détecte ma configuration MQTT Manager ou me permette de la saisir manuellement,
So that je n'aie pas à deviner les paramètres de connexion.

**Acceptance Criteria:**

**Given** le démon est actif
**When** j'accède à la configuration du plugin
**Then** le plugin tente une auto-détection si MQTT Manager est présent
**And** un fallback manuel permet de saisir : host, port, user, password
**And** les paramètres additionnels sont supportés : TLS / validation certificat pour broker distant
**And** la configuration est stockée via les mécanismes standards Jeedom
**And** un test de connexion est déclenchable depuis l'UI
**And** un message de guidage clair s'affiche si aucun broker n'est disponible/configuré

### Story 1.3: Validation de la Connexion et Statut du Pont

As a utilisateur Jeedom,
I want voir un statut "Connecté" clair dès que le pont communique avec MQTT,
So that je sois sûr que la publication vers Home Assistant est possible.

**Acceptance Criteria:**

**Given** la configuration MQTT est saisie
**When** le démon tente de se connecter
**Then** l'interface affiche distinctement l'état du démon et l'état MQTT (badges séparés)
**And** le démon configure un LWT (Last Will and Testament) MQTT
**And** les logs montrent clairement les succès/échecs de connexion broker
**And** une reconnexion automatique est tentée après une coupure temporaire
**And** en cas d'échec broker, le plugin reste pilotable côté Jeedom et remonte un état dégradé explicite (ex: "MQTT Déconnecté")

---

## Epic 2: Découverte & Mapping Intelligent

Objectif : L'utilisateur scanne sa maison Jeedom et voit apparaître ses équipements dans HA avec un typage correct (ou un diagnostic clair si KO).

> [!IMPORTANT]
> **Règle Transverse Epic 2 :** Toute décision de mapping doit être déterministe, confidence-aware, diagnostiquable, et respecter la règle : ne pas publier plutôt que publier faux.

### Story 2.1: Topology Scraper & Contexte Spatial

As a utilisateur Jeedom,
I want que le plugin identifie mes équipements éligibles et leur contexte,
So that je puisse préparer une projection fiable dans Home Assistant.

**Acceptance Criteria:**

**Given** le moteur du démon est actif
**When** un scan de la topologie est déclenché
**Then** l'inventaire Jeedom (eqLogics et commandes) est extrait via les interfaces standard
**And** les IDs Jeedom (eqLogic, cmd, object) sont normalisés dans un modèle interne canonique
**And** les objets Jeedom sont utilisés comme source de contexte spatial et base de `suggested_area`, sans équivalence stricte avec les areas HA
**And** les équipements exclus explicitement ou manifestement non éligibles sont marqués avec une raison explorable (préparation diagnostic)

### Story 2.2: Mapping & Exposition des Lumières

As a utilisateur Jeedom,
I want retrouver mes lumières (On/Off, Dimmer) dans HA avec un niveau de confiance explicite,
So that je puisse les piloter avec une configuration fiable.

**Acceptance Criteria:**

**Given** la topologie Jeedom est scrapée
**When** le moteur de mapping traite un équipement d'éclairage
**Then** la décision de mapping produit : un type cible, un niveau de confiance (Sûr / Probable / Ambigu) et une raison
**And** les entités "Sûres" sont publiées via MQTT Discovery
**And** les entités "Probables" ne sont publiées que si la politique d'exposition le permet, sinon elles restent diagnostiquées mais non publiées
**And** les entités "Ambigües" ne sont pas publiées par défaut ; les cas non sûrs sont expliqués dans le diagnostic

### Story 2.3: Mapping & Exposition des Ouvrants (Volets)

As a utilisateur Jeedom,
I want retrouver mes volets et brise-soleil dans HA sans fausse représentation,
So that je gère les ouvertures de ma maison sereinement.

**Acceptance Criteria:**

**Given** le moteur de mapping traite un volet
**When** les commandes de positionnement sont analysées
**Then** si la position n'est pas disponible ou pas honnêtement mappable, le volet reste publié avec les capacités disponibles (open/close/stop) sans inventer de position
**And** la publication MQTT Discovery reflète fidèlement les capacités réelles détectées
**And** les inversions de sens configurées dans Jeedom sont respectées

### Story 2.4: Mapping & Exposition des Prises / Switches

As a utilisateur Jeedom,
I want retrouver mes prises et relais simples dans HA,
So that je puisse piloter mes appareils électriques.

**Acceptance Criteria:**

**Given** le moteur de mapping traite un actionneur simple
**When** il correspond à un type `switch` (Prise, Relais)
**Then** le mapping produit une entité `switch` HA fiable
**And** les métadonnées (device_class, icon) sont ajoutées uniquement si elles sont confirmées par le type générique Jeedom
**And** les commandes ou valeurs invalides ne produisent aucune publication mensongère

### Story 2.5: Mapping & Exposition des Capteurs (Numériques & Binaires)

As a utilisateur Jeedom,
I want visualiser mes mesures et états binaires dans HA sans fausse précision,
So that je supervise ma maison avec des données réelles.

**Acceptance Criteria:**

**Given** le moteur de mapping traite des commandes d'info
**When** elles correspondent à des mesures numériques ou des états binaires
**Then** le système produit des entités `sensor` ou `binary_sensor` correspondantes
**And** les métadonnées HA (`unit_of_measurement`, `device_class`, `state_class`) sont incluses uniquement si elles sont fiables
**And** une commande avec unité absente ou douteuse ne se voit pas attribuer de métadonnée arbitraire
**And** toute incohérence détectée (ex: valeur non numérique pour un sensor) bloque la publication de l'entité et alimente le diagnostic

---

## Epic 3: Synchronisation & Pilotage

Objectif : L'utilisateur pilote ses équipements depuis HA et voit les retours d'état en temps réel (< 2s).

> [!IMPORTANT]
> **Règle Transverse Epic 3 :** Aucune synchronisation ne doit publier un état faux pour "faire joli". L'état réel est préféré ; à défaut, le comportement doit rester explicable, cohérent et conforme à la politique de mapping honnête.

### Story 3.1: Synchronisation incrémentale des états Jeedom → HA

As a utilisateur Jeedom,
I want que mes changements d'état soient répercutés fidèlement dans HA,
So that j'aie une vision juste de ma maison en temps réel.

**Acceptance Criteria:**

**Given** des équipements sont déjà publiés dans HA
**When** un changement d'état survient dans Jeedom (via `event::changes`)
**Then** le démon Python détecte le changement pour la commande mappée
**And** le démon déclenche une publication MQTT vers le `state_topic` correspondant
**And** la latence cible est proche de 1s, et acceptable ≤ 2s en contexte nominal sur le périmètre V1

### Story 3.2: Pilotage HA → Jeedom avec confirmation honnête d'état

As a utilisateur Home Assistant,
I want piloter mes équipements depuis HA avec une confirmation réelle de réussite,
So that je sois sûr que mes ordres sont exécutés.

**Acceptance Criteria:**

**Given** un actionneur est disponible dans HA
**When** j'envoie une commande (ON/OFF, position, niveau, etc.) depuis HA
**Then** le démon écoute le `command_topic` MQTT et traduit l'ordre
**And** l'ordre est transmis à Jeedom via l'interface standard retenue par l'architecture (API Jeedom)
**And** le plugin privilégie la confirmation par état réel quand elle existe
**And** pour les commandes sans retour fiable, il applique la politique prévue (optimiste contrôlé ou action stateless), sans comportement mensonger

### Story 3.3: Disponibilité du pont et des entités quand l'information est fiable

As a utilisateur Home Assistant,
I want visualiser l'état de disponibilité de mes équipements,
So that je sache si mon système est opérationnel.

**Acceptance Criteria:**

**Given** le pont est en service
**When** l'état de connectivité change (pont ou équipement)
**Then** le plugin expose une disponibilité cohérente pour le pont via le LWT global
**And** le plugin expose une disponibilité pour les entités quand une information fiable d'indisponibilité existe côté Jeedom
**And** en cas d'arrêt du pont ou de perte de connectivité broker, les entités concernées sont marquées indisponibles
**And** le plugin distingue l'indisponibilité du pont (problème global) d'une indisponibilité propre à un équipement (problème local) quand l'info est disponible

---

## Epic 4: Maîtrise du Périmètre & Diagnostic

Objectif : L'utilisateur affine ce qui est publié (exclusions) et résout les problèmes via l'interface de diagnostic.

> [!IMPORTANT]
> **Règle Transverse Epic 4 :** L'Epic 4 ne doit pas créer un "outil de debug pour développeur" exposé brut à l'utilisateur ; il doit transformer la complexité technique en diagnostic métier explicable et actionnable.

### Story 4.1: Interface de Diagnostic de Couverture

As a utilisateur Jeedom,
I want voir une liste claire de mes équipements avec leur statut de publication,
So that je comprenne instantanément ce qui est visible dans HA.

**Acceptance Criteria:**

**Given** la maison a été scannée
**When** j'ouvre l'interface de diagnostic
**Then** le plugin affiche les statuts harmonisés : Publié, Partiellement publié, Non publié, Exclu
**And** le niveau de confiance de mapping est affiché quand il est pertinent (Sûr / Probable / Ambigu / Ignoré)
**And** les badges visuels UX sont utilisés pour refléter ces états de manière intuitive

### Story 4.2: Diagnostic détaillé et Suggestions de Remédiation

As a utilisateur Jeedom,
I want accéder au détail technique d'un équipement problématique et savoir comment le corriger,
So that je puisse rendre ma maison HA plus complète en autonomie.

**Acceptance Criteria:**

**Given** une ligne de diagnostic présente un état "Non publié" ou "Partiellement publié"
**When** j'ouvre l'accordéon de détail
**Then** la remédiation affichée est actionnable mais non intimidante
**And** le système distingue clairement : problème de typage Jeedom, type non supporté en V1, exclusion volontaire, mapping ambigu
**And** les conseils de correction sont spécifiques à la cause détectée (ex: "Configurez le type générique sur la commande 'Etat'")

### Story 4.3: Gestion des Exclusions et Actions Manuelles

As a utilisateur Jeedom,
I want pouvoir exclure un équipement de HA ou forcer un rescan complet,
So that je garde mon installation Home Assistant propre.

**Acceptance Criteria:**

**Given** le plugin est configuré
**When** j'effectue une action manuelle sur un équipement (Exclure) ou globalement (Rescan)
**Then** l'exclusion par équipement est appliquée avec retrait immédiat dans HA (Unpublish MQTT)
**And** le système permet un rescan / republication complète avec purge contrôlée du cache local
**And** toute action manuelle est confirmée visuellement dans l'UI avec un résultat clair (Succès / Partiel / Échec)

### Story 4.4: Export de Diagnostic pour Support

As a utilisateur Jeedom,
I want exporter un rapport de diagnostic complet mais anonymisé,
So that je puisse obtenir de l'aide sans exposer mes données sensibles.

**Acceptance Criteria:**

**Given** j'ai besoin d'assistance technique
**When** je clique sur "Télécharger le diagnostic support"
**Then** le fichier généré contient la topologie normalisée, les décisions de mapping, les raisons de non-publication et les versions (Plugin, Jeedom, Python, Broker)
**And** les secrets, mots de passe et tokens sont strictement absents de l'export
**And** un mode "partage externe" permet de pseudonymiser les noms d'équipements pour protéger la vie privée

---

## Epic 5: Fiabilité & Cycle de Vie

Objectif : Le système gère les redémarrages, les renommages et les suppressions sans créer d'entités fantômes dans le cas nominal.

> [!IMPORTANT]
> **Règle Transverse Epic 5 :** L'Epic 5 ne vise pas un "zéro défaut invisible", mais un comportement de cycle de vie propre, stable et explicable, sans accumulation durable d'entités fantômes ni rupture inutile des identifiants.

### Story 5.1: Persistance et Republication Post-Reboot

As a utilisateur Jeedom,
I want que mes équipements redeviennent disponibles dans HA après un redémarrage,
So that le pont revienne automatiquement à un état cohérent sans nécessiter d'intervention manuelle dans le cas nominal.

**Acceptance Criteria:**

**Given** le pont a déjà fonctionné
**When** un redémarrage survient (démon, Jeedom, broker ou Home Assistant)
**Then** le démon recharge son cache technique, se revalide contre Jeedom, puis republie ce qui doit l'être
**And** les messages "Retained" sont utilisés conformément à la stratégie retenue pour Discovery et Availability, permettant une redécouverte rapide par HA
**And** la republication est lissée dans le temps pour éviter les pics de charge (> 10s pour les gros parcs)
**And** la reconnexion MQTT déclenche une reprise propre sans duplication inutile

### Story 5.2: Stabilité des Identifiants et Renommages

As a utilisateur Jeedom,
I want pouvoir renommer mes équipements dans Jeedom,
So that je puisse faire évoluer mon installation sans créer de nouvelle entité ni casser les références existantes côté HA dans le cas nominal.

**Acceptance Criteria:**

**Given** un équipement déjà publié dans HA
**When** je modifie son nom dans Jeedom
**Then** le mapping met à jour le `name` de l'entité dans HA lors du prochain scan
**And** le `unique_id` HA (basé exclusivement sur les IDs internes Jeedom) reste inchangé
**And** aucune nouvelle entité ou doublon n'est créé dans Home Assistant suite à ce renommage

### Story 5.3: Nettoyage Automatique et Gestion des Écarts

As a utilisateur Jeedom,
I want que les équipements supprimés dans Jeedom disparaissent de HA,
So that j'évite l'accumulation d'entités fantômes.

**Acceptance Criteria:**

**Given** un scan de topologie est effectué
**When** un équipement est identifié comme "Supprimé" dans Jeedom (et non juste indisponible)
**Then** le système publie un payload vide "Retained" sur le topic Discovery de l'entité concernée pour solliciter son retrait dans HA
**And** le cache local du démon est synchronisé pour refléter la réalité de Jeedom
**And** la disparition de l'entité est mentionnée comme raison dans le diagnostic si pertinent
**And** le système distingue clairement la suppression réelle (retrait Discovery) de l'indisponibilité temporaire (statut Availability)
