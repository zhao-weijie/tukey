"""CLI entry point for Tukey."""

import argparse
import threading
import webbrowser

import uvicorn

from tukey.server.app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Tukey — LLM comparison workbench")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--data-dir", default=None, help="Data directory (default: ~/.tukey)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser on startup")
    args = parser.parse_args()

    app = create_app(data_dir=args.data_dir)

    if not args.no_browser:
        url = f"http://localhost:{args.port}"
        # Delay slightly so server is ready before browser opens
        threading.Timer(1.5, webbrowser.open, args=[url]).start()

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
