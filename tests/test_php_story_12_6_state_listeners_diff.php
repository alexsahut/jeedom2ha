<?php
// ARTEFACT — Story 12.6 (CC-45, AC10) : recalage des listeners d'état par différence. Fonction pure de différence
// (conserver / créer / supprimer), réalignement sur une base simulée de listeners (identifiants stables d'un
// réalignement à l'autre), échec du démon, listeners mal formés, doublons, câblage de syncStateListeners().
// Identifiants fictifs uniquement (CC-48).
// Exécution : php tests/test_php_story_12_6_state_listeners_diff.php

$root = dirname(__DIR__);
$passed = 0;
$failed = 0;

function check($label, $condition) {
    global $passed, $failed;
    if ($condition) {
        $passed++;
        echo "  ✔ {$label}\n";
        return;
    }
    $failed++;
    echo "  ✖ {$label}\n";
}

require_once $root . '/core/php/jeedom2ha_state_listeners.php';

if (!function_exists('jeedom2ha_state_listener_plan')) {
    echo "  ✖ jeedom2ha_state_listener_plan() absente\n";
    echo "\n0 réussis, 1 échoués\n";
    exit(1);
}

// ---------------------------------------------------------------------------
// Base simulée : id => description (eq_id, cmd_id, events), comme listener::byClass + getOption/getEvent.
// ---------------------------------------------------------------------------
class FakeListenerStore {
    public $rows = array();
    public $nextId = 42001;
    public $created = array();
    public $removed = array();
    public $trace = array();
    public $failCreateAt = null;
    public $failRemoveAt = null;

    public function add($eqId, $cmdId, $events = null) {
        $id = $this->nextId++;
        $this->rows[$id] = array(
            'eq_id' => $eqId,
            'cmd_id' => $cmdId,
            'events' => $events === null ? array('#' . $cmdId . '#') : $events,
        );
        return $id;
    }

    public function ids() {
        $ids = array_keys($this->rows);
        sort($ids);
        return $ids;
    }

    public function realign($response, $withDescribe = true, &$stats = null) {
        $store = $this;
        $warnings = array();
        $args = array(
            function () use ($response, $store) {
                $store->trace[] = 'fetch';
                if ($response instanceof \Throwable) { throw $response; }
                return $response;
            },
            function () use ($store) { $store->trace[] = 'list'; return $store->ids(); },
            function ($id) use ($store) {
                if ($store->failRemoveAt !== null && count($store->removed) + 1 === $store->failRemoveAt) {
                    throw new Exception('db remove');
                }
                $store->trace[] = 'remove:' . $id;
                $store->removed[] = $id;
                unset($store->rows[$id]);
            },
            function (int $eqId, int $cmdId) use ($store) {
                if ($store->failCreateAt !== null && count($store->created) + 1 === $store->failCreateAt) {
                    throw new Exception('db save');
                }
                $id = $store->add($eqId, $cmdId);
                $store->trace[] = 'create:' . $eqId . '/' . $cmdId;
                $store->created[] = $id;
            },
            function (string $m) use (&$warnings) { $warnings[] = $m; },
        );
        if ($withDescribe) {
            $args[] = function ($id) use ($store) {
                if (!isset($store->rows[$id])) { throw new Exception('listener disparu'); }
                $row = $store->rows[$id];
                if ($row === 'boom') { throw new Exception('description illisible'); }
                return array('id' => $id, 'eq_id' => $row['eq_id'], 'cmd_id' => $row['cmd_id'], 'events' => $row['events']);
            };
            $count = jeedom2ha_realign_state_listeners($args[0], $args[1], $args[2], $args[3], $args[4], $args[5], $stats);
        } else {
            $count = jeedom2ha_realign_state_listeners($args[0], $args[1], $args[2], $args[3], $args[4]);
        }
        return array($count, $warnings);
    }

    public function reset() {
        $this->created = array();
        $this->removed = array();
        $this->trace = array();
    }
}

function targets_response(array $pairs) {
    $listeners = array();
    foreach ($pairs as $p) {
        $listeners[] = array('eq_id' => $p[0], 'cmd_id' => $p[1], 'ha_type' => 'sensor', 'state_topic' => 'jeedom2ha/' . $p[0] . '/state');
    }
    return array('status' => 'ok', 'listeners' => $listeners);
}

$parc = array(array(10, 101), array(10, 102), array(11, 111));

// ---------------------------------------------------------------------------
echo "Fonction pure de différence\n";
// ---------------------------------------------------------------------------
$targets = array(array('eq_id' => 10, 'cmd_id' => 101), array('eq_id' => 11, 'cmd_id' => 111));
$existing = array(
    array('id' => 1, 'eq_id' => 10, 'cmd_id' => 101, 'events' => array('#101#')),
    array('id' => 2, 'eq_id' => 11, 'cmd_id' => 111, 'events' => '["#111#"]'),
);
$plan = jeedom2ha_state_listener_plan($targets, $existing);
check('cible identique : tout conservé', array_column($plan['keep'], 'id') === array(1, 2));
check('cible identique : 0 création', count($plan['create']) === 0);
check('cible identique : 0 suppression', count($plan['remove']) === 0);
check('événements en chaîne JSON acceptés (selon la version du cœur)', in_array(2, array_column($plan['keep'], 'id'), true));

$plan = jeedom2ha_state_listener_plan(array_merge($targets, array(array('eq_id' => 12, 'cmd_id' => 121))), $existing);
check('ajout d\'une commande : 1 création', $plan['create'] === array(array('eq_id' => 12, 'cmd_id' => 121)));
check('ajout d\'une commande : 0 suppression', count($plan['remove']) === 0);

$plan = jeedom2ha_state_listener_plan(array($targets[0]), $existing);
check('retrait d\'une commande : 1 suppression (la bonne)', array_column($plan['remove'], 'id') === array(2));
check('retrait d\'une commande : 0 création', count($plan['create']) === 0);

$dup = array_merge($existing, array(array('id' => 3, 'eq_id' => 10, 'cmd_id' => 101, 'events' => array('#101#'))));
$plan = jeedom2ha_state_listener_plan($targets, $dup);
check('doublon : le premier relevé est conservé', array_column($plan['keep'], 'id') === array(1, 2));
check('doublon : le second est supprimé', array_column($plan['remove'], 'id') === array(3));

$plan = jeedom2ha_state_listener_plan(array_merge($targets, array($targets[0])), $existing);
check('cible renvoyée deux fois par le démon : aucune création en double', count($plan['create']) === 0);
$plan = jeedom2ha_state_listener_plan(array(array('eq_id' => 12, 'cmd_id' => 121), array('eq_id' => 12, 'cmd_id' => 121)), array());
check('nouvelle cible en double : une seule création', count($plan['create']) === 1);

$plan = jeedom2ha_state_listener_plan(array(), $existing);
check('liste valide vide : tout supprimé', array_column($plan['remove'], 'id') === array(1, 2));

$bad = array(
    array('id' => 1, 'eq_id' => 10, 'cmd_id' => 101, 'events' => array('#101#', '#102#')),
    array('id' => 2, 'eq_id' => 11, 'cmd_id' => 111, 'events' => array('#999#')),
);
$plan = jeedom2ha_state_listener_plan($targets, $bad);
check('événements multiples ou différents : remplacés (supprimés)', array_column($plan['remove'], 'id') === array(1, 2));
check('événements multiples ou différents : recréés', count($plan['create']) === 2);

$wrongEq = array(array('id' => 1, 'eq_id' => 99, 'cmd_id' => 101, 'events' => array('#101#')));
$plan = jeedom2ha_state_listener_plan(array($targets[0]), $wrongEq);
check('eq_id différent pour la même commande : remplacé',
    array_column($plan['remove'], 'id') === array(1) && $plan['create'] === array($targets[0]));

$malformed = array(
    array('id' => 1, 'eq_id' => null, 'cmd_id' => 101, 'events' => array('#101#')),
    array('id' => 2, 'eq_id' => 11, 'cmd_id' => 'abc', 'events' => array('#111#')),
    array('id' => 3, 'eq_id' => 10, 'cmd_id' => 102, 'events' => null),
    array('id' => 4, 'eq_id' => 10, 'cmd_id' => 102, 'events' => '{pas du json'),
    array('id' => 5, 'eq_id' => 10, 'cmd_id' => 102, 'events' => array()),
    array('id' => 6, 'eq_id' => 10, 'cmd_id' => 0, 'events' => array('#0#')),
    'pas un tableau',
);
$plan = jeedom2ha_state_listener_plan(array(array('eq_id' => 10, 'cmd_id' => 101), array('eq_id' => 10, 'cmd_id' => 102)), $malformed);
check('listeners mal formés : jamais conservés', count($plan['keep']) === 0);
check('listeners mal formés : tous supprimés (sauf l\'entrée sans identité)', array_column($plan['remove'], 'id') === array(1, 2, 3, 4, 5, 6));
check('listeners mal formés : cibles recréées', count($plan['create']) === 2);

$numeric = array(array('id' => 1, 'eq_id' => '10', 'cmd_id' => '101', 'events' => array('#101#')));
$plan = jeedom2ha_state_listener_plan(array($targets[0]), $numeric);
check('options numériques en chaîne (stockage JSON du cœur) : conservé', array_column($plan['keep'], 'id') === array(1));

$zeroEq = array(array('id' => 1, 'eq_id' => 0, 'cmd_id' => 101, 'events' => array('#101#')));
$plan = jeedom2ha_state_listener_plan(array(array('eq_id' => 0, 'cmd_id' => 101)), $zeroEq);
check('revue — cible à eq_id 0 (admise par le contrat) : listener conservé, pas recréé à chaque tic',
    array_column($plan['keep'], 'id') === array(1) && !$plan['create'] && !$plan['remove']);
$negEq = array(array('id' => 1, 'eq_id' => -1, 'cmd_id' => 101, 'events' => array('#101#')));
$plan = jeedom2ha_state_listener_plan(array(array('eq_id' => 0, 'cmd_id' => 101)), $negEq);
check('revue — eq_id négatif : mal formé, remplacé', array_column($plan['remove'], 'id') === array(1));

// ---------------------------------------------------------------------------
echo "\nRéalignement sur une base simulée\n";
// ---------------------------------------------------------------------------
$store = new FakeListenerStore();
list($c, $w) = $store->realign(targets_response($parc));
check('premier enregistrement : 3 créés', count($store->created) === 3 && $c === 3);
$before = $store->ids();

$store->reset();
$stats = null;
list($c, $w) = $store->realign(targets_response($parc), true, $stats);
check('cible identique : 0 création', count($store->created) === 0);
check('cible identique : 0 suppression', count($store->removed) === 0);
check('cible identique : identifiants inchangés', $store->ids() === $before);
check('cible identique : nombre en place rendu', $c === 3);
check('statistiques : 3 conservés, 0 créé, 0 supprimé',
    $stats === array('kept' => 3, 'created' => 0, 'removed' => 0));

$store->reset();
list($c, $w) = $store->realign(targets_response($parc));
check('deuxième tic : identifiants toujours inchangés', $store->ids() === $before && !$store->created && !$store->removed);

$store->reset();
list($c, $w) = $store->realign(targets_response(array_merge($parc, array(array(12, 121)))));
check('ajout d\'une commande : 1 création', count($store->created) === 1 && count($store->removed) === 0);
check('ajout d\'une commande : anciens identifiants conservés', count(array_intersect($before, $store->ids())) === 3);

$store->reset();
list($c, $w) = $store->realign(targets_response($parc));
check('retrait d\'une commande : 1 suppression', count($store->removed) === 1 && count($store->created) === 0);
check('retrait d\'une commande : identifiants d\'origine restants', $store->ids() === $before);

$dupId = $store->add(10, 101);
$store->reset();
list($c, $w) = $store->realign(targets_response($parc));
check('doublon : nettoyé', $store->removed === array($dupId) && $store->ids() === $before);

$store->reset();
$store->trace = array();
$badId = $store->add(10, 102, array('#102#', '#999#'));
$store->rows[$before[1]]['events'] = array('#555#');
$store->reset();
list($c, $w) = $store->realign(targets_response($parc));
check('listener mal formé d\'une cible voulue : remplacé (créer puis supprimer)',
    $store->trace === array('fetch', 'list', 'create:10/102', 'remove:' . $before[1], 'remove:' . $badId));

// Démon en échec, réponse invalide : rien supprimé.
$store = new FakeListenerStore();
$store->realign(targets_response($parc));
$before = $store->ids();
foreach (array(
    'exception à la récupération' => new Exception('timeout'),
    'démon muet (null)' => null,
    'status != ok' => array('status' => 'error'),
    'listeners absent' => array('status' => 'ok'),
    'cible mal formée' => array('status' => 'ok', 'listeners' => array(array('eq_id' => 10, 'cmd_id' => 101), array('cmd_id' => 0))),
) as $label => $response) {
    $store->reset();
    list($c, $w) = $store->realign($response);
    check('démon en échec (' . $label . ') : aucune suppression ni création',
        $c === null && !$store->removed && !$store->created && $store->ids() === $before && count($w) === 1);
}

$store->reset();
list($c, $w) = $store->realign(array('status' => 'ok', 'listeners' => array()));
check('cible valide vide : tout supprimé (plus rien de publié, inchangé)', count($store->removed) === 3 && $c === 0);

// Création interrompue : aucune suppression ; suppression interrompue : avertissement.
$store = new FakeListenerStore();
$store->realign(targets_response(array(array(10, 101))));
$store->rows[$store->ids()[0]]['events'] = array('#999#');
$store->reset();
$store->failCreateAt = 1;
list($c, $w) = $store->realign(targets_response(array(array(10, 101), array(11, 111))));
check('création interrompue : null, aucune suppression', $c === null && !$store->removed && count($w) === 1);
$store->failCreateAt = null;
$store->failRemoveAt = 1;
$store->reset();
list($c, $w) = $store->realign(targets_response(array(array(10, 101), array(11, 111))));
check('suppression interrompue : créations faites, un avertissement', count($store->created) === 2 && count($w) === 1 && $c === 2);

// Description qui lève : listener remplacé.
$store = new FakeListenerStore();
$store->realign(targets_response(array(array(10, 101))));
$old = $store->ids()[0];
$store->rows[$old] = 'boom';
$store->reset();
list($c, $w) = $store->realign(targets_response(array(array(10, 101))));
check('description illisible : listener remplacé', $store->removed === array($old) && count($store->created) === 1);

// Compatibilité 19.5 : sans description, tout est remplacé.
$store = new FakeListenerStore();
$store->realign(targets_response($parc));
$store->reset();
list($c, $w) = $store->realign(targets_response($parc), false);
check('sans fonction de description (appel historique) : tout remplacé', count($store->created) === 3 && count($store->removed) === 3);

// ---------------------------------------------------------------------------
echo "\nCâblage de syncStateListeners()\n";
// ---------------------------------------------------------------------------
$class = file_get_contents($root . '/core/class/jeedom2ha.class.php');
$start = strpos($class, 'public static function syncStateListeners(');
$end = strpos($class, 'public static function stateListener(');
$body = ($start !== false && $end !== false) ? substr($class, $start, $end - $start) : '';
check('syncStateListeners passe une description (options et événements)',
    strpos($body, "getOption('cmd_id')") !== false && strpos($body, "getOption('eq_id')") !== false
    && strpos($body, 'getEvent()') !== false && strpos($body, 'getId()') !== false);
check('syncStateListeners récupère les statistiques', strpos($body, '$stats') !== false);
check('plus de journal « (re)enregistré(s) » à chaque resynchronisation', strpos($body, '(re)enregistré(s)') === false);

echo "\n{$passed} réussis, {$failed} échoués\n";
exit($failed === 0 ? 0 : 1);
