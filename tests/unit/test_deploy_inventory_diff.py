"""
test_deploy_inventory_diff.py — Point 8 : preuve unitaire, SANS SSH ni box
réelle, du diff d'inventaire MQTT affiché par deploy-to-box.sh à la fin du
déploiement.

scripts/deploy-inventory-diff.sh est pure bash : elle ne fait aucun
ssh/mosquitto_sub elle-même (ce fetch reste dans deploy-to-box.sh), donc
elle est testable ici uniquement avec des chaînes avant/après en argument.

Rejouer :
    pytest tests/unit/test_deploy_inventory_diff.py -v
"""
import subprocess
from pathlib import Path

LIB = Path(__file__).resolve().parents[2] / "scripts" / "deploy-inventory-diff.sh"


def _diff(before: str, after: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", f"set -euo pipefail; source '{LIB}'; jeedom2ha_diff_topic_lists \"$1\" \"$2\"", "--", before, after],
        capture_output=True,
        text=True,
    )


def test_reports_counts_and_no_changes_when_lists_are_identical():
    topics = "jeedom2ha_pool/switch/pump\njeedom2ha_pool/sensor/temp"

    result = _diff(topics, topics)

    assert result.returncode == 0, result.stderr
    assert "Entités avant : 2 | Entités après : 2" in result.stdout
    assert "Topics ajoutés : aucun" in result.stdout
    assert "Topics retirés : aucun" in result.stdout


def test_reports_added_topics_only():
    before = "jeedom2ha_pool/switch/pump"
    after = "jeedom2ha_pool/switch/pump\njeedom2ha_pool/sensor/temp"

    result = _diff(before, after)

    assert result.returncode == 0, result.stderr
    assert "Entités avant : 1 | Entités après : 2" in result.stdout
    assert "Topics ajoutés :" in result.stdout
    assert "+ jeedom2ha_pool/sensor/temp" in result.stdout
    assert "Topics retirés : aucun" in result.stdout


def test_reports_removed_topics_only():
    before = "jeedom2ha_pool/switch/pump\njeedom2ha_pool/sensor/temp"
    after = "jeedom2ha_pool/switch/pump"

    result = _diff(before, after)

    assert result.returncode == 0, result.stderr
    assert "Entités avant : 2 | Entités après : 1" in result.stdout
    assert "Topics ajoutés : aucun" in result.stdout
    assert "Topics retirés :" in result.stdout
    assert "- jeedom2ha_pool/sensor/temp" in result.stdout


def test_reports_both_added_and_removed_topics():
    before = "jeedom2ha_pool/switch/pump\njeedom2ha_pool/sensor/old"
    after = "jeedom2ha_pool/switch/pump\njeedom2ha_pool/sensor/new"

    result = _diff(before, after)

    assert result.returncode == 0, result.stderr
    assert "Entités avant : 2 | Entités après : 2" in result.stdout
    assert "+ jeedom2ha_pool/sensor/new" in result.stdout
    assert "- jeedom2ha_pool/sensor/old" in result.stdout


def test_handles_empty_before_content():
    result = _diff("", "jeedom2ha_pool/switch/pump")

    assert result.returncode == 0, result.stderr
    assert "Entités avant : 0 | Entités après : 1" in result.stdout
    assert "+ jeedom2ha_pool/switch/pump" in result.stdout


def test_handles_empty_after_content():
    result = _diff("jeedom2ha_pool/switch/pump", "")

    assert result.returncode == 0, result.stderr
    assert "Entités avant : 1 | Entités après : 0" in result.stdout
    assert "- jeedom2ha_pool/switch/pump" in result.stdout


def test_handles_both_empty():
    result = _diff("", "")

    assert result.returncode == 0, result.stderr
    assert "Entités avant : 0 | Entités après : 0" in result.stdout
    assert "Topics ajoutés : aucun" in result.stdout
    assert "Topics retirés : aucun" in result.stdout
