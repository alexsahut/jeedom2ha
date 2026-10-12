# Story 24.10 : Écarts résiduels après mesure

Status: draft

> **Brouillon de cadrage (2026-10-12), `draft`, jamais `ready-for-dev`.** Rédigé par une session cloud déléguée, documentaire. **La portée n'est pas fixée** : elle dépend de la baseline de 24.2 et des stories 24.4 à 24.9. Ne passe pas à `ready-for-dev` avant que ClaudeBox ait classé chaque écart restant. Pointeurs pris sur `main` à `b1acad7`. Aucun nom réel (CC-48).

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
| Prise dont les commandes sont `ENERGY_ON/OFF` | `SwitchMapper` traite `ENERGY_ON` seul, `ENERGY_OFF` seul, ou le trio avec `ENERGY_STATE` (`mapping/switch.py:121-200`) ; sans état, le switch est optimiste. | **Inconnue** : le type attendu par le référentiel et le type publié ne sont pas donnés. L'export les donnera. |
| Capteur sans température ni humidité | La température et l'humidité sont mappées par type générique, plus par unité fiable pour W/Wh/kWh (`mapping/sensor.py`, `models/topology.py:269-295`) ; un capteur sans ces types tombe sur le repli `sensor` ambigu (`mapping/fallback.py`). | **Inconnue** : quel type est attendu, quel signal Jeedom existe (unité, nom, type générique absent). |

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
