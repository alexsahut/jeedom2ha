# Story 24.13 : Journaliser le motif d'échec d'un ordre renvoyé par Jeedom

Status: review

> Correctif court rédigé et implémenté par une session cloud déléguée (2026-11-12), à partir d'un constat de production : un ordre HA vers un équipement a été refusé par Jeedom et le démon n'a journalisé aucune cause. Aucun nom réel, aucune IP, aucune marque (CC-48). Aucun déploiement ni accès à la box : la preuve terrain reste à ClaudeBox.

## Story

En tant que mainteneur qui diagnostique un ordre Home Assistant resté sans effet,
je veux que la ligne de journal du démon donne le motif d'échec renvoyé par Jeedom,
afin de trouver la cause sans reproduire la panne ni ouvrir d'autres journaux.

**Parcours : démon.** Comportement standard attendu chez tout utilisateur (aucun cas propre à une installation).

## Contexte : faits établis dans le code (`origin/main` a6d8e95)

- `sync/command.py`, `_execute_exec_cmd` (`cmd::execCmd`) et sa fonction sœur `_execute_scenario_start` (`scenario::changeState`) ne gardaient que `_last_exec_error_reason` (`jeedom_rpc_error` / `jeedom_rpc_timeout`) : ni le code ni le message de `error` JSON-RPC, ni le statut HTTP, ni le type d'exception.
- Ligne observée en production (12/11), seule trace de l'échec :
  `[SYNC-CMD] eq_id=<eq> topic=jeedom2ha/<eq>/<cmd>/set reason_code=jeedom_rpc_error action=execute_command`.
  La cause réelle (un plugin tiers levait une exception, son authentification ayant expiré) n'apparaissait nulle part côté démon.

## Critères d'acceptation

1. **AC1 — détail JSON-RPC** : si Jeedom répond avec un membre `error`, la ligne WARNING `[SYNC-CMD]` existante (`action=execute_command` ou `action=execute_scenario_command`) se termine par `error_detail=code=<code> message=<message>` (un `error` non structuré donne `message=<texte>`).
2. **AC2 — HTTP** : un statut HTTP différent de 200 donne `error_detail=http_status=<statut>` ; le corps de la réponse n'est pas lu.
3. **AC3 — exception** : une exception (aiohttp, délai dépassé, réponse illisible, autre) donne `error_detail=exception=<Type>` : le type seul, ni message ni traceback.
4. **AC4 — secrets** : jamais l'apikey, jamais le corps de la requête. Les motifs `apikey=`, `api_key=`, `token=`, `password=` (aussi sous les formes `clé: valeur` et JSON) sont remplacés par `<clé>=***` ; la clé API du cœur configurée est aussi remplacée par `***` si elle apparaît telle quelle.
5. **AC5 — une ligne, bornée** : retours à la ligne et tabulations neutralisés (espaces), détail tronqué à 200 caractères (`RPC_ERROR_DETAIL_MAX_LEN`, suffixe `...`). Le masquage est fait avant la troncature.
6. **AC6 — contrats inchangés** : `reason_code` reste `jeedom_rpc_error` / `jeedom_rpc_timeout`, les autres champs et leur ordre sont inchangés ; `error_detail` est ajouté en dernier champ, seulement sur ces lignes d'échec d'appel Jeedom.
7. **AC7 — succès et autres lignes** : un succès ne porte aucun `error_detail` ; le détail est remis à zéro à chaque appel et n'est jamais repris par une ligne ultérieure (rejet sans appel, succès suivant).
8. **AC8 — API non configurée** : endpoint ou clé absents → `error_detail=jeedom_api_not_configured`, aucun appel.

## Tâches

- [x] T1 — Établir les faits (`_execute_exec_cmd`, `_execute_scenario_start`, `_log_cmd`).
- [x] T2 — Garder un détail sûr à chaque sortie en échec des deux fonctions (`_set_exec_error_detail`, `_rpc_error_payload_detail`, `_rpc_exception_detail`, `_sanitize_rpc_error_detail`).
- [x] T3 — Ajouter `error_detail=` à la ligne WARNING existante depuis `_log_cmd` (seulement pour `reason_code` RPC et les actions `execute_command` / `execute_scenario_command`).
- [x] T4 — Tests (`resources/daemon/tests/unit/test_story_24_13_journal_erreur_rpc.py`, 21 cas) : erreur JSON-RPC avec message, `error` non structuré, apikey / token / password / JSON / clé du cœur masqués, HTTP 500, exception aiohttp, réponse illisible, timeout, message long tronqué, message multiligne, API non configurée, succès sans `error_detail`, pas de détail résiduel après un échec, chemin scénario (erreur JSON-RPC, timeout, HTTP 503, succès).
- [ ] T5 — Preuve terrain (ClaudeBox) : lors d'un prochain échec réel d'un ordre, la ligne WARNING `[SYNC-CMD]` du démon porte `error_detail=` avec le motif renvoyé par Jeedom, sans secret.

## Garde-fous

- Ajouts seuls dans `resources/daemon/` (garde 25.4 : aucune ligne retirée, rien à déclarer). Vérifié explicitement contre `origin/main` (a6d8e95) : `git diff origin/main --numstat -- resources/daemon` → 73 ajouts, 0 retrait. Le type d'exception est lu par `sys.exc_info()` pour ne pas modifier les clauses `except` existantes.
- `desktop/js/jeedom2ha_mapping_override.js` non modifié (garde 24.2).
- Aucun changement de routage, de discovery, de topic ni d'abonnement MQTT.

## Dev Agent Record

### Agent Model Used

Claude Opus 5.5 (session Claude Code cloud déléguée).

### Implementation Notes

- Format : `error_detail` est le dernier champ de la ligne, non entre guillemets ; sa valeur peut contenir des espaces (`code=... message=...`). Un lecteur de journal doit donc prendre tout ce qui suit `error_detail=` jusqu'à la fin de la ligne.
- L'état partagé `_last_exec_error_detail` suit le motif existant de `_last_exec_error_reason` : il est posé juste avant le `return False`, sans `await` entre la pose et la journalisation.

### Tests

- `python -m pytest` : 3053 passed, 9 deselected (dont 21 dans `test_story_24_13_journal_erreur_rpc.py`).
- `flake8 resources/daemon tests` : 0 erreur.
- `node --test tests/unit/*.node.test.js` : 1214 tests, 1214 pass, 0 fail.

### File List

- `resources/daemon/sync/command.py` (modifié, ajouts seuls)
- `resources/daemon/tests/unit/test_story_24_13_journal_erreur_rpc.py` (nouveau)
- `_bmad-output/implementation-artifacts/24-13-journaliser-le-motif-d-echec-d-un-ordre-renvoye-par-jeedom.md` (nouveau)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (entrée 24-13 sous pe-epic-24)

### Points ouverts

- Le message d'erreur JSON-RPC vient de Jeedom ou d'un plugin tiers : au-delà des motifs masqués, il peut contenir des noms d'équipements. Il est journalisé au niveau WARNING du démon, comme le reste de la ligne.
- Les autres appels JSON-RPC du démon (lecture fraîche d'état, synchronisation) ne sont pas concernés par ce correctif.
