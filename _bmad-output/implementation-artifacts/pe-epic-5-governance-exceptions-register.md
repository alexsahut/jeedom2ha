# Registre des exceptions de gouvernance — Cycle Moteur de Projection Explicable

**Statut :** actif  
**Date de création :** 2026-04-16  
**Owner pilotage :** Alexandre (Project Lead) + Alice (Product Owner) + Bob (Scrum Master)

## 1. Objet

Rendre explicites, justifiées et traçables toutes les non-ouvertures de composants HA dans le cycle courant.

Ce registre est la référence obligatoire pour :
- les revues de stories,
- les arbitrages backlog,
- le gate d’alignement pre-go/no-go.

## 2. Règle d’usage (obligatoire)

- Par défaut, un composant `connu` et `validable` est ouvrable (FR39/FR40).
- Toute non-ouverture doit avoir une entrée active dans ce registre.
- Toute entrée active doit contenir : décision, justification, source d’autorité, owner, critère de levée.
- Aucune non-ouverture implicite (scope caché) n’est autorisée.

## 3. Références d’autorité

- `prd.md` : FR37, FR38, FR39, FR40 ; NFR10.
- `architecture-delta-review-prd-final.md` : `PRODUCT_SCOPE` en mode `governed-open`, item 14 fermé par FR39/FR40.
- `architecture-projection-engine.md` : composants connus + `PRODUCT_SCOPE` initial.
- `epics-projection-engine.md` : AR13 (gate FR40/NFR10 pour toute ouverture).
- `sprint-status.yaml` : `pe-epic-5` bloqué tant que gate non levé.

## 4. Exceptions actives

| ID | Composant HA | Décision active | Justification | Source d’autorité | Owner | Statut | Critère de levée |
|---|---|---|---|---|---|---|---|
| GOV-PE5-001 | `sensor` | Non-ouvert dans le cycle à date | Ouverture non encore portée par incrément dédié FR40 | PRD FR39/FR40 + Epics AR13 | PO + Project Lead | active | Incrément avec (1) cas nominal, (2) cas d’échec validation, (3) test non-régression 4D ; puis décision d’ouverture tracée |
| GOV-PE5-002 | `binary_sensor` | Non-ouvert dans le cycle à date | Idem | PRD FR39/FR40 + Epics AR13 | PO + Project Lead | active | Même critère de levée FR40/NFR10 |
| GOV-PE5-003 | `button` | Non-ouvert dans le cycle à date | Idem | PRD FR39/FR40 + Epics AR13 | PO + Project Lead | active | Même critère de levée FR40/NFR10 |
| GOV-PE5-004 | `number` | Non-ouvert dans le cycle à date | Idem | PRD FR39/FR40 + Epics AR13 | PO + Project Lead | active | Même critère de levée FR40/NFR10 |
| GOV-PE5-005 | `select` | Non-ouvert dans le cycle à date | Idem | PRD FR39/FR40 + Epics AR13 | PO + Project Lead | active | Même critère de levée FR40/NFR10 |
| GOV-PE5-006 | `climate` | Non-ouvert dans le cycle à date | Idem | PRD FR39/FR40 + Epics AR13 | PO + Project Lead | active | Même critère de levée FR40/NFR10 |

## 5. Preuves techniques de contexte (trace)

- Composants connus présents dans l’architecture : `sensor`, `binary_sensor`, `button`, `number`, `select`, `climate`.
- `PRODUCT_SCOPE` initial documenté : `["light", "cover", "switch"]`.
- Interprétation de référence : `PRODUCT_SCOPE` est une base de départ gouvernée, pas un plafond arbitraire.

## 6. Contrôle vivant

Checklist à exécuter avant toute story impactant l’ouverture :
1. La non-ouverture envisagée référence-t-elle un ID `GOV-PE5-xxx` actif ?
2. Le motif est-il explicite, justifié, et aligné PRD/architecture/epics ?
3. Le critère de levée FR40/NFR10 est-il clairement défini dans la story ?
4. Le tracker/story reference-t-il l’ID d’exception concerné ?

## 7. Journal des changements

- **2026-04-16** — création du registre (levée #1 du gate d’alignement pe-epic-5).
