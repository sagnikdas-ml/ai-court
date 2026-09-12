"""OpenRouter client for previewing a task plan from a project description."""
from __future__ import annotations

import json
import os
from typing import Any

import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"

TASK_PLAN_SCHEMA: dict[str, Any] = {
    "name": "research_task_plan",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "minItems": 2,
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "depends_on": {"type": "array", "items": {"type": "integer"}},
                    },
                    "required": ["title", "description", "depends_on"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["tasks"],
        "additionalProperties": False,
    },
}


class OpenRouterClient:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def task_plan(self, description: str) -> list[dict[str, Any]]:
        if not self.configured:
            raise RuntimeError("OpenRouter is not configured. Add OPENROUTER_API_KEY first.")
        prompt = (
            "Create a practical, ordered research project task plan from this description. "
            "Return 2 to 10 tasks. Use zero-based indexes in depends_on, and only refer "
            "to earlier tasks. Include hiring only if the description calls for it. "
            "Return only a JSON object in this exact shape, without Markdown: "
            '{"tasks":[{"title":"string","description":"string","depends_on":[0]}]}.\n\n'
            f"Project description:\n{description}"
        )
        supports_schema = self._supports_structured_outputs()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a precise research project planner. Return only the requested JSON."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        if supports_schema:
            payload["response_format"] = {"type": "json_schema", "json_schema": TASK_PLAN_SCHEMA}
            payload["provider"] = {"require_parameters": True}
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "Objection Research Operations",
            },
            json=payload,
            timeout=35,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        plan = json.loads(content)
        if not isinstance(plan.get("tasks"), list):
            raise RuntimeError("The model returned an invalid task plan.")
        for index, task in enumerate(plan["tasks"]):
            if not isinstance(task.get("title"), str) or not isinstance(task.get("description"), str):
                raise RuntimeError("The model returned a task without a title or description.")
            dependencies = task.get("depends_on")
            if not isinstance(dependencies, list) or any(not isinstance(value, int) or value < 0 or value >= index for value in dependencies):
                raise RuntimeError("The model returned invalid task dependencies.")
        return plan["tasks"]

    def _supports_structured_outputs(self) -> bool:
        """Ask OpenRouter which optional features the selected model exposes."""
        response = requests.get(
            f"https://openrouter.ai/api/v1/model/{self.model}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=15,
        )
        if not response.ok:
            return False
        return "structured_outputs" in response.json().get("data", {}).get("supported_parameters", [])
