# Story H1 : Refonte de l'interface, front v2 + front v3 (scénarios publiés au choix, aide au clic)

Status: done

Epic: (Chantier hors cycle BMAD 2026-11, rattachement rétrospectif)

Story Key (sprint-status): `h1-refonte-interface-front-v2-v3`

> **Story rédigée après coup le 23/11/2026 : le développement n'a pas suivi le cycle BMAD.**
> Source unique : la PR #406 (fusion `40e1421`), sa description, ses commits, ses commentaires et ses fils de revue, lus par l'API REST GitHub, et la liste des PR de lot fusionnées dans `claude/front-v2` et `claude/front-v3`. Aucun accès à la box ni à Home Assistant pour cette rédaction. Ce qui ne se déduit pas de ces sources est écrit « non établi ».

## Story

En tant que personne qui installe et règle jeedom2ha,
je veux une interface qui se comprend sans phrase d'explication (démarrage guidé, une seule liste « À faire », fiche « Dans Jeedom → Dans Home Assistant », aide au clic, onglet Scénarios),
afin de voir, inclure, exclure et corriger ce qui est publié sans aide extérieure, et de choisir les scénarios publiés.

**Parcours : interface + démon (champs additifs) + PHP.** Aucun changement de ce que Home Assistant reçoit (voir AC8).

## Contexte

- Branche d'intégration `claude/front-v3` (qui contient `claude/front-v2`), fusionnée dans `main` par la PR #406 le 15/11/2026 (`40e1421`).
- Chaque lot avait sa PR, relue par Codex et ClaudeBox, avec une CI verte (d'après la description de #406) :
  - **v2 (nuit du 13 au 14/11)** : #387 (Lot 0, socle), #388 (Lot 4, configuration), #389 (Lot 3, démon : champs additifs), #390 (Lot 2, fiche équipement), #391 (Lot 1, démarrage guidé), #392 (Lot 7, maison et pièce), #393 (Lot 5, corriger le type), #394 (Lot 6, exclusion unifiée), #395 (Lot 8, guide « Premiers pas »), #396 (Lot 9b), #397 (Lot 9a) ;
  - **v3 (14 et 15/11)**, issue d'un challenge UX entre un agent BMAD et un agent ClaudeBox : #398 (Lot 0, correctifs), #399 (Lot 4a, scénarios côté serveur), #400 (Lot 2), #401 (Lot 1), #402 (Lot 4b, onglet Scénarios), #403 (Lot 3), #404 (Lot 5, documentation), #405 (Lot 6, info-bulles) ;
  - correctifs issus de la revue Codex de #406 : #407 (Lot 7) et #408 (Lot 8).
- Go explicite d'Alexandre pour la fusion : 14/11/2026 à 22:10 (description de #406).
- Lien avec la story 26-0 (audit « premier arrivant », epic 26) : **non établi**. Les sources ne disent pas si cette refonte est issue des constats de 26-0.
- Aucune story, aucun SCP et aucune décision consignée dans `_bmad-output/` avant le développement.

## Critères d'acceptation (tels que livrés)

1. **AC1 — Démarrage guidé et barre d'état.** Un démarrage guidé et une barre d'état unique, avec le bouton « Appliquer (n) » (v2 Lot 1, v3).
2. **AC2 — Fiche équipement.** Fiche « Dans Jeedom → Dans Home Assistant », compacte, avec une bande de cause d'une ligne (v2 Lot 2, v3 Lot 2).
3. **AC3 — Corriger le type.** Fenêtre modale « Corriger le type » avec aperçu, annulation et garde-fous ; « Annuler » après « Publier quand même » préserve les réglages des commandes sœurs (retrait limité `scope=command` côté démon, #407).
4. **AC4 — Exclusion unifiée.** Exclusion unifiée avec confirmations chiffrées, cases à trois états (v2 Lot 6, v3).
5. **AC5 — Maison et pièces.** Une seule liste « À faire », tuiles de pièce avec liseré d'état, arbre unique avec fil d'Ariane, recherche dans toute la maison.
6. **AC6 — Configuration.** Configuration réduite, connexion guidée « en un clic » (v2 Lot 4, v3 Lot 3).
7. **AC7 — Aide.** Plus aucune phrase d'explication à l'écran ; bulles d'aide ⓘ au clic (v3 Lot 6) ; lexique ; guide « Premiers pas » (`docs/fr_FR/premiers-pas.md`) et documentation par écran avec captures.
8. **AC8 — Scénarios publiés au choix (option B).** Onglet Scénarios. Les scénarios déjà publiés le restent (migration idempotente qui les inscrit) ; les nouveaux arrivent non publiés et sont marqués ✱ ; sur une installation neuve, aucun n'est publié sans choix explicite. Un retrait non confirmé reste affiché « en attente de Home Assistant » avec « Réessayer » (`withdraw_pending`, `ha_pending`, `in_ha` à `null` tant que la présence est inconnue, #408).
9. **AC9 — Projection Home Assistant inchangée.** Le front ne change rien à ce que HA reçoit : tests octet pour octet sur les messages MQTT, 135 (v2) et 145 (scénarios).

## UI Impact

- **UI Impact:** Oui

## Tâches

- [x] T1 — Front v2, lots 0 à 9b (#387 à #397).
- [x] T2 — Front v3, lots 0 à 6 (#398 à #405), dont scénarios côté serveur (option B) et onglet Scénarios.
- [x] T3 — Correctifs de revue Codex sur #406 : #407 (annulation qui préserve les réglages sœurs), #408 (retrait de scénario non confirmé gardé en attente).
- [x] T4 — Non-régression de la projection HA (AC9) et migration des scénarios vérifiée sur la démo (VM 122) : 5/5, idempotente (description de #406).
- [x] T5 — Documentation utilisateur (`docs/fr_FR/index.md`, `premiers-pas.md`, `compteurs.md`, `installation-github.md`, captures, `changelog_beta.md`).
- [ ] T6 — Validation UX d'usage réel, nommément identifiée (règle « story touchant l'interface » de `docs/bmad-parcours-rapide-complet.md`) : **non établi**.

## Dev Agent Record

### Agent Model Used

Sessions Claude Code (signature des PR) ; modèle exact : non établi.

### Fusion

- PR #406, branche `claude/front-v3`, tête `e23ccbf`, fusionnée le 15/11/2026 à 10:37 UTC : `40e1421246ad80142917311ad36e2c8bfb8958cd`.
- CI de la tête : verte (lint, tests Python 3.9 / 3.11 / 3.12, charge, Node, PHP 7.4 / 8.2, `bash -n`, Market, politiques de PR).
- Revue Codex : deux constats P2 (réglages sœurs effacés par « Annuler » ; retrait de scénario échoué lu comme absent), corrigés par #407 et #408 ; dernière revue sur `e23ccbf` : « Didn't find any major issues ».

### Fichiers (principaux)

- PHP : `core/ajax/jeedom2ha.ajax.php`, `core/class/jeedom2ha.class.php`, `core/php/jeedom2ha_reevaluation.php`, `core/php/jeedom2ha_scenario_publication.php` (nouveau), `desktop/php/jeedom2ha.php`, `desktop/php/jeedom2ha_overview_helpers.php`, `plugin_info/configuration.php`, `plugin_info/install.php`.
- JS / CSS : `desktop/css/jeedom2ha_v2.css` (nouveau), `desktop/css/jeedom2ha.css`, `desktop/js/jeedom2ha.js`, `jeedom2ha_exclusions.js`, `jeedom2ha_guide.js`, `jeedom2ha_ha_side.js`, `jeedom2ha_infotip.js`, `jeedom2ha_lexique.js`, `jeedom2ha_scenarios.js`, `jeedom2ha_type_panel.js` (nouveaux), `jeedom2ha_mapping_surface.js`, `jeedom2ha_overview.js`, `jeedom2ha_workview.js`, `jeedom2ha_mapping_override.js` (+5 lignes).
- Démon : `resources/daemon/models/ha_side.py` (nouveau), `models/topology.py`, `export/decision_export.py`, `transport/http_server.py` (ajouts).
- Gate UX : `tests/e2e/gate/lib/*.mjs`, `tests/e2e/gate/parcours/*.mjs` (dont `exclusion-unifiee-simulee.mjs`, nouveau), `scripts/doc-captures.js` (nouveau).
- Documentation : `docs/fr_FR/` (voir T5).

### Tests

- Python : `test_front_v2_lot3_champs_additifs.py`, `test_front_v2_lot3_projection_identique.py`, `test_front_v2_lot6_revert_equipment_scope.py`, `test_front_v3_lot4a_projection_identique.py`, `test_front_v3_lot7_annuler_preserve.py`, `test_front_v3_lot8_retrait_attente.py` ; lignes de base `tests/fixtures/front_v2_lot3/discovery_baseline.json` et `front_v3_lot4a/scenarios_upgrade_baseline.json`.
- PHP : `tests/test_php_front_v2_lot3_bridge_status.php`, `tests/test_php_front_v3_lot4a_scenarios.php`.
- Node : `tests/unit/test_front_v2_*.node.test.js`, `tests/unit/test_front_v3_*.node.test.js`.
- Rejouer : `make test`, `flake8`, `node --test tests/unit/*.node.test.js`.
- Nombre de tests passés au SHA de fusion : non établi (la CI est verte).

### Faits de production

- `40e1421` est un ancêtre de `c015cc9`, déployé en production le 22/11/2026 à 12:13 : cette story est donc en production.
- Inventaire des entités avant / après sur la production pour cette story : non établi.
- Validation UX d'usage réel (qui, quand, sur quel SHA) : non établi.

## Change Log

- 2026-11-13 / 2026-11-15 — Développement hors cycle BMAD, par lots (#387 à #405, #407, #408).
- 2026-11-15 — PR #406 fusionnée dans `main` (`40e1421`).
- 2026-11-22 — En production avec `c015cc9` (12:13).
- 2026-11-23 — Story rédigée après coup (backfill BMAD, décision d'Alexandre du 23/11), statut `done` ; validation UX non établie.
