# Gate d’alignement pre-go/no-go — pe-epic-5

**Date :** 2026-04-16  
**Projet :** jeedom2ha  
**Cycle :** Moteur de Projection Explicable  
**Epic ciblé :** `pe-epic-5`

## 1. Objet du gate

Valider (ou refuser) le démarrage de `pe-epic-5` sur base de pilotage, conformément à la décision de rétro `pe-epic-4` : pas de démarrage sans preuve d’alignement explicite et partageable.

## 2. Intention dominante du cycle

Formulation de référence (rétro `pe-epic-4`) :

> Ouvrir tout composant HA proprement mappable, structurellement validable et non bloqué par une exception de gouvernance explicitement décidée, justifiée et tracée.

## 3. Référentiel contrôlé

Artefacts revus :
- `_bmad-output/implementation-artifacts/pe-epic-4-retro-2026-04-15.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture-projection-engine.md`
- `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md`
- `_bmad-output/planning-artifacts/pipeline-contract.md`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`

## 4. Check d’alignement

### 4.1 Rétro ↔ PRD

**Statut : ALIGNÉ**

- La rétro impose une ouverture par défaut conditionnée par validité structurelle + gouvernance explicite tracée.
- Le PRD final confirme :
  - pas de liste fermée arbitraire,
  - ouverture fondée sur registre + validation + testabilité,
  - FR37/FR38/FR39/FR40 cohérents avec cette direction.

### 4.2 PRD ↔ Architecture

**Statut : PARTIELLEMENT ALIGNÉ (AMBIGU)**

- `architecture-delta-review-prd-final.md` ferme explicitement l’item 14 (FR39/FR40) et recadre `PRODUCT_SCOPE` en mode `governed-open`.
- `architecture-projection-engine.md` contient encore des formulations pouvant être lues comme une base scope fixe V1.x et des "décisions encore ouvertes".

**Conclusion contrôle :** alignement réel présent, mais lisibilité de référence encore ambiguë si la préséance du delta n’est pas explicitée dans le pilotage.

### 4.3 Architecture ↔ Epics / Tracker

**Statut : ALIGNÉ SOUS BLOQUAGE DE GATE**

- `epics-projection-engine.md` cadre `pe-epic-5` sur FR26–FR30, cohérent avec le pipeline.
- Le tracker maintient `pe-epic-5` en `backlog` avec blocage gate d’alignement.

## 5. Exceptions de gouvernance actives

**Statut : NON CONFORME (TRACABILITÉ INSUFFISANTE)**

- Aucun artefact dédié de type "registre des exceptions de gouvernance actives" n’a été trouvé dans les artefacts actifs.
- Les non-ouvertures courantes sont principalement implicites via `PRODUCT_SCOPE` initial (`light`, `cover`, `switch`) alors que d’autres composants sont connus du registre.

## 6. Vérification absence de scope caché

**Statut : ÉCHEC**

- Tant qu’il n’existe pas de registre d’exceptions actif, les non-ouvertures restent partiellement implicites (absence dans `PRODUCT_SCOPE`), donc insuffisamment traçables au standard décidé en rétro.

## 7. Verdict GO / NO-GO

# **NO-GO**

`pe-epic-5` ne peut pas passer en démarrage à la date du gate.

## 8. Conditions de levée (bloquants uniquement)

1. **Créer et activer un registre explicite des exceptions de gouvernance** (artefact pilotage, partageable) avec au minimum :
   - composant,
   - statut (ouvert / non ouvert),
   - décision,
   - justification,
   - source d’autorité (PRD/architecture/epic),
   - date et owner.

2. **Rendre explicite la préséance documentaire** dans les artefacts de pilotage :
   - `architecture-delta-review-prd-final.md` fait foi pour l’interprétation FR39/FR40 et du mode `governed-open` en cas de tension de lecture avec `architecture-projection-engine.md`.

3. **Relier le backlog au registre d’exceptions** :
   - toute non-ouverture utilisée en arbitrage `pe-epic-5` doit référencer une entrée du registre (aucune non-ouverture implicite non tracée).

---

**Décision Scrum Master BMAD (etat initial du gate) :** NO-GO confirmé jusqu’à levée des 3 conditions ci-dessus.

---

## Addendum de suivi — 2026-04-16 (levées post-gate)

### État des conditions initiales

1. **Registre d'exceptions de gouvernance**  
   **Statut : LEVÉ**  
   **Preuve :** `_bmad-output/implementation-artifacts/pe-epic-5-governance-exceptions-register.md`

2. **Preséance documentaire explicite**  
   **Statut : LEVÉ**  
   **Preuve :** `_bmad-output/implementation-artifacts/pe-epic-5-document-precedence.md`

3. **Reference systematique du backlog vers les exceptions**  
   **Statut : LEVÉ**  
   **Preuve :** `_bmad-output/implementation-artifacts/pe-epic-5-gov-reference-micro-protocol.md`

### Verdict operationnel courant

**GO** — les 3 conditions de levee sont couvertes par des artefacts opposables.

`pe-epic-5` peut passer en **preparation** (pas en dev direct) dans le cadre de ces references:
- registre d'exceptions actif,
- preséance documentaire explicite,
- micro-protocole GOV-PE5-xxx applique en prep story/review.
