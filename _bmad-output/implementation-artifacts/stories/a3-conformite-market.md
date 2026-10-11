# Story A3 : Conformité Market — E3, E5

Status: ready-for-dev

Epic: (Chantier Market 2026-10)

Story Key (sprint-status): `a3-conformite-market`

## Story

En tant que mainteneur,  
je veux vérifier et corriger l'absence de conformité du plugin aux exigences du Market Jeedom (info.json, version, description, changelogs),  
afin que la première publication soit acceptée et que les mises à jour utilisateurs fonctionnent correctement.

## Description

Écarts constatés (main @7dd0120) :

### E3 — info.json incomplet
- **description** : 60 caractères (< 80 exigés par le Market)
- **changelog_beta**, **documentation_beta** : absents (obligatoires par le Market)
- **changelog**, **documentation** : pointent sur blob/main (risque de 404 après publication)
- **link.forum** : vide
- **issue** : absent
- **language** : annonce `en_US` alors que seule la doc fr existe
- **compatibility luna/atlas** : non testée
- **plugin_info/template_icon.png** : fichier à supprimer (non conforme Market, remplacer par icon officiellement acceptée)

### E5 — Version incohérente
- **pluginVersion** (info.json) : `0.3.0`
- **Tag Git versionnel** : `v1.1.0`
- **Cible D6** : version `1.2.0`
- Incohérence à résoudre avant publication

### Livrable
1. **Correction info.json** :
   - Description : >= 80 car, claire et en français ou bilingue
   - changelog_beta, documentation_beta : ajouter avec contenu réel (ou renvois vers fichiers versionnés)
   - link.forum : remplir si existe, sinon documenter l'absence
   - issue : ajouter le lien de support (GitHub issues ou équivalent)
   - language : corriger selon la doc réelle (en_US si doc existe, sinon `fr_FR` si doc fr seule)
   - Tester compatibilité luna/atlas (ou documenter pourquoi non applicable)
   - template_icon.png : supprimer, fournir une icône conforme Market

2. **pluginVersion** : aligner sur `1.2.0` (D6)

3. **README utilisateur** : créer ou compléter pour la doc de première lecture utilisateur

4. **CI de validation** :
   - À chaque PR, vérifier la conformité info.json contre les règles Jeedom (anti-régression E3/E5)
   - Rejeter si description < 80 car, changelogs absents, ou version incohérente

### Parcours rapide
1. Lire le fichier `plugin_info/info.json` actuel et les exigences Market officielles
2. Corriger manuellement : description (80+ car), version 1.2.0, description_beta/changelog_beta, language, icon
3. Ajouter une brève validation en CI (shell script, 10 lignes)

### Parcours complet (recommandé pour prod)
1. Même corrections que parcours rapide
2. Créer un test CI Python : parser info.json, valider chaque champ contre un schéma Jeedom (min/max, types, champs obligatoires)
3. Implémenter un manifest de champs obligatoires pour le Market (version, description min 80 car, changelogs, etc.)
4. Ajouter un test de synthaxe JSON + test de présence des clés obligatoires
5. Documenter la procédure de maintien de conformité dans `docs/release-market.md`
6. Tester en Jeedom vierge (Debian 11/12, LXC à côté ClawBox) que le plugin s'installe sans erreur

## Acceptance Criteria

1. **Given** le fichier `plugin_info/info.json`  
   **When** la description est lue  
   **Then** elle contient >= 80 caractères et décrit clairement le plugin.

2. **Given** les champs `changelog_beta` et `documentation_beta`  
   **When** info.json est parsé  
   **Then** ces deux champs existent et contiennent du contenu réel (pas placeholder).

3. **Given** les URLs de changelog et documentation  
   **When** elles sont converties de blob/main en URLs stables (releases, tags, ou doc statique)  
   **Then** aucune URL ne pointe sur `blob/main` directement.

4. **Given** le champ `language`  
   **When** info.json est vérifié  
   **Then** il correspond à la langue réelle de la documentation disponible (en_US si doc en + fr, sinon fr_FR).

5. **Given** la version dans info.json  
   **When** la plugin est publiée  
   **Then** `pluginVersion` = `1.2.0` (D6) et correspond au tag Git versionnel.

6. **Given** l'icône du plugin  
   **When** elle est vérifiée  
   **Then** `template_icon.png` est supprimé, remplacé par une icône conforme Market (format, taille, visibilité).

7. **Given** la CI de validation conformité  
   **When** une PR est créée vers `main`  
   **Then** un job valide que info.json respecte le schéma Jeedom (anti-régression E3/E5).

8. **Given** un README utilisateur  
   **When** le plugin est installé pour la première fois  
   **Then** l'utilisateur dispose d'une doc claire sur installation, configuration, utilisation (liens vers docs détaillées).

## Tasks / Subtasks

### Parcours rapide
- [ ] T1 — Corriger info.json
  - [ ] Augmenter description à >= 80 car
  - [ ] Ajouter `changelog_beta` et `documentation_beta` (contenu réel ou renvoi)
  - [ ] Corriger `language` (en_US ou fr_FR selon doc)
  - [ ] Ajouter/compléter `issue`
  - [ ] Remplacer/supprimer template_icon.png
  - [ ] Changer `pluginVersion` en `1.2.0`

- [ ] T2 — Ajouter validation en CI (basique)
  - [ ] Créer un script shell simple : vérifier que description >= 80 car, pluginVersion contient "1.2.0"
  - [ ] Ajouter un step de validation à `.github/workflows/` ou tests existants

- [ ] T3 — Créer README utilisateur basique
  - [ ] Vue d'ensemble du plugin (1–2 paragraphes)
  - [ ] Prérequis d'installation
  - [ ] Lien vers la doc détaillée

### Parcours complet (recommandé)
- [ ] T4 — Implémenter test de conformité Jeedom
  - [ ] Créer `resources/daemon/tests/unit/test_info_json_compliance.py` ou équivalent
  - [ ] Parser info.json avec un schéma (JSON Schema ou validateur custom)
  - [ ] Vérifier champs obligatoires : name, description >= 80, pluginVersion, changelog, documentation, etc.
  - [ ] Tester les URLs (changelog, doc) en tant que liens valides (ou au moins bien formés)

- [ ] T5 — Tester en Jeedom vierge (parcours clawbox, isolé)
  - [ ] LXC Debian 11 vierge + Jeedom + installer le plugin depuis le paquet local
  - [ ] Vérifier qu'aucune erreur d'installation n'apparaît
  - [ ] Tester la première activation du daemon

- [ ] T6 — Documenter procédure conformité
  - [ ] `docs/release-market.md` : ajouter une section "Avant publication : checklist conformité"
  - [ ] Lister tous les champs info.json obligatoires
  - [ ] Ajouter des exemples de valeurs conformes

## Impact Produit

- **Si non fait** : première publication Market sera rejetée (description trop courte, changelogs manquants) ; utilisateurs ne verront pas de mise à jour proposée.
- **Si parcours rapide** : conformité minimale atteinte ; publication possible mais sans garantie de maintien de conformité future.
- **Si parcours complet** : conformité garantie par CI anti-régression, test en Jeedom vierge, procédure documentée ; publication Market stable et fiable.

## Rollback / Plan de Retour Arrière

- **Corrections info.json** : revert du commit modifiant `plugin_info/info.json` ; restaurer les valeurs antérieures.
- **CI check** : supprimer le job de validation ; conformité redevient manuelle.
- **Icon** : restaurer `template_icon.png` d'une branche antérieure si besoin.

## Notes

- Cette story a une dépendance douce avec A2 : A2 dépend d'un info.json stable pour définir la version du paquet (donc A3 doit être terminée avant A2 en prod, mais elles peuvent démarrer en parallèle).
- Ordre proposé : **A1 et A3 en parallèle, puis A2**.
- Consulter la doc officielle Jeedom Market (https://doc.jeedom.com/fr_FR/plugins/market/) pour les champs exactement obligatoires (peut avoir changé depuis oct 2026).
- Les URLs de documentation peuvent rester sur `blob/main` si elles sont versionnées (ex: `blob/v1.2.0/docs/...`) — à valider avec ClaudeBox.
