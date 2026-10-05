"""CC-34 — les écritures d'overrides sont atomiques et conservent les droits."""
from __future__ import annotations

import builtins
import json
import os
import stat

import pytest

from mapping import overrides as overrides_module
from mapping.overrides import (
    remove_equipment_override,
    remove_override,
    save_equipment_override,
    save_override,
)


def _write_raw(tmp_path, raw):
    path = tmp_path / "ha_overrides.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def _raw(*, command=True, equipment=True):
    return {
        "schema_version": 2,
        "overrides": {"1:2": {"source": "user", "ha_entity_type": "switch"}}
        if command else {},
        "equipment_overrides": {"1": {"source": "user", "publication_override": "exclude"}}
        if equipment else {},
    }


def test_echec_json_dump_preserve_octets_et_supprime_temporaire(tmp_path, monkeypatch, caplog):
    """Un échec avant replace ne tronque jamais le fichier publié."""
    path = _write_raw(tmp_path, _raw())
    original = path.read_bytes()

    def failing_dump(*args, **kwargs):
        raise OSError("échec injecté")

    monkeypatch.setattr(overrides_module.json, "dump", failing_dump)

    assert save_override(3, 4, {"ha_entity_type": "light"}, str(tmp_path)) is False
    assert path.read_bytes() == original
    assert list(tmp_path.glob(".ha_overrides.*")) == []
    assert "Échec sauvegarde override : échec injecté" in caplog.text


@pytest.mark.parametrize(
    "operation",
    (
        lambda directory: save_override(3, 4, {"ha_entity_type": "light"}, directory),
        lambda directory: save_equipment_override(3, {"publication_override": "exclude"}, directory),
        lambda directory: remove_override(1, 2, directory),
        lambda directory: remove_equipment_override(1, directory),
    ),
)
def test_les_quatre_ecritures_remplacent_un_temporaire_du_meme_dossier(
    tmp_path, monkeypatch, operation,
):
    """Le fichier final n'est jamais ouvert en écriture et est remplacé atomiquement."""
    final_path = _write_raw(tmp_path, _raw())
    real_open = builtins.open
    replaced = []

    def guarded_open(file, mode="r", *args, **kwargs):
        if os.fspath(file) == os.fspath(final_path) and any(flag in mode for flag in "wax+"):
            raise AssertionError("le fichier final ne doit pas être ouvert en écriture")
        return real_open(file, mode, *args, **kwargs)

    def recording_replace(source, destination):
        replaced.append((source, destination))
        return real_replace(source, destination)

    real_replace = os.replace
    monkeypatch.setattr(builtins, "open", guarded_open)
    monkeypatch.setattr(overrides_module.os, "replace", recording_replace)

    assert operation(str(tmp_path)) is True
    assert len(replaced) == 1
    assert replaced[0][1] == str(final_path)
    assert os.path.dirname(replaced[0][0]) == str(tmp_path)
    assert not os.path.exists(replaced[0][0])


def test_ecriture_conserve_les_droits_du_fichier_existant(tmp_path):
    path = _write_raw(tmp_path, _raw())
    os.chmod(path, 0o640)

    assert save_override(3, 4, {"ha_entity_type": "light"}, str(tmp_path)) is True
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


def test_contrat_visible_retours_et_schema_json(tmp_path):
    """Les retours CRUD et le schéma v2 restent identiques après le changement interne."""
    directory = str(tmp_path)

    assert save_override(3, 4, {"ha_entity_type": "light"}, directory) is True
    assert save_equipment_override(3, {"publication_override": "exclude"}, directory) is True
    assert remove_override(3, 4, directory) is True
    assert remove_equipment_override(3, directory) is True
    assert remove_override(3, 4, directory) is False

    persisted = json.loads((tmp_path / "ha_overrides.json").read_text(encoding="utf-8"))
    assert persisted == {"schema_version": 2, "overrides": {}, "equipment_overrides": {}}
