// ARTEFACT — Story 25.1 (AC3 à AC6, AC10 à AC16, AC22, AC26) : la fenêtre d'une pièce, rendue par le
// VRAI code (jeedom2ha.js + jeedom2ha_mapping_surface.js) sur un faux DOM. Un seul état par équipement,
// dit de la même façon dans le badge, les compteurs et l'en-tête déplié ; réglage de publication
// segmenté ; « Appliquer » conditionnel ; menu « ⋯ » ; tableau regroupé par entité ; cause dite une
// fois ; commandes ignorées repliées ; un seul équipement déplié. Identifiants fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const M = require('../../desktop/js/jeedom2ha_mapping_override.js');
const { createUi, tree, ok, READY, EXCLUDED, DISABLED, BRIDGE_UP, view } = require('./helpers/ui_harness');

const BLOCKED = view('no_generic_type_configured', false, false);
const IGNORED = view('command_not_covered', false, false);
const plain = (text) => text.replace(/\{\{|\}\}/g, '');

function room(id, name, equipmentIds) {
  return { object_id: id, object_name: name, equipments: equipmentIds.map((eq) => ({ eq_id: eq, eq_name: 'Eq ' + eq, enabled: true })) };
}

function openRoomWith(rooms, objectId, trees) {
  const ui = createUi(rooms);
  ui.respond('getBridgeStatus', { state: 'ok', result: BRIDGE_UP });
  ui.openRoom(objectId);
  (trees || []).forEach((t) => ui.respond('getMappingOverrides', t));
  return ui;
}

const pendingEntity = (ids) => ({ ha_entity_type: 'light', command_ids: ids, decision: READY, override_pending: true, publication_override: null, override_command_id: ids[0], present_in_ha: true });
const entity = (type, ids, extra) => Object.assign({
  ha_entity_type: type, command_ids: ids, decision: READY, publication_override: null,
  override_command_id: ids[0], override_pending: false, present_in_ha: true,
}, extra || {});

/** Six équipements fictifs, un par état de D1. */
function sixStates() {
  const disabledAndExcluded = tree(5, [EXCLUDED], { decision: DISABLED, present: false });
  return {
    rooms: [room(7, 'Zone', [1, 2, 3, 4, 5, 6])],
    trees: [
      ok(tree(1, [READY])),                                              // published
      ok(tree(2, [READY], { entities: [pendingEntity([200])] })),        // to_apply
      ok(tree(3, [BLOCKED], { present: false })),                        // blocked
      ok(tree(4, [EXCLUDED], { decision: EXCLUDED, present: false })),   // excluded
      ok(disabledAndExcluded),                                           // disabled (prime sur excluded)
      ok(tree(6, [IGNORED], { present: false })),                        // nothing_to_publish
    ],
    expected: { 1: 'published', 2: 'to_apply', 3: 'blocked', 4: 'excluded', 5: 'disabled', 6: 'nothing_to_publish' },
  };
}

describe('25.1 / AC3 — badge, compteurs et en-tête déplié disent le même état', () => {
  it('pour chacun des six états : mot du badge, classe de la ligne, compteur de la pièce et en-tête identiques', () => {
    const fixture = sixStates();
    const ui = openRoomWith(fixture.rooms, 7, fixture.trees);
    const counted = {};
    ui.$('.j2ha-room-counter').list.forEach((el) => { counted[el.attrs['data-state']] = Number(ui.$(el).text().trim().split(' ')[0]); });
    for (const [id, state] of Object.entries(fixture.expected)) {
      const panel = ui.$(`.j2ha-eq-panel[data-eq-id="${id}"]`);
      const word = M.EQUIPMENT_STATE_LABELS[state];
      assert.equal(panel.find('.j2ha-eq-publish-badge').text().trim(), word, 'badge ' + id);
      assert.ok(panel.hasClass('j2ha-state-' + state), 'classe de la ligne ' + id);
      assert.equal(panel.find('.j2ha-eq-head-state').text().trim(), word, 'en-tête déplié ' + id);
      assert.equal(counted[state], 1, 'compteur de la pièce ' + state);
    }
    assert.deepEqual(Object.keys(counted).sort(), Object.values(fixture.expected).sort());
  });

  it('la somme des compteurs par état égale le nombre d’équipements lus (3 pièces fictives)', () => {
    const rooms = [room(1, 'A', [11, 12, 13]), room(2, 'B', [21, 22]), room(3, 'C', [31, 32, 33, 34])];
    const sets = {
      1: [tree(11, [READY]), tree(12, [BLOCKED], { present: false }), tree(13, [DISABLED], { present: false })],
      2: [tree(21, [IGNORED], { present: false }), tree(22, [READY], { entities: [pendingEntity([2200])] })],
      3: [tree(31, [READY]), tree(32, [READY]), tree(33, [EXCLUDED], { present: false }), tree(34, [], { present: false })],
    };
    for (const [objectId, trees] of Object.entries(sets)) {
      const ui = openRoomWith(rooms, Number(objectId), trees.map(ok));
      const total = ui.$('.j2ha-room-counter').list.reduce((sum, el) => sum + Number(ui.$(el).text().trim().split(' ')[0]), 0);
      assert.equal(total, trees.length, 'pièce ' + objectId);
    }
  });
});

describe('25.1 / AC4 — « Désactivé » prime sur « Exclu » (visible)', () => {
  it('l’équipement désactivé et exclu affiche « Désactivé » ; le compteur « désactivé » vaut 1, « exclu » 0', () => {
    const t = tree(5, [EXCLUDED], { decision: DISABLED, present: false });
    const ui = openRoomWith([room(7, 'Zone', [5])], 7, [ok(t)]);
    const panel = ui.$('.j2ha-eq-panel[data-eq-id="5"]');
    assert.equal(panel.find('.j2ha-eq-publish-badge').text().trim(), 'Désactivé');
    assert.doesNotMatch(panel.find('.j2ha-eq-head').text(), /Exclu/);
    const chips = ui.$('.j2ha-room-counter').list.map((el) => [el.attrs['data-state'], ui.$(el).text().trim()]);
    assert.deepEqual(chips, [['disabled', '1 désactivé']]);
  });
});

describe('25.1 / AC5 — commandes ignorées hors des défauts', () => {
  it('3 publiées, 1 bloquée, 5 ignorées : ligne « 3 publiées · 1 bloquée · 5 ignorées » ; mention de 1 bloquée ; 1 défaut', () => {
    const diagnostics = [READY, READY, READY, BLOCKED, IGNORED, IGNORED, IGNORED, IGNORED, IGNORED];
    const t = tree(1, diagnostics, { present: true });
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    const panel = ui.$('.j2ha-eq-panel[data-eq-id="1"]');
    assert.equal(panel.find('.j2ha-eq-counter').list.map((el) => ui.$(el).text()).join(' · '), '3 publiées · 1 bloquée · 5 ignorées');
    assert.match(panel.find('.j2ha-eq-blocked-mention').text(), /1 bloquée/);
    assert.equal(M.summarizeEquipmentCounters(t).defects, 1);
  });

  it('une cause « non pris en charge par le plugin » est dite sur la ligne repliée des ignorées', () => {
    const scope = view('ha_component_not_in_product_scope', false, false);
    const t = tree(1, [READY, scope], { present: true });
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    assert.match(ui.$('.j2ha-eq-panel[data-eq-id="1"] .j2ha-ignored-summary').text(), /non pris en charge par le plugin/);
  });
});

describe('25.1 / AC6 — compteurs de la pièce, zéros masqués', () => {
  it('« Appliquer » ne figure pas dans les compteurs ; aucun « 0 … » ; l’ordre est celui des états', () => {
    const fixture = sixStates();
    const ui = openRoomWith(fixture.rooms, 7, fixture.trees);
    const texts = ui.$('.j2ha-room-counter').list.map((el) => ui.$(el).text().trim());
    assert.deepEqual(texts, ['1 publié', '1 à appliquer', '1 bloqué', '1 exclu', '1 désactivé', '1 rien à publier']);
    assert.ok(texts.every((t) => !/^0 /.test(t)));
  });

  it('équipements non lus et présence inconnue conservés, au glossaire', () => {
    const old = tree(1, [READY], { sync: { override_pending: false } });
    const ui = openRoomWith([room(7, 'Zone', [1, 2])], 7, [ok(old)]);
    ui.fail('getMappingOverrides');
    const text = ui.$('.j2ha-room-counters').text();
    assert.match(text, /1 équipement non lu/);
    assert.match(text, /1 équipement dont la présence dans Home Assistant est inconnue \(démon plus ancien\)/);
  });
});

describe('25.1 / AC10 — réglage de publication segmenté', () => {
  const EQ = '.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-controls';

  it('radiogroup de trois radios Automatique | Toujours | Jamais, position courante montrée', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [READY]))]);
    const group = ui.$(EQ + ' .j2ha-seg');
    assert.equal(group.attr('role'), 'radiogroup');
    const radios = ui.$(EQ + ' .j2ha-seg-btn');
    assert.deepEqual(radios.list.map((el) => el.attrs.role), ['radio', 'radio', 'radio']);
    assert.deepEqual(radios.list.map((el) => plain(ui.$(el).text())), ['Automatique', 'Toujours', 'Jamais']);
    assert.deepEqual(radios.list.map((el) => el.attrs['aria-checked']), ['true', 'false', 'false']);
  });

  it('exclu → « Jamais » actif ; forcé → « Toujours » actif', () => {
    const excluded = tree(1, [READY]);
    excluded.equipment_publication_override = 'exclude';
    const forced = tree(1, [READY]);
    forced.equipment_publication_override = 'force_publish';
    for (const [t, key] of [[excluded, 'never'], [forced, 'always']]) {
      const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
      assert.deepEqual(ui.$(EQ + ' .j2ha-seg-active').list.map((el) => el.attrs['data-value']), [key]);
    }
  });

  it('un clic sur un segment appelle les routes d’écriture existantes (exclure / forcer / revenir)', () => {
    const blockedTree = tree(1, [BLOCKED], { decision: BLOCKED, present: false });
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(blockedTree)]);
    ui.click(EQ + ' .j2ha-seg-never');
    const call = ui.pending('savePublicationOverride')[0];
    assert.deepEqual([call.data.eqId, call.data.publicationPolicy], [1, 'exclude']);
    call.respond({ state: 'ok', result: null });
    assert.equal(ui.pending('getMappingOverrides')[0].data.eqId, 1);
    ui.respond('getMappingOverrides', ok(Object.assign(tree(1, [BLOCKED], { decision: EXCLUDED, present: false }), { equipment_publication_override: 'exclude' })));
    ui.click(EQ + ' .j2ha-seg-auto');
    assert.equal(ui.pending('revertPublicationOverride')[0].data.eqId, 1);
    assert.equal(ui.pending('revertPublicationOverride')[0].data.cmdId, undefined);
  });

  it('les anciens boutons Exclure / Forcer / Revenir au mode automatique n’existent plus', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [READY]))]);
    const text = ui.$('.modal-j2ha-room').text();
    assert.doesNotMatch(text, /Revenir au mode automatique|Forcer l|Exclure l|Exclure cette|Forcer cette/);
    const walk = (dir) => fs.readdirSync(dir).flatMap((f) => (fs.statSync(dir + '/' + f).isDirectory() ? walk(dir + '/' + f) : [dir + '/' + f]));
    for (const file of walk('desktop')) {
      assert.doesNotMatch(fs.readFileSync(file, 'utf8'), /Revenir au mode automatique|Forcer l|Exclure l|Exclure cette|Forcer cette/, file);
    }
  });

  it('segments indisponibles : cause en infobulle, désactivés (infobulle aussi sur le conteneur)', () => {
    // Équipement inéligible : ni « Toujours » ni « Jamais » n'auraient d'effet.
    const t = tree(1, [READY], { present: true });
    t.eligible = false;
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    const always = ui.$(EQ + ' .j2ha-seg-always');
    assert.equal(always.prop('disabled'), true);
    assert.equal(always.attr('aria-disabled'), 'true');
    assert.match(always.attr('title'), /non éligible/);
    assert.equal(ui.$(EQ + ' .j2ha-seg-item').list[1].attrs.title, always.attr('title'), 'infobulle aussi sur le conteneur (boutons désactivés)');
    // Un bouton désactivé ne peut pas recevoir le focus : les flèches le sautent.
    ui.key(EQ + ' .j2ha-seg-auto', 'ArrowRight');
    assert.equal(ui.dom.focused, ui.$(EQ + ' .j2ha-seg-auto').list[0], 'aucune autre position utilisable : le focus reste sur la position courante');
  });

  it('navigation clavier : Tab (tabindex itinérant), flèches, Début / Fin, Espace / Entrée (clic natif)', () => {
    // Équipement bloqué, rien de publié : les trois positions sont utilisables.
    // Décision refusée mais projetable : « Toujours » est possible (un aperçu du démon le confirmera).
    const refused = Object.assign(view('ambiguous_skipped', false, false), { ha_entity_type: 'light', projection_validity: { is_valid: true, missing_capabilities: [], missing_fields: [] } });
    const t = tree(1, [refused], { decision: refused, present: false });
    t.entities = [entity('light', [100], { decision: refused })];
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    assert.equal(ui.$(EQ + ' .j2ha-seg-btn').list.filter((el) => el.props.disabled).length, 0);
    // Tab : seule la position courante est dans l'ordre de tabulation.
    const tabindex = () => ui.$(EQ + ' .j2ha-seg-btn').list.map((el) => el.attrs.tabindex);
    assert.deepEqual(tabindex(), ['0', '-1', '-1']);
    // Flèches : déplacent le focus sans rien écrire.
    const auto = ui.$(EQ + ' .j2ha-seg-auto').list[0];
    ui.key(EQ + ' .j2ha-seg-auto', 'ArrowRight');
    assert.equal(ui.dom.focused, ui.$(EQ + ' .j2ha-seg-always').list[0]);
    assert.equal(ui.dom.focused.tag, 'button', 'un vrai <button> : Espace et Entrée déclenchent le clic');
    assert.deepEqual(tabindex(), ['-1', '0', '-1']);
    ui.key(EQ + ' .j2ha-seg-always', 'ArrowLeft');
    assert.equal(ui.dom.focused, auto);
    ui.key(EQ + ' .j2ha-seg-auto', 'End');
    assert.equal(ui.dom.focused, ui.$(EQ + ' .j2ha-seg-never').list[0]);
    ui.key(EQ + ' .j2ha-seg-never', 'ArrowRight');
    assert.equal(ui.dom.focused, auto, 'retour au début');
    ui.key(EQ + ' .j2ha-seg-auto', 'Home');
    assert.equal(ui.dom.focused, auto);
    assert.equal(ui.calls.filter((c) => /^(save|revert)|executeHaAction/.test(c.action || '')).length, 0, 'les flèches n’écrivent jamais');
  });
});

describe('25.1 / AC11 — « Appliquer » seulement quand un réglage attend', () => {
  const EQ = '.j2ha-eq-panel[data-eq-id="1"] ';

  it('absent du DOM quand l’état n’est pas « À appliquer »', () => {
    for (const t of [tree(1, [READY]), tree(1, [BLOCKED], { present: false }), tree(1, [EXCLUDED], { present: false })]) {
      const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
      assert.equal(ui.$(EQ + '.j2ha-eq-apply').length, 0);
    }
  });

  it('published → to_apply (après un changement de segment) → bouton visible ; clic réussi → published, bouton absent', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [READY], { entities: [entity('light', [100])] }))]);
    assert.equal(ui.$(EQ + '.j2ha-eq-apply').length, 0);
    // L'équipement est publié : « Jamais » demande une confirmation (il quitterait Home Assistant).
    ui.click(EQ + '.j2ha-seg-never');
    ui.lastConfirmation().options.buttons.confirm.callback();
    ui.respond('savePublicationOverride', { state: 'ok', result: null });
    ui.respond('getMappingOverrides', ok(Object.assign(tree(1, [READY], { entities: [pendingEntity([100])] }), { equipment_publication_override: 'exclude' })));
    assert.equal(ui.$(EQ + '.j2ha-eq-apply').length, 1, 'bouton visible');
    assert.equal(ui.$(EQ + '.j2ha-eq-apply').prop('disabled'), false);
    ui.click(EQ + '.j2ha-eq-apply');
    const call = ui.pending('executeHaAction')[0];
    assert.deepEqual([call.data.intention, call.data.portee, call.data.selection], ['publier', 'equipement', '[1]']);
    ui.respond('executeHaAction', { state: 'ok', result: { payload: { resultat: 'succes', message: 'Fait.' } } });
    ui.respond('getMappingOverrides', ok(tree(1, [READY])));
    assert.equal(ui.$(EQ + '.j2ha-eq-apply').length, 0, 'bouton absent une fois publié');
    assert.equal(ui.$(EQ + '.j2ha-eq-publish-badge').text().trim(), 'Publié');
  });

  it('clic en échec → bouton visible avec le message d’erreur existant', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [READY], { entities: [pendingEntity([100])] }))]);
    ui.click(EQ + '.j2ha-eq-apply');
    ui.fail('executeHaAction');
    assert.equal(ui.$(EQ + '.j2ha-eq-apply').length, 1);
    assert.equal(ui.$(EQ + '.j2ha-eq-apply').prop('disabled'), false);
    assert.match(ui.$(EQ + '.j2ha-publication-error').text(), /Le démon ne répond pas/);
  });
});

describe('25.1 / AC12 — menu d’actions secondaires « ⋯ »', () => {
  const EQ = '.j2ha-eq-panel[data-eq-id="1"] ';

  it('« Republier », « Tout remettre en automatique… », un trait puis « Supprimer de Home Assistant… » (rouge dans le menu seulement)', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [READY]))]);
    const entries = ui.$(EQ + '.j2ha-menu li').list.map((li) => ({
      role: li.attrs.role, text: plain(ui.$(li).text()), danger: ui.$(li).find('.j2ha-menu-danger').length === 1,
    }));
    assert.deepEqual(entries, [
      { role: 'none', text: 'Republier', danger: false },
      { role: 'none', text: 'Tout remettre en automatique…', danger: false },
      { role: 'separator', text: '', danger: false },
      { role: 'none', text: 'Supprimer de Home Assistant…', danger: true },
    ]);
    assert.equal(ui.$(EQ + '.j2ha-eq-actions').length, 0);
  });

  it('bouton « ⋯ » : aria-haspopup, aria-expanded, fermeture par Échap et par clic extérieur', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [READY]))]);
    const toggle = EQ + '.j2ha-menu-toggle';
    assert.equal(ui.$(toggle).attr('aria-haspopup'), 'menu');
    assert.equal(ui.$(toggle).attr('aria-expanded'), 'false');
    ui.click(toggle);
    assert.equal(ui.$(toggle).attr('aria-expanded'), 'true');
    assert.ok(ui.$(EQ + '.j2ha-menu-wrap').hasClass('j2ha-menu-open'));
    ui.key(EQ + '.j2ha-menu', 'Escape');
    assert.equal(ui.$(toggle).attr('aria-expanded'), 'false');
    assert.equal(ui.dom.focused, ui.$(toggle).list[0], 'le focus revient sur « ⋯ »');
    ui.click(toggle);
    ui.clickOutside();
    assert.equal(ui.$(toggle).attr('aria-expanded'), 'false');
    assert.ok(!ui.$(EQ + '.j2ha-menu-wrap').hasClass('j2ha-menu-open'));
  });

  it('flèches dans le menu ; un choix referme le menu', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [READY]))]);
    ui.click(EQ + '.j2ha-menu-toggle');
    assert.equal(ui.dom.focused, ui.$(EQ + '.j2ha-eq-republish').list[0], 'ouverture : premier choix focalisé');
    ui.key(EQ + '.j2ha-menu', 'ArrowDown');
    // Premier appel avec cible = menu lui-même : l'index est inconnu, on se positionne sur le premier choix.
    assert.ok(ui.dom.focused);
    ui.click(EQ + '.j2ha-eq-republish');
    assert.ok(!ui.$(EQ + '.j2ha-menu-wrap').hasClass('j2ha-menu-open'));
    assert.equal(ui.pending('executeHaAction').length, 1, 'même route qu’avant');
  });

  it('pièce : « Republier » et « Supprimer de Home Assistant… » dans le menu de l’en-tête de pièce', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [READY]))]);
    const head = '.modal-j2ha-room .j2ha-room-actions ';
    assert.equal(ui.$(head + '.j2ha-menu-toggle').attr('aria-haspopup'), 'menu');
    assert.equal(plain(ui.$(head + '.j2ha-room-republish').text()), 'Republier');
    assert.equal(plain(ui.$(head + '.j2ha-room-recreate').text()), 'Supprimer de Home Assistant…');
    assert.ok(ui.$(head + '.j2ha-room-recreate').hasClass('j2ha-menu-danger'));
  });

  it('les confirmations de suppression gardent leur texte d’impact et « rien n’est recréé »', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [READY]))]);
    for (const selector of ['.j2ha-room-recreate', EQ + '.j2ha-eq-recreate']) {
      ui.click(selector);
      const { options } = ui.lastConfirmation();
      for (const word of ['historique', 'dashboards', 'automatisations', 'Rien n\'est recréé automatiquement']) {
        assert.ok(options.message.includes(word), word);
      }
      options.buttons.cancel.callback();
    }
  });
});

describe('25.1 / AC13 — tableau regroupé par entité', () => {
  function multi() {
    const diagnostics = [READY, READY, READY, READY, READY, READY, READY, IGNORED, IGNORED, IGNORED, IGNORED, IGNORED];
    const t = tree(1, diagnostics, { present: true, entities: [
      entity('switch', [100, 101, 102]), entity('sensor', [103, 104, 105, 106]),
    ] });
    return t;
  }
  const PANEL = '.j2ha-eq-panel[data-eq-id="1"] ';

  it('colonnes Commande | Dans Home Assistant | Type Jeedom | Type HA, en-têtes sans majuscules forcées', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(multi())]);
    assert.deepEqual(ui.$(PANEL + '.j2ha-cmd-table th').list.map((el) => plain(ui.$(el).text())),
      ['Commande', 'Dans Home Assistant', 'Type Jeedom', 'Type HA']);
    const css = fs.readFileSync('desktop/css/jeedom2ha.css', 'utf8');
    assert.doesNotMatch(css, /text-transform:\s*uppercase/);
  });

  it('un groupe par entité : domaine traduit + terme technique, effectif, contrôle segmenté compact ; plus de liste séparée', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(multi())]);
    const heads = ui.$(PANEL + '.j2ha-group-head').list;
    assert.equal(heads.length, 2);
    assert.deepEqual(heads.map((h) => ui.$(h).find('.j2ha-group-name strong').text()), ['Interrupteur', 'Capteur']);
    assert.deepEqual(heads.map((h) => ui.$(h).find('.j2ha-tech').text()), ['switch', 'sensor']);
    assert.deepEqual(heads.map((h) => ui.$(h).find('.j2ha-group-count').text().trim()), ['3 {{commandes}}', '4 {{commandes}}']);
    heads.forEach((h) => assert.equal(ui.$(h).find('.j2ha-seg-compact .j2ha-seg-btn').length, 3));
    assert.equal(ui.$(PANEL + '.j2ha-entity-row').length, 0, 'la liste « switch — Commandes : … » disparaît');
    // Les commandes suivent leur en-tête (3 puis 4) : 7 lignes de commande, aucune des 5 ignorées.
    assert.equal(ui.$(PANEL + 'tr.mapping-override-cmd').length, 7);
  });

  it('une seule entité : pas d’en-tête de groupe', () => {
    const t = tree(1, [READY, READY], { entities: [entity('light', [100, 101])] });
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    assert.equal(ui.$(PANEL + '.j2ha-group-head').length, 0);
    assert.equal(ui.$(PANEL + 'tr.mapping-override-cmd').length, 2);
  });

  it('« Dans Home Assistant » : Publiée → domaine, Bloquée, — ; aucune répétition de « Sera publié »', () => {
    const t = tree(1, [READY, BLOCKED, view('excluded_plugin', false, false)], { present: true,
      entities: [entity('light', [100])] });
    t.commands[1].published_in_ha = false;
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    const cells = ui.$(PANEL + '.mo-diag-cell').list.map((el) => plain(ui.$(el).text().trim()));
    assert.deepEqual(cells, ['Publiée → Lumière (light)', 'Bloquée', 'Exclue']);
    assert.doesNotMatch(ui.$(PANEL + '.j2ha-cmd-table').text(), /Sera publié|dans Home Assistant\./);
  });

  it('« Type HA » : lien « auto » / « imposé (sensor) » ; sélecteur seulement après clic ; jamais pour une ignorée', () => {
    const t = tree(1, [READY, READY], { entities: [entity('sensor', [100, 101])] });
    t.commands[1].override_applied = true;
    t.commands[1].effective_ha = 'sensor';
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    const links = ui.$(PANEL + '.j2ha-type-link').list.map((el) => plain(ui.$(el).text()));
    assert.deepEqual(links, ['auto', 'imposé (sensor)']);
    assert.ok(ui.$(PANEL + '.j2ha-type-forced').length === 1, 'surligné quand un type est imposé');
    assert.equal(ui.$(PANEL + 'select').length, 0, 'sélecteur non rendu en permanence');
    const ignored = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [READY, IGNORED], { entities: [entity('light', [100])] }))]);
    assert.equal(ignored.$(PANEL + '.j2ha-type-link').length, 1, 'aucun réglage de type pour la commande ignorée');
  });

  it('« Type Jeedom » en texte normal (pas de monospace)', () => {
    const css = fs.readFileSync('desktop/css/jeedom2ha.css', 'utf8');
    assert.doesNotMatch(css, /font-family:\s*monospace/);
  });
});

describe('25.1 / AC14 — la cause est dite une fois, avec un lien', () => {
  const PANEL = '.j2ha-eq-panel[data-eq-id="1"] ';
  const CAUSE = 'types génériques non configurés dans Jeedom';

  it('11 commandes bloquées pour la même cause : un encart, le bouton, la phrase une seule fois dans le DOM', () => {
    const t = tree(1, Array.from({ length: 11 }, () => BLOCKED), { present: false });
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    const notices = ui.$(PANEL + '.j2ha-notice');
    assert.equal(notices.length, 1);
    assert.match(notices.find('.j2ha-notice-text').text(), /11 commandes bloquées : types génériques non configurés dans Jeedom/);
    const button = notices.find('.j2ha-open-generic-types');
    assert.equal(plain(button.text()), 'Ouvrir les types génériques');
    assert.equal(button.attr('href'), 'index.php?v=d&p=types');
    const occurrences = ui.$(PANEL).text().split(CAUSE).length - 1;
    assert.equal(occurrences, 1, 'la phrase de cause apparaît exactement une fois');
    ui.$(PANEL + '.mo-diag-cell').list.forEach((cell) => assert.equal(plain(ui.$(cell).text().trim()), 'Bloquée'));
    // Ouvrir l'écran Jeedom n'écrit rien : seules des lectures ont été émises.
    assert.ok(ui.calls.every((c) => ['getBridgeStatus', 'getMappingOverrides'].includes(c.action)));
  });

  it('causes différentes : un encart par cause, avec son nombre ; jamais un par commande', () => {
    const t = tree(1, [BLOCKED, BLOCKED, view('ha_missing_state_topic', false, false), READY], { present: true });
    t.commands[3].published_in_ha = true;
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    const notices = ui.$(PANEL + '.j2ha-notice-text').list.map((el) => ui.$(el).text().trim());
    assert.deepEqual(notices, ['2 commandes bloquées : types génériques non configurés dans Jeedom', '1 commande bloquée : pas de retour d’état exploitable']);
    assert.equal(ui.$(PANEL + '.j2ha-open-generic-types').length, 1, 'le lien seulement pour la cause qui le justifie');
  });

  it('« Voir la première commande bloquée » : supprimé si tout est bloqué, conservé sinon', () => {
    const all = openRoomWith([room(7, 'Zone', [1])], 7, [ok(tree(1, [BLOCKED, BLOCKED], { present: false }))]);
    assert.equal(all.$(PANEL + '.j2ha-goto-blocking').length, 0);
    const mixed = tree(1, [READY, BLOCKED], { present: true });
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(mixed)]);
    assert.equal(ui.$(PANEL + '.j2ha-goto-blocking').length, 1);
    assert.match(ui.$(PANEL + '.j2ha-goto-blocking').text(), /Voir la première commande bloquée/);
  });
});

describe('25.1 / AC15 — commandes ignorées repliées', () => {
  const PANEL = '.j2ha-eq-panel[data-eq-id="1"] ';
  const names = ['Pinguer nœud', 'Soigner nœud', 'Réveiller nœud', 'Statut radio', 'Version'];

  function withIgnored() {
    const t = tree(1, [READY, IGNORED, IGNORED, IGNORED, IGNORED, IGNORED], { present: true, entities: [entity('light', [100])] });
    t.commands.forEach((c, i) => { if (i > 0) c.cmd_name = names[i - 1]; });
    return t;
  }

  it('une ligne repliée « 5 commandes ignorées, sans équivalent dans Home Assistant : … », dépliable au clic', () => {
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(withIgnored())]);
    assert.equal(ui.$(PANEL + 'tr.mapping-override-cmd').length, 1, 'les ignorées ne sont pas des lignes du tableau');
    const toggle = ui.$(PANEL + '.j2ha-ignored-toggle');
    assert.equal(toggle.attr('aria-expanded'), 'false');
    assert.equal(ui.$(PANEL + '.j2ha-ignored-summary').text().trim(),
      '5 commandes ignorées, sans équivalent dans Home Assistant : Pinguer nœud, Soigner nœud, Réveiller nœud…');
    assert.equal(ui.$(PANEL + '.j2ha-ignored-list li').length, 5);
    assert.ok(!ui.$(PANEL + '.j2ha-ignored').hasClass('j2ha-open'));
    ui.click(PANEL + '.j2ha-ignored-toggle');
    assert.equal(ui.$(PANEL + '.j2ha-ignored-toggle').attr('aria-expanded'), 'true');
    assert.ok(ui.$(PANEL + '.j2ha-ignored').hasClass('j2ha-open'));
    assert.equal(ui.$(PANEL + '.j2ha-ignored-toggle').list[0].tag, 'button', 'opérable au clavier (bouton natif)');
    assert.equal(ui.$(PANEL + '.j2ha-ignored-toggle').attr('aria-controls'), ui.$(PANEL + '.j2ha-ignored-list').attr('id'));
  });
});

describe('25.1 / AC16 — un seul équipement déplié, en-tête collant, un seul défilement', () => {
  it('déplier B replie A ; l’accordéon n’est plus multisélectionnable', () => {
    const ui = openRoomWith([room(7, 'Zone', [1, 2])], 7, [ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    const toggleA = '.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-toggle';
    const toggleB = '.j2ha-eq-panel[data-eq-id="2"] .j2ha-eq-toggle';
    ui.click(toggleA);
    assert.equal(ui.$(toggleA).attr('aria-expanded'), 'true');
    assert.ok(ui.$('.j2ha-eq-panel[data-eq-id="1"]').hasClass('j2ha-eq-open'));
    ui.click(toggleB);
    assert.equal(ui.$(toggleA).attr('aria-expanded'), 'false');
    assert.ok(!ui.$('.j2ha-eq-panel[data-eq-id="1"]').hasClass('j2ha-eq-open'));
    assert.ok(!ui.$('.j2ha-eq-panel[data-eq-id="1"] .panel-collapse').hasClass('in'));
    assert.equal(ui.$('.j2ha-eq-panel.j2ha-eq-open').length, 1);
    ui.click(toggleB);
    assert.equal(ui.$('.j2ha-eq-panel.j2ha-eq-open').length, 0, 'un second clic replie');
    assert.equal(ui.$('.j2ha-eq-accordion').attr('aria-multiselectable'), undefined);
  });

  it('plus de max-height ni d’overflow imbriqué dans le JS ni le PHP ; en-tête collant et fond distinct dans le CSS', () => {
    for (const file of ['desktop/js/jeedom2ha.js', 'desktop/js/jeedom2ha_mapping_surface.js', 'desktop/js/jeedom2ha_mapping_override.js', 'desktop/php/jeedom2ha.php']) {
      assert.doesNotMatch(fs.readFileSync(file, 'utf8'), /max-height|overflow-y|aria-multiselectable/, file);
    }
    const css = fs.readFileSync('desktop/css/jeedom2ha.css', 'utf8');
    assert.match(css, /\.j2ha-eq-panel\.j2ha-eq-open > \.j2ha-eq-head\s*\{[^}]*position:\s*sticky;[^}]*top:\s*0/);
    assert.doesNotMatch(css, /\.j2ha-eq-cmdlist[^{]*\{[^}]*overflow/);
    assert.match(css, /\.j2ha-eq-open > \.panel-collapse > \.panel-body\s*\{[^}]*background-color:\s*var\(--j2ha-surface\)[^}]*border-left:\s*3px solid var\(--j2ha-ok\)/);
  });
});

describe('25.1 / AC22 — aucune lecture ni écriture de plus', () => {
  it('ouvrir une pièce : une lecture par équipement et rien d’autre ; ouvrir/replier un équipement ne lit rien', () => {
    const ui = openRoomWith([room(7, 'Zone', [1, 2])], 7, [ok(tree(1, [READY])), ok(tree(2, [READY]))]);
    const actions = ui.calls.map((c) => c.action).sort();
    assert.deepEqual(actions, ['getBridgeStatus', 'getMappingOverrides', 'getMappingOverrides']);
    ui.click('.j2ha-eq-panel[data-eq-id="1"] .j2ha-eq-toggle');
    ui.click('.j2ha-eq-panel[data-eq-id="2"] .j2ha-eq-toggle');
    assert.equal(ui.calls.length, 3);
  });
});

describe('25.1 / AC26 — accessibilité minimale', () => {
  it('l’état n’est jamais porté par la seule couleur (mot + icône) ; boutons-icônes nommés', () => {
    const fixture = sixStates();
    const ui = openRoomWith(fixture.rooms, 7, fixture.trees);
    ui.$('.j2ha-eq-publish-badge').list.forEach((badge) => {
      assert.ok(ui.$(badge).find('i').length === 1, 'icône');
      assert.ok(ui.$(badge).find('.j2ha-state-text').text().trim().length > 0, 'mot');
    });
    ui.$('.j2ha-menu-toggle').list.forEach((toggle) => assert.equal(toggle.attrs['aria-label'], '{{Autres actions}}'));
    ui.$('.j2ha-seg').list.forEach((group) => assert.ok(group.attrs['aria-label']));
  });
});

describe('25.1 / revue R1 (ClaudeBox) — P2-2, P2-3, P3-2, P3-3', () => {
  const PANEL = '.j2ha-eq-panel[data-eq-id="1"] ';
  const EQ = PANEL + '.j2ha-eq-controls';
  const refused = Object.assign(view('ambiguous_skipped', false, false), { ha_entity_type: 'light', projection_validity: { is_valid: true, missing_capabilities: [], missing_fields: [] } });
  const writes = (ui) => ui.calls.filter((c) => /^(save|revert)|executeHaAction/.test(c.action || ''));

  it('P2-2 : « Voir la première commande bloquée » fait défiler la fenêtre jusqu’à la ligne (scrollIntoView) et la surligne', () => {
    const t = tree(1, [READY, BLOCKED], { present: true });
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    const row = ui.$(PANEL + 'tr.mapping-override-cmd[data-cmd-id="101"]');
    const seen = [];
    row.list[0].scrollIntoView = (options) => seen.push(options);
    ui.click(PANEL + '.j2ha-goto-blocking');
    assert.equal(JSON.stringify(seen), '[{"block":"center"}]');
    assert.ok(row.hasClass('j2ha-diag-target-highlight'));
    const css = fs.readFileSync('desktop/css/jeedom2ha.css', 'utf8');
    assert.match(css, /\.j2ha-cmd-table tr\.mapping-override-cmd\s*\{[^}]*scroll-margin-top/);
  });

  it('P2-3 : un clic sur « Automatique » déjà actif n’écrit jamais, même avec des types HA imposés', () => {
    const t = tree(1, [READY], { entities: [entity('light', [100])] });
    t.commands[0].override_applied = true;
    t.commands[0].effective_ha = 'light';
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    assert.ok(ui.$(EQ + ' .j2ha-seg-auto').hasClass('j2ha-seg-active'));
    ui.click(EQ + ' .j2ha-seg-auto');
    assert.equal(writes(ui).length, 0);
    assert.equal(ui.pending('getMappingOverrides').length, 0);
  });

  it('P2-3 : « Tout remettre en automatique… » (menu ⋯) liste ce qui sera retiré, puis retire sur la route existante', () => {
    const t = tree(1, [READY, READY], { entities: [entity('light', [100], { publication_override: 'exclude_command' }), entity('sensor', [101])] });
    t.commands[1].override_applied = true;
    t.commands[1].effective_ha = 'sensor';
    t.equipment_publication_override = 'force_publish';
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    const reset = ui.$(PANEL + '.j2ha-eq-reset');
    assert.equal(plain(reset.text()), 'Tout remettre en automatique…');
    assert.notEqual(reset.prop('disabled'), true);
    ui.click(PANEL + '.j2ha-eq-reset');
    assert.equal(writes(ui).length, 0, 'rien n’est écrit avant la confirmation');
    const message = plain(ui.$(ui.lastConfirmation().options.message).text());
    assert.match(message, /réglage « Toujours » de l’équipement/);
    assert.match(message, /1 réglage « Jamais » ou « Toujours » d’entité/);
    assert.match(message, /1 type Home Assistant imposé/);
    ui.lastConfirmation().options.buttons.confirm.callback();
    const call = ui.pending('revertPublicationOverride')[0];
    assert.deepEqual([call.data.eqId, call.data.cmdId], [1, undefined]);
  });

  it('P2-3 : annuler la confirmation n’écrit rien ; l’entrée est grisée sans réglage à retirer', () => {
    const ui = openRoomWith([room(7, 'Zone', [1, 2])], 7, [ok(tree(1, [READY], { entities: [entity('light', [100], { publication_override: 'force_publish' })] })), ok(tree(2, [READY]))]);
    ui.click(PANEL + '.j2ha-eq-reset');
    ui.lastConfirmation().options.buttons.cancel.callback();
    assert.equal(writes(ui).length, 0);
    const none = ui.$('.j2ha-eq-panel[data-eq-id="2"] .j2ha-eq-reset');
    assert.equal(none.prop('disabled'), true);
    assert.match(none.attr('title'), /Aucun réglage de publication à retirer/);
  });

  it('P3-2 : « Toujours » → aperçu du démon puis savePublicationOverride force_publish (équipement)', () => {
    const t = tree(1, [refused], { decision: refused, present: false });
    t.entities = [entity('light', [100], { decision: refused })];
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    ui.click(EQ + ' .j2ha-seg-always');
    const preview = ui.pending('previewMappingOverride')[0];
    assert.deepEqual([preview.data.eqId, preview.data.publicationPolicy, preview.data.cmdId], [1, 'force_publish', undefined]);
    preview.respond({ state: 'ok', result: { payload: { overridden: { entities: [{ ha_entity_type: 'light', command_ids: [100], decision: READY }] } } } });
    ui.lastConfirmation().options.buttons.confirm.callback();
    const save = ui.pending('savePublicationOverride')[0];
    assert.deepEqual([save.data.eqId, save.data.publicationPolicy, save.data.cmdId], [1, 'force_publish', undefined]);
  });

  it('P3-3 : « Voir la première commande bloquée » et l’icône « Retirer le type imposé » répondent à Entrée et Espace', () => {
    const t = tree(1, [READY, BLOCKED], { present: true });
    t.commands[0].override_applied = true;
    t.commands[0].effective_ha = 'light';
    const ui = openRoomWith([room(7, 'Zone', [1])], 7, [ok(t)]);
    const seen = [];
    ui.$(PANEL + 'tr.mapping-override-cmd[data-cmd-id="101"]').list[0].scrollIntoView = (o) => seen.push(o);
    ui.key(PANEL + '.j2ha-goto-blocking', 'Enter');
    ui.key(PANEL + '.j2ha-goto-blocking', ' ');
    assert.equal(seen.length, 2);
    ui.key(PANEL + '.mo-revert-cmd', ' ');
    const call = ui.pending('revertMappingOverride')[0];
    assert.deepEqual([call.data.eqId, call.data.cmdId], [1, 100]);
  });
});
