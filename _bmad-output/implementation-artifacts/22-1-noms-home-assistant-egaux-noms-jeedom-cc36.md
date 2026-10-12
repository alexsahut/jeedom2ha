# Story 22.1 : Noms Home Assistant = noms Jeedom (CC-36)

Status: review

> **Statut : `ready-for-dev` (2026-10-12).** Alexandre a tranché les questions le 2026-10-12 vers 05:50, relayé par ClaudeBox : **Q1 A, Q2 A, Q3 A, Q4 A, Q5 A, Q6 A, Q7 B, QD deux stories** (voir « Décisions d'Alexandre »). `ready-for-dev` est accordé par ClaudeBox au nom de cette décision. Brouillon de cadrage rédigé par une session cloud déléguée (documentaire, lecture seule : aucun accès box, Home Assistant ni secret). Les pointeurs `fichier:ligne` sont pris sur `main` à `ab3a854`. **R1 (ClaudeBox, 2026-10-12, relevé de terrain en lecture seule vers 04:30)** : F4 et H6 sont des faits (HA 2026.9.4). Aucun nom réel d'équipement, de pièce, de scénario ou de personne dans ce fichier (CC-48) : seuls des identifiants.

## Story

En tant qu'utilisateur qui pilote sa maison par la voix et par des tableaux de bord dans Home Assistant,
je veux que chaque appareil porte le nom de l'équipement Jeedom et que la pièce de Jeedom soit proposée à sa création,
afin que « le nom et la pièce Jeedom font foi partout » (décision d'Alexandre, 2026-10-01 18:21) et qu'Assist reconnaisse les noms que je connais.

**Parcours : démon uniquement** (discovery MQTT). Aucun écran ne change. Preuve terrain obligatoire par l'humain : inventaire des registres HA avant/après.

## Décisions d'Alexandre (2026-10-12, vers 05:50, relayées par ClaudeBox)

Toutes les recommandations sont retenues, avec **Q7 B**. `ready-for-dev` est accordé par ClaudeBox au nom de cette décision.

- **Q1 A** — `device.name` = nom de l'équipement Jeedom (accents compris), identique pour toutes les entités de l'équipement.
- **Q2 A** — entité unique : nom de l'équipement ; plusieurs entités : nom de la commande.
- **Q3 A** — un renommage Jeedom atteint HA au sync suivant (rescan, redémarrage du démon, « Republier ») ; documenté ; aucun hook `postSave`.
- **Q4 A** — `suggested_area` envoyée à chaque sync ; documenté que HA ne l'applique qu'à la création de l'appareil.
- **Q5 A** — noms et pièces choisis à la main dans HA font foi ; aucun rapport, aucune détection.
- **Q6 A** — les `entity_id` et noms existants ne sont pas touchés ; pas de recréation proposée par cette story.
- **Q7 B** — pour toute entité **nouvelle ou recréée**, `entity_id` technique stable fixé par `default_entity_id`, dont la valeur est **exactement** celle d'`object_id` que le démon envoie aujourd'hui (F10) pour cette entité, préfixée du domaine : `<domaine>.<object_id actuel>`. C'est la forme des 41 entités d'avant le 2026-05-06. Les `entity_id` existants ne changent pas. Conséquence : les cartes de tableau de bord citent l'`entity_id`, pas le nom affiché ; seule la voix (Assist) s'appuie sur le nom. Avec B, automatisations, scripts et cartes survivent à une recréation ; une entité actuellement à `entity_id` dérivé des noms (les 306 créées depuis le 2026-05-06) qui serait recréée prendrait, une fois, la forme technique.
- **QD** — deux stories, 22-1 puis 22-2.

## Contexte

- **Audit du 2026-10-02** (parité, hors dépôt) : sur 94 équipements exposés à HomeKit et projetés dans HA, 44 portaient un nom différent du nom Jeedom (`ha_name` du cache). Un renommage dans Jeedom n'est pas republié.
- **Mesure du 2026-10-12 vers 03:30** (registres de HA et page du plugin) : 91 appareils `jeedom2ha_<eq_id>` ; **62** au nom exact de l'équipement Jeedom, **29** à un autre nom : 67, 174, 206, 207, 234, 235, 312, 456, 457, 459, 468, 475, 506, 519, 520, 521, 522, 523, 553, 579, 580, 583, 585, 594, 603, 628, 631, 632, 633. 1 seul appareil renommé à la main (`name_by_user`). 347 entités jeedom2ha dont 84 boutons de scénario ; 37 entités renommées à la main, 23 avec une pièce choisie à la main, aucune avec alias.
- **Hors périmètre :** parité HomeKit (CC-33, epic suivant), chantier Market, compteurs et lisibilité (22.2), tout accès box/HA. (`object_id` / `default_entity_id` n'est plus hors périmètre : voir H6 et Q7.)

## Faits relevés dans le code (lecture seule, `main` `ab3a854`)

| # | Fait | Pointeur |
|---|---|---|
| F1 | Le nom d'une entité et le nom de l'appareil viennent du **même champ** `MappingResult.ha_name`. | `resources/daemon/models/mapping.py:147`, `discovery/publisher.py:421` (appareil), `:449` (entité lumière), `:492`, `:539`, `:580`, `:617`, `:646`, `:681`, `:715` |
| F2 | Mappers « entité unique » (lumière, volet, switch, capteur, repli, bouton d'équipement) : `ha_name = eq.name` (nom de l'équipement Jeedom, accents conservés). | `mapping/light.py:157,193,225,254,322` ; `cover.py:138,174,215,293` ; `switch.py:159,227,271` ; `sensor.py:228,253` ; `fallback.py:35,50` ; `button.py:34` |
| F3 | Mappers « par commande » : `ha_name = cmd.name` (nom de la **commande**) : capteurs multiples, capteurs binaires, switch construit sur une commande d'état. | `mapping/sensor.py:290` ; `binary_sensor.py:124` ; `switch.py:305` |
| F4 | **Tous** les payloads d'un même équipement portent le même `device.identifiers` (`jeedom2ha_<eq_id>`) mais `device.name = mapping.ha_name` **propre à chaque entité**. Quand un équipement a une entité nommée d'après une commande, plusieurs noms d'appareil concurrents sont envoyés ; le dernier reçu par HA l'emporte. **Confirmé sur le terrain (R1, 12/10)** : pour **chacun** des 29 appareils, le nom de l'appareil dans HA est égal au nom de découverte (`original_name`) de l'une de ses entités, donc à un nom de commande. 16 de ces 29 appareils n'ont qu'une entité (nommée d'après une commande, F3) ; 13 en ont plusieurs ; au total **149 entités**. | `publisher.py:404-430` |
| F5 | Le **bouton de scénario** : appareil et entité nommés d'après le scénario (`scenario.name`), identifiant d'appareil = `ha_unique_id` du scénario ; pas de pièce (`suggested_area=None`). Hors écart mesuré. | `mapping/button.py:55-56`, `publisher.py:411-415` |
| F6 | `suggested_area` = nom de l'**objet Jeedom** de l'équipement, ou absent. Envoyé dans le bloc `device` à chaque publication quand il existe. | `models/topology.py:213-218`, `publisher.py:427-428` |
| F7 | **Chaque sync republie la configuration complète** de toute entité dont la décision est « publier », sans comparer à l'état précédent : un nom Jeedom modifié part donc à MQTT au sync suivant. La détection de renommage (`_detect_lifecycle_changes`) **ne fait que journaliser** (« rename détecté », « area change »). | `transport/http_server.py:1024-1107` (journal), `:1620-1664` (publication à chaque sync) |
| F8 | Ce qui **déclenche** un sync : le démarrage du démon (amorçage) et les actions de l'interface (rescan, Publier/Republier). Les hooks d'équipement du plugin sont vides : **aucun sync à l'enregistrement d'un équipement dans Jeedom**. C'est pourquoi un renommage n'apparaît pas dans HA tant qu'aucun sync n'a eu lieu. | `core/class/jeedom2ha.class.php:288-302` (amorçage), `:857-870` (`postUpdate`/`postSave` vides) |
| F9 | Le cache disque garde `ha_name` et `suggested_area` par équipement pour détecter ces changements au boot (journal seulement). | `cache/disk_cache.py:128-134,190-191` |
| F10 | Les payloads envoient toujours `object_id` (`jeedom2ha_<eq_id>` ou `…_<cmd_id>`). **Il n'est plus appliqué par HA 2026.9.4** (voir H6 : l'`entity_id` des entités créées depuis le 2026-05-06 dérive des noms). | `publisher.py:451,494,541,582,619,648,683,717` |

## Ce que fait Home Assistant (non vérifié par cette session)

La documentation officielle de HA n'était pas accessible depuis la session (réseau restreint). Seules des sources secondaires ont été lues : le billet développeur « change naming MQTT entities » (2023-07-21) et un fil de la communauté. À **confirmer sur la documentation officielle et sur le terrain** avant de figer les AC :

- **H1 (source secondaire).** Depuis HA 2023.8, les entités MQTT ont `has_entity_name = True` : le nom affiché est « nom de l'appareil + nom de l'entité ». Un `name` d'entité identique au nom de l'appareil est dédoublonné (avec un message de réparation). Conséquence : pour une entité unique, `name = device.name = nom Jeedom` s'affiche comme le nom de l'appareil ; mais pour un équipement multi-entités, le nom affiché d'une entité dépend du **nom de l'appareil**.
- **H2 (hypothèse).** Un nom d'appareil ou d'entité choisi à la main dans HA (`name_by_user`) l'emporte sur le nom de la découverte, qui n'est plus appliqué qu'à `original_name`. Vérification : renommer à la main une entité de test, republier, relire `name` / `original_name` dans le registre.
- **H3 (hypothèse).** HA ne recalcule pas l'`entity_id` d'une entité déjà enregistrée quand son nom de découverte change. Vérification : renommer un équipement de test dans Jeedom, rescanner, relever l'`entity_id` avant/après.
- **H4 (hypothèse).** HA n'applique `suggested_area` qu'à la **création** de l'appareil (jamais à une redécouverte). Conséquence : changer la pièce dans Jeedom ne déplace pas l'appareil existant. Vérification : idem, avec un changement de pièce sur un équipement de test.
- **H5 (hypothèse).** Une redécouverte met à jour `device.name` si l'appareil n'a pas de `name_by_user`. Vérification : relevé avant/après sur un des 29 appareils.
- **H6 (fait de terrain, R1).** La box tourne **HA 2026.9.4**. Les **41** entités jeedom2ha créées jusqu'au 2026-05-05 ont un `entity_id` de la forme `<domaine>.jeedom2ha_…` (issu d'`object_id`). Les **306** créées depuis le 2026-05-06, dont les **84** boutons de scénario, ont un `entity_id` dérivé des **noms** (appareil puis entité). La coupure est nette et vaut pour tous les domaines (light, switch, sensor, climate, button…). Depuis cette date, `object_id` n'est donc plus appliqué alors que le démon l'envoie toujours (F10). La cause probable est côté HA (retrait de `object_id` au profit de `default_entity_id`, annoncé par des sources secondaires) : **à confirmer en Task 0** sur la documentation officielle. Conséquence : toute entité **nouvelle ou recréée** reçoit un `entity_id` tiré de ses noms à la création, donc des noms que cette story change (voir Q7).

### Faits de la documentation officielle (ClaudeBox, 2026-10-12, page de l'intégration MQTT `device_tracker.mqtt`) — Task 0

- `default_entity_id` est une option **documentée** de la découverte MQTT. Avec un `unique_id`, il n'est utilisé **qu'à la première création** de l'entité. S'il est défini, il **remplace un `entity_id` personnalisé par l'utilisateur** quand l'entité est supprimée puis recréée.
- Il doit être **complet**, domaine compris (`sensor.…`, `binary_sensor.…`) : une valeur sans domaine donne un `entity_id` inattendu (signalement public dans le dépôt de HA, issue 157241). Le démon l'envoie donc toujours sous la forme `<domaine>.<object_id>`.
- Sur la box (HA 2026.9.4), `object_id` n'est plus appliqué depuis le 2026-05-06 (H6) ; il reste envoyé par le démon.
- La vérification sur un équipement de test (création d'une entité neuve, relevé de l'`entity_id`) sera faite par ClaudeBox à la preuve terrain ; elle n'est pas faisable depuis la session cloud.

## Effet attendu (mesure à partir des faits du 2026-10-12)

- **Appareils :** **29 sur 91 changeraient de nom** (32 %), pour prendre le nom de l'équipement Jeedom ; **62 inchangés**. Si l'appareil renommé à la main (1) fait partie des 29, il n'est pas touché (H2) ; sinon, aucun impact. Pour chacun des 29, le nom actuel est le nom d'une commande (F4 confirmé) : 16 appareils à une seule entité, 13 à plusieurs.
- **Entités renommées à la main (37) :** leur nom personnalisé est conservé (H2) ; leur `entity_id` ne bouge pas (H3). Aucune ne dépend de la nouvelle règle, sauf si Alexandre choisit la recréation (Q6 B), qui les perdrait.
- **Pièces choisies à la main (23) :** conservées (H4) ; la pièce Jeedom n'est de toute façon pas réappliquée à un appareil existant.
- **Entités dont le nom affiché peut changer :** jusqu'à **149** (toutes les entités des 29 appareils), moins celles déjà renommées à la main, car leur nom affiché dérive du nom de l'appareil (H1) et, pour les entités nommées d'après une commande, de la règle de Q2. Le nombre exact reste à compter en Task 1 (entités renommées à la main parmi ces 149).
- **`entity_id` des entités existantes : aucun changement** attendu (H3, à vérifier par le protocole). Les automatisations qui s'appuient sur les `entity_id` ne bougent pas. Ce qui peut bouger : les tableaux de bord et phrases vocales qui s'appuient sur les **noms affichés** des 29 appareils.
- **`entity_id` des entités nouvelles ou recréées : ils suivent les noms** (H6, fait de terrain). Après 22.1, une entité créée (nouvel équipement, ou recréation) prendra un `entity_id` tiré des **noms Jeedom** ; l'`entity_id` d'une entité recréée peut donc changer par rapport à aujourd'hui (voir Q6 B et Q7).
- **Boutons de scénario (84) :** inchangés (F5).

## Critères d'acceptation (figés sur les décisions)

- **AC1.** Pour un équipement Jeedom, `device.name` est identique dans les payloads de **toutes** ses entités (principale et secondaires) : le nom de l'équipement, accents compris [Q1 A].
- **AC2.** Le nom d'entité est le nom de l'équipement pour un équipement à une seule entité, et le nom de la commande pour un équipement à plusieurs entités [Q2 A].
- **AC3.** Après renommage d'un équipement dans Jeedom, le nom d'appareil publié change au sync ou rescan suivant, sans hook d'enregistrement [Q3 A]. Test démon : renommage → payload re-publié avec le nouveau nom.
- **AC4.** La pièce Jeedom est envoyée à chaque sync dans `suggested_area` (inchangé) ; la limite « HA ne l'applique qu'à la création de l'appareil » est écrite dans la documentation utilisateur [Q4 A].
- **AC5.** Aucune entité **existante** ne change d'`entity_id` ni d'`unique_id` (vérifié par l'inventaire avant/après) ; aucun nom/pièce choisi à la main n'est écrasé [Q5 A, Q6 A]. Pour une entité **nouvelle ou recréée**, chaque payload porte `default_entity_id` = `<domaine>.<object_id>`, où `<object_id>` est **exactement** la valeur d'`object_id` envoyée aujourd'hui dans le même payload (F10), pour tous les types d'entité (lumière, volet, switch, capteur, capteur binaire, bouton d'équipement et de scénario, climat, alarme) [Q7 B]. Test unitaire du payload de chaque publisher : `default_entity_id` égal à `<domaine>.<object_id>`, y compris pour les entités à `node_id`/`object_id` propres (secondaires, boutons de scénario). `object_id` reste envoyé (aucun changement d'`unique_id` ni de topic).
- **AC6.** Golden et contrat de sync mis à jour **uniquement** pour le champ `device.name` des équipements concernés et le champ additif `default_entity_id` ; aucune autre différence.
- **AC7.** Gate 20-0 vert avant `done` (aucune écriture transmise à la box) ; preuve terrain par l'humain : inventaire avant/après des registres appareils et entités de HA (nom, `name_by_user`, `entity_id`, pièce), rapproché de la liste des 29.
- **AC8.** Aucun nom réel dans le code de test, les fixtures, la story, la PR (CC-48).

## Tâches

- **Task 0 — Vérifier H1 à H5 et que `default_entity_id` est bien appliqué par HA 2026.9.4** (et pourquoi `object_id` ne l'est plus), sur la documentation officielle de HA si l'accès est possible, sinon sur un **équipement de test** (création d'une entité neuve, relevé de son `entity_id`). **Si `default_entity_id` n'est pas appliqué comme décrit, s'arrêter et revenir vers ClaudeBox avant de généraliser.**
- **Task 1 — Inventaire « avant » (humain, lecture seule)** : pour les 91 appareils et leurs entités, relever nom affiché, `name_by_user`, `original_name`, `entity_id`, pièce ; comparer au nom Jeedom ; comptes par appareil (entités, dont celles renommées à la main). Sans nom réel dans le dépôt (identifiants seuls).
- [x] **Task 2 — Démon : un seul nom d'appareil par équipement** (`publisher.py:_build_device_block`) selon Q1 A ; ne plus dériver `device.name` du `ha_name` d'une entité secondaire.
- [x] **Task 3 — Démon : règle du nom d'entité** selon Q2 A (mappers F2/F3 ou publisher).
- [x] **Task 3b — Démon : `default_entity_id` pour les entités nouvelles ou recréées** (Q7 B) : ajouter `default_entity_id` = `<domaine>.<object_id>` dans chaque payload de découverte, en reprenant la valeur d'`object_id` déjà calculée pour le payload (F10) ; ne pas modifier `object_id`, `unique_id` ni topic. Test du payload de chaque publisher (AC5).
- [x] **Task 4 — Tests** : unitaires (device identique sur toutes les entités d'un équipement multi-entités ; forme de l'équipement 579 ; renommage → republication au sync), golden mis à jour, fixtures anonymisées. `make test` et `flake8` verts.
- **Task 5 — Gate 20-0 + déploiement standard (humain) + inventaire « après »** ; rapprochement avec la liste des 29 ; protocole H2/H3/H4 sur un équipement de test.
- [x] **Task 6 — Documentation** : `docs/fr_FR` (nom = nom Jeedom, pièce appliquée à la création seulement, comment renommer à la main, comment forcer la pièce via recréation ; `entity_id` technique stable des entités créées) selon Q3 A, Q4 A, Q5 A, Q6 A, Q7 B.

## Garde-fous

- Gate 20-0 vert avant tout `done` ; aucune écriture transmise à la box par le gate.
- Preuve terrain avec inventaire avant/après ; `scripts/deploy-to-box.sh` jamais lancé par une session cloud.
- Aucun `entity_id`, `unique_id` ni topic **existant** ne change (AC5) ; seuls les champs de nom changent, plus le champ additif `default_entity_id` (Q7 B, AC5-AC6).
- Aucun nom réel d'équipement, de pièce, de scénario ou de personne (CC-48) ; ni secret ni IP privée.
- Une PR = un sujet : les noms et l'`entity_id` des entités créées sont un seul sujet (les deux dérivent des mêmes champs de nom, H6).

## Questions pour Alexandre (tranchées le 2026-10-12 : options non retenues marquées « écartée »)

**Q1 — Quel nom d'appareil dans HA ?**
- **A (retenue).** Toujours le nom de l'équipement Jeedom, identique pour toutes les entités de l'équipement. Conséquence : 29 appareils sur 91 prennent le nom Jeedom ; la voix reconnaît les noms Jeedom ; les noms affichés des entités de ces 29 appareils changent (les `entity_id` non). Les automatisations par `entity_id` ne bougent pas ; les tableaux de bord affichent le nouveau nom.
- **B (écartée).** Ne rien changer. Les 29 gardent un nom venu d'une commande ; la décision du 2026-10-01 n'est pas tenue.

**Q2 — Quel nom d'entité ?**
- **A (retenue).** Équipement à une seule entité : nom de l'équipement (HA l'affiche comme l'appareil). Équipement à plusieurs entités : nom de la commande. Conséquence : lecture naturelle (« <équipement> <commande> »), pas de doublon ; certains noms d'entités changent d'affichage.
- **B (écartée).** Toujours le nom de l'équipement pour l'entité principale, nom de commande pour les autres. Conséquence : proche de A, mais l'entité principale d'un équipement multi-entités s'affiche avec le seul nom d'appareil.
- **C (écartée).** Ne pas toucher aux noms d'entité. Conséquence : le nom affiché reste hétérogène ; moins de changements visibles.

**Q3 — Quand un renommage Jeedom atteint-il HA ?**
- **A (retenue).** Au sync suivant (rescan, redémarrage du démon, « Republier ») : c'est déjà le comportement du code (F7) ; on corrige les noms et on **documente** qu'il faut un rescan. Aucun nouveau code PHP.
- **B (écartée).** Déclencher une republication de l'équipement à chaque enregistrement dans Jeedom (hook `postSave`). Conséquence : HA suit en direct, mais nouveau code PHP/démon, risque de rafale lors d'éditions en série, preuve terrain plus lourde.

**Q4 — La pièce Jeedom.**
- **A (retenue).** Envoyer la pièce à chaque sync (déjà le cas) et documenter que HA ne l'applique qu'à la création de l'appareil (H4). Les 23 pièces choisies à la main ne sont pas touchées. Un appareil existant ne change de pièce que si l'utilisateur le fait dans HA ou le recrée.
- **B (écartée).** Ne rien documenter ni promettre. Conséquence : confusion probable quand une pièce modifiée dans Jeedom ne suit pas.

**Q5 — Noms et pièces choisis à la main dans HA (1 appareil, 37 entités, 23 pièces).**
- **A (retenue).** Ils font foi côté HA : le plugin n'y touche pas, aucune détection ni rapport. Conséquence : la règle « Jeedom fait foi » vaut pour ce que l'utilisateur n'a pas personnalisé.
- **B (écartée).** Fournir un rapport en lecture seule listant les noms manuels qui divergent de Jeedom. Conséquence : utile pour un grand ménage, mais le plugin n'a pas d'accès aux registres HA (MQTT seul) : nécessite un outil externe, hors périmètre.

**Q6 — Les `entity_id` et noms existants des 29 appareils.**
- **A (retenue).** Ne pas y toucher : seuls les noms affichés changent (H3). Aucun risque pour les automatisations par `entity_id`.
- **B (écartée).** Proposer ensuite une recréation (« Supprimer puis recréer ») pour les aligner aussi sur les nouveaux noms. Conséquence : une entité recréée reçoit un `entity_id` **tiré des noms du moment** (H6) : il change pour toutes celles dont il dérivait d'un nom ; historique perdu, noms et pièces manuels perdus (37 entités, 23 pièces) : à éviter sans accord explicite et sans liste préalable des automatisations touchées.

**Q7 — `entity_id` des entités nouvelles ou recréées (H6 : `object_id` n'est plus appliqué par HA 2026.9.4).**
Les 41 entités d'avant le 2026-05-06 ont un `entity_id` technique `<domaine>.jeedom2ha_…` ; les 306 suivantes (dont les 84 boutons de scénario) en ont un tiré des noms. Pour toute entité créée ou recréée à partir de 22.1 :
- **A (écartée).** `entity_id` dérivé des noms (comportement actuel de fait ; le démon cesse d'envoyer `object_id`, devenu inutile). Conséquence : identifiants lisibles qui suivent les noms Jeedom **à la création**, mais un renommage ultérieur dans Jeedom ne les change pas, et deux équipements de même nom reçoivent un suffixe numérique ; une recréation change l'`entity_id` d'une entité dont il dérive d'un nom, donc casse les automatisations, tableaux de bord et phrases vocales qui le citent.
- **B (retenue).** Identifiant technique stable via `default_entity_id` = `<domaine>.<object_id actuel>` (cohérent avec les 41 anciennes). Conséquence : `entity_id` prévisibles, identiques après une recréation, insensibles aux renommages (les automatisations survivent à une recréation) ; en revanche illisibles, et à partir de 22.1 les entités créées reprennent la forme technique, donc une recréation d'une des 306 entités actuelles à `entity_id` lisible le **changerait** vers la forme technique (une fois). **Correction (décision d'Alexandre) :** les cartes de tableau de bord citent l'`entity_id`, pas le nom affiché ; seule la voix (Assist) s'appuie sur le nom. Avec B, automatisations, scripts et cartes survivent à une recréation.
- **C (écartée).** Ne rien décider ici : conserver le comportement de fait sans le maîtriser. Conséquence : un futur changement de HA peut modifier les `entity_id` sans que le plugin le sache : non recommandé.
**Retenue : B**, sous réserve de la Task 0 (`default_entity_id` effectivement appliqué par HA 2026.9.4, vérifié sur la documentation ou sur un équipement de test avant toute généralisation).

**QD — Découpage (tranchée : deux stories, 22-1 puis 22-2).** Deux stories (22.1 noms, 22.2 compteurs et lisibilité). Alternatives : une seule story (une seule preuve terrain mais deux domaines : démon seul / interface) ; ou trois stories avec 22.2 scindée en compteurs/CC-51 puis CC-55, CC-58, CC-60 et P3 (voir 22.2).

## Vérifications non faites par cette session

H1 à H5 (comportement de HA) et la cause de H6 (le fait de terrain est établi, pas sa cause) ; appartenance de l'appareil renommé à la main aux 29 ; nombre d'entités renommées à la main parmi les 149 ; garantie de `default_entity_id` sur HA 2026.9.4. Établi par le relevé de terrain R1 (ClaudeBox) : F4, la version de HA, la coupure des `entity_id` au 2026-05-06.

## Journal des décisions

- 2026-10-01 18:21 — Alexandre : « le nom et la pièce Jeedom font foi partout ».
- 2026-10-11 15:48 — Alexandre : ordre de la suite = CC-44 + CC-47, puis CC-36 avec CC-51 et « compteurs », puis parité HomeKit (CC-33).
- 2026-10-12 — Cadrage documentaire (cette session) : story en `draft`, décisions Q1 à Q7 attendues.
- 2026-10-12 — R1 (ClaudeBox, relevé de terrain vers 04:30) : F4 et H6 confirmés (HA 2026.9.4 ; 41 entités à `entity_id` technique, 306 à `entity_id` dérivé des noms depuis le 2026-05-06 ; 29 appareils, 149 entités) ; Q7 refaite en question produit ; hors-périmètre `object_id` retiré.
- 2026-10-12, vers 05:50 — **Décisions d'Alexandre** (relayées par ClaudeBox) : Q1 A, Q2 A, Q3 A, Q4 A, Q5 A, Q6 A, **Q7 B** (`default_entity_id` = `<domaine>.<object_id actuel>` pour les entités nouvelles ou recréées), QD deux stories ; conséquence de Q7 corrigée (cartes de tableau de bord = `entity_id`, voix = nom). **`ready-for-dev` accordé** par ClaudeBox au nom de cette décision ; AC figés, options écartées retirées des AC et tâches.

## Dev Agent Record

### Implementation Plan / notes

- **Task 0** : faits de la documentation officielle consignés (section dédiée ci-dessus, H6, documentation utilisateur). Vérification terrain sur équipement de test laissée à ClaudeBox (aucun accès HA/box ici).
- **Task 2** (`publisher._build_device_block`) : `device.name` = nom de l'équipement Jeedom lu dans le snapshot (`eq.name`) pour tout équipement ; le bouton de scénario garde le nom du scénario (`ha_name`) ; repli sur `ha_name` si l'équipement est absent du snapshot.
- **Task 3** (`mapping/registry.MapperRegistry.map_all`) : règle Q2 A appliquée à un seul endroit (`_apply_entity_name_rule`) : un seul mapping pour l'équipement → `ha_name = eq.name` ; plusieurs → chaque entité porte le nom de sa commande, l'entité principale (switch, light, cover) garde le nom de l'équipement (voir R1 : essai de la revue Codex P1 retiré). Les mappers ne changent pas.
- **Task 3b** (`publisher._add_default_entity_id`) : `default_entity_id = <domaine>.<object_id>` calculé depuis l'`object_id` déjà présent dans le payload (identique par construction) pour les 8 publishers (light, cover, switch, sensor, binary_sensor, button — équipement et scénario —, climate, alarm_control_panel). `object_id`, `unique_id`, topics et disponibilité inchangés.
- **Task 4** : `tests/unit/test_story_22_1_noms_jeedom.py` (17 tests : `device.name` unique sur la forme 579 multi-entités, règle du nom d'entité, accents, bouton de scénario, `default_entity_id` par domaine et pour les entités secondaires, `unique_id`/`object_id`/topic inchangés, renommage → republication avec nouveau `device.name`). Golden réaligné : seule la référence figée du bouton de scénario (`test_story_21_1_cc44_scenario_lifecycle.py`) gagne `default_entity_id` ; aucune autre différence. Noms génériques uniquement (CC-48).
- **Task 6** : `docs/fr_FR/index.md` (annexe « noms et identifiants dans Home Assistant », dont la recréation qui reprend l'`entity_id` technique) et `docs/fr_FR/changelog_beta.md` (entrée du 2026-10-12).
- Tasks 1 et 5 : humain / ClaudeBox (inventaires avant/après, gate 20-0, déploiement, preuve terrain) — non réalisables ici, non cochées.
- Vérifications locales : `make test` 679 passed ; `flake8` propre ; `node --test tests/unit/*.node.test.js` 421 pass.

### Changements de payload (liste pour la PR)

- `device.name` : nom de l'équipement Jeedom pour toutes les entités (changement visible pour les équipements dont une entité portait un nom de commande).
- Champ additif `default_entity_id` sur tous les payloads de découverte.
- `name` d'une entité unique nommée d'après une commande (F3) : devient le nom de l'équipement (Q2 A).

### R1 (relecture ClaudeBox de la PR #249, tête `1867c4b`, 2026-10-12)

- **P1 CI.** `make test` ne couvre que `tests/` ; la CI lance `python -m pytest` (`testpaths = tests, resources/daemon/tests`, plus de 2100 tests). La suite complète a été lancée localement comme la CI : 6 tests de `resources/daemon/tests/unit/test_story_19_4_guard_publisher_calls.py` échouaient (traces MQTT figées).
- **Fixtures réalignées** (régénérées avec `JEEDOM2HA_GUARD_REGEN=1`, après suppression des références), `resources/daemon/tests/fixtures/story_19_4_guard/` : 8 fichiers `*_mqtt.json` (s1, s2, s3, s4 publier/sync1/sync2, s5, s6 sync2). Différences vérifiées champ par champ contre les anciennes : **uniquement** `device.name` (145 occurrences, nom d'équipement à la place du nom d'une commande) et le champ additif `default_entity_id` (309 occurrences). Aucun changement de `name` d'entité dans ce corpus, ni de topic, `retain`, `unique_id`, `object_id` ou disponibilité. Les fixtures sémantiques (`s*.json`) et de disponibilité (`*_avail.json`) sont inchangées. `golden_corpus/` inchangé.
- **Retrait de l'essai Codex P1** (`deb862a`) : renommer l'entité principale d'un équipement multi-entités d'après sa commande d'état produisait, sur le corpus doré, des noms comme « Etat » ou « active » pour un switch ou une lumière, au-delà de ce que la relecture R1 avait validé. Le registre est revenu à la règle de `1867c4b` (l'entité principale garde le nom de l'équipement). Point laissé à décision : voir la PR.
- **P3.** Branche mise à jour sur `main` (`5105c0f`) ; seul conflit : `sprint-status.yaml`, lignes 21-1/epic 21 de `main` conservées, ligne de 22-1 gardée, commentaires `last_updated` fusionnés.
- Suite complète du démon : voir la description de la PR pour le résultat final.

### Change Log

- 2026-10-12 : implémentation Tasks 2, 3, 3b, 4, 6 ; statut `review`.

### File List

- `_bmad-output/implementation-artifacts/22-1-noms-home-assistant-egaux-noms-jeedom-cc36.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `resources/daemon/discovery/publisher.py`
- `resources/daemon/mapping/registry.py`
- `tests/unit/test_story_22_1_noms_jeedom.py` (nouveau)
- `tests/unit/test_story_21_1_cc44_scenario_lifecycle.py`
- `docs/fr_FR/index.md`
- `docs/fr_FR/changelog_beta.md`
