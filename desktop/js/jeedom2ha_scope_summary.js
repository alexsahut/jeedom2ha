(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haScopeSummary = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

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

  // Story 3.4 — Task 5 : mapper statuts agrégés backend → badge UI (status_code canonique)
  // Pure présentation — aucune logique métier. La source de vérité reste aggregation.py.
  function getAggregatedStatusLabel(statusCode) {
    var s = (typeof statusCode === 'string') ? statusCode : '';
    if (s === 'published')           return '<span class="label label-success">Publié</span>';
    if (s === 'excluded')            return '<span class="label" style="background-color:#999;color:#fff;">Exclu</span>';
    if (s === 'ambiguous')           return '<span class="label label-warning">Ambigu</span>';
    if (s === 'not_supported')       return '<span class="label label-default" style="background-color:#666!important;">Non supporté</span>';
    if (s === 'infra_incident')      return '<span class="label label-danger">Incident infrastructure</span>';
    // Story 4.3 : "Partiellement publié" absorbé — statut principal = Publié
    if (s === 'partially_published') return '<span class="label label-success">Publié</span>';
    if (s === 'empty')               return '<span class="label label-default">Vide</span>';
    return '';
  }

  // Story 3.4 — Compteurs compacts counts_by_status (lecture seule depuis backend)
  function renderCountsByStatus(counts) {
    if (!counts || typeof counts !== 'object') { return ''; }
    var order = ['published', 'partially_published', 'ambiguous', 'excluded', 'not_supported', 'infra_incident'];
    var labels = {
      'published': 'Publié', 'partially_published': 'Partiel',
      'ambiguous': 'Ambigu', 'excluded': 'Exclu',
      'not_supported': 'Non sup.', 'infra_incident': 'Infra'
    };
    var parts = [];
    for (var s = 0; s < order.length; s++) {
      var code = order[s];
      var count = counts[code];
      if (isFiniteNumber(count) && count > 0) {
        parts.push('<span style="font-size:0.8em;margin-left:4px;color:#555;">' + escapeHtml(labels[code] || code) + ':&nbsp;' + count + '</span>');
      }
    }
    return parts.join('');
  }

  // Story 4.2 — table de correspondance perimetre backend → libellé UI (source de vérité unique)
  function buildPerimetreLabel(perimetre) {
    if (perimetre === 'exclu_par_piece')      return 'Exclu par la pièce';
    if (perimetre === 'exclu_par_plugin')     return 'Exclu par le plugin';
    if (perimetre === 'exclu_sur_equipement') return 'Exclu sur cet équipement';
    return '';
  }

  // Story 4.2 — lit les compteurs depuis le contrat diagnostics 4.1 (inclus/exclus/ecarts)
  function buildCompteurs(rawCompteurs) {
    return {
      total:  readCount(rawCompteurs, 'total'),
      inclus: readCount(rawCompteurs, 'inclus'),
      exclus: readCount(rawCompteurs, 'exclus'),
      ecarts: readCount(rawCompteurs, 'ecarts'),
    };
  }

  // Story 4.2 — fallback daemon-down : traduit les clés scope (include/exclude) vers le nouveau modèle
  function buildCompteursFallback(rawScopeCounts) {
    return {
      total:  readCount(rawScopeCounts, 'total'),
      inclus: readCount(rawScopeCounts, 'include'),
      exclus: readCount(rawScopeCounts, 'exclude'),
      ecarts: null,
    };
  }

  // Story 4.3 — table de traduction confidence backend → libellé UI (diagnostic technique uniquement)
  function translateConfidence(value) {
    if (value === 'sure')      return 'Sûr';
    if (value === 'probable')  return 'Probable';
    if (value === 'ambiguous') return 'Ambigu';
    return '';
  }

  // Story 3.4 — equipDiag : données diagnostic backend pour cet équipement (null si absent)
  // Story 4.2 — perimetre_label depuis contrat diagnostics 4.1 (lecture seule)
  // Story 4.3 — confidence et in_scope ajoutés (lecture seule)
  function buildEquipmentModel(entry, equipDiag, isInScope) {
    var diag = (equipDiag && typeof equipDiag === 'object') ? equipDiag : {};
    var perimetre = readString(diag.perimetre, '');
    return {
      eq_id: entry.eq_id,
      name: readString(entry.name, ''),
      effective_state: readString(entry.effective_state, ''),
      perimetre: perimetre,
      perimetre_label: buildPerimetreLabel(perimetre),
      statut: readString(diag.statut, ''),
      ecart: (typeof diag.ecart === 'boolean') ? diag.ecart : null,
      cause_label: readString(diag.cause_label, ''),
      cause_action: readString(diag.cause_action, ''),
      has_pending_home_assistant_changes: readBoolean(entry.has_pending_home_assistant_changes, false),
      // Story 3.4 — contrat métier backend (lecture seule — source : taxonomy.py + _DIAGNOSTIC_MESSAGES)
      status_code:   readString(diag.status_code, ''),
      reason_code:   readString(diag.reason_code, ''),
      detail:        readString(diag.detail, ''),
      remediation:   readString(diag.remediation, ''),
      v1_limitation: readBoolean(diag.v1_limitation, false),
      // Story 4.3 — confiance visible uniquement en diagnostic technique détaillé
      confidence: readString(diag.confidence, ''),
      // Story 4.4 / AC8 — détails de couverture commandes (surface technique uniquement)
      matched_commands: readCommandCoverage(diag.matched_commands),
      unmatched_commands: readCommandCoverage(diag.unmatched_commands),
      // Story 4.3 — in_scope : true si l'équipement est dans la surface filtrée backend
      in_scope: isInScope === true,
    };
  }

  function toDisplayCount(value) {
    if (isFiniteNumber(value)) {
      return String(value);
    }
    return '&mdash;';
  }

  function getPerimetreDisplayLabel(perimetre) {
    if (perimetre === 'inclus')                 return 'Inclus';
    if (perimetre === 'exclu_par_piece')        return 'Exclu par la pièce';
    if (perimetre === 'exclu_par_plugin')       return 'Exclu par le plugin';
    if (perimetre === 'exclu_sur_equipement')   return 'Exclu sur cet équipement';
    return 'Périmètre inconnu';
  }

  function getStatutDisplayLabel(statut) {
    if (statut === 'publie')     return 'Publié';
    if (statut === 'non_publie') return 'Non publié';
    return 'Statut inconnu';
  }

  function getEcartDisplayLabel(ecart) {
    if (ecart === true)  return 'Écart à traiter';
    if (ecart === false) return 'Aligné';
    return 'Écart inconnu';
  }

  function renderPerimetreBadge(perimetre) {
    var label = getPerimetreDisplayLabel(perimetre);
    if (perimetre === 'inclus') {
      return '<span class="label label-success">Périmètre : ' + escapeHtml(label) + '</span>';
    }
    if (perimetre.indexOf('exclu_') === 0) {
      return '<span class="label" style="background-color:#777;color:#fff;">Périmètre : ' + escapeHtml(label) + '</span>';
    }
    return '<span class="label label-default">Périmètre : ' + escapeHtml(label) + '</span>';
  }

  function renderStatutBadge(statut) {
    var label = getStatutDisplayLabel(statut);
    if (statut === 'publie') {
      return '<span class="label label-success">Statut : ' + escapeHtml(label) + '</span>';
    }
    if (statut === 'non_publie') {
      return '<span class="label label-default" style="background-color:#666!important;">Statut : ' + escapeHtml(label) + '</span>';
    }
    return '<span class="label label-default">Statut : ' + escapeHtml(label) + '</span>';
  }

  function renderEcartBadge(ecart) {
    var label = getEcartDisplayLabel(ecart);
    if (ecart === true) {
      return '<span class="label label-warning">Écart : ' + escapeHtml(label) + '</span>';
    }
    if (ecart === false) {
      return '<span class="label label-default">Écart : ' + escapeHtml(label) + '</span>';
    }
    return '<span class="label label-default">Écart : ' + escapeHtml(label) + '</span>';
  }

  function renderCauseLines(equipement) {
    if (equipement.ecart !== true) {
      return '';
    }
    var causeLabel = (equipement.cause_label !== '') ? equipement.cause_label : 'Cause non renseignée';
    var html = '';
    html += '<div style="margin-top:4px;font-size:0.9em;color:#555;"><em>Cause</em> : ' + escapeHtml(causeLabel) + '</div>';
    if (equipement.cause_action !== '') {
      html += '<div style="margin-top:2px;font-size:0.9em;color:#777;"><em>Action</em> : ' + escapeHtml(equipement.cause_action) + '</div>';
    }
    return html;
  }

  function renderCommandCoverageItems(commands) {
    var items = [];
    for (var i = 0; i < commands.length; i++) {
      var cmd = commands[i];
      var parts = [];
      if (cmd.cmd_id !== null) {
        parts.push('#' + String(cmd.cmd_id));
      }
      if (cmd.cmd_name !== '') {
        parts.push(cmd.cmd_name);
      }
      if (cmd.generic_type !== '') {
        parts.push('(' + cmd.generic_type + ')');
      }
      if (parts.length === 0) {
        parts.push('commande non renseignée');
      }
      items.push('<li>' + escapeHtml(parts.join(' ')) + '</li>');
    }
    return '<ul style="margin:4px 0 0 16px;padding:0;">' + items.join('') + '</ul>';
  }

  function renderCommandCoverageSection(equipement) {
    var matched = Array.isArray(equipement.matched_commands) ? equipement.matched_commands : [];
    var unmatched = Array.isArray(equipement.unmatched_commands) ? equipement.unmatched_commands : [];
    if (matched.length === 0 && unmatched.length === 0) {
      return '';
    }

    var html = '';
    html += '<div style="margin-top:4px;font-size:0.9em;color:#555;">';
    html += '<em>Couverture commandes</em> : ' + matched.length + ' mappée(s), ' + unmatched.length + ' non mappée(s)';
    html += '</div>';

    if (matched.length > 0) {
      html += '<div style="margin-top:2px;font-size:0.85em;color:#666;"><em>matched_commands</em></div>';
      html += renderCommandCoverageItems(matched);
    }
    if (unmatched.length > 0) {
      html += '<div style="margin-top:2px;font-size:0.85em;color:#666;"><em>unmatched_commands</em></div>';
      html += renderCommandCoverageItems(unmatched);
    }

    return html;
  }

  function renderFourDSurface(surfaceClassName, surfaceTitle, equipement) {
    var html = '<div class="' + surfaceClassName + '" style="margin-top:6px;margin-left:4px;">';
    html += '<div style="font-size:0.85em;color:#666;"><strong>' + escapeHtml(surfaceTitle) + '</strong></div>';
    html += '<div style="margin-top:3px;">';
    html += renderPerimetreBadge(equipement.perimetre);
    html += '<span style="margin-left:6px;">' + renderStatutBadge(equipement.statut) + '</span>';
    html += '<span style="margin-left:6px;">' + renderEcartBadge(equipement.ecart) + '</span>';
    html += '</div>';
    html += renderCauseLines(equipement);
    html += '</div>';
    return html;
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

    // Story 4.3 — surface filtrée in-scope depuis backend (perimetre=inclus uniquement)
    // Graceful degradation : absent → fallback comportement actuel (tous les détails affichés)
    var inScopeRaw = Array.isArray(safeResponse.in_scope_equipments) ? safeResponse.in_scope_equipments : null;
    var inScopeByEqId = null;
    if (inScopeRaw !== null) {
      inScopeByEqId = {};
      for (var k = 0; k < inScopeRaw.length; k++) {
        var ise = inScopeRaw[k];
        if (ise && ise.eq_id != null) {
          inScopeByEqId[String(ise.eq_id)] = true;
        }
      }
    }

    // Story 3.4 — données diagnostic (soft : absent si daemon indisponible)
    var diagEquipments = (safeResponse.diagnostic_equipments && typeof safeResponse.diagnostic_equipments === 'object')
      ? safeResponse.diagnostic_equipments : {};
    var diagRooms = Array.isArray(safeResponse.diagnostic_rooms) ? safeResponse.diagnostic_rooms : [];
    var diagSummary = (safeResponse.diagnostic_summary && typeof safeResponse.diagnostic_summary === 'object')
      ? safeResponse.diagnostic_summary : null;

    // Index rooms diagnostic par object_id pour lookup O(1)
    var diagRoomByObjectId = {};
    var diagRoomCompteursByObjectId = {};
    for (var r = 0; r < diagRooms.length; r++) {
      var dr = diagRooms[r];
      if (dr && typeof dr === 'object') {
        // Normalise object_id : le scope utilise 0 pour "Aucun", le diagnostic utilise null
        var roomObjId = (dr.object_id != null) ? dr.object_id : 0;
        diagRoomByObjectId[String(roomObjId)] = (dr.summary && typeof dr.summary === 'object') ? dr.summary : null;
        // Story 4.2 — compteurs par pièce depuis contrat diagnostics 4.1
        diagRoomCompteursByObjectId[String(roomObjId)] = (dr.compteurs && typeof dr.compteurs === 'object') ? dr.compteurs : null;
      }
    }

    var normalizedPieces = [];
    var piecesByObjectId = {};

    for (var i = 0; i < pieces.length; i++) {
      var piece = pieces[i];
      if (!piece || typeof piece !== 'object') {
        continue;
      }
      // Story 4.2 — compteurs depuis diagnostics si disponibles, sinon fallback scope
      var diagCompteurs = diagRoomCompteursByObjectId[String(piece.object_id)] || null;
      var normalizedPiece = {
        object_id: piece.object_id,
        object_name: readString(piece.object_name, 'Aucune pièce'),
        counts: diagCompteurs ? buildCompteurs(diagCompteurs) : buildCompteursFallback(piece.counts),
        has_pending_home_assistant_changes: readBoolean(piece.has_pending_home_assistant_changes, false),
        equipements: [],
        // Story 3.4 — agrégation backend par pièce (null si daemon absent)
        diagnostic_summary: diagRoomByObjectId[String(piece.object_id)] || null,
      };
      normalizedPieces.push(normalizedPiece);
      piecesByObjectId[String(piece.object_id)] = normalizedPiece;
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

      // Story 3.4 — lookup données diagnostic par eq_id (clés numériques JSON → prop string en JS)
      var eqDiag = diagEquipments[equipement.eq_id] || diagEquipments[String(equipement.eq_id)] || null;
      // Story 4.3 — isInScope : true si in_scope_equipments disponible ET eq_id présent dedans
      // Story 4.4 — fallback robuste non-sémantique : si la surface in_scope est absente,
      // s'appuyer uniquement sur perimetre backend quand il est fourni.
      var isInScope = false;
      if (inScopeByEqId === null) {
        var diagPerimetre = (eqDiag && typeof eqDiag === 'object') ? readString(eqDiag.perimetre, '') : '';
        isInScope = (diagPerimetre === '') ? true : (diagPerimetre === 'inclus');
      } else {
        isInScope = (inScopeByEqId[String(equipement.eq_id)] === true);
      }
      pieceModel.equipements.push(buildEquipmentModel(equipement, eqDiag, isInScope));
    }

    // Story 4.2 — compteurs globaux depuis diagnostics si disponibles, sinon fallback scope
    var globalCompteurs = (diagSummary && diagSummary.compteurs && typeof diagSummary.compteurs === 'object') ? diagSummary.compteurs : null;
    return {
      has_contract: true,
      global_counts: globalCompteurs ? buildCompteurs(globalCompteurs) : buildCompteursFallback(globalSection.counts),
      global_pending: readBoolean(globalSection.has_pending_home_assistant_changes, false),
      pieces: normalizedPieces,
      // Story 3.4 — agrégation backend globale (null si daemon absent)
      diagnostic_summary: diagSummary,
    };
  }

  function renderStat(title, value) {
    var html = '<div class="col-xs-6 col-sm-3" style="margin-bottom:8px;">';
    html += '<div class="well well-sm" style="margin-bottom:0;">';
    html += '<div style="font-size:0.85em;color:#666;">' + escapeHtml(title) + '</div>';
    html += '<div style="font-size:1.35em;font-weight:600;line-height:1.2;">' + toDisplayCount(value) + '</div>';
    html += '</div></div>';
    return html;
  }

  function renderEquipmentState(state) {
    var normalizedState = readString(state, '');
    if (normalizedState === 'include') {
      return '<span class="label label-success">' + escapeHtml(normalizedState) + '</span>';
    }
    if (normalizedState === 'exclude') {
      return '<span class="label" style="background-color:#999;color:#fff;">' + escapeHtml(normalizedState) + '</span>';
    }
    return '<span class="label label-default">' + escapeHtml(normalizedState || 'inconnu') + '</span>';
  }

  function renderPieceEquipements(piece) {
    var equipements = Array.isArray(piece.equipements) ? piece.equipements : [];
    var html = '<div><strong>{{Équipements}}</strong></div>';

    if (equipements.length === 0) {
      html += '<div class="text-muted" style="margin-top:6px;"><em>{{Aucun équipement visible dans cette pièce côté contrat backend}}</em></div>';
      return html;
    }

    html += '<ul class="list-unstyled" style="margin:8px 0 0 0;">';
    for (var i = 0; i < equipements.length; i++) {
      var equipement = equipements[i];
      html += '<li style="padding:6px 0;' + (i > 0 ? 'border-top:1px solid #eee;' : '') + '">';
      if (equipement.name !== '') {
        html += '<span style="font-weight:bold;margin-right:8px;">' + escapeHtml(equipement.name) + '</span>';
        html += '<span style="font-size:0.9em;color:#777;">(#' + escapeHtml(equipement.eq_id) + ')</span>';
      } else {
        html += '<span class="label label-info">#' + escapeHtml(equipement.eq_id) + '</span>';
      }
      if (equipement.has_pending_home_assistant_changes === true) {
        html += '<span class="label label-warning" style="margin-left:8px;">Changements à appliquer</span>';
      }

      // Surface 1 — Console principale : lecture 4D native, visible pour tous les équipements
      html += renderFourDSurface('j2ha-surface-console', 'Console principale', equipement);

      // Surfaces 2/3 — uniquement in-scope : diagnostic utilisateur + diagnostic technique détaillé
      if (equipement.in_scope === true) {
        html += renderFourDSurface('j2ha-surface-diagnostic-user', 'Diagnostic utilisateur', equipement);

        html += '<details class="j2ha-surface-diagnostic-tech" style="margin-top:6px;margin-left:4px;">';
        html += '<summary style="font-size:0.85em;color:#666;"><strong>Diagnostic technique détaillé</strong></summary>';

        if (equipement.status_code !== '') {
          html += '<div style="margin-top:4px;font-size:0.9em;color:#555;"><em>status_code</em> : ' + escapeHtml(equipement.status_code);
          var statusCodeLabel = getAggregatedStatusLabel(equipement.status_code);
          if (statusCodeLabel !== '') {
            html += ' <span style="margin-left:4px;">' + statusCodeLabel + '</span>';
          }
          html += '</div>';
        }
        if (equipement.reason_code !== '') {
          html += '<div style="margin-top:2px;font-size:0.9em;color:#555;"><em>reason_code</em> : ' + escapeHtml(equipement.reason_code) + '</div>';
        }
        if (equipement.detail !== '') {
          html += '<div style="margin-top:2px;font-size:0.9em;color:#555;">' + escapeHtml(equipement.detail) + '</div>';
        }
        if (equipement.remediation !== '') {
          html += '<div style="margin-top:2px;font-size:0.9em;color:#777;"><em>Action recommandée</em> : ' + escapeHtml(equipement.remediation) + '</div>';
        }
        if (equipement.v1_limitation === true) {
          html += '<div style="margin-top:4px;"><span class="label label-default">Limitation Home Assistant</span></div>';
        }
        var confidenceLabel = translateConfidence(equipement.confidence);
        if (confidenceLabel !== '') {
          html += '<div style="margin-top:2px;font-size:0.85em;color:#777;"><em>Confiance</em> : ' + escapeHtml(confidenceLabel) + '</div>';
        }
        html += renderCommandCoverageSection(equipement);
        html += '</details>';
      }
      html += '</li>';
    }
    html += '</ul>';
    return html;
  }

  function render(model) {
    if (!model || model.has_contract !== true) {
      var message = readString(model && model.message, "Aucune synthèse backend disponible. Lancez d'abord une synchronisation.");
      return '<div class="alert alert-info" style="margin-bottom:0;">' + escapeHtml(message) + '</div>';
    }

    var html = '';
    html += '<div class="row">';
    html += renderStat('Total', model.global_counts.total);
    html += renderStat('Inclus', model.global_counts.inclus);
    html += renderStat('Exclus', model.global_counts.exclus);
    html += renderStat('Écarts', model.global_counts.ecarts);
    html += '</div>';
    if (model.global_pending === true) {
      html += '<div style="margin-bottom:8px;"><span class="label label-warning">Changements à appliquer</span></div>';
    }

    html += '<div class="table-responsive" style="margin-top:10px;">';
    html += '<table class="table table-condensed table-bordered" id="table_scopeSummaryPieces">';
    html += '<thead><tr>';
    html += '<th>{{Pièce}}</th>';
    html += '<th style="width:90px;">{{Total}}</th>';
    html += '<th style="width:90px;">{{Inclus}}</th>';
    html += '<th style="width:90px;">{{Exclus}}</th>';
    html += '<th style="width:110px;">{{Écarts}}</th>';
    html += '</tr></thead><tbody>';

    if (model.pieces.length === 0) {
      html += '<tr><td colspan="5" class="text-center"><em>{{Aucune pièce disponible dans le contrat backend}}</em></td></tr>';
    } else {
      for (var i = 0; i < model.pieces.length; i++) {
        var piece = model.pieces[i];
        var pieceIdAttr = escapeHtml(String(piece.object_id));
        html += '<tr class="j2ha-piece-summary" data-piece-id="' + pieceIdAttr + '" style="cursor:pointer;">';
        html += '<td>';
        html += '<span class="j2ha-toggle-icon" style="margin-right:6px;font-size:0.8em;color:#888;">&#9654;</span>';
        html += escapeHtml(piece.object_name);
        if (piece.has_pending_home_assistant_changes === true) {
          html += ' <span class="label label-warning">Changements à appliquer</span>';
        }
        html += '</td>';
        html += '<td>' + toDisplayCount(piece.counts.total) + '</td>';
        html += '<td>' + toDisplayCount(piece.counts.inclus) + '</td>';
        html += '<td>' + toDisplayCount(piece.counts.exclus) + '</td>';
        html += '<td>' + toDisplayCount(piece.counts.ecarts) + '</td>';
        html += '</tr>';
        html += '<tr class="j2ha-piece-detail" data-piece-id="' + pieceIdAttr + '" style="display:none;">';
        html += '<td colspan="5">' + renderPieceEquipements(piece) + '</td>';
        html += '</tr>';
      }
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
