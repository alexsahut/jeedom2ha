<?php
// ARTEFACT — story/system-health : appareil « Santé de Jeedom » (lecture seule). Relevé pur (plugins à démon propre,
// mises à jour, nombre de messages, version du cœur), gardes (plugin absent, sans méthode, qui lève une exception,
// sans démon), empreinte, pas du cron (désactivé par défaut : aucune lecture ni aucun appel ; purge unique à la
// désactivation) et câblage dans la classe. Identifiants et noms fictifs uniquement (CC-48).
// Exécution : php tests/test_php_story_system_health.php

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

require_once $root . '/core/php/jeedom2ha_system_health.php';

/** Faux objet `plugin` du cœur (mêmes méthodes publiques, Jeedom 4.4 à 4.6). */
class FakePlugin {
    public $id; public $name; public $active; public $own; public $state; public $throwOn;
    public function __construct($id, $name, $own = 1, $state = 'ok', $active = 1, $throwOn = null) {
        $this->id = $id; $this->name = $name; $this->own = $own; $this->state = $state; $this->active = $active;
        $this->throwOn = $throwOn;
    }
    private function maybeThrow($m) { if ($this->throwOn === $m) { throw new Exception('panne fictive'); } }
    public function getId() { $this->maybeThrow('getId'); return $this->id; }
    public function getName() { $this->maybeThrow('getName'); return $this->name; }
    public function isActive() { $this->maybeThrow('isActive'); return $this->active; }
    public function getHasOwnDeamon() { $this->maybeThrow('getHasOwnDeamon'); return $this->own; }
    public function deamon_info() {
        $this->maybeThrow('deamon_info');
        return $this->state === null ? null : array('state' => $this->state, 'launchable' => 'ok');
    }
}
/** Plugin d'un ancien cœur : pas de getHasOwnDeamon. */
class OldPlugin {
    public function getId() { return 'plugin_ancien'; }
    public function getName() { return 'Ancien'; }
}

// ---------------------------------------------------------------------------
echo "Relevé d'un plugin\n";
check('démon en marche (state ok) -> running vrai', jeedom2ha_system_health_plugin_row(new FakePlugin('plugin_a', 'Alpha'))
    === array('id' => 'plugin_a', 'name' => 'Alpha', 'running' => true));
check('démon arrêté (state nok) -> running faux', jeedom2ha_system_health_plugin_row(new FakePlugin('plugin_a', 'Alpha', 1, 'nok'))['running'] === false);
check('réponse inattendue de deamon_info -> running faux', jeedom2ha_system_health_plugin_row(new FakePlugin('plugin_a', 'Alpha', 1, null))['running'] === false);
check('deamon_info qui lève -> running faux, sans exception', jeedom2ha_system_health_plugin_row(new FakePlugin('plugin_a', 'Alpha', 1, 'ok', 1, 'deamon_info'))['running'] === false);
check('plugin sans démon propre -> rien', jeedom2ha_system_health_plugin_row(new FakePlugin('plugin_sans', 'Sans démon', 0)) === null);
check('plugin inactif -> rien', jeedom2ha_system_health_plugin_row(new FakePlugin('plugin_a', 'Alpha', 1, 'ok', 0)) === null);
check('jeedom2ha lui-même -> rien (déjà « État du pont »)', jeedom2ha_system_health_plugin_row(new FakePlugin('jeedom2ha', 'Jeedom2HA')) === null);
check('getId qui lève -> rien, sans exception', jeedom2ha_system_health_plugin_row(new FakePlugin('x', 'X', 1, 'ok', 1, 'getId')) === null);
check('getHasOwnDeamon qui lève -> rien', jeedom2ha_system_health_plugin_row(new FakePlugin('x', 'X', 1, 'ok', 1, 'getHasOwnDeamon')) === null);
check('cœur ancien sans getHasOwnDeamon -> rien', jeedom2ha_system_health_plugin_row(new OldPlugin()) === null);
check('plugin absent (null, tableau) -> rien', jeedom2ha_system_health_plugin_row(null) === null && jeedom2ha_system_health_plugin_row(array('id' => 'x')) === null);
check('nom vide -> identifiant', jeedom2ha_system_health_plugin_row(new FakePlugin('plugin_a', ''))['name'] === 'plugin_a');

// ---------------------------------------------------------------------------
echo "Relevé complet\n";
$plugins = array(
    new FakePlugin('plugin_z', 'Zêta'),
    new FakePlugin('plugin_sans', 'Sans démon', 0),
    new FakePlugin('plugin_b', 'Bêta', 1, 'nok'),
    new FakePlugin('plugin_err', 'En erreur', 1, 'ok', 1, 'deamon_info'),
    null,
    new FakePlugin('jeedom2ha', 'Jeedom2HA'),
    new FakePlugin('plugin_b', 'Bêta doublon'),
);
$readers = array(
    'plugins' => function () use ($plugins) { return $plugins; },
    'updates' => function () { return 3; },
    'messages' => function () { return '2'; },
    'core_version' => function () { return '4.5.1'; },
);
$snap = jeedom2ha_system_health_snapshot($readers);
check('démons triés par identifiant, sans doublon, sans plugin sans démon ni jeedom2ha',
    array_map(function ($d) { return $d['id']; }, $snap['daemons']) === array('plugin_b', 'plugin_err', 'plugin_z'));
check('le premier relevé d\'un identifiant en double est gardé', $snap['daemons'][0]['name'] === 'Bêta');
check('un plugin en erreur reste présent, arrêté', $snap['daemons'][1]['running'] === false);
check('compteurs et version lus', $snap['updates'] === 3 && $snap['messages'] === 2 && $snap['core_version'] === '4.5.1');
check('le relevé ne contient que des nombres pour les messages (jamais de texte)', !array_key_exists('message_text', $snap) && is_int($snap['messages']));
$broken = jeedom2ha_system_health_snapshot(array(
    'plugins' => function () { throw new Exception('liste illisible'); },
    'updates' => function () { throw new Exception('panne'); },
    'messages' => function () { return 'texte libre'; },
    'core_version' => function () { return array('x'); },
));
check('toutes les lectures en panne : relevé vide, sans exception',
    $broken === array('daemons' => array(), 'updates' => null, 'messages' => null, 'core_version' => null));
check('lecteurs absents : relevé vide', jeedom2ha_system_health_snapshot(array())
    === array('daemons' => array(), 'updates' => null, 'messages' => null, 'core_version' => null));
check('liste de messages (tableau) : seulement leur nombre', jeedom2ha_system_health_count(function () { return array('a', 'b'); }) === 2);
check('compteur négatif -> illisible', jeedom2ha_system_health_count(function () { return -1; }) === null);

echo "Base des agrégats « démons en service X/Y » (calculés par le démon sur ce même relevé)\n";
$six = array();
for ($i = 0; $i < 5; $i++) { $six[] = new FakePlugin('plugin_' . $i, 'P' . $i); }
$six[] = new FakePlugin('plugin_err', 'En erreur', 1, 'ok', 1, 'deamon_info');
$six[] = new FakePlugin('plugin_sans', 'Sans démon', 0);
$agg = jeedom2ha_system_health_snapshot(array('plugins' => function () use ($six) { return $six; }));
$runningFlags = array_map(function ($d) { return $d['running']; }, $agg['daemons']);
check('5 démons ok et 1 en exception : 6 lignes, 5 en marche, 1 arrêtée (l\'exception compte comme arrêtée)',
    count($agg['daemons']) === 6 && count(array_filter($runningFlags)) === 5);
$fp6 = jeedom2ha_system_health_fingerprint($agg);
$agg2 = $agg; $agg2['daemons'][5]['running'] = true;
check('le démon en panne qui redémarre change l\'empreinte (les trois valeurs sont renvoyées)', jeedom2ha_system_health_fingerprint($agg2) !== $fp6);

// ---------------------------------------------------------------------------
echo "Empreinte\n";
$fp = jeedom2ha_system_health_fingerprint($snap);
check('SHA-256 hexadécimal', (bool) preg_match('/^[0-9a-f]{64}$/', $fp));
check('inchangée si rien ne change', jeedom2ha_system_health_fingerprint($snap) === $fp);
$rev = $snap; $rev['daemons'] = array_reverse($rev['daemons']);
check('indépendante de l\'ordre des démons', jeedom2ha_system_health_fingerprint($rev) === $fp);
$c = $snap; $c['daemons'][0]['running'] = true;
check('change si un démon démarre ou s\'arrête', jeedom2ha_system_health_fingerprint($c) !== $fp);
$c = $snap; $c['messages'] = 5;
check('change si le nombre de messages change', jeedom2ha_system_health_fingerprint($c) !== $fp);
$c = $snap; $c['updates'] = 0;
check('change si le nombre de mises à jour change', jeedom2ha_system_health_fingerprint($c) !== $fp);
$c = $snap; $c['core_version'] = '4.5.2';
check('change si la version du cœur change', jeedom2ha_system_health_fingerprint($c) !== $fp);
$c = $snap; array_pop($c['daemons']);
check('change si un plugin à démon disparaît', jeedom2ha_system_health_fingerprint($c) !== $fp);

// ---------------------------------------------------------------------------
echo "Case de configuration\n";
check('défaut (absente, vide, 0) : désactivée', !jeedom2ha_system_health_enabled('') && !jeedom2ha_system_health_enabled(null)
    && !jeedom2ha_system_health_enabled('0') && !jeedom2ha_system_health_enabled(0));
check('cochée : 1, "1", true', jeedom2ha_system_health_enabled('1') && jeedom2ha_system_health_enabled(1) && jeedom2ha_system_health_enabled(true));

// ---------------------------------------------------------------------------
echo "Pas du cron\n";
function tick_env(array $over = array()) {
    $env = (object) array('enabled' => false, 'published' => false, 'stored' => '', 'sent' => array(), 'logs' => array(),
        'reads' => 0, 'response' => array('status' => 'ok', 'failed' => 0), 'purge_response' => array('status' => 'ok', 'purge_complete' => true));
    foreach ($over as $k => $v) { $env->$k = $v; }
    $env->deps = array(
        'enabled' => function () use ($env) { return $env->enabled; },
        'published' => function () use ($env) { return $env->published; },
        'set_published' => function ($p) use ($env) { $env->published = $p; },
        'stored' => function () use ($env) { return $env->stored; },
        'store' => function ($f) use ($env) { $env->stored = $f; },
        'snapshot' => function () use ($env) {
            $env->reads++;
            return array('daemons' => array(array('id' => 'plugin_a', 'name' => 'Alpha', 'running' => true)),
                         'updates' => 1, 'messages' => 0, 'core_version' => '4.4.0');
        },
        'send' => function ($payload) use ($env) {
            $env->sent[] = $payload;
            return $payload['enabled'] ? $env->response : $env->purge_response;
        },
        'log' => function ($level, $message) use ($env) { $env->logs[] = $level . ':' . $message; },
    );
    return $env;
}

$env = tick_env();
$r = jeedom2ha_system_health_tick($env->deps);
check('désactivé par défaut : aucune lecture, aucun appel au démon', $r['status'] === 'disabled' && $env->sent === array() && $env->reads === 0);

$env = tick_env(array('enabled' => true));
$r = jeedom2ha_system_health_tick($env->deps);
check('activé : relevé envoyé une fois, empreinte mémorisée, marqué publié', $r['status'] === 'published'
    && count($env->sent) === 1 && $env->sent[0]['enabled'] === true && $env->stored !== '' && $env->published === true);
check('le relevé envoyé contient le démon, les compteurs et la version',
    $env->sent[0]['snapshot']['daemons'][0]['id'] === 'plugin_a' && $env->sent[0]['snapshot']['core_version'] === '4.4.0');
$r = jeedom2ha_system_health_tick($env->deps);
check('empreinte inchangée : rien n\'est renvoyé', $r['status'] === 'unchanged' && count($env->sent) === 1);

$env = tick_env(array('enabled' => true, 'response' => array('status' => 'error')));
$r = jeedom2ha_system_health_tick($env->deps);
check('envoi refusé : empreinte non mémorisée (nouvel essai), mais marqué publié (purge possible)',
    $r['status'] === 'failed' && $env->stored === '' && $env->published === true);
$env->response = null;
$r = jeedom2ha_system_health_tick($env->deps);
check('démon injoignable : échec sans exception', $r['status'] === 'failed' && $env->stored === '');

// Revue P2 : après A publié, un envoi de B échoué ou partiel efface l'empreinte : le retour aux valeurs A est republié.
$env = tick_env(array('enabled' => true));
check('A publié', jeedom2ha_system_health_tick($env->deps)['status'] === 'published' && $env->stored !== '');
$stateA = $env->deps['snapshot'];
$env->deps['snapshot'] = function () use ($env) {
    $env->reads++;
    return array('daemons' => array(array('id' => 'plugin_a', 'name' => 'Alpha', 'running' => false)),
                 'updates' => 1, 'messages' => 0, 'core_version' => '4.4.0');
};
$env->response = array('status' => 'error', 'failed' => 1);
$r = jeedom2ha_system_health_tick($env->deps);
check('B en échec ou partiel : empreinte effacée (plus celle de A)', $r['status'] === 'failed' && $env->stored === '');
$env->deps['snapshot'] = $stateA;
$env->response = array('status' => 'ok', 'failed' => 0);
$sentBefore = count($env->sent);
$r = jeedom2ha_system_health_tick($env->deps);
check('retour aux valeurs de A : republié (jamais « inchangé » sur un état de B resté dans HA)',
    $r['status'] === 'published' && count($env->sent) === $sentBefore + 1);

$env = tick_env(array('enabled' => true));
$env->deps['send'] = function () { throw new Exception('réseau fictif'); };
check('appel qui lève : échec propre', jeedom2ha_system_health_tick($env->deps)['status'] === 'failed');

$env = tick_env(array('enabled' => false, 'published' => true, 'stored' => str_repeat('a', 64)));
$r = jeedom2ha_system_health_tick($env->deps);
check('case décochée après publication : une purge envoyée, sans relevé', $r['status'] === 'purged'
    && $env->sent === array(array('enabled' => false)) && $env->reads === 0);
check('purge réussie : plus marqué publié, empreinte oubliée', $env->published === false && $env->stored === '');
$r = jeedom2ha_system_health_tick($env->deps);
check('ensuite : plus rien n\'est envoyé', $r['status'] === 'disabled' && count($env->sent) === 1);

$env = tick_env(array('enabled' => false, 'published' => true, 'purge_response' => array('status' => 'ok', 'purge_complete' => false)));
$r = jeedom2ha_system_health_tick($env->deps);
check('purge incomplète : reste marqué publié, nouvel essai au passage suivant', $r['status'] === 'failed' && $env->published === true);
$env->purge_response = array('status' => 'ok', 'purge_complete' => true);
check('nouvel essai réussi', jeedom2ha_system_health_tick($env->deps)['status'] === 'purged' && $env->published === false);

$stored = 'x';
jeedom2ha_system_health_invalidate(function ($f) use (&$stored) { $stored = $f; });
check('démarrage du démon : empreinte oubliée (relevé renvoyé)', $stored === '');

// ---------------------------------------------------------------------------
echo "Câblage dans la classe\n";
$class = file_get_contents($root . '/core/class/jeedom2ha.class.php');
check('le fichier de fonctions est chargé', strpos($class, "require_once __DIR__  . '/../php/jeedom2ha_system_health.php';") !== false);
check('cron5 appelle le pas, dans son propre try (n\'empêche jamais la réévaluation)',
    (bool) preg_match('/public static function cron5\(\) \{.*?reevaluateDecisionsIfChanged\(\);.*?\}\s*\/\/[^\n]*\n\s*try \{\s*self::systemHealthTick\(\);\s*\} catch \(\\\\Throwable \$e\)/s', $class));
check('relevé gardé : classes et méthodes du cœur testées avant appel',
    strpos($class, "class_exists('plugin') && method_exists('plugin', 'listPlugin')") !== false
    && strpos($class, "method_exists('update', 'nbNeedUpdate')") !== false
    && strpos($class, "method_exists('message', 'nbMessage')") !== false
    && strpos($class, "method_exists('jeedom', 'version')") !== false);
check('les plugins actifs seulement', strpos($class, 'plugin::listPlugin(true)') !== false);
check('le démarrage du démon oublie l\'empreinte', (bool) preg_match('/function deamon_start\(\) \{\s*self::deamon_stop\(\);.*?jeedom2ha_system_health_invalidate/s', $class));
check('l\'enregistrement de la configuration applique la case tout de suite, sans jamais bloquer',
    (bool) preg_match('/function postSaveConfiguration\(\) \{.*?try \{\s*self::systemHealthTick\(\);\s*\} catch \(\\\\Throwable \$e\)/s', $class));
check('route du démon dédiée', JEEDOM2HA_SYSTEM_HEALTH_ROUTE === '/action/system_health');
check('clé de la case : publishSystemHealth', JEEDOM2HA_SYSTEM_HEALTH_ENABLED_KEY === 'publishSystemHealth');
$code = '';
foreach (token_get_all(file_get_contents($root . '/core/php/jeedom2ha_system_health.php')) as $tok) {
    if (is_array($tok) && in_array($tok[0], array(T_COMMENT, T_DOC_COMMENT), true)) { continue; }
    $code .= is_array($tok) ? $tok[1] : $tok;
}
check('fichier pur : aucun appel au cœur Jeedom (hors commentaires)', !preg_match('/\b(plugin|update|message|config|log|jeedom|DB)::/', $code));

echo "Contrat de l'enveloppe callDaemon (correctif fix/system-health-envelope)\n";
// callDaemon n'envoie un corps POST que si la charge est non vide, puis l'enveloppe dans
// {action, payload, request_id, timestamp} : le démon lit `payload` (test pytest de l'enveloppe).
check('callDaemon enveloppe la charge sous « payload »', (bool) preg_match(
    "/if \\(\\\$_method === 'POST' && !empty\\(\\\$_payload\\)\\) \\{.*?'action' => \\\$action,\\s*'payload' => \\\$_payload,\\s*'request_id' => .*?'timestamp' =>/s", $class));
$action = str_replace('/', '.', str_replace('action/', '', ltrim(JEEDOM2HA_SYSTEM_HEALTH_ROUTE, '/')));
check('nom d\'action dérivé par callDaemon : system_health', $action === 'system_health');
$env = tick_env(array('enabled' => false, 'published' => true));
jeedom2ha_system_health_tick($env->deps);
check('la purge part avec une charge non vide (sinon callDaemon n\'enverrait aucun corps)',
    count($env->sent) === 1 && !empty($env->sent[0]) && $env->sent[0] === array('enabled' => false));
$env = tick_env(array('enabled' => true));
jeedom2ha_system_health_tick($env->deps);
check('la publication part avec enabled et snapshot', !empty($env->sent[0]) && $env->sent[0]['enabled'] === true && is_array($env->sent[0]['snapshot']));
// Réponses du démon telles que callDaemon les rend (JSON décodé, codes d'erreur lus grâce à ignore_errors).
check('réponse 200 du démon acceptée', jeedom2ha_system_health_response_ok(array('status' => 'ok', 'entities' => 7, 'removed' => array(), 'failed' => 0)));
check('réponse 400 / 503 du démon refusée', !jeedom2ha_system_health_response_ok(array('status' => 'error', 'message' => "Champ 'enabled' (booléen) obligatoire."))
    && !jeedom2ha_system_health_response_ok(array('status' => 'error', 'message' => 'Broker MQTT indisponible.')));
check('purge complète acceptée, incomplète refusée', jeedom2ha_system_health_response_ok(array('status' => 'ok', 'removed' => array(), 'purge_complete' => true), true)
    && !jeedom2ha_system_health_response_ok(array('status' => 'ok', 'removed' => array(), 'purge_complete' => false), true));
check('démon injoignable (null) refusé', !jeedom2ha_system_health_response_ok(null));

echo "\n{$passed} passed, {$failed} failed\n";
exit($failed === 0 ? 0 : 1);
