# ARTEFACT — Story 5.1 : tests unitaires de la façade /action/execute.
"""Tests de la façade backend unique — validation paramètres, rejet, réponse homogène."""

import json
import pytest
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from transport.http_server import create_app


SECRET = "test-secret-5.1"
VALID_HEADERS = {"X-Local-Secret": SECRET}


class TestFacadeValidation(AioHTTPTestCase):
    """AC 1 — Validation des paramètres et rejet explicite."""

    async def get_application(self):
        return create_app(SECRET)

    @unittest_run_loop
    async def test_intention_inconnue_rejet(self):
        """Intention non reconnue → rejet avec erreur explicite."""
        resp = await self.client.post(
            "/action/execute",
            json={"intention": "detruire", "portee": "equipement", "selection": [1]},
            headers=VALID_HEADERS,
        )
        assert resp.status == 400
        body = await resp.json()
        assert body["status"] == "error"
        assert "intention" in body.get("message", "").lower()

    @unittest_run_loop
    async def test_portee_inconnue_rejet(self):
        """Portée non reconnue → rejet avec erreur explicite."""
        resp = await self.client.post(
            "/action/execute",
            json={"intention": "publier", "portee": "univers", "selection": [1]},
            headers=VALID_HEADERS,
        )
        assert resp.status == 400
        body = await resp.json()
        assert body["status"] == "error"
        assert "portee" in body.get("message", "").lower() or "portée" in body.get("message", "").lower()

    @unittest_run_loop
    async def test_selection_vide_rejet(self):
        """Sélection vide → rejet."""
        resp = await self.client.post(
            "/action/execute",
            json={"intention": "publier", "portee": "equipement", "selection": []},
            headers=VALID_HEADERS,
        )
        assert resp.status == 400
        body = await resp.json()
        assert body["status"] == "error"

    @unittest_run_loop
    async def test_selection_absente_rejet(self):
        """Sélection absente → rejet."""
        resp = await self.client.post(
            "/action/execute",
            json={"intention": "publier", "portee": "equipement"},
            headers=VALID_HEADERS,
        )
        assert resp.status == 400

    @unittest_run_loop
    async def test_intention_publier_reconnue(self):
        """Intention 'publier' → acceptée."""
        resp = await self.client.post(
            "/action/execute",
            json={"intention": "publier", "portee": "equipement", "selection": [42]},
            headers=VALID_HEADERS,
        )
        assert resp.status == 200
        body = await resp.json()
        assert body["status"] == "ok"

    @unittest_run_loop
    async def test_intention_supprimer_reconnue(self):
        """Intention 'supprimer' → acceptée."""
        resp = await self.client.post(
            "/action/execute",
            json={"intention": "supprimer", "portee": "equipement", "selection": [42]},
            headers=VALID_HEADERS,
        )
        assert resp.status == 200
        body = await resp.json()
        assert body["status"] == "ok"

    @unittest_run_loop
    async def test_sans_auth_401(self):
        """Pas de secret → 401."""
        resp = await self.client.post(
            "/action/execute",
            json={"intention": "publier", "portee": "equipement", "selection": [1]},
        )
        assert resp.status == 401


class TestFacadeReponseHomogene(AioHTTPTestCase):
    """AC 1 — Contrat de réponse homogène quelle que soit la portée."""

    async def get_application(self):
        return create_app(SECRET)

    ENVELOPE_KEYS = {"action", "status", "payload", "request_id", "timestamp"}
    PAYLOAD_KEYS = {"intention", "portee", "selection", "resultat", "message"}

    async def _call(self, portee, selection):
        resp = await self.client.post(
            "/action/execute",
            json={"intention": "publier", "portee": portee, "selection": selection},
            headers=VALID_HEADERS,
        )
        body = await resp.json()
        return resp.status, body

    @unittest_run_loop
    async def test_portee_equipement(self):
        status, body = await self._call("equipement", [42])
        assert status == 200
        assert set(body.keys()) >= self.ENVELOPE_KEYS
        assert set(body["payload"].keys()) >= self.PAYLOAD_KEYS

    @unittest_run_loop
    async def test_portee_piece(self):
        status, body = await self._call("piece", [10])
        assert status == 200
        assert set(body.keys()) >= self.ENVELOPE_KEYS
        assert set(body["payload"].keys()) >= self.PAYLOAD_KEYS

    @unittest_run_loop
    async def test_portee_global(self):
        status, body = await self._call("global", ["all"])
        assert status == 200
        assert set(body.keys()) >= self.ENVELOPE_KEYS
        assert set(body["payload"].keys()) >= self.PAYLOAD_KEYS

    @unittest_run_loop
    async def test_reponse_homogene_entre_portees(self):
        """Le contrat de réponse a la même structure quelle que soit la portée."""
        _, body_eq = await self._call("equipement", [42])
        _, body_piece = await self._call("piece", [10])
        _, body_global = await self._call("global", ["all"])
        # Mêmes clés dans payload
        assert set(body_eq["payload"].keys()) == set(body_piece["payload"].keys())
        assert set(body_eq["payload"].keys()) == set(body_global["payload"].keys())

    @unittest_run_loop
    async def test_action_field_coherent(self):
        """Le champ 'action' est toujours 'action.execute'."""
        _, body = await self._call("equipement", [42])
        assert body["action"] == "action.execute"
