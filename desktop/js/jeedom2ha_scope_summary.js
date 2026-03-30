(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haScopeSummary = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  var ROOM_STATUS_VALUES = {
    'Publiee': true,
    'Partiellement publiee': true,
    'Non publiee': true,
  };
  var ROOM_PERIMETRE_VALUES = {
    'Incluse': true,
    'Exclue': true,
  };

  function isFiniteNumber(value) {
    return typeof value === 'number' && Number.isFinite(value);
  }

  function readCount(counts, key) {
    if (!counts || typeof counts !== 'object') {
      return null;
    }
    return isFiniteNumber(counts[key]) ? counts[key] : null;
  }

  function readString(value, fallback) {
    if (typeof value === 'string' && value.trim() !== '') {
      return value;
    }
    return fallback;
  }

  function readBoolean(value, fallback) {
    if (typeof value === 'boolean') {
      return value;
    }
    return fallback;
  }

  function readCommandCoverage(commands) {
    if (!Array.isArray(commands)) {
      return [];
    }
    var normalized = [];
    for (var i = 0; i < commands.length; i++) {
      var cmd = commands[i];
      if (!cmd || typeof cmd !== 'object') {
        continue;
      }
      normalized.push({
        cmd_id: isFiniteNumber(cmd.cmd_id) ? cmd.cmd_id : null,
        cmd_name: readString(cmd.cmd_name, ''),
        generic_type: readString(cmd.generic_type, ''),
      });
    }
    return normalized;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function toDisplayCount(value) {
    if (isFiniteNumber(value)) {
      return String(value);
    }
    return '&mdash;';
  }

  var MUTED_BADGE_STYLE = 'background-color:#777;color:#fff;';

  function renderMutedBadge(contentHtml) {
    return '<span class="label label-default j2ha-muted-badge" style="' + MUTED_BADGE_STYLE + '">' + contentHtml + '</span>';
  }

  function renderBinaryCount(value) {
    var content = '&nbsp;';
    if (value === null || typeof value === 'undefined') {
      content = '&mdash;';
    } else if (isFiniteNumber(value)) {
      if (value === 1) {
        content = '&#10003;';
      } else if (value === 0) {
        content = '&nbsp;';
      } else {
        content = String(value);
      }
    }
    return '<span class="j2ha-binary-cell" style="display:inline-block;min-width:12px;text-align:center;">' + content + '</span>';
  }

  // Story 3.4 — rétro-compat tests existants (utilitaire indépendant du rendu home)
  function getAggregatedStatusLabel(statusCode) {
    var s = (typeof statusCode === 'string') ? statusCode : '';
    if (s === 'published')           return '<span class="label label-success">Publié</span>';
    if (s === 'excluded')            return '<span class="label" style="background-color:#999;color:#fff;">Exclu</span>';
    if (s === 'ambiguous')           return '<span class="label label-warning">Ambigu</span>';
    if (s === 'not_supported')       return '<span class="label label-default" style="background-color:#666!important;">Non supporté</span>';
    if (s === 'infra_incident')      return '<span class="label label-danger">Incident infrastructure</span>';
    if (s === 'partially_published') return '<span class="label label-success">Publié</span>';
    if (s === 'empty')               return '<span class="label label-default">Vide</span>';
    return '';
  }

  // Story 4.2 — table de correspondance périmètre backend -> libellé UI
  function buildPerimetreLabel(perimetre) {
    if (perimetre === 'exclu_par_piece')      return 'Exclu par la pièce';
    if (perimetre === 'exclu_par_plugin')     return 'Exclu par le plugin';
    if (perimetre === 'exclu_sur_equipement') return 'Exclu sur cet équipement';
    if (perimetre === 'inclus')               return 'Inclus';
    return '';
  }

  function buildCompteurs(rawCompteurs) {
    return {
      total: readCount(rawCompteurs, 'total'),
      inclus: readCount(rawCompteurs, 'inclus'),
      exclus: readCount(rawCompteurs, 'exclus'),
      ecarts: readCount(rawCompteurs, 'ecarts'),
      publies: readCount(rawCompteurs, 'publies'),
    };
  }

  function buildCompteursFallback(rawScopeCounts) {
    return {
      total: readCount(rawScopeCounts, 'total'),
      inclus: readCount(rawScopeCounts, 'include'),
      exclus: readCount(rawScopeCounts, 'exclude'),
      ecarts: null,
      publies: null,
    };
  }

  function readRoomStatus(value) {
    if (typeof value !== 'string') {
      return '';
    }
    return ROOM_STATUS_VALUES[value] === true ? value : '';
  }

  function readRoomPerimetre(value) {
    if (typeof value !== 'string') {
      return '';
    }
    return ROOM_PERIMETRE_VALUES[value] === true ? value : '';
  }

  function buildHomeSignals(rawSignals) {
    var safeSignals = (rawSignals && typeof rawSignals === 'object') ? rawSignals : {};
    var globalSignal = (safeSignals.global && typeof safeSignals.global === 'object') ? safeSignals.global : {};
    var rawPiecesSignals = Array.isArray(safeSignals.pieces) ? safeSignals.pieces : [];

    var piecesByObjectId = {};
    for (var i = 0; i < rawPiecesSignals.length; i++) {
      var pieceSignal = rawPiecesSignals[i];
      if (!pieceSignal || typeof pieceSignal !== 'object') {
        continue;
      }
      var objectId = String(pieceSignal.object_id);
      piecesByObjectId[objectId] = {
        perimetre: readRoomPerimetre(pieceSignal.perimetre),
        publies: isFiniteNumber(pieceSignal.publies) ? pieceSignal.publies : null,
        statut: readRoomStatus(pieceSignal.statut),
      };
    }

    return {
      global: {
        publies: isFiniteNumber(globalSignal.publies) ? globalSignal.publies : null,
        statut: readRoomStatus(globalSignal.statut),
      },
      piecesByObjectId: piecesByObjectId,
    };
  }

  function buildEquipmentModel(entry, equipDiag, isInScope) {
    var diag = (equipDiag && typeof equipDiag === 'object') ? equipDiag : {};
    var perimetre = readString(diag.perimetre, '');
    var ecart = (typeof diag.ecart === 'boolean') ? diag.ecart : null;
    var isExclu = perimetre.indexOf('exclu_') === 0;

    return {
      level: 'equipement',
      eq_id: entry.eq_id,
      name: readString(entry.name, ''),
      effective_state: readString(entry.effective_state, ''),
      perimetre: perimetre,
      perimetre_label: buildPerimetreLabel(perimetre),
      statut: readString(diag.statut, ''),
      ecart: ecart,
      cause_label: readString(diag.cause_label, ''),
      cause_action: readString(diag.cause_action, ''),
      has_pending_home_assistant_changes: readBoolean(entry.has_pending_home_assistant_changes, false),
      status_code: readString(diag.status_code, ''),
      reason_code: readString(diag.reason_code, ''),
      detail: readString(diag.detail, ''),
      remediation: readString(diag.remediation, ''),
      v1_limitation: readBoolean(diag.v1_limitation, false),
      confidence: readString(diag.confidence, ''),
      matched_commands: readCommandCoverage(diag.matched_commands),
      unmatched_commands: readCommandCoverage(diag.unmatched_commands),
      in_scope: isInScope === true,
      counts: {
        total: 1,
        exclus: isExclu ? 1 : 0,
        inclus: perimetre === 'inclus' ? 1 : 0,
        publies: readCount(diag, 'publies'),
        ecarts: ecart === null ? null : (ecart ? 1 : 0),
      },
    };
  }

  function createModel(response) {
    var safeResponse = (response && typeof response === 'object') ? response : {};
    if (safeResponse.status !== 'ok' || !safeResponse.published_scope || typeof safeResponse.published_scope !== 'object') {
      return {
        has_contract: false,
        message: readString(
          safeResponse.message,
          "Aucune synthèse backend disponible. Lancez d'abord une synchronisation."
        ),
      };
    }

    var scope = safeResponse.published_scope;
    var globalSection = (scope.global && typeof scope.global === 'object') ? scope.global : {};
    var pieces = Array.isArray(scope.pieces) ? scope.pieces : [];
    var equipements = Array.isArray(scope.equipements) ? scope.equipements : [];

    var inScopeRaw = Array.isArray(safeResponse.in_scope_equipments) ? safeResponse.in_scope_equipments : null;
    var inScopeByEqId = null;
    if (inScopeRaw !== null) {
      inScopeByEqId = {};
      for (var s = 0; s < inScopeRaw.length; s++) {
        var scoped = inScopeRaw[s];
        if (scoped && scoped.eq_id != null) {
          inScopeByEqId[String(scoped.eq_id)] = true;
        }
      }
    }

    var diagEquipments = (safeResponse.diagnostic_equipments && typeof safeResponse.diagnostic_equipments === 'object')
      ? safeResponse.diagnostic_equipments : {};
    var diagRooms = Array.isArray(safeResponse.diagnostic_rooms) ? safeResponse.diagnostic_rooms : [];
    var diagSummary = (safeResponse.diagnostic_summary && typeof safeResponse.diagnostic_summary === 'object')
      ? safeResponse.diagnostic_summary : null;

    var homeSignals = buildHomeSignals(safeResponse.home_signals);

    var diagRoomCompteursByObjectId = {};
    for (var r = 0; r < diagRooms.length; r++) {
      var dr = diagRooms[r];
      if (!dr || typeof dr !== 'object') {
        continue;
      }
      var roomObjId = (dr.object_id != null) ? dr.object_id : 0;
      diagRoomCompteursByObjectId[String(roomObjId)] = (dr.compteurs && typeof dr.compteurs === 'object')
        ? dr.compteurs
        : null;
    }

    var normalizedPieces = [];
    var piecesByObjectId = {};

    for (var i = 0; i < pieces.length; i++) {
      var piece = pieces[i];
      if (!piece || typeof piece !== 'object') {
        continue;
      }
      var objectIdKey = String(piece.object_id);
      var diagCompteurs = diagRoomCompteursByObjectId[objectIdKey] || null;
      var pieceCounters = diagCompteurs ? buildCompteurs(diagCompteurs) : buildCompteursFallback(piece.counts);
      var pieceSignals = homeSignals.piecesByObjectId[objectIdKey] || { perimetre: '', publies: null, statut: '' };
      pieceCounters.publies = pieceSignals.publies;

      var normalizedPiece = {
        level: 'piece',
        object_id: piece.object_id,
        object_name: readString(piece.object_name, 'Aucune pièce'),
        perimetre_room: pieceSignals.perimetre,
        status_room: pieceSignals.statut,
        counts: pieceCounters,
        equipements: [],
      };
      normalizedPieces.push(normalizedPiece);
      piecesByObjectId[objectIdKey] = normalizedPiece;
    }

    for (var j = 0; j < equipements.length; j++) {
      var equipement = equipements[j];
      if (!equipement || typeof equipement !== 'object') {
        continue;
      }

      var pieceModel = piecesByObjectId[String(equipement.object_id)];
      if (!pieceModel) {
        continue;
      }

      var eqDiag = diagEquipments[equipement.eq_id] || diagEquipments[String(equipement.eq_id)] || null;
      var isInScope = inScopeByEqId ? inScopeByEqId[String(equipement.eq_id)] === true : false;
      pieceModel.equipements.push(buildEquipmentModel(equipement, eqDiag, isInScope));
    }

    var globalCompteurs = (diagSummary && diagSummary.compteurs && typeof diagSummary.compteurs === 'object')
      ? diagSummary.compteurs
      : null;
    var globalCounts = globalCompteurs ? buildCompteurs(globalCompteurs) : buildCompteursFallback(globalSection.counts);
    globalCounts.publies = homeSignals.global.publies;

    return {
      has_contract: true,
      global: {
        level: 'global',
        key: 'global',
        name: 'Parc global',
        status_room: homeSignals.global.statut,
        counts: globalCounts,
      },
      pieces: normalizedPieces,
    };
  }

  function renderTableHeader() {
    var html = '';
    html += '<thead><tr>';
    html += '<th>Nom</th>';
    html += '<th>Perimetre</th>';
    html += '<th>Statut</th>';
    html += '<th>Ecart</th>';
    html += '<th>Total</th>';
    html += '<th>Exclus</th>';
    html += '<th>Inclus</th>';
    html += '<th>Publies</th>';
    html += '<th>Ecarts</th>';
    html += '</tr></thead>';
    return html;
  }

  function renderNameCell(label, level, isToggle, nodeId) {
    var indentPx = 0;
    if (level === 'piece') {
      indentPx = 12;
    } else if (level === 'equipement') {
      indentPx = 24;
    }

    var html = '<div style="display:flex;align-items:center;">';
    html += '<span style="display:inline-block;width:' + indentPx + 'px;"></span>';

    if (isToggle) {
      html += '<span class="j2ha-toggle-icon" data-node-id="' + escapeHtml(nodeId) + '" style="margin-right:6px;font-size:0.8em;color:#888;">&#9654;</span>';
    } else {
      html += '<span style="display:inline-block;width:10px;margin-right:6px;"></span>';
    }

    html += '<span>' + escapeHtml(label) + '</span>';
    html += '</div>';
    return html;
  }

  function renderPerimetreBadge(perimetre, level) {
    if (level !== 'equipement') {
      return renderMutedBadge('&mdash;');
    }
    if (perimetre === 'inclus') {
      return '<span class="label label-success">Inclus</span>';
    }
    var label = buildPerimetreLabel(perimetre);
    if (label !== '') {
      return renderMutedBadge(escapeHtml(label));
    }
    return renderMutedBadge('&mdash;');
  }

  function renderRoomPerimetreBadge(perimetreRoom) {
    if (perimetreRoom === 'Incluse') {
      return '<span class="label label-success">Incluse</span>';
    }
    if (perimetreRoom === 'Exclue') {
      return renderMutedBadge('Exclue');
    }
    return renderMutedBadge('&mdash;');
  }

  function renderRoomStatusBadge(statusRoom) {
    if (statusRoom === 'Publiee') {
      return '<span class="label label-success">Publiee</span>';
    }
    if (statusRoom === 'Partiellement publiee') {
      return '<span class="label label-warning">Partiellement publiee</span>';
    }
    if (statusRoom === 'Non publiee') {
      return renderMutedBadge('Non publiee');
    }
    return renderMutedBadge('&mdash;');
  }

  function renderEquipmentStatutBadge(statut) {
    if (statut === 'publie') {
      return '<span class="label label-success">Publié</span>';
    }
    if (statut === 'non_publie') {
      return renderMutedBadge('Non publié');
    }
    return renderMutedBadge('&mdash;');
  }

  function renderPieceEcartBadge(ecartsCount) {
    if (!isFiniteNumber(ecartsCount)) {
      return renderMutedBadge('&mdash;');
    }
    if (ecartsCount > 0) {
      return '<span class="label label-warning">Ecart</span>';
    }
    return '<span class="label label-success">Alignée</span>';
  }

  function renderEquipmentEcartBadge(equipement) {
    if (equipement.ecart === true) {
      var cause = equipement.cause_label !== '' ? equipement.cause_label : 'Cause indisponible';
      var tooltip = cause + ' | Voir le diagnostic pour le detail';
      return '<span class="label label-warning j2ha-ecart-badge j2ha-ecart-clickable j2ha-ecart-affordance" role="button" tabindex="0"'
        + ' style="cursor:pointer;"'
        + ' data-eq-id="' + escapeHtml(String(equipement.eq_id)) + '"'
        + ' title="' + escapeHtml(tooltip) + '">Ecart</span>';
    }
    if (equipement.ecart === false) {
      return '<span class="label label-success">Aligné</span>';
    }
    return renderMutedBadge('&mdash;');
  }

  function renderRow(columns, options) {
    var classes = options.classes || '';
    var attrs = options.attrs || '';
    var style = options.style || '';
    var html = '<tr class="' + classes + '" ' + attrs;
    if (style !== '') {
      html += ' style="' + style + '"';
    }
    html += '>';
    for (var i = 0; i < columns.length; i++) {
      html += '<td>' + columns[i] + '</td>';
    }
    html += '</tr>';
    return html;
  }

  function render(model) {
    if (!model || model.has_contract !== true) {
      var message = readString(model && model.message, "Aucune synthèse backend disponible. Lancez d'abord une synchronisation.");
      return '<div class="alert alert-info" style="margin-bottom:0;">' + escapeHtml(message) + '</div>';
    }

    var html = '';
    html += '<div class="table-responsive" style="margin-top:0;">';
    html += '<table class="table table-condensed table-bordered" id="table_scopeSummaryHierarchy">';
    html += renderTableHeader();
    html += '<tbody>';

    var globalColumns = [
      renderNameCell(model.global.name, 'global', true, 'global'),
      renderMutedBadge('&mdash;'),
      renderMutedBadge('&mdash;'),
      renderPieceEcartBadge(model.global.counts.ecarts),
      toDisplayCount(model.global.counts.total),
      toDisplayCount(model.global.counts.exclus),
      toDisplayCount(model.global.counts.inclus),
      toDisplayCount(model.global.counts.publies),
      toDisplayCount(model.global.counts.ecarts),
    ];

    html += renderRow(globalColumns, {
      classes: 'j2ha-row-global j2ha-row-toggle',
      attrs: 'data-node-type="global" data-node-id="global" data-expanded="false"',
      style: 'cursor:pointer;',
    });

    for (var i = 0; i < model.pieces.length; i++) {
      var piece = model.pieces[i];
      var pieceNodeId = 'piece-' + String(piece.object_id);
      var pieceColumns = [
        renderNameCell(piece.object_name, 'piece', true, pieceNodeId),
        renderRoomPerimetreBadge(piece.perimetre_room),
        renderRoomStatusBadge(piece.status_room),
        renderPieceEcartBadge(piece.counts.ecarts),
        toDisplayCount(piece.counts.total),
        toDisplayCount(piece.counts.exclus),
        toDisplayCount(piece.counts.inclus),
        toDisplayCount(piece.counts.publies),
        toDisplayCount(piece.counts.ecarts),
      ];

      html += renderRow(pieceColumns, {
        classes: 'j2ha-row-piece j2ha-row-toggle j2ha-child-of-global',
        attrs: 'data-node-type="piece" data-node-id="' + escapeHtml(pieceNodeId) + '" data-piece-id="' + escapeHtml(String(piece.object_id)) + '" data-expanded="false"',
        style: 'display:none;cursor:pointer;',
      });

      for (var j = 0; j < piece.equipements.length; j++) {
        var eq = piece.equipements[j];
        var label = eq.name !== '' ? (eq.name + ' (#' + String(eq.eq_id) + ')') : ('#' + String(eq.eq_id));
        var eqColumns = [
          renderNameCell(label, 'equipement', false, ''),
          renderPerimetreBadge(eq.perimetre, 'equipement'),
          renderEquipmentStatutBadge(eq.statut),
          renderEquipmentEcartBadge(eq),
          renderBinaryCount(eq.counts.total),
          renderBinaryCount(eq.counts.exclus),
          renderBinaryCount(eq.counts.inclus),
          renderBinaryCount(eq.counts.publies),
          renderBinaryCount(eq.counts.ecarts),
        ];

        html += renderRow(eqColumns, {
          classes: 'j2ha-row-equipement j2ha-child-of-piece-' + escapeHtml(String(piece.object_id)),
          attrs: 'data-piece-id="' + escapeHtml(String(piece.object_id)) + '" data-eq-id="' + escapeHtml(String(eq.eq_id)) + '"',
          style: 'display:none;',
        });
      }
    }

    if (model.pieces.length === 0) {
      html += '<tr><td colspan="9" class="text-center"><em>Aucune pièce disponible dans le contrat backend</em></td></tr>';
    }

    html += '</tbody></table></div>';
    return html;
  }

  return {
    createModel: createModel,
    render: render,
    getAggregatedStatusLabel: getAggregatedStatusLabel,
    buildPerimetreLabel: buildPerimetreLabel,
  };
}));
