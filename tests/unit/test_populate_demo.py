"""Story 23.1 — tests de scripts/demo/populate_demo.py avec un faux serveur JSON-RPC Jeedom."""
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "demo" / "populate_demo.py"
_spec = importlib.util.spec_from_file_location("populate_demo", SCRIPT)
pd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pd)

API_KEY = "test-key-not-a-secret"


class FakeJeedom:
    """État en mémoire + dispatch des méthodes du contrat présumé (JsonRpcContract)."""

    def __init__(self, preexisting_eqs=()):
        self.rooms, self.eqs, self.cmds, self.scenarios = [], list(preexisting_eqs), [], []
        self.next_id = 100
        self.calls = []
        self.unsupported = set()

    def _id(self):
        self.next_id += 1
        return self.next_id

    def _upsert(self, table, params):
        params = {k: v for k, v in params.items() if k != "apikey"}
        if "id" in params:
            for row in table:
                if row["id"] == params["id"]:
                    row.update(params)
                    return row
        row = dict(params, id=self._id())
        table.append(row)
        return row

    def dispatch(self, method, p):
        self.calls.append(method)
        if method in self.unsupported:
            raise KeyError(method)
        c = pd.JsonRpcContract
        if method == c.ROOM_ALL:
            return self.rooms
        if method == c.ROOM_SAVE:
            return self._upsert(self.rooms, p)
        if method == c.EQ_ALL:
            return self.eqs
        if method == c.EQ_SAVE:
            if p.get("eqType_name") != "virtual":
                raise KeyError("eqType_name virtual required")
            params = {k: v for k, v in p.items() if k not in ("apikey", "cmd")}
            eq = self._upsert(self.eqs, params)
            requested = p.get("cmd", [])
            names = set()
            for command in requested:
                if "eqLogic_id" in command or any(value is None for value in command.values()):
                    raise KeyError("cmd must not override eqLogic_id or contain null")
                if command.get("type") == "action" and not command.get("configuration", {}).get("infoName"):
                    raise KeyError("infoName required for virtual action")
                cmd = dict(command, eqLogic_id=eq["id"])
                names.add(cmd["name"])
                self._upsert(self.cmds, cmd)
            # virtual::postSave creates Rafraichir; eqLogic::save must retain it even
            # though the client need not include it in every complete command list.
            if not any(cmd["eqLogic_id"] == eq["id"] and cmd.get("logicalId") == "refresh"
                       for cmd in self.cmds):
                self.cmds.append({"id": self._id(), "eqLogic_id": eq["id"], "name": "Rafraichir",
                                  "logicalId": "refresh", "type": "action", "subType": "other"})
            self.cmds[:] = [cmd for cmd in self.cmds
                            if cmd["eqLogic_id"] != eq["id"] or cmd.get("logicalId") == "refresh"
                            or cmd.get("name") in names]
            return eq
        if method == c.CMD_BY_EQ:
            return [x for x in self.cmds if x["eqLogic_id"] == p["eqLogic_id"]]
        if method == c.SCENARIO_ALL:
            return self.scenarios
        if method == c.SCENARIO_SAVE:
            return self._upsert(self.scenarios, p)
        raise KeyError(method)

    @property
    def writes(self):
        return [m for m in self.calls if m.endswith("::save")]


@pytest.fixture
def server():
    state = FakeJeedom()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if req["params"].get("apikey") != API_KEY:
                body = {"jsonrpc": "2.0", "id": req["id"], "error": {"code": -32001, "message": "denied"}}
            else:
                try:
                    body = {"jsonrpc": "2.0", "id": req["id"],
                            "result": state.dispatch(req["method"], req["params"])}
                except KeyError:
                    body = {"jsonrpc": "2.0", "id": req["id"],
                            "error": {"code": -32601, "message": "Method not found"}}
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    state.url = "http://127.0.0.1:%d/core/api/jeeApi.php" % httpd.server_address[1]
    yield state
    httpd.shutdown()
    httpd.server_close()


def adapter_for(state, key=API_KEY):
    return pd.JeedomAdapter(pd.JeedomRpc(state.url, key))


def test_dataset_covers_acceptance_criteria():
    inv = pd.populate(None, dry_run=True)
    s = inv["summary"]
    assert s["rooms"] == 5 and s["scenarios"] == 3 and 14 <= s["equipments"] <= 17
    types = {c["generic_type"] for e in inv["equipments"] for c in e["cmds"]}
    assert {"LIGHT_STATE", "LIGHT_SLIDER", "FLAP_SLIDER", "POWER", "TEMPERATURE", "HUMIDITY",
            "OPENING", "OPENING_WINDOW", "PRESENCE", "CONSUMPTION"} <= types
    assert s["untyped_equipments"] >= 1 and s["excluded_equipments"] >= 1
    kwh = [c for e in pd.EQUIPMENTS for c in e["cmds"] if c["generic_type"] == "CONSUMPTION"]
    assert kwh and kwh[0]["unit"] == "kWh"


def test_populate_creates_everything(server):
    inv = pd.populate(adapter_for(server), dry_run=False)
    assert len(server.rooms) == 5 and len(server.eqs) == 16 and len(server.scenarios) == 3
    assert len(server.cmds) == inv["summary"]["cmds"] + len(server.eqs)  # Rafraichir
    assert all(e["eqType_name"] == "virtual" and e["object_id"] for e in server.eqs)
    assert sum(1 for e in server.eqs if e["configuration"]["jeedom2ha_excluded"] == 1) == 1
    assert inv["summary"]["by_status"] == {"created": 69}


def test_rerun_is_idempotent(server):
    pd.populate(adapter_for(server), dry_run=False)
    before = (len(server.rooms), len(server.eqs), len(server.cmds), len(server.scenarios))
    ids_before = {cmd["name"] + ":" + str(cmd["eqLogic_id"]): cmd["id"] for cmd in server.cmds}
    server.calls.clear()
    inv = pd.populate(adapter_for(server), dry_run=False)
    assert (len(server.rooms), len(server.eqs), len(server.cmds), len(server.scenarios)) == before
    assert server.writes == []
    assert {cmd["name"] + ":" + str(cmd["eqLogic_id"]): cmd["id"] for cmd in server.cmds} == ids_before
    assert set(inv["summary"]["by_status"]) == {"exists"}


def test_rerun_repairs_drift_without_duplicates(server):
    pd.populate(adapter_for(server), dry_run=False)
    cmd = next(c for c in server.cmds if c.get("generic_type") == "POWER")
    cmd["generic_type"] = ""
    n = len(server.cmds)
    inv = pd.populate(adapter_for(server), dry_run=False)
    assert len(server.cmds) == n and cmd["generic_type"] == "POWER"
    assert inv["summary"]["by_status"].get("updated") == 1


def test_dry_run_with_connection_writes_nothing(server):
    inv = pd.populate(adapter_for(server), dry_run=True)
    assert server.writes == []
    assert inv["dry_run"] is True and inv["connected"] is True
    assert set(inv["summary"]["by_status"]) == {"would_create"}


def test_dry_run_after_populate_reports_exists(server):
    pd.populate(adapter_for(server), dry_run=False)
    server.calls.clear()
    inv = pd.populate(adapter_for(server), dry_run=True)
    assert server.writes == [] and set(inv["summary"]["by_status"]) == {"exists"}


def test_offline_dry_run_makes_no_call():
    inv = pd.populate(None, dry_run=True)
    assert inv["connected"] is False and set(inv["summary"]["by_status"]) == {"planned"}
    assert all(item["write_plan"]["method"] == pd.JsonRpcContract.EQ_SAVE
               and item["write_plan"]["cmd_count"] == len(spec["cmds"])
               for item, spec in zip(inv["equipments"], pd.EQUIPMENTS))


def test_refuses_non_empty_box(server):
    server.eqs.append({"id": 1, "name": "Equipement Maison", "object_id": None})
    with pytest.raises(pd.DemoError, match="pas vierge"):
        pd.populate(adapter_for(server), dry_run=False)
    assert server.writes == []
    pd.populate(adapter_for(server), dry_run=False, allow_non_empty=True)
    assert len(server.eqs) == 17


def test_unsupported_method_gives_clear_error_without_url(server):
    server.unsupported.add(pd.JsonRpcContract.SCENARIO_SAVE)
    with pytest.raises(pd.DemoError) as exc:
        pd.populate(adapter_for(server), dry_run=False)
    assert "scenario::save" in str(exc.value) and "127.0.0.1" not in str(exc.value)


def test_wrong_key_error_does_not_leak_key(server):
    with pytest.raises(pd.DemoError) as exc:
        pd.populate(adapter_for(server, key="wrong-key-xyz"), dry_run=False)
    assert "wrong-key-xyz" not in str(exc.value)


def test_unreachable_server_error_does_not_leak_url():
    rpc = pd.JeedomRpc("http://127.0.0.1:9/core/api/jeeApi.php", API_KEY, timeout=1)
    with pytest.raises(pd.DemoError) as exc:
        rpc.call("eqLogic::all")
    assert "127.0.0.1" not in str(exc.value)


def test_inventory_is_anonymised(server):
    text = json.dumps(pd.populate(adapter_for(server), dry_run=False))
    assert API_KEY not in text and "127.0.0.1" not in text and "http" not in text
    assert '"id"' not in text


def _env(tmp_path, **over):
    values = {"JEEDOM_API_URL": "http://127.0.0.1/x", "JEEDOM_API_KEY": "k",
              "JEEDOM_DEMO_TARGET": "demo"}
    values.update(over)
    p = tmp_path / "demo.env"
    p.write_text("# commentaire\n" + "\n".join("%s=%s" % kv for kv in values.items()
                                               if kv[1] is not None) + "\n")
    p.chmod(0o600)
    return p


def test_env_file_ok(tmp_path):
    assert pd.load_config(str(_env(tmp_path)))["JEEDOM_API_KEY"] == "k"


def test_env_file_inside_repo_refused():
    inside = pd.REPO_ROOT / "tests" / "unit" / "_tmp_demo.env"
    inside.write_text("JEEDOM_API_URL=x\n")
    try:
        with pytest.raises(pd.DemoError, match="HORS du dépôt"):
            pd.load_config(str(inside))
    finally:
        inside.unlink()


def test_env_requires_demo_target_and_keys(tmp_path):
    with pytest.raises(pd.DemoError, match="DEMO_TARGET"):
        pd.load_config(str(_env(tmp_path, JEEDOM_DEMO_TARGET=None)))
    with pytest.raises(pd.DemoError, match="manquante"):
        pd.load_config(str(_env(tmp_path, JEEDOM_API_KEY="")))


def test_cli_has_no_secret_argument():
    flags = {o for a in pd.build_parser()._actions for o in a.option_strings}
    assert not any(k in f for f in flags for k in ("key", "token", "password", "secret", "url"))


def test_main_requires_env_file_without_dry_run(capsys):
    assert pd.main([]) == 1
    assert "--env-file" in capsys.readouterr().err


def test_main_end_to_end(server, tmp_path, capsys):
    env = _env(tmp_path, JEEDOM_API_URL=server.url, JEEDOM_API_KEY=API_KEY)
    assert pd.main(["--env-file", str(env)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["summary"]["by_status"] == {"created": 69}
    assert pd.main(["--env-file", str(env)]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["by_status"] == {"exists": 69}
    assert len(server.eqs) == 16


def test_name_collision_with_foreign_equipment_is_refused_even_with_allow(server):
    room = server.dispatch(pd.JsonRpcContract.ROOM_SAVE, {"name": "Salon"})
    server.eqs.append({"id": 1, "name": "Lumiere Salon", "object_id": room["id"],
                       "eqType_name": "zwave", "configuration": {}})
    with pytest.raises(pd.DemoError, match="aucune réutilisation"):
        pd.populate(adapter_for(server), dry_run=False, allow_non_empty=True)
    assert "eqLogic::save" not in server.writes


def test_created_equipments_carry_owner_marker(server):
    pd.populate(adapter_for(server), dry_run=False)
    assert all(e["configuration"][pd.OWNER_MARKER] for e in server.eqs)


def test_on_off_actions_carry_distinct_values():
    acts = {c["name"]: c["configuration"].get("value")
            for e in pd.EQUIPMENTS for c in e["cmds"] if c["generic_type"] == "LIGHT_ON" or
            c["generic_type"] == "LIGHT_OFF" for c in [c]}
    assert acts == {"On": "1", "Off": "0"}


def test_cover_actions_are_all_linked_to_position():
    actions = [cmd for equipment in pd.EQUIPMENTS for cmd in equipment["cmds"]
               if cmd["generic_type"] in {"FLAP_UP", "FLAP_DOWN"}]
    assert [(cmd["configuration"]["infoName"], cmd["configuration"]["value"]) for cmd in actions] == [
        ("Position", "100"), ("Position", "0"), ("Position", "100"), ("Position", "0")]


def test_equipment_save_is_the_only_command_creation_path(server):
    pd.populate(adapter_for(server), dry_run=False)
    assert "cmd::save" not in server.calls
    saves = [call for call in server.calls if call == pd.JsonRpcContract.EQ_SAVE]
    assert len(saves) == len(pd.EQUIPMENTS)


def test_new_equipment_command_payload_has_no_parent_override_or_null():
    spec = pd.EQUIPMENTS[0]
    payload = pd._eqlogic_payload(spec, room_id=101, existing=None, existing_cmds={})
    assert all("eqLogic_id" not in cmd and all(value is not None for value in cmd.values())
               for cmd in payload["cmd"])


def test_compose_requires_pinned_tag():
    text = (SCRIPT.parent / "docker-compose.ha.yml").read_text()
    assert "${HA_IMAGE_TAG:?" in text and ":-stable" not in text
