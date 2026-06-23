# Retrospective pe-epic-12 - Restitution d'etat runtime

Date: 2026-06-22
Projet: jeedom2ha
Cycle actif: Moteur de projection explicable

## Synthese

`pe-epic-12` est livre. Il corrige la regression systemique des entites publiees en discovery mais laissees en etat `unknown`. Le chemin Jeedom vers Home Assistant publie desormais l'etat initial puis les changements event-driven, en restant subordonne a la discovery effective du candidat.

## Valeur livree

- Story 12.1 : streaming `sensor` et `binary_sensor`, avec callback PHP et resolver daemon.
- Story 12.2 : streaming `switch`; `button` conserve volontairement une semantique sans readback.
- Story 12.3 : realignement des sources BMAD actives et cloture documentaire des epics 11/12.

## Preuves

- PR #123 : implementation 12.1 (`d5b86ce`) et correctif de gating discovery (`0a79966`); 860 tests verts.
- PR #125, commit `6e24693` : implementation 12.2; 893 tests verts apres correction de revue.
- Gate terrain 12.1 : 88 listeners et eq553 « Tension reseau » a 238.4 V au lieu de `unknown`.
- Gate terrain 12.2 : switch reel commande on/off, eq554 non `unknown`, non-regression eq553/light/cover.

## Risques residuels

- Les domaines `climate` et suivants ne sont pas couverts par ces deux vagues et doivent rester gouvernes par FR49.
- La coherence `state_topic` subset discovery doit rester une propriete testee lors de toute future extension.
- L'issue #124 reste le suivi explicite du topic discovery eq-level legacy lors d'une migration node-scoped.

## Lecons

- Publier une entite sans son chemin de valeur donne une parite visuelle trompeuse; discovery et state doivent etre verifies ensemble.
- Le gating sur la discovery reelle est plus sur que la seule eligibilite theorique du candidat.
- Les vagues par domaine reduisent le risque et rendent les gates terrain reproductibles.
- Un `button` ne doit pas recevoir artificiellement un etat readback pour uniformiser l'implementation.

## Conclusion

Le runtime state streaming est operationnel sur les domaines vises et les preuves terrain confirment la sortie de `unknown`. Apres la revue de la story 12.3, l'epic peut revenir definitivement a `done`.
