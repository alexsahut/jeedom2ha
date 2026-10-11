# Story A2 : Paquet distribuable et promotion épurée — D2

Status: ready-for-dev

Epic: (Chantier Market 2026-10)

Story Key (sprint-status): `a2-paquet-distribuable-promotion-epuree`

## Story

En tant que mainteneur,  
je veux disposer d'un script de construction de paquet épuré (excluant _bmad, tests, scripts de dev) et d'une CI de contrôle anti-régression,  
afin de publier un artefact stable sur les branches `beta` et `stable` et garantir que seuls les fichiers de production y sont inclus.

## Description

Décision validée (D2) : les branches `beta` et `stable` doivent contenir un paquet épuré produit depuis un SHA de `main` par un script versionné.

### Base existante
- Fichier de filtrage : `.rsync-plugin-deploy.filter` (présent à la racine, liste les exclusions)
- Git strategy : `docs/git-strategy.md` (politique Git et branches)
- Release marker : `docs/release-market.md` (procédure de publication Market — à amender)

### Livrable
1. **Script de construction** : shell ou Python, deterministique, basé sur `.rsync-plugin-deploy.filter`
   - Entrée : SHA de main (ex: `7dd0120`)
   - Sortie : paquet zipé ou tree épuré prêt pour `beta`/`stable`
   - Exclusions : `_bmad*`, `tests`, `scripts`, `.claude`, `.agent(s)`, `CLAUDE.md`, `.github`
   - Vérification : liste des fichiers inclus figée et vérifiable

2. **Test CI de contrôle anti-régression** : 
   - À chaque PR, vérifier que le paquet construit contient bien et seulement les fichiers attendus
   - Bloquer si un fichier interdit (ex: `.github`, `_bmad`) se retrouve dans le paquet
   - Rapporter la list des fichiers inclus pour audit

3. **Amendments documentation** :
   - `docs/git-strategy.md` §1.3 (ou nouvelle section) : documenter le script de construction et son invocation
   - `docs/release-market.md` §3 : préciser comment promouvoir un SHA déployé en `beta` sans pousser directement
   - Ajouter un schéma ou pseudo-code pour la promotion : tag vX.Y.Z → beta (fast-forward) → stable (fast-forward)

### Parcours rapide
1. Écrire le script de construction (50 lignes shell max) basé sur rsync + `.rsync-plugin-deploy.filter`
2. Tester manuellement : `./build-package.sh 7dd0120` produit un paquet valide
3. Ajouter une section brève à `docs/git-strategy.md` avec la commande de lancement
4. Documenter la liste d'exclusion figée (celle du `.rsync-plugin-deploy.filter` actuel)

### Parcours complet (recommandé pour prod)
1. Même script que parcours rapide
2. Ajouter une CI check : créer un job GitHub Actions qui, à chaque PR vers `main`, construit le paquet et valide le contenu
3. Définir une "liste de fichiers attendus" (manifest) figée en CI, rejetant toute régression d'exclusion
4. Implémenter un test de reconstruction de `beta` depuis le paquet à blanc, **SANS pousser sur beta**
   - Vérifie que le paquet binaire peut être dépakcé et utilisé comme source pour `beta`
   - Compare le hash du contenu (arbre `git`) avec le SHA source de `main`
5. Complèter les amendments à `git-strategy.md` et `release-market.md` avec exemples concrets
6. Ajouter un diagramme Mermaid dans `release-market.md` montrant : SHA deployé → tag vX.Y.Z → beta (fast-forward) → stable (fast-forward)

## Acceptance Criteria

1. **Given** le script de construction  
   **When** exécuté sur un SHA valide de `main` (ex: `7dd0120`)  
   **Then** un paquet épuré est produit, sans aucun fichier des exclusions.

2. **Given** les exclusions listées dans `.rsync-plugin-deploy.filter`  
   **When** le script s'exécute  
   **Then** chaque fichier/dossier exclu est bien absent du paquet final.

3. **Given** une liste de fichiers attendus (manifest)  
   **When** une PR est créée  
   **Then** la CI valide que le paquet construit respecte le manifest (anti-régression).

4. **Given** le paquet binaire produit  
   **When** il est décompressé sur une branche `beta` vierge  
   **Then** le contenu du tree est identique au SHA source de `main` (excepté `.git`, `.gitignore`, etc.).

5. **Given** la reconstruction de `beta` à partir du paquet  
   **When** elle s'exécute en CI  
   **Then** elle réussit SANS pousser sur `beta` (preuve locale uniquement).

6. **Given** les amendments à `git-strategy.md` et `release-market.md`  
   **When** la PR est créée  
   **Then** le processus complet de promotion (tag → beta → stable) est documenté avec exemples.

## Tasks / Subtasks

### Parcours rapide
- [ ] T1 — Écrire le script de construction
  - [ ] Créer `scripts/build-package-for-market.sh` (ou équivalent)
  - [ ] Parser `.rsync-plugin-deploy.filter` ou l'utiliser directement avec rsync
  - [ ] Accepter un SHA en argument, construire le paquet
  - [ ] Tester manuellement sur `7dd0120`
  - [ ] Vérifier qu'aucun `_bmad`, `tests`, `scripts`, `.claude` ne figure dans le paquet

- [ ] T2 — Documenter brièvement dans `git-strategy.md`
  - [ ] Ajouter une section "Construction du paquet" avec la commande d'invocation
  - [ ] Lister les exclusions (copie simple du `.rsync-plugin-deploy.filter`)

### Parcours complet (recommandé)
- [ ] T3 — Ajouter CI check GitHub Actions
  - [ ] Créer un job `.github/workflows/validate-package.yml`
  - [ ] À chaque PR vers `main`, construire le paquet et valider le contenu
  - [ ] Rejeter si un fichier interdit est présent (fail la PR)

- [ ] T4 — Implémenter test de reconstruction
  - [ ] Ajouter un step CI qui dépacque le paquet sur une branche `beta` de test
  - [ ] Comparer le hash du tree avec le SHA source
  - [ ] Loger "reconstruction OK" ou signaler une différence
  - [ ] **NE PAS pousser sur `beta` réelle** — test local uniquement

- [ ] T5 — Complèter les amendments documentation
  - [ ] `docs/git-strategy.md` §1.3 : détailler la construction et l'invocation du script
  - [ ] `docs/release-market.md` §3 : préciser le flow promotion (tag → beta → stable)
  - [ ] Ajouter un diagramme Mermaid ou pseudo-code
  - [ ] Ajouter des exemples concrets de commandes git (push force interdites, fast-forward obligatoire)

## Impact Produit

- **Si non fait** : promotion manuelle vers `beta`/`stable` risque d'inclure des fichiers non pertinents (_bmad, tests, etc.), dégradant la maintenabilité et augmentant la taille du paquet Market.
- **Si parcours rapide** : script basique qui fonctionne mais sans CI ; dépend de l'humain pour valider l'absence de régression.
- **Si parcours complet** : CI automatisée anti-régression, test de reconstruction, documentation précise ; promotion devient safe et reproductible.

## Rollback / Plan de Retour Arrière

- **Script** : git revert du commit contenant le script ; reprendre la construction manuelle (non recommandé).
- **CI check** : supprimer le job `.github/workflows/validate-package.yml` ; CI redevient permissive.
- **Reconstruction de beta** : revenir à promotion manuelle (git push direct sur `beta`).

## Notes

- Cette story dépend d'une `info.json` stable et vérifiée (story A3) pour définir la version d'export.
- L'ordre d'exécution proposé : **A1 et A3 en parallèle (indépendants), puis A2** (dépend d'un info.json clarifié par A3).
- Le script DOIT être déterministique (même SHA en entrée → même paquet en sortie, bit-for-bit si possible).
- Exclusions supplémentaires éventuelles : consulter ClawBox pour les spécificités Jeedom.
