// Front v2 — Lot 9a : finitions écran issues du second « regard neuf » (v2). Modules purs et VRAI code de la surface sur le
// faux DOM : portée du choix de type (entité, pas commande), libellé « Automatique », ligne de cause qui nomme le mot et le
// type, fiche « contradiction » qui mène à « Publier quand même » (réglage « Toujours » existant), repères « désactivé »,
// panneau « Choisir » (« dont N désactivés », exclus nommés par plugin), un seul libellé « Pilotable », mots du démon traduits.
// Données fictives (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const L = require('../../desktop/js/jeedom2ha_lexique.js');
const HS = require('../../desktop/js/jeedom2ha_ha_side.js');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const TP = require('../../desktop/js/jeedom2ha_type_panel.js');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const X = require('../../desktop/js/jeedom2ha_exclusions.js');
const { createDom } = require('./helpers/fake_dom');
const { createUi, BRIDGE_UP } = require('./helpers/ui_harness');
const { ACTION_OK } = require('./helpers/write_scenarios');
const { DEMO, demoRoom, diag } = require('./helpers/front_v2_demo_trees');
const { startPage, phpAvailable } = require('./helpers/page_b_harness');

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const plain = (text) => String(text).replace(/\{\{|\}\}/g, '').replace(/\s+/g, ' ').trim();
const maybe = phpAvailable ? it : it.skip;

function openFiche(tree) {
  const ui = createUi([demoRoom()], { pluginNames: { virtual: 'Virtuel' } });
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  ui.openRoomWith(9, [{ state: 'ok', result: { payload: tree } }]);
  const P = `.j2ha-eq-panel[data-eq-id="${tree.jeedom_eq_id}"] `;
  const text = (selector) => plain(ui.$(P + selector).text());
  const done = () => ui.win.Jeedom2haSurface.clearEquipment();
  return { ui, P, text, done };
}

/** Lampe typée « prise », projection VALIDE en interrupteur : seul le nom bloque (le réglage « Toujours » est possible). */
function lampeValide() {
  const t = DEMO.lampePrise(true);
  const d = () => diag('ambiguous_skipped', { code: 'name_heuristic_rejection', type: 'switch', valid: true });
  t.commands.forEach((c) => { c.diagnostic = d(); c.override_types_allowed = ['light', 'switch']; });
  t.entities[0].decision = d();
  t.equipment_decision = d();
  return t;
}

describe('Lot 9a — lexique : ligne de cause, contradiction, mots du démon', () => {
  it('« le mot « lampe » du nom écarte le type … » quand le démon donne le mot et le type ; sinon le libellé figé', () => {
    const group = { code: 'name_heuristic_rejection', label: M.REASON_LABELS.name_heuristic_rejection, count: 3 };
    assert.equal(L.causeLine(group, { matched_keyword: 'lampe', ha_entity_type: 'switch' }),
      '3 commandes bloquées : le mot « lampe » du nom écarte le type Interrupteur (switch)');
    assert.equal(L.causeLine(group, null), M.buildCauseNoticeText(group), 'sans contexte : le texte de toujours');
    assert.equal(L.causeLine({ code: 'name_heuristic_rejection', label: 'x', count: 1 }, { matched_keyword: 'lampe' }), '1 commande bloquée : x');
    assert.ok(M.REASON_LABELS.name_heuristic_rejection === 'un mot du nom de l’équipement écarte ce type', 'libellé figé inchangé');
  });

  it('le contexte est lu dans l’arbre du démon, jamais deviné', () => {
    assert.deepEqual(HS.rejectionContext(DEMO.lampePrise(true)), { matched_keyword: 'lampe', ha_entity_type: 'switch' });
    assert.equal(HS.rejectionContext(DEMO.lumiere(true)), null);
    assert.equal(HS.rejectionContext(null), null);
  });

  it('point 9 : contradiction et hésitation → « Publier quand même », jamais « Corriger le type… » seul', () => {
    for (const code of ['name_heuristic_rejection', 'ambiguous_skipped', 'probable_skipped', 'low_confidence']) {
      const sheet = L.causeSheet(code, {});
      assert.equal(sheet.actions[0].key, 'publish_anyway', code);
      assert.equal(sheet.actions[0].label, 'Publier quand même', code);
      assert.ok(!sheet.actions.some((a) => a.key === 'correct_type'), code + ' : le type ne lève pas un blocage de confiance');
      assert.match(sheet.aide, /« Publier quand même » : l’équipement passe sur « Toujours »/, code);
      assert.ok(L.canPublishAnyway(code), code);
    }
    const name = L.causeSheet('name_heuristic_rejection', {});
    assert.deepEqual(name.actions.map((a) => a.label), ['Publier quand même', 'Renommer l’équipement dans Jeedom, puis Relire Jeedom']);
    assert.match(name.pourquoi, /^Ce n’est pas un doute mais une contradiction/);
    const orphan = L.causeSheet('switch_state_orphan', {});
    assert.deepEqual(orphan.actions.map((a) => a.key), ['correct_type', 'publish_anyway', 'equipment'], 'type d’abord, puis « Toujours »');
    assert.equal(L.canPublishAnyway('no_generic_type_configured'), false);
  });

  it('point 8 : mots techniques traduits à l’affichage (libellés figés et textes du démon inchangés à la source)', () => {
    assert.equal(L.userWords(M.REASON_LABELS.probable_skipped),
      'reconnu avec un léger doute, non publié avec le réglage « Ne publier que les équipements reconnus avec certitude »');
    assert.equal(L.userWords(M.REASON_LABELS.no_supported_generic_type), 'type pas encore pris en charge par le plugin');
    assert.equal(L.userWords(M.REASON_LABELS.discovery_publish_failed), 'échec de la publication MQTT à la dernière relecture');
    assert.equal(L.userWords('Parc global'), 'Toute la maison');
    assert.equal(L.userWords('Rien à dire.'), 'Rien à dire.');
    assert.equal(L.causeLine({ code: 'probable_skipped', label: M.REASON_LABELS.probable_skipped, count: 2 }, null),
      '2 commandes bloquées : reconnu avec un léger doute, non publié avec le réglage « Ne publier que les équipements reconnus avec certitude »');
    for (const [, shown] of L.USER_WORDS) assert.doesNotMatch(shown, /sync|V1|sûr uniquement|Parc global|backend|forçage/);
  });
});

describe('Lot 9a — panneau « Corriger le type » : portée réelle du choix', () => {
  it('scopeOf : nom de l’entité et commandes qu’elle regroupe ; inconnue → repli honnête', () => {
    const raw = DEMO.lampePrise(true);
    const tree = M.normalizeTree(raw);
    assert.deepEqual(TP.scopeOf(tree, raw, 2312, 'Lampe Chevet'), { name: 'Lampe Chevet', commands: ['État', 'On', 'Off'], known: true });
    assert.deepEqual(TP.scopeOf(tree, raw, 9999, 'Lampe Chevet'), { name: 'Lampe Chevet', commands: [], known: false });
    assert.equal(TP.cellLabel({ override_applied: false }), 'Automatique');
  });

  // Revue #397 (Codex + coordinateur) : depuis le panneau, « Publier quand même » GARDE le type choisi (lampe typée prise →
  // lumière) : aperçu type + « Toujours » ensemble, puis saveMappingOverride, savePublicationOverride, publication ;
  // « Annuler » défait les deux.
  it('aperçu refusé pour cause de confiance : « Publier quand même » garde le type, enregistre type PUIS « Toujours »', async () => {
    const { ui, P, done } = openFiche(lampeValide());
    const link = ui.$(P + 'tr[data-cmd-id="2311"] .j2ha-type-link');
    assert.equal(plain(link.text()), 'Automatique');
    ui.click(P + 'tr[data-cmd-id="2311"] .j2ha-type-link');
    const panel = '.j2ha-v3-type-modal[data-eq-id="231"][data-type-panel-for="2311"] '; // Front v3 (Lot 3) : fenêtre posée sur body
    assert.equal(plain(ui.$(panel + '.j2ha-v2-type-title').text()), 'Type dans Home Assistant de « Lampe Chevet »');
    ui.$(`${panel}input[data-type="light"]`).prop('checked', true).trigger('change');
    await sleep(450);
    const refused = diag('ambiguous_skipped', { code: 'name_heuristic_rejection', type: 'light', valid: true });
    const first = ui.pending('previewMappingOverride')[0];
    assert.deepEqual({ ...first.data }, { action: 'previewMappingOverride', eqId: 231, cmdId: 2311, haEntityType: 'light' }, 'corps inchangé');
    first.respond({ state: 'ok', result: { status: 'ok', payload: {
      jeedom_eq_id: 231, mapped: true, covered: true, auto: lampeValide().equipment_decision, overridden: refused } } });
    assert.equal(ui.$(panel + '.j2ha-v2-type-save').prop('disabled'), true, 'enregistrer reste impossible');
    const box = ui.$(panel + '.j2ha-v2-type-anyway-box');
    assert.equal(box.length, 1, 'jamais un bouton grisé muet');
    // Garde levée (front v3, Lot 3) : une ligne « Le type seul ne suffit pas » ; l'explication passe en info-bulle ⓘ.
    assert.match(plain(box.text()), /Le type seul ne suffit pas/);
    // Garde levée (front v3, Lot 6) : le texte de ⓘ est dans `data-j2ha-tip` (bulle au clic), plus dans `title` ; même assertion.
    assert.match(plain(box.find('.j2ha-v3-info').attr('data-j2ha-tip')), /garde le type choisi et ajoute le réglage « Toujours »/);
    ui.click(panel + '.j2ha-v2-type-anyway');
    assert.equal(ui.$('.j2ha-v3-type-modal[data-eq-id="231"] .j2ha-v2-type-panel').length, 1, 'le panneau reste ouvert, le type choisi aussi');
    assert.equal(ui.$(`${panel}input[data-type="light"]`).prop('checked'), true);
    const both = ui.pending('previewMappingOverride').slice(-1)[0];
    assert.deepEqual({ ...both.data }, { action: 'previewMappingOverride', eqId: 231, cmdId: 2311, haEntityType: 'light', publicationPolicy: 'force_publish' },
      'un seul aperçu : le type choisi ET « Toujours »');
    const forced = diag('publication_forced', { type: 'light', valid: true, publish: true, code: 'name_heuristic_rejection' });
    both.respond({ state: 'ok', result: { status: 'ok', payload: { jeedom_eq_id: 231, mapped: true, covered: true,
      auto: lampeValide().equipment_decision, overridden: forced,
      entities_before: [{ ha_entity_type: 'switch', ha_default_entity_id: 'switch.jeedom2ha_eq_231', will_publish: false }],
      entities_after: [{ ha_entity_type: 'light', ha_default_entity_id: 'light.jeedom2ha_eq_231', ha_controllable: true, ha_capabilities: ['on_off'], will_publish: true }] } } });
    assert.match(plain(ui.$(panel + '.j2ha-v2-diff').text()), /Après\s*1 lumière/);
    // Garde levée (front v3, Lot 3) : libellé court, la suite en info-bulle.
    assert.match(plain(ui.$(panel + '.j2ha-v2-type-anyway-on').text()), /type choisi \+ « Toujours »/);
    const save = ui.$(panel + '.j2ha-v2-type-save');
    assert.equal(plain(save.text()), 'Enregistrer et publier quand même');
    assert.equal(save.prop('disabled'), false);
    assert.ok(!ui.calls.some((c) => ['saveMappingOverride', 'savePublicationOverride'].includes(c.action)), 'rien n’est écrit avant la validation');
    ui.click(panel + '.j2ha-v2-type-save');
    const t1 = ui.respond('saveMappingOverride', { state: 'ok', result: { status: 'ok' } });
    assert.deepEqual({ ...t1.data }, { action: 'saveMappingOverride', eqId: 231, cmdId: 2311, haEntityType: 'light' });
    const t2 = ui.respond('savePublicationOverride', { state: 'ok', result: { status: 'ok' } });
    assert.deepEqual({ ...t2.data }, { action: 'savePublicationOverride', eqId: 231, publicationPolicy: 'force_publish', cmdId: 2311 });
    ui.respond('executeHaAction', ACTION_OK);
    assert.match(plain(ui.$(P + '.j2ha-v2-type-toast').text()), /^Lampe Chevet est maintenant une lumière dans Home Assistant\.\s*Annuler$/);
    // « Annuler » défait les deux : « Toujours » retiré, puis retour au type précédent (automatique) et publication.
    ui.click(P + '.j2ha-v2-type-undo');
    const r1 = ui.respond('revertPublicationOverride', { state: 'ok', result: { status: 'ok' } });
    assert.deepEqual({ ...r1.data }, { action: 'revertPublicationOverride', eqId: 231, cmdId: 2311 });
    const r2 = ui.respond('revertMappingOverride', { state: 'ok', result: { status: 'ok' } });
    assert.deepEqual({ ...r2.data }, { action: 'revertMappingOverride', eqId: 231, cmdId: 2311 });
    ui.respond('executeHaAction', ACTION_OK);
    assert.match(plain(ui.$(P + '.j2ha-v2-type-toast').text()), /Réglage précédent rétabli\./);
    done();
  });

  it('changer de choix après « Publier quand même » revient à l’enregistrement simple', async () => {
    const { ui, P, done } = openFiche(lampeValide());
    ui.click(P + 'tr[data-cmd-id="2311"] .j2ha-type-link');
    const panel = '.j2ha-v3-type-modal[data-eq-id="231"][data-type-panel-for="2311"] '; // Front v3 (Lot 3) : fenêtre posée sur body
    ui.$(`${panel}input[data-type="light"]`).trigger('change');
    await sleep(450);
    const refused = diag('ambiguous_skipped', { code: 'name_heuristic_rejection', type: 'light', valid: true });
    ui.pending('previewMappingOverride')[0].respond({ state: 'ok', result: { status: 'ok', payload: { jeedom_eq_id: 231, mapped: true, covered: true, auto: refused, overridden: refused } } });
    ui.click(panel + '.j2ha-v2-type-anyway');
    ui.pending('previewMappingOverride').slice(-1)[0].respond({ state: 'ok', result: { status: 'ok', payload: { jeedom_eq_id: 231, mapped: true, covered: true, auto: refused,
      overridden: diag('publication_forced', { type: 'light', valid: true, publish: true }) } } });
    assert.equal(plain(ui.$(panel + '.j2ha-v2-type-save').text()), 'Enregistrer et publier quand même');
    ui.$(`${panel}input[data-type="auto"]`).trigger('change');
    assert.equal(plain(ui.$(panel + '.j2ha-v2-type-save').text()), 'Enregistrer et publier');
    done();
  });
});

describe('Lot 9a — fiche de cause : « Publier quand même »', () => {
  // Garde levée (front v3, Lot 2) : la bande dit le mot et le type en 4 mots ; le décompte et le libellé d'origine passent dans
  // « Détails techniques » (menu ⋯). Le bouton « Publier quand même » dit sa conséquence : « Publier en interrupteur ».
  it('la fiche nomme le mot et le type, et « Publier quand même » passe par l’aperçu « Toujours » de l’équipement', () => {
    const { ui, P, text, done } = openFiche(lampeValide());
    assert.equal(text('.j2ha-eq-notices .j2ha-eq-band-what'), 'Nom « lampe » ≠ type « prise »');
    assert.match(text('.j2ha-eq-tech'), /3 commandes bloquées : le mot « lampe » du nom écarte le type Interrupteur \(switch\)/);
    assert.match(text('.j2ha-eq-tech'), /Libellé d’origine : 3 commandes bloquées : un mot du nom de l’équipement écarte ce type/);
    assert.doesNotMatch(text('.j2ha-eq-notices'), /Le plugin ne tranche pas à votre place/);
    assert.equal(text('.j2ha-eq-notices .j2ha-v2-publish-anyway'), 'Publier en interrupteur');
    assert.equal(ui.$(P + '.j2ha-eq-notices .j2ha-v2-correct-type').length, 0);
    ui.click(P + '.j2ha-eq-notices .j2ha-v2-publish-anyway');
    const preview = ui.pending('previewMappingOverride').slice(-1)[0];
    assert.ok(preview, 'aperçu demandé');
    assert.equal(preview.data.publicationPolicy, 'force_publish');
    assert.equal(preview.data.cmdId, undefined, 'portée équipement');
    done();
  });

  // Garde levée (front v3, Lot 2) : « Toujours » n'est jamais grisé. Le bouton passe toujours par l'aperçu du démon (lecture
  // seule) ; c'est l'aperçu qui dit un refus, avant toute écriture. Déjà sur « Toujours » : la raison est dite, rien n'est demandé.
  it('« Publier en … » : toujours l’aperçu « Toujours » d’abord (jamais grisé) ; déjà « Toujours » : la raison est dite', () => {
    const { ui, P, done } = openFiche(DEMO.lampePrise(true));
    assert.notEqual(ui.$(P + '.j2ha-eq-controls .j2ha-seg-always').prop('disabled'), true);
    ui.click(P + '.j2ha-eq-notices .j2ha-v2-publish-anyway');
    const preview = ui.pending('previewMappingOverride').slice(-1)[0];
    assert.ok(preview, 'aperçu demandé');
    assert.equal(preview.data.publicationPolicy, 'force_publish');
    assert.ok(!ui.calls.some((c) => c.action === 'savePublicationOverride'), 'rien n’est écrit avant la confirmation');
    done();
    const forced = DEMO.lampePrise(true);
    forced.entities[0].publication_override = 'force_publish';
    forced.equipment_publication_override = 'force_publish';
    const second = openFiche(forced);
    const before = second.ui.calls.length;
    second.ui.click(second.P + '.j2ha-eq-notices .j2ha-v2-publish-anyway');
    assert.equal(second.ui.calls.length, before);
    assert.match(plain(second.ui.$(second.P + '.j2ha-eq-notices .j2ha-publication-error').text()), /déjà sur « Toujours »/);
    second.done();
  });

  it('un seul libellé « Pilotable » sur la fiche (sans « lire l’état ») ', () => {
    const t = DEMO.lumiere(true);
    t.entities[0].ha_capabilities = ['on_off', 'read'];
    const { ui, P, text, done } = openFiche(t);
    // Garde levée (front v3, Lot 2) : « Pilotable » est dit une fois, sur la ligne de l'entité ; les verbes vont en info-bulle.
    assert.equal(text('.j2ha-eq-capacity'), 'Pilotable');
    assert.equal(ui.$(P + '.j2ha-eq-capacity').length, 1);
    assert.equal(ui.$(P + '.j2ha-eq-capacity').attr('title'), 'allumer, éteindre');
    assert.doesNotMatch(text('.j2ha-eq-sides'), /lire l’état/);
    done();
  });
});

describe('Lot 9a — compteurs : pourquoi il manque un équipement', () => {
  it('inactiveMarks : désactivés et « rien à publier » comptés depuis l’état unique', () => {
    const room = { equipments: [{ state: 'published' }, { state: 'disabled' }, { state: 'disabled' }, { state: 'nothing_to_publish' }, { state: 'excluded' }] };
    assert.deepEqual(O.inactiveMarks(room).map((m) => [m.key, m.count, plain(m.text)]), [['disabled', 2, '2 désactivés'], ['nothing_to_publish', 1, '1 rien à publier']]);
    assert.deepEqual(O.inactiveMarks({ equipments: [] }), []);
  });

  // Garde levée (front v3, Lot 1, cible §1) : la tuile n'a plus de ligne de texte ; « 1 désactivé » devient une marque chiffrée
  // (icône fa-power-off + nombre, le mot en info-bulle et pour les lecteurs d'écran), toujours dans le nom accessible.
  maybe('tuile de pièce : « 1 désactivé » en marque chiffrée, dans le nom accessible', () => {
    const ui = startPage();
    const card = ui.$('#j2ha_roomCards .j2ha-room-card[data-object_id="3"]');
    const mark = card.find('.j2ha-room-marks .j2ha-mark-disabled');
    assert.equal(mark.length, 1);
    assert.equal(plain(mark.text()), '1 désactivé');
    assert.equal(plain(mark.attr('title')), '1 désactivé');
    assert.equal(mark.find('.fa-power-off').length, 1);
    assert.match(plain(card.attr('aria-label')), /1 désactivé/);
    assert.equal(card.find('.j2ha-v2-room-inactive').length, 0, 'plus de ligne de texte');
  });

  it('« Choisir » : « dont 1 désactivé dans Jeedom » ; par plugin, les exclus sont nommés', () => {
    const dom = createDom();
    const rooms = [{ object_id: 1, object_name: 'Buanderie', father_id: 0, excluded: false, equipments: [
      { eq_id: 1, eq_name: 'Lave-linge', enabled: true, eq_type: 'virtual' },
      { eq_id: 2, eq_name: 'Prise Désactivée', enabled: false, eq_type: 'virtual' },
      { eq_id: 3, eq_name: 'Sèche-linge', enabled: true, eq_type: 'virtual' },
    ] }];
    const d = (reason, publish) => ({ ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: publish,
      projection_validity: { is_valid: true, missing_capabilities: [], missing_fields: [], reason_code: null } });
    const entry = (id, reason, publish) => ({ jeedom_eq_id: id, equipment_decision: d(reason, publish), entities: [],
      commands: [{ jeedom_cmd_id: id * 10, covered: true, diagnostic: d(reason, publish), published_in_ha: publish }],
      sync_status: { published_in_ha: publish, synced_should_publish: publish, current_should_publish: publish, override_pending: false } });
    const snapshot = { kind: 'ok', view: { stale: false, equipments: { 1: entry(1, 'sure_mapping', true), 2: entry(2, 'sure_mapping', true), 3: entry(3, 'publication_excluded_eqlogic', false) } } };
    const panel = X.createPanel({ $: dom.$, bootbox: dom.bootbox, rooms: () => rooms, snapshot: () => snapshot, excludedPlugins: () => '',
      pluginNames: { virtual: 'Virtuel' }, apply: () => true });
    const res = panel.open({});
    const count = () => plain(res.root.find('.j2ha-v2-excl-group .j2ha-v2-excl-count').text());
    // Garde levée (front v3, Lot 3) : compteur « n/m » ; le détail (dont les désactivés) passe en info-bulle, et une marque
    // « ⏻ 1 » dit le désactivé.
    assert.equal(count(), '2/3');
    const countNode = res.root.find('.j2ha-v2-excl-group .j2ha-v2-excl-count');
    assert.equal(plain(countNode.attr('title')), '3 équipements · 2 non exclus dont 1 désactivé dans Jeedom · « Non exclu » ne veut pas dire « publié »');
    assert.equal(plain(res.root.find('.j2ha-v2-excl-group .j2ha-v3-excl-off').text()), '1');
    assert.equal(plain(res.root.find('.j2ha-v2-excl-group .j2ha-v3-excl-off').attr('title')), '1 désactivé dans Jeedom');
    res.root.find('.j2ha-v2-excl-mode button[data-mode="plugin"]').list[0].handlers.click.call(null, {});
    assert.equal(plain(res.root.find('.j2ha-v2-excl-group[data-kind="plugin"] .j2ha-v2-excl-names').text()), 'Exclu : Sèche-linge');
  });
});

describe('Lot 9a — point 8 : jargon retiré de l’écran', () => {
  it('aucun des mots relevés n’est plus écrit dans un texte affiché du front', () => {
    const fs = require('node:fs');
    const shown = (file) => fs.readFileSync(file, 'utf8').split('\n')
      .filter((line) => !/^\s*(\/\/|\*|\/\*)/.test(line)).join('\n');
    const files = ['desktop/js/jeedom2ha.js', 'desktop/js/jeedom2ha_mapping_surface.js', 'desktop/js/jeedom2ha_overview.js',
      'desktop/js/jeedom2ha_workview.js', 'desktop/js/jeedom2ha_guide.js', 'desktop/js/jeedom2ha_exclusions.js'];
    for (const file of files) {
      for (const marker of shown(file).match(/\{\{[^}]*\}\}/g) || []) {
        assert.doesNotMatch(marker, /Projection|forçage|backend|dashboards|commande clé|Parc global|dernier sync|sûr uniquement|V1 du plugin/, `${file} : ${marker}`);
      }
    }
    // Raisons de mapping_override.js (ajouts seuls) : traduites à l'affichage, texte d'origine inchangé à la source.
    const reason = M.publicationActionState({ decision: null, override_command_id: null }).reason;
    assert.match(reason, /commande clé/);
    assert.equal(L.userWords(reason), 'Cette entité ne se règle pas seule : réglez l’équipement entier.');
    assert.equal(L.userWords('Projection invalide pour ce type HA.'), 'Ce type Home Assistant est invalide pour cette entité.');
  });
});
