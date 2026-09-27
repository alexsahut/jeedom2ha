"""
test_version_reporting.py — Unit tests for the daemon's startup version/SHA
reporting (point 1b): pluginVersion is read dynamically from
plugin_info/info.json instead of a hardcoded constant, and the deployed
commit SHA is read from an optional VERSION file at the plugin root.

All tests use temporary files (tmp_path) — never the repo's real
plugin_info/info.json or VERSION.
"""
import json

from resources.daemon.main import _read_deploy_sha, _read_plugin_version, _UNKNOWN_VERSION


class TestReadPluginVersion:
    """AC: pluginVersion is read from plugin_info/info.json."""

    def test_reads_version_from_valid_info_json(self, tmp_path):
        """Given a valid info.json with a pluginVersion,
        When read,
        Then the exact version string is returned."""
        info_json = tmp_path / "info.json"
        info_json.write_text(json.dumps({"pluginVersion": "0.3.0"}))

        assert _read_plugin_version(str(info_json)) == "0.3.0"

    def test_falls_back_to_unknown_when_file_missing(self, tmp_path):
        """Given no info.json at the given path,
        When read,
        Then the fallback value is returned instead of raising."""
        missing = tmp_path / "does-not-exist.json"

        assert _read_plugin_version(str(missing)) == _UNKNOWN_VERSION

    def test_falls_back_to_unknown_when_json_invalid(self, tmp_path):
        """Given a file that is not valid JSON,
        When read,
        Then the fallback value is returned instead of raising."""
        info_json = tmp_path / "info.json"
        info_json.write_text("{not valid json")

        assert _read_plugin_version(str(info_json)) == _UNKNOWN_VERSION

    def test_falls_back_to_unknown_when_key_absent(self, tmp_path):
        """Given valid JSON without a pluginVersion key,
        When read,
        Then the fallback value is returned."""
        info_json = tmp_path / "info.json"
        info_json.write_text(json.dumps({"id": "jeedom2ha"}))

        assert _read_plugin_version(str(info_json)) == _UNKNOWN_VERSION


class TestReadDeploySha:
    """AC: the deployed commit SHA is read from an optional VERSION file."""

    def test_reads_sha_from_version_file(self, tmp_path):
        """Given a VERSION file written by deploy-to-box.sh (key=value lines),
        When read,
        Then the sha= value is returned."""
        version_file = tmp_path / "VERSION"
        version_file.write_text(
            "version=0.3.0\nsha=abc123def456\ndeployed_at=2026-09-27T12:00:00Z\ngit_status=clean\n"
        )

        assert _read_deploy_sha(str(version_file)) == "abc123def456"

    def test_falls_back_to_unknown_when_version_file_missing(self, tmp_path):
        """Given no VERSION file at the given path,
        When read,
        Then the fallback value is returned instead of raising."""
        missing = tmp_path / "VERSION"

        assert _read_deploy_sha(str(missing)) == _UNKNOWN_VERSION

    def test_falls_back_to_unknown_when_sha_line_absent(self, tmp_path):
        """Given a VERSION file without a sha= line,
        When read,
        Then the fallback value is returned."""
        version_file = tmp_path / "VERSION"
        version_file.write_text("version=0.3.0\n")

        assert _read_deploy_sha(str(version_file)) == _UNKNOWN_VERSION
