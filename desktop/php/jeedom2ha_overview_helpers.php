<?php
/**
 * Story 25.3 — Aides pures de la page principale (icône et couleur des objets Jeedom, regroupement par
 * objet parent, rendu des cartes de pièce). Aucune dépendance au cœur Jeedom : testable en ligne de commande.
 * Compatible PHP 7.4.
 *
 * Le HTML d'icône d'un objet Jeedom est une valeur NON FIABLE : on n'en retient que des classes CSS d'une liste
 * blanche, reconstruites puis échappées ; une couleur n'est acceptée que si c'est un littéral hexadécimal.
 */

if (!defined('J2HA_ICON_FALLBACK')) {
	define('J2HA_ICON_FALLBACK', 'fas fa-door-open');
}

/** Classes de famille Font Awesome / Jeedom admises seules. */
function j2ha_icon_family_classes() {
	return array('fas', 'far', 'fab', 'fal', 'fa', 'icon');
}

/** Classes de glyphe admises (préfixes des jeux d'icônes de Jeedom 4.4 à 4.6). */
function j2ha_icon_glyph_pattern() {
	return '/^(?:fa|jeedom|jeedomapp|nature|maison|meteo|loisir|techno|divers|securite|mdi|fontawesome)-[A-Za-z0-9-]{1,40}$/';
}

/**
 * Réduit le HTML d'icône d'un objet (`getDisplay('icon')`) à une liste de classes CSS sûres.
 * Repli : porte (`fas fa-door-open`) si l'icône est absente, vide ou rejetée.
 */
function j2ha_icon_classes($rawHtml) {
	if (!is_string($rawHtml) || $rawHtml === '') {
		return J2HA_ICON_FALLBACK;
	}
	if (!preg_match('/<i\b[^>]*?\bclass\s*=\s*(["\'])([^"\'<>]*)\1/i', $rawHtml, $m)) {
		return J2HA_ICON_FALLBACK;
	}
	$families = j2ha_icon_family_classes();
	$family = array();
	$glyphs = array();
	foreach (preg_split('/\s+/', trim($m[2])) as $token) {
		if ($token === '') {
			continue;
		}
		if (in_array($token, $families, true)) {
			$family[] = $token;
		} elseif (preg_match(j2ha_icon_glyph_pattern(), $token)) {
			$glyphs[] = $token;
		}
	}
	if (count($glyphs) === 0) {
		return J2HA_ICON_FALLBACK;
	}
	if (count($family) === 0) {
		$family[] = 'fas';
	}
	return implode(' ', array_merge(array_unique($family), array_unique($glyphs)));
}

/** Couleur d'objet : littéral hexadécimal `#RGB` ou `#RRGGBB` seulement, sinon chaîne vide. */
function j2ha_color_hex($raw) {
	if (!is_string($raw)) {
		return '';
	}
	$raw = trim($raw);
	return preg_match('/^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/', $raw) ? $raw : '';
}

function j2ha_html($text) {
	return htmlspecialchars((string) $text, ENT_QUOTES, 'UTF-8');
}

/**
 * Regroupe les pièces par objet parent direct.
 *
 * @param array $rooms     pièces de `j2haRoomsTree` (object_id, object_name, father_id facultatif)
 * @param array $ancestors objets sans équipement propre : {object_id, name, father_id}
 * @return array liste de groupes {title: string|null, rooms: array}. Ordre : pièces isolées (sans titre), puis
 *               un groupe par parent dans l'ordre natif de Jeedom, puis la pseudo-pièce « Sans pièce ».
 */
function j2ha_group_rooms(array $rooms, array $ancestors) {
	$names = array();
	$fathers = array();
	foreach ($ancestors as $a) {
		$id = (int) $a['object_id'];
		$names[$id] = (string) $a['name'];
		$fathers[$id] = isset($a['father_id']) ? (int) $a['father_id'] : 0;
	}
	foreach ($rooms as $r) {
		$id = (int) $r['object_id'];
		if ($id <= 0) {
			continue;
		}
		$names[$id] = (string) $r['object_name'];
		$fathers[$id] = isset($r['father_id']) ? (int) $r['father_id'] : 0;
	}
	$knownFather = function ($id) use (&$names, &$fathers) {
		$f = isset($fathers[$id]) ? $fathers[$id] : 0;
		return ($f > 0 && $f !== $id && isset($names[$f])) ? $f : 0;
	};
	$heads = array();
	foreach ($rooms as $r) {
		$id = (int) $r['object_id'];
		if ($id > 0 && $knownFather($id) > 0) {
			$heads[$knownFather($id)] = true;
		}
	}
	$title = function ($id) use (&$names, $knownFather) {
		$chain = array();
		$seen = array();
		$cur = $id;
		while ($cur > 0 && isset($names[$cur]) && !isset($seen[$cur])) {
			array_unshift($chain, $names[$cur]);
			$seen[$cur] = true;
			$cur = $knownFather($cur);
		}
		return implode(' › ', $chain);
	};

	$isolated = array();
	$byParent = array();
	$order = array();
	$pseudo = array();
	foreach ($rooms as $r) {
		$id = (int) $r['object_id'];
		if ($id <= 0) {
			$pseudo[] = $r;
			continue;
		}
		$key = isset($heads[$id]) ? $id : $knownFather($id);
		if ($key === 0) {
			$isolated[] = $r;
			continue;
		}
		if (!isset($byParent[$key])) {
			$byParent[$key] = array();
			$order[] = $key;
		}
		$byParent[$key][] = $r;
	}
	// La carte du parent, s'il porte des équipements, ouvre son propre groupe.
	foreach ($order as $key) {
		usort($byParent[$key], function ($a, $b) use ($key) {
			$ra = ((int) $a['object_id'] === $key) ? 0 : 1;
			$rb = ((int) $b['object_id'] === $key) ? 0 : 1;
			return $ra - $rb;
		});
	}
	$groups = array();
	if (count($isolated) > 0) {
		$groups[] = array('title' => null, 'rooms' => $isolated);
	}
	foreach ($order as $key) {
		$groups[] = array('title' => $title($key), 'rooms' => $byParent[$key]);
	}
	if (count($pseudo) > 0) {
		$groups[] = array('title' => null, 'rooms' => $pseudo);
	}
	return $groups;
}

/** Carte de pièce : conserve `objectDisplayCard`, `j2ha-room-card`, `data-object_id` et `onclick` (jamais `eqLogicDisplayCard`). */
function j2ha_render_room_card(array $room) {
	$id = (int) $room['object_id'];
	$icon = isset($room['icon_classes']) ? j2ha_icon_classes('<i class="' . $room['icon_classes'] . '"></i>') : J2HA_ICON_FALLBACK;
	$color = isset($room['color']) ? j2ha_color_hex($room['color']) : '';
	$html = '<div class="objectDisplayCard cursor j2ha-room-card" data-object_id="' . $id . '" tabindex="0" role="button"'
		. ($color !== '' ? ' data-color="' . j2ha_html($color) . '"' : '')
		. ' onclick="j2haOpenRoom(' . $id . ')">';
	$html .= '<i class="' . j2ha_html($icon) . ' j2ha-room-icon"></i>';
	$html .= '<br>';
	$html .= '<span class="name' . ($id > 0 ? ' j2ha-free-name' : '') . '">' . j2ha_html($room['object_name']) . '</span>';
	$html .= '<span class="text-muted j2ha-room-count"> (' . count($room['equipments']) . ')</span>';
	$html .= '<div class="j2ha-room-state"></div>';
	$html .= '</div>';
	return $html;
}

/** Cartes regroupées par objet parent ; `$groups` vient de `j2ha_group_rooms`. */
function j2ha_render_room_groups(array $groups) {
	$html = '';
	foreach ($groups as $group) {
		$html .= '<div class="j2ha-room-group">';
		if ($group['title'] !== null && $group['title'] !== '') {
			$html .= '<h4 class="j2ha-room-group-title j2ha-free-name">' . j2ha_html($group['title']) . '</h4>';
		}
		$html .= '<div class="objectListContainer">';
		foreach ($group['rooms'] as $room) {
			$html .= j2ha_render_room_card($room);
		}
		$html .= '</div></div>';
	}
	return $html;
}
