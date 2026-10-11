<?php
if (!isConnect('admin')) {
	throw new Exception('{{401 - Accès non autorisé}}');
}
// Déclaration des variables obligatoires
$plugin = plugin::byId('jeedom2ha');
sendVarToJS('eqType', $plugin->getId());

// Story 16.8 — Arbre pièce -> équipement pour la surface de mapping HA (modèle Homebridge).
// Consommé côté front (data Jeedom, aucune route daemon ajoutée). Les eqLogics de type
// jeedom2ha sont exclus : ce sont des templates du bridge, pas des cibles de mapping.
$j2haRoomsTree = array();
foreach ((jeeObject::buildTree(null, false)) as $object) {
	$roomEqList = array();
	foreach (eqLogic::byObjectId($object->getId(), false) as $roomEq) {
		if ($roomEq->getEqType_name() === 'jeedom2ha') {
			continue;
		}
		$roomEqList[] = array(
			'eq_id'   => (int) $roomEq->getId(),
			'eq_name' => $roomEq->getName(),
			'enabled' => ($roomEq->getIsEnable() == 1),
		);
	}
	if (count($roomEqList) === 0) {
		continue;
	}
	$j2haRoomsTree[] = array(
		'object_id'     => (int) $object->getId(),
		'object_name'   => $object->getName(),
		'parent_number' => (int) $object->getConfiguration('parentNumber'),
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
	$unassignedEqList[] = array(
		'eq_id'   => (int) $roomEq->getId(),
		'eq_name' => $roomEq->getName(),
		'enabled' => ($roomEq->getIsEnable() == 1),
	);
}
if (count($unassignedEqList) > 0) {
	$j2haRoomsTree[] = array(
		'object_id'     => 0,
		'object_name'   => __('Sans pièce', __FILE__),
		'parent_number' => 0,
		'equipments'    => $unassignedEqList,
	);
}
sendVarToJS('j2haRoomsTree', $j2haRoomsTree);
?>

<div class="row row-overflow">
	<!-- Page d'accueil du plugin -->
	<div class="col-xs-12 eqLogicThumbnailDisplay">
		<legend><i class="fas fa-cog"></i> {{Gestion}}</legend>
		<div class="eqLogicThumbnailContainer">
			<div class="cursor eqLogicAction logoPrimary" data-action="add"><i class="fas fa-plus-circle"></i><br><span>{{Ajouter}}</span></div>
			<div class="cursor eqLogicAction logoSecondary" data-action="gotoPluginConf"><i class="fas fa-wrench"></i><br><span>{{Configuration}}</span></div>
		</div>

		<!-- Bandeau global de santé toujours visible (Story 2.2) -->
		<div id="div_bridgeHealthBanner" class="well well-sm" style="margin:10px 5px; display:flex; flex-wrap:wrap; gap:15px; align-items:center;">
			<div style="display:flex; align-items:center;">
				<i class="fas fa-server" style="margin-right:5px;"></i> <strong>{{Bridge}}</strong> :
				<span id="span_healthBridge" class="label label-default" style="margin-left:5px;">{{Chargement...}}</span>
			</div>
			<div style="display:flex; align-items:center;">
				<i class="fas fa-network-wired" style="margin-right:5px;"></i> <strong>{{MQTT}}</strong> :
				<span id="span_healthMqtt" class="label label-default" style="margin-left:5px;">{{Chargement...}}</span>
				<span id="span_healthMqttBroker" style="margin-left:8px; color:#666; font-size:0.9em;"></span>
			</div>
			<div style="display:flex; align-items:center;">
				<i class="fas fa-sync-alt" style="margin-right:5px;"></i> <strong>{{Dernière synchro}}</strong> :
				<span id="span_healthSync" style="margin-left:5px; font-weight:500; color:#555;">{{...}}</span>
			</div>
			<div style="display:flex; align-items:center;">
				<i class="fas fa-tasks" style="margin-right:5px;"></i> <strong>{{Dernière opération}}</strong> :
				<span id="span_healthOp" class="label label-default" style="margin-left:5px;">{{...}}</span>
				<span id="span_healthOpMsg" style="margin-left:8px; color:#666; font-size:0.9em;"></span>
			</div>
		</div>

		<!-- Zone Actions Home Assistant — Story 2.3
		     Boutons visibles et soumis au gating. Aucun handler click câblé ici.
		     Logique opérationnelle complète → Epic 4 (Stories 4.2 et 4.3). -->
		<div id="div_haActions" class="well well-sm" style="margin:10px 5px;">
			<strong>{{Actions Home Assistant}}</strong>
			<div style="margin-top:8px;">
				<button type="button"
				        class="btn btn-default btn-sm j2ha-ha-action"
				        data-ha-action="republier"
				        disabled>
					<i class="fas fa-upload"></i> {{Republier dans Home Assistant}}
				</button>
				<button type="button"
				        id="bt_rescanTopology"
				        class="btn btn-default btn-sm j2ha-ha-action"
				        data-ha-action="rescan"
				        disabled
				        style="margin-left:8px;">
					<i class="fas fa-sync-alt"></i> {{Rescanner la topologie Jeedom}}
				</button>
				<button type="button"
				        class="btn btn-default btn-sm j2ha-ha-action"
				        data-ha-action="supprimer-recreer"
				        disabled
				        style="margin-left:8px;">
					<i class="fas fa-recycle"></i> {{Supprimer puis recréer dans Home Assistant}}
				</button>
			</div>
			<div id="div_haGatingReason"
			     class="text-muted"
			     style="margin-top:6px; font-size:0.9em; display:none;">
			</div>
		</div>

		<!-- Export diagnostic support -->
		<div class="form-group" style="margin:4px 5px 10px 5px;">
			<div class="col-sm-12">
				<label style="font-weight:normal; margin-right:8px;">
					<input type="checkbox" id="cb_pseudonymize" style="margin-right:4px;"/>
					{{Pseudonymiser les noms d'équipements}}
				</label>
				<button id="bt_exportDiagnostic" class="btn btn-default btn-sm">
					<i class="fas fa-download"></i> {{Télécharger le diagnostic support}}
				</button>
				<span id="span_exportResult" style="display:none; margin-left:8px;"></span>
			</div>
		</div>

		<!-- Story 16.8 — Surface de mapping HA par pièce (modèle Homebridge : pièce -> équipement -> commande).
		     Point d'entrée dédié, supersède l'onglet inatteignable de la 16.5. -->
		<legend><i class="fas fa-home"></i> {{Configuration Home Assistant par pièce}}</legend>
		<div class="alert alert-info" style="margin:10px 5px;">
			<i class="fas fa-info-circle"></i>
			{{Choisissez une pièce pour voir ses équipements et, pour chaque commande, si elle répond aux prérequis Home Assistant (prêt / bloquant + pourquoi). Le type natif Jeedom (partagé Homebridge) n'est jamais modifié.}}
		</div>
		<?php
		if (count($j2haRoomsTree) == 0) {
			echo '<div class="text-center" style="font-size:1.1em; margin:10px 5px;">{{Aucune pièce avec équipement trouvée.}}</div>';
		} else {
			echo '<div class="objectListContainer" id="j2ha_roomCards">';
			foreach ($j2haRoomsTree as $room) {
				echo '<div class="objectDisplayCard cursor j2ha-room-card" data-object_id="' . $room['object_id'] . '" onclick="j2haOpenRoom(' . $room['object_id'] . ')">';
				echo '<i class="fas fa-door-open" style="font-size:3em; margin-top:10px;"></i>';
				echo '<br>';
				echo '<span class="name">' . $room['object_name'] . '</span>';
				echo '<span class="text-muted"> (' . count($room['equipments']) . ')</span>';
				echo '</div>';
			}
			echo '</div>';
		}
		?>

	</div> <!-- /.eqLogicThumbnailDisplay -->

	<!-- Page de présentation de l'équipement -->
	<div class="col-xs-12 eqLogic" style="display: none;">
		<!-- barre de gestion de l'équipement -->
		<div class="input-group pull-right" style="display:inline-flex;">
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
			     dans la surface « Configuration Home Assistant par pièce » (modale par pièce). -->

		</div><!-- /.tab-content -->
	</div><!-- /.eqLogic -->
</div><!-- /.row row-overflow -->

<!-- Inclusion du fichier CSS du plugin (dossier, nom_du_fichier, extension_du_fichier, id_du_plugin) -->
<?php include_file('desktop', 'jeedom2ha', 'css', 'jeedom2ha'); ?>
<!-- Inclusion du fichier javascript du plugin (dossier, nom_du_fichier, extension_du_fichier, id_du_plugin) -->
<?php include_file('desktop', 'jeedom2ha_mapping_override', 'js', 'jeedom2ha'); ?>
<?php include_file('desktop', 'jeedom2ha_mapping_surface', 'js', 'jeedom2ha'); ?>
<?php include_file('desktop', 'jeedom2ha_action_budget', 'js', 'jeedom2ha'); ?>
<?php include_file('desktop', 'jeedom2ha', 'js', 'jeedom2ha'); ?>
<!-- Inclusion du fichier javascript du core - NE PAS MODIFIER NI SUPPRIMER -->
<?php include_file('core', 'plugin.template', 'js'); ?>
