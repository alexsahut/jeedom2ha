// ARTEFACT — Story 25.8 (AC6) : le menu « ⋯ » d'une carte de pièce demande l'exclusion SANS ouvrir la pièce — le clic, keydown et
// keyup du bouton, du menu et de ses entrées sont arrêtés (stopPropagation) avant l'`onclick` de la carte et l'écouteur clavier de
// jeedom2ha_overview.js. La carte de « Sans pièce » n'a pas de menu ; les cartes gardent leur balisage (objectDisplayCard,
// .j2ha-room-card, data-object_id, onclick) ; le menu réutilise le composant .j2ha-menu-* de 25.1 sans en modifier les règles.
// Vrai squelette PHP (faux cœur Jeedom) et vrai code sur faux DOM ; identifiants fictifs (CC-48).
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { SCENE, phpAvailable, startPage, plain } = require('./helpers/page_b_harness');
const { diffAgainstBase, removedLines } = require('./helpers/git_base');

const maybe = phpAvailable ? it : it.skip;
const SCENE_EXCLUDED = Object.assign({}, SCENE, { config: { excludedObjects: ' 3 ,5' } });
const CARD = (id) => `#j2ha_roomCards .j2ha-room-card[data-object_id="${id}"]`;

/** Événement factice qui consigne l'arrêt de la propagation. */
function event(extra) {
  const e = Object.assign({ stopped: 0, prevented: 0, stopPropagation() { e.stopped += 1; }, preventDefault() { e.prevented += 1; } }, extra || {});
  return e;
}
function fire(ui, selector, type, evt) {
  const el = ui.$(selector).first();
  assert.equal(el.length, 1, selector);
  const handler = el.list[0].handlers[type];
  assert.equal(typeof handler, 'function', `${selector} : gestionnaire ${type}`);
  handler.call(el.list[0], evt);
  return evt;
}

describe('25.8 / AC6 — balisage des cartes', () => {
  maybe('chaque carte de pièce (id > 0) a un menu ; « Sans pièce » n\'en a pas', () => {
    const ui = startPage({ scene: SCENE_EXCLUDED });
    for (const room of ui.rooms) {
      const menus = ui.$(`${CARD(room.object_id)} .j2ha-room-menu`);
      assert.equal(menus.length, room.object_id > 0 ? 1 : 0, 'pièce ' + room.object_id);
    }
    assert.equal(ui.$(`${CARD(0)} .j2ha-menu-toggle`).length, 0);
    assert.equal(ui.$(`${CARD(0)} .j2ha-room-exclude`).length, 0);
  });

  maybe('les cartes conservent objectDisplayCard, .j2ha-room-card, data-object_id, onclick, role et tabindex', () => {
    const ui = startPage({ scene: SCENE_EXCLUDED });
    for (const room of ui.rooms) {
      const card = ui.$(CARD(room.object_id));
      assert.equal(card.length, 1);
      assert.ok(card.hasClass('objectDisplayCard') && card.hasClass('j2ha-room-card'));
      assert.equal(card.attr('onclick'), `j2haOpenRoom(${room.object_id})`);
      assert.equal(card.attr('role'), 'button');
      assert.equal(card.attr('tabindex'), '0');
      assert.ok(!card.hasClass('eqLogicDisplayCard'));
    }
  });

  maybe('le menu réutilise le composant .j2ha-menu-* de 25.1 ; l\'entrée est de la famille data-ha-action (gating)', () => {
    const ui = startPage({ scene: SCENE_EXCLUDED });
    const wrap = ui.$(`${CARD(3)} .j2ha-room-menu`);
    assert.ok(wrap.hasClass('j2ha-menu-wrap'));
    assert.equal(ui.$(`${CARD(3)} .j2ha-menu-toggle`).attr('aria-haspopup'), 'menu');
    assert.equal(ui.$(`${CARD(3)} .j2ha-menu-toggle`).attr('aria-expanded'), 'false');
    assert.ok(plain(ui.$(`${CARD(3)} .j2ha-menu-toggle`).attr('aria-label')).startsWith('Actions de la pièce'));
    assert.equal(ui.$(`${CARD(3)} .j2ha-menu .j2ha-menu-item`).length, 1);
    assert.equal(ui.$(`${CARD(3)} .j2ha-room-exclude`).attr('data-ha-action'), 'exclure-piece');
    assert.equal(ui.$(`${CARD(3)} .j2ha-room-exclude`).attr('role'), 'menuitem');
  });

  maybe('libellé de l\'entrée selon l\'état : « Exclure la pièce… » / « Ne plus exclure la pièce… »', () => {
    const ui = startPage({ scene: SCENE_EXCLUDED });
    assert.equal(plain(ui.$(`${CARD(3)} .j2ha-room-exclude`).text()), 'Ne plus exclure la pièce…');
    assert.equal(ui.$(`${CARD(3)} .j2ha-room-exclude`).attr('data-excluded'), '1');
    assert.equal(plain(ui.$(`${CARD(4)} .j2ha-room-exclude`).text()), 'Exclure la pièce…');
    assert.equal(ui.$(`${CARD(4)} .j2ha-room-exclude`).attr('data-excluded'), '0');
  });

  it('le CSS du composant de menu et des cartes n\'est pas modifié : ajouts seulement (leçon #296)', () => {
    const diff = diffAgainstBase(['-U0'], ['desktop/css/jeedom2ha.css']);
    if (diff === null) return;
    assert.deepEqual(removedLines(diff), [], 'aucune ligne de CSS existante modifiée ou retirée');
    const css = fs.readFileSync('desktop/css/jeedom2ha.css', 'utf8');
    for (const selector of ['.j2ha-room-has-menu', '.j2ha-room-excluded-line']) {
      assert.ok(css.includes(selector), selector);
      assert.ok(!new RegExp(`^${selector.replace('.', '\\.')}\\s*[,{]`, 'm').test(css), selector + ' : jamais un sélecteur nu');
    }
  });
});

describe('25.8 / AC6 — le menu n\'ouvre jamais la pièce', () => {
  maybe('clic sur le bouton « ⋯ » : propagation arrêtée, aucune pièce ouverte, menu ouvert', () => {
    const ui = startPage({ scene: SCENE_EXCLUDED });
    const e = fire(ui, `${CARD(4)} .j2ha-menu-toggle`, 'click', event());
    assert.ok(e.stopped >= 1, 'stopPropagation du clic');
    assert.deepEqual(ui.opened, []);
    assert.ok(ui.$(`${CARD(4)} .j2ha-room-menu`).hasClass('j2ha-menu-open'));
    assert.equal(ui.$(`${CARD(4)} .j2ha-menu-toggle`).attr('aria-expanded'), 'true');
  });

  maybe('keydown (Entrée, Espace, flèches, Échap) et keyup du bouton, du menu et de ses entrées : propagation arrêtée', () => {
    const ui = startPage({ scene: SCENE_EXCLUDED });
    for (const key of ['Enter', ' ', 'ArrowDown', 'ArrowUp', 'Escape']) {
      assert.ok(fire(ui, `${CARD(4)} .j2ha-menu-toggle`, 'keydown', event({ key })).stopped >= 1, 'bouton keydown ' + key);
      assert.ok(fire(ui, `${CARD(4)} .j2ha-menu`, 'keydown', event({ key })).stopped >= 1, 'menu keydown ' + key);
    }
    assert.ok(fire(ui, `${CARD(4)} .j2ha-menu-toggle`, 'keyup', event({ key: ' ' })).stopped >= 1, 'bouton keyup');
    assert.ok(fire(ui, `${CARD(4)} .j2ha-menu`, 'keyup', event({ key: ' ' })).stopped >= 1, 'menu keyup');
    assert.ok(fire(ui, `${CARD(4)} .j2ha-menu`, 'click', event()).stopped >= 1, 'zone du menu click');
    assert.deepEqual(ui.opened, []);
  });

  maybe('l\'écouteur clavier de la carte, lui, ouvre bien la pièce : seul un événement non arrêté l\'atteint', () => {
    const ui = startPage({ scene: SCENE_EXCLUDED });
    fire(ui, CARD(4), 'keydown', event({ key: 'Enter' }));
    assert.deepEqual(ui.opened, [4]);
  });

  maybe('clic sur l\'entrée : propagation arrêtée, la demande d\'exclusion part vers la fonction du gabarit, sans requête', () => {
    const ui = startPage({ scene: SCENE_EXCLUDED });
    const before = ui.calls.length;
    const e = fire(ui, `${CARD(4)} .j2ha-room-exclude`, 'click', event());
    assert.ok(e.stopped >= 1);
    assert.deepEqual(ui.opened, []);
    assert.equal(ui.excludeCalls.length, 1);
    const [id, name, excluded] = ui.excludeCalls[0];
    assert.equal([id, name, excluded].join('|'), '4|Salle B <i>fictive</i>|true');
    assert.equal(ui.calls.length, before, 'la page B ne fait aucune requête d\'écriture');
  });

  maybe('une pièce déjà exclue demande « ne plus exclure » (excluded=false)', () => {
    const ui = startPage({ scene: SCENE_EXCLUDED });
    fire(ui, `${CARD(3)} .j2ha-room-exclude`, 'click', event());
    assert.equal(ui.excludeCalls[0][2], false);
  });

  maybe('une entrée grisée (gating, opération en cours) ne demande rien', () => {
    const ui = startPage({ scene: SCENE_EXCLUDED });
    assert.equal(ui.$(`${CARD(4)} .j2ha-room-exclude`).attr('disabled'), '', 'rendue grisée par la page (levée par le gating du pont)');
    ui.$(`${CARD(4)} .j2ha-room-exclude`).prop('disabled', true);
    fire(ui, `${CARD(4)} .j2ha-room-exclude`, 'click', event());
    assert.equal(ui.excludeCalls.length, 0);
  });
});
