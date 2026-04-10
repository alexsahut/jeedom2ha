# Changelog — jeedom2ha

>**NOTE**
>
>S'il n'y a pas d'information sur la mise à jour, c'est que celle-ci concerne uniquement de la documentation, une traduction ou des corrections mineures.

---

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
