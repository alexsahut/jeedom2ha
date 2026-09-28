"""VM wrapper: execute the real shell flow with SSH/MQTT/Python stand-ins."""
import json
import os
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("mqtt_rc,python_rc", [(27, 0), (5, 0), (27, 2)])
def test_wrapper_secret_transport_and_cleanup(tmp_path, mqtt_rc, python_rc):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    mock = bin_dir / "mock"
    mock.write_text(r'''#!/usr/bin/python3
import json, os, pathlib, stat, subprocess, sys
role = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
root = pathlib.Path(os.environ["PROBE_TEST_ROOT"])
with (root / "argv.jsonl").open("a") as f:
    f.write(json.dumps([role, args]) + "\n")
if role == "ssh":
    if "-O" in args:
        (root / "closed").touch()
        sys.exit(0)
    if "-fN" in args:
        assert "127.0.0.1:15508:127.0.0.1:55080" in args
        (root / "work_dir").write_text(str(pathlib.Path(args[args.index("-S") + 1]).parent))
        sys.exit(0)
    source = sys.stdin.read()
    if '"local_secret"' in source:
        print(json.dumps({"local_secret": "test-local-secret", "daemon_port": "55080"}))
    elif '"mqtt::password"' in source:
        print(json.dumps({"host": "127.0.0.1", "port": 1883,
                          "user": "test mqtt user", "pass": "test ' mqtt password \\\""}))
    else:
        assert "mosquitto_sub" in source
        assert "/action/" not in source
        sys.exit(subprocess.run(["bash", "-s"], input=source, text=True).returncode)
elif role == "mosquitto_sub":
    assert not set(args) & {"-u", "-P", "-o"}
    directory = pathlib.Path(os.environ["XDG_CONFIG_HOME"])
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    config = directory / "mosquitto_sub"
    assert stat.S_IMODE(config.stat().st_mode) == 0o600
    assert config.read_text() == "-u test mqtt user\n-P test ' mqtt password \\\"\n"
    (root / "auth_dir").write_text(str(directory))
    # Story 19.2 — second read-only subscription (retained state topics),
    # distinguished from the discovery one by its -t filter.
    if args[args.index("-t") + 1] == "jeedom2ha/+/+/state":
        print("jeedom2ha/1/1/state")
    else:
        print("homeassistant/light/jeedom2ha_1/config")
    sys.exit(int(os.environ["PROBE_MQTT_RC"]))
elif role == "probe-python":
    assert os.environ["JEEDOM2HA_LOCAL_SECRET"] == "test-local-secret"
    assert "JEEDOM2HA_LOCAL_SECRET_FILE" not in os.environ
    inventory = pathlib.Path(args[args.index("--mqtt-inventory-file") + 1])
    assert stat.S_IMODE(inventory.stat().st_mode) == 0o600
    assert inventory.read_text() == "homeassistant/light/jeedom2ha_1/config\n"
    state_inventory = pathlib.Path(args[args.index("--mqtt-state-inventory-file") + 1])
    assert stat.S_IMODE(state_inventory.stat().st_mode) == 0o600
    assert state_inventory.read_text() == "jeedom2ha/1/1/state\n"
    (root / "python_called").touch()
    sys.exit(int(os.environ["PROBE_PYTHON_RC"]))
''')
    mock.chmod(0o755)
    for name in ("ssh", "mosquitto_sub", "probe-python"):
        (bin_dir / name).symlink_to(mock)
    result = subprocess.run(
        [str(ROOT / "scripts/parity-snapshot.sh"), "capture"],
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}",
             "PROBE_TEST_ROOT": str(tmp_path), "PROBE_MQTT_RC": str(mqtt_rc),
             "PROBE_PYTHON_RC": str(python_rc),
             "JEEDOM2HA_PARITY_PYTHON": str(bin_dir / "probe-python"),
             "JEEDOM2HA_LOCAL_SECRET_FILE": "must-be-cleared"},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == (mqtt_rc if mqtt_rc != 27 else python_rc), result.stderr
    assert (tmp_path / "closed").exists()
    assert not Path((tmp_path / "work_dir").read_text()).exists()
    assert not Path((tmp_path / "auth_dir").read_text()).exists()
    assert (tmp_path / "python_called").exists() == (mqtt_rc == 27)
    exposed = (tmp_path / "argv.jsonl").read_text() + result.stdout + result.stderr
    for secret in ("test-local-secret", "test mqtt user", "mqtt password"):
        assert secret not in exposed
    calls = [json.loads(line) for line in (tmp_path / "argv.jsonl").read_text().splitlines()]
    # Story 19.2 adds a second (state-topic) subscription after the discovery
    # one; a failing first subscription (mqtt_rc=5) aborts before it runs.
    expected_mosquitto_calls = 2 if mqtt_rc == 27 else 1
    assert [role for role, _ in calls].count("mosquitto_sub") == expected_mosquitto_calls
