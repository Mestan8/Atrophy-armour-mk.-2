import http.client
import json
from pathlib import Path
import subprocess
import sys
import threading
from typing import Generator

import pytest

from server import AtrophyServer, create_server


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def server(tmp_path: Path) -> Generator[AtrophyServer, None, None]:
    running = create_server(port=0, database_path=tmp_path / "library.sqlite3")
    thread = threading.Thread(target=running.serve_forever, daemon=True)
    thread.start()
    yield running
    running.shutdown()
    running.server_close()
    thread.join(timeout=5)


def request(
    server: AtrophyServer,
    method: str,
    path: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], bytes]:
    connection = http.client.HTTPConnection(*server.server_address[:2], timeout=30)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        headers = {key.lower(): value for key, value in response.getheaders()}
        return response.status, headers, response.read()
    finally:
        connection.close()


def post_json(
    server: AtrophyServer, path: str, data: dict[str, object]
) -> tuple[int, dict[str, object]]:
    status, _, body = request(
        server,
        "POST",
        path,
        json.dumps(data).encode("utf-8"),
        {"Content-Type": "application/json"},
    )
    return status, json.loads(body)


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/", "text/html"),
        ("/index.html", "text/html"),
        ("/library.html", "text/html"),
        ("/measurements.html", "text/html"),
        ("/assets/css/site.css", "text/css"),
        ("/assets/js/explorer.js", "text/javascript"),
        ("/simulator.html", "text/html"),
        ("/assets/css/simulator.css", "text/css"),
        ("/assets/js/simulator.js", "text/javascript"),
        ("/assets/js/sim/scene.js", "text/javascript"),
        ("/assets/vendor/three/three.module.js", "text/javascript"),
        ("/assets/vendor/three/three.core.js", "text/javascript"),
        ("/assets/vendor/three/OrbitControls.js", "text/javascript"),
    ],
)
def test_pages_and_assets_are_served(
    server: AtrophyServer, path: str, content_type: str
) -> None:
    status, headers, body = request(server, "GET", path)

    assert status == 200
    assert headers["content-type"].startswith(content_type)
    assert body


def test_pages_have_no_web_fonts_or_animation_scripts() -> None:
    for page in ("index.html", "library.html", "measurements.html", "simulator.html"):
        html = (PROJECT_ROOT / "web" / page).read_text(encoding="utf-8")
        assert "fonts.googleapis" not in html
        assert "motion-boot" not in html and "reveal.js" not in html
    css = (PROJECT_ROOT / "web" / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    assert "@keyframes" not in css and "transition" not in css and "animation" not in css


def test_plotly_is_served_locally(server: AtrophyServer) -> None:
    status, headers, body = request(server, "GET", "/assets/vendor/plotly.min.js")

    assert status == 200
    assert headers["content-type"].startswith("text/javascript")
    assert len(body) > 1_000_000


@pytest.mark.parametrize(
    "path",
    [
        "/app.py",
        "/data/study_library.sqlite3",
        "/.git/config",
        "/../app.py",
        "/assets/../../app.py",
        "/%2e%2e/app.py",
        "/assets/",
        "/api/unknown",
    ],
)
def test_project_files_and_unknown_paths_are_not_exposed(
    server: AtrophyServer, path: str
) -> None:
    status, _, body = request(server, "GET", path)

    assert status == 404
    assert b"import" not in body


def test_startup_loads_the_catalog_and_api_returns_results(
    server: AtrophyServer,
) -> None:
    status, _, body = request(
        server,
        "GET",
        "/api/scenario?study=fitts-2010&category=fibre&region=calf_ankle",
    )
    view = json.loads(body)

    assert status == 200
    titles = [row["title"] for row in view["rows"]]
    assert "Fitts et al. (2010) · Soleus type I fibre peak isometric force" in titles
    row = view["rows"][titles.index("Fitts et al. (2010) · Soleus type I fibre peak isometric force")]
    assert row["metrics"][0]["text"] == "-34.9%"
    assert row["metrics"][0]["tag"] == "calculated"


@pytest.mark.parametrize("path", ["/api/library", "/api/measurements?study=greene-2021"])
def test_other_pages_return_data(server: AtrophyServer, path: str) -> None:
    status, _, body = request(server, "GET", path)
    assert status == 200
    assert json.loads(body)


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/api/measurements", b'{"study_id": "scott-2023"}'),
        ("POST", "/api/measurements/verify", b'{"record_id": 1}'),
        ("POST", "/api/scenario", b"{}"),
        ("POST", "/", None),
        ("PUT", "/api/measurements", b"{}"),
        ("DELETE", "/api/measurements", None),
    ],
)
def test_the_server_is_read_only(
    server: AtrophyServer, method: str, path: str, body: bytes | None
) -> None:
    headers = {"Content-Type": "application/json"} if body else {}
    status, response_headers, _ = request(server, method, path, body, headers)

    assert status == 405
    assert response_headers["allow"] == "GET, HEAD"


def test_controls_endpoint_returns_control_state_only(server: AtrophyServer) -> None:
    status, _, body = request(server, "GET", "/api/scenario/controls?study=greene-2021")
    view = json.loads(body)

    assert status == 200
    assert set(view) == {"notice", "controls"}
    assert view["controls"][0]["value"] == "greene-2021"


def test_concurrent_requests_succeed(server: AtrophyServer) -> None:
    statuses: list[int] = []

    def fetch() -> None:
        statuses.append(request(server, "GET", "/api/scenario")[0])

    threads = [threading.Thread(target=fetch) for _ in range(12)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert statuses == [200] * 12


def test_application_does_not_require_streamlit() -> None:
    script = (
        "import sys; sys.modules['streamlit'] = None; "
        "import app, server, api; print('imported')"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert completed.returncode == 0, completed.stderr
    assert "imported" in completed.stdout


def test_requirements_no_longer_list_streamlit() -> None:
    requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "streamlit" not in requirements.lower()


def test_a_second_server_on_an_occupied_port_is_refused(server: AtrophyServer) -> None:
    from server import PortInUseError

    port = server.server_address[1]
    with pytest.raises(PortInUseError) as raised:
        create_server(port=port, database_path=":memory:")

    assert raised.value.port == port
    assert f"Port {port} is already in use" in raised.value.strerror
    assert f"--port {port + 1}" in raised.value.strerror


def test_app_reports_a_busy_port_and_exits_non_zero(
    server: AtrophyServer, capsys: pytest.CaptureFixture[str]
) -> None:
    import app

    port = server.server_address[1]
    assert app.main(["--no-browser", "--port", str(port)]) == 1
    message = capsys.readouterr().err
    assert f"Port {port} is already in use, probably by an older Atrophy Armour server" in message


def test_controls_load_first_without_any_results_request(tmp_path: Path) -> None:
    fresh = create_server(port=0, database_path=tmp_path / "first.sqlite3")
    thread = threading.Thread(target=fresh.serve_forever, daemon=True)
    thread.start()
    try:
        status, headers, body = request(fresh, "GET", "/api/scenario/controls")
        view = json.loads(body)
        assert status == 200
        assert headers["content-type"] == "application/json"
        assert [control["id"] for control in view["controls"]] == [
            "study", "category", "region", "countermeasure", "subgroup", "recovery",
        ]
        assert all(control["options"] for control in view["controls"])
    finally:
        fresh.shutdown()
        fresh.server_close()
        thread.join(timeout=5)


def test_health_reports_the_api_version_the_page_expects(server: AtrophyServer) -> None:
    import re

    from api import API_VERSION

    status, _, body = request(server, "GET", "/api/health")
    assert status == 200
    assert json.loads(body) == {"status": "ok", "api_version": API_VERSION}
    script = (PROJECT_ROOT / "web" / "assets" / "js" / "explorer.js").read_text(encoding="utf-8")
    assert re.search(r"const API_VERSION='([^']+)'", script).group(1) == API_VERSION


def test_simulator_endpoint_returns_values_with_provenance(server: AtrophyServer) -> None:
    from api import API_VERSION

    status, headers, body = request(server, "GET", "/api/simulator/soleus?day=177&cohort=all")
    assert status == 200
    assert headers["content-type"].startswith("application/json")
    view = json.loads(body)
    assert view["api_version"] == API_VERSION
    volume = next(p for p in view["parameters"] if p["id"] == "soleus_volume")
    assert volume["value"] == 383 and volume["value_type"] == "reported"
    assert volume["end"]["source"] == "Trappe et al. (2009)"

    status, _, body = request(server, "GET", "/api/simulator/soleus?day=999&cohort=nobody&shape=x")
    view = json.loads(body)
    assert status == 200
    assert view["day"]["clamped"] is True and view["day"]["value"] == 177
    assert view["cohort"]["id"] == "all"


def test_simulator_page_and_endpoint_are_get_only(server: AtrophyServer) -> None:
    status, _ = post_json(server, "/api/simulator/soleus", {"day": 10})
    assert status == 405


def test_simulator_page_expects_the_same_api_version() -> None:
    import re

    from api import API_VERSION

    script = (PROJECT_ROOT / "web" / "assets" / "js" / "simulator.js").read_text(encoding="utf-8")
    assert re.search(r"const API_VERSION='([^']+)'", script).group(1) == API_VERSION


def test_three_js_is_vendored_locally_and_pinned() -> None:
    vendor = PROJECT_ROOT / "web" / "assets" / "vendor" / "three"
    module = (vendor / "three.module.js").read_text(encoding="utf-8")
    assert "SPDX-License-Identifier: MIT" in module[:300]
    assert (vendor / "LICENSE").exists()
    page = (PROJECT_ROOT / "web" / "simulator.html").read_text(encoding="utf-8")
    assert "cdn" not in page.lower().replace("no cdn", "").replace("from a cdn", "")
    assert "./assets/vendor/three/three.module.js" in page
