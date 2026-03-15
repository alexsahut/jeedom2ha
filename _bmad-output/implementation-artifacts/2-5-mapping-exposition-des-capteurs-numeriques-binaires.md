# Story 2.5: Mapping & Exposition des Capteurs (Numériques & Binaires)

Status: done

## Story

As a utilisateur Jeedom,
I want visualiser mes mesures et états binaires dans HA sans fausse précision,
so that je supervise ma maison avec des données réelles.

## Acceptance Criteria

1. [x] **Given** le moteur de mapping traite des commandes d'info **When** elles correspondent à des mesures numériques ou des états binaires **Then** le système produit des entités `sensor` ou `binary_sensor` correspondantes
2. [x] **And** les métadonnées HA (`device_class`) sont incluses **uniquement** si le `generic_type` ou le type d'équipement confirme de façon univoque la nature du capteur
3. [x] **And** `unit_of_measurement` MUST NOT be manipulated or guessed; it is published ONLY if Jeedom provides a non-empty unit AND it matches or is directly convertible to a recognized unit for that `device_class`
4. [x] **And** `state_class` is included ONLY if semantics are certain (e.g., `measurement` for temperature, `total_increasing` ONLY for energy consumption with explicit criteria, not by default)
5. [x] **And** toute incohérence détectée (ex: valeur non numérique pour un sensor num, unité aberrante) bloque la publication de l'entité et alimente le diagnostic
6. [x] **And** les valeurs binaires sont normalisées (`"ON"`/`"OFF"`) avant publication, avec rejet silencieux (+ diagnostic) si la conversion est impossible
7. [x] **And** le payload `config` original MQTT de l'entité doit définir explicitement `payload_on: "ON"` et `payload_off: "OFF"` pour les binary_sensors
8. [x] **And** l'état initial des capteurs MUST be published to their state topics immediately following the discovery payload publication to avoid "Unknown" states in HA

## Hardened Definition of Done (Retrospective Epic 1 + Story 2.4)

- [x] **Validation par Tests Unitaires :** `test_sensor_mapper.py`, `test_discovery_publisher.py`, `test_http_server.py`.
- [x] **Smoke Test MQTT Discovery :** Simulé par `test_http_server.py` (vérification des topics et payloads).
- [x] **Pas de Régression :** Lumières (2.2), Volets (2.3) et Switches (2.4) testés via `pytest tests/`.

## Tasks / Subtasks

- [x] **Task 1 — Créer le SensorMapper (`mapping/sensor.py`)**
  - [x] 1.1 Créer la classe `SensorMapper`. Retourne `List[MappingResult]`.
  - [x] 1.2 Détection via `generic_type` (TEMPERATURE, HUMIDITY, etc.).
  - [x] 1.3 Gestion des confiances (sure/probable/ambiguous).
  - [x] 1.4 Mapping strict des unités et device_class.
  - [x] 1.5 Normalisation binaire ("ON"/"OFF").

- [x] **Task 2 — Étendre le DiscoveryPublisher (`discovery/publisher.py`)**
  - [x] 2.1 Ajouter `publish_sensor` et `publish_binary_sensor`.
  - [x] 2.2 MQTT Conventions : `unique_id` & `object_id` = `jeedom2ha_cmd_{id}`.
  - [x] 2.3 Groupement `device` par `eq_id`.
  - [x] 2.4 Champs conditionnels (`unit`, `device_class`, `state_class`).
  - [x] 2.5 Payloads binaires explicites.

- [x] **Task 3 — Intégrer au handler sync (`transport/http_server.py`)**
  - [x] 3.1 Instancier `SensorMapper` et traiter les résultats multiples.
  - [x] 3.2 Utiliser `ha_unique_id` pour le tracking et retrait MQTT.
  - [x] 3.3 Publication de l'état initial (AC 2.6/2.8).
  - [x] 3.4 Mise à jour des compteurs diagnostics.

- [x] **Task 4 — Tests et Validation**
  - [x] 4.1 Unit tests Mapper.
  - [x] 4.2 Unit tests Publisher.
  - [x] 4.3 Integration tests Sync route.
  - [x] 4.4 Non-regression check.
