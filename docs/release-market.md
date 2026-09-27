# Procédure de publication Jeedom Market — jeedom2ha

Ce document décrit la procédure de publication du plugin `jeedom2ha` sur le
Jeedom Market (canaux `beta` et `stable`). Il **ne déclenche aucune action** :
aucune écriture Git au-delà de ce fichier, aucun tag `v*`, aucune action sur
le Market ou sur la box.

Chaque fait est étiqueté **PROUVÉ** (preuve inline : URL + citation, ou
commande shell + sortie réelle exécutée dans ce repo) ou **HYPOTHÈSE** (avec
la manière concrète de la lever).

## 1. Faits sur le Market

### 1.1 Compte développeur et validation — PROUVÉ

Avant toute publication, il faut un compte développeur validé par l'équipe
Jeedom.

> Source : https://doc.jeedom.com/fr_FR/dev/publication_plugin
> Citation (extrait indexé de la page officielle) :
> « Pré-requis. S'être inscrit en tant que dev, voir ici. Avoir attendu la
> validation du compte market comme développeur. »

Cette page n'est accessible qu'au travers du rendu JS du site
`doc.jeedom.com` (un fetch HTTP direct renvoie 404, y compris sur la racine
`/fr_FR/dev`) ; la citation ci-dessus provient de l'indexation du moteur de
recherche sur cette URL exacte, pas d'une supposition.

**Délai de validation du compte dev : HYPOTHÈSE.** Aucun délai chiffré n'a
été trouvé sur une page officielle lors de cette recherche. À prouver en
consultant le fil communautaire
`https://community.jeedom.com/t/compte-partenaire-developpeur/145263` (retours
d'utilisateurs sur des délais vécus, non normatifs) ou en ouvrant une demande
de compte dev réelle et en chronométrant la réponse.

### 1.2 Ce que le Market lit sur GitHub (branches) — PROUVÉ (partiel) + HYPOTHÈSE (partiel)

**PROUVÉ** : la fiche GitHub d'un plugin sur le Market expose des champs
explicites de configuration où l'auteur déclare *quelle branche* correspond
au canal beta et *quelle branche* correspond au canal stable — ce ne sont pas
des noms figés côté Jeedom, mais des valeurs saisies par le développeur.

> Source : https://community.jeedom.com/t/solved-how-to-setup-github-repo-for-my-plugin/1206
> Extrait indexé (exemple d'un autre plugin) :
> « Utilisateur ou organisation du dépot: snipsco
> Nom du dépôt: snips-jeedom-plugin
> Beta: beta
> Stable: master »

Confirmation secondaire (autre plugin, exemple similaire) :

> Source : https://jeedomiser.fr/article/installer-vos-plugins
> Extrait : « ID logique du plugin : fbbot […] Utilisateur ou organisation du
> dépôt : NextDom […] Nom du dépôt : plugin-fbbot […] Branche : master »

Pour `jeedom2ha`, les branches déclarées seraient donc `beta` → `beta` et
`stable` → `stable`, ce qui correspond déjà à la convention de noms utilisée
dans ce repo (voir `docs/git-strategy.md`), sans changement nécessaire.

**HYPOTHÈSE** : la fréquence exacte de synchronisation (auto périodique vs
bouton "Synchronize Market" vs webhook GitHub) n'est pas confirmée avec un
chiffre précis. Élément partiel PROUVÉ :

> Source : https://doc.jeedom.com/en_US/core/4.1/update
> Extrait indexé : « Jeedom periodically connects to the Market to see if
> updates are available. The date of the last check is indicated at the top
> left of the page. »

Donc il y a bien un mécanisme périodique automatique côté **box cliente**
(vérification qu'une nouvelle version existe), en plus d'un bouton de
synchronisation manuelle côté **fiche Market** (voir 1.5). Le délai exact de
ce cycle périodique (minutes/heures) n'est pas confirmé — à prouver en
consultant `Configuration → Mise à jour / Market → onglet Market` sur une
instance Jeedom réelle (paramètre "Vérifier automatiquement s'il y a des
mises à jour").

### 1.3 Contenu empaqueté — PROUVÉ (absence de mécanisme d'exclusion Git)

Recherche d'un mécanisme d'exclusion `export-ignore` dans ce repo :

```
$ find . -iname ".gitattributes"
(aucun résultat)
```

Aucun fichier `.gitattributes` n'existe dans `jeedom2ha`. Il n'y a donc
**aucune règle `export-ignore`** définie pour ce repo — un `git archive`
(ou tout mécanisme Market s'appuyant dessus) sur une branche donnée
empaquetterait tout le contenu versionné de cette branche, y compris
`tests/`, `_bmad/`, `.github/`, `scripts/`, `docs/`, etc.

**PROUVÉ (mécanisme de l'ancienne installation par ZIP)** : le mécanisme
générique "installer depuis un fichier" attend un `plugin_info/` à la racine
du zip, dont le nom de fichier zip == ID du plugin :

> Source : https://doc.jeedom.com/en_US/core/4.2/plugin
> Extrait : « Attention, in the case of adding by a zip file, the name of
> the zip must be the same as the ID of the plugin and upon opening the ZIP
> a plugin_info folder must be present. »

**HYPOTHÈSE** : pour une installation **depuis GitHub** (le cas retenu par
`jeedom2ha`), le mécanisme réel de récupération du contenu (checkout complet
de la branche vs archive filtrée par le serveur Market) n'a pas été confirmé
par une preuve directe. À prouver concrètement en :
1. publiant une version beta réelle (une fois le compte dev validé),
2. installant cette version beta sur une box de test,
3. inspectant le contenu réellement présent sous le répertoire du plugin sur
   cette box (`ls -la /path/plugin/jeedom2ha`) pour vérifier si `tests/`,
   `_bmad/`, `.github/` etc. sont présents ou non.

Tant que cette preuve terrain n'est pas faite, il faut supposer par défaut
que **tout ce qui est versionné sur `beta`/`stable` sera livré aux
utilisateurs finaux**, y compris les répertoires de développement — à la
différence du déploiement `rsync` interne qui, lui, filtre explicitement via
`.rsync-plugin-deploy.filter` (voir 1.6). C'est un écart de mécanisme
important entre déploiement interne et publication Market.

### 1.4 Champs `info.json` qui comptent pour la version — PROUVÉ

Lecture du fichier réel du repo :

```
$ cat plugin_info/info.json
{
	"id": "jeedom2ha",
	"name": "Jeedom2HA",
	"pluginVersion": "0.3.0",
	...
	"require": "4.4",
	"os" : { "min" : 11, "max" : 12.99 },
	...
	"changelog": "https://github.com/alexsahut/jeedom2ha/blob/main/docs/fr_FR/changelog.md",
	"documentation": "https://github.com/alexsahut/jeedom2ha/blob/main/docs/fr_FR/index.md",
	...
}
```

Champ qui porte la version affichée/comparée par le Market : `pluginVersion`
(actuellement `"0.3.0"`, semver — voir entrée changelog du 2026-09-27 :
« Version lisible : `pluginVersion` passé en semver »).
Champ de compatibilité comparé au core Jeedom de la box : `require` (`"4.4"`).
Champ de compatibilité OS : `os.min` / `os.max` (`11` / `12.99`).

**Point d'attention factuel (PROUVÉ par lecture directe, à corriger avant
publication)** : les champs `changelog` et `documentation` pointent en dur
vers `blob/main/...`. Une box qui installe la version **stable** ou **beta**
affichera donc, via ces liens, le changelog/la doc de la branche `main` —
pas celui réellement livré sur le canal installé. Tant que `beta`/`stable`
sont figées loin derrière `main` (voir section 2), ces liens sont trompeurs
pour un utilisateur du Market. **HYPOTHÈSE sur la correction** : soit garder
les liens sur `main` par convention (le contenu documentaire n'y change pas
souvent différemment des autres branches), soit les faire pointer sur
`blob/stable/...` / `blob/beta/...` selon le canal — ce choix reste à trancher
par Alex, ce n'est pas un fait Market mais une décision produit.

### 1.5 Changelog et doc exigés par le Market — PROUVÉ (mécanisme d'affichage) + fait local

> Source : https://doc.jeedom.com/en_US/core/4.1/update
> Extrait : « Pre-update : Allows you to update the update script […] If the
> changelog is empty but you still have an update, it means that the
> documentation has been updated. […] it is often an update of the
> translation, documentation. »

Cela confirme que le Market/Update Center **affiche un changelog** à
l'utilisateur avant mise à jour, et qu'un changelog vide est toléré pour un
changement documentaire mineur — mais implique qu'un changelog est attendu
dans le cas général.

Fait local (PROUVÉ par lecture) : `docs/fr_FR/changelog.md` est à jour et
détaillé jusqu'au 2026-09-27 (dernière entrée : v0.3.0). En revanche,
`docs/fr_FR/changelog_beta.md` est encore le **stub générique du template
Jeedom** (« Changelog plugin template - beta », entrées 2020-2022, aucune
entrée réelle de `jeedom2ha`) :

```
$ head -8 docs/fr_FR/changelog_beta.md
# Changelog plugin template - beta

# 19/01/2022

- Optimisations V4.2

# 20/11/2020

- Présentation officielle V4
```

**PROUVÉ (gap réel identifié)** : ce fichier devra être remplacé par un vrai
changelog beta avant toute première publication, sans quoi les utilisateurs
du canal beta verraient le texte de template Jeedom générique.

### 1.6 Comportement d'une box market/stable lors d'une mise à jour — PROUVÉ (partiel) + HYPOTHÈSE (partiel)

**PROUVÉ (mécanisme de sauvegarde générale, pas spécifique au plugin)** :

> Source : https://doc.jeedom.com/en_US/core/4.1/update
> Extrait : « Save before : Back up Jeedom before updating. The backup is
> performed locally only (neither Market nor Samba). »

C'est une sauvegarde **de l'instance Jeedom entière**, optionnelle/à la
discrétion de l'utilisateur au moment de la mise à jour — pas une garantie
automatique de rollback plugin par plugin.

**HYPOTHÈSE (préservation de `data/` par le remplacement Market)** : aucune
preuve officielle directe trouvée confirmant que le mécanisme de mise à jour
Market exclut spécifiquement un répertoire `data/` du plugin lors du
remplacement de fichiers. Ce comportement existe et est **prouvé** dans notre
propre script (`scripts/deploy-to-box.sh`, voir 1.3bis / section 4), mais
c'est un mécanisme **que nous avons écrit nous-mêmes**, pas une garantie du
Market. À prouver concrètement par un test terrain : installer une version
beta réelle sur une box de test contenant des données dans le répertoire
`data/` du plugin, déclencher une mise à jour Market vers une version
supérieure, puis vérifier que `data/` est toujours présent et inchangé après
la mise à jour.

**HYPOTHÈSE (redémarrage du démon)** : aucune preuve officielle directe que
Jeedom relance automatiquement le démon `hasOwnDeamon: true` après une mise à
jour Market du plugin. Le fichier `info.json` déclare bien
`"hasOwnDeamon": true` (fait PROUVÉ par lecture), ce qui indique à Jeedom que
le plugin a un démon à gérer, mais le comportement exact post-update
(redémarrage automatique vs redémarrage manuel requis par l'utilisateur)
reste à vérifier sur box de test.

## 2. État actuel — beta / stable / main

Commandes exécutées dans ce worktree (`docs/market-release-procedure`,
`origin` à jour via `git fetch --tags` avant capture) :

```
$ git for-each-ref --format='%(refname:short) %(objectname) %(committerdate:iso-strict)' \
    refs/remotes/origin/main refs/remotes/origin/beta refs/remotes/origin/stable
origin/beta   1a149ca3e19d303cc6256c3d3382539af80f2fb8   2026-04-10T15:40:32+02:00
origin/main   dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e   2026-09-27T15:29:40+02:00
origin/stable dfd58d67063c497ccae0749190c4556d85b55ae7   2026-04-10T15:41:02+02:00

$ echo "beta..main:   $(git rev-list --count origin/beta..origin/main)"
beta..main:   143
$ echo "stable..beta: $(git rev-list --count origin/stable..origin/beta)"
stable..beta: 0
$ echo "stable..main: $(git rev-list --count origin/stable..origin/main)"
stable..main: 143

$ git tag -l 'v*'
v1.1.0
$ git tag -l 'deploy-*' | tail -5
deploy-d7db48a01cc47fb2c54c7d2584e3ab31ec4e8f7b-20260927T122724Z
deploy-dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e-20260927T133649Z
```

Lecture de ces chiffres :
- `stable` est strictement identique en contenu à `beta` (0 commit d'écart,
  `git diff --stat origin/beta origin/stable` est vide) : `stable` n'a qu'un
  commit de fusion "de plus" (`dfd58d6`, la merge PR #74 depuis `beta`), sans
  aucun changement de fichier.
- `beta` et `stable` sont figées au 2026-04-10 (`1a149ca` / `dfd58d6`),
  toutes deux 143 commits en retard sur `main` (`dd304f1`, 2026-09-27).
- Le tag `v1.1.0` (166cb7b) est un ancêtre commun de `main` **et** de
  `beta` — c'est la dernière release taguée avant le gel :

```
$ git log -1 --format='%H %ai %s' v1.1.0
166cb7beda25777021dce6ca97081c721b5dbdc0 2026-04-10 15:40:10 +0200 \
  docs(v1.1): closeout Epic 5 — gouvernance Git maint/vX.Y + retro + sprint-status (#72)

$ git log -3 --format='%H %s' origin/beta
1a149ca3e19d303cc6256c3d3382539af80f2fb8 Merge pull request #73 from alexsahut/main
166cb7beda25777021dce6ca97081c721b5dbdc0 docs(v1.1): closeout Epic 5 ... (#72)
538032e73da850e4ccccd83a06f86d8d218975e9 feat(epic-5): closeout stories 5.4 + 5.7 ... (#71)

$ git log -3 --format='%H %s' origin/stable
dfd58d67063c497ccae0749190c4556d85b55ae7 Merge pull request #74 from alexsahut/beta
1a149ca3e19d303cc6256c3d3382539af80f2fb8 Merge pull request #73 from alexsahut/main
166cb7beda25777021dce6ca97081c721b5dbdc0 docs(v1.1): closeout Epic 5 ... (#72)
```

**Précédent historique important (PROUVÉ)** : la dernière promotion réelle
`main → beta` et `beta → stable` ne s'est **pas** faite par un `push`
fast-forward brut, mais par des **pull requests de fusion** GitHub (#73 puis
#74), produisant chacune un commit de merge explicite (`Merge pull request
#73 from alexsahut/main`, `Merge pull request #74 from alexsahut/beta`). Ce
précédent est cohérent avec `docs/git-strategy.md` (§ Règles de merge) :
« La promotion de `main` vers `beta` doit se faire par merge commit de
promotion. […] Une promotion de release ne doit pas utiliser […] » — le
document de gouvernance qui fait autorité sur ce repo exige un **commit de
merge de promotion**, pas un simple déplacement de pointeur en fast-forward
silencieux. La procédure de la section 3 suit donc ce précédent réel et cette
règle écrite, pas une hypothèse de fast-forward brut.

Rappel (déjà établi hors de ce document, non re-vérifié ici) : la box de
référence est installée depuis le Market en canal **stable**, version
installée le 13/03, version distante annoncée « N/A » (aucune mise à jour
proposée au 26/09) — cohérent avec le fait que `stable` (contenu figé au
2026-04-10) n'a pas bougé depuis.

## 3. Promotion du même SHA vers `beta` puis `stable`

Décideur explicite pour **chaque** passage de canal : **Alex**. Aucun agent
IA ne déclenche ces étapes seul.

### Étape 0 — Gates requis avant toute promotion

- CI verte sur le commit candidat sur `main` (matrice complète exigée par la
  protection de branche `main`, contextes requis constatés) :

```
$ gh api repos/alexsahut/jeedom2ha/branches/main/protection --jq '.required_status_checks.contexts'
[
  "PR Routing Policy", "PR Metadata Policy", "Lint (Python 3.9)",
  "Test Report", "Test (Python 3.9)", "Test (Python 3.11)",
  "Node unit tests", "PHP lint & tests (PHP 7.4)",
  "PHP lint & tests (PHP 8.2)", "Shell syntax (bash -n)"
]
```

- Le commit candidat doit déjà avoir été **déployé et validé sur la box**
  réelle, matérialisé par un tag `deploy-<sha>-<horodatage>` existant sur ce
  SHA (convention déjà en usage, voir section 2).
- Si l'écran/l'UI du plugin a été modifié depuis la dernière promotion :
  preuve UX (capture ou description du test manuel) attachée à la PR de
  promotion.
- `docs/fr_FR/changelog.md` (et, une fois créé réellement, le changelog beta)
  à jour pour couvrir tous les changements depuis la dernière promotion.
- `plugin_info/info.json` → `pluginVersion` cohérent avec le tag `vX.Y.Z`
  visé (semver, voir section 1.4).

### Étape 1 — Tag de release sur le commit déployé et validé

```
git tag -a vX.Y.Z <sha-deploye-et-valide> -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

Condition : `<sha-deploye-et-valide>` doit déjà porter un tag `deploy-...`
(preuve terrain que ce SHA tourne réellement sur la box).

### Étape 2 — Promotion `main` → `beta` (décision Alex)

Suit le précédent réel (PR #73) et `docs/git-strategy.md` : une pull request
de promotion dédiée `main → beta`, fusionnée par un **merge commit explicite**
(pas de squash, pas de fast-forward silencieux) :

```
git checkout beta
git pull origin beta
git merge --no-ff vX.Y.Z -m "Promote main to beta: vX.Y.Z"
# revue par Alex puis :
git push origin beta
```

(Alternative outillée équivalente : ouvrir la PR `main → beta` sur GitHub et
la fusionner avec la stratégie "Create a merge commit", jamais "Squash" ni
"Rebase", pour préserver un commit de promotion traçable — cohérent avec
l'historique constaté de PR #73/#74.)

### Étape 3 — Promotion `beta` → `stable` (décision Alex, après validation beta)

Même mécanique, une fois `beta` validée (retours utilisateurs canal beta,
délai de validation à la discrétion d'Alex) :

```
git checkout stable
git pull origin stable
git merge --no-ff beta -m "Promote beta to stable: vX.Y.Z"
# revue par Alex puis :
git push origin stable
```

**Écart avec la commande brute demandée initialement** : une publication par
« fast-forward » brut (`git push origin <sha>:refs/heads/beta`) déplacerait
le pointeur de branche sans laisser de trace de commit de promotion. Ce
document s'écarte volontairement de cette formulation littérale pour suivre
la règle déjà écrite et déjà appliquée dans ce repo
(`docs/git-strategy.md`, précédent PR #73/#74) : un commit de merge de
promotion explicite. Si Alex préfère malgré tout un fast-forward strict pour
une prochaine promotion, c'est une dérogation à documenter explicitement à ce
moment-là, pas la procédure par défaut.

## 4. Le piège de la première publication

La box de référence croit tourner la version Market stable depuis le 13/03,
alors que le plugin **n'est pas encore publié sur le Market** (confirmé par
Alex). La première publication réelle sur le canal stable doit donc
correspondre exactement au code qui tourne réellement en prod sur cette box
au moment de la publication — pas à un état arbitraire de `stable` (qui est
aujourd'hui figée bien en amont, au commit `dfd58d6` / 2026-04-10).

**Vérification obligatoire avant la 1ère publication stable** : comparer
explicitement le SHA que l'on s'apprête à publier avec le SHA effectivement
déployé sur la box (matérialisé par le tag `deploy-...` le plus récent, voir
section 6 pour la commande exacte). Si ces deux SHA diffèrent, la publication
ne doit pas avoir lieu tant que le SHA candidat n'est pas exactement celui
qui tourne sur la box (ou un descendant explicitement re-déployé et
re-validé avant publication).

### Cohabitation `deploy-to-box.sh` (rsync) vs mise à jour Market — PROUVÉ (mécanisme local) + HYPOTHÈSE (mécanisme Market)

**PROUVÉ (mécanisme local, lecture de `scripts/deploy-to-box.sh`)** :

```
$ grep -n "rsync\|--delete\|data/\|VERSION" scripts/deploy-to-box.sh | sed -n '1,20p'
...
652:sudo rsync -a --delete --exclude 'data/' "${JEEDOM_STAGING_DIR}/" "${JEEDOM_BOX_PATH}/"
...
665:echo "  1c. VERSION → ${JEEDOM_BOX_PATH}/VERSION"
```

`deploy-to-box.sh` fait un `rsync --delete` qui **exclut explicitement**
`data/` (`--exclude 'data/'`), donc préserve les données du plugin sur la
box, puis écrit un fichier `VERSION` (version + SHA + date) à la racine du
plugin, **après** ce rsync pour ne pas en être victime.

**HYPOTHÈSE (mécanisme Market)** : rien ne prouve que le remplacement de
fichiers déclenché par une mise à jour Market applique la même exclusion de
`data/` — voir 1.6. Tant que ce n'est pas vérifié sur box de test, il faut
considérer `data/` comme **non garanti préservé** par une mise à jour Market.

**Risque d'alternance des deux mécanismes (PROUVÉ par lecture de code, pas
de test terrain nécessaire)** : le fichier `VERSION` écrit par
`deploy-to-box.sh` n'est pas un artefact connu ou lu par le mécanisme Market
(il n'apparaît dans aucun champ `info.json`). Si les deux mécanismes sont
utilisés en alternance sur une même box :
- une mise à jour Market écrasera le code déployé manuellement par rsync,
  sans mettre à jour (ni même connaître) le fichier `VERSION` — celui-ci
  deviendra silencieusement obsolète et mensonger (il indiquera un SHA qui
  n'est plus celui réellement en place) ;
- inversement, un rsync manuel après une mise à jour Market écrasera le code
  livré par le Market sans que le Market en soit informé, cassant la
  cohérence de version affichée dans l'UI Jeedom (qui se fierait au Market
  pour connaître la version installée).

**Recommandation opérationnelle (conséquence directe des faits ci-dessus,
pas une nouvelle hypothèse)** : ne jamais utiliser les deux mécanismes en
alternance sur la même box après le basculement vers le Market. Une fois la
box basculée sur un canal Market, `deploy-to-box.sh` ne doit plus y être
exécuté directement.

### Bascule propre `rsync` manuel → chaîne Market

Étapes déduites des faits ci-dessus (procédure recommandée, pas encore
exécutée) :
1. S'assurer que le SHA tournant sur la box via le dernier `rsync` manuel est
   exactement le SHA publié en première version stable Market (vérification
   section 6).
2. Ne plus exécuter `deploy-to-box.sh` sur cette box après la première
   installation/mise à jour réussie depuis le Market.
3. Marquer ce dernier `rsync` manuel comme le dernier de son genre (par
   exemple par une entrée dans le tag `deploy-...` existant ou une note dans
   le suivi de projet), pour qu'aucun humain ou agent ne relance
   `deploy-to-box.sh` sur cette box par réflexe.
4. Toute évolution suivante suit désormais uniquement le flux
   `main → beta → stable` de la section 3, et la box se met à jour via le
   Market (proposition de mise à jour, action manuelle de l'utilisateur pour
   l'appliquer).

## 5. Retour arrière côté Market

**HYPOTHÈSE (capacité de rollback Market)** : aucune preuve officielle
directe trouvée confirmant qu'un utilisateur peut, depuis l'UI Jeedom,
réinstaller délibérément une version antérieure déjà publiée d'un plugin
(par opposition à simplement ne pas appliquer une mise à jour proposée). Les
pages officielles consultées (`doc.jeedom.com/en_US/core/4.1/update`,
`doc.jeedom.com/en_US/core/4.2/plugin`) décrivent la proposition de mise à
jour et son application, mais aucune fonction explicite de "downgrade" vers
une version Market antérieure choisie par l'utilisateur. À prouver
concrètement : chercher, sur une box de test avec un plugin ayant plusieurs
versions stables publiées, si l'UI Market propose un choix de version ou
uniquement "installer la dernière".

**Fait établi (hors recherche Market, déjà validé sur ce projet)** : le
véritable filet de sécurité de rollback reste `scripts/deploy-to-box.sh
--rollback`, déjà exercé et validé lors des exercices 1 et 2 de déploiement
sur la box réelle (restauration depuis l'archive tar.gz sauvegardée avant
écrasement, voir entrée changelog 2026-09-27 : « sauvegarde automatique
(archive tar.gz, permissions 700/600) du plugin existant avant écrasement »).
Le Market, même s'il expose un mécanisme de retour en arrière (à prouver),
ne doit pas être considéré comme le filet de sécurité principal pour ce
projet : c'est `deploy-to-box.sh --rollback` qui a une preuve d'exécution
réelle sur la box de référence.

## 6. Vérification à blanc (lecture seule, ne pousse rien)

Bloc de commandes reproductible, **exécuté réellement dans ce worktree** au
moment de la rédaction de ce document (sortie collée telle quelle
ci-dessous, et également collée dans le corps de la PR) :

```bash
#!/usr/bin/env bash
# Lecture seule stricte : ne crée aucun tag, ne pousse aucune branche,
# ne touche ni au Market ni à la box.
set -euo pipefail

CANDIDATE_SHA="$(git rev-parse HEAD)"
echo "SHA candidat : ${CANDIDATE_SHA}"

LATEST_DEPLOY_TAG="$(git tag -l 'deploy-*' --sort=-creatordate | head -1)"
echo "Tag deploy- le plus récent : ${LATEST_DEPLOY_TAG}"

DEPLOY_SHA_FROM_NAME="$(echo "${LATEST_DEPLOY_TAG}" | sed -E 's/^deploy-([0-9a-f]+)-.*$/\1/')"
echo "SHA extrait du nom du tag : ${DEPLOY_SHA_FROM_NAME}"

# 1. Correspondance exacte tag <-> SHA effectivement déployé (comparaison de
#    chaînes entre le SHA porté par le nom du tag et le SHA réel du commit
#    pointé par le tag).
TAG_COMMIT_SHA="$(git rev-list -n1 "${LATEST_DEPLOY_TAG}")"
if [ "${TAG_COMMIT_SHA}" = "${DEPLOY_SHA_FROM_NAME}" ]; then
  echo "[OK] correspondance exacte nom-de-tag <-> commit pointé"
else
  echo "[ECHEC] divergence nom-de-tag vs commit pointé"
fi

# 2. Le candidat est-il ancêtre (ou égal) du SHA deploy- le plus récent ?
if git merge-base --is-ancestor "${CANDIDATE_SHA}" "${DEPLOY_SHA_FROM_NAME}"; then
  echo "[OK] candidat ancêtre ou égal au SHA déployé"
else
  echo "[ECHEC] candidat NON ancêtre du SHA déployé"
fi

# 3. Diff de contenu entre le candidat et le tag deploy- existant le plus
#    proche : doit être vide si c'est exactement le même commit.
echo "--- git diff --stat candidat vs tag deploy ---"
git diff --stat "${CANDIDATE_SHA}" "${DEPLOY_SHA_FROM_NAME}" || true
echo "(vide ci-dessus = même contenu)"
```

### Sortie réelle obtenue (exécutée le 2026-09-27, HEAD du worktree = `dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e`)

```
SHA candidat : dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e
Tag deploy- le plus récent : deploy-dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e-20260927T133649Z
SHA extrait du nom du tag : dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e
[OK] correspondance exacte nom-de-tag <-> commit pointé
[OK] candidat ancêtre ou égal au SHA déployé
--- git diff --stat candidat vs tag deploy ---
(vide ci-dessus = même contenu)
```

Interprétation : dans cet exemple, le SHA candidat est exactement le SHA
déjà déployé et validé sur la box (`dd304f1...`) — c'est le cas attendu pour
une première publication stable conforme à la section 4. Aucune commande de
ce bloc ne crée de tag, ne pousse de branche, ni n'agit sur le Market ou la
box.
