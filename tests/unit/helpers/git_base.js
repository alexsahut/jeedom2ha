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
      return execFileSync('git', args.map((a) => (a === '{base}' ? base : a)), { encoding: 'utf8', cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] });
    } catch { /* base suivante */ }
  }
  return null;
}

/** `git diff <options> {base} -- <files>` : texte du diff, '' si vide, null si aucune base. */
function diffAgainstBase(options, files) {
  return git(['diff', ...options, '{base}', '--', ...files]);
}

const removedLines = (diff) => diff.split('\n').filter((l) => l.startsWith('-') && !l.startsWith('---'));

module.exports = { diffAgainstBase, removedLines, BASES };
