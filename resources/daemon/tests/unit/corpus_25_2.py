"""Story 25.2 — corpus fictif partagé (instantané, route agrégée, charge).

Identifiants et noms fictifs uniquement (CC-48). Chaque équipement couvre une forme
d'état distincte : publié, override en attente, sans commande, désactivé, exclu, aucune
commande couvrable, multi-entités, sans pièce, dépublication différée.
"""

from models.mapping import PublicationDecision
from models.topology import JeedomCmd, JeedomEqLogic, JeedomObject, TopologySnapshot
from mapping.overrides import save_override, save_equipment_override

SECRET = "test_secret_25_2"

PUBLISHED_EQ = 101
PENDING_EQ = 102
EMPTY_EQ = 103
DISABLED_EQ = 104
EXCLUDED_EQ = 105
UNCOVERED_EQ = 106
MULTI_ENTITY_EQ = 107
NO_ROOM_EQ = 108
DEFERRED_UNPUBLISH_EQ = 109
CMD_OVERRIDE_EQ = 110


def _cmd(eq_id, n, name, generic_type, type_="info", sub_type="binary"):
    return JeedomCmd(id=eq_id * 10 + n, name=name, generic_type=generic_type, type=type_, sub_type=sub_type)


def _light_cmds(eq_id):
    return [
        _cmd(eq_id, 1, "On", "LIGHT_ON", "action", "other"),
        _cmd(eq_id, 2, "Off", "LIGHT_OFF", "action", "other"),
        _cmd(eq_id, 3, "Etat", "LIGHT_STATE"),
    ]


def build_snapshot():
    eqs = [
        JeedomEqLogic(id=PUBLISHED_EQ, name="Eq A", object_id=1, eq_type_name="light", cmds=_light_cmds(PUBLISHED_EQ)),
        JeedomEqLogic(id=PENDING_EQ, name="Eq B", object_id=1, eq_type_name="light", cmds=_light_cmds(PENDING_EQ)),
        JeedomEqLogic(id=EMPTY_EQ, name="Eq C", object_id=2, eq_type_name="virtual", cmds=[]),
        JeedomEqLogic(id=DISABLED_EQ, name="Eq D", object_id=2, is_enable=False, eq_type_name="light",
                      cmds=_light_cmds(DISABLED_EQ)),
        JeedomEqLogic(id=EXCLUDED_EQ, name="Eq E", object_id=2, is_excluded=True, exclusion_source="eqlogic",
                      eq_type_name="light", cmds=_light_cmds(EXCLUDED_EQ)),
        JeedomEqLogic(id=UNCOVERED_EQ, name="Eq F", object_id=3, eq_type_name="virtual", cmds=[
            _cmd(UNCOVERED_EQ, 1, "Brut", None, "info", "string"),
            _cmd(UNCOVERED_EQ, 2, "Inconnu", "NO_SUCH_GENERIC_TYPE", "info", "numeric"),
        ]),
        JeedomEqLogic(id=MULTI_ENTITY_EQ, name="Eq G", object_id=3, eq_type_name="prise", cmds=[
            _cmd(MULTI_ENTITY_EQ, 1, "On", "ENERGY_ON", "action", "other"),
            _cmd(MULTI_ENTITY_EQ, 2, "Off", "ENERGY_OFF", "action", "other"),
            _cmd(MULTI_ENTITY_EQ, 3, "Etat", "ENERGY_STATE"),
            JeedomCmd(id=MULTI_ENTITY_EQ * 10 + 4, name="Conso W", type="info", sub_type="numeric",
                      unit="W", current_value=42),
        ]),
        JeedomEqLogic(id=NO_ROOM_EQ, name="Eq H", object_id=None, eq_type_name="light", cmds=_light_cmds(NO_ROOM_EQ)),
        JeedomEqLogic(id=DEFERRED_UNPUBLISH_EQ, name="Eq I", object_id=3, eq_type_name="light",
                      cmds=_light_cmds(DEFERRED_UNPUBLISH_EQ)),
        JeedomEqLogic(id=CMD_OVERRIDE_EQ, name="Eq J", object_id=3, eq_type_name="light",
                      cmds=_light_cmds(CMD_OVERRIDE_EQ)),
    ]
    return TopologySnapshot(
        timestamp="2026-10-18T12:00:00Z",
        objects={1: JeedomObject(id=1, name="Pièce 1"), 2: JeedomObject(id=2, name="Pièce 2"),
                 3: JeedomObject(id=3, name="Pièce 3")},
        eq_logics={eq.id: eq for eq in eqs},
    )


def apply_corpus(app, data_dir):
    """Pose topologie, publications synchronisées et overrides persistés sur `app` / `data_dir`."""
    app["topology"] = build_snapshot()
    app["data_dir"] = str(data_dir)
    app["publications"] = {
        PUBLISHED_EQ: PublicationDecision(should_publish=True, reason="sure"),
        PENDING_EQ: PublicationDecision(should_publish=True, reason="sure"),
        DEFERRED_UNPUBLISH_EQ: PublicationDecision(should_publish=True, reason="sure"),
        CMD_OVERRIDE_EQ: PublicationDecision(should_publish=True, reason="sure"),
    }
    app["pending_discovery_unpublish"] = {DEFERRED_UNPUBLISH_EQ: "light"}
    save_equipment_override(PENDING_EQ, {"publication_override": "exclude"}, str(data_dir))
    save_override(CMD_OVERRIDE_EQ, CMD_OVERRIDE_EQ * 10 + 3, {"ha_entity_type": "switch"}, str(data_dir))
    return app


ALL_EQ_IDS = [
    PUBLISHED_EQ, PENDING_EQ, EMPTY_EQ, DISABLED_EQ, EXCLUDED_EQ, UNCOVERED_EQ,
    MULTI_ENTITY_EQ, NO_ROOM_EQ, DEFERRED_UNPUBLISH_EQ, CMD_OVERRIDE_EQ,
]
