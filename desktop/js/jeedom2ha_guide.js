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
    known: 'jeedom2ha.guide.known',
    // Front v3 (Lot 3) : les quatre étapes ont été vues « Fait » ensemble (signaux observés) : le guide ne s'ouvre plus seul.
    finished: 'jeedom2ha.guide.finished',
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

  /** Item « Home Assistant » de la barre d'état : masqué si le démon ne fournit pas le champ, ou s'il est arrêté.
   * Front v2 (Lot 6, retour de démo) : sans signal de démarrage depuis le dernier démarrage du démon (`birth_seen_at` null),
   * l'état est NEUTRE, « Non confirmé » (Home Assistant qui tourne déjà ne se signale pas de nouveau) ; vu : « Vu à HH:MM »
   * (« Vu le JJ/MM à HH:MM » si ce n'est pas aujourd'hui). `now` (ms) : facultatif, pour les tests.
   * Front v2 (Lot 9a, regard neuf v2) : `confirmed` = l'utilisateur a cliqué « Je l'ai vu » (guide ou « Vérifier
   * l'installation… ») ; sans signal du démon, l'item dit alors « Confirmé par vous » (vert pâle) au lieu de « Non confirmé ».
   * Le signal du démon reste prioritaire (« Vu à HH:MM »). */
  function haBarItem(status, now, confirmed) {
    var ha = haInfo(status);
    if (!ha || !status.daemon) return { visible: false, text: '', seen: false, confirmed: false };
    if (ha.seen_at) {
      var parts = shortDate(ha.seen_at).split(' ');
      if (parts.length !== 2) return { visible: true, seen: true, confirmed: false, text: '{{Vu}}' };
      var seen = new Date(ha.seen_at);
      var today = new Date(typeof now === 'number' ? now : Date.now());
      var sameDay = seen.getFullYear() === today.getFullYear() && seen.getMonth() === today.getMonth() && seen.getDate() === today.getDate();
      return { visible: true, seen: true, confirmed: false, text: sameDay ? '{{Vu à}} ' + parts[1] : '{{Vu le}} ' + parts[0] + ' {{à}} ' + parts[1] };
    }
    if (confirmed === true) return { visible: true, seen: false, confirmed: true, text: '{{Confirmé par vous}}' };
    return { visible: true, seen: false, confirmed: false, text: '{{Non confirmé}}' };
  }

  var HA_TOOLTIP = '{{Home Assistant se signale sur le broker quand il démarre ; s\'il tourne déjà, c\'est normal. Vérifiez qu\'il voit l\'appareil « Jeedom (jeedom2ha) ».}}';
  // Front v2 (Lot 9a) : infobulle de « Confirmé par vous ».
  var HA_CONFIRMED_TOOLTIP = '{{Vous avez indiqué que Home Assistant voit l\'appareil « Jeedom (jeedom2ha) ». Home Assistant se signalera de lui-même à son prochain démarrage.}}';

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

  function lastOperation(status) {
    var op = status && status.derniere_operation_resultat;
    return op && typeof op === 'object' ? op : null;
  }

  /**
   * Une publication a-t-elle RÉUSSI ? Une relecture terminée ne suffit pas : le démon renseigne
   * `derniere_synchro_terminee` même quand la publication échoue (échec MQTT total). Sources, de la plus sûre à la moins
   * sûre : `status.publication.equipments_published > 0` (Lot 3), une lecture des états qui
   * compte au moins un équipement publié, le résultat de la dernière opération (réussie ou partielle), la mémoire du
   * navigateur.
   */
  function publishedOk(status, summary, local) {
    var pub = publicationInfo(status);
    // Lot 3 : compté sur la mémoire vive du démon. > 0 prouve la publication ; 0 ne prouve rien seul (juste après un
    // redémarrage du démon, avant sa relecture « boot ») : les autres preuves décident alors.
    if (pub && pub.equipments !== null && pub.equipments > 0) return true;
    if (summary && summary.read && summary.published > 0) return true;
    var op = lastOperation(status);
    if (status && status.derniere_synchro_terminee && op && (op.resultat === 'succes' || op.resultat === 'partiel')) return true;
    return !!(local && local.published);
  }

  /** Dernière relecture tentée mais en échec (le bouton de l'étape 4 devient « Réessayer »). */
  function publishFailed(status) {
    var op = lastOperation(status);
    return !!(status && status.derniere_synchro_terminee && op && op.intention === 'sync' && op.resultat === 'echec');
  }

  /**
   * Installation déjà connue = une publication a RÉUSSI (jamais une simple tentative : le démon renseigne la date de fin
   * même quand la publication échoue, et il lance une relecture « boot » dès son premier démarrage). Preuves :
   * `status.publication.equipments_published > 0`, lecture des états avec au moins un publié, relecture réussie ou
   * partielle, ou ce navigateur l'a déjà constaté. Une panne d'une installation connue n'affiche JAMAIS le guide plein
   * écran : la barre d'état et « Vérifier l'installation… » suffisent.
   */
  function knownInstall(status, summary, local) {
    return !!((local && (local.known || local.published)) || publishedOk(status, summary, null));
  }

  /**
   * Les quatre étapes de E1. `status` : réponse de getBridgeStatus (`undefined` = pas encore lue, `null` = illisible) ;
   * `readState` : { kind } de la lecture des états ; `summary` : summaryFrom() ; `local` : préférences du navigateur.
   * État d'une étape : `done`, `current` (la première non faite), `blocked` (les suivantes), `error` (la première non faite,
   * avec une cause). Une étape faite reste faite, même si une précédente ne l'est plus.
   * Front v2 (Lot 9a, regard neuf v2) : jamais une étape « À faire » avant une étape « Fait ». L'étape 1 non faite suivie
   * d'une étape faite est soit en erreur (cause connue), soit « en vérification » (`checking`, état pas encore lu).
   * Front v3 (Lot 0, « fail-closed ») : une étape n'est « Fait » (`done`) que si le signal qu'elle nomme est OBSERVÉ :
   *   1. démon et broker en marche (état du démon) ;
   *   2. Home Assistant confirmé (signal de démarrage vu par le démon, ou « Je l'ai vu » de l'utilisateur) ;
   *   3. choix fait par l'utilisateur, ou publication réussie observée (le choix par défaut a été appliqué) ;
   *   4. publication réussie observée (état du démon, lecture des états, dernière relecture réussie ou partielle).
   * Rien n'est plus « réputé fait » : une étape dont le signal n'est que déduit (étape 2 alors qu'une étape suivante est
   * faite) ou seulement mémorisé par ce navigateur (publication constatée hier, démon redémarré depuis) est « À vérifier »
   * (`verify`), avec un bouton qui lance la vérification. « À vérifier » ne bloque pas l'ordre des étapes.
   */
  function computeSteps(status, readState, summary, local) {
    var loc = local || {};
    var sum = summary || {};
    var ha = haInfo(status);
    // Observé seulement : la mémoire du navigateur (`loc.published`) ne fait plus cocher l'étape 4.
    var isSynced = publishedOk(status, sum, null);
    var remembered = !isSynced && !!loc.published;
    var failed = !isSynced && publishFailed(status);
    var broker = brokerState(status);

    var s1 = { key: 'broker', number: 1, done: bridgeUp(status), cause: '', remedy: 'config' };
    // Front v3 (Lot 3) : `short` = la cause en quelques mots, affichée sur la ligne de l'étape (la cause entière en info-bulle).
    if (!s1.done) {
      if (status === null) { s1.cause = '{{Jeedom n\'a pas pu lire l\'état du démon.}}'; s1.short = '{{État du démon illisible}}'; }
      else if (status && !status.daemon) { s1.cause = '{{Le démon est arrêté.}}'; s1.short = '{{Démon arrêté}}'; }
      else if (broker === 'disconnected') { s1.cause = '{{Le broker MQTT ne répond pas.}}'; s1.short = '{{Broker injoignable}}'; }
      else if (broker === 'connecting' || broker === 'reconnecting') s1.note = '{{Connexion au broker en cours…}}';
    }
    var s2 = { key: 'ha', number: 2, done: !!(ha && ha.seen_at) || !!loc.haSeen, auto: !!(ha && ha.seen_at), manual: !(ha && ha.seen_at), ha_known: !!ha };
    var s3 = { key: 'choice', number: 3, done: !!loc.choice || isSynced };
    var s4 = { key: 'publish', number: 4, done: isSynced, empty: sum.jeedom_equipments === 0 };
    // Publication seulement mémorisée par ce navigateur : à revérifier (relecture), sauf échec observé ou Jeedom vide.
    if (remembered && !failed && !s4.empty) {
      s4.verify = true;
      if (!s3.done) s3.verify = true;
    }
    if (s4.empty && !s4.done) {
      s4.cause = '{{Jeedom ne contient encore aucun équipement à publier. Ajoutez des équipements dans Jeedom, puis revenez ici.}}';
      s4.short = '{{Aucun équipement dans Jeedom}}';
    } else if (failed) {
      s4.retry = true;
      s4.cause = '{{La dernière publication a échoué : rien n\'est encore dans Home Assistant. Vérifiez le broker MQTT, puis réessayez.}}';
      s4.short = '{{La dernière publication a échoué}}';
    }

    // Une étape ultérieure faite (ou à revérifier) laisse penser que l'étape 2 a été franchie, sans le prouver : à vérifier.
    if (!s2.done && (s3.done || s4.done || s3.verify || s4.verify)) s2.verify = true;

    var steps = [s1, s2, s3, s4];
    var laterDone = steps.slice(1).some(function (step) { return step.done || step.verify; });
    var firstOpen = -1;
    steps.forEach(function (step, index) {
      if (step.done) { step.state = 'done'; return; }
      if (step.verify) {
        // N'arrête pas l'ordre ; `waitFor` : une étape précédente reste ouverte (la relecture de l'étape 4 l'attend).
        step.state = 'verify';
        if (firstOpen !== -1) step.waitFor = steps[firstOpen].number;
        return;
      }
      if (firstOpen === -1) {
        firstOpen = index;
        step.state = step.cause ? 'error' : (index === 0 && laterDone ? 'checking' : 'current');
      } else {
        step.state = 'blocked';
        step.waitFor = steps[firstOpen].number;
      }
    });
    // Complet = toutes les étapes « Fait » : une étape « À vérifier » ne compte pas comme faite.
    return { steps: steps, current: firstOpen, complete: steps.every(function (step) { return step.done; }), synced: isSynced };
  }

  /**
   * Le guide s'affiche seul tant que rien n'a encore été publié avec succès : jamais relu, démon / broker indisponible,
   * ou dernière relecture en échec (première relecture « boot » ratée comprise). Jamais pour une installation connue
   * (voir knownInstall), jamais avant la première lecture des états, jamais après « Ne plus afficher ».
   */
  function shouldShow(status, readState, local, summary) {
    var loc = local || {};
    // Front v3 (Lot 3) : un guide réellement terminé (quatre étapes « Fait » observées) ne s'ouvre plus de lui-même.
    if (loc.dismissed || loc.finished) return false;
    var kind = readState && readState.kind;
    if (!kind) return false;
    if (knownInstall(status, summary, loc)) return false;
    if (kind === 'never_synced') return true;
    if (status === undefined) return false;
    if (status === null || !bridgeUp(status)) return true;
    return publishFailed(status);
  }

  /**
   * Contrôles de E7, dans l'ordre. État : `ok`, `fail` (le premier arrête la liste : les suivants passent à `wait`),
   * `warn` (à vérifier, n'arrête pas), `skip` (non vérifiable avec ce démon : non affiché).
   * Front v2 (Lot 9a) : quatre statuts au plus à l'écran (OK / À corriger / À vérifier / En attente). Home Assistant sans
   * signal de démarrage est « À vérifier » (`ask` : boutons « Je l'ai vu » / « Je ne vois pas l'appareil… », causes
   * repliées) ; confirmé par l'utilisateur (`local.haSeen`) : « OK », « Confirmé par vous ».
   */
  function checkInstall(status, readState, summary, local) {
    var sum = summary || {};
    var loc = local || {};
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
    // Front v2 (Lot 9a) : sans signal de démarrage, « À vérifier » (n'arrête pas la liste) avec « Je l'ai vu » ; les trois
    // causes ne sont montrées qu'en dépliant « Je ne vois pas l'appareil dans Home Assistant ».
    var haCheck = { key: 'ha', title: '{{Home Assistant sur le broker}}', state: 'skip', detail: '' };
    if (ha && ha.seen_at) {
      haCheck.state = 'ok';
      haCheck.detail = haBarItem(status).text;
    } else if (ha && loc.haSeen) {
      haCheck.state = 'ok';
      haCheck.detail = '{{Confirmé par vous}}';
    } else if (ha) {
      haCheck.state = 'warn';
      haCheck.detail = HA_TOOLTIP;
      haCheck.help = true;
      haCheck.ask = true;
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
      known: get(STORAGE_KEYS.known) === '1',
      finished: get(STORAGE_KEYS.finished) === '1',
    };
  }

  function writeLocal(storage, key, value) {
    try {
      if (!storage) return;
      if (value) storage.setItem(STORAGE_KEYS[key], '1'); else storage.removeItem(STORAGE_KEYS[key]);
    } catch (e) { /* stockage indisponible (navigation privée) : le choix vaut pour cette page seulement */ }
  }

  // Front v3 (Lot 3) : une ligne par étape ; `title` (3 mots) est affiché, `text` passe dans l'info-bulle ⓘ de la ligne.
  var STEP_TEXT = {
    broker: {
      title: '{{Connecter le broker}}',
      text: '{{Le même broker que celui de Home Assistant. Le plugin y dépose vos équipements, Home Assistant les y lit.}}',
    },
    ha: {
      title: '{{Vérifier Home Assistant}}',
      text: '{{Dans Home Assistant : Paramètres › Appareils et services › MQTT. L\'appareil « Jeedom (jeedom2ha) » doit y apparaître, avec l\'entité « État du pont ».}}',
    },
    choice: {
      title: '{{Choisir ce qui est publié}}',
      text: '{{Par défaut, tout ce que le plugin reconnaît est publié. Vous pourrez changer d\'avis à tout moment.}}',
    },
    publish: {
      title: '{{Publier les équipements}}',
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

    // Préférences gardées EN MÉMOIRE pour la page ; le stockage local n'est qu'une persistance au mieux (refusé en
    // navigation privée : le guide avance quand même, le choix vaut alors pour cette page seulement).
    var mem = {};
    function local() {
      var stored = readLocal(env.storage);
      Object.keys(mem).forEach(function (key) { if (mem[key]) stored[key] = true; });
      return stored;
    }
    function remember(key) {
      mem[key] = true;
      writeLocal(env.storage, key, true);
    }
    // Front v2 (Lot 9a) : « Je l'ai vu » (guide ou « Vérifier l'installation… ») est mémorisé (page + stockage local au mieux)
    // et la barre d'état est prévenue pour passer à « Confirmé par vous ».
    function confirmHaSeen() {
      remember('haSeen');
      learn(); // Front v3 (Lot 3) : la dernière étape confirmée peut terminer le guide.
      if (typeof env.onHaConfirmed === 'function') env.onHaConfirmed();
    }
    // Ce que la page apprend de l'état réel : installation connue, publication réussie (retenu pour les pannes futures).
    function learn() {
      var loc = local();
      if (!loc.known && knownInstall(st.status, summary(), {})) remember('known');
      if (!loc.published && publishedOk(st.status, summary(), {})) remember('published');
      // Front v3 (Lot 3) : guide réellement terminé (quatre « Fait » observés, jamais une mémoire) : il ne s'ouvrira plus seul.
      if (!loc.finished && computeSteps(st.status, readState(), summary(), loc).complete) remember('finished');
    }
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

    // ⓘ : l'explication en info-bulle (title + aria-label), atteignable au clavier.
    function info(text, cls) {
      return $('<span class="j2ha-v3-info" role="img" tabindex="0"></span>').addClass(cls || '').attr('title', text).attr('aria-label', text)
        .append($('<i class="fas fa-info-circle" aria-hidden="true"></i>'));
    }

    function button(label, cls, onClick) {
      var $b = $('<button type="button" class="btn btn-sm"></button>').addClass(cls || 'btn-default').text(label);
      $b.on('click', function (event) { if (event && event.preventDefault) event.preventDefault(); onClick(); });
      return $b;
    }

    function stepLabel(step) {
      if (step.state === 'done') return el('<span class="j2ha-v2-lbl is-ok"></span>', step.auto === false && step.key === 'ha' ? '{{Fait (vu par vous)}}' : '{{Fait}}');
      if (step.state === 'verify') return el('<span class="j2ha-v2-lbl is-todo"></span>', '{{À vérifier}}');
      if (step.state === 'checking') return el('<span class="j2ha-v2-lbl is-off"></span>', '{{Vérification en cours}}');
      if (step.state === 'error') return el('<span class="j2ha-v2-lbl is-warn"></span>', '{{À corriger}}');
      if (step.state === 'current') return el('<span class="j2ha-v2-lbl is-todo"></span>', '{{À faire}}');
      return null;
    }

    function stepActions(step, model) {
      var $acts = $('<div class="j2ha-v2-acts"></div>');
      var active = step.state === 'current' || step.state === 'error' || (step.state === 'verify' && !step.waitFor);
      if (step.key === 'broker' && !step.done) {
        $acts.append(button('{{Ouvrir la configuration MQTT}}', active ? 'btn-primary j2ha-v2-btn-primary' : 'btn-default', function () { if (actions.openConfig) actions.openConfig(); }));
      }
      // « À vérifier » : le bouton principal de l'étape porte aussi la classe j2ha-v2-guide-verify (il lance la vérification).
      var verifyCls = step.state === 'verify' ? ' j2ha-v2-guide-verify' : '';
      if (step.key === 'ha' && !step.done && step.state !== 'blocked') {
        // Le seul témoin possible ici est l'utilisateur : il regarde dans Home Assistant et le confirme.
        $acts.append(button('{{Je l\'ai vu}}', 'btn-primary j2ha-v2-btn-primary j2ha-v2-guide-haseen' + verifyCls, function () {
          confirmHaSeen();
          st.haHelp = false;
          render();
        }));
        $acts.append(button('{{Je ne le vois pas}}', 'btn-default j2ha-v2-guide-hahelp', function () {
          st.haHelp = !st.haHelp;
          render();
        }).attr('aria-expanded', st.haHelp ? 'true' : 'false'));
      }
      if (step.key === 'choice' && !step.done && step.state !== 'blocked') {
        $acts.append(button('{{Tout publier (recommandé)}}', 'btn-primary j2ha-v2-btn-primary j2ha-v2-guide-all' + verifyCls, function () {
          remember('choice');
          render();
        }));
        $acts.append(button('{{Choisir…}}', 'btn-default j2ha-v2-guide-choose', function () {
          remember('choice');
          if (actions.openChoose) actions.openChoose();
          render();
        }));
      }
      if (step.key === 'publish' && !step.done && !step.empty) {
        var publishing = st.phase === 'publishing';
        // « À vérifier » : relire Jeedom (relecture existante) observe de nouveau la publication.
        var pubLabel = step.retry ? '{{Réessayer de publier}}' : (step.state === 'verify' ? '{{Vérifier la publication}}' : '{{Publier dans Home Assistant}}');
        var $pub = button(publishing ? '{{Publication en cours…}}' : pubLabel, (active ? 'btn-primary j2ha-v2-btn-primary j2ha-v2-guide-publish' : 'btn-default j2ha-v2-guide-publish') + verifyCls, publish);
        if (step.state === 'verify') $pub.attr('title', '{{Relit Jeedom et confirme ce qui est dans Home Assistant}}');
        if (publishing) $pub.prepend(' ').prepend($('<i class="fas fa-spinner fa-spin"></i>'));
        $pub.prop('disabled', !active || publishing);
        $acts.append($pub);
      }
      // Front v3 (Lot 3) : « Terminez l'étape N d'abord » n'est plus une phrase : c'est l'info-bulle de la ligne grisée.
      return $acts.children().length ? $acts : null;
    }

    function textSpan(text) { return el('<span></span>', text); }

    // Front v3 (Lot 4b) : onglet Scénarios de la page (jeedom2ha_scenarios.js), injectable par `env.scenarios` ; absent = rien.
    function scenarioHook() {
      if (env.scenarios) return env.scenarios;
      var g = typeof globalThis !== 'undefined' ? globalThis : null;
      return g && g.Jeedom2haScenariosPage ? g.Jeedom2haScenariosPage : null;
    }

    // « n scénarios lancés à la main → [Publier ces n] » : ferme le guide et présélectionne ces scénarios dans l'onglet
    // Scénarios ; rien n'est publié avant « Appliquer ». Jamais un scénario programmé ou déclenché (voir suggestionIds).
    function scenarioSuggestion() {
      var hook = scenarioHook();
      var n = hook && typeof hook.suggestionCount === 'function' ? hook.suggestionCount() : 0;
      if (!n || typeof hook.preselectSuggested !== 'function') return null;
      var $line = $('<div class="j2ha-v2-small j2ha-v3-sc-guide-suggest"></div>');
      $line.append($('<i class="fas fa-hand-pointer" aria-hidden="true"></i>'));
      $line.append(textSpan(' ' + n + ' ' + (n > 1 ? '{{scénarios lancés à la main}}' : '{{scénario lancé à la main}}') + ' → '));
      var $btn = button(n > 1 ? '{{Publier ces}} ' + n : '{{Publier ce scénario}}', 'btn-default btn-xs j2ha-v2-guide-scenarios', function () {
        close();
        hook.preselectSuggested();
      });
      $btn.attr('title', '{{Prépare la publication ; rien n’est envoyé avant « Appliquer »}}');
      return $line.append($btn);
    }

    // Front v3 (Lot 3) : UNE ligne par étape — pastille, titre de 3 mots, état, action(s), ⓘ — sans phrase permanente. La cause
    // d'un arrêt tient en quelques mots (`short`), la phrase entière est dans l'info-bulle de l'état.
    function renderStep(step, model) {
      var text = STEP_TEXT[step.key];
      var cls = { done: 'is-done', current: 'is-current', checking: 'is-current', verify: 'is-current', error: 'is-blocked', blocked: 'is-wait' }[step.state];
      var $step = $('<div class="j2ha-v2-step j2ha-v3-step-line" role="listitem"></div>').addClass(cls).attr('data-step', step.key);
      if (step.waitFor && (step.state === 'blocked' || step.state === 'verify')) {
        var wait = '{{Terminez l\'étape}} ' + step.waitFor + ' {{d\'abord.}}';
        $step.attr('title', wait).attr('aria-description', wait);
      }
      $step.append(el('<div class="j2ha-v2-step-num" aria-hidden="true"></div>', step.state === 'done' ? '✔' : String(step.number)));
      var $body = $('<div class="j2ha-v2-step-body"></div>');
      var $title = el('<div class="j2ha-v2-step-title"></div>', step.number + '. ' + text.title + ' ');
      var $lbl = stepLabel(step);
      if ($lbl) {
        if (step.cause) $lbl.attr('title', step.cause).attr('aria-label', step.cause);
        $title.append($lbl);
      }
      if (step.short) $title.append(el('<span class="j2ha-v2-small j2ha-v3-step-cause j2ha-v2-step-cause"></span>', step.short));
      else if (step.cause) $title.append(el('<span class="j2ha-v2-small j2ha-v3-step-cause j2ha-v2-step-cause"></span>', step.cause));
      if (step.note) $title.append(el('<span class="j2ha-v2-muted j2ha-v2-small j2ha-v3-step-note"></span>', step.note));
      if (step.key === 'publish' && st.error && !step.done) $title.append(el('<span class="j2ha-v2-small j2ha-v3-step-cause j2ha-v3-step-error" role="alert"></span>', st.error));
      var tip = text.text + (step.key === 'ha' && !step.done && step.ha_known ? ' ' + '{{Home Assistant ne s\'est pas encore signalé sur le broker.}} ' + HA_TOOLTIP : '');
      $title.append(info(tip, 'j2ha-v3-step-info'));
      $body.append($title);
      if (step.key === 'ha' && st.haHelp && !step.done) {
        var $help = $('<ul class="j2ha-v2-guide-causes j2ha-v2-small"></ul>');
        HA_CAUSES.forEach(function (cause) { $help.append(el('<li></li>', cause)); });
        $body.append($help);
      }
      // Front v3 (Lot 4b) : étape 3, même suggestion que l'onglet Scénarios (présélection seulement).
      if (step.key === 'choice' && step.state !== 'blocked') {
        var $scenarios = scenarioSuggestion();
        if ($scenarios) $body.append($scenarios);
      }
      $step.append($body);
      var $acts = stepActions(step, model);
      if ($acts) $step.append($acts);
      return $step;
    }

    // Front v3 (Lot 3) : écran de fin d'une ligne (✓ chiffre), « où les trouver » et les exemples en info-bulle.
    function renderDone() {
      var sum = summary();
      var pub = publicationInfo(st.status);
      var $box = $('<div class="j2ha-v2-guide-done"></div>');
      var count = sum.read ? sum.published : (pub && pub.equipments !== null ? pub.equipments : null);
      var headline;
      if (count === null) headline = '{{C\'est fait : vos équipements sont dans Home Assistant.}}';
      else if (count === 0) headline = '{{Relecture faite : 0 publié}}';
      else if (count === 1) headline = '{{C\'est fait : 1 équipement est dans Home Assistant.}}';
      else headline = '{{C\'est fait :}} ' + count + ' {{équipements sont dans Home Assistant.}}';
      var tip = ['{{Où les trouver : dans Home Assistant, Paramètres › Appareils et services › MQTT.}}'];
      if (sum.names.length) tip.push('{{Par exemple :}} ' + sum.names.map(function (n) { return '« ' + n + ' »'; }).join(', ') + '.');
      if (pub && pub.scenarios) tip.push('+ ' + pub.scenarios + ' ' + (pub.scenarios > 1 ? '{{scénarios publiés comme boutons}}' : '{{scénario publié comme bouton}}'));
      $box.append(el('<h3 class="j2ha-v2-guide-title"></h3>', '✓ ' + headline + ' ').append(info(tip.join(' '), 'j2ha-v3-done-info')));
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
        // Front v3 (Lot 3) : le titre seul ; la présentation passe en info-bulle.
        $intro.append(el('<h3 class="j2ha-v2-guide-title"></h3>', '{{Bienvenue dans jeedom2ha}} ')
          .append(info('{{jeedom2ha publie vos équipements Jeedom dans Home Assistant. Jeedom reste la source : rien n\'y est modifié.}}')));
        $head.append($intro);
        $head.append(button('{{Fermer}}', 'btn-default j2ha-v2-guide-close', function () { close(); }));
        $root.append($head);
        var $steps = $('<div class="j2ha-v2-steps" role="list"></div>');
        model.steps.forEach(function (step) { $steps.append(renderStep(step, model)); });
        $root.append($steps);
        var $foot = $('<p class="j2ha-v2-muted j2ha-v2-small j2ha-v2-guide-foot"></p>');
        var $never = $('<button type="button" class="btn btn-link btn-xs j2ha-v2-link j2ha-v2-guide-dismiss"></button>').text('{{Ne plus afficher ce guide}}');
        $never.on('click', function () {
          remember('dismissed');
          close();
        });
        $never.attr('title', '{{Il se rouvre par le menu ⋯ › Guide de démarrage}}');
        $foot.append($never);
        $root.append($foot);
      }
      setMainHidden(true);
    }


    function publish() {
      if (st.phase === 'publishing' || typeof actions.publish !== 'function') return;
      st.error = '';
      st.phase = 'publishing';
      render();
      var started = actions.publish(function (failed) {
        if (failed) {
          st.phase = 'steps';
          st.error = '{{La publication n\'a pas abouti.}}';
        } else {
          // Pas de « connue » ici : seule une preuve de succès (état du démon, lecture des états) la pose, dans learn().
          remember('choice');
          st.phase = 'done';
        }
        render();
      });
      if (started === false) {
        st.phase = 'steps';
        st.error = '{{Une opération est déjà en cours.}}';
        render();
      }
    }

    function evaluate() {
      learn();
      // L'écran de fin ne survit pas à un démon qui dit que la publication a échoué : retour à l'étape 4.
      if (st.phase === 'done' && publishFailed(st.status) && !publishedOk(st.status, summary(), local())) {
        st.phase = 'steps';
        st.visible = true;
        if (!st.mode) st.mode = 'auto';
      }
      if (st.closed || st.mode === 'manual' || st.phase !== 'steps') { render(); return; }
      var show = shouldShow(st.status, readState(), local(), summary());
      if (show && (typeof env.canAutoShow !== 'function' || env.canAutoShow())) {
        st.visible = true;
        st.mode = 'auto';
      } else if (!show && st.mode === 'auto' && (local().dismissed || publishedOk(st.status, summary(), local()))) {
        // Affiché seul, le guide reste là tant que rien n'est publié : une relecture terminée en échec rend
        // l'installation « connue » mais l'étape 4 doit encore proposer de réessayer.
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

    // Front v2 (Lot 9a) : quatre statuts au plus (OK / À corriger / À vérifier / En attente).
    var CHECK_WORDS = { ok: '{{OK}}', fail: '{{À corriger}}', warn: '{{À vérifier}}', wait: '{{En attente}}' };

    function checkRow(check, $dialogHolder, rerender) {
      var word = CHECK_WORDS[check.state];
      var lbl = { ok: 'is-ok', fail: 'is-warn', warn: 'is-todo', wait: 'is-off' }[check.state];
      var $row = $('<div class="j2ha-v2-row j2ha-v2-check" role="listitem"></div>').attr('data-check', check.key).addClass('is-' + check.state);
      $row.append(el('<span class="j2ha-v2-lbl"></span>', word).addClass(lbl));
      var $grow = $('<div class="j2ha-v2-grow"></div>');
      // Front v3 (Lot 3) : le titre du contrôle, puis un détail court sur la même ligne (date, broker) ; un détail long passe en
      // info-bulle ⓘ ; « En attente » le dit par l'info-bulle de la ligne grisée.
      var $head = el('<div class="j2ha-v2-check-title"></div>', check.title);
      if (check.detail && check.state !== 'wait') {
        if (check.detail.replace(/\{\{|\}\}/g, '').length <= 48) $head.append(el('<span class="j2ha-v2-muted j2ha-v2-small j2ha-v3-check-detail"></span>', ' · ' + check.detail));
        else $head.append($('<span></span>').text(' ')).append(info(check.detail, 'j2ha-v3-check-info'));
      }
      $grow.append($head);
      if (check.state === 'wait') $row.attr('title', '{{Corrigez d\'abord le point ci-dessus.}}');
      if (check.ask && check.state !== 'wait') {
        // « Je l'ai vu » mémorise le constat ; les trois causes n'apparaissent qu'en dépliant « Je ne vois pas… ».
        var $askActs = $('<div class="j2ha-v2-acts j2ha-v2-check-ask"></div>');
        var $help = $('<ul class="j2ha-v2-guide-causes j2ha-v2-small j2ha-v2-check-causes"></ul>').hide();
        HA_CAUSES.forEach(function (cause) { $help.append(el('<li></li>', cause)); });
        // Front v3 (Lot 3) : [Vu] / [Pas vu], même style ; la question est dans l'info-bulle.
        $askActs.append(button('{{Vu}}', 'btn-default j2ha-v2-check-haseen', function () {
          confirmHaSeen();
          if (typeof rerender === 'function') rerender();
        }).attr('title', '{{Je vois l\'appareil « Jeedom (jeedom2ha) » dans Home Assistant}}'));
        var $notSeen = button('{{Pas vu}}', 'btn-default j2ha-v2-check-hahelp', function () {
          var open = $notSeen.attr('aria-expanded') !== 'true';
          $notSeen.attr('aria-expanded', open ? 'true' : 'false');
          if (open) $help.show(); else $help.hide();
        }).attr('aria-expanded', 'false').attr('title', '{{Je ne vois pas l\'appareil dans Home Assistant}}');
        $askActs.append($notSeen);
        $grow.append($askActs);
        $grow.append($help);
      }
      $row.append($grow);
      if (check.remedy && check.state !== 'wait') {
        $row.append(button(check.remedy.label, 'btn-default j2ha-v2-check-remedy', function () {
          $dialogHolder.close();
          var fn = { config: actions.openConfig, rescan: actions.rescan, blocked: function () { if (actions.openFilter) actions.openFilter('blocked'); } }[check.remedy.action];
          if (typeof fn === 'function') fn();
        }));
      }
      return $row;
    }

    function openCheck() {
      if (!env.bootbox || typeof env.bootbox.dialog !== 'function') return null;
      var checks = checkInstall(st.status, readState(), summary(), local());
      var holder = { close: function () {} };
      var $content = $('<div class="j2ha-v2 j2ha-v2-checkbox"></div>');
      // Front v3 (Lot 3) : plus de phrase d'introduction ; les mots d'état se lisent seuls (l'ordre d'arrêt est dans l'info-bulle
      // de chaque ligne « En attente »).
      var $list = $('<div class="j2ha-v2-checks" role="list"></div>');
      function renderChecks() {
        checks = checkInstall(st.status, readState(), summary(), local());
        $list.empty();
        checks.forEach(function (check) { $list.append(checkRow(check, holder, renderChecks)); });
      }
      renderChecks();
      $content.append($list);

      // Pied « Pour le support » : le contenu existant de l'export du diagnostic (case et bouton, identifiants et
      // gestionnaire inchangés) est déplacé ici, puis rendu à sa place à la fermeture. Idem pour l'export de décision.
      var $support = $('<div class="j2ha-v2-check-support"></div>');
      $support.append(el('<h4 class="j2ha-v2-check-head"></h4>', '{{Pour le support}} ')
        .append(info('{{Un fichier qui décrit votre installation jeedom2ha. À joindre à votre message sur le forum.}}', 'j2ha-v3-support-info')));
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
        // Front v3 (Lot 3) : un seul style de lien (j2ha-v2-link) ; le rôle du journal en info-bulle.
        $li.append($('<a class="j2ha-v2-link" target="_blank" rel="noopener"></a>').attr('href', 'index.php?v=d&p=log&logfile=' + log[0]).attr('title', log[1]).text(log[0]));
        $logs.append($li);
      });
      $adv.append(el('<div class="j2ha-v2-small j2ha-v3-check-logs-head"></div>', '{{Journaux du plugin :}}'));
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
      return { checks: checks, dialog: dialog, close: holder.close, rerender: renderChecks };
    }

    return {
      onStatus: function (status) { st.status = status; evaluate(); },
      onSnapshot: function (snapshot) { st.snapshot = snapshot || null; evaluate(); },
      open: open,
      close: close,
      openCheck: openCheck,
      render: render,
      // Front v2 (Lot 9a) : l'utilisateur a-t-il confirmé voir l'appareil dans Home Assistant (mémoire de la page ou stockage) ?
      haConfirmed: function () { return local().haSeen === true; },
      state: function () { return { visible: st.visible, mode: st.mode, phase: st.phase, error: st.error }; },
    };
  }

  return {
    version: 2,
    STORAGE_KEYS: STORAGE_KEYS,
    STEP_KEYS: STEP_KEYS,
    HA_TOOLTIP: HA_TOOLTIP,
    HA_CONFIRMED_TOOLTIP: HA_CONFIRMED_TOOLTIP,
    shortDate: shortDate,
    haInfo: haInfo,
    publicationInfo: publicationInfo,
    haBarItem: haBarItem,
    relectureFusion: relectureFusion,
    summaryFrom: summaryFrom,
    computeSteps: computeSteps,
    shouldShow: shouldShow,
    publishedOk: publishedOk,
    publishFailed: publishFailed,
    knownInstall: knownInstall,
    checkInstall: checkInstall,
    readLocal: readLocal,
    createGuide: createGuide,
  };
}));
