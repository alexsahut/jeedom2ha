# Story A2 : Paquet distribuable et promotion épurée via branches `release/vX.Y.Z` (D2)

Status: done

Epic: (Chantier Market 2026-10)

Story Key (sprint-status): `a2-paquet-distribuable-promotion-epuree`

## Story

En tant que mainteneur,  
je veux un script de construction de paquet épuré et un mécanisme de promotion par branche intermédiaire `release/vX.Y.Z` + PR + merge commit,  
afin de publier sur `beta`/`stable` un artefact Market conforme sans jamais fusionner l'arbre complet de `main` ni utiliser de fast-forward.

## Description

Décision validée (D2) : les branches `beta` et `stable` reçoivent un paquet épuré produit depuis un SHA de `main` par un script versionné — **jamais** de fast-forward, **jamais** de push direct. `docs/git-strategy.md` impose : promotion `main -> beta` et `beta -> stable` par **merge commit de promotion**, jamais squash, jamais cherry-pick comme méthode normale, et une story ne doit jamais être mergée directement vers `beta`/`stable`.

### Mécanisme réel retenu

1. Script de construction : part d'un SHA de `main` déjà déployé et validé sur la box (portant un tag `deploy-...`), produit un **arbre épuré** filtré par un manifeste (base : `.rsync-plugin-deploy.filter`, actuellement : `.git`, `.env*`, `.github/`, `.agent(s)/`, `.claude/`, `tests/`, `scripts/`, `_bmad*`, `docs/` en entier, fichiers de dev).
2. **Correctif obligatoire** : le filtre actuel exclut `docs/` en entier. Or `plugin_info/info.json` référence `changelog`/`documentation`/`changelog_beta`/`documentation_beta` sous forme de liens `blob/<branche>/docs/fr_FR/...` (story A3). Si `docs/` est totalement exclu du paquet publié sur `beta`/`stable`, ces liens renvoient une 404 une fois le repo réellement épuré sur ces branches. **Le manifeste doit inclure `docs/fr_FR/`** (changelog, documentation utilisateur) dans le paquet épuré.
3. Le script écrit cet arbre épuré sur une **branche `release/vX.Y.Z` créée depuis l'état courant de `beta`** (pas depuis main), avec un commit unique : `release vX.Y.Z (source <sha>)`.
4. Ouverture d'une **PR `release/vX.Y.Z -> beta`**, mergée par **merge commit** (jamais fast-forward, jamais squash) — conforme à la politique existante.
5. Une fois `beta` validée, même mécanisme pour `beta -> stable` : branche `release/vX.Y.Z` (ou équivalent) basée sur `stable`, PR, merge commit.
6. **Aucune fusion de l'arbre complet de `main`** : seul l'arbre épuré transite, via la branche intermédiaire — ce n'est pas un merge Git classique de `main` dans `beta`, c'est une construction + remplacement contrôlé du contenu, committé comme un seul commit de release.

### Point ouvert — protection de branche (décision à soumettre, pas tranchée ici)

`beta`/`stable` sont probablement protégées par des checks requis (`PR Routing Policy`, suite de tests) qui dépendent de `.github/workflows/`. Si `.github/` est exclu du paquet épuré, une PR `release/vX.Y.Z -> beta` ne pourra jamais satisfaire ces checks et ne sera jamais mergeable.

Deux options possibles, **à soumettre à Alex/ClaudeBox, pas tranchées par cette story** :
- **Option 1** : conserver sur `beta`/`stable` un sous-ensemble minimal de `.github/workflows/` (ex. un seul workflow de validation du paquet/manifeste), distinct du paquet plugin lui-même — c'est-à-dire que le manifeste d'exclusion appliqué au paquet *livré sur le Market* n'est pas forcément identique à ce qui reste committé sur la branche `beta`/`stable` elle-même.
- **Option 2** : ajuster les règles de protection de branche sur `beta`/`stable` pour n'exiger qu'un check spécifique à la release (ex. validation du manifeste), distinct des checks complets de `main`.

Cette story documente le problème et propose les deux options ; elle ne modifie pas la protection de branche sans validation explicite.

### Parcours

**Parcours complet uniquement** (règle CC-10 — pas de choix laissé ici, la story touche directement au mécanisme de publication Market, enjeu fort) :
1. Script de construction déterministe (SHA → paquet épuré, incluant `docs/fr_FR/`)
2. CI anti-régression du manifeste d'exclusion (bloque toute régression de la liste)
3. Mécanisme de branche `release/vX.Y.Z` + PR + merge commit documenté et testé à blanc
4. Amendements `docs/git-strategy.md` et `docs/release-market.md`
5. Proposition documentée (non tranchée) sur la protection de branche

## Acceptance Criteria

1. **Given** le script de construction et un SHA de `main`  
   **When** il s'exécute  
   **Then** l'arbre produit respecte le manifeste : chaque fichier/dossier exclu (`.git`, `.github/`, `.agent(s)/`, `.claude/`, `tests/`, `scripts/`, `_bmad*`) est absent, et `docs/fr_FR/` est présent.

2. **Given** un manifeste de fichiers attendus (figé, versionné)  
   **When** une PR touchant le script ou le manifeste est créée  
   **Then** la CI valide le contenu produit contre ce manifeste et rejette toute régression (fichier interdit présent, ou fichier requis absent).

3. **Given** l'arbre épuré produit par le script pour un SHA donné  
   **When** il est comparé au SHA source filtré par le même manifeste (appliqué directement sur l'arbre de `main`)  
   **Then** les deux sont identiques — **pas** « identique au SHA source » brut (contradiction avec l'épuration), mais « identique au SHA source filtré par le manifeste ».

4. **Given** une branche `release/vX.Y.Z` construite depuis `beta` avec l'arbre épuré  
   **When** la reconstruction est testée à blanc (local ou CI)  
   **Then** elle réussit, produit un commit `release vX.Y.Z (source <sha>)`, et **aucun push n'est effectué vers `beta` ni `stable` réelles**.

5. **Given** les amendements à `docs/git-strategy.md` (règles de merge / politique de promotion) et `docs/release-market.md`  
   **When** la PR est créée  
   **Then** le mécanisme réel (branche `release/vX.Y.Z` + PR + merge commit, jamais fast-forward) est documenté avec un exemple concret de commandes.

6. **Given** le problème de protection de branche  
   **When** la fiche est relue  
   **Then** les deux options sont présentées comme décision ouverte à soumettre à Alex, sans que la story ne les tranche ni ne les implémente.

## Tasks / Subtasks

- [ ] T1 — Écrire le script de construction du paquet épuré
  - [ ] Créer `scripts/build-market-package.sh` (ou équivalent), argument = SHA source
  - [ ] Baser le manifeste sur `.rsync-plugin-deploy.filter`, **en retirant `docs/` de l'exclusion et en ajoutant une inclusion explicite de `docs/fr_FR/`**
  - [ ] Produire un arbre/tarball épuré, déterministe (même SHA en entrée → même sortie)
  - [ ] Tester manuellement sur un SHA réel (ex. `7dd0120`)

- [ ] T2 — CI anti-régression du manifeste
  - [ ] Figer la liste de fichiers/dossiers attendus (manifeste versionné, distinct du `.rsync-plugin-deploy.filter` si besoin de divergence documentée)
  - [ ] Ajouter un job CI qui construit le paquet sur chaque PR touchant le script/manifeste et valide le contenu

- [ ] T3 — Mécanisme de branche `release/vX.Y.Z`
  - [ ] Implémenter la création de branche `release/vX.Y.Z` depuis `beta` (ou `stable`), remplacement de l'arbre par le paquet épuré, commit unique de release
  - [ ] Tester la reconstruction à blanc, sans push vers `beta`/`stable` réelles
  - [ ] Documenter la commande exacte de création de la PR de promotion (`release/vX.Y.Z -> beta`, merge commit, jamais fast-forward/squash)

- [ ] T4 — Amendements documentation
  - [ ] `docs/git-strategy.md` : section dédiée au script de construction et au flux `release/vX.Y.Z` (sans contredire les règles de merge existantes — les renforcer/préciser)
  - [ ] `docs/release-market.md` : détailler la procédure complète avec exemples de commandes git réels
  - [ ] Documenter explicitement l'inclusion de `docs/fr_FR/` dans le paquet et pourquoi (liens info.json)

- [ ] T5 — Documenter le point ouvert protection de branche
  - [ ] Décrire les deux options (workflow minimal conservé sur beta/stable, ou ajustement des checks requis)
  - [ ] Ne pas trancher ni implémenter — signaler comme décision à soumettre à Alex/ClaudeBox

## Impact Produit

- **Si non fait** : toute promotion `main -> beta -> stable` reste manuelle et risque d'inclure des fichiers de dev, ou de casser les liens changelog/doc de `info.json` si `docs/` reste totalement exclu.
- **Si fait** : promotion reproductible, traçable (un commit = une release), conforme à `docs/git-strategy.md`, liens `info.json` valides sur `beta`/`stable`.

## Rollback / Plan de Retour Arrière

- **Script/CI** : revert du commit introduisant le script et le job CI ; retour à une construction manuelle du paquet (non recommandé, mais sans impact sur l'état existant de `beta`/`stable`).
- **Branche `release/vX.Y.Z`** : supprimer la branche locale/distante si créée par erreur ; aucune PR mergée vers `beta`/`stable` tant que la décision protection de branche n'est pas prise — donc aucun rollback de promotion réelle n'est nécessaire au stade de cette story.
- **Amendements doc** : revert des commits sur `git-strategy.md`/`release-market.md`.

## Notes

- Aucun parcours alternatif : **parcours complet uniquement** (CC-10 — enjeu fort sur le mécanisme de publication).
- Dépendance douce avec A3 : A2 a besoin d'un `info.json` stabilisé (version, liens) pour définir le contenu exact du paquet — **A3 doit être terminée avant que A2 ne soit déclarée `done`**, même si les deux démarrent en parallèle.
- Ordre proposé : **A1 et A3 en parallèle, puis A2**.
- Ce document ne modifie ni ne pousse sur `beta`/`stable` — toute exécution réelle de promotion reste soumise au go d'Alex.
