"""Story 16.7 — Profils partageables : export anonymisable + import sous schéma versionné.

Étend le contrat d'override (pe-epic-16) avec l'export/import de profils, en réutilisant
strictement les primitives de persistance existantes (`overrides.py`) — aucun nouveau module
de persistance, aucun chemin d'écriture parallèle (Dev Notes 16.1/16.7).

Invariants figés ici :
- AC5 : un profil exporté est anonymisable — aucun secret / hostname / chemin absolu /
  identifiant machine, même si `ha_overrides.json` a été édité à la main (whitelist stricte).
- AC6 : l'import réutilise le refus explicite de `schema_version` (`{1, 2}`) ; version
  absente / non entière / non supportée → refus explicite (ValueError), jamais un cold-start.
- Aucun `sync`/`transport`/MQTT dans le chemin export/import (assertion structurelle).
- D10 : l'export/import ne touche que la couche override, jamais le `generic_type` natif.
"""
from __future__ import annotations

import ast
import inspect
import json
import os

import pytest

from mapping import overrides as overrides_module
from mapping.overrides import (
    export_profile,
    import_profile,
    list_equipment_overrides,
    list_overrides,
    save_equipment_override,
    save_override,
)


# --------------------------------------------------------------------------- #
# Task 1 — Export de profil anonymisable (AC5)
# --------------------------------------------------------------------------- #

def test_export_profile_round_trip_cles_composites(tmp_path):
    """Un export reflète les overrides persistés, indexés par clés composites eq:cmd / eq."""
    data_dir = str(tmp_path)
    save_override(553, 5138, {"ha_entity_type": "switch"}, data_dir)
    save_equipment_override(67, {"publication_override": "exclude"}, data_dir)

    profile = export_profile(data_dir)

    assert profile["schema_version"] in (1, 2)
    assert "553:5138" in profile["overrides"]
    assert profile["overrides"]["553:5138"]["ha_entity_type"] == "switch"
    assert profile["equipment_overrides"]["67"]["publication_override"] == "exclude"


def test_export_profile_fichier_absent_retourne_profil_vide(tmp_path):
    """Aucun override persisté → profil bien formé mais vide (pas d'erreur)."""
    profile = export_profile(str(tmp_path))
    assert profile == {"schema_version": 2, "overrides": {}, "equipment_overrides": {}}


def test_export_profile_ne_fuit_aucun_motif_sensible(tmp_path):
    """AC5 : même avec un ha_overrides.json pollué de champs sensibles, l'export les strippe.

    Whitelist stricte : seuls source / ha_entity_type / publication_override survivent.
    """
    data_dir = str(tmp_path)
    # Fichier pollué à la main avec des champs qui ne doivent JAMAIS sortir d'un profil.
    polluted = {
        "schema_version": 2,
        "overrides": {
            "553:5138": {
                "source": "user",
                "ha_entity_type": "switch",
                "publication_override": None,
                "localSecret": "s3cr3t-token-abc",
                "hostname": "box-alexandre.local",
                "abs_path": "/Users/alexandre/Dev/jeedom/ha_overrides.json",
                "machine_id": "aa:bb:cc:dd:ee:ff",
            }
        },
        "equipment_overrides": {
            "67": {
                "source": "user",
                "publication_override": "exclude",
                "token": "Bearer xyz",
                "owner_email": "alexandre@example.com",
            }
        },
    }
    with open(os.path.join(data_dir, "ha_overrides.json"), "w", encoding="utf-8") as f:
        json.dump(polluted, f)

    profile = export_profile(data_dir)
    blob = json.dumps(profile)

    for forbidden in (
        "localSecret", "s3cr3t", "hostname", "box-alexandre",
        "/Users/", "machine_id", "aa:bb:cc", "token", "Bearer",
        "owner_email", "example.com",
    ):
        assert forbidden not in blob, f"motif sensible fuité dans le profil : {forbidden}"

    # La sémantique de mapping, elle, est bien conservée.
    assert profile["overrides"]["553:5138"] == {"source": "user", "ha_entity_type": "switch"}
    assert profile["equipment_overrides"]["67"] == {"source": "user", "publication_override": "exclude"}


# --------------------------------------------------------------------------- #
# Task 2 — Import de profil sous schéma versionné (AC6)
# --------------------------------------------------------------------------- #

def test_import_profile_round_trip_export_import(tmp_path):
    """export → import → export : idempotence des clés composites et de la sémantique."""
    source_dir = str(tmp_path / "src")
    dest_dir = str(tmp_path / "dst")
    os.makedirs(source_dir)
    os.makedirs(dest_dir)

    save_override(553, 5138, {"ha_entity_type": "switch"}, source_dir)
    save_override(554, 5535, {"ha_entity_type": "sensor"}, source_dir)
    save_equipment_override(67, {"publication_override": "exclude"}, source_dir)

    profile = export_profile(source_dir)
    import_profile(profile, dest_dir)

    assert export_profile(dest_dir)["overrides"] == profile["overrides"]
    assert export_profile(dest_dir)["equipment_overrides"] == profile["equipment_overrides"]
    assert list_overrides(dest_dir)["553:5138"]["ha_entity_type"] == "switch"
    assert list_equipment_overrides(dest_dir)["67"]["publication_override"] == "exclude"


@pytest.mark.parametrize("bad_version", [None, "2", 3, 0, True, 1.0])
def test_import_profile_refuse_schema_version_invalide(tmp_path, bad_version):
    """AC6 : version absente / non entière / non supportée → ValueError explicite."""
    profile = {"schema_version": bad_version, "overrides": {}, "equipment_overrides": {}}
    with pytest.raises(ValueError):
        import_profile(profile, str(tmp_path))


def test_import_profile_schema_version_absent_refuse(tmp_path):
    """AC6 : schema_version absent → refus explicite (jamais un cold-start silencieux)."""
    with pytest.raises(ValueError):
        import_profile({"overrides": {}, "equipment_overrides": {}}, str(tmp_path))


@pytest.mark.parametrize("good_version", [1, 2])
def test_import_profile_accepte_versions_supportees(tmp_path, good_version):
    """AC6 : schema_version ∈ {1, 2} accepté."""
    data_dir = str(tmp_path)
    profile = {
        "schema_version": good_version,
        "overrides": {"553:5138": {"ha_entity_type": "switch"}},
        "equipment_overrides": {},
    }
    import_profile(profile, data_dir)
    assert list_overrides(data_dir)["553:5138"]["ha_entity_type"] == "switch"


def test_import_profile_strippe_champs_non_whitelistes(tmp_path):
    """Un profil malveillant ne peut pas injecter de champ sensible dans le fichier local."""
    data_dir = str(tmp_path)
    profile = {
        "schema_version": 2,
        "overrides": {
            "553:5138": {"ha_entity_type": "switch", "localSecret": "inject", "path": "/etc/x"}
        },
        "equipment_overrides": {},
    }
    import_profile(profile, data_dir)

    stored = list_overrides(data_dir)["553:5138"]
    assert "localSecret" not in stored
    assert "path" not in stored
    assert stored["ha_entity_type"] == "switch"


def test_import_profile_cle_composite_invalide_refusee(tmp_path):
    """Une clé d'override non 'eq:cmd' est refusée explicitement (pas d'écriture partielle muette)."""
    profile = {
        "schema_version": 2,
        "overrides": {"filtration_pompe": {"ha_entity_type": "switch"}},
        "equipment_overrides": {},
    }
    with pytest.raises(ValueError):
        import_profile(profile, str(tmp_path))


# --------------------------------------------------------------------------- #
# Invariant structurel — aucun couplage sync/transport/MQTT (D8)
# --------------------------------------------------------------------------- #

def test_export_import_sans_dependance_sync_transport_mqtt():
    """AC6 / D8 : le chemin export/import ne fait aucun appel sync/transport/MQTT.

    Assertion structurelle : le module overrides n'importe aucun symbole de sync / transport
    / mqtt (cf. convention 16.1). On inspecte les sources d'export_profile et import_profile.
    """
    source = inspect.getsource(export_profile) + "\n" + inspect.getsource(import_profile)
    tree = ast.parse(source)  # fonctions module-level : source non indentée, parse direct

    forbidden = ("sync", "transport", "mqtt", "publisher", "paho")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [n.name for n in node.names] + [getattr(node, "module", "") or ""]
            for name in names:
                assert not any(f in name.lower() for f in forbidden), \
                    f"import interdit dans le chemin export/import : {name}"

    # Et le module lui-même ne référence aucun de ces couplages au niveau import.
    module_src = inspect.getsource(overrides_module)
    for banned in ("import sync", "import transport", "from transport", "paho.mqtt"):
        assert banned not in module_src, f"couplage interdit détecté : {banned}"
