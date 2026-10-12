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
            return self._upsert(self.eqs, p)
        if method == c.CMD_BY_EQ:
            return [x for x in self.cmds if x["eqLogic_id"] == p["eqLogic_id"]]
        if method == c.CMD_SAVE:
            return self._upsert(self.cmds, p)
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
    assert len(server.cmds) == inv["summary"]["cmds"]
    assert all(e["eqType_name"] == "virtual" and e["object_id"] for e in server.eqs)
    assert sum(1 for e in server.eqs if e["configuration"]["jeedom2ha_excluded"] == 1) == 1
    assert inv["summary"]["by_status"] == {"created": 71}


def test_rerun_is_idempotent(server):
    pd.populate(adapter_for(server), dry_run=False)
    before = (len(server.rooms), len(server.eqs), len(server.cmds), len(server.scenarios))
    server.calls.clear()
    inv = pd.populate(adapter_for(server), dry_run=False)
    assert (len(server.rooms), len(server.eqs), len(server.cmds), len(server.scenarios)) == before
    assert server.writes == []
    assert set(inv["summary"]["by_status"]) == {"exists"}


def test_rerun_repairs_drift_without_duplicates(server):
    pd.populate(adapter_for(server), dry_run=False)
    cmd = next(c for c in server.cmds if c["generic_type"] == "POWER")
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
    assert first["summary"]["by_status"] == {"created": 71}
    assert pd.main(["--env-file", str(env)]) == 0
    assert json.loads(capsys.readouterr().out)["summary"]["by_status"] == {"exists": 71}
    assert len(server.eqs) == 16
