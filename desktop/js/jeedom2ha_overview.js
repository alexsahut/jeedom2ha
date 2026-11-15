/* Story 25.3 — Page principale B : lecture des états (un seul appel), agrégats, jauge maison filtrante,
 * cartes de pièce, barre de santé (menu « ⋯ », boîte du diagnostic).
 *
 * Aucune règle d'état n'est écrite ici : l'état d'un équipement est le retour de `resolveEquipmentState`
 * (25.1), les compteurs de pièce sont ceux de `summarizeRoom`, la maison en est la somme. La route
 * `getEquipmentStates` (25.2) est lue par UNE fonction (`ajaxFetch`) ; `refresh=1` n'y est posé que par
 * le bouton « Actualiser ». Partie pure (testée sous Node) + partie navigateur en fin de fichier. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('./jeedom2ha_mapping_override.js'),
      function () { return require('./jeedom2ha_lexique.js'); }, function () { return require('./jeedom2ha_ha_side.js'); });
    return;
  }
  root.Jeedom2haOverview = factory(root.Jeedom2haMappingOverride,
    function () { return root.Jeedom2haLexique || null; }, function () { return root.Jeedom2haHaSide || null; });
}(typeof globalThis !== 'undefined' ? globalThis : this, function (M, lexicon, haSide) {
  'use strict';

  // Front v3 (Lot 6) : composant d'aide unique (jeedom2ha_infotip.js), chargé avant ce module dans la page ; sous node, requis.
  function infoTipApi() {
    var g = typeof globalThis !== 'undefined' ? globalThis : null;
    if (g && g.Jeedom2haInfoTip) return g.Jeedom2haInfoTip;
    if (typeof require === 'function') { try { return require('./jeedom2ha_infotip.js'); } catch (e) { return null; } }
    return null;
  }

  // Pastille ou marque purement informative : focusable, cliquable, même bulle que ⓘ ; son `title` reste en complément.
  function infoTip($el, opts) { var T = infoTipApi(); return T ? T.attach($el, undefined, opts) : $el; }


  var AJAX_URL = 'plugins/jeedom2ha/core/ajax/jeedom2ha.ajax.php';
  var COALESCE_MS = 500;            // Q7 : une action = une relecture, coalescée
  var RETRY_DELAYS_MS = [2000, 5000, 10000]; // Q6 : au plus 3 relectures pendant une opération
  var VISIBLE_MIN_AGE_MS = 60000;   // Q10 : retour d'onglet, seulement si la lecture a plus de 60 s
  var AJAX_TIMEOUT_MS = 20000;

  function w(text) { return '{{' + text + '}}'; }

  function plural(count, singular, pluralForm) {
    return count + ' ' + w(count > 1 ? pluralForm : singular);
  }

  // --- Libellés (AC4, AC10, AC11) : les mots d'état viennent de M.EQUIPMENT_STATE_LABELS ---
  var MSG_NEVER_SYNCED = '{{Aucune synchronisation n\'a encore eu lieu}}';
  var MSG_ACTION_NOTICE = '{{Opération en cours : ces chiffres peuvent changer}}';
  var MSG_IN_PROGRESS = '{{Mise à jour en cours…}}';
  var MSG_UNAVAILABLE = '{{Chiffres indisponibles}}';

  function unreadLabel(count) { return plural(count, 'non lu', 'non lus'); }

  /**
   * Front v2 (Lot 9a, regard neuf v2) : repères des équipements « inactifs » d'une pièce (désactivés dans Jeedom, rien à
   * publier), pour que « 3 / 4 publiés » dise toujours pourquoi il en manque. Lus dans les lignes de `computeOverview`
   * (état unique `resolveEquipmentState`) ; « Exclu » garde son propre repère. Rend [{ key, count, text }].
   */
  function inactiveMarks(room) {
    var rows = room && Array.isArray(room.equipments) ? room.equipments : [];
    var disabled = rows.filter(function (r) { return r.state === 'disabled'; }).length;
    var nothing = rows.filter(function (r) { return r.state === 'nothing_to_publish'; }).length;
    var marks = [];
    if (disabled > 0) marks.push({ key: 'disabled', count: disabled, text: plural(disabled, 'désactivé', 'désactivés') });
    if (nothing > 0) marks.push({ key: 'nothing_to_publish', count: nothing, text: nothing + ' ' + w('rien à publier') });
    return marks;
  }
  function blockedMentionLabel(count) { return plural(count, 'bloquée', 'bloquées'); }

  function houseHeadline(published, total) {
    return { number: String(published), sub: w(published > 1 ? 'publiés' : 'publié') + ' ' + w('sur') + ' ' + total };
  }

  // --- Agrégats (D1) ---
  var GROUP_OF_STATE = {
    published: 'published',
    to_apply: 'to_apply',
    blocked: 'blocked',
    excluded: 'other',
    disabled: 'other',
    nothing_to_publish: 'other',
  };
  var GROUP_KEYS = ['published', 'to_apply', 'blocked', 'other', 'unread'];

  // Filtres de la maison, dans l'ordre de la légende (AC10).
  var FILTERS = [
    { key: 'published', label: function (n) { return plural(n, 'publié', 'publiés'); } },
    { key: 'blocked', label: function (n) { return plural(n, 'bloqué', 'bloqués'); } },
    { key: 'to_apply', label: function (n) { return n + ' ' + w('à appliquer'); } },
    // Front v2 (Lot 7) : « exclus ou inactifs » (amendement du glossaire, spec 3.2) : exclus, désactivés et rien à publier.
    { key: 'other', label: function (n) { return n + ' ' + w('exclus ou inactifs'); } },
    { key: 'unread', label: function (n) { return unreadLabel(n); } },
  ];

  function emptyCounts() { return { published: 0, to_apply: 0, blocked: 0, other: 0, unread: 0 }; }

  // Puces de filtre (Story 25.4) : calculées ICI pour la page principale ET pour la vue de travail, afin qu'aucun second
  // calcul d'effectifs n'existe. Front v2 (Lot 7, E2) : une puce à zéro n'est PAS affichée, SAUF la puce active (`active`) :
  // elle reste visible et cliquable pour pouvoir retirer le filtre (portée « pièce » de 25.6 où la pièce ne compte aucun
  // équipement du filtre hérité de la page B). `disabled` reste dans le contrat (toujours faux).
  function chipsFor(counts, active) {
    var c = counts || emptyCounts();
    var chips = [];
    FILTERS.forEach(function (f) {
      var count = c[f.key] || 0;
      var isActive = active === f.key;
      if (count === 0 && !isActive) return;
      chips.push({ key: f.key, count: count, label: f.label(count), disabled: false });
    });
    return chips;
  }

  // `rooms` : j2haRoomsTree (seule source des pièces, des noms et de `enabled`) ;
  // `equipments` : payload.equipments de la route (clés = String(eq_id)).
  function computeOverview(rooms, equipments) {
    var byId = equipments && typeof equipments === 'object' ? equipments : {};
    var out = { total: 0, rooms_count: 0, rooms: [], counts: emptyCounts(), house: null };
    var summaries = [];
    (Array.isArray(rooms) ? rooms : []).forEach(function (room) {
      var list = Array.isArray(room.equipments) ? room.equipments : [];
      var trees = [];
      var enabledById = {};
      var counts = emptyCounts();
      var rows = [];
      list.forEach(function (eq) {
        enabledById[eq.eq_id] = eq.enabled;
        var entry = Object.prototype.hasOwnProperty.call(byId, String(eq.eq_id)) ? byId[String(eq.eq_id)] : null;
        var row = {
          eq_id: eq.eq_id, eq_name: eq.eq_name, room_id: room.object_id, room_name: room.object_name,
          state: null, blocked_mention: 0, group: 'unread',
          // Story 25.7 : cause d'exclusion (mention à côté du mot « Exclu », jamais un état) et plugin de l'équipement.
          cause: null, homekit_kept: false, eq_type: typeof eq.eq_type === 'string' ? eq.eq_type : '',
          // Front v2 (Lot 7) : conseil (mention dérivée, jamais un état) ; `null` = inconnu sans requête de plus.
          advice: null,
        };
        if (entry && typeof entry === 'object') {
          // `summarizeRoom` lit l'identifiant dans l'entrée : on le garantit sans cloner l'entrée.
          trees.push(entry.jeedom_eq_id === eq.eq_id ? entry : Object.assign({}, entry, { jeedom_eq_id: eq.eq_id }));
          var resolved = M.resolveEquipmentState(entry, eq.enabled);
          row.state = resolved.state;
          row.blocked_mention = resolved.blocked_mention;
          row.group = GROUP_OF_STATE[resolved.state];
          // Story 24.4 (R1) : relevé de sa pièce exclue par HomeKit (champ additif de la route agrégée).
          row.homekit_kept = entry.homekit_kept_in_excluded_room === true;
          if (resolved.state === 'excluded') row.cause = M.exclusionCauseOf(entry, eq.enabled);
          row.advice = adviceOfEntry(entry, resolved.state);
        }
        counts[row.group] += 1;
        rows.push(row);
      });
      var summary = M.summarizeRoom(trees, list.length, enabledById);
      summaries.push(summary);
      var exclusion = M.exclusionBreakdown(rows.filter(function (r) { return r.state === 'excluded'; }));
      out.rooms.push({
        object_id: room.object_id, object_name: room.object_name, summary: summary, counts: counts, exclusion: exclusion, equipments: rows,
        advice: adviceCount(rows),
        // Story 25.8 : la pièce est exclue (clé `excludedObjects`) — jamais pour « Sans pièce ».
        excluded: room.excluded === true && room.object_id > 0,
      });
      out.total += list.length;
      if (room.object_id > 0) out.rooms_count += 1;
      GROUP_KEYS.forEach(function (key) { out.counts[key] += counts[key]; });
    });
    out.house = M.summarizeHouse(summaries);
    var all = [];
    out.rooms.forEach(function (r) { all = all.concat(r.equipments); });
    out.advice = adviceCount(all);
    return out;
  }

  // --- Front v2 (Lot 7) : conseils connus sans requête de plus ---
  // Un conseil (« publié mais améliorable ») se lit dans les `hints` d'un arbre. La route agrégée `/system/equipment_states`
  // ne les porte pas (liste blanche sous garde) et les fiches ne sont jamais lues une à une : le nombre n'est connu que si
  // CHAQUE entrée lue porte `hints` (tableau, même vide). Sinon `null` : aucune puce, aucun bloc, aucune mention.
  function adviceOfEntry(entry, state) {
    if (!entry || !Array.isArray(entry.hints)) return null;
    if (state !== 'published') return false;
    var H = haSide();
    var hints = H && typeof H.computeHints === 'function' ? H.computeHints(entry) : entry.hints;
    return Array.isArray(hints) && hints.length > 0;
  }

  function adviceCount(rows) {
    var read = rows.filter(function (row) { return row.state !== null; });
    if (read.length === 0 || read.some(function (row) { return row.advice === null; })) return null;
    return read.filter(function (row) { return row.advice === true; }).length;
  }

  function adviceLabel(count) { return plural(count, 'conseil', 'conseils'); }

  // --- Front v2 (Lot 7) : bloc « À faire » (E2) ---
  // Une ligne par équipement bloqué (puis par conseil connu), avec la cause en clair et l'action de sa fiche
  // (`Jeedom2haLexique.causeSheet`). La cause est lue dans l'entrée AGRÉGÉE par `groupBlockedCauses` (source unique) : aucun
  // arbre n'est lu. Rend toutes les lignes ; la page n'en affiche que les cinq premières.
  function causeSentence(quoi) {
    var text = String(quoi || '').replace(/^Non publié\s*:\s*/, '');
    return text ? text.charAt(0).toUpperCase() + text.slice(1) : '';
  }

  function todoItems(overview, equipments) {
    var items = [];
    if (!overview) return items;
    var byId = equipments && typeof equipments === 'object' ? equipments : {};
    var L = lexicon();
    var H = haSide();
    var advice = [];
    overview.rooms.forEach(function (room) {
      room.equipments.forEach(function (row) {
        var entry = Object.prototype.hasOwnProperty.call(byId, String(row.eq_id)) ? byId[String(row.eq_id)] : null;
        if (!entry) return;
        var base = { eq_id: row.eq_id, eq_name: row.eq_name, eq_type: row.eq_type, room_id: row.room_id, room_name: row.room_name };
        if (row.state === 'blocked') {
          var groups = M.groupBlockedCauses(entry);
          var first = groups[0] || null;
          var context = H && typeof H.nameTypeWords === 'function' ? H.nameTypeWords(entry, row.eq_name) || {} : {};
          var sheet = first && first.code && L ? L.causeSheet(first.code, context) : null;
          items.push(Object.assign(base, {
            kind: 'blocked',
            // Front v3 (Lot 1) : code de la cause, pour son libellé court (la phrase reste en info-bulle).
            code: first && first.code ? first.code : null,
            text: sheet && sheet.known ? causeSentence(sheet.quoi) : (first ? (L && typeof L.causeLine === 'function' ? L.causeLine(first, null) : M.buildCauseNoticeText(first)) : ''),
            action: sheet && sheet.known && sheet.actions.length ? sheet.actions[0] : null,
          }));
        } else if (row.advice === true) {
          var hints = H && typeof H.computeHints === 'function' ? H.computeHints(entry) : [];
          var hint = hints[0] || null;
          var tip = hint && L ? L.causeSheet(hint.code, { count: hint.count }) : null;
          advice.push(Object.assign(base, { kind: 'advice', code: hint && hint.code ? hint.code : null, text: tip && tip.known ? tip.quoi : '', action: null }));
        }
      });
    });
    return items.concat(advice);
  }

  function filterRows(overview, key) {
    var rows = [];
    overview.rooms.forEach(function (room) {
      room.equipments.forEach(function (row) { if (key === 'advice' ? row.advice === true : row.group === key) rows.push(row); });
    });
    return rows;
  }

  // Segments de la jauge, dans l'ordre publiés / à appliquer / bloqués / exclus ou inactifs / non lus.
  var GAUGE_ORDER = ['published', 'to_apply', 'blocked', 'other', 'unread'];

  function gaugeSegments(counts, total) {
    var segments = [];
    GAUGE_ORDER.forEach(function (key) {
      var count = (counts && counts[key]) || 0;
      if (count > 0 && total > 0) segments.push({ key: key, count: count, pct: (count / total) * 100 });
    });
    return segments;
  }

  function gaugeLabel(counts, total) {
    var parts = [(counts.published || 0) + ' ' + w((counts.published || 0) > 1 ? 'publiés' : 'publié') + ' ' + w('sur') + ' ' + total];
    if (counts.to_apply > 0) parts.push(counts.to_apply + ' ' + w('à appliquer'));
    if (counts.blocked > 0) parts.push(plural(counts.blocked, 'bloqué', 'bloqués'));
    if (counts.other > 0) parts.push(counts.other + ' ' + w('exclus ou inactifs'));
    if (counts.unread > 0) parts.push(unreadLabel(counts.unread));
    return parts.join(', ');
  }

  // --- Front v3 (Lot 1) : page maison sans phrase — figure, puces, marques de tuile, liseré, verdict de la barre d'état ---

  /** « 8 / 22 » + « publiés » (chiffre maison, 26 px). */
  function houseFigure(published, total) {
    var p = published || 0;
    return { number: p + ' / ' + (total || 0), sub: w(p > 1 ? 'publiés' : 'publié') };
  }

  // Une puce = icône + nombre + mot, définition en info-bulle. Ordre du liseré : publiés, à appliquer, bloqués, exclus.
  // `scope` : 'grid' = la puce filtre la grille des pièces ; 'todo' = la puce montre la liste « À faire ».
  var HOUSE_CHIPS = [
    { key: 'published', icon: 'fa-check-circle', scope: 'grid', one: 'publié', many: 'publiés', title: '{{Visible dans Home Assistant}}' },
    { key: 'to_apply', icon: 'fa-clock', scope: 'grid', one: 'à appliquer', many: 'à appliquer', title: '{{Réglage enregistré, à envoyer avec « Appliquer »}}' },
    { key: 'blocked', icon: 'fa-exclamation-triangle', scope: 'todo', one: 'bloqué', many: 'bloqués', title: '{{Le plugin ne peut pas le publier : voir « À faire »}}' },
    { key: 'other', icon: 'fa-eye-slash', scope: 'grid', one: 'exclu ou inactif', many: 'exclus ou inactifs', title: '{{Exclus par vous, désactivés dans Jeedom ou sans rien à publier}}' },
    { key: 'unread', icon: 'fa-question-circle', scope: 'grid', one: 'non lu', many: 'non lus', title: '{{État pas encore lu}}' },
    { key: 'advice', icon: 'fa-lightbulb', scope: 'todo', one: 'conseil', many: 'conseils', title: '{{Publié, mais pourrait faire mieux}}' },
  ];

  function chipDef(key) { return HOUSE_CHIPS.filter(function (c) { return c.key === key; })[0] || null; }

  /** Puces de la maison : seulement les nombres non nuls, sauf la puce active (pour pouvoir la relâcher). */
  function houseChips(counts, advice, active) {
    var c = counts || emptyCounts();
    var out = [];
    HOUSE_CHIPS.forEach(function (def) {
      var count = def.key === 'advice' ? (typeof advice === 'number' ? advice : 0) : (c[def.key] || 0);
      if (count === 0 && active !== def.key) return;
      out.push({ key: def.key, count: count, word: w(count > 1 ? def.many : def.one), icon: def.icon, title: def.title, scope: def.scope });
    });
    return out;
  }

  /** Libellé d'un segment du liseré (info-bulle et nom accessible) : « 6 à appliquer ». */
  function segmentLabel(key, count) {
    if (key === 'published') return plural(count, 'publié', 'publiés');
    if (key === 'to_apply') return count + ' ' + w('à appliquer');
    if (key === 'blocked') return plural(count, 'bloqué', 'bloqués');
    if (key === 'other') return count + ' ' + w('exclus ou inactifs');
    return unreadLabel(count);
  }

  /**
   * Marques d'une tuile de pièce : icône + nombre, seulement les nombres non nuls (dans l'ordre bloqués, à appliquer,
   * désactivés, rien à publier, non lus, exclus). `word` complète le nombre pour l'info-bulle et les lecteurs d'écran.
   * `only` (facultatif) : la clé du filtre actif de la grille (seules ses marques restent ; « other » = exclus, désactivés,
   * rien à publier).
   */
  function tileMarks(room, only) {
    var c = (room && room.counts) || emptyCounts();
    var rows = room && Array.isArray(room.equipments) ? room.equipments : [];
    var n = function (state) { return rows.filter(function (r) { return r.state === state; }).length; };
    var marks = [];
    var push = function (key, group, count, icon, word) {
      if (count > 0) marks.push({ key: key, group: group, count: count, icon: icon, word: word, title: count + ' ' + word });
    };
    push('blocked', 'blocked', c.blocked, 'fa-exclamation-triangle', w(c.blocked > 1 ? 'bloqués' : 'bloqué'));
    push('to_apply', 'to_apply', c.to_apply, 'fa-clock', w('à appliquer'));
    push('disabled', 'other', n('disabled'), 'fa-power-off', w(n('disabled') > 1 ? 'désactivés' : 'désactivé'));
    push('nothing_to_publish', 'other', n('nothing_to_publish'), 'fa-minus-circle', w('rien à publier'));
    push('unread', 'unread', c.unread, 'fa-question-circle', w(c.unread > 1 ? 'non lus' : 'non lu'));
    // Story 25.7 : « N exclus » = la ventilation des exclusions (`exclusionBreakdown`), en dernier.
    var excluded = room && room.exclusion && typeof room.exclusion.excluded === 'number' ? room.exclusion.excluded : n('excluded');
    push('excluded', 'other', excluded, 'fa-eye-slash', w(excluded > 1 ? 'exclus' : 'exclu'));
    return only ? marks.filter(function (m) { return m.group === only; }) : marks;
  }

  /** Une pièce reste-t-elle dans la grille sous le filtre `key` ? (les pièces à 0 sont masquées) */
  function roomMatchesFilter(room, key) {
    if (!key) return true;
    if (!room || !room.counts) return false;
    return (room.counts[key] || 0) > 0;
  }

  /** Équipements « à appliquer » (identifiants numériques), dans l'ordre des pièces : cible du bouton « Appliquer (n) ». */
  function toApplyIds(overview) {
    if (!overview) return [];
    return filterRows(overview, 'to_apply').map(function (row) { return row.eq_id; });
  }

  /**
   * Confirmation de « Appliquer (n) » : { title, lines[], confirmLabel }. Le démon reprend la décision au clic (réglages relus) :
   * selon les réglages en attente, l'équipement est publié, mis à jour ou retiré — la ligne le dit.
   */
  function applyDialog(count) {
    var n = typeof count === 'number' && count > 0 ? Math.floor(count) : 0;
    var lines = [n + ' ' + w(n > 1 ? 'équipements publiés, mis à jour ou retirés de Home Assistant selon vos réglages' : 'équipement publié, mis à jour ou retiré de Home Assistant selon vos réglages')];
    return { title: w('Appliquer') + ' ' + n + ' ' + w(n > 1 ? 'réglages en attente ?' : 'réglage en attente ?'), lines: lines, confirmLabel: w('Appliquer') + ' (' + n + ')' };
  }

  var VERDICT_MAX_AGE_MS = 24 * 3600 * 1000;

  /**
   * Mémoire de la dernière relecture OBSERVÉE par la page : quand la dernière opération du démon est une relecture, son
   * résultat est retenu avec sa date de fin (`derniere_synchro_terminee`). Elle survit à une opération suivante (« Appliquer »,
   * « Republier ») tant que la date de fin de relecture ne change pas. Pure : rend la mémoire à jour.
   */
  function rememberSync(memory, status) {
    var op = status && typeof status === 'object' ? status.derniere_operation_resultat : null;
    var at = status && typeof status.derniere_synchro_terminee === 'string' ? status.derniere_synchro_terminee : null;
    if (op && typeof op === 'object' && op.intention === 'sync' && at) return { at: at, ok: op.resultat === 'succes' };
    return memory && memory.at === at ? memory : null;
  }

  /**
   * Verdict de la barre d'état, FAIL-CLOSED. `ok` (« ✓ Rien à faire ») seulement si TOUT est prouvé :
   *   - démon et broker en marche ;
   *   - états lus, rien à appliquer, rien de bloqué, rien de non lu ;
   *   - la dernière opération, quelle qu'elle soit (relecture, « Appliquer », « Republier »…), a RÉUSSI (aucune en échec) ;
   *   - une relecture RÉUSSIE terminée il y a moins de 24 h : la dernière opération elle-même, ou la relecture retenue par
   *     `rememberSync` (même date de fin) quand une opération réussie l'a suivie.
   * Quelque chose à faire : `null` (« Appliquer (n) » et « À faire » le disent). Sinon `unverified` (« ? Non vérifié »
   * + [Relire]). `memory` : rendu de `rememberSync` ; `now` (ms) : facultatif, pour les tests.
   */
  function statusVerdict(status, overview, now, memory) {
    if (!status || typeof status !== 'object' || !status.daemon) return null;
    var broker = status.broker || status.mqtt || {};
    if (broker.state !== 'connected') return null;
    var c = overview && overview.counts ? overview.counts : null;
    if (c && ((c.to_apply || 0) > 0 || (c.blocked || 0) > 0)) return null;
    var unverified = { kind: 'unverified', text: w('Non vérifié'), title: w('Dernière relecture réussie inconnue ou de plus de 24 h') };
    if (!c || (c.unread || 0) > 0) return unverified;
    var op = status.derniere_operation_resultat;
    if (!op || typeof op !== 'object' || op.resultat !== 'succes') return unverified;
    var at = typeof status.derniere_synchro_terminee === 'string' ? status.derniere_synchro_terminee : null;
    var syncOk = op.intention === 'sync' || (!!memory && memory.ok === true && memory.at === at);
    if (!syncOk || !at) return unverified;
    var atMs = new Date(at).getTime();
    var t = typeof now === 'number' ? now : Date.now();
    if (!isFinite(atMs) || t - atMs > VERDICT_MAX_AGE_MS || atMs - t > 5 * 60 * 1000) return unverified;
    var d = new Date(atMs);
    return { kind: 'ok', text: w('Rien à faire'), title: w('Relu à') + ' ' + pad2(d.getHours()) + ':' + pad2(d.getMinutes()) };
  }

  /** Nombre de scénarios publiés (champ additif `status.publication.scenarios_published`) ; `null` si inconnu. */
  function scenarioCount(status) {
    var publication = status && typeof status === 'object' ? status.publication : null;
    var n = publication && typeof publication === 'object' ? publication.scenarios_published : null;
    return typeof n === 'number' && isFinite(n) && n >= 0 ? Math.floor(n) : null;
  }

  /**
   * Front v3 (Lot 4b) : texte du compte de l'onglet « Scénarios ». Avec la liste du démon (`status.scenarios`, Lot 4a) :
   * « publiés/total », suivi de ✱ s'il y a des nouveaux. Sans elle (démon ancien) : le nombre publié d'avant, ou rien.
   */
  function scenarioTabText(status) {
    var list = status && typeof status === 'object' && Array.isArray(status.scenarios) ? status.scenarios.filter(function (s) { return s && typeof s === 'object'; }) : null;
    if (list) {
      var published = list.filter(function (s) { return s.published === true; }).length;
      return published + '/' + list.length + (list.some(function (s) { return s.is_new === true; }) ? ' ✱' : '');
    }
    var n = scenarioCount(status);
    return n === null ? '' : String(n);
  }

  // Cause d'une ligne « À faire » en quatre mots au plus ; la phrase complète de la fiche reste en info-bulle.
  var TODO_SHORT_CAUSES = {
    no_generic_type_configured: '{{Sans type générique}}',
    ambiguous_skipped: '{{Type ambigu}}',
    name_heuristic_rejection: '{{Nom contraire au type}}',
    duplicate_generic_types: '{{Types génériques en double}}',
    conflicting_generic_types: '{{Types génériques en conflit}}',
    switch_state_orphan: '{{Aucun ordre On / Off}}',
    probable_skipped: '{{Type pas assez sûr}}',
    low_confidence: '{{Type pas assez sûr}}',
    no_supported_generic_type: '{{Type non pris en charge}}',
    no_mapping: '{{Aucun type correspondant}}',
    skipped_no_mapping_candidate: '{{Aucun type correspondant}}',
    no_projection_possible: '{{Aucune commande utilisable}}',
    ha_missing_command_topic: '{{Rien à piloter}}',
    ha_missing_state_topic: '{{Pas de retour d’état}}',
    discovery_publish_failed: '{{Envoi MQTT échoué}}',
  };

  function shortCause(code) {
    return typeof code === 'string' && Object.prototype.hasOwnProperty.call(TODO_SHORT_CAUSES, code) ? TODO_SHORT_CAUSES[code] : '';
  }

  function pad2(n) { return ('0' + n).slice(-2); }

  // --- Story 25.8 : exclusion d'une pièce — nombre d'entités annoncé (Q1 B) et texte de la confirmation (D4) ---
  // Fonctions PURES : le nombre est calculé depuis la copie des états déjà en mémoire (aucune requête avant le clic de confirmation).

  /**
   * @param {object} snap `page.snapshot()` : { kind, view: { stale, equipments, overview } }
   * @param {Array} rooms `j2haRoomsTree`
   * @returns {{known: boolean, entities: number, unknown: number, unread: number, pending: number}} `entities` : entités PRÉSENTES dans
   *   Home Assistant (`present_in_ha`) des équipements lus de la pièce ; `unknown` : entités à présence inconnue (non comptées) ;
   *   `unread` : équipements de la pièce absents de la copie ; `pending` : effectif maison « à appliquer » (la relecture les applique aussi).
   */
  function roomExclusionImpact(snap, rooms, roomId) {
    // `atLeast` (relecture ClaudeBox #309, P2-1) : un réglage en attente peut remplacer une entité (domaine changé) dont
    // l'ancienne version reste dans Home Assistant jusqu'à la relecture ; le nombre est alors un minimum, annoncé comme tel.
    var out = { known: false, entities: 0, unknown: 0, unread: 0, pending: 0, atLeast: false };
    var view = snap && snap.view;
    if (!snap || snap.kind !== 'ok' || !view || view.stale === true || !view.equipments || !view.overview) return out;
    out.known = true;
    out.pending = (view.overview.counts && view.overview.counts.to_apply) || 0;
    var room = (Array.isArray(rooms) ? rooms : []).filter(function (r) { return r && r.object_id === roomId; })[0];
    if (!room) return out;
    (Array.isArray(room.equipments) ? room.equipments : []).forEach(function (eq) {
      var key = String(eq.eq_id);
      if (!Object.prototype.hasOwnProperty.call(view.equipments, key)) { out.unread += 1; return; }
      // Story 24.4 (R1) : un équipement actif, exposé à HomeKit et d'état d'équipement `inherit` sera relevé de la pièce
      // exclue (même règle que le démon) : ses entités ne seront pas retirées.
      var entry = view.equipments[key];
      if (eq.enabled !== false && entry && entry.homekit_exposed_effective === true && entry.scope_inherit === true) return;
      var entities = view.equipments[key] && Array.isArray(view.equipments[key].entities) ? view.equipments[key].entities : [];
      entities.forEach(function (entity) {
        if (entity && entity.present_in_ha === true) out.entities += 1;
        else if (!entity || typeof entity.present_in_ha !== 'boolean') out.unknown += 1;
        if (entity && entity.override_pending === true) out.atLeast = true;
      });
    });
    return out;
  }

  /** Texte de la confirmation (D4) : { title, lines[], confirmLabel, danger }. Le nom est du texte brut (échappé au rendu). */
  function roomExclusionDialog(input) {
    var rawName = input && input.name;
    var name = rawName === undefined || rawName === null ? '' : String(rawName);
    var impact = (input && input.impact) || { known: false, entities: 0, unknown: 0, unread: 0, pending: 0 };
    var lines = [];
    var out;
    if (input && input.excluded) {
      if (!impact.known) {
        lines.push("{{Nombre d'entités inconnu : la lecture des états n'est pas disponible.}}");
      } else if (impact.entities === 0 && impact.atLeast) {
        lines.push("{{Des entités encore présentes dans Home Assistant (réglage en attente) seront retirées ; leur nombre exact n'est pas connu.}}");
      } else if (impact.entities === 0) {
        lines.push("{{Aucune entité n'est publiée dans cette pièce.}}");
      } else {
        lines.push((impact.atLeast ? w('Au moins') + ' ' : '') + impact.entities + ' ' + w(impact.entities > 1 ? 'entités seront retirées' : 'entité sera retirée') + ' ' + w('de Home Assistant.'));
      }
      if (impact.known && impact.unknown > 0) {
        lines.push(impact.unknown + ' ' + w(impact.unknown > 1 ? 'entités dont la présence est inconnue ne sont pas comptées.' : 'entité dont la présence est inconnue n\'est pas comptée.'));
      }
      if (impact.known && impact.unread > 0) {
        lines.push(impact.unread + ' ' + w(impact.unread > 1 ? 'équipements non lus ne sont pas comptés.' : 'équipement non lu n\'est pas compté.'));
      }
      out = { title: w('Exclure la pièce') + ' « ' + name + ' » ' + w('de Home Assistant ?'), lines: lines, confirmLabel: '{{Exclure la pièce}}', danger: true };
    } else {
      lines.push("{{Ses équipements seront relus et publiés s'ils sont publiables.}}");
      out = { title: w('Ne plus exclure la pièce') + ' « ' + name + ' » ?', lines: lines, confirmLabel: '{{Ne plus exclure}}', danger: false };
    }
    if (impact.pending > 0) {
      lines.push(w('La relecture appliquera aussi') + ' ' + (impact.pending > 1 ? w('les') + ' ' + impact.pending + ' ' + w('réglages en attente') : w('le réglage en attente')) + ' ' + w('de la maison.'));
    }
    return out;
  }

  // --- États de rendu de la lecture (D2) ---
  function classifyResponse(data) {
    var result = data && data.state === 'ok' ? data.result : null;
    var payload = result && typeof result === 'object' && result.status === 'ok' ? result.payload : null;
    if (!payload || typeof payload !== 'object') {
      return { kind: 'unavailable', payload: null, message: MSG_UNAVAILABLE, retry: false };
    }
    if (payload.available === true) {
      var busy = !!(payload.meta && payload.meta.action_in_progress === true);
      return {
        kind: 'ok', payload: payload, action_in_progress: busy,
        notice: busy ? MSG_ACTION_NOTICE : '', retry: busy,
      };
    }
    if (payload.reason === 'action_in_progress') {
      return { kind: 'in_progress', payload: null, message: MSG_IN_PROGRESS, notice: MSG_ACTION_NOTICE, retry: true };
    }
    return { kind: 'never_synced', payload: null, message: MSG_NEVER_SYNCED, retry: false };
  }

  // Modèle de rendu : jamais « NaN », jamais une jauge de « non lus » quand la lecture n'a pas eu lieu.
  function buildViewModel(response, rooms, valid) {
    var res = response || {};
    var vm = { kind: res.kind, overview: null, equipments: null, stale: false, message: '', notice: '', gauge: 'neutral' };
    var source = null;
    if (res.kind === 'ok' && res.payload) {
      source = res.payload;
      vm.notice = res.notice || '';
    } else if (res.kind === 'in_progress') {
      vm.message = res.message || MSG_IN_PROGRESS;
      if (valid) { source = valid; vm.stale = true; vm.notice = MSG_ACTION_NOTICE; }
    } else if (res.kind === 'unavailable') {
      vm.message = res.message || MSG_UNAVAILABLE;
      if (valid) { source = valid; vm.stale = true; }
    } else if (res.kind === 'never_synced') {
      vm.message = res.message || MSG_NEVER_SYNCED;
    }
    if (source) {
      vm.overview = computeOverview(rooms, source.equipments);
      // Même copie que celle des agrégats (jamais une seconde lecture) : la vue de travail y lit les causes (Story 25.4).
      vm.equipments = source.equipments && typeof source.equipments === 'object' ? source.equipments : {};
      vm.gauge = 'normal';
    }
    return vm;
  }

  // --- Lecture : un appel, coalescence, relectures bornées, retour d'onglet ---
  function createReader(env) {
    var st = { kind: null, response: null, valid: null, readAt: null, lastOkAt: null, refreshing: false, loading: false };
    var inflight = false;
    var dirty = false;
    var queuedRefresh = false;
    var coalesceTimer = null;
    var retryTimer = null;
    var retryIndex = 0;

    function snapshot() {
      return { kind: st.kind, response: st.response, valid: st.valid, readAt: st.readAt, refreshing: st.refreshing, loading: st.loading };
    }
    function emit() { if (typeof env.onUpdate === 'function') env.onUpdate(snapshot()); }
    function clearTimer(id) { if (id !== null) env.clearTimeout(id); }
    function cancelRetry() { clearTimer(retryTimer); retryTimer = null; }

    function run(refresh, fromRetry) {
      clearTimer(coalesceTimer); coalesceTimer = null;
      cancelRetry();
      if (!fromRetry) retryIndex = 0;
      if (inflight) {
        if (refresh) queuedRefresh = true; else dirty = true;
        return;
      }
      inflight = true;
      st.loading = true;
      if (refresh) st.refreshing = true;
      emit();
      env.readStates(refresh, function (data) {
        inflight = false;
        st.loading = false;
        var res = classifyResponse(data);
        st.kind = res.kind;
        st.response = res;
        if (res.kind === 'ok') {
          st.valid = res.payload;
          st.readAt = new Date(env.now());
          st.lastOkAt = env.now();
        } else if (res.kind === 'never_synced') {
          st.valid = null;
        }
        if (!queuedRefresh) st.refreshing = false;
        if (res.retry && retryIndex < RETRY_DELAYS_MS.length) {
          retryTimer = env.setTimeout(function () { retryTimer = null; run(false, true); }, RETRY_DELAYS_MS[retryIndex]);
          retryIndex += 1;
        }
        emit();
        if (queuedRefresh) {
          queuedRefresh = false;
          run(true);
        } else if (dirty) {
          dirty = false;
          trigger();
        }
      });
    }

    function trigger() {
      if (coalesceTimer !== null) return;
      coalesceTimer = env.setTimeout(function () { coalesceTimer = null; run(false); }, COALESCE_MS);
    }

    return {
      load: function () { run(false); },
      trigger: trigger,
      // « Actualiser » : seul appelant de refresh=1 ; désactivé tant que sa réponse est attendue.
      refresh: function () {
        if (st.refreshing) return;
        st.refreshing = true;
        run(true);
      },
      onVisible: function () {
        if (st.lastOkAt === null || env.now() - st.lastOkAt > VISIBLE_MIN_AGE_MS) trigger();
      },
      state: snapshot,
    };
  }

  // Unique site d'appel de la route agrégée (25.2). Aucune boucle : un appel par lecture.
  function ajaxFetch($) {
    return function (refresh, done) {
      var data = { action: 'getEquipmentStates' };
      if (refresh) data.refresh = '1';
      $.ajax({
        type: 'POST', url: AJAX_URL, data: data, dataType: 'json', timeout: AJAX_TIMEOUT_MS,
        success: function (body) { done(body); },
        error: function () { done(null); },
      });
    };
  }

  // --- Navigateur : rendu de la barre, du bloc maison, de la liste filtrée et des cartes ---
  var STATE_ICONS = {
    published: 'fa-check-circle',
    to_apply: 'fa-clock',
    blocked: 'fa-exclamation-triangle',
    excluded: 'fa-eye-slash',
    disabled: 'fa-pause-circle',
    nothing_to_publish: 'fa-minus-circle',
  };

  function createPage(env) {
    var $ = env.$;
    var rooms = env.rooms || [];
    var pluginNames = env.pluginNames || {}; // Story 25.7 : { identifiant: nom affiché } lu par la page (j2haPluginNames)
    var filter = null;
    var lastView = null;
    var lastState = null;
    var openMenuWrap = null;
    var subscribers = [];

    var reader = createReader({
      readStates: env.readStates,
      now: env.now,
      setTimeout: env.setTimeout,
      clearTimeout: env.clearTimeout,
      onUpdate: function (state) { lastState = state; render(); },
    });

    function chipId(key) { return '.j2ha-chip-filter[data-filter="' + key + '"]'; }

    // Story 25.8 : l'état « pièce exclue » vit dans `rooms` (j2haRoomsTree, champ `excluded`) ; une écriture réussie le
    // remplace pour TOUTES les pièces depuis `excluded_objects` (une écriture d'un autre onglet est ainsi reflétée).
    function roomOf(id) { return rooms.filter(function (r) { return r.object_id === id; })[0] || null; }
    function isRoomExcluded(id) { var r = roomOf(id); return !!r && r.object_id > 0 && r.excluded === true; }
    function roomName(id) { var r = roomOf(id); return r ? String(r.object_name) : ''; }
    function setExcludedObjects(ids) {
      var list = Array.isArray(ids) ? ids : [];
      rooms.forEach(function (room) { room.excluded = room.object_id > 0 && list.indexOf(room.object_id) !== -1; });
      render();
    }

    function stateWord(state) {
      return $('<span class="j2ha-state-word"></span>').addClass('j2ha-state-' + state)
        .append($('<i class="fas"></i>').addClass(STATE_ICONS[state]))
        .append($('<span class="j2ha-state-text"></span>').text(' ' + M.EQUIPMENT_STATE_LABELS[state]));
    }

    // Liseré segmenté (maison : 6 px ; tuile : 4 px). Chaque segment porte un `title` et un `aria-label` avec son compte.
    function buildGauge(counts, total, extraClass) {
      var $gauge = $('<div class="j2ha-gauge j2ha-v3-stripe" role="group"></div>').addClass(extraClass || '');
      $gauge.attr('aria-label', gaugeLabel(counts, total));
      gaugeSegments(counts, total).forEach(function (seg) {
        var label = segmentLabel(seg.key, seg.count);
        var $seg = $('<span class="j2ha-seg" role="img"></span>').addClass('j2ha-seg-' + seg.key)
          .attr('data-filter', seg.key).attr('title', label).attr('aria-label', label).attr('style', 'flex-grow:' + seg.count);
        if (extraClass !== 'j2ha-gauge-card') {
          $seg.on('click', function () { activateFilter(seg.key); });
        }
        $gauge.append($seg);
      });
      return $gauge;
    }

    function setText(selector, text) { $(selector).text(text); }

    function renderHouse(vm) {
      var $block = $('#j2ha_houseBlock');
      $block.toggleClass('j2ha-stale', vm.stale === true);
      var status = vm.notice || vm.message || '';
      setText('#j2ha_readStatus', status);
      var $gaugeHost = $('#j2ha_houseGauge').empty();
      // Les puces sont reconstruites à chaque rendu : le focus clavier est rendu à la puce qui l'avait.
      var active = env.document && env.document.activeElement;
      var focusKey = active && active.classList && active.classList.contains('j2ha-chip-filter') ? active.getAttribute('data-filter') : null;
      var $chips = $('#j2ha_houseChips').empty();
      if (!vm.overview) {
        setText('#j2ha_houseNumber', '');
        setText('#j2ha_houseSub', '');
        $gaugeHost.append($('<div class="j2ha-gauge j2ha-gauge-neutral j2ha-v3-stripe" role="img"></div>').attr('aria-label', vm.message || w('Chargement...')));
        return;
      }
      var o = vm.overview;
      var head = houseFigure(o.counts.published, o.total);
      setText('#j2ha_houseNumber', head.number);
      setText('#j2ha_houseSub', head.sub);
      $gaugeHost.append(buildGauge(o.counts, o.total));
      houseChips(o.counts, o.advice, filter).forEach(function (chip) {
        var $chip = $('<button type="button" class="j2ha-chip-filter j2ha-v3-chip"></button>')
          .addClass('j2ha-chip-filter-' + chip.key).attr('data-filter', chip.key)
          .attr('aria-pressed', filter === chip.key ? 'true' : 'false')
          .attr('aria-controls', chip.scope === 'todo' ? 'j2ha_v2_todo' : 'j2ha_roomCards')
          .attr('title', chip.title)
          .attr('aria-label', chip.count + ' ' + chip.word + ' : ' + chip.title)
          .append($('<i class="fas" aria-hidden="true"></i>').addClass(chip.icon))
          .append($('<b class="j2ha-v3-chip-n"></b>').text(String(chip.count)))
          .append(document_text(' '))
          .append($('<span class="j2ha-v3-chip-word"></span>').text(chip.word));
        $chip.on('click', function () { activateFilter(chip.key); });
        $chip.on('keydown', onFilterKey);
        $chips.append($chip);
      });
      if (focusKey) $chips.find(chipId(focusKey)).focus();
    }

    function document_text(text) { return env.document.createTextNode(text); }

    function currentStatus() { return typeof env.bridgeStatus === 'function' ? env.bridgeStatus() : null; }

    // Onglets (« Équipements n » / « Scénarios n ») : le nombre de scénarios vient du démon (`status.publication`).
    function renderTabs() {
      var total = rooms.reduce(function (n, room) { return n + (Array.isArray(room.equipments) ? room.equipments.length : 0); }, 0);
      setText('#j2ha_tabEquipmentsCount', String(total));
      setText('#j2ha_tabScenariosCount', scenarioTabText(currentStatus()));
    }

    var activeTab = 'equipments';
    function selectTab(key) {
      activeTab = key === 'scenarios' ? 'scenarios' : 'equipments';
      $('.j2ha-v3-tab').each(function (_i, el) {
        var on = $(el).attr('data-tab') === activeTab;
        $(el).attr('aria-selected', on ? 'true' : 'false').attr('tabindex', on ? '0' : '-1');
        $(el).closest('li').toggleClass('active', on);
      });
      $('#j2ha_tab_equipments').prop('hidden', activeTab !== 'equipments');
      $('#j2ha_tab_scenarios').prop('hidden', activeTab !== 'scenarios');
    }

    var syncMemory = null;
    // Barre d'état, partie « page » : bouton « Appliquer (n) » (visible si n > 0) et verdict « Rien à faire » fail-closed.
    function renderStatus() {
      var o = lastView && lastView.overview;
      var n = o && !lastView.stale ? (o.counts.to_apply || 0) : 0;
      var $apply = $('#bt_j2haApply');
      if ($apply.attr('data-ha-pending') !== '1') {
        $apply.find('.j2ha-v3-apply-count').text(n > 0 ? '(' + n + ')' : '');
        $apply.prop('hidden', n === 0);
        $apply.attr('title', n + ' ' + w(n > 1 ? 'réglages à envoyer à Home Assistant' : 'réglage à envoyer à Home Assistant'));
      }
      var $verdict = $('#j2ha_v3_verdict').empty().removeAttr('data-kind').removeAttr('title');
      syncMemory = rememberSync(syncMemory, currentStatus());
      var verdict = statusVerdict(currentStatus(), o && !lastView.stale ? o : null, env.now(), syncMemory);
      if (!verdict) return;
      $verdict.attr('data-kind', verdict.kind).attr('title', verdict.title);
      if (verdict.kind === 'ok') {
        $verdict.append($('<i class="fas fa-check-circle" aria-hidden="true"></i>')).append(document_text(' ' + verdict.text));
        return;
      }
      $verdict.append($('<span class="j2ha-v3-verdict-q" aria-hidden="true">?</span>')).append(document_text(' ' + verdict.text + ' '));
      var $reread = $('<button type="button" class="btn btn-default btn-xs j2ha-v3-reread"></button>').text(w('Relire'))
        .attr('title', w('Relire Jeedom'));
      $reread.on('click', function () { $('#bt_rescanTopology').trigger('click'); });
      $verdict.append($reread);
    }

    // ↻ (« Actualiser les chiffres ») : heure de la dernière lecture des états en info-bulle, rotation pendant la lecture.
    function renderFreshness(state) {
      var at = state && state.readAt;
      var $button = $('#bt_refreshStates');
      var busy = !!(state && state.refreshing);
      var label = busy ? w('Actualisation…') : w('Actualiser les chiffres') + (at ? ' (' + w('relus à') + ' ' + pad2(at.getHours()) + ':' + pad2(at.getMinutes()) + ')' : '');
      $button.prop('disabled', busy);
      $button.attr('aria-busy', busy ? 'true' : 'false').attr('title', label).attr('aria-label', label);
      $button.empty().append($('<i class="fas fa-sync-alt" aria-hidden="true"></i>').toggleClass('fa-spin', busy));
    }

    // Story 25.8 : libellé du menu « ⋯ » de la carte selon l'état d'exclusion de la pièce (« Exclure… » / « Ne plus exclure… »).
    function syncRoomMenu($card, excluded) {
      var $item = $card.find('.j2ha-room-exclude');
      if ($item.length === 0) return;
      $item.attr('data-excluded', excluded ? '1' : '0');
      $item.find('.j2ha-room-exclude-label').text(excluded ? w('Ne plus exclure la pièce…') : w('Exclure la pièce…'));
    }

    // Équipements de la pièce pas encore exclus dans la copie des états (relecture à faire ou échouée) : ni « Exclu », ni
    // « Désactivé » (qui prime et le reste), ni non lu.
    function notYetRemovedCount(room) {
      return room.equipments.filter(function (row) { return row.state !== null && row.state !== 'excluded' && row.state !== 'disabled' && row.homekit_kept !== true; }).length;
    }

    // Story 24.4 (R1) : équipements gardés dans la pièce exclue par l'exposition HomeKit (jamais « pas encore retirés »).
    function keptHomekitCount(room) {
      return room.equipments.filter(function (row) { return row.homekit_kept === true; }).length;
    }

    // Marque : icône + nombre visibles ; le mot (« 2 bloqués ») est lu par les lecteurs d'écran et repris en info-bulle.
    function markNode(cls, icon, count, word, title) {
      return $('<span class="j2ha-mark j2ha-v3-mark"></span>').addClass(cls).attr('title', title || (count + ' ' + word))
        .append($('<i class="fas" aria-hidden="true"></i>').addClass(icon))
        .append($('<span class="j2ha-v3-mark-n"></span>').text(String(count)))
        .append($('<span class="j2ha-v3-sr"></span>').text(' ' + word));
    }

    // Pièce exclue : ⊘ à la place du ratio ; « pas encore retirés » et « gardés (HomeKit) » en marques chiffrées.
    function excludedMarks(notYet, kept) {
      var out = [];
      if (notYet > 0) out.push(markNode('j2ha-room-notyet', 'fa-clock', notYet, w(notYet > 1 ? 'pas encore retirés' : 'pas encore retiré')));
      if (kept > 0) out.push(markNode('j2ha-room-homekit-kept', 'fa-home', kept, w(kept > 1 ? 'gardés (HomeKit)' : 'gardé (HomeKit)')));
      return out;
    }

    // Ratio « n/m » de la tuile, en tête de `.j2ha-room-state` (placé dans la grille de la tuile par le CSS). Le compteur affiché
    // (publiés, ou l'état filtré) est aussi exposé en `data-count` sur la tuile : une pièce exclue n'affiche que ⊘, son
    // compteur reste lisible par les parcours.
    function setRatio($slot, text, title, excluded) {
      var $ratio = $('<span class="j2ha-v3-tile-ratio"></span>');
      $slot.append($ratio);
      if (excluded) {
        $ratio.addClass('j2ha-room-excluded-line').attr('title', w('Pièce exclue'))
          .append($('<i class="fas fa-eye-slash" aria-hidden="true"></i>'))
          .append($('<span class="j2ha-room-ratio j2ha-v3-sr"></span>').text(w('Pièce exclue')));
        return;
      }
      $ratio.removeClass('j2ha-room-excluded-line');
      if (title) $ratio.attr('title', title);
      $ratio.append($('<span class="j2ha-room-ratio"></span>').text(text));
    }

    // Filtre de grille actif (puces Publiés, À appliquer, Exclus, Non lus) ; Bloqués et Conseils montrent la liste « À faire ».
    function gridFilter() { var def = chipDef(filter); return def && def.scope === 'grid' ? filter : null; }
    function todoFilter() { var def = chipDef(filter); return def && def.scope === 'todo' ? filter : null; }

    function renderCards(vm) {
      var o = vm.overview;
      var gf = o ? gridFilter() : null;
      // Bloqués / Conseils : la vue filtrée EST la liste « À faire » (une seule représentation à la fois).
      $('#j2ha_roomCards').prop('hidden', !!(o && todoFilter()));
      $('#j2ha_roomCards .j2ha-room-card').each(function (_i, el) {
        var $card = $(el);
        var id = parseInt($card.attr('data-object_id'), 10);
        var $slot = $card.find('.j2ha-room-state').empty();
        var room = o ? o.rooms.filter(function (r) { return r.object_id === id; })[0] : null;
        var excluded = isRoomExcluded(id);
        syncRoomMenu($card, excluded);
        $card.removeClass('j2ha-room-blocked j2ha-room-dim j2ha-room-excluded').prop('hidden', false).removeAttr('data-count');
        if (!room) {
          $card.removeAttr('aria-label').removeAttr('title');
          if (excluded) setRatio($slot, '', '', true);
          if (excluded) {
            // Les états ne sont pas lus : la tuile dit quand même que la pièce est exclue (écriture déjà enregistrée).
            $card.addClass('j2ha-room-excluded');
            $card.attr('aria-label', roomName(id) + ', ' + w('pièce exclue'));
          }
          return;
        }
        var c = room.counts;
        var total = room.summary.equipments_total;
        // Filtre de grille : les pièces à 0 sont masquées ; les compteurs de la tuile suivent le filtre.
        if (gf && !roomMatchesFilter(room, gf)) $card.prop('hidden', true);
        var shown = gf ? (c[gf] || 0) : c.published;
        var ratioTitle = gf ? segmentLabel(gf, shown) + ' ' + w('sur') + ' ' + total : room.object_name + ' : ' + c.published + ' ' + w(c.published > 1 ? 'publiés' : 'publié') + ' ' + w('sur') + ' ' + total;
        if (excluded) $card.addClass('j2ha-room-excluded');
        setRatio($slot, shown + '/' + total, ratioTitle, excluded);
        $card.attr('data-count', String(shown));
        var $marks = $('<div class="j2ha-room-marks j2ha-v3-marks"></div>');
        tileMarks(room, gf).forEach(function (mark) {
          $marks.append(markNode('j2ha-mark-' + mark.key, mark.icon, mark.count, mark.word));
        });
        if (excluded) excludedMarks(notYetRemovedCount(room), keptHomekitCount(room)).forEach(function ($m) { $marks.append($m); });
        // Story 25.7 (Q5) : ventilation des exclusions (plugin, pièce, individuelle) dans le nom accessible et l'info-bulle.
        var excludedText = '';
        if (room.exclusion && room.exclusion.excluded > 0) {
          excludedText = w('Exclus') + ' : ' + M.exclusionBreakdownText(room.exclusion, pluginNames);
          $marks.find('.j2ha-mark-excluded').attr('title', excludedText).attr('aria-label', excludedText);
        }
        $slot.append($marks);
        $slot.append(buildGauge(c, total, 'j2ha-gauge-card'));
        if (c.blocked > 0) $card.addClass('j2ha-room-blocked');
        var inactiveText = inactiveMarks(room).map(function (m) { return m.text; }).join(', ');
        $card.attr('aria-label', room.object_name + (excluded ? ', ' + w('pièce exclue') : '') + ', ' + gaugeLabel(c, total) + (inactiveText ? ', ' + inactiveText : '') + (excludedText ? ', ' + excludedText : ''));
      });
      // Un titre de groupe dont toutes les tuiles sont masquées disparaît avec elles.
      $('#j2ha_roomCards .j2ha-room-group').each(function (_i, el) {
        var $g = $(el);
        var visible = 0;
        $g.find('.j2ha-room-card').each(function (_j, card) { if (!$(card).prop('hidden')) visible += 1; });
        $g.prop('hidden', visible === 0);
      });
    }

    // L'ordre de la liste est celui de la grille (pièces regroupées par parent), puis l'ordre natif des équipements.
    function orderLikeGrid(rows) {
      var position = {};
      $('#j2ha_roomCards .j2ha-room-card').each(function (index, el) {
        position[$(el).attr('data-object_id')] = index;
      });
      var rank = function (row) { return Object.prototype.hasOwnProperty.call(position, String(row.room_id)) ? position[String(row.room_id)] : Number.MAX_SAFE_INTEGER; };
      return rows.map(function (row, index) { return { row: row, index: index }; })
        .sort(function (a, b) { return (rank(a.row) - rank(b.row)) || (a.index - b.index); })
        .map(function (entry) { return entry.row; });
    }

    function onFilterKey(event) {
      if (event && event.key === 'Escape' && filter) {
        setFilter(null);
      }
    }

    // --- Liste « À faire » (#j2ha_v2_todo) : une ligne par équipement bloqué, puis par conseil ; masquée si vide ---
    var TODO_LIMIT = 5;
    var todoExpanded = false;

    function equipmentUrl(item) {
      var type = typeof item.eq_type === 'string' && /^[A-Za-z0-9_-]{1,64}$/.test(item.eq_type) ? item.eq_type : '';
      return type ? 'index.php?v=d&m=' + type + '&p=' + type + '&id=' + encodeURIComponent(String(item.eq_id)) : '';
    }

    // L'action de la fiche de cause (Jeedom2haLexique) : « Corriger le type… » et « Voir » ouvrent la fiche de l'équipement
    // dans la page ; les types génériques et l'équipement s'ouvrent dans Jeedom (nouvel onglet).
    function todoAction(item) {
      var key = item.action && item.action.key;
      var href = key === 'generic_types' ? 'index.php?v=d&p=types' : (key === 'equipment' || key === 'rename' ? equipmentUrl(item) : '');
      if (href) {
        var $link = $('<a class="btn btn-default btn-xs j2ha-v2-todo-action" target="_blank" rel="noopener"></a>')
          .attr('href', href).attr('data-action', key).attr('title', item.action.label);
        if (key === 'generic_types') $link.append($('<i class="fas fa-tags" aria-hidden="true"></i>')).append(document_text(' ' + w('Types génériques')));
        else $link.text(item.action.label);
        return $link;
      }
      // Front v2 (Lot 9a, point 9) : « Publier quand même » ouvre la fiche, où le bouton du même nom règle l'équipement sur
      // « Toujours » (aperçu et confirmation habituels, puis « Appliquer »).
      var inPage = key === 'correct_type' || key === 'publish_anyway';
      var label = inPage ? item.action.label : w('Voir');
      var $btn = $('<button type="button" class="btn btn-default btn-xs j2ha-v2-todo-action"></button>')
        .attr('data-action', key || 'open').text(label);
      $btn.attr('aria-label', label + ' : ' + item.eq_name);
      $btn.on('click', function () { openEquipmentView(item.room_id, item.eq_id); });
      return $btn;
    }

    function todoRow(item) {
      var blocked = item.kind === 'blocked';
      var $row = $('<div class="j2ha-v2-row j2ha-v2-todo-row j2ha-v3-todo-row"></div>').attr('data-eq-id', item.eq_id).attr('data-kind', item.kind)
        .addClass(blocked ? 'is-warn' : 'is-tip');
      var stateWordText = blocked ? M.EQUIPMENT_STATE_LABELS.blocked : w('Conseil');
      $row.append(infoTip($('<i class="fas j2ha-v3-todo-icon"></i>').addClass(blocked ? 'fa-exclamation-triangle' : 'fa-lightbulb')
        .attr('title', stateWordText).attr('aria-label', stateWordText).attr('role', 'img')));
      // Le nom ouvre la fiche de l'équipement dans la page (même chemin que « Voir »).
      var $open = $('<button type="button" class="j2ha-free-name j2ha-v3-todo-name j2ha-v3-todo-open"></button>').text(item.eq_name)
        .attr('title', item.eq_name);
      $open.on('click', function () { openEquipmentView(item.room_id, item.eq_id); });
      $row.append($open);
      $row.append($('<span class="text-muted j2ha-free-name j2ha-v3-todo-room"></span>').text(item.room_name));
      var short = shortCause(item.code);
      var $cause = $('<span class="j2ha-v2-todo-cause j2ha-v3-todo-cause"></span>').text(short || item.text || '');
      if (item.text) infoTip($cause.attr('title', item.text), { doc: 'les-causes-de-blocage' });
      $row.append($cause);
      $row.append(todoAction(item));
      return $row;
    }

    function renderTodo(vm) {
      var $host = $('#j2ha_v2_todo').empty();
      if (!vm.overview || gridFilter()) return;
      var only = todoFilter();
      var all = todoItems(vm.overview, vm.equipments);
      var items = orderLikeGrid(all.filter(function (i) { return i.kind === 'blocked'; }))
        .concat(orderLikeGrid(all.filter(function (i) { return i.kind !== 'blocked'; })));
      if (only) items = items.filter(function (i) { return only === 'blocked' ? i.kind === 'blocked' : i.kind === 'advice'; });
      if (items.length === 0) return;
      var $head = $('<div class="j2ha-v2-todo-head"></div>')
        .append($('<strong class="j2ha-v2-todo-title"></strong>').text('{{À faire}}'))
        .append($('<span class="j2ha-v3-todo-n"></span>').text(String(items.length)));
      $host.append($head);
      var $list = $('<div class="j2ha-v3-todo-list"></div>');
      var limit = only || todoExpanded ? items.length : TODO_LIMIT;
      items.slice(0, limit).forEach(function (item) { $list.append(todoRow(item)); });
      $host.append($list);
      if (items.length > limit) {
        var $more = $('<button type="button" class="j2ha-v2-link j2ha-v3-todo-more"></button>')
          .text(w('Tout afficher') + ' (' + items.length + ')');
        $more.on('click', function () { todoExpanded = true; render(); });
        $host.append($more);
      }
    }

    function render() {
      lastView = buildViewModel(lastState && lastState.response, rooms, lastState && lastState.valid);
      renderHouse(lastView);
      renderFreshness(lastState);
      renderCards(lastView);
      renderTodo(lastView);
      renderTabs();
      renderStatus();
      subscribers.slice().forEach(function (fn) { fn(); });
    }

    function setFilter(key) {
      filter = (key && filter !== key) ? key : null;
      render();
    }

    // Story 25.4 : un filtre posé tel quel (sans bascule) : état initial de la vue de travail (une seule vérité de filtre).
    function setFilterExact(key) {
      var next = GROUP_KEYS.indexOf(key) !== -1 ? key : null;
      if (next === filter) return;
      filter = next;
      render();
    }

    // Front v3 (Lot 1) : une puce ou un segment du liseré filtre SUR PLACE — la grille (pièces à 0 masquées, compteurs filtrés)
    // pour Publiés / À appliquer / Exclus / Non lus, la liste « À faire » pour Bloqués / Conseils ; un second clic le retire.
    function activateFilter(key) {
      setFilter(key);
    }

    // Pose le filtre (jamais de bascule) et amène sa représentation à l'écran.
    function showFilter(key) {
      if (filter !== key) { filter = key; render(); }
      var node = $(todoFilter() ? '#j2ha_v2_todo' : '#j2ha_roomCards').get(0);
      if (node && typeof node.scrollIntoView === 'function') node.scrollIntoView({ block: 'nearest' });
    }

    function openEquipmentView(roomId, eqId) {
      if (typeof env.openView === 'function' && env.openView({ room: roomId, eq: eqId }) !== false) return;
      if (typeof env.openRoom === 'function') env.openRoom(roomId);
    }

    // Menu « ⋯ » : balisage dans la page PHP, comportement ici (ouvre au clic et au clavier, Échap, clic extérieur).
    function closeMenu(returnFocus) {
      if (!openMenuWrap) return;
      var $toggle = openMenuWrap.find('.j2ha-menu-toggle');
      openMenuWrap.removeClass('j2ha-menu-open');
      openMenuWrap.closest('.j2ha-room-has-menu').removeClass('j2ha-room-menu-shown');
      $toggle.attr('aria-expanded', 'false');
      if (returnFocus) $toggle.focus();
      openMenuWrap = null;
    }

    function menuItems($wrap) {
      var items = [];
      $wrap.find('.j2ha-menu-item').each(function (_i, el) { if (!$(el).prop('disabled')) items.push(el); });
      return items;
    }

    // Menu d'une carte de pièce : la carte (overflow:hidden du cœur) le laisse déborder tant qu'il est ouvert ; aligné à droite
    // sous le « ⋯ », il bascule à gauche s'il sortirait de la fenêtre (première carte d'une rangée).
    function placeRoomMenu($wrap) {
      var $card = $wrap.closest('.j2ha-room-has-menu');
      if ($card.length === 0) return;
      $card.addClass('j2ha-room-menu-shown');
      $wrap.removeClass('j2ha-room-menu-start');
      var menu = $wrap.find('.j2ha-room-menu-list').get(0);
      if (!menu || typeof menu.getBoundingClientRect !== 'function') return;
      if (menu.getBoundingClientRect().left < 8) $wrap.addClass('j2ha-room-menu-start');
    }

    function bindMenu($wrap) {
      var $toggle = $wrap.find('.j2ha-menu-toggle');
      function open() {
        closeMenu(false);
        $wrap.addClass('j2ha-menu-open');
        $toggle.attr('aria-expanded', 'true');
        openMenuWrap = $wrap;
        placeRoomMenu($wrap);
        var first = menuItems($wrap)[0];
        if (first) $(first).focus();
      }
      $toggle.on('click', function (event) {
        if (event && event.stopPropagation) event.stopPropagation();
        if (openMenuWrap && openMenuWrap.get(0) === $wrap.get(0)) closeMenu(false); else open();
      });
      function onKey(event) {
        // Story 25.8 : un menu posé dans une carte ne doit jamais faire remonter ses touches jusqu'à la carte (qui ouvrirait la pièce).
        if (event && event.stopPropagation) event.stopPropagation();
        var key = event && event.key;
        if (key === 'Escape') { closeMenu(true); return; }
        if (key !== 'ArrowDown' && key !== 'ArrowUp') return;
        if (event.preventDefault) event.preventDefault();
        if (!$wrap.hasClass('j2ha-menu-open')) { open(); return; }
        var items = menuItems($wrap);
        if (items.length === 0) return;
        var at = items.indexOf(event.target);
        var next = key === 'ArrowDown' ? (at + 1) % items.length : (at <= 0 ? items.length - 1 : at - 1);
        $(items[next]).focus();
      }
      $toggle.on('keydown', onKey);
      $wrap.find('.j2ha-menu').on('keydown', onKey);
      $wrap.find('.j2ha-menu-item').each(function (_i, el) {
        $(el).on('click.j2haMenu', function () { closeMenu(false); });
      });
    }

    // Story 25.8 (AC6) : menu « ⋯ » d'une carte de pièce. La carte est un role="button" qui ouvre la pièce : le clic, keydown et keyup
    // du bouton, du menu et de ses entrées sont arrêtés avant l'`onclick` de la carte et l'écouteur clavier ci-dessous.
    function bindRoomMenu($wrap) {
      var $card = $wrap.closest('.j2ha-room-card');
      var $toggle = $wrap.find('.j2ha-menu-toggle');
      var $menu = $wrap.find('.j2ha-menu');
      function stop(event) { if (event && event.stopPropagation) event.stopPropagation(); }
      // Classe posée ici (le balisage de la carte reste celui de 25.3) : elle ancre le menu dans le coin de la carte.
      $card.addClass('j2ha-room-has-menu');
      bindMenu($wrap);
      $toggle.on('keyup', stop);
      $menu.on('click', stop);
      $menu.on('keyup', stop);
      $wrap.find('.j2ha-room-exclude').on('click', function (event) {
        stop(event);
        var $item = $wrap.find('.j2ha-room-exclude');
        if ($item.prop('disabled')) return;
        var id = parseInt($card.attr('data-object_id'), 10);
        if (typeof env.excludeRoom === 'function') env.excludeRoom(id, roomName(id), !isRoomExcluded(id), $item, $toggle);
      });
    }

    // « Télécharger le diagnostic… » : le contenu (case « Pseudonymiser » et bouton d'export, identifiants et
    // gestionnaire inchangés) est déplacé dans une boîte bootbox, puis rendu à sa place à la fermeture.
    function openDiagnosticDialog() {
      var $holder = $('#div_diagnosticDialog');
      var $content = $holder.children();
      var dialog = env.bootbox.dialog({
        title: w('Télécharger le diagnostic support'),
        message: $content,
        onEscape: true,
        backdrop: true,
        buttons: { close: { label: w('Fermer'), className: 'btn-default' } },
      });
      if (dialog && typeof dialog.on === 'function') {
        dialog.on('hidden.bs.modal', function () { $holder.append($content); });
      }
    }

    // « Télécharger l'export de décision… » (story 24.2) : même mécanique que le diagnostic, contenu du bouton de
    // téléchargement (lecture seule, identifiants seulement) déplacé dans une boîte puis rendu à sa place à la fermeture.
    function openDecisionExportDialog() {
      var $holder = $('#div_decisionExportDialog');
      var $content = $holder.children();
      var dialog = env.bootbox.dialog({
        title: w('Télécharger l\'export de décision'),
        message: $content,
        onEscape: true,
        backdrop: true,
        buttons: { close: { label: w('Fermer'), className: 'btn-default' } },
      });
      if (dialog && typeof dialog.on === 'function') {
        dialog.on('hidden.bs.modal', function () { $holder.append($content); });
      }
    }

    function init() {
      $('#bt_refreshStates').on('click', function () { reader.refresh(); });
      // Front v3 (Lot 1) : onglets Équipements / Scénarios (flèches gauche / droite entre les deux).
      $('.j2ha-v3-tab').each(function (_i, el) {
        $(el).on('click', function () { selectTab($(el).attr('data-tab')); });
        $(el).on('keydown', function (event) {
          var key = event && event.key;
          if (key !== 'ArrowLeft' && key !== 'ArrowRight') return;
          if (event.preventDefault) event.preventDefault();
          selectTab(activeTab === 'equipments' ? 'scenarios' : 'equipments');
          $('.j2ha-v3-tab[data-tab="' + activeTab + '"]').focus();
        });
      });
      $('#j2ha_moreMenu .j2ha-menu-wrap').each(function (_i, el) { bindMenu($(el)); });
      $('#j2ha_roomCards .j2ha-room-menu').each(function (_i, el) { bindRoomMenu($(el)); });
      $('#bt_openDiagnostic').on('click', openDiagnosticDialog);
      $('#bt_openDecisionExport').on('click', openDecisionExportDialog);
      $('#j2ha_roomCards .j2ha-room-card').each(function (_i, el) {
        $(el).on('keydown', function (event) {
          if (event && (event.key === 'Enter' || event.key === ' ')) {
            if (event.preventDefault) event.preventDefault();
            if (typeof env.openRoom === 'function') env.openRoom(parseInt($(el).attr('data-object_id'), 10));
          }
        });
        var color = $(el).attr('data-color');
        var node = $(el).get(0);
        if (color && node && node.style && typeof node.style.setProperty === 'function') {
          node.style.setProperty('--j2ha-room-color', color);
        }
      });
      $(env.document).on('click', function (event) {
        if (openMenuWrap && $(event && event.target).closest('.j2ha-menu-wrap').length === 0) closeMenu(false);
      });
      selectTab('equipments');
      render();
      reader.load();
    }

    function snapshotNow() {
      return { kind: lastState && lastState.kind, view: lastView, filter: filter, readAt: lastState && lastState.readAt };
    }

    return {
      reader: reader, init: init, render: render, setFilter: setFilter, setFilterExact: setFilterExact,
      // Story 25.8 : drapeau « pièce exclue » (lecture) et remplacement depuis `excluded_objects` d'une écriture réussie.
      isRoomExcluded: isRoomExcluded, setExcludedObjects: setExcludedObjects,
      // Confirmation chiffrée de l'exclusion d'une pièce, calculée depuis la copie des états en mémoire (aucune requête).
      exclusionDialog: function (id, name, excluded) {
        return roomExclusionDialog({ name: name, excluded: excluded, impact: roomExclusionImpact(snapshotNow(), rooms, id) });
      },
      filter: function () { return filter; },
      view: function () { return lastView; },
      // L'état du démon vient d'être relu (onglet Scénarios, Appliquer, verdict), sans relire les équipements.
      statusChanged: function () { renderTabs(); renderStatus(); },
      // Front v3 (Lot 1) : cible et confirmation de « Appliquer (n) », lues dans la copie des états (aucune requête).
      toApplyIds: function () { return lastView && !lastView.stale ? toApplyIds(lastView.overview) : []; },
      applyDialog: function () { return applyDialog(lastView && !lastView.stale ? toApplyIds(lastView.overview).length : 0); },
      selectTab: selectTab,
      // Story 25.4 : ce que la vue de travail lit (copie unique en mémoire, agrégats dérivés) et abonnement aux rendus.
      snapshot: snapshotNow,
      subscribe: function (fn) {
        subscribers.push(fn);
        return function () { subscribers = subscribers.filter(function (f) { return f !== fn; }); };
      },
    };
  }

  var api = {
    computeOverview: computeOverview,
    filterRows: filterRows,
    gaugeSegments: gaugeSegments,
    gaugeLabel: gaugeLabel,
    houseHeadline: houseHeadline,
    chipsFor: chipsFor,
    roomExclusionImpact: roomExclusionImpact,
    roomExclusionDialog: roomExclusionDialog,
    todoItems: todoItems,
    causeSentence: causeSentence,
    houseFigure: houseFigure,
    houseChips: houseChips,
    HOUSE_CHIPS: HOUSE_CHIPS,
    segmentLabel: segmentLabel,
    tileMarks: tileMarks,
    roomMatchesFilter: roomMatchesFilter,
    toApplyIds: toApplyIds,
    applyDialog: applyDialog,
    statusVerdict: statusVerdict,
    rememberSync: rememberSync,
    scenarioCount: scenarioCount,
    scenarioTabText: scenarioTabText,
    shortCause: shortCause,
    adviceCount: adviceCount,
    adviceLabel: adviceLabel,
    GROUP_KEYS: GROUP_KEYS,
    GROUP_OF_STATE: GROUP_OF_STATE,
    plural: plural,
    inactiveMarks: inactiveMarks,
    unreadLabel: unreadLabel,
    blockedMentionLabel: blockedMentionLabel,
    classifyResponse: classifyResponse,
    buildViewModel: buildViewModel,
    createReader: createReader,
    createPage: createPage,
    ajaxFetch: ajaxFetch,
    FILTERS: FILTERS,
  };

  // Démarrage dans le navigateur (jamais sous Node : les tests pilotent createPage / createReader).
  if (typeof window !== 'undefined' && typeof window.$ === 'function' && typeof document !== 'undefined' && !(typeof module === 'object' && module.exports)) {
    window.$(function () {
      if (window.$('#j2ha_houseBlock').length === 0) return;
      var page = createPage({
        $: window.$,
        document: document,
        bootbox: window.bootbox,
        rooms: window.j2haRoomsTree || [],
        pluginNames: window.j2haPluginNames || {},
        readStates: ajaxFetch(window.$),
        now: function () { return Date.now(); },
        setTimeout: function (fn, ms) { return window.setTimeout(fn, ms); },
        clearTimeout: function (id) { window.clearTimeout(id); },
        openRoom: function (id) { if (typeof window.j2haOpenRoom === 'function') window.j2haOpenRoom(id); },
        // Story 25.8 : demande d'exclusion d'une pièce (confirmation chiffrée, écriture, relecture) — jeedom2ha.js.
        excludeRoom: function () { if (typeof window.requestRoomExclusion === 'function') return window.requestRoomExclusion.apply(window, arguments); },
        // Front v2 (Lot 7) : dernier état du démon (relais getBridgeStatus de jeedom2ha.js), lu pour la mention des scénarios.
        bridgeStatus: function () { return window.jeedom2haLastBridgeStatus || null; },
        // Story 25.4 : la vue de travail remplace la fenêtre de pièce ; `false` = vue indisponible (repli sur la page B).
        openView: function (target) {
          var view = window.Jeedom2haWorkviewInstance;
          return view && typeof view.open === 'function' ? view.open(target) : false;
        },
      });
      window.Jeedom2haOverviewPage = page;
      // Fins d'action (succès ou échec) : une relecture sans refresh, coalescée (AC6).
      window.j2haNotifyStatesChanged = function () { page.reader.trigger(); };
      document.addEventListener('visibilitychange', function () {
        if (document.visibilityState === 'visible') page.reader.onVisible();
      });
      // Front v2 (Lot 7) : chaque réponse de getBridgeStatus (lue par jeedom2ha.js) met à jour la mention des scénarios ;
      // aucune requête ajoutée, on écoute seulement la fin des appels existants.
      window.$(document).on('ajaxComplete', function (_event, _xhr, settings) {
        var data = settings && settings.data;
        if (typeof data === 'string' && data.indexOf('action=getBridgeStatus') !== -1) page.statusChanged();
      });
      page.init();
    });
  }

  return api;
}));
