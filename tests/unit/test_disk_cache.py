"""
test_disk_cache.py — Unit tests for the disk cache module (Stories 5.1 + 5.2).

Covers:
  - save_publications_cache: happy path, missing data_dir
  - load_publications_cache: happy path, missing file, corrupted JSON, type conversion
  - AC #1: cache written with correct format (entity_type, published, ha_name, suggested_area)
  - AC #2: cache loads correctly (absent → {}, corrupted → {})
  - AC #3: cold start without file → boot_cache empty, no publish
  - AC #9 (5.2): save produces new format with ha_name and suggested_area
  - AC #10 (5.2): load of 5.1 cache (without ha_name) returns ha_name="", suggested_area=None
"""
import json
import os
import tempfile

import pytest


class TestSavePublicationsCache:
    """AC #1 / AC #9 — save_publications_cache writes correct format."""

    def _make_decision(self, entity_type: str, published: bool, ha_name: str = "", suggested_area=None):
        """Helper to build a minimal PublicationDecision-like object."""
        mapping = type("MappingResult", (), {
            "ha_entity_type": entity_type,
            "ha_name": ha_name,
            "suggested_area": suggested_area,
        })()
        decision = type(
            "PublicationDecision",
            (),
            {"mapping_result": mapping, "discovery_published": published},
        )()
        return decision

    def test_save_writes_correct_json_format(self, tmp_path):
        from resources.daemon.cache.disk_cache import save_publications_cache

        publications = {
            123: self._make_decision("light", True),
            456: self._make_decision("cover", True),
            789: self._make_decision("switch", False),
        }
        save_publications_cache(publications, str(tmp_path))

        cache_path = tmp_path / "jeedom2ha_cache.json"
        assert cache_path.exists()
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)

        assert data["123"] == {"entity_type": "light", "published": True, "ha_name": "", "suggested_area": None}
        assert data["456"] == {"entity_type": "cover", "published": True, "ha_name": "", "suggested_area": None}
        assert data["789"] == {"entity_type": "switch", "published": False, "ha_name": "", "suggested_area": None}

    def test_save_keys_are_strings(self, tmp_path):
        """JSON keys must be strings (JSON limitation)."""
        from resources.daemon.cache.disk_cache import save_publications_cache

        publications = {42: self._make_decision("light", True)}
        save_publications_cache(publications, str(tmp_path))

        with open(tmp_path / "jeedom2ha_cache.json", encoding="utf-8") as f:
            data = json.load(f)

        assert "42" in data
        assert 42 not in data

    def test_save_with_missing_data_dir_logs_warning_no_crash(self, caplog):
        from resources.daemon.cache.disk_cache import save_publications_cache
        import logging

        publications = {1: self._make_decision("light", True)}
        with caplog.at_level(logging.WARNING, logger="resources.daemon.cache.disk_cache"):
            save_publications_cache(publications, "/nonexistent/path/that/does/not/exist")

        assert any("CACHE" in record.message for record in caplog.records)

    def test_save_empty_publications(self, tmp_path):
        from resources.daemon.cache.disk_cache import save_publications_cache

        save_publications_cache({}, str(tmp_path))
        with open(tmp_path / "jeedom2ha_cache.json", encoding="utf-8") as f:
            data = json.load(f)
        assert data == {}

    def test_save_decision_without_mapping_result(self, tmp_path):
        """Decision with mapping_result=None should not crash."""
        from resources.daemon.cache.disk_cache import save_publications_cache

        decision = type("PublicationDecision", (), {"mapping_result": None, "discovery_published": False})()
        save_publications_cache({55: decision}, str(tmp_path))

        with open(tmp_path / "jeedom2ha_cache.json", encoding="utf-8") as f:
            data = json.load(f)
        assert data["55"] == {"entity_type": "", "published": False, "ha_name": "", "suggested_area": None}

    def test_save_includes_ha_name_and_suggested_area(self, tmp_path):
        """AC #9 — save persists ha_name and suggested_area from mapping_result."""
        from resources.daemon.cache.disk_cache import save_publications_cache

        publications = {
            10: self._make_decision("light", True, ha_name="Lampe Salon", suggested_area="Salon"),
            20: self._make_decision("cover", True, ha_name="Volet Chambre", suggested_area="Chambre"),
            30: self._make_decision("switch", False, ha_name="Prise Bureau", suggested_area=None),
        }
        save_publications_cache(publications, str(tmp_path))

        with open(tmp_path / "jeedom2ha_cache.json", encoding="utf-8") as f:
            data = json.load(f)

        assert data["10"] == {"entity_type": "light", "published": True, "ha_name": "Lampe Salon", "suggested_area": "Salon"}
        assert data["20"] == {"entity_type": "cover", "published": True, "ha_name": "Volet Chambre", "suggested_area": "Chambre"}
        assert data["30"] == {"entity_type": "switch", "published": False, "ha_name": "Prise Bureau", "suggested_area": None}


class TestLoadPublicationsCache:
    """AC #2 / AC #10 — load_publications_cache: absent file → {}, corrupted → {}, happy path."""

    def test_load_happy_path(self, tmp_path):
        """Load a 5.1 cache (without ha_name/suggested_area) — backward compat AC #10."""
        from resources.daemon.cache.disk_cache import load_publications_cache

        cache_data = {
            "123": {"entity_type": "light", "published": True},
            "456": {"entity_type": "cover", "published": False},
        }
        with open(tmp_path / "jeedom2ha_cache.json", "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        result = load_publications_cache(str(tmp_path))

        # 5.1 cache: ha_name and suggested_area default to "" and None respectively
        assert result == {
            123: {"entity_type": "light", "published": True, "ha_name": "", "suggested_area": None},
            456: {"entity_type": "cover", "published": False, "ha_name": "", "suggested_area": None},
        }

    def test_load_51_cache_without_ha_name_returns_defaults(self, tmp_path, caplog):
        """AC #10 — 5.1 cache without ha_name/suggested_area → defaults, no error log."""
        from resources.daemon.cache.disk_cache import load_publications_cache
        import logging

        cache_51 = {
            "42": {"entity_type": "light", "published": True},
        }
        with open(tmp_path / "jeedom2ha_cache.json", "w", encoding="utf-8") as f:
            json.dump(cache_51, f)

        with caplog.at_level(logging.ERROR, logger="resources.daemon.cache.disk_cache"):
            result = load_publications_cache(str(tmp_path))

        # No error logged
        assert not any(record.levelno >= logging.ERROR for record in caplog.records)
        # Defaults applied
        assert result[42]["ha_name"] == ""
        assert result[42]["suggested_area"] is None
        assert result[42]["entity_type"] == "light"
        assert result[42]["published"] is True

    def test_load_new_format_full_fields(self, tmp_path):
        """Load a 5.2 cache with all fields present."""
        from resources.daemon.cache.disk_cache import load_publications_cache

        cache_52 = {
            "10": {"entity_type": "light", "published": True, "ha_name": "Lampe Salon", "suggested_area": "Salon"},
            "20": {"entity_type": "switch", "published": False, "ha_name": "Prise Bureau", "suggested_area": None},
        }
        with open(tmp_path / "jeedom2ha_cache.json", "w", encoding="utf-8") as f:
            json.dump(cache_52, f)

        result = load_publications_cache(str(tmp_path))

        assert result[10] == {"entity_type": "light", "published": True, "ha_name": "Lampe Salon", "suggested_area": "Salon"}
        assert result[20] == {"entity_type": "switch", "published": False, "ha_name": "Prise Bureau", "suggested_area": None}

    def test_load_converts_keys_to_int(self, tmp_path):
        """Keys must be converted from str to int on load."""
        from resources.daemon.cache.disk_cache import load_publications_cache

        with open(tmp_path / "jeedom2ha_cache.json", "w", encoding="utf-8") as f:
            json.dump({"99": {"entity_type": "switch", "published": True}}, f)

        result = load_publications_cache(str(tmp_path))

        assert 99 in result
        assert isinstance(list(result.keys())[0], int)

    def test_load_missing_file_returns_empty_dict(self, tmp_path, caplog):
        """AC #3 — cold start: missing cache → {} with INFO log."""
        from resources.daemon.cache.disk_cache import load_publications_cache
        import logging

        with caplog.at_level(logging.INFO, logger="resources.daemon.cache.disk_cache"):
            result = load_publications_cache(str(tmp_path))

        assert result == {}
        assert any("cold start" in record.message.lower() for record in caplog.records)

    def test_load_corrupted_json_returns_empty_dict(self, tmp_path, caplog):
        """AC #3 — corrupted cache → {} with INFO log."""
        from resources.daemon.cache.disk_cache import load_publications_cache
        import logging

        with open(tmp_path / "jeedom2ha_cache.json", "w", encoding="utf-8") as f:
            f.write("{ this is not valid json }")

        with caplog.at_level(logging.INFO, logger="resources.daemon.cache.disk_cache"):
            result = load_publications_cache(str(tmp_path))

        assert result == {}
        assert any("cold start" in record.message.lower() for record in caplog.records)

    def test_load_non_dict_json_returns_empty_dict(self, tmp_path):
        """JSON root is a list instead of dict → {}."""
        from resources.daemon.cache.disk_cache import load_publications_cache

        with open(tmp_path / "jeedom2ha_cache.json", "w", encoding="utf-8") as f:
            json.dump([1, 2, 3], f)

        result = load_publications_cache(str(tmp_path))
        assert result == {}

    def test_load_skips_entries_with_invalid_keys(self, tmp_path):
        """Non-integer keys in JSON are silently skipped."""
        from resources.daemon.cache.disk_cache import load_publications_cache

        with open(tmp_path / "jeedom2ha_cache.json", "w", encoding="utf-8") as f:
            json.dump({
                "42": {"entity_type": "light", "published": True},
                "not-a-number": {"entity_type": "light", "published": True},
            }, f)

        result = load_publications_cache(str(tmp_path))
        assert 42 in result
        assert len(result) == 1

    def test_load_skips_entries_with_non_dict_values(self, tmp_path):
        """Non-dict values in JSON are silently skipped."""
        from resources.daemon.cache.disk_cache import load_publications_cache

        with open(tmp_path / "jeedom2ha_cache.json", "w", encoding="utf-8") as f:
            json.dump({
                "1": {"entity_type": "light", "published": True},
                "2": "invalid-value",
            }, f)

        result = load_publications_cache(str(tmp_path))
        assert 1 in result
        assert 2 not in result


class TestColdStartBehavior:
    """AC #3 — daemon starts normally with empty boot_cache when no file."""

    def test_cold_start_boot_cache_is_empty(self, tmp_path):
        """AC #3: load with missing file → empty dict → no publications loaded."""
        from resources.daemon.cache.disk_cache import load_publications_cache

        result = load_publications_cache(str(tmp_path))
        assert result == {}
        # No publications from cache → INV-2 preserved (no publish)

    def test_save_then_load_roundtrip(self, tmp_path):
        """save then load should return equivalent data (eq_ids as int, correct types)."""
        from resources.daemon.cache.disk_cache import save_publications_cache, load_publications_cache

        mapping = type("MappingResult", (), {
            "ha_entity_type": "light",
            "ha_name": "Lampe Test",
            "suggested_area": "Salon",
        })()
        decision = type(
            "PublicationDecision",
            (),
            {"mapping_result": mapping, "discovery_published": True},
        )()
        publications = {10: decision, 20: decision}

        save_publications_cache(publications, str(tmp_path))
        result = load_publications_cache(str(tmp_path))

        assert set(result.keys()) == {10, 20}
        for entry in result.values():
            assert entry["entity_type"] == "light"
            assert entry["published"] is True
            assert entry["ha_name"] == "Lampe Test"
            assert entry["suggested_area"] == "Salon"
