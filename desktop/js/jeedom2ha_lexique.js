// Front v2 — Lot 2 : lexique de la fiche équipement, `window.Jeedom2haLexique`.
// Traduit en mots simples les causes et les conseils affichés, au gabarit unique « quoi / pourquoi / actions / aide »,
// et donne le libellé français des types génériques Jeedom (le code reste en infobulle).
// Module pur : aucun DOM, aucune E/S ; chargeable sous node (module.exports) comme dans la page (globale).
// Les libellés courts de `REASON_LABELS` (jeedom2ha_mapping_override.js) ne sont pas recopiés ni modifiés : ce module
// porte seulement les textes longs. Textes en français simple, sans point final dans les étiquettes d'action.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
    return;
  }
  root.Jeedom2haLexique = factory();
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  // --- Actions proposées par une fiche : une clé, un libellé. La page décide du geste (lien, bouton). ---
  var ACTIONS = {
    generic_types: 'Ouvrir les types génériques',
    equipment: 'Ouvrir l’équipement dans Jeedom',
    correct_type: 'Corriger le type…',
    plugin_config: 'Ouvrir la configuration du plugin',
    republish: 'Republier',
    // Front v2 (Lot 9a, point 9) : un blocage par CONFIANCE (le plugin hésite, ou le nom contredit les types) ne se lève pas
    // en changeant le type (la confiance est gardée par le démon) : seul le réglage « Toujours » de l'équipement le lève.
    publish_anyway: 'Publier quand même',
    rename: 'Renommer l’équipement dans Jeedom, puis Relire Jeedom',
  };

  function action(key) {
    return { key: key, label: ACTIONS[key] };
  }

  function plural(count, one, many) {
    return count > 1 ? many : one;
  }

  function countOf(context) {
    var n = context && typeof context.count === 'number' && isFinite(context.count) ? Math.floor(context.count) : 0;
    return n > 0 ? n : 0;
  }

  function quoted(word) {
    return '« ' + word + ' »';
  }

  // Phrase d'explication des types génériques, dite à l'identique partout où elle sert.
  var GENERIC_TYPES_SENTENCE = 'Dans Jeedom, chaque commande peut porter un « type générique » qui dit son rôle '
    + '(par exemple « Lumière État », « Lumière Bouton On »). Sans lui, le plugin ne peut rien en déduire.';
  var GENERIC_TYPES_HELP = 'C’est la voie durable : elle sert aussi aux autres plugins.';
  var RELOAD_HELP = 'Une fois la correction faite dans Jeedom, cliquez sur Relire Jeedom.';

  // Front v2 (Lot 9a, point 9) : ce que fait « Publier quand même » (réglage « Toujours » de l'équipement, puis « Appliquer »).
  var PUBLISH_ANYWAY_HELP = 'Cliquez sur « Publier quand même » : l’équipement passe sur « Toujours » et sera publié avec le type '
    + 'que lui donnent ses types génériques, après « Appliquer ».';

  // Codes dont le blocage se lève par « Publier quand même » (réglage « Toujours ») et non en changeant le type.
  var PUBLISH_ANYWAY_CODES = ['ambiguous_skipped', 'name_heuristic_rejection', 'switch_state_orphan', 'probable_skipped', 'low_confidence'];

  // Front v2 (Lot 9a) : phrase qui lève la contradiction apparente avec le réglage « En cas de doute : Publier quand même ».
  var NAME_CONTRADICTION_SENTENCE = 'Ce n’est pas un doute mais une contradiction : le réglage « En cas de doute sur un équipement » '
    + 'de la configuration ne s’y applique pas, et le plugin ne publie pas cet équipement de lui-même.';

  // Gabarit commun du blocage par le nom (cause) et du conseil « le nom dit… » (équipement publié).
  function nameTypeSheet(context) {
    var c = context || {};
    var quoi = c.name_word && c.type_word
      ? 'Non publié : le nom dit ' + quoted(c.name_word) + ', les types Jeedom disent ' + quoted(c.type_word) + '.'
      : 'Non publié : le nom de l’équipement et ses types Jeedom ne disent pas la même chose.';
    return {
      quoi: quoi,
      pourquoi: 'Le plugin ne tranche pas à votre place.',
      actions: ['correct_type', 'generic_types'],
      aide: 'Choisissez le type voulu, ou corrigez les types génériques dans Jeedom.',
    };
  }

  // --- Fiches des causes (codes de REASON_LABELS, raisons sans libellé, conseils) ---
  // Chaque entrée : function (context) → { quoi, pourquoi, actions: [clé…], aide }.
  // `context` (facultatif) : { count, name_word, type_word, plugin_name }.
  var SHEETS = {
    // Causes de blocage (corrigeables).
    ambiguous_skipped: function () {
      return {
        quoi: 'Non publié : le plugin hésite sur le type de cet équipement.',
        pourquoi: 'Les types génériques de ses commandes peuvent correspondre à plusieurs types Home Assistant. '
          + 'Le plugin ne tranche pas à votre place : le réglage de la configuration « En cas de doute » ne s’applique pas à ce cas.',
        actions: ['publish_anyway', 'generic_types'],
        aide: PUBLISH_ANYWAY_HELP + ' Ou précisez les types génériques dans Jeedom, puis cliquez sur Relire Jeedom.',
      };
    },
    name_heuristic_rejection: function (context) {
      var sheet = nameTypeSheet(context);
      // Front v2 (Lot 9a, regard neuf v2) : la configuration annonce « En cas de doute : Publier quand même » ; ce cas n'est
      // pas un doute mais une contradiction, que ce réglage ne publie pas. Une phrase, puis quoi faire.
      sheet.pourquoi = NAME_CONTRADICTION_SENTENCE;
      // Point 9 : « Corriger le type… » ne lève pas ce blocage (la contradiction reste) : il n'est plus proposé ici.
      sheet.actions = ['publish_anyway', 'rename'];
      sheet.aide = PUBLISH_ANYWAY_HELP + ' Ou retirez ce mot du nom de l’équipement dans Jeedom, puis cliquez sur Relire Jeedom.';
      return sheet;
    },
    duplicate_generic_types: function () {
      return {
        quoi: 'Non publié : le même type générique est posé sur plusieurs commandes.',
        pourquoi: 'Le plugin ne sait pas laquelle utiliser.',
        actions: ['generic_types'],
        aide: 'Gardez ce type générique sur une seule commande. ' + RELOAD_HELP,
      };
    },
    conflicting_generic_types: function () {
      return {
        quoi: 'Non publié : les types génériques de cet équipement se contredisent.',
        pourquoi: 'Ils décrivent des appareils différents (par exemple une lumière et un volet).',
        actions: ['generic_types'],
        aide: 'Gardez des types génériques d’une seule famille. ' + RELOAD_HELP,
      };
    },
    switch_state_orphan: function () {
      return {
        quoi: 'Non publié : un état existe, mais aucun ordre On / Off.',
        pourquoi: 'Sans ordre, il n’y a rien à piloter. Il peut être publié en lecture seule.',
        actions: ['correct_type', 'publish_anyway', 'equipment'],
        aide: 'Choisissez « Capteur binaire (binary_sensor) » comme type, puis « Publier quand même » ; ou ajoutez les ordres dans Jeedom.',
      };
    },
    probable_skipped: function () {
      return {
        quoi: 'Non publié : le plugin n’est pas assez sûr du type.',
        pourquoi: 'La configuration du plugin ne publie que les types sûrs.',
        actions: ['publish_anyway', 'plugin_config'],
        aide: PUBLISH_ANYWAY_HELP + ' Ou choisissez « Publier quand même (recommandé) » sous « En cas de doute sur un équipement » dans la configuration du plugin.',
      };
    },
    low_confidence: function () {
      return {
        quoi: 'Non publié : le plugin n’est pas assez sûr du type.',
        pourquoi: 'La confiance obtenue est inférieure à celle demandée par la configuration du plugin.',
        actions: ['publish_anyway', 'plugin_config'],
        aide: PUBLISH_ANYWAY_HELP + ' Ou précisez les types génériques dans Jeedom.',
      };
    },
    no_generic_type_configured: function () {
      return {
        quoi: 'Non publié : Jeedom ne sait pas à quoi servent ces commandes.',
        pourquoi: GENERIC_TYPES_SENTENCE,
        actions: ['generic_types'],
        aide: 'Ouvrez les types génériques et indiquez le rôle de chaque commande. ' + GENERIC_TYPES_HELP,
      };
    },
    no_mapping: function () {
      return {
        quoi: 'Non publié : aucun type Home Assistant ne correspond.',
        pourquoi: 'Les types génériques de ces commandes ne suffisent pas à reconnaître l’appareil.',
        actions: ['generic_types', 'correct_type'],
        aide: GENERIC_TYPES_HELP,
      };
    },
    skipped_no_mapping_candidate: function () {
      return {
        quoi: 'Non publié : aucun type Home Assistant à proposer.',
        pourquoi: 'Le plugin n’a trouvé aucun type possible pour cet équipement.',
        actions: ['generic_types'],
        aide: GENERIC_TYPES_HELP,
      };
    },
    no_projection_possible: function () {
      return {
        quoi: 'Non publié : aucune commande utilisable.',
        pourquoi: 'Aucune commande info ou action de cet équipement ne peut devenir une entité Home Assistant.',
        actions: ['equipment', 'generic_types'],
        aide: 'Vérifiez les commandes de l’équipement dans Jeedom.',
      };
    },
    ha_missing_command_topic: function () {
      return {
        quoi: 'Non publié : rien à piloter.',
        pourquoi: 'Ce type Home Assistant demande des ordres (On / Off par exemple), et aucun n’est reconnu.',
        actions: ['generic_types', 'correct_type'],
        aide: 'Typez les ordres dans Jeedom, ou choisissez un type en lecture seule.',
      };
    },
    ha_missing_state_topic: function () {
      return {
        quoi: 'Non publié : pas de retour d’état.',
        pourquoi: 'Ce type Home Assistant a besoin d’une commande info qui donne l’état, et aucune n’est reconnue.',
        actions: ['equipment'],
        aide: 'Vérifiez dans Jeedom que l’état de l’appareil est bien une commande info typée.',
      };
    },
    discovery_publish_failed: function () {
      return {
        quoi: 'Non publié : l’envoi à Home Assistant a échoué la dernière fois.',
        pourquoi: 'Le broker MQTT n’a pas accepté le message, ou la connexion était coupée.',
        actions: ['republish'],
        aide: 'Vérifiez la connexion MQTT dans la barre d’état, puis republiez.',
      };
    },
    // Raisons sans libellé aujourd'hui dans REASON_LABELS.
    ha_missing_required_option: function () {
      return {
        quoi: 'Non publié : une information obligatoire manque.',
        pourquoi: 'Home Assistant exige une information que les commandes de cet équipement ne donnent pas.',
        actions: ['generic_types', 'correct_type'],
        aide: 'Vérifiez les types génériques, ou choisissez un autre type.',
      };
    },
    ha_missing_temperature_command_topic: function () {
      return {
        quoi: 'Non publié : pas d’ordre pour régler la température.',
        pourquoi: 'Un thermostat dans Home Assistant demande une commande qui règle la consigne.',
        actions: ['generic_types', 'correct_type'],
        aide: 'Typez la commande de consigne dans Jeedom, ou choisissez un capteur en lecture seule.',
      };
    },
    local_availability_publish_failed: function () {
      return {
        quoi: 'La disponibilité n’a pas pu être envoyée à Home Assistant.',
        pourquoi: 'Le broker MQTT n’a pas accepté le message. Home Assistant peut afficher l’équipement indisponible.',
        actions: ['republish'],
        aide: 'Vérifiez la connexion MQTT dans la barre d’état, puis republiez.',
      };
    },
    // Commandes ignorées (rien à corriger).
    no_supported_generic_type: function () {
      return {
        quoi: 'Pas d’équivalent dans Home Assistant.',
        pourquoi: 'Ce type générique n’est pas encore pris en charge par le plugin.',
        actions: [],
        aide: 'Rien à faire : la commande est simplement ignorée.',
      };
    },
    command_not_covered: function () {
      return {
        quoi: 'Pas d’équivalent dans Home Assistant.',
        pourquoi: 'Cette commande ne correspond à aucune entité publiée.',
        actions: [],
        aide: 'Rien à faire : la commande est simplement ignorée.',
      };
    },
    ha_component_not_in_product_scope: function () {
      return {
        quoi: 'Non pris en charge par le plugin.',
        pourquoi: 'Ce type Home Assistant n’est pas encore publié par jeedom2ha.',
        actions: [],
        aide: 'Rien à faire : la commande est simplement ignorée.',
      };
    },
    // Codes d'état (pas des erreurs).
    disabled_eqlogic: function () {
      return {
        quoi: 'Désactivé dans Jeedom.',
        pourquoi: 'Un équipement désactivé n’est jamais publié.',
        actions: ['equipment'],
        aide: 'Activez-le dans Jeedom pour le publier.',
      };
    },
    excluded_eqlogic: function () {
      return {
        quoi: 'Exclu : cet équipement est dans la liste des exclusions.',
        pourquoi: 'Un équipement exclu n’est pas publié dans Home Assistant.',
        actions: [],
        aide: 'Choisissez « Automatique » pour ne plus l’exclure.',
      };
    },
    excluded_plugin: function (context) {
      var name = context && context.plugin_name ? ' ' + quoted(context.plugin_name) : '';
      return {
        quoi: 'Exclu par son plugin' + name + '.',
        pourquoi: 'Les équipements de ce plugin ne sont pas publiés dans Home Assistant.',
        actions: ['plugin_config'],
        aide: 'Retirez ce plugin de « Plugins exclus » dans la configuration du plugin.',
      };
    },
    excluded_object: function () {
      return {
        quoi: 'Exclu par sa pièce.',
        pourquoi: 'Toute la pièce est exclue de Home Assistant.',
        actions: [],
        aide: 'Ne plus exclure la pièce depuis ses « Autres actions ».',
      };
    },
    publication_excluded_eqlogic: function () {
      return {
        quoi: 'Exclu : réglage « Jamais » sur cet équipement.',
        pourquoi: 'Vous avez choisi de ne pas le publier.',
        actions: [],
        aide: 'Choisissez « Automatique » pour revenir au choix du plugin.',
      };
    },
    publication_excluded_command: function () {
      return {
        quoi: 'Exclue : réglage « Jamais » sur cette entité.',
        pourquoi: 'Vous avez choisi de ne pas la publier.',
        actions: [],
        aide: 'Choisissez « Automatique » pour revenir au choix du plugin.',
      };
    },
    publication_forced: function () {
      return {
        quoi: 'Publié par votre réglage « Toujours ».',
        pourquoi: 'Le plugin hésitait ; votre réglage l’emporte.',
        actions: [],
        aide: 'Choisissez « Automatique » pour revenir au choix du plugin.',
      };
    },
    sure_mapping: function () {
      return {
        quoi: 'Type reconnu : publication normale.',
        pourquoi: 'Les types génériques suffisent à reconnaître l’appareil.',
        actions: [],
        aide: '',
      };
    },
    no_commands: function () {
      return {
        quoi: 'Rien à publier : aucune commande dans Jeedom.',
        pourquoi: 'Sans commande, il n’y a rien à montrer dans Home Assistant.',
        actions: ['equipment'],
        aide: 'Ajoutez des commandes à l’équipement dans Jeedom.',
      };
    },

    // Conseils (équipement publié mais dégradé) — codes `hints` du démon.
    actions_not_linked_to_state: function (context) {
      var n = countOf(context);
      var quoi = n > 1
        ? n + ' sorties pourraient être pilotables.'
        : 'Cet équipement pourrait être pilotable.';
      return {
        quoi: quoi,
        pourquoi: 'Les ordres On et Off existent, mais Jeedom ne dit pas à quel état chacun correspond. '
          + (n > 1 ? 'Elles sont donc publiées en lecture seule.' : 'Il est donc publié en lecture seule.'),
        actions: ['equipment'],
        aide: 'Dans chaque ordre On / Off, renseignez le champ « Valeur » avec l’état de la même sortie, '
          + 'puis cliquez sur Relire Jeedom.',
      };
    },
    binary_state_without_orders: function () {
      return {
        quoi: 'Publié comme capteur d’ouverture.',
        pourquoi: 'Sans ordres Ouvrir et Fermer typés, Home Assistant peut seulement lire son état.',
        actions: ['generic_types'],
        aide: 'Dans les types génériques de Jeedom, donnez aux ordres d’ouverture et de fermeture leur type de portail '
          + 'ou de garage, puis cliquez sur Relire Jeedom.',
      };
    },
    speed_not_carried: function () {
      return {
        quoi: 'La vitesse n’est pas reprise.',
        pourquoi: 'Le plugin publie ce ventilateur comme un interrupteur (marche / arrêt). '
          + 'Les ventilateurs à vitesse ne sont pas encore pris en charge.',
        actions: [],
        aide: '',
      };
    },
    name_type_mismatch: function (context) {
      return nameTypeSheet(context);
    },
  };

  // Codes de conseil (mention « Conseil », jamais un état).
  var HINT_CODES = ['actions_not_linked_to_state', 'binary_state_without_orders', 'speed_not_carried', 'name_type_mismatch'];

  /**
   * Fiche d'une cause ou d'un conseil : { code, known, quoi, pourquoi, actions: [{ key, label }], aide }.
   * Code inconnu (démon plus récent) : « Cause non répertoriée », le code reste lisible dans les détails techniques.
   */
  function causeSheet(code, context) {
    var key = typeof code === 'string' ? code : '';
    var build = key && Object.prototype.hasOwnProperty.call(SHEETS, key) ? SHEETS[key] : null;
    if (!build) {
      return {
        code: key || null,
        known: false,
        quoi: 'Cause non répertoriée.',
        pourquoi: 'Le démon signale une cause que cette page ne sait pas encore expliquer.',
        actions: [],
        aide: 'Le code est donné dans « Détails techniques » : il aide le support.',
      };
    }
    var sheet = build(context || {});
    return {
      code: key,
      known: true,
      quoi: sheet.quoi,
      pourquoi: sheet.pourquoi,
      actions: sheet.actions.map(action),
      aide: sheet.aide || '',
    };
  }

  /**
   * Front v2 (Lot 9a, point 8) : mots techniques encore présents dans des libellés figés (`REASON_LABELS`) ou dans des textes
   * du démon (intouchable). Traduits AU MOMENT DE L'AFFICHAGE ; le texte d'origine reste disponible (« Détails techniques »).
   * Chaque entrée : [texte cherché, texte affiché] ; ordre = priorité (le plus long d'abord).
   */
  var USER_WORDS = [
    ['confiance « probable » exclue par la politique « sûr uniquement »',
      'reconnu avec un léger doute, non publié avec le réglage « Ne publier que les équipements reconnus avec certitude »'],
    ['politique « sûr uniquement »', 'réglage « Ne publier que les équipements reconnus avec certitude »'],
    ['type non couvert par la V1 du plugin', 'type pas encore pris en charge par le plugin'],
    ['dans la V1 du plugin', 'dans cette version du plugin'],
    ['la V1 du plugin', 'cette version du plugin'],
    ['échec de publication MQTT au dernier sync', 'échec de la publication MQTT à la dernière relecture'],
    ['lors du dernier sync', 'lors de la dernière relecture'],
    ['au dernier sync', 'à la dernière relecture'],
    ['Parc global', 'Toute la maison'],
    // Raisons de `publicationActionState` (jeedom2ha_mapping_override.js, ajouts seuls : texte d'origine gardé à la source).
    ['Aucune commande clé propre à cette entité.', 'Cette entité ne se règle pas seule : réglez l’équipement entier.'],
    ['Projection invalide pour ce type HA.', 'Ce type Home Assistant est invalide pour cette entité.'],
  ];

  /** Texte affichable : mots techniques remplacés (voir USER_WORDS) ; un texte sans ces mots est rendu tel quel. */
  function userWords(text) {
    if (typeof text !== 'string' || text === '') return typeof text === 'string' ? text : '';
    var out = text;
    USER_WORDS.forEach(function (pair) {
      if (out.indexOf(pair[0]) !== -1) out = out.split(pair[0]).join(pair[1]);
    });
    return out;
  }

  /**
   * Front v2 (Lot 9a, regard neuf v2) : ligne « N commandes bloquées : … » d'un groupe de `groupBlockedCauses`, enrichie
   * quand la cause nomme un mot et un type connus. Les libellés figés de `REASON_LABELS` ne sont pas modifiés : seul le
   * rendu change. `context` : { matched_keyword, ha_entity_type } (lus dans l'arbre du démon, voir
   * `Jeedom2haHaSide.rejectionContext`) ; sans eux, le libellé du groupe tel quel.
   */
  function causeLine(group, context) {
    var g = group || {};
    var n = typeof g.count === 'number' && g.count > 0 ? Math.floor(g.count) : 0;
    var label = typeof g.label === 'string' ? g.label : '';
    var c = context || {};
    if (g.code === 'name_heuristic_rejection' && typeof c.matched_keyword === 'string' && c.matched_keyword
      && typeof c.ha_entity_type === 'string' && c.ha_entity_type) {
      label = 'le mot ' + quoted(c.matched_keyword) + ' du nom écarte le type ' + haTypeLabel(c.ha_entity_type);
    } else {
      label = userWords(label);
    }
    return n + ' ' + plural(n, 'commande bloquée', 'commandes bloquées') + ' : ' + label;
  }

  function knownCodes() {
    return Object.keys(SHEETS);
  }

  function isHintCode(code) {
    return HINT_CODES.indexOf(code) !== -1;
  }

  // --- Types génériques Jeedom : libellés français (ceux de l'écran « Types d'équipement » du cœur) ---
  var GENERIC_TYPE_LABELS = {
    LIGHT_STATE: 'Lumière État',
    LIGHT_STATE_BOOL: 'Lumière État (binaire)',
    LIGHT_ON: 'Lumière Bouton On',
    LIGHT_OFF: 'Lumière Bouton Off',
    LIGHT_TOGGLE: 'Lumière Bascule',
    LIGHT_SLIDER: 'Lumière Variateur',
    LIGHT_BRIGHTNESS: 'Lumière Luminosité',
    LIGHT_COLOR: 'Lumière Couleur',
    LIGHT_SET_COLOR: 'Lumière Couleur (ordre)',
    LIGHT_COLOR_TEMP: 'Lumière Température de couleur',
    LIGHT_SET_COLOR_TEMP: 'Lumière Température de couleur (ordre)',
    LIGHT_MODE: 'Lumière Mode',
    ENERGY_STATE: 'Prise État',
    ENERGY_ON: 'Prise Bouton On',
    ENERGY_OFF: 'Prise Bouton Off',
    ENERGY_SLIDER: 'Prise Variateur',
    SWITCH_STATE: 'Interrupteur État',
    SWITCH_ON: 'Interrupteur Bouton On',
    SWITCH_OFF: 'Interrupteur Bouton Off',
    FLAP_STATE: 'Volet État',
    FLAP_UP: 'Volet Bouton Monter',
    FLAP_DOWN: 'Volet Bouton Descendre',
    FLAP_STOP: 'Volet Bouton Stop',
    FLAP_SLIDER: 'Volet Position',
    FLAP_BSO_STATE: 'Volet BSO État',
    FLAP_BSO_UP: 'Volet BSO Bouton Monter',
    FLAP_BSO_DOWN: 'Volet BSO Bouton Descendre',
    FLAP_TILT_STATE: 'Volet Inclinaison État',
    FLAP_TILT_SLIDER: 'Volet Inclinaison',
    BARRIER_STATE: 'Portail État',
    BARRIER_OPEN: 'Portail Bouton Ouvrir',
    BARRIER_CLOSE: 'Portail Bouton Fermer',
    GARAGE_STATE: 'Garage État',
    GB_OPEN: 'Portail ou garage Bouton Ouvrir',
    GB_CLOSE: 'Portail ou garage Bouton Fermer',
    GB_TOGGLE: 'Portail ou garage Bouton Bascule',
    GARAGE_OPEN: 'Garage Bouton Ouvrir',
    GARAGE_CLOSE: 'Garage Bouton Fermer',
    LOCK_STATE: 'Serrure État',
    LOCK_OPEN: 'Serrure Bouton Ouvrir',
    LOCK_CLOSE: 'Serrure Bouton Fermer',
    FAN_STATE: 'Ventilateur État',
    FAN_ON: 'Ventilateur Bouton On',
    FAN_OFF: 'Ventilateur Bouton Off',
    FAN_SPEED_STATE: 'Ventilateur Vitesse État',
    FAN_SPEED: 'Ventilateur Vitesse',
    HEATING_STATE: 'Chauffage État',
    HEATING_ON: 'Chauffage Bouton On',
    HEATING_OFF: 'Chauffage Bouton Off',
    HEATING_OTHER: 'Chauffage Autre',
    THERMOSTAT_STATE: 'Thermostat État',
    THERMOSTAT_TEMPERATURE: 'Thermostat Température ambiante',
    THERMOSTAT_SETPOINT: 'Thermostat Consigne',
    THERMOSTAT_SET_SETPOINT: 'Thermostat Régler la consigne',
    THERMOSTAT_MODE: 'Thermostat Mode',
    THERMOSTAT_SET_MODE: 'Thermostat Changer de mode',
    TEMPERATURE: 'Température',
    HUMIDITY: 'Humidité',
    BRIGHTNESS: 'Luminosité',
    PRESSURE: 'Pression',
    CO2: 'CO2',
    POWER: 'Puissance électrique',
    CONSUMPTION: 'Consommation électrique',
    VOLTAGE: 'Tension',
    BATTERY: 'Batterie',
    BATTERY_CHARGING: 'Batterie en charge',
    PRESENCE: 'Présence',
    OPENING: 'Porte',
    OPENING_WINDOW: 'Fenêtre',
    SMOKE: 'Détection de fumée',
    FLOOD: 'Inondation',
    SABOTAGE: 'Sabotage',
    SHOCK: 'Choc',
    UV: 'UV',
    NOISE: 'Bruit',
    RAIN_CURRENT: 'Pluie (actuelle)',
    WIND_SPEED: 'Vent (vitesse)',
    MODE_STATE: 'Mode',
    MODE_SET_STATE: 'Changer de mode',
    ALARM_STATE: 'Alarme État',
    ALARM_ENABLE_STATE: 'Alarme État activée',
    ALARM_MODE: 'Alarme Mode',
    ALARM_ARMED: 'Alarme Armer',
    ALARM_RELEASED: 'Alarme Libérer',
    ALARM_SET_MODE: 'Alarme Changer de mode',
    GENERIC_INFO: 'Générique (info)',
    GENERIC_ACTION: 'Générique (action)',
    DONT: 'Ne pas tenir compte',
  };

  /** Libellé français d'un type générique : { label, code } ; code inconnu → libellé = code ; vide → null. */
  function genericTypeLabel(code) {
    if (typeof code !== 'string' || !code) {
      return null;
    }
    var label = Object.prototype.hasOwnProperty.call(GENERIC_TYPE_LABELS, code) ? GENERIC_TYPE_LABELS[code] : code;
    return { label: label, code: code };
  }

  // --- Types Home Assistant : « Lumière (light) » partout ---
  var HA_TYPE_LABELS = {
    alarm_control_panel: 'Alarme',
    binary_sensor: 'Capteur binaire',
    button: 'Bouton',
    climate: 'Thermostat',
    cover: 'Volet',
    fan: 'Ventilateur',
    light: 'Lumière',
    lock: 'Serrure',
    number: 'Nombre',
    scene: 'Scène',
    select: 'Liste de choix',
    sensor: 'Capteur',
    switch: 'Interrupteur',
    valve: 'Vanne',
  };

  /** « Lumière (light) » ; type inconnu → le code seul ; vide → « Entité Home Assistant ». */
  function haTypeLabel(type) {
    if (typeof type !== 'string' || !type) {
      return 'Entité Home Assistant';
    }
    return Object.prototype.hasOwnProperty.call(HA_TYPE_LABELS, type) ? HA_TYPE_LABELS[type] + ' (' + type + ')' : type;
  }

  // --- Capacités dites en verbes ---
  var CAPABILITY_VERBS = {
    on_off: ['allumer', 'éteindre'],
    open_close: ['ouvrir', 'fermer'],
    stop: ['arrêter'],
    position: ['régler la position'],
    tilt: ['orienter'],
    brightness: ['régler la luminosité'],
    temperature: ['régler la température'],
    mode: ['changer de mode'],
    press: ['déclencher'],
    lock: ['verrouiller', 'déverrouiller'],
    read: ['lire l’état'],
  };
  var CAPABILITY_ORDER = ['on_off', 'open_close', 'stop', 'position', 'tilt', 'brightness', 'temperature', 'mode', 'press', 'lock', 'read'];

  /** Verbes d'une liste de capacités, dans un ordre stable et sans doublon. */
  function capabilityVerbs(capabilities) {
    var list = Array.isArray(capabilities) ? capabilities : [];
    var verbs = [];
    CAPABILITY_ORDER.forEach(function (cap) {
      if (list.indexOf(cap) === -1) return;
      CAPABILITY_VERBS[cap].forEach(function (verb) {
        if (verbs.indexOf(verb) === -1) verbs.push(verb);
      });
    });
    return verbs;
  }

  return {
    version: 2,
    ACTIONS: ACTIONS,
    HINT_CODES: HINT_CODES.slice(),
    GENERIC_TYPE_LABELS: GENERIC_TYPE_LABELS,
    HA_TYPE_LABELS: HA_TYPE_LABELS,
    causeSheet: causeSheet,
    causeLine: causeLine,
    PUBLISH_ANYWAY_CODES: PUBLISH_ANYWAY_CODES.slice(),
    canPublishAnyway: function (code) { return PUBLISH_ANYWAY_CODES.indexOf(code) !== -1; },
    userWords: userWords,
    USER_WORDS: USER_WORDS,
    knownCodes: knownCodes,
    isHintCode: isHintCode,
    genericTypeLabel: genericTypeLabel,
    haTypeLabel: haTypeLabel,
    capabilityVerbs: capabilityVerbs,
    plural: plural,
  };
}));
