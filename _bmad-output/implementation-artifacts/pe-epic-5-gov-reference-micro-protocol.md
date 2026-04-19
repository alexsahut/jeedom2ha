# Micro-protocole d'application — references GOV-PE5-xxx

**Statut :** actif  
**Date :** 2026-04-16  
**Objet :** lever la condition #3 du gate en rendant opposable la reference systematique aux exceptions de gouvernance pour toute non-ouverture.

## 1. Regle obligatoire

Toute decision de non-ouverture d'un composant HA dans `pe-epic-5` doit contenir une reference explicite a un ID `GOV-PE5-xxx` actif.

Sans ID explicite:
- la prep story est **non conforme**,
- la review est **non conforme**,
- la decision est **non opposable**.

## 2. Application en prep story (check bloquant)

Avant passage en `ready-for-dev`, verifier et tracer:
1. `Decision`: ouverture ou non-ouverture.
2. Si `non-ouverture`: ID `GOV-PE5-xxx` actif obligatoire.
3. `Justification`: alignee avec le registre et la source d'autorite.
4. `Criteres de levee`: rappeles (FR40/NFR10 ou critere du registre).

Format minimal attendu dans la story:

`Decision non-ouverture: GOV-PE5-xxx - <motif court>`

## 3. Application en review (check bloquant)

Avant validation review:
1. Toute non-ouverture mentionnee dans la story/PR renvoie a un ID `GOV-PE5-xxx`.
2. L'ID reference existe et est `active` dans le registre.
3. Aucun arbitrage implicite de type "hors scope" sans ID.

Si un de ces points echoue: review en **request changes**.

## 4. Rule d'opposabilite

- Registre source: `pe-epic-5-governance-exceptions-register.md`
- Preséance: `pe-epic-5-document-precedence.md`
- Gate: `pe-epic-5-alignment-gate.md`

En cas d'absence de reference GOV, l'arbitrage de non-ouverture est considere invalide.

## 5. Entree en vigueur

Applicable immediatement a toute prep story / review liee a `pe-epic-5`.

## 6. Trace de levee gate

Ce protocole constitue la preuve de levee de la condition #3 du gate d'alignement pre-`pe-epic-5`.
