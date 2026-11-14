// ARTEFACT — Front v2, Lot 8 : guide « Premiers pas », documentation alignée sur l'écran (spec R24, glossaire 3.x).
// - « Premiers pas » existe, est lié en tête de index.md, parle comme l'écran et sans jargon interne ;
// - chaque libellé d'action du lexique (desktop/js/jeedom2ha_lexique.js) cité comme action figure dans la documentation ;
// - la documentation ne cite aucun libellé de bouton absent du code (libellés en gras entre « », entrées de menu en « … ») ;
// - les libellés retirés de l'écran par les lots 1 à 7 ne sont plus cités.
// Aucun nom réel (CC-48).
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { describe, it } = require('node:test');
const assert = require('node:assert/strict');
const L = require('../../desktop/js/jeedom2ha_lexique.js');

const root = path.join(__dirname, '..', '..');
const read = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const index = read('docs/fr_FR/index.md');
const compteurs = read('docs/fr_FR/compteurs.md');
const premiers = read('docs/fr_FR/premiers-pas.md');
const DOCS = { 'index.md': index, 'premiers-pas.md': premiers, 'compteurs.md': compteurs };

// Texte comparable : marqueurs de traduction retirés, apostrophes typographiques et échappées ramenées à « ' », espaces réduits.
const norm = (text) => String(text).replace(/[’‘]/g, "'").replace(/\\'/g, "'").replace(/\{\{|\}\}/g, '').replace(/\s+/g, ' ');
const codeFiles = ['desktop/js', 'desktop/php', 'core', 'plugin_info'].flatMap((dir) => fs.readdirSync(path.join(root, dir), { recursive: true })
  .filter((f) => /\.(js|php)$/.test(f)).map((f) => path.join(dir, f)));
const code = norm(codeFiles.map(read).join('\n'));

const word = (w) => new RegExp('(?<![\\p{L}\\p{N}_])' + w + '(?![\\p{L}\\p{N}_])', 'iu');

describe('Lot 8 — « Premiers pas »', () => {
  it('la page existe, est liée en tête de index.md et renvoie à la documentation complète', () => {
    const head = index.split('\n').slice(0, 12).join('\n');
    assert.match(head, /\[Premiers pas\]\(premiers-pas\.md\)/, 'lien vers « Premiers pas » en tête de index.md');
    assert.match(premiers, /^# Premiers pas/m);
    assert.match(premiers, /\]\(index\.md\)/);
    assert.match(premiers, /\*\*jeedom2ha publie vos équipements Jeedom dans Home Assistant\.\*\* Jeedom reste la source : rien n'y est modifié\./);
  });

  it('les quatre étapes du guide de démarrage sont citées avec les titres de l’écran, dans l’ordre', () => {
    const guide = norm(read('desktop/js/jeedom2ha_guide.js'));
    const steps = ['Connecter le broker MQTT', 'Vérifier que Home Assistant écoute', 'Choisir ce qui est publié', 'Publier dans Home Assistant'];
    let from = 0;
    steps.forEach((title, i) => {
      assert.ok(guide.includes(title), `« ${title} » absent du guide`);
      const at = premiers.indexOf(`${i + 1}. **« ${title} »**`, from);
      assert.ok(at >= from, `étape ${i + 1} « ${title} »`);
      from = at;
    });
    for (const label of ['Ouvrir la configuration MQTT', 'Tester, enregistrer et redémarrer le démon', "Je l'ai vu", 'Je ne le vois pas',
      'Tout publier (recommandé)', 'Choisir…', 'Voir ma maison', 'Ne plus afficher ce guide', 'Guide de démarrage']) {
      assert.ok(premiers.includes(`« ${label} »`), `« ${label} » cité`);
      assert.ok(code.includes(norm(label)), `« ${label} » absent du code`);
    }
  });

  it('dit où trouver ses équipements dans Home Assistant, avec la capture versionnée', () => {
    assert.match(premiers, /^## Où trouver vos équipements dans Home Assistant$/m);
    assert.match(premiers, /Paramètres › Appareils et services/);
    assert.match(premiers, /« Jeedom \(jeedom2ha\) »/);
    assert.match(premiers, /\]\(images\/home-assistant-appareils\.png\)/);
    assert.ok(fs.existsSync(path.join(root, 'docs/fr_FR/images/home-assistant-appareils.png')));
  });

  it('les trois questions, « Relire Jeedom ou Republier tout ? », corriger un type, choisir ce qui est publié, vérifier l’installation', () => {
    for (const heading of ['## Trois questions, pour chaque équipement', '## Relire Jeedom ou Republier tout ?', '## Corriger un type',
      '## Choisir ce qui est publié', '## Quelque chose ne va pas ? « Vérifier l\'installation… »']) {
      assert.ok(premiers.includes('\n' + heading + '\n'), heading);
    }
    for (const question of ['Qu\'est-ce qui est publié ?', 'Pourquoi pas ?', 'Comment changer ?']) assert.ok(premiers.includes(question), question);
    for (const label of ['Corriger le type…', 'Enregistrer et publier', 'Vérifier l\'installation…', 'Relire Jeedom', 'Republier tout']) {
      assert.ok(premiers.includes(`« ${label} »`), label);
    }
  });

  it('reste courte et sans jargon interne (termes interdits des tests de glossaire et de la spec 3.1)', () => {
    assert.ok(premiers.split('\n').length < 120, 'une page courte');
    const FORBIDDEN = ['override', 'mapping', 'bridge', 'prête', 'prêtes', 'prêt', 'prêts', 'bloquante', 'bloquantes', 'rescanner', 'rescan',
      'modale', 'fenêtre', 'forcer', 'forçage', 'synchro', 'synchronisation', 'page principale', 'barre de santé', 'Type Jeedom',
      'Plus d\'actions', 'imposé', 'parc', 'entity_id', 'projection', 'domaine', 'payload', 'topic', 'discovery'];
    for (const forbidden of FORBIDDEN) assert.doesNotMatch(premiers, word(forbidden.replace(' ', '\\s')), `« ${forbidden} »`);
  });

  it('cloisonnement : aucun libellé de compteur (ils vivent dans compteurs.md)', () => {
    const counters = /\d (publiés?|publiées?|à appliquer|exclus?|exclues?|désactivés?|rien à publier|ignorées?)\b|Chargement des compteurs|Compteurs indisponibles|équipements? non lus?/;
    assert.doesNotMatch(premiers, counters);
  });

  it('les liens de « Premiers pas » vers index.md visent des titres existants', () => {
    const slug = (title) => title.toLowerCase().replace(/[^\p{L}\p{N}\s-]/gu, '').replace(/\s/g, '-');
    const anchors = index.split('\n').filter((l) => /^#{1,6} /.test(l)).map((l) => slug(l.replace(/^#+ /, '')));
    for (const m of premiers.matchAll(/\]\(index\.md#([^)]+)\)/g)) assert.ok(anchors.includes(m[1]), `premiers-pas.md → index.md#${m[1]}`);
  });
});

describe('Lot 8 — index.md : glossaire cible, écrans, « dix types »', () => {
  it('le glossaire de la présentation porte les mots cibles (spec 3.1)', () => {
    for (const term of ['Publier', 'Relire Jeedom', 'Republier', 'Appliquer', 'Réglage', 'Type générique', 'Type HA', 'Entité', 'Conseil',
      'État', 'Pièce', 'Maison', 'Démon', 'Barre d\'état']) {
      assert.ok(new RegExp('^\\| \\*\\*' + term.replace(/[()]/g, '\\$&') + '\\*\\*').test(index.split('\n').find((l) => l.startsWith(`| **${term}**`)) || ''), term);
    }
    assert.match(index, /« Personnalisé »/);
    assert.match(index, /« objet » dans Jeedom, « zone » dans Home Assistant/);
  });

  it('une ancre par écran, listée en tête', () => {
    for (const anchor of ['#la-barre-détat', '#première-publication--le-guide-de-démarrage', '#le-bloc-de-la-maison', '#la-vue-de-travail',
      '#le-détail-dun-équipement', '#corriger-le-type-dune-commande', '#exclure-une-pièce', '#vérifier-linstallation', '#configuration',
      '#les-causes-de-blocage', '#les-conseils']) {
      assert.ok(index.includes(`](${anchor})`), anchor);
    }
  });

  it('« dix types » publiés, vanne et serrure comprises, écrits « Lumière (light) »', () => {
    assert.match(index, /Le plugin publie dix types d'entités Home Assistant/);
    const section = index.slice(index.indexOf('### Ce que le plugin sait publier'), index.indexOf('### Limites'));
    const rows = section.split('\n').filter((l) => /^\| [^-|][^|]* \(`[a-z_]+`\) \|/.test(l));
    assert.equal(rows.length, 10);
    for (const [type, label] of Object.entries(L.HA_TYPE_LABELS)) {
      if (section.includes(`(\`${type}\`)`)) assert.ok(section.includes(`| ${label} (\`${type}\`) |`), type);
    }
    assert.ok(section.includes('(`valve`)') && section.includes('(`lock`)'));
  });

  it('la configuration (E8), le guide (E1) et « Vérifier l’installation » (E7) sont décrits avec les libellés de l’écran', () => {
    for (const label of ['Tester, enregistrer et redémarrer le démon', 'Tester seulement', 'Connexion testée', 'Réglages enregistrés', 'Démon redémarré',
      'En cas de doute sur un équipement', 'Publier quand même (recommandé)', 'Ne publier que les équipements reconnus avec certitude',
      'Enregistrer et relire Jeedom', 'Récupérer depuis MQTT Manager', 'Réinitialiser le formulaire', 'Bienvenue dans jeedom2ha', 'Guide de démarrage',
      'Le démon tourne', 'Le broker MQTT répond', 'Home Assistant a été vu sur ce broker', 'Dernière relecture réussie', 'Pour le support',
      'Télécharger le diagnostic support', 'Télécharger l\'export de décision', 'Journaux du plugin :']) {
      assert.ok(index.includes(label), `« ${label} » décrit dans index.md`);
      assert.ok(code.includes(norm(label)), `« ${label} » absent du code`);
    }
    const advanced = index.slice(index.indexOf('### Vérifier l\'installation'));
    assert.match(advanced, /\*\*Avancé\*\* \(replié\)[\s\S]*« Télécharger l'export de décision »/, 'export de décision documenté dans « Avancé »');
  });
});

describe('Lot 8 — la documentation parle exactement comme l’écran', () => {
  it('chaque libellé d’action du lexique est cité dans index.md et dans « Premiers pas »', () => {
    const labels = Object.values(L.ACTIONS);
    assert.ok(labels.length >= 5);
    for (const label of labels) {
      assert.ok(norm(index).includes(`« ${norm(label)} »`), `index.md : « ${label} »`);
      assert.ok(norm(premiers).includes(`« ${norm(label)} »`), `premiers-pas.md : « ${label} »`);
    }
  });

  it('aucun libellé de bouton cité en gras entre « » n’est absent du code', () => {
    for (const [name, text] of Object.entries(DOCS)) {
      for (const m of text.matchAll(/\*\*« ([^»*]+?) »\*\*/g)) {
        if (/^(N|\d+) /.test(m[1])) continue; // gabarit chiffré (« N bloqués ») : décrit dans compteurs.md, construit par le code
        assert.ok(code.includes(norm(m[1])), `${name} : « ${m[1]} » n'existe pas à l'écran`);
      }
    }
  });

  it('aucune entrée de menu ou action « … » citée n’est absente du code', () => {
    for (const [name, text] of Object.entries(DOCS)) {
      for (const m of text.matchAll(/« ([A-ZÀ-Ý][^«»:…—\d]{2,60}…) »/g)) {
        assert.ok(code.includes(norm(m[1])), `${name} : « ${m[1]} » n'existe pas à l'écran`);
      }
    }
  });

  it('les libellés retirés de l’écran par les lots 1 à 7 ne sont plus cités', () => {
    const STALE = ['Type Jeedom', 'Plus d\'actions', 'Tester la connexion', 'Publier les équipements sûrs et probables', 'Publier uniquement les équipements sûrs',
      'Dernière synchro', 'Synchronisation terminée', 'exclus et autres', 'Configuration Home Assistant par pièce', 'imposé (', 'neuf types',
      'barre de santé', 'Télécharger le diagnostic…', 'Toutes les pièces »', 'Rechercher une pièce ou un équipement', 'Appliquer les filtres et rescanner',
      'enregistré automatiquement', 'Actions de la pièce', 'configuration par pièce'];
    for (const [name, raw] of Object.entries(DOCS)) {
      const text = raw.replace(/<!--[\s\S]*?-->/g, ''); // l'en-tête de maintenance de compteurs.md peut nommer l'ancien libellé
      for (const stale of STALE) {
        assert.ok(!norm(text).toLowerCase().includes(norm(stale).toLowerCase()), `${name} cite encore « ${stale} »`);
      }
    }
    // « page principale » : seul le bouton de retour de la vue de travail porte encore ce libellé à l'écran.
    for (const [name, text] of Object.entries(DOCS)) {
      const prose = text.replace(/« Page principale »/g, '').replace(/<!--[\s\S]*?-->/g, '');
      assert.doesNotMatch(prose, /page principale/i, `${name} : « page principale » hors du bouton de retour`);
    }
  });

  it('plus de phrase sur les anciennes versions dans la documentation utilisateur', () => {
    for (const [name, text] of Object.entries(DOCS)) {
      const prose = text.replace(/<!--[\s\S]*?-->/g, '');
      assert.doesNotMatch(prose, /n'ouvre plus|Il n'y a plus de champ|ancien champ|anciennement|reprises telles quelles|version qui ne tenait pas/i, name);
    }
  });
});
