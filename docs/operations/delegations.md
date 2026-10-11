# Journal des délégations Claude Code cloud

Une ligne par session déléguée (voir `docs/delegation-claude-cloud.md`).
Statuts : `en cours` · `PR ouverte` · `mergée` · `abandonnée`.

Rappel (garde-fou CC-56) : `scripts/deploy-to-box.sh` reste hors périmètre
cloud (secrets/box non accessibles) et exige toujours
`--sha "$(git rev-parse HEAD)"` pour toute exécution locale — ne jamais
citer ce script sans ce flag dans une entrée de ce journal.

| Date | Tâche | Session (ID/URL) | PR | Statut |
|------|-------|------------------|----|--------|
| 2026-10-06 | Story 20.3 — create-story : suppression du gabarit Jeedom et libellés français | [session_01LCk74VN94U3wF72KU9aYnn](https://claude.ai/code/session_01LCk74VN94U3wF72KU9aYnn?from=cli&m=0) | [#220](https://github.com/alexsahut/jeedom2ha/pull/220) | mergée |
| 2026-10-08 | Story 20.3 — dev-story : suppression de la synthèse « Parc global » et de la modale Diagnostic, libellés français | [session_01W64jqBzpoWJJnkdiHXBtuh](https://claude.ai/code/session_01W64jqBzpoWJJnkdiHXBtuh) | [#225](https://github.com/alexsahut/jeedom2ha/pull/225) | PR ouverte |
| 2026-10-11 | Story 20.3 — R1 : correctifs de revue post-fusion (A à I) depuis `story/20-3-revue-r1-post-fusion`, PR vers `main` sans fusion | [session_019KzusdyP2UahqkFEG8WgPM](https://claude.ai/code/session_019KzusdyP2UahqkFEG8WgPM?from=cli&m=0) | — | en cours |
| 2026-10-11 | Story 20.5 — create-story : documentation utilisateur réécrite (CC-07 d) ; lancée sur `story/20-5-create-story` (non poussée avant lancement), la session a continué sur sa propre branche `claude/story-20-5-create-story-j6t1kx` | [session_011bffC3jkNEEXd4yaZRxDYj](https://claude.ai/code/session_011bffC3jkNEEXd4yaZRxDYj?from=cli&m=0) | [#230](https://github.com/alexsahut/jeedom2ha/pull/230) | mergée |
| 2026-10-11 | Story 20.5 — dev-story : Tasks 1 à 4 et préparation 6.1, table de traçabilité affirmation → fichier:ligne, documentation sous `docs/fr_FR` ; lancée sur `story/20-5-dev-story` (non poussée avant lancement), branche réelle de la session à confirmer à l'ouverture de sa PR | [session_01MswuaDVxn8QGzjtRt5iukX](https://claude.ai/code/session_01MswuaDVxn8QGzjtRt5iukX?from=cli&m=0) | — | en cours |
