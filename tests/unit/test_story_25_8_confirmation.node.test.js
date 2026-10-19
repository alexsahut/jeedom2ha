// ARTEFACT — Story 25.8 (AC8, Q1 B, Q6, Q7, Q8) : la confirmation d'exclusion de pièce annonce un nombre d'ENTITÉS calculé par UNE
// fonction pure depuis la copie des états en mémoire (aucune requête avant le clic de confirmation), avec les pluriels accordés par
// le code ; la phrase des réglages en attente apparaît si et seulement si l'effectif maison « à appliquer » est non nul ; le bouton de
// confirmation est rouge pour « Exclure » et principal pour « Ne plus exclure » ; Annuler / croix / Échap n'écrivent rien et libèrent
// les réservations. Vrai code sur faux DOM ; identifiants fictifs (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const { startWorkview, phpAvailable } = require('./helpers/workview_harness');
const { plain } = require('./helpers/page_b_harness');

const maybe = phpAvailable ? it : it.skip;

const entity = (present) => ({ override_pending: false, present_in_ha: present });
const entry = (id, entities) => ({ jeedom_eq_id: id, entities });
const ROOMS = [{ object_id: 2, object_name: 'Pièce fictive', equipments: [{ eq_id: 201 }, { eq_id: 202 }, { eq_id: 203 }] }];
const snapshot = (equipments, overrides) => Object.assign({
  kind: 'ok',
  view: { stale: false, equipments, overview: { counts: { to_apply: 0 } } },
}, overrides || {});

describe('25.8 / AC8 — fonction pure du nombre d\'entités (Q1 B)', () => {
  it('compte les entités présentes dans Home Assistant des équipements de la pièce', () => {
    const impact = O.roomExclusionImpact(snapshot({
      201: entry(201, [entity(true), entity(true), entity(false)]),
      202: entry(202, [entity(true)]),
      203: entry(203, []),
    }), ROOMS, 2);
    assert.deepEqual(impact, { known: true, entities: 3, unknown: 0, unread: 0, pending: 0, atLeast: false });
  });

  it('une entité dont la présence est inconnue n\'est pas comptée mais signalée ; un équipement non lu aussi', () => {
    const impact = O.roomExclusionImpact(snapshot({
      201: entry(201, [entity(true), { override_pending: false }, entity(null)]),
      202: entry(202, [entity(false)]),
    }), ROOMS, 2);
    assert.equal(impact.entities, 1);
    assert.equal(impact.unknown, 2);
    assert.equal(impact.unread, 1);
  });

  it('lecture indisponible (en cours, indisponible, jamais synchronisé, copie périmée) : nombre inconnu (Q8)', () => {
    for (const kind of ['in_progress', 'unavailable', 'never_synced', null]) {
      const impact = O.roomExclusionImpact(snapshot({ 201: entry(201, [entity(true)]) }, { kind }), ROOMS, 2);
      assert.equal(impact.known, false, String(kind));
    }
    assert.equal(O.roomExclusionImpact(null, ROOMS, 2).known, false);
    const stale = snapshot({ 201: entry(201, [entity(true)]) });
    stale.view.stale = true;
    assert.equal(O.roomExclusionImpact(stale, ROOMS, 2).known, false, 'copie périmée');
  });

  it('l\'effectif des réglages en attente est celui de la maison (« à appliquer »)', () => {
    const snap = snapshot({ 201: entry(201, [entity(true)]) });
    snap.view.overview.counts.to_apply = 4;
    assert.equal(O.roomExclusionImpact(snap, ROOMS, 2).pending, 4);
  });

  it('pièce inconnue : aucun comptage', () => {
    const impact = O.roomExclusionImpact(snapshot({}), ROOMS, 99);
    assert.deepEqual([impact.entities, impact.unread], [0, 0]);
  });
});

describe('25.8 / AC8 — texte de la confirmation (D4)', () => {
  const known = (n, extra) => Object.assign({ known: true, entities: n, unknown: 0, unread: 0, pending: 0 }, extra || {});
  const dialog = (excluded, impact, name) => {
    const d = O.roomExclusionDialog({ name: name || 'Pièce fictive', excluded, impact });
    return { title: plain(d.title), lines: d.lines.map(plain), confirmLabel: plain(d.confirmLabel), danger: d.danger };
  };

  it('exclure : titre, pluriels accordés par le code, bouton rouge', () => {
    assert.equal(dialog(true, known(5)).title, 'Exclure la pièce « Pièce fictive » de Home Assistant ?');
    assert.deepEqual(dialog(true, known(5)).lines, ['5 entités seront retirées de Home Assistant.']);
    assert.deepEqual(dialog(true, known(1)).lines, ['1 entité sera retirée de Home Assistant.']);
    assert.deepEqual(dialog(true, known(0)).lines, ["Aucune entité n'est publiée dans cette pièce."]);
    const d = dialog(true, known(2));
    assert.equal(d.confirmLabel, 'Exclure la pièce');
    assert.equal(d.danger, true);
  });

  it('exclure, lecture indisponible : le nombre est dit inconnu et l\'action reste possible (Q8)', () => {
    const d = dialog(true, { known: false, entities: 0, unknown: 0, unread: 0, pending: 0 });
    assert.deepEqual(d.lines, ["Nombre d'entités inconnu : la lecture des états n'est pas disponible."]);
    assert.equal(d.danger, true);
  });

  it('la phrase des réglages en attente apparaît si et seulement si l\'effectif est non nul (Q6)', () => {
    assert.ok(!dialog(true, known(2, { pending: 0 })).lines.join(' ').includes('réglage'));
    assert.deepEqual(dialog(true, known(2, { pending: 3 })).lines, [
      '2 entités seront retirées de Home Assistant.',
      'La relecture appliquera aussi les 3 réglages en attente de la maison.',
    ]);
    assert.ok(dialog(true, known(2, { pending: 1 })).lines[1].includes('le réglage en attente de la maison'));
    assert.ok(dialog(false, known(0, { pending: 2 })).lines.join(' ').includes('2 réglages en attente'));
  });

  it('présence inconnue ou équipements non lus : dit une fois, sans changer le nombre annoncé', () => {
    const d = dialog(true, known(2, { unknown: 1, unread: 2 }));
    assert.equal(d.lines[0], '2 entités seront retirées de Home Assistant.');
    assert.ok(d.lines.some((l) => l.includes('1 entité dont la présence est inconnue')));
    assert.ok(d.lines.some((l) => l.includes('2 équipements non lus')));
  });

  it('ne plus exclure : confirmation sans nombre, bouton principal (pas rouge) (Q7)', () => {
    const d = dialog(false, known(7));
    assert.equal(d.title, 'Ne plus exclure la pièce « Pièce fictive » ?');
    assert.deepEqual(d.lines, ["Ses équipements seront relus et publiés s'ils sont publiables."]);
    assert.equal(d.confirmLabel, 'Ne plus exclure');
    assert.equal(d.danger, false);
    assert.ok(!d.lines.join(' ').includes('7'), 'aucun nombre');
  });

  it('le nom de la pièce est du texte brut dans la fonction pure (échappé au rendu, jamais interprété)', () => {
    const d = O.roomExclusionDialog({ name: '<img src=x onerror=alert(1)>', excluded: true, impact: known(1) });
    assert.ok(d.title.includes('<img src=x onerror=alert(1)>'));
  });
});

const SCENE = {
  objects: [{ id: 2, name: 'Pièce <b>fictive</b>', father_id: null, display: {} }, { id: 3, name: 'Autre pièce', father_id: null, display: {} }],
  eqlogics: { 2: [{ id: 201, name: 'Eq 201' }, { id: 202, name: 'Eq 202' }], 3: [{ id: 301, name: 'Eq 301' }] },
  config: { excludedObjects: '' },
};
const diag = (reason, publish) => ({ confidence: null, ha_entity_type: null, publication_reason: reason, reason_code: null, should_publish: publish,
  projection_validity: { is_valid: publish, missing_capabilities: [], missing_fields: [], reason_code: publish ? null : reason } });
const published = (id, nEntities) => ({
  jeedom_eq_id: id, equipment_decision: diag('sure_mapping', true),
  entities: Array.from({ length: nEntities }, () => ({ override_pending: false, present_in_ha: true })),
  commands: [{ jeedom_cmd_id: id * 10, covered: true, diagnostic: diag('sure_mapping', true), published_in_ha: true }],
  sync_status: { published_in_ha: true, synced_should_publish: true, current_should_publish: true, override_pending: false },
});
const pendingEntry = (id) => Object.assign(published(id, 1), {
  entities: [{ override_pending: true, present_in_ha: false }],
  sync_status: { published_in_ha: false, synced_should_publish: false, current_should_publish: true, override_pending: true },
  commands: [{ jeedom_cmd_id: id * 10, covered: true, diagnostic: diag('sure_mapping', true), published_in_ha: false }],
});
const equipments = (extra) => Object.assign({ 201: published(201, 2), 202: published(202, 1), 301: published(301, 1) }, extra || {});

function start(extra, options) {
  const ui = startWorkview(Object.assign({ scene: SCENE, equipments: equipments(extra) }, options || {}));
  ui.bridgeUp();
  return ui;
}
const menuItem = (ui, id) => ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${id}"] .j2ha-room-exclude`);

describe('25.8 / AC8 — confirmation dans la page : aucune requête avant le clic de confirmation', () => {
  maybe('exclure : 3 entités annoncées, bouton rouge, nom échappé, 0 requête, seul le clic de confirmation écrit', () => {
    const ui = start();
    const before = ui.calls.length;
    ui.click('#j2ha_roomCards .j2ha-room-card[data-object_id="2"] .j2ha-room-exclude');
    const dlg = ui.lastConfirmation();
    assert.ok(dlg, 'confirmation ouverte');
    assert.equal(plain(dlg.options.title), 'Exclure la pièce « Pièce &lt;b&gt;fictive&lt;/b&gt; » de Home Assistant ?');
    assert.ok(plain(dlg.options.message).includes('3 entités seront retirées de Home Assistant.'));
    assert.equal(dlg.options.buttons.confirm.className, 'btn-danger');
    assert.equal(plain(dlg.options.buttons.confirm.label), 'Exclure la pièce');
    assert.equal(ui.calls.length, before, 'aucune requête avant la confirmation');
    assert.equal(ui.count('saveRoomExclusion'), 0);
    assert.equal(ui.count('scanTopology'), 0);
  });

  maybe('réglages en attente : la phrase chiffrée est présente seulement si des équipements sont « à appliquer »', () => {
    const calm = start();
    calm.click('#j2ha_roomCards .j2ha-room-card[data-object_id="2"] .j2ha-room-exclude');
    assert.ok(!plain(calm.lastConfirmation().options.message).includes('réglage'));
    const busy = start({ 301: pendingEntry(301) });
    busy.click('#j2ha_roomCards .j2ha-room-card[data-object_id="2"] .j2ha-room-exclude');
    assert.ok(plain(busy.lastConfirmation().options.message).includes('La relecture appliquera aussi le réglage en attente de la maison.'));
  });

  maybe('lecture des états indisponible : « Nombre d\'entités inconnu » et le bouton reste actif (Q8)', () => {
    const ui = start(null, { states: false });
    ui.bridgeUp();
    ui.click('#j2ha_roomCards .j2ha-room-card[data-object_id="2"] .j2ha-room-exclude');
    const dlg = ui.lastConfirmation();
    assert.ok(plain(dlg.options.message).includes("Nombre d'entités inconnu : la lecture des états n'est pas disponible."));
    assert.equal(dlg.options.buttons.confirm.className, 'btn-danger');
  });

  maybe('Annuler, croix et Échap ferment sans écrire, libèrent les réservations et rendent le focus au déclencheur', () => {
    for (const how of ['cancel', 'close', 'escape']) {
      const ui = start();
      const toggle = ui.$('#j2ha_roomCards .j2ha-room-card[data-object_id="2"] .j2ha-menu-toggle');
      ui.click('#j2ha_roomCards .j2ha-room-card[data-object_id="2"] .j2ha-room-exclude');
      assert.equal(ui.sandbox.window.jeedom2haRescanInProgress, true, how + ' : réservé pendant la confirmation');
      const dlg = ui.lastConfirmation();
      if (how === 'cancel') dlg.options.buttons.cancel.callback();
      else if (how === 'escape') dlg.options.onEscape();
      dlg.close();
      assert.equal(ui.count('saveRoomExclusion'), 0, how);
      assert.equal(ui.count('scanTopology'), 0, how);
      assert.equal(ui.sandbox.window.jeedom2haRescanInProgress, false, how + ' : réservation libérée');
      assert.equal(ui.isDisabled('#bt_rescanTopology'), false, how + ' : « Relire Jeedom » rendu');
      assert.equal(ui.dom.focused, toggle.list[0], how + ' : focus rendu au bouton « ⋯ » de la carte');
    }
  });

  maybe('« Ne plus exclure » : confirmation sans nombre, bouton principal', () => {
    const ui = start(null, {});
    // pièce 2 exclue dans la configuration
    const excluded = start(null, { scene: Object.assign({}, SCENE, { config: { excludedObjects: '2' } }) });
    excluded.click('#j2ha_roomCards .j2ha-room-card[data-object_id="2"] .j2ha-room-exclude');
    const dlg = excluded.lastConfirmation();
    assert.equal(plain(dlg.options.title), 'Ne plus exclure la pièce « Pièce &lt;b&gt;fictive&lt;/b&gt; » ?');
    assert.ok(plain(dlg.options.message).includes("Ses équipements seront relus et publiés s'ils sont publiables."));
    assert.equal(dlg.options.buttons.confirm.className, 'btn-primary');
    assert.equal(ui.count('saveRoomExclusion'), 0);
  });
});

// Relecture ClaudeBox de #309 (P2-1) : un réglage en attente peut remplacer une entité (domaine changé) ; l'ancienne reste dans
// Home Assistant jusqu'à la relecture et n'apparaît pas dans `entities[]`. Le nombre annoncé est alors un minimum, dit comme tel.
describe('25.8 / AC8 — nombre minimum quand un réglage est en attente (relecture #309)', () => {
  const pending = (present) => ({ override_pending: true, present_in_ha: present });
  it('un réglage en attente sur une entité de la pièce rend le nombre minimum', () => {
    const impact = O.roomExclusionImpact(snapshot({ 201: entry(201, [entity(true), pending(false)]) }), ROOMS, 2);
    assert.equal(impact.entities, 1);
    assert.equal(impact.atLeast, true);
    const d = O.roomExclusionDialog({ name: 'Pièce fictive', excluded: true, impact });
    assert.ok(d.lines.some((l) => plain(l).startsWith('Au moins 1 entité sera retirée')), JSON.stringify(d.lines));
  });
  it('aucune entité présente mais un réglage en attente : pas de « Aucune entité » mais un nombre inconnu', () => {
    const snap = snapshot({ 201: entry(201, [pending(false)]) });
    const impact = O.roomExclusionImpact(snap, ROOMS, 2);
    assert.equal(impact.entities, 0);
    assert.equal(impact.atLeast, true);
    const d = O.roomExclusionDialog({ name: 'Pièce fictive', excluded: true, impact });
    assert.ok(!d.lines.some((l) => plain(l).includes('Aucune entité')), JSON.stringify(d.lines));
  });
  it('sans réglage en attente, le nombre reste exact (pas de « Au moins »)', () => {
    const impact = O.roomExclusionImpact(snapshot({ 201: entry(201, [entity(true), entity(true)]) }), ROOMS, 2);
    assert.equal(impact.atLeast, false);
    const d = O.roomExclusionDialog({ name: 'Pièce fictive', excluded: true, impact });
    assert.ok(d.lines.some((l) => plain(l).startsWith('2 entités seront retirées')), JSON.stringify(d.lines));
  });
});
