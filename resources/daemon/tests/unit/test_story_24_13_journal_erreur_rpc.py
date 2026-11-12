"""Story 24.13 — journaliser le motif d'échec d'un ordre renvoyé par Jeedom.

Constat : quand Jeedom répondait en erreur à ``cmd::execCmd`` (par exemple un plugin
tiers qui lève une exception), le démon ne journalisait que
``[SYNC-CMD] ... reason_code=jeedom_rpc_error action=execute_command`` : la cause
n'apparaissait nulle part.

Ici, le vrai ``_execute_exec_cmd`` / ``_execute_scenario_start`` est exercé contre une
session HTTP factice ; la ligne WARNING existante gagne ``error_detail=...`` (code et
message JSON-RPC, statut HTTP, ou type d'exception), masqué, sur une ligne, tronqué.
``reason_code`` est inchangé. Données fictives (CC-48).
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock

import aiohttp
import pytest

from mapping.button import ScenarioButtonMapper
from models.mapping import MappingResult, PublicationDecision, SwitchCapabilities
from models.topology import JeedomCmd, JeedomScenario
from sync.command import RPC_ERROR_DETAIL_MAX_LEN, CommandSynchronizer

EQ_ID = 9130
SCENARIO_ID = 9131
CORE_APIKEY = "fictive-core-apikey-0123456789"
TOPIC = f"jeedom2ha/{EQ_ID}/set"
SCENARIO_TOPIC = f"jeedom2ha/scenario_{SCENARIO_ID}/cmd"


# --------------------------------------------------------------------------- doubles


class _FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def json(self, content_type=None):  # noqa: ARG002
        if isinstance(self._payload, BaseException):
            raise self._payload
        return self._payload


class _FakeSession:
    """Rend, dans l'ordre, une réponse (status, payload) ou lève une exception."""

    closed = False

    def __init__(self, *outcomes):
        self._outcomes = list(outcomes)
        self.requests = []

    def post(self, endpoint, json):
        self.requests.append((endpoint, json))
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        status, payload = outcome
        return _FakeResponse(status, payload)

    async def close(self):
        self.closed = True


def _switch_mapping() -> MappingResult:
    commands = {
        "ENERGY_ON": JeedomCmd(id=91301, name="On", generic_type="ENERGY_ON", type="action", sub_type="other"),
        "ENERGY_OFF": JeedomCmd(id=91302, name="Off", generic_type="ENERGY_OFF", type="action", sub_type="other"),
    }
    return MappingResult(
        ha_entity_type="switch",
        confidence="sure",
        reason_code="switch_on_off_only",
        jeedom_eq_id=EQ_ID,
        ha_unique_id=f"jeedom2ha_eq_{EQ_ID}",
        ha_name=f"Switch {EQ_ID}",
        commands=commands,
        capabilities=SwitchCapabilities(
            has_on_off=True,
            has_state=False,
            on_off_confidence="sure",
            device_class="outlet",
        ),
    )


def _sync(*outcomes, endpoint="http://jeedom.invalid/core/api/jeeApi.php", apikey=CORE_APIKEY):
    mapping = _switch_mapping()
    decision = PublicationDecision(
        should_publish=True,
        reason="sure",
        mapping_result=mapping,
        state_topic=f"jeedom2ha/{EQ_ID}/state",
        active_or_alive=True,
    )
    sc_mapping = ScenarioButtonMapper().map(JeedomScenario(id=SCENARIO_ID, name="Scénario fictif"))
    sc_decision = PublicationDecision(
        should_publish=True,
        reason="scenario_button",
        mapping_result=sc_mapping,
        active_or_alive=True,
    )
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message.return_value = True
    app = {
        "mappings": {mapping.ha_unique_id: mapping},
        "publications": {mapping.ha_unique_id: decision},
        "scenario_publications": {SCENARIO_ID: sc_decision},
        "state_synchronizer": None,
    }
    sync = CommandSynchronizer(
        app=app,
        mqtt_bridge=bridge,
        jeedom_api_endpoint=endpoint,
        jeedom_core_apikey=apikey,
    )
    session = _FakeSession(*outcomes)
    sync._session = session
    return sync, session


def _run(sync, topic=TOPIC, payload="ON"):
    return asyncio.run(sync.handle_command_message(topic, payload))


def _sync_cmd_lines(caplog, action="execute_command"):
    return [
        r.getMessage() for r in caplog.records
        if r.getMessage().startswith("[SYNC-CMD]") and f"action={action}" in r.getMessage()
    ]


def _failure_line(caplog, action="execute_command"):
    lines = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and f"action={action}" in r.getMessage()
    ]
    assert len(lines) == 1, [r.getMessage() for r in caplog.records]
    return lines[0].getMessage()


def _detail(line: str) -> str:
    assert " error_detail=" in line, line
    return line.split(" error_detail=", 1)[1]


def _rpc_error(code, message):
    return 200, {"jsonrpc": "2.0", "id": "x", "error": {"code": code, "message": message}}


def _assert_no_secret(caplog):
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert CORE_APIKEY not in text
    # jamais le corps de la requête
    assert "cmd::execCmd" not in text
    assert "params" not in text


# --------------------------------------------------------------------------- cmd::execCmd


def test_erreur_json_rpc_avec_message(caplog):
    sync, session = _sync(_rpc_error(-32000, "Authentification expirée côté plugin"))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False

    line = _failure_line(caplog)
    assert line.startswith(
        f"[SYNC-CMD] eq_id={EQ_ID} topic={TOPIC} reason_code=jeedom_rpc_error action=execute_command "
    )
    assert _detail(line) == "code=-32000 message=Authentification expirée côté plugin"
    assert len(session.requests) == 1
    _assert_no_secret(caplog)


def test_erreur_json_rpc_sans_code_ni_message_reste_journalisee(caplog):
    sync, _ = _sync((200, {"error": "texte brut"}))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False
    assert _detail(_failure_line(caplog)) == "message=texte brut"


@pytest.mark.parametrize(
    "message, fragments_interdits",
    [
        ("échec apikey=SECRET-A1 sur l'appel", ["SECRET-A1"]),
        ("refus token=SECRET-T2&next=1", ["SECRET-T2"]),
        ("login password='mot de passe' invalide", ["mot de passe", "passe'"]),
        ('{"apikey": "SECRET-J3", "token":"SECRET-J4"}', ["SECRET-J3", "SECRET-J4"]),
        (f"clé reçue {CORE_APIKEY} refusée", [CORE_APIKEY]),
    ],
)
def test_message_avec_secret_masque(caplog, message, fragments_interdits):
    sync, _ = _sync(_rpc_error(-32001, message))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False

    detail = _detail(_failure_line(caplog))
    assert "***" in detail
    for fragment in fragments_interdits:
        assert fragment not in detail
    _assert_no_secret(caplog)


def test_motifs_masques_par_nom():
    sync, _ = _sync()
    sync._set_exec_error_detail("apikey=a token=b password=c Access_Token: d")
    assert sync._last_exec_error_detail == "apikey=*** token=*** password=*** Access_Token=***"


@pytest.mark.parametrize(
    "message",
    [
        '{"password": "prefix\\"SECRET_SUFFIX"} fin',
        '{"token": "a\\\\b\\"SECRET_SUFFIX"} fin',
        "token='x\\'SECRET_SUFFIX' fin",
    ],
)
def test_secret_avec_guillemet_echappe_entierement_masque(message):
    # Revue Codex #374 : une valeur entre guillemets contenant un guillemet échappé
    # ne doit laisser aucune partie du secret dans le journal.
    sync, _ = _sync()
    sync._set_exec_error_detail(message)
    assert "SECRET_SUFFIX" not in sync._last_exec_error_detail
    assert sync._last_exec_error_detail.endswith(" fin")


def test_http_500(caplog):
    sync, _ = _sync((500, {"error": {"message": "corps ignoré"}}))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False

    line = _failure_line(caplog)
    assert "reason_code=jeedom_rpc_error" in line
    assert _detail(line) == "http_status=500"
    assert "corps ignoré" not in line


def test_exception_aiohttp(caplog):
    sync, _ = _sync(aiohttp.ClientConnectionError(f"connexion refusée apikey={CORE_APIKEY}"))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False

    line = _failure_line(caplog)
    assert "reason_code=jeedom_rpc_error" in line
    assert _detail(line) == "exception=ClientConnectionError"
    assert "Traceback" not in caplog.text
    _assert_no_secret(caplog)


def test_reponse_illisible_donne_le_type_d_exception(caplog):
    sync, _ = _sync((200, ValueError("pas du JSON")))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False
    line = _failure_line(caplog)
    assert "reason_code=jeedom_rpc_error" in line
    assert _detail(line) == "exception=ValueError"


def test_timeout(caplog):
    sync, _ = _sync(asyncio.TimeoutError())
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False

    line = _failure_line(caplog)
    assert "reason_code=jeedom_rpc_timeout" in line
    assert _detail(line) == f"exception={asyncio.TimeoutError.__name__}"


def test_message_long_tronque(caplog):
    long_message = "début " + "x" * 600 + " FIN"
    sync, _ = _sync(_rpc_error(-32000, long_message))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False

    detail = _detail(_failure_line(caplog))
    assert len(detail) <= RPC_ERROR_DETAIL_MAX_LEN
    assert detail.startswith("code=-32000 message=début xxx")
    assert detail.endswith("...")
    assert "FIN" not in detail


def test_message_multiligne_sur_une_ligne(caplog):
    sync, _ = _sync(_rpc_error(-32000, "ligne 1\nligne 2\r\n\tligne 3"))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False

    line = _failure_line(caplog)
    assert "\n" not in line and "\r" not in line and "\t" not in line
    assert _detail(line) == "code=-32000 message=ligne 1 ligne 2 ligne 3"


def test_api_non_configuree(caplog):
    sync, session = _sync(apikey="")
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False
    line = _failure_line(caplog)
    assert "reason_code=jeedom_rpc_error" in line
    assert _detail(line) == "jeedom_api_not_configured"
    assert session.requests == []


def test_succes_sans_error_detail(caplog):
    sync, _ = _sync((200, {"jsonrpc": "2.0", "id": "x", "result": True}))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is True

    lines = _sync_cmd_lines(caplog)
    assert any("reason_code=command_executed" in line for line in lines)
    assert all("error_detail" not in r.getMessage() for r in caplog.records)
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


def test_succes_apres_echec_ne_reprend_pas_l_ancien_detail(caplog):
    sync, _ = _sync(_rpc_error(-32000, "première panne"), (200, {"result": True}))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False
        caplog.clear()
        assert _run(sync, payload="OFF") is True

    assert sync._last_exec_error_detail == ""
    assert all("error_detail" not in r.getMessage() for r in caplog.records)


def test_les_autres_lignes_ne_portent_pas_le_detail(caplog):
    """Un rejet ultérieur sans appel Jeedom ne reprend pas le détail d'une panne passée."""
    sync, _ = _sync(_rpc_error(-32000, "panne"))
    with caplog.at_level(logging.INFO):
        assert _run(sync) is False
        caplog.clear()
        assert _run(sync, payload="PEUT-ETRE") is False

    assert "reason_code=invalid_command_payload" in caplog.text
    assert "error_detail" not in caplog.text


# --------------------------------------------------------------------------- scenario::changeState


def test_scenario_erreur_json_rpc(caplog):
    sync, session = _sync(_rpc_error(-32000, "Scénario introuvable"))
    with caplog.at_level(logging.INFO):
        assert _run(sync, topic=SCENARIO_TOPIC, payload="PRESS") is False

    line = _failure_line(caplog, action="execute_scenario_command")
    assert line.startswith(
        f"[SYNC-CMD] eq_id=scenario_{SCENARIO_ID} topic={SCENARIO_TOPIC} "
        "reason_code=jeedom_rpc_error action=execute_scenario_command "
    )
    assert _detail(line) == "code=-32000 message=Scénario introuvable"
    assert session.requests[0][1]["method"] == "scenario::changeState"
    _assert_no_secret(caplog)


def test_scenario_timeout_et_http(caplog):
    sync, _ = _sync(asyncio.TimeoutError(), (503, None))
    with caplog.at_level(logging.INFO):
        assert _run(sync, topic=SCENARIO_TOPIC, payload="PRESS") is False
        line_timeout = _failure_line(caplog, action="execute_scenario_command")
        caplog.clear()
        assert _run(sync, topic=SCENARIO_TOPIC, payload="PRESS") is False
        line_http = _failure_line(caplog, action="execute_scenario_command")

    assert "reason_code=jeedom_rpc_timeout" in line_timeout
    assert _detail(line_timeout) == f"exception={asyncio.TimeoutError.__name__}"
    assert "reason_code=jeedom_rpc_error" in line_http
    assert _detail(line_http) == "http_status=503"


def test_scenario_succes_sans_error_detail(caplog):
    sync, _ = _sync((200, {"result": True}))
    with caplog.at_level(logging.INFO):
        assert _run(sync, topic=SCENARIO_TOPIC, payload="PRESS") is True
    assert "reason_code=scenario_started" in caplog.text
    assert "error_detail" not in caplog.text
