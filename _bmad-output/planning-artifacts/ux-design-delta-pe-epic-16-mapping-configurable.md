---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
lastStep: 14
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/product-brief-jeedom2ha-2026-04-09.md
  - _bmad-output/planning-artifacts/architecture-delta-pe-epic-16-mapping-configurable.md
  - _bmad-output/planning-artifacts/homebridge-homekit-vs-ha-delta-2026-06-07.md
  - _bmad-output/project-context.md
---

# UX Design Specification jeedom2ha — Delta pe-epic-16 (Mapping configurable commande par commande)

**Author:** Alexandre
**Date:** 2026-07-06

---

<!-- UX design content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

### Project Vision

Story 16b apporte l'écran de configuration du mapping HA commande par commande, en surface du backend d'override déjà tranché (pe-16a, D8-D12). L'enjeu UX n'est pas de créer un éditeur générique : c'est de rendre visible et actionnable, pour chaque commande d'un parc de 284 équipements, l'écart entre l'attendu HA calculé par le moteur de projection et ce que l'utilisateur veut réellement exposer — sans jamais toucher au `generic_type` Jeedom natif partagé avec Homebridge (D10).

### Target Users

Utilisateur unique de référence : "Sébastien", administrateur Jeedom expert, déjà exposé à Homebridge/HomeKit. Son point de douleur documenté sur Homebridge : configurer un type à l'aveugle, sans savoir pourquoi il ne fonctionne pas, ni ce qui manque. Il attend de jeedom2ha un diagnostic, pas juste un formulaire.

### Key Design Challenges

- Surcharge cognitive potentielle : 4 niveaux de hiérarchie (pièce → équipement → commande → détail), 3 états par champ (natif / override / suggéré), deux référentiels attendus (HA + Homebridge déjà connu de l'utilisateur).
- Risque de régression produit : si "attendu HA" et "attendu Homebridge" apparaissent côte à côte sans séparation visuelle forte et permanente, l'utilisateur peut être tenté de modifier le `generic_type` natif en pensant changer un simple type HA (contrainte D10, non négociable).
- Contrainte technique : rendu en jQuery/Bootstrap natif Jeedom, sans framework front — un tree-view 4 niveaux doit rester un empilement d'accordéons, avec chargement différé des données (source `ha-projection-reference.md/.yaml`) pour ne pas charger 284 équipements d'un coup.

### Design Opportunities

- Disclosure progressive : liste dense et scannable par défaut (arbo pièce/équipement, comme Homebridge), détail riche (attendu HA, override, diff) uniquement à l'ouverture d'une commande.
- Le dry-run de validation (capabilities actuelles suffisantes ou non pour un `ha_entity_type` choisi) n'est pas un correctif de fin de parcours (Story 16.6) : le concevoir dès l'écran 16b évite de refaire l'UI deux fois et répond directement au vrai besoin de Sébastien (comprendre le pourquoi, pas configurer à l'aveugle).
- Colonne "Jeedom natif (partagé Homebridge)" verrouillée en lecture seule vs colonne "Override HA (jeedom2ha uniquement)" éditable, jamais le même champ visuel pour les deux — signal constant, pas une notice ponctuelle.

## Core Experience

### The ONE Thing

L'expérience qui doit être parfaite : **rendre un équipement "projetable" sur HA**, depuis un point d'entrée unique et évident — un onglet "HA / jeedom2ha" sur la fiche équipement Jeedom existante, jamais un écran séparé perdu dans un menu, jamais mélangé aux onglets natifs Homebridge de la même fiche. L'action doit se sentir comme une continuité naturelle de la fiche équipement, pas comme un outil rapporté.

### Platform

Interface d'administration Jeedom native uniquement (desktop, souris/clavier). Pas d'usage tactile/tablette à concevoir pour cette story — simplifie le rendu jQuery/Bootstrap et la densité d'information tolérable à l'écran.

### The Effortless Moment

Le point d'automatisation clé : le **dry-run instantané**. Dès que l'utilisateur sélectionne un `ha_entity_type` pour une commande, le statut de projection (✅ prêt / ⚠️ override possible / ❌ bloquant) se recalcule sans action supplémentaire — pas de bouton "valider" séparé. Techniquement, c'est un appel en lecture seule à `validate_projection()` sur une copie patchée du `MappingResult`, réutilisant `reason_details` déjà existant (aucun nouveau moteur de diagnostic). Contraintes d'implémentation actées : call ajax débounced (300-500ms), état de chargement visible sous 200ms, un seul appel par équipement édité (pas un par commande en cascade), et le call ne se déclenche qu'à l'ouverture du niveau commande (pas au chargement de la page entière, pour ne pas charger 284 équipements d'un coup).

### Moment of Success

Le moment critique qui doit marcher à tout prix, même si le reste de l'écran est encore rugueux : celui où Sébastien comprend **pourquoi** une commande n'est pas encore exposée côté HA et voit **exactement** quoi corriger (capability manquante, override nécessaire, etc.) — un diagnostic actionnable, pas juste un statut binaire prêt/pas prêt.

## Desired Emotional Response

### Primary Emotional Goals

**En contrôle**, pas "efficace à toute vitesse". Sébastien vient d'une expérience Homebridge où il subissait la configuration à l'aveugle sans comprendre pourquoi un type ne fonctionnait pas ; la vitesse d'exécution ne répare pas ce point de douleur, la compréhension oui. Le sentiment recherché après avoir rendu une commande "projetable" avec succès n'est pas la satisfaction d'avoir "fini vite", mais la **clarté rétrospective** : comprendre pourquoi ça marche maintenant, pas juste voir une coche verte.

### Emotional Journey Mapping

- **Première ouverture de l'onglet "HA / jeedom2ha" sur un équipement neuf** : viser une carte lisible immédiatement, jamais un sentiment de mur — même face à 20 commandes non configurées, grâce à la disclosure progressive (liste dense par défaut, détail au clic).
- **Pendant le dry-run (300-500ms de débounce)** : le calcul en cours doit se lire clairement comme circonscrit à la colonne "override HA", jamais comme un état de chargement global de la fiche équipement — pour ne pas générer d'anxiété de type "est-ce que je suis en train de casser Homebridge ?".
- **Si le dry-run révèle un blocage (capability manquante)** : vécu comme une étape normale et attendue du diagnostic, jamais comme un échec de l'outil. Le ton du message prime sur sa présence : "Capability X manquante pour ce type HA" plutôt que "Erreur".
- **Au moment du succès** : on s'autorise un signal positif franc et marqué (couleur verte nette), pour créer un vrai moment de satisfaction — tranché comme exception au ton globalement sobre et factuel du reste de l'écran.
- **Retour sur l'écran après plusieurs jours** : retrouver immédiatement le même niveau de confiance qu'à la première réussite, sans redécouvrir un outil opaque.
- **Si un blocage persiste après plusieurs tentatives** : Sébastien doit ressentir "je sais quoi faire ensuite" (lien vers où configurer la capability manquante), jamais "je suis bloqué sans recours".

### Micro-Emotions

- **Confiance vs. Anxiété de régression** : le risque émotionnel spécifique à ce produit n'est pas la confusion générique, mais la peur diffuse de casser un plugin voisin (Homebridge) en touchant un champ qui semble proche. La séparation visuelle stricte native/override (actée en step 2) sert autant cet objectif émotionnel que l'objectif fonctionnel D10.
- **Accomplissement vs. Frustration** : le succès doit être identifiable d'un coup d'œil (signal vert franc), la frustration d'un blocage doit être désamorcée par une explication immédiate et actionnable, jamais laissée en l'état.

### Design Implications

- **En contrôle** → séparation visuelle permanente native (lecture seule) / override (éditable), jamais le même traitement visuel pour les deux ; diagnostic textuel explicite plutôt qu'icônes ambiguës.
- **Pas d'anxiété de régression** → le feedback de chargement du dry-run reste visuellement contenu dans le périmètre de la commande/colonne override, jamais un indicateur de chargement au niveau de toute la fiche équipement.
- **Blocage vécu comme normal, pas comme un échec** → ton neutre et factuel pour les messages de diagnostic ("Capability X manquante"), pas de rouge alarmant ni de vocabulaire d'erreur ; lien direct vers la capability manquante pour transformer le blocage en prochaine action claire.
- **Moment de succès marqué** → seule exception au ton sobre général : un signal positif franc (vert net) au passage en statut ✅, pour ancrer un vrai moment de satisfaction sans réintroduire de bruit visuel ailleurs sur l'écran.

### Emotional Design Principles

1. La compréhension prime sur la vitesse : chaque interaction doit renforcer le sentiment de contrôle de Sébastien, pas seulement raccourcir son parcours.
2. Le périmètre visuel du feedback (chargement, diagnostic) doit toujours rester lisible comme circonscrit à jeedom2ha/HA, jamais comme touchant Homebridge.
3. Le vocabulaire des états doit rester neutre et factuel en cas de blocage, et ne s'autoriser un signal fort (couleur, emphase) qu'au moment du succès confirmé.
4. Toute réussite passée doit rester immédiatement reconnaissable en cas de retour ultérieur sur l'écran — pas de redécouverte de l'outil à chaque session.

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

Sébastien n'a qu'une seule référence directe : **Homebridge**, et son jugement est net et asymétrique.

- **Configuration (point fort)** : l'expérience Homebridge de saisie/édition des plugins et de leurs paramètres est jugée bonne — claire, structurée, prévisible.
- **Diagnostic et projection (point faible)** : c'est précisément là que Homebridge échoue. Aucun retour clair sur *pourquoi* un accessoire ne se comporte pas comme attendu côté HomeKit, aucune vue de "ce qui sera projeté" avant de le découvrir en vrai dans l'app Maison. Sébastien configure à l'aveugle, puis constate le résultat après coup — exactement le vécu qu'on a identifié en step 3-4 comme contre-modèle à ne pas reproduire.

Aucune autre application n'est citée comme référence — pas d'inspiration cross-catégorie (pas d'outil de dev, pas d'app grand public). La contrainte explicite est de **rester dans les standards Jeedom et plugin Jeedom** plutôt que d'importer des patterns d'interfaces extérieures à l'écosystème.

### Transferable UX Patterns

**Patterns à emprunter à Homebridge (partie configuration) :**

- Structure de saisie par accessoire/commande, prévisible et cohérente d'un item à l'autre — déjà aligné avec le triptyque natif/override/diagnostic acté en step 3.
- Clarté du contour de ce qui appartient à quel plugin — cohérent avec l'onglet "HA / jeedom2ha" séparé des onglets natifs Homebridge (step 3, Persona 3).

**Patterns issus des standards Jeedom/plugin (source principale d'inspiration) :**

- Réutiliser les composants d'admin Jeedom déjà connus de Sébastien (onglets de fiche équipement, badges de statut, alertes contextuelles) plutôt qu'introduire un vocabulaire visuel nouveau — cohérence avec toute l'interface qu'il utilise déjà au quotidien.
- S'appuyer sur les conventions jQuery/Bootstrap déjà en place dans l'admin Jeedom (accordéons, badges colorés, tooltips) pour l'implémentation des zones définies en step 3, sans composant générique réinventé.

### Anti-Patterns to Avoid

- **Configurer à l'aveugle sans retour de projection** (l'anti-pattern central de Homebridge) — c'est exactement ce que le dry-run instantané (step 3-4) doit éliminer.
- **Découvrir le résultat après coup plutôt qu'avant validation** — tout écart entre écran de config et comportement réel côté HA doit être visible *avant* que Sébastien ne quitte l'écran, jamais après.
- **Introduire une esthétique ou des composants étrangers aux standards Jeedom/plugin** — un écran qui "ne ressemble pas à Jeedom" créerait une rupture de confiance et casserait le sentiment de continuité acté en step 3 ("continuité de la fiche équipement existante, pas un outil à part").

### Design Inspiration Strategy

**What to Adopt:**

- La clarté structurelle de la configuration Homebridge (saisie prévisible, un item à la fois) — parce qu'elle soutient directement le workflow séquentiel commande par commande déjà tranché en step 4.
- Les composants d'admin standards Jeedom (onglets, badges, accordéons Bootstrap) — parce qu'ils garantissent la continuité visuelle et la confiance immédiate de Sébastien.

**What to Adapt:**

- Le principe de statut par item (présent chez Homebridge) — à enrichir avec le diagnostic actionnable (reason_details + lien vers la capability manquante) que Homebridge n'offre pas du tout.

**What to Avoid:**

- Le silence diagnostique de Homebridge — conflit direct avec l'objectif "en contrôle" (step 4) et la clarté rétrospective attendue par Sébastien.
- Tout pattern visuel ou composant hors standards Jeedom/plugin — ne correspond pas à la contrainte explicite de rester dans l'écosystème natif de l'admin Jeedom.

Cette stratégie confirme et renforce les décisions déjà prises en step 2-4 (disclosure progressive, séparation stricte native/override, dry-run instantané) plutôt que d'introduire de nouvelles directions — logique, puisque la seule référence disponible (Homebridge) est surtout utile en contre-exemple.

## Design System Foundation

### 1.1 Design System Choice

Design system natif Jeedom : réutilisation des composants d'admin déjà en place dans l'écosystème de plugins Jeedom (onglets de fiche équipement, badges de statut, accordéons Bootstrap, tooltips) — pas de bibliothèque de composants externe (Material, Ant, Tailwind UI, etc.).

### Rationale for Selection

- Cohérence visuelle immédiate avec le reste de l'admin Jeedom que Sébastien utilise déjà au quotidien — aucun nouveau vocabulaire visuel à apprendre.
- Aligné avec la contrainte explicite du step 5 : rester dans les standards Jeedom et plugin Jeedom plutôt qu'importer des patterns extérieurs à l'écosystème.
- Zéro dette technique ou dépendance JS supplémentaire, cohérent avec la contrainte "desktop only, vanilla jQuery/Bootstrap" actée en step 3.
- Renforce le sentiment "en contrôle" et la continuité (step 4) : un écran qui ressemble au reste de Jeedom ne déclenche pas de rupture de confiance.

### Implementation Approach

Réutiliser les classes et patterns Bootstrap déjà présents dans les autres onglets de plugins Jeedom (y compris ceux d'Homebridge, pour la cohérence inter-plugins visible par Sébastien) — accordéons `<details>`/panels existants pour la hiérarchie pièce → équipement → commande, badges de statut standards, tooltips natifs. Pas de thème CSS dédié ni de composant générique réinventé.

### Customization Strategy

Personnalisation strictement limitée à ce qui sert les principes actés en step 4 : un signal de couleur verte franche au moment du succès (statut ✅), un ton neutre et factuel partout ailleurs (pas de rouge alarmant pour les blocages). Aucune refonte visuelle globale, aucune identité graphique propre à cet écran.

## 2. Core User Experience

### 2.1 Defining Experience

L'interaction qui définit le produit : **éditer un `ha_entity_type` sur une commande et voir instantanément si elle est projetable sur HA, sans quitter la fiche équipement Jeedom**. Si cette interaction précise fonctionne parfaitement, tout le reste (arborescence, historique, edge cases) devient secondaire — c'est elle que Sébastien décrirait s'il devait résumer "ce que fait jeedom2ha pour le mapping HA" en une phrase : *"je choisis un type, et je sais tout de suite si ça marche et pourquoi."*

### 2.2 User Mental Model

- **Modèle actuel (Homebridge)** : configurer → sauvegarder → sortir de l'écran → aller vérifier dans l'app HomeKit si le comportement est le bon. Un aller-retour mental coûteux, sans garantie, où l'échec ne se découvre qu'après coup.
- **Frustration principale** : l'absence totale de retour sur la projection avant de "sortir" de l'outil de configuration — Sébastien configure à l'aveugle puis constate.
- **Rupture attendue avec jeedom2ha** : dès l'ouverture de l'onglet "HA / jeedom2ha", l'utilisateur doit sentir qu'il n'aura *pas besoin* de sortir de l'écran pour vérifier quoi que ce soit — le diagnostic est intégré, immédiat, et fait autorité (il reflète l'exacte réalité de ce que `decide_publication` publierait).

### 2.3 Success Criteria

Le badge vert seul ne suffit pas à convaincre un utilisateur échaudé par Homebridge. Le succès doit s'accompagner d'un contenu explicite, pas seulement d'un statut :

- Le diagnostic affiche ce qui a été validé concrètement (ex. "capability X détectée, mapping Y confirmé"), en réutilisant `reason_details` **aussi en mode succès** — jusqu'ici sous-exploité en mode échec uniquement dans les steps précédents.
- Vitesse perçue : retour sous 200ms (indicateur de chargement) puis résultat sous 300-500ms (débounce), sinon Sébastien croit que rien ne se passe.
- Ce qui doit arriver automatiquement : le recalcul du diagnostic dès sélection d'un `ha_entity_type`, sans action de validation séparée (cf. 2.5).

**Indicateurs de succès :**
- [ ] Sébastien comprend *pourquoi* ça marche, pas seulement *que* ça marche.
- [ ] Aucun aller-retour vers un autre écran (HA, Homebridge) n'est nécessaire pour confirmer le résultat.
- [ ] Le même niveau de confiance est retrouvé instantanément lors d'un retour sur l'écran plusieurs jours après.

### 2.4 Novel UX Patterns

- **Établi, pas de pédagogie nécessaire** : la structure en onglets/accordéons de fiche équipement est un pattern que Sébastien connaît déjà via Homebridge et le reste de l'admin Jeedom.
- **Nouveau dans cet écosystème** : le triptyque "natif (lecture seule) / override (éditable) / diagnostic" affiché côte à côte est inédit pour Sébastien dans ce contexte précis.
- **Stratégie retenue** : pas de tutoriel ni de couche pédagogique séparée. La pédagogie est portée par l'état lui-même — au tout premier accès sans override configuré, afficher explicitement "Aucun override configuré — voici ce qui sera utilisé par défaut" plutôt qu'un champ vide silencieux.

### 2.5 Experience Mechanics

**1. Initiation :**
Sébastien ouvre l'onglet "HA / jeedom2ha" sur la fiche d'un équipement. Un GET initial charge en un seul appel les statuts de toutes les commandes et leurs `reason_details`. Aucune action requise pour déclencher ce premier diagnostic.

**2. Interaction :**
Il ouvre l'accordéon d'une commande (les commandes bloquantes s'ouvrent automatiquement, plafonné à 3-4 pour éviter la surcharge), puis sélectionne/modifie un `ha_entity_type` dans la colonne override. Chaque édition déclenche un POST unique et séquentiel — un aller-retour dry-run par commande, jamais un batch groupé (tension tranchée à l'étape précédente).

**3. Feedback :**
Après débounce (300-500ms), le diagnostic se met à jour dans le périmètre visuel strict de la colonne override — jamais un indicateur de chargement global de la fiche équipement, pour ne jamais suggérer un impact sur Homebridge. En cas de blocage : message factuel et actionnable ("Capability X manquante pour ce type HA", avec lien direct vers où la configurer), explicitement recadré comme circonscrit à la projection HA ("aucun impact Homebridge"). En cas de succès : signal vert franc, avec le détail de ce qui a été validé (cf. 2.3).

**4. Completion :**
**Le dry-run réussi implique l'auto-validation de l'override** — pas de bouton "Enregistrer" séparé. Dès que le diagnostic passe au vert, cet état devient la réalité de ce qui sera publié : il n'y a qu'une seule étape de validation, pas deux. Sébastien peut revenir à la fiche équipement standard à tout moment sans action explicite de sauvegarde ; le dry-run réussi est déjà la vérité.

## Visual Design Foundation

### Color System

Aucune palette de marque propre à jeedom2ha : réutilisation stricte de la palette sémantique déjà en place dans l'admin Jeedom/Bootstrap (pas de nouvelles teintes introduites). Mapping sémantique conforme aux décisions du step 4 :

- **Succès (dry-run passé)** : vert franc et net — seule exception volontaire à la sobriété générale, pour ancrer le moment de satisfaction.
- **Blocage (dry-run en échec)** : teinte neutre (gris/ambre discret plutôt que rouge alarmant) — le rouge est explicitement évité pour ne pas évoquer une régression ou un danger côté Homebridge ; le message textuel factuel porte l'information, pas la couleur.
- **Natif Jeedom (lecture seule)** : traitement visuel neutre et légèrement estompé (grisé), cohérent avec les conventions "champ désactivé" déjà utilisées dans l'admin.
- **Override HA (éditable)** : traitement visuel standard "champ actif" Bootstrap, sans couleur d'accent propre — la distinction avec le natif se fait par le contraste actif/lecture-seule, pas par une couleur dédiée à l'override.
- Conformité accessibilité : contrastes alignés sur les standards déjà validés de l'admin Jeedom (pas de vérification supplémentaire nécessaire, aucune nouvelle combinaison de couleur introduite).

### Typography System

- Typographie native de l'admin Jeedom, inchangée — aucune police ni échelle typographique propre à cet écran.
- Ton rédactionnel : sobre et factuel technique, cohérent avec l'objectif "en contrôle" (step 4) — pas de formulations enjouées ou marketing.
- Contenu majoritairement composé de libellés courts et badges au niveau fermé (arborescence dense), avec des phrases de diagnostic plus longues (ex. "Capability X manquante pour ce type HA") uniquement au niveau ouvert du triptyque — la hiérarchie typographique existante (corps de texte standard pour le diagnostic, libellés en gras/petite taille pour les statuts) suffit, sans nouvelle échelle.

### Spacing & Layout Foundation

- Densité par défaut : compacte, façon Homebridge — l'arborescence pièce → équipement → commande fermée doit rester scannable rapidement sur un parc de 284 équipements, sans espacement excessif qui allongerait le scroll.
- Aération ciblée : uniquement à l'intérieur d'une commande ouverte (triptyque natif/override/diagnostic), où l'espace doit permettre de lire confortablement les trois colonnes côte à côte sans les tasser.
- Unité de base et grille : spacing Bootstrap standard déjà en usage dans les autres onglets de plugins Jeedom (y compris Homebridge) — aucun système d'espacement personnalisé, pour garantir la continuité visuelle actée en step 3 et 6.

### Accessibility Considerations

- Le blocage ne repose jamais uniquement sur la couleur : le message textuel factuel ("Capability X manquante...") est la source d'information primaire, la teinte neutre n'est qu'un renfort visuel secondaire — conforme au principe de ne pas coder l'information uniquement par la couleur.
- Le contraste lecture-seule (natif) vs éditable (override) doit rester perceptible même sans couleur d'accent, via les conventions standards Jeedom de champs désactivés (déjà conformes aux contrastes de l'admin existant).
- Aucune nouvelle vérification d'accessibilité requise au-delà de l'existant : le choix de ne rien réinventer visuellement (color system, typographie, spacing) hérite directement de la conformité déjà validée de l'admin Jeedom natif.

## Design Direction Decision

### Design Directions Explored

Vu les contraintes déjà verrouillées (step 5 : standards Jeedom stricts, step 8 : aucune nouvelle palette/typo), l'exploration a porté uniquement sur l'organisation de la liste des commandes au sein de l'onglet, pas sur une nouvelle esthétique :

- **Direction 1 — Liste plate** : toutes les commandes de l'équipement en accordéons au même niveau, dans l'ordre natif Jeedom.
- **Direction 2 — Priorité aux blocages** : les commandes bloquantes remontent en tête et s'auto-ouvrent (plafonné à 3-4), le reste replié sous "Autres commandes".
- **Direction 3 — Bandeau résumé sticky** : reprend la Direction 2, avec le bandeau résumé global (✅/⚠️/❌) fixé en haut pendant le scroll.

### Chosen Direction

**Direction 1 — Liste plate**, sans réordonnancement ni bandeau sticky.

### Design Rationale

Reste fidèle à l'ordre natif Jeedom des commandes, sans logique de tri additionnelle à maintenir ni à expliquer à l'utilisateur — cohérent avec la contrainte "rester dans les standards Jeedom/plugin" (step 5) et avec le principe de continuité de la fiche équipement existante (step 3). L'auto-ouverture plafonnée des commandes bloquantes (actée en step 3/7) reste appliquée à l'intérieur de cette liste plate — elle n'exige pas de réordonnancement structurel, juste un état d'ouverture par défaut différent selon le statut de chaque accordéon.

### Implementation Approach

Rendu en accordéons Bootstrap standards, un par commande, dans l'ordre de retour natif de l'API Jeedom pour l'équipement — aucun tri, regroupement ou repositionnement côté front. Le bandeau résumé reste un bloc statique en tête de l'onglet (non sticky), cohérent avec l'absence de traitement spécial de layout au-delà de ce qui est déjà acté.

## User Journey Flows

**Fondation PRD** : Parcours 3 — Sébastien, utilisateur expert : *"Je pilote la projection au lieu de la subir"* (prd.md, l.134-138). Ce parcours (antérieur à l'epic 16) pose l'exigence de fond : voir ce que le moteur aurait décidé nativement, ce qui a été surchargé, et les conséquences de cette surcharge dans le diagnostic, avec traçabilité de la décision — "je publie en connaissance de cause, sans perdre la traçabilité de la décision." Les deux flows ci-dessous traduisent cette exigence en mécanique concrète pour l'écran 16b.

### Rendre une commande projetable (happy path)

```mermaid
flowchart TD
    A[Ouvre onglet "HA / jeedom2ha" sur la fiche équipement] --> B[GET initial: statuts + reason_details de toutes les commandes]
    B --> C[Bandeau résumé global affiché ✅/⚠️/❌]
    C --> D[Ouvre l'accordéon d'une commande]
    D --> E[Voit triptyque: natif lecture-seule / override éditable / diagnostic]
    E --> F[Sélectionne un ha_entity_type dans override]
    F --> G[Débounce 300-500ms, indicateur visible sous 200ms]
    G --> G2{Nouvelle édition pendant le débounce ?}
    G2 -->|Oui| F
    G2 -->|Non| H[POST dry-run sur cette commande uniquement; tout POST précédent en vol est annulé/ignoré]
    H --> I{Résultat}
    I -->|Succès| J[Diagnostic vert franc + détail: capability X détectée, mapping Y confirmé]
    J --> K[Auto-validation: l'override devient l'état réel, pas de bouton Enregistrer]
    K --> L[Sébastien referme l'accordéon ou passe à la commande suivante]
```

### Diagnostiquer un blocage et le résoudre

```mermaid
flowchart TD
    A[Commande bloquante détectée au GET initial] --> B[Auto-ouverture, plafonnée à 3-4 commandes]
    B --> C[Diagnostic neutre/factuel: "Capability X manquante pour ce type HA"]
    C --> D{Premier blocage rencontré sur cet équipement ?}
    D -->|Oui| D2[Affiche une fois: "aucun impact Homebridge"]
    D -->|Non| E[Lien direct vers où configurer la capability manquante]
    D2 --> E
    E --> F{Sébastien corrige la capability ailleurs puis revient}
    F -->|Oui| G[Retour sur l'onglet: ancre de commande stable, GET refait office de source de vérité systématique]
    G --> H[Correction externe visible sans action manuelle; rouvre la commande, re-sélectionne le ha_entity_type]
    H --> I[Nouveau dry-run: succès --> Flow "happy path" étapes G-K]
    F -->|Pas encore| J[Referme l'accordéon: statut reste ⚠️/❌ dans le bandeau résumé, aucune perte d'état]
```

### Journey Patterns

**Navigation** : un seul niveau de navigation supplémentaire par commande (accordéon), pas de sous-écran ni de page dédiée ; ancre de commande stable pour permettre un retour direct après une correction externe (capability configurée ailleurs).

**Décision** : "un `ha_entity_type` = un dry-run = une vérité" — jamais de validation en deux temps ; le GET initial est systématiquement la source de vérité (pas de cache front), donc une correction externe redevient visible sans action manuelle de l'utilisateur.

**Feedback** : toujours circonscrit visuellement à la colonne override de la commande concernée ; le message "aucun impact Homebridge" n'apparaît qu'une seule fois par équipement (au premier blocage rencontré), pour rester rassurant sans devenir du bruit répétitif.

### Flow Optimization Principles

- **Efficacité** : annulation du POST précédent si une nouvelle édition survient pendant le débounce, pour éviter qu'un résultat obsolète s'affiche après un résultat plus récent (race condition).
- **Continuité entre sessions** : le bandeau résumé global se comporte comme une mémoire persistante de l'équipement — fermer l'onglet et revenir plus tard restitue exactement le même état, sans perte d'override validé.
- **Non-répétition du message de réassurance** : "aucun impact Homebridge" affiché une seule fois par équipement plutôt qu'à chaque commande bloquée, pour préserver sa valeur rassurante.
- **Retour après correction externe** : l'ancre de commande stable évite à Sébastien de devoir rechercher manuellement quelle commande était bloquée dans la liste plate (Direction 1, step 9).

## Component Strategy

### Design System Components

Déjà disponibles nativement (Bootstrap/Jeedom, step 6) : onglets de fiche équipement, accordéons, badges de statut, tooltips, conventions visuelles champ désactivé/actif.

### Custom Components

**Triptyque commande** (natif lecture-seule / override éditable / diagnostic) — composant central, inédit dans l'écosystème Jeedom. Largeur relative fixe et ordre stable des 3 colonnes (natif toujours à gauche, override au milieu, diagnostic à droite), constants d'une commande à l'autre pour permettre un scan rapide.

**Bandeau résumé équipement** — statut global agrégé ✅/⚠️/❌ (un seul appel `validate_projection()`, step 3), non sticky (step 9). Son état de chargement initial (premier GET) est visuellement distinct de l'indicateur de dry-run d'une commande, pour ne jamais laisser croire que tout l'équipement recalcule alors qu'une seule commande est concernée. Son statut agrégé porte une ancre directe vers la première commande bloquante — jamais un chiffre abstrait sans lien d'action.

**Indicateur de dry-run** — circonscrit à la colonne override d'une commande, visible sous 200ms. Aucun flash intermédiaire "annulé/erreur" en cas de nouvelle édition pendant le débounce : l'indicateur reste en état chargement jusqu'au nouveau résultat, pour préserver la fluidité perçue.

**Bandeau de réassurance Homebridge** — composant séparé du message de diagnostic récurrent, affiché une seule fois par équipement au premier blocage rencontré ("aucun impact Homebridge"), pour rester auditable/testable indépendamment du diagnostic lui-même.

### Component Implementation Strategy

Tous les composants custom s'appuient sur les tokens du design system natif (step 8 : palette, typo, spacing Bootstrap standard) — aucun nouveau vocabulaire visuel. Le triptyque et le bandeau résumé sont les deux composants dont la cohérence structurelle (largeur des colonnes, distinction des granularités de chargement) est non négociable, car ils portent directement les objectifs "en contrôle" et "pas d'anxiété de régression" du step 4.

### Implementation Roadmap

**Phase 1 — Composants cœur** : Triptyque commande et indicateur de dry-run — nécessaires au flow "Rendre une commande projetable" (step 10, happy path).

**Phase 2 — Composants de support** : Bandeau résumé équipement avec ancre vers la première commande bloquante — nécessaire au flow "Diagnostiquer un blocage et le résoudre" (step 10).

**Phase 3 — Composant de renforcement** : Bandeau de réassurance Homebridge — améliore la confiance perçue sans être bloquant pour le happy path, peut suivre une fois les deux premières phases stabilisées.

## UX Consistency Patterns

### Feedback Patterns

- **Succès** : signal vert franc, exception assumée à la sobriété générale (step 4/8), accompagné du détail concret validé (`reason_details` en mode succès, step 7) — jamais une simple coche sans texte.
- **Blocage** : teinte neutre (jamais rouge, step 8), message factuel et actionnable ("Capability X manquante pour ce type HA" + lien direct), ton qui présente le blocage comme une étape normale du diagnostic, pas un échec (step 4).
- **Chargement** : deux granularités visuellement distinctes et non interchangeables — chargement global du bandeau résumé (premier GET de l'onglet) vs chargement local d'une commande (dry-run, circonscrit à la colonne override), visible sous 200ms, résultat sous 300-500ms (step 3/11).
- **Réassurance contextuelle** : "aucun impact Homebridge" comme composant séparé, affiché une seule fois par équipement au premier blocage, jamais répété à chaque commande (step 10/11).

### Form Patterns

- Un seul champ éditable par commande : la sélection du `ha_entity_type` en colonne override — pas de formulaire multi-champs à valider globalement.
- Pas de bouton "Enregistrer" séparé : la validation est portée par le dry-run lui-même, auto-appliqué dès succès (step 7, 2.5) — aucune double étape de validation.
- Race condition gérée en amont du pattern de formulaire : toute nouvelle édition pendant le débounce annule la requête précédente sans flash d'état intermédiaire (step 10/11).

### Additional Patterns — État vide

- Commande sans override configuré : afficher explicitement "Aucun override configuré — voici ce qui sera utilisé par défaut" (valeur native) plutôt qu'un champ vide silencieux (step 7, 2.4) — la pédagogie du triptyque est portée par cet état lui-même, pas par un tutoriel séparé.
- Équipement sans commande bloquante au premier chargement : le bandeau résumé affiche directement un statut ✅ global, sans nécessiter d'ouverture manuelle d'accordéon pour le confirmer.

### Design System Integration

Tous ces patterns s'appuient sur les composants Bootstrap/Jeedom déjà en place (badges, accordéons, tooltips, champs actif/désactivé) — aucune nouvelle brique visuelle introduite au-delà des 4 composants custom actés en step 11. Catégories volontairement écartées comme non pertinentes pour cet écran : hiérarchie de boutons multiples (un seul geste d'édition par commande, pas de CTA concurrents), navigation complexe (point d'entrée unique déjà défini en step 3), modales/overlays (aucune prévue), recherche/filtrage (hors scope Story 16b).

## Responsive Design & Accessibility

### Responsive Strategy

Desktop uniquement (souris/clavier), conformément à la contrainte actée en step 3 — aucune adaptation tablette ou mobile à concevoir pour Story 16b. L'écran cible une seule plage d'affichage desktop, ce qui simplifie la densité d'information (liste plate, step 9) sans compromis de lisibilité à gérer sur petit écran.

### Breakpoint Strategy

Pas de breakpoints supplémentaires : un seul rendu desktop (≥1024px), aligné sur les autres onglets de plugins Jeedom déjà en place. Aucune stratégie mobile-first ni desktop-first à arbitrer, la question ne se pose pas hors périmètre desktop.

### Accessibility Strategy

Niveau visé : **WCAG AA**, cohérent avec le standard déjà en usage dans l'admin Jeedom. Points clés :

- Contrastes hérités de l'admin Jeedom natif (aucune nouvelle combinaison de couleur introduite, step 8).
- Information jamais codée uniquement par la couleur : le message factuel de diagnostic prime toujours sur la teinte (succès vert / blocage neutre, step 8/12).
- Navigation clavier complète sur les accordéons de commande et le triptyque (natif / override / diagnostic) — tabulation logique dans l'ordre des 3 colonnes (step 11).
- Labels ARIA sur les 4 composants custom (triptyque, bandeau résumé, indicateur de dry-run, bandeau de réassurance Homebridge) pour une lecture correcte par lecteur d'écran, notamment sur les transitions d'état (chargement → succès/blocage).
- Cibles tactiles non applicables (desktop only, pas d'exigence de taille minimale 44x44px liée au tactile).

### Testing Strategy

Réutilisation des pratiques déjà en place sur l'admin Jeedom/plugins : tests navigateur desktop standards (Chrome, Firefox), vérification clavier-only sur les accordéons et le triptyque, contrôle de contraste hérité (pas de nouvelle vérification si aucune nouvelle couleur n'est introduite). Pas de protocole de test spécifique mobile/tablette à prévoir, hors périmètre.

### Implementation Guidelines

- Structure HTML sémantique pour les accordéons et le triptyque (pas de div génériques sans rôle).
- ARIA labels et rôles sur les 4 composants custom, en particulier pour signaler les changements d'état dynamiques (dry-run en cours, résultat succès/blocage) aux lecteurs d'écran.
- Gestion du focus clavier cohérente avec l'auto-ouverture des commandes bloquantes (step 3/10) : le focus ne doit pas sauter de façon surprenante lors de l'ouverture automatique de plusieurs accordéons au chargement.
- Pas d'unités responsive spécifiques (rem/vw/vh) au-delà des conventions déjà utilisées dans l'admin Jeedom, aucun media query supplémentaire nécessaire (desktop only).
