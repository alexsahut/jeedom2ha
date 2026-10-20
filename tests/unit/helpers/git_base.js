'use strict';

/* Base de comparaison des gardes « diff vide » de la Story 25.4 : main, origin/main, puis le SHA de main à la création de la
 * branche (4ff80cd, PR #300 fusionnée). Rend null si aucune base n'est disponible (clone superficiel) : le garde est alors
 * sans effet, comme ceux de 25.3. */

const { execFileSync } = require('node:child_process');
const path = require('node:path');

const ROOT = path.join(__dirname, '..', '..', '..');
const BASES = ['main', 'origin/main', '4ff80cdbb04532ff01d7d6fbe6ee640333a21898'];

function git(args) {
  for (const base of BASES) {
    try {
      return execFileSync('git', args.map((a) => a.split('{base}').join(base)), { encoding: 'utf8', cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] });
    } catch { /* base suivante */ }
  }
  return null;
}

/** `git diff <options> {base} -- <files>` : texte du diff, '' si vide, null si aucune base. */
function diffAgainstBase(options, files) {
  return git(['diff', ...options, '{base}', '--', ...files]);
}

/** Contenu d'un fichier à la base de comparaison (`git show <base>:<fichier>`), null si aucune base (story 24.2). */
function fileAtBase(file) {
  return git(['show', '{base}:' + file]);
}

/* Seule ligne retirée admise dans jeedom2ha_mapping_override.js : le JSDoc `@returns {{…}|null}` de 25.7, dont le `{{` était
 * apparié par le traducteur du cœur Jeedom avec le `}}` d'un libellé plus bas (« {{par le plugin X » sur la box, gate 25.6).
 * Commentaire seul : aucune règle d'état n'est touchée. Voir test_jeedom_traducteur_marqueurs. */
const ALLOWED_REMOVED = new Set(['-   * @returns {{kind: string, code: string}|null}']);

const removedLines = (diff) => diff.split('\n').filter((l) => l.startsWith('-') && !l.startsWith('---') && !ALLOWED_REMOVED.has(l));

module.exports = { diffAgainstBase, fileAtBase, removedLines, BASES, ALLOWED_REMOVED };
