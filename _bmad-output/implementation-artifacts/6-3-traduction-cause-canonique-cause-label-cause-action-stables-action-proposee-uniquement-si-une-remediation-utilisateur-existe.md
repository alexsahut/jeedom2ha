# Story 6.3 : Traduction cause canonique → `cause_label` / `cause_action` stables — action proposée uniquement si une remédiation utilisateur existe

Status: done

<!-- Créée le 2026-04-21 — correct-course approuvé — séquencement 6.2 / 6.3 réaligné -->
<!-- 6.2 reste in-progress, 6.3 est la prochaine story requise -->

## Story

En tant qu'utilisateur de jeedom2ha,
je veux que chaque cause d'échec canonique du moteur soit traduite en un libellé stable et lisible, et qu'une action soit proposée uniquement lorsqu'une remédiation accessible par l'utilisateur existe — et lorsqu'il n'y en a pas, que le système le dise explicitement plutôt que de rester silencieux,
afin que le diagnostic soit toujours actionnable quand quelque chose peut être fait, et honnête quand rien ne peut l'être.

## Contexte / Objectif produit

### Séquencement et gate terrain ayant motivé cette story

La Story 6.2 a été exécutée comme amélioration UX pure de `cause_label` / `cause_action`. Son gate terrain réel du **2026-04-21** a conclu à un **NO-GO**. Le correct-course approuvé a retenu l'**Option 2 — re-séquencer 6.2 et 6.3** :

- 6.2 reste `in-progress` — son contrat story-level doit être réaligné ; aucun dev ne repart depuis 6.2
- 6.3 devient la **prochaine story requise** — elle porte la sémantique honnête `cause_label` / `cause_action` et la règle **no faux CTA**

Référence : `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-21.md`

### Problèmes terrain à absorber (résumé exécutif)

| Step pipeline visible | Constat terrain 2026-04-21 | Exigence story 6.3 |
|---|---|---|
| Step 3 (validation HA) | `cause_label` non clair — `cause_action` non comprise — compréhension > 60 s | `cause_label` doit expliquer l'invalidité HA ; `cause_action` = null — la contrainte relève de l'appareil physique, pas d'une configuration accessible à l'utilisateur |
| Step 4 (décision publication) | Décision perçue, mais action floue (faux CTA) | Aucun CTA du type "Choisir manuellement le type d'équipement" ne survit sans surface réelle et prouvée dans l'application |
| Step 2 (mapping) | Lecture rapide mais incohérence perçue entre "non supporté V1" et la promesse d'ouverture gouvernée | Le libellé ne doit pas laisser croire à une fermeture arbitraire du produit si le problème relève du mapping ou d'une gouvernance d'ouverture explicable |

### Cas terrain de référence (hérités de la story 6.1)

- **Step 3 réel** : `Garage / CHACON_porte-garage` (cmds `#2210-2212`) — `pipeline_step_visible = 3`
- **Step 4 réel** : `terrasse / lames pergola (virt)` (`eq_id 380`) — `pipeline_step_visible = 4`
- **Observation 6.1 / 6.2** : le libellé `Mapping ambigu` apparaissait sur les deux cas ; le stepper seul les distinguait

### Faux CTA identifié à éliminer dans le code existant

Dans `resources/daemon/models/cause_mapping.py`, le dictionnaire `CAUSE_MAPPING` (introduit par la story 6.2) contient :

```python
"ambiguous_skipped": {
    "step_4": {
        "label": "Plusieurs types possibles — décision non automatique",
        "action": "Choisir manuellement le type d'équipement",  # ← FAUX CTA — aucune surface n'existe
    },
}
```

**Ce faux CTA est le blocage principal identifié par le terrain pour step 4. Il doit être supprimé dans cette story.**

Le test `test_resolve_cause_ux_ambiguous_step_4` dans `test_story_6_2_contextual_cause_mapping.py` **valide actuellement ce faux CTA et doit être corrigé dans cette story** (il sera cassé intentionnellement par le fix).

### Objectif produit

Faire du diagnostic une surface **sémantiquement honnête**, où :

- `cause_label` est **toujours renseigné** — chaque équipement a une explication lisible par un humain
- `cause_action` **n'existe que si une remédiation utilisateur réelle existe** dans l'application jeedom2ha ou dans Jeedom
- lorsqu'aucune action directe n'est possible, `cause_action` est **null** et la couche d'affichage présente un message standardisé — pas de silence, pas de fausse promesse
- aucun faux CTA n'est autorisé à être déployé

---

## Scope

### In scope

- Révision de la **table de traduction backend** (`reason_code → cause_label / cause_action`) :
  - codes class 2 (invalidité HA) : `cause_action = null` — contrainte structurelle, l'utilisateur ne peut pas agir directement
  - code class 3 (scope produit) : `cause_action = null` — gouvernance de cycle, non arbitraire
  - causes step 2 (ambiguïté / absence de mapping) : `cause_label` clarifiant la nature du blocage parmi les trois catégories (impossibilité, ambiguïté, gouvernance de scope)
- Révision du **mapping contextuel par étape** pour les causes partagées entre steps :
  - éliminer tous les faux CTA (en particulier l'action step 4 pour les causes d'ambiguïté)
  - libellés distincts step 3 / step 4 pour les causes partagées — sans dépendre du stepper
- Mise à jour des tests existants qui valident actuellement un faux CTA
- Nouveau fichier de tests story 6.3 : `resources/daemon/tests/unit/test_story_6_3_honest_cause_mapping.py`
- Gate terrain "no faux CTA" bloquant avant done

### Out of scope

- Toute modification du pipeline backend (étapes 1 à 5)
- Toute création, suppression, inversion de sens ou renommage de `reason_code`
- Toute logique métier ou recontextualisation côté frontend (JS, PHP)
- Toute création de surface UI parallèle
- Toute refonte de la modal diagnostic existante
- Tout chantier de `projection_validity` dans `_build_traceability()` (périmètre 6.2)
- Ne pas clore la story 6.2 — elle reste `in-progress`

---

## Acceptance Criteria

### AC1 — `cause_label` toujours renseigné

**Given** 100 % des équipements exposés dans le diagnostic (`/system/diagnostics`)
**When** le champ `cause_label` est inspecté pour un équipement en écart `inclus / non publié`
**Then** `cause_label` n'est jamais `null` ni une chaîne vide
**And** le libellé est lisible par un humain non technique
_[Source : FR32, `epics-projection-engine.md` — Story 6.3 AC]_

---

### AC2 — Sémantique honnête pour les échecs de validation HA (step 3, class 2)

**Given** un équipement bloqué par une invalidité HA (codes de classe 2 : commande requise absente, état requis absent, champ obligatoire manquant, composant inconnu du moteur)
**When** l'utilisateur lit le diagnostic
**Then** `cause_label` exprime clairement l'invalidité HA (ex. "Projection HA incomplète — commande requise absente")
**And** `cause_action` est `null` — la contrainte relève de l'appareil physique, pas d'une configuration Jeedom accessible à l'utilisateur
_[Source : FR33, sprint-change-proposal-2026-04-21.md §3 Step 3, architecture-projection-engine.md D8]_

---

### AC3 — Sémantique honnête pour les refus de scope produit (step 4, class 3)

**Given** un équipement bloqué par la gouvernance de scope (composant HA connu mais non ouvert dans ce cycle)
**When** l'utilisateur lit le diagnostic
**Then** `cause_label` distingue la gouvernance d'ouverture du produit d'un problème de mapping
**And** `cause_action` est `null` — aucune configuration Jeedom ne peut résoudre ce blocage dans le cycle courant
**And** le libellé ne suggère pas une fermeture arbitraire du produit
_[Source : FR33, sprint-change-proposal-2026-04-21.md §3 Step 4]_

---

### AC4 — Règle de contrat `cause_action` : null si aucune remédiation utilisateur réelle, message standardisé à l'affichage

**Given** n'importe quel équipement en écart dans le diagnostic
**When** le champ `cause_action` est inspecté
**Then** si une remédiation utilisateur réelle existe (opération réalisable dans jeedom2ha ou Jeedom standard sans intervention du mainteneur ni modification de code), `cause_action` contient l'instruction correspondante
**And** si aucune remédiation utilisateur directe n'existe, `cause_action` est `null` — jamais un CTA fictif (ex. "Choisir manuellement le type d'équipement")
**And** la couche d'affichage présente un message standardisé du type "Aucune action utilisateur directe possible" pour tout `cause_action` null en contexte d'écart
_[Source : FR32, FR33, sprint-change-proposal-2026-04-21.md §3 Step 4, correct-course approuvé]_

---

### AC5 — Distinction step 2 / step 3 / step 4 par libellé, sans dépendre du stepper

**Given** deux équipements partageant le même `decision_trace.reason_code = ambiguous_skipped`
**And** l'un affiche `pipeline_step_visible = 3` et l'autre `pipeline_step_visible = 4`
**When** l'utilisateur lit le diagnostic de chacun
**Then** le `cause_label` visible n'est pas identique entre les deux cas
**And** le libellé step 3 exprime un problème de projection / validation technique (sans faux CTA)
**And** le libellé step 4 exprime un arbitrage de décision / publication (sans faux CTA)
**And** l'utilisateur peut distinguer les deux situations sans s'appuyer uniquement sur le stepper
_[Source : 6.2 story AC1, sprint-change-proposal §3 Step 3 / Step 4]_

---

### AC6 — Libellé step 2 : distinction explicite entre impossibilité de mapping, ambiguïté et limitation de scope

**Given** un équipement bloqué en step 2 selon l'une des trois catégories :
- **impossibilité de mapping** : aucun type HA reconnu pour les commandes présentes
- **ambiguïté de mapping** : plusieurs types HA possibles — le moteur ne peut pas trancher seul
- **limitation de scope produit** : type HA connu mais non ouvert dans ce cycle
**When** l'utilisateur lit le `cause_label` de chacun des trois cas
**Then** les trois libellés sont distincts et permettent de comprendre la nature du blocage sans consulter le stepper ni un log technique
**And** le libellé "limitation de scope" exprime la gouvernance d'ouverture de cycle — il n'induit pas que le produit a arbitrairement fermé ce type d'équipement
**And** le libellé "ambiguïté" exprime une configuration Jeedom à préciser — il ne porte un `cause_action` que si une surface réelle existe dans jeedom2ha pour agir
**And** le libellé "impossibilité" exprime l'absence de correspondance de mapping — il ne fait pas référence à une politique produit
_[Source : FR32, sprint-change-proposal-2026-04-21.md §3 Step 2, epics-projection-engine.md Story 6.3]_

---

### AC7 — Non-régression du contrat 4D et des invariants pipeline

**Given** le corpus de non-régression V1.1 et le corpus du cycle moteur de projection
**When** l'ensemble des tests de non-régression est exécuté après la livraison de la story
**Then** 0 `reason_code` existant n'est modifié, supprimé ou renommé
**And** le contrat 4D (`perimetre`, `statut`, `ecart`, `cause_code`, `cause_label`, `cause_action`, `traceability`) reste rétrocompatible
**And** les invariants I4, I7, I10 du `pipeline-contract.md` continuent de passer
**And** aucune logique métier nouvelle n'est introduite dans le frontend (JS/PHP)
_[Source : NFR7, NFR8, pipeline-contract.md I4 / I7 / I10, 6.2 story AC4 / AC5]_

---

### AC8 — Gate terrain "no faux CTA" bloquant avant done

**Given** un gate terrain réel sur box Jeedom couvrant au minimum :
- un cas `step 2` (mapping échoué : `no_supported_generic_type` ou `ambiguous_skipped`)
- un cas `step 3` (validation HA : `ha_missing_command_topic` ou équivalent — ex. CHACON_porte-garage)
- un cas `step 4` (décision de publication : `ha_component_not_in_product_scope` ou `ambiguous_skipped` step 4)
**When** un utilisateur lit le diagnostic sur la box réelle pour chacun de ces cas
**Then** aucun `cause_action` visible ne promet une action inexistante dans l'application
**And** `cause_label` est compréhensible en moins de 30 secondes pour chaque cas
**And** les cas step 3 et step 4 sont distinguables sans s'appuyer sur le stepper
**And** le résultat, la date, l'environnement et les `eq_id` observés sont documentés dans la story avant passage à `done`
_[Source : 6.2 story AC6, sprint-change-proposal-2026-04-21.md §4.2, correct-course approuvé]_

---

## Tasks / Subtasks

<!-- Story terrain détectée (box Jeedom / test terrain dans AC8 + Dev Notes) :
     Task 0 Pre-flight terrain injectée automatiquement en tête. -->

- [x] Task 0 — Pre-flight terrain (DEV/TEST ONLY — pas la release Market)
  - [x] Dry-run : vérifier sans transférer : `./scripts/deploy-to-box.sh --dry-run`
  - [x] Sélectionner le mode selon l'objectif de la story :
    - Vérification lecture diagnostic sans republier : `./scripts/deploy-to-box.sh --stop-daemon-cleanup`
    - Cycle complet republication + validation discovery : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Vérifier que le script se termine avec `Deploy complete.` ou `Stop+cleanup terminé.`

- [x] Task 1 — Réviser le mapping contextuel par étape — éliminer tous les faux CTA (AC: #4, #5)
  - [x] Identifier toutes les entrées du mapping contextuel contenant des faux CTA (en particulier l'action step 4 pour les causes d'ambiguïté)
  - [x] Remplacer tout CTA sans surface réelle par `null` — y compris "Choisir manuellement le type d'équipement"
  - [x] Réviser le libellé step 3 des causes d'ambiguïté : exprimer le problème structurel de projection, avec une `cause_action` non-null uniquement si l'utilisateur peut réellement configurer les commandes dans Jeedom
  - [x] Maintenir la cohérence entre les alias de reason_codes d'ambiguïté

- [x] Task 2 — Mettre à jour la table de traduction backend pour les codes class 2 (AC: #2)
  - [x] Codes d'invalidité HA (commande absente, état absent, champ obligatoire manquant) : `cause_action = null` — la contrainte relève de l'appareil physique, pas d'une configuration accessible à l'utilisateur
  - [x] Code composant inconnu du moteur : `cause_action` déjà null — vérifier que `cause_label` est explicite sur l'absence de support
  - [x] Vérifier l'alignement des `cause_label` class 2 avec la table de référence de l'architecture [Source: architecture-projection-engine.md §Reason codes proposés — classe 2]

- [x] Task 3 — Mettre à jour la table de traduction backend pour class 3 et causes step 2 (AC: #3, #6)
  - [x] Code scope produit : `cause_label` distingue la gouvernance d'ouverture du refus arbitraire ; `cause_action = null`
  - [x] Causes d'impossibilité et d'ambiguïté de mapping : réviser les `cause_label` pour que les trois catégories step 2 soient lisiblement distinctes (impossibilité / ambiguïté / gouvernance de scope)
  - [x] Pour les causes d'ambiguïté step 2 : `cause_action` peut être non-null si et seulement si l'utilisateur peut réellement corriger les types génériques dans Jeedom

- [x] Task 4 — Vérifier le contrat de sortie de la fonction pure de mapping UX (AC: #1, #4)
  - [x] S'assurer que le fallback retourne toujours un `cause_label` non-null et informatif
  - [x] Vérifier que `cause_action = null` est propagé proprement — jamais converti en CTA fictif par la fonction de lookup
  - [x] Vérifier que la couche d'affichage (JS) présente un message standardisé "Aucune action utilisateur directe possible" pour tout `cause_action` null en contexte d'écart — sans logique locale de mapping `reason_code → libellé`

- [x] Task 5 — Écrire la suite de tests story 6.3 et corriger les tests 6.2 cassés (AC: #1–#7)
  - [x] Créer `resources/daemon/tests/unit/test_story_6_3_honest_cause_mapping.py` couvrant :
    - AC1 : `cause_label` jamais null/vide pour tous les reason_codes actifs
    - AC2 : codes class 2 → `cause_action = null` (jamais une instruction supposant une action utilisateur possible)
    - AC3 : code class 3 → `cause_action = null`
    - AC4 : `cause_action` non-null uniquement si action réelle — jamais "Choisir manuellement le type d'équipement"
    - AC5 : libellés distincts entre step 3 et step 4 pour une même cause canonique
    - AC6 : les trois catégories step 2 produisent des libellés distincts
    - AC7 : non-régression des invariants pipeline (I4 / I7)
  - [x] **Mettre à jour le test existant validant le comportement step_4** : remplacer l'assertion faux CTA par le nouveau comportement attendu (`cause_action = null`)
  - [x] Vérifier que le corpus de non-régression global passe

- [x] Task 6 — Gate terrain "no faux CTA" bloquant (AC: #8)
  - [x] Déployer sur box Jeedom réelle via `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon`
  - [x] Valider sur un cas step 2 (mapping ambiguity ou no_supported_generic_type) : libellé non trompeur, action honnête
  - [x] Valider sur un cas step 3 (validation HA : CHACON_porte-garage ou équivalent) : libellé clarifie l'invalidité HA, aucun faux CTA
  - [x] Valider sur un cas step 4 (décision publication : lames pergola ou ha_component_not_in_product_scope) : libellé distingue la gouvernance, aucun faux CTA
  - [x] Documenter dans la section **Completion Notes** de la story : date, environnement, eq_id / cas observés, verdict, éventuelles limites explicites
  - [x] Gate bloquant : si un seul faux CTA est encore visible sur la box, la story reste `in-progress`

### Review Follow-ups (AI) — 2026-04-22

Issus du code review 6.3. Les points doc/process et faibles ont été corrigés directement (File List, Dev Notes, apostrophes, header artefact, test AC3, DoD). Un seul point reste ouvert en décision produit.

- [ ] [AI-Review][M3][OPEN-DECISION] `resources/daemon/transport/http_server.py:1946-1950` — incohérence potentielle entre `cause_code` (issu de `reason_code` legacy) et `cause_label / cause_action` (issus de `decision_reason_code` canonique). Détail et proposition dans le bloc **M3 — Point de décision produit** ci-dessous.

---

## Dev Notes

### Architecture des fichiers à toucher

| Fichier | Type de modification | Justification |
|---|---|---|
| `resources/daemon/models/cause_mapping.py` | Modification (correction) | Source unique des traductions `reason_code → cause_label / cause_action` — toutes les corrections sont ici |
| `resources/daemon/tests/unit/test_story_6_3_honest_cause_mapping.py` | Création | Nouveau fichier de tests story 6.3 |
| `resources/daemon/tests/unit/test_story_6_2_contextual_cause_mapping.py` | Modification (correction) | Le test `test_resolve_cause_ux_ambiguous_step_4` valide actuellement un faux CTA — **doit être corrigé** |

**Ne PAS toucher :**
- `core/ajax/jeedom2ha.ajax.php` (passthrough strict)
- `resources/daemon/validation/ha_component_registry.py` (hors scope)
- Tout autre module du pipeline (étapes 1–5 intactes)

**Contrats à préserver (modifications ciblées autorisées) :**
- `resources/daemon/transport/http_server.py` : **signature** de `resolve_cause_ux()` inchangée ; câblage ponctuel dans `_handle_system_diagnostics` autorisé pour consommer la sortie du mapping corrigé (cause_label / cause_action lus depuis `resolve_cause_ux(decision_reason_code, pipeline_step_visible)`).
- `desktop/js/jeedom2ha.js` et `desktop/js/jeedom2ha_diagnostic_helpers.js` : **aucune logique métier locale** de mapping `reason_code → libellé`. Seul le message standardisé AC4 ("Aucune action utilisateur directe possible") est autorisé côté rendu, et la suppression des fallbacks locaux (legacyReasonLabels, remediation, commandTabReasonCodes) est attendue pour aligner la lecture sur le backend.

**Note de review 6.3 :** La version initiale des Dev Notes listait `http_server.py` et les helpers JS comme "ne pas toucher", ce qui entrait en contradiction avec l'AC4 (message JS standardisé) et le besoin de câbler `resolve_cause_ux()` côté endpoint. Section clarifiée le 2026-04-22 après code review.

### Points d'entrée dans le code existant

Le module de mapping de causes (`resources/daemon/models/cause_mapping.py`) expose trois niveaux de contrat à aligner :

1. **Table de traduction backend** : traduit chaque `reason_code` en `(cause_code, cause_label, cause_action)`. Corrections ciblées sur les codes class 2, class 3 et les causes d'ambiguïté step 2. Aucune clé de la table n'est supprimée ni renommée.

2. **Mapping contextuel par étape** : traduit `(cause_canonique, step_pipeline)` en `(label, action)` pour les causes partagées entre plusieurs steps. Introduit par la story 6.2 — les faux CTA se trouvent ici.

3. **Fonction pure de mapping UX** : entrée `(reason_code, pipeline_step)`, sortie `{cause_label, cause_action}`. La signature et le rôle restent inchangés ; seul le contenu des tables est corrigé.

Le handler HTTP consomme la sortie de cette fonction sans la modifier — il ne doit pas être touché.

### Contrat de sortie attendu après implémentation

| Reason code | pipeline_step | cause_label | cause_action attendu |
|---|---|---|---|
| `ambiguous_skipped` | 2 | "Mapping ambigu — plusieurs types possibles" | Action réelle si configurable dans Jeedom, sinon null |
| `ambiguous_skipped` | 3 | Libellé exprimant la contrainte structurelle de projection | Action réelle si configurable dans Jeedom, sinon null |
| `ambiguous_skipped` | 4 | Libellé exprimant l'arbitrage de décision / publication | **null** — aucune surface dans l'application |
| `ha_missing_command_topic` | 3 | "Projection HA incomplète — commande requise absente" | **null** |
| `ha_missing_state_topic` | 3 | "Projection HA incomplète — état requis absent" | **null** |
| `ha_missing_required_option` | 3 | "Projection HA incomplète — champ obligatoire manquant" | **null** |
| `ha_component_unknown` | 3 | "Type d'entité HA inconnu du moteur" | **null** |
| `ha_component_not_in_product_scope` | 4 | Libellé gouvernance explicable (non arbitraire) | **null** |
| `no_supported_generic_type` | 2 | Libellé distinguant absence de mapping et gouvernance de scope | null ou action réelle selon l'arbitrage Task 3 |

### Règle de contrat `cause_action` — décision tranchée

**Backend** : `cause_action = null` lorsqu'aucune remédiation utilisateur directe n'existe. Cette règle est unique et non optionnelle — pas de constante textuelle de fallback dans les données.

**Couche d'affichage (JS)** : lorsque `cause_action` est null et que l'équipement présente un écart, l'interface affiche un message standardisé du type _"Aucune action utilisateur directe possible"_. Cette logique d'affichage est vérifiée dans Task 4 — sans y introduire de mapping local `reason_code → libellé`.

**Règle de décision** : une action ne peut être non-null que si l'utilisateur peut réellement la réaliser dans jeedom2ha ou Jeedom standard, sans intervention du mainteneur, sans modification de code, sans attendre une release. En cas de doute → null.

### Intelligence tirée de la Story 6.2 (learnings terrain)

- Le faux CTA le plus impactant : `"Choisir manuellement le type d'équipement"` dans `CAUSE_MAPPING["ambiguous_skipped"]["step_4"]["action"]` — il n'y a pas de surface dans jeedom2ha pour choisir manuellement le type HA
- Pour CHACON_porte-garage (step 3) : l'équipement a des commandes (`#2210-2212`) mais le mapping produit une projection HA invalide ; l'utilisateur ne peut pas ajouter une commande manquante à un appareil physiquement contraint
- Pour lames pergola (step 4, `eq_id 380`) : la décision de publication est refusée ; l'action "choisir le type" n'a pas de surface réelle dans l'application
- Le prototype 6.2 est un **référentiel négatif** (ce qui NE FONCTIONNE PAS), pas un point de départ à consolider

### Git Intelligence Summary

- Dernier commit feature terrain : `0cb3988` — `feat(pe-6.1): diagnostic par étape pipeline + separation step5 failed (#98)` — pose les fondations réutilisées
- Dernier commit de closeout : `3f11eea` — `chore(bmad): close story 6.1 after merge and set tracker done (#99)`
- L'implémentation 6.2 est en `main` (CAUSE_MAPPING + resolve_cause_ux déjà en place) — la story 6.3 corrige le contenu, pas l'architecture de la fonction

### Fondations opposables (ne pas remettre en cause)

- La cause canonique principale provient de `traceability.decision_trace.reason_code` — immuable
- Le pipeline canonique reste strictement ordonné : `1 → 2 → 3 → 4 → 5` — immuable
- `cause_mapping.py` reste l'unique endroit autorisé pour traduire `reason_code → (cause_code, cause_label, cause_action)` — immuable
- L'invariant **I7** est non négociable : `technical_reason_code` n'alimente jamais la cause principale
- L'invariant **I4** est non négociable : cause principale = premier échec dans l'ordre pipeline
- **NFR8** : 0 `reason_code` historique ne doit être renommé, supprimé ou voir son sens inversé

### Dev Agent Guardrails

- **Règle absolue** : si vous ne trouvez pas de surface réelle dans l'application pour une action proposée, l'action est `None`
- **Règle absolue** : ne pas toucher au fichier `http_server.py` — le contrat de `resolve_cause_ux()` reste `(reason_code: str, pipeline_step: int) -> Dict[str, str]`
- **Règle absolue** : ne pas modifier les clés de `_REASON_CODE_TO_CAUSE` — uniquement les valeurs des tuples `cause_label` et `cause_action`
- **Règle absolue** : ne pas refermer la story 6.2 — elle reste `in-progress`
- **Anti-pattern interdit** : introduire une logique conditionnelle métier dans `resolve_cause_ux()` au-delà d'une table de lookup + fallback
- **Anti-pattern interdit** : ajouter de la logique cause dans `core/ajax/jeedom2ha.ajax.php` ou dans le JS

### Guardrail — Déploiement terrain (DEV/TEST ONLY)

- Utiliser **exclusivement** `scripts/deploy-to-box.sh` pour tout test sur la box Jeedom réelle
- Ne jamais improviser de rsync ad hoc, copie SSH manuelle ou procédure parallèle
- Référence complète modes + cycle validé terrain :
  `_bmad-output/implementation-artifacts/jeedom2ha-test-context-jeedom-reel.md`
- Cycle canonique (NON remplacé par le script) : `main → beta → stable → Jeedom Market`

### Project Structure Notes

- `resources/daemon/models/cause_mapping.py` — module pur, standalone, sans dépendance sur `http_server`, `aggregation`, `taxonomy`
- `resources/daemon/tests/unit/` — répertoire de tests unitaires du daemon ; nommer `test_story_6_3_*.py`
- Le commentaire `# ARTEFACT FIGÉ — Story 4.1 / Story 4.3` en tête de `cause_mapping.py` doit être mis à jour pour mentionner story 6.3 après implémentation

### References

- [Source: `_bmad-output/planning-artifacts/epics-projection-engine.md` — Story 6.3, Feature 6, FR32, FR33]
- [Source: `_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-21.md` — §4.2 Pull forward 6.3, §3 Step 2/3/4]
- [Source: `_bmad-output/implementation-artifacts/6-2-diagnostic-enrichissement-cause-et-actions-l-utilisateur-comprend-clairement-le-probleme-et-comment-le-corriger.md` — Contexte terrain, faux CTA identifiés]
- [Source: `_bmad-output/planning-artifacts/pipeline-contract.md` — I4, I7, I10]
- [Source: `_bmad-output/planning-artifacts/architecture-projection-engine.md` — AR11, D8, §Reason codes proposés — classe 2 / classe 3]
- [Source: `resources/daemon/models/cause_mapping.py` — code existant à corriger]
- [Source: `resources/daemon/tests/unit/test_story_6_2_contextual_cause_mapping.py` — test à corriger]

---

## Definition of Done

- [x] Table de traduction backend : `cause_action = null` pour tous les codes class 2 et class 3 — aucune action fictive _(test_ac2_*, test_ac3_*)_
- [x] Mapping contextuel par étape : aucun faux CTA — `cause_action = null` pour les steps sans remédiation utilisateur réelle _(test_ac4_*)_
- [x] `cause_label` jamais null pour 100 % des reason_codes actifs _(test_ac1_*)_
- [x] Les trois catégories step 2 (impossibilité de mapping, ambiguïté, gouvernance de scope) produisent des libellés distincts _(test_ac6_three_step2_categories_have_distinct_labels)_
- [x] Test existant validant le faux CTA step_4 corrigé (`cause_action = null` attendu) _(test_resolve_cause_ux_ambiguous_step_4)_
- [x] Suite de tests story 6.3 créée — tous les cas verts _(resources/daemon/tests/unit/test_story_6_3_honest_cause_mapping.py)_
- [x] Corpus de non-régression global passe _(1105 pytest + 198 node PASS post-corrections review)_
- [x] Gate terrain "no faux CTA" documenté dans Completion Notes avec date, eq_id et verdict PASS _(2026-04-22, box 192.168.1.21, cas step 2/3/4)_
- [x] Code review — M1/M2/L1/L2/L4/L5 corrigés ; **M3 déclassé en follow-up non bloquant** (voir Review Follow-ups)
- [x] Story 6.2 reste `in-progress` — non close _(cf. sprint-status.yaml)_

---

## Dev Agent Record

### Agent Model Used

Claude Sonnet 4.6

### Debug Log References

### Completion Notes List

**Gate terrain "no faux CTA" — 2026-04-22**
- Environnement : box Jeedom réelle 192.168.1.21, daemon port 55080, post-sync 30/278 publiés
- Déploiement : `./scripts/deploy-to-box.sh --cleanup-discovery --restart-daemon` → `Deploy complete.`
- **Cas step 2** : eq_id=587 `Iphone Alex`, reason_code=`no_supported_generic_type`
  - cause_label=`"Types génériques Jeedom hors périmètre du cycle courant"` — lisible, no V1
  - cause_action=`null` ✓ — aucun faux CTA
- **Cas step 3** : eq_id=287 `CHACON_porte-garage`, reason_code=`ambiguous_skipped`
  - cause_label=`"Projection HA structurellement incomplète — ambiguïté de mapping non résolue"` ✓
  - cause_action=`"Préciser les types génériques sur les commandes dans Jeedom pour lever l'ambiguïté"` ✓ — action réelle dans Jeedom
- **Cas step 4** : eq_id=380 `lames pergola (virt)`, reason_code=`ambiguous_skipped`
  - cause_label=`"Arbitrage de publication non automatique — ambiguïté de mapping non résolue"` ✓
  - cause_action=`null` ✓ — aucun faux CTA
- **Verdict** : PASS — aucun faux CTA détecté sur 278 équipements
- **Limite** : `ha_component_not_in_product_scope` absent du dataset terrain (aucun composant HA reconnu hors-scope dans la configuration actuelle). Couvert par tests unitaires AC3 (152 PASS).
- **Suite de tests** : 595 pytest PASS + 198 node PASS + 0 régression

### File List

**Backend — moteur de traduction cause**
- `resources/daemon/models/cause_mapping.py` (modifié — table 6.3 honnête, CAUSE_MAPPING contextuel, header artefact figé actualisé, apostrophes harmonisées)
- `resources/daemon/transport/http_server.py` (modifié — câblage `resolve_cause_ux(decision_reason_code, pipeline_step_visible)` dans `_handle_system_diagnostics`, signature de `resolve_cause_ux()` inchangée)

**Tests backend**
- `resources/daemon/tests/unit/test_story_6_3_honest_cause_mapping.py` (créé — couverture AC1–AC7)
- `resources/daemon/tests/unit/test_story_6_2_contextual_cause_mapping.py` (créé — tests contextuels 6.2 alignés sur sémantique 6.3, faux CTA supprimé)
- `resources/daemon/tests/unit/test_cause_mapping.py` (modifié — snapshot et libellés class 2/3 alignés sur 6.3)
- `resources/daemon/tests/unit/test_diagnostic_endpoint.py` (modifié — assertions endpoint alignées sur cause_label/cause_action 6.3)

**Frontend — lecture stricte backend**
- `desktop/js/jeedom2ha.js` (modifié — suppression `reasonLabels` local + fallback `remediation` + `commandTabReasonCodes` ; message AC4 "Aucune action utilisateur directe possible")
- `desktop/js/jeedom2ha_diagnostic_helpers.js` (modifié — retrait du paramètre `legacyReasonLabels` de `getDiagnosticReasonLabel`, retrait fallback `remediation` dans `resolveDiagnosticAction`)

**Tests frontend**
- `tests/unit/test_story_6_3_honest_cause_mapping.node.test.js` (créé — AC1/AC4 frontend)
- `tests/unit/test_story_6_2_frontend_backend_first.node.test.js` (créé — guardrail backend-first)
- `tests/unit/test_story_3_2_reason_labels_sync.py` (modifié — ancien guard AI-3 sur `reasonLabels` remplacé par le guard "pas de mapping local")
- `tests/unit/test_story_4_2_diagnostic_decision.node.test.js` (modifié — suppression du paramètre `legacyReasonLabels` dans les assertions 4.2)

**Planning / tracking**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modifié)
- `_bmad-output/planning-artifacts/epics-projection-engine.md` (modifié)

> **Note review 2026-04-22** : périmètre élargi à l'ensemble du diff uncommitted — inclut les fichiers hérités de Story 6.2 (toujours `in-progress`) qui atterrissent naturellement avec 6.3, car 6.3 corrige le contenu d'un outillage dont le câblage endpoint + la purge frontend ont été amorcés par 6.2.

### Change Log

- 2026-04-22 — Implémentation Story 6.3 : sémantique honnête cause_label/cause_action — suppression faux CTA, cause_action=None class 2+3, révision libellés, message standardisé JS, gate terrain PASS
- 2026-04-22 — Code review : corrections M1 (File List complet), M2 (Dev Notes clarifiées), L1 (apostrophes harmonisées), L2 (DoD cochée), L4 (header artefact figé mentionne 6.2 + 6.3), L5 (test AC3 durci — exclusion explicite des connotations mapping). M3 isolé en follow-up non bloquant (voir bloc ci-dessous). 1105 pytest + 198 node PASS post-corrections.

---

## M3 — Point de décision produit (isolé du code review 6.3)

**Contexte**
Dans `resources/daemon/transport/http_server.py`, section `_handle_system_diagnostics`, le bloc qui remplit le contrat 4D pour un équipement `inclus / non_publié` mélange deux sources de `reason_code` :

```python
cause_code, _, _ = reason_code_to_cause(reason_code)                      # reason_code legacy
cause_ux = resolve_cause_ux(decision_reason_code, pipeline_step_visible)  # decision_trace.reason_code canonique
cause_label = cause_ux["cause_label"]
cause_action = cause_ux["cause_action"]
```

`cause_code` est dérivé du `reason_code` legacy ; `cause_label` et `cause_action` sont dérivés du `decision_reason_code` issu de `traceability.decision_trace`. En régime nominal ils sont identiques — mais le code n'exprime ni n'impose cette contrainte.

**Impact réel du risque**
- **Fréquence observée** : 0 divergence sur le gate terrain 2026-04-22 (278 équipements, box réelle) ni sur 1105 pytest + 198 node.
- **Scénario de divergence** : cas où `reason_code` (legacy, calculé tôt pour le modèle 4D) et `decision_trace.reason_code` (canonique, résolu en fin de pipeline) pointent vers des causes différentes — par exemple si un futur enrichissement du moteur fait diverger la vue taxonomique de la vue pipeline.
- **Symptôme utilisateur** : un `cause_code` désignant la cause X accompagné d'un `cause_label / cause_action` décrivant Y. Incohérence visible uniquement par l'utilisateur qui croiserait export machine et UI. Invariant **I4** (cause unique = premier échec pipeline) resterait respecté côté UI ; seule la cohérence interne 4D est en jeu.
- **Classe de risque** : dette latente, non régressive sur la sémantique utilisateur courante. Aucun faux CTA n'en résulterait (M3 ne contredit pas l'objectif 6.3). 

**Proposition minimale de correction**
Aligner `cause_code` sur la même source canonique que `cause_label / cause_action`, sans toucher aux contrats ni introduire de logique métier :

```python
cause_code, _, _ = reason_code_to_cause(decision_reason_code or reason_code)
cause_ux = resolve_cause_ux(decision_reason_code, pipeline_step_visible)
cause_label = cause_ux["cause_label"]
cause_action = cause_ux["cause_action"]
```

- `decision_reason_code or reason_code` : fallback sur le legacy si le canonique est vide — conserve le comportement actuel sur les flux qui n'émettent pas encore de `decision_trace.reason_code`.
- Accompagné d'un test dédié (assertion que `cause_code`, `cause_label` et `cause_action` dérivent du même reason_code dans `/system/diagnostics`).
- Périmètre estimé : 1 ligne de code + 1 test d'invariant — ~30 minutes.

**Classification proposée : follow-up Epic 6 (rétrospective), pas follow-up 6.3**
Raisonnement :
1. **Pas un prérequis de 6.3** — l'AC de la story porte sur la sémantique de `cause_label / cause_action`, pas sur l'alignement de `cause_code`. Corriger M3 dans 6.3 dépasse son scope narratif.
2. **Pas un bug régressif** — le comportement d'avant 6.3 avait déjà ce mélange (`cause_code` et `cause_label` tous deux dérivés de `reason_code` legacy). 6.3 a bougé `cause_label/action` vers le canonique, ce qui a **exposé** la dette mais ne l'a pas créée.
3. **Pas un bloqueur terrain** — gate terrain PASS ; aucun utilisateur n'est actuellement affecté.
4. **Dette de gouvernance contractuelle** — cohérente avec l'axe rétro `pe-epic-6` : formaliser la source canonique unique pour les trois champs `cause_*` dans le contrat 4D.

**Recommandation** : créer un action item dans la rétrospective `pe-epic-6` avec le libellé *"Aligner cause_code sur decision_reason_code canonique dans http_server.py pour supprimer la dette d'incohérence latente 4D — proposition dans story 6.3"*.

**Décision attendue de ta part, Alexandre** : valider follow-up rétro Epic 6 (par défaut) **ou** rapatrier dans 6.3 avant merge.
