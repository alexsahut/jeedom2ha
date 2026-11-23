# Story H4 : Capteur « État » des portails et portes de garage

Status: done

Epic: (Chantier hors cycle BMAD 2026-11, rattachement rétrospectif)

Story Key (sprint-status): `h4-capteur-etat-des-portails-et-portes-de-garage`

> **Story rédigée après coup le 23/11/2026 : le développement n'a pas suivi le cycle BMAD.**
> Source unique : la PR #412 (fusion `0b826bb`), sa description et ses commits, lus par l'API REST GitHub. Aucun accès à la box ni à Home Assistant pour cette rédaction. Ce qui ne se déduit pas de ces sources est écrit « non établi ».

## Story

En tant qu'utilisateur qui suit un portail ou une porte de garage dans Home Assistant,
je veux voir ses cinq états (fermé, en fermeture, arrêté, en ouverture, ouvert),
afin de distinguer un portail arrêté d'un portail ouvert ou fermé, ce que la `cover` de HA ne sait pas montrer.

**Parcours : démon (mapping, discovery, état).** Suite de la story 24-7 (covers portail / garage).

## Contexte

- Une cover barrière publiée par 24-7 reçoit l'état `stopped` (valeur Jeedom 253), mais HA n'a pas d'état « arrêté » pour une cover.
- Formes décrites par la PR : eq 199 (`GARAGE_STATE` 1626 numérique, `GB_TOGGLE`), eq 496 (`BARRIER_STATE` 4543 numérique, `GB_OPEN`, `GB_CLOSE`, `GB_TOGGLE`), eq 455 (`BARRIER_STATE` binaire, équipement exclu par son objet). Attendu annoncé : exactement 2 capteurs ajoutés (199 et 496).

## Critères d'acceptation (tels que livrés)

1. **AC1 — Compagnon.** Quand `CoverMapper._map_barrier` publie une cover (état `BARRIER_STATE` ou `GARAGE_STATE` numérique, `barrier_mode` non nul), un `sensor` compagnon s'ajoute : `device_class: enum`, options `closed`, `closing`, `stopped`, `opening`, `open`, tirées de la même table que la cover (`sync/readback.py`), nom « État », même appareil et même disponibilité que la cover.
2. **AC2 — Valeur hors convention.** `100`, `1`, `2.55e2`, texte, vide… : rien n'est publié.
3. **AC3 — Lecture seule.** Aucun `command_topic`, aucun ordre routé (`…/barrier_state`, `…/barrier_state/set`, `…/<cmd>/set` testés).
4. **AC4 — Espace de noms propre.** `unique_id` `jeedom2ha_eq_<eq>_cmd_<cmd>_barrier_state`, `object_id` `jeedom2ha_<eq>_<cmd>_barrier_state`, `state_topic` `jeedom2ha/<eq>/<cmd>/barrier_state`.
5. **AC5 — Le capteur suit sa cover.** Cover publiée → capteur publié ; cover exclue ou refusée → capteur non publié, même raison ; cover retypée par « Corriger le type » → capteur absent ; un override posé sur l'état vise la cover, jamais le capteur.
6. **AC6 — Aucun compagnon** pour : volets `FLAP_*`, barrière à état binaire (reste `binary_sensor` `garage_door`), barrière non éligible (`GB_OPEN` seul), équipement non éligible, cover exclue.
7. **AC7 — Exception documentée à « une commande = une entité ».** L'info d'état est portée par la cover et par son capteur, et seulement dans ce cas ; documentée dans `mapping/barrier_state_sensor.py`, `models/evaluate_equipment.py`, `sync/state.py` et la doc utilisateur. La liste des écoutes PHP garde une seule entrée pour la commande d'état.
8. **AC8 — Ajouts seulement.** Cover inchangée (`map_all(...)[:1] == _map_all_base(...)`) ; scène représentative contre une ligne de base capturée sur `main` (`8e881e0`) : seuls 3 messages ajoutés (configurations des capteurs), aucun message existant changé ni disparu, ordre identique, contrat 4D inchangé.
9. **AC9 — « Corriger le type » reste ouvrable sur l'état d'un portail.** Le compagnon (`reason_details.barrier_companion_of`) ne compte pas comme une seconde entité portant la commande d'état (`8067666`).

## UI Impact

- **UI Impact:** Oui, limité : un ajout dans `desktop/js/jeedom2ha_mapping_override.js` (AC9) ; la PR indique « Écran : non modifié » avant ce dernier commit.

## Tâches

- [x] T1 — Mapper `mapping/barrier_state_sensor.py` et ajout dans `mapping/registry.py`.
- [x] T2 — Décision qui suit la cover (`models/evaluate_equipment.py`), discovery (`discovery/publisher.py`), état (`sync/state.py`, événement aussi envoyé au compagnon).
- [x] T3 — Tests, ligne de base, garde 25.4 (`REPLACED_BY_BARRIER_STATE_SENSOR`).
- [x] T4 — Documentation (`docs/fr_FR/index.md`, section « Portails et portes de garage » ; `changelog_beta.md`).
- [x] T5 — Correctif d'écran (AC9, `8067666`).
- [ ] T6 — Preuve terrain après déploiement (2 capteurs attendus, 253 vu `stopped`) : non établi.

## Dev Agent Record

### Agent Model Used

Session Claude Code (signature des commits) ; modèle exact : non établi.

### Fusion

- PR #412, branche `story/barrier-state-sensor`, tête `8067666`, fusionnée le 16/11/2026 à 16:40 UTC : `0b826bb508f96e351d4946b30f9d66f10b0c6d9f`.
- Commits : `b9d1f81`, `4a25860` (fusion de `main`), `8067666`.
- CI : le lint Python 3.9 était bloqué par le passage d'`ubuntu-latest` à 26.04 ; corrigé hors de cette PR par #413 (`3dfae83`), puis `main` fusionnée dans la branche ; CI de la tête verte.
- Titre de la PR : « feat(cover): … » ; message du commit de fusion : « feat(sensor): capteur État des portes de garage et portails (#412) ».

### Fichiers

- Démon : `mapping/barrier_state_sensor.py` (nouveau), `mapping/registry.py`, `models/evaluate_equipment.py`, `discovery/publisher.py`, `sync/state.py` (une ligne de retour remplacée, déclarée à la garde 25.4).
- Écran : `desktop/js/jeedom2ha_mapping_override.js` (+3).
- Documentation : `docs/fr_FR/index.md`, `docs/fr_FR/changelog_beta.md`.
- Fixtures : `tests/fixtures/barrier_state_sensor/projection_baseline.json` (nouveau).

### Tests

- `resources/daemon/tests/unit/test_story_barrier_state_sensor.py` (37 tests d'après la PR) et `barrier_state_corpus.py`.
- `tests/unit/test_story_barrier_state_sensor.node.test.js`.
- Adaptés : `test_story_24_7_portail_garage_cover.py`, `test_story_24_8_vanne_arrosage_valve.py`, `test_story_25_4_non_regression.node.test.js`.
- Résultat annoncé par la PR : 3547 tests Python passés en local, `flake8` vert ; seul échec Node : 25.4 / AC8, préexistant dans l'environnement de la session. Rejouer : `make test`, `flake8`, `node --test tests/unit/*.node.test.js`.

### Faits de production

- `0b826bb` est un ancêtre de `c015cc9`, déployé en production le 22/11/2026 à 12:13 : cette story est en production.
- Capteurs « État » effectivement publiés en production : non établi.

## Change Log

- 2026-11-16 — PR #412 ouverte (`b9d1f81`) ; CI bloquée par l'image Ubuntu, débloquée par #413.
- 2026-11-16 — Correctif d'écran (`8067666`) ; fusion dans `main` (`0b826bb`).
- 2026-11-22 — En production avec `c015cc9` (12:13).
- 2026-11-23 — Story rédigée après coup (backfill BMAD), statut `done` ; preuve terrain non établie.
