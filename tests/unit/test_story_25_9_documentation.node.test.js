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
  // Garde levée (front v3, Lot 3) : la liste à cocher « Plugins exclus » quitte la configuration (une seule source : le panneau
  // « Choisir ce qui est publié ») ; le § « Ce qui est publié » renvoie au panneau et ne décrit plus de liste ; la famille 7 suit.
  it('§ Ce qui est publié : renvoi au panneau unique, plus de liste à cocher ni de ligne « Pièces exclues »', () => {
    assert.ok(filtering.length > 200, 'section présente');
    assert.match(filtering, /\[Choisir ce qui est publié\]\(#choisir-ce-qui-est-publié\)/);
    assert.doesNotMatch(filtering, /liste à cocher|\| \*\*Pièces exclues\*\* \||\| \*\*Plugins exclus\*\* \|/);
    assert.doesNotMatch(filtering, /virtual,zwave,rfxcom|`1,5,12`/);
  });

  it('§ Première publication et famille 7 « Exclusions volontaires » sont réalignées', () => {
    assert.match(index, /3\. « Choisir ce qui est publié » \| « Tout publier \(recommandé\) » ou « Choisir… »/);
    assert.match(index, /Plugin décoché dans le panneau « Choisir ce qui est publié » \(Par plugin\)\./);
    assert.match(index, /recochez le plugin dans le panneau « Choisir ce qui est publié »/);
    assert.doesNotMatch(index, /champs « Plugins exclus » et « Pièces exclues »|liste « Plugins exclus » de la configuration/);
  });

  it('plus aucun champ « Pièces exclues » décrit comme un champ de configuration', () => {
    assert.doesNotMatch(index, /Champ « Pièces exclues »/);
    assert.doesNotMatch(index, /au champ « Pièces exclues »/);
  });

  // Garde levée (front v2, Lot 9b, regard neuf v2 G6/G8) : la mention « Anciennement « Politique de publication ». » parlait d'une
  // version que l'utilisateur n'a jamais connue ; elle est remplacée par la distinction doute / blocage. Le libellé n'est plus exigé.
  it('chaque libellé cité existe verbatim dans la page de configuration', () => {
    // Garde levée (front v3, Lot 3) : libellés de la configuration réduite au broker.
    for (const label of ['Choisir ce qui est publié', 'Retour à la page du plugin', 'Une seule installation jeedom2ha par broker MQTT.',
      'cron5 désactivé : mises à jour manuelles', 'Tester, enregistrer et redémarrer le démon', 'Réinitialiser le formulaire']) {
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
