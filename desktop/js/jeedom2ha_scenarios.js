/* Front v3 (Lot 4b) : onglet « Scénarios » de la page du plugin (option B : un scénario n'est publié que si on l'a choisi).
 *
 * Deux parties :
 *  - des fonctions PURES (aucun DOM), testées sous node : lecture de `status.scenarios`, compte de l'onglet, filtres,
 *    suggestion « lancés à la main », corps de la requête et confirmation chiffrée ;
 *  - un contrôleur `createPanel(env)` qui rend l'onglet dans #j2ha_tab_scenarios. Tout ce qui touche à la page (jQuery,
 *    requête, confirmation, réservation de « Relire Jeedom ») est injecté par `env`.
 *
 * Lecture seule : `getBridgeStatus` (relayé par jeedom2ha.js), champ additif `scenarios` du Lot 4a. Absent = démon ancien.
 * Une seule écriture : `saveScenarioPublication` (ids_to_publish, ids_to_unpublish), qui relit Jeedom elle-même : aucune
 * relecture n'est enchaînée ici, seul l'état du démon est relu ensuite. Aucun identifiant HA n'est deviné : `ha_entity_id`
 * vient du démon. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haScenarios = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
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
  var AJAX_TIMEOUT_MS = 90000; // la route relit Jeedom : même budget client que « Relire Jeedom »

  // --- Lecture ---

  /** Liste des scénarios du démon, ou null si le champ manque (démon ancien, démon injoignable, état illisible). */
  function readList(status) {
    var list = status && typeof status === 'object' ? status.scenarios : null;
    if (!Array.isArray(list)) return null;
    return list.filter(function (s) {
      return s && typeof s === 'object' && typeof s.id === 'number' && isFinite(s.id) && s.id > 0;
    });
  }

  function isPublished(s) { return s.published === true; }

  /** Compte de l'onglet : « publiés/total », suivi de ✱ s'il y a des nouveaux ; null si la liste manque. */
  function tabCount(list) {
    if (!Array.isArray(list)) return null;
    var published = list.filter(isPublished).length;
    var fresh = list.some(function (s) { return s.is_new === true; });
    return published + '/' + list.length + (fresh ? ' ✱' : '');
  }

  // Façons de lancer un scénario (lues dans `manual`, `has_schedule`, `has_trigger`) ; [] si illisible.
  var MODES = [
    { key: 'manual', icon: 'fa-hand-pointer', word: '{{À la main}}', option: '{{Lancé à la main}}' },
    { key: 'schedule', icon: 'fa-calendar-alt', word: '{{Programmé}}', option: '{{Programmé}}' },
    { key: 'trigger', icon: 'fa-bolt', word: '{{Déclenché}}', option: '{{Déclenché}}' },
  ];
  function modeKeys(s) {
    if (s.manual === true) return ['manual'];
    var keys = [];
    if (s.has_schedule === true) keys.push('schedule');
    if (s.has_trigger === true) keys.push('trigger');
    return keys;
  }

  // Puces de filtre, dans l'ordre de l'écran.
  var CHIPS = [
    { key: 'published', cls: 'ok', icon: 'fa-check-circle', word: '{{Publiés}}', title: '{{Publiés comme boutons dans Home Assistant}}',
      test: function (s) { return s.published === true; } },
    { key: 'unpublished', cls: 'off', icon: 'fa-eye-slash', word: '{{Non publiés}}', title: '{{Aucun bouton dans Home Assistant}}',
      test: function (s) { return s.published === false; } },
    { key: 'inactive', cls: 'off', icon: 'fa-pause', word: '{{Inactifs}}', title: '{{Désactivés dans Jeedom}}',
      test: function (s) { return s.is_active !== true; } },
    { key: 'new', cls: 'todo', icon: '', word: '{{Nouveaux}}', title: '{{Apparus depuis votre dernier choix}}',
      test: function (s) { return s.is_new === true; } },
  ];
  function chipOf(key) { return CHIPS.filter(function (c) { return c.key === key; })[0] || null; }

  /** Puces à afficher : nombres non nuls, plus la puce active (pour pouvoir la relâcher). */
  function chipsFor(list, active) {
    return CHIPS.map(function (chip) {
      return { key: chip.key, cls: chip.cls, icon: chip.icon, word: chip.word, title: chip.title, count: list.filter(chip.test).length };
    }).filter(function (chip) { return chip.count > 0 || chip.key === active; });
  }

  /** Groupes présents, triés ; '' (sans groupe) en dernier ; un groupe illisible (null) n'est pas proposé. */
  function groupsOf(list) {
    var seen = {};
    var out = [];
    var none = false;
    list.forEach(function (s) {
      if (s.group === '') { none = true; return; }
      if (typeof s.group !== 'string' || seen[s.group]) return;
      seen[s.group] = true;
      out.push(s.group);
    });
    out.sort(function (a, b) { return a.localeCompare(b, 'fr'); });
    if (none) out.push('');
    return out;
  }

  function fold(text) {
    var t = String(text || '').toLowerCase();
    return typeof t.normalize === 'function' ? t.normalize('NFD').replace(/[̀-ͯ]/g, '') : t;
  }

  /** Filtre : { chip, group (null = tous), mode (null = tous), query }. */
  function filterList(list, filter) {
    var f = filter || {};
    var chip = f.chip ? chipOf(f.chip) : null;
    var query = fold(f.query).trim();
    return list.filter(function (s) {
      if (chip && !chip.test(s)) return false;
      if (f.group !== null && f.group !== undefined && s.group !== f.group) return false;
      if (f.mode && modeKeys(s).indexOf(f.mode) === -1) return false;
      if (query && fold(s.name).indexOf(query) === -1 && fold(s.group).indexOf(query) === -1) return false;
      return true;
    });
  }

  function sortList(list) {
    return list.slice().sort(function (a, b) {
      return String(a.name || '').localeCompare(String(b.name || ''), 'fr') || a.id - b.id;
    });
  }

  // --- Choix en attente : { id: publié voulu }, seulement là où il diffère du choix enregistré ---

  function byId(list) {
    var out = {};
    list.forEach(function (s) { out[s.id] = s; });
    return out;
  }

  function effective(s, pending) {
    return Object.prototype.hasOwnProperty.call(pending, s.id) ? pending[s.id] === true : s.published === true;
  }

  /** Pose « publié voulu » sur `ids` ; une valeur égale au choix enregistré retire l'attente. Rend un nouvel objet. */
  function setPending(list, pending, ids, wanted) {
    var index = byId(list);
    var out = {};
    Object.keys(pending).forEach(function (id) { if (index[id]) out[id] = pending[id]; });
    ids.forEach(function (id) {
      var s = index[id];
      if (!s) return;
      if ((s.published === true) === (wanted === true)) delete out[id];
      else out[id] = wanted === true;
    });
    return out;
  }

  /** Attentes encore valables après une relecture de l'état (celles que le démon reflète déjà disparaissent). */
  function prunePending(list, pending) {
    var index = byId(list);
    var out = {};
    Object.keys(pending).forEach(function (id) {
      if (index[id] && (index[id].published === true) !== (pending[id] === true)) out[id] = pending[id];
    });
    return out;
  }

  /** Corps de `saveScenarioPublication` (listes JSON strictes, triées) ; null si rien n'est à envoyer. */
  function requestFor(list, pending) {
    var index = byId(list);
    var publish = [];
    var unpublish = [];
    Object.keys(pending).forEach(function (id) {
      var s = index[id];
      if (!s || (s.published === true) === (pending[id] === true)) return;
      (pending[id] === true ? publish : unpublish).push(s.id);
    });
    if (publish.length + unpublish.length === 0) return null;
    var asc = function (a, b) { return a - b; };
    publish.sort(asc);
    unpublish.sort(asc);
    return {
      action: 'saveScenarioPublication',
      ids_to_publish: '[' + publish.join(',') + ']',
      ids_to_unpublish: '[' + unpublish.join(',') + ']',
      publish: publish,
      unpublish: unpublish,
    };
  }

  /**
   * Issue de `saveScenarioPublication` : 'ok' (relecture réussie et boutons à jour), 'partial' (choix enregistré, relecture
   * partielle ou boutons de scénario pas tous publiés ou retirés : `operation_result: 'partiel'` ou
   * `scenario_availability_complete: false`), 'failed' (choix enregistré, relecture en échec), 'error' (rien d'enregistré).
   */
  function saveOutcome(data) {
    var res = data && data.result;
    if (!data || data.state !== 'ok' || !res || typeof res !== 'object' || res.saved !== true) return 'error';
    var rescan = res.rescan;
    if (!rescan || typeof rescan !== 'object' || rescan.status !== 'ok' || rescan.operation_result === 'echec') return 'failed';
    if (rescan.operation_result !== 'succes' || rescan.scenario_availability_complete === false) return 'partial';
    return 'ok';
  }

  /** Scénarios dont le bouton dans Home Assistant ne suit pas encore le choix enregistré (`in_ha` lu du démon). */
  function haMismatchIds(list) {
    if (!Array.isArray(list)) return [];
    return list.filter(haWaiting).map(function (s) { return s.id; });
  }

  /**
   * Bouton pas encore à jour dans Home Assistant. Lot 8 (revue P2 #406) : `withdraw_pending` (retrait non confirmé, `in_ha`
   * alors inconnu) et `ha_pending` (publication, disponibilité ou retrait non confirmé par la dernière synchro) priment ;
   * sinon, choix enregistré et `in_ha` en désaccord. Un `in_ha` inconnu (null) n'est jamais lu comme « absent ».
   */
  function haWaiting(s) {
    if (s.withdraw_pending === true || s.ha_pending === true) return true;
    if (s.in_ha === null) return true;
    return (s.published === true) !== (s.in_ha === true);
  }

  function buttonsWord(n) { return n + ' ' + (n > 1 ? '{{boutons}}' : '{{bouton}}'); }

  /** Confirmation chiffrée d'un retrait ; null si rien n'est retiré (pas de confirmation). */
  function removalDialog(request) {
    if (!request || request.unpublish.length === 0) return null;
    var n = request.unpublish.length;
    var lines = ['{{Les automatisations Home Assistant qui les utilisent ne marcheront plus.}}'];
    if (request.publish.length > 0) lines.push(buttonsWord(request.publish.length) + ' ' + (request.publish.length > 1 ? '{{seront aussi ajoutés.}}' : '{{sera aussi ajouté.}}'));
    return { title: '{{Retirer}} ' + buttonsWord(n) + ' {{de Home Assistant ?}}', lines: lines, confirmLabel: '{{Retirer}} (' + n + ')' };
  }

  /** Ligne de confirmation après succès. */
  function successLine(request) {
    var parts = [];
    if (request.publish.length) parts.push(request.publish.length + ' ' + (request.publish.length > 1 ? '{{publiés}}' : '{{publié}}'));
    if (request.unpublish.length) parts.push(request.unpublish.length + ' ' + (request.unpublish.length > 1 ? '{{retirés}}' : '{{retiré}}'));
    return '{{Choix appliqué :}} ' + parts.join(', ');
  }

  /**
   * Suggestion « n scénarios lancés à la main » : scénarios actifs, non publiés, lancés à la main (`manual === true`, jamais
   * un programmé ou un déclenché), qui sont nouveaux, ou tous si aucun scénario n'est publié (installation neuve). Ceux déjà
   * en attente de publication sont retirés. Rend la liste des identifiants (vide = pas de ligne).
   */
  function suggestionIds(list, pending) {
    if (!Array.isArray(list)) return [];
    var p = pending || {};
    var fresh = !list.some(isPublished);
    return list.filter(function (s) {
      return s.published === false && s.manual === true && s.is_active === true && (s.is_new === true || fresh) && p[s.id] !== true;
    }).map(function (s) { return s.id; });
  }

  function suggestionText(n) {
    return {
      line: n + ' ' + (n > 1 ? '{{scénarios lancés à la main}}' : '{{scénario lancé à la main}}'),
      button: n > 1 ? '{{Publier ces}} ' + n : '{{Publier ce scénario}}',
    };
  }

  // --- Contrôleur ---

  function createPanel(env) {
    var $ = env.$;
    var st = {
      filter: { chip: null, group: null, mode: null, query: '' },
      pending: {},
      selected: {},
      busy: false,
      statusSeq: 0, // relectures de l'état du démon observées (une issue partielle attend la suivante)
      result: null, // { kind: 'ok' | 'warn' | 'error', text }
      built: false,
    };

    function list() { return readList(env.status()); }
    function root() { return $('#j2ha_tab_scenarios'); }

    function icon(cls) { return $('<i class="fas" aria-hidden="true"></i>').addClass(cls); }
    function textNode(text) { return env.document.createTextNode(text); }

    function build() {
      var $root = root().empty().addClass('j2ha-v3-sc');
      var $bar = $('<div class="j2ha-v3-chipbar j2ha-v3-sc-bar"></div>');
      $bar.append($('<div class="j2ha-chips j2ha-v3-sc-chips" role="group"></div>').attr('aria-label', '{{Filtrer les scénarios}}'));
      var $group = $('<select class="form-control input-sm j2ha-v3-sc-group"></select>').attr('aria-label', '{{Groupe}}').attr('title', '{{Groupe}}');
      var $mode = $('<select class="form-control input-sm j2ha-v3-sc-mode"></select>').attr('aria-label', '{{Mode}}').attr('title', '{{Mode}}');
      $mode.append($('<option value=""></option>').text('{{Tous les modes}}'));
      MODES.forEach(function (m) { $mode.append($('<option></option>').attr('value', m.key).text(m.option)); });
      var $search = $('<input type="search" class="form-control input-sm j2ha-v3-sc-search">')
        .attr('placeholder', '{{Rechercher}}').attr('aria-label', '{{Rechercher un scénario}}');
      $group.on('change', function () {
        var v = $group.val();
        st.filter.group = v === '*' || v === null ? null : (v === '-' ? '' : String(v).slice(1));
        render();
      });
      $mode.on('change', function () { st.filter.mode = $mode.val() || null; render(); });
      $search.on('input', function () { st.filter.query = String($search.val() || ''); render(); });
      $bar.append($('<div class="j2ha-v3-sc-filters"></div>').append($group, $mode, $search));
      $root.append($bar);
      $root.append($('<div class="j2ha-v3-sc-suggest" hidden></div>'));
      $root.append($('<div class="j2ha-v3-sc-body"></div>'));
      $root.append($('<div class="j2ha-v3-sc-selbar" hidden></div>'));
      $root.append($('<div class="j2ha-v3-sc-foot" hidden></div>'));
      $root.append($('<div class="j2ha-v3-sc-result" role="status" aria-live="polite"></div>'));
      st.built = true;
    }

    function renderGroups(items) {
      var $group = root().find('.j2ha-v3-sc-group');
      var groups = groupsOf(items);
      var current = st.filter.group;
      if (current !== null && groups.indexOf(current) === -1) { current = null; st.filter.group = null; }
      $group.empty().append($('<option value="*"></option>').text('{{Tous les groupes}}'));
      groups.forEach(function (g) {
        $group.append($('<option></option>').attr('value', g === '' ? '-' : 'g' + g).text(g === '' ? '{{Sans groupe}}' : g));
      });
      $group.val(current === null ? '*' : (current === '' ? '-' : 'g' + current));
      $group.prop('hidden', groups.length < 2 && current === null);
    }

    function renderChips(items) {
      var $chips = root().find('.j2ha-v3-sc-chips').empty();
      var focused = env.document.activeElement;
      var focusKey = focused && focused.classList && focused.classList.contains('j2ha-v3-sc-chip') ? focused.getAttribute('data-filter') : null;
      chipsFor(items, st.filter.chip).forEach(function (chip) {
        var $chip = $('<button type="button" class="j2ha-chip-filter j2ha-v3-chip j2ha-v3-sc-chip"></button>')
          .addClass('j2ha-v3-sc-chip-' + chip.cls).attr('data-filter', chip.key)
          .attr('aria-pressed', st.filter.chip === chip.key ? 'true' : 'false')
          .attr('aria-controls', 'j2ha_scTable').attr('title', chip.title)
          .attr('aria-label', chip.count + ' ' + chip.word + ' : ' + chip.title);
        if (chip.icon) $chip.append(icon(chip.icon));
        $chip.append($('<b class="j2ha-v3-chip-n"></b>').text(chip.key === 'new' ? '✱ ' + chip.count : String(chip.count)))
          .append(textNode(' ')).append($('<span class="j2ha-v3-chip-word"></span>').text(chip.word));
        $chip.on('click', function () {
          st.filter.chip = st.filter.chip === chip.key ? null : chip.key;
          render();
        });
        $chips.append($chip);
      });
      if (focusKey) $chips.find('.j2ha-v3-sc-chip[data-filter="' + focusKey + '"]').focus();
    }

    function renderSuggestion(items) {
      var $box = root().find('.j2ha-v3-sc-suggest').empty();
      var ids = suggestionIds(items, st.pending);
      $box.prop('hidden', ids.length === 0);
      if (ids.length === 0) return;
      var text = suggestionText(ids.length);
      var $btn = $('<button type="button" class="btn btn-default btn-xs j2ha-v3-sc-suggest-btn"></button>').text(text.button)
        .attr('title', '{{Prépare la publication ; rien n’est envoyé avant « Appliquer »}}');
      $btn.on('click', function () { preselectSuggested(); });
      $box.append(icon('fa-hand-pointer'), textNode(' ' + text.line + ' → '), $btn);
    }

    function modeCell(s) {
      var $cell = $('<td class="j2ha-v3-sc-modecell"></td>');
      var keys = modeKeys(s);
      if (keys.length === 0) {
        $cell.append($('<span class="j2ha-v3-sc-muted"></span>').text('—').attr('title', '{{Mode illisible}}'));
        return $cell;
      }
      keys.forEach(function (key) {
        var m = MODES.filter(function (x) { return x.key === key; })[0];
        $cell.append(infoTip($('<span class="j2ha-v3-sc-tag"></span>').addClass('j2ha-v3-sc-mode-' + key).attr('title', m.option).append(icon(m.icon), textNode(' ' + m.word))));
      });
      return $cell;
    }

    function haCell(s) {
      var $cell = $('<td class="j2ha-v3-sc-hacell"></td>');
      // État réel côté Home Assistant (`in_ha`), pas seulement le choix enregistré.
      if (haWaiting(s)) {
        return $cell.append(infoTip($('<span class="j2ha-v3-sc-tag j2ha-v3-sc-hawait"></span>')
          .attr('title', s.published !== true ? '{{Retiré de vos choix, mais le retrait n’est pas encore confirmé}}'
            : (s.in_ha === true ? '{{Mise à jour pas encore confirmée par Home Assistant}}' : '{{Choisi, mais le bouton n’est pas encore dans Home Assistant}}'))
          .append($('<span aria-hidden="true">◷</span>'), textNode(' {{En attente de Home Assistant}}'))));
      }
      if (s.published !== true) return $cell.append($('<span class="j2ha-v3-sc-muted"></span>').text('—').attr('title', '{{Pas publié}}'));
      if (s.is_active !== true) {
        return $cell.append(infoTip($('<span class="j2ha-v3-sc-tag j2ha-v3-sc-muted j2ha-v3-sc-unavail"></span>')
          .attr('title', '{{Le bouton existe, mais ne fait rien tant que le scénario est inactif}}')
          .append(icon('fa-ban'), textNode(' {{Indisponible}}'))));
      }
      if (typeof s.ha_entity_id !== 'string' || s.ha_entity_id === '') {
        return $cell.append($('<span class="j2ha-v3-sc-muted"></span>').text('—').attr('title', '{{Identifiant pas encore connu}}'));
      }
      var $code = $('<code class="j2ha-v3-sc-entity"></code>').text(s.ha_entity_id);
      var $copy = $('<button type="button" class="j2ha-v2-link j2ha-v2-copy j2ha-v3-sc-copy"></button>')
        .attr('title', '{{Copier l’identifiant}}').attr('aria-label', '{{Copier l’identifiant}}').append(icon('fa-copy'));
      $copy.on('click', function () { if (typeof env.copy === 'function') env.copy(s.ha_entity_id, $copy); });
      return $cell.append($code, $copy);
    }

    function row(s) {
      var on = effective(s, st.pending);
      var waiting = Object.prototype.hasOwnProperty.call(st.pending, s.id);
      var $tr = $('<tr class="j2ha-v3-sc-row"></tr>').attr('data-id', String(s.id)).toggleClass('is-pending', waiting).toggleClass('is-inactive', s.is_active !== true);
      var $check = $('<input type="checkbox" class="j2ha-v3-sc-check">').prop('checked', !!st.selected[s.id])
        .attr('aria-label', '{{Sélectionner}} ' + s.name);
      $check.on('change', function () {
        if ($check.prop('checked')) st.selected[s.id] = true;
        else delete st.selected[s.id];
        render();
      });
      $tr.append($('<td class="j2ha-v3-sc-cb"></td>').append($check));
      var $name = $('<td class="j2ha-v3-sc-namecell"></td>').append($('<span class="j2ha-v3-sc-name"></span>').text(s.name || ('#' + s.id)));
      if (s.is_new === true) $name.append(infoTip($('<span class="j2ha-v3-sc-new"></span>').attr('title', '{{Apparu depuis votre dernier choix}}').text('✱ {{nouveau}}')));
      if (typeof s.group === 'string' && s.group !== '') $name.append($('<span class="j2ha-v3-sc-group-tag"></span>').text(s.group));
      $tr.append($name);
      $tr.append(modeCell(s));
      $tr.append($('<td class="j2ha-v3-sc-jeedom"></td>').append(s.is_active === true
        ? $('<span class="j2ha-v3-sc-tag j2ha-v3-sc-active"></span>').append(icon('fa-play'), textNode(' {{Actif}}'))
        : $('<span class="j2ha-v3-sc-tag j2ha-v3-sc-muted"></span>').append(icon('fa-pause'), textNode(' {{Inactif}}'))));
      $tr.append(haCell(s));
      var $switch = $('<button type="button" class="j2ha-v3-sc-switch" role="switch"></button>')
        .attr('aria-checked', on ? 'true' : 'false').attr('aria-label', '{{Publier}} ' + s.name)
        .attr('title', on ? '{{Publié : cliquer pour ne plus publier}}' : '{{Pas publié : cliquer pour publier}}')
        .prop('disabled', st.busy);
      $switch.on('click', function () {
        st.pending = setPending(list() || [], st.pending, [s.id], !on);
        st.result = null;
        render();
        root().find('.j2ha-v3-sc-row[data-id="' + s.id + '"] .j2ha-v3-sc-switch').focus();
      });
      var $pub = $('<td class="j2ha-v3-sc-pub"></td>').append($switch);
      if (waiting) $pub.append($('<span class="j2ha-v3-sc-wait" title="{{À appliquer}}"></span>').append($('<span aria-hidden="true">◷</span>'), $('<span class="j2ha-v3-sr"></span>').text('{{À appliquer}}')));
      $tr.append($pub);
      return $tr;
    }

    function renderTable(items, shown) {
      var $body = root().find('.j2ha-v3-sc-body').empty();
      if (shown.length === 0) {
        var $none = $('<div class="j2ha-v3-sc-empty"></div>').text('{{Aucun scénario ne correspond}} ');
        var $clear = $('<button type="button" class="btn btn-link btn-xs j2ha-v3-sc-clear"></button>').text('{{Effacer les filtres}}');
        $clear.on('click', function () {
          st.filter = { chip: null, group: null, mode: null, query: '' };
          root().find('.j2ha-v3-sc-search').val('');
          root().find('.j2ha-v3-sc-mode').val('');
          render();
        });
        $body.append($none.append($clear));
        return;
      }
      var $table = $('<table class="table table-condensed j2ha-v3-sc-table" id="j2ha_scTable"></table>');
      var allSel = shown.every(function (s) { return st.selected[s.id]; });
      var someSel = shown.some(function (s) { return st.selected[s.id]; });
      var $all = $('<input type="checkbox" class="j2ha-v3-sc-all">').prop('checked', allSel).attr('aria-label', '{{Tout sélectionner}}').attr('title', '{{Tout sélectionner}}');
      var node = $all.get(0);
      if (node) node.indeterminate = someSel && !allSel;
      $all.on('change', function () {
        var check = $all.prop('checked');
        shown.forEach(function (s) { if (check) st.selected[s.id] = true; else delete st.selected[s.id]; });
        render();
        root().find('.j2ha-v3-sc-all').focus();
      });
      var $head = $('<tr></tr>').append($('<th class="j2ha-v3-sc-cb"></th>').append($all));
      ['{{Scénario}}', '{{Mode}}', '{{Jeedom}}', '{{Dans Home Assistant}}', '{{Publier}}'].forEach(function (label, i) {
        $head.append($('<th></th>').addClass(['', 'j2ha-v3-sc-modecell', 'j2ha-v3-sc-jeedom', 'j2ha-v3-sc-hacell', 'j2ha-v3-sc-pub'][i]).text(label));
      });
      var $tbody = $('<tbody></tbody>');
      sortList(shown).forEach(function (s) { $tbody.append(row(s)); });
      $table.append($('<thead></thead>').append($head), $tbody);
      $body.append($table);
    }

    function selectedIds(items) {
      var index = byId(items);
      return Object.keys(st.selected).filter(function (id) { return index[id]; }).map(Number);
    }

    function renderSelbar(items) {
      var ids = selectedIds(items);
      var $bar = root().find('.j2ha-v3-sc-selbar').empty();
      $bar.prop('hidden', ids.length === 0);
      if (ids.length === 0) return;
      var n = ids.length;
      $bar.append($('<b class="j2ha-v3-sc-selcount"></b>').text(n + ' ' + (n > 1 ? '{{sélectionnés}}' : '{{sélectionné}}')));
      var $pub = $('<button type="button" class="btn btn-default btn-sm j2ha-v3-sc-selpub"></button>').append(icon('fa-check'), textNode(' {{Publier}} (' + n + ')'));
      var $unpub = $('<button type="button" class="btn btn-default btn-sm j2ha-v3-sc-selunpub"></button>').append(icon('fa-eye-slash'), textNode(' {{Ne pas publier}} (' + n + ')'));
      var mark = function (wanted) {
        st.pending = setPending(items, st.pending, ids, wanted);
        st.selected = {};
        st.result = null;
        render();
      };
      $pub.prop('disabled', st.busy).on('click', function () { mark(true); });
      $unpub.prop('disabled', st.busy).on('click', function () { mark(false); });
      var $clear = $('<button type="button" class="btn btn-default btn-sm j2ha-v3-sc-selclear" aria-label="{{Désélectionner}}" title="{{Désélectionner}}"></button>').append(icon('fa-times'));
      $clear.on('click', function () { st.selected = {}; render(); });
      $bar.append($pub, $unpub, $('<span class="j2ha-v3-sc-spacer"></span>'), $clear);
    }

    function renderFoot(items) {
      var request = requestFor(items, st.pending);
      var $foot = root().find('.j2ha-v3-sc-foot').empty();
      $foot.prop('hidden', !request && !st.busy);
      if (!request && !st.busy) return;
      var n = request ? request.publish.length + request.unpublish.length : 0;
      var ready = typeof env.ready === 'function' ? env.ready() : { ok: true };
      var $cancel = $('<button type="button" class="btn btn-default btn-sm j2ha-v3-sc-cancel"></button>').text('{{Annuler}}')
        .attr('title', '{{Oublier les changements non appliqués}}').prop('disabled', st.busy);
      $cancel.on('click', function () { st.pending = {}; render(); });
      var $apply = $('<button type="button" class="btn btn-primary btn-sm j2ha-v3-sc-apply"></button>');
      if (st.busy) $apply.append($('<i class="fas fa-spinner fa-spin" aria-hidden="true"></i>'), textNode(' {{Application…}}'));
      else $apply.append(icon('fa-upload'), textNode(' {{Appliquer}} (' + n + ')'));
      $apply.prop('disabled', st.busy || !ready.ok).attr('title', ready.ok ? n + ' ' + (n > 1 ? '{{changements à envoyer à Home Assistant}}' : '{{changement à envoyer à Home Assistant}}') : ready.reason);
      $apply.on('click', apply);
      $foot.append($('<span class="j2ha-v3-sc-spacer"></span>'), $cancel, $apply);
    }

    function renderResult(items) {
      var $line = root().find('.j2ha-v3-sc-result').empty().removeAttr('data-kind');
      var result = st.result;
      if (!result) return;
      if (result.kind === 'partial') {
        // Avant la relecture de l'état qui suit l'enregistrement : le nombre demandé ; après : les boutons réellement en retard.
        var fresh = st.statusSeq > result.seq;
        var n = fresh ? haMismatchIds(items).length : result.request.publish.length + result.request.unpublish.length;
        if (fresh && n === 0) {
          st.result = result = { kind: 'ok', text: successLine(result.request) };
        } else {
          var request = result.request;
          var $retry = $('<button type="button" class="btn btn-default btn-xs j2ha-v3-sc-retry"></button>').text('{{Réessayer}}')
            .attr('title', '{{Renvoie le même choix et relit Jeedom}}').prop('disabled', st.busy);
          $retry.on('click', function () { send(request); });
          $line.attr('data-kind', 'warn').append(icon('fa-exclamation-triangle'),
            textNode(' {{Choix enregistré}} · ' + buttonsWord(n) + ' {{pas encore à jour dans Home Assistant}} · '), $retry);
          return;
        }
      }
      var icons = { ok: 'fa-check-circle', warn: 'fa-exclamation-triangle', error: 'fa-exclamation-triangle' };
      $line.attr('data-kind', result.kind).append(icon(icons[result.kind]), textNode(' ' + result.text));
    }

    function renderState(kind) {
      var $root = root().empty().removeClass('j2ha-v3-sc');
      st.built = false;
      if (kind === 'loading') return;
      var $box = $('<div class="j2ha-v3-sc-state"></div>').attr('data-kind', kind);
      if (kind === 'empty') {
        $box.append(icon('fa-film'), textNode(' {{Aucun scénario dans Jeedom}}'));
      } else {
        $box.append(icon('fa-question-circle'), textNode(' {{Liste indisponible}} · '));
        var $reread = $('<button type="button" class="btn btn-default btn-xs j2ha-v3-sc-reread"></button>').text('{{Relire}}')
          .attr('title', '{{Relire l’état du démon}}');
        $reread.on('click', function () { if (typeof env.refreshStatus === 'function') env.refreshStatus(); });
        $box.append($reread);
      }
      $root.append($box);
    }

    function render() {
      if (root().length === 0) return;
      var status = env.status();
      if (status === undefined) { renderState('loading'); return; }
      var items = readList(status);
      if (items === null) { renderState('unavailable'); return; }
      if (items.length === 0) { renderState('empty'); return; }
      st.pending = prunePending(items, st.pending);
      if (!st.built) build();
      renderGroups(items);
      renderChips(items);
      renderSuggestion(items);
      renderTable(items, filterList(items, st.filter));
      renderSelbar(items);
      renderFoot(items);
      renderResult(items);
    }

    function preselectSuggested() {
      var items = list();
      if (!items) return [];
      var ids = suggestionIds(items, st.pending);
      st.pending = setPending(items, st.pending, ids, true);
      st.result = null;
      if (typeof env.selectTab === 'function') env.selectTab();
      render();
      return ids;
    }

    function finish(result) {
      st.busy = false;
      st.result = result;
      if (typeof env.release === 'function') env.release();
      render();
    }

    function send(request) {
      var reserved = typeof env.reserve === 'function' ? env.reserve() : true;
      if (!reserved) {
        st.result = { kind: 'warn', text: '{{Une opération est déjà en cours : réessayez dans un instant.}}' };
        render();
        return;
      }
      st.busy = true;
      st.result = null;
      render();
      env.post({ action: request.action, ids_to_publish: request.ids_to_publish, ids_to_unpublish: request.ids_to_unpublish }, {
        success: function (data) {
          var outcome = saveOutcome(data);
          if (outcome === 'error') {
            var why = data && typeof data.result === 'string' && data.result ? data.result : '{{Le choix n’a pas été enregistré.}}';
            finish({ kind: 'error', text: why });
            return;
          }
          if (outcome === 'ok') finish({ kind: 'ok', text: successLine(request) });
          else if (outcome === 'partial') finish({ kind: 'partial', request: request, seq: st.statusSeq });
          else finish({ kind: 'warn', text: '{{Choix enregistré, mais la relecture a échoué : lancez « Relire Jeedom ».}}' });
          if (typeof env.afterSave === 'function') env.afterSave();
        },
        error: function () {
          finish({ kind: 'error', text: '{{Erreur de communication : relisez la liste avant de recommencer.}}' });
          if (typeof env.afterSave === 'function') env.afterSave();
        },
      });
    }

    function apply() {
      if (st.busy) return;
      var items = list();
      var request = items ? requestFor(items, st.pending) : null;
      if (!request) return;
      var dialog = removalDialog(request);
      if (!dialog) { send(request); return; }
      env.confirm(dialog, function () { send(request); });
    }

    return {
      render: render,
      /** Une réponse de getBridgeStatus vient d'arriver. */
      statusChanged: function () { st.statusSeq += 1; render(); },
      apply: apply,
      preselectSuggested: preselectSuggested,
      /** Nombre de scénarios que la suggestion présélectionnerait (0 = pas de suggestion). */
      suggestionCount: function () { return suggestionIds(list(), st.pending).length; },
      pending: function () { return Object.assign({}, st.pending); },
      state: function () { return { busy: st.busy, result: st.result, filter: Object.assign({}, st.filter) }; },
    };
  }

  var api = {
    AJAX_URL: AJAX_URL,
    MODES: MODES,
    CHIPS: CHIPS,
    readList: readList,
    tabCount: tabCount,
    modeKeys: modeKeys,
    chipsFor: chipsFor,
    groupsOf: groupsOf,
    filterList: filterList,
    sortList: sortList,
    setPending: setPending,
    prunePending: prunePending,
    requestFor: requestFor,
    removalDialog: removalDialog,
    successLine: successLine,
    saveOutcome: saveOutcome,
    haMismatchIds: haMismatchIds,
    haWaiting: haWaiting,
    suggestionIds: suggestionIds,
    suggestionText: suggestionText,
    createPanel: createPanel,
  };

  // --- Page du plugin ---
  if (typeof window !== 'undefined' && typeof window.$ === 'function' && typeof document !== 'undefined' && !(typeof module === 'object' && module.exports)) {
    window.$(function () {
      var $ = window.$;
      if ($('#j2ha_tab_scenarios').length === 0) return;
      var reservation = null;
      var panel = createPanel({
        $: $,
        document: document,
        // `undefined` tant que jeedom2ha.js n'a pas encore lu l'état du démon.
        status: function () { return window.jeedom2haLastBridgeStatus; },
        refreshStatus: function () { if (typeof window.refreshBridgeStatus === 'function') window.refreshBridgeStatus(); },
        selectTab: function () {
          var page = window.Jeedom2haOverviewPage;
          if (page && typeof page.selectTab === 'function') page.selectTab('scenarios');
        },
        ready: function () {
          if (window.jeedom2haRescanInProgress === true) return { ok: false, reason: '{{Une opération est déjà en cours.}}' };
          if (typeof window.isHABridgeAvailable === 'function' && !window.isHABridgeAvailable(window.jeedom2haLastBridgeStatus || null)) {
            return { ok: false, reason: '{{Démon ou MQTT indisponible.}}' };
          }
          return { ok: true };
        },
        // Même réservation que « Relire Jeedom » : aucune autre opération ne part pendant l'enregistrement et sa relecture.
        reserve: function () {
          if (window.jeedom2haRescanInProgress === true) return false;
          var $rescan = $('#bt_rescanTopology');
          var snapshot = $rescan.length && typeof window.setHaActionPendingState === 'function'
            ? window.setHaActionPendingState($rescan, '{{Enregistrement…}}') : null;
          var owner = {};
          window.jeedom2haRescanInProgress = true;
          window.jeedom2haRescanOwner = owner;
          if (typeof window.applyHAGating === 'function') window.applyHAGating(window.jeedom2haLastBridgeStatus || null);
          reservation = { owner: owner, snapshot: snapshot, $rescan: $rescan };
          return true;
        },
        release: function () {
          var r = reservation;
          reservation = null;
          if (!r) return;
          if (typeof window.releaseTopologyRescanReservation === 'function') {
            window.releaseTopologyRescanReservation(r.$rescan, r.snapshot, r.owner);
          } else if (window.jeedom2haRescanOwner === r.owner) {
            window.jeedom2haRescanOwner = null;
            window.jeedom2haRescanInProgress = false;
          }
        },
        post: function (data, handlers) {
          $.ajax({ type: 'POST', url: AJAX_URL, data: data, dataType: 'json', timeout: AJAX_TIMEOUT_MS, success: handlers.success, error: handlers.error });
        },
        // La route a déjà relu Jeedom : on relit seulement l'état du démon, puis les chiffres des équipements.
        afterSave: function () {
          if (typeof window.refreshBridgeStatus === 'function') window.refreshBridgeStatus();
          if (typeof window.j2haNotifyStatesChanged === 'function') window.j2haNotifyStatesChanged();
        },
        confirm: function (dialog, onConfirm) {
          var esc = function (t) { return $('<span></span>').text(String(t)).html(); };
          var message = dialog.lines.map(function (line) { return '<p>' + esc(line) + '</p>'; }).join('');
          if (typeof window.confirmHaPublishAction === 'function') {
            window.confirmHaPublishAction(esc(dialog.title), message, dialog.confirmLabel, onConfirm, function () {}, 'btn-danger');
          } else if (window.confirm(dialog.title)) {
            onConfirm();
          }
        },
        copy: function (value, $button) {
          var clipboard = window.navigator && window.navigator.clipboard;
          if (!clipboard || typeof clipboard.writeText !== 'function') return;
          try {
            clipboard.writeText(value).then(function () { $button.attr('title', '{{Copié}}').addClass('is-copied'); }, function () {});
          } catch (e) {
            // Presse-papiers refusé : l'identifiant reste lisible et sélectionnable.
          }
        },
      });
      window.Jeedom2haScenariosPage = panel;
      // Chaque réponse de getBridgeStatus (lue par jeedom2ha.js) met la liste à jour ; aucune requête ajoutée.
      $(document).on('ajaxComplete', function (_event, _xhr, settings) {
        var data = settings && settings.data;
        if (typeof data === 'string' && data.indexOf('action=getBridgeStatus') !== -1) panel.statusChanged();
      });
      panel.render();
    });
  }

  return api;
}));
