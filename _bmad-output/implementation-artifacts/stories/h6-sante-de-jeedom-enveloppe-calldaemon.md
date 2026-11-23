# Story H6 : « Santé de Jeedom » — la route accepte l'enveloppe `callDaemon`

Status: done

Epic: (Chantier hors cycle BMAD 2026-11, rattachement rétrospectif)

Story Key (sprint-status): `h6-sante-de-jeedom-enveloppe-calldaemon`

> **Story rédigée après coup le 23/11/2026 : le développement n'a pas suivi le cycle BMAD.**
> Sources : la PR #415 (fusion `c015cc9`), sa description et ses commits, lus par l'API REST GitHub ; pour la production, seuls les faits transmis le 23/11 (voir « Faits de production »). Aucun accès à la box ni à Home Assistant pour cette rédaction. Ce qui ne se déduit pas de ces sources est écrit « non établi ».

## Story

En tant qu'utilisateur qui coche « Publier la santé de Jeedom »,
je veux que l'appareil « Santé de Jeedom » soit réellement publié par un Jeedom réel,
afin que l'option livrée par H5 fonctionne hors des tests.

**Parcours : démon (route) + PHP (relevé).** Correctif court de H5 (#414).

## Contexte (constat)

- Sur la démo, avant la production, `POST /action/system_health` répond **400** et aucun appareil n'est publié.
- Cause (PR) : `jeedom2ha::callDaemon` enveloppe tout POST dans `{"action", "payload", "request_id", "timestamp"}` ; la route lisait `enabled` à la racine du corps. Les tests de #414 postaient le corps nu et ne reproduisaient donc pas l'appel réel.

## Critères d'acceptation (tels que livrés)

1. **AC1 — Enveloppe acceptée.** `_handle_action_system_health` travaille sur `body["payload"]` quand c'est un objet, comme les autres routes ; le corps nu reste accepté. Seule modification du démon : 4 lignes ajoutées, aucune retirée.
2. **AC2 — Enveloppe exacte testée.** `enabled: true` avec un `snapshot` → publication des 7 entités ; `enabled: false` → purge complète ; enveloppe sans `enabled`, `enabled` non booléen, `snapshot` absent ou invalide → le même 400 qu'avant.
3. **AC3 — Contrat PHP figé.** `callDaemon` place la charge sous `payload` ; la purge part avec une charge non vide (`{"enabled": false}`) ; `jeedom2ha_system_health_response_ok` accepte 200 et refuse 400, 503, purge incomplète et démon injoignable.
4. **AC4 — Relevé toujours encodable en JSON (relecture P3).** Un nom de plugin, un identifiant ou une version en UTF-8 invalide est assaini à la construction du relevé (`mb_convert_encoding`, à défaut `iconv`, sinon remplacement direct) ; `callDaemon` n'est pas modifié.

## UI Impact

- **UI Impact:** Non

## Tâches

- [x] T1 — Correctif de la route (`resources/daemon/transport/http_server.py`, +4).
- [x] T2 — Assainissement UTF-8 du relevé (`core/php/jeedom2ha_system_health.php`).
- [x] T3 — Tests pytest et PHP sur l'enveloppe réelle.
- [x] T4 — Validation sur la démo avant la production (avec H5).
- [x] T5 — Mise en production : `c015cc9`, 22/11/2026 à 12:13 ; appareil « Santé de Jeedom » actif.

## Dev Agent Record

### Agent Model Used

Session Claude Code (signature de la PR) ; modèle exact : non établi.

### Fusion

- PR #415, branche `fix/system-health-envelope`, tête `4a55227`, fusionnée le 20/11/2026 à 08:21 UTC : `c015cc9e30c038c58b429756bb6f001be196cd65`.
- Commits : `29f0f42` (enveloppe), `4a55227` (UTF-8 invalide).
- CI de la tête : verte.

### Fichiers

- `core/php/jeedom2ha_system_health.php`
- `resources/daemon/transport/http_server.py` (+4, aucune ligne retirée)
- `resources/daemon/tests/unit/test_story_system_health.py`
- `tests/test_php_story_system_health.php`

### Tests

- Résultat annoncé par la PR : `make test` 828 passés ; démon 2743 passés ; `flake8` vert ; tests PHP « Santé » : 69 vérifications. Rejouer : `make test`, `flake8`, `php tests/test_php_story_system_health.php`.

### Faits de production

- Démo validée avant la production (H5 + H6) ; le 400 trouvé sur la démo est la cause de cette story.
- `c015cc9` déployé en production le 22/11/2026 à 12:13.
- Appareil « Santé de Jeedom » actif ; 427 entités (relevé transmis ; périmètre exact du décompte : non établi).

## Change Log

- 2026-11-20 — PR #415 ouverte (`29f0f42`), puis `4a55227` (relecture P3).
- 2026-11-20 — Fusion dans `main` (`c015cc9`).
- 2026-11-22 — `c015cc9` en production (12:13).
- 2026-11-23 — Story rédigée après coup (backfill BMAD), statut `done`.
