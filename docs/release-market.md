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
recherche sur cette URL exacte, pas d'une supposition. **Étiquette : extrait
indexé, page non récupérable directement** — la page complète n'a pas pu être
lue (fetch échoué/tronqué), seul un extrait indexé par le moteur de recherche
a pu être confirmé.

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

> Source : https://doc.jeedom.com/en_US/core/4.1/update (**extrait indexé,
> page non récupérable directement** — fetch direct confirmé en 404 lors de
> cette relecture, seul un extrait indexé par le moteur de recherche a pu
> être confirmé)
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

### 1.3 Contenu empaqueté — PROUVÉ (empiriquement, sur deux plugins tiers réels) + GATE BLOQUANTE résiduelle sur `tests/`

Recherche d'un mécanisme d'exclusion `export-ignore` dans ce repo :

```
$ find . -iname ".gitattributes"
(aucun résultat)
```

Aucun fichier `.gitattributes` n'existe dans `jeedom2ha`. Il n'y a donc
**aucune règle `export-ignore`** définie pour ce repo.

**PROUVÉ (preuve empirique terrain, pas seulement documentaire)** : deux
plugins tiers réellement installés depuis le Market sur la box de référence
(`asahut@192.168.1.21`, lecture seule) ont été comparés à leur dépôt GitHub
public, sur la branche effectivement servie (déduite du champ `changelog`/
`documentation` de leur `info.json`) :

```
$ ssh asahut@192.168.1.21 'ls -a /var/www/html/plugins/tahoma/'
. .. 3rdparty compress.sh core desktop plugin_info README.md

$ curl -s https://api.github.com/repos/redbug26/jeedom-tahoma/contents/?ref=master | jq -r '.[].name'
.gitignore 3rdparty README.md compress.sh core desktop doc plugin_info

$ curl -s https://api.github.com/repos/redbug26/jeedom-tahoma/contents/.gitattributes?ref=master
{"message":"Not Found", ...}
```

```
$ ssh asahut@192.168.1.21 'ls -a /var/www/html/plugins/worxLandroidS/'
. .. composer.json composer.lock core desktop docs LICENSE plugin_info README.md resources vendor

$ curl -s https://api.github.com/repos/mips2648/jeedom-worxLandroidS/contents/?ref=beta | jq -r '.[].name'
.github .gitignore .markdownlint.json LICENSE README.md composer.json composer.lock core desktop docs plugin_info resources
# (branche master : liste identique)

$ curl -s https://api.github.com/repos/mips2648/jeedom-worxLandroidS/contents/.gitattributes?ref=beta
{"message":"Not Found", ...}
```

Conclusions tirées de cette preuve terrain, pas d'une supposition :
1. **`.github/`, les dotfiles (`.gitignore`, `.markdownlint.json`) et les
   dossiers `doc`/`docs` ne sont PAS livrés sur la box réelle**, alors qu'ils
   sont bien présents sur la branche GitHub effectivement servie par le
   Market pour ces deux plugins (la suppression de `doc`/`docs` recoupe
   d'ailleurs exactement le `rm -rf` explicite lu dans `doUpdate()`, voir
   1.6 — confirmation croisée code + terrain).
2. **Aucun des deux dépôts n'a de `.gitattributes`** (404 confirmé sur les
   deux) : le filtrage constaté n'est donc **pas** un `export-ignore` Git.
   Le mécanisme réel (filtrage côté serveur Market avant livraison à la box,
   ou traitement spécifique d'une archive GitHub qui exclurait déjà ces
   éléments) reste **HYPOTHÈSE** — non confirmé par une preuve directe de son
   fonctionnement interne, seul le résultat observé est prouvé.
3. **`tests/` reste non tranché** : ni `tahoma` ni `worxLandroidS` n'ont de
   dossier `tests/` (ou équivalent `_bmad/`, `.claude/`, `.agent`, `scripts/`)
   à leur racine GitHub, donc cette preuve ne dit rien sur le sort réservé à
   ce type de dossier.

**Fix de parité proposé, revu à la lumière de cette preuve** : ajouter un
`.gitattributes export-ignore` serait **inutile** au vu du point 2
ci-dessus — le mécanisme observé n'en dépend pas pour `.github`/dotfiles chez
ces deux plugins, rien ne garantit qu'il en tiendrait compte pour `jeedom2ha`
non plus. La seule option fiable est de **ne pas présumer** que `tests/`,
`_bmad/`, `.claude/`, `.agent`, `scripts/` seront filtrés comme `.github` l'a
été, et de traiter ce point comme une **GATE BLOQUANTE explicite avant la
première publication** (pas un « à vérifier » facultatif) : inspecter
réellement le contenu du plugin sur la box **après** la première publication
beta (`ls -la` du répertoire du plugin), avant toute promotion vers
`stable`. Si `tests/`/`_bmad/`/`.claude/`/`.agent`/`scripts/` s'avèrent
livrés aux utilisateurs, il faudra alors soit les retirer physiquement de
`beta`/`stable` (branches dédiées sans ces dossiers), soit contacter le
support Market pour confirmer si un `.gitattributes export-ignore` serait
pris en compte malgré l'absence de précédent observé.

**PROUVÉ (mécanisme de l'ancienne installation par ZIP)** : le mécanisme
générique "installer depuis un fichier" attend un `plugin_info/` à la racine
du zip, dont le nom de fichier zip == ID du plugin :

> Source : https://doc.jeedom.com/en_US/core/4.2/plugin (**extrait indexé,
> page non récupérable directement** — fetch direct confirmé en 404 lors de
> cette relecture)
> Extrait : « Attention, in the case of adding by a zip file, the name of
> the zip must be the same as the ID of the plugin and upon opening the ZIP
> a plugin_info folder must be present. »

**HYPOTHÈSE (mécanisme exact de récupération)** : pour une installation
**depuis GitHub** (le cas retenu par `jeedom2ha`), le mécanisme précis de
récupération du contenu (checkout complet de la branche vs archive filtrée
par le serveur Market) n'a pas été confirmé par une preuve directe de son
fonctionnement interne — voir la preuve empirique ci-dessus (1.3, comparaison
`tahoma`/`worxLandroidS`) qui prouve le **résultat** (`.github`/dotfiles/
`doc`/`docs` non livrés) sans prouver le **mécanisme**.

Pour `jeedom2ha` spécifiquement, cette preuve terrain reste à faire une fois
la première version beta réellement publiée (une fois le compte dev validé) :
inspecter le contenu réel du répertoire du plugin (`ls -la` sur la box, en
lecture seule) après installation, pour vérifier si `tests/`, `_bmad/`,
`.claude/`, `.agent`, `scripts/` sont présents ou non — voir 1.3 pour le
statut de gate bloquante de ce point précis. Pour `.github/` et les
dotfiles (`.gitignore` notamment), la preuve empirique de 1.3 permet
désormais de considérer, par analogie avec deux plugins tiers réels, qu'ils
ne seront **probablement pas** livrés — mais « probablement » n'est pas
« prouvé pour `jeedom2ha` », d'où le maintien de la gate sur l'ensemble du
point tant qu'aucune inspection directe post-publication n'a été faite.

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

**Recommandation (Point F, à valider par Alex, pas un fait imposé)** : pour
la **première publication**, faire pointer `changelog`/`documentation` sur
`blob/stable/...` plutôt que sur `blob/beta/...` ou `main` — un lien
`stable` reste correct quel que soit le canal effectivement installé par
l'utilisateur final (`stable` est un sous-ensemble figé de `beta`, voir
section 2 : contenu strictement identique aujourd'hui), alors qu'un lien
`beta` afficherait par erreur une documentation non encore stabilisée à un
utilisateur du canal stable.

### 1.5 Changelog et doc exigés par le Market — PROUVÉ (mécanisme d'affichage) + fait local

> Source : https://doc.jeedom.com/en_US/core/4.1/update (**extrait indexé,
> page non récupérable directement** — fetch direct confirmé en 404)
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

### 1.6 Comportement d'une box market/stable lors d'une mise à jour — PROUVÉ (quasi-totalité, relecture directe du cœur Jeedom)

Cette section a été revérifiée par **lecture directe, en lecture seule via
SSH (`asahut@192.168.1.21`), du code source PHP du cœur Jeedom réellement
installé sur la box de référence** — pas par déduction ni par de la
documentation tierce. Fichiers lus : `core/class/update.class.php`,
`core/php/utils.inc.php`, `core/class/plugin.class.php`. Aucune commande
d'écriture n'a été exécutée sur la box pendant cette relecture (uniquement
`sed`/`grep` sur des fichiers existants).

**PROUVÉ (mécanisme de sauvegarde générale, pas spécifique au plugin)** :

> Source : https://doc.jeedom.com/en_US/core/4.1/update (**extrait indexé,
> page non récupérable directement** — fetch direct confirmé en 404 lors de
> cette relecture)
> Extrait : « Save before : Back up Jeedom before updating. The backup is
> performed locally only (neither Market nor Samba). »

C'est une sauvegarde **de l'instance Jeedom entière**, optionnelle/à la
discrétion de l'utilisateur au moment de la mise à jour — pas une garantie
automatique de rollback plugin par plugin.

**PROUVÉ — suppression de `doc`/`docs`, puis fusion additive (pas une
synchronisation miroir) du contenu du plugin** :

> `core/class/update.class.php`, méthode `doUpdate()` (ligne 282), lignes
> 345-354 :
> ```php
> if (file_exists(__DIR__ . '/../../plugins/' . $this->getLogicalId() . '/doc')) {
>     shell_exec('sudo rm -rf ' . __DIR__ . '/../../plugins/' . $this->getLogicalId() . '/doc');
> }
> if (file_exists(__DIR__ . '/../../plugins/' . $this->getLogicalId() . '/docs')) {
>     shell_exec('sudo rm -rf ' . __DIR__ . '/../../plugins/' . $this->getLogicalId() . '/docs');
> }
> shell_exec('find ' . $cibDir . '/ -exec touch {} +');
> rmove($cibDir . '/', __DIR__ . '/../../plugins/' . $this->getLogicalId(), false, array(), true);
> ```

Avant chaque mise à jour Market, Jeedom **supprime explicitement** `doc/` et
`docs/` du plugin déjà installé (`sudo rm -rf`), `touch` tous les fichiers du
zip téléchargé, puis appelle `rmove()` avec son 3ᵉ paramètre (`$_emptyDest`)
à `false`.

> `core/php/utils.inc.php`, fonction `rmove()` (ligne 569) :
> ```php
> function rmove($src, $dst, $_emptyDest = true, $_exclude = array(), $_noError = false, $_params = array()) {
>     if (!file_exists($src)) { return true; }
>     if ($_emptyDest) {
>         rrmdir($dst);
>     }
>     ...
> ```

`$_emptyDest` contrôle si `$dst` est vidé (`rrmdir($dst)`) avant la copie ;
appelé à `false`, ce `rrmdir($dst)` n'est **jamais** exécuté. La mise à jour
Market est donc une **fusion additive/écrasante**, jamais un miroir strict :
elle ajoute/écrase les fichiers du nouveau zip mais ne supprime pas les
fichiers déjà présents sur la box absents du nouveau zip — sauf `doc`/`docs`
(supprimés explicitement juste avant) et sauf le nettoyage ciblé ci-dessous.

**Conséquence directe pour `data/` — PROUVÉ (préservation, corollaire du
même code)** : `data/` n'étant jamais vidé (fusion additive) ni dans la liste
de nettoyage ciblé (voir plus bas), son contenu **est bien préservé** par une
mise à jour Market, comme le fait notre propre `deploy-to-box.sh` — mais pour
une raison différente (fusion additive générique côté Jeedom, pas une
exclusion `data/` spécifique comme dans notre script).

**Conséquence directe pour `resources/` — PROUVÉ (risque de fichiers
orphelins, corollaire du même code)** : le nettoyage ciblé post-install (voir
plus bas) ne couvre qu'une liste fermée de dossiers qui **n'inclut pas
`resources/`**. Si un fichier du démon Python sous `resources/daemon/`
(actuel point d'entrée : `resources/daemon/main.py`) est retiré d'une future
version de `jeedom2ha`, une mise à jour Market **ne le supprimera jamais** de
la box : fusion additive + `resources/` hors périmètre du nettoyage 7 jours
= fichier orphelin permanent. **Garde-fou concret proposé** :
`plugin_info/install.php` expose déjà une fonction `jeedom2ha_update()`
(appelée par `callInstallFunction('update')`, voir plus bas), aujourd'hui
limitée à créer `data/` si absent :
> ```php
> function jeedom2ha_update() {
>     $dataDir = __DIR__ . '/../data';
>     if (!is_dir($dataDir)) {
>         if (!mkdir($dataDir, 0775, true)) { ... } else { ... }
>     }
> }
> ```
C'est le point d'accroche naturel pour y ajouter, avant la première
publication si l'on veut se prémunir de ce risque, un nettoyage explicite de
`resources/daemon/` (comparer le contenu réel sur la box à une liste de
fichiers attendus embarquée dans le zip, supprimer le surplus) — à écrire,
pas seulement à documenter.

**PROUVÉ — permissions réinitialisées à `775` (pas `755`) après une mise à
jour Market** :

> `core/class/update.class.php`, `postInstallUpdate()` (ligne 439), lignes
> 453-455 :
> ```php
> $cmd = system::getCmdSudo() . 'chown -R ' . system::get('www-uid') . ':' . system::get('www-gid') . ' ' . $cibDir . ';';
> $cmd .= system::getCmdSudo() . 'chmod 775 -R ' . $cibDir . ';';
> $cmd .= system::getCmdSudo() . 'chmod 775 -R ' . $cibDir . '/.*;';
> exec($cmd);
> ```

Le Market impose `chown www-data:www-data` puis `chmod 775` récursif
(fichiers, dossiers **et** fichiers cachés) après chaque mise à jour. Ce que
l'on observe aujourd'hui sur la box, en `755` (répertoires, ligne 654) /
`644` (fichiers, ligne 655), **n'est pas un comportement Market — c'est un
artefact de notre propre `scripts/deploy-to-box.sh`** :

> `scripts/deploy-to-box.sh`, lignes 654-655 (`chmod` dirs → `755`, `chmod`
> fichiers → `644`).

Une fois la box basculée sur une vraie mise à jour Market, les permissions
passeront donc à `775` partout — ce n'est pas une régression à corriger, mais
un écart attendu entre les deux mécanismes, à ne pas confondre avec un
problème de sécurité si on l'observe après une vraie mise à jour Market.

**PROUVÉ — nettoyage ciblé des fichiers de plus de 7 jours, liste fermée de
dossiers, coquille `3rparty` déjà présente dans le cœur Jeedom lui-même** :

> `core/class/update.class.php`, ligne 459 :
> ```php
> foreach (array('3rdparty', '3rparty', 'desktop', 'mobile', 'core', 'docs', 'install', 'script', 'plugin_info') as $folder) {
>     if (!file_exists($cibDir . '/' . $folder)) { continue; }
>     shell_exec('find ' . $cibDir . '/' . $folder . '/* -mtime +7 -type f ! -iname "custom.*" ! -iname "common.config.php" ! -path "./vendor/*"  -delete 2>/dev/null');
> }
> ```

Liste exacte et complète, telle qu'écrite dans le cœur Jeedom : `3rdparty`,
`3rparty` (sic — doublon avec coquille, présent tel quel dans le code source
Jeedom, pas une erreur de cette relecture), `desktop`, `mobile`, `core`,
`docs`, `install`, `script`, `plugin_info`. **`resources/` n'y figure pas** —
confirme le risque de fichiers orphelins documenté ci-dessus.

**PROUVÉ — `setIsEnable(1)` arrête le démon mais ne le relance jamais
directement** :

> `core/class/update.class.php`, ligne 471, dans `postInstallUpdate()` :
> `if (is_object($plugin) && $plugin->isActive()) { $plugin->setIsEnable(1); }`
> (appelé seulement si le plugin était déjà actif avant la mise à jour)

> `core/class/plugin.class.php`, `setIsEnable()` (ligne 939), extraits
> (lignes 954-1032) :
> ```php
> $deamonAutoState = config::byKey('deamonAutoMode', $this->getId(), 1);
> config::save('deamonAutoMode', 0, $this->getId());
> ...
> if ($_state == 1) {
>     $this->deamon_stop();
>     $deamon_info = $this->deamon_info();
>     sleep(1);
>     if ($deamon_info['state'] == 'ok') {
>         $this->deamon_stop();
>     }
>     if ($alreadyActive == 1) {
>         $out = $this->callInstallFunction('update');
>     } else { $out = $this->callInstallFunction('install'); }
>     ...
> }
> ...
> if ($deamonAutoState) {
>     config::save('deamonAutoMode', 1, $this->getId());
> }
> ```

`setIsEnable(1)` désactive temporairement `deamonAutoMode`, appelle
`deamon_stop()` (jusqu'à deux fois si besoin), déclenche
`callInstallFunction('update')` (notre `jeedom2ha_update()` ci-dessus), **puis
restaure `deamonAutoMode` à sa valeur précédente — sans jamais appeler
`deamon_start()`**. Le fichier `info.json` déclare bien `"hasOwnDeamon": true`
(fait PROUVÉ par lecture, inchangé), mais cela ne déclenche aucun redémarrage
direct dans ce chemin de code : le redémarrage effectif dépend entièrement de
la surveillance périodique `deamonAutoMode` déjà existante côté Jeedom (le
mécanisme qui relance un démon détecté `nok`), pas d'un appel synchrone au
sein de la mise à jour elle-même. **Conséquence opérationnelle** : après une
mise à jour Market, il peut donc y avoir un délai (durée du cycle de
surveillance `deamonAutoMode`, non chiffrée par cette relecture) avant que le
démon de synchronisation HomeKit (`resources/daemon/main.py`) ne redémarre
réellement — pas une réaction instantanée garantie.

**PROUVÉ — compatibilité `require` vérifiée avant installation, pas après** :

> `core/class/update.class.php`, `doUpdate()`, lignes 330-332 :
> ```php
> if (is_file($cibDir . '/plugin_info/info.json') && is_array($data = json_decode(file_get_contents($cibDir . '/plugin_info/info.json'), true)) && isset($data['require'])) {
>     $vJeedom = jeedom::version();
>     if (version_compare($data['require'], $vJeedom, '>')) {
>         // rrmdir($cibDir) ; installation annulée avant remplacement
>     }
> }
> ```

Le champ `require` de `plugin_info/info.json` (`"4.4"` pour `jeedom2ha`, voir
1.4) est comparé à la version du cœur Jeedom **avant** que le contenu
téléchargé ne remplace quoi que ce soit sur la box : en cas d'incompatibilité,
l'installation est annulée (`rrmdir($cibDir)`) avant tout remplacement. Un
second contrôle équivalent existe côté activation du plugin
(`plugin.class.php::setIsEnable()`, ligne 940 :
`version_compare(jeedom::version(), $this->getRequire()) == -1`), qui bloque
l'activation (pas seulement la mise à jour) si le cœur est trop ancien.

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
- **Gate PROUVÉ (Point C) — validation Jeedom sur instance vierge, délai non
  garanti.** Source directe, contenu réel récupéré via l'API JSON Discourse
  (le rendu HTML de la page est en JS, non lisible par un simple fetch) :

  > Source : https://community.jeedom.com/t/comment-faire-passer-un-pluggin-en-stable/105451
  > (fil réel, contenu récupéré via `community.jeedom.com/.../105451.json`)
  >
  > Mips (2023-04-13) : « tu dois t'assurer que ton plugin s'installe et
  > démarre correctement sur une installation de jeedom vierge »
  >
  > Sekiro, membre de l'équipe de validation (2023-04-14) : « Nous validons
  > les plugins quand notre emploi du temps nous le permet »

  Deux conséquences directes pour `jeedom2ha`, avant toute demande de
  passage en `stable` :
  1. Le plugin doit être testé installation + démarrage du démon sur une
     **instance Jeedom fraîche** ("vierge") — pas seulement sur la box de
     référence, déjà configurée avec des dépendances potentiellement
     masquantes (précédent réel dans le même fil : un module Python manquant
     dans les dépendances déclarées n'a été détecté que sur une VM neuve,
     `pip install` ayant réussi ailleurs à cause d'un module déjà présent
     pour un autre plugin).
  2. `jeedom2ha` déclare `"os": {"min": 11, "max": 12.99}` (voir 1.4) : ce
     test d'installation vierge doit donc être fait sur **Debian 11 ET
     Debian 12** (les deux bornes de compatibilité annoncées), pas une seule.
  3. Le délai de validation par l'équipe Jeedom **n'est pas garanti** ("quand
     notre emploi du temps nous le permet") — à budgéter comme un délai
     inconnu et non négociable dans la planification d'une première
     publication stable, pas comme un SLA.

### Étape 1 — Tag de release sur le commit déployé et validé

```
git tag -a vX.Y.Z <sha-deploye-et-valide> -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

Condition : `<sha-deploye-et-valide>` doit déjà porter un tag `deploy-...`
(preuve terrain que ce SHA tourne réellement sur la box).

### Étape 2 — Promotion `main` → `beta` (décision Alex)

**PROUVÉ (mécanisme obligatoire, pas une convention optionnelle)** : la
promotion **doit** passer par une vraie pull request GitHub `main → beta`,
pas par un `git merge` local suivi d'un `git push origin beta`. Preuve
directe, lecture de `.github/workflows/pr-governance.yml` (job
`routing-policy`, déclenché sur `pull_request_target`) :

```python
elif base == "beta":
    if head != "main":
        fail(f"Promotion invalide: une PR vers beta doit venir de main, pas de '{head}'.")
    print("Promotion valide detectee: main -> beta")
```

Ce contrôle (`PR Routing Policy`) est un **required status check** sur la
branche `beta` (confirmé section « Protection de branche » ci-dessous) : il
ne s'exécute que sur un évènement `pull_request_target`, donc seule une PR
GitHub réelle `main → beta` peut le satisfaire — un `git push` direct ne le
déclenche jamais. Procédure :

```
gh pr create --base beta --head main \
  --title "Promote main to beta: vX.Y.Z" \
  --body "Promotion vX.Y.Z (voir docs/release-market.md §3)"
# revue par Alex, CI verte (PR Routing Policy incluse), puis :
gh pr merge --merge   # stratégie "Create a merge commit" — jamais Squash ni Rebase
```

(Cohérent avec le précédent réel PR #73/#74 et `docs/git-strategy.md`, qui
exige un commit de merge de promotion explicite — pas de squash, pas de
fast-forward.)

**Invariant obligatoire après la fusion — « ARBRE publié = arbre du tag
déployé »** : une fois la PR de promotion fusionnée, vérifier que le
contenu de `beta` est strictement identique à celui du tag `vX.Y.Z` (les
SHA diffèrent forcément, un commit de merge étant créé, mais l'arbre de
fichiers doit être byte-identique) :

```
git fetch origin beta
git diff --quiet vX.Y.Z origin/beta   # DOIT être silencieux (exit 0)
```

Si cette commande échoue (exit non nul), la promotion **n'est pas
conforme** et ne doit pas être considérée terminée — investiguer avant de
passer à l'étape suivante. Précédent réel vérifié pour la dernière
promotion connue (PR #73, tag `v1.1.0` = `166cb7b`, HEAD beta post-merge =
`1a149ca`) :

```
$ git diff --quiet 166cb7b 1a149ca && echo "IDENTIQUE (exit 0)"
IDENTIQUE (exit 0)
```

### Étape 3 — Promotion `beta` → `stable` (décision Alex, après validation beta)

Même mécanique obligatoire (PR réelle, pas de push direct), une fois `beta`
validée (retours utilisateurs canal beta, délai de validation à la
discrétion d'Alex). Preuve directe, même fichier :

```python
elif base == "stable":
    if head != "beta":
        fail(f"Promotion invalide: une PR vers stable doit venir de beta, pas de '{head}'.")
    print("Promotion valide detectee: beta -> stable")
```

```
gh pr create --base stable --head beta \
  --title "Promote beta to stable: vX.Y.Z" \
  --body "Promotion vX.Y.Z (voir docs/release-market.md §3)"
# revue par Alex, CI verte, puis :
gh pr merge --merge
```

Puis la même vérification obligatoire de l'invariant :

```
git fetch origin stable
git diff --quiet vX.Y.Z origin/stable   # DOIT être silencieux (exit 0)
```

### Protection de branche `beta`/`stable` — PROUVÉ (lecture directe, lecture seule)

```
$ gh api repos/alexsahut/jeedom2ha/branches/beta/protection
$ gh api repos/alexsahut/jeedom2ha/branches/stable/protection
```

Résultat réel (identique pour `beta` et `stable`) :
- `required_status_checks.contexts` inclut `"PR Routing Policy"`,
  `"PR Metadata Policy"`, tests Python/Node — **la PR de promotion doit
  passer cette CI** pour pouvoir être fusionnée dans l'UI GitHub standard.
- `required_pull_request_reviews.required_approving_review_count: 0` — une
  review formelle **n'est pas obligatoire** (0 approbation exigée), mais la
  présence même de cette règle empêche un `git push` direct non-admin sur
  ces branches : le changement doit transiter par une PR.
- `enforce_admins.enabled: false` — **nuance importante, à ne pas ignorer** :
  ces règles (y compris `PR Routing Policy`) ne s'appliquent **pas** à un
  compte administrateur du repo. Un push direct ou une fusion sans review
  reste donc techniquement possible pour Alex (admin), même s'il contredit
  la procédure documentée ici. Ce document décrit la procédure **à suivre**,
  pas une garantie technique absolue contre un contournement volontaire par
  un administrateur.
- `allow_force_pushes.enabled: false`, `allow_deletions.enabled: false` :
  ces deux protections-là s'appliquent bien à tous, y compris aux
  administrateurs (elles ne dépendent pas de `enforce_admins`).

**Écart avec la commande brute demandée initialement** : une publication par
« fast-forward » brut (`git push origin <sha>:refs/heads/beta`) déplacerait
le pointeur de branche sans laisser de trace de commit de promotion, **et
serait de toute façon rejetée par la protection de branche pour un compte
non-admin** (voir ci-dessus). Ce
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

### Cohabitation `deploy-to-box.sh` (rsync) vs mise à jour Market — PROUVÉ (les deux mécanismes)

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

**PROUVÉ (mécanisme Market, relecture directe du cœur Jeedom — voir 1.6)** :
la mise à jour Market **préserve également** `data/`, mais par un mécanisme
différent du nôtre : ce n'est pas une exclusion ciblée (`--exclude 'data/'`),
c'est une conséquence de la fusion additive de `rmove(..., false)` (jamais de
`rrmdir($dst)`) combinée au fait que `data/` n'apparaît pas dans la liste
fermée de nettoyage 7 jours (`3rdparty`, `3rparty`, `desktop`, `mobile`,
`core`, `docs`, `install`, `script`, `plugin_info` — voir 1.6). Les deux
mécanismes aboutissent donc au même résultat pratique (`data/` préservé) par
des chemins de code totalement différents — ce n'est plus une hypothèse à
vérifier sur le terrain, c'est prouvé par lecture croisée des deux codes
sources.

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
concrètement, avec un plugin tiers ayant déjà plusieurs versions stables
publiées (il n'existe pas de box de test dédiée pour ce projet — voir note
ci-dessous — cette vérification se ferait donc sur une box Jeedom
quelconque, y compris potentiellement la box de référence de la maison, une
fois son canal Market basculé sur un plugin tiers de test) : vérifier si
l'UI Market propose un choix de version ou uniquement "installer la
dernière".

**Note (Point F, pas de box de test dédiée)** : ce projet n'a pas de box de
test Jeedom distincte de la box de référence de la maison — c'est un choix
explicite d'Alex. Toute vérification « terrain » mentionnée dans ce document
(comportement Market réel, préservation de fichiers, redémarrage du démon,
contenu livré) se ferait donc, le cas échéant, sur la **box de production
réelle de la maison**, après bascule explicite de son canal Market vers
`beta` — et uniquement sur décision explicite d'Alex, jamais une action
unilatérale de `clawcode`/ClaudeBox.

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

**Point E — script corrigé.** La version précédente de ce script avait
quatre défauts identifiés et corrigés ici :
1. `git diff --stat ... || true` ne faisait jamais échouer le script même en
   cas de divergence (le `|| true` avale systématiquement le code de sortie)
   — remplacé par `git diff --quiet`, qui fait échouer le script
   (`set -euo pipefail` + `exit 1` explicite) en cas de différence réelle.
2. Le contrôle « candidat ancêtre ou égal » (`--is-ancestor`) était trop
   laxiste pour le cas de la 1ère publication stable (section 4), qui exige
   une **égalité stricte** avec le SHA en prod, pas seulement une ascendance
   — remplacé par une comparaison stricte de SHA.
3. Le script se fiait au dernier tag `deploy-*` comme source de vérité, or
   ce tag peut être en retard sur un rollback : **incident réel constaté le
   2026-09-27 à 15:35**, où le dernier tag `deploy-*` pointait sur `d7db48a`
   alors que la box avait déjà été rollback-ée en `0.2.0` par
   `deploy-to-box.sh --rollback` sans nouveau tag `deploy-*` associé au
   rollback lui-même — remplacé par une lecture **directe** du fichier
   `VERSION` sur la box via SSH en lecture seule (`cat`, aucune écriture).
4. Le candidat était implicitement `HEAD` — remplacé par un paramètre
   explicite obligatoire (`${1:?candidat requis}`), avec vérification
   croisée que `pluginVersion` (`info.json`) correspond au tag `vX.Y.Z` visé
   s'il existe déjà.

Script reproductible, **réexécuté réellement dans ce worktree** au moment de
la rédaction de cette révision (sortie collée telle quelle ci-dessous, et
également collée dans le corps de la PR) :

```bash
#!/usr/bin/env bash
# Lecture seule stricte : ne crée aucun tag, ne pousse aucune branche,
# ne touche ni au Market ni à la box (une seule commande SSH en lecture,
# `cat` du fichier VERSION, aucune écriture).
set -euo pipefail

CANDIDATE_REF="${1:?candidat requis : SHA ou ref à vérifier, ex. \$(git rev-parse HEAD)}"
CANDIDATE_SHA="$(git rev-parse "${CANDIDATE_REF}")"
echo "SHA candidat : ${CANDIDATE_SHA}"

# 1. pluginVersion du candidat cohérent avec un éventuel tag vX.Y.Z existant.
PLUGIN_VERSION="$(git show "${CANDIDATE_SHA}:plugin_info/info.json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["pluginVersion"])')"
echo "pluginVersion du candidat : ${PLUGIN_VERSION}"
EXPECTED_TAG="v${PLUGIN_VERSION}"
if git rev-parse "${EXPECTED_TAG}" >/dev/null 2>&1; then
  TAG_SHA="$(git rev-parse "${EXPECTED_TAG}")"
  if [ "${TAG_SHA}" = "${CANDIDATE_SHA}" ]; then
    echo "[OK] le tag ${EXPECTED_TAG} existe déjà et pointe exactement sur le candidat"
  else
    echo "[ECHEC] le tag ${EXPECTED_TAG} existe mais pointe sur ${TAG_SHA} (candidat = ${CANDIDATE_SHA})"
    exit 1
  fi
else
  echo "[INFO] le tag ${EXPECTED_TAG} n'existe pas encore (attendu avant la 1ère publication de cette version)"
fi

# 2. SHA réellement en place sur la box, lu DIRECTEMENT (source de vérité) :
#    jamais déduit du dernier tag deploy-, qui peut être en retard sur un
#    rollback (incident constaté le 2026-09-27 15:35 : dernier tag deploy-
#    pointait sur d7db48a alors que la box tournait déjà en 0.2.0 après
#    --rollback).
BOX_VERSION_RAW="$(ssh -o BatchMode=yes -o ConnectTimeout=5 asahut@192.168.1.21 'cat /var/www/html/plugins/jeedom2ha/VERSION' 2>/dev/null || true)"
if [ -z "${BOX_VERSION_RAW}" ]; then
  echo "[ECHEC] impossible de lire VERSION sur la box (SSH ou fichier absent)"
  exit 1
fi
echo "--- VERSION lu sur la box (asahut@192.168.1.21, lecture seule) ---"
echo "${BOX_VERSION_RAW}"
BOX_SHA="$(echo "${BOX_VERSION_RAW}" | sed -n 's/^sha=//p')"
echo "SHA réellement déployé sur la box (source de vérité) : ${BOX_SHA}"

# 3. Egalité STRICTE candidat <-> box, exigée pour la 1ère publication
#    (section 4 : le premier `stable` publié DOIT être exactement le code
#    en prod, pas un ancêtre — "ancêtre ou égal" est trop laxiste ici).
if [ "${CANDIDATE_SHA}" = "${BOX_SHA}" ]; then
  echo "[OK] candidat strictement identique au SHA déployé sur la box"
else
  echo "[ECHEC] candidat (${CANDIDATE_SHA}) différent du SHA déployé sur la box (${BOX_SHA})"
  echo "--- git diff --quiet candidat vs SHA déployé (diagnostic) ---"
  if git diff --quiet "${CANDIDATE_SHA}" "${BOX_SHA}" 2>/dev/null; then
    echo "[INFO] même contenu malgré des SHA différents — à investiguer avant de continuer"
  else
    echo "[ECHEC] contenu également différent"
  fi
  exit 1
fi

echo "Vérification à blanc terminée : candidat conforme, strictement identique à la box."
```

### Sortie réelle obtenue — cas conforme (réexécuté le 2026-09-27, candidat = `origin/main`)

```
$ git fetch origin --quiet
$ bash verify-release-candidate.sh origin/main
SHA candidat : dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e
pluginVersion du candidat : 0.3.0
[INFO] le tag v0.3.0 n'existe pas encore (attendu avant la 1ère publication de cette version)
--- VERSION lu sur la box (asahut@192.168.1.21, lecture seule) ---
version=0.3.0
sha=dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e
deployed_at=2026-09-27T13:36:40Z
git_status=clean
SHA réellement déployé sur la box (source de vérité) : dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e
[OK] candidat strictement identique au SHA déployé sur la box
Vérification à blanc terminée : candidat conforme, strictement identique à la box.
$ echo "EXIT_CODE=$?"
EXIT_CODE=0
```

### Sortie réelle obtenue — cas d'échec volontaire (réexécuté le 2026-09-27, candidat = `v1.1.0`, ancien SHA)

```
$ bash verify-release-candidate.sh v1.1.0
SHA candidat : e1325f05df16e70bf53f717a7c843f809521b3f5
pluginVersion du candidat : 0.1
[INFO] le tag v0.1 n'existe pas encore (attendu avant la 1ère publication de cette version)
--- VERSION lu sur la box (asahut@192.168.1.21, lecture seule) ---
version=0.3.0
sha=dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e
deployed_at=2026-09-27T13:36:40Z
git_status=clean
SHA réellement déployé sur la box (source de vérité) : dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e
[ECHEC] candidat (e1325f05df16e70bf53f717a7c843f809521b3f5) différent du SHA déployé sur la box (dd304f17fc3d1b9069ba9c14770a9b07a67d6d0e)
--- git diff --quiet candidat vs SHA déployé (diagnostic) ---
[ECHEC] contenu également différent
$ echo "EXIT_CODE=$?"
EXIT_CODE=1
```

Interprétation : le premier cas confirme que le SHA candidat (`origin/main`,
`dd304f1...`) est exactement le SHA déjà déployé et validé sur la box —
c'est le cas attendu pour une première publication stable conforme à la
section 4. Le second cas confirme que le script **échoue bien avec un code
de sortie non nul** dès que le candidat diffère réellement de la box — le
défaut n°1 ci-dessus (`|| true` qui masquait les échecs) est corrigé.
Aucune commande de ce script n'écrit quoi que ce soit : ni tag, ni branche,
ni Market, ni box (une seule commande SSH, en lecture seule).
