# Preséance documentaire - Cycle Moteur de Projection Explicable

**Statut :** actif  
**Date :** 2026-04-16  
**Objet :** lever le blocage #2 du gate d'alignement pre-`pe-epic-5` en fixant une regle de lecture opposable.

## 1. Regle de preséance (opposable)

En cas de tension de lecture entre artefacts:

1. `pe-epic-4-retro-2026-04-15.md` fixe l'intention dominante de pilotage.
2. `prd.md` fixe l'intention produit et les exigences FR/NFR.
3. `architecture-delta-review-prd-final.md` fait foi pour l'interpretation finale PRD <-> architecture.
4. `architecture-projection-engine.md` reste la base technique, sauf si un point est explicitement recadre/ferme par le delta.
5. `epics-projection-engine.md` et `sprint-status.yaml` declinent l'execution dans ce cadre.

## 2. Regle explicite FR39/FR40 (point critique)

Pour toute decision d'ouverture/non-ouverture composant:

- l'interpretation de reference est celle du delta final:
  - `PRODUCT_SCOPE` = base de depart du cycle, pas plafond arbitraire,
  - modele d'ouverture = `governed-open`,
  - conditions d'ouverture = FR39/FR40 + NFR10/AR13.
- en cas de tension de lecture avec l'architecture de base, **le delta final prevaut**.

## 3. Regle de review

Toute review de prep story / arbitrage backlog `pe-epic-5` doit verifier:

1. Conformite a l'intention dominante du cycle.
2. Conformite a FR39/FR40 selon la lecture delta.
3. Si non-ouverture: presence d'une exception active dans le registre de gouvernance.

## 4. Effet sur le gate d'alignement

- Blocage #2 (preséance documentaire non explicite): **leve**.
- Les blocages restants sont evalues via le gate d'alignement et le registre d'exceptions.

## 5. References

- `_bmad-output/implementation-artifacts/pe-epic-4-retro-2026-04-15.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture-delta-review-prd-final.md`
- `_bmad-output/planning-artifacts/architecture-projection-engine.md`
- `_bmad-output/planning-artifacts/epics-projection-engine.md`
- `_bmad-output/implementation-artifacts/pe-epic-5-governance-exceptions-register.md`
- `_bmad-output/implementation-artifacts/pe-epic-5-alignment-gate.md`
