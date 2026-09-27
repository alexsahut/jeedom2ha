# Suivi — chore/version-and-deploy-hygiene (points 1 & 4)

## État

- **PR** : [#160](https://github.com/alexsahut/jeedom2ha/pull/160) — `chore/version-and-deploy-hygiene` → `main`
- **SHA** : `6ffc3c8a1d4e1fa5e2e685c9a625387d8bf6b9fb`
- **CI** : verte sur ce SHA (2026-09-27) — `gh pr checks 160` : Lint, Test (Python 3.9 & 3.12), Node, PHP (7.4 & 8.2), Shell syntax, PR Metadata/Routing Policy, Test Report — tous `pass`. Burn-In `skipping` (normal, hors planning/label).
- **Statut** : PR ouverte, **non mergée** — revue humaine explicitement requise pour ce mandat (contrairement au précédent).
- **Parcours BMAD** : rapide (justifié dans la description de la PR selon les 4 critères de `docs/bmad-parcours-rapide-complet.md`).

## Contenu livré

1. `pluginVersion` → `0.3.0` (`plugin_info/info.json`) + entrée changelog.
2. `resources/daemon/main.py` : version + SHA lus dynamiquement (`plugin_info/info.json`, `VERSION` optionnel), log de démarrage étendu, fallback `"inconnu"` si absent/invalide.
3. `scripts/deploy-to-box.sh` : écriture atomique d'un `VERSION` sur la box après le rsync destructeur (relecture de vérification), sauvegarde archive (700/600) avant chaque écrasement.
4. `.rsync-plugin-deploy.filter` + `tests/unit/test_rsync_deploy_filter.py` : garde CI de non-fuite (dry-run réel).

## Reste à valider par un humain

- Revue de code de la PR #160 (logique deploy-to-box.sh, format VERSION, permissions archives).
- Décision de merge (aucun merge automatique effectué).
- Aucune validation terrain sur la box réelle n'est requise ni n'a été faite : le changement ne touche pas la publication vers Home Assistant (uniquement log de démarrage + fichier `VERSION` hors `data/`).
