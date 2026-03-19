"""CLI entry point: `uv run tukey` or `python -m tukey`."""

import uvicorn

from tukey.server.app import create_app


def main() -> None:
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
