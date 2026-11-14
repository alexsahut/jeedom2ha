'use strict';

// Front v2 — Lot 1 : démarrage guidé (E1), barre d'état (E0), « Vérifier l'installation… » (E7).
// Table de vérité des étapes (démon arrêté, broker en erreur, jamais relu, relu), affichage seul du guide, stockage
// local, publication sans confirmation, écran de fin, contrôles de E7 et branchement dans jeedom2ha.js.
// Données fictives seulement.

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const G = require('../../desktop/js/jeedom2ha_guide.js');
const { plain, phpAvailable } = require('./helpers/page_b_harness');
const { startGuide } = require('./helpers/guide_harness');
const { createUi } = require('./helpers/ui_harness');

const maybe = phpAvailable ? it : it.skip;
const states = (model) => model.steps.map((s) => s.state);

const UP = { daemon: true, broker: { state: 'connected', broker: 'broker.exemple.test:1883' }, derniere_operation_resultat: 'aucun' };
const STOPPED = { daemon: false };
const BROKER_DOWN = { daemon: true, broker: { state: 'disconnected' } };
const SYNCED = Object.assign({}, UP, {
  derniere_synchro_terminee: '2026-11-13T22:06:00+00:00',
  derniere_operation_resultat: { resultat: 'succes', intention: 'sync', message: 'Synchronisation terminée.' },
});
const NEVER = { kind: 'never_synced' };
// Ce que renvoie le démon après `_build_sync_failure_response` : date de fin renseignée, résultat « echec ».
const FAILED = Object.assign({}, UP, {
  derniere_synchro_terminee: '2026-11-13T22:06:00+00:00',
  derniere_operation_resultat: { resultat: 'echec', intention: 'sync', message: 'Synchronisation échouée — erreur inattendue.' },
});
const READ_OK = { kind: 'ok' };
const NEVER_BODY = { state: 'ok', result: { status: 'ok', payload: { available: false, reason: 'never_synced' } } };

describe('Lot 1 — computeSteps : table de vérité', () => {
  it('démon arrêté : étape 1 en erreur (cause), les trois autres en attente de l’étape 1', () => {
    const m = G.computeSteps(STOPPED, { kind: 'unavailable' }, {}, {});
    assert.deepEqual(states(m), ['error', 'blocked', 'blocked', 'blocked']);
    assert.equal(plain(m.steps[0].cause), 'Le démon est arrêté.');
    assert.deepEqual(m.steps.slice(1).map((s) => s.waitFor), [1, 1, 1]);
  });

  it('état du pont illisible (null) : étape 1 en erreur ; pas encore lu (undefined) : étape 1 en cours, sans cause', () => {
    assert.equal(G.computeSteps(null, null, {}, {}).steps[0].state, 'error');
    const m = G.computeSteps(undefined, null, {}, {});
    assert.equal(m.steps[0].state, 'current');
    assert.equal(m.steps[0].cause, '');
  });

  it('broker en erreur : étape 1 en erreur avec la cause MQTT ; connexion en cours : étape 1 en cours, avec une note', () => {
    const m = G.computeSteps(BROKER_DOWN, NEVER, {}, {});
    assert.deepEqual(states(m), ['error', 'blocked', 'blocked', 'blocked']);
    assert.equal(plain(m.steps[0].cause), 'Le broker MQTT ne répond pas.');
    const c = G.computeSteps({ daemon: true, broker: { state: 'connecting' } }, NEVER, {}, {});
    assert.equal(c.steps[0].state, 'current');
    assert.match(plain(c.steps[0].note), /Connexion au broker/);
  });

  it('jamais relu, démon et broker en marche, sans champ ha (repli) : étape 2 en cours, case manuelle', () => {
    const m = G.computeSteps(UP, NEVER, {}, {});
    assert.deepEqual(states(m), ['done', 'current', 'blocked', 'blocked']);
    assert.equal(m.steps[1].manual, true);
    assert.equal(m.steps[1].ha_known, false);
    assert.equal(m.steps[3].waitFor, 2);
  });

  it('jamais relu, Home Assistant vu par le démon : étape 2 cochée seule ; « Je l’ai vu » coche aussi', () => {
    const seen = Object.assign({}, UP, { ha: { birth_seen_at: '2026-11-13T20:04:00+00:00', discovery_prefix: 'homeassistant' } });
    assert.deepEqual(states(G.computeSteps(seen, NEVER, {}, {})), ['done', 'done', 'current', 'blocked']);
    assert.equal(G.computeSteps(seen, NEVER, {}, {}).steps[1].auto, true);
    const notSeen = Object.assign({}, UP, { ha: { birth_seen_at: null } });
    assert.deepEqual(states(G.computeSteps(notSeen, NEVER, {}, {})), ['done', 'current', 'blocked', 'blocked']);
    assert.equal(G.computeSteps(notSeen, NEVER, {}, {}).steps[1].ha_known, true);
    assert.deepEqual(states(G.computeSteps(notSeen, NEVER, {}, { haSeen: true })), ['done', 'done', 'current', 'blocked']);
  });

  it('jamais relu, choix fait : étape 4 active', () => {
    assert.deepEqual(states(G.computeSteps(UP, NEVER, {}, { haSeen: true, choice: true })), ['done', 'done', 'done', 'current']);
  });

  it('relu : étapes 3 et 4 faites ; une étape faite le reste même si une précédente ne l’est plus', () => {
    const m = G.computeSteps(SYNCED, READ_OK, {}, {});
    assert.deepEqual(states(m), ['done', 'current', 'done', 'done']);
    assert.equal(m.synced, true);
    const down = G.computeSteps(STOPPED, { kind: 'unavailable' }, {}, { published: true, haSeen: true });
    assert.deepEqual(states(down), ['error', 'done', 'done', 'done']);
    assert.equal(G.computeSteps(SYNCED, READ_OK, {}, { haSeen: true }).complete, true);
  });

  it('Jeedom vide : l’étape 4 le dit et ne propose pas de publier', () => {
    const m = G.computeSteps(UP, NEVER, { jeedom_equipments: 0 }, { haSeen: true, choice: true });
    assert.equal(m.steps[3].state, 'error');
    assert.match(plain(m.steps[3].cause), /aucun équipement à publier/);
  });
});

describe('Lot 1 — revue PR #391 : publication réussie, installation connue', () => {
  it('première relecture « boot » en échec, rien publié : le guide s’affiche, même si la lecture des états répond', () => {
    assert.equal(G.shouldShow(FAILED, NEVER, {}), true);
    assert.equal(G.shouldShow(FAILED, READ_OK, {}, { read: true, published: 0 }), true);
    assert.equal(G.shouldShow(FAILED, READ_OK, { known: true }), false, 'installation connue : jamais');
  });

  it('relecture terminée en échec : pas de publication réussie, étape 4 en erreur avec « Réessayer »', () => {
    assert.equal(G.publishedOk(FAILED, null, {}), false);
    assert.equal(G.publishFailed(FAILED), true);
    const m = G.computeSteps(FAILED, NEVER, {}, { haSeen: true, choice: true });
    assert.deepEqual(states(m), ['done', 'done', 'done', 'error']);
    assert.equal(m.steps[3].retry, true);
  });

  // Forme réelle du Lot 3 (resources/daemon/models/ha_side.py) : publication.{equipments,entities,scenarios}_published,
  // comptés sur la mémoire vive du démon (0 juste après un redémarrage).
  it('status.publication (Lot 3) : > 0 prouve la publication ; 0 seul ne prouve rien (les autres preuves décident)', () => {
    const zero = { publication: { equipments_published: 0, entities_published: 0, scenarios_published: 0 } };
    assert.equal(G.publishedOk(Object.assign({}, FAILED, zero), null, {}), false, 'échec MQTT total : 0 et « echec »');
    assert.equal(G.publishedOk(Object.assign({}, UP, zero), null, {}), false);
    assert.equal(G.publishedOk(Object.assign({}, UP, zero), null, { published: true }), true, 'démon redémarré : mémoire du navigateur');
    assert.equal(G.publishedOk(Object.assign({}, SYNCED, zero), null, {}), true, 'relecture réussie, rien d’éligible');
    // Relais PHP getBridgeStatus, démon injoignable : ha et publication à null → item masqué, aucun compteur.
    const relayDown = { daemon: false, broker: { state: 'unknown' }, derniere_synchro_terminee: null, ha: null, publication: null, derniere_operation_resultat: 'aucun' };
    assert.equal(G.haBarItem(relayDown).visible, false);
    assert.equal(G.publicationInfo(relayDown), null);
    assert.equal(G.haInfo(relayDown), null);
    const relayUp = Object.assign({}, UP, { ha: { birth_seen_at: null, discovery_prefix: 'homeassistant' }, publication: { equipments_published: 29, entities_published: 41, scenarios_published: 12 } });
    assert.equal(plain(G.haBarItem(relayUp).text), 'Pas encore vu');
    assert.deepEqual(G.publicationInfo(relayUp), { equipments: 29, entities: 41, scenarios: 12 });
    assert.equal(G.publishedOk(relayUp, null, {}), true);
    const some = Object.assign({}, FAILED, { publication: { equipments_published: 12 } });
    assert.equal(G.publishedOk(some, null, {}), true);
    assert.equal(G.publishedOk(UP, { read: true, published: 1 }, {}), true, 'lecture des états avec un publié');
    assert.equal(G.publishedOk(UP, { read: true, published: 0 }, {}), false);
    assert.equal(G.publishedOk(SYNCED, null, {}), true, 'résultat « succes » sans le champ du Lot 3');
  });

  it('installation connue : jamais de guide sur une panne, ni sur une lecture « jamais relu » après une relecture', () => {
    assert.equal(G.shouldShow(STOPPED, { kind: 'unavailable' }, { known: true }), false);
    assert.equal(G.shouldShow(UP, NEVER, { known: true }), false);
    // Revue ClaudeBox : « connue » = preuve de SUCCÈS, jamais une simple tentative.
    assert.equal(G.knownInstall(FAILED, null, {}), false, 'relecture tentée mais en échec : pas connue');
    assert.equal(G.knownInstall(undefined, { read: true, published: 0 }, {}), false, 'lecture valide sans publié : pas connue');
    assert.equal(G.knownInstall(undefined, { read: true, published: 2 }, {}), true);
    assert.equal(G.knownInstall(SYNCED, null, {}), true, 'relecture réussie');
    assert.equal(G.knownInstall(Object.assign({}, UP, { publication: { equipments_published: 5 } }), null, {}), true);
    assert.equal(G.knownInstall(STOPPED, null, {}), false);
    assert.equal(G.shouldShow(SYNCED, READ_OK, {}, { read: true, published: 4 }), false);
  });
});

describe('Lot 1 — shouldShow', () => {
  it('jamais relu : affiché ; relu : jamais ; « Ne plus afficher » l’emporte', () => {
    assert.equal(G.shouldShow(UP, NEVER, {}), true);
    assert.equal(G.shouldShow(UP, READ_OK, {}), false);
    assert.equal(G.shouldShow(STOPPED, READ_OK, {}, { read: true, published: 3 }), false, 'lecture valide avec des publiés : connue');
    assert.equal(G.shouldShow(UP, NEVER, { dismissed: true }), false);
  });

  it('démon ou broker indisponible : affiché seulement si ce navigateur n’a jamais vu de publication', () => {
    assert.equal(G.shouldShow(STOPPED, { kind: 'unavailable' }, {}), true);
    assert.equal(G.shouldShow(BROKER_DOWN, { kind: 'unavailable' }, {}), true);
    assert.equal(G.shouldShow(null, { kind: 'unavailable' }, {}), true);
    assert.equal(G.shouldShow(STOPPED, { kind: 'unavailable' }, { published: true }), false);
    const succeeded = { derniere_synchro_terminee: '2026-11-13T10:00:00Z', derniere_operation_resultat: { resultat: 'succes', intention: 'sync' } };
    assert.equal(G.shouldShow(Object.assign({}, BROKER_DOWN, succeeded), { kind: 'unavailable' }, {}), false, 'relecture réussie : connue');
    // Une date de fin seule (tentative) ne prouve rien : le démon la pose aussi quand la publication échoue.
    assert.equal(G.shouldShow(Object.assign({}, BROKER_DOWN, { derniere_synchro_terminee: '2026-11-13T10:00:00Z' }), { kind: 'unavailable' }, {}), true);
  });

  it('rien avant la première lecture des états (pas d’éclair au chargement)', () => {
    assert.equal(G.shouldShow(STOPPED, null, {}), false);
    assert.equal(G.shouldShow(undefined, { kind: 'unavailable' }, {}), false);
  });
});

describe('Lot 1 — barre d’état : item Home Assistant et « Dernière relecture »', () => {
  it('item Home Assistant masqué sans le champ (repli Lot 3) ou démon arrêté ; « Vu le … à … » / « Pas encore vu »', () => {
    assert.equal(G.haBarItem(UP).visible, false);
    assert.equal(G.haBarItem({ daemon: false, ha: { birth_seen_at: null } }).visible, false);
    const notSeen = G.haBarItem(Object.assign({}, UP, { ha: { birth_seen_at: null } }));
    assert.deepEqual([notSeen.visible, notSeen.seen, plain(notSeen.text)], [true, false, 'Pas encore vu']);
    const seen = G.haBarItem(Object.assign({}, UP, { ha: { birth_seen_at: '2026-11-13T21:04:00' } }));
    assert.equal(seen.seen, true);
    assert.equal(plain(seen.text), 'Vu le 13/11 à 21:04');
  });

  it('fusion : date courte + résultat quand la dernière opération est la relecture ; date seule sinon', () => {
    const date = '2026-11-13T23:06:00';
    const f = G.relectureFusion({ derniere_synchro_terminee: date, derniere_operation_resultat: { resultat: 'partiel', intention: 'sync' } });
    assert.deepEqual([plain(f.text), f.fused], ['13/11 23:06 · Partielle', true]);
    const other = G.relectureFusion({ derniere_synchro_terminee: date, derniere_operation_resultat: { resultat: 'succes', intention: 'publier' } });
    assert.deepEqual([other.text, other.fused], ['13/11 23:06', false]);
    assert.deepEqual(G.relectureFusion({ derniere_operation_resultat: 'aucun' }), { text: '', fused: false });
  });
});

describe('Lot 1 — checkInstall (E7)', () => {
  const titles = (list) => list.map((c) => [c.key, c.state]);

  it('démon arrêté : premier contrôle en échec avec remède, les suivants en attente', () => {
    const list = G.checkInstall(STOPPED, null, {});
    assert.deepEqual(titles(list), [['daemon', 'fail'], ['broker', 'wait'], ['reread', 'wait']]);
    assert.equal(list[0].open, true);
    assert.equal(list[0].remedy.action, 'config');
  });

  it('broker déconnecté : s’arrête au broker ; jamais relu : s’arrête à la relecture (remède « Relire Jeedom »)', () => {
    assert.deepEqual(titles(G.checkInstall(BROKER_DOWN, null, {})), [['daemon', 'ok'], ['broker', 'fail'], ['reread', 'wait']]);
    const never = G.checkInstall(UP, NEVER, {});
    assert.deepEqual(titles(never), [['daemon', 'ok'], ['broker', 'ok'], ['reread', 'fail']]);
    assert.equal(never[2].remedy.action, 'rescan');
    assert.match(plain(never[1].detail), /broker\.exemple\.test/);
  });

  it('Home Assistant pas encore vu : à vérifier (n’arrête pas) avec trois causes ; relecture partielle : « Voir lesquels »', () => {
    const status = Object.assign({}, SYNCED, { ha: { birth_seen_at: null }, derniere_operation_resultat: { resultat: 'partiel', intention: 'sync' } });
    const list = G.checkInstall(status, READ_OK, { read: true, blocked: 0 });
    assert.deepEqual(titles(list), [['daemon', 'ok'], ['broker', 'ok'], ['ha', 'warn'], ['reread', 'fail'], ['blocked', 'wait']]);
    assert.equal(list[2].help, true);
    assert.equal(list[3].remedy.action, 'blocked');
  });

  it('tout va bien : tous OK ; des bloqués : à vérifier avec le lien vers le filtre', () => {
    const status = Object.assign({}, SYNCED, { ha: { birth_seen_at: '2026-11-13T20:04:00' } });
    assert.ok(G.checkInstall(status, READ_OK, { read: true, blocked: 0 }).every((c) => c.state === 'ok'));
    const list = G.checkInstall(status, READ_OK, { read: true, blocked: 4 });
    assert.equal(plain(list[4].title), '4 équipements bloqués');
    assert.equal(list[4].remedy.action, 'blocked');
  });
});

describe('Lot 1 — le guide sur la page rendue (squelette PHP réel, overview réel, faux DOM)', () => {
  maybe('installation configurée : aucun guide, la vue principale reste affichée', () => {
    const ui = startGuide();
    ui.guide.onStatus(SYNCED);
    assert.equal(ui.$('#j2ha_v2_guide').children().length, 0);
    assert.notEqual(ui.$('#j2ha_mainView').list[0].visible, false);
  });

  maybe('jamais relu : « Bienvenue dans jeedom2ha », vue principale masquée (non détruite), étape 1 en cours si le démon est arrêté', () => {
    const ui = startGuide({ page: { answer: false } });
    ui.guide.onStatus(STOPPED);
    ui.answer(NEVER_BODY);
    assert.match(ui.text('#j2ha_v2_guide'), /Bienvenue dans jeedom2ha/);
    assert.equal(ui.$('#j2ha_mainView').list[0].visible, false);
    assert.equal(ui.$('#j2ha_roomCards').length, 1, 'non détruite');
    const steps = ui.$('#j2ha_v2_guide .j2ha-v2-step').list;
    assert.equal(steps.length, 4);
    assert.ok(steps[0].classes.has('is-blocked'));
    assert.ok(steps.slice(1).every((s) => s.classes.has('is-wait')));
    assert.match(ui.text('#j2ha_v2_guide'), /Terminez l'étape 1 d'abord/);
    ui.click('#j2ha_v2_guide .j2ha-v2-btn-primary');
    assert.deepEqual(ui.actions.calls, ['config']);
  });

  maybe('parcours complet : « Je l’ai vu », « Tout publier », puis publier SANS confirmation et écran de fin chiffré', () => {
    const ui = startGuide({ page: { answer: false } });
    ui.guide.onStatus(UP);
    ui.answer(NEVER_BODY);
    ui.click('#j2ha_v2_guide .j2ha-v2-guide-hahelp');
    assert.equal(ui.$('#j2ha_v2_guide .j2ha-v2-guide-causes li').length, 3, '« Je ne le vois pas » : trois causes');
    ui.click('#j2ha_v2_guide .j2ha-v2-guide-haseen');
    assert.equal(ui.storage.data[G.STORAGE_KEYS.haSeen], '1');
    ui.click('#j2ha_v2_guide .j2ha-v2-guide-all');
    assert.equal(ui.$('#j2ha_v2_guide .j2ha-v2-guide-publish').prop('disabled'), false);
    const dialogs = ui.dom.dialogs.length;
    ui.click('#j2ha_v2_guide .j2ha-v2-guide-publish');
    assert.deepEqual(ui.actions.calls, ['publish']);
    assert.equal(ui.dom.dialogs.length, dialogs, 'aucune confirmation');
    assert.equal(ui.$('#j2ha_v2_guide .j2ha-v2-guide-publish').prop('disabled'), true, 'pas de second envoi');
    ui.finishPublish(false);
    assert.equal(ui.storage.data[G.STORAGE_KEYS.known], undefined, '« connue » attend une preuve de succès');
    assert.equal(ui.storage.data[G.STORAGE_KEYS.published], undefined, 'publication réussie : attestée par l’état réel, pas par la fin de la relecture');
    assert.match(ui.text('#j2ha_v2_guide'), /C'est fait : vos équipements sont dans Home Assistant\./);
    // Relecture des états après la publication : le nombre et trois noms publiés apparaissent.
    ui.page.reader.load();
    ui.answer(require('./helpers/page_b_harness').okBody(require('./helpers/page_b_harness').equipmentsFor(ui.rooms)));
    const view = ui.page.view().overview;
    assert.equal(ui.storage.data[G.STORAGE_KEYS.published], view.counts.published > 0 ? '1' : undefined);
    assert.equal(ui.storage.data[G.STORAGE_KEYS.known], view.counts.published > 0 ? '1' : undefined);
    const text = ui.text('#j2ha_v2_guide');
    assert.match(text, new RegExp(`C'est fait : ${view.counts.published} équipements sont dans Home Assistant\\.`));
    assert.match(text, /Paramètres › Appareils et services › MQTT/);
    assert.match(text, /Par exemple : « [^»]+ », « [^»]+ », « [^»]+ »\./);
    if (view.counts.blocked > 0) {
      ui.click('#j2ha_v2_guide .j2ha-v2-guide-blocked');
      assert.equal(ui.actions.calls[ui.actions.calls.length - 1], 'filter:blocked');
    } else {
      ui.click('#j2ha_v2_guide .j2ha-v2-guide-home');
    }
    assert.equal(ui.$('#j2ha_v2_guide').children().length, 0);
    assert.notEqual(ui.$('#j2ha_mainView').list[0].visible, false, 'la maison réapparaît');
  });

  maybe('publication en échec ou refusée (opération en cours) : le guide reste sur l’étape 4 et le dit', () => {
    const ui = startGuide({ page: { answer: false }, storage: { [G.STORAGE_KEYS.haSeen]: '1', [G.STORAGE_KEYS.choice]: '1' } });
    ui.guide.onStatus(UP);
    ui.answer(NEVER_BODY);
    ui.click('#j2ha_v2_guide .j2ha-v2-guide-publish');
    ui.finishPublish(true);
    assert.equal(ui.guide.state().phase, 'steps');
    assert.match(ui.text('#j2ha_v2_guide'), /La publication n'a pas abouti/);
    const busy = startGuide({ page: { answer: false }, publishBusy: true, storage: { [G.STORAGE_KEYS.haSeen]: '1', [G.STORAGE_KEYS.choice]: '1' } });
    busy.guide.onStatus(UP);
    busy.answer(NEVER_BODY);
    busy.click('#j2ha_v2_guide .j2ha-v2-guide-publish');
    assert.match(busy.text('#j2ha_v2_guide'), /Une opération est déjà en cours/);
  });

  maybe('« Ne plus afficher » est retenu ; le menu « Guide de démarrage » rouvre quand même ; stockage refusé : aucune erreur', () => {
    const ui = startGuide({ page: { answer: false } });
    ui.guide.onStatus(UP);
    ui.answer(NEVER_BODY);
    ui.click('#j2ha_v2_guide .j2ha-v2-guide-dismiss');
    assert.equal(ui.storage.data[G.STORAGE_KEYS.dismissed], '1');
    assert.equal(ui.$('#j2ha_v2_guide').children().length, 0);
    ui.guide.onStatus(UP);
    assert.equal(ui.$('#j2ha_v2_guide').children().length, 0, 'ne revient pas seul');
    ui.guide.open();
    assert.match(ui.text('#j2ha_v2_guide'), /Bienvenue dans jeedom2ha/);
    ui.click('#j2ha_v2_guide .j2ha-v2-guide-close');
    assert.equal(ui.$('#j2ha_v2_guide').children().length, 0);

  });

  // Revue PR #391 (point 3) : stockage refusé = préférences gardées en mémoire, le guide avance quand même.
  maybe('stockage local refusé : « Je l’ai vu » et « Tout publier » font avancer le guide jusqu’à l’étape 4', () => {
    const broken = startGuide({ page: { answer: false }, brokenStorage: true });
    broken.guide.onStatus(UP);
    broken.answer(NEVER_BODY);
    broken.click('#j2ha_v2_guide .j2ha-v2-guide-haseen');
    assert.ok(broken.$('#j2ha_v2_guide .j2ha-v2-step[data-step="ha"]').hasClass('is-done'));
    broken.click('#j2ha_v2_guide .j2ha-v2-guide-all');
    assert.ok(broken.$('#j2ha_v2_guide .j2ha-v2-step[data-step="choice"]').hasClass('is-done'));
    assert.ok(broken.$('#j2ha_v2_guide .j2ha-v2-step[data-step="publish"]').hasClass('is-current'));
    assert.equal(broken.$('#j2ha_v2_guide .j2ha-v2-guide-publish').prop('disabled'), false);
    broken.click('#j2ha_v2_guide .j2ha-v2-guide-dismiss');
    broken.guide.onStatus(UP);
    assert.equal(broken.$('#j2ha_v2_guide').children().length, 0, '« Ne plus afficher » tenu pour la page');
  });

  // Revue ClaudeBox de f6396c6 : la relecture « boot » du premier démarrage échoue, rien n'est publié.
  maybe('première relecture « boot » échouée, rien publié : guide affiché au chargement, étape 4 en erreur avec « Réessayer »', () => {
    const ui = startGuide({ page: { answer: false }, storage: { [G.STORAGE_KEYS.haSeen]: '1', [G.STORAGE_KEYS.choice]: '1' } });
    ui.guide.onStatus(FAILED);
    ui.answer(NEVER_BODY);
    assert.match(ui.text('#j2ha_v2_guide'), /Bienvenue dans jeedom2ha/);
    assert.equal(ui.$('#j2ha_mainView').list[0].visible, false);
    const step = ui.$('#j2ha_v2_guide .j2ha-v2-step[data-step="publish"]');
    assert.ok(step.hasClass('is-blocked'), 'étape 4 en erreur');
    assert.match(plain(step.text()), /La dernière publication a échoué/);
    assert.equal(plain(ui.$('#j2ha_v2_guide .j2ha-v2-guide-publish').text()), 'Réessayer de publier');
    assert.equal(ui.storage.data[G.STORAGE_KEYS.known], undefined);
    // Le démon répond aussi à la lecture des états, sans aucun équipement publié : le guide reste.
    const ok = startGuide({ page: { answer: false } });
    ok.guide.onStatus(FAILED);
    ok.answer({ state: 'ok', result: { status: 'ok', payload: { schema_version: 1, available: true, meta: { action_in_progress: false }, equipments: {}, unread: [] } } });
    assert.match(ok.text('#j2ha_v2_guide'), /Bienvenue dans jeedom2ha/);
  });

  // Revue PR #391 (point 1) : une panne d'une installation connue n'affiche jamais le guide plein écran.
  maybe('installation connue sans passage par le guide : une panne du démon n’affiche pas le guide, ni maintenant ni au rechargement', () => {
    const ui = startGuide();
    ui.guide.onStatus(SYNCED);
    assert.equal(ui.storage.data[G.STORAGE_KEYS.known], '1');
    ui.guide.onStatus(STOPPED);
    ui.guide.onSnapshot({ kind: 'unavailable', view: null });
    assert.equal(ui.$('#j2ha_v2_guide').children().length, 0);
    assert.notEqual(ui.$('#j2ha_mainView').list[0].visible, false, 'la maison reste affichée');
    const reload = startGuide({ page: { answer: false }, storage: Object.assign({}, ui.storage.data) });
    reload.guide.onStatus(STOPPED);
    reload.answer({ state: 'ok', result: 'démon injoignable' });
    assert.equal(reload.$('#j2ha_v2_guide').children().length, 0);
    const fresh = startGuide({ page: { answer: false } });
    fresh.guide.onStatus(STOPPED);
    fresh.answer({ state: 'ok', result: 'démon injoignable' });
    assert.match(fresh.text('#j2ha_v2_guide'), /Bienvenue/, 'premier lancement : le guide s’affiche');
  });

  // Revue PR #391 (point 2) : relecture terminée ≠ publication réussie.
  maybe('relecture terminée en échec (échec MQTT total) : l’étape 4 reste ouverte, avec la cause et « Réessayer de publier »', () => {
    const ui = startGuide({ page: { answer: false }, storage: { [G.STORAGE_KEYS.haSeen]: '1', [G.STORAGE_KEYS.choice]: '1' } });
    ui.guide.onStatus(UP);
    ui.answer(NEVER_BODY);
    ui.click('#j2ha_v2_guide .j2ha-v2-guide-publish');
    ui.finishPublish(false); // la relecture a « abouti » côté client…
    ui.guide.onStatus(FAILED); // …mais le démon dit « echec » (date de fin renseignée quand même)
    assert.equal(ui.guide.state().phase, 'steps', 'pas d’écran « C’est fait » sur un échec');
    assert.equal(ui.guide.state().visible, true, 'le guide reste affiché');
    const step = ui.$('#j2ha_v2_guide .j2ha-v2-step[data-step="publish"]');
    assert.ok(step.hasClass('is-blocked'), 'étape 4 en erreur');
    assert.match(plain(step.text()), /La dernière publication a échoué/);
    assert.equal(plain(ui.$('#j2ha_v2_guide .j2ha-v2-guide-publish').text()), 'Réessayer de publier');
    assert.equal(ui.$('#j2ha_v2_guide .j2ha-v2-guide-publish').prop('disabled'), false);
    assert.equal(ui.storage.data[G.STORAGE_KEYS.published], undefined);
    // Chemin courant : la relecture revient en échec côté client, puis la barre relit le démon.
    const direct = startGuide({ page: { answer: false }, storage: { [G.STORAGE_KEYS.haSeen]: '1', [G.STORAGE_KEYS.choice]: '1' } });
    direct.guide.onStatus(UP);
    direct.answer(NEVER_BODY);
    direct.click('#j2ha_v2_guide .j2ha-v2-guide-publish');
    direct.finishPublish(true);
    direct.guide.onStatus(FAILED);
    assert.equal(direct.guide.state().visible, true);
    assert.equal(plain(direct.$('#j2ha_v2_guide .j2ha-v2-guide-publish').text()), 'Réessayer de publier');
  });

  maybe('une vue de travail ouverte par l’adresse n’est jamais recouverte par le guide', () => {
    const ui = startGuide({ page: { answer: false }, canAutoShow: false });
    ui.guide.onStatus(UP);
    ui.answer(NEVER_BODY);
    assert.equal(ui.$('#j2ha_v2_guide').children().length, 0);
  });

  maybe('« Vérifier l’installation… » : s’arrête au premier échec, remède cliquable (ferme la boîte), exports déplacés puis rendus', () => {
    const ui = startGuide();
    ui.guide.onStatus(BROKER_DOWN);
    const res = ui.guide.openCheck();
    assert.deepEqual(res.checks.map((c) => [c.key, c.state]), [['daemon', 'ok'], ['broker', 'fail'], ['reread', 'wait'], ['blocked', 'wait']]);
    const modal = ui.$(ui.dom.dialogs[0].modal);
    assert.equal(modal.find('.j2ha-v2-check').length, 4);
    assert.equal(modal.find('#bt_exportDiagnostic').length, 1);
    assert.equal(modal.find('#cb_pseudonymize').length, 1);
    assert.equal(modal.find('.j2ha-v2-check-advanced-body #bt_exportDecision').length, 1);
    assert.equal(modal.find('.j2ha-v2-check-logs li').length, 3);
    const toggle = modal.find('.j2ha-v2-check-advanced');
    assert.equal(toggle.attr('aria-expanded'), 'false');
    toggle.list[0].handlers.click.call(toggle.list[0], {});
    assert.equal(toggle.attr('aria-expanded'), 'true');
    const remedy = modal.find('.j2ha-v2-check-remedy');
    assert.equal(remedy.length, 1, 'un seul remède : celui du premier échec');
    remedy.list[0].handlers.click.call(remedy.list[0], { preventDefault() {} });
    assert.deepEqual(ui.actions.calls, ['config']);
    assert.equal(ui.$('#div_diagnosticDialog #bt_exportDiagnostic').length, 1, 'contenu rendu à sa place');
    assert.equal(ui.$('#div_decisionExportDialog #bt_exportDecision').length, 1);
  });
});

describe('Lot 1 — jeedom2ha.js : barre d’état, relecture, guide branché', () => {
  const src = fs.readFileSync('desktop/js/jeedom2ha.js', 'utf8');

  function bar() {
    const ui = createUi([]);
    ui.sandbox.Jeedom2haGuide = G;
    ui.dom.add('<div class="j2ha-health-item"><strong>Dernière relecture</strong><span id="span_healthSync"></span></div>');
    ui.dom.add('<div class="j2ha-health-item" id="div_op"><strong>Dernière opération</strong><span id="span_healthOp"></span><span id="span_healthOpMsg"></span></div>');
    ui.dom.add('<div id="div_healthHa" class="j2ha-health-item" style="display:none;"><strong>Home Assistant</strong><span id="span_healthHa"></span></div>');
    return ui;
  }

  it('relecture fusionnée : « 13/11 23:06 · Réussie », « Dernière opération » masquée ; item Home Assistant affiché', () => {
    const ui = bar();
    ui.sandbox.refreshBridgeStatus();
    ui.respond('getBridgeStatus', { state: 'ok', result: Object.assign({}, SYNCED, { derniere_synchro_terminee: '2026-11-13T23:06:00', ha: { birth_seen_at: '2026-11-13T21:04:00' } }) });
    assert.equal(plain(ui.$('#span_healthSync').text()), '13/11 23:06 · Réussie');
    assert.equal(ui.$('#div_op').list[0].visible, false);
    assert.equal(plain(ui.$('#span_healthOpMsg').text()), 'Relecture terminée.');
    assert.equal(ui.$('#div_healthHa').list[0].visible, true);
    assert.equal(plain(ui.$('#span_healthHa').text()), 'Vu le 13/11 à 21:04');
    assert.ok(ui.$('#span_healthHa').hasClass('label-success'));
    assert.equal(ui.sandbox.window.jeedom2haBridgeInflight, false, 'lecture terminée');
  });

  it('sans champ ha (démon avant Lot 3) : item masqué ; démon arrêté : item masqué, « Dernière opération » visible', () => {
    const ui = bar();
    ui.sandbox.refreshBridgeStatus();
    ui.respond('getBridgeStatus', { state: 'ok', result: Object.assign({}, UP, { derniere_operation_resultat: { resultat: 'succes', intention: 'publier', message: 'ok' } }) });
    assert.equal(ui.$('#div_healthHa').list[0].visible, false);
    assert.notEqual(ui.$('#div_op').list[0].visible, false);
    ui.sandbox.refreshBridgeStatus();
    ui.respond('getBridgeStatus', { state: 'ok', result: { daemon: false, ha: { birth_seen_at: null } } });
    assert.equal(ui.$('#div_healthHa').list[0].visible, false);
    assert.equal(ui.$('#div_op').list[0].visible, true);
  });

  it('le guide reçoit chaque état du pont (et null en erreur)', () => {
    const ui = bar();
    const seen = [];
    ui.sandbox.window.Jeedom2haGuideInstance = { onStatus: (r) => seen.push(r) };
    ui.sandbox.refreshBridgeStatus();
    ui.respond('getBridgeStatus', { state: 'ok', result: UP });
    ui.sandbox.refreshBridgeStatus();
    ui.fail('getBridgeStatus');
    assert.deepEqual(seen.map((r) => r && r.daemon), [true, null]);
  });

  it('publication du guide : même chemin que « Relire Jeedom » (réservation, scanTopology), sans confirmation', () => {
    const ui = bar();
    const done = [];
    const dialogs = ui.dom.dialogs.length;
    assert.equal(ui.sandbox.publishFromGuide((failed) => done.push(failed)), true);
    assert.equal(ui.dom.dialogs.length, dialogs, 'aucune confirmation');
    assert.equal(ui.sandbox.window.jeedom2haRescanInProgress, true);
    assert.equal(ui.sandbox.publishFromGuide(() => {}), false, 'une opération à la fois');
    ui.respond('scanTopology', { state: 'ok', result: { status: 'ok', operation_result: 'succes', operation_message: 'Synchronisation terminée.' } });
    assert.deepEqual(done, [false]);
    assert.equal(ui.sandbox.window.jeedom2haRescanInProgress, false);
    assert.ok(ui.dom.alerts.some((a) => plain(a.message) === 'Relecture terminée.'));
  });

  it('source : rafraîchissement toutes les 30 s, onglet visible, arrêt quand la page n’est plus là ; menu branché', () => {
    assert.match(src, /var J2HA_BRIDGE_REFRESH_MS = 30000;/);
    assert.match(src, /document\.visibilityState === 'hidden'\) return;/);
    assert.match(src, /if \(\$\('#span_healthBridge'\)\.length === 0\) \{\s*window\.clearInterval/);
    assert.match(src, /\$\('#bt_j2haOpenGuide'\)\.on\('click'/);
    assert.match(src, /\$\('#bt_j2haCheckInstall'\)\.on\('click'/);
    assert.match(src, /refreshBridgeStatus\(\);\s*startBridgeStatusAutoRefresh\(\);\s*setupGuide\(\);/);
  });

  it('libellés {{…}} sur une seule ligne dans le guide ; aucun JSON.stringify ni source unique recopiée', () => {
    const guide = fs.readFileSync('desktop/js/jeedom2ha_guide.js', 'utf8');
    for (const line of guide.split('\n')) {
      assert.equal((line.match(/\{\{/g) || []).length, (line.match(/\}\}/g) || []).length, line);
    }
    assert.doesNotMatch(guide, /JSON\.stringify|COMMAND_CAUSE_CATEGORIES|categoryOfCause|resolveEquipmentState/);
  });
});
