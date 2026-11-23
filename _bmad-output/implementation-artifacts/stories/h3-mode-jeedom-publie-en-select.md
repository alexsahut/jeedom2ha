# Story H3 : Un mode Jeedom publié en `select` Home Assistant

Status: done

Epic: (Chantier hors cycle BMAD 2026-11, rattachement rétrospectif)

Story Key (sprint-status): `h3-mode-jeedom-publie-en-select`

> **Story rédigée après coup le 23/11/2026 : le développement n'a pas suivi le cycle BMAD.**
> Source unique : la PR #411 (fusion `8e881e0`), sa description, ses commits et ses commentaires, lus par l'API REST GitHub. Aucun accès à la box ni à Home Assistant pour cette rédaction. Ce qui ne se déduit pas de ces sources est écrit « non établi ».

## Story

En tant qu'utilisateur qui pilote un mode Jeedom (une info texte posée par plusieurs actions),
je veux le retrouver dans Home Assistant comme un `select` dont les options sont les valeurs du mode,
afin de lire et de changer ce mode depuis HA sans entité en double ni ordre deviné.

**Parcours : démon (mapping, discovery, ordres, état) + PHP (export) + interface (« Corriger le type »).** Ouvre `select` dans `PRODUCT_SCOPE` (AR13 / FR40).

## Contexte

- Empilée sur #410 (fusionnée avant). Cas réels décrits : chauffe-eau (eq 554, info 5489 posée par trois actions) et équipement « Modes » (eq 104, info 651, 7 modes).
- Antécédent documentaire : la story 17-2 (cadrage, 2026-07-17) avait conclu qu'aucun cas ne justifiait l'ouverture de `select` à cette date. La décision qui rouvre ce point : non établi dans `_bmad-output/` (seule la PR la porte).

## Critères d'acceptation (tels que livrés)

1. **AC1 — Reconnaissance, par ordre de confiance** (`mapping/select.py`) : (1) types génériques standard `MODE_STATE` + `MODE_SET_STATE` (dès qu'une action est reliée à l'info, seules les actions reliées comptent ; repli sur le nom des actions seulement pour une info texte sans aucun lien dans l'équipement) ; (2) action de sous-type `select` avec `listValue`, reliée à une info (options = libellés) ; (3) actions reliées par `updateCmdId` / `updateCmdToValue` (cœur) ou `infoId` / `value` (virtual), chacune écrivant une constante. Confiance `sure`.
2. **AC2 — Pas de devinette.** Moins de deux options, deux actions écrivant la même valeur, deux actions « liste » sur la même info, action reliée sans valeur constante (WARNING) : pas de select.
3. **AC3 — Jamais en double.** Pas de select si son info ou l'une de ses actions est déjà portée par une autre entité, jamais de select partiel, jamais pour les familles sensibles (`LOCK_`, `ALARM_`, `SIREN_`, `GB_`, `BARRIER_`, `GARAGE_`, `VALVE_`, `IRRIG_`, `FAUCET_`, `FLAP_`, `LIGHT_`, `THERMOSTAT_`, `HEATING_`). Une info numérique publiée en capteur et pilotée par une action « liste » garde son capteur, sans select.
4. **AC4 — Identité propre.** `unique_id` `jeedom2ha_eq_<eq>_select_<info>`, topics `jeedom2ha/<eq>/select_<info>/state` et `/set` (couvert par l'abonnement `jeedom2ha/+/+/set`), `optimistic: false` ; un identifiant déjà pris est écarté.
5. **AC5 — État et ordres.** Valeur hors options → état `None` (unknown), comparaison exacte ; l'option reçue exécute l'action qui l'écrit, toute autre valeur est refusée ; jamais d'état supposé.
6. **AC6 — Entité secondaire.** `MapperRegistry.map_all` calcule la projection d'avant à l'identique puis ajoute les select (`additional_mappings`) ; aucune entité n'est remplacée, renommée ni re-routée. Un select n'est principal que pour un équipement qui n'avait aucune entité.
7. **AC7 — « Corriger le type ».** Override `ha_entity_type: "select"` = rôle « Mode (état) » sur une info, « Mode (commande) » sur une action ; jamais un retypage d'une autre entité ; types génériques Jeedom jamais touchés ; aperçu dans `/system/overrides/preview`. Limite assumée : quand ni l'info ni les actions ne sont reconnues, rien n'est proposé.
8. **AC8 — AR13 / FR40.** Registre `select` (entrée inchangée, `SelectCapabilities` ajoutée), `validate_projection()` nominal et échecs (`ha_missing_required_option`, `ha_missing_command_topic`), `test_governance_fr40_proof_select`, contrat 4D vérifié ; `select` ajouté à `PRODUCT_SCOPE` et au registre des publishers (`publish_select`), streamé par `StateSynchronizer`.
9. **AC9 — Ajouts seulement.** Sur une installation existante, seuls des `select` s'ajoutent ; aucun topic, payload, identifiant ni nom existant ne change (scène représentative contre une ligne de base capturée sur #410, `b81d81d`). Compteurs de synchro : nouvelles clés `selects_*`.

## UI Impact

- **UI Impact:** Oui (rôles « Mode (état) » / « Mode (commande) » dans « Corriger le type »)

## Tâches

- [x] T1 — Export PHP additif : `update_cmd_to_value`, `virtual_value`, `list_value` (`core/php/jeedom2ha_command_links.php`), modèle `JeedomCmd`.
- [x] T2 — Mapper `mapping/select.py`, ajout en fin de `map_all` (`mapping/registry.py`), overrides (`mapping/overrides.py`).
- [x] T3 — Discovery (`discovery/publisher.py`, `discovery/registry.py`), validation (`validation/ha_component_registry.py`), ordres (`sync/command.py`), état (`sync/state.py`), transport (`transport/http_server.py`), export de décision.
- [x] T4 — Écran « Corriger le type » (`jeedom2ha_type_panel.js`, `jeedom2ha_mapping_surface.js`, `jeedom2ha_mapping_override.js`) et documentation.
- [x] T5 — Tests, fixtures régénérées (ajouts seuls), garde 25.4.
- [x] T6 — Relecture traitée (`7167f11`) ; formes réelles décrites par la PR intégrées (`61fcee2`, `d38e229`) ; mécanisme de retrait de bouton essayé (`75e0d10`) puis retiré (`61fcee2`).
- [ ] T7 — Preuve terrain après déploiement (inventaire des entités avant / après, select attendus sur 554 et 104) : non établi.

## Dev Agent Record

### Agent Model Used

Session Claude Code (signature de la PR) ; modèle exact : non établi.

### Fusion

- PR #411, branche `story/select-mode`, tête `69ea1d4`, fusionnée le 15/11/2026 à 22:39 UTC : `8e881e0951b00c98b8cae113c64bb4d4f3179e63`.
- Commits propres : `88abccd`, `7167f11`, `4035910`, `75e0d10`, `61fcee2`, `d38e229`, puis `69ea1d4` (fusion de `main` après #410).
- CI de la tête : verte. Revue Codex automatique : en échec technique, aucun constat.

### Fichiers

- Démon : `mapping/select.py` (nouveau), `mapping/registry.py`, `mapping/overrides.py`, `discovery/publisher.py`, `discovery/registry.py`, `export/decision_export.py`, `models/evaluate_equipment.py`, `models/ha_side.py`, `models/mapping.py`, `models/topology.py`, `sync/command.py`, `sync/state.py`, `transport/http_server.py`, `validation/ha_component_registry.py`.
- PHP : `core/php/jeedom2ha_command_links.php`.
- Écran : `desktop/js/jeedom2ha_mapping_override.js`, `jeedom2ha_mapping_surface.js`, `jeedom2ha_type_panel.js`.
- Documentation : `docs/fr_FR/index.md`, `docs/fr_FR/changelog_beta.md`.
- Fixtures : `tests/fixtures/select_mode/projection_baseline.json` (nouveau) ; régénérées (ajouts seuls) : golden 8.4, gardes 19.4 (s1, s2, s3, s5), lignes de base front v2 Lot 3 et v3 Lot 4a.

### Tests

- `resources/daemon/tests/unit/test_story_select_mode.py` (89 tests d'après la PR) et `select_mode_corpus.py`.
- `tests/unit/test_story_select_mode.node.test.js` (5) et `test_story_select_mode_navigateur_reel.node.test.js` (3, Chromium réel).
- `tests/test_php_command_links.php` (+ `listValue`).
- Tests qui figent la liste des types ouverts mis à jour (7.2, 7.3, 7.4, 8.2, 9.1 à 9.3, 24.7, 24.9, registre, FR40).
- Résultat annoncé par la PR : `make test` 3505 passés, `flake8` vert ; seul échec Node : 25.4 / AC8, préexistant dans l'environnement de la session. Rejouer : `make test`, `flake8`, `node --test tests/unit/*.node.test.js`.

### Faits de production

- `8e881e0` est un ancêtre de `c015cc9`, déployé en production le 22/11/2026 à 12:13 : cette story est en production.
- Select effectivement publiés en production : non établi.
- Validation UX d'usage réel : non établi.

## Change Log

- 2026-11-15 — PR #411 ouverte, empilée sur #410 (`88abccd`).
- 2026-11-15 — Relecture traitée (`7167f11`, `4035910`) ; formes réelles (`61fcee2`, `d38e229`).
- 2026-11-15 — Fusion dans `main` après #410 (`8e881e0`).
- 2026-11-22 — En production avec `c015cc9` (12:13).
- 2026-11-23 — Story rédigée après coup (backfill BMAD), statut `done` ; preuve terrain et validation UX non établies.
