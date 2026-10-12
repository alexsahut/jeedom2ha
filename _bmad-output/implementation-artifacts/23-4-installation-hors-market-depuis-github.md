# Story 23.4 : Installation hors Market depuis GitHub

Status: draft

> Brouillon. Relecture ClaudeBox obligatoire; test sur VM vierge 23.1 seulement.

## Story

En tant que bêta-testeur, je veux une installation GitHub vérifiée, afin de tester la branche réellement maintenue sans ambiguïté.

## Critères d'acceptation proposés

1. `docs/fr_FR` documente « Installer depuis GitHub (bêta) »: archive de `main` tant que C1 n'a pas livré une `beta` maintenue, puis bascule explicitement sur `beta`; extraction sous `plugins/jeedom2ha`, droits, activation, dépendances.
2. Procédure exécutée sur VM 122 vierge: instance fonctionnelle, versions et contrôles anonymisés.
3. README/docs/site nomment la même branche à jour; tant que C1/A2 ne maintient pas `beta`, elle n'est pas présentée comme dernière version.
4. Prérequis Mosquitto/HA renvoient à la documentation sans secrets.
5. Mise à niveau/rollback testés ou explicitement exclus.

## Tâches proposées

- [ ] **Prérequis :** snapshot vierge A66/23.1 confirmé; branche = `main` jusqu'à C1, aucune promesse `beta` avant cette bascule.
- [ ] ClaudeBox confirme snapshot vierge et bascule de branche après C1.
- [ ] Écrire/exécuter procédure et conserver preuve anonymisée.
- [ ] Aligner README/site/docs et retirer références beta obsolètes.
