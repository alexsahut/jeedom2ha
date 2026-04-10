// ARTEFACT — Story 5.4 : tests JS — readOperationSnapshot (normalisation) + couverture comportementale badge/message bandeau.
'use strict';

const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const Jeedom2haScopeSummary = require('../../desktop/js/jeedom2ha_scope_summary.js');

const { readOperationSnapshot } = Jeedom2haScopeSummary;

// ---------------------------------------------------------------------------
// Export vérification
// ---------------------------------------------------------------------------

describe('5.4 — readOperationSnapshot : export', () => {
  it('readOperationSnapshot est bien exporté (non null, fonction)', () => {
    assert.ok(typeof readOperationSnapshot === 'function');
  });
});

// ---------------------------------------------------------------------------
// AC 6 — Normalisation : cas null / undefined / string / objet invalide
// ---------------------------------------------------------------------------

describe('5.4 / AC6 — readOperationSnapshot : normalisation null / undefined', () => {
  it('readOperationSnapshot(null) → resultat="aucun", autres champs null', () => {
    const r = readOperationSnapshot(null);
    assert.strictEqual(r.resultat, 'aucun');
    assert.strictEqual(r.intention, null);
    assert.strictEqual(r.portee, null);
    assert.strictEqual(r.message, null);
    assert.strictEqual(r.volume, null);
    assert.strictEqual(r.timestamp, null);
  });

  it('readOperationSnapshot(undefined) → même résultat que null', () => {
    const r = readOperationSnapshot(undefined);
    assert.strictEqual(r.resultat, 'aucun');
    assert.strictEqual(r.intention, null);
    assert.strictEqual(r.message, null);
  });
});

describe('5.4 / AC6 — readOperationSnapshot : normalisation string legacy', () => {
  it('readOperationSnapshot("succes") → resultat="succes", autres null', () => {
    const r = readOperationSnapshot('succes');
    assert.strictEqual(r.resultat, 'succes');
    assert.strictEqual(r.intention, null);
    assert.strictEqual(r.message, null);
    assert.strictEqual(r.volume, null);
  });

  it('readOperationSnapshot("aucun") → resultat="aucun"', () => {
    assert.strictEqual(readOperationSnapshot('aucun').resultat, 'aucun');
  });

  it('readOperationSnapshot("invalide") → resultat="aucun" (string inconnue)', () => {
    assert.strictEqual(readOperationSnapshot('invalide').resultat, 'aucun');
  });
});

describe('5.4 / AC6 — readOperationSnapshot : objet enrichi valide', () => {
  it('objet complet → champs corrects', () => {
    const raw = {
      resultat: 'partiel',
      intention: 'publier',
      portee: 'piece',
      message: '5 équipements mis à jour, 2 n\'ont pas pu être traités.',
      volume: 5,
      timestamp: '2026-04-09T10:00:00+00:00',
    };
    const r = readOperationSnapshot(raw);
    assert.strictEqual(r.resultat, 'partiel');
    assert.strictEqual(r.intention, 'publier');
    assert.strictEqual(r.portee, 'piece');
    assert.strictEqual(r.message, '5 équipements mis à jour, 2 n\'ont pas pu être traités.');
    assert.strictEqual(r.volume, 5);
    assert.strictEqual(r.timestamp, '2026-04-09T10:00:00+00:00');
  });

  it('resultat invalide dans objet → resultat="aucun"', () => {
    const r = readOperationSnapshot({ resultat: 'invalide', intention: 'publier' });
    assert.strictEqual(r.resultat, 'aucun');
  });

  it('message vide string → message=null (normalisé)', () => {
    const r = readOperationSnapshot({ resultat: 'succes', message: '' });
    assert.strictEqual(r.message, null);
  });

  it('message null → message=null', () => {
    const r = readOperationSnapshot({ resultat: 'succes', message: null });
    assert.strictEqual(r.message, null);
  });
});

// ---------------------------------------------------------------------------
// AC 5 — Couverture rendu badge — données pilotant switch(_opObj.resultat)
// ---------------------------------------------------------------------------

describe('5.4 / AC5 — Rendu badge : données pilotant le switch resultat', () => {
  it('"succes" → resultat correct pour badge label-success', () => {
    const r = readOperationSnapshot({ resultat: 'succes', message: '12 équipements mis à jour.' });
    assert.strictEqual(r.resultat, 'succes');
  });

  it('"partiel" → resultat correct pour badge label-warning orange', () => {
    const r = readOperationSnapshot({ resultat: 'partiel', message: '3 mis à jour, 2 non traités.' });
    assert.strictEqual(r.resultat, 'partiel');
  });

  it('"echec" → resultat correct pour badge label-warning orange', () => {
    const r = readOperationSnapshot({ resultat: 'echec', message: 'Synchronisation échouée.' });
    assert.strictEqual(r.resultat, 'echec');
  });

  it('"aucun" → resultat correct pour badge label-default', () => {
    const r = readOperationSnapshot({ resultat: 'aucun' });
    assert.strictEqual(r.resultat, 'aucun');
  });
});

// ---------------------------------------------------------------------------
// AC 5 — Couverture rendu message — données pilotant $opMsg.text(_opObj.message || '')
// ---------------------------------------------------------------------------

describe('5.4 / AC5 — Rendu message : données pilotant $opMsg.text()', () => {
  it('message non vide → retourné tel quel pour $opMsg.text(...)', () => {
    const r = readOperationSnapshot({ resultat: 'succes', message: '12 équipements mis à jour.' });
    assert.strictEqual(r.message, '12 équipements mis à jour.');
  });

  it('message null → null → $opMsg.text("") via || ""', () => {
    const r = readOperationSnapshot({ resultat: 'succes', message: null });
    assert.strictEqual(r.message, null);
    // Simulation comportement JS : _opObj.message || '' → ''
    assert.strictEqual(r.message || '', '');
  });

  it('message string vide → normalisé null → $opMsg.text("")', () => {
    const r = readOperationSnapshot({ resultat: 'succes', message: '' });
    assert.strictEqual(r.message, null);
    assert.strictEqual(r.message || '', '');
  });
});
