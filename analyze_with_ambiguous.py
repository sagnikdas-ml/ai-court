import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://app.ambiguous.ai"

# You can keep using the same qbot API key you already used successfully.
API_KEY = os.getenv("AMBIGUOUS_API_KEY")

CHANNEL_ID = "e7f59238-5029-45d4-9ce5-cfb67f7aa3aa"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def fetch_messages():
    url = f"{BASE_URL}/api/channels/{CHANNEL_ID}/messages"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    messages = response.json()["data"]

    # Remove system messages like "X added qbot"
    messages = [
        msg
        for msg in messages
        if msg.get("author") is not None
    ]

    # API returned newest first in your test.
    messages.reverse()

    return messages


def build_transcript(messages):
    lines = []

    for msg in messages:
        content = msg["content"]

        # Ignore the initial "Welcome to..." message.
        if content.lower().startswith("welcome to"):
            continue

        name = msg["author"]["display_name"]

        lines.append(f"{name}: {content}")

    return "\n".join(lines)


def analyze_with_ambiguous(transcript):
    prompt = f"""
You are a workplace delegation-analysis agent.

Analyze this conversation between employees:

--- CONVERSATION ---

{transcript}

--- END CONVERSATION ---

Determine whether the employees are discussing a concrete task that
could reasonably be delegated to another worker.

Good delegation candidates include:
- repetitive model evaluation
- testing
- data collection
- data cleaning
- data labeling
- benchmark execution
- running predefined experiments
- repetitive hardware testing/integration
- QA
- documentation
- routine analysis

Do NOT flag something merely because employees are busy.

The task should be concrete enough that another person could reasonably
take ownership of it.

Return ONLY valid JSON with exactly these fields:

{{
    "opportunity_detected": true,
    "task": "",
    "reason": "",
    "delegation_score": 0.0,
    "complexity": "junior",
    "required_skills": [],
    "estimated_effort": "",
    "suggested_profile": ""
}}

Rules:

- delegation_score must be from 0 to 1
- complexity must be exactly one of:
  junior
  intermediate
  senior

- Do not make hiring decisions.
- Do not select or reject a person.
- Only assess the work opportunity.
"""

    payload = {
        "message": prompt,
        "context": {
            "audience": "agent"
        }
    }

    response = requests.post(
        f"{BASE_URL}/api/assistant/chat",
        headers=HEADERS,
        json=payload,
    )

    print("ASSISTANT STATUS:", response.status_code)

    if not response.ok:
        print(response.text)
        response.raise_for_status()

    return response.json()


if __name__ == "__main__":
    messages = fetch_messages()

    transcript = build_transcript(messages)

    print("\n======== TRANSCRIPT ========\n")
    print(transcript)

    print("\n======== ANALYSIS ========\n")

    result = analyze_with_ambiguous(transcript)

    print(json.dumps(result, indent=2))