---
stepsCompleted: ["step-01-document-discovery", "step-02-prd-analysis", "step-03-epic-coverage-validation", "step-04-ux-alignment", "step-05-epic-quality-review", "step-06-final-assessment"]
filesIncluded: ["prd.md", "architecture.md", "ux-design-specification.md", "epics.md"]
---
# Implementation Readiness Assessment Report

**Date:** 2026-03-12
**Project:** jeedom2ha

## Document Discovery Results

**PRD Documents:**
- [prd.md](file:///Users/alexandre/Dev/jeedom/plugins/jeedom2ha/_bmad-output/planning-artifacts/prd.md) (52814 bytes, 2026-03-12)

**Architecture Documents:**
- [architecture.md](file:///Users/alexandre/Dev/jeedom/plugins/jeedom2ha/_bmad-output/planning-artifacts/architecture.md) (21455 bytes, 2026-03-12)

**UX Design Documents:**
- [ux-design-specification.md](file:///Users/alexandre/Dev/jeedom/plugins/jeedom2ha/_bmad-output/planning-artifacts/ux-design-specification.md) (36328 bytes, 2026-03-12)

**Epics & Stories Documents:**
- [epics.md](file:///Users/alexandre/Dev/jeedom/plugins/jeedom2ha/_bmad-output/planning-artifacts/epics.md) (6767 bytes, 2026-03-12)

---

## Issues Found

- ## PRD Analysis

### Functional Requirements

FR1: L'utilisateur peut lancer un bootstrap automatique qui lit l'inventaire Jeedom et publie les équipements exploitables dans Home Assistant via MQTT Discovery.
FR2: Le système peut mapper automatiquement les commandes Jeedom vers des entités HA en utilisant les types génériques Jeedom comme moteur principal de mapping.
FR3: Le système peut utiliser le type/sous-type Jeedom comme deuxième moteur de mapping lorsque le type générique est absent ou insuffisant.
FR4: Le système peut associer une métadonnée de confiance (sûr / probable / ambigu) à chaque mapping pour piloter la politique d'exposition.
FR5: Le système applique une politique d'exposition conservative : en cas d'ambiguïté de mapping, l'équipement n'est pas publié plutôt que publié avec un mapping potentiellement faux.
FR6: L'utilisateur peut forcer un rescan / republication manuelle à tout moment pour voir l'effet de ses corrections de typage ou d'ajustements d'installation.
FR7: Le système peut générer des noms d'affichage construits à partir du contexte Jeedom (nom d'objet parent et nom d'équipement), permettant à l'utilisateur de reconnaître ses équipements dans HA sans ambiguïté.
FR8: Le système peut associer un contexte spatial utilisable par HA (suggested_area dans la discovery MQTT) lorsque l'objet parent Jeedom est défini.
FR9: Le système peut republier automatiquement les configurations nécessaires après un redémarrage de HA ou du broker MQTT.
FR10: Le système peut publier des lumières (on/off, dimmer si disponible et correctement mappé) comme entités HA pilotables.
FR11: Le système peut publier des prises / switches comme entités HA pilotables.
FR12: Le système peut publier des volets / covers (open/close/stop, position si disponible et correctement mappée) comme entités HA pilotables.
FR13: Le système peut publier des capteurs numériques simples (température, humidité, puissance, énergie, batterie) comme entités HA avec métadonnées conformes aux conventions HA lorsque ces métadonnées sont disponibles et pertinentes.
FR14: Le système peut publier des capteurs binaires simples (ouverture, mouvement/présence, fuite, fumée) comme entités HA avec métadonnées conformes lorsque ces métadonnées sont disponibles et pertinentes.
FR15: L'utilisateur HA peut piloter les actionneurs publiés (lumières, prises, volets) depuis Home Assistant avec exécution effective dans Jeedom.
FR16: Le système peut mettre à jour dans HA l'état des équipements pilotés pour refléter l'état Jeedom lorsque cet état est disponible sur le périmètre supporté.
FR17: Le système peut synchroniser les changements d'état Jeedom vers HA de manière incrémentale (sans rescan complet) en régime nominal.
FR18: L'utilisateur peut exclure un équipement spécifique de la publication.
FR19: Le système peut republier proprement après modification des exclusions (les entités exclues disparaissent de HA, les entités restantes sont inchangées).
FR20: Le système peut détecter l'ajout d'un nouvel équipement dans Jeedom et le publier dans HA au prochain rescan.
FR21: Le système peut détecter le renommage d'un équipement dans Jeedom et mettre à jour le nom d'affichage dans HA sans changer le unique_id.
FR22: Le système peut retirer proprement de HA les entités correspondant à des équipements supprimés dans Jeedom.
FR23: Le système utilise des unique_id stables basés sur les IDs Jeedom (pas les noms) pour que les entités HA survivent aux renommages et déplacements.
FR24: Le système peut signaler l'indisponibilité du bridge afin que HA reflète correctement l'état global de la publication.
FR25: Le système peut exposer un état de disponibilité par entité permettant à HA de distinguer un équipement indisponible d'un équipement supprimé.
FR26: L'utilisateur peut consulter un diagnostic de couverture intégré dans l'interface Jeedom montrant, pour chaque équipement : publié / partiellement publié / non publié + raison principale.
FR27: Le diagnostic peut suggérer des actions de remédiation à l'utilisateur (ex : "configurez le type générique dans Jeedom").
FR28: L'utilisateur peut exporter le diagnostic de couverture pour le transmettre au support.
FR29: Le système produit des logs incluant l'identifiant équipement, le résultat de mapping et la raison d'échec le cas échéant, lisibles sans expertise MQTT et utilisables pour le support à distance.
FR30: Le système documente explicitement le périmètre V1 supporté et les raisons de non-publication dans le diagnostic.
FR31: Le système peut auto-détecter la configuration du broker MQTT via MQTT Manager si celui-ci est présent.
FR32: L'utilisateur peut configurer manuellement les paramètres de connexion au broker MQTT en l'absence de MQTT Manager.
FR33: Le système peut détecter l'absence de broker MQTT et guider l'utilisateur clairement vers la configuration nécessaire.
FR34: L'utilisateur peut configurer les paramètres globaux du plugin (niveau de log, options de publication).
FR35: Le système supporte l'authentification au broker MQTT.
FR36: L'utilisateur peut déclencher une republication complète propre de la configuration publiée vers HA.

Total FRs: 36

### Non-Functional Requirements

NFR1: Pour les commandes simples du périmètre V1, en contexte nominal (réseau local, broker disponible, équipement avec retour d'état compatible), la latence perçue HA → Jeedom → retour d'état doit être ≤ 2s, avec une cible idéale autour de 1s. Une latence ≥ 5s est considérée comme non acceptable.
NFR2: Le bootstrap initial ne doit pas rendre l'interface Jeedom inutilisable : le temps de réponse de l'interface Jeedom ne doit pas dépasser 10s pendant le bootstrap, et aucune saturation durable des ressources de la box ne doit survenir.
NFR3: Après redémarrage HA/broker, la republication doit être lissée sur au moins 5s pour les installations de plus de 50 entités, afin d'éviter un pic de charge susceptible de dégrader Jeedom ou le broker.
NFR4: Le démon doit rester opérationnel en régime nominal sans intervention manuelle.
NFR5: Le démon ne doit pas présenter de dégradation progressive de mémoire ou de stabilité sur une exécution prolongée : la consommation mémoire ne doit pas augmenter de plus de 20% après 72h d'exécution continue par rapport à la valeur stabilisée après démarrage.
NFR6: Le démon doit se reconnecter automatiquement au broker MQTT en moins de 30s après rétablissement de la connectivité, sans intervention utilisateur.
NFR7: Pas d'accumulation durable d'entités fantômes dans HA lors d'un usage normal (ajout, renommage, suppression, rescan).
NFR8: Les transitions d'état du cycle de vie doivent être déterministes, documentées et explicables.
NFR9: Une mise à jour du plugin ne doit pas provoquer de rupture non documentée du parc d'entités existant.
NFR10: Après redémarrage de Home Assistant, les entités découvertes doivent redevenir disponibles sans intervention manuelle de l'utilisateur.
NFR11: Le plugin doit supporter l'authentification au broker MQTT (utilisateur/mot de passe). Support TLS si broker distant.
NFR12: Aucune donnée d'installation ne doit être transmise vers l'extérieur du réseau local sans action explicite de l'utilisateur.
NFR13: Les mécanismes d'export (diagnostic, logs) doivent minimiser les données personnelles incluses. Pas de télémétrie sans consentement explicite ; toute télémétrie éventuelle est désactivée par défaut.
NFR14: Les identifiants de connexion broker ne doivent pas apparaître en clair dans les logs.
NFR15: Les messages MQTT Discovery publiés doivent être compatibles avec les exigences documentées par Home Assistant pour unique_id, device, origin, availability, retained config et métadonnées d'entité pertinentes.
NFR16: Le namespace MQTT du plugin ne doit pas entrer en collision avec les autres clients MQTT courants (Zigbee2MQTT, ESPHome, Tasmota, Node-RED).
NFR17: Le plugin doit être compatible avec les versions Jeedom 4.4.9+, Debian 12, Python 3.9+. La matrice de compatibilité HA sera cadrée au démarrage du développement.
NFR18: La politique de retained messages doit être conforme aux attentes HA : discovery et availability en retained, commandes non retained.
NFR19: La consommation CPU/RAM du démon en régime nominal doit rester compatible avec les box à ressources limitées : cible < 5% CPU et < 100 Mo RAM sur Raspberry Pi 4 pour une installation de référence (~80 équipements).
NFR20: La charge I/O générée par le plugin ne doit pas augmenter la latence des autres plugins Jeedom de plus de 500ms en régime nominal.
NFR21: Le bootstrap initial doit étaler la publication sur au moins 10s pour les installations de plus de 50 équipements, afin de ne pas saturer les box à ressources limitées lors du premier scan complet.
NFR22: En cas d'échec de publication, de reconnexion ou de mapping, le plugin doit produire une information exploitable permettant d'identifier la cause sans analyse MQTT bas niveau.

Total NFRs: 22

### Additional Requirements

- **Licences** : GPL v3 pour le plugin Jeedom.
- **Distribution** : Jeedom Market via GitHub.
- **Conformité** : RGPD (minimisation, local), Cyber Resilience Act (reporting vulnérabilités).
- **Architecture** : Démon Python 3 asynchrone via `jeedomdaemon`.
- **Compatibilité venv** : Utilisation impérative de `system::getCmdPython3(__CLASS__)` pour l'environnement virtuel Jeedom.

### PRD Completeness Assessment

Le PRD est extrêmement complet et mature. Les exigences sont granulaires, numérotées et couvrent l'intégralité du cycle de vie du produit (MVP, Growth, Vision). Les critères de succès sont mesurables et les parcours utilisateurs détaillent bien les cas limites attendus.

## Epic Coverage Validation

### Coverage Matrix

| FR Number | PRD Requirement | Epic Coverage | Status |
| :--- | :--- | :--- | :--- |
| FR1 | Discovery & Publication auto | Epic 2 (ST2.1, ST2.3) | ✓ Covered |
| FR2 | Mapping via `generic_type` | Epic 2 (ST2.2) | ✓ Covered |
| FR3 | Fallback via type/sous-type | Epic 2 (ST2.2) | ✓ Covered |
| FR4 | Métadonnée de confiance | - | ❌ Missing Story |
| FR5 | Politique conservative | - | ❌ Missing Story |
| FR6 | Force rescan / republication | Epic 4 (ST4.2) | ✓ Covered |
| FR7 | Noms d'affichage cohérents | Epic 2 (ST2.3) | ✓ Covered |
| FR8 | Contexte spatial (`area`) | Epic 2 (ST2.3) | ✓ Covered |
| FR9 | Republication auto (reboot) | Epic 5 (ST5.1) | ✓ Covered |
| FR10-14| Support types (Light, Cover, etc.)| Epic 2 (ST2.2) | ✓ Covered |
| FR15 | Pilotage HA -> Jeedom | Epic 3 (ST3.2) | ✓ Covered |
| FR16 | Retour d'état Jeedom -> HA | Epic 3 (ST3.1) | ✓ Covered |
| FR17 | Synchro incrémentale | Epic 3 (ST3.1) | ✓ Covered |
| FR18-19| Exclusions | Epic 4 (ST4.4) | ✓ Covered |
| FR20-23| Cycle de vie & IDs stables | Epic 5 (ST5.2) | ✓ Covered |
| FR24-25| Disponibilité (LWT) | Epic 3 (ST3.3) | ✓ Covered |
| FR26-28| Diagnostic UI & Export | Epic 4 (ST4.1, ST4.3) | ✓ Covered |
| FR29 | Logs exploitables | Epic 1 (ST1.2) | ✓ Covered |
| FR30 | Documentation périmètre (diag) | Epic 4 (ST4.1) | ✓ Covered |
| FR31 | Auto-détection MQTT Manager | - | ❌ Missing Story |
| FR32 | Configuration manuelle broker | - | ❌ Missing Story |
| FR33 | Guidance absence broker | - | ❌ Missing Story |
| FR34 | Configuration globale | Epic 1 (ST1.1) | ✓ Covered |
| FR35 | Auth MQTT | - | ❌ Missing Story |
| FR36 | Republication manuelle | Epic 4 (ST4.2) | ✓ Covered |

### Missing Requirements

#### Critical Missing FRs (Configuration MQTT)
FR31, FR32, FR33, FR35 : La gestion complète de la connexion au broker MQTT (détection, configuration, sécurité et guidage utilisateur) n'est pas couverte par les User Stories actuelles. 
- **Impact** : Risque de blocage dès l'installation si le broker n'est pas auto-configuré par MQTT Manager.
- **Recommandation** : Ajouter une Story "ST1.4 : Configuration de la connectivité MQTT" dans l'Epic 1.

#### High Priority Missing FRs (Mapping Policy)
FR4, FR5 : La logique fine de confiance du mapping et l'exclusion des cas ambigus manquent de critères d'acceptation explicites.
- **Impact** : Risque de publication d'entités erronées dans HA, dégradant la confiance utilisateur.
- **Recommandation** : Enrichir ST2.2 avec des critères sur la gestion de la confiance (Sûr/Probable/Ambigu).

### Coverage Statistics

- Total PRD FRs: 36
- FRs covered in epics: 30
- Coverage percentage: 83%

## UX Alignment Assessment

### UX Document Status
- **Fichier trouvé** : `ux-design-specification.md`
- **Contenu** : Complet (Principes, Design System, Patterns, User Flows).

### Alignment Issues
- **UX ↔ Architecture** : Alignement fort sur la stratégie "Native-Clean" (utilisation des composants Jeedom Core v4.4+). L'architecture PHP/Python supporte bien le modèle de diagnostic asynchrone requis par l'UX.
- **UX ↔ Epics** : Déphasage sur l'Onboarding. L'UX insiste sur la détection automatique et le guidage MQTT, mais les Stories de l'Epic 1 ne détaillent pas ces écrans de configuration/guidage.

### Warnings
- ⚠️ **Risque Onboarding** : Sans les Stories de configuration MQTT (FR31-35), le "moment déclic" (maison dans HA en < 1h) risque d'être gâché par une installation technique trop abrupte.

## Epic Quality Review

### Quality Assessment Findings

#### 🔴 Critical Violations
- **Epic 1 Sans Valeur Utilisateur Directe** : L'Epic 1 ("Fondations") est purement technique (Scaffolding, Démon, Bridge). Bien qu'essentielle, elle ne livre aucun incrément de valeur pour l'utilisateur final. 
- **Recommandation** : Fusionner ST1.1 avec une première story de valeur (ex: ST2.1) ou orienter l'Epic 1 vers "Connectivité initiale Jeedom-HA".

#### 🟠 Major Issues
- **Story ST2.2 Surdimensionnée** : Le moteur de mapping (ST2.2) couvre tous les types d'équipements MVP (Lumières, Volets, Prises, Capteurs). C'est un périmètre trop large pour une seule story.
- **Recommandation** : Découper ST2.2 par domaine (ex: ST2.2a : Mapping Éclairage, ST2.2b : Mapping Ouvrants, etc.).
- **Forward Dependency (Implicit)** : ST2.3 (Publication) semble dépendre techniquement du succès complet de ST2.2 pour être testable.

#### 🟡 Minor Concerns
- **Nomenclature Technique** : Les titres d'Epics ("Cycle de Vie", "Démon Python") sont trop orientés vers l'implémentation.
- **Recommandation** : Utiliser des titres orientés valeur (ex: "Fiabilité du pont", "Communication Jeedom <-> HA").

### Best Practices Compliance
- [x] Epic independence maintained
- [ ] Epic delivers user value (Epic 1 fails)
- [ ] Stories appropriately sized (ST2.2 fails)
- [x] No forward dependencies
- [x] Clear acceptance criteria

## Summary and Recommendations

### Overall Readiness Status
**NEEDS WORK**

Le projet `jeedom2ha` dispose d'une base documentaire solide et d'une architecture cohérente. Cependant, le découpage actuel des Epics et Stories présente des lacunes critiques qui pourraient compliquer le démarrage et l'onboarding utilisateur.

### Critical Issues Requiring Immediate Action
1. **Configuration MQTT Orpheline** : Aucune User Story ne couvre la configuration du broker (auto ou manuelle) ni le guidage utilisateur en cas d'absence de broker. C'est un point bloquant pour le "Happy Path".
2. **Découpage ST2.2** : La Story couvrant tout le moteur de mapping est trop vaste et risque de devenir un "trou noir" de développement sans visibilité de progression par domaine.
3. **Valeur de l'Epic 1** : L'Epic 1 est totalement technique, ne respectant pas les principes de livraison de valeur utilisateur.

### Recommended Next Steps

1. **Ajouter une Story ST1.4** ("Configuration et Onboarding MQTT") pour couvrir les exigences FR31 à FR35.
2. **Scinder ST2.2** en sous-stories par domaine fonctionnel (ex: ST2.2a Lumières, ST2.2b Ouvrants, ST2.2c Capteurs).
3. **Reformuler l'Epic 1** pour inclure un jalon de connectivité visible pour l'utilisateur (ex: "Connexion et Statut du Bridge").
4. **Enrichir le moteur de mapping** avec des critères d'acceptation sur la gestion de la confiance (FR4/FR5).

### Final Note

Cette évaluation a identifié des points d'amélioration structurels majeurs. Bien que le socle PRD/Architecture soit prêt, un ajustement du backlog (Epics/Stories) est fortement recommandé avant de lancer l'implémentation pour garantir un flux de développement sain et une expérience utilisateur conforme aux ambitions du produit.

---
**Date de l'évaluation** : 2026-03-12
**Assesseur** : Antigravity (BMM)

**Implementation Readiness Assessment Complete**
Report generated: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-03-12.md`
