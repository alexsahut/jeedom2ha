# Validation terrain pe-epic-5

## 1. Objet

Centraliser une preuve terrain unique, explicite et opposable pour `pe-epic-5`, afin de statuer sur la levée du gate de readiness avant `pe-epic-6`.

## 2. Périmètre terrain validé

Le périmètre attendu couvre le déploiement sur box Jeedom réelle et la validation finale Alexandre des livrables `pe-epic-5` du cycle Moteur de Projection Explicable, en particulier les stories `5.1` et `5.2` et leur comportement global en terrain.

## 3. Date

`2026-04-19`

## 4. État de validation

**Validé (niveau de preuve réaliste — dataset contraint)**

État retenu : **A. Gate terrain pe-epic-5 levé.**

## 5. Redéfinition du niveau de preuve terrain (décision Alexandre)

Décision Alexandre du `2026-04-19` :

Le niveau de preuve initial du gate terrain, basé sur une couverture exhaustive step 1 à step 5, est requalifié comme trop ambitieux par rapport au dataset réel observable sur la box Jeedom.

Le gate terrain `pe-epic-5` est désormais considéré comme levé si :

1. le déploiement est réussi sur box réelle ;
2. le runtime est sain ;
3. l'invariant I7 est observé sur des cas réels ;
4. au moins un cas publié et un cas non publié sont observés ;
5. aucune violation de séparation décision / résultat technique n'est constatée.

La couverture exhaustive des steps 3, 4 et des échecs step 5 n'est plus requise en terrain réel, car dépendante du dataset disponible et non du comportement structurel du système.

## 6. Base probatoire terrain

- Commit terrain déployé : `a372e3a` (`fix(pe-epic-5): figer le lot terrain I7`)
- Box réelle : `192.168.1.21`
- Script utilisé : `scripts/deploy-to-box.sh`
- Date du run : `2026-04-19`
- Validation finale Alexandre : `oui`

### 6.1 Déploiement et runtime

- Déploiement réel réussi sur box Jeedom via `deploy-to-box.sh`
- Healthcheck post-déploiement : `mqtt.state=connected`
- Endpoint `/system/status` : `status=ok`
- Endpoint `/system/diagnostics` : `status=ok`, `278` équipements
- Logs plugin datés du `2026-04-19` : aucune ligne `ERROR`, `CRITICAL`, `Traceback` ou `Exception`

### 6.2 Cas observés

- Cas publié observé :
  - `eq_id=391`
  - `decision_trace.reason_code="published"`
  - `publication_trace.last_discovery_publish_result="success"`
- Cas non publié step 1 observé :
  - `eq_id=577`
  - `decision_trace.reason_code="excluded"`
  - `publication_trace.last_discovery_publish_result="not_attempted"`
- Cas non publié step 2 observé :
  - `eq_id=587`
  - `decision_trace.reason_code="no_supported_generic_type"`
  - `publication_trace.last_discovery_publish_result="not_attempted"`

### 6.3 Cas non observés sur ce dataset

- Aucun cas step 3 observé
- Aucun cas step 4 observé
- Aucun cas `publication_trace.last_discovery_publish_result="failed"` observé

Ces absences sont attribuées au dataset terrain disponible sur la box au moment du run, et ne remettent pas en cause la levée du gate dans le cadre redéfini par Alexandre.

## 7. Invariant I7 et séparation décision / résultat technique

- Cas réels publiés et non publiés inspectés sans dérive observée
- Aucune contamination de `decision_trace.reason_code` par un code technique step 5
- Aucune violation visible de séparation entre cause canonique et résultat technique
- Aucune incohérence runtime détectée pendant le run terrain

## 8. Décision Alexandre (Project Lead)

Décision explicite Alexandre du `2026-04-19` :

- le gate terrain `pe-epic-5` est levé selon un niveau de preuve réaliste et opposable ;
- la contrainte de couverture exhaustive step 3 / step 4 / step 5 failed est levée pour le terrain réel ;
- la décision sera réévaluée si de nouveaux cas apparaissent sur la box.

## 9. Impact sur le gate pe-epic-6

- Gate terrain `pe-epic-5` : **levé**
- Gate de readiness `pe-epic-6` : **levé**
- Verdict à date : **GO pe-epic-6**
