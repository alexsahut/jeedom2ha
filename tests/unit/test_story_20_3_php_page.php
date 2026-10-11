<?php
// ARTEFACT — Story 20.3 (AC1, AC2, AC6, AC7) : la page principale ne contient plus la synthèse
// « Parc global », l'action Diagnostic ni le vocabulaire de gabarit ; les relais PHP et l'export
// support sont conservés. Lecture du source seulement (aucun cœur Jeedom requis).
// Exécution : php tests/unit/test_story_20_3_php_page.php

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

$page = file_get_contents(__DIR__ . '/../../desktop/php/jeedom2ha.php');
$ajax = file_get_contents(__DIR__ . '/../../core/ajax/jeedom2ha.ajax.php');
$klass = file_get_contents(__DIR__ . '/../../core/class/jeedom2ha.class.php');
// Texte rendu : sans commentaires HTML ni commentaires PHP.
$rendered = preg_replace(array('/<!--.*?-->/s', '/\/\*.*?\*\//s', '/^\s*\/\/.*$/m'), '', $page);

echo "AC1 — synthèse supprimée\n";
foreach (array('div_scopeSummary', 'bt_refreshScopeSummary', 'Parc global', 'Synthèse du périmètre publié', 'jeedom2ha_scope_summary', 'jeedom2ha_diagnostic_helpers') as $needle) {
    check("la page ne contient pas « {$needle} »", strpos($rendered, $needle) === false);
}

echo "AC2 — action Diagnostic supprimée, squelette Jeedom et export conservés\n";
check('aucune action data-action="diagnostic"', strpos($rendered, 'data-action="diagnostic"') === false);
check('« Ajouter » garde eqLogicAction et data-action="add"', preg_match('/eqLogicAction[^>]*data-action="add"/', $rendered) === 1);
check('« Configuration » garde eqLogicAction et data-action="gotoPluginConf"', preg_match('/eqLogicAction[^>]*data-action="gotoPluginConf"/', $rendered) === 1);
check('le conteneur eqLogicThumbnailContainer est conservé', strpos($rendered, 'eqLogicThumbnailContainer') !== false);
check('« Télécharger le diagnostic support » est conservé', strpos($rendered, 'bt_exportDiagnostic') !== false);

echo "AC6 — vocabulaire de gabarit retiré\n";
foreach (array('Mes templates', 'Équipement Template', 'Paramètre n°1', 'Paramètres spécifiques', 'Mot de passe', 'Auto-actualisation', 'Configuration mapping') as $needle) {
    check("la page ne contient pas « {$needle} »", strpos($rendered, $needle) === false);
}
foreach (array('param1', 'password', 'autorefresh') as $key) {
    check("aucun eqLogicAttr orphelin « {$key} »", strpos($rendered, 'data-l2key="' . $key . '"') === false);
}
check('titre « Configuration Home Assistant par pièce »', strpos($rendered, '{{Configuration Home Assistant par pièce}}') !== false);
check('le cœur Jeedom garde plugin.template', strpos($rendered, "include_file('core', 'plugin.template', 'js')") !== false);

echo "AC7 — relais conservés\n";
check("le relais getDiagnostics est conservé", strpos($ajax, "'getDiagnostics'") !== false);
check("le relais getPublishedScopeForConsole est conservé", strpos($ajax, "'getPublishedScopeForConsole'") !== false);
check("le relais exportDiagnostic est conservé", strpos($ajax, "'exportDiagnostic'") !== false);
check('jeedom2ha::getPublishedScopeForConsole est conservée', strpos($klass, 'public static function getPublishedScopeForConsole') !== false);

echo "--- Bilan Story 20.3 / page : {$passed}/" . ($passed + $failed) . " passés, {$failed} échoués ---\n";
exit($failed === 0 ? 0 : 1);
