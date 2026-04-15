# Artefact visuel prescriptif — Story 4.2

Statut: validé pour implémentation
Story liée: `4-2-diagnostic-de-la-decision-l-utilisateur-distingue-un-refus-de-politique-produit-d-un-refus-de-gouvernance-d-ouverture`
Surface cible: modal existante `Diagnostic de Couverture`

## Contraintes non négociables

- Aucune nouvelle surface UI
- Aucune nouvelle colonne
- Aucune dérive home/diagnostic
- La lecture visible ne dépend jamais du `reason_code` brut
- La distinction doit être perceptible immédiatement dans `Raison` et `Action recommandée`

## Vue prescriptive

La modal conserve exactement ses colonnes actuelles :

`Pièce | Nom | Ecart | Statut | Confiance | Raison`

### Cas A — refus par politique produit

```text
| Salon | Lampe buffet | Non publié | Bloqué | Faible | Confiance insuffisante pour la politique active |

Action recommandée
Assouplir la politique de confiance si vous souhaitez autoriser un mapping moins fiable.
```

### Cas B — refus par gouvernance d'ouverture

```text
| Salon | Détecteur multi-capteurs | Non publié | Bloqué | Élevée | Composant Home Assistant non ouvert dans ce cycle |

Action recommandée
Aucune action côté Jeedom : ce composant n'est pas encore pris en charge dans le cycle courant.
```

## Règles de wording

- `low_confidence` doit parler de politique active ou de confiance insuffisante.
- `low_confidence` ne doit plus être rendu comme `Aucun mapping compatible`.
- `ha_component_not_in_product_scope` doit parler de composant non ouvert ou non pris en charge dans le cycle.
- `ha_component_not_in_product_scope` ne doit jamais ressembler à un échec de mapping.
- `Action recommandée` du cas gouvernance doit expliciter qu'il n'existe pas de levier direct côté configuration Jeedom.

## Critères visuels de validation

- Les deux lignes restent lisibles sans connaissance du pipeline interne.
- Les deux cas ne peuvent pas être confondus si l'utilisateur ne voit que le texte affiché.
- La différence perçue repose sur le texte visible, pas sur la colonne `Confiance` seule.
- La surface garde la même structure que la modal actuelle.
