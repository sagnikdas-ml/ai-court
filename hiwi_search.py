"""Search the public web for potential HiWi candidates using Exa."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

EXA_SEARCH_URL = "https://api.exa.ai/search"
DEFAULT_RESULT_COUNT = 10
DEFAULT_CANDIDATE_COUNT = 5
DEFAULT_TIMEOUT_SECONDS = 30

_CANDIDATE_FIELDS = (
    "name", "profile_url", "current_role", "affiliation", "location",
    "skills", "research_topics", "evidence", "source_url", "match_rationale",
)


class HiWiSearchError(RuntimeError):
    """Raised when a HiWi candidate search cannot be completed."""


def _load_api_key(config_path: str | os.PathLike[str] = ".exa") -> str:
    """Load EXA_API_KEY from the environment or a local .exa file."""
    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if api_key:
        return api_key
    path = Path(config_path)
    if not path.is_file():
        raise HiWiSearchError(
            f"Exa API key not found. Set EXA_API_KEY or create {path} "
            "with EXA_API_KEY=<your-key>."
        )
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "EXA_API_KEY" and value.strip().strip("\"'"):
            return value.strip().strip("\"'")
    raise HiWiSearchError(f"EXA_API_KEY is missing or empty in {path}.")


def _search_payload(position_name: str, result_count: int) -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Candidate's full name."},
            "current_role": {"type": "string", "description": "Current role or degree."},
            "affiliation": {"type": "string", "description": "University, lab, or employer."},
            "location": {"type": "string", "description": "Publicly stated location."},
            "skills": {"type": "array", "items": {"type": "string"}},
            "research_topics": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "string", "description": "Short evidence from the source."},
            "match_rationale": {"type": "string", "description": "Why the source matches the requested role."},
        },
        "required": ["name", "evidence", "match_rationale"],
    }
    return {
        "query": (
            f"Potential candidates for a HiWi student research assistant position in {position_name}. "
            "Find public profiles or pages for people whose education, research, projects, or skills "
            "match this role. Include LinkedIn, university, laboratory, ORCID, and personal research pages."
        ),
        "type": "auto",
        "numResults": result_count,
        "additionalQueries": [
            f"site:linkedin.com/in {position_name} student researcher",
            f"site:*.edu {position_name} student researcher",
            f"site:orcid.org {position_name} researcher",
        ],
        "contents": {
            "summary": {"query": f"Candidate details and evidence relevant to {position_name}", "schema": schema},
            "highlights": {"query": f"Evidence of fit for {position_name}", "maxCharacters": 500},
        },
        "systemPrompt": (
            "Return individual people who may be suitable candidates. Prefer public academic or professional "
            "profiles. Do not infer private contact information. Avoid duplicate people and clearly mark unknowns."
        ),
    }


def _request_exa(api_key: str, payload: Mapping[str, Any], timeout: int) -> dict[str, Any]:
    request = Request(
        EXA_SEARCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": api_key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS endpoint
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HiWiSearchError(f"Exa API returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise HiWiSearchError(f"Could not reach Exa API: {exc.reason}") from exc
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HiWiSearchError("Exa API returned invalid JSON.") from exc
    if not isinstance(decoded, dict):
        raise HiWiSearchError("Exa API returned an unexpected response shape.")
    if decoded.get("error"):
        raise HiWiSearchError(f"Exa API error: {decoded['error']}")
    return decoded


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "; ".join(text for item in value if (text := _as_text(item)))
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()


def _summary(result: Mapping[str, Any]) -> dict[str, Any]:
    summary = result.get("summary")
    if isinstance(summary, dict):
        return dict(summary)
    if isinstance(summary, str):
        try:
            decoded = json.loads(summary)
            if isinstance(decoded, dict):
                return decoded
        except json.JSONDecodeError:
            return {"evidence": summary}
    return {}


def _candidate_from_result(result: Mapping[str, Any]) -> dict[str, Any] | None:
    summary = _summary(result)
    name = _as_text(summary.get("name") or result.get("author"))
    source_url = _as_text(result.get("url"))
    if not name or not source_url:
        return None
    candidate = {
        "name": name,
        "profile_url": _as_text(summary.get("profile_url")) or source_url,
        "current_role": _as_text(summary.get("current_role")),
        "affiliation": _as_text(summary.get("affiliation")),
        "location": _as_text(summary.get("location")),
        "skills": summary.get("skills") if isinstance(summary.get("skills"), list) else [],
        "research_topics": summary.get("research_topics") if isinstance(summary.get("research_topics"), list) else [],
        "evidence": _as_text(summary.get("evidence") or result.get("highlights")),
        "source_url": source_url,
        "match_rationale": _as_text(summary.get("match_rationale")),
    }
    return {field: candidate[field] for field in _CANDIDATE_FIELDS}


def _extract_candidates(response: Mapping[str, Any], limit: int) -> list[dict[str, Any]]:
    results = response.get("results", [])
    if not isinstance(results, list):
        raise HiWiSearchError("Exa response did not contain a results list.")
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    seen_names: set[str] = set()
    for result in results:
        if not isinstance(result, dict):
            continue
        candidate = _candidate_from_result(result)
        if not candidate:
            continue
        url_key = candidate["source_url"].lower().rstrip("/")
        name_key = candidate["name"].casefold()
        if url_key in seen_urls or name_key in seen_names:
            continue
        seen_urls.add(url_key)
        seen_names.add(name_key)
        candidates.append(candidate)
        if len(candidates) == limit:
            break
    return candidates


def find_hiwi_candidates(
    position_name: str,
    *,
    limit: int = DEFAULT_CANDIDATE_COUNT,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    config_path: str | os.PathLike[str] = ".exa",
) -> dict[str, Any]:
    """Find public-web leads for a HiWi role and return JSON-compatible data."""
    position_name = position_name.strip()
    if not position_name:
        raise ValueError("position_name must not be empty.")
    if not 1 <= limit <= 25:
        raise ValueError("limit must be between 1 and 25.")
    if timeout <= 0:
        raise ValueError("timeout must be positive.")
    response = _request_exa(
        _load_api_key(config_path),
        _search_payload(position_name, max(DEFAULT_RESULT_COUNT, limit * 2)),
        timeout,
    )
    return {"position_name": position_name, "candidates": _extract_candidates(response, limit)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find public-web candidates for a HiWi position.")
    parser.add_argument("position_name", help="Role name, for example 'Computer Vision HiWi'")
    parser.add_argument("--limit", type=int, default=DEFAULT_CANDIDATE_COUNT)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(find_hiwi_candidates(args.position_name, limit=args.limit), indent=2, ensure_ascii=False))
    except (HiWiSearchError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
