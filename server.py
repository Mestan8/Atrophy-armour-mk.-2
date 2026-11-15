"""Local HTTP server: the pages in web/ plus the JSON API that feeds them."""

from collections.abc import Callable, Mapping
import errno
from functools import cache
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import socket
import sqlite3
from urllib.parse import parse_qsl, urlsplit

from plotly.offline import get_plotlyjs

from api import (
    build_health_view,
    build_library_view,
    build_measurements_view,
    build_scenario_controls_view,
    build_scenario_view,
    build_simulator_view,
)
from database import connect_database
from evidence_catalog import catalog, external_sources
from simulator_model import parameters as simulator_parameters
from study_library import DEFAULT_DATABASE_PATH, initialize_database


WEB_ROOT = Path(__file__).resolve().parent / "web"
PLOTLY_PATH = "/assets/vendor/plotly.min.js"

_LOGGER = logging.getLogger(__name__)

_Route = Callable[[sqlite3.Connection, Mapping[str, object]], dict[str, object]]

_GET_ROUTES: dict[str, _Route] = {
    "/api/health": build_health_view,
    "/api/scenario": build_scenario_view,
    "/api/scenario/controls": build_scenario_controls_view,
    "/api/library": build_library_view,
    "/api/measurements": build_measurements_view,
    "/api/simulator/soleus": build_simulator_view,
}


@cache
def _plotly_bundle() -> bytes:
    """Serve the plotly.js that ships with the installed Python package."""
    return get_plotlyjs().encode("utf-8")


class _Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".mjs": "text/javascript; charset=utf-8",
        ".json": "application/json",
        # The OS MIME registry (used on Windows) may not know these theme assets.
        ".woff2": "font/woff2",
        ".webp": "image/webp",
    }
    _cache_policy = "no-cache"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def do_GET(self) -> None:
        url = urlsplit(self.path)
        if url.path == PLOTLY_PATH:
            self._cache_policy = "max-age=3600"
            self._send(HTTPStatus.OK, _plotly_bundle(), "text/javascript; charset=utf-8")
        elif url.path.startswith("/api/"):
            self._dispatch(_GET_ROUTES.get(url.path), dict(parse_qsl(url.query)))
        else:
            super().do_GET()

    def _refuse_write(self) -> None:
        """The app is read-only: every write method is refused."""
        # Drain any body so the connection closes cleanly.
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            length = 0
        if 0 < length <= 1024 * 1024:
            self.rfile.read(length)
        self.close_connection = True
        body = json.dumps({"error": "This server is read-only."}).encode("utf-8")
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_POST = do_PUT = do_PATCH = do_DELETE = _refuse_write

    def _dispatch(self, route: _Route | None, data: Mapping[str, object]) -> None:
        if route is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        connection = self.server.open_connection()
        try:
            body = route(connection, data)
        except Exception:
            _LOGGER.exception("Request failed: %s", self.path)
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "The server could not complete this request."},
            )
        else:
            self._send_json(HTTPStatus.OK, body)
        finally:
            connection.close()

    def _send_json(self, status: HTTPStatus, body: Mapping[str, object]) -> None:
        self._send(status, json.dumps(body).encode("utf-8"), "application/json")

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", self._cache_policy)
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def list_directory(self, path) -> None:
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        _LOGGER.debug(format, *args)


# Windows error codes for "address already in use" and, with an exclusive bind,
# "access denied" (WSAEADDRINUSE, WSAEACCES).
_PORT_IN_USE_WINERRORS = {10048, 10013}


class PortInUseError(OSError):
    """The port is taken, most likely by another Atrophy Armour Mk. 2 server."""

    def __init__(self, port: int) -> None:
        super().__init__(
            errno.EADDRINUSE,
            f"Port {port} is already in use, probably by an older Atrophy Armour Mk. 2 "
            "server. Close that terminal/process or start with "
            f"--port {port + 1}.",
        )
        self.port = port


class AtrophyServer(ThreadingHTTPServer):
    daemon_threads = True
    # ThreadingHTTPServer sets allow_reuse_address. On Windows that becomes
    # SO_REUSEADDR, which lets a second process bind a port that is already
    # serving, so an old server can silently keep answering with old code.
    # Elsewhere SO_REUSEADDR only allows rebinding after TIME_WAIT, so it is kept.
    allow_reuse_address = os.name != "nt"

    def server_bind(self) -> None:
        if os.name == "nt" and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def __init__(
        self,
        address: tuple[str, int],
        database_path: str | Path,
    ) -> None:
        self.database_path = database_path
        # Fail at startup, not mid-request, if any evidence record lacks provenance.
        catalog()
        external_sources()
        simulator_parameters()
        initialize_database(database_path).close()
        try:
            super().__init__(address, _Handler)
        except OSError as error:
            in_use = error.errno == errno.EADDRINUSE or getattr(
                error, "winerror", None
            ) in _PORT_IN_USE_WINERRORS
            if in_use and address[1] != 0:
                raise PortInUseError(address[1]) from error
            raise

    def open_connection(self) -> sqlite3.Connection:
        connection = connect_database(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def create_server(
    host: str = "127.0.0.1",
    port: int = 8501,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> AtrophyServer:
    """Prepare the Study Library and bind the server; port 0 picks a free port."""
    return AtrophyServer((host, port), database_path)
