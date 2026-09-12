"""MCP entry point for the FindPeople candidate search agent."""

from __future__ import annotations

import argparse
from typing import Any

from candidate_search import CandidateSearchError, find_candidates

MAX_CANDIDATES = 5


def run_candidate_search(
    role: str,
    *,
    limit: int = MAX_CANDIDATES,
    exa_config_path: str = ".exa",
) -> dict[str, Any]:
    """Return up to five candidates for the requested role."""
    if not 1 <= limit <= MAX_CANDIDATES:
        raise ValueError(f"limit must be between 1 and {MAX_CANDIDATES}.")

    result = find_candidates(role, limit=limit, config_path=exa_config_path)
    for index, candidate in enumerate(result["candidates"], start=1):
        candidate["candidate_number"] = index
    return result


def create_mcp_server(*, host: str = "127.0.0.1", port: int = 8000):
    """Build the MCP server used by an Ambiguous coworker."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install dependencies with `python3 -m pip install -r requirements.txt`.") from exc

    server = FastMCP("FindPeople", host=host, port=port)

    @server.tool()
    def search_candidates(role: str) -> dict[str, Any]:
        """Find up to five public-web candidates for a job role."""
        try:
            return run_candidate_search(role)
        except (CandidateSearchError, ValueError) as exc:
            raise RuntimeError(str(exc)) from exc

    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the FindPeople MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport to serve (default: stdio).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind host.")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port.")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    create_mcp_server(host=args.host, port=args.port).run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
