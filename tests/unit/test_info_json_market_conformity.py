"""
test_info_json_market_conformity.py — conformité de plugin_info/info.json au
Market Jeedom (référence : doc.jeedom.com/fr_FR/dev/structure_info_json).

Aucune valeur de version n'est codée en dur : la cohérence est vérifiée entre
pluginVersion, le dernier tag Git ``v*`` et le changelog référencé par info.json.

Rejouer :
    pytest tests/unit/test_info_json_market_conformity.py -v
"""
import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
INFO_PATH = ROOT / "plugin_info" / "info.json"

REQUIRED_FIELDS = (
    "id", "name", "description", "licence", "author", "require", "category",
    "changelog", "documentation", "changelog_beta", "documentation_beta",
)
MIN_DESCRIPTION_LEN = 80
UNTESTED_COMPATIBILITY = {"luna", "atlas"}
BLOB_RE = re.compile(
    r"^https://github\.com/[^/]+/[^/]+/blob/(?P<branch>[^/]+)/(?P<path>docs/fr_FR/.+)$"
)
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


@pytest.fixture(scope="module")
def info():
    return json.loads(INFO_PATH.read_text(encoding="utf-8"))


def _git(*args):
    try:
        res = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return res.stdout.strip()


def _version_tuple(text):
    return tuple(int(p) for p in text.split("."))


def _version_tags(raw):
    return [t for t in (raw or "").splitlines() if re.fullmatch(r"v\d+\.\d+\.\d+", t)]


def _repo_file(url):
    m = BLOB_RE.match(url)
    assert m, f"lien hors docs/fr_FR : {url}"
    return ROOT / m.group("path")


def test_required_fields_present(info):
    for field in REQUIRED_FIELDS:
        assert info.get(field), f"champ obligatoire manquant ou vide : {field}"


def test_description_min_length_per_declared_language(info):
    assert info["language"], "language ne doit pas être vide"
    for lang in info["language"]:
        text = info["description"].get(lang, "")
        assert len(text) >= MIN_DESCRIPTION_LEN, (
            f"description.{lang} : {len(text)} car. < {MIN_DESCRIPTION_LEN}"
        )


def test_language_matches_description_and_docs(info):
    assert set(info["description"]) == set(info["language"])
    assert info["language"] == ["fr_FR"], "seule la doc fr_FR existe (décision 20-5)"
    assert (ROOT / "docs" / "fr_FR").is_dir()


@pytest.mark.parametrize("field,branch", [
    ("changelog", "stable"), ("documentation", "stable"),
    ("changelog_beta", "beta"), ("documentation_beta", "beta"),
])
def test_doc_links_target_channel_branch_and_existing_file(info, field, branch):
    m = BLOB_RE.match(info[field])
    assert m, f"{field} doit pointer vers blob/{branch}/docs/fr_FR/... : {info[field]}"
    assert m.group("branch") == branch
    assert _repo_file(info[field]).is_file(), f"{field} : fichier absent du dépôt"


def test_compatibility_excludes_untested_platforms(info):
    assert info["compatibility"]
    assert not UNTESTED_COMPATIBILITY & set(info["compatibility"])


def test_issue_link_declared(info):
    assert re.match(r"^https://github\.com/[^/]+/[^/]+/issues/?$", info.get("issue", ""))


def test_icons_present_and_template_icon_removed():
    assert (ROOT / "plugin_info" / "jeedom2ha_icon.png").is_file()
    assert (ROOT / "plugin_info" / "jeedom2ha_icon.svg").is_file()
    assert not (ROOT / "plugin_info" / "template_icon.png").exists()


def test_plugin_version_is_semver(info):
    assert SEMVER_RE.match(info["pluginVersion"])


def test_plugin_version_not_behind_latest_tag_and_exact_when_tagged(info):
    tags = _version_tags(_git("tag", "--list", "v*"))
    if not tags:
        pytest.skip("aucun tag v* disponible (clone sans tags)")
    latest = max(tags, key=lambda t: _version_tuple(t[1:]))
    current = _version_tuple(info["pluginVersion"])
    assert current >= _version_tuple(latest[1:]), (
        f"pluginVersion {info['pluginVersion']} < dernier tag {latest}"
    )
    head_tags = _version_tags(_git("tag", "--points-at", "HEAD"))
    if head_tags:
        assert info["pluginVersion"] in {t[1:] for t in head_tags}, (
            f"HEAD est taggé {head_tags} : pluginVersion doit être égal au tag"
        )


def test_changelog_has_entry_citing_plugin_version(info):
    text = _repo_file(info["changelog"]).read_text(encoding="utf-8")
    version = re.escape(info["pluginVersion"])
    pattern = re.compile(rf"^#\s.*(?<![\w.])v?{version}(?![\w.])", re.MULTILINE)
    assert pattern.search(text), (
        f"aucune entrée de changelog (en-tête '# ...') ne cite {info['pluginVersion']}"
    )
