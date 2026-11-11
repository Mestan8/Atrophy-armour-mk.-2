"""Start Atrophy Armour and open it in the default browser."""

import argparse
import sys
import webbrowser

from server import PortInUseError, create_server


def main(arguments: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Atrophy Armour locally.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="do not open a browser window",
    )
    options = parser.parse_args(arguments)

    try:
        server = create_server(options.host, options.port)
    except PortInUseError as error:
        print(error.strerror, file=sys.stderr)
        return 1
    except OSError as error:
        print(f"Could not start on port {options.port}: {error}", file=sys.stderr)
        return 1

    url = f"http://{options.host}:{server.server_address[1]}/"
    print(f"Atrophy Armour is running at {url} (press Ctrl+C to stop)", flush=True)
    if not options.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
