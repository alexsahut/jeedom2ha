// ARTEFACT — Story 25.3 (AC1, AC4, AC8 à AC12, AC13) : la page principale B rendue pour de vrai (squelette PHP
// exécuté avec un faux cœur Jeedom) puis animée par le VRAI jeedom2ha_overview.js sur le faux DOM. Aucun réseau ;
// identifiants, noms et couleurs fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const { SCENE, FIXTURE, plain, clone, phpAvailable, renderPhp, mainPart, equipmentsFor, okBody, startPage } = require('./helpers/page_b_harness');

const maybe = phpAvailable ? it : it.skip;

describe('25.3 / AC8 — le bandeau bleu disparaît, une ligne d’aide le remplace', () => {
  maybe('aucun .alert.alert-info.j2ha-surface-intro ; ligne d’aide ≤ 20 mots avec lien « Aide »', () => {
    const { html } = renderPhp(SCENE);
    const main = mainPart(html);
    assert.doesNotMatch(main, /j2ha-surface-intro|alert-info/);
    const help = main.match(/<p class="text-muted j2ha-help-line">([\s\S]*?)<\/p>/);
    assert.ok(help, 'ligne d’aide');
    const sentence = plain(help[1].replace(/<a [\s\S]*?<\/a>/, ''));
    assert.ok(sentence.trim().split(/\s+/).length <= 20, sentence);
    assert.doesNotMatch(sentence, /prêt|bloquant/i);
    assert.match(help[1], /<a href="https:\/\/doc\.example\.test\/plugin" target="_blank" rel="noopener">\{\{Aide\}\}<\/a>/);
    assert.equal(fs.existsSync('desktop/css/jeedom2ha.css'), true);
    assert.doesNotMatch(fs.readFileSync('desktop/css/jeedom2ha.css', 'utf8'), /j2ha-surface-intro/);
    assert.doesNotMatch(fs.readFileSync('desktop/php/jeedom2ha.php', 'utf8').replace(/<!--[\s\S]*?-->/g, ''), /j2ha-surface-intro/);
  });

  maybe('lien d’aide : repli sur le lien d’info.json si le cœur ne fournit pas une URL https', () => {
    const { html } = renderPhp(Object.assign({}, SCENE, { doc: 'javascript:alert(1)' }));
    assert.match(html, /href="https:\/\/github\.com\/alexsahut\/jeedom2ha\/blob\/stable\/docs\/fr_FR\/index\.md"/);
    assert.doesNotMatch(html, /javascript:alert/);
  });

  maybe('la note « type natif Jeedom partagé avec Homebridge » est reportée dans la documentation, pas en bandeau', () => {
    const doc = fs.readFileSync('docs/fr_FR/index.md', 'utf8');
    assert.match(doc, /Homebridge/);
    assert.match(doc, /type natif Jeedom/);
  });
});

describe('25.3 / AC9 — barre de santé compacte, actions, menu « ⋯ »', () => {
  maybe('identifiants et attributs conservés ; quatre briques ; Republier tout et Relire Jeedom puis « ⋯ »', () => {
    const main = mainPart(renderPhp(SCENE).html);
    for (const id of ['span_healthBridge', 'span_healthMqtt', 'span_healthMqttBroker', 'span_healthSync', 'span_healthOp', 'span_healthOpMsg', 'bt_rescanTopology', 'div_haGatingReason', 'div_haActions']) {
      assert.ok(main.includes(`id="${id}"`), id);
    }
    const labels = [...main.matchAll(/<strong>(\{\{[^}]+\}\})<\/strong>/g)].map((m) => plain(m[1]));
    assert.deepEqual(labels, ['Démon', 'MQTT', 'Dernière synchro', 'Dernière opération']);
    assert.match(main, /data-ha-action="republier"[\s\S]*?\{\{Republier tout\}\}/);
    assert.match(main, /data-ha-action="rescan"/);
    assert.match(main, /aria-label="\{\{Plus d'actions\}\}"/);
    assert.match(main, /aria-haspopup="menu" aria-expanded="false"/);
    assert.doesNotMatch(main, /well/, 'plus de bloc « well » plein écran');
    assert.ok(!main.includes('{{Actions Home Assistant}}'), 'plus de zone « Actions Home Assistant »');
  });

  maybe('menu : « Télécharger le diagnostic… », « Télécharger l’export de décision… » (24.2), séparateur, « Supprimer tout de Home Assistant… » seul rouge, gating conservé', () => {
    const ui = startPage();
    const items = ui.$('#j2ha_moreMenu .j2ha-menu li').list.map((li) => ({
      role: li.attrs.role, text: plain(ui.$(li).text()).trim(),
    }));
    assert.deepEqual(items, [
      { role: 'none', text: 'Télécharger le diagnostic…' },
      { role: 'none', text: 'Télécharger l\'export de décision…' },
      { role: 'separator', text: '' },
      { role: 'none', text: 'Supprimer tout de Home Assistant…' },
    ]);
    const danger = ui.$('.j2ha-menu-danger');
    assert.equal(danger.length, 1);
    assert.equal(danger.attr('data-ha-action'), 'supprimer-recreer');
    assert.ok(danger.hasClass('j2ha-ha-action'), 'même gestionnaire et même gating qu’avant');
    assert.equal(ui.$('.j2ha-ha-action[data-ha-action="supprimer-recreer"]').length, 1);
    assert.equal(ui.$('.j2ha-btn-danger').length, 0);
  });

  maybe('le menu s’ouvre au clic et au clavier, se ferme par Échap (focus rendu) et par clic extérieur', () => {
    const ui = startPage();
    const wrap = () => ui.$('#j2ha_moreMenu .j2ha-menu-wrap');
    assert.equal(ui.$('.j2ha-menu-toggle').attr('aria-expanded'), 'false');
    ui.click('.j2ha-menu-toggle');
    assert.ok(wrap().hasClass('j2ha-menu-open'));
    assert.equal(ui.$('.j2ha-menu-toggle').attr('aria-expanded'), 'true');
    assert.equal(ui.dom.focused, ui.$('#bt_openDiagnostic').list[0], 'le premier élément actif prend le focus');
    ui.key('#j2ha_moreMenu .j2ha-menu', 'Escape');
    assert.ok(!wrap().hasClass('j2ha-menu-open'));
    assert.equal(ui.dom.focused, ui.$('.j2ha-menu-toggle').list[0], 'le focus revient au bouton');
    ui.key('.j2ha-menu-toggle', 'ArrowDown');
    assert.ok(wrap().hasClass('j2ha-menu-open'), 'ouverture au clavier');
    ui.dom.documentEl.handlers.click.call(ui.dom.documentEl, { target: ui.dom.body });
    assert.ok(!wrap().hasClass('j2ha-menu-open'), 'clic extérieur');
  });

  maybe('« Télécharger le diagnostic… » ouvre une boîte qui porte la case et le bouton ; fermer n’émet aucune écriture', () => {
    const ui = startPage();
    const before = ui.calls.length;
    ui.click('#bt_openDiagnostic');
    assert.equal(ui.dom.dialogs.length, 1);
    const dialog = ui.dom.dialogs[0];
    assert.match(plain(dialog.options.title), /diagnostic/i);
    const modal = ui.$(dialog.modal);
    assert.equal(modal.find('#cb_pseudonymize').length, 1, 'la case « Pseudonymiser »');
    assert.equal(modal.find('#bt_exportDiagnostic').length, 1);
    assert.match(plain(modal.text()), /Pseudonymiser les noms d'équipements/);
    dialog.close();
    assert.equal(ui.calls.length, before, 'fermer ne déclenche aucune requête');
    assert.equal(ui.$('#div_diagnosticDialog #bt_exportDiagnostic').length, 1, 'le contenu retourne à sa place');
  });

  maybe('l’export garde son comportement : même action ajax et mêmes paramètres (source inchangée)', () => {
    const src = fs.readFileSync('desktop/js/jeedom2ha.js', 'utf8');
    assert.match(src, /action:\s+'exportDiagnostic'/);
    assert.match(src, /pseudonymize: \$\('#cb_pseudonymize'\)\.is\(':checked'\) \? '1' : '0'/);
    assert.match(src, /\$\('#bt_exportDiagnostic'\)\.on\('click'/);
  });
});

describe('25.3 / AC1, AC10 — bloc maison', () => {
  maybe('un seul appel au chargement, sans refresh, aucun getMappingOverrides', () => {
    const ui = startPage({ answer: false });
    assert.equal(ui.calls.length, 1);
    assert.equal(ui.calls[0].action, 'getEquipmentStates');
    assert.equal('refresh' in ui.calls[0].data, false);
    assert.equal(ui.calls.filter((c) => c.action === 'getMappingOverrides').length, 0);
  });

  maybe('« N publiés sur M », équipements Jeedom et pièces, jauge role="img" qui somme à M', () => {
    const ui = startPage();
    const overview = ui.page.view().overview;
    assert.equal(ui.text('#j2ha_houseNumber'), String(overview.counts.published));
    assert.equal(ui.text('#j2ha_houseSub'), `${overview.counts.published > 1 ? 'publiés' : 'publié'} sur ${overview.total}`);
    assert.equal(overview.total, 12);
    assert.equal(ui.text('#j2ha_houseMeta'), '12 équipements Jeedom, 4 pièces');
    const gauge = ui.$('#j2ha_houseGauge .j2ha-gauge');
    assert.equal(gauge.length, 1);
    assert.equal(gauge.attr('role'), 'img');
    assert.equal(plain(gauge.attr('aria-label')).startsWith(`${overview.counts.published} publié`), true);
    const segs = ui.$('#j2ha_houseGauge .j2ha-seg').list;
    assert.equal(segs.reduce((n, el) => n + Number(/flex-grow:(\d+)/.exec(el.attrs.style)[1]), 0), overview.total);
    segs.forEach((el) => assert.equal(el.attrs['aria-hidden'], 'true'));
    assert.doesNotMatch(plain(ui.dom.body.children.map((c) => ui.$(c).text()).join(' ')), /Sera publié|prête|NaN|undefined/);
  });

  maybe('légende en puces : button aria-pressed, ordre fixe, puces à zéro désactivées, « non lus » seulement si > 0', () => {
    const ui = startPage();
    const chips = ui.$('#j2ha_houseChips .j2ha-chip-filter').list;
    assert.deepEqual(chips.map((c) => c.attrs['data-filter']), ['published', 'blocked', 'to_apply', 'other', 'unread']);
    chips.forEach((c) => { assert.equal(c.tag, 'button'); assert.equal(c.attrs['aria-pressed'], 'false'); });
    const counts = ui.page.view().overview.counts;
    chips.forEach((c) => assert.equal(c.props.disabled === true, counts[c.attrs['data-filter']] === 0, c.attrs['data-filter']));
    assert.equal(counts.unread, 1);
    assert.equal(plain(ui.$(chips[4]).text()).trim(), '1 non lu');
    // Sans équipement non lu, la puce « non lus » n’existe pas.
    const rooms = ui.rooms.map((r) => Object.assign({}, r, { equipments: r.equipments.filter((e) => e.eq_id !== 998) }));
    const all = O.computeOverview(rooms, equipmentsFor(ui.rooms));
    assert.equal(all.counts.unread, 0);
  });

  maybe('« Actualiser » et « Chiffres relus à HH:MM » (heure locale de la lecture)', () => {
    const ui = startPage();
    const at = ui.page.reader.state().readAt;
    const hhmm = ('0' + at.getHours()).slice(-2) + ':' + ('0' + at.getMinutes()).slice(-2);
    assert.equal(ui.text('#j2ha_freshness'), `Chiffres relus à ${hhmm}`);
    assert.equal(plain(ui.$('#bt_refreshStates').text()).trim(), 'Actualiser');
  });

  maybe('« Actualiser » : un appel refresh=1, bouton désactivé pendant l’attente, puis réactivé', () => {
    const ui = startPage();
    ui.click('#bt_refreshStates');
    const refresh = ui.calls.filter((c) => !c.settled);
    assert.equal(refresh.length, 1);
    assert.equal(refresh[0].data.refresh, '1');
    assert.equal(ui.$('#bt_refreshStates').prop('disabled'), true);
    assert.equal(ui.$('#bt_refreshStates').attr('aria-busy'), 'true');
    assert.match(plain(ui.$('#bt_refreshStates').text()), /Actualisation/);
    ui.answer(okBody(equipmentsFor(ui.rooms)));
    assert.equal(ui.$('#bt_refreshStates').prop('disabled'), false);
    assert.equal(ui.calls.filter((c) => c.data.refresh === '1').length, 1, 'le seul refresh=1 de la session');
  });
});

describe('25.3 / AC11 — filtres globaux sans requête réseau', () => {
  maybe('chaque puce non vide affiche la liste ; le nombre de lignes égale le nombre annoncé ; 0 appel ajax', () => {
    const ui = startPage();
    const before = ui.calls.length;
    const counts = ui.page.view().overview.counts;
    for (const key of ['published', 'blocked', 'to_apply', 'other', 'unread']) {
      if (counts[key] === 0) continue;
      ui.click(`#j2ha_houseChips .j2ha-chip-filter[data-filter="${key}"]`);
      assert.equal(ui.$('#j2ha_filterList .j2ha-frow').length, counts[key], key);
      assert.equal(ui.$(`#j2ha_houseChips .j2ha-chip-filter[data-filter="${key}"]`).attr('aria-pressed'), 'true');
      ui.click(`#j2ha_houseChips .j2ha-chip-filter[data-filter="${key}"]`);
      assert.equal(ui.$('#j2ha_filterList .j2ha-frow').length, 0, 'second clic = filtre retiré');
    }
    assert.equal(ui.calls.length, before, 'aucune requête réseau');
  });

  maybe('l’ordre de la liste est celui de la grille (pièces regroupées par parent), puis l’ordre natif', () => {
    const ui = startPage();
    const grid = ui.$('#j2ha_roomCards .j2ha-room-card').list.map((el) => Number(el.attrs['data-object_id']));
    assert.deepEqual(grid, [5, 2, 3, 4, 0], 'la grille regroupe : isolées, groupe du parent, Sans pièce');
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]');
    const roomIds = ui.$('#j2ha_filterList .j2ha-frow-btn').list.map((el) => Number(el.attrs['data-room-id']));
    assert.ok(roomIds.length > 2);
    const ranks = roomIds.map((id) => grid.indexOf(id));
    assert.deepEqual(ranks, [...ranks].sort((a, b) => a - b), 'ordre de la grille');
    // Au sein d'une pièce, l'ordre natif de j2haRoomsTree est conservé.
    const inRoom = (id) => ui.$('#j2ha_filterList .j2ha-frow-btn').list.filter((el) => Number(el.attrs['data-room-id']) === id)
      .map((el) => plain(ui.$(el).find('.j2ha-frow-name').text()));
    for (const id of grid) {
      const names = inRoom(id);
      assert.deepEqual(names, [...names].sort((a, b) => Number(a.slice(3)) - Number(b.slice(3))), 'ordre natif dans la pièce ' + id);
    }
  });

  maybe('un segment de la jauge et la puce partagent le même gestionnaire', () => {
    const ui = startPage();
    ui.click('#j2ha_houseGauge .j2ha-seg[data-filter="published"]');
    assert.equal(ui.page.filter(), 'published');
    assert.equal(ui.$('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]').attr('aria-pressed'), 'true');
  });

  maybe('Échap et « Tout afficher » retirent le filtre ; le texte des lignes est échappé (nom libre)', () => {
    const ui = startPage();
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]');
    assert.ok(ui.page.filter());
    ui.key('#j2ha_filterPanel', 'Escape');
    assert.equal(ui.page.filter(), null);
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]');
    ui.click('#bt_clearFilter');
    assert.equal(ui.page.filter(), null);
    for (const key of ['published', 'other', 'to_apply', 'blocked']) {
      const chip = ui.$(`#j2ha_houseChips .j2ha-chip-filter[data-filter="${key}"]`);
      if (chip.prop('disabled')) continue;
      ui.page.setFilter(key);
      ui.$('#j2ha_filterList .j2ha-frow-name').list.forEach((n) => assert.doesNotMatch(ui.$(n).html(), /<b>|<i>/));
      ui.page.setFilter(null);
    }
  });

  maybe('une ligne porte état (mot + icône), nom, pièce ; un clic ouvre la fenêtre de la pièce ; cartes sans correspondance atténuées', () => {
    const ui = startPage();
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="unread"]');
    const row = ui.$('#j2ha_filterList .j2ha-frow-btn').first();
    assert.match(plain(row.text()), /Non lu/);
    assert.match(plain(row.text()), /Eq 998/);
    assert.match(plain(row.text()), /Salle B/);
    assert.ok(row.find('.fa-question-circle').length === 1, 'icône + mot');
    row.list[0].handlers.click.call(row.list[0], {});
    assert.deepEqual(ui.opened, [4]);
    const cards = ui.$('#j2ha_roomCards .j2ha-room-card').list;
    const dimmed = cards.filter((c) => c.classes.has('j2ha-room-dim')).map((c) => c.attrs['data-object_id']);
    assert.deepEqual(dimmed.sort(), ['0', '2', '3', '5'], 'seule la pièce B contient un équipement non lu');
    assert.equal(ui.$('#j2ha_roomCards .j2ha-room-card').length, 5, 'aucune carte masquée');
  });

  maybe('après une relecture, un filtre actif est réappliqué aux nouveaux chiffres', () => {
    const ui = startPage();
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]');
    const before = ui.$('#j2ha_filterList .j2ha-frow').length;
    const equipments = equipmentsFor(ui.rooms);
    Object.values(equipments).forEach((entry) => { entry.sync_status.published_in_ha = false; });
    ui.page.reader.trigger();
    ui.timers.splice(0).forEach((t) => t.fn());
    ui.answer(okBody(equipments));
    assert.equal(ui.page.filter(), 'published');
    assert.equal(ui.$('#j2ha_filterList .j2ha-frow').length, ui.page.view().overview.counts.published);
    assert.ok(before >= 0);
  });
});

describe('25.3 / AC12 — cartes de pièce', () => {
  maybe('jauge, « n / t publiés », repères non nuls seulement, liseré orange si bloqué ; somme des cartes = maison', () => {
    const ui = startPage();
    const o = ui.page.view().overview;
    const sum = (key) => o.rooms.reduce((n, r) => n + r.counts[key], 0);
    for (const key of ['published', 'to_apply', 'blocked', 'other', 'unread']) assert.equal(sum(key), o.counts[key], key);
    o.rooms.forEach((room) => {
      const card = ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${room.object_id}"]`);
      assert.equal(card.length, 1);
      const ratio = plain(card.find('.j2ha-room-ratio').text());
      assert.equal(ratio, `${room.counts.published} / ${room.summary.equipments_total} ${room.counts.published > 1 ? 'publiés' : 'publié'}`);
      const gauge = card.find('.j2ha-gauge');
      assert.equal(gauge.length, 1);
      assert.equal(gauge.attr('role'), 'img');
      assert.equal(card.find('.j2ha-seg').list.reduce((n, el) => n + Number(/flex-grow:(\d+)/.exec(el.attrs.style)[1]), 0), room.summary.equipments_total);
      assert.equal(card.find('.j2ha-mark-blocked').length, room.counts.blocked > 0 ? 1 : 0);
      assert.equal(card.find('.j2ha-mark-to_apply').length, room.counts.to_apply > 0 ? 1 : 0);
      assert.equal(card.find('.j2ha-mark-unread').length, room.counts.unread > 0 ? 1 : 0);
      assert.equal(card.hasClass('j2ha-room-blocked'), room.counts.blocked > 0);
      assert.match(card.attr('aria-label'), new RegExp(room.object_name.replace(/[<>/]/g, '.').slice(0, 5)));
    });
    assert.equal(ui.$('#j2ha_roomCards .j2ha-mark-unread').text().replace(/\{\{|\}\}/g, ''), '1 non lu');
  });

  maybe('contrat de la carte conservé : objectDisplayCard, cursor, j2ha-room-card, data-object_id, onclick, jamais eqLogicDisplayCard', () => {
    const { html } = renderPhp(SCENE);
    const cards = [...html.matchAll(/<div class="objectDisplayCard cursor j2ha-room-card"[^>]*>/g)].map((m) => m[0]);
    assert.equal(cards.length, 5);
    cards.forEach((tag) => {
      assert.match(tag, /data-object_id="\d+"/);
      assert.match(tag, /onclick="j2haOpenRoom\(\d+\)"/);
      assert.match(tag, /tabindex="0" role="button"/);
    });
    assert.doesNotMatch(html, /eqLogicDisplayCard/);
  });

  maybe('la carte est opérable au clavier (Entrée, Espace)', () => {
    const ui = startPage();
    ui.key('#j2ha_roomCards .j2ha-room-card[data-object_id="3"]', 'Enter');
    ui.key('#j2ha_roomCards .j2ha-room-card[data-object_id="0"]', ' ');
    assert.deepEqual(ui.opened, [3, 0]);
  });

  maybe('la pseudo-pièce « Sans pièce » est rendue comme les autres, icône de repli, en dernier', () => {
    const ui = startPage();
    const cards = ui.$('#j2ha_roomCards .j2ha-room-card').list;
    assert.equal(cards[cards.length - 1].attrs['data-object_id'], '0');
    assert.ok(ui.$(cards[cards.length - 1]).find('.fa-door-open').length === 1);
    assert.equal(ui.$(cards[cards.length - 1]).find('.j2ha-gauge').length, 1);
  });

  maybe('toutes les pièces de j2haRoomsTree sont rendues, sans filtre implicite (Q11)', () => {
    const ui = startPage();
    assert.equal(ui.$('#j2ha_roomCards .j2ha-room-card').length, ui.rooms.length);
  });
});

describe('25.3 / AC4, D2 — états de rendu dans la page', () => {
  maybe('avant la première synchro : jauge neutre, message, cartes sans jauge, aucune relecture automatique', () => {
    const ui = startPage({ answer: false });
    ui.answer({ state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: false, equipments: {}, unread: [] } } });
    assert.equal(ui.text('#j2ha_readStatus'), 'Aucune synchronisation n\'a encore eu lieu');
    assert.equal(ui.$('#j2ha_houseGauge .j2ha-gauge-neutral').length, 1);
    assert.equal(ui.$('#j2ha_houseChips .j2ha-chip-filter').length, 0);
    assert.equal(ui.$('#j2ha_roomCards .j2ha-gauge').length, 0);
    assert.equal(ui.$('#j2ha_roomCards .j2ha-room-card').length, 5, 'cartes comme aujourd’hui');
    assert.equal(ui.timers.length, 0);
    assert.doesNotMatch(ui.text('#j2ha_houseBlock'), /NaN|undefined|0 publiés sur 0/);
  });

  maybe('action en cours : chiffres affichés + mention role="status" ; relecture planifiée', () => {
    const ui = startPage({ answer: false });
    ui.answer(okBody(equipmentsFor(ui.rooms), { action_in_progress: true }));
    assert.equal(ui.text('#j2ha_readStatus'), 'Opération en cours : ces chiffres peuvent changer');
    assert.equal(ui.$('#j2ha_readStatus').attr('role'), 'status');
    assert.equal(ui.$('#j2ha_readStatus').attr('aria-live'), 'polite');
    assert.ok(ui.$('#j2ha_houseChips .j2ha-chip-filter').length > 0);
    assert.equal(ui.timers.filter((t) => t.ms === 2000).length, 1);
  });

  maybe('reason:action_in_progress sans chiffres : « Mise à jour en cours… » ; avec chiffres en mémoire : atténués', () => {
    const ui = startPage({ answer: false });
    ui.answer({ state: 'ok', result: { status: 'ok', payload: { available: false, reason: 'action_in_progress', equipments: {}, unread: [] } } });
    assert.equal(ui.text('#j2ha_readStatus'), 'Mise à jour en cours…');
    assert.equal(ui.$('#j2ha_houseGauge .j2ha-gauge-neutral').length, 1);
    // Chiffres valides puis opération : atténués.
    const ui2 = startPage();
    ui2.page.reader.trigger();
    ui2.timers.splice(0).forEach((t) => t.fn());
    ui2.answer({ state: 'ok', result: { status: 'ok', payload: { available: false, reason: 'action_in_progress', equipments: {}, unread: [] } } });
    assert.ok(ui2.$('#j2ha_houseBlock').hasClass('j2ha-stale'));
    assert.ok(ui2.$('#j2ha_houseChips .j2ha-chip-filter').length > 0);
    assert.equal(ui2.text('#j2ha_readStatus'), 'Opération en cours : ces chiffres peuvent changer');
  });

  maybe('erreur ajax : « Chiffres indisponibles », bouton « Actualiser » actif, derniers chiffres atténués', () => {
    const ui = startPage();
    ui.page.reader.trigger();
    ui.timers.splice(0).forEach((t) => t.fn());
    ui.answer(null);
    assert.equal(ui.text('#j2ha_readStatus'), 'Chiffres indisponibles');
    assert.equal(ui.$('#bt_refreshStates').prop('disabled'), false);
    assert.ok(ui.$('#j2ha_houseBlock').hasClass('j2ha-stale'));
    const first = startPage({ answer: false });
    first.answer(null);
    assert.equal(first.text('#j2ha_readStatus'), 'Chiffres indisponibles');
    assert.equal(first.$('#j2ha_houseChips .j2ha-chip-filter').length, 0);
    assert.equal(first.timers.length, 0, 'pas de relecture automatique sur erreur');
  });

  maybe('la zone d’état est un role="status" aria-live="polite" dès le rendu', () => {
    const main = mainPart(renderPhp(SCENE).html);
    assert.match(main, /id="j2ha_readStatus"[^>]*role="status" aria-live="polite"/);
  });
});

describe('25.3 / AC13 — icône, couleur Jeedom, regroupement par objet parent', () => {
  maybe('chaque carte reprend l’icône de l’objet (repli : porte) et sa couleur validée (data-color)', () => {
    const ui = startPage({ answer: false });
    const card = (id) => ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${id}"]`);
    assert.ok(card(2).find('.j2ha-room-icon').hasClass('fa-bed'));
    assert.equal(card(2).attr('data-color'), '#ff8800');
    assert.ok(card(3).find('.j2ha-room-icon').hasClass('jeedom-maison'));
    assert.equal(card(3).attr('data-color'), undefined);
    assert.equal(card(4).attr('data-color'), '#123');
    assert.ok(card(5).find('.j2ha-room-icon').hasClass('fa-door-open'), 'repli : porte');
  });

  maybe('cartes regroupées par parent : isolées sans sous-titre, groupe du parent (sa carte en tête), « Sans pièce » en dernier', () => {
    const { html } = renderPhp(SCENE);
    const groups = [...html.matchAll(/<div class="j2ha-room-group">(?:<h4 class="j2ha-room-group-title j2ha-free-name">([^<]*)<\/h4>)?([\s\S]*?)<\/div><\/div>(?=<div class="j2ha-room-group">|<\/div>)/g)]
      .map((m) => ({ title: m[1] || null, ids: [...m[2].matchAll(/data-object_id="(\d+)"/g)].map((x) => Number(x[1])) }));
    assert.deepEqual(groups, [
      { title: null, ids: [5] },
      { title: 'Maison fictive › Étage fictif', ids: [2, 3, 4] },
      { title: null, ids: [0] },
    ]);
  });

  maybe('l’ordre natif de Jeedom est conservé à l’intérieur de chaque groupe', () => {
    const scene = clone(SCENE);
    scene.objects = [
      { id: 10, name: 'Parent sans équipement', father_id: null, display: {} },
      { id: 12, name: 'Zèbre', father_id: 10, display: {} },
      { id: 11, name: 'Abeille', father_id: 10, display: {} },
    ];
    scene.eqlogics = { 12: [{ id: 1, name: 'a' }], 11: [{ id: 2, name: 'b' }] };
    const { html } = renderPhp(scene);
    assert.match(html, /Parent sans équipement<\/h4>[\s\S]*data-object_id="12"[\s\S]*data-object_id="11"/);
  });

  maybe('l’extension de j2haRoomsTree est additive : champs historiques inchangés, deux variables JS (+ eq_type et j2haPluginNames de 25.7)', () => {
    const { vars } = renderPhp(SCENE);
    const room = vars.j2haRoomsTree.find((r) => r.object_id === 3);
    // Story 25.8 : `excluded` est ajouté (champ additif) ; les sept champs historiques sont inchangés.
    assert.deepEqual(Object.keys(room).sort(), ['color', 'equipments', 'excluded', 'father_id', 'icon_classes', 'object_id', 'object_name', 'parent_number']);
    assert.equal(typeof room.excluded, 'boolean');
    assert.equal(typeof room.object_id, 'number');
    // Story 25.7 : `eq_type` est ajouté (identifiant du plugin) ; les trois champs historiques sont inchangés.
    assert.deepEqual(Object.keys(room.equipments[0]).sort(), ['enabled', 'eq_id', 'eq_name', 'eq_type']);
    assert.equal(typeof vars.j2haPluginNames, 'object');
    assert.deepEqual(vars.j2haAncestors, [{ object_id: 1, name: 'Maison fictive', father_id: 0 }]);
  });

  maybe('entrées hostiles : repli sûr, jamais de HTML d’icône brut dans la page', () => {
    const scene = clone(SCENE);
    scene.objects = [
      { id: 1, name: 'H1', father_id: null, display: { icon: '"><script>alert(1)</script>', tagColor: 'red;background:url(x)' } },
      { id: 2, name: 'H2', father_id: null, display: { icon: '<i class="javascript:alert(1)"></i>', tagColor: '#12345' } },
      { id: 3, name: 'H3', father_id: null, display: { icon: '<i class="evil-class fas"></i>', tagColor: 'expression(1)' } },
      { id: 4, name: 'H4', father_id: null, display: { icon: '<i class="fas fa-bed" onclick="x()"><script>', tagColor: '#ABCDEF' } },
    ];
    scene.eqlogics = { 1: [{ id: 1, name: 'a' }], 2: [{ id: 2, name: 'b' }], 3: [{ id: 3, name: 'c' }], 4: [{ id: 4, name: 'd' }] };
    const { html, vars } = renderPhp(scene);
    assert.doesNotMatch(html.replace(/<!--[\s\S]*?-->/g, ''), /<script|javascript:|expression\(|url\(x\)|evil-class/);
    const rooms = Object.fromEntries(vars.j2haRoomsTree.map((r) => [r.object_id, r]));
    assert.equal(rooms[1].icon_classes, 'fas fa-door-open');
    assert.equal(rooms[1].color, '');
    assert.equal(rooms[2].icon_classes, 'fas fa-door-open');
    assert.equal(rooms[2].color, '');
    assert.equal(rooms[3].icon_classes, 'fas fa-door-open');
    assert.equal(rooms[4].icon_classes, 'fas fa-bed');
    assert.equal(rooms[4].color, '#ABCDEF');
    assert.doesNotMatch(html, /onclick="x\(\)"/);
  });

  maybe('la couleur n’est jamais appliquée au texte ni en fond : variable CSS d’accent seulement, repli --j2ha-*', () => {
    const css = fs.readFileSync('desktop/css/jeedom2ha.css', 'utf8');
    const uses = css.split('\n').filter((l) => /--j2ha-room-color/.test(l));
    assert.ok(uses.length >= 2);
    uses.forEach((line) => assert.match(line, /var\(--j2ha-room-color, var\(--(?:j2ha-|logo-primary-color)/));
    // Accent seulement : la couleur teinte l'icône (glyphe) et un filet de bordure ; jamais le texte ni un fond.
    const blocks = css.match(/[^{}]+\{[^{}]*--j2ha-room-color[^{}]*\}/g) || [];
    blocks.forEach((block) => {
      const selector = block.slice(0, block.indexOf('{')).trim();
      assert.doesNotMatch(block, /background(-color)?\s*:[^;]*--j2ha-room-color/, block);
      if (/(^|;|\{)\s*color\s*:[^;]*--j2ha-room-color/.test(block)) {
        // Story 25.4 : les icônes de l'arbre et du détail de la vue C portent la même couleur d'accent (glyphe seulement).
        assert.match(selector, /\.(j2ha-room-icon|j2ha-wv-icon|j2ha-wv-roomicon)$/, 'seule l\'icône peut porter la couleur : ' + selector);
      }
    });
  });
});
