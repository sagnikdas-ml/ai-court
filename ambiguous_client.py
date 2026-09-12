"""Small, opt-in client for the Ambiguous workspace REST API.

No network request is made unless a user explicitly asks to sync and has provided
AMBIGUOUS_API_KEY in Streamlit secrets or the process environment.
"""
from __future__ import annotations

import os
from typing import Any

import requests

BASE_URL = os.getenv("AMBIGUOUS_API_URL", "https://app.ambiguous.ai").rstrip("/")


class AmbiguousClient:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("AMBIGUOUS_API_KEY")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        if not self.configured:
            raise RuntimeError("Ambiguous AI is not configured. Add AMBIGUOUS_API_KEY first.")
        response = requests.request(
            method,
            f"{BASE_URL}/api{path}",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        return response.json() if response.content else {}

    def list_tasks(self) -> Any:
        return self._request("GET", "/tasks")

    def create_task(self, title: str, details: str, status: str = "todo") -> Any:
        # Confirm task field names against your workspace's OpenAPI reference before production use.
        return self._request("POST", "/tasks", {"title": title, "details": details, "status": status})
