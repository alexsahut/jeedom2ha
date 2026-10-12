<?php
/* This file is part of Jeedom.
*
* Jeedom is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* Jeedom is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with Jeedom. If not, see <http://www.gnu.org/licenses/>.
*/

/*
 * Story 19.6 (AC1, AC2, AC3, AC4, AC5, AC8) — budget fixe du relais PHP.
 *
 * Fonctions PURES, sans dépendance au cœur Jeedom (pas de core.inc.php) :
 * chargé par core/ajax/jeedom2ha.ajax.php et directement par les tests CI
 * (tests/unit/test_story_19_6_php_relay.php), comme jeedom2ha_state_listeners.php.
 */

if (!defined('JEEDOM2HA_ACTION_BUDGET_R')) {
    define('JEEDOM2HA_ACTION_BUDGET_R', 60);
    define('JEEDOM2HA_ACTION_BUDGET_RESERVE_S', 5);
    define('JEEDOM2HA_ACTION_BUDGET_STATUS_TIMEOUT_S', 3);
    define('JEEDOM2HA_ACTION_BUDGET_CLICK_READ_DEADLINE_S', 10);
    define('JEEDOM2HA_ACTION_BUDGET_REALIGN_TIMEOUT_S', 3);
}

// Story A1 — relais dont la durée suit la taille du parc (scanTopology, exportDiagnostic,
// getDiagnostics) : même budget fixe R que les actions Publier/Supprimer (motif (b') de 19-6).
// Relais indépendants de la taille du parc (testMqttConnection, getMappingOverrides) : budget
// court fixe, inchangé depuis l'origine.
if (!defined('JEEDOM2HA_RELAY_BUDGET_SHORT_S')) {
    define('JEEDOM2HA_RELAY_BUDGET_SHORT_S', 15);
}

function jeedom2ha_action_deadline_s(): int {
    return JEEDOM2HA_ACTION_BUDGET_R - JEEDOM2HA_ACTION_BUDGET_RESERVE_S;
}

/** AC1 — ligne de journal (info) figée par un test : intention, portée, R, reserve_s, deadline_s, durée mesurée. */
function jeedom2ha_build_action_budget_log_line(
    string $intention,
    string $portee,
    int $r,
    int $reserveS,
    int $deadlineS,
    float $durationS
): string {
    return sprintf(
        '[ACTION-BUDGET] intention=%s portee=%s R=%d reserve_s=%d deadline_s=%d duration_s=%.3f',
        $intention,
        $portee,
        $r,
        $reserveS,
        $deadlineS,
        $durationS
    );
}

/**
 * AC5 — message d'erreur pour le second cas (démon joignable, action non terminée dans R).
 * Chaîne brute (pas de __()) : ce fichier reste chargeable sans le cœur Jeedom (motif
 * jeedom2ha_state_listeners.php) ; la traduction éventuelle relève de l'appelant runtime.
 */
function jeedom2ha_action_timeout_message(): string {
    // Correction de revue (bloc C) — le démon est celui du plugin, pas Home Assistant.
    return 'L\'action Home Assistant dure plus longtemps que prévu (plus de 60 s). '
        . 'Elle peut se poursuivre côté démon : actualisez la page dans un instant pour voir le résultat.';
}

/** AC3 / AC5 — message d'erreur pour un démon injoignable (statut préalable ou de diagnostic). */
function jeedom2ha_action_daemon_unreachable_message(): string {
    return 'Le démon ne répond pas (timeout API) — vérifiez qu\'il est bien démarré';
}

/**
 * Revue Codex P2 (PR #189, tour 6) — message d'erreur pour une réponse démon non-JSON /
 * échec immédiat (par exemple un HTTP 500), distinct du vrai dépassement d'AC5 : la durée
 * mesurée de l'appel est très inférieure à R, ce n'est donc pas un dépassement du budget.
 */
function jeedom2ha_action_daemon_error_message(): string {
    return 'Le démon a renvoyé une erreur pendant l\'action Home Assistant — consultez les logs du plugin';
}

/**
 * AC1, AC3, AC4, AC5, AC8 — orchestration pure de l'appel /action/execute.
 * Toute dépendance externe est injectée : aucun accès direct au démon ni au cœur Jeedom.
 * Ordre imposé (AC3) : sonde de statut, puis lecture au clic (publier), puis l'action.
 *
 * @param string   $intention          'publier' ou 'supprimer'
 * @param array    $params             payload de base (intention, portee, selection, ...)
 * @param callable $probeStatus        function(int $timeoutS, int $maxAttempts): ?array — GET /system/status
 * @param callable|null $collectClickValues function(): ?array — lecture au clic (publier seulement, déjà bornée par l'appelant, AC2)
 * @param callable $callAction         function(array $params, int $timeoutS): ?array — POST /action/execute
 * @param callable $realign            function(array $daemonResult): void — réalignement (AC4), no-op si non applicable
 * @param callable $log                function(string $level, string $message): void — journal niveau + message
 *                                     (correction de revue, bloc C) : 'info' pour la ligne de budget (AC1),
 *                                     'error' quand le démon est injoignable (statut préalable ou second statut),
 *                                     'warning' pour le dépassement d'AC5, 'warning' pour le refus 409 (AC8).
 * @param callable $now                function(): float — horloge injectable pour mesurer la durée de l'appel
 * @return array résultat du démon (payload /action/execute)
 * @throws Exception message destiné à l'UI
 */
function jeedom2ha_dispatch_action_relay(
    string $intention,
    array $params,
    callable $probeStatus,
    ?callable $collectClickValues,
    callable $callAction,
    callable $realign,
    callable $log,
    callable $now
): array {
    $r         = JEEDOM2HA_ACTION_BUDGET_R;
    $reserveS  = JEEDOM2HA_ACTION_BUDGET_RESERVE_S;
    $deadlineS = jeedom2ha_action_deadline_s();

    // AC3 — sonde de statut AVANT toute lecture au clic et avant l'action.
    $status = $probeStatus(JEEDOM2HA_ACTION_BUDGET_STATUS_TIMEOUT_S, 1);
    if ($status === null) {
        $log('error', '[ACTION] ' . jeedom2ha_action_daemon_unreachable_message());
        throw new Exception(jeedom2ha_action_daemon_unreachable_message());
    }

    // AC2/AC3 — lecture au clic, publier seulement, après la sonde et avant l'action.
    if ($intention === 'publier' && $collectClickValues !== null) {
        $clickValues = $collectClickValues();
        if ($clickValues !== null) {
            $params['current_values'] = $clickValues;
        }
    }

    // AC1 — budget fixe transmis au démon, indépendant de la taille de la portée.
    $params['deadline_s'] = $deadlineS;

    $start    = $now();
    $result   = $callAction($params, $r);
    $duration = $now() - $start;

    $log('info', jeedom2ha_build_action_budget_log_line(
        $intention,
        (string)($params['portee'] ?? ''),
        $r,
        $reserveS,
        $deadlineS,
        $duration
    ));

    if ($result === null) {
        // Revue Codex P2 (PR #189, tour 6) — une réponse null avec une durée très inférieure
        // à R n'est pas un dépassement (par exemple un HTTP 500 immédiat côté démon) : pas de
        // second statut, pas de réalignement, message distinct de celui d'AC5.
        if ($duration < ($r - 1)) {
            $log('error', '[ACTION] ' . jeedom2ha_action_daemon_error_message());
            throw new Exception(jeedom2ha_action_daemon_error_message());
        }

        // AC5 — second statut de diagnostic (distinct de celui d'AC3), pour distinguer
        // un démon injoignable d'un démon joignable mais qui n'a pas répondu dans R.
        $status2 = $probeStatus(JEEDOM2HA_ACTION_BUDGET_STATUS_TIMEOUT_S, 1);
        if ($status2 === null) {
            $log('error', '[ACTION] ' . jeedom2ha_action_daemon_unreachable_message());
            throw new Exception(jeedom2ha_action_daemon_unreachable_message());
        }
        $log('warning', '[ACTION] ' . jeedom2ha_action_timeout_message());
        throw new Exception(jeedom2ha_action_timeout_message());
    }

    if (($result['code'] ?? null) === 'action_in_progress') {
        // AC8 — transmis tel quel à l'UI, sans réalignement ni second statut.
        $conflictMessage = (string)($result['message'] ?? 'Une action Home Assistant est déjà en cours.');
        $log('warning', '[ACTION] ' . $conflictMessage);
        throw new Exception($conflictMessage);
    }

    // AC4 — réalignement (délégué : la décision intention === 'publier' reste dans $realign).
    $realign($result);

    return $result;
}

/**
 * Story A1 — ligne de journal (info) du budget d'un relais dépendant de la taille du parc.
 * Pas de deadline_s : ces relais côté démon ne font aucune pause de lissage (voir ci-dessous).
 */
function jeedom2ha_build_relay_budget_log_line(string $relais, int $r, float $durationS): string {
    return sprintf('[RELAY-BUDGET] relais=%s R=%d duration_s=%.3f', $relais, $r, $durationS);
}

/** Story A1 — dépassement réel du budget R par un relais lecture/synchronisation (démon joignable). */
function jeedom2ha_relay_timeout_message(): string {
    return 'Le démon met plus longtemps que prévu à répondre (plus de ' . JEEDOM2HA_ACTION_BUDGET_R . ' s). '
        . 'Il est toujours actif : actualisez la page dans un instant pour voir le résultat.';
}

/**
 * Story A1 — orchestration pure d'un relais dont la durée dépend de la taille du parc
 * (scanTopology → /action/sync, exportDiagnostic et getDiagnostics → /system/diagnostics).
 *
 * Décision d'audit (A1/T1) : /action/sync et /system/diagnostics ne contiennent aucune pause de
 * lissage côté démon (les seules pauses d'`asyncio.sleep` sont celles de /action/execute et du
 * republish broker/HA, déclenché hors de ces relais). Il n'y a donc rien à plafonner :
 * `deadline_s` n'est PAS transmis (le démon l'ignorerait) et `action_pacing.py` n'est pas
 * modifié. Seul le budget fixe R (indépendant du parc) remplace l'ancien timeout de 15 s.
 *
 * Le message « injoignable » n'est émis que si une sonde de statut échoue après un échec ;
 * le message de dépassement n'est émis que si l'appel a réellement consommé le budget R.
 *
 * @param string   $relais      nom du relais (journal)
 * @param callable $call        function(int $timeoutS): ?array — appel démon, borné à R
 * @param callable $probeStatus function(int $timeoutS, int $maxAttempts): ?array — GET /system/status
 * @param callable $log         function(string $level, string $message): void
 * @param callable $now         function(): float — horloge injectable
 * @return array résultat du démon
 * @throws Exception message destiné à l'UI
 */
function jeedom2ha_dispatch_parc_relay(
    string $relais,
    callable $call,
    callable $probeStatus,
    callable $log,
    callable $now
): array {
    $r = JEEDOM2HA_ACTION_BUDGET_R;

    $start    = $now();
    $result   = $call($r);
    $duration = $now() - $start;

    $log('info', jeedom2ha_build_relay_budget_log_line($relais, $r, $duration));

    if ($result !== null) {
        return $result;
    }

    $status = $probeStatus(JEEDOM2HA_ACTION_BUDGET_STATUS_TIMEOUT_S, 1);
    if ($status === null) {
        $log('error', '[' . $relais . '] ' . jeedom2ha_action_daemon_unreachable_message());
        throw new Exception(jeedom2ha_action_daemon_unreachable_message());
    }
    if ($duration < ($r - 1)) {
        $log('error', '[' . $relais . '] ' . jeedom2ha_action_daemon_error_message());
        throw new Exception(jeedom2ha_action_daemon_error_message());
    }
    $log('warning', '[' . $relais . '] ' . jeedom2ha_relay_timeout_message());
    throw new Exception(jeedom2ha_relay_timeout_message());
}
