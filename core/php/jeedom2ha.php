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
 * Registered with jeedomdaemon via --callback. Without a reachable endpoint
 * the daemon exits immediately at startup on a non-200 response.
 *
 * Story 1.1: pure HTTP 200 stub, no Jeedom dependencies.
 * Full callback logic (daemon → Jeedom events, state updates) is out of scope
 * for Story 1.1 and will be implemented in a later story.
 */

try {
    header('Content-Type: application/json; charset=utf-8');
    http_response_code(200);
    echo json_encode(['status' => 'ok']);
} catch (\Throwable $e) {
    header('Content-Type: application/json; charset=utf-8');
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'Internal error']);
}
