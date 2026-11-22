import json
import logging
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import store


class EngineHandler(BaseHTTPRequestHandler):
    def respond(self, status, body):
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/health":
            self.respond(200, {"status": "ok"})
            return
        try:
            if url.path == "/status":
                result = store.status()
            elif url.path == "/seasons":
                result = store.seasons()
            elif url.path == "/playoffs/progress":
                jobs = parse_qs(url.query).get("job", [])
                if len(jobs) != 1:
                    self.respond(400, {"error": "A valid job ID is required."})
                    return
                try:
                    job = str(UUID(jobs[0]))
                except ValueError:
                    self.respond(400, {"error": "A valid job ID is required."})
                    return
                result = store.playoff_progress(job)
            elif url.path in ("/rankings", "/playoffs"):
                values = parse_qs(url.query).get("season", [])
                if len(values) != 1 or not values[0].isascii() or not values[0].isdigit():
                    self.respond(400, {"error": "A valid season is required."})
                    return
                season = int(values[0])
                if not 2020 <= season <= datetime.now(timezone.utc).year:
                    self.respond(400, {"error": "Season must be between 2020 and the current year."})
                    return
                if url.path == "/playoffs":
                    weeks = parse_qs(url.query).get("week", [])
                    if len(weeks) != 1 or not weeks[0].isascii() or not weeks[0].isdigit() or not 1 <= int(weeks[0]) <= 18:
                        self.respond(400, {"error": "A valid week between 1 and 18 is required."})
                        return
                    jobs = parse_qs(url.query).get("job", [])
                    if len(jobs) > 1:
                        self.respond(400, {"error": "A valid job ID is required."})
                        return
                    try:
                        job = str(UUID(jobs[0])) if jobs else None
                    except ValueError:
                        self.respond(400, {"error": "A valid job ID is required."})
                        return
                    result = store.playoff_data(season, int(weeks[0]), job) if job else store.playoff_data(season, int(weeks[0]))
                else:
                    result = store.season_data(season)
            else:
                self.respond(404, {"error": "Not found."})
                return
            self.respond(200, result)
        except Exception:
            logging.exception("Could not serve engine request")
            self.respond(503, {"error": "NFL data is unavailable. Check engine logs and refresh status."})


def refresh_loop():
    while True:
        try:
            store.refresh()
            logging.info("NFL data refresh completed.")
        except Exception:
            logging.exception("NFL data refresh failed; existing data remains available.")
        threading.Event().wait(24 * 60 * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    threading.Thread(target=refresh_loop, daemon=True).start()
    port = int(os.environ.get("PORT", "8000"))
    ThreadingHTTPServer(("0.0.0.0", port), EngineHandler).serve_forever()
