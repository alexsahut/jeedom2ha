# Story 24.12 : Boutons d'équipement routés vers Jeedom

Status: review

> Correctif court rédigé et implémenté par une session cloud déléguée (2026-11-12), à partir d'un constat de ClaudeBox du 01/11 (« non prouvé »). Le défaut est désormais **prouvé par test** avant correction. Aucun nom réel ni IP (CC-48). Aucun déploiement ni accès à la box : la preuve terrain (appui réel dans HA) reste à ClaudeBox et Alexandre.

## Story

En tant qu'utilisateur qui voit dans Home Assistant un bouton publié par jeedom2ha pour une commande d'équipement,
je veux qu'un appui sur ce bouton exécute la commande Jeedom correspondante,
afin que le bouton fasse ce qu'il annonce, comme les boutons de scénario.

**Parcours : démon.** Comportement standard attendu chez tout utilisateur (aucun cas propre à une installation).

## Contexte : faits établis dans le code (`origin/main` avant correctif)

- La discovery publie les boutons d'équipement sur `jeedom2ha/<eq_id>/cmd` : `mapping/button.py:38` (`ButtonMapper`), `mapping/fallback.py:54` (`FallbackMapper`, bouton de repli), et `discovery/publisher.py:920-945` (`_build_button_payload` : `command_topic` du mapping, sinon `jeedom2ha/<eq_id>/cmd` ; aucun `payload_press`, donc HA envoie son défaut `PRESS`).
- Le pont MQTT est bien abonné à `jeedom2ha/+/cmd` (`transport/mqtt_client.py:32`, commentaire « scenario button commands ») ; un message retenu sur un topic de commande y est déjà ignoré (garde 24.7 I4).
- `sync/command.py` ne routait `/cmd` que pour `jeedom2ha/scenario_<id>/cmd` (`handle_command_message`, regex `_SCENARIO_CMD_TOPIC_RE`). Pour `jeedom2ha/<eq_id>/cmd`, `_parse_topic` ne reconnaissait aucun motif → rejet `invalid_command_topic`. Pour un bouton secondaire publié sur un topic de nœud (`jeedom2ha/<eq>/<cmd>/set`), `_expected_command_topics` ne connaissait pas le type `button` → rejet `topic_not_published_by_discovery`.
- Reproduction (test `test_story_24_12_boutons_equipement.py`, avant correctif) : 13 échecs, dont les deux cas de référence :
  - `[SYNC-CMD] eq_id=- topic=jeedom2ha/9120/cmd reason_code=invalid_command_topic action=reject_command` (bouton mono-entité) ;
  - `[SYNC-CMD] eq_id=9121 topic=jeedom2ha/9121/91219/set reason_code=topic_not_published_by_discovery action=reject_command` (bouton secondaire).
  Aucune commande Jeedom n'était appelée.

## Critères d'acceptation

1. **AC1 — mono-entité** : `PRESS` sur `jeedom2ha/<eq_id>/cmd` d'un bouton d'équipement publié et vivant exécute `cmd::execCmd` sur SA commande action, exactement une fois, sans option ; aucun état n'est publié (bouton sans état).
2. **AC2 — secondaire** : `PRESS` sur le topic de commande d'un bouton secondaire (topic relu dans sa discovery) exécute uniquement SA commande, exactement une fois. Le topic d'équipement n'est jamais routé vers un secondaire qui ne le publie pas.
3. **AC3 — payload** : seul le payload configuré déclenche (`reason_details["payload_press"]` s'il existe, sinon `PRESS`, comparaison exacte) ; tout autre payload est refusé (`invalid_command_payload`).
4. **AC4 — message retenu** : un message retenu sur le topic d'un bouton (mono ou secondaire) est ignoré (même garde que 24.7, `retained_command_ignored`), un message direct passe.
5. **AC5 — commande liée** : seules les commandes du mapping du bouton sont candidates, et parmi elles seules les commandes `action` de sous-type `other` (un appui ne porte pas de valeur) ; jamais une commande `info`. Aucune candidate → `missing_action_command` ; plusieurs (ex. switch forcé en bouton : ON et OFF) → `ambiguous_button_action`, jamais devinée.
6. **AC6 — cible inconnue ou non publiée** : équipement inconnu, bouton non publié ou non vivant, entité indisponible → rien n'est exécuté (codes existants).
7. **AC7 — non-régression** : boutons de scénario inchangés (`scenario::changeState`), switch, cover, vanne et portail inchangés ; les suites existantes restent vertes.

## Tâches

- [x] T1 — Établir les faits et reproduire le défaut par un test qui échoue (AC1, AC2).
- [x] T2 — Router `jeedom2ha/<eq_id>/cmd` (`_BUTTON_CMD_TOPIC_RE`, canal `press`) ; topic attendu d'un bouton = celui de sa discovery (`_expected_command_topics`).
- [x] T3 — Traduire un appui (`_translate_button_command`) avec les garde-fous AC3 et AC5.
- [x] T4 — Tests : mono-entité, secondaire, repli, payloads inattendus, payload configuré, commande inexistante, info, sous-types à valeur, ambiguïté, non publié, message retenu / direct, non-régression scénario / switch / multi-entité / cover (vanne et portail : suites 24.8 et 24.7).
- [ ] T5 — Preuve terrain (ClaudeBox / Alexandre) : appui réel dans HA sur un bouton d'équipement, une seule exécution vue dans le journal Jeedom, journal démon `reason_code=command_executed`.

## Garde-fous

- Ajouts seuls dans `resources/daemon/` (garde 25.4 : aucune ligne retirée, rien à déclarer).
- Aucun changement de discovery, de topic publié ni d'abonnement MQTT : seul le routage entrant change.
- Pas de politique de confirmation nouvelle : un bouton reste `stateless`.

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée).

### Implementation Notes

- `sync/command.py` (ajouts seuls) :
  - `_BUTTON_CMD_TOPIC_RE`, `_BUTTON_DEFAULT_PAYLOAD_PRESS`, `_BUTTON_PRESSABLE_SUB_TYPES` ;
  - `_parse_topic` : `jeedom2ha/<eq_id>/cmd` → canal `press` (le routage reste conditionné à un candidat publié qui expose CE topic, `_resolve_runtime_target` inchangé) ;
  - `_expected_command_topics` : pour `button`, le topic exact de `_build_button_payload` (`reason_details.get("command_topic", "jeedom2ha/<eq_id>/cmd")`) ;
  - `_translate_command` : un mapping `button` passe par `_translate_button_command` quelle que soit la forme du topic (déjà apparié à la discovery du bouton) ;
  - `_translate_button_command` : payload exact, unique commande `action`/`other` du mapping, famille `button_press` (politique `stateless` par défaut).
- Les boutons de scénario gardent leur chemin (`_SCENARIO_CMD_TOPIC_RE` testé en premier, inchangé).

### Tests

- `python -m pytest` : 2867 passed, 9 deselected (dont 33 nouveaux dans `resources/daemon/tests/unit/test_story_24_12_boutons_equipement.py`).
- `flake8 resources/daemon tests` : 0 erreur.
- `node --test tests/unit/*.node.test.js` : 1214 tests, 1214 pass, 0 fail (garde 25.4 vert : aucune ligne retirée sous `resources/daemon/`).

### File List

- `resources/daemon/sync/command.py` (modifié, ajouts seuls)
- `resources/daemon/tests/unit/test_story_24_12_boutons_equipement.py` (nouveau)
- `_bmad-output/implementation-artifacts/24-12-boutons-equipement-routes-vers-jeedom.md` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (entrée 24-12 sous pe-epic-24)

### Points ouverts

- **Bouton secondaire** : aucun mapper natif n'en produit aujourd'hui ; le seul chemin réel est un override de type (ex. secondaire switch forcé en bouton), dont les commandes ON et OFF sont alors refusées comme ambiguës. Choisir la commande désignée par l'override (clé `eq:cmd`) demanderait de la conserver dans `apply_type_override` : hors périmètre, à trancher si le besoin existe.
- **Bouton de repli** (`FallbackMapper`) : il retient la première commande action quel que soit son sous-type ; un repli sur une action slider / message / couleur / liste est publié dans HA mais un appui est refusé (`missing_action_command`) plutôt que d'exécuter l'action sans valeur. Le signaler dans la surface (ou ne pas publier ce repli) relèverait d'une autre story.
- Preuve terrain T5 à faire après fusion.
