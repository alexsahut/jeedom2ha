# Sprint Change Proposal — Story 1.2-bis : Fiabilisation Auto-détection MQTT Manager

**Date :** 2026-03-13
**Sprint :** Epic 1 — Connectivité & Onboarding du Pont
**Auteur :** Alexandre
**Scope :** Minor — implémentation directe par l'équipe dev

---

## Section 1 : Résumé du problème

### Problème identifié

L'auto-détection de la configuration MQTT Manager (plugin `mqtt2`) implémentée dans la Story 1.2 ne fonctionne pas de manière fiable en conditions réelles. Deux dysfonctionnements distincts ont été identifiés :

1. **Clés de configuration inconnues** : `getMqttManagerConfig()` lit les clés `mqttAddress`, `mqttPort`, `mqttUser`, `mqttPass` dans la table de configuration du plugin `mqtt2`, mais les vraies clés utilisées par la version installée ne correspondent pas — aucun résultat n'est retourné (ou des valeurs internes incorrectes, comme le port 1885 du broker Mosquitto interne).

2. **Absence de mécanisme d'import/reset** : une fois une configuration manuelle sauvegardée, l'utilisateur ne dispose d'aucun moyen de :
   - l'écraser par une nouvelle auto-détection,
   - la réinitialiser pour repartir de zéro,
   - forcer un import depuis MQTT Manager si la détection automatique a échoué au chargement.

### Contexte de découverte

Découvert lors des tests d'intégration de la Story 1.2 sur une installation Jeedom réelle avec MQTT Manager actif. Le test de connexion MQTT fonctionne correctement (credentials, TLS, port), mais l'auto-détection retourne des paramètres incorrects ou aucun résultat.

### Preuves

- Logs diagnostiques : aucun `[MQTT-DIAG] mqtt2 key=` loggué → les clés lues ne sont pas celles stockées par `mqtt2`
- Port 1885 retourné (port Mosquitto interne) au lieu de 1883 (port broker client)
- TLS activé par défaut dans certains cas alors que le broker est configuré sans TLS
- Après sauvegarde manuelle, le formulaire pré-remplit depuis la config sauvegardée — aucun bouton pour importer depuis `mqtt2`

---

## Section 2 : Analyse d'impact

### Impact Epic

| Epic | Impact | Description |
|------|--------|-------------|
| Epic 1 | Modifié | Story 1.2 partiellement complète. Nouvelle story 1.2-bis à ajouter. Story 1.3 non bloquée. |
| Epic 2–5 | Aucun | Fonctionnement cœur non affecté — la config manuelle fonctionne. |

### Impact Stories

| Story | Statut | Action |
|-------|--------|--------|
| Story 1.2 | Done (partiel) | Marquer done — test connexion, config manuelle, TLS, sécurité password sont fonctionnels |
| Story 1.2-bis | À créer | Nouvelle story : fiabilisation auto-détection + UX import/reset |
| Story 1.3 | En attente | Peut démarrer — non bloquée par 1.2-bis |

### Conflits Artifacts

| Artifact | Conflit | Action requise |
|----------|---------|---------------|
| PRD — FR31 | Partiel | Enrichir : préciser le comportement d'import forcé et les cas d'erreur d'auto-détection |
| PRD — FR32 | Partiel | Enrichir : ajouter le cas "écraser config manuelle par auto-détection" |
| UX Spec | Gap | Ajouter : bouton "Récupérer depuis MQTT Manager", états d'erreur UX, action reset formulaire |
| Architecture | Mineur | Documenter les cas `null` explicites de `getMqttManagerConfig()` |
| Code — diagnostic | Temporaire | Retirer la boucle de diagnostic des clés une fois les vraies clés identifiées |

### Impact Technique

- Uniquement PHP (`jeedom2ha.class.php`, `jeedom2ha.ajax.php`) et JS (`configuration.php`)
- Aucun impact sur le démon Python ni sur l'API HTTP interne
- Pas de nouveau endpoint HTTP nécessaire
- Tests : non-régression sur le test de connexion + tests manuels sur Jeedom réel

---

## Section 3 : Approche recommandée

### Option retenue : Ajustement direct (Option 1)

**Rationale :**
- Story 1.2 substantiellement complète — les corrections critiques (credentials, URL AJAX, ConnectionResetError, port filtering, TLS default) sont en place et fonctionnelles
- Le gap restant est circonscrit et bien identifié
- Aucun rollback nécessaire — l'existant est solide
- Impact timeline minimal : 1 story courte dans Epic 1
- Le MVP n'est pas menacé — configuration manuelle fonctionnelle en attendant

**Effort :** Medium
**Risque :** Low
**Timeline :** Story 1.2-bis réalisable avant ou en parallèle de 1.3

---

## Section 4 : Propositions de changements détaillées

### 4.1 — Nouvelle Story 1.2-bis à créer dans Epic 1

```
Story: [1.2-bis] Fiabilisation Auto-détection MQTT Manager & Import Forcé

As a utilisateur Jeedom,
I want pouvoir importer la configuration de MQTT Manager en un clic et comprendre
pourquoi l'auto-détection échoue si elle ne trouve rien,
So that je n'aie pas à deviner les paramètres MQTT même quand la config manuelle est déjà renseignée.

Acceptance Criteria:

Given le plugin mqtt2 est actif
When je clique sur "Récupérer depuis MQTT Manager"
Then les champs host, port, user sont écrasés avec les valeurs détectées
And un message de confirmation (ou d'erreur explicite) est affiché
And le mot de passe n'est jamais chargé dans le DOM

Given le plugin mqtt2 est absent ou inactif
When l'auto-détection est tentée (au chargement ou via bouton)
Then un message d'erreur clair s'affiche ("Plugin MQTT Manager non détecté ou inactif")

Given les clés de configuration réelles de mqtt2 sont identifiées (via logs diagnostiques)
When getMqttManagerConfig() est appelée
Then les vraies clés sont lues correctement et le port interne (1885) est filtré

Given la configuration manuelle est renseignée
When l'utilisateur clique sur "Réinitialiser le formulaire"
Then les champs sont vidés (sans sauvegarder) pour permettre une saisie fraîche
```

### 4.2 — Modifications epics.md

```
Section : Epic 1 — Connectivité & Onboarding du Pont

ANCIEN :
- Story 1.1: Initialisation et Communication PHP ↔ Python
- Story 1.2: Configuration et Onboarding MQTT (Auto & Manuel)
- Story 1.3: Validation de la Connexion et Statut du Pont

NOUVEAU :
- Story 1.1: Initialisation et Communication PHP ↔ Python
- Story 1.2: Configuration et Onboarding MQTT (Auto & Manuel)
- Story 1.2-bis: Fiabilisation Auto-détection MQTT Manager & Import Forcé  ← NOUVEAU
- Story 1.3: Validation de la Connexion et Statut du Pont

Rationale: Gap identifié lors de l'implémentation — auto-détection non fiable + UX import manquante
```

### 4.3 — Enrichissement PRD (FR31 + FR32)

```
PRD — Section Functional Requirements

FR31 — ANCIEN :
Auto-détection MQTT via MQTT Manager

FR31 — NOUVEAU :
Auto-détection MQTT via MQTT Manager avec gestion explicite des cas d'échec
(plugin absent, clés inconnues, port interne) et possibilité d'import forcé
par l'utilisateur via action dédiée

FR32 — ANCIEN :
Configuration manuelle MQTT fallback

FR32 — NOUVEAU :
Configuration manuelle MQTT fallback avec mécanisme de remplacement par
auto-détection (import forcé) et réinitialisation du formulaire
```

### 4.4 — Enrichissement UX Spec

```
Section : Configuration MQTT — Formulaire

AJOUTER :
- Bouton "Récupérer depuis MQTT Manager" (visible uniquement si mqtt2 est actif)
  → Appel AJAX getMqttConfig avec mode=force
  → Écrase les champs host/port/user avec les valeurs détectées
  → Affiche : succès ("Configuration importée") ou erreur ("Plugin non détecté")

- Bouton/lien "Réinitialiser" (discret, texte seul)
  → Vide les champs host/port/user/password du formulaire (sans sauvegarder)

- État d'erreur auto-détection :
  → Badge "Plugin MQTT Manager non détecté" en warning si mqtt2 absent
  → Badge "Clés de configuration non trouvées" en warning si mqtt2 présent mais clés vides
  → Message distingué de l'état "Configuration manuelle" (déjà affiché)
```

---

## Section 5 : Plan de handoff

### Classification du changement

**Minor** — Implémentation directe par l'équipe dev, sans coordination PO/PM/Architecte nécessaire.

### Responsabilités

| Rôle | Action |
|------|--------|
| Dev Agent | Créer le fichier story `1-2-bis-*.md` via workflow `create-story` |
| Dev Agent | Implémenter la story 1.2-bis (PHP + JS) |
| Dev Agent | Mettre à jour `epics.md` avec la nouvelle story |
| Dev Agent | Mettre à jour `sprint-status.yaml` |
| Dev Agent | Retirer le code de diagnostic temporaire une fois les vraies clés identifiées |

### Critères de succès

- [ ] `getMqttManagerConfig()` retourne les bonnes valeurs sur une installation réelle avec mqtt2
- [ ] Le bouton "Récupérer depuis MQTT Manager" fonctionne et écrase les champs
- [ ] Les erreurs d'auto-détection sont affichées clairement (plugin absent, clés non trouvées)
- [ ] L'utilisateur peut réinitialiser le formulaire
- [ ] Le code de diagnostic temporaire est retiré
- [ ] Aucune régression sur le test de connexion MQTT (story 1.2)

### Prochaine action immédiate

Créer la story `1-2-bis` via : `/bmad-bmm-create-story`

---

*Généré par le workflow Correct Course — 2026-03-13*
