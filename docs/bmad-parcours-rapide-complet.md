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
  - la **commande exacte** pour les rejouer.
- **Story touchant l'interface** : statut `ready-for-UX-validation` obligatoire avant `done`, puis preuve d'usage réel de l'interface. Le gate UX outillé n'existe pas encore : en attendant, une validation manuelle est acceptée mais doit être **nommément identifiée** — qui a validé, quand, sur quel SHA/environnement.
