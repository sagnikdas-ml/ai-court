"""Ambiguous workspace integration for the HiWi candidate search agent.

The MCP tool searches Exa, creates a structured Ambiguous Sheet, and posts a
summary to an Ambiguous Chat channel.
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from hiwi_search import HiWiSearchError, find_hiwi_candidates

DEFAULT_AMBIGUOUS_API_URL = "https://app.ambiguous.ai/api"
MAX_CANDIDATES = 5
SHEET_COLUMNS = [
    "Name",
    "Profile URL",
    "Current Role",
    "Affiliation",
    "Location",
    "Skills",
    "Research Topics",
    "Evidence",
    "Source URL",
    "Match Rationale",
]


class AmbiguousIntegrationError(RuntimeError):
    """Raised when an Ambiguous workspace operation fails."""


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise AmbiguousIntegrationError(f"Missing required environment variable: {name}")
    return value


def _cell_name(row: int, column: int) -> str:
    letters = ""
    while column:
        column, remainder = divmod(column - 1, 26)
        letters = chr(65 + remainder) + letters
    return f"{letters}{row}"


def _candidate_rows(candidates: list[Mapping[str, Any]]) -> list[list[str]]:
    rows = [SHEET_COLUMNS]
    for candidate in candidates:
        rows.append([
            str(candidate.get("name", "")),
            str(candidate.get("profile_url", "")),
            str(candidate.get("current_role", "")),
            str(candidate.get("affiliation", "")),
            str(candidate.get("location", "")),
            "; ".join(str(value) for value in candidate.get("skills", [])),
            "; ".join(str(value) for value in candidate.get("research_topics", [])),
            str(candidate.get("evidence", "")),
            str(candidate.get("source_url", "")),
            str(candidate.get("match_rationale", "")),
        ])
    return rows


class AmbiguousClient:
    """Small REST client for the Ambiguous Sheet and Chat APIs."""

    def __init__(self, api_key: str, *, base_url: str = DEFAULT_AMBIGUOUS_API_URL, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.base_url}/{path.lstrip('/')}",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:  # noqa: S310 - configured HTTPS API
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise AmbiguousIntegrationError(
                f"Ambiguous API returned HTTP {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise AmbiguousIntegrationError(f"Could not reach Ambiguous API: {exc.reason}") from exc
        try:
            result = json.loads(body) if body else {}
        except json.JSONDecodeError as exc:
            raise AmbiguousIntegrationError("Ambiguous API returned invalid JSON.") from exc
        if not isinstance(result, dict):
            raise AmbiguousIntegrationError("Ambiguous API returned an unexpected response shape.")
        return result

    def create_sheet(self, title: str) -> dict[str, Any]:
        return self._request("POST", "/sheets", {"title": title})

    def write_sheet(self, sheet_id: str, rows: list[list[str]]) -> dict[str, Any]:
        updates = [
            {"cell": _cell_name(row_index, column_index), "value": value}
            for row_index, row in enumerate(rows, start=1)
            for column_index, value in enumerate(row, start=1)
        ]
        return self._request("PATCH", f"/sheets/{sheet_id}/cells", {"updates": updates})

    def send_chat_message(self, channel_id: str, body: str) -> dict[str, Any]:
        return self._request("POST", f"/channels/{channel_id}/messages", {"body": body})


def _sheet_id(sheet: Mapping[str, Any]) -> str:
    value = sheet.get("id") or sheet.get("sheet_id")
    if not value:
        raise AmbiguousIntegrationError("Ambiguous did not return a Sheet ID.")
    return str(value)


def _sheet_url(sheet: Mapping[str, Any], sheet_id: str) -> str:
    return str(sheet.get("url") or f"https://app.ambiguous.ai/sheets/{sheet_id}")


def _summary_message(position_name: str, result_count: int, sheet_url: str) -> str:
    return (
        f"**HiWi candidate search completed**\n"
        f"Role: `{position_name}`\n"
        f"Candidates found: {result_count}\n"
        f"Results Sheet: {sheet_url}\n\n"
        "These are public-web leads and require human review before outreach."
    )


def run_hiwi_search_in_ambiguous(
    position_name: str,
    *,
    limit: int = MAX_CANDIDATES,
    exa_config_path: str = ".exa",
    ambiguous_api_key: str | None = None,
    ambiguous_api_url: str | None = None,
    chat_channel_id: str | None = None,
) -> dict[str, Any]:
    """Search Exa and persist the result in an Ambiguous Sheet and Chat."""
    if not 1 <= limit <= MAX_CANDIDATES:
        raise ValueError(f"limit must be between 1 and {MAX_CANDIDATES}.")
    result = find_hiwi_candidates(position_name, limit=limit, config_path=exa_config_path)
    client = AmbiguousClient(
        ambiguous_api_key or _required_env("AMBIGUOUS_API_KEY"),
        base_url=ambiguous_api_url or os.environ.get("AMBIGUOUS_API_URL", DEFAULT_AMBIGUOUS_API_URL),
    )
    sheet = client.create_sheet(f"HiWi candidates - {result['position_name']}")
    sheet_id = _sheet_id(sheet)
    client.write_sheet(sheet_id, _candidate_rows(result["candidates"]))
    channel_id = chat_channel_id or _required_env("AMBIGUOUS_CHAT_CHANNEL_ID")
    sheet_url = _sheet_url(sheet, sheet_id)
    chat = client.send_chat_message(
        channel_id,
        _summary_message(result["position_name"], len(result["candidates"]), sheet_url),
    )
    return {
        **result,
        "sheet_id": sheet_id,
        "sheet_url": sheet_url,
        "chat_message": chat,
    }


def create_mcp_server():
    """Build the MCP server that exposes the Ambiguous workspace tool."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install dependencies with `python3 -m pip install -r requirements.txt`.") from exc

    server = FastMCP("HiWi Search Agent")

    @server.tool()
    def search_hiwi_candidates(position_name: str) -> dict[str, Any]:
        """Find up to five HiWi candidates and save the results in Ambiguous."""
        try:
            return run_hiwi_search_in_ambiguous(position_name)
        except (HiWiSearchError, AmbiguousIntegrationError, ValueError) as exc:
            raise RuntimeError(str(exc)) from exc

    return server


if __name__ == "__main__":
    create_mcp_server().run(transport="stdio")
