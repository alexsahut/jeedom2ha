# ARTEFACT — Story 5.1 : tests unitaires du constructeur actions_ha.
"""Tests du signal actions_ha — label contextuel, matrice de disponibilité, bridge gating."""

import pytest

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from models.actions_ha import build_actions_ha, label_publier


# ---------------------------------------------------------------------------
# Label contextuel — fonction pure (AC 3)
# ---------------------------------------------------------------------------

class TestLabelPublier:
    def test_non_publie_label_creer(self):
        assert label_publier(False) == "Créer dans Home Assistant"

    def test_publie_label_republier(self):
        assert label_publier(True) == "Republier dans Home Assistant"

    def test_basculement_label(self):
        """Le label bascule immédiatement quand est_publie_ha change."""
        assert label_publier(False) != label_publier(True)


# ---------------------------------------------------------------------------
# Matrice de disponibilité — cas nominaux bridge disponible (AC 4)
# ---------------------------------------------------------------------------

class TestMatriceNominale:
    def test_non_publie_inclus(self):
        """est_publie_ha=False, inclus → publier actif, supprimer grisé."""
        actions = build_actions_ha(est_publie_ha=False, est_inclus=True, bridge_disponible=True)
        assert actions["publier"]["label"] == "Créer dans Home Assistant"
        assert actions["publier"]["disponible"] is True
        assert actions["publier"]["raison_indisponibilite"] is None
        assert actions["supprimer"]["disponible"] is False
        assert actions["supprimer"]["raison_indisponibilite"] is not None
        assert "entité" in actions["supprimer"]["raison_indisponibilite"].lower() or \
               "publi" in actions["supprimer"]["raison_indisponibilite"].lower()

    def test_publie_inclus(self):
        """est_publie_ha=True, inclus → publier actif (Republier), supprimer actif."""
        actions = build_actions_ha(est_publie_ha=True, est_inclus=True, bridge_disponible=True)
        assert actions["publier"]["label"] == "Republier dans Home Assistant"
        assert actions["publier"]["disponible"] is True
        assert actions["supprimer"]["disponible"] is True
        assert actions["supprimer"]["raison_indisponibilite"] is None

    def test_label_supprimer_toujours_identique(self):
        """Le label supprimer est toujours 'Supprimer de Home Assistant'."""
        a1 = build_actions_ha(est_publie_ha=False, est_inclus=True, bridge_disponible=True)
        a2 = build_actions_ha(est_publie_ha=True, est_inclus=True, bridge_disponible=True)
        assert a1["supprimer"]["label"] == "Supprimer de Home Assistant"
        assert a2["supprimer"]["label"] == "Supprimer de Home Assistant"


# ---------------------------------------------------------------------------
# Bridge indisponible → tout grisé (AC 5)
# ---------------------------------------------------------------------------

class TestBridgeIndisponible:
    def test_bridge_off_tout_grise(self):
        """Infrastructure indisponible → toutes actions grisées avec raison."""
        actions = build_actions_ha(est_publie_ha=False, est_inclus=True, bridge_disponible=False)
        assert actions["publier"]["disponible"] is False
        assert actions["supprimer"]["disponible"] is False
        # Raison lisible mentionnant le pont
        assert "pont" in actions["publier"]["raison_indisponibilite"].lower() or \
               "bridge" in actions["publier"]["raison_indisponibilite"].lower() or \
               "indisponible" in actions["publier"]["raison_indisponibilite"].lower()

    def test_bridge_off_meme_avec_publie(self):
        """Même si publié, bridge off → tout grisé."""
        actions = build_actions_ha(est_publie_ha=True, est_inclus=True, bridge_disponible=False)
        assert actions["publier"]["disponible"] is False
        assert actions["supprimer"]["disponible"] is False

    def test_bridge_off_raison_distincte_de_config(self):
        """La raison bridge est distincte de la raison 'aucune entité'."""
        actions_bridge = build_actions_ha(est_publie_ha=False, est_inclus=True, bridge_disponible=False)
        actions_nominal = build_actions_ha(est_publie_ha=False, est_inclus=True, bridge_disponible=True)
        assert actions_bridge["supprimer"]["raison_indisponibilite"] != \
               actions_nominal["supprimer"]["raison_indisponibilite"]


# ---------------------------------------------------------------------------
# Niveau de confirmation (scope équipement) — Dev Notes §4
# ---------------------------------------------------------------------------

class TestNiveauConfirmation:
    def test_publier_equipement_aucune(self):
        """Action positive équipement : pas de modale → 'aucune'."""
        actions = build_actions_ha(est_publie_ha=False, est_inclus=True, bridge_disponible=True)
        assert actions["publier"]["niveau_confirmation"] == "aucune"

    def test_supprimer_equipement_forte(self):
        """Supprimer équipement : modale forte → 'forte'."""
        actions = build_actions_ha(est_publie_ha=True, est_inclus=True, bridge_disponible=True)
        assert actions["supprimer"]["niveau_confirmation"] == "forte"


# ---------------------------------------------------------------------------
# Shape du signal — complétude des champs (AC 2)
# ---------------------------------------------------------------------------

class TestShapeSignal:
    REQUIRED_FIELDS = {"label", "disponible", "raison_indisponibilite", "niveau_confirmation"}

    def test_publier_shape(self):
        actions = build_actions_ha(est_publie_ha=False, est_inclus=True, bridge_disponible=True)
        assert set(actions["publier"].keys()) == self.REQUIRED_FIELDS

    def test_supprimer_shape(self):
        actions = build_actions_ha(est_publie_ha=True, est_inclus=True, bridge_disponible=True)
        assert set(actions["supprimer"].keys()) == self.REQUIRED_FIELDS

    def test_top_level_keys(self):
        actions = build_actions_ha(est_publie_ha=False, est_inclus=True, bridge_disponible=True)
        assert set(actions.keys()) == {"publier", "supprimer"}


# ---------------------------------------------------------------------------
# Cohérence actions_ha ↔ 4D (AC 7) — invariants contractuels
# ---------------------------------------------------------------------------

class TestCoherence4D:
    def test_non_publie_implique_creer(self):
        """statut=non_publie (est_publie_ha=False) → label Créer."""
        actions = build_actions_ha(est_publie_ha=False, est_inclus=True, bridge_disponible=True)
        assert "Créer" in actions["publier"]["label"]

    def test_publie_implique_republier(self):
        """statut=publie (est_publie_ha=True) → label Republier."""
        actions = build_actions_ha(est_publie_ha=True, est_inclus=True, bridge_disponible=True)
        assert "Republier" in actions["publier"]["label"]

    def test_action_positive_non_destructive(self):
        """Invariant I5 — l'action publier est toujours disponible pour un inclus bridge-up."""
        for publie in (True, False):
            actions = build_actions_ha(est_publie_ha=publie, est_inclus=True, bridge_disponible=True)
            assert actions["publier"]["disponible"] is True

    def test_supprimer_seul_flux_destructif(self):
        """Invariant I6 — supprimer est le seul chemin destructif. Preuve contractuelle :
        le niveau_confirmation de supprimer est 'forte', celui de publier 'aucune'."""
        actions = build_actions_ha(est_publie_ha=True, est_inclus=True, bridge_disponible=True)
        assert actions["supprimer"]["niveau_confirmation"] == "forte"
        assert actions["publier"]["niveau_confirmation"] == "aucune"
