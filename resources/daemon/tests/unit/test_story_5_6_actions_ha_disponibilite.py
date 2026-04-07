# ARTEFACT — Story 5.6 : tests unitaires build_actions_ha avec est_publiable.
"""Tests de cohérence visuelle — boutons HA fidèles à leur disponibilité réelle.

Couvre les AC 1, 4, 5 de la Story 5.6 :
- AC 1 : publier grisé quand est_publiable=False (bridge OK)
- AC 4 : comportement inchangé quand est_publiable=True (non-régression)
- AC 5 : supprimer indépendant de est_publiable
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from models.actions_ha import build_actions_ha, _RAISON_NON_PUBLIABLE


# ---------------------------------------------------------------------------
# AC 1 — publier grisé pour équipement non-publiable (bridge OK)
# ---------------------------------------------------------------------------

class TestEstPubliableFalseBridgeOk:
    def test_publier_disponible_false(self):
        """est_publiable=False + bridge OK → publier.disponible=False."""
        actions = build_actions_ha(
            est_publie_ha=False,
            est_inclus=True,
            bridge_disponible=True,
            est_publiable=False,
        )
        assert actions["publier"]["disponible"] is False

    def test_publier_raison_lisible_non_vide(self):
        """est_publiable=False → raison_indisponibilite non vide et lisible."""
        actions = build_actions_ha(
            est_publie_ha=False,
            est_inclus=True,
            bridge_disponible=True,
            est_publiable=False,
        )
        raison = actions["publier"]["raison_indisponibilite"]
        assert raison is not None
        assert len(raison) > 0
        assert raison == _RAISON_NON_PUBLIABLE

    def test_publier_raison_couvre_pub_decision_none(self):
        """pub_decision=None → est_publiable=False → même raison lisible."""
        # Simulation : est_publiable=False représente aussi pub_decision=None
        actions = build_actions_ha(
            est_publie_ha=False,
            est_inclus=True,
            bridge_disponible=True,
            est_publiable=False,
        )
        assert actions["publier"]["disponible"] is False
        assert actions["publier"]["raison_indisponibilite"] == _RAISON_NON_PUBLIABLE

    def test_label_publier_reste_contextuel(self):
        """Le label reste contextuel (Créer / Republier) même quand grisé."""
        actions_non_publie = build_actions_ha(
            est_publie_ha=False, est_inclus=True, bridge_disponible=True, est_publiable=False
        )
        actions_publie = build_actions_ha(
            est_publie_ha=True, est_inclus=True, bridge_disponible=True, est_publiable=False
        )
        assert "Créer" in actions_non_publie["publier"]["label"]
        assert "Republier" in actions_publie["publier"]["label"]


# ---------------------------------------------------------------------------
# AC 5 — supprimer indépendant de est_publiable
# ---------------------------------------------------------------------------

class TestSupprimerIndependantDeEstPubliable:
    def test_publie_ha_true_est_publiable_false_supprimer_actif(self):
        """est_publie_ha=True + est_publiable=False → supprimer.disponible=True (entité HA existante)."""
        actions = build_actions_ha(
            est_publie_ha=True,
            est_inclus=True,
            bridge_disponible=True,
            est_publiable=False,
        )
        assert actions["publier"]["disponible"] is False
        assert actions["supprimer"]["disponible"] is True

    def test_publie_ha_false_est_publiable_false_supprimer_grise(self):
        """est_publie_ha=False + est_publiable=False → supprimer.disponible=False (rien à supprimer)."""
        actions = build_actions_ha(
            est_publie_ha=False,
            est_inclus=True,
            bridge_disponible=True,
            est_publiable=False,
        )
        assert actions["supprimer"]["disponible"] is False

    def test_supprimer_raison_independante_de_est_publiable(self):
        """La raison_indisponibilite de supprimer ne mentionne pas la publiabilité."""
        actions = build_actions_ha(
            est_publie_ha=False,
            est_inclus=True,
            bridge_disponible=True,
            est_publiable=False,
        )
        raison_sup = actions["supprimer"]["raison_indisponibilite"]
        # La raison de supprimer doit être différente de celle de publier
        assert raison_sup != _RAISON_NON_PUBLIABLE


# ---------------------------------------------------------------------------
# AC 4 — comportement inchangé quand est_publiable=True (non-régression)
# ---------------------------------------------------------------------------

class TestEstPubliableVraiComportementInchange:
    def test_publiable_true_par_defaut_publie_non_publie(self):
        """est_publiable=True (défaut) → comportement Story 5.1 intact."""
        actions_defaut = build_actions_ha(
            est_publie_ha=False, est_inclus=True, bridge_disponible=True
        )
        actions_explicite = build_actions_ha(
            est_publie_ha=False, est_inclus=True, bridge_disponible=True, est_publiable=True
        )
        assert actions_defaut == actions_explicite

    def test_publiable_true_publier_disponible(self):
        """est_publiable=True → publier.disponible=True pour inclus bridge OK."""
        actions = build_actions_ha(
            est_publie_ha=False,
            est_inclus=True,
            bridge_disponible=True,
            est_publiable=True,
        )
        assert actions["publier"]["disponible"] is True
        assert actions["publier"]["raison_indisponibilite"] is None

    def test_publiable_true_publie_ha_true(self):
        """est_publiable=True + est_publie_ha=True → publier et supprimer disponibles."""
        actions = build_actions_ha(
            est_publie_ha=True,
            est_inclus=True,
            bridge_disponible=True,
            est_publiable=True,
        )
        assert actions["publier"]["disponible"] is True
        assert actions["supprimer"]["disponible"] is True


# ---------------------------------------------------------------------------
# Bridge down prioritaire sur est_publiable
# ---------------------------------------------------------------------------

class TestBridgeDownPrioritaireSurEstPubliable:
    def test_bridge_down_est_publiable_false_tout_grise(self):
        """Bridge down + est_publiable=False → tout grisé (bridge prioritaire)."""
        actions = build_actions_ha(
            est_publie_ha=False,
            est_inclus=True,
            bridge_disponible=False,
            est_publiable=False,
        )
        assert actions["publier"]["disponible"] is False
        assert actions["supprimer"]["disponible"] is False
        # La raison doit mentionner le bridge, pas la publiabilité
        raison_pub = actions["publier"]["raison_indisponibilite"]
        assert raison_pub != _RAISON_NON_PUBLIABLE
        assert "pont" in raison_pub.lower() or "bridge" in raison_pub.lower() or "indisponible" in raison_pub.lower()

    def test_bridge_down_est_publiable_true_tout_grise(self):
        """Bridge down + est_publiable=True → tout grisé (bridge prioritaire — inchangé 5.1)."""
        actions = build_actions_ha(
            est_publie_ha=True,
            est_inclus=True,
            bridge_disponible=False,
            est_publiable=True,
        )
        assert actions["publier"]["disponible"] is False
        assert actions["supprimer"]["disponible"] is False

    def test_bridge_down_raison_est_bridge_pas_publiabilite(self):
        """Bridge down : raison publier = bridge, même avec est_publiable=False."""
        actions_bridge_publiable = build_actions_ha(
            est_publie_ha=False, est_inclus=True, bridge_disponible=False, est_publiable=True
        )
        actions_bridge_non_publiable = build_actions_ha(
            est_publie_ha=False, est_inclus=True, bridge_disponible=False, est_publiable=False
        )
        # Les deux cas retournent la même raison bridge
        assert (
            actions_bridge_publiable["publier"]["raison_indisponibilite"]
            == actions_bridge_non_publiable["publier"]["raison_indisponibilite"]
        )
