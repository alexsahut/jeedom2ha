"""test_daemon_secrets_file.py — CC-08 key hygiene: --secretsfile support.

apikey/localsecret/jeedomcoreapikey must never appear as CLI argv (visible via
``ps aux`` / ``/proc/<pid>/cmdline``). When ``--secretsfile`` points to a
``KEY=VALUE`` file, Jeedom2haConfig.parse() must read it and inject the three
secret values into the parsed args in memory, without changing sys.argv.
Backward compatibility: without --secretsfile, argv-provided values (or
their defaults) are used unchanged, as before this change.
"""
import os
from unittest.mock import patch

from resources.daemon.main import Jeedom2haConfig, _load_secrets_file


_BASE_CLI_ARGS = [
    "--loglevel", "debug",
    "--sockethost", "127.0.0.1",
    "--socketport", "0",
    "--callback", "http://127.0.0.1/fake",
    "--pid", "/tmp/test-jeedom2ha.pid",
    "--cycle", "0.5",
]


class TestLoadSecretsFile:
    def test_reads_key_value_lines(self, tmp_path):
        secrets_path = tmp_path / "daemon.secrets"
        secrets_path.write_text("apikey=abc123\nlocalsecret=def456\njeedomcoreapikey=ghi789\n")

        secrets = _load_secrets_file(str(secrets_path))

        assert secrets == {
            "apikey": "abc123",
            "localsecret": "def456",
            "jeedomcoreapikey": "ghi789",
        }

    def test_ignores_blank_lines_and_lines_without_equals(self, tmp_path):
        secrets_path = tmp_path / "daemon.secrets"
        secrets_path.write_text("apikey=abc123\n\nmalformed_line_no_equals\nlocalsecret=def456\n")

        secrets = _load_secrets_file(str(secrets_path))

        assert secrets == {"apikey": "abc123", "localsecret": "def456"}


class TestJeedom2haConfigSecretsFileInjection:
    def test_without_secretsfile_keeps_argv_values(self):
        argv = ["main.py"] + _BASE_CLI_ARGS + [
            "--apikey", "argv-apikey",
            "--localsecret", "argv-localsecret",
            "--jeedomcoreapikey", "argv-core-key",
        ]
        with patch("sys.argv", argv):
            config = Jeedom2haConfig()
            config.parse()

        assert config.api_key == "argv-apikey"
        assert config.localsecret == "argv-localsecret"
        assert config.jeedomcoreapikey == "argv-core-key"

    def test_with_secretsfile_overrides_argv_defaults(self, tmp_path):
        secrets_path = tmp_path / "daemon.secrets"
        secrets_path.write_text(
            "apikey=file-apikey\nlocalsecret=file-localsecret\njeedomcoreapikey=file-core-key\n"
        )
        os.chmod(secrets_path, 0o600)

        argv = ["main.py"] + _BASE_CLI_ARGS + ["--secretsfile", str(secrets_path)]
        with patch("sys.argv", argv):
            config = Jeedom2haConfig()
            config.parse()

        assert config.api_key == "file-apikey"
        assert config.localsecret == "file-localsecret"
        assert config.jeedomcoreapikey == "file-core-key"

    def test_secretsfile_value_not_present_in_argv(self, tmp_path):
        """The secret values themselves must never be passed as CLI arguments."""
        secrets_path = tmp_path / "daemon.secrets"
        secrets_path.write_text("apikey=super-secret-value\n")

        argv = ["main.py"] + _BASE_CLI_ARGS + ["--secretsfile", str(secrets_path)]
        with patch("sys.argv", argv):
            config = Jeedom2haConfig()
            config.parse()

            assert "super-secret-value" not in " ".join(argv)
            assert config.api_key == "super-secret-value"
