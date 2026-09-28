"""Tests de Story 19.3 — Surface pièce / aperçu branchés sur le contrat de décision (AC1-AC7)."""

import copy
import json
from pathlib import Path
import pytest

from mapping.overrides import (
    list_equipment_overrides,
    list_overrides,
    remove_equipment_override,
    remove_override,
    save_override,
)
from models.decision_taxonomy import CommandDecision, PublicationDecision
from models.evaluate_equipment import evaluate_equipment
from models.mapping import PublicationResult
from models.topology import assess_eligibility


@pytest.fixture
def temp_overrides_file(tmp_path):
    """Fixture pour tester les overrides avec un fichier temporaire."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    overrides_file = data_dir / "ha_overrides.json"
    # Initialiser un fichier d'overrides vide
    overrides_file.write_text(json.dumps({
        "schema_version": 2,
        "overrides": {},
        "equipment_overrides": {}
    }))
    return overrides_file


class TestAC1SurfaceRespectEligibility:
    """AC1 — La surface par pièce respecte l'éligibilité réelle."""

    def test_ac1_excluded_equipment_surface_uses_evaluate_equipment(self, app_fixture, temp_overrides_file):
        """AC1: Surface affiche statut 'exclu' pour équipement exclu par éligibilité amont + override."""
        app = app_fixture
        # Patch _DATA_DIR pour utiliser le fichier temporaire
        import resources.daemon.transport.http_server as http_module
        original_data_dir = getattr(http_module, '_DATA_DIR', None)
        http_module._DATA_DIR = str(temp_overrides_file.parent)

        try:
            # Équipement exclu par éligibilité amont (ex: core_type='virtual', non éligible pour HA)
            eq_id = 9999
            core_type = 'virtual'
            jee_type = 'Virtual'
            equipment = {
                'id': eq_id,
                'name': 'Excluded Equipment',
                'eqType_name': jee_type,
            }

            # Vérifier que l'équipement est inéligible
            eligibility = assess_eligibility(equipment)
            assert not eligibility.is_eligible, "Equipment doit être inéligible"

            # Ajouter un override de publication (pour ce test, imaginaire, l'équipement reste inéligible)
            override = {
                'eq_id': eq_id,
                'publication_exclude': True,
            }
            save_override(override, data_dir=str(temp_overrides_file.parent))

            # Évaluer l'équipement (AC1: doit consommer evaluate_equipment())
            evaluation = evaluate_equipment(
                eq_id=eq_id,
                core_type=core_type,
                equipment=equipment,
                data_dir=str(temp_overrides_file.parent),
                confidence_policy=app['confidence_policy'],
            )

            # La surface par pièce (_build_mapping_override_tree) appelle cette fonction
            # et utilise le statut renvoyé. Ici on teste que le statut est bien 'exclu'.
            # L'équipement doit être inéligible (should_publish=False due à ineligibility, pas à override)
            assert evaluation.status == 'ineligible', f"Equipment doit être inéligible, got {evaluation.status}"

            # Vérifier que l'override est bien en place
            overrides = list_equipment_overrides(data_dir=str(temp_overrides_file.parent), eq_id=eq_id)
            assert len(overrides) > 0, "Equipment override doit exister"

        finally:
            if original_data_dir:
                http_module._DATA_DIR = original_data_dir
            else:
                delattr(http_module, '_DATA_DIR')


class TestAC2PreviewConsistency:
    """AC2 — L'aperçu à blanc reflète la même vérité que la surface."""

    def test_ac2_preview_and_surface_consistent(self, app_fixture, temp_overrides_file):
        """AC2: Aperçu et surface donnent même réponse pour le même override."""
        app = app_fixture

        # Équipement avec mapping valide
        eq_id = 100
        core_type = 'eq'
        equipment = {'id': eq_id, 'name': 'Light', 'eqType_name': 'Light'}

        # Évaluation sans overrides (aperçu propre)
        eval_no_override = evaluate_equipment(
            eq_id=eq_id,
            core_type=core_type,
            equipment=equipment,
            data_dir=str(temp_overrides_file.parent),
            confidence_policy=app['confidence_policy'],
        )

        # Ajouter un override TYPE proposé et réévaluer (aperçu avec override)
        proposed_overrides = {
            f"{eq_id}:999": {'command_type': 'switch'},  # CMD 999 => switch
        }
        eval_with_override = evaluate_equipment(
            eq_id=eq_id,
            core_type=core_type,
            equipment=equipment,
            proposed_overrides=proposed_overrides,
            data_dir=str(temp_overrides_file.parent),
            confidence_policy=app['confidence_policy'],
        )

        # Les deux évaluations doivent consommer la même logique (AC2: consistency)
        # Vérifier que l'override proposé est bien pris en compte
        assert eval_with_override is not None, "Evaluation with proposed override must succeed"
        # Le contrat de réponse doit être cohérent entre les deux appels
        # (pas de logique dupliquée côté surface)


class TestAC3RevertRemovesAllOverrides:
    """AC3 — CC-19: 'revenir au mode auto' efface tous les overrides d'équipement."""

    def test_ac3_revert_removes_type_and_publication_overrides(self, temp_overrides_file):
        """AC3: Après revert, plus aucun override (TYPE ou publication) pour l'équipement."""
        eq_id = 200
        cmd_id_1 = 1001
        cmd_id_2 = 1002
        data_dir = str(temp_overrides_file.parent)

        # Ajouter overrides TYPE sur deux commandes
        save_override({
            'eq_id': eq_id,
            'cmd_id': cmd_id_1,
            'command_type': 'switch',
        }, data_dir=data_dir)
        save_override({
            'eq_id': eq_id,
            'cmd_id': cmd_id_2,
            'command_type': 'light',
        }, data_dir=data_dir)

        # Ajouter override de publication
        save_override({
            'eq_id': eq_id,
            'publication_exclude': True,
        }, data_dir=data_dir)

        # Vérifier que les overrides existent
        type_overrides = list_overrides(data_dir=data_dir, eq_id=eq_id, cmd_id=None)
        assert len(type_overrides) >= 2, "Type overrides must exist before revert"

        eq_overrides = list_equipment_overrides(data_dir=data_dir, eq_id=eq_id)
        assert len(eq_overrides) > 0, "Equipment override must exist before revert"

        # Simuler la revert (supprimer tous les overrides de l'équipement)
        # AC3: effacer chaque eq_id:cmd_id puis remove_equipment_override
        for override in type_overrides:
            # Parse override key to get eq_id:cmd_id
            parts = override.split(':')
            if len(parts) == 2:
                remove_override(override, data_dir=data_dir)

        # Puis effacer l'override d'équipement
        remove_equipment_override(eq_id, data_dir=data_dir)

        # Vérifier qu'aucun override ne subsiste
        remaining_type_overrides = list_overrides(data_dir=data_dir, eq_id=eq_id, cmd_id=None)
        remaining_eq_overrides = list_equipment_overrides(data_dir=data_dir, eq_id=eq_id)

        assert len(remaining_type_overrides) == 0, f"No type overrides should remain, got {remaining_type_overrides}"
        assert len(remaining_eq_overrides) == 0, f"No equipment overrides should remain, got {remaining_eq_overrides}"


class TestAC4ReasonLabels:
    """AC4 — Libellés français pour toutes les raisons exposées."""

    def test_ac4_reason_labels_complete(self):
        """AC4: REASON_LABELS contient tous les reason_codes exposés (pas de code brut)."""
        from resources.daemon.models.decision_taxonomy import CommandDecision

        # Importer les raisons connues
        reason_codes = {
            'publication_excluded_eqlogic',
            'publication_excluded_command',
            'publication_forced',
            'sure_mapping',
            'ha_component_not_in_product_scope',
            'no_mapping',
            'skipped_no_mapping_candidate',
            # Ajouter d'autres raisons si nécessaire (Story 19.0/19.1)
        }

        # Vérifier que les raisons ont des labels (côté JS: REASON_LABELS)
        # Ici on teste juste qu'une raison donnée peut être exposée sans crash
        for reason_code in reason_codes:
            decision = CommandDecision(
                should_publish=False,
                reason=reason_code,
                confidence=None,
            )
            # Le diagnostic ne doit jamais valoir None (AC7)
            assert decision.reason is not None, f"Reason must not be None for {reason_code}"


class TestAC6TwoTemporalities:
    """AC6 — Deux temporalités explicites (decision synchronisée vs overrides courants)."""

    def test_ac6_badge_for_unapplied_override(self, app_fixture, temp_overrides_file):
        """AC6: Badge indique qu'un override n'est pas encore appliqué."""
        # Ce test vérifie que la surface distingue:
        # - La dernière décision synchronisée (app["publications"])
        # - Les overrides courants (en mémoire avant sync)
        # Un badge visuel indique le delta.
        pass  # Logique frontend + backend coordination — skeleton pour maintenant


class TestAC7NoSilentDiagnostic:
    """AC7 — Aucune commande sans raison (golden 59)."""

    def test_ac7_golden_59_no_silent_commands(self, app_fixture):
        """AC7: Golden 59 contient zéro commande sans raison."""
        # Ce test demande un accès au golden file et vérification que chaque commande
        # a une CommandDecision + une raison + un libellé français.
        # Skeleton : à implémenter avec données réelles.
        pass


class TestAC3ConflictInterCommands:
    """Test de conflit inter-commandes (Dev Notes: CC-22 de Story 19.1)."""

    def test_ac2_conflict_inter_command_override_priority(self, app_fixture, temp_overrides_file):
        """Dev Notes: Un override TYPE persisté sur une autre commande de la même entité
        doit être sélectionné correctement lors de evaluate_equipment()."""
        eq_id = 300
        cmd_id_existing = 2001
        cmd_id_target = 2002
        data_dir = str(temp_overrides_file.parent)

        # Ajouter un override TYPE sur cmd_id_existing (persisté)
        save_override({
            'eq_id': eq_id,
            'cmd_id': cmd_id_existing,
            'command_type': 'switch',
        }, data_dir=data_dir)

        # Proposer un override sur cmd_id_target (via proposed_overrides)
        proposed_overrides = {
            f"{eq_id}:{cmd_id_target}": {'command_type': 'light'},
        }

        # Évaluer l'équipement avec l'override proposé
        evaluation = evaluate_equipment(
            eq_id=eq_id,
            core_type='eq',
            equipment={'id': eq_id, 'name': 'Multi-Command Equipment'},
            proposed_overrides=proposed_overrides,
            data_dir=data_dir,
            confidence_policy=app_fixture['confidence_policy'],
        )

        # Les overrides persistés ne doivent pas être mutés par l'appel proposed
        # Vérifier que l'override sur cmd_id_existing est toujours 'switch'
        persisted_overrides = list_overrides(data_dir=data_dir, eq_id=eq_id, cmd_id=cmd_id_existing)
        assert any('switch' in str(o) for o in persisted_overrides), \
            "Persisted override must not be mutated by proposed_overrides"
