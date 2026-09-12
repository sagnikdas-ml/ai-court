import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://app.ambiguous.ai"
API_KEY = os.getenv("AMBIGUOUS_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

RESEARCH_CHANNEL_ID = "e7f59238-5029-45d4-9ce5-cfb67f7aa3aa"


def post_to_chat(message):
    response = requests.post(
        f"{BASE_URL}/api/channels/{RESEARCH_CHANNEL_ID}/messages",
        headers=HEADERS,
        json={
            "content": message
        },
        timeout=30,
    )

    print(
        "POST TO AMBIGUOUS CHAT ->",
        response.status_code
    )

    response.raise_for_status()

    return response.json()


#==========suggestion text========

def build_suggestion_message(
    opportunity,
    candidate_matches,
    job_result,
    new_job=None,
):
    lines = []

    lines.append(
        "🤖 I found a potential delegation opportunity."
    )

    lines.append("")

    lines.append(
        f"Task: {opportunity.get('task')}"
    )

    lines.append(
        f"Estimated effort: "
        f"{opportunity.get('estimated_effort')}"
    )

    lines.append(
        f"Suggested level: "
        f"{opportunity.get('complexity')}"
    )

    lines.append("")

    lines.append(
        "Why I flagged this:"
    )

    lines.append(
        opportunity.get(
            "reason",
            ""
        )
    )

    lines.append("")

    # Candidate section
    if candidate_matches:

        lines.append(
            "Potential candidate matches:"
        )

        for candidate in candidate_matches[:3]:

            score = candidate.get(
                "match_score",
                0
            )

            lines.append("")

            lines.append(
                f"• {candidate.get('name')} "
                f"({score:.0%} match)"
            )

            matched_skills = candidate.get(
                "matched_skills",
                []
            )

            if matched_skills:
                lines.append(
                    "  Relevant skills: "
                    + ", ".join(
                        matched_skills
                    )
                )

            lines.append(
                "  Why this candidate matches: "
                + candidate.get(
                    "why_candidate_matches",
                    ""
                )
            )

    else:

        lines.append(
            "No sufficiently relevant candidate "
            "was found in the current candidate pool."
        )

    lines.append("")

    # Job section
    if job_result["job_exists"]:

        job = job_result["best_match"]

        lines.append(
            "✅ An existing job opening may already cover this work."
        )

        lines.append(
            f"Opening: {job.get('title')}"
        )

        lines.append(
            "Why it matches: "
            + job.get(
                "why_job_matches",
                ""
            )
        )

    else:

        lines.append(
            "⚠️ I could not find an existing job opening "
            "that appropriately matches this work."
        )

        lines.append("")

        lines.append(
            "Why a new opening may be needed:"
        )

        lines.append(
            job_result.get(
                "why_new_job_opening_needed",
                ""
            )
        )

        if new_job:

            lines.append("")

            lines.append(
                "Suggested new opening:"
            )

            lines.append(
                f"• {new_job.get('title')}"
            )

            lines.append(
                f"• Level: {new_job.get('level')}"
            )

            lines.append(
                "• Skills: "
                + ", ".join(
                    new_job.get(
                        "skills",
                        []
                    )
                )
            )

            lines.append("")

            lines.append(
                "Would you like me to send this suggestion "
                "to HR for review?"
            )

    lines.append("")

    lines.append(
        "This is a staffing suggestion for human review, "
        "not an automated hiring decision."
    )

    return "\n".join(lines)

# =========================================================
# AMBIGUOUS API
# =========================================================

def api_get(path, params=None):
    response = requests.get(
        f"{BASE_URL}{path}",
        headers=HEADERS,
        params=params,
        timeout=30,
    )

    print(f"GET {path} -> {response.status_code}")

    response.raise_for_status()
    return response.json()


def call_assistant(prompt):
    response = requests.post(
        f"{BASE_URL}/api/assistant/chat",
        headers=HEADERS,
        json={
            "message": prompt,
            "context": {
                "audience": "agent"
            }
        },
        timeout=60,
    )

    print(
        "Ambiguous Assistant ->",
        response.status_code
    )

    if not response.ok:
        print("\nAMBIGUOUS ERROR:")
        print(response.text)
        print()

        raise RuntimeError(
            f"Assistant request failed "
            f"with HTTP {response.status_code}"
        )

    payload = response.json()

    text = payload.get(
        "response",
        ""
    ).strip()

    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):
            lines = lines[:-1]

        text = "\n".join(
            lines
        ).strip()

    return json.loads(text)


# =========================================================
# SHEET HELPERS
# =========================================================

def list_sheets():
    result = api_get(
        "/api/sheets"
    )

    return result.get(
        "data",
        []
    )


def find_sheet_by_name(name):
    for sheet in list_sheets():

        sheet_name = (
            sheet.get("name")
            or sheet.get("title")
            or ""
        )

        if (
            sheet_name.strip().lower()
            == name.strip().lower()
        ):
            return sheet

    raise RuntimeError(
        f"Sheet not found: {name}"
    )


def read_sheet(sheet_id):
    return api_get(
        f"/api/sheets/{sheet_id}/range",
        params={
            "spec": "Sheet1!A1:Z100"
        },
    )


def extract_matrix(response):
    if isinstance(
        response.get("values"),
        list
    ):
        return response["values"]

    data = response.get(
        "data"
    )

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        if isinstance(
            data.get("values"),
            list
        ):
            return data["values"]

        if isinstance(
            data.get("rows"),
            list
        ):
            return data["rows"]

    if isinstance(
        response.get("rows"),
        list
    ):
        return response["rows"]

    raise RuntimeError(
        "Unexpected sheet response:\n"
        + json.dumps(
            response,
            indent=2
        )
    )


def matrix_to_records(matrix):
    if not matrix:
        return []

    headers = [
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        for value in matrix[0]
    ]

    records = []

    for row in matrix[1:]:

        if not any(
            str(value).strip()
            for value in row
        ):
            continue

        row = row + [""] * (
            len(headers) - len(row)
        )

        record = {}

        for index, header in enumerate(
            headers
        ):
            record[header] = row[index]

        records.append(
            record
        )

    return records


def load_candidates():
    sheet = find_sheet_by_name(
        "Candidate Pool"
    )

    response = read_sheet(
        sheet["id"]
    )

    return matrix_to_records(
        extract_matrix(
            response
        )
    )


def load_jobs():
    sheet = find_sheet_by_name(
        "job portal"
    )

    response = read_sheet(
        sheet["id"]
    )

    return matrix_to_records(
        extract_matrix(
            response
        )
    )


# =========================================================
# CANDIDATE MATCHING
# =========================================================

def _normalize_text(value):
    return str(value or "").strip().lower()


def _candidate_prefilter_score(candidate, opportunity):
    """
    Cheap local pre-filter to reduce 63 candidates
    to a small shortlist before sending anything to the LLM.
    """

    task_text = " ".join([
        _normalize_text(opportunity.get("task")),
        _normalize_text(opportunity.get("reason")),
        " ".join(
            _normalize_text(skill)
            for skill in opportunity.get("required_skills", [])
        ),
        _normalize_text(opportunity.get("suggested_profile")),
    ])

    candidate_text = " ".join([
        _normalize_text(candidate.get("skills")),
        _normalize_text(candidate.get("role")),
        _normalize_text(candidate.get("level")),
        _normalize_text(candidate.get("status")),
    ])

    score = 0

    # broad semantic-ish keyword families for local filtering only
    keyword_groups = [
        ["qa", "testing", "evaluation", "benchmark"],
        ["ml", "machine learning", "model"],
        ["data analysis", "analysis"],
        ["research"],
        ["documentation", "recording"],
        ["python"],
        ["hardware", "integration"],
        ["data collection"],
    ]

    for group in keyword_groups:
        task_has = any(word in task_text for word in group)
        candidate_has = any(word in candidate_text for word in group)

        if task_has and candidate_has:
            score += 2

    required_level = _normalize_text(
        opportunity.get("complexity")
    )

    candidate_level = _normalize_text(
        candidate.get("level")
    )

    if required_level == candidate_level:
        score += 3

    return score


def prefilter_candidates(
    opportunity,
    candidates,
    limit=12,
):
    scored = []

    for candidate in candidates:
        score = _candidate_prefilter_score(
            candidate,
            opportunity,
        )

        if score > 0:
            scored.append(
                (score, candidate)
            )

    scored.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return [
        candidate
        for _, candidate in scored[:limit]
    ]


def match_candidates(
    opportunity,
    candidates,
):
    shortlisted = prefilter_candidates(
        opportunity,
        candidates,
        limit=5,
    )

    print(
        f"Prefiltered {len(candidates)} candidates "
        f"down to {len(shortlisted)} candidates."
    )

    if not shortlisted:
        return []

    compact_candidates = []

    for candidate in shortlisted:
        compact_candidates.append({
            "candidate_id": candidate.get("candidate_id"),
            "name": candidate.get("name"),
            "level": candidate.get("level"),
            "skills": candidate.get("skills"),
            "years": candidate.get("years"),
            "role": candidate.get("role"),
            "status": candidate.get("status"),
        })

    prompt = f"""
You are evaluating existing candidate profiles against a newly discovered
work opportunity.

This is recommendation support only.
You are NOT making a hiring decision.

WORK OPPORTUNITY:

{json.dumps(opportunity, indent=2)}

CANDIDATES:

{json.dumps(compact_candidates, indent=2)}

Evaluate the candidates using only:
- professional skills
- technical experience
- experience level
- relevance to the actual task
- previous applicant or talent-pool status

Important:
- Do not match someone only because their experience level is appropriate.
- Their skills or professional background must actually relate to the work.
- Semantic skill matching is allowed.
- For example, "QA" may be relevant to "model evaluation or QA testing".
- Do not infer sensitive or protected characteristics.
- Do not hire or reject anyone.
- These are suggestions for human review only.

Return ONLY valid JSON in exactly this format:

{{
  "matches": [
    {{
      "candidate_id": "",
      "name": "",
      "match_score": 0.0,
      "matched_skills": [],
      "why_candidate_matches": ""
    }}
  ]
}}

Rules:

- match_score must be between 0 and 1
- include only candidates with match_score >= 0.50
- return at most 3 candidate matches

For why_candidate_matches, explain clearly:
1. which candidate skills or experience relate to the task
2. why their experience level is suitable
3. any meaningful limitation or partial mismatch

Keep each explanation concise.
"""

    print(
        "Candidate matching prompt length:",
        len(prompt)
    )

    result = call_assistant(
        prompt
    )

    matches = result.get(
        "matches",
        []
    )

    matches.sort(
        key=lambda item:
            item.get(
                "match_score",
                0
            ),
        reverse=True,
    )

    return matches[:3]

# =========================================================
# JOB MATCHING
# =========================================================

def check_existing_job(
    opportunity,
    jobs,
):
    open_jobs = []

    for job in jobs:
        status = str(
            job.get(
                "status",
                ""
            )
        ).strip().lower()

        if status in {
            "open",
            "active",
            "hiring",
        }:
            open_jobs.append(
                job
            )

    prompt = f"""
You are checking whether an existing open job
already covers a newly discovered work requirement.

WORK OPPORTUNITY:

{json.dumps(opportunity, indent=2)}

CURRENT OPEN JOBS:

{json.dumps(open_jobs, indent=2)}

Determine whether one of the open jobs is a
reasonable match for this work.

Evaluate:
- actual task type
- required skills
- seniority
- scope of responsibility

Important:
- Do not match a job only because it is in the same broad field.
- For example, a Senior ML Engineer role should NOT automatically
  match a junior repetitive model-evaluation task.
- A match must be genuinely suitable in both skills and level.

Return ONLY valid JSON:

{{
  "matching_job_exists": true,
  "best_match": {{
    "job_id": "",
    "title": "",
    "match_score": 0.0,
    "why_job_matches": ""
  }},
  "why_new_job_opening_needed": ""
}}

If there is NO suitable open job:

{{
  "matching_job_exists": false,
  "best_match": null,
  "why_new_job_opening_needed": ""
}}

Rules:

- match_score must be between 0 and 1
- consider a job a match only if match_score >= 0.65
- why_new_job_opening_needed must clearly explain:
  1. why the existing open jobs do not fit
  2. what gap exists in skills or seniority
  3. why creating a new opening is appropriate
"""

    result = call_assistant(
        prompt
    )

    best_match = result.get(
        "best_match"
    )

    if (
        result.get(
            "matching_job_exists"
        )
        and best_match
        and float(
            best_match.get(
                "match_score",
                0
            )
        ) >= 0.65
    ):
        return {
            "job_exists": True,
            "best_match": best_match,
            "why_new_job_opening_needed": ""
        }

    return {
        "job_exists": False,
        "best_match": None,
        "why_new_job_opening_needed":
            result.get(
                "why_new_job_opening_needed",
                ""
            ),
    }


# =========================================================
# SIMULATED JOB CREATION
# =========================================================

def create_job_suggestion(
    opportunity
):
    task = str(
        opportunity.get(
            "task",
            ""
        )
    ).lower()

    level = str(
        opportunity.get(
            "complexity",
            "junior"
        )
    ).title()

    if (
        "evaluation" in task
        or "benchmark" in task
        or "model" in task
    ):
        title = (
            f"{level} "
            "ML Evaluation Assistant"
        )

    elif "data" in task:
        title = (
            f"{level} "
            "Data Research Assistant"
        )

    elif "hardware" in task:
        title = (
            f"{level} "
            "Hardware Integration Assistant"
        )

    else:
        title = (
            f"{level} "
            "Research Support Assistant"
        )

    return {
        "created": True,
        "title": title,
        "level": opportunity.get(
            "complexity"
        ),
        "skills": opportunity.get(
            "required_skills",
            []
        ),
        "estimated_effort":
            opportunity.get(
                "estimated_effort"
            ),
    }


# =========================================================
# FULL PROCESS
# =========================================================

def process_opportunity(opportunity):
    print("\n")
    print("=" * 70)
    print("PROCESSING OPPORTUNITY")
    print("=" * 70)

    print("Task:", opportunity.get("task"))
    print("Complexity:", opportunity.get("complexity"))
    print("Skills:", opportunity.get("required_skills"))

    # -----------------------------------------------------
    # Candidates
    # -----------------------------------------------------

    print("\nLoading candidate pool...")

    candidates = load_candidates()

    print(f"Loaded {len(candidates)} candidates.")

    print("\nMatching candidates...")

    candidate_matches = match_candidates(
        opportunity,
        candidates,
    )

    print("\n")
    print("=" * 70)
    print("CANDIDATE MATCHES")
    print("=" * 70)

    if not candidate_matches:
        print("No sufficiently relevant candidate found.")

    for candidate in candidate_matches:
        print("\nName:")
        print(candidate.get("name"))

        print("\nMatch score:")
        print(candidate.get("match_score"))

        print("\nMatched skills:")
        print(candidate.get("matched_skills"))

        print("\nWHY THIS CANDIDATE MATCHES:")
        print(candidate.get("why_candidate_matches"))

        print("\n------------------------------")

    # -----------------------------------------------------
    # Jobs
    # -----------------------------------------------------

    print("\nLoading job portal...")

    jobs = load_jobs()

    print(f"Loaded {len(jobs)} jobs.")

    print("\nChecking existing open jobs...")

    job_result = check_existing_job(
        opportunity,
        jobs,
    )

    # -----------------------------------------------------
    # Existing job
    # -----------------------------------------------------

    if job_result["job_exists"]:
        job = job_result["best_match"]

        print("\n")
        print("=" * 70)
        print("MATCHING JOB ALREADY EXISTS")
        print("=" * 70)

        print("Title:", job.get("title"))
        print("Score:", job.get("match_score"))

        print("\nWHY THIS JOB MATCHES:")
        print(job.get("why_job_matches"))

        message = build_suggestion_message(
            opportunity=opportunity,
            candidate_matches=candidate_matches,
            job_result=job_result,
        )

        post_to_chat(message)

        return {
            "job_exists": True,
            "job_created": False,
            "matching_job": job,
            "candidate_matches": candidate_matches,
        }

    # -----------------------------------------------------
    # New job needed
    # -----------------------------------------------------

    print("\n")
    print("=" * 70)
    print("NO MATCHING JOB EXISTS")
    print("=" * 70)

    print("\nWHY A NEW JOB OPENING IS NEEDED:")
    print(
        job_result[
            "why_new_job_opening_needed"
        ]
    )

    new_job = create_job_suggestion(
        opportunity
    )

    print("\n")
    print("=" * 70)
    print("JOB OPENING CREATED")
    print("=" * 70)

    print("Title:", new_job["title"])
    print("Level:", new_job["level"])

    print(
        "Skills:",
        ", ".join(
            new_job["skills"]
        )
    )

    print(
        "Estimated effort:",
        new_job["estimated_effort"]
    )

    message = build_suggestion_message(
        opportunity=opportunity,
        candidate_matches=candidate_matches,
        job_result=job_result,
        new_job=new_job,
    )

    post_to_chat(message)

    return {
        "job_exists": False,
        "job_created": True,
        "why_new_job_opening_needed":
            job_result[
                "why_new_job_opening_needed"
            ],
        "created_job": new_job,
        "candidate_matches": candidate_matches,
    }


# =========================================================
# TEST USING YOUR CURRENT ANALYSIS OUTPUT
# =========================================================

if __name__ == "__main__":

    opportunity = {
        "opportunity_detected": True,

        "task": (
            "Run the documented model evaluation "
            "across all configurations on the "
            "1,500-sample benchmark and record "
            "the results."
        ),

        "reason": (
            "This is a concrete, repetitive testing "
            "task with a documented procedure and "
            "clear deliverable, so another worker "
            "could reasonably take ownership of it."
        ),

        "delegation_score": 0.93,

        "complexity": "junior",

        "required_skills": [
            "following documented procedures",
            "model evaluation or QA testing",
            "result recording and organization",
            "attention to detail",
        ],

        "estimated_effort":
            "2 days",

        "suggested_profile": (
            "A detail-oriented QA or ML evaluation "
            "support worker who can follow a "
            "predefined testing workflow and log "
            "results accurately."
        ),
    }

    final_result = (
        process_opportunity(
            opportunity
        )
    )

    print("\n")
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(
        json.dumps(
            final_result,
            indent=2,
            ensure_ascii=False,
        )
    )

    response = requests.post(
    f"{BASE_URL}/api/assistant/chat",
    headers=HEADERS,
    json={
        "message": "Say hello",
        "context": {
            "audience": "agent"
        }
    },
    timeout=60,
)

payload = response.json()

print(json.dumps(payload, indent=2))