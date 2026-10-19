<?php
if (!isConnect('admin')) {
	throw new Exception('{{401 - Accès non autorisé}}');
}
// Déclaration des variables obligatoires
$plugin = plugin::byId('jeedom2ha');
sendVarToJS('eqType', $plugin->getId());

// Story 25.3 — aides pures : icône / couleur des objets Jeedom (liste blanche), regroupement par parent.
require_once __DIR__ . '/jeedom2ha_overview_helpers.php';

// Story 16.8 — Arbre pièce -> équipement pour la surface de mapping HA (modèle Homebridge).
// Consommé côté front (data Jeedom, aucune route daemon ajoutée). Les eqLogics de type
// jeedom2ha sont exclus : ce sont des templates du bridge, pas des cibles de mapping.
// Story 25.7 (Q1 A) : `eq_type` (identifiant du plugin de l'équipement) par équipement et table `j2haPluginNames`.
// Story 25.3 (AC13) : extension ADDITIVE — `father_id`, `icon_classes`, `color` ; les champs existants
// ne changent ni de nom ni de type. Les objets sans équipement propre alimentent `j2haAncestors`
// (sous-titres de groupe) et ne produisent pas de carte.
$j2haRoomsTree = array();
$j2haAncestors = array();
$j2haPluginIds = array();
foreach ((jeeObject::buildTree(null, false)) as $object) {
	$roomEqList = array();
	foreach (eqLogic::byObjectId($object->getId(), false) as $roomEq) {
		if ($roomEq->getEqType_name() === 'jeedom2ha') {
			continue;
		}
		$pluginId = j2ha_plugin_id($roomEq->getEqType_name());
		$j2haPluginIds[] = $pluginId;
		$roomEqList[] = array(
			'eq_id'   => (int) $roomEq->getId(),
			'eq_name' => $roomEq->getName(),
			'enabled' => ($roomEq->getIsEnable() == 1),
			'eq_type' => $pluginId,
		);
	}
	$fatherId = ($object->getFather_id() !== null) ? (int) $object->getFather_id() : 0;
	if (count($roomEqList) === 0) {
		$j2haAncestors[] = array(
			'object_id' => (int) $object->getId(),
			'name'      => $object->getName(),
			'father_id' => $fatherId,
		);
		continue;
	}
	$j2haRoomsTree[] = array(
		'object_id'     => (int) $object->getId(),
		'object_name'   => $object->getName(),
		'parent_number' => (int) $object->getConfiguration('parentNumber'),
		'father_id'     => $fatherId,
		'icon_classes'  => j2ha_icon_classes((string) $object->getDisplay('icon')),
		'color'         => j2ha_color_hex((string) $object->getDisplay('tagColor')),
		'equipments'    => $roomEqList,
	);
}
// Story 20.1 : la convention daemon object_id=0 rassemble les équipements sans
// objet (null ou -1). Les désactivés restent dans l'ordre natif Jeedom.
$unassignedEqList = array();
foreach (eqLogic::byObjectId(null, false) as $roomEq) {
	if ($roomEq->getEqType_name() === 'jeedom2ha') {
		continue;
	}
	$pluginId = j2ha_plugin_id($roomEq->getEqType_name());
	$j2haPluginIds[] = $pluginId;
	$unassignedEqList[] = array(
		'eq_id'   => (int) $roomEq->getId(),
		'eq_name' => $roomEq->getName(),
		'enabled' => ($roomEq->getIsEnable() == 1),
		'eq_type' => $pluginId,
	);
}
if (count($unassignedEqList) > 0) {
	$j2haRoomsTree[] = array(
		'object_id'     => 0,
		'object_name'   => __('Sans pièce', __FILE__),
		'parent_number' => 0,
		'father_id'     => 0,
		'icon_classes'  => J2HA_ICON_FALLBACK,
		'color'         => '',
		'equipments'    => $unassignedEqList,
	);
}
sendVarToJS('j2haRoomsTree', $j2haRoomsTree);
sendVarToJS('j2haAncestors', $j2haAncestors);
// Story 25.7 : nom affiché des seuls plugins présents (API du cœur ; repli sur l'identifiant si le plugin est inconnu).
sendVarToJS('j2haPluginNames', j2ha_plugin_names($j2haPluginIds, function ($pluginId) {
	return plugin::byId($pluginId)->getName();
}));

// Story 25.3 (Q9) : lien « Aide » vers la documentation du plugin (API du cœur, repli sur le lien d'info.json).
$j2haDocUrl = '';
try {
	$j2haDocUrl = (string) $plugin->getDocumentation();
} catch (Throwable $e) {
	$j2haDocUrl = '';
}
if (strpos($j2haDocUrl, 'https://') !== 0) {
	$j2haDocUrl = 'https://github.com/alexsahut/jeedom2ha/blob/stable/docs/fr_FR/index.md';
}
?>

<div class="row row-overflow">
	<!-- Page d'accueil du plugin -->
	<div class="col-xs-12 eqLogicThumbnailDisplay">
		<legend><i class="fas fa-cog"></i> {{Gestion}}</legend>
		<div class="eqLogicThumbnailContainer">
			<div class="cursor eqLogicAction logoSecondary" data-action="gotoPluginConf"><i class="fas fa-wrench"></i><br><span>{{Configuration}}</span></div>
		</div>

		<!-- Story 25.3 — Barre de santé compacte (Démon, MQTT, Dernière synchro, Dernière opération), actions
		     courantes à droite et menu « ⋯ ». Les identifiants span_health*, bt_rescanTopology et data-ha-action
		     sont conservés (refreshBridgeStatus, applyHAGating, gate 20-0). -->
		<div id="div_bridgeHealthBanner" class="j2ha-health-banner j2ha-health-bar">
			<div class="j2ha-health-items">
				<div class="j2ha-health-item">
					<strong>{{Démon}}</strong>
					<span id="span_healthBridge" class="label label-default j2ha-health-value">{{Chargement...}}</span>
				</div>
				<div class="j2ha-health-item">
					<strong>{{MQTT}}</strong>
					<span id="span_healthMqtt" class="label label-default j2ha-health-value">{{Chargement...}}</span>
					<span id="span_healthMqttBroker" class="j2ha-health-note"></span>
				</div>
				<div class="j2ha-health-item">
					<strong>{{Dernière synchro}}</strong>
					<span id="span_healthSync" class="j2ha-health-sync">{{...}}</span>
				</div>
				<div class="j2ha-health-item">
					<strong>{{Dernière opération}}</strong>
					<span id="span_healthOp" class="label label-default j2ha-health-value">{{...}}</span>
					<span id="span_healthOpMsg" class="j2ha-health-note"></span>
				</div>
			</div>
			<div id="div_haActions" class="j2ha-health-actions j2ha-ha-actions">
				<button type="button"
				        class="btn btn-default btn-sm j2ha-ha-action"
				        data-ha-action="republier"
				        disabled>
					<i class="fas fa-upload"></i> {{Republier tout}}
				</button>
				<button type="button"
				        id="bt_rescanTopology"
				        class="btn btn-default btn-sm j2ha-ha-action"
				        data-ha-action="rescan"
				        disabled>
					<i class="fas fa-sync-alt"></i> {{Relire Jeedom}}
				</button>
				<span id="j2ha_moreMenu">
					<span class="j2ha-menu-wrap">
						<button type="button" class="btn btn-default btn-sm j2ha-menu-toggle"
						        aria-haspopup="menu" aria-expanded="false"
						        aria-label="{{Plus d'actions}}" title="{{Plus d'actions}}">
							<i class="fas fa-ellipsis-h"></i>
						</button>
						<ul class="j2ha-menu" role="menu">
							<li role="none">
								<button type="button" id="bt_openDiagnostic" class="j2ha-menu-item" role="menuitem">
									<i class="fas fa-download"></i>{{Télécharger le diagnostic…}}
								</button>
							</li>
							<li class="j2ha-menu-sep" role="separator"></li>
							<li role="none">
								<button type="button"
								        class="j2ha-menu-item j2ha-menu-danger j2ha-ha-action"
								        role="menuitem"
								        data-ha-action="supprimer-recreer"
								        disabled>
									<i class="fas fa-trash"></i>{{Supprimer tout de Home Assistant…}}
								</button>
							</li>
						</ul>
					</span>
				</span>
			</div>
		</div>
		<div id="div_haGatingReason"
		     class="text-muted j2ha-ha-gating-reason">
		</div>

		<!-- Export du diagnostic support : contenu de la boîte ouverte par « Télécharger le diagnostic… »
		     (même action ajax, mêmes paramètres, même gestionnaire qu'avant ; seul l'emplacement change). -->
		<div id="div_diagnosticDialog" class="j2ha-diagnostic-dialog" style="display:none;">
			<div class="form-group j2ha-export">
				<label class="j2ha-export-label">
					<input type="checkbox" id="cb_pseudonymize" class="j2ha-export-check"/>
					{{Pseudonymiser les noms d'équipements}}
				</label>
				<button id="bt_exportDiagnostic" class="btn btn-default btn-sm">
					<i class="fas fa-download"></i> {{Télécharger le diagnostic support}}
				</button>
				<span id="span_exportResult" class="j2ha-export-result"></span>
			</div>
		</div>

		<!-- Story 16.8 / 25.3 — Surface de mapping HA par pièce (modèle Homebridge : pièce -> équipement -> commande).
		     Story 25.4 : #j2ha_mainView regroupe titre, bloc maison, liste filtrée et cartes (masqués, non détruits, quand la
		     vue de travail #j2ha_workView est ouverte) ; la barre de santé reste visible au-dessus. -->
		<div id="j2ha_mainView">
		<legend><i class="fas fa-home"></i> {{Configuration Home Assistant par pièce}}</legend>
		<p class="text-muted j2ha-help-line">{{Choisissez une pièce pour voir ses équipements et ce qui est publié dans Home Assistant.}} <a href="<?php echo j2ha_html($j2haDocUrl); ?>" target="_blank" rel="noopener">{{Aide}}</a></p>

		<!-- Bloc maison : « N publiés sur M », jauge segmentée, puces = filtres globaux (sans requête réseau). -->
		<div id="j2ha_houseBlock" class="j2ha-house">
			<div class="j2ha-house-main">
				<span id="j2ha_houseNumber" class="j2ha-house-number"></span>
				<span id="j2ha_houseSub" class="j2ha-house-sub"></span>
			</div>
			<div id="j2ha_houseMeta" class="text-muted j2ha-house-meta"></div>
			<div id="j2ha_houseGauge" class="j2ha-house-gauge"></div>
			<div id="j2ha_houseChips" class="j2ha-chips"></div>
			<div class="j2ha-house-fresh">
				<span id="j2ha_freshness" class="text-muted"></span>
				<button type="button" id="bt_refreshStates" class="btn btn-default btn-xs"><i class="fas fa-sync-alt"></i> {{Actualiser}}</button>
			</div>
			<div id="j2ha_readStatus" class="text-muted j2ha-read-status" role="status" aria-live="polite"></div>
		</div>
		<div id="j2ha_filterPanel" class="j2ha-filter-panel" style="display:none;">
			<div class="j2ha-filter-head">
				<strong id="j2ha_filterTitle"></strong>
				<button type="button" id="bt_clearFilter" class="btn btn-default btn-xs">{{Tout afficher}}</button>
			</div>
			<ul id="j2ha_filterList" class="j2ha-filter-list"></ul>
		</div>
		<?php
		if (count($j2haRoomsTree) == 0) {
			echo '<div class="text-center j2ha-no-rooms">{{Aucune pièce avec équipement trouvée.}}</div>';
		} else {
			echo '<div class="j2ha-room-groups" id="j2ha_roomCards">';
			echo j2ha_render_room_groups(j2ha_group_rooms($j2haRoomsTree, $j2haAncestors));
			echo '</div>';
		}
		?>
		</div> <!-- /#j2ha_mainView -->

		<!-- Story 25.4 — Vue de travail maître-détail (jeedom2ha_workview.js) : arbre pièces → équipements à gauche, détail
		     à droite. Construite à l'ouverture ; remplace l'ancienne fenêtre de pièce. -->
		<div id="j2ha_workView" class="j2ha-wv" style="display:none;"></div>

	</div> <!-- /.eqLogicThumbnailDisplay -->

	<!-- Page de présentation de l'équipement -->
	<div class="col-xs-12 eqLogic" style="display: none;">
		<!-- barre de gestion de l'équipement -->
		<div class="input-group pull-right j2ha-inline-flex">
			<span class="input-group-btn">
				<!-- Les balises <a></a> sont volontairement fermées à la ligne suivante pour éviter les espaces entre les boutons. Ne pas modifier -->
				<a class="btn btn-sm btn-default eqLogicAction roundedLeft" data-action="configure"><i class="fas fa-cogs"></i><span class="hidden-xs"> {{Configuration avancée}}</span>
				</a><a class="btn btn-sm btn-default eqLogicAction" data-action="copy"><i class="fas fa-copy"></i><span class="hidden-xs"> {{Dupliquer}}</span>
				</a><a class="btn btn-sm btn-success eqLogicAction" data-action="save"><i class="fas fa-check-circle"></i> {{Sauvegarder}}
				</a><a class="btn btn-sm btn-danger eqLogicAction roundedRight" data-action="remove"><i class="fas fa-minus-circle"></i> {{Supprimer}}
				</a>
			</span>
		</div>
		<!-- Onglets -->
		<ul class="nav nav-tabs" role="tablist">
			<li role="presentation"><a href="#" class="eqLogicAction" aria-controls="home" role="tab" data-toggle="tab" data-action="returnToThumbnailDisplay"><i class="fas fa-arrow-circle-left"></i></a></li>
			<li role="presentation" class="active"><a href="#eqlogictab" aria-controls="home" role="tab" data-toggle="tab"><i class="fas fa-tachometer-alt"></i> {{Equipement}}</a></li>
			<li role="presentation"><a href="#commandtab" aria-controls="home" role="tab" data-toggle="tab"><i class="fas fa-list"></i> {{Commandes}}</a></li>
		</ul>
		<div class="tab-content">
			<!-- Onglet de configuration de l'équipement -->
			<div role="tabpanel" class="tab-pane active" id="eqlogictab">
				<!-- Partie gauche de l'onglet "Equipements" -->
				<!-- Paramètres généraux et spécifiques de l'équipement -->
				<form class="form-horizontal">
					<fieldset>
						<div class="col-lg-6">
							<legend><i class="fas fa-wrench"></i> {{Paramètres généraux}}</legend>
							<div class="form-group">
								<label class="col-sm-4 control-label">{{Nom de l'équipement}}</label>
								<div class="col-sm-6">
									<input type="text" class="eqLogicAttr form-control" data-l1key="id" style="display:none;">
									<input type="text" class="eqLogicAttr form-control" data-l1key="name" placeholder="{{Nom de l'équipement}}">
								</div>
							</div>
							<div class="form-group">
								<label class="col-sm-4 control-label">{{Objet parent}}</label>
								<div class="col-sm-6">
									<select id="sel_object" class="eqLogicAttr form-control" data-l1key="object_id">
										<option value="">{{Aucun}}</option>
										<?php
										$options = '';
										foreach ((jeeObject::buildTree(null, false)) as $object) {
											$options .= '<option value="' . $object->getId() . '">' . str_repeat('&nbsp;&nbsp;', $object->getConfiguration('parentNumber')) . $object->getName() . '</option>';
										}
										echo $options;
										?>
									</select>
								</div>
							</div>
							<div class="form-group">
								<label class="col-sm-4 control-label">{{Catégorie}}</label>
								<div class="col-sm-6">
									<?php
									foreach (jeedom::getConfiguration('eqLogic:category') as $key => $value) {
										echo '<label class="checkbox-inline">';
										echo '<input type="checkbox" class="eqLogicAttr" data-l1key="category" data-l2key="' . $key . '" >' . $value['name'];
										echo '</label>';
									}
									?>
								</div>
							</div>
							<div class="form-group">
								<label class="col-sm-4 control-label">{{Options}}</label>
								<div class="col-sm-6">
									<label class="checkbox-inline"><input type="checkbox" class="eqLogicAttr" data-l1key="isEnable" checked>{{Activer}}</label>
									<label class="checkbox-inline"><input type="checkbox" class="eqLogicAttr" data-l1key="isVisible" checked>{{Visible}}</label>
								</div>
							</div>
						</div>

						<!-- Partie droite de l'onglet "Équipement" -->
						<!-- Affiche un champ de commentaire par défaut mais vous pouvez y mettre ce que vous voulez -->
						<div class="col-lg-6">
							<legend><i class="fas fa-info"></i> {{Informations}}</legend>
							<div class="form-group">
								<label class="col-sm-4 control-label">{{Description}}</label>
								<div class="col-sm-6">
									<textarea class="form-control eqLogicAttr autogrow" data-l1key="comment"></textarea>
								</div>
							</div>
						</div>
					</fieldset>
				</form>
			</div><!-- /.tabpanel #eqlogictab-->

			<!-- Onglet des commandes de l'équipement -->
			<div role="tabpanel" class="tab-pane" id="commandtab">
				<a class="btn btn-default btn-sm pull-right cmdAction" data-action="add" style="margin-top:5px;"><i class="fas fa-plus-circle"></i> {{Ajouter une commande}}</a>
				<br><br>
				<div class="table-responsive">
					<table id="table_cmd" class="table table-bordered table-condensed">
						<thead>
							<tr>
								<th class="hidden-xs" style="min-width:50px;width:70px;">ID</th>
								<th style="min-width:200px;width:350px;">{{Nom}}</th>
								<th>{{Type}}</th>
								<th style="min-width:260px;">{{Options}}</th>
								<th>{{Etat}}</th>
								<th style="min-width:80px;width:200px;">{{Actions}}</th>
							</tr>
						</thead>
						<tbody>
						</tbody>
					</table>
				</div>
			</div><!-- /.tabpanel #commandtab-->

			<!-- Story 16.8 — L'onglet override par commande (16.5) est retiré : point d'entrée
			     inatteignable (0 eqLogic jeedom2ha). Le triptyque + diagnostic vivent désormais
			     dans la surface « Configuration Home Assistant par pièce » (vue de travail maître-détail). -->

		</div><!-- /.tab-content -->
	</div><!-- /.eqLogic -->
</div><!-- /.row row-overflow -->

<!-- Inclusion du fichier CSS du plugin (dossier, nom_du_fichier, extension_du_fichier, id_du_plugin) -->
<?php include_file('desktop', 'jeedom2ha', 'css', 'jeedom2ha'); ?>
<!-- Inclusion du fichier javascript du plugin (dossier, nom_du_fichier, extension_du_fichier, id_du_plugin) -->
<?php include_file('desktop', 'jeedom2ha_mapping_override', 'js', 'jeedom2ha'); ?>
<?php include_file('desktop', 'jeedom2ha_mapping_surface', 'js', 'jeedom2ha'); ?>
<?php include_file('desktop', 'jeedom2ha_action_budget', 'js', 'jeedom2ha'); ?>
<?php include_file('desktop', 'jeedom2ha_overview', 'js', 'jeedom2ha'); ?>
<?php include_file('desktop', 'jeedom2ha_workview', 'js', 'jeedom2ha'); ?>
<?php include_file('desktop', 'jeedom2ha', 'js', 'jeedom2ha'); ?>
<!-- Inclusion du fichier javascript du core - NE PAS MODIFIER NI SUPPRIMER -->
<?php include_file('core', 'plugin.template', 'js'); ?>
