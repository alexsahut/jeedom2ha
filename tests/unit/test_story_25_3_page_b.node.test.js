// ARTEFACT — Story 25.3 (AC1, AC4, AC8 à AC12, AC13) : la page principale B rendue pour de vrai (squelette PHP
// exécuté avec un faux cœur Jeedom) puis animée par le VRAI jeedom2ha_overview.js sur le faux DOM. Aucun réseau ;
// identifiants, noms et couleurs fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const O = require('../../desktop/js/jeedom2ha_overview.js');
const { SCENE, FIXTURE, plain, clone, phpAvailable, renderPhp, mainPart, equipmentsFor, okBody, startPage } = require('./helpers/page_b_harness');
const { startGuide } = require('./helpers/guide_harness');

const maybe = phpAvailable ? it : it.skip;

describe('25.3 / AC8 — le bandeau bleu disparaît, une ligne d’aide le remplace', () => {
  // Garde levée (front v3, Lot 1, « zéro paragraphe permanent ») : la ligne d'aide disparaît ; le lien « Aide » devient une
  // icône `fa-question-circle` de la barre d'état (title et aria-label « Aide »), même URL.
  maybe('aucun .alert.alert-info.j2ha-surface-intro ; aucune ligne d’aide ; lien « Aide » en icône dans la barre d’état', () => {
    const { html } = renderPhp(SCENE);
    const main = mainPart(html);
    assert.doesNotMatch(main, /j2ha-surface-intro|alert-info/);
    assert.doesNotMatch(main, /j2ha-help-line/);
    assert.match(main, /<a class="btn btn-default btn-sm j2ha-v3-icon-btn j2ha-v3-help" href="https:\/\/doc\.example\.test\/plugin" target="_blank" rel="noopener"\s+title="\{\{Aide\}\}" aria-label="\{\{Aide\}\}"><i class="fas fa-question-circle"><\/i><\/a>/);
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
    // Garde levée (front v3, Lot 1) : pastilles « point + mot » (Démon, MQTT, Home Assistant), le mot porté par `data-word`
    // et le détail en info-bulle ; « Relu HH:MM » ; « Dernière opération » masquée sauf échec ; plus d'intitulés <strong>.
    const words = [...main.matchAll(/class="j2ha-v3-pill" data-word="([^"]*)"/g)].map((m) => plain(m[1]));
    assert.deepEqual(words, ['Démon', 'MQTT', 'Home Assistant', '']);
    assert.doesNotMatch(main, /<strong>\{\{(Dernière relecture|Dernière opération)\}\}<\/strong>/);
    // « Republier tout » passe dans le menu ⋯ ; « Appliquer (n) » (masqué tant que n = 0) précède « Relire Jeedom ».
    assert.match(main, /id="bt_j2haApply"[\s\S]*?data-ha-action="appliquer"[\s\S]*?hidden[\s\S]*?id="bt_rescanTopology"/);
    assert.match(main, /<ul class="j2ha-menu" role="menu">[\s\S]*?data-ha-action="republier"[\s\S]*?\{\{Republier tout\}\}/);
    assert.match(main, /data-ha-action="rescan"/);
    // ⚙ : la configuration du plugin, même déclencheur du cœur que l'ancienne tuile « Gestion / Configuration ».
    assert.match(main, /class="btn btn-default btn-sm eqLogicAction j2ha-v3-icon-btn" data-action="gotoPluginConf"\s+title="\{\{Configuration\}\}" aria-label="\{\{Configuration\}\}"/);
    assert.doesNotMatch(main, /\{\{Gestion\}\}|logoSecondary/);
    // Garde levée (front v2, Lot 1) : glossaire 3.2 « Plus d'actions » → « Autres actions ».
    assert.match(main, /aria-label="\{\{Autres actions\}\}"/);
    assert.match(main, /aria-haspopup="menu" aria-expanded="false"/);
    assert.doesNotMatch(main, /well/, 'plus de bloc « well » plein écran');
    assert.ok(!main.includes('{{Actions Home Assistant}}'), 'plus de zone « Actions Home Assistant »');
  });

  // Garde levée (front v2, Lot 1) : les deux exports quittent le menu pour « Vérifier l'installation… » (E7).
  // Garde levée (front v3, Lot 1) : « Republier tout » rejoint le menu (geste de dépannage), avant le séparateur.
  maybe('menu : « Vérifier l’installation… », « Guide de démarrage », « Republier tout », séparateur, « Supprimer tout de Home Assistant… » seul rouge, gating conservé', () => {
    const ui = startPage();
    const items = ui.$('#j2ha_moreMenu .j2ha-menu li').list.map((li) => ({
      role: li.attrs.role, text: plain(ui.$(li).text()).trim(),
    }));
    assert.deepEqual(items, [
      { role: 'none', text: 'Vérifier l\'installation…' },
      { role: 'none', text: 'Guide de démarrage' },
      { role: 'none', text: 'Republier tout' },
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
    assert.equal(ui.dom.focused, ui.$('#bt_j2haCheckInstall').list[0], 'le premier élément actif prend le focus');
    ui.key('#j2ha_moreMenu .j2ha-menu', 'Escape');
    assert.ok(!wrap().hasClass('j2ha-menu-open'));
    assert.equal(ui.dom.focused, ui.$('.j2ha-menu-toggle').list[0], 'le focus revient au bouton');
    ui.key('.j2ha-menu-toggle', 'ArrowDown');
    assert.ok(wrap().hasClass('j2ha-menu-open'), 'ouverture au clavier');
    ui.dom.documentEl.handlers.click.call(ui.dom.documentEl, { target: ui.dom.body });
    assert.ok(!wrap().hasClass('j2ha-menu-open'), 'clic extérieur');
  });

  // Garde levée (front v2, Lot 1) : la case et le bouton du diagnostic sont portés par « Vérifier l'installation… ».
  maybe('« Vérifier l’installation… » porte la case et le bouton du diagnostic ; fermer n’émet aucune écriture', () => {
    const ui = startGuide();
    const before = ui.calls.length;
    ui.guide.openCheck();
    assert.equal(ui.dom.dialogs.length, 1);
    const dialog = ui.dom.dialogs[0];
    assert.match(plain(dialog.options.title), /Vérifier l'installation/);
    const modal = ui.$(dialog.modal);
    assert.equal(modal.find('#cb_pseudonymize').length, 1, 'la case « Pseudonymiser »');
    assert.equal(modal.find('#bt_exportDiagnostic').length, 1);
    // Garde levée (front v3, Lot 3) : libellés courts « Pseudonymiser » et « Diagnostic ».
    assert.match(plain(modal.text()), /Pseudonymiser/);
    assert.match(plain(modal.find('#bt_exportDiagnostic').text()), /Diagnostic/);
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

  // Garde levée (front v3, Lot 1) : chiffre « n / m » + « publiés » ; la ligne « 12 équipements Jeedom, 4 pièces » est retirée
  // (le nombre d'équipements est dans l'onglet) ; chaque segment du liseré porte `title` et `aria-label` avec son compte.
  maybe('« n / m publiés », onglet « Équipements m », liseré qui somme à m, segments étiquetés', () => {
    const ui = startPage();
    const overview = ui.page.view().overview;
    assert.equal(ui.text('#j2ha_houseNumber'), `${overview.counts.published} / ${overview.total}`);
    assert.equal(ui.text('#j2ha_houseSub'), overview.counts.published > 1 ? 'publiés' : 'publié');
    assert.equal(overview.total, 12);
    assert.equal(ui.text('#j2ha_tabEquipmentsCount'), '12');
    assert.equal(ui.$('#j2ha_houseMeta').length, 0);
    const gauge = ui.$('#j2ha_houseGauge .j2ha-gauge');
    assert.equal(gauge.length, 1);
    assert.equal(gauge.attr('role'), 'group');
    assert.equal(plain(gauge.attr('aria-label')).startsWith(`${overview.counts.published} publié`), true);
    const segs = ui.$('#j2ha_houseGauge .j2ha-seg').list;
    assert.equal(segs.reduce((n, el) => n + Number(/flex-grow:(\d+)/.exec(el.attrs.style)[1]), 0), overview.total);
    segs.forEach((el) => {
      const count = Number(/flex-grow:(\d+)/.exec(el.attrs.style)[1]);
      assert.equal(el.attrs.role, 'img');
      assert.equal(plain(el.attrs.title), plain(el.attrs['aria-label']));
      assert.match(plain(el.attrs.title), new RegExp('^' + count + ' '));
    });
    assert.doesNotMatch(plain(ui.dom.body.children.map((c) => ui.$(c).text()).join(' ')), /Sera publié|prête|NaN|undefined/);
  });

  // Garde levée (front v2, Lot 7, spec E2) : les puces à zéro ne sont plus grisées mais masquées.
  // Garde levée (front v3, Lot 1) : ordre du liseré (publiés, à appliquer, bloqués, exclus) ; une puce = icône + nombre + mot,
  // la définition en info-bulle.
  maybe('puces : button aria-pressed, ordre du liseré, puces à zéro masquées, « non lus » seulement si > 0, définition en info-bulle', () => {
    const ui = startPage();
    const chips = ui.$('#j2ha_houseChips .j2ha-chip-filter').list;
    const counts = ui.page.view().overview.counts;
    assert.deepEqual(chips.map((c) => c.attrs['data-filter']), ['published', 'to_apply', 'blocked', 'other', 'unread'].filter((key) => counts[key] > 0));
    chips.forEach((c) => { assert.equal(c.tag, 'button'); assert.equal(c.attrs['aria-pressed'], 'false'); });
    chips.forEach((c) => assert.notEqual(c.props.disabled, true, c.attrs['data-filter']));
    chips.forEach((c) => { assert.ok(c.attrs.title, 'définition en info-bulle'); assert.equal(ui.$(c).find('i.fas').length, 1, 'icône'); });
    assert.equal(counts.unread, 1);
    assert.equal(plain(ui.$(chips[chips.length - 1]).text()).trim(), '1 non lu');
    // Sans équipement non lu, la puce « non lus » n’existe pas.
    const rooms = ui.rooms.map((r) => Object.assign({}, r, { equipments: r.equipments.filter((e) => e.eq_id !== 998) }));
    const all = O.computeOverview(rooms, equipmentsFor(ui.rooms));
    assert.equal(all.counts.unread, 0);
  });

  // Garde levée (front v3, Lot 1) : « Chiffres relus à… / Actualiser » devient l'icône ↻, l'heure de lecture en info-bulle.
  maybe('↻ « Actualiser les chiffres » : heure locale de la lecture en info-bulle, aucune phrase', () => {
    const ui = startPage();
    const at = ui.page.reader.state().readAt;
    const hhmm = ('0' + at.getHours()).slice(-2) + ':' + ('0' + at.getMinutes()).slice(-2);
    assert.equal(plain(ui.$('#bt_refreshStates').attr('title')), `Actualiser les chiffres (relus à ${hhmm})`);
    assert.equal(plain(ui.$('#bt_refreshStates').attr('aria-label')), `Actualiser les chiffres (relus à ${hhmm})`);
    assert.equal(plain(ui.$('#bt_refreshStates').text()).trim(), '');
    assert.equal(ui.$('#j2ha_freshness').length, 0);
  });

  maybe('« Actualiser » : un appel refresh=1, bouton désactivé pendant l’attente, puis réactivé', () => {
    const ui = startPage();
    ui.click('#bt_refreshStates');
    const refresh = ui.calls.filter((c) => !c.settled);
    assert.equal(refresh.length, 1);
    assert.equal(refresh[0].data.refresh, '1');
    assert.equal(ui.$('#bt_refreshStates').prop('disabled'), true);
    assert.equal(ui.$('#bt_refreshStates').attr('aria-busy'), 'true');
    assert.match(plain(ui.$('#bt_refreshStates').attr('title')), /Actualisation/);
    assert.equal(ui.$('#bt_refreshStates .fa-spin').length, 1);
    ui.answer(okBody(equipmentsFor(ui.rooms)));
    assert.equal(ui.$('#bt_refreshStates').prop('disabled'), false);
    assert.equal(ui.calls.filter((c) => c.data.refresh === '1').length, 1, 'le seul refresh=1 de la session');
  });
});

describe('25.3 / AC11 — filtres globaux sans requête réseau', () => {
  // Garde levée (front v3, Lot 1, P8) : plus de liste filtrée (#j2ha_filterPanel). Les puces Publiés, À appliquer, Exclus et
  // Non lus filtrent la GRILLE (pièces à 0 masquées, compteurs filtrés) ; Bloqués (et Conseils) montrent la liste « À faire »
  // (la grille est alors masquée : une seule représentation à la fois). Second clic = filtre retiré.
  maybe('chaque puce de grille masque les pièces à 0 et filtre les compteurs ; second clic : tout revient ; 0 appel ajax', () => {
    const ui = startPage();
    const before = ui.calls.length;
    const o = ui.page.view().overview;
    for (const key of ['published', 'to_apply', 'other', 'unread']) {
      if (o.counts[key] === 0) continue;
      ui.click(`#j2ha_houseChips .j2ha-chip-filter[data-filter="${key}"]`);
      assert.equal(ui.$(`#j2ha_houseChips .j2ha-chip-filter[data-filter="${key}"]`).attr('aria-pressed'), 'true');
      assert.equal(ui.$(`#j2ha_houseChips .j2ha-chip-filter[data-filter="${key}"]`).attr('aria-controls'), 'j2ha_roomCards');
      o.rooms.forEach((room) => {
        const card = ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${room.object_id}"]`);
        assert.equal(card.prop('hidden'), room.counts[key] === 0, `${key} / pièce ${room.object_id}`);
        if (room.counts[key] > 0) assert.equal(plain(card.find('.j2ha-room-ratio').text()), `${room.counts[key]}/${room.summary.equipments_total}`);
      });
      const shown = ui.$('#j2ha_roomCards .j2ha-room-card').list.filter((c) => !c.props.hidden)
        .reduce((n, c) => n + Number(plain(ui.$(c).find('.j2ha-room-ratio').text()).split('/')[0]), 0);
      assert.equal(shown, o.counts[key], 'la somme des tuiles visibles égale la puce');
      ui.click(`#j2ha_houseChips .j2ha-chip-filter[data-filter="${key}"]`);
      assert.equal(ui.page.filter(), null, 'second clic = filtre retiré');
      assert.equal(ui.$('#j2ha_roomCards .j2ha-room-card').list.filter((c) => c.props.hidden).length, 0);
    }
    assert.equal(ui.calls.length, before, 'aucune requête réseau');
  });

  maybe('« Bloqués » montre la liste « À faire » (bloqués seulement, tous) et masque la grille ; second clic : retour', () => {
    const ui = startPage();
    const o = ui.page.view().overview;
    assert.ok(o.counts.blocked > 0);
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="blocked"]');
    assert.equal(ui.$('#j2ha_houseChips .j2ha-chip-filter[data-filter="blocked"]').attr('aria-controls'), 'j2ha_v2_todo');
    assert.equal(ui.$('#j2ha_roomCards').prop('hidden'), true);
    const rows = ui.$('#j2ha_v2_todo .j2ha-v2-todo-row').list;
    assert.equal(rows.length, o.counts.blocked);
    rows.forEach((r) => assert.equal(r.attrs['data-kind'], 'blocked'));
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="blocked"]');
    assert.equal(ui.$('#j2ha_roomCards').prop('hidden'), false);
  });

  maybe('un filtre de grille masque la liste « À faire » et les titres de groupe vides', () => {
    const ui = startPage();
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="unread"]');
    assert.equal(ui.$('#j2ha_v2_todo').children().length, 0);
    const groups = ui.$('#j2ha_roomCards .j2ha-room-group').list;
    groups.forEach((g) => {
      const visible = ui.$(g).find('.j2ha-room-card').list.filter((c) => !c.props.hidden).length;
      assert.equal(!!g.props.hidden, visible === 0);
    });
  });

  maybe('un segment du liseré et la puce partagent le même gestionnaire', () => {
    const ui = startPage();
    ui.click('#j2ha_houseGauge .j2ha-seg[data-filter="published"]');
    assert.equal(ui.page.filter(), 'published');
    assert.equal(ui.$('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]').attr('aria-pressed'), 'true');
  });

  maybe('Échap sur une puce retire le filtre', () => {
    const ui = startPage();
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]');
    assert.ok(ui.page.filter());
    ui.key('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]', 'Escape');
    assert.equal(ui.page.filter(), null);
  });

  maybe('après une relecture, un filtre actif est réappliqué aux nouveaux chiffres', () => {
    const ui = startPage();
    ui.click('#j2ha_houseChips .j2ha-chip-filter[data-filter="published"]');
    const equipments = equipmentsFor(ui.rooms);
    Object.values(equipments).forEach((entry) => { entry.sync_status.published_in_ha = false; });
    ui.page.reader.trigger();
    ui.timers.splice(0).forEach((t) => t.fn());
    ui.answer(okBody(equipments));
    assert.equal(ui.page.filter(), 'published');
    const o = ui.page.view().overview;
    o.rooms.forEach((room) => {
      assert.equal(ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${room.object_id}"]`).prop('hidden'), room.counts.published === 0);
    });
  });
});

describe('25.3 / AC12 — cartes de pièce', () => {
  // Garde levée (front v3, Lot 1) : tuile 220 × 72 — ratio « n/t » (sans mot, détail en info-bulle), marques icône + nombre
  // (le mot est lu par les lecteurs d'écran), liseré de 4 px étiqueté (role="group", segments role="img").
  maybe('liseré, « n/t », marques non nulles seulement, classe « bloquée » si bloqué ; somme des tuiles = maison', () => {
    const ui = startPage();
    const o = ui.page.view().overview;
    const sum = (key) => o.rooms.reduce((n, r) => n + r.counts[key], 0);
    for (const key of ['published', 'to_apply', 'blocked', 'other', 'unread']) assert.equal(sum(key), o.counts[key], key);
    o.rooms.forEach((room) => {
      const card = ui.$(`#j2ha_roomCards .j2ha-room-card[data-object_id="${room.object_id}"]`);
      assert.equal(card.length, 1);
      const ratio = plain(card.find('.j2ha-room-ratio').text());
      assert.equal(ratio, `${room.counts.published}/${room.summary.equipments_total}`);
      assert.match(plain(card.find('.j2ha-v3-tile-ratio').attr('title')), new RegExp(`${room.counts.published} publiés? sur ${room.summary.equipments_total}$`));
      const gauge = card.find('.j2ha-gauge');
      assert.equal(gauge.length, 1);
      assert.equal(gauge.attr('role'), 'group');
      assert.equal(card.find('.j2ha-seg').list.reduce((n, el) => n + Number(/flex-grow:(\d+)/.exec(el.attrs.style)[1]), 0), room.summary.equipments_total);
      assert.equal(card.find('.j2ha-mark-blocked').length, room.counts.blocked > 0 ? 1 : 0);
      assert.equal(card.find('.j2ha-mark-to_apply').length, room.counts.to_apply > 0 ? 1 : 0);
      assert.equal(card.find('.j2ha-mark-unread').length, room.counts.unread > 0 ? 1 : 0);
      assert.equal(card.hasClass('j2ha-room-blocked'), room.counts.blocked > 0);
      assert.match(card.attr('aria-label'), new RegExp(room.object_name.replace(/[<>/]/g, '.').slice(0, 5)));
    });
    assert.equal(ui.$('#j2ha_roomCards .j2ha-mark-unread').text().replace(/\{\{|\}\}/g, ''), '1 non lu');
  });

  // Garde levée (front v3, Lot 1, cible §1) : le CSS du cœur impose `div[class*="DisplayCard"] { height:130px; overflow:hidden }`
  // et `div[class*="ListContainer"] > div.cursor { width:130px }` : la tuile ne porte plus `objectDisplayCard` et n'est dans
  // aucun `*ListContainer`. Le reste du contrat (cursor, j2ha-room-card, data-object_id, onclick, clavier) est conservé.
  maybe('contrat de la tuile : cursor, j2ha-room-card, data-object_id, onclick ; aucune classe *DisplayCard ni conteneur *ListContainer', () => {
    const { html } = renderPhp(SCENE);
    assert.doesNotMatch(mainPart(html), /DisplayCard|ListContainer/);
    const cards = [...html.matchAll(/<div class="cursor j2ha-room-card j2ha-v3-tile[^"]*"[^>]*>/g)].map((m) => m[0]);
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
    const groups = [...html.matchAll(/<div class="j2ha-room-group j2ha-v3-group">(?:<h4 class="j2ha-room-group-title j2ha-free-name">([^<]*)<\/h4>)?([\s\S]*?)<\/div><\/div>(?=<div class="j2ha-room-group j2ha-v3-group">|<\/div>)/g)]
      .map((m) => ({ title: m[1] || null, ids: [...m[2].matchAll(/data-object_id="(\d+)"/g)].map((x) => Number(x[1])) }));
    // Garde levée (front v3, Lot 1) : le titre de groupe ne garde que le nom du parent direct (plus de « Maison › »).
    assert.deepEqual(groups, [
      { title: null, ids: [5] },
      { title: 'Étage fictif', ids: [2, 3, 4] },
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
