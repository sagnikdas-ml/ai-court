# Apex AI

**Apex AI is an AI-powered workforce delegation and hiring assistant built on Ambiguous.**

It observes workplace conversations, detects work that can be delegated, identifies suitable candidates from an existing talent pool, checks whether an appropriate job opening already exists, and surfaces the recommendation to HR for review.

The project combines conversational AI, live workplace events, candidate matching, job-gap detection, Ambiguous Sheets, and an HR dashboard into one workflow.

---

## The Problem

Teams often discover staffing needs informally during everyday conversations.

For example:

> "We still haven't tested the model against those 1,500 evaluation samples."

> "Someone needs to run every configuration and record the results."

> "That will probably take two days. The procedure is already documented."

Normally, this information stays buried in chat.

A manager must manually:

1. recognize that the work can be delegated,
2. determine what skills are required,
3. search previous applicants or the talent pool,
4. check whether an appropriate job opening already exists,
5. contact HR,
6. review candidates,
7. track the final staffing decision.

Apex AI turns this into an AI-assisted workflow.

---

# How Apex AI Works

```text
Employee conversation
        ↓
Ambiguous Chat
        ↓
Apex AI analyzes recent conversation
        ↓
Delegation opportunity detected?
        ↓
Extract task requirements
        ↓
Search Candidate Pool
        ↓
AI candidate matching
        ↓
Check existing Job Portal
        ↓
┌─────────────────────┬─────────────────────┐
│ Matching job exists │ No matching job     │
│                     │                     │
│ Recommend opening   │ Suggest new opening │
└─────────────────────┴─────────────────────┘
        ↓
Post recommendation back to chat
        ↓
Store top candidate recommendation
        ↓
Ambiguous `chosen` Sheet
        ↓
HR Dashboard
        ↓
Human review / hiring workflow
```

The system is designed as **decision support for HR and managers**. Candidate recommendations are based on job-relevant professional information such as skills, experience, role, and seniority. Final employment decisions remain with human reviewers.

---

# Core Features

## 1. Conversation-Based Opportunity Detection

Apex AI analyzes workplace conversations and looks for concrete work that could reasonably be delegated.

It extracts information such as:

- task description
- reason for delegation
- required skills
- estimated effort
- expected seniority
- suggested worker profile
- delegation confidence

Example:

```json
{
  "opportunity_detected": true,
  "task": "Run the documented model evaluation across all configurations on the 1,500-sample benchmark and record the results.",
  "delegation_score": 0.93,
  "complexity": "junior",
  "required_skills": [
    "following documented procedures",
    "model evaluation or QA testing",
    "result recording and organization",
    "attention to detail"
  ],
  "estimated_effort": "2 days"
}
```

---

## 2. Candidate Pool Search

Candidate information is stored in the Ambiguous Sheet:

```text
Candidate Pool
```

Candidate records include fields such as:

```text
candidate_id
name
level
skills
status
years
role
```

The system can work with previous applicants, talent-pool candidates, and other professional candidate profiles stored in the workspace.

---

## 3. Two-Stage Candidate Matching

To keep the AI workflow efficient, Apex AI does not send the entire candidate database to the model.

Instead:

```text
Candidate Pool
     ↓
Local pre-filter
     ↓
Top 5 potentially relevant candidates
     ↓
Ambiguous Assistant
     ↓
Semantic candidate evaluation
     ↓
Top recommendations
```

The local pre-filter considers job-related information such as:

- required level
- ML/model experience
- QA/testing
- data analysis
- research
- documentation
- Python
- hardware/integration
- data collection

The Ambiguous Assistant then performs semantic evaluation of the shortlisted candidates.

Each recommendation contains:

```json
{
  "candidate_id": "...",
  "name": "...",
  "match_score": 0.86,
  "matched_skills": [
    "QA",
    "ML",
    "data analysis"
  ],
  "why_candidate_matches": "..."
}
```

Candidate recommendations are produced for human review rather than automatic hiring decisions.

---

## 4. Job Opening Detection

Apex AI also reads the Ambiguous Sheet:

```text
job portal
```

It checks whether an existing open position genuinely covers the newly detected work.

The analysis considers:

- task type
- required skills
- seniority
- scope of responsibility

For example, the system should not treat:

```text
Senior ML Engineer
```

as an appropriate match for a:

```text
Junior ML Evaluation Assistant
```

simply because both involve machine learning.

A job must match the actual task and expected seniority.

---

## 5. New Job Recommendation

If no appropriate job opening exists, Apex AI generates a suggested opening.

Example:

```text
Junior ML Evaluation Assistant

Level:
junior

Skills:
- model evaluation
- QA testing
- following documented procedures
- result recording
- attention to detail

Estimated effort:
2 days
```

For the current MVP, this is a **job-opening recommendation**, not autonomous creation of a real employment position.

---

## 6. Recommendation Posted Back to Chat

After the analysis completes, qbot posts the result into the same Ambiguous conversation.

Example:

```text
🤖 I found a potential delegation opportunity.

Task:
Run the documented model evaluation across all configurations
on the 1,500-sample benchmark and record the results.

Estimated effort: 2 days
Suggested level: junior

Why I flagged this:
This is a repetitive testing task with a documented procedure
and a clear deliverable.

Potential candidate matches:

• Candidate A (86% match)
  Relevant skills: QA, ML, data analysis
  Why this candidate matches: ...

• Candidate B (74% match)
  Relevant skills: research, documentation
  Why this candidate matches: ...

⚠️ I could not find an existing job opening that appropriately
matches this work.

Suggested new opening:
• Junior ML Evaluation Assistant
• Level: junior
• Skills: model evaluation, QA testing, result recording

This is a staffing suggestion for human review,
not an automated hiring decision.
```

---

# Live Event Architecture

Apex AI can operate as a live agent rather than requiring the analysis script to be manually executed.

Ambiguous exposes workspace events including:

```text
message.received
```

The live architecture is:

```text
New Ambiguous message
        ↓
message.received event
        ↓
Ambiguous Webhook
        ↓
Public HTTPS endpoint
        ↓
Apex AI listener
        ↓
Conversation analysis
        ↓
Candidate + job analysis
        ↓
Recommendation posted to Ambiguous
```

During local development, a Cloudflare Tunnel can expose the local webhook listener:

```powershell
.\cloudflared.exe tunnel --url http://localhost:8000
```

This provides a temporary HTTPS URL that can be registered with Ambiguous.

---

# Ambiguous Sheets

Apex AI currently uses three main Ambiguous Sheets.

## Candidate Pool

Stores available candidate profiles.

| Field | Description |
|---|---|
| `candidate_id` | Candidate identifier |
| `name` | Candidate name |
| `level` | Professional/seniority level |
| `skills` | Professional skills |
| `status` | Candidate source/status |
| `years` | Years of experience |
| `role` | Current or previous role |

---

## job portal

Stores existing job openings.

Typical fields:

| Field | Description |
|---|---|
| `job_id` | Job identifier |
| `title` | Job title |
| `skills` | Required skills |
| `level` | Required seniority |
| `status` | Open/closed status |
| `department` | Department |

---

## chosen

Stores candidates surfaced for the HR workflow.

| Field | Description |
|---|---|
| `candidate_id` | Candidate identifier |
| `name` | Candidate name |
| `level` | Candidate level |
| `skills` | Candidate skills |
| `status` | Candidate status |
| `years` | Years of experience |
| `role` | Candidate role |
| `state` | HR workflow state |
| `offer_amount` | Offer amount when applicable |

The highest-ranked recommendation can be written into this sheet as:

```text
state = final_recommendation
```

This makes the recommendation available to the HR dashboard for review.

---

# HR Dashboard

Apex AI includes a Cloudflare Workers-based HR dashboard.

The dashboard reads candidate information from Ambiguous Sheets and provides a human-facing interface for reviewing the candidates surfaced by the agent.

The Worker architecture keeps the Ambiguous API credential on the server rather than exposing it in browser JavaScript.

```text
Browser
   ↓
Cloudflare Worker
   ↓
Ambiguous API
   ↓
Ambiguous Sheets
```

The dashboard supports HR workflow actions such as:

- reviewing candidate information
- reviewing skills and experience
- viewing recommendation state
- recording an offer
- updating hiring state
- rejecting a candidate
- managing previously hired candidates

---

# Architecture

```text
                    ┌───────────────────────────┐
                    │      Ambiguous Chat       │
                    │      #research-team       │
                    └─────────────┬─────────────┘
                                  │
                         message.received
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │      Apex AI Agent        │
                    │                           │
                    │ Opportunity Detection     │
                    │ Candidate Matching        │
                    │ Job Matching              │
                    └───────┬───────────┬───────┘
                            │           │
                ┌───────────┘           └───────────┐
                ▼                                   ▼
      ┌───────────────────┐               ┌───────────────────┐
      │  Candidate Pool   │               │    job portal     │
      │ Ambiguous Sheet   │               │ Ambiguous Sheet   │
      └───────────────────┘               └───────────────────┘
                │
                ▼
      ┌───────────────────┐
      │      chosen       │
      │ Ambiguous Sheet   │
      └─────────┬─────────┘
                │
                ▼
      ┌───────────────────┐
      │   HR Dashboard    │
      │ Cloudflare Worker │
      └───────────────────┘
```

---

# Technology Stack

### AI and Agent Layer

- Ambiguous Assistant
- Ambiguous Chat API
- Ambiguous workspace events
- Python
- Requests

### Data Layer

- Ambiguous Sheets
- Candidate Pool
- Job Portal
- Chosen Candidates

### Live Agent

- Flask
- Ambiguous webhooks
- `message.received`
- Cloudflare Tunnel

### HR Dashboard

- Cloudflare Workers
- JavaScript
- HTML/CSS
- Ambiguous API

---

# Local Python Setup

Requires Python 3.11+.

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install requests python-dotenv flask
```

Create a local `.env`:

```env
AMBIGUOUS_API_KEY=your_key_here
```

Never commit `.env` or expose the API key in browser-side code.

---

# Running the Candidate/Job Pipeline

For development, the pipeline can be executed manually:

```powershell
python .\candidate_job_match.py
```

The script:

```text
loads Candidate Pool
        ↓
pre-filters candidates
        ↓
semantically evaluates shortlist
        ↓
checks job portal
        ↓
creates recommendation
        ↓
writes top recommendation to chosen
        ↓
posts result to Ambiguous Chat
```

---

# Running the Live Agent

Start the webhook listener:

```powershell
python .\live_agent.py
```

By default the local Flask application listens on:

```text
http://localhost:8000
```

Expose it using Cloudflare Tunnel:

```powershell
.\cloudflared.exe tunnel --url http://localhost:8000
```

Cloudflare will provide a temporary URL similar to:

```text
https://example.trycloudflare.com
```

The webhook endpoint is:

```text
https://example.trycloudflare.com/ambiguous-webhook
```

Register the endpoint for:

```text
message.received
```

After registration, new Ambiguous messages can trigger the Apex AI pipeline automatically.

---

# Cloudflare Dashboard Development

Install dependencies:

```bash
npm install
```

Create local development variables:

```bash
cp .dev.vars.example .dev.vars
```

Set:

```text
AMBIGUOUS_API_KEY
```

Then:

```bash
npm run dev
```

The Worker keeps the Ambiguous credential server-side.

Typical API routes include:

```text
GET   /api/candidates
GET   /api/chosen
PATCH /api/chosen/:candidate_id/state
GET   /api/health
```

---

# Cloudflare Deployment

Authenticate Wrangler:

```bash
npx wrangler login
```

Store the Ambiguous credential:

```bash
npx wrangler secret put AMBIGUOUS_API_KEY
```

Deploy:

```bash
npm run deploy
```

Never commit API keys or webhook signing secrets.

---

# Security

Apex AI follows several important security principles:

- Ambiguous API credentials remain server-side.
- `.env` and `.dev.vars` should never be committed.
- Webhook signing secrets should be stored as environment variables.
- Browser code does not directly receive the Ambiguous API key.
- Candidate recommendations use professional/job-relevant information.
- Sensitive or protected characteristics should not be used for candidate matching.
- Employment recommendations remain subject to human review.

If an API key has been accidentally exposed, rotate it before deployment.

---

# Current MVP Scope

The hackathon MVP demonstrates:

- workplace conversation analysis
- delegation opportunity detection
- task requirement extraction
- candidate-pool retrieval
- semantic candidate matching
- candidate ranking
- existing job-opening detection
- new job-opening suggestions
- recommendation posting into Ambiguous Chat
- chosen-candidate persistence in Ambiguous Sheets
- live `message.received` event integration
- HR review through a Cloudflare dashboard

Future improvements could include:

- richer candidate retrieval
- embeddings/vector search for large candidate pools
- configurable approval workflows
- HR notifications
- automatic job-draft creation after approval
- duplicate opportunity detection
- recommendation audit history
- production webhook deployment
- evaluation datasets for candidate-matching quality

---

# Responsible Use

Apex AI is designed to **assist**, not replace, human staffing and hiring decisions.

The system can identify work requirements, retrieve potentially relevant professional profiles, and organize information for HR review. Candidate recommendations should be evaluated by authorized humans before any employment action is taken.

---

## Authors

- Sagnik Das
- Prasanna Bhat
- Pawan Saxena

## License

MIT License