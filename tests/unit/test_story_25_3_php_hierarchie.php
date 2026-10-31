<?php
// ARTEFACT — Story 25.3 (AC13) : icône et couleur des objets Jeedom (liste blanche, jamais de HTML brut) et
// regroupement des cartes par objet parent. Fonctions pures, sans cœur Jeedom. Données fictives (CC-48).
// Exécution : php tests/unit/test_story_25_3_php_hierarchie.php

require_once __DIR__ . '/../../desktop/php/jeedom2ha_overview_helpers.php';

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

echo "Icône : classes de la liste blanche seulement\n";
check('icône Font Awesome conservée', j2ha_icon_classes('<i class="fas fa-bed"></i>') === 'fas fa-bed');
check('icône Jeedom conservée', j2ha_icon_classes('<i class="icon jeedom-maison"></i>') === 'icon jeedom-maison');
check('famille ajoutée si absente', j2ha_icon_classes('<i class="fa-couch"></i>') === 'fas fa-couch');
check('classe inconnue retirée, glyphe conservé', j2ha_icon_classes('<i class="evil-class fas fa-bed"></i>') === 'fas fa-bed');
check('uniquement une classe inconnue : repli porte', j2ha_icon_classes('<i class="evil-class fas"></i>') === J2HA_ICON_FALLBACK);
check('vide : repli porte', j2ha_icon_classes('') === J2HA_ICON_FALLBACK);
check('non chaîne : repli porte', j2ha_icon_classes(null) === J2HA_ICON_FALLBACK);
foreach (array('"><script>alert(1)</script>', '<i class="javascript:alert(1)"></i>', '<i class="fas fa-bed" onclick="x()"><script>', '<i class=\'fas "x\'>', '<img src=x onerror=alert(1)>') as $hostile) {
    $out = j2ha_icon_classes($hostile);
    check('entrée hostile → sortie sûre : ' . substr($hostile, 0, 30), preg_match('/^[A-Za-z0-9 _-]+$/', $out) === 1 && strpos($out, 'script') === false && strpos($out, 'onerror') === false && strpos($out, 'onclick') === false);
}

echo "Couleur : littéral hexadécimal validé, sinon ignorée\n";
check('#RGB accepté', j2ha_color_hex('#f80') === '#f80');
check('#RRGGBB accepté', j2ha_color_hex(' #FF8800 ') === '#FF8800');
foreach (array('red', 'red;background:url(x)', '#12345', '#gggggg', 'rgb(1,2,3)', 'expression(1)', '"><script>', '#ff8800;', '') as $bad) {
    check('couleur rejetée : ' . $bad, j2ha_color_hex($bad) === '');
}
check('non chaîne rejetée', j2ha_color_hex(null) === '');

echo "Regroupement par objet parent\n";
function room($id, $name, $father) {
    return array('object_id' => $id, 'object_name' => $name, 'father_id' => $father, 'equipments' => array(array('eq_id' => $id * 10)));
}
$ancestors = array(array('object_id' => 1, 'name' => 'Maison', 'father_id' => 0));
$groups = j2ha_group_rooms(array(room(2, 'Étage', 1), room(3, 'Salle A', 2), room(4, 'Salle B', 2), room(5, 'Isolée', 0)), $ancestors);
$summary = array_map(function ($g) { return array($g['title'], array_map(function ($r) { return $r['object_id']; }, $g['rooms'])); }, $groups);
check('isolées sans titre, puis groupe du parent (sa carte en tête), titre « Parent › Enfant »', $summary === array(
    array(null, array(5)),
    array('Maison › Étage', array(2, 3, 4)),
));
$groups = j2ha_group_rooms(array(room(12, 'Zèbre', 10), room(11, 'Abeille', 10)), array(array('object_id' => 10, 'name' => 'Parent sans équipement', 'father_id' => 0)));
check('ordre natif conservé dans le groupe ; parent sans équipement : sous-titre seulement', count($groups) === 1 && $groups[0]['title'] === 'Parent sans équipement' && $groups[0]['rooms'][0]['object_id'] === 12 && $groups[0]['rooms'][1]['object_id'] === 11);
$pseudo = array('object_id' => 0, 'object_name' => 'Sans pièce', 'father_id' => 0, 'equipments' => array(array('eq_id' => 1)));
$groups = j2ha_group_rooms(array($pseudo, room(5, 'Isolée', 0)), array());
check('« Sans pièce » en dernier, sans sous-titre', end($groups)['rooms'][0]['object_id'] === 0 && end($groups)['title'] === null);
$groups = j2ha_group_rooms(array(room(5, 'Orpheline', 99)), array());
check('parent inconnu : pièce isolée, aucun sous-titre inventé', count($groups) === 1 && $groups[0]['title'] === null);
$groups = j2ha_group_rooms(array(room(5, 'Boucle', 5)), array());
check('objet parent de lui-même : pas de boucle infinie', count($groups) === 1 && $groups[0]['title'] === null);
$groups = j2ha_group_rooms(array(room(5, 'A', 6), room(6, 'B', 5)), array());
check('cycle de parents : terminaison garantie', count($groups) >= 1);

echo "Rendu des cartes\n";
$html = j2ha_render_room_groups(j2ha_group_rooms(array(room(2, 'Nom <b>x</b> & "q"', 0)), array()));
check('nom échappé', strpos($html, '<b>') === false && strpos($html, '&lt;b&gt;x&lt;/b&gt; &amp; &quot;q&quot;') !== false);
check('contrat de la carte conservé', strpos($html, 'class="objectDisplayCard cursor j2ha-room-card"') !== false && strpos($html, 'data-object_id="2"') !== false && strpos($html, 'onclick="j2haOpenRoom(2)"') !== false);
check('jamais eqLogicDisplayCard', strpos($html, 'eqLogicDisplayCard') === false);
$card = j2ha_render_room_card(array('object_id' => 3, 'object_name' => 'C', 'icon_classes' => 'fas fa-bed" onmouseover="x', 'color' => '#abc;x', 'equipments' => array()));
check('classes d\'icône re-filtrées au rendu, couleur invalide absente', strpos($card, 'onmouseover') === false && strpos($card, 'data-color') === false);

echo "--- Bilan Story 25.3 / PHP hiérarchie : {$passed}/" . ($passed + $failed) . " passés, {$failed} échoués ---\n";
exit($failed === 0 ? 0 : 1);
