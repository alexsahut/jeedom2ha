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

/**
 * Callback stub — daemon → Jeedom
 *
 * This file is the callback endpoint registered with jeedomdaemon via --callback.
 * Without it the daemon exits immediately on a 404 at startup.
 *
 * Story 1.1: minimal stub — returns HTTP 200 so the daemon stays alive.
 * Full callback logic (state updates, events) is out of scope for Story 1.1
 * and will be implemented in a later story.
 */

try {
    require_once __DIR__ . '/../../../core/php/core.inc.php';

    header('Content-Type: application/json');
    http_response_code(200);
    echo json_encode(['status' => 'ok']);

} catch (Exception $e) {
    header('Content-Type: application/json');
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'Internal error']);
    log::add('jeedom2ha', 'error', '[CALLBACK] ' . $e->getMessage());
}
