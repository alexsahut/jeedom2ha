// ARTEFACT — Story 25.9 (AC8) : `index.md` et `changelog_beta.md` décrivent la liste à cocher « Plugins exclus » et le retrait du champ
// « Pièces exclues » ; chaque libellé cité existe verbatim dans plugin_info/configuration.php ou core/php/. Plugins fictifs (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const root = path.join(__dirname, '..', '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const index = read('docs/fr_FR/index.md');
const changelog = read('docs/fr_FR/changelog_beta.md');
const page = [read('plugin_info/configuration.php'), read('core/php/jeedom2ha_excluded_plugins.php')].join('\n').replace(/\{\{|\}\}/g, '').replace(/\\'/g, "'");
// Garde levée (front v2, Lot 8) : le § « Filtrage et publication » suit le titre du bloc à l'écran, « Ce qui est publié » (E8).
const filtering = index.slice(index.indexOf('### Ce qui est publié'), index.indexOf('### Avancé et tâche planifiée'));

describe('25.9 / AC8 — documentation de la configuration', () => {
  it('§ Filtrage et publication : liste à cocher (plugins présents, absents encore exclus, ordre sans importance), plus de ligne « Pièces exclues »', () => {
    for (const needle of ['liste à cocher', 'au moins un équipement', 'jeedom2ha lui-même', 'absent de Jeedom', 'L\'ordre des cases n\'a pas d\'importance',
      'Sauvegarder', 'même format']) {
      assert.ok(filtering.includes(needle) || index.includes(needle), needle);
    }
    assert.doesNotMatch(filtering, /\| \*\*Pièces exclues\*\* \|/);
    assert.doesNotMatch(filtering, /virtual,zwave,rfxcom|`1,5,12`/);
    assert.match(filtering, /Pièces exclues : elles se règlent depuis la page du plugin \(menu « ⋯ » d'une carte de pièce, ou détail de la pièce\)\./);
    assert.match(filtering, /\[Exclure une pièce\]\(#exclure-une-pièce\)/);
    // Garde levée (front v2, Lot 8, R24) : « reprises telles quelles » décrivait la migration de l'ancien champ ; retiré de la doc
    // (le changelog le garde).
    assert.ok(filtering.length > 500, 'section présente');
  });

  // Garde levée (front v2, Lot 8) : « Première synchronisation » devient « Première publication : le guide de démarrage » (E1) ;
  // l'étape 3 du guide (« Choisir ce qui est publié ») remplace la liste numérotée.
  it('§ Première publication et famille 7 « Exclusions volontaires » sont réalignées', () => {
    assert.match(index, /3\. « Choisir ce qui est publié » \| « Tout publier \(recommandé\) » ou « Choisir… »/);
    assert.match(index, /Plugin coché dans la liste « Plugins exclus » de la configuration\./);
    assert.match(index, /décochez le plugin dans « Plugins exclus »/);
    assert.doesNotMatch(index, /champs « Plugins exclus » et « Pièces exclues »/);
  });

  it('plus aucun champ « Pièces exclues » décrit comme un champ de configuration', () => {
    assert.doesNotMatch(index, /Champ « Pièces exclues »/);
    assert.doesNotMatch(index, /au champ « Pièces exclues »/);
  });

  it('chaque libellé cité existe verbatim dans la page de configuration', () => {
    for (const label of ['Plugins exclus', '(absent de Jeedom)', 'Aucun plugin avec des équipements.', 'Les équipements des plugins cochés ne sont pas publiés dans Home Assistant.',
      "Pièces exclues : elles se règlent depuis la page du plugin (menu « ⋯ » d'une carte de pièce, ou détail de la pièce).", 'pièces exclues', 'pièce exclue',
      'Ouvrir la page du plugin', 'Politique de publication']) {
      assert.ok(page.includes(label), `« ${label} » absent de la page de configuration`);
    }
  });

  it('changelog_beta.md : l\'entrée mentionne la liste à cocher et le renvoi, sans nom réel', () => {
    const entry = changelog.split('\n---\n').find((part) => part.includes('configuration : plugins à cocher'));
    assert.ok(entry, 'entrée présente');
    assert.match(entry, /liste à cocher/);
    assert.match(entry, /« Pièces exclues »/);
    assert.match(entry, /reprises telles quelles/);
    assert.doesNotMatch(entry, /\b(salon|cuisine|chambre|garage|Alexandre|Dupont)\b/i);
  });
});
