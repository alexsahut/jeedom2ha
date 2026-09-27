# Parcours BMAD : rapide ou complet

## Critères de choix

**Parcours rapide** (`quick-spec` + `quick-dev`) : applicable **uniquement** si les quatre conditions suivantes sont **toutes** vraies.

1. Changement local (aucune dépendance externe modifiée, aucun contrat d'API tiers touché).
2. Réversible (un simple revert du commit suffit à annuler l'effet).
3. Sans effet sur l'interface utilisateur (aucun fichier front-end, aucun écran, aucun libellé visible modifié).
4. Sans effet sur la publication vers Home Assistant (aucun changement de payload, de topic, de registre ou de daemon de sync).

**Parcours complet** : dès qu'**une seule** des quatre conditions ci-dessus est fausse.

## Règles non négociables (les deux parcours)

- **Critères d'acceptation testables**, rédigés avant toute ligne de code.
- **Impact production et procédure de retour arrière** rédigés avant de coder — jamais après, jamais "au besoin".
- **Définition de `done`** :
  - un SHA précis ;
  - CI verte sur ce SHA ;
  - tests ciblés **nommés explicitement** (pas "les tests passent") ;
  - la **commande exacte** pour les rejouer ;
  - tout changement touchant la publication vers Home Assistant exige une preuve terrain après déploiement par le gate (inventaire des entités avant/après, 0 erreur) avant de passer `done`.
- **Story touchant l'interface** : statut `ready-for-UX-validation` obligatoire avant `done`, puis preuve d'usage réel de l'interface. Le gate UX outillé n'existe pas encore : en attendant, une validation manuelle est acceptée mais doit être **nommément identifiée** — qui a validé, quand, sur quel SHA/environnement.

## Personnalisations BMAD à préserver

BMAD est un framework tiers installé sous `_bmad/`. Une mise à jour future de BMAD peut écraser ces fichiers ; si cela arrive, les 3 changements ci-dessous doivent être réappliqués manuellement :

- `_bmad/bmm/workflows/4-implementation/sprint-status/workflow.md` : le statut `ready-for-UX-validation` a été ajouté partout où les statuts de story sont listés, comptés, validés ou affichés (statuts valides, compteurs, résumé, mode data, mode validate), ainsi qu'une action suggérée dédiée.
- `_bmad/bmm/workflows/4-implementation/code-review/workflow.md` : l'étape 5 détecte désormais un impact UI (champ `UI Impact` de la story, ou fichiers modifiés sous `desktop/`/`core/ajax/`) et route vers le statut `ready-for-UX-validation` au lieu de `done` directement, avec synchronisation correspondante dans `sprint-status.yaml`.
- `_bmad/bmm/workflows/4-implementation/create-story/template.md` : ajout du champ `UI Impact` au gabarit de story, utilisé par `code-review` pour la détection d'impact UI ci-dessus.
