# Story 20.3 — audit préparatoire local

**Date :** 2026-10-08
**SHA lu :** `9d8f2dce30e8b887ced76a5c23b7161b0b66a13f` (`main`)
**Nature :** lecture seule du code et des tests ; aucun accès box/HA, aucun test terrain, aucun changement de statut.

## Résultat

Les faits F1 à F7 de la story sont toujours exacts au SHA lu. Le code de 20.2 est déjà intégré ; sa clôture terrain/UX reste le seul prérequis de statut avant `ready-for-dev`. Cet audit prépare le futur `dev-story` sans anticiper ce passage.

## Revalidation après clôture 20.2

**SHA relu :** `b2a89dfbc74c80901cfb2bf0292e108cfa3ac5d1` (`main`), le 2026-10-08.

- F1 à F7 sont inchangés; les routes d'export/support et leurs relais backend restent hors retrait.
- La recherche F6 retrouve les mêmes 22 références tests/gate; aucun texte CSS généré par `content:` n'est concerné.
- Alexandre a validé la table de libellés proposée le 2026-10-08 (« table 20.3 OK »). Les formulations validées sont intégrées à la section suivante et l'inventaire exhaustif de code reste une tâche de développement, au SHA de la branche de réalisation.

### Table de libellés validée

| Chaîne actuelle | Traitement validé |
| --- | --- |
| `Configuration mapping Home Assistant par pièce` | `Configuration Home Assistant par pièce` |
| `Mes templates` et le message d'absence Template | suppression |
| `Paramètres spécifiques`, `Nom du paramètre n°1`, `Paramètre n°1`, `Mot de passe`, `Auto-actualisation` et assistant cron | suppression |
| `Aucun mapping trouvé…` / `aucun mapping ne couvre…` | `Aucun type Home Assistant identifié…` / `Aucun type Home Assistant ne couvre…` |
| `mapping ambigu` | `type Home Assistant ambigu` |
| `mapping direct` | `type Home Assistant identifié` |
| `commande non couverte par un mapping` | `commande sans type Home Assistant applicable` |

Les identifiants techniques (`eq_id`, `reason_code`, noms de routes) restent internes et ne sont jamais rendus.

## Inventaire initial des libellés d'usage

| Chaîne actuelle | Traitement 20.3 acté | Libellé/issue cible |
| --- | --- | --- |
| `Synthèse du périmètre publié`, `Parc global` | retrait | aucun : la surface par pièce remplace la synthèse |
| `Diagnostic`, `Diagnostic de Couverture`, `Écart`, `Confiance` | retrait | aucun : la cause par commande reste dans la surface ; l'export support est conservé |
| `Parité FAN → switch` | retrait | aucun : décision Q3=A |
| `Mes templates`, `Aucun équipement Template trouvé…` | retrait | aucun : la liste de gabarits n'est pas une surface produit |
| `Paramètres spécifiques` | retrait | les champs sans usage disparaissent |
| `Nom du paramètre n°1`, `Paramètre n°1` | retrait | champ `param1` supprimé |
| `Mot de passe` | retrait | champ `configuration.password` supprimé |
| `Auto-actualisation`, l'assistant cron associé | retrait | champ `configuration.autorefresh` supprimé |
| `Configuration mapping Home Assistant par pièce` | réécriture | `Configuration Home Assistant par pièce` |
| `mapping` dans les explications affichées à l'utilisateur | réécriture ciblée | `configuration Home Assistant` ou formulation métier équivalente ; ne pas modifier les clés/contrats internes |

La vérification exhaustive (PHP, JS et CSS `content:`) reste une tâche de développement : elle doit être rejouée au SHA où 20.2 sera `done`, puis la table finale sera soumise à Alexandre avant le remplacement des chaînes hors liste ci-dessus.

## Réaffectation des références de tests et du gate

| Référence actuelle | Décision préparée |
| --- | --- |
| `tests/e2e/gate/lib/policy.mjs` | retirer l'autorisation de lecture `getPublishedScopeForConsole`; conserver le refus par défaut |
| `tests/e2e/gate/page-load-request-inventory.mjs` | retirer l'attente de la requête de synthèse ; ajouter l'absence de `getPublishedScopeForConsole` et `getDiagnostics` |
| `tests/test_php_published_scope_relay.php`, `tests/unit/test_story_5_1_php_relay.php` | conserver les relais : les routes ne sont pas supprimées (AC7) ; retirer seulement l'hypothèse qu'ils alimentent l'UI |
| `test_scope_summary_presenter.node.test.js` | retirer avec `jeedom2ha_scope_summary.js` |
| `test_story_15_2_streaming_badge_console.node.test.js`, `test_story_15_3_fan_parity_badge_console.node.test.js` | retirer les assertions de badges UI retirés par Q3=A ; préserver toute couverture daemon indépendante |
| `test_story_3_4_ai5_frontend_passthrough.node.test.js`, `test_story_4_2_vocab_exclusion.node.test.js`, `test_story_4_3_diagnostic_in_scope.node.test.js`, `test_story_4_4_integration_ui_4d.node.test.js`, `test_story_4_5_home_landing.node.test.js` | remplacer les assertions de synthèse/badge Écart par une assertion d'absence ; ne pas supprimer les couvertures de contrat backend |
| `test_story_4_2_diagnostic_decision.node.test.js`, `test_story_4_6_diagnostic_modal.node.test.js`, `test_story_6_1_pipeline_step.node.test.js`, `test_story_6_2_frontend_backend_first.node.test.js`, `test_story_6_3_honest_cause_mapping.node.test.js` | extraire/conserver les fonctions de contrat encore utiles sans la modale, ou déplacer leur couverture vers le démon ; supprimer la dépendance à `jeedom2ha_diagnostic_helpers.js` si aucun consommateur UI ne subsiste |
| `test_story_5_1_actions_ha_frontend.node.test.js`, `test_story_5_2_frontend.node.test.js`, `test_story_5_3_frontend.node.test.js`, `test_story_5_7_badge_suppr_harmonie.node.test.js` | migrer les assertions d'actions ciblées vers la modale de pièce; confirmer les mêmes routes et confirmations fortes |
| `test_story_5_4_bandeau.node.test.js` | déplacer `readOperationSnapshot` hors du module de synthèse ou tester son remplaçant ; le bandeau global est conservé |

## Points de contrôle pour le futur dev-story

1. Refaire cet audit au SHA post-clôture 20.2 : l'audit ne vaut pas attestation des Tasks 1.1–1.5.
2. Tracer les compteurs uniquement depuis l'arbre de la pièce ouverte ; aucun chargement global ni nouvelle décision frontend.
3. Préserver les routes de diagnostic et de périmètre pour l'export/support, même si l'interface ne les appelle plus au chargement.
4. Ne retirer un test historique qu'après avoir nommé sa couverture de remplacement ou constaté que la fonction produit est retirée par une décision Q3=A.
