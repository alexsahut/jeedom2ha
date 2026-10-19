/* Story 25.4 — Vue de travail maître-détail (C) : remplace la fenêtre de pièce.
 *
 * Un clic sur une carte de pièce ou sur un filtre de la page principale ouvre, dans la page du plugin, une vue
 * pleine hauteur : l'arbre pièces → équipements (filtrable, recherchable) à gauche, le détail de la pièce
 * (« À traiter dans cette pièce ») ou de l'équipement choisi à droite.
 *
 * Règles (AC4 à AC8) :
 *  - l'état d'un équipement est TOUJOURS `resolveEquipmentState` (via les agrégats de la page B) ; ce module n'écrit
 *    aucune règle d'état, aucune partition de causes, aucune table de libellés d'état ;
 *  - aucune lecture de `getEquipmentStates` ici : la vue lit la copie unique de la page B (`page.snapshot()`) ;
 *  - un arbre unitaire (`getMappingOverrides`) n'est lu qu'à la SÉLECTION d'un équipement, par la surface ;
 *  - les écritures sont celles de la surface (jeedom2ha_mapping_surface.js), inchangées.
 *
 * Partie pure (testée sous Node) : fragment d'URL, arbre, recherche, KPI, liste « À traiter » ; puis le contrôleur
 * (`createWorkview`) et son démarrage dans le navigateur. Tout le CSS de la vue est sous `.j2ha-wv` / `.j2ha-wv-`. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory(require('./jeedom2ha_mapping_override.js'), require('./jeedom2ha_overview.js'));
    return;
  }
  root.Jeedom2haWorkview = factory(root.Jeedom2haMappingOverride, root.Jeedom2haOverview);
}(typeof globalThis !== 'undefined' ? globalThis : this, function (M, O) {
  'use strict';

  // Seuil de repli entre la disposition large (deux colonnes) et la disposition étroite (panneau repliable) : UNE
  // constante, reprise à l'identique par la media query CSS de la vue (test d'égalité).
  var LAYOUT_SPLIT_MIN_WIDTH = 1024;
  var MIN_HEIGHT = 480;               // hauteur minimale utile de la vue (Q12)
  var SEARCH_DEBOUNCE_MS = 150;
  var FRAGMENT_PREFIX = 'j2ha-vue=';
  var STORAGE_KEY = 'j2ha-vue';        // repli sessionStorage (Q1) si le fragment est inutilisable
  var FILTER_KEYS = ['published', 'blocked', 'to_apply', 'other', 'unread'];
  var ICON_FALLBACK = 'fas fa-door-open';

  function w(text) { return '{{' + text + '}}'; }

  // --- Fragment d'URL : `#j2ha-vue=piece:P;eq:E;f:F` (valeurs validées avant tout usage, AC7, AC18) ---

  var INT_RE = /^(0|[1-9][0-9]{0,8})$/;
  var POSITIVE_RE = /^[1-9][0-9]{0,8}$/;

  function parseFragment(hash) {
    if (typeof hash !== 'string') return null;
    var text = hash.charAt(0) === '#' ? hash.slice(1) : hash;
    if (text.indexOf(FRAGMENT_PREFIX) !== 0) return null;
    var body = text.slice(FRAGMENT_PREFIX.length);
    if (body === '') return null;
    var out = { piece: null, eq: null, filter: null };
    var seen = {};
    var parts = body.split(';');
    for (var i = 0; i < parts.length; i++) {
      var m = /^([a-z]+):([A-Za-z0-9_]+)$/.exec(parts[i]);
      if (!m || seen[m[1]]) return null;
      seen[m[1]] = true;
      if (m[1] === 'piece' && INT_RE.test(m[2])) out.piece = parseInt(m[2], 10);
      else if (m[1] === 'eq' && POSITIVE_RE.test(m[2])) out.eq = parseInt(m[2], 10);
      else if (m[1] === 'f' && FILTER_KEYS.indexOf(m[2]) !== -1) out.filter = m[2];
      else return null;
    }
    if (out.eq !== null && out.piece === null) return null;
    return out;
  }

  function formatFragment(state) {
    var s = state || {};
    var parts = [];
    if (typeof s.piece === 'number') parts.push('piece:' + s.piece);
    if (typeof s.eq === 'number') parts.push('eq:' + s.eq);
    if (typeof s.filter === 'string' && FILTER_KEYS.indexOf(s.filter) !== -1) parts.push('f:' + s.filter);
    return parts.length ? '#' + FRAGMENT_PREFIX + parts.join(';') : '';
  }

  // L'état lu dans l'URL n'est accepté que s'il désigne une pièce existante et un équipement de CETTE pièce.
  function resolveFragment(parsed, rooms) {
    if (!parsed) return null;
    if (parsed.piece === null) return parsed.eq === null ? { piece: null, eq: null, filter: parsed.filter } : null;
    var list = Array.isArray(rooms) ? rooms : [];
    var room = null;
    for (var i = 0; i < list.length; i++) {
      if (list[i].object_id === parsed.piece) { room = list[i]; break; }
    }
    if (!room) return null;
    if (parsed.eq !== null && !room.equipments.some(function (eq) { return eq.eq_id === parsed.eq; })) return null;
    return { piece: parsed.piece, eq: parsed.eq, filter: parsed.filter };
  }

  // Insensible à la casse et aux accents ; le texte est toujours littéral (jamais une expression régulière).
  function foldText(text) {
    var s = String(text === undefined || text === null ? '' : text).toLowerCase();
    return typeof s.normalize === 'function' ? s.normalize('NFD').replace(/[̀-ͯ]/g, '') : s;
  }

  // --- Arbre pièces → équipements (AC11 à AC13) ---

  function safeIcon(classes) {
    return typeof classes === 'string' && /^[A-Za-z0-9 _-]{1,80}$/.test(classes) ? classes : ICON_FALLBACK;
  }

  function safeColor(color) {
    return typeof color === 'string' && /^#(?:[0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(color) ? color : '';
  }

  /** Pièces décorées : `j2haRoomsTree` normalisé (ordre natif) + icône et couleur sûres (jamais de HTML). */
  function decorateRooms(raw) {
    var normalized = M.normalizeRoomsTree(raw || []);
    var byId = {};
    (Array.isArray(raw) ? raw : []).forEach(function (room) { byId[parseInt(room && room.object_id, 10)] = room; });
    return normalized.map(function (room) {
      var source = byId[room.object_id] || {};
      return Object.assign({}, room, { icon_classes: safeIcon(source.icon_classes), color: safeColor(source.color) });
    });
  }

  /**
   * @param {object} input rooms (décorées), groups ([{ title, room_ids }] lus dans la grille de la page B), overview
   *   (`computeOverview` ou null), filter, search, expanded ({ id: true }), selectedRoom, selectedEq.
   * Rend { groups: [{ title, rooms: [...] }], rowCount, active, hasStates } ; chaque pièce porte ses lignes (le rendu
   * différé ne les affiche que dépliées, Q5).
   */
  function buildTreeModel(input) {
    var rooms = input.rooms || [];
    var overview = input.overview || null;
    var filter = overview ? input.filter || null : null;
    var needle = foldText(input.search || '').trim();
    var active = !!filter || needle !== '';
    var expanded = input.expanded || {};
    var byRoom = {};
    if (overview) overview.rooms.forEach(function (r) { byRoom[r.object_id] = r; });
    var roomsById = {};
    rooms.forEach(function (r) { roomsById[r.object_id] = r; });

    var groups = (input.groups && input.groups.length) ? input.groups.slice() : [{ title: null, room_ids: rooms.map(function (r) { return r.object_id; }) }];
    var placed = {};
    groups.forEach(function (g) { g.room_ids.forEach(function (id) { placed[id] = true; }); });
    var rest = rooms.filter(function (r) { return !placed[r.object_id]; }).map(function (r) { return r.object_id; });
    if (rest.length) groups.push({ title: null, room_ids: rest });

    var model = { groups: [], rowCount: 0, roomCount: 0, active: active, hasStates: !!overview };
    groups.forEach(function (g) {
      var list = [];
      g.room_ids.forEach(function (id) {
        var room = roomsById[id];
        if (!room) return;
        var ov = byRoom[id] || null;
        var rowsById = {};
        if (ov) ov.equipments.forEach(function (r) { rowsById[r.eq_id] = r; });
        var nameMatch = needle !== '' && foldText(room.object_name).indexOf(needle) !== -1;
        var rows = [];
        room.equipments.forEach(function (eq) {
          var src = rowsById[eq.eq_id] || null;
          var row = {
            eq_id: eq.eq_id, name: eq.eq_name, enabled: eq.enabled,
            state: src ? src.state : null, mention: src ? src.blocked_mention : 0, group: src ? src.group : null,
            unread: !!ov && !!src && src.state === null,
            selected: input.selectedEq === eq.eq_id,
          };
          if (filter && row.group !== filter) return;
          if (needle !== '' && !nameMatch && foldText(eq.eq_name).indexOf(needle) === -1) return;
          rows.push(row);
        });
        if (active && rows.length === 0) return;
        var counts = ov ? ov.counts : null;
        var isExpanded = active ? true : !!expanded[id];
        list.push({
          object_id: id, name: room.object_name, icon: room.icon_classes, color: room.color,
          total: room.equipments.length,
          published: counts ? counts.published : null, blocked: counts ? counts.blocked : 0, to_apply: counts ? counts.to_apply : 0,
          hasStates: !!ov, expanded: isExpanded, selected: input.selectedRoom === id && input.selectedEq == null,
          rows: isExpanded ? rows : [],
        });
        model.roomCount += 1;
        if (isExpanded) model.rowCount += rows.length;
      });
      if (list.length) model.groups.push({ title: g.title, rooms: list });
    });
    return model;
  }

  // --- Détail de pièce : liste « À traiter dans cette pièce » (AC14, Q8, Q11) ---
  // Causes et décomptes sont produits par les fonctions de 25.1 appliquées à l'entrée AGRÉGÉE : aucune lecture d'arbre.
  function buildTreatList(ovRoom, entries, room) {
    if (!ovRoom) return [];
    var byId = {};
    room.equipments.forEach(function (eq) { byId[eq.eq_id] = eq; });
    return ovRoom.equipments.filter(function (r) { return r.state === 'blocked' || r.state === 'to_apply'; }).map(function (r) {
      var entry = entries && Object.prototype.hasOwnProperty.call(entries, String(r.eq_id)) ? entries[String(r.eq_id)] : null;
      var eq = byId[r.eq_id] || { eq_name: '', enabled: true };
      var item = {
        eq_id: r.eq_id, name: eq.eq_name, state: r.state, mention: r.blocked_mention,
        causes: [], genericTypes: false, counters: '', canApply: r.state === 'to_apply',
      };
      if (entry) {
        var groups = M.groupBlockedCauses(entry);
        item.causes = r.state === 'blocked' ? groups.map(function (g) {
          return { text: M.buildCauseNoticeText(g), raw: g.raw_code, genericTypes: !!g.generic_types_link };
        }) : [];
        item.genericTypes = item.causes.some(function (c) { return c.genericTypes; });
        item.counters = M.buildEquipmentCounterLabels(entry, eq.enabled).text;
      }
      return item;
    });
  }

  /** « Les N équipements … n'appellent aucune action » : nombres issus de `summarizeRoom` (équipements lus). */
  function noActionSentence(summary) {
    var read = summary && typeof summary.equipments_read === 'number' ? summary.equipments_read : 0;
    var unread = summary && summary.equipments_total > read;
    if (read === 1) return w(unread ? "L'équipement lu de cette pièce n'appelle aucune action" : "L'équipement de cette pièce n'appelle aucune action");
    return w('Les') + ' ' + read + ' ' + w(unread ? 'équipements lus de cette pièce' : 'équipements de cette pièce') + ' ' + w("n'appellent aucune action");
  }

  // --- Contrôleur ---

  function createWorkview(env) {
    var $ = env.$;
    var doc = env.document;
    var win = env.window;
    var surface = env.surface;
    var page = env.page;
    var timeoutSet = env.setTimeout;
    var timeoutClear = env.clearTimeout;

    var rooms = decorateRooms(env.rooms);
    var roomsById = {};
    var st = {
      open: false, room: null, eq: null, search: '', expanded: {}, drawerOpen: false, layout: null,
      pushed: 0, savedScroll: 0, lastFilter: null, groupTitleOf: {}, searchTimer: null, built: false, focusTitle: false,
    };
    var $root = null;
    var $main = null;
    var el = {};
    var mql = null;
    var groups = null;

    function indexRooms() {
      roomsById = {};
      rooms.forEach(function (r) { roomsById[r.object_id] = r; });
    }
    indexRooms();

    function roomOfEq(eqId) {
      for (var i = 0; i < rooms.length; i++) {
        if (rooms[i].equipments.some(function (eq) { return eq.eq_id === eqId; })) return rooms[i];
      }
      return null;
    }
    function eqOf(room, eqId) {
      var found = room.equipments.filter(function (eq) { return eq.eq_id === eqId; });
      return found.length ? found[0] : null;
    }

    function snap() {
      var s = page && typeof page.snapshot === 'function' ? page.snapshot() : null;
      return s || { view: null, filter: null };
    }
    function overviewOf() {
      var s = snap();
      return s.view && s.view.overview ? s.view.overview : null;
    }
    function entriesOf() {
      var s = snap();
      return s.view && s.view.equipments ? s.view.equipments : null;
    }
    function overviewRoom(id) {
      var o = overviewOf();
      if (!o) return null;
      for (var i = 0; i < o.rooms.length; i++) if (o.rooms[i].object_id === id) return o.rooms[i];
      return null;
    }

    // Regroupement par objet parent : celui de la grille de la page B (aucun second algorithme), lu dans son balisage.
    function readGroups() {
      var out = [];
      $('#j2ha_roomCards .j2ha-room-group').each(function () {
        var $g = $(this);
        var title = $g.find('.j2ha-room-group-title').first().text();
        var ids = [];
        $g.find('.j2ha-room-card').each(function () {
          var id = parseInt($(this).attr('data-object_id'), 10);
          if (!isNaN(id)) ids.push(id);
        });
        out.push({ title: title || null, room_ids: ids });
      });
      return out;
    }
    function groupTitleFor(roomId) {
      var list = groups || [];
      for (var i = 0; i < list.length; i++) if (list[i].room_ids.indexOf(roomId) !== -1) return list[i].title;
      return null;
    }

    // --- Annonces (zone role=status aria-live=polite) ---
    function announce(text) {
      if (el.live) el.live.text(text);
    }

    // --- Coquille ---
    function build() {
      if (st.built) return;
      groups = readGroups();
      $root = $('#j2ha_workView');
      $main = $('#j2ha_mainView');
      $root.empty();

      var $bar = $('<div class="j2ha-wv-bar"></div>');
      el.back = $('<button type="button" class="btn btn-default btn-sm j2ha-wv-back"></button>')
        .append($('<i class="fas fa-arrow-left"></i>')).append(doc.createTextNode(' ' + w('Toutes les pièces')));
      el.drawerToggle = $('<button type="button" class="btn btn-default btn-sm j2ha-wv-drawer-toggle" aria-expanded="false" aria-controls="j2ha_wvNav"></button>')
        .append($('<i class="fas fa-list"></i>')).append(doc.createTextNode(' ' + w('Pièces')));
      el.readStatus = $('<div class="text-muted j2ha-wv-read-status" role="status" aria-live="polite"></div>');
      el.live = $('<span class="j2ha-wv-live" role="status" aria-live="polite"></span>');
      $bar.append(el.back).append(el.drawerToggle).append(el.readStatus).append(el.live);

      var $body = $('<div class="j2ha-wv-body"></div>');
      el.nav = $('<aside class="j2ha-wv-nav" id="j2ha_wvNav"></aside>');
      var $tools = $('<div class="j2ha-wv-tools"></div>');
      el.search = $('<input type="search" class="form-control input-sm j2ha-wv-search" autocomplete="off"/>')
        .attr('aria-label', w('Rechercher une pièce ou un équipement')).attr('placeholder', w('Rechercher une pièce ou un équipement'));
      el.chips = $('<div class="j2ha-wv-chips"></div>');
      el.searchStatus = $('<div class="text-muted j2ha-wv-search-status" role="status" aria-live="polite"></div>');
      $tools.append(el.search).append(el.chips).append(el.searchStatus);
      el.tree = $('<ul class="j2ha-wv-tree" role="tree"></ul>').attr('aria-label', w('Pièces et équipements'));
      el.nav.append($tools).append(el.tree);

      el.detail = $('<div class="j2ha-wv-detail"></div>');
      el.reassurance = $('<div id="j2haSurface_reassurance" class="alert alert-warning" role="status" aria-live="polite"></div>')
        .append($('<i class="fas fa-shield-alt"></i>'))
        .append(doc.createTextNode(' ' + w('Aucun impact Homebridge : cet écran ne modifie que la sortie Home Assistant de jeedom2ha.')));
      el.reassurance.hide();
      el.feedback = $('<div class="j2ha-room-feedback" role="status"></div>');
      el.feedback.hide();
      el.pane = $('<div class="j2ha-wv-pane"></div>');
      el.detail.append(el.reassurance).append(el.feedback).append(el.pane);
      $body.append(el.nav).append(el.detail);
      $root.append($bar).append($body);

      el.back.on('click', goBack);
      el.drawerToggle.on('click', function () { setDrawer(!st.drawerOpen); });
      el.search.on('input', function () {
        var value = $(this).val();
        if (st.searchTimer !== null) timeoutClear(st.searchTimer);
        st.searchTimer = timeoutSet(function () {
          st.searchTimer = null;
          st.search = typeof value === 'string' ? value : '';
          renderTree();
          announceResults();
        }, SEARCH_DEBOUNCE_MS);
      });
      // Échap ne quitte jamais la vue (Q13) : il ferme d'abord le menu ou la confirmation ouverts (gérés ailleurs).
      el.search.on('keydown', function () {});
      el.tree.on('keydown', onTreeKey);
      surface.setHost({ isRoomShown: function (objectId) { return st.open && st.room === objectId; } });

      installLayout();
      st.built = true;
    }

    // --- Disposition large / étroite, hauteur ---
    function currentWidth() { return typeof win.innerWidth === 'number' ? win.innerWidth : LAYOUT_SPLIT_MIN_WIDTH; }

    function computeLayout() {
      if (mql && typeof mql.matches === 'boolean') return mql.matches ? 'split' : 'compact';
      return currentWidth() >= LAYOUT_SPLIT_MIN_WIDTH ? 'split' : 'compact';
    }

    function applyLayout(announceChange) {
      var next = computeLayout();
      var changed = st.layout !== next;
      st.layout = next;
      if ($root) $root.attr('data-j2ha-layout', next);
      if (changed) {
        // Compact : panneau ouvert tant qu'aucune sélection n'existe ; large : jamais de tiroir.
        st.drawerOpen = next === 'compact' && st.room === null;
        syncDrawer();
        if (announceChange) announce(next === 'split' ? w('Disposition en deux colonnes') : w('Disposition en une colonne'));
      }
    }

    function installLayout() {
      try {
        mql = typeof win.matchMedia === 'function' ? win.matchMedia('(min-width: ' + LAYOUT_SPLIT_MIN_WIDTH + 'px)') : null;
      } catch (e) {
        mql = null;
      }
      if (mql && typeof mql.addEventListener === 'function') {
        mql.addEventListener('change', function () { applyLayout(true); applyHeight(); });
      } else if (mql && typeof mql.addListener === 'function') {
        mql.addListener(function () { applyLayout(true); applyHeight(); });
      }
      // Repli (matchMedia absent ou en erreur) et recalcul de la hauteur : resize / orientationchange.
      win.addEventListener('resize', function () { applyLayout(true); applyHeight(); });
      win.addEventListener('orientationchange', function () { applyLayout(true); applyHeight(); });
      applyLayout(false);
    }

    function offsetTop() {
      if (typeof env.offsetTop === 'function') return env.offsetTop();
      var node = $root && $root.get(0);
      return node && typeof node.getBoundingClientRect === 'function' ? Math.max(0, node.getBoundingClientRect().top) : 0;
    }

    // Q12 : hauteur = fenêtre − décalage haut MESURÉ à l'exécution (la barre varie selon la version de Jeedom et la
    // barre d'adresse d'iOS change 100vh), avec un minimum utile. La CSS porte les replis dvh / vh.
    function height() {
      var viewport = typeof win.innerHeight === 'number' ? win.innerHeight : 0;
      return Math.max(MIN_HEIGHT, Math.round(viewport - offsetTop()));
    }

    function applyHeight() {
      var node = $root && $root.get(0);
      if (node && node.style && typeof node.style.setProperty === 'function') node.style.setProperty('--j2ha-wv-height', height() + 'px');
    }

    function setDrawer(open) {
      st.drawerOpen = !!open;
      syncDrawer();
    }
    function syncDrawer() {
      if (!el.nav) return;
      el.nav.toggleClass('j2ha-wv-nav-open', st.layout === 'compact' && st.drawerOpen);
      el.drawerToggle.attr('aria-expanded', st.layout === 'compact' && st.drawerOpen ? 'true' : 'false');
      el.drawerToggle.attr('aria-label', st.drawerOpen ? w('Masquer les pièces') : w('Pièces'));
    }

    // --- État d'URL (fragment, repli sessionStorage) ---
    function currentHash() { return typeof win.location.hash === 'string' ? win.location.hash : ''; }
    function baseUrl() { return (win.location.pathname || '') + (win.location.search || ''); }

    function store(state) {
      try { if (win.sessionStorage) win.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(Object.assign({ mode: 'storage' }, state))); } catch (e) { /* stockage indisponible */ }
    }
    function unstore() {
      try { if (win.sessionStorage) win.sessionStorage.removeItem(STORAGE_KEY); } catch (e) { /* stockage indisponible */ }
    }

    function syncUrl(mode) {
      var state = { piece: st.room, eq: st.eq, filter: snap().filter };
      var hash = formatFragment(state);
      if (hash === currentHash()) return;
      try {
        if (mode === 'push') {
          win.history.pushState({ j2ha: st.pushed + 1 }, '', hash === '' ? baseUrl() : hash);
          st.pushed += 1;
        } else {
          win.history.replaceState({ j2ha: st.pushed }, '', hash === '' ? baseUrl() : hash);
        }
      } catch (e) {
        // Le cœur intercepte ou interdit le fragment : la sélection est gardée en session (pas de lien partageable).
        store(state);
      }
    }

    function goBack() {
      if (st.pushed > 0 && typeof win.history.go === 'function') {
        win.history.go(-st.pushed);
        return;
      }
      try { win.history.replaceState(null, '', baseUrl()); } catch (e) { /* inutilisable */ }
      closeView();
    }

    function onPop(event) {
      var depth = event && event.state && typeof event.state.j2ha === 'number' ? event.state.j2ha : 0;
      st.pushed = depth;
      var parsed = resolveFragment(parseFragment(currentHash()), rooms);
      if (!parsed) {
        if (st.open) closeView();
        return;
      }
      open({ room: parsed.piece, eq: parsed.eq, filter: parsed.filter, fromHistory: true, exactFilter: true });
    }

    // --- Sélection ---
    function resetFeedback() {
      if (el.feedback) el.feedback.empty().hide();
    }

    function afterSelect(opts, changedRoom) {
      var o = opts || {};
      if (st.layout === 'compact') setDrawer(false);
      if (changedRoom) resetFeedback();
      if (o.history !== false) syncUrl('push');
      if (o.user) st.focusTitle = true;
    }

    function selectRoom(id, opts) {
      var room = roomsById[id];
      if (!room) return false;
      var changedRoom = st.room !== id;
      var changed = changedRoom || st.eq !== null;
      st.room = id;
      st.eq = null;
      st.expanded[id] = true;
      surface.clearEquipment();
      surface.setRoom(room);
      renderTree();
      renderPane();
      afterSelect(opts, changedRoom);
      if (changed) announce(w('Pièce') + ' ' + room.object_name);
      focusTitleIfAsked();
      return true;
    }

    function selectEquipment(roomId, eqId, opts) {
      var room = roomsById[roomId];
      var eq = room ? eqOf(room, eqId) : null;
      if (!room || !eq) return false;
      var changedRoom = st.room !== roomId;
      st.room = roomId;
      st.eq = eqId;
      st.expanded[roomId] = true;
      renderTree();
      renderEquipmentPane(room, eq);
      afterSelect(opts, changedRoom);
      announce(w('Équipement') + ' ' + eq.eq_name);
      focusTitleIfAsked();
      return true;
    }

    function clearSelection() {
      st.room = null;
      st.eq = null;
      surface.clearEquipment();
      renderTree();
      renderPane();
      if (st.layout === 'compact') setDrawer(true);
    }

    function focusTitleIfAsked() {
      if (!st.focusTitle) return;
      st.focusTitle = false;
      var title = el.pane.find('.j2ha-wv-title').first();
      if (title.length) title.focus();
    }

    // --- Ouverture, fermeture ---
    function enterView() {
      st.savedScroll = typeof win.scrollY === 'number' ? win.scrollY : (win.pageYOffset || 0);
      $main.hide();
      $root.show();
      st.open = true;
      surface.resetSession();
      applyLayout(false);
      applyHeight();
      if (typeof win.scrollTo === 'function') win.scrollTo(0, 0);
    }

    function closeView() {
      if (!st.open) return;
      if (st.searchTimer !== null) { timeoutClear(st.searchTimer); st.searchTimer = null; }
      surface.clearEquipment();
      st.open = false;
      st.room = null;
      st.eq = null;
      st.search = '';
      st.pushed = 0;
      if (el.search) el.search.val('');
      el.pane.empty();
      resetFeedback();
      unstore();
      $root.hide();
      $main.show();
      if (typeof win.scrollTo === 'function') win.scrollTo(0, st.savedScroll);
    }

    /**
     * Ouvre la vue. `target` : { room?, eq?, filter?, fromHistory?, exactFilter? }. Rend `false` si la cible est
     * invalide (pièce inconnue, équipement d'une autre pièce) : l'appelant garde alors la page principale.
     */
    function open(target) {
      var t = target || {};
      var roomId = t.room === undefined || t.room === null ? null : Number(t.room);
      var eqId = t.eq === undefined || t.eq === null ? null : Number(t.eq);
      if (roomId !== null && !roomsById[roomId]) return false;
      if (eqId !== null) {
        var owner = roomId !== null ? roomsById[roomId] : roomOfEq(eqId);
        if (!owner || !eqOf(owner, eqId)) return false;
        roomId = owner.object_id;
      }
      if (!$('#j2ha_workView').length) return false;
      build();
      if (!st.open) enterView();
      if (t.exactFilter || (t.filter !== undefined && t.filter !== null)) page.setFilterExact(t.filter === undefined ? null : t.filter);
      st.lastFilter = snap().filter;
      var opts = { history: false, user: !t.fromHistory };
      if (roomId === null) clearSelection();
      else if (eqId !== null) selectEquipment(roomId, eqId, opts);
      else selectRoom(roomId, opts);
      renderChips();
      renderStatus();
      if (!t.fromHistory) syncUrl('push');
      return true;
    }

    // Retour à la page principale : l'état de B est conservé (filtre, défilement) ; le fragment n'est retiré que par goBack.
    function reconcile(nextRooms) {
      rooms = decorateRooms(nextRooms);
      indexRooms();
      if (!st.open) return;
      if (st.room !== null && !roomsById[st.room]) {
        clearSelection();
      } else if (st.eq !== null && !eqOf(roomsById[st.room], st.eq)) {
        selectRoom(st.room, { history: false });
      } else {
        renderTree();
      }
    }

    // --- Rendu : puces, état de lecture, arbre ---
    function renderStatus() {
      var s = snap();
      var view = s.view;
      var text = view ? (view.notice || view.message || '') : '';
      el.readStatus.text(text);
      if ($root) $root.toggleClass('j2ha-stale', !!(view && view.stale));
    }

    function renderChips() {
      var overview = overviewOf();
      var active = snap().filter;
      var focusKey = null;
      var focused = doc.activeElement;
      if (focused && focused.classList && focused.classList.contains('j2ha-wv-chip')) focusKey = focused.getAttribute('data-filter');
      el.chips.empty();
      if (!overview) return;
      O.chipsFor(overview.counts).forEach(function (chip) {
        var $chip = $('<button type="button" class="j2ha-chip-filter j2ha-wv-chip"></button>')
          .addClass('j2ha-chip-filter-' + chip.key).attr('data-filter', chip.key)
          .attr('aria-pressed', active === chip.key ? 'true' : 'false')
          .append($('<span class="j2ha-chip-dot"></span>'))
          .append(doc.createTextNode(chip.label));
        if (chip.disabled) $chip.prop('disabled', true);
        $chip.on('click', function () { page.setFilter(chip.key); });
        el.chips.append($chip);
      });
      if (focusKey) el.chips.find('.j2ha-wv-chip[data-filter="' + focusKey + '"]').focus();
    }

    function stateCell(state) {
      var $cell = $('<span class="j2ha-wv-state"></span>');
      if (state) $cell.append(surface.stateWord(state));
      return $cell;
    }

    function itemKey($item) { return $item.attr('data-key'); }

    function keyOfFocus() {
      var focused = doc.activeElement;
      if (!focused || !el.tree.get(0) || typeof focused.getAttribute !== 'function') return null;
      var $item = $(focused).closest('[role=treeitem]');
      return $item.length ? itemKey($item) : null;
    }

    function buildRoomItem(room) {
      var $item = $('<li class="j2ha-wv-room" role="treeitem" aria-level="1"></li>')
        .attr('data-object_id', room.object_id).attr('data-key', 'r' + room.object_id)
        .attr('aria-expanded', room.expanded ? 'true' : 'false').attr('aria-selected', room.selected ? 'true' : 'false')
        .attr('tabindex', '-1');
      var $row = $('<div class="j2ha-wv-row"></div>');
      var $toggle = $('<button type="button" class="j2ha-wv-toggle" tabindex="-1"></button>')
        .attr('aria-label', room.expanded ? w('Replier') : w('Déplier'))
        .append($('<i class="fas"></i>').addClass(room.expanded ? 'fa-chevron-down' : 'fa-chevron-right'));
      $row.append($toggle);
      $row.append($('<i class="j2ha-wv-icon"></i>').addClass(room.icon).attr('aria-hidden', 'true'));
      $row.append($('<span class="j2ha-wv-name j2ha-free-name"></span>').text(room.name));
      if (room.published !== null) {
        $row.append($('<span class="text-muted j2ha-wv-ratio"></span>').text(room.published + ' / ' + room.total));
      }
      var $marks = $('<span class="j2ha-wv-room-marks"></span>');
      if (room.blocked > 0) $marks.append($('<span class="j2ha-mark j2ha-mark-blocked"></span>').text(O.plural(room.blocked, 'bloqué', 'bloqués')));
      if (room.to_apply > 0) $marks.append($('<span class="j2ha-mark j2ha-mark-to_apply"></span>').text(room.to_apply + ' ' + w('à appliquer')));
      $row.append($marks);
      if (room.color) {
        var node = $item.get(0);
        if (node && node.style && typeof node.style.setProperty === 'function') node.style.setProperty('--j2ha-room-color', room.color);
      }
      $toggle.on('click', function (event) {
        if (event && event.stopPropagation) event.stopPropagation();
        st.expanded[room.object_id] = !st.expanded[room.object_id];
        renderTree();
      });
      $row.on('click', function () { selectRoom(room.object_id, { user: true }); });
      $item.append($row);
      if (room.expanded) {
        var $group = $('<ul class="j2ha-wv-eqs" role="group"></ul>');
        room.rows.forEach(function (row) { $group.append(buildEquipmentItem(room, row)); });
        $item.append($group);
      }
      return $item;
    }

    function buildEquipmentItem(room, row) {
      var $item = $('<li class="j2ha-wv-eq" role="treeitem" aria-level="2"></li>')
        .attr('data-eq-id', row.eq_id).attr('data-key', 'e' + row.eq_id)
        .attr('aria-selected', row.selected ? 'true' : 'false').attr('tabindex', '-1');
      if (!row.enabled) $item.addClass('j2ha-wv-eq-disabled');
      var $row = $('<div class="j2ha-wv-row"></div>');
      $row.append(stateCell(row.state));
      $row.append($('<span class="j2ha-wv-name j2ha-free-name"></span>').text(row.name));
      if (!row.enabled) $row.append($('<span class="text-muted j2ha-wv-off"></span>').text(' ' + w('(désactivé dans Jeedom)')));
      if (row.unread) $row.append($('<span class="text-muted j2ha-wv-unread"></span>').text(w('non lu')));
      if (row.mention > 0) $row.append($('<span class="j2ha-mark j2ha-mark-blocked"></span>').text(O.blockedMentionLabel(row.mention)));
      $row.on('click', function () { selectEquipment(room.object_id, row.eq_id, { user: true }); });
      $item.append($row);
      return $item;
    }

    function renderTree() {
      if (!el.tree) return;
      var focusKey = keyOfFocus();
      var node = el.tree.get(0);
      var scroll = node && typeof node.scrollTop === 'number' ? node.scrollTop : 0;
      var model = buildTreeModel({
        rooms: rooms, groups: groups, overview: overviewOf(), filter: snap().filter, search: st.search,
        expanded: st.expanded, selectedRoom: st.room, selectedEq: st.eq,
      });
      el.tree.empty();
      model.groups.forEach(function (g) {
        if (g.title) {
          el.tree.append($('<li class="j2ha-wv-group" role="presentation"></li>')
            .append($('<span class="j2ha-wv-group-title j2ha-free-name"></span>').text(g.title)));
        }
        g.rooms.forEach(function (room) { el.tree.append(buildRoomItem(room)); });
      });
      el.searchStatus.text(model.roomCount === 0 && (model.active) ? w('Aucun résultat') : '');
      // Roving tabindex : une seule ligne dans l'ordre de tabulation (celle qui a le focus, sinon la sélection, sinon la première).
      var target = focusKey ? el.tree.find('[data-key="' + focusKey + '"]') : $();
      if (!target.length) target = el.tree.find('[aria-selected="true"]');
      if (!target.length) target = el.tree.find('[role=treeitem]').first();
      target.first().attr('tabindex', '0');
      if (focusKey && target.length) target.first().focus();
      if (node && typeof node.scrollTop === 'number') node.scrollTop = scroll;
    }

    function announceResults() {
      var o = overviewOf();
      if (st.search === '' && !snap().filter) return;
      var model = buildTreeModel({ rooms: rooms, groups: groups, overview: o, filter: snap().filter, search: st.search, expanded: st.expanded, selectedRoom: st.room, selectedEq: st.eq });
      announce(model.roomCount === 0 ? w('Aucun résultat') : model.rowCount + ' ' + w(model.rowCount > 1 ? 'équipements affichés' : 'équipement affiché'));
    }

    // --- Clavier de l'arbre (motif ARIA tree) ---
    function onTreeKey(event) {
      var key = event && event.key;
      var target = event && event.target;
      if (!target) return;
      var $item = $(target).closest('[role=treeitem]');
      var items = el.tree.find('[role=treeitem]').get();
      var at = $item.length ? items.indexOf($item.get(0)) : -1;
      if (at === -1) return;
      function focusAt(index) {
        if (index < 0 || index >= items.length) return;
        items.forEach(function (node) { $(node).attr('tabindex', node === items[index] ? '0' : '-1'); });
        $(items[index]).focus();
      }
      var isRoom = $item.hasClass('j2ha-wv-room');
      var handled = true;
      if (key === 'ArrowDown') focusAt(at + 1);
      else if (key === 'ArrowUp') focusAt(at - 1);
      else if (key === 'Home') focusAt(0);
      else if (key === 'End') focusAt(items.length - 1);
      else if (key === 'ArrowRight') {
        if (isRoom && $item.attr('aria-expanded') !== 'true') { st.expanded[parseInt($item.attr('data-object_id'), 10)] = true; renderTree(); }
        else if (isRoom) focusAt(at + 1);
      } else if (key === 'ArrowLeft') {
        if (isRoom && $item.attr('aria-expanded') === 'true') { st.expanded[parseInt($item.attr('data-object_id'), 10)] = false; renderTree(); }
        else if (!isRoom) {
          for (var i = at - 1; i >= 0; i--) { if ($(items[i]).hasClass('j2ha-wv-room')) { focusAt(i); break; } }
        }
      } else if (key === 'Enter' || key === ' ' || key === 'Spacebar') {
        if (isRoom) selectRoom(parseInt($item.attr('data-object_id'), 10), { user: true });
        else selectEquipment(st.room !== null && eqOf(roomsById[st.room] || { equipments: [] }, parseInt($item.attr('data-eq-id'), 10)) ? st.room : roomOfEqId($item), parseInt($item.attr('data-eq-id'), 10), { user: true });
      } else {
        handled = false;
      }
      if (handled && event.preventDefault) event.preventDefault();
    }

    function roomOfEqId($item) {
      var owner = roomOfEq(parseInt($item.attr('data-eq-id'), 10));
      return owner ? owner.object_id : null;
    }

    // --- Détail ---
    function crumb(room, withEquipment) {
      var $nav = $('<nav class="j2ha-wv-crumb text-muted"></nav>').attr('aria-label', w("Fil d'Ariane"));
      var parent = groupTitleFor(room.object_id);
      var last = parent && parent.slice(-room.object_name.length) === room.object_name ? '' : room.object_name;
      if (parent) $nav.append($('<span class="j2ha-free-name"></span>').text(parent));
      if (parent && last) $nav.append(doc.createTextNode(' › '));
      if (last) {
        if (withEquipment) {
          var $link = $('<button type="button" class="btn btn-link j2ha-wv-crumb-room j2ha-free-name"></button>').text(last);
          $link.on('click', function () { selectRoom(room.object_id, { user: true }); });
          $nav.append($link);
        } else {
          $nav.append($('<span class="j2ha-free-name"></span>').text(last));
        }
      }
      return $nav;
    }

    function renderPane() {
      el.pane.empty();
      var room = st.room !== null ? roomsById[st.room] : null;
      if (!room) {
        el.pane.append($('<div class="text-muted j2ha-wv-empty"></div>').text(w('Sélectionnez une pièce ou un équipement')));
        return;
      }
      el.pane.append(crumb(room, false));
      var $head = $('<div class="j2ha-wv-roomhead"></div>');
      $head.append($('<i class="j2ha-wv-roomicon"></i>').addClass(room.icon_classes).attr('aria-hidden', 'true'));
      var $title = $('<h2 class="j2ha-wv-title" tabindex="-1"></h2>');
      $title.append($(room.object_id > 0 ? '<span class="j2ha-free-name"></span>' : '<span></span>').text(room.object_name));
      $head.append($title);
      $head.append(surface.buildRoomActions(room));
      el.pane.append($head);
      el.kpis = $('<div class="j2ha-wv-kpis" role="group"></div>').attr('aria-label', w('Indicateurs de la pièce'));
      el.todo = $('<section class="j2ha-wv-todo"></section>');
      el.pane.append(el.kpis).append(el.todo);
      refreshRoomDynamic();
      // Les boutons créés ici suivent le même gating que les boutons globaux (pont indisponible) et l'état des
      // équipements de la pièce (entrées agrégées) dès l'affichage, sans attendre le rendu suivant de la page B.
      surface.refreshRoomGating(room, roomEntries(room));
    }

    function renderEquipmentPane(room, eq) {
      el.kpis = null;
      el.todo = null;
      el.pane.empty();
      el.pane.append(crumb(room, true));
      var $host = $('<div class="j2ha-wv-eqhost"></div>');
      el.pane.append($host);
      surface.openEquipment($host, room, eq);
    }

    function kpiButton(item, group) {
      var $kpi = $('<button type="button" class="j2ha-chip j2ha-room-counter j2ha-wv-kpi"></button>')
        .addClass('j2ha-chip-' + item.state).attr('data-state', item.state).attr('data-filter', group)
        .attr('aria-pressed', snap().filter === group ? 'true' : 'false')
        .append($('<i class="fas"></i>').addClass(STATE_ICON(item.state)))
        .append(doc.createTextNode(' ' + item.text));
      $kpi.on('click', function () { page.setFilter(group); });
      return $kpi;
    }

    function STATE_ICON(state) {
      return { published: 'fa-check-circle', to_apply: 'fa-clock', blocked: 'fa-exclamation-triangle', excluded: 'fa-eye-slash', disabled: 'fa-pause-circle', nothing_to_publish: 'fa-minus-circle' }[state];
    }

    function todoRow(room, item) {
      var $row = $('<li class="j2ha-wv-todo-row"></li>').attr('data-eq-id', item.eq_id);
      var $main = $('<div class="j2ha-wv-todo-main"></div>');
      $main.append($('<span class="j2ha-wv-state"></span>').append(surface.stateWord(item.state)));
      $main.append($('<span class="j2ha-wv-todo-name j2ha-free-name"></span>').text(item.name));
      if (item.counters) $main.append($('<span class="text-muted j2ha-wv-todo-counters"></span>').text(item.counters));
      $row.append($main);
      if (item.causes.length) {
        var $causes = $('<ul class="j2ha-wv-todo-causes"></ul>');
        item.causes.forEach(function (cause) {
          var $cause = $('<li class="j2ha-wv-todo-cause"></li>').append($('<i class="fas fa-exclamation-triangle"></i>'));
          var $text = $('<span class="j2ha-notice-text"></span>').text(' ' + cause.text);
          if (cause.raw) $text.attr('title', cause.raw);
          $causes.append($cause.append($text));
        });
        $row.append($causes);
      }
      var $actions = $('<div class="j2ha-wv-todo-actions"></div>');
      var $error = $('<div class="j2ha-publication-error text-danger"></div>').hide();
      if (item.genericTypes) {
        var $link = $('<a class="btn btn-default btn-xs j2ha-open-generic-types" target="_blank" rel="noopener"></a>')
          .attr('href', surface.genericTypesUrl).text(w('Ouvrir les types génériques'));
        $link.on('click', function (event) { if (event && event.stopPropagation) event.stopPropagation(); });
        $actions.append($link);
      }
      if (item.canApply) {
        // Q11 : écriture directe (executeHaAction publier / equipement), sans lire d'arbre ; même réservation de bouton.
        var $apply = $('<button type="button" class="btn btn-primary btn-xs j2ha-wv-todo-apply" data-ha-action="republier"></button>').text(w('Appliquer'));
        $apply.on('click', function (event) {
          if (event && event.stopPropagation) event.stopPropagation();
          surface.setRoom(room);
          surface.applyEquipment(item.eq_id, $apply, $error);
        });
        $actions.append($apply);
      }
      $actions.append($error);
      $row.append($actions);
      // Un clic sur le reste de la ligne sélectionne l'équipement.
      $row.on('click', function () { selectEquipment(room.object_id, item.eq_id, { user: true }); });
      return $row;
    }

    function refreshRoomDynamic() {
      if (st.room === null || st.eq !== null || !el.kpis) return;
      var room = roomsById[st.room];
      var ov = overviewRoom(st.room);
      el.kpis.empty();
      el.todo.empty();
      if (ov) {
        var labels = M.buildRoomCounterLabels(ov.summary);
        labels.items.forEach(function (item) { el.kpis.append(kpiButton(item, O.GROUP_OF_STATE[item.state])); });
        [labels.unread, labels.presence_unknown].forEach(function (text) {
          if (text) el.kpis.append($('<span class="text-muted j2ha-wv-kpi-note"></span>').text(text));
        });
      }
      el.todo.append($('<h3 class="j2ha-wv-todo-title"></h3>').text(w('À traiter dans cette pièce')));
      if (!ov) return;
      var list = buildTreatList(ov, entriesOf(), room);
      if (list.length === 0) {
        var $empty = $('<div class="j2ha-wv-todo-empty"></div>');
        $empty.append($('<p class="j2ha-wv-todo-none"></p>').text(w('Rien à traiter dans cette pièce')));
        $empty.append($('<p class="text-muted j2ha-wv-todo-sentence"></p>').text(noActionSentence(ov.summary)));
        el.todo.append($empty);
      } else {
        var $list = $('<ul class="j2ha-wv-todo-list"></ul>');
        list.forEach(function (item) { $list.append(todoRow(room, item)); });
        el.todo.append($list);
      }
    }

    function roomEntries(room) {
      var all = entriesOf();
      if (!all) return [];
      var out = [];
      room.equipments.forEach(function (eq) {
        if (Object.prototype.hasOwnProperty.call(all, String(eq.eq_id))) {
          var entry = all[String(eq.eq_id)];
          out.push(entry.jeedom_eq_id === eq.eq_id ? entry : Object.assign({}, entry, { jeedom_eq_id: eq.eq_id }));
        }
      });
      return out;
    }

    // --- Mise à jour à chaque rendu de la page B (relecture des états) ---
    function onPageRender() {
      if (!st.open) return;
      renderStatus();
      renderChips();
      renderTree();
      if (st.room !== null && st.eq === null) refreshRoomDynamic();
      if (st.room !== null) {
        var room = roomsById[st.room];
        surface.refreshRoomGating(room, roomEntries(room));
        if (st.eq !== null && entriesOf() && Object.prototype.hasOwnProperty.call(entriesOf(), String(st.eq))) {
          surface.refreshEquipmentState(Object.assign({}, entriesOf()[String(st.eq)], { jeedom_eq_id: st.eq }));
        }
      }
      var filter = snap().filter;
      if (filter !== st.lastFilter) {
        st.lastFilter = filter;
        syncUrl('replace');
      }
    }

    if (page && typeof page.subscribe === 'function') page.subscribe(onPageRender);
    win.addEventListener('popstate', onPop);

    // Point d'entrée des cartes (Q14) : `onclick="j2haOpenRoom(id)"` ; seul contrat : ouvrir la vue sur cette pièce.
    win.j2haOpenRoom = function (objectId) {
      var id = parseInt(objectId, 10);
      if (!isNaN(id)) open({ room: id });
    };

    function start() {
      // Entrée d'historique reçue d'un rechargement (history.state conservé par le navigateur) : le nombre de niveaux poussés.
      var initial = win.history && win.history.state;
      st.pushed = initial && typeof initial.j2ha === 'number' ? initial.j2ha : 0;
      var parsed = resolveFragment(parseFragment(currentHash()), rooms);
      if (parsed) {
        open({ room: parsed.piece, eq: parsed.eq, filter: parsed.filter, fromHistory: true, exactFilter: true });
        return;
      }
      try {
        var saved = win.sessionStorage ? JSON.parse(win.sessionStorage.getItem(STORAGE_KEY) || 'null') : null;
        if (saved && saved.mode === 'storage' && currentHash() === '') {
          var again = resolveFragment({ piece: saved.piece === undefined ? null : saved.piece, eq: saved.eq === undefined ? null : saved.eq, filter: saved.filter || null }, rooms);
          if (again) open({ room: again.piece, eq: again.eq, filter: again.filter, fromHistory: true, exactFilter: true });
        }
      } catch (e) { /* stockage illisible : page principale */ }
    }

    return {
      open: open, start: start, reconcile: reconcile, height: height,
      isOpen: function () { return st.open; },
      state: function () { return { open: st.open, room: st.room, eq: st.eq, layout: st.layout, search: st.search, drawerOpen: st.drawerOpen }; },
    };
  }

  var api = {
    LAYOUT_SPLIT_MIN_WIDTH: LAYOUT_SPLIT_MIN_WIDTH,
    FILTER_KEYS: FILTER_KEYS,
    parseFragment: parseFragment,
    formatFragment: formatFragment,
    resolveFragment: resolveFragment,
    foldText: foldText,
    decorateRooms: decorateRooms,
    buildTreeModel: buildTreeModel,
    buildTreatList: buildTreatList,
    noActionSentence: noActionSentence,
    createWorkview: createWorkview,
  };

  // Démarrage dans le navigateur, après la page principale (jamais sous Node : les tests pilotent createWorkview).
  if (typeof window !== 'undefined' && typeof window.$ === 'function' && typeof document !== 'undefined' && !(typeof module === 'object' && module.exports)) {
    window.$(function () {
      if (window.$('#j2ha_workView').length === 0 || !window.Jeedom2haOverviewPage || !window.Jeedom2haSurface) return;
      var view = createWorkview({
        $: window.$, document: document, window: window, surface: window.Jeedom2haSurface, page: window.Jeedom2haOverviewPage,
        rooms: window.j2haRoomsTree || [],
        setTimeout: function (fn, ms) { return window.setTimeout(fn, ms); },
        clearTimeout: function (id) { window.clearTimeout(id); },
      });
      window.Jeedom2haWorkviewInstance = view;
      view.start();
    });
  }

  return api;
}));
