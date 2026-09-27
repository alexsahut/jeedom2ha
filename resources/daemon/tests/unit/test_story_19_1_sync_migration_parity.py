"""Story 19.1 — Task 4 : le pipeline `/action/sync` délègue réellement à `evaluate_equipment()`
(Story 19.0), sans changement de comportement (AC1, AC2).

Ces tests couvrent les garde-fous explicites de la migration :
  - `evaluate_equipment()` est bien le point d'entrée utilisé pour l'étape 2→4 (mapping,
    override de type, validation projection, décision de publication) d'un équipement
    éligible — pas une réplique parallèle du pipeline classique.
  - Le `MapperRegistry` reste instancié UNE SEULE FOIS par cycle de sync et INJECTÉ dans
    `evaluate_equipment()` — jamais recréé à l'intérieur.
  - Les liens croisés bidirectionnels (`decision.mapping_result is mapping`) posés par
    `evaluate_equipment()` survivent au stockage dans `app["mappings"]`/`app["publications"]`.
  - Les garde-fous préexistants (équipement inéligible, mapping `None`) continuent à être
    respectés à l'identique après migration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.evaluate_equipment import evaluate_equipment as _real_evaluate_equipment
from transport.http_server import create_app


SECRET = "test-secret-pe-19-1-sync-migration"


def _sync_body(eq_logics: list[dict]) -> dict:
    return {
        "action": "sync",
        "payload": {
            "objects": [{"id": 1, "name": "Salon"}],
            "eq_logics": eq_logics,
            "sync_config": {"confidence_policy": "sure_probable"},
        },
        "request_id": "pe-19-1-test",
        "timestamp": "2026-09-27T00:00:00Z",
    }


def _light_eq_payload(eq_id: int, cmds: list[dict]) -> dict:
    return {
        "id": eq_id,
        "name": f"Lumiere {eq_id}",
        "object_id": 1,
        "is_enable": True,
        "is_visible": True,
        "eq_type": "virtual",
        "is_excluded": False,
        "status": {"timeout": 0},
        "cmds": cmds,
    }


_VALID_LIGHT_CMDS = [
    {"id": 1, "name": "On", "generic_type": "LIGHT_ON", "type": "action", "sub_type": "other"},
    {"id": 2, "name": "Off", "generic_type": "LIGHT_OFF", "type": "action", "sub_type": "other"},
    {"id": 3, "name": "Etat", "generic_type": "LIGHT_STATE", "type": "info", "sub_type": "binary"},
]

_NO_MAPPABLE_ACTION_CMDS = [
    # generic_type non-null (éligible) mais ni "info" ni "action" (type="config") : aucun
    # mapper spécifique ne le reconnaît et le FallbackMapper terminal renvoie None
    # (mapping/fallback.py — ni _has_info_command ni _has_action_command).
    {"id": 1, "name": "Config", "generic_type": "UNKNOWN_GENERIC_TYPE", "type": "config", "sub_type": "other"},
]


@pytest.fixture
def app():
    return create_app(local_secret=SECRET)


@pytest.fixture
async def cli(aiohttp_client, app):
    return await aiohttp_client(app)


@pytest.fixture
def mock_publisher():
    publisher = AsyncMock()
    publisher.publish_light = AsyncMock(return_value=True)
    publisher.publish_cover = AsyncMock(return_value=True)
    publisher.publish_switch = AsyncMock(return_value=True)
    publisher.unpublish_by_eq_id = AsyncMock(return_value=True)
    return publisher


def _set_connected_bridge(app):
    bridge = MagicMock()
    bridge.is_connected = True
    bridge.publish_message = MagicMock(return_value=True)
    app["mqtt_bridge"] = bridge


async def test_sync_delegates_primary_pipeline_to_evaluate_equipment(cli, app, mock_publisher):
    """Le sync appelle bien `evaluate_equipment()` pour chaque équipement éligible et mappé —
    pas de réplique locale de l'enchaînement map/override/validate/decide."""
    calls: list[dict] = []

    def _evaluate_spy(*args, **kwargs):
        calls.append(kwargs)
        return _real_evaluate_equipment(*args, **kwargs)

    _set_connected_bridge(app)
    payload = _sync_body([_light_eq_payload(201, _VALID_LIGHT_CMDS)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher), patch(
        "transport.http_server.evaluate_equipment", side_effect=_evaluate_spy
    ):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    assert len(calls) == 1, "evaluate_equipment() doit être appelée une fois pour l'unique équipement éligible mappé"
    assert calls[0]["confidence_policy"] == "sure_probable"
    assert app["confidence_policy"] == "sure_probable"


async def test_sync_uses_app_data_dir_for_overrides_and_publication_cache(
    cli, app, mock_publisher, monkeypatch, tmp_path
):
    """Le resolver app data_dir alimente le sync, sans retomber sur le data/ global."""
    import transport.http_server as hs

    calls = []
    monkeypatch.setattr(hs, "list_overrides", lambda path: calls.append(("overrides", path)) or {})
    monkeypatch.setattr(
        hs, "list_equipment_overrides", lambda path: calls.append(("equipment", path)) or {}
    )
    monkeypatch.setattr(
        hs, "save_publications_cache", lambda _publications, path: calls.append(("cache", path))
    )
    app["data_dir"] = str(tmp_path)
    _set_connected_bridge(app)

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post(
            "/action/sync",
            json=_sync_body([_light_eq_payload(206, _VALID_LIGHT_CMDS)]),
            headers={"X-Local-Secret": SECRET},
        )

    assert resp.status == 200
    assert calls == [
        ("overrides", str(tmp_path)),
        ("equipment", str(tmp_path)),
        ("cache", str(tmp_path)),
    ]


async def test_mapper_registry_instantiated_once_and_injected_not_recreated(cli, app, mock_publisher):
    """Le `MapperRegistry` reste instancié UNE SEULE FOIS par sync et transmis tel quel à
    `evaluate_equipment()` — jamais recréé à l'intérieur de la boucle (guardrail Alexandre)."""
    from mapping.registry import MapperRegistry as _RealMapperRegistry

    instances_created: list[object] = []
    injected_registries: list[object] = []

    class _SpyMapperRegistry(_RealMapperRegistry):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            instances_created.append(self)

    def _evaluate_spy(*args, **kwargs):
        injected_registries.append(kwargs.get("mapper_registry"))
        return _real_evaluate_equipment(*args, **kwargs)

    _set_connected_bridge(app)
    payload = _sync_body(
        [
            _light_eq_payload(202, _VALID_LIGHT_CMDS),
            _light_eq_payload(203, _VALID_LIGHT_CMDS),
        ]
    )

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher), patch(
        "transport.http_server.MapperRegistry", _SpyMapperRegistry
    ), patch("transport.http_server.evaluate_equipment", side_effect=_evaluate_spy):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    assert len(instances_created) == 1, "un seul MapperRegistry doit être créé par cycle de sync"
    assert len(injected_registries) == 2, "evaluate_equipment() doit être appelée une fois par équipement éligible"
    for registry in injected_registries:
        assert registry is instances_created[0], (
            "le MapperRegistry injecté dans evaluate_equipment() doit être la même instance "
            "que celle créée une fois par sync — jamais recréée en interne"
        )


async def test_publication_mapping_identity_link_preserved_in_app_state(cli, app, mock_publisher):
    """Les liens croisés bidirectionnels posés par `evaluate_equipment()`
    (`decision.mapping_result is mapping`) doivent survivre au stockage dans
    `app["mappings"]`/`app["publications"]` (guardrail Alexandre #3)."""
    _set_connected_bridge(app)
    payload = _sync_body([_light_eq_payload(204, _VALID_LIGHT_CMDS)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200

    mapping = app["mappings"][204]
    decision = app["publications"][204]
    assert decision.mapping_result is mapping
    assert mapping.publication_decision_ref is decision


async def test_sync_consumes_evaluation_secondary_decisions_without_redeciding(
    cli, app, mock_publisher
):
    """Un secondaire refusé par le contrat ne doit pas être recalculé puis publié par le sync.

    La mutation est volontairement limitée à l'objet `EquipmentEvaluation` créé pour ce
    test : elle simule une décision du contrat qui diffère du calcul historique et prouve
    que l'orchestrateur consomme bien `secondary_decisions`.
    """
    mock_publisher.publish_sensor = AsyncMock(return_value=True)
    _set_connected_bridge(app)
    payload = _sync_body([
        {
            "id": 205, "name": "Prise avec conso", "object_id": 1,
            "is_enable": True, "is_visible": True, "eq_type": "prise",
            "is_excluded": False, "status": {"timeout": 0},
            "cmds": [
                {"id": 2051, "name": "On", "generic_type": "ENERGY_ON", "type": "action", "sub_type": "other"},
                {"id": 2052, "name": "Off", "generic_type": "ENERGY_OFF", "type": "action", "sub_type": "other"},
                {"id": 2053, "name": "Etat", "generic_type": "ENERGY_STATE", "type": "info", "sub_type": "binary"},
                {"id": 2054, "name": "Conso", "generic_type": None, "type": "info", "sub_type": "numeric", "unit": "W"},
            ],
        }
    ])

    def _evaluate_with_temporarily_refused_secondary(*args, **kwargs):
        evaluation = _real_evaluate_equipment(*args, **kwargs)
        assert evaluation.secondary_decisions
        secondary = evaluation.secondary_decisions[0]
        secondary.should_publish = False
        secondary.reason = "test_contract_secondary_refused"
        return evaluation

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher), patch(
        "transport.http_server.evaluate_equipment",
        side_effect=_evaluate_with_temporarily_refused_secondary,
    ):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    mock_publisher.publish_sensor.assert_not_awaited()
    secondary = app["mappings"][205].additional_mappings[0]
    assert secondary.publication_decision_ref.reason == "test_contract_secondary_refused"


async def test_ineligible_equipment_still_skipped_after_migration(cli, app, mock_publisher):
    """Garde-fou préexistant : un équipement inéligible n'apparaît ni dans `app["mappings"]`
    ni dans `app["publications"]`, à l'identique du pipeline classique (pas de régression)."""
    _set_connected_bridge(app)
    payload = _sync_body(
        [
            {
                "id": 301,
                "name": "Equipement sans generic_type",
                "object_id": 1,
                "is_enable": True,
                "is_visible": True,
                "eq_type": "virtual",
                "is_excluded": False,
                "status": {"timeout": 0},
                "cmds": [
                    {"id": 1, "name": "Cmd", "generic_type": None, "type": "action", "sub_type": "other"},
                ],
            }
        ]
    )

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    assert 301 not in app["mappings"]
    assert 301 not in app["publications"]


async def test_mapping_none_still_skipped_after_migration(cli, app, mock_publisher):
    """Garde-fou préexistant : un équipement éligible mais que `mapper_registry.map()` ne
    parvient pas à mapper (`None`) n'apparaît ni dans `app["mappings"]` ni dans
    `app["publications"]`, à l'identique du pipeline classique."""
    _set_connected_bridge(app)
    payload = _sync_body([_light_eq_payload(302, _NO_MAPPABLE_ACTION_CMDS)])

    with patch("transport.http_server.DiscoveryPublisher", return_value=mock_publisher):
        resp = await cli.post("/action/sync", json=payload, headers={"X-Local-Secret": SECRET})

    assert resp.status == 200
    assert 302 not in app["mappings"]
    assert 302 not in app["publications"]
