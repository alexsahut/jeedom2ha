/* Story 25.3 — Page principale B : lecture des états (un seul appel), agrégats, jauge maison filtrante,
 * cartes de pièce, barre de santé (menu « ⋯ », boîte du diagnostic).
 *
 * Aucune règle d'état n'est écrite ici : l'état d'un équipement est le retour de `resolveEquipmentState`
 * (25.1), les compteurs de pièce sont ceux de `summarizeRoom`, la maison en est la somme. La route
 * `getEquipmentStates` (25.2) est lue par UNE fonction (`ajaxFetch`) ; `refresh=1` n'y est posé que par
 * le bouton « Actualiser ». Partie pure (testée sous Node) + partie navigateur en fin de fichier. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('./jeedom2ha_mapping_override.js'));
    return;
  }
  root.Jeedom2haOverview = factory(root.Jeedom2haMappingOverride);
}(typeof globalThis !== 'undefined' ? globalThis : this, function (M) {
  'use strict';

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
    { key: 'other', label: function (n) { return n + ' ' + w('exclus et autres'); } },
    { key: 'unread', label: function (n) { return unreadLabel(n); } },
  ];

  function emptyCounts() { return { published: 0, to_apply: 0, blocked: 0, other: 0, unread: 0 }; }

  // Puces de filtre (Story 25.4) : calculées ICI pour la page principale ET pour la vue de travail, afin qu'aucun second
  // calcul d'effectifs n'existe. « Non lus » n'apparaît que s'il y en a ; une puce à zéro est désactivée.
  function chipsFor(counts) {
    var c = counts || emptyCounts();
    var chips = [];
    FILTERS.forEach(function (f) {
      var count = c[f.key] || 0;
      if (f.key === 'unread' && count === 0) return;
      chips.push({ key: f.key, count: count, label: f.label(count), disabled: count === 0 });
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
        };
        if (entry && typeof entry === 'object') {
          // `summarizeRoom` lit l'identifiant dans l'entrée : on le garantit sans cloner l'entrée.
          trees.push(entry.jeedom_eq_id === eq.eq_id ? entry : Object.assign({}, entry, { jeedom_eq_id: eq.eq_id }));
          var resolved = M.resolveEquipmentState(entry, eq.enabled);
          row.state = resolved.state;
          row.blocked_mention = resolved.blocked_mention;
          row.group = GROUP_OF_STATE[resolved.state];
        }
        counts[row.group] += 1;
        rows.push(row);
      });
      var summary = M.summarizeRoom(trees, list.length, enabledById);
      summaries.push(summary);
      out.rooms.push({ object_id: room.object_id, object_name: room.object_name, summary: summary, counts: counts, equipments: rows });
      out.total += list.length;
      if (room.object_id > 0) out.rooms_count += 1;
      GROUP_KEYS.forEach(function (key) { out.counts[key] += counts[key]; });
    });
    out.house = M.summarizeHouse(summaries);
    return out;
  }

  function filterRows(overview, key) {
    var rows = [];
    overview.rooms.forEach(function (room) {
      room.equipments.forEach(function (row) { if (row.group === key) rows.push(row); });
    });
    return rows;
  }

  // Segments de la jauge, dans l'ordre publiés / à appliquer / bloqués / exclus et autres / non lus.
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
    if (counts.other > 0) parts.push(counts.other + ' ' + w('exclus et autres'));
    if (counts.unread > 0) parts.push(unreadLabel(counts.unread));
    return parts.join(', ');
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

  function pad2(n) { return ('0' + n).slice(-2); }

  function createPage(env) {
    var $ = env.$;
    var rooms = env.rooms || [];
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

    function stateWord(state) {
      return $('<span class="j2ha-state-word"></span>').addClass('j2ha-state-' + state)
        .append($('<i class="fas"></i>').addClass(STATE_ICONS[state]))
        .append($('<span class="j2ha-state-text"></span>').text(' ' + M.EQUIPMENT_STATE_LABELS[state]));
    }

    function buildGauge(counts, total, extraClass) {
      var $gauge = $('<div class="j2ha-gauge" role="img"></div>').addClass(extraClass || '');
      $gauge.attr('aria-label', gaugeLabel(counts, total));
      gaugeSegments(counts, total).forEach(function (seg) {
        var $seg = $('<span class="j2ha-seg"></span>').addClass('j2ha-seg-' + seg.key)
          .attr('data-filter', seg.key).attr('aria-hidden', 'true').attr('style', 'flex-grow:' + seg.count);
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
        setText('#j2ha_houseMeta', '');
        $gaugeHost.append($('<div class="j2ha-gauge j2ha-gauge-neutral" role="img"></div>').attr('aria-label', vm.message || w('Chargement...')));
        return;
      }
      var o = vm.overview;
      var head = houseHeadline(o.counts.published, o.total);
      setText('#j2ha_houseNumber', head.number);
      setText('#j2ha_houseSub', head.sub);
      setText('#j2ha_houseMeta', o.total + ' ' + w('équipements Jeedom') + ', ' + plural(o.rooms_count, 'pièce', 'pièces'));
      $gaugeHost.append(buildGauge(o.counts, o.total));
      chipsFor(o.counts).forEach(function (chip) {
        var $chip = $('<button type="button" class="j2ha-chip-filter"></button>')
          .addClass('j2ha-chip-filter-' + chip.key).attr('data-filter', chip.key)
          .attr('aria-pressed', filter === chip.key ? 'true' : 'false')
          .append($('<span class="j2ha-chip-dot"></span>'))
          .append(document_text(chip.label));
        if (chip.disabled) $chip.prop('disabled', true);
        $chip.on('click', function () { activateFilter(chip.key); });
        $chip.on('keydown', onFilterKey);
        $chips.append($chip);
      });
      if (focusKey) $chips.find(chipId(focusKey)).focus();
    }

    function document_text(text) { return env.document.createTextNode(text); }

    function renderFreshness(state) {
      var at = state && state.readAt;
      setText('#j2ha_freshness', at ? w('Chiffres relus à') + ' ' + pad2(at.getHours()) + ':' + pad2(at.getMinutes()) : '');
      var $button = $('#bt_refreshStates');
      var busy = !!(state && state.refreshing);
      $button.prop('disabled', busy);
      $button.attr('aria-busy', busy ? 'true' : 'false');
      $button.empty().append($('<i class="fas fa-sync-alt"></i>').toggleClass('fa-spin', busy))
        .append(document_text(' ' + (busy ? w('Actualisation…') : w('Actualiser'))));
    }

    function renderCards(vm) {
      var o = vm.overview;
      $('#j2ha_roomCards .j2ha-room-card').each(function (_i, el) {
        var $card = $(el);
        var id = parseInt($card.attr('data-object_id'), 10);
        var $slot = $card.find('.j2ha-room-state').empty();
        var room = o ? o.rooms.filter(function (r) { return r.object_id === id; })[0] : null;
        $card.removeClass('j2ha-room-blocked j2ha-room-dim');
        if (!room) {
          $card.removeAttr('aria-label');
          return;
        }
        var c = room.counts;
        var total = room.summary.equipments_total;
        $slot.append($('<div class="j2ha-room-ratio"></div>').text(c.published + ' / ' + total + ' ' + w(c.published > 1 ? 'publiés' : 'publié')));
        $slot.append(buildGauge(c, total, 'j2ha-gauge-card'));
        var $marks = $('<div class="j2ha-room-marks"></div>');
        if (c.blocked > 0) $marks.append($('<span class="j2ha-mark j2ha-mark-blocked"></span>').text(plural(c.blocked, 'bloqué', 'bloqués')));
        if (c.to_apply > 0) $marks.append($('<span class="j2ha-mark j2ha-mark-to_apply"></span>').text(c.to_apply + ' ' + w('à appliquer')));
        if (c.unread > 0) $marks.append($('<span class="j2ha-mark j2ha-mark-unread"></span>').text(unreadLabel(c.unread)));
        $slot.append($marks);
        if (c.blocked > 0) $card.addClass('j2ha-room-blocked');
        if (filter && filterMatchesNothing(room)) $card.addClass('j2ha-room-dim');
        $card.attr('aria-label', room.object_name + ', ' + gaugeLabel(c, total));
      });
    }

    function filterMatchesNothing(room) {
      return room.counts[filter] === 0;
    }

    function renderList(vm) {
      var $panel = $('#j2ha_filterPanel');
      var $list = $('#j2ha_filterList').empty();
      if (!filter || !vm.overview) {
        $panel.hide();
        return;
      }
      var rows = orderLikeGrid(filterRows(vm.overview, filter));
      var def = FILTERS.filter(function (f) { return f.key === filter; })[0];
      setText('#j2ha_filterTitle', def.label(rows.length));
      rows.forEach(function (row) {
        var $btn = $('<button type="button" class="j2ha-frow-btn"></button>').attr('data-room-id', row.room_id);
        if (row.state) $btn.append(stateWord(row.state));
        else $btn.append($('<span class="j2ha-state-word j2ha-state-unread"></span>').append($('<i class="fas fa-question-circle"></i>')).append($('<span class="j2ha-state-text"></span>').text(' ' + w('Non lu'))));
        $btn.append($('<span class="j2ha-frow-name j2ha-free-name"></span>').text(row.eq_name));
        $btn.append($('<span class="text-muted j2ha-frow-room j2ha-free-name"></span>').text(row.room_name));
        if (row.blocked_mention > 0) $btn.append($('<span class="j2ha-mark j2ha-mark-blocked"></span>').text(blockedMentionLabel(row.blocked_mention)));
        $btn.on('click', function () { openEquipmentView(row.room_id, row.eq_id); });
        $btn.on('keydown', onFilterKey);
        $list.append($('<li class="j2ha-frow"></li>').append($btn));
      });
      $panel.show();
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

    function render() {
      lastView = buildViewModel(lastState && lastState.response, rooms, lastState && lastState.valid);
      renderHouse(lastView);
      renderFreshness(lastState);
      renderCards(lastView);
      renderList(lastView);
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

    // Story 25.4 (AC1) : une puce ou un segment de la jauge ouvre la vue de travail avec ce filtre ; un second clic sur
    // le filtre déjà actif le retire (la page principale reste affichée). Sans vue (env.openView absent ou refusé),
    // le comportement de 25.3 est conservé : liste filtrée sur la page principale.
    function activateFilter(key) {
      if (filter === key) { setFilter(null); return; }
      if (typeof env.openView === 'function' && env.openView({ filter: key }) !== false) return;
      setFilter(key);
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
      $toggle.attr('aria-expanded', 'false');
      if (returnFocus) $toggle.focus();
      openMenuWrap = null;
    }

    function menuItems($wrap) {
      var items = [];
      $wrap.find('.j2ha-menu-item').each(function (_i, el) { if (!$(el).prop('disabled')) items.push(el); });
      return items;
    }

    function bindMenu($wrap) {
      var $toggle = $wrap.find('.j2ha-menu-toggle');
      function open() {
        closeMenu(false);
        $wrap.addClass('j2ha-menu-open');
        $toggle.attr('aria-expanded', 'true');
        openMenuWrap = $wrap;
        var first = menuItems($wrap)[0];
        if (first) $(first).focus();
      }
      $toggle.on('click', function (event) {
        if (event && event.stopPropagation) event.stopPropagation();
        if (openMenuWrap && openMenuWrap.get(0) === $wrap.get(0)) closeMenu(false); else open();
      });
      function onKey(event) {
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

    function init() {
      $('#bt_refreshStates').on('click', function () { reader.refresh(); });
      $('#bt_clearFilter').on('click', function () { setFilter(null); });
      $('#j2ha_filterPanel').on('keydown', onFilterKey);
      $('#j2ha_moreMenu .j2ha-menu-wrap').each(function (_i, el) { bindMenu($(el)); });
      $('#bt_openDiagnostic').on('click', openDiagnosticDialog);
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
      render();
      reader.load();
    }

    return {
      reader: reader, init: init, render: render, setFilter: setFilter, setFilterExact: setFilterExact,
      filter: function () { return filter; },
      view: function () { return lastView; },
      // Story 25.4 : ce que la vue de travail lit (copie unique en mémoire, agrégats dérivés) et abonnement aux rendus.
      snapshot: function () {
        return { kind: lastState && lastState.kind, view: lastView, filter: filter, readAt: lastState && lastState.readAt };
      },
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
    GROUP_KEYS: GROUP_KEYS,
    GROUP_OF_STATE: GROUP_OF_STATE,
    plural: plural,
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
        readStates: ajaxFetch(window.$),
        now: function () { return Date.now(); },
        setTimeout: function (fn, ms) { return window.setTimeout(fn, ms); },
        clearTimeout: function (id) { window.clearTimeout(id); },
        openRoom: function (id) { if (typeof window.j2haOpenRoom === 'function') window.j2haOpenRoom(id); },
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
      page.init();
    });
  }

  return api;
}));
