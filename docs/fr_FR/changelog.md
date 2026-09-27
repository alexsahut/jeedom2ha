# Changelog — jeedom2ha

>**NOTE**
>
>S'il n'y a pas d'information sur la mise à jour, c'est que celle-ci concerne uniquement de la documentation, une traduction ou des corrections mineures.

---

# 2026-09-27 — v0.3.0

- CC-17 : support OS resserré à Debian 11 et 12 (`os.min` 10 → 11) ; matrice CI Python 3.9 / 3.11 avec Python 3.12 ré-ajouté comme test de compatibilité future ; `Test Report` devient un gate global qui échoue si un job attendu échoue ou est annulé (burn-in limité à `success`/`skipped`)
- Version lisible : `pluginVersion` passé en semver (0.3.0), le démon journalise désormais sa version et le SHA du commit déployé au démarrage (`[DAEMON] jeedom2ha daemon v<version> (sha <sha>) starting`)
- `deploy-to-box.sh` écrit un fichier `VERSION` (version + sha + date + statut git) à la racine du plugin sur la box après chaque déploiement, hors de portée du rsync `--delete`
- Hygiène déploiement : sauvegarde automatique (archive tar.gz, permissions 700/600) du plugin existant avant écrasement ; renforcement du filtre rsync (`node_modules/`) et test CI garantissant qu'aucun chemin de développement (`.git`, `tests/`, `_bmad*`, `.venv`, `docs/`, `.github/`, `scripts/`, etc.) ne peut fuiter vers la box

# 2026-03-19

- Identité visuelle : nouvelle icône plugin (J→HA, navy/vert/bleu)
- README et documentation `docs/fr_FR` réécrits depuis le template générique

# 2026-03-18

- Story 4.3 : exclusions multicritères par équipement et famille, politique de confiance (sûr / sûr+probable), bouton "Appliquer et Rescanner"
- Story 4.2-bis : homogénéité de traçabilité et explicabilité diagnostique
- Story 2.6 : déduplication des commandes generic_type dupliquées (PR #15)

# 2026-03-16

- Story 3.3 : disponibilité du pont et des entités (availability_topic), validée sur box réelle

# 2026-03-15

- Story 3.2-bis : bootstrap runtime après restart daemon (réémission discovery)
- Story 3.2 : pilotage HA → Jeedom avec confirmation honnête d'état

# 2026-03-13

- Story 3.1 : synchronisation incrémentale des états Jeedom → HA (event::changes)
- Story 4.2 : diagnostic détaillé avec suggestions de remédiation
- Story 4.1 : interface de diagnostic de couverture

# 2026-03-12

- Story 2.4 : mapping et exposition des prises/switches
- Story 2.3 : mapping et exposition des volets/covers
- Story 2.2 : mapping et exposition des lumières (on/off, dimmable, RGB)
- Story 2.1 : topology scraper, contexte spatial (pièces Jeedom → suggested_area)
- Story 2.5 (capteurs numériques et binaires) : non intégré — prévu dans une prochaine version
- Story 1.3 : validation de la connexion et statut du pont (badge MQTT)
- Story 1.2-bis : fiabilisation de l'auto-détection MQTT Manager, import forcé
- Story 1.2 : configuration et onboarding MQTT (auto-détection / manuel, TLS)
- Story 1.1 : initialisation et communication PHP ↔ Python (daemon asyncio)

---

Légende des statuts :
- **done** : livré et validé
- **beta** : disponible sur la branche beta, en cours de test terrain
