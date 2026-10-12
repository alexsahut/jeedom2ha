# Story 22.1 : Noms Home Assistant = noms Jeedom (CC-36)

Status: draft

> **Statut : `draft` (2026-10-12).** Brouillon de cadrage rédigé par une session cloud déléguée (documentaire, lecture seule : aucun accès box, Home Assistant ni secret ; aucun code touché). **Rien n'est `ready-for-dev`** : Alexandre tranche les questions Q1 à Q7 via ClaudeBox. Les pointeurs `fichier:ligne` sont pris sur `main` à `ab3a854`. **R1 (ClaudeBox, 2026-10-12, relevé de terrain en lecture seule vers 04:30)** : F4 et H6 passent de l'hypothèse au fait (HA 2026.9.4) ; Q7 devient une question produit de cette story. Aucun nom réel d'équipement, de pièce, de scénario ou de personne dans ce fichier (CC-48) : seuls des identifiants.

## Story

En tant qu'utilisateur qui pilote sa maison par la voix et par des tableaux de bord dans Home Assistant,
je veux que chaque appareil porte le nom de l'équipement Jeedom et que la pièce de Jeedom soit proposée à sa création,
afin que « le nom et la pièce Jeedom font foi partout » (décision d'Alexandre, 2026-10-01 18:21) et qu'Assist reconnaisse les noms que je connais.

**Parcours : démon uniquement** (discovery MQTT). Aucun écran ne change. Preuve terrain obligatoire par l'humain : inventaire des registres HA avant/après.

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

## Effet attendu (mesure à partir des faits du 2026-10-12)

- **Appareils :** **29 sur 91 changeraient de nom** (32 %), pour prendre le nom de l'équipement Jeedom ; **62 inchangés**. Si l'appareil renommé à la main (1) fait partie des 29, il n'est pas touché (H2) ; sinon, aucun impact. Pour chacun des 29, le nom actuel est le nom d'une commande (F4 confirmé) : 16 appareils à une seule entité, 13 à plusieurs.
- **Entités renommées à la main (37) :** leur nom personnalisé est conservé (H2) ; leur `entity_id` ne bouge pas (H3). Aucune ne dépend de la nouvelle règle, sauf si Alexandre choisit la recréation (Q6 B), qui les perdrait.
- **Pièces choisies à la main (23) :** conservées (H4) ; la pièce Jeedom n'est de toute façon pas réappliquée à un appareil existant.
- **Entités dont le nom affiché peut changer :** jusqu'à **149** (toutes les entités des 29 appareils), moins celles déjà renommées à la main, car leur nom affiché dérive du nom de l'appareil (H1) et, pour les entités nommées d'après une commande, de la règle de Q2. Le nombre exact reste à compter en Task 1 (entités renommées à la main parmi ces 149).
- **`entity_id` des entités existantes : aucun changement** attendu (H3, à vérifier par le protocole). Les automatisations qui s'appuient sur les `entity_id` ne bougent pas. Ce qui peut bouger : les tableaux de bord et phrases vocales qui s'appuient sur les **noms affichés** des 29 appareils.
- **`entity_id` des entités nouvelles ou recréées : ils suivent les noms** (H6, fait de terrain). Après 22.1, une entité créée (nouvel équipement, ou recréation) prendra un `entity_id` tiré des **noms Jeedom** ; l'`entity_id` d'une entité recréée peut donc changer par rapport à aujourd'hui (voir Q6 B et Q7).
- **Boutons de scénario (84) :** inchangés (F5).

## Critères d'acceptation provisoires

- **AC1.** Pour un équipement Jeedom, `device.name` est identique dans les payloads de **toutes** ses entités (principale et secondaires) : le nom de l'équipement, accents compris [Q1].
- **AC2.** Le nom d'entité suit la règle choisie en Q2 (provisoire : entité unique = nom de l'équipement ; plusieurs entités = nom de la commande).
- **AC3.** Après renommage d'un équipement dans Jeedom, le nom d'appareil publié change au sync ou rescan suivant [Q3]. Test démon : renommage → payload re-publié avec le nouveau nom.
- **AC4.** La pièce Jeedom est envoyée à chaque sync dans `suggested_area` (inchangé) ; la limite « HA ne l'applique qu'à la création de l'appareil » est écrite dans la documentation utilisateur [Q4].
- **AC5.** Aucune entité **existante** ne change d'`entity_id` ni d'`unique_id` (vérifié par l'inventaire avant/après) ; aucun nom/pièce choisi à la main n'est écrasé [Q5, Q6]. Pour une entité **nouvelle ou recréée**, l'`entity_id` suit la règle choisie en Q7 (dérivé des noms, ou stable par `default_entity_id`), documentée et testée [Q7].
- **AC6.** Golden et contrat de sync mis à jour **uniquement** pour le champ `device.name` des équipements concernés ; aucune autre différence.
- **AC7.** Gate 20-0 vert avant `done` (aucune écriture transmise à la box) ; preuve terrain par l'humain : inventaire avant/après des registres appareils et entités de HA (nom, `name_by_user`, `entity_id`, pièce), rapproché de la liste des 29.
- **AC8.** Aucun nom réel dans le code de test, les fixtures, la story, la PR (CC-48).

## Tâches

- **Task 0 — Vérifier H1 à H5 et la cause de H6 sur la documentation officielle de HA** (pourquoi `object_id` n'est plus appliqué en 2026.9.4 ; ce que `default_entity_id` garantit) (si l'accès est possible) ; sinon, protocole terrain de la Task 5 sur un équipement de test.
- **Task 1 — Inventaire « avant » (humain, lecture seule)** : pour les 91 appareils et leurs entités, relever nom affiché, `name_by_user`, `original_name`, `entity_id`, pièce ; comparer au nom Jeedom ; comptes par appareil (entités, dont celles renommées à la main). Sans nom réel dans le dépôt (identifiants seuls).
- **Task 2 — Démon : un seul nom d'appareil par équipement** (`publisher.py:_build_device_block`) selon Q1 ; ne plus dériver `device.name` du `ha_name` d'une entité secondaire.
- **Task 3 — Démon : règle du nom d'entité** selon Q2 (mappers F2/F3 ou publisher).
- **Task 3b — Démon : `entity_id` des entités nouvelles ou recréées** selon Q7 (ajout éventuel de `default_entity_id` dans les payloads ; sort de `object_id`).
- **Task 4 — Tests** : unitaires (device identique sur toutes les entités d'un équipement multi-entités ; forme de l'équipement 579 ; renommage → republication au sync), golden mis à jour, fixtures anonymisées. `make test` et `flake8` verts.
- **Task 5 — Gate 20-0 + déploiement standard (humain) + inventaire « après »** ; rapprochement avec la liste des 29 ; protocole H2/H3/H4 sur un équipement de test.
- **Task 6 — Documentation** : `docs/fr_FR` (nom = nom Jeedom, pièce appliquée à la création seulement, comment renommer à la main, comment forcer la pièce via recréation) selon Q3 à Q6.

## Garde-fous

- Gate 20-0 vert avant tout `done` ; aucune écriture transmise à la box par le gate.
- Preuve terrain avec inventaire avant/après ; `scripts/deploy-to-box.sh` jamais lancé par une session cloud.
- Aucun `entity_id`, `unique_id` ni topic **existant** ne change (AC5) ; seuls les champs de nom changent, plus `default_entity_id` si Q7 B est retenue (AC6 mis à jour en conséquence).
- Aucun nom réel d'équipement, de pièce, de scénario ou de personne (CC-48) ; ni secret ni IP privée.
- Une PR = un sujet : les noms et l'`entity_id` des entités créées sont un seul sujet (les deux dérivent des mêmes champs de nom, H6).

## Questions pour Alexandre

**Q1 — Quel nom d'appareil dans HA ?**
- **A (recommandé).** Toujours le nom de l'équipement Jeedom, identique pour toutes les entités de l'équipement. Conséquence : 29 appareils sur 91 prennent le nom Jeedom ; la voix reconnaît les noms Jeedom ; les noms affichés des entités de ces 29 appareils changent (les `entity_id` non). Les automatisations par `entity_id` ne bougent pas ; les tableaux de bord affichent le nouveau nom.
- **B.** Ne rien changer. Les 29 gardent un nom venu d'une commande ; la décision du 2026-10-01 n'est pas tenue.

**Q2 — Quel nom d'entité ?**
- **A (recommandé).** Équipement à une seule entité : nom de l'équipement (HA l'affiche comme l'appareil). Équipement à plusieurs entités : nom de la commande. Conséquence : lecture naturelle (« <équipement> <commande> »), pas de doublon ; certains noms d'entités changent d'affichage.
- **B.** Toujours le nom de l'équipement pour l'entité principale, nom de commande pour les autres. Conséquence : proche de A, mais l'entité principale d'un équipement multi-entités s'affiche avec le seul nom d'appareil.
- **C.** Ne pas toucher aux noms d'entité. Conséquence : le nom affiché reste hétérogène ; moins de changements visibles.

**Q3 — Quand un renommage Jeedom atteint-il HA ?**
- **A (recommandé).** Au sync suivant (rescan, redémarrage du démon, « Republier ») : c'est déjà le comportement du code (F7) ; on corrige les noms et on **documente** qu'il faut un rescan. Aucun nouveau code PHP.
- **B.** Déclencher une republication de l'équipement à chaque enregistrement dans Jeedom (hook `postSave`). Conséquence : HA suit en direct, mais nouveau code PHP/démon, risque de rafale lors d'éditions en série, preuve terrain plus lourde.

**Q4 — La pièce Jeedom.**
- **A (recommandé).** Envoyer la pièce à chaque sync (déjà le cas) et documenter que HA ne l'applique qu'à la création de l'appareil (H4). Les 23 pièces choisies à la main ne sont pas touchées. Un appareil existant ne change de pièce que si l'utilisateur le fait dans HA ou le recrée.
- **B.** Ne rien documenter ni promettre. Conséquence : confusion probable quand une pièce modifiée dans Jeedom ne suit pas.

**Q5 — Noms et pièces choisis à la main dans HA (1 appareil, 37 entités, 23 pièces).**
- **A (recommandé).** Ils font foi côté HA : le plugin n'y touche pas, aucune détection ni rapport. Conséquence : la règle « Jeedom fait foi » vaut pour ce que l'utilisateur n'a pas personnalisé.
- **B.** Fournir un rapport en lecture seule listant les noms manuels qui divergent de Jeedom. Conséquence : utile pour un grand ménage, mais le plugin n'a pas d'accès aux registres HA (MQTT seul) : nécessite un outil externe, hors périmètre.

**Q6 — Les `entity_id` et noms existants des 29 appareils.**
- **A (recommandé).** Ne pas y toucher : seuls les noms affichés changent (H3). Aucun risque pour les automatisations par `entity_id`.
- **B.** Proposer ensuite une recréation (« Supprimer puis recréer ») pour les aligner aussi sur les nouveaux noms. Conséquence : une entité recréée reçoit un `entity_id` **tiré des noms du moment** (H6) : il change pour toutes celles dont il dérivait d'un nom ; historique perdu, noms et pièces manuels perdus (37 entités, 23 pièces) : à éviter sans accord explicite et sans liste préalable des automatisations touchées.

**Q7 — `entity_id` des entités nouvelles ou recréées (H6 : `object_id` n'est plus appliqué par HA 2026.9.4).**
Les 41 entités d'avant le 2026-05-06 ont un `entity_id` technique `<domaine>.jeedom2ha_…` ; les 306 suivantes (dont les 84 boutons de scénario) en ont un tiré des noms. Pour toute entité créée ou recréée à partir de 22.1 :
- **A.** `entity_id` dérivé des noms (comportement actuel de fait ; le démon cesse d'envoyer `object_id`, devenu inutile). Conséquence : identifiants lisibles qui suivent les noms Jeedom **à la création**, mais un renommage ultérieur dans Jeedom ne les change pas, et deux équipements de même nom reçoivent un suffixe numérique ; une recréation change l'`entity_id` d'une entité dont il dérive d'un nom, donc casse les automatisations, tableaux de bord et phrases vocales qui le citent.
- **B (recommandé).** Identifiant technique stable via `default_entity_id` (par exemple `<domaine>.jeedom2ha_<eq>_<cmd>`, cohérent avec les 41 anciennes). Conséquence : `entity_id` prévisibles, identiques après une recréation, insensibles aux renommages (les automatisations survivent à une recréation) ; en revanche illisibles, et à partir de 22.1 les entités créées reprennent la forme technique, donc une recréation d'une des 306 entités actuelles à `entity_id` lisible le **changerait** vers la forme technique (une fois). Les voix et tableaux de bord s'appuient sur le nom affiché, pas sur l'`entity_id`, donc la voix n'est pas touchée.
- **C.** Ne rien décider ici : conserver le comportement de fait sans le maîtriser. Conséquence : un futur changement de HA peut modifier les `entity_id` sans que le plugin le sache : non recommandé.
Recommandation : **B**, sous réserve de Task 0 (garantie réelle de `default_entity_id` sur 2026.9.4) et d'un test sur un équipement de test avant toute généralisation.

**QD — Découpage.** Recommandé : deux stories (22.1 noms, 22.2 compteurs et lisibilité). Alternatives : une seule story (une seule preuve terrain mais deux domaines : démon seul / interface) ; ou trois stories avec 22.2 scindée en compteurs/CC-51 puis CC-55, CC-58, CC-60 et P3 (voir 22.2).

## Vérifications non faites par cette session

H1 à H5 (comportement de HA) et la cause de H6 (le fait de terrain est établi, pas sa cause) ; appartenance de l'appareil renommé à la main aux 29 ; nombre d'entités renommées à la main parmi les 149 ; garantie de `default_entity_id` sur HA 2026.9.4. Établi par le relevé de terrain R1 (ClaudeBox) : F4, la version de HA, la coupure des `entity_id` au 2026-05-06.

## Journal des décisions

- 2026-10-01 18:21 — Alexandre : « le nom et la pièce Jeedom font foi partout ».
- 2026-10-11 15:48 — Alexandre : ordre de la suite = CC-44 + CC-47, puis CC-36 avec CC-51 et « compteurs », puis parité HomeKit (CC-33).
- 2026-10-12 — Cadrage documentaire (cette session) : story en `draft`, décisions Q1 à Q7 attendues.
- 2026-10-12 — R1 (ClaudeBox, relevé de terrain vers 04:30) : F4 et H6 confirmés (HA 2026.9.4 ; 41 entités à `entity_id` technique, 306 à `entity_id` dérivé des noms depuis le 2026-05-06 ; 29 appareils, 149 entités) ; Q7 refaite en question produit ; hors-périmètre `object_id` retiré.

## Dev Agent Record

(à remplir après `ready-for-dev`)

### File List

- `_bmad-output/implementation-artifacts/22-1-noms-home-assistant-egaux-noms-jeedom-cc36.md` (nouveau)
