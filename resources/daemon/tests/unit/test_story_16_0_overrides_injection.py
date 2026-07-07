"""Story 16.0/16.1 - Contrat d'override : invariants D10/D11 et persistance backend v1.

Ce module fige, sous forme de tests exécutables, les invariants architecturaux
non négociables du contrat d'override (gates epic-level pe-epic-16) tels que documentés
dans `architecture-delta-pe-epic-16-mapping-configurable.md` (D9, D10, D11) :

- un override HA ne modifie jamais le `generic_type` Jeedom natif (D10) ;
- une décision de mapping reste soumise à `validate_projection()` même en présence d'un
  override, qui ne bypasse jamais un échec de validation structurelle (D11) ;
- (16.1) les overrides sont persistés dans `data/ha_overrides.json` (`schema_version: 1`,
  clé composite `eq_id:cmd_id`), avec refus explicite (jamais un cold-start silencieux)
  sur un schéma invalide/non supporté (D9).

Story 16.2 doit étendre ce fichier (pas en créer un nouveau) une fois l'injection dans le
pipeline (`apply_*`/`resolve_*`) disponible.
"""

from __future__ import annotations

import ast
import inspect
import json
import logging
import os

import pytest

from mapping import overrides as overrides_module
from mapping.overrides import list_overrides, remove_override, save_override
from mapping.switch import SwitchMapper
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from validation.ha_component_registry import validate_projection


def _snapshot(eq: JeedomEqLogic) -> TopologySnapshot:
    return TopologySnapshot(
        timestamp="2026-07-06T00:00:00Z",
        objects={1: JeedomObject(id=1, name="Local technique")},
        eq_logics={eq.id: eq},
    )


def _switch_eq(*, eq_id: int, cmd_id: int, generic_type: str = "SWITCH_STATE") -> JeedomEqLogic:
    return JeedomEqLogic(
        id=eq_id,
        name=f"Switch {eq_id}",
        object_id=1,
        eq_type_name="virtual",
        cmds=[
            JeedomCmd(
                id=cmd_id,
                name=f"Cmd {cmd_id}",
                generic_type=generic_type,
                type="info",
                sub_type="binary",
                unit=None,
                current_value=1,
            )
        ],
    )


def test_generic_type_natif_jamais_mute_par_le_pipeline_de_mapping():
    """D10 : le pipeline de mapping (`map()`) ne mute jamais le `generic_type` Jeedom natif.

    Baseline de non-régression : ce test doit rester vert une fois `overrides.py` (Story 16.1)
    introduit, puisque D8/16a garantit que le patch d'override s'applique uniquement sur une
    copie du `MappingResult`, jamais sur l'objet `JeedomCmd`/`JeedomEqLogic` source.
    """
    eq = _switch_eq(eq_id=16001, cmd_id=160011, generic_type="SWITCH_STATE")
    original_generic_type = eq.cmds[0].generic_type

    SwitchMapper().map(eq, _snapshot(eq))

    assert eq.cmds[0].generic_type == original_generic_type == "SWITCH_STATE"


def test_validate_projection_reste_autoritaire_sur_un_ha_entity_type_incompatible():
    """D11 : une projection structurellement invalide n'est jamais considérée valide.

    Ce test fige le comportement de `validate_projection()` face à un `ha_entity_type`
    inconnu du registre HA — invariant que Story 16.1+ doit respecter : un override
    référençant un `ha_entity_type` incompatible avec les capabilities détectées ne doit
    jamais transformer un `is_valid=False` en `is_valid=True` par contournement.
    """
    validity = validate_projection("ha_entity_type_inexistant_16_0", capabilities=None)

    assert validity.is_valid is False
    assert validity.reason_code == "ha_component_unknown"


def _read_overrides_file(data_dir: str) -> dict:
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_save_override_puis_list_overrides_round_trip(tmp_path):
    """AC1 : un override sauvegardé est relisible via la clé composite eq_id:cmd_id."""
    data_dir = str(tmp_path)

    save_override(553, 5138, {"ha_entity_type": "switch"}, data_dir)

    assert list_overrides(data_dir) == {"553:5138": {"ha_entity_type": "switch", "source": "user"}}


def test_save_override_persiste_schema_version_2_sur_disque(tmp_path):
    """AC1/AC3 : persistance fichier JSON avec schema_version, pas de table SQL.

    Story 16.3 (SCP 2026-07-07) : `_SCHEMA_VERSION` est passé à 2 — tout `save_override`
    (même sur un fichier absent) écrit désormais `schema_version: 2` (migration
    transparente, bump au premier write).
    """
    data_dir = str(tmp_path)

    save_override(553, 5138, {"ha_entity_type": "switch"}, data_dir)

    on_disk = _read_overrides_file(data_dir)
    assert on_disk["schema_version"] == 2
    assert on_disk["overrides"]["553:5138"]["source"] == "user"


def test_save_override_ajoute_source_user_par_defaut(tmp_path):
    """D9 : champ source: 'user' appliqué par défaut si absent de l'override fourni."""
    data_dir = str(tmp_path)

    save_override(553, 5138, {"ha_entity_type": "switch"}, data_dir)

    assert list_overrides(data_dir)["553:5138"]["source"] == "user"


def test_save_override_respecte_une_source_explicite(tmp_path):
    """D9 : 'source' n'est jamais écrasé si déjà fourni (anticipe 'suggested' en 16.3+)."""
    data_dir = str(tmp_path)

    save_override(553, 5138, {"ha_entity_type": "switch", "source": "suggested"}, data_dir)

    assert list_overrides(data_dir)["553:5138"]["source"] == "suggested"


def test_save_override_ne_supprime_pas_les_entrees_existantes(tmp_path):
    """Round-trip multi-entrées : sauvegarder un second override ne perd pas le premier."""
    data_dir = str(tmp_path)

    save_override(553, 5138, {"ha_entity_type": "switch"}, data_dir)
    save_override(554, 5535, {"ha_entity_type": "sensor"}, data_dir)

    assert set(list_overrides(data_dir).keys()) == {"553:5138", "554:5535"}


def test_remove_override_supprime_une_entree_existante(tmp_path):
    data_dir = str(tmp_path)
    save_override(553, 5138, {"ha_entity_type": "switch"}, data_dir)

    removed = remove_override(553, 5138, data_dir)

    assert removed is True
    assert list_overrides(data_dir) == {}


def test_remove_override_retourne_false_si_entree_absente(tmp_path):
    data_dir = str(tmp_path)

    assert remove_override(999, 1, data_dir) is False


def test_list_overrides_retourne_vide_si_fichier_absent(tmp_path):
    """Cold start : aucun fichier encore créé — dict vide, pas d'exception."""
    assert list_overrides(str(tmp_path)) == {}


def test_list_overrides_refuse_schema_version_trop_recente_avec_diagnostic(tmp_path, caplog):
    """AC4 : schema_version inconnue/trop récente -> refus explicite, pas de cold-start silencieux.

    Story 16.3 a étendu les versions supportées à {1, 2} — ce test utilise donc désormais
    une version au-delà de cet ensemble (3) pour continuer à couvrir le refus explicite.
    """
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": 3, "overrides": {"553:5138": {"source": "user"}}}, f)

    with caplog.at_level(logging.ERROR):
        result = list_overrides(data_dir)

    assert result == {}
    assert any("schema_version" in record.getMessage() for record in caplog.records)


def test_list_overrides_refuse_schema_version_absente(tmp_path, caplog):
    """AC4 : schema_version absente du fichier -> refus explicite (diagnostic loggé)."""
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"overrides": {"553:5138": {"source": "user"}}}, f)

    with caplog.at_level(logging.ERROR):
        result = list_overrides(data_dir)

    assert result == {}
    assert any("schema_version" in record.getMessage() for record in caplog.records)


def test_save_override_refuse_ecraser_un_fichier_de_schema_invalide(tmp_path):
    """AC4 : un override ne bypasse jamais un schéma invalide -> ValueError, fichier intact."""
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": 99, "overrides": {}}, f)

    with pytest.raises(ValueError):
        save_override(553, 5138, {"ha_entity_type": "switch"}, data_dir)

    on_disk = _read_overrides_file(data_dir)
    assert on_disk["schema_version"] == 99


def test_list_overrides_refuse_un_fichier_json_corrompu_avec_diagnostic(tmp_path, caplog):
    """AC4 : fichier présent mais JSON illisible -> refus explicite, jamais un cold-start silencieux."""
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("{ ceci n'est pas du JSON valide ,,, ")

    with caplog.at_level(logging.ERROR):
        result = list_overrides(data_dir)

    assert result == {}
    assert any("corrompu" in record.getMessage() for record in caplog.records)


def test_list_overrides_refuse_une_racine_non_objet_avec_diagnostic(tmp_path, caplog):
    """AC4 : racine JSON non-objet (liste) -> refus explicite (diagnostic loggé)."""
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(["pas", "un", "objet"], f)

    with caplog.at_level(logging.ERROR):
        result = list_overrides(data_dir)

    assert result == {}
    assert any("racine non-objet" in record.getMessage() for record in caplog.records)


def test_list_overrides_refuse_cle_overrides_absente_avec_diagnostic(tmp_path, caplog):
    """AC4 : schema_version valide mais clé 'overrides' absente -> refus explicite."""
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1}, f)

    with caplog.at_level(logging.ERROR):
        result = list_overrides(data_dir)

    assert result == {}
    assert any("overrides" in record.getMessage() for record in caplog.records)


def test_list_overrides_refuse_cle_overrides_non_dict_avec_diagnostic(tmp_path, caplog):
    """AC4 : clé 'overrides' présente mais non-objet (liste) -> refus explicite."""
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "overrides": []}, f)

    with caplog.at_level(logging.ERROR):
        result = list_overrides(data_dir)

    assert result == {}
    assert any("overrides" in record.getMessage() for record in caplog.records)


def test_list_overrides_refuse_schema_version_non_entiere_avec_diagnostic(tmp_path, caplog):
    """AC4 : schema_version de type string ('1') -> refus explicite (pas de coercion silencieuse)."""
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": "1", "overrides": {"553:5138": {"source": "user"}}}, f)

    with caplog.at_level(logging.ERROR):
        result = list_overrides(data_dir)

    assert result == {}
    assert any("schema_version" in record.getMessage() for record in caplog.records)


def test_list_overrides_refuse_schema_version_booleenne_avec_diagnostic(tmp_path, caplog):
    """AC4 : schema_version booléenne (True == 1 en Python) -> refus explicite malgré l'égalité numérique.

    Garde-fou contre le piège `bool` sous-classe de `int` : `True == 1` mais un booléen
    n'est jamais une version de schéma valide.
    """
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": True, "overrides": {"553:5138": {"source": "user"}}}, f)

    with caplog.at_level(logging.ERROR):
        result = list_overrides(data_dir)

    assert result == {}
    assert any("schema_version" in record.getMessage() for record in caplog.records)


def test_remove_override_retourne_false_sur_schema_invalide(tmp_path):
    """AC4 : remove_override ne touche jamais un fichier de schéma invalide -> False, fichier intact."""
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": 99, "overrides": {"553:5138": {"source": "user"}}}, f)

    assert remove_override(553, 5138, data_dir) is False

    on_disk = _read_overrides_file(data_dir)
    assert on_disk["schema_version"] == 99
    assert on_disk["overrides"] == {"553:5138": {"source": "user"}}


def test_overrides_module_n_importe_jamais_transport_sync_ou_mqtt():
    """AC5 : ce module ne touche ni au pipeline de sync, ni au transport MQTT.

    Assertion structurelle plutôt qu'un mock : aucun import de ces modules dans
    mapping/overrides.py, donc aucun appel possible (pas juste "non appelé" en pratique).
    """
    source = inspect.getsource(overrides_module)
    tree = ast.parse(source)

    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.add(node.module.split(".")[0])

    forbidden = {"transport", "sync", "paho", "mqtt"}
    assert imported_names.isdisjoint(forbidden)
