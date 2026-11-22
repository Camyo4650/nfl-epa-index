import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from service import EngineHandler


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), EngineHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()

    def request(self, path):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_health_and_invalid_routes(self):
        self.assertEqual(self.request("/health"), (200, {"status": "ok"}))
        self.assertEqual(self.request("/rankings?season=invalid")[0], 400)
        self.assertEqual(self.request("/rankings?season=2019")[0], 400)
        self.assertEqual(self.request("/rankings?season=2024&season=2025")[0], 400)
        self.assertEqual(self.request("/playoffs?season=2024")[0], 400)
        self.assertEqual(self.request("/playoffs?season=2024&week=19")[0], 400)
        self.assertEqual(self.request("/playoffs?season=2024&week=1&week=2")[0], 400)
        self.assertEqual(self.request("/playoffs/progress?job=invalid")[0], 400)
        self.assertEqual(self.request("/playoffs?season=2024&week=1&job=invalid")[0], 400)
        self.assertEqual(self.request("/unknown")[0], 404)

    @patch("service.store")
    def test_success_and_engine_errors(self, store):
        store.seasons.return_value = {"seasons": [2024]}
        self.assertEqual(self.request("/seasons"), (200, {"seasons": [2024]}))
        store.status.return_value = {"latestWeek": 10}
        self.assertEqual(self.request("/status"), (200, {"latestWeek": 10}))
        store.playoff_data.return_value = {"week": 10}
        self.assertEqual(self.request("/playoffs?season=2024&week=10"), (200, {"week": 10}))
        store.playoff_data.assert_called_once_with(2024, 10)
        job = "12345678-1234-5678-1234-567812345678"
        store.playoff_progress.return_value = {"completed": 10000, "total": 100000}
        self.assertEqual(self.request(f"/playoffs/progress?job={job}"),
                         (200, {"completed": 10000, "total": 100000}))
        store.season_data.side_effect = RuntimeError("upstream failed")
        self.assertEqual(self.request("/rankings?season=2024")[0], 503)
