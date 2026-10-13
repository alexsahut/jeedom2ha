# Story 23.4 : Installation hors Market depuis GitHub

Status: in-progress (partie documentaire livrée ; AC2 non fait)

> Cadrage approuvé par ClaudeBox le 2026-10-12. Brouillon. Relecture ClaudeBox obligatoire; test sur VM vierge 23.1 seulement.

## Story

En tant que bêta-testeur, je veux une installation GitHub vérifiée, afin de tester la branche réellement maintenue sans ambiguïté.

## Critères d'acceptation proposés

1. `docs/fr_FR` documente « Installer depuis GitHub (bêta) »: archive de `main` tant que C1 n'a pas livré une `beta` maintenue, puis bascule explicitement sur `beta`; extraction sous `plugins/jeedom2ha`, droits, activation, dépendances.
2. Procédure exécutée sur VM 122 vierge: instance fonctionnelle, versions et contrôles anonymisés.
3. README/docs/site nomment la même branche à jour; tant que C1/A2 ne maintient pas `beta`, elle n'est pas présentée comme dernière version.
4. Prérequis Mosquitto/HA renvoient à la documentation sans secrets.
5. Mise à niveau/rollback testés ou explicitement exclus.

## Avancement

- AC1 : documenté dans `docs/fr_FR/installation-github.md` (archive de `main`, extraction, droits, activation, dépendances).
- AC2 : **NON FAIT, hors périmètre de cette tâche documentaire.** Aucune exécution sur VM, aucune preuve terrain.
- AC3 : README et `docs/fr_FR/index.md` pointent vers la nouvelle page et nomment `main` ; `beta` n'est pas présentée comme livrée.
- AC4 : prérequis Mosquitto/HA renvoient à `docs/fr_FR/index.md`, sans secret.
- AC5 : mise à niveau et rollback **documentés mais non testés** (mention explicite dans la page).

## Tâches proposées

- [ ] **Prérequis :** snapshot vierge A66/23.1 confirmé; branche = `main` jusqu'à C1, aucune promesse `beta` avant cette bascule.
- [ ] ClaudeBox confirme snapshot vierge et bascule de branche après C1.
- [ ] Exécuter la procédure sur VM vierge et conserver une preuve anonymisée (AC2 — non fait).
- [x] Écrire la procédure (`docs/fr_FR/installation-github.md`).
- [x] Aligner README et `docs/fr_FR/index.md` (aucune référence `beta` obsolète trouvée) ; site non concerné par cette tâche.
