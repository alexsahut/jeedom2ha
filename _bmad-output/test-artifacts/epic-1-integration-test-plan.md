# Plan de Test Intégration — Epic 1 : Connectivité & Onboarding du Pont

**Date :** 2026-03-13
**Environnement :** Instance Jeedom de dev
**Prérequis :** Broker Mosquitto accessible (local ou distant), plugin mqtt2 installé et configuré (pour tests auto-détection)

> Cocher chaque case au fur et à mesure. Si un test échoue, noter le comportement observé en dessous.

---

## Prérequis Environnement

- [ ] Jeedom Core 4.4.9+ installé et fonctionnel
- [ ] Plugin jeedom2ha installé en mode développeur
- [ ] Dépendances installées (page plugin → "Installer les dépendances")
- [ ] Broker Mosquitto accessible (noter host/port/user/pass)
- [ ] Plugin mqtt2 installé et configuré (pour les tests d'auto-détection)
- [ ] Outil CLI disponible : `mosquitto_sub` (pour vérifier les messages MQTT)
- [ ] Accès aux logs Jeedom : Analyse → Logs → `jeedom2ha`

---

## 1. Daemon — Démarrage & Communication (Story 1.1)

### 1.1 Démarrage normal

- [ ] Aller dans Plugins → Gestion des plugins → jeedom2ha
- [ ] Cliquer "Activer" si le plugin n'est pas actif
- [ ] Cliquer "Démarrer" le démon
- [ ] **Attendu :** Le statut du démon passe à OK (pastille verte)
- [ ] **Vérifier les logs** (`jeedom2ha` en niveau DEBUG) : présence de `[DAEMON]` avec message de démarrage

### 1.2 Heartbeat / Liveness

- [ ] Le daemon est démarré
- [ ] Aller dans la page de gestion du plugin → le statut daemon est OK
- [ ] **Attendu :** Le daemon répond au healthcheck (le statut reste OK, pas de timeout)

### 1.3 Arrêt propre

- [ ] Cliquer "Arrêter" le démon
- [ ] **Attendu :** Le statut passe à NOK (pastille rouge)
- [ ] **Vérifier les logs** : présence du message de shutdown propre

### 1.4 Daemon ne répond pas

- [ ] Stopper le daemon manuellement (`kill -9` du process Python si nécessaire)
- [ ] Rafraîchir la page de gestion
- [ ] **Attendu :** Le statut est NOK — l'interface Jeedom affiche clairement que le démon est arrêté

---

## 2. Configuration MQTT — Auto-détection (Story 1.2)

### 2.1 Auto-détection avec mqtt2 actif

- [ ] S'assurer que mqtt2 est installé, actif et configuré avec un broker valide
- [ ] Aller dans Plugins → jeedom2ha → Configuration
- [ ] **Attendu :** Les champs Host, Port, User sont pré-remplis avec les valeurs de mqtt2
- [ ] **Attendu :** Bandeau bleu "MQTT Manager détecté — configuration pré-remplie"
- [ ] **Attendu :** Le champ mot de passe est `type="password"` (jamais visible en clair)

### 2.2 Auto-détection sans mqtt2

- [ ] Désactiver le plugin mqtt2 (ou le désinstaller)
- [ ] Recharger la page de configuration jeedom2ha
- [ ] **Attendu :** Bandeau orange "Aucun broker MQTT détecté. Installez MQTT Manager ou saisissez les paramètres manuellement."
- [ ] **Attendu :** Les champs sont vides et éditables
- [ ] **Attendu :** Pas de rouge — l'absence de mqtt2 n'est PAS une panne

### 2.3 Configuration manuelle

- [ ] Saisir manuellement : host, port, user, mot de passe
- [ ] Sauvegarder (bouton standard Jeedom)
- [ ] Recharger la page
- [ ] **Attendu :** Les champs sont pré-remplis (sauf le mot de passe qui est masqué)
- [ ] **Attendu :** Bandeau "Configuration manuelle" (bleu)

---

## 3. Test de Connexion MQTT (Story 1.2)

### 3.1 Connexion réussie

- [ ] Config MQTT valide saisie (host, port, user, pass corrects)
- [ ] Cliquer "Tester la connexion"
- [ ] **Attendu :** Spinner pendant le test, puis badge vert "Connexion réussie"

### 3.2 Host inexistant

- [ ] Saisir un host invalide (ex: `host.inexistant.local`)
- [ ] Cliquer "Tester la connexion"
- [ ] **Attendu :** Badge rouge "Hôte introuvable : vérifiez l'adresse du broker"

### 3.3 Port fermé

- [ ] Host valide, port invalide (ex: 9999)
- [ ] Cliquer "Tester la connexion"
- [ ] **Attendu :** Badge rouge "Port refusé : le broker n'écoute pas sur ce port"

### 3.4 Mauvais identifiants

- [ ] Host/port valides, mauvais user ou mot de passe
- [ ] Cliquer "Tester la connexion"
- [ ] **Attendu :** Badge rouge "Authentification refusée : vérifiez identifiant et mot de passe"

### 3.5 Daemon stoppé

- [ ] Stopper le daemon
- [ ] Cliquer "Tester la connexion"
- [ ] **Attendu :** Message "Le démon ne répond pas" (pas de crash UI)

### 3.6 TLS

- [ ] Si un broker TLS est disponible : activer TLS, tester
- [ ] **Attendu :** Connexion réussie si certificat valide
- [ ] Broker auto-signé avec `Vérifier le certificat` décoché : connexion réussie
- [ ] Broker auto-signé avec `Vérifier le certificat` coché : badge "Erreur TLS"

---

## 4. Import Forcé MQTT Manager (Story 1.2-bis)

### 4.1 Import réussi

- [ ] mqtt2 actif et configuré
- [ ] Config manuelle déjà saisie (champs remplis)
- [ ] Cliquer "Récupérer depuis MQTT Manager"
- [ ] **Attendu :** Champs mis à jour avec les valeurs mqtt2
- [ ] **Attendu :** Badge vert "Configuration importée depuis MQTT Manager"
- [ ] **Attendu :** Indicateur mot de passe visible (pas le mot de passe lui-même)
- [ ] **Vérifier Network tab** (F12) : la réponse JSON ne contient PAS de champ `password`

### 4.2 Import — mqtt2 inactif

- [ ] Désactiver mqtt2
- [ ] Cliquer "Récupérer depuis MQTT Manager"
- [ ] **Attendu :** Badge orange "Plugin MQTT Manager (mqtt2) non détecté ou inactif"

### 4.3 Réinitialiser le formulaire

- [ ] Des champs sont remplis
- [ ] Cliquer "Réinitialiser le formulaire"
- [ ] **Attendu :** Tous les champs vidés immédiatement (host, port, user, password)
- [ ] **Attendu :** Pas de sauvegarde automatique — les anciennes valeurs sont conservées en base tant qu'on ne sauvegarde pas

### 4.4 Non-régression test connexion après import

- [ ] Importer depuis MQTT Manager
- [ ] Sauvegarder
- [ ] Cliquer "Tester la connexion"
- [ ] **Attendu :** "Connexion réussie" (le mot de passe importé et chiffré est bien utilisé)

---

## 5. Connexion MQTT Persistante & LWT (Story 1.3)

> **Note :** Ces tests nécessitent que la Story 1.3 soit implémentée et déployée.

### 5.1 Connexion automatique au démarrage

- [ ] Config MQTT valide sauvegardée
- [ ] Démarrer le daemon
- [ ] **Attendu :** Logs `[MQTT] Connexion MQTT initiée vers host:port` puis `[MQTT] Connected`
- [ ] Vérifier avec `mosquitto_sub -t 'jeedom2ha/#' -v --retained-only` :
  - [ ] **Attendu :** `jeedom2ha/bridge/status online` (retained)

### 5.2 Démarrage sans config MQTT

- [ ] Supprimer la config MQTT (vider le host, sauvegarder)
- [ ] Démarrer le daemon
- [ ] **Attendu :** Le daemon démarre en OK
- [ ] **Attendu :** Log `[DAEMON] Pas de configuration MQTT, connexion différée`
- [ ] **Attendu :** Pas de tentative de connexion MQTT

### 5.3 Arrêt propre — publication offline

- [ ] Daemon connecté au broker
- [ ] Ouvrir un terminal : `mosquitto_sub -t 'jeedom2ha/bridge/status' -v`
- [ ] Arrêter le daemon via Jeedom (bouton "Arrêter")
- [ ] **Attendu :** Le terminal affiche `jeedom2ha/bridge/status offline`

### 5.4 LWT — kill brutal

- [ ] Daemon connecté au broker
- [ ] Ouvrir un terminal : `mosquitto_sub -t 'jeedom2ha/bridge/status' -v`
- [ ] Tuer le daemon brutalement : `kill -9 <pid_du_daemon>`
- [ ] **Attendu :** Après le timeout keepalive (~60s), le broker publie automatiquement `jeedom2ha/bridge/status offline`

### 5.5 Reconnexion automatique

- [ ] Daemon connecté au broker
- [ ] Arrêter le broker Mosquitto temporairement : `sudo systemctl stop mosquitto`
- [ ] **Attendu :** Logs `[MQTT] Disconnected` ou `Reconnecting`
- [ ] Redémarrer le broker : `sudo systemctl start mosquitto`
- [ ] **Attendu :** Reconnexion automatique en moins de 30s
- [ ] **Attendu :** Logs `[MQTT] Reconnected` ou `Connected`
- [ ] **Attendu :** Birth message `online` re-publié sur `jeedom2ha/bridge/status`

### 5.6 UI — Badge MQTT sur page équipements

- [ ] Daemon connecté au broker
- [ ] Aller dans Plugins → jeedom2ha (page des équipements)
- [ ] **Attendu :** Badge "MQTT Connecté" (vert) avec l'adresse du broker
- [ ] Couper le broker → rafraîchir ou attendre 30s
- [ ] **Attendu :** Badge "MQTT Déconnecté" ou "MQTT Reconnexion..." (orange — PAS rouge)
- [ ] Reconnecter le broker → rafraîchir ou attendre 30s
- [ ] **Attendu :** Badge revient à "MQTT Connecté" (vert)

### 5.7 UI — Daemon stoppé vs MQTT déconnecté

- [ ] Stopper le daemon
- [ ] Aller dans la page équipements
- [ ] **Attendu :** Badge "Démon arrêté" (gris) — pas de confusion avec un état MQTT

### 5.8 UI — MQTT non configuré

- [ ] Daemon démarré sans config MQTT
- [ ] Aller dans la page équipements
- [ ] **Attendu :** Badge "MQTT Non configuré" (gris)

---

## 6. Sécurité & Logs (Transverse)

### 6.1 Pas de secrets dans les logs

- [ ] Passer les logs en DEBUG
- [ ] Effectuer toutes les opérations : démarrage, config, test connexion, import mqtt2
- [ ] Ouvrir les logs `jeedom2ha`
- [ ] **Attendu :** AUCUN mot de passe en clair dans les logs (ni PHP ni Python)
- [ ] **Attendu :** `--localsecret` et `--apikey` masqués avec `***` dans les logs de démarrage

### 6.2 Pas de secrets dans les réponses AJAX

- [ ] Ouvrir F12 → Network
- [ ] Effectuer : chargement config, import mqtt2, test connexion
- [ ] Inspecter chaque réponse JSON
- [ ] **Attendu :** Aucun champ `password` dans les réponses (uniquement `has_password: true/false`)

### 6.3 API daemon protégée

- [ ] Depuis le serveur Jeedom, tenter un appel direct sans secret :
  ```bash
  curl http://127.0.0.1:55080/system/status
  ```
- [ ] **Attendu :** Réponse 401 Unauthorized
- [ ] Avec le secret (récupérable dans la config plugin en base) :
  ```bash
  curl -H "X-Local-Secret: <secret>" http://127.0.0.1:55080/system/status
  ```
- [ ] **Attendu :** Réponse 200 avec payload structuré

---

## 7. Tests Unitaires Automatisés

- [ ] Exécuter les tests Python :
  ```bash
  cd /path/to/jeedom2ha && make test
  # ou: python -m pytest tests/ -v
  ```
- [ ] **Attendu :** Tous les tests passent (0 failures)
- [ ] Nombre de tests attendu : 54+ (Story 1.1-1.2) + tests Story 1.3

---

## Résumé

| Section | Résultat | Notes |
|---------|----------|-------|
| 1. Daemon startup | [ ] OK / [ ] KO | |
| 2. Auto-détection MQTT | [ ] OK / [ ] KO | |
| 3. Test connexion | [ ] OK / [ ] KO | |
| 4. Import forcé mqtt2 | [ ] OK / [ ] KO | |
| 5. MQTT persistant & LWT | [ ] OK / [ ] KO | |
| 6. Sécurité & logs | [ ] OK / [ ] KO | |
| 7. Tests unitaires | [ ] OK / [ ] KO | |

**Verdict final :** [ ] Epic 1 VALIDÉ / [ ] Epic 1 À CORRIGER

**Testeur :** Alexandre
**Date de validation :** ___________
