// ARTEFACT — Front v2, Lot 9b : finitions de la documentation et de la configuration (regard neuf v2, G6/G7/G8).
// - « Premiers pas » et index.md sans jargon interne (hors annexe qui l'explique) ;
// - encadré « Avant de commencer » : un broker partagé, une installation par broker, mots du nom qui écartent un type (liste
//   exacte du démon, lue ici sans rien modifier), zone fixée à la création ;
// - un seul chemin pour trouver ses appareils dans Home Assistant, le même que le guide ;
// - « non exclu » n'est pas « publié » ; « Voir la première commande bloquée » décrit comme le code ;
// - configuration : « Une seule installation jeedom2ha par broker MQTT » visible, plus de mention « Anciennement ».
// Aucun nom réel (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');

const root = path.join(__dirname, '..', '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const index = read('docs/fr_FR/index.md');
const premiers = read('docs/fr_FR/premiers-pas.md');
const config = read('plugin_info/configuration.php').replace(/\{\{|\}\}/g, '');
const guide = read('desktop/js/jeedom2ha_guide.js').replace(/\{\{|\}\}/g, '').replace(/\\'/g, "'");

const word = (w) => new RegExp('(?<![\\p{L}\\p{N}_])' + w.replace(/\s+/g, '\\s+') + '(?![\\p{L}\\p{N}_])', 'iu');
const JARGON = ['projection', 'commande clé', 'forçage', 'V1 du plugin', 'Parc global', 'backend', 'dashboards', 'sync',
  'sûr uniquement', 'confiance « probable »', 'jeedom2ha_excluded'];

const section = (text, heading) => {
  const start = text.indexOf('\n' + heading + '\n');
  assert.ok(start >= 0, heading);
  const rest = text.slice(start + heading.length + 2);
  const next = rest.search(/\n#{1,3} /);
  return next < 0 ? rest : rest.slice(0, next);
};

// Mots du nom qui écartent un type : lus dans le démon (lecture seule), jamais recopiés à la main dans le test.
const keywords = (file, name) => {
  const src = read(file);
  const block = src.slice(src.indexOf(name + ' = {'), src.indexOf('}', src.indexOf(name + ' = {')));
  return [...block.matchAll(/"([^"]+)"/g)].map((m) => m[1]);
};
const NAME_WORDS = {
  lumière: keywords('resources/daemon/mapping/light.py', '_NON_LIGHT_KEYWORDS'),
  interrupteur: keywords('resources/daemon/mapping/switch.py', '_NON_SWITCH_KEYWORDS'),
  volet: keywords('resources/daemon/mapping/cover.py', '_NON_COVER_KEYWORDS'),
};

describe('Lot 9b — jargon', () => {
  it('« Premiers pas » ne contient aucun mot de la liste de jargon', () => {
    for (const j of JARGON) assert.doesNotMatch(premiers, word(j), `premiers-pas.md : « ${j} »`);
  });

  // Le Lot 9a traduit ces mots à l'affichage (USER_WORDS du lexique) : la doc cite les textes affichés, sans annexe de jargon.
  it('index.md ne contient aucun mot de la liste de jargon', () => {
    for (const j of JARGON) assert.doesNotMatch(index, word(j), `index.md : « ${j} »`);
    assert.ok(!index.includes('mots techniques encore affichés'), 'plus d’annexe de jargon');
  });
});

describe('Lot 9b — « Premiers pas » : avant de commencer', () => {
  const box = section(premiers, '## Avant de commencer : trois règles à connaître');

  it('l’encadré vient avant le guide et pose les trois règles', () => {
    assert.ok(premiers.indexOf('## Avant de commencer') < premiers.indexOf('## Le guide de démarrage'));
    assert.match(box, /Un seul broker MQTT, partagé avec Home Assistant, et une seule installation jeedom2ha par broker/);
    assert.match(box, /La pièce dans Home Assistant est fixée à la création/);
    assert.match(box, /Certains mots du nom d'un équipement écartent un type/);
  });

  it('la liste des mots est exactement celle du démon, type par type', () => {
    for (const [type, words] of Object.entries(NAME_WORDS)) {
      assert.ok(words.length >= 10, `${type} : liste lue dans le démon`);
      const line = box.split('\n').find((l) => l.includes(`pour une **${type}`) || l.includes(`pour un **${type}`) || l.includes(`une **prise ou un ${type}`));
      assert.ok(line, `ligne de la liste pour ${type}`);
      const cited = line.slice(line.indexOf(':') + 1).replace(/[;.]\s*$/, '').split(',').map((w) => w.trim()).filter(Boolean);
      assert.deepEqual([...cited].sort(), [...words].sort(), `${type} : mêmes mots que le démon`);
    }
    assert.match(box, /« Lumière garage »/);
    // Revue #396 : pour un nom qui écarte un type, corriger le type est une impasse (reste ambigu) ; la consigne est
    // « renommer puis Relire Jeedom » ou publication « Toujours » puis « Appliquer ».
    assert.match(box, /« Relire Jeedom »/);
    assert.match(box, /« Toujours »\*\*, puis \*\*« Appliquer »/);
    assert.doesNotMatch(box, /avec \*\*« Corriger le type… »\*\*/);
    const annex = section(index, '### Annexe : nommage des équipements');
    assert.match(annex, /« Toujours », puis « Appliquer »/);
    assert.doesNotMatch(annex, /avec « Corriger le type… »/);
  });

  it('l’annexe « nommage » de index.md porte les mêmes mots', () => {
    const annex = section(index, '### Annexe : nommage des équipements');
    for (const words of Object.values(NAME_WORDS)) for (const w of words) assert.match(annex, word(w), w);
  });
});

describe('Lot 9b — un seul chemin vers ses appareils', () => {
  const PATH = 'Paramètres › Appareils et services › MQTT';
  it('le guide, « Premiers pas » et index.md disent le même chemin', () => {
    assert.ok(guide.includes(PATH), 'guide');
    assert.ok(section(premiers, '## Où trouver vos équipements dans Home Assistant').includes(PATH));
    for (const [name, text] of [['premiers-pas.md', premiers], ['index.md', index]]) {
      assert.doesNotMatch(text, /onglet \*\*Appareils\*\*|tapez « Jeedom »|Paramètres → Appareils/, name);
    }
  });
});

describe('Lot 9b — exactitude doc / écran', () => {
  it('« non exclu » n’est pas « publié », dans le panneau « Choisir ce qui est publié »', () => {
    assert.match(section(index, '### Choisir ce qui est publié'), /« Non exclu » ne veut pas dire « publié »/);
    assert.match(section(premiers, '## Choisir ce qui est publié'), /« Non exclu » ne veut pas dire « publié »/);
  });

  it('« Voir la première commande bloquée » : absent seulement quand chaque commande est bloquée (code)', () => {
    const surface = read('desktop/js/jeedom2ha_mapping_surface.js');
    assert.match(surface, /index === 0 && summary\.first_blocking_cmd_id !== null && !M\.allCommandsBlocked\(tree\)/);
    assert.match(index, /sous la première fiche de cause/);
    assert.match(index, /quand chacune de ses commandes est bloquée, il n'y a rien d'autre à montrer et le lien est absent/);
  });

  it('le nombre de pièces exclues n’est promis que s’il y en a', () => {
    assert.match(config, /\$j2haExcludedRoomsCount > 0/);
    assert.match(index, /Quand au moins une pièce est exclue, leur nombre est rappelé dessous/);
  });

  it('les deux règles qui piquent sont en tête de leur section', () => {
    const broker = section(index, '### Connexion au broker MQTT').trim();
    assert.ok(broker.startsWith('> **Une seule installation jeedom2ha par broker MQTT.**'), 'broker');
    const zone = section(index, '### Annexe : pièces dans Home Assistant (zone suggérée)').trim();
    assert.ok(zone.startsWith('> **La zone Home Assistant est fixée à la création de l\'appareil.**'), 'zone');
  });

  it('le sommaire en tête renvoie à chaque section de premier niveau', () => {
    const head = index.slice(0, index.indexOf('\n## Présentation'));
    const slug = (title) => title.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, '').replace(/\s/g, '-');
    for (const h of index.split('\n').filter((l) => /^## /.test(l) && l !== '## Sommaire')) {
      assert.ok(head.includes(`(#${slug(h.slice(3))})`), h);
    }
    assert.ok(fs.existsSync(path.join(root, 'docs/fr_FR/compteurs.md')), 'compteurs.md présent');
    assert.ok(head.includes('](compteurs.md)'));
  });
});

describe('Lot 9b — libellés du Lot 9a, tels que le code les affiche', () => {
  const code = ['desktop/js/jeedom2ha_lexique.js', 'desktop/js/jeedom2ha_mapping_surface.js', 'desktop/js/jeedom2ha_guide.js',
    'desktop/js/jeedom2ha_exclusions.js', 'desktop/js/jeedom2ha.js'].map(read).join('\n')
    .replace(/\{\{|\}\}/g, '').replace(/\\'/g, "'").replace(/[’‘]/g, "'");
  const docs = (index + premiers).replace(/[’‘]/g, "'");
  for (const label of ['Publier quand même', "Renommer l'équipement dans Jeedom, puis Relire Jeedom", 'Confirmé par vous',
    'Types impossibles pour cet équipement', 'Type dans Home Assistant de', 'Dans Home Assistant, cette entité est :',
    'Ce choix vaut pour les commandes :', 'Enregistrer et publier quand même', 'Je ne vois pas l\'appareil dans Home Assistant',
    'Vérification en cours', 'Réputée faite : une publication a réussi.', "Ce n'est pas un doute mais une contradiction",
    "Cette entité ne se règle pas seule : réglez l'équipement entier.", 'Ce type Home Assistant est invalide pour cette entité.',
    'Erreur de communication avec le démon du plugin.', 'dont 1 désactivé dans Jeedom']) {
    it(`« ${label} » : à l’écran et dans la doc`, () => {
      assert.ok(code.includes(label), `« ${label} » absent du code`);
      assert.ok(docs.includes(label), `« ${label} » absent de la doc`);
    });
  }
  it('plus aucun ancien libellé du panneau de type ni « auto » dans la colonne « Type HA »', () => {
    assert.doesNotMatch(docs, /Autres types, non proposés|non proposé par le plugin pour cette commande|Corriger le type de « /);
    assert.doesNotMatch(docs, /« auto »/);
  });
});

describe('Lot 9b — configuration', () => {
  it('« Une seule installation jeedom2ha par broker MQTT » est affiché dans le bloc du broker, avec sa conséquence', () => {
    const mqtt = config.slice(config.indexOf('Connexion au broker MQTT'), config.indexOf('id="bt_mqttTestSaveRestart"'));
    assert.match(mqtt, /Une seule installation jeedom2ha par broker MQTT\./);
    assert.match(mqtt, /retirerait les boutons de scénario de celle-ci, et inversement\./);
  });

  it('un bouton principal par bloc, « Sauvegarder » de Jeedom expliqué, plus de mention d’une ancienne version', () => {
    assert.doesNotMatch(config, /Anciennement/);
    assert.equal((config.match(/class="btn btn-primary"/g) || []).length, 2, 'un bouton bleu par bloc');
    assert.match(config, /Le bouton « Sauvegarder » de Jeedom enregistre aussi ce bloc mais ne relit pas Jeedom/);
    assert.match(config, /Un équipement dont le nom contredit ses types Jeedom n'est pas un doute/);
  });
});
