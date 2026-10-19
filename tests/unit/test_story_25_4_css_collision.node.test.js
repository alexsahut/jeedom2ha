// ARTEFACT — Story 25.4 (AC2, AC24, AC25) : non-régression anti-collision du CSS. Leçon de la PR #296 : une règle de
// jauge sur `.j2ha-seg` nue avait réduit le contrôle segmenté « Automatique | Toujours | Jamais » à 2 px sur la box,
// et seul le gate l'avait vu. Trois contrôles : (1) PORTÉE — tout sélecteur ajouté est sous `.j2ha-wv` ou `.j2ha-wv-` ;
// (2) NON-MODIFICATION — aucune déclaration d'un sélecteur de la référence n'a changé (hors sélecteurs de la fenêtre
// de pièce retirés) ; (3) COLLISION VISUELLE dans un vrai Chromium (vrai CSS, vrai jQuery), avec un test NÉGATIF qui
// réinjecte la règle fautive et doit échouer. Données fictives (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { selectorTable } = require('./helpers/capture_story_25_4_references');
const { withRealView } = require('./helpers/workview_browser');

const root = path.join(__dirname, '..', '..');
const css = fs.readFileSync(path.join(root, 'desktop/css/jeedom2ha.css'), 'utf8');
const baseline = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/story_25_4_css_baseline.json'), 'utf8'));
const shared = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/story_25_4_shared_classes.json'), 'utf8'));
const finalTable = selectorTable(css);
const bare = (key) => key.replace(/^.*\| /, '');
// Story 25.7 (AC8) : UNE seule règle hors de .j2ha-wv, sur la classe nouvelle du repère de carte, déclarée sous .j2ha-room-groups.
const OUTSIDE_ALLOWED = ['.j2ha-room-groups .j2ha-mark.j2ha-mark-excluded'];
// Story 25.8 : menu « ⋯ » de la carte de pièce et ligne « Pièce exclue » — classes NOUVELLES de la story, sous .j2ha-room-groups.
const ROOM_CARD_25_8 = /^\.j2ha-room-groups \.j2ha-room-(card\.j2ha-room-has-menu|card \.j2ha-room-menu(-toggle|-list)?|excluded-line)/;

test('25.4 / AC25 (1) portée — tout sélecteur ajouté commence par .j2ha-wv ou contient .j2ha-wv-', () => {
  const added = Object.keys(finalTable).filter((key) => !(key in baseline.selectors));
  assert.ok(added.length > 0, 'la vue C a du CSS');
  const outside = added.filter((key) => !(bare(key).startsWith('.j2ha-wv') || bare(key).includes('.j2ha-wv-') || OUTSIDE_ALLOWED.includes(bare(key)) || ROOM_CARD_25_8.test(bare(key))));
  assert.deepEqual(outside, [], 'sélecteurs ajoutés hors de la portée de la vue');
  // Jamais un sélecteur nu sur un composant partagé ni un nom générique de la maquette.
  const generic = added.filter((key) => /(^|[\s>+~,])\.(seg|chip|pill|dot|row|btn|c-[a-z]+|j2ha-seg|j2ha-menu|j2ha-badge|j2ha-gauge|j2ha-state-[a-z_]+)([\s.:>+~,\[]|$)/.test(bare(key))
    && !/\.j2ha-wv/.test(bare(key).split(/\s+/)[0] || ''));
  assert.deepEqual(generic, []);
});

test('25.4 / AC25 (2) non-modification — aucune déclaration d’un sélecteur de la référence n’a changé', () => {
  const removed = new Set(baseline.modal_selectors);
  const changed = [];
  for (const [key, declarations] of Object.entries(baseline.selectors)) {
    if (removed.has(bare(key))) continue;
    if (finalTable[key] !== declarations) changed.push(key);
  }
  assert.deepEqual(changed, []);
});

test('25.4 / AC2 — les sélecteurs propres à la fenêtre de pièce sont supprimés (pas seulement inutilisés)', () => {
  const stillThere = baseline.modal_selectors.filter((selector) => Object.keys(finalTable).some((key) => bare(key) === selector));
  assert.deepEqual(stillThere, []);
  assert.doesNotMatch(css, /j2ha-eq-accordion|panel-group|panel-collapse|j2ha-eq-toggle/);
});

test('25.4 / AC24 — l’inventaire des classes partagées est écrit dans l’en-tête du bloc CSS de la vue', () => {
  const header = css.slice(css.indexOf('Vue de travail C'), css.indexOf('Vue de travail C') + 6000);
  assert.ok(css.includes('Vue de travail C'), 'bloc de la vue repérable');
  for (const component of shared.components) {
    for (const cls of component.classes.filter((c) => /^\.j2ha-(seg|menu-wrap|state-word|badge|gauge|chip)\b/.test(c)).slice(0, 1)) {
      assert.ok(header.includes(cls.replace(/^\./, '')), 'inventaire : ' + cls);
    }
  }
});

/** Mesures de non-collision sur la page réelle : le contrôle segmenté de la vue C, la jauge de la page B, et le contrôle « seul ». */
async function measure(page) {
  return page.evaluate(() => {
    const style = (el) => getComputedStyle(el);
    const group = document.querySelector('.j2ha-wv [role=radiogroup].j2ha-seg');
    const buttons = [...group.querySelectorAll('.j2ha-seg-btn')];
    const gaugeSeg = document.querySelector('#j2ha_roomCards .j2ha-gauge .j2ha-seg');
    // « Seul » : le même balisage hors de la vue et hors de la jauge.
    const alone = document.createElement('div');
    alone.id = 'j2ha-test-alone';
    alone.style.cssText = 'position:absolute;left:0;top:0;visibility:hidden';
    alone.innerHTML = group.outerHTML;
    document.body.appendChild(alone);
    const aloneGroup = alone.querySelector('[role=radiogroup].j2ha-seg');
    const out = {
      groupWidth: group.getBoundingClientRect().width,
      buttonsWidth: buttons.reduce((sum, b) => sum + b.getBoundingClientRect().width, 0),
      groupFlexBasis: style(group).flexBasis,
      groupMinWidth: style(group).minWidth,
      aloneWidth: aloneGroup.getBoundingClientRect().width,
      gaugeMinWidth: gaugeSeg ? style(gaugeSeg).minWidth : null,
      gaugeFlexBasis: gaugeSeg ? style(gaugeSeg).flexBasis : null,
      gaugeHeight: gaugeSeg ? gaugeSeg.getBoundingClientRect().height : null,
      neighbours: [...group.parentElement.children].map((el) => el.getBoundingClientRect().width),
    };
    alone.remove();
    return out;
  });
}

function assertNoCollision(m) {
  assert.ok(m.groupWidth > 2, `contrôle segmenté réduit à ${m.groupWidth}px`);
  assert.ok(m.groupWidth >= m.buttonsWidth - 1, `largeur ${m.groupWidth} inférieure à celle de ses boutons ${m.buttonsWidth}`);
  assert.ok(Math.abs(m.groupWidth - m.aloneWidth) <= 1, `taille différente dans la vue (${m.groupWidth}) et seul (${m.aloneWidth})`);
  assert.notEqual(m.groupMinWidth, '2px', 'min-width d’un segment de jauge sur le contrôle segmenté');
  assert.notEqual(m.groupFlexBasis, '0px', 'flex-basis d’un segment de jauge sur le contrôle segmenté');
  assert.ok(m.gaugeMinWidth === null || m.gaugeMinWidth === '2px', 'la jauge garde ses propres règles');
  assert.ok(m.gaugeFlexBasis === null || m.gaugeFlexBasis === '0px', 'la jauge garde ses propres règles');
}

async function openEquipment(page, ctx) {
  await page.locator('#j2ha_roomCards .j2ha-room-card').first().click();
  const eq = page.locator('.j2ha-wv-eq .j2ha-wv-row').first();
  await eq.click();
  await page.locator('.j2ha-wv [role=radiogroup].j2ha-seg .j2ha-seg-btn').first().waitFor({ state: 'visible' });
}

test('25.4 / AC25 (3) collision visuelle — le contrôle segmenté a la même taille dans la vue C, dans la page B et seul', async (t) => {
  await withRealView(t, {}, async (page, ctx) => {
    // Jauge de la page B (avant l'ouverture de la vue) : ses segments gardent leurs règles.
    const gaugeBefore = await page.evaluate(() => {
      const seg = document.querySelector('#j2ha_roomCards .j2ha-gauge .j2ha-seg');
      const s = getComputedStyle(seg);
      return { minWidth: s.minWidth, flexBasis: s.flexBasis, width: seg.getBoundingClientRect().width };
    });
    assert.equal(gaugeBefore.minWidth, '2px');
    assert.equal(gaugeBefore.flexBasis, '0px');
    assert.ok(gaugeBefore.width > 2);
    await openEquipment(page, ctx);
    assertNoCollision(await measure(page));
    // Retour : la jauge n'a pas bougé.
    await page.locator('.j2ha-wv-back').click();
    const gaugeAfter = await page.evaluate(() => {
      const seg = document.querySelector('#j2ha_roomCards .j2ha-gauge .j2ha-seg');
      const s = getComputedStyle(seg);
      return { minWidth: s.minWidth, flexBasis: s.flexBasis, width: seg.getBoundingClientRect().width };
    });
    assert.deepEqual(gaugeAfter, gaugeBefore);
    assert.deepEqual(ctx.errors, []);
  });
});

test('25.4 / AC25 — test négatif : la règle fautive de 25.3 (`.j2ha-seg { flex-basis: 0; min-width: 2px }` nue) FAIT ÉCHOUER le contrôle', async (t) => {
  await withRealView(t, { extraCss: '\n.j2ha-seg { flex-basis: 0; min-width: 2px; }\n' }, async (page, ctx) => {
    await openEquipment(page, ctx);
    const m = await measure(page);
    assert.throws(() => assertNoCollision(m), /réduit|inférieure|différente|min-width|flex-basis/);
  });
});
