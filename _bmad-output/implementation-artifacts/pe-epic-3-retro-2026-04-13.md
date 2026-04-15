# Rétrospective pe-epic-3 — Validation HA obligatoire + registre gouverné à 3 états

**Date :** 2026-04-13
**Cycle actif :** Moteur de Projection Explicable
**Epic :** pe-epic-3 — Deux sous-capacités distinctes : la validation HA est obligatoire avant publication, et le registre gouverne l'ouverture des composants
**Statut de l'epic :** `done` dans `sprint-status.yaml`
**Statut rétrospective :** clôturée
**Participants :** Alexandre (Project Lead), Bob (Scrum Master), Alice (Product Owner), Winston (Architect), Charlie (Senior Dev), Dana (QA Engineer)

---

## Résumé de livraison

### Stories clôturées

| Story | Description | Agent | Statut | Gate terrain |
|---|---|---|---|---|
| 3.1 | Registre HA — module validation/ avec HA_COMPONENT_REGISTRY et PRODUCT_SCOPE | Codex (GPT-5) | done | N/A |
| 3.2 | Validation HA — fonction pure validate_projection() | Claude Sonnet 4-6 | done | N/A |
| 3.3 | Gouvernance d'ouverture — cadre FR40 avec verrou CI | Claude Sonnet 4-6 | done | N/A |

### Métriques finales

- Stories complétées : **3/3** (100%)
- Tests : 337 → 365 (+28 tests dans l'epic), **0 régression**
- PRs mergées : #81 (3.1), #83 (3.2), #84 (3.3) — toutes squash-merged
- Gate terrain : **N/A** — epic backend pur
- Durée : ~3 jours (2026-04-10 → 2026-04-13)
- Blockers : **0**
- Fichiers de production modifiés hors scope : **0**

### Code review findings

| Story | Finding | Type | Statut |
|---|---|---|---|
| 3.2 | M1 — fallback reason_code retournait le nom brut de capability au lieu d'un code métier | Bug fonctionnel | Corrigé |
| 3.2 | R1 — test d'intégrité registre manquant (capabilities → reason mapping) | Renforcement | Ajouté |
| 3.2 | M2 — type annotation `capabilities: object` au lieu de `MappingCapabilities` (D4) | Déviation documentée | Documenté, dette vivante |
| 3.3 | `_GOVERNED_SCOPE` restructuré de set → dict (lien explicite composant → preuve) | Amélioration de design | Corrigé |
| 3.3 | Documentation des 3 conditions FR40 avec enforcement dans `_GOVERNED_SCOPE` | Documentation | Ajouté |

---

## Continuité avec la rétro Epic 5 (V1.1, 2026-04-09)

Première rétrospective du cycle Moteur de Projection Explicable. pe-epic-1 et pe-epic-2 n'ont pas eu de rétro (marquées `optional`).

| Action item Epic 5 | Engagement | Statut dans pe-epic-3 |
|---|---|---|
| AI-1 — Flux système opérationnel externalisé | Externaliser le modèle mental du flux complet | ⏳ Avancé — modèle clarifié côté architecture produit, mais pas encore externalisé sous forme d'artefact unique partageable |
| AI-2 — Effets plateforme Jeedom documentés | Recenser les comportements Jeedom hors périmètre | ⏳ Avancé — conscience du sujet présente, savoir partiellement passé dans la pratique, mais pas encore figé en artefact canonique |
| AI-3 — Modèle canonique du moteur de projection | Prérequis absolu avant le prochain cycle | ✅ Complété — `architecture-projection-engine.md` formalise le pipeline à 5 étapes, les classes d'échec, le registre HA, la frontière Jeedom/HA |

**Bilan :** AI-3 a été le socle structurant du cycle PE. AI-1 et AI-2 sont devenus plus urgents qu'anticipé — AI-1 en particulier est un prérequis concret pour pe-epic-4.

---

## Ce qui a bien marché

### 1. Découpage pipeline exemplaire

Les trois stories correspondent aux trois états du registre HA : `connu` (3.1), `validable` (3.2), `ouvert` (3.3). Ce n'est pas un hasard : c'est le reflet d'une architecture bien conçue en amont. Le pipeline à 5 étapes posé en AI-3 porte ses fruits — chaque story consolide une frontière du pipeline sans empiéter sur les autres.

### 2. Timing de cycle optimal

pe-epic-3 s'est exécuté au bon moment : après le modèle canonique, avant la décision de publication explicite. Résultat : `PRODUCT_SCOPE`, `ProjectionValidity`, `validate_projection()` et le cadre FR40 sont maintenant des faits établis pour pe-epic-4, pas des hypothèses floues.

### 3. Discipline de scope irréprochable

Zéro blocker, zéro dérive hors sujet, zéro fichier de production modifié hors scope. Chaque story a explicitement documenté ses frontières (y compris les fichiers "hors scope"). Le résultat est un enrichissement purement additif : +28 tests, 0 régression, contrat 4D intact.

### 4. Code review efficace et structurante

La code review a attrapé un vrai bug fonctionnel (M1 — fallback reason_code), amélioré un design (dict vs set pour `_GOVERNED_SCOPE`), et renforcé le système (test d'intégrité registre R1). Le filet de sécurité fonctionne.

### 5. Exécution multi-agent fluide

GPT-5 pour la story de données (3.1), Claude Sonnet 4-6 pour les stories de logique (3.2, 3.3). Pas de friction aux points de handoff — chaque agent a trouvé le travail de son prédécesseur directement exploitable.

---

## Ce qui a été difficile

### 1. Déviation de type M2

`validate_projection()` accepte `capabilities: object` au lieu du type contractuel `MappingCapabilities` (D4). Choix pragmatique : le type Union ne peut pas accepter les doubles de test pour les composants connus mais non ouverts (`sensor`, `select`). L'architecture reconnaît le problème dans ses "Points ouverts #1". C'est de la dette contenue mais réelle.

### 2. Spécifications insuffisantes aux frontières des contrats

Les erreurs détectées en review (M1, `_GOVERNED_SCOPE`) ont un point commun : ce ne sont pas des erreurs dans le cœur de la logique, ce sont des erreurs aux **frontières** du contrat — les zones de traduction entre étapes. Les cas limites, reason_codes de bord et comportements interdits restent implicites dans les stories.

### 3. Dépendance structurelle à la code review pour les bords

La code review a parfaitement joué son rôle. Mais le risque est de commencer à en dépendre pour détecter des sujets qui devraient être contractuels dès la story. Le système de qualité fonctionne, mais par filet de sécurité, pas par construction.

---

## Cause racine synthétique

Les contrats entre étapes du pipeline sont explicites et bien testés. Les contrats **aux bords** de chaque étape — cas limites, valeurs de bord, comportements interdits — restent encore implicites, portés par le modèle mental des développeurs et attrapés par la code review plutôt que spécifiés et testés par construction.

---

## Enseignements clés

1. **La discipline de scope et l'enrichissement additif sont les piliers de la qualité du cycle** — le pattern d'isolation par étape, sans modification de fichiers hors scope, produit un système prévisible et testable.

2. **Les erreurs ont migré du centre vers les bords des contrats** — c'est un signal de maturité du pipeline. Mais il faut adapter les spécifications et les tests à cette nouvelle réalité.

3. **Les tests "anti-contrat" sont la couche manquante** — tester ce que le système DOIT interdire, pas seulement ce qu'il doit produire. Chaque règle critique doit avoir son test négatif.

4. **Le système est solide localement mais il manque une représentation globale partagée** — AI-1 (flux système externalisé) est devenu un prérequis concret pour pe-epic-4, pas un nice-to-have pour plus tard.

---

## Action items

### AI-1 — Artefact pipeline partagé (solder AI-1 rétro Epic 5)

**Owner :** Winston (Architect) + Alexandre
**Timing :** avant création de la première story pe-epic-4
**Critère de succès :** document dans `_bmad-output/planning-artifacts/` décrivant pour chaque étape du pipeline : entrée, sortie, invariants, reason_codes possibles, et la règle de cause principale canonique. Lisible en 5 minutes. Tout développeur ou testeur peut aligner son modèle mental dessus.
**Condition :** prérequis absolu avant lancement pe-epic-4.

### AI-2 — Checkpoint contrat `cause_mapping.py` avant Story 4.3

**Owner :** Charlie (Senior Dev) + Winston
**Timing :** avant démarrage de Story 4.3
**Critère de succès :** mini-document ou section dans les dev notes de Story 4.3 explicitant : (a) codes existants et statut non-négociable, (b) règle d'ajout additif, (c) comportements interdits (renommage, inversion, suppression), (d) tests de non-régression obligatoires pour toute modification.

### AI-3 — Qualifier Story 4.2 : backend-only ou surface critique

**Owner :** Alice (Product Owner) + Alexandre
**Timing :** avant création de Story 4.2
**Critère de succès :** décision documentée — soit "backend-only : pas d'artefact visuel ni gate terrain", soit "surface critique : artefact visuel prescriptif + gate terrain obligatoires".

### AI-4 — Documenter M2 comme dette vivante + non-aggravation

**Owner :** Charlie (Senior Dev)
**Timing :** immédiat
**Critère de succès :** M2 documenté avec : (a) nature de la déviation (`capabilities: object` vs `MappingCapabilities`), (b) périmètre d'impact actuel (contenu dans `validate_projection()`), (c) condition de déclenchement du réalignement (ouverture d'un nouveau composant FR40 avec dataclass dédiée), (d) vérification que les stories 4.x ne propagent pas le trou de typage au-delà de `validate_projection()`.

### AI-5 — Spécifier les bords du contrat dans les stories pe-epic-4

**Owner :** Bob (Scrum Master)
**Timing :** intégré dans la création de chaque story pe-epic-4
**Critère de succès :** chaque story critique (4.1, 4.3, 4.4 au minimum) inclut dans ses dev notes : cas limites obligatoires, reason_codes attendus, comportements interdits, et au moins un test "anti-contrat" par règle critique.

---

## Analyse des changements significatifs

**Aucun changement significatif détecté.** Les fondations livrées par pe-epic-3 correspondent exactement à ce que pe-epic-4 attend. Le plan de pe-epic-4 reste valide tel que défini. Les action items portent sur les conditions de préparation, pas sur le contenu des stories.

---

## Évaluation de readiness pe-epic-3

| Dimension | Statut | Note |
|---|---|---|
| Stories 3/3 | ✅ Solide | 100% complétées, 0 blocker |
| Tests 365/365 | ✅ Solide | +28 tests, 0 régression, isolation par étape |
| PRs mergées | ✅ Propre | Historique traçable, squash-merge |
| Acceptance stakeholders | ✅ N/A | Epic backend pur |
| Gate terrain | ✅ N/A | Pas de composant UI |
| Dette technique | 🟡 Documentée | M2 contenu, action item posé |
| Démarrage pe-epic-4 | ⏸️ Conditionnel | 4 prérequis de préparation |

---

## Chemin critique

1. **Produire AI-1** — artefact pipeline partagé (prérequis absolu pe-epic-4)
2. **Qualifier AI-3** — Story 4.2 backend-only ou surface critique
3. **Produire AI-2** — checkpoint contrat `cause_mapping.py` (avant Story 4.3)
4. **Documenter AI-4** — M2 dette vivante (immédiat)
5. **Lancer pe-epic-4** quand les 4 prérequis sont validés

---

## Message de clôture

pe-epic-3 laisse le projet dans une bonne position : le socle est propre, les dépendances de pe-epic-4 sont en place, et les risques restants sont nommés, bornés et actionnables. Le cycle ne ralentit pas parce qu'on doute du fond — on prend un temps court de préparation parce qu'on veut garder la qualité du cycle en montant d'un cran en complexité.

---

**Date de révision :** 2026-04-13
**Cycle :** Moteur de Projection Explicable — pe-epic-3 clôturé, pe-epic-4 en préparation
