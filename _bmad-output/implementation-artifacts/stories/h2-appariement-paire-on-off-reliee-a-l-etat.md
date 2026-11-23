# Story H2 : Interrupteur apparié à la paire On/Off reliée à l'info d'état

Status: done

Epic: (Chantier hors cycle BMAD 2026-11, rattachement rétrospectif)

Story Key (sprint-status): `h2-appariement-paire-on-off-reliee-a-l-etat`

> **Story rédigée après coup le 23/11/2026 : le développement n'a pas suivi le cycle BMAD.**
> Source unique : la PR #410 (fusion `0aa0852`), sa description, ses commits et ses commentaires, lus par l'API REST GitHub. Aucun accès à la box ni à Home Assistant pour cette rédaction. Ce qui ne se déduit pas de ces sources est écrit « non établi ».

## Story

En tant qu'utilisateur qui pilote depuis Home Assistant un équipement portant plusieurs paires d'ordres On/Off,
je veux que l'interrupteur exécute la paire reliée à l'info d'état, et qu'il ne soit pas publié quand le choix est ambigu,
afin qu'un ordre « On » ou « Off » n'agisse jamais sur une autre fonction (un mode, par exemple) que celle de l'état affiché.

**Parcours : démon (mapping) + PHP (export des liens) + interface (libellés).**

## Contexte (constat de la PR)

- Un équipement qui porte plusieurs actions de même sens (deux `ENERGY_ON`, deux `ENERGY_OFF`) gardait **la dernière action vue**.
- Cas réel décrit (eq 554, chauffe-eau virtuel) : une paire « On / Off » pilote le relais et met l'état à jour ; une paire « Manu / auto » ne change qu'un mode. Le switch de HA changeait le mode au lieu du relais.
- Seuls `SwitchMapper` (`ENERGY_*`) et `PresenceSwitchMapper` (`SET_ON` / `SET_OFF`) gardaient « la dernière vue » ; `LightMapper` et `CoverMapper` refusent déjà les doublons, `SWITCH_*` / `FAN_*` apparient déjà par nom.

## Critères d'acceptation (tels que livrés)

1. **AC1 — Lien action → info lu dans Jeedom, en lecture seule.** Champ « Valeur » du cœur (`linked_value`, déjà exporté), configuration `updateCmdId` du cœur, configuration `infoId` du seul plugin virtual. Seul le lien est exporté (`update_cmd_id`, `virtual_info_id`, ajout seulement), jamais la valeur écrite.
2. **AC2 — Une seule paire : comportement inchangé**, reliée ou non.
3. **AC3 — Plusieurs paires.** Pour chaque sens présent, l'unique action reliée à l'état retenu est gardée. Une action non reliée, même seule dans son sens, rend le cas ambigu (**fail-closed**).
4. **AC4 — Ambiguïté.** Pas de switch : mapping `ambiguous`, raison `switch_pairing_ambiguous`, aucun ordre routable (`has_on_off=False`, même avec « Publier quand même »). Les autres entités de l'équipement (capteurs) restent publiées.
5. **AC5 — État retenu unique.** Avec plusieurs paires et plusieurs infos d'état candidates, l'état retenu est celui que visent les actions reliées, quel que soit l'ordre des commandes ; une seule fonction (`energy_state_of`) le donne au switch et aux mappers de capteurs (pas de capteur binaire en double).
6. **AC6 — Écran et documentation.** Libellé de cause « plusieurs ordres On/Off — reliez à l'état, dans Jeedom, ceux qui pilotent l'appareil », catégorie Bloquée, bande « Ordres On/Off en double », liste « À faire », fiche du lexique ; le remède nomme les vrais champs (« Commande information à mettre à jour » pour un virtuel, commande d'état liée sinon). `docs/fr_FR/index.md` et `changelog_beta.md`.
7. **AC7 — Effet sur une installation existante.** Équipement à une seule paire : rien ne change. Équipement à plusieurs paires dont une reliée : même identifiant, mêmes topics, même discovery ; seules les commandes exécutées changent. Équipement à plusieurs paires sans lien univoque : le switch est dépublié, la cause est affichée. Les types génériques de Jeedom ne sont jamais modifiés.
8. **AC8 — Non-régression.** Scène représentative rejouée contre une ligne de base capturée sur `main` (`e332b8f`) : trace MQTT identique message pour message hors des équipements visés. Golden 8.4 régénéré (seule différence : la paire du switch du chauffe-eau). Garde 25.4 : `REPLACED_BY_FIX_SWITCH_APPARIEMENT`.

## UI Impact

- **UI Impact:** Oui (libellés, lexique, bande de cause ; aucun nouvel écran)

## Tâches

- [x] T1 — Export PHP des liens (`core/php/jeedom2ha_command_links.php`, appelé par `core/class/jeedom2ha.class.php`) et modèle `JeedomCmd` (`linked_info_ids()`).
- [x] T2 — Règles d'appariement (`resources/daemon/mapping/pairing.py`) appliquées à `switch.py` et `presence_switch.py` ; `energy_state_of` partagé avec `sensor.py` et `binary_sensor.py`.
- [x] T3 — Cause `switch_pairing_ambiguous` (`models/cause_mapping.py`) et écran (lexique, surface, vue d'ensemble, override).
- [x] T4 — Tests, golden 8.4, garde 25.4, documentation.
- [x] T5 — Relectures traitées : relecture indépendante (54ac78d) et contre-relecture (50214ff), voir Change Log.
- [ ] T6 — Vérification en lecture seule, avant déploiement, des liens réels des actions de l'eq 554 (risque résiduel nommé dans la PR) : non établi.
- [ ] T7 — Preuve terrain après déploiement (inventaire des entités avant / après, 0 erreur) : non établi.

## Dev Agent Record

### Agent Model Used

Session Claude Code (signature de la PR) ; modèle exact : non établi.

### Fusion

- PR #410, branche `fix/switch-appariement-etat`, tête `b81d81d`, fusionnée le 15/11/2026 à 22:30 UTC : `0aa08525248d660564c9a6aab85859bb48a0a8fe`.
- Commits : `8f2da02`, `54ac78d`, `50214ff`, `b81d81d`.
- CI de la tête : verte. Revue Codex automatique : en échec technique (« We couldn't complete this review »), aucun constat.

### Fichiers

- PHP : `core/class/jeedom2ha.class.php`, `core/php/jeedom2ha_command_links.php` (nouveau).
- Démon : `resources/daemon/mapping/pairing.py` (nouveau), `mapping/switch.py`, `mapping/presence_switch.py`, `mapping/sensor.py`, `mapping/binary_sensor.py`, `models/cause_mapping.py`, `models/topology.py`.
- Écran : `desktop/js/jeedom2ha_lexique.js`, `jeedom2ha_mapping_override.js`, `jeedom2ha_mapping_surface.js`, `jeedom2ha_overview.js`.
- Documentation : `docs/fr_FR/index.md`, `docs/fr_FR/changelog_beta.md`.
- Fixtures : `tests/fixtures/fix_switch_appariement/projection_baseline.json` (nouveau), `golden_corpus/expected_sync_snapshot.json`, `golden_corpus/sync_payload.json`.

### Tests

- `resources/daemon/tests/unit/test_fix_switch_appariement_etat.py` (37 tests d'après la PR) et `fix_switch_appariement_corpus.py`.
- `tests/test_php_command_links.php` (9).
- `tests/unit/test_fix_switch_appariement_etat.node.test.js` (6) et `test_fix_switch_appariement_etat_navigateur_reel.node.test.js` (2, Chromium réel).
- Adaptés : `test_story_11_2_eq554_multi_domain.py`, `test_story_19_2_p1_publication_decision_ref_coherence.py`, `test_story_25_1_compteurs.node.test.js`, `test_story_25_4_non_regression.node.test.js`.
- Résultat annoncé par la PR : `make test` 3412 passés, `flake8` vert ; un échec Node préexistant (25.4 / AC8) dans l'environnement de la session, rouge aussi sur `main`. Rejouer : `make test`, `flake8`, `node --test tests/unit/*.node.test.js`.

### Faits de production

- `0aa0852` est un ancêtre de `c015cc9`, déployé en production le 22/11/2026 à 12:13 : cette story est en production.
- Effet réel sur l'eq 554 en production (paire retenue, ou switch dépublié) : non établi.
- Validation UX d'usage réel : non établi.

## Change Log

- 2026-11-15 — PR #410 ouverte (`8f2da02`).
- 2026-11-15 — Relecture indépendante traitée (`54ac78d`) : remède exact, sens unique gardé, état indépendant de l'ordre des commandes.
- 2026-11-15 — Contre-relecture traitée (`50214ff`) : export réduit au lien, état retenu par `energy_state_of`, fail-closed rétabli, code mort retiré ; `b81d81d` : test d'une action portant deux liens.
- 2026-11-15 — Fusion dans `main` (`0aa0852`).
- 2026-11-22 — En production avec `c015cc9` (12:13).
- 2026-11-23 — Story rédigée après coup (backfill BMAD), statut `done` ; preuve terrain et validation UX non établies.
