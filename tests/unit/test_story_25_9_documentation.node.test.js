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
const filtering = index.slice(index.indexOf('### Filtrage et publication'), index.indexOf('## Première synchronisation'));

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
    assert.match(filtering, /reprises telles quelles/);
  });

  it('§ Première synchronisation et famille 7 « Exclusions volontaires » sont réalignées', () => {
    assert.match(index, /2\. Ajustez les filtres si nécessaire \(plugins exclus, politique de publication ; les pièces s'excluent depuis la page du plugin\)\./);
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
