# Story 24.10 : Écarts résiduels après mesure

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft` jusqu'à son `create-story`, après la baseline.** Rédigé par une session cloud déléguée, documentaire. **La portée n'est pas fixée** : elle dépend de la baseline de 24.2 et des stories 24.4 à 24.9. Ne passe pas à `ready-for-dev` avant que ClaudeBox ait classé chaque écart restant. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).
>
> **R1 (ClaudeBox, 12/10) intégrée** : types génériques des deux équipements établis ; une hypothèse de cause, fondée sur le code, est posée pour le capteur (à confirmer par l'export).

## Story

En tant que mainteneur de la parité,
je veux traiter, un par un et après mesure, les écarts de type qui subsistent (une prise `ENERGY_ON/OFF`, un capteur sans température ni humidité) une fois les types principaux livrés,
afin de refermer la liste des 15 écarts de type sans deviner leur cause.

**Parcours : démon, éventuellement documentation seulement.**

## Dépendances

- Dépend de **24.2** (baseline), **24.4** et des stories de type déjà livrées (24.6 à 24.9 selon l'ordre réel).
- La liste des équipements concernés vient de ClaudeBox (export + référentiel).

## Ce que l'on sait, et ce que l'on ne sait pas

| Écart | Fait établi dans le code | Cause |
|---|---|---|
| Prise `ENERGY_ON`, `ENERGY_OFF`, `ENERGY_STATE` (*établi par ClaudeBox le 12/10*) | Trio complet : `SwitchMapper` le traite comme un `switch` avec état réel relu (`mapping/switch.py:121-200`, `sync/state.py:35-48`). Le mapping nominal existe déjà. | **Inconnue** : le trio étant complet, l'écart ne vient pas d'un type manquant du mapping ; type attendu par le référentiel et type publié ne sont pas donnés (jointure ? entité absente ? multi-entité ?). L'export les donnera. |
| Capteur `WEATHER_TEMPERATURE`, `WEATHER_HUMIDITY`, `WEATHER_PRESSURE`, `SIREN_STATE` (*établi par ClaudeBox le 12/10*) | Les trois types `WEATHER_*` **sont mappés** en `sensor` (`mapping/sensor.py:40-42`). Mais la chaîne de mappers s'arrête au premier mapper qui reconnaît l'équipement (`mapping/registry.py:24-35,80-86`) et `BinarySensorMapper` passe avant `SensorMapper` : `SIREN_STATE` donne un `binary_sensor` (`mapping/binary_sensor.py:46`), et le cas multi-domaine n'existe que pour une forme `switch` (`:69-87`). | **Hypothèse (non vérifiée)** : l'équipement serait publié comme simple `binary_sensor` de sirène, **sans** ses mesures de température, d'humidité et de pression. À confirmer par l'export (`ha_type`, commandes `covered: false`). Si confirmée, la correction est un cas multi-domaine borné (sensor + binary_sensor), sans nouveau composant. |

## Critères d'acceptation proposés (conditionnels)

- **AC1.** Pour chaque écart restant, une ligne de classement (identifiants seulement) : cause, type attendu, type publié, action (corriger le mapping, poser un override, corriger le type générique dans Jeedom côté utilisateur, ou « équivalent fonctionnel : aucun écart »).
- **AC2.** Un écart dont la cause est une configuration Jeedom (type générique absent) n'est **pas** corrigé par le plugin : le plugin ne modifie jamais les types génériques Jeedom (exigence 5) ; la raison canonique et l'action recommandée sont visibles dans l'export et l'écran.
- **AC3.** Un écart dont la cause est le mapping fait l'objet d'une correction minimale, bornée, testée, sans nouveau composant ; si un nouveau composant est nécessaire, la correction devient une story séparée (FR40/NFR10).
- **AC4.** Aucune heuristique sur les noms ; aucune inférence au-delà de l'unité fiable ou du type générique ; principe de moindre nuisance respecté.
- **AC5.** Golden et contrat 4D verts ; aucun nom réel (CC-48) ; preuve terrain par ClaudeBox (export avant/après).

## Tâches proposées

- [ ] **Task 0 — Classement (ClaudeBox)** à partir de l'export « après » de 24.9 : liste des équipements encore en écart de type.
- [ ] **Task 1 — Décision avec Alexandre** pour chaque classe d'écart (corriger / override / équivalent).
- [ ] **Task 2 — Corrections bornées** et tests, une PR par sujet ; **gate et preuve terrain (humain)**.

## Garde-fous

- Pas de story d'implémentation avant le classement : le brouillon est volontairement ouvert.
- `scripts/deploy-to-box.sh` jamais lancé par une session cloud.

## Vérifications non faites par cette session

Tout ce qui est « Inconnue » ci-dessus ; le nombre d'écarts restants après 24.4 à 24.9.

## Journal des décisions

- 2026-10-12 — Cadrage documentaire (session cloud déléguée) : story `draft`.
- 2026-10-12, 13:22 — **Décisions d'Alexandre** (relayées par ClaudeBox) : aucune question ne porte sur cette story ; elle reste `draft`, portée à fixer sur la baseline.
