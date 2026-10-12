# Story 23.5 — Fiche d'options de licence (pour décision d'Alexandre)

- **Statut :** fiche d'arbitrage, en attente de décision écrite d'Alexandre. Aucun fichier de licence, métadonnée ou README n'est modifié par cette fiche.
- **Date de rédaction :** 2026-10-12 (base : `main` = `78cf903`).
- **Avertissement :** ce document n'est **pas un avis juridique**. Il recense des faits du dépôt et des options à instruire. Toute conclusion juridique (compatibilité, effet sur les versions publiées, obligations Market) doit être confirmée par une consultation qualifiée et/ou par le support Jeedom avant action.
- **Étiquettes :** **CONSTATÉ** = relevé dans le dépôt par commande reproductible (section 6). **NON RELU** = source externe citée à vérifier ; elle n'a pas pu être consultée lors de la rédaction (réseau limité : `gnu.org` et `doc.jeedom.com` injoignables depuis la session). **HYPOTHÈSE** = à lever.

## 1. Constat de l'écart (CONSTATÉ, dépôt au 2026-10-12)

Trois états de licence coexistent, dont deux sont déclarés dans les métadonnées et le README, et un troisième dans les en-têtes de code.

| # | Emplacement | Licence affichée | Remarque |
|---|---|---|---|
| 1 | `LICENSE` (281 lignes) | Texte de la **GNU GPL version 2, juin 1991** | La mention « any later version » n'y figure que dans le mode d'emploi du texte standard (annexe), pas comme choix du dépôt. |
| 2 | `plugin_info/info.json` l.10 | `"licence": "AGPL"` | Valeur sans numéro de version (« AGPL » seul). |
| 3 | `README.md` l.167 | `Licence \| AGPL` | Idem, sans version. |
| 4 | En-têtes de `core/class/jeedom2ha.class.php`, `plugin_info/{install,pre_install,configuration}.php` (l.5-6) | « GNU General Public License … **either version 3** of the License, or (at your option) any later version » | GPL v3-ou-ultérieure, ni GPL-2.0 ni AGPL. |
| 5 | Documents de planification (`_bmad-output/planning-artifacts/epics.md` l.94, rapports de readiness 2026-03-12 et 2026-03-13) | « GPL v3 pour le plugin Jeedom » | Intention de cadrage initiale, antérieure à l'écart. |

Autres constats :

- `pyproject.toml` ne déclare aucun champ de licence ; aucun identifiant SPDX ni en-tête de copyright n'a été trouvé dans les fichiers Python/JS.
- L'historique local est partiel (dépôt shallow : premier commit visible `3f14b89`, 2026-10-01, pour `LICENSE`, `info.json` et `README.md`). **La date d'introduction réelle de chaque état n'est donc pas établie** ; cela se lève avec un clone complet (`git fetch --unshallow` puis `git log --follow -- LICENSE plugin_info/info.json README.md`).
- Le champ `licence` est obligatoire dans `info.json` selon la story A3 (`_bmad-output/implementation-artifacts/stories/a3-conformite-market.md` l.17, qui cite `doc.jeedom.com/fr_FR/dev/structure_info_json` — NON RELU ici).

## 2. Versions et canaux déjà publiés (CONSTATÉ au 2026-10-12)

| Référence | Date | `pluginVersion` | `info.json` licence | `LICENSE` | En-têtes PHP |
|---|---|---|---|---|---|
| tag `v1.1.0` (`166cb7b`) | 2026-04-10 | `0.1` | AGPL | GPL-2.0 | GPL v3+ |
| branche `stable` (`dfd58d6`) | 2026-04-10 | `0.1` | AGPL | GPL-2.0 | — |
| branche `beta` (`1a149ca`) | 2026-04-10 | `0.1` | AGPL | GPL-2.0 | — |
| `main` (`78cf903`) | 2026-10-12 | `0.3.0` | AGPL | GPL-2.0 | GPL v3+ |

- L'écart existe donc **depuis le premier état publié observable** ; il n'a pas été introduit récemment.
- Les tags du dépôt distant sont `v1.1.0`, `story-4.3-…`, `bmad-v1.1-…`, `backup/…` et des tags `deploy-*` (internes). Aucune autre release `v*` n'est visible.
- **À confirmer par Alexandre (HYPOTHÈSE) :** si une version a réellement été distribuée via le Market (et à qui), ou si seules ces branches/tag GitHub existent. Cela change la portée de la question « versions déjà publiées ».
- **À confirmer :** si des tiers ont contribué du code (aucune contribution externe n'a été recherchée ici). Le titulaire des droits sur chaque partie conditionne la possibilité de changer de licence.

## 3. Comparaison des options

Légende : ce qui suit est une grille de lecture, à valider ; les références officielles à relire sont en section 5.

### Option A — AGPL-3.0 (ou AGPL-3.0-or-later)

- **Copyleft fort, avec clause réseau (§13)** : un tiers qui modifie le logiciel et le propose aux utilisateurs via un réseau doit leur offrir le code source modifié (NON RELU, texte AGPLv3 §13).
- Redistribution : source obligatoire, mêmes termes pour les œuvres dérivées.
- **Cohérence :** alignerait `info.json` et README (déjà « AGPL »). Il faudrait remplacer `LICENSE` (GPL-2.0 → AGPL-3.0) et les en-têtes PHP (GPL v3+).
- **Pertinence réelle de la clause réseau pour ce plugin :** le démon tourne chez l'utilisateur (box locale), il n'est pas offert en service à des tiers ; l'apport pratique de l'AGPL sur la GPL est donc limité (HYPOTHÈSE à confirmer).
- **Contrainte :** le plugin s'exécute dans Jeedom, dont le cœur est sous GPL (en-têtes « Jeedom » des fichiers PHP du plugin). La compatibilité d'une combinaison AGPL-3.0 avec le cœur Jeedom doit être vérifiée (HYPOTHÈSE ; voir §5, point sur la compatibilité GPLv3 ↔ AGPLv3, NON RELU).

### Option B — GPL-3.0-or-later

- Copyleft fort sans clause réseau. **Cohérent avec les en-têtes PHP existants** et avec l'intention de planification (« GPL v3 pour le plugin »).
- Il faudrait remplacer `LICENSE` (GPL-2.0 → GPL-3.0) et corriger `info.json` et README (« AGPL » → « GPL-3.0-or-later »). C'est le plus petit écart aux en-têtes de code, mais le plus grand à l'affichage public actuel (`info.json`, README).
- Les en-têtes GPL v3+ du plugin proviennent du gabarit de fichiers de plugin Jeedom (HYPOTHÈSE sur l'origine) ; ce n'est pas une règle Market établie (règle Market : NON RELU).

### Option C — GPL-2.0-only / GPL-2.0-or-later (maintenir `LICENSE`)

- Ne demande **aucun changement de `LICENSE`** : on aligne `info.json`, README et en-têtes PHP sur GPL-2.0 (ou GPL-2.0-or-later).
- Mais les en-têtes PHP actuels disent « version 3 ou ultérieure » : il faudrait les réécrire (le détenteur des droits peut le faire s'il est seul auteur, sous réserve de la section 2).
- Une GPL-2.0-**only** est connue pour être non compatible avec la GPLv3 en l'état (NON RELU, FAQ GNU) : en cas de réutilisation de code GPLv3-seul, ce serait bloquant.

### Option D — Licence propriétaire / source-disponible (EULA, non libre)

- Permet de verrouiller redistribution et usage ; nécessite de s'assurer que **toutes** les parties sont possédées ou sous licence compatible (dépendances Python, librairies JS/PHP incluses, code Jeedom copié depuis le gabarit de plugin).
- **HYPOTHÈSE à lever :** les règles du Market imposent-elles une licence libre pour un plugin déposé sur le dépôt Jeedom ? Les plugins payants existent sur le Market (les tags `free`/`paid` figurent sur la page de publication, source indexée non relue), mais les conditions de licence associées ne sont pas établies ici.
- Contradictoire avec les en-têtes GPL du code actuel et avec le cœur Jeedom (GPL) si le code du plugin s'y lie ; à instruire.

### Option E — Double licence (libre + commerciale)

- Le titulaire des droits publie le code sous une licence libre (A, B ou C) **et** une licence commerciale distincte pour les acheteurs qui ne veulent pas du copyleft.
- Exige la maîtrise de tous les droits d'auteur (pas de contributeur tiers non cédant) et des dépendances compatibles avec cette stratégie. Complexité de gestion non négligeable.

### Tableau de synthèse

| Critère | A AGPL-3.0 | B GPL-3.0+ | C GPL-2.0 | D Propriétaire | E Double |
|---|---|---|---|---|---|
| Alignement `info.json` actuel | oui | non | non | non | selon cas |
| Alignement `LICENSE` actuel | non | non | oui | non | non |
| Alignement en-têtes PHP actuels | non | oui | non | non | non |
| Fichiers à modifier (ordre de grandeur) | `LICENSE` + en-têtes + README/info précis | `LICENSE` + `info.json` + README | en-têtes + `info.json` + README | tout + EULA | tout + contrat |
| Copyleft | fort + réseau | fort | fort | aucun | selon branche libre |
| Vente sur le Market | à confirmer (§4) | à confirmer | à confirmer | à confirmer | à confirmer |
| Risque d'incompatibilité avec cœur Jeedom (GPL) | à vérifier | faible (HYPOTHÈSE) | à vérifier si GPL-2.0-only | élevé (HYPOTHÈSE) | à vérifier |

## 4. Implications pour un plugin payant sur le Jeedom Market

- **Vendre n'est pas exclu par un copyleft** : la GPL/AGPL autorise de facturer la distribution ; en revanche, l'acheteur reçoit les mêmes libertés (redistribuer le code, y compris gratuitement) (NON RELU, FAQ GNU, entrée « DoINeedToBeFree »/vente de copies). Le modèle économique repose alors sur le service, le support, la commodité et les mises à jour, pas sur l'exclusivité du code.
- **Ce que les règles du Market imposent à un plugin payant (licence imposée ? commission ? accès aux sources ?) n'est pas établi.** Les pages `doc.jeedom.com/fr_FR/dev/publication_plugin` et `…/structure_info_json` n'ont pas pu être consultées ; un extrait indexé signale l'existence des tags `free`/`paid`. **Action attribuée à Alexandre :** relever les conditions auprès de la documentation développeur ou du support Jeedom (liste de questions en §7).
- Le champ `licence` d'`info.json` est une chaîne de texte libre aux yeux du dépôt (aucune validation locale) ; sa valeur exacte attendue par le Market est à confirmer.
- Si le dépôt GitHub est public et la licence libre, rien n'empêche techniquement un tiers de proposer gratuitement le code ; l'option D ou E répond à ce risque mais impose les prérequis de la section 2.

## 5. Traitement des versions déjà publiées (AGPL/GPL-2.0)

À instruire, aucune conclusion ici :

1. **Ce qui a été distribué est régi par ce qui accompagnait la distribution.** Les exemplaires déjà reçus (tag `v1.1.0`, branches `stable`/`beta`, éventuels téléchargements Market) contenaient simultanément un `LICENSE` GPL-2.0 et une métadonnée AGPL : la licence applicable à ces exemplaires est précisément ce qu'une consultation juridique doit déterminer (HYPOTHÈSE).
2. **Le titulaire des droits peut en principe publier les versions futures sous une autre licence** s'il détient seul les droits, mais cela ne retire pas rétroactivement les droits déjà accordés sur les exemplaires déjà distribués sous une licence libre (NON RELU, FAQ GNU sur le changement de licence par le titulaire ; à confirmer juridiquement).
3. **Options de traitement historique** (à choisir après avis) : (a) ne rien faire sur l'historique et appliquer la licence choisie à partir de la prochaine version, avec une mention explicite dans le changelog ; (b) publier une note de clarification pour les versions existantes (par ex. « les versions ≤ vX sont aussi disponibles sous GPL-2.0 ») ; (c) republier une version corrective portant la bonne licence. Aucune de ces actions n'est lancée par cette fiche.
4. **Tags et branches :** modifier ou supprimer `v1.1.0`, `stable` ou `beta` est une action historique hors périmètre ; elle exigerait une décision et une action d'Alexandre (critère d'acceptation 4 de la story).

## 6. Sources et reproductibilité

Constats du dépôt (commandes exécutées le 2026-10-12 sur `main` = `78cf903` ; les tags/branches distantes ont été récupérés par `git fetch origin tag v1.1.0` et `git fetch origin stable beta`) :

```bash
sed -n 1,3p LICENSE
grep -n licence plugin_info/info.json
grep -n "Licence" README.md
grep -n "version 3" core/class/jeedom2ha.class.php plugin_info/*.php
git show v1.1.0:plugin_info/info.json | grep -E 'licence|pluginVersion'
git show origin/stable:LICENSE | sed -n 1,2p   # idem origin/beta
git ls-remote --tags origin | grep -v deploy-
git rev-parse --is-shallow-repository          # true
```

Références externes **à relire avant décision** (NON RELU lors de la rédaction) :

- GNU, « GNU Affero General Public License v3 », §13 (Remote Network Interaction) : <https://www.gnu.org/licenses/agpl-3.0.html>
- GNU, « Frequently Asked Questions about the GNU Licenses » (vente de copies, compatibilité GPLv2/GPLv3, relicenciement par le titulaire) : <https://www.gnu.org/licenses/gpl-faq.html>
- GNU, « Various Licenses and Comments about Them » (compatibilité AGPLv3/GPLv3, constatée dans un résultat de recherche du 2026-10-12 sur <https://www.gnu.org/l/license-list.html>)
- Jeedom, « Publication d'un plugin » : <https://doc.jeedom.com/fr_FR/dev/publication_plugin> (extrait indexé : tags `free`/`paid`)
- Jeedom, « Structure du fichier info.json » : <https://doc.jeedom.com/fr_FR/dev/structure_info_json>
- Dépôt : `docs/release-market.md` (procédure Market interne, section 1).

## 7. Décisions et informations demandées à Alexandre

Aucun changement de licence ne sera appliqué avant réponse écrite à ces points.

1. **Licence cible** : A (AGPL-3.0), B (GPL-3.0+), C (GPL-2.0), D, E, ou autre.
2. **Modèle commercial visé** : plugin payant sur le Market (oui/non), gratuit, ou les deux ; niveau d'exclusivité souhaité sur le code.
3. **Titularité** : êtes-vous l'unique titulaire des droits sur le code du plugin ? Des contributions tierces (code, assets, traductions) ou du code copié du gabarit Jeedom sont-ils présents ?
4. **Publication réelle** : une version a-t-elle déjà été distribuée via le Market, et à quels utilisateurs ?
5. **Conditions Market** : à relever auprès du support Jeedom ou de la documentation développeur :
   - Le Market impose-t-il une licence ou une famille de licences pour un plugin payant ?
   - Quelle valeur exacte attend le champ `licence` ?
   - Les sources doivent-elles rester publiques ?
   - Y a-t-il une commission ou un accord à signer ?
6. **Consultation juridique** : souhaitez-vous la solliciter (recommandé pour les points de la section 5) ? Action attribuée à Alexandre.
7. **Traitement historique** : option 5.3 (a), (b) ou (c).

## 8. Suite prévue, après décision uniquement

Le critère d'acceptation 3 de la story (alignement `LICENSE`, `info.json`, README, en-têtes, documentation, métadonnées Market, plus un test de cohérence automatisé) sera traité dans une PR distincte après décision écrite d'Alexandre.
