"""Story 16.3 — overrides de publication et exclusion explicite (AC1/AC2).

Couvre :
- Task 1 : schéma v2 (`equipment_overrides` séparé, champ `publication_override` aux deux
  niveaux), migration transparente v1 → v2 (lecture non disruptive, bump au premier write).
- Task 2 : `resolve_publication_override()` — fonction pure, précédence exclusion-équipement
  (veto absolu) > override-commande > force_publish-équipement (défaut) > nominal.
- Task 3 : `decide_publication()` étendu (paramètre `publication_override`), injection entre
  l'étape 3 (projection valide) et les étapes 4a/4b (PRODUCT_SCOPE / confidence_policy).
- Task 4 : reason_codes dédiés (`publication_excluded_eqlogic`/`publication_excluded_command`/
  `publication_forced`), diagnostic `reason_details` (`underlying_confidence`,
  `publication_override_applied`, `override_source`), sans jamais réécrire le reason nominal.
- Task 5 : garde-fou I2 — un override "forcer publication" ne bypass jamais une projection
  invalide, ni le scope produit (PRODUCT_SCOPE).
- Non-régression : absence d'override = comportement identique à l'existant.

Isolation :
  - Aucune dépendance MQTT/broker/daemon pour les tests `overrides.py`/`decide_publication.py`
    (fonctions pures / I/O fichier temporaire uniquement, `tmp_path`).
  - Le seul test touchant `http_server.py` appelle directement le helper interne
    `_resolve_publication_override_for_mapping` (même précédent que Story 16.2 appelant
    `_detect_lifecycle_changes` directement), sans mock MQTT/aiohttp.
"""
from __future__ import annotations

import json
import os

from mapping.overrides import (
    list_equipment_overrides,
    list_overrides,
    remove_equipment_override,
    resolve_publication_override,
    save_equipment_override,
    save_override,
)
from models.decide_publication import decide_publication
from models.mapping import LightCapabilities, MappingResult, ProjectionValidity
import transport.http_server as http_server


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _valid_pv() -> ProjectionValidity:
    return ProjectionValidity(
        is_valid=True, reason_code=None, missing_fields=[], missing_capabilities=[]
    )


def _invalid_pv(reason_code: str = "ha_missing_state_topic") -> ProjectionValidity:
    return ProjectionValidity(
        is_valid=False, reason_code=reason_code, missing_fields=[], missing_capabilities=[]
    )


def _make_mapping(
    *,
    jeedom_eq_id: int = 553,
    ha_entity_type: str = "light",
    confidence: str = "sure",
    projection_validity: ProjectionValidity | None = None,
) -> MappingResult:
    mr = MappingResult(
        ha_entity_type=ha_entity_type,
        confidence=confidence,
        reason_code="light_on_off",
        jeedom_eq_id=jeedom_eq_id,
        ha_unique_id=f"jeedom2ha_eq_{jeedom_eq_id}",
        ha_name="Test eq",
        capabilities=LightCapabilities(has_on_off=True),
    )
    mr.projection_validity = projection_validity if projection_validity is not None else _valid_pv()
    return mr


def _read_overrides_file(data_dir: str) -> dict:
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #
# Task 1 — Schéma v2 : equipment_overrides + CRUD                             #
# --------------------------------------------------------------------------- #

def test_list_equipment_overrides_retourne_vide_si_fichier_absent(tmp_path):
    assert list_equipment_overrides(str(tmp_path)) == {}


def test_save_equipment_override_puis_list_round_trip(tmp_path):
    data_dir = str(tmp_path)

    save_equipment_override(553, {"publication_override": "exclude"}, data_dir)

    assert list_equipment_overrides(data_dir) == {
        "553": {"publication_override": "exclude", "source": "user"}
    }


def test_save_equipment_override_persiste_schema_version_2(tmp_path):
    data_dir = str(tmp_path)

    save_equipment_override(553, {"publication_override": "force_publish"}, data_dir)

    on_disk = _read_overrides_file(data_dir)
    assert on_disk["schema_version"] == 2
    assert on_disk["equipment_overrides"]["553"]["publication_override"] == "force_publish"


def test_remove_equipment_override_supprime_une_entree_existante(tmp_path):
    data_dir = str(tmp_path)
    save_equipment_override(553, {"publication_override": "exclude"}, data_dir)

    removed = remove_equipment_override(553, data_dir)

    assert removed is True
    assert list_equipment_overrides(data_dir) == {}


def test_remove_equipment_override_retourne_false_si_absente(tmp_path):
    assert remove_equipment_override(999, str(tmp_path)) is False


def test_equipment_overrides_et_overrides_sont_des_sections_separees(tmp_path):
    """SCP 2026-07-07 : pas de mélange de clés — `overrides` reste `eq_id:cmd_id`."""
    data_dir = str(tmp_path)

    save_override(553, 5138, {"ha_entity_type": "switch"}, data_dir)
    save_equipment_override(553, {"publication_override": "exclude"}, data_dir)

    assert list_overrides(data_dir) == {
        "553:5138": {"ha_entity_type": "switch", "source": "user"}
    }
    assert list_equipment_overrides(data_dir) == {
        "553": {"publication_override": "exclude", "source": "user"}
    }


def test_fichier_v1_existant_se_charge_sans_equipment_overrides_ni_reecriture_disque(tmp_path):
    """Migration transparente : un fichier v1 (Story 16.1/16.2) reste lisible tel quel,
    `equipment_overrides` synthétisé à `{}` en mémoire, AUCUNE réécriture disque déclenchée
    par une lecture pure (D9/D11)."""
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "overrides": {"553:5138": {"source": "user"}}}, f)

    assert list_overrides(data_dir) == {"553:5138": {"source": "user"}}
    assert list_equipment_overrides(data_dir) == {}

    on_disk_after_read = _read_overrides_file(data_dir)
    assert on_disk_after_read["schema_version"] == 1  # inchangé par la lecture


def test_fichier_v1_existant_bascule_v2_sur_disque_au_premier_write(tmp_path):
    """Le bump `schema_version: 2` sur disque n'intervient qu'au prochain
    save_override/save_equipment_override — jamais depuis un chemin de lecture pure."""
    data_dir = str(tmp_path)
    path = os.path.join(data_dir, "ha_overrides.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "overrides": {"553:5138": {"source": "user"}}}, f)

    save_override(554, 5535, {"ha_entity_type": "sensor"}, data_dir)

    on_disk = _read_overrides_file(data_dir)
    assert on_disk["schema_version"] == 2
    assert on_disk["overrides"]["553:5138"]["source"] == "user"  # préservé
    assert on_disk["overrides"]["554:5535"]["ha_entity_type"] == "sensor"


# --------------------------------------------------------------------------- #
# Task 2 — resolve_publication_override() : précédence                       #
# --------------------------------------------------------------------------- #

def test_resolve_publication_override_absence_totale_retourne_none():
    assert resolve_publication_override(553, 5138, {}, {}) is None


def test_resolve_publication_override_exclusion_commande():
    overrides = {"553:5138": {"publication_override": "exclude"}}
    assert resolve_publication_override(553, 5138, overrides, {}) == "exclude_command"


def test_resolve_publication_override_exclusion_equipement():
    equipment_overrides = {"553": {"publication_override": "exclude"}}
    assert resolve_publication_override(553, 5138, {}, equipment_overrides) == "exclude_eqlogic"


def test_resolve_publication_override_force_publish_commande():
    overrides = {"553:5138": {"publication_override": "force_publish"}}
    assert resolve_publication_override(553, 5138, overrides, {}) == "force_publish"


def test_resolve_publication_override_force_publish_equipement_par_defaut():
    """Aucun override de commande -> le force_publish équipement s'applique en défaut."""
    equipment_overrides = {"553": {"publication_override": "force_publish"}}
    assert resolve_publication_override(553, 9999, {}, equipment_overrides) == "force_publish"


def test_resolve_publication_override_precedence_exclusion_equipement_bat_force_publish_commande():
    """Précédence tranchée par le SCP : veto exclusion-équipement (1) > override-commande (2)."""
    overrides = {"553:5138": {"publication_override": "force_publish"}}
    equipment_overrides = {"553": {"publication_override": "exclude"}}

    result = resolve_publication_override(553, 5138, overrides, equipment_overrides)

    assert result == "exclude_eqlogic"


def test_resolve_publication_override_precedence_commande_bat_force_publish_equipement():
    """Override de commande (2) plus spécifique que le force_publish équipement (3) par défaut."""
    overrides = {"553:5138": {"publication_override": "exclude"}}
    equipment_overrides = {"553": {"publication_override": "force_publish"}}

    result = resolve_publication_override(553, 5138, overrides, equipment_overrides)

    assert result == "exclude_command"


def test_resolve_publication_override_ignore_les_entrees_sans_publication_override():
    """Une entrée `overrides`/`equipment_overrides` sans le champ (ex. Story 16.2 seule,
    juste `ha_entity_type`) ne doit jamais être interprétée comme un override de publication."""
    overrides = {"553:5138": {"ha_entity_type": "switch"}}
    equipment_overrides = {"553": {}}

    assert resolve_publication_override(553, 5138, overrides, equipment_overrides) is None


# --------------------------------------------------------------------------- #
# Task 3/4 — decide_publication() étendu : exclusion (AC1) / forçage (AC2)     #
# --------------------------------------------------------------------------- #

def test_decide_publication_exclude_eqlogic_bloque_une_publication_par_ailleurs_valide():
    mapping = _make_mapping(confidence="sure")

    result = decide_publication(mapping, publication_override="exclude_eqlogic")

    assert result.should_publish is False
    assert result.reason == "publication_excluded_eqlogic"
    assert result.reason_details["publication_override_applied"] is True
    assert result.reason_details["override_source"] == "user"


def test_decide_publication_exclude_command_bloque_une_publication_par_ailleurs_valide():
    mapping = _make_mapping(confidence="sure")

    result = decide_publication(mapping, publication_override="exclude_command")

    assert result.should_publish is False
    assert result.reason == "publication_excluded_command"


def test_decide_publication_force_publish_debloque_un_probable_sous_sure_only():
    """AC2 : projection valide + confidence_policy=sure_only bloquerait un `probable` —
    le force_publish le débloque, sans jamais réécrire le reason nominal en `probable`."""
    mapping = _make_mapping(confidence="probable")

    result = decide_publication(
        mapping, confidence_policy="sure_only", publication_override="force_publish"
    )

    assert result.should_publish is True
    assert result.reason == "publication_forced"
    assert result.reason_details["underlying_confidence"] == "probable"
    assert result.reason_details["publication_override_applied"] is True
    assert result.reason_details["override_source"] == "user"


def test_decide_publication_absence_override_comportement_identique_existant():
    """Non-régression : `publication_override=None` (défaut) = comportement natif inchangé."""
    mapping = _make_mapping(confidence="sure")

    result = decide_publication(mapping)

    assert result.should_publish is True
    assert result.reason == "sure"
    assert result.reason_details is None


# --------------------------------------------------------------------------- #
# Task 5 — Garde-fou I2 : aucun bypass de la validation HA                     #
# --------------------------------------------------------------------------- #

def test_i2_force_publish_ne_bypass_jamais_une_projection_invalide():
    """Garde-fou non négociable (Task 5) : `is_valid=False` reste `should_publish=False`
    même avec un override "forcer publication"."""
    mapping = _make_mapping(
        confidence="sure", projection_validity=_invalid_pv("ha_missing_state_topic")
    )

    result = decide_publication(mapping, publication_override="force_publish")

    assert result.should_publish is False
    assert result.reason == "ha_missing_state_topic"  # cause amont (étape 3) préservée, I4


def test_i2_exclude_eqlogic_evalue_apres_projection_invalide_i4():
    """I4 : une projection invalide (étape 3) reste la cause retenue — l'exclusion utilisateur
    (étape 4) ne doit jamais masquer un échec amont."""
    mapping = _make_mapping(
        confidence="sure", projection_validity=_invalid_pv("ha_component_unknown")
    )

    result = decide_publication(mapping, publication_override="exclude_eqlogic")

    assert result.should_publish is False
    assert result.reason == "ha_component_unknown"


def test_force_publish_ne_bypass_pas_le_niveau_3_product_scope():
    """Un force_publish ne débloque QUE le niveau 4b (confidence_policy) — jamais le
    niveau 3 (PRODUCT_SCOPE)."""
    mapping = _make_mapping(confidence="sure")

    result = decide_publication(
        mapping, product_scope=[], publication_override="force_publish"
    )

    assert result.should_publish is False
    assert result.reason == "ha_component_not_in_product_scope"


# --------------------------------------------------------------------------- #
# Wiring — http_server._resolve_publication_override_for_mapping (Task 3)     #
# --------------------------------------------------------------------------- #

def test_http_server_resolve_publication_override_for_mapping_equipement():
    mapping = _make_mapping(jeedom_eq_id=553)
    equipment_overrides_cache = {"553": {"publication_override": "exclude"}}

    result = http_server._resolve_publication_override_for_mapping(
        mapping, {}, equipment_overrides_cache
    )

    assert result == "exclude_eqlogic"


def test_http_server_resolve_publication_override_for_mapping_sans_commande_ne_plante_pas():
    """Une mapping sans `commands` ni `cmd_id` dans `reason_details` doit quand même
    résoudre les règles équipement (sentinel cmd_id, cf. docstring du helper)."""
    mapping = _make_mapping(jeedom_eq_id=553)
    assert mapping.commands in (None, {})

    result = http_server._resolve_publication_override_for_mapping(
        mapping, {}, {"553": {"publication_override": "force_publish"}}
    )

    assert result == "force_publish"


def test_http_server_resolve_publication_override_for_mapping_retourne_none_si_absent():
    mapping = _make_mapping(jeedom_eq_id=553)

    result = http_server._resolve_publication_override_for_mapping(mapping, {}, {})

    assert result is None
