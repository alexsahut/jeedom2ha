// Front v2 — Lot 1 : démarrage guidé (E1) et « Vérifier l'installation… » (E7).
//
// Deux parties :
//  - des fonctions PURES (aucun DOM) : `computeSteps`, `shouldShow`, `checkInstall`, `summaryFrom`, libellés de la barre
//    d'état ; elles sont testées sous node (tests/unit/test_front_v2_guide.node.test.js) ;
//  - un contrôleur `createGuide(env)` qui rend le guide dans #j2ha_v2_guide et la boîte de contrôle ; tout ce qui touche
//    à la page (jQuery, bootbox, stockage local, actions) est injecté par `env` (jeedom2ha.js dans la page, un faux DOM
//    dans les tests).
//
// Contrat démon (Lot 3, additif) : `status.ha.birth_seen_at` et `status.publication.*` peuvent manquer. Repli : l'étape 2
// se coche à la main, l'item « Home Assistant » est masqué, aucun compteur de scénarios.
//
// Aucune écriture n'est créée ici : « Publier dans Home Assistant » réutilise la relecture existante (scanTopology),
// fournie par `env.actions.publish`.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haGuide = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // Clés du stockage local (préférences de ce navigateur seulement ; illisible = valeurs par défaut).
  var STORAGE_KEYS = {
    dismissed: 'jeedom2ha.guide.dismissed',
    haSeen: 'jeedom2ha.guide.haSeen',
    choice: 'jeedom2ha.guide.choice',
    published: 'jeedom2ha.guide.published',
  };

  var STEP_KEYS = ['broker', 'ha', 'choice', 'publish'];

  function pad(n) { return ('0' + n).slice(-2); }

  /** « 13/11 21:04 » (heure locale du navigateur) ; chaîne vide si la date est illisible. */
  function shortDate(iso) {
    if (typeof iso !== 'string' || iso === '') return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    return pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  function brokerState(status) {
    if (!status || typeof status !== 'object') return null;
    var info = status.broker || status.mqtt || {};
    return typeof info.state === 'string' ? info.state : 'unconfigured';
  }

  function bridgeUp(status) {
    return !!(status && status.daemon && brokerState(status) === 'connected');
  }

  /** Bloc `ha` du démon s'il porte le champ `birth_seen_at` (Lot 3) ; sinon null (repli). */
  function haInfo(status) {
    var ha = status && typeof status === 'object' ? status.ha : null;
    if (!ha || typeof ha !== 'object' || !Object.prototype.hasOwnProperty.call(ha, 'birth_seen_at')) return null;
    return { seen_at: typeof ha.birth_seen_at === 'string' && ha.birth_seen_at !== '' ? ha.birth_seen_at : null };
  }

  function publicationInfo(status) {
    var p = status && typeof status === 'object' ? status.publication : null;
    if (!p || typeof p !== 'object') return null;
    var num = function (v) { return typeof v === 'number' && isFinite(v) && v >= 0 ? v : null; };
    return { equipments: num(p.equipments_published), entities: num(p.entities_published), scenarios: num(p.scenarios_published) };
  }

  /** Item « Home Assistant » de la barre d'état : masqué si le démon ne fournit pas le champ, ou s'il est arrêté. */
  function haBarItem(status) {
    var ha = haInfo(status);
    if (!ha || !status.daemon) return { visible: false, text: '', seen: false };
    if (ha.seen_at) {
      var at = shortDate(ha.seen_at);
      var parts = at.split(' ');
      return { visible: true, seen: true, text: parts.length === 2 ? '{{Vu le}} ' + parts[0] + ' {{à}} ' + parts[1] : '{{Vu}}' };
    }
    return { visible: true, seen: false, text: '{{Pas encore vu}}' };
  }

  var HA_TOOLTIP = '{{Home Assistant se signale sur le broker quand il démarre. S\'il n\'a pas redémarré depuis l\'installation, c\'est normal.}}';

  var RESULT_WORDS = { succes: '{{Réussie}}', partiel: '{{Partielle}}', echec: '{{Échouée}}' };

  /** Fusion « Dernière relecture » + « Dernière opération » : vraie quand la dernière opération EST la relecture. */
  function relectureFusion(status) {
    var op = status && status.derniere_operation_resultat;
    var date = status ? shortDate(status.derniere_synchro_terminee) : '';
    if (!date) return { text: '', fused: false };
    if (op && typeof op === 'object' && op.intention === 'sync' && RESULT_WORDS[op.resultat]) {
      return { text: date + ' · ' + RESULT_WORDS[op.resultat], fused: true };
    }
    return { text: date, fused: false };
  }

  /** Résumé de la dernière lecture des états (page.snapshot() de jeedom2ha_overview.js) ; null si aucune lecture valide. */
  function summaryFrom(snapshot, jeedomEquipments) {
    var out = { jeedom_equipments: typeof jeedomEquipments === 'number' ? jeedomEquipments : null, read: false, published: 0, blocked: 0, to_apply: 0, other: 0, total: 0, names: [] };
    var overview = snapshot && snapshot.view && snapshot.view.overview;
    if (!overview || !overview.counts) return out;
    out.read = true;
    out.published = overview.counts.published || 0;
    out.blocked = overview.counts.blocked || 0;
    out.to_apply = overview.counts.to_apply || 0;
    out.other = overview.counts.other || 0;
    out.total = overview.total || 0;
    (overview.rooms || []).forEach(function (room) {
      (room.equipments || []).forEach(function (row) {
        if (row.state === 'published' && out.names.length < 3) out.names.push(row.eq_name);
      });
    });
    return out;
  }

  function synced(status, readState, local) {
    return !!((readState && readState.kind === 'ok') || (status && status.derniere_synchro_terminee) || (local && local.published));
  }

  /**
   * Les quatre étapes de E1. `status` : réponse de getBridgeStatus (`undefined` = pas encore lue, `null` = illisible) ;
   * `readState` : { kind } de la lecture des états ; `summary` : summaryFrom() ; `local` : préférences du navigateur.
   * État d'une étape : `done`, `current` (la première non faite), `blocked` (les suivantes), `error` (la première non faite,
   * avec une cause). Une étape faite reste faite, même si une précédente ne l'est plus.
   */
  function computeSteps(status, readState, summary, local) {
    var loc = local || {};
    var sum = summary || {};
    var ha = haInfo(status);
    var isSynced = synced(status, readState, loc);
    var broker = brokerState(status);

    var s1 = { key: 'broker', number: 1, done: bridgeUp(status), cause: '', remedy: 'config' };
    if (!s1.done) {
      if (status === null) s1.cause = '{{Jeedom n\'a pas pu lire l\'état du démon.}}';
      else if (status && !status.daemon) s1.cause = '{{Le démon est arrêté.}}';
      else if (broker === 'disconnected') s1.cause = '{{Le broker MQTT ne répond pas.}}';
      else if (broker === 'connecting' || broker === 'reconnecting') s1.note = '{{Connexion au broker en cours…}}';
    }
    var s2 = { key: 'ha', number: 2, done: !!(ha && ha.seen_at) || !!loc.haSeen, auto: !!(ha && ha.seen_at), manual: !(ha && ha.seen_at), ha_known: !!ha };
    var s3 = { key: 'choice', number: 3, done: !!loc.choice || isSynced };
    var s4 = { key: 'publish', number: 4, done: isSynced, empty: sum.jeedom_equipments === 0 };
    if (s4.empty && !s4.done) s4.cause = '{{Jeedom ne contient encore aucun équipement à publier. Ajoutez des équipements dans Jeedom, puis revenez ici.}}';

    var steps = [s1, s2, s3, s4];
    var firstOpen = -1;
    steps.forEach(function (step, index) {
      if (step.done) { step.state = 'done'; return; }
      if (firstOpen === -1) {
        firstOpen = index;
        step.state = step.cause ? 'error' : 'current';
      } else {
        step.state = 'blocked';
        step.waitFor = steps[firstOpen].number;
      }
    });
    return { steps: steps, current: firstOpen, complete: firstOpen === -1, synced: isSynced };
  }

  /**
   * Le guide s'affiche seul quand rien n'a encore été publié : jamais relu, ou démon / broker indisponible sur une
   * installation que ce navigateur n'a jamais vue publiée. Jamais avant la première lecture des états ; jamais si
   * l'utilisateur a choisi « Ne plus afficher ».
   */
  function shouldShow(status, readState, local) {
    var loc = local || {};
    if (loc.dismissed) return false;
    var kind = readState && readState.kind;
    if (!kind) return false;
    if (kind === 'ok') return false;
    if (kind === 'never_synced') return true;
    if (status === undefined) return false;
    var down = status === null || !bridgeUp(status);
    return down && !loc.published && !(status && status.derniere_synchro_terminee);
  }

  /**
   * Contrôles de E7, dans l'ordre. État : `ok`, `fail` (le premier arrête la liste : les suivants passent à `wait`),
   * `warn` (à vérifier, n'arrête pas), `skip` (non vérifiable avec ce démon : non affiché).
   */
  function checkInstall(status, readState, summary) {
    var sum = summary || {};
    var list = [];
    var broker = brokerState(status);
    var daemon = { key: 'daemon', title: '{{Le démon tourne}}', state: 'ok', detail: '' };
    if (status === null || status === undefined) {
      daemon.state = 'fail';
      daemon.detail = '{{Jeedom n\'a pas pu lire l\'état du démon.}}';
      daemon.remedy = { action: 'config', label: '{{Ouvrir la configuration du plugin}}' };
    } else if (!status.daemon) {
      daemon.state = 'fail';
      daemon.detail = '{{Le démon est arrêté.}}';
      daemon.remedy = { action: 'config', label: '{{Ouvrir la configuration du plugin}}' };
    }
    list.push(daemon);

    var mqtt = { key: 'broker', title: '{{Le broker MQTT répond}}', state: 'ok', detail: '' };
    if (broker === 'connected') {
      var info = (status.broker || status.mqtt || {});
      mqtt.detail = info.broker ? '{{Connecté à}} ' + info.broker : '{{Connecté}}';
    } else {
      mqtt.state = 'fail';
      if (broker === 'disconnected') mqtt.detail = '{{Le broker MQTT ne répond pas : vérifiez son adresse, son port et l\'utilisateur MQTT.}}';
      else if (broker === 'connecting' || broker === 'reconnecting') mqtt.detail = '{{Connexion au broker en cours : réessayez dans quelques secondes.}}';
      else mqtt.detail = '{{Aucun broker MQTT n\'est configuré.}}';
      mqtt.remedy = { action: 'config', label: '{{Ouvrir la configuration MQTT}}' };
    }
    list.push(mqtt);

    var ha = haInfo(status);
    var haCheck = { key: 'ha', title: '{{Home Assistant a été vu sur ce broker}}', state: 'skip', detail: '' };
    if (ha && ha.seen_at) {
      haCheck.state = 'ok';
      haCheck.detail = haBarItem(status).text;
    } else if (ha) {
      haCheck.state = 'warn';
      haCheck.detail = HA_TOOLTIP;
      haCheck.help = true;
    }
    list.push(haCheck);

    var reread = { key: 'reread', title: '{{Dernière relecture réussie}}', state: 'ok', detail: '' };
    var op = status && status.derniere_operation_resultat;
    var date = status ? shortDate(status.derniere_synchro_terminee) : '';
    if (!date) {
      reread.state = 'fail';
      reread.detail = '{{Aucune relecture pour l\'instant.}}';
      reread.remedy = { action: 'rescan', label: '{{Relire Jeedom}}' };
    } else if (op && typeof op === 'object' && op.intention === 'sync' && op.resultat === 'partiel') {
      reread.state = 'fail';
      reread.detail = date + ' · ' + '{{Partielle : des équipements n\'ont pas pu être publiés.}}';
      reread.remedy = { action: 'blocked', label: '{{Voir lesquels}}' };
    } else if (op && typeof op === 'object' && op.intention === 'sync' && op.resultat === 'echec') {
      reread.state = 'fail';
      reread.detail = date + ' · ' + '{{Échouée.}}';
      reread.remedy = { action: 'rescan', label: '{{Relire Jeedom}}' };
    } else {
      reread.detail = date;
    }
    list.push(reread);

    var blocked = { key: 'blocked', title: '{{Équipements bloqués}}', state: 'skip', detail: '' };
    if (sum.read) {
      if (sum.blocked > 0) {
        blocked.state = 'warn';
        blocked.title = sum.blocked > 1 ? sum.blocked + ' {{équipements bloqués}}' : '{{1 équipement bloqué}}';
        blocked.detail = '{{Ils ne sont pas publiés : chaque fiche dit pourquoi.}}';
        blocked.remedy = { action: 'blocked', label: '{{Voir les équipements bloqués}}' };
      } else {
        blocked.state = 'ok';
        blocked.title = '{{Aucun équipement bloqué}}';
      }
    }
    list.push(blocked);

    var stopped = false;
    list.forEach(function (check) {
      if (check.state === 'skip') return;
      if (stopped) { check.state = 'wait'; return; }
      if (check.state === 'fail') { check.open = true; stopped = true; }
    });
    return list.filter(function (check) { return check.state !== 'skip'; });
  }

  // --- Contrôleur (DOM injecté) ---

  function readLocal(storage) {
    var get = function (key) {
      try { return storage && typeof storage.getItem === 'function' ? storage.getItem(key) : null; } catch (e) { return null; }
    };
    return {
      dismissed: get(STORAGE_KEYS.dismissed) === '1',
      haSeen: get(STORAGE_KEYS.haSeen) === '1',
      choice: get(STORAGE_KEYS.choice) === '1',
      published: get(STORAGE_KEYS.published) === '1',
    };
  }

  function writeLocal(storage, key, value) {
    try {
      if (!storage) return;
      if (value) storage.setItem(STORAGE_KEYS[key], '1'); else storage.removeItem(STORAGE_KEYS[key]);
    } catch (e) { /* stockage indisponible (navigation privée) : le choix vaut pour cette page seulement */ }
  }

  var STEP_TEXT = {
    broker: {
      title: '{{Connecter le broker MQTT}}',
      text: '{{Le même broker que celui de Home Assistant. Le plugin y dépose vos équipements, Home Assistant les y lit.}}',
    },
    ha: {
      title: '{{Vérifier que Home Assistant écoute}}',
      text: '{{Dans Home Assistant : Paramètres › Appareils et services › MQTT. L\'appareil « Jeedom (jeedom2ha) » doit y apparaître, avec l\'entité « État du pont ».}}',
    },
    choice: {
      title: '{{Choisir ce qui est publié}}',
      text: '{{Par défaut, tout ce que le plugin reconnaît est publié. Vous pourrez changer d\'avis à tout moment.}}',
    },
    publish: {
      title: '{{Publier dans Home Assistant}}',
      text: '{{Le plugin va lire Jeedom et publier ce qu\'il reconnaît. Vous verrez le détail juste après.}}',
    },
  };

  var HA_CAUSES = [
    '{{L\'intégration MQTT n\'est pas installée dans Home Assistant : Paramètres › Appareils et services › Ajouter une intégration › MQTT.}}',
    '{{Home Assistant utilise un autre broker : indiquez le même dans la configuration du plugin.}}',
    '{{La découverte MQTT est désactivée : dans les options de l\'intégration MQTT de Home Assistant, activez la découverte.}}',
  ];

  var LOGS = [
    ['jeedom2ha', '{{le plugin}}'],
    ['jeedom2ha_daemon', '{{les ordres reçus de Home Assistant et les refus}}'],
    ['jeedom2ha_packages', '{{l\'installation}}'],
  ];

  function createGuide(env) {
    var $ = env.$;
    var actions = env.actions || {};
    var st = {
      status: undefined,
      snapshot: null,
      visible: false,
      mode: null,          // 'auto' (affiché seul) ou 'manual' (rouvert par le menu)
      closed: false,       // fermé par l'utilisateur pour cette page
      phase: 'steps',      // 'steps' | 'publishing' | 'done'
      haHelp: false,
      error: '',
      hidMain: false,
    };

    function local() { return readLocal(env.storage); }
    function jeedomCount() {
      return (env.rooms || []).reduce(function (n, room) { return n + ((room && room.equipments) ? room.equipments.length : 0); }, 0);
    }
    function summary() { return summaryFrom(st.snapshot, jeedomCount()); }
    function readState() { return st.snapshot ? { kind: st.snapshot.kind } : null; }

    function setMainHidden(hidden) {
      var $main = $('#j2ha_mainView');
      if (hidden && !st.hidMain && $main.length && $main.is(':visible')) {
        $main.hide();
        st.hidMain = true;
      } else if (!hidden && st.hidMain) {
        $main.show();
        st.hidMain = false;
      }
    }

    function el(html, text) {
      var $node = $(html);
      if (text !== undefined) $node.text(text);
      return $node;
    }

    function button(label, cls, onClick) {
      var $b = $('<button type="button" class="btn btn-sm"></button>').addClass(cls || 'btn-default').text(label);
      $b.on('click', function (event) { if (event && event.preventDefault) event.preventDefault(); onClick(); });
      return $b;
    }

    function stepLabel(step) {
      if (step.state === 'done') return el('<span class="j2ha-v2-lbl is-ok"></span>', step.auto === false && step.key === 'ha' ? '{{Fait (vu par vous)}}' : '{{Fait}}');
      if (step.state === 'error') return el('<span class="j2ha-v2-lbl is-warn"></span>', '{{À corriger}}');
      if (step.state === 'current') return el('<span class="j2ha-v2-lbl is-todo"></span>', '{{À faire}}');
      return null;
    }

    function stepActions(step, model) {
      var $acts = $('<div class="j2ha-v2-acts"></div>');
      var active = step.state === 'current' || step.state === 'error';
      if (step.key === 'broker' && !step.done) {
        $acts.append(button('{{Ouvrir la configuration MQTT}}', active ? 'btn-primary j2ha-v2-btn-primary' : 'btn-default', function () { if (actions.openConfig) actions.openConfig(); }));
      }
      if (step.key === 'ha' && !step.done && step.state !== 'blocked') {
        $acts.append(button('{{Je l\'ai vu}}', 'btn-primary j2ha-v2-btn-primary j2ha-v2-guide-haseen', function () {
          writeLocal(env.storage, 'haSeen', true);
          st.haHelp = false;
          render();
        }));
        $acts.append(button('{{Je ne le vois pas}}', 'btn-default j2ha-v2-guide-hahelp', function () {
          st.haHelp = !st.haHelp;
          render();
        }).attr('aria-expanded', st.haHelp ? 'true' : 'false'));
      }
      if (step.key === 'choice' && !step.done && step.state !== 'blocked') {
        $acts.append(button('{{Tout publier (recommandé)}}', 'btn-primary j2ha-v2-btn-primary j2ha-v2-guide-all', function () {
          writeLocal(env.storage, 'choice', true);
          render();
        }));
        $acts.append(button('{{Choisir…}}', 'btn-default j2ha-v2-guide-choose', function () {
          writeLocal(env.storage, 'choice', true);
          if (actions.openChoose) actions.openChoose();
          render();
        }));
      }
      if (step.key === 'publish' && !step.done && !step.empty) {
        var publishing = st.phase === 'publishing';
        var $pub = button(publishing ? '{{Publication en cours…}}' : '{{Publier dans Home Assistant}}', active ? 'btn-primary j2ha-v2-btn-primary j2ha-v2-guide-publish' : 'btn-default j2ha-v2-guide-publish', publish);
        if (publishing) $pub.prepend(' ').prepend($('<i class="fas fa-spinner fa-spin"></i>'));
        $pub.prop('disabled', !active || publishing);
        $acts.append($pub);
      }
      if (step.state === 'blocked') {
        $acts.append(el('<span class="j2ha-v2-muted j2ha-v2-small"></span>', '{{Terminez l\'étape}} ' + step.waitFor + ' {{d\'abord.}}'));
      }
      return $acts.children().length ? $acts : null;
    }

    function renderStep(step, model) {
      var text = STEP_TEXT[step.key];
      var cls = { done: 'is-done', current: 'is-current', error: 'is-blocked', blocked: 'is-wait' }[step.state];
      var $step = $('<div class="j2ha-v2-step" role="listitem"></div>').addClass(cls).attr('data-step', step.key);
      $step.append(el('<div class="j2ha-v2-step-num" aria-hidden="true"></div>', step.state === 'done' ? '✔' : String(step.number)));
      var $body = $('<div class="j2ha-v2-step-body"></div>');
      var $title = el('<div class="j2ha-v2-step-title"></div>', step.number + '. ' + text.title + ' ');
      var $lbl = stepLabel(step);
      if ($lbl) $title.append($lbl);
      $body.append($title);
      $body.append(el('<div class="j2ha-v2-small"></div>', text.text));
      if (step.cause) $body.append(el('<div class="j2ha-v2-alert is-warn j2ha-v2-step-cause"></div>', step.cause));
      if (step.note) $body.append(el('<div class="j2ha-v2-muted j2ha-v2-small"></div>', step.note));
      if (step.key === 'ha' && !step.done && step.ha_known) {
        $body.append(el('<div class="j2ha-v2-muted j2ha-v2-small"></div>', '{{Home Assistant ne s\'est pas encore signalé sur le broker.}} ' + HA_TOOLTIP));
      }
      if (step.key === 'ha' && st.haHelp && !step.done) {
        var $help = $('<ul class="j2ha-v2-guide-causes j2ha-v2-small"></ul>');
        HA_CAUSES.forEach(function (cause) { $help.append(el('<li></li>', cause)); });
        $body.append($help);
      }
      if (step.key === 'publish' && st.error && !step.done) $body.append(el('<div class="j2ha-v2-alert is-warn"></div>', st.error));
      var $acts = stepActions(step, model);
      if ($acts) $body.append($acts);
      $step.append($body);
      return $step;
    }

    function renderDone() {
      var sum = summary();
      var pub = publicationInfo(st.status);
      var $box = $('<div class="j2ha-v2-guide-done"></div>');
      var count = sum.read ? sum.published : (pub && pub.equipments !== null ? pub.equipments : null);
      var headline;
      if (count === null) headline = '{{C\'est fait : vos équipements sont dans Home Assistant.}}';
      else if (count === 0) headline = '{{La relecture est faite, mais aucun équipement n\'est publié pour l\'instant.}}';
      else if (count === 1) headline = '{{C\'est fait : 1 équipement est dans Home Assistant.}}';
      else headline = '{{C\'est fait :}} ' + count + ' {{équipements sont dans Home Assistant.}}';
      $box.append(el('<h3 class="j2ha-v2-guide-title"></h3>', headline));
      if (pub && pub.scenarios) {
        $box.append(el('<p class="j2ha-v2-muted"></p>', '+ ' + pub.scenarios + ' ' + (pub.scenarios > 1 ? '{{scénarios publiés comme boutons}}' : '{{scénario publié comme bouton}}')));
      }
      $box.append(el('<p></p>', '{{Où les trouver : dans Home Assistant, Paramètres › Appareils et services › MQTT.}}'));
      if (sum.names.length) {
        $box.append(el('<p class="j2ha-v2-guide-names"></p>', '{{Par exemple :}} ' + sum.names.map(function (n) { return '« ' + n + ' »'; }).join(', ') + '.'));
      }
      var $acts = $('<div class="j2ha-v2-acts"></div>');
      $acts.append(button('{{Voir ma maison}}', 'btn-primary j2ha-v2-btn-primary j2ha-v2-guide-home', function () { close(); }));
      if (sum.read && sum.blocked > 0) {
        var label = sum.blocked > 1 ? sum.blocked + ' {{équipements ont besoin de vous}}' : '{{1 équipement a besoin de vous}}';
        $acts.append(button(label, 'btn-default j2ha-v2-guide-blocked', function () {
          close();
          if (actions.openFilter) actions.openFilter('blocked');
        }));
      }
      $box.append($acts);
      return $box;
    }

    function render() {
      var $root = $('#j2ha_v2_guide');
      if ($root.length === 0) return;
      if (!st.visible) {
        $root.empty();
        setMainHidden(false);
        return;
      }
      var model = computeSteps(st.status, readState(), summary(), local());
      $root.empty().attr('role', 'region').attr('aria-label', '{{Guide de démarrage}}');
      if (st.phase === 'done') {
        $root.append(renderDone());
      } else {
        var $head = $('<div class="j2ha-v2-guide-head"></div>');
        var $intro = $('<div></div>');
        $intro.append(el('<h3 class="j2ha-v2-guide-title"></h3>', '{{Bienvenue dans jeedom2ha}}'));
        $intro.append(el('<p></p>', '{{jeedom2ha publie vos équipements Jeedom dans Home Assistant. Jeedom reste la source : rien n\'y est modifié.}}'));
        $head.append($intro);
        $head.append(button('{{Fermer}}', 'btn-default j2ha-v2-guide-close', function () { close(); }));
        $root.append($head);
        var $steps = $('<div class="j2ha-v2-steps" role="list"></div>');
        model.steps.forEach(function (step) { $steps.append(renderStep(step, model)); });
        $root.append($steps);
        var $foot = $('<p class="j2ha-v2-muted j2ha-v2-small j2ha-v2-guide-foot"></p>');
        var $never = $('<button type="button" class="btn btn-link btn-xs j2ha-v2-link j2ha-v2-guide-dismiss"></button>').text('{{Ne plus afficher ce guide}}');
        $never.on('click', function () {
          writeLocal(env.storage, 'dismissed', true);
          close();
        });
        $foot.append($never);
        $foot.append(textSpan(' · {{rouvrable par « Autres actions › Guide de démarrage »}}'));
        $root.append($foot);
      }
      setMainHidden(true);
    }

    function textSpan(text) { return el('<span></span>', text); }

    function publish() {
      if (st.phase === 'publishing' || typeof actions.publish !== 'function') return;
      st.error = '';
      st.phase = 'publishing';
      render();
      var started = actions.publish(function (failed) {
        if (failed) {
          st.phase = 'steps';
          st.error = '{{La publication n\'a pas abouti : lisez le message affiché, puis réessayez.}}';
        } else {
          writeLocal(env.storage, 'published', true);
          writeLocal(env.storage, 'choice', true);
          st.phase = 'done';
        }
        render();
      });
      if (started === false) {
        st.phase = 'steps';
        st.error = '{{Une opération est déjà en cours : réessayez dans un instant.}}';
        render();
      }
    }

    function evaluate() {
      if (st.closed || st.mode === 'manual' || st.phase !== 'steps') { render(); return; }
      var show = shouldShow(st.status, readState(), local());
      if (show && (typeof env.canAutoShow !== 'function' || env.canAutoShow())) {
        st.visible = true;
        st.mode = 'auto';
      } else if (!show && st.mode === 'auto') {
        st.visible = false;
        st.mode = null;
      }
      render();
    }

    function open() {
      st.visible = true;
      st.closed = false;
      st.mode = 'manual';
      st.phase = 'steps';
      st.error = '';
      render();
      var $root = $('#j2ha_v2_guide');
      if ($root.length && $root.get(0) && typeof $root.get(0).scrollIntoView === 'function') $root.get(0).scrollIntoView();
    }

    function close() {
      st.visible = false;
      st.closed = true;
      st.mode = null;
      st.phase = 'steps';
      render();
    }

    // --- E7 : Vérifier l'installation ---

    function checkRow(check, $dialogHolder) {
      var word = { ok: '{{OK}}', fail: '{{À corriger}}', warn: '{{À vérifier}}', wait: '{{En attente}}' }[check.state];
      var lbl = { ok: 'is-ok', fail: 'is-warn', warn: 'is-todo', wait: 'is-off' }[check.state];
      var $row = $('<div class="j2ha-v2-row j2ha-v2-check" role="listitem"></div>').attr('data-check', check.key).addClass('is-' + check.state);
      $row.append(el('<span class="j2ha-v2-lbl"></span>', word).addClass(lbl));
      var $grow = $('<div class="j2ha-v2-grow"></div>');
      $grow.append(el('<div class="j2ha-v2-check-title"></div>', check.title));
      if (check.detail && check.state !== 'wait') $grow.append(el('<div class="j2ha-v2-muted j2ha-v2-small"></div>', check.detail));
      if (check.state === 'wait') $grow.append(el('<div class="j2ha-v2-muted j2ha-v2-small"></div>', '{{Corrigez d\'abord le point ci-dessus.}}'));
      if (check.help && check.state !== 'wait') {
        var $help = $('<ul class="j2ha-v2-guide-causes j2ha-v2-small"></ul>');
        HA_CAUSES.forEach(function (cause) { $help.append(el('<li></li>', cause)); });
        $grow.append($help);
      }
      $row.append($grow);
      if (check.remedy && check.state !== 'wait') {
        $row.append(button(check.remedy.label, check.state === 'fail' ? 'btn-primary j2ha-v2-btn-primary j2ha-v2-check-remedy' : 'btn-default j2ha-v2-check-remedy', function () {
          $dialogHolder.close();
          var fn = { config: actions.openConfig, rescan: actions.rescan, blocked: function () { if (actions.openFilter) actions.openFilter('blocked'); } }[check.remedy.action];
          if (typeof fn === 'function') fn();
        }));
      }
      return $row;
    }

    function openCheck() {
      if (!env.bootbox || typeof env.bootbox.dialog !== 'function') return null;
      var checks = checkInstall(st.status, readState(), summary());
      var holder = { close: function () {} };
      var $content = $('<div class="j2ha-v2 j2ha-v2-checkbox"></div>');
      var $list = $('<div class="j2ha-v2-checks" role="list"></div>');
      checks.forEach(function (check) { $list.append(checkRow(check, holder)); });
      $content.append($list);

      // Pied « Pour le support » : le contenu existant de l'export du diagnostic (case et bouton, identifiants et
      // gestionnaire inchangés) est déplacé ici, puis rendu à sa place à la fermeture. Idem pour l'export de décision.
      var $support = $('<div class="j2ha-v2-check-support"></div>');
      $support.append(el('<h4 class="j2ha-v2-check-head"></h4>', '{{Pour le support}}'));
      $support.append(el('<p class="j2ha-v2-small"></p>', '{{Un fichier qui décrit votre installation jeedom2ha. À joindre à votre message sur le forum.}}'));
      var $diagHolder = $('#div_diagnosticDialog');
      var $diag = $diagHolder.children();
      $support.append($diag);
      var $advToggle = $('<button type="button" class="btn btn-link btn-xs j2ha-v2-link j2ha-v2-check-advanced" aria-expanded="false"></button>').text('{{Avancé}}');
      var $adv = $('<div class="j2ha-v2-check-advanced-body"></div>').hide();
      var $decHolder = $('#div_decisionExportDialog');
      var $dec = $decHolder.children();
      $adv.append($dec);
      var $logs = $('<ul class="j2ha-v2-small j2ha-v2-check-logs"></ul>');
      LOGS.forEach(function (log) {
        var $li = $('<li></li>');
        $li.append($('<a target="_blank" rel="noopener"></a>').attr('href', 'index.php?v=d&p=log&logfile=' + log[0]).text(log[0]));
        $li.append(textSpan(' : ' + log[1]));
        $logs.append($li);
      });
      $adv.append(el('<p class="j2ha-v2-small"></p>', '{{Journaux du plugin :}}'));
      $adv.append($logs);
      $advToggle.on('click', function () {
        var open = $advToggle.attr('aria-expanded') !== 'true';
        $advToggle.attr('aria-expanded', open ? 'true' : 'false');
        if (open) $adv.show(); else $adv.hide();
      });
      $support.append($advToggle);
      $support.append($adv);
      $content.append($support);

      var restored = false;
      var dialog = env.bootbox.dialog({
        title: '{{Vérifier l\'installation}}',
        message: $content,
        onEscape: true,
        backdrop: true,
        buttons: { close: { label: '{{Fermer}}', className: 'btn-default' } },
      });
      function restore() {
        if (restored) return;
        restored = true;
        $diagHolder.append($diag);
        $decHolder.append($dec);
      }
      if (dialog && typeof dialog.on === 'function') dialog.on('hidden.bs.modal', restore);
      holder.close = function () {
        if (dialog && typeof dialog.modal === 'function') dialog.modal('hide');
        restore();
      };
      return { checks: checks, dialog: dialog, close: holder.close };
    }

    return {
      onStatus: function (status) { st.status = status; evaluate(); },
      onSnapshot: function (snapshot) { st.snapshot = snapshot || null; evaluate(); },
      open: open,
      close: close,
      openCheck: openCheck,
      render: render,
      state: function () { return { visible: st.visible, mode: st.mode, phase: st.phase, error: st.error }; },
    };
  }

  return {
    version: 2,
    STORAGE_KEYS: STORAGE_KEYS,
    STEP_KEYS: STEP_KEYS,
    HA_TOOLTIP: HA_TOOLTIP,
    shortDate: shortDate,
    haInfo: haInfo,
    publicationInfo: publicationInfo,
    haBarItem: haBarItem,
    relectureFusion: relectureFusion,
    summaryFrom: summaryFrom,
    computeSteps: computeSteps,
    shouldShow: shouldShow,
    checkInstall: checkInstall,
    readLocal: readLocal,
    createGuide: createGuide,
  };
}));
