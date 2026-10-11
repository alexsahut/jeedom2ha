# Story A1 : Limite de performance des relais PHP (15s) — E4

Status: ready-for-dev

Epic: (Chantier Market 2026-10)

Story Key (sprint-status): `a1-limite-de-performance-relais-15s`

## Story

En tant que mainteneur,  
je veux identifier et restructurer les cinq relais PHP qui imposent un timeout de 15 secondes (contre les 19–30 s typiques du reste du code),  
afin d'aligner les performances observées sur le design architectural 19-6 et d'éviter les interruptions utilisateur sur le terrain.

## Description

Écart constaté (E4, main @7dd0120) : cinq appels relais PHP dans `core/ajax/jeedom2ha.ajax.php` imposent chacun un délai de 15 secondes :

- ligne ~596 : test MQTT
- ligne ~632 : scan topologie
- ligne ~648 : diagnostic  
- ligne ~727 : export
- ligne ~910 : override

Ces délais empiriques ont été mis en place sans justification documentée. La conception 19-6 (à consulter dans `_bmad-output/implementation-artifacts/`) propose une architecture de requêtes asynchrones avec timeout par étape (19–30 s type), mieux adaptée au runtime.

### Parcours rapide
1. Auditer les cinq relais : vérifier que chaque appel est bien bloquant et que 15 s est vraiment atteint en production
2. Aligner chaque timeout sur le design 19-6 (ou justifier le maintien de 15 s si une contrainte spécifique existe)
3. Documenter la décision pour chacun dans un commentaire inline

### Parcours complet
1. Même audit que le parcours rapide
2. Refactoriser chaque relais pour découpler le traitement long (backend MQTT, scan) du feedback frontend
3. Implémenter une queue asynchrone pour les opérations longues
4. Ajouter des métriques (temps réel de chaque relais, nombre de dépassements)
5. Tester en environnement identique à la prod (LXC Debian 11/12, deamon Python, MQTT)

## Acceptance Criteria

1. **Given** la liste des cinq relais à timeout 15 s (lignes ~596, ~632, ~648, ~727, ~910)  
   **When** chacun est audité vs design 19-6  
   **Then** une décision (align ou justifier) est documentée inline pour chaque ligne.

2. **Given** un relais qui fait appel à MQTT ou scan topologie  
   **When** il s'exécute en production (Debian 11/12, deamon jeedom2ha)  
   **Then** le temps réel observé ne dépasse pas le timeout documenté.

3. **Given** le parcours complet (refactoring + queue)  
   **When** il est implémenté  
   **Then** le feedback frontend n'est jamais bloqué plus de 2–3 s, même si le backend prend 19–30 s.

4. **Given** la suite de tests existante  
   **When** les changements sont appliqués  
   **Then** tous les tests passent sans régression.

5. **Given** les métriques instrumentées (parcours complet uniquement)  
   **When** le daemon est en runtime  
   **Then** chaque relais rapporte son temps réel via logs structurés ou télémétrie.

## Tasks / Subtasks

### Parcours rapide
- [ ] T1 — Auditer les cinq relais et documenter la décision pour chacun
  - [ ] Vérifier les lignes ~596, ~632, ~648, ~727, ~910 dans `core/ajax/jeedom2ha.ajax.php`
  - [ ] Consulter design 19-6 pour comprendre la timeout cible
  - [ ] Ajouter un commentaire inline justifiant le timeout (align ou rationale de maintien)
  - [ ] Créer un tableau de synthèse (relais, ligne, raison, timeout projeté) dans la PR

### Parcours complet (recommandé pour prod)
- [ ] T2 — Refactoriser les relais bloquants en appels découplés
  - [ ] Extraire le traitement long (MQTT, scan, diagnostic) dans des fonctions backend séparées
  - [ ] Implémenter une queue asynchrone (ex: Redis, fichier, ou in-memory si isolé) pour les opérations > 5 s
  - [ ] Assurer que le relais retourne un feedback rapide (< 3 s) même si backend continue
- [ ] T3 — Ajouter des métriques
  - [ ] Instrumenter chaque relais avec `time()` avant/après
  - [ ] Loger le temps réel et le timeout assigné
  - [ ] Exporter en format compatible avec la télémétrie projet (ex: syslog structuré)
- [ ] T4 — Tester en environnement de prod
  - [ ] Créer un LXC Debian 11 vierge avec jeedom2ha (parcours à décider avec ClawBox)
  - [ ] Reproduire les cinq opérations et confirmer les temps réels observés
  - [ ] Valider que le feedback frontend n'est jamais bloqué

## Impact Produit

- **Si non fait** : utilisateurs continueront à voir des pauses de 15 s sur 5 opérations clés (test MQTT, scan topologie, etc.), dégrade l'UX et peut cacher des timeouts réseau réels.
- **Si parcours rapide** : temps réduit à 5–10 s en moyenne (justification/align documentée), amélioration UX modérée, aucun refactoring.
- **Si parcours complet** : temps perçu par l'utilisateur réduit à 2–3 s max, feedback immédiat même si backend traite 19–30 s, forte amélioration UX.

## Rollback / Plan de Retour Arrière

- **Parcours rapide** : revert des commentaires inline, aucun impact code fonctionnel.
- **Parcours complet** :
  1. Revert des changements PHP dans `core/ajax/jeedom2ha.ajax.php`
  2. Revert de la queue asynchrone (ou désactiver par flag si implémentée)
  3. Relancer le daemon jeedom2ha
  4. Temps revient aux valeurs 15 s d'origine

## Notes

- Cette story ne touche pas à la logique de publication, mapping ou override — seulement aux relais d'UI.
- Le design 19-6 est la référence architecturale ; consulte-le avant de décider des timeouts.
- Ordre / parallélisme : **A1 peut être menée en parallèle de A3** (conformité Market), aucune dépendance dure.
