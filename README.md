# Slack Delegation Assistant

A Python Slack bot that detects delegatable work, extracts task requirements with OpenAI, and matches fictional employees in SQLite. Run a complete local demonstration without credentials, or connect it to two Slack test channels.

```text
Alice + Bob -> Slack Socket Mode -> latest 10 messages -> OpenAI structured analysis
            -> deterministic employee matching -> Slack suggestion + three buttons
```

## Quick start (Windows PowerShell)

Requires Python 3.11 or newer. Run from this repository:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m delegation_bot seed
.\.venv\Scripts\python.exe -m delegation_bot replay --scenario junior-task --analyzer mock
.\.venv\Scripts\python.exe -m pytest
```

Using the virtual environment's Python directly avoids PowerShell activation-policy issues. After activating it, the equivalent commands are `python -m delegation_bot ...` and `pytest`.

Mock mode prints the Alice/Bob conversation, a suggestion, and the candidate shortlist. It returns **scripted fixture output, not real text analysis**. Replay always uses an isolated in-memory database and never sends messages to Slack.

Try other scenarios and simulate button clicks:

```powershell
.\.venv\Scripts\python.exe -m delegation_bot replay --scenario senior-task
.\.venv\Scripts\python.exe -m delegation_bot replay --scenario casual-chat
.\.venv\Scripts\python.exe -m delegation_bot replay --scenario completed-work
.\.venv\Scripts\python.exe -m delegation_bot replay --scenario no-match
.\.venv\Scripts\python.exe -m delegation_bot replay --scenario multiple-tasks
.\.venv\Scripts\python.exe -m delegation_bot replay --scenario prompt-injection
.\.venv\Scripts\python.exe -m delegation_bot replay --action ask_hr
.\.venv\Scripts\python.exe -m delegation_bot replay --action ignore
```

## Real text analysis with OpenAI

Edit `.env` locally and set `OPENAI_API_KEY` and `OPENAI_MODEL` to a model available to your API project that supports Responses Structured Outputs. The model is deliberately configurable; no paid API call occurs in mock mode.

```powershell
.\.venv\Scripts\python.exe -m delegation_bot replay --scenario junior-task --analyzer openai
```

The implementation calls `client.responses.parse(..., text_format=Analysis)` with a Pydantic schema. It asks for concrete unfinished deliverables, junior/senior requirements, difficulty, required skills, rationale, and source message IDs. This is task extraction, not sentiment analysis. No embeddings, training, or vector database are needed for this demo.

Conversation text is supplied as untrusted data. Prior opportunities are included to reduce paraphrased duplicates. The app checks that evidence IDs exist and only posts actionable, nonempty tasks. Invalid or refused responses produce no suggestion; transient API failures have at most two retries. Structured output constrains format, but the live model's interpretation still needs evaluation.

Reference: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Connect a real Slack workspace

1. Open [Slack app management](https://api.slack.com/apps) and choose **Create New App → From a manifest**. Select your test workspace and paste `slack-app-manifest.json`.
2. In **Basic Information → App-Level Tokens**, generate a token with `connections:write`. Put its `xapp-...` value in `SLACK_APP_TOKEN`. App-level tokens are created separately; the manifest cannot generate them.
3. In **OAuth & Permissions**, install the app to your workspace. Put the **Bot User OAuth Token** (`xoxb-...`) in `SLACK_BOT_TOKEN`.
4. Verify **Socket Mode** and **Interactivity** are enabled. Under **Event Subscriptions**, the bot event is `message.channels`. Required bot scopes are `channels:history` and `chat:write`. Reinstall if scopes change.
5. Create two public test channels, for example `delegation-demo` and `delegation-hr`. Invite the app to both using `/invite @Delegation Assistant`.
6. Copy their channel IDs from channel details into `SLACK_CHANNEL_ID` and `HR_CHANNEL_ID`. Use different channels. Do not use channel names or `#` prefixes.
7. Set the OpenAI variables as above, then run:

```powershell
.\.venv\Scripts\python.exe -m delegation_bot run
```

Keep the process running. Socket Mode opens an outbound connection; no public webhook URL or ngrok is needed. Two people use their own Slack accounts as Alice and Bob. No user impersonation or automated message seeding is performed.

Reference: [Slack Bolt Socket Mode](https://docs.slack.dev/tools/bolt-python/concepts/socket-mode/).

## Alice/Bob live demo

Paste these messages in order into the configured test channel. Send the final two close together, then wait five seconds plus API latency. If you pause earlier, the bot may analyze the partial conversation, which is expected.

| Speaker | Message |
|---|---|
| Alice | The sales team needs a weekly summary from their CSV exports. |
| Bob | What should the summary contain? |
| Alice | Revenue totals by region and a list of missing customer IDs. |
| Bob | Is this a dashboard or just a file? |
| Alice | Just a CSV report generated by a Python script. |
| Bob | Do we have example inputs? |
| Alice | Yes, sample files and the expected output format are ready. |
| Bob | That sounds straightforward with pandas. |
| Alice | I'm busy with the payment migration. Can someone else take this? |
| Bob | A junior developer could implement it, and I can review it. |

Expected: a thread reply identifying the reporting task, usually low difficulty and junior level, with Python/pandas/CSV skills. Live wording and classification can vary.

- **View Candidates:** private ephemeral shortlist for the person clicking. The scripted task ranks Maya Chen, Priya Shah, and Leo Martins; Leo lacks pandas and is labeled a partial match.
- **Ignore:** mark the card ignored and suppress that task in the same conversation.
- **Ask HR:** send the summary, candidate shortlist, requester, and source reference to the HR test channel. Clicking is the explicit send action; there is no automatic assignment.

Smoke-test checklist: confirm one suggestion appears, inspect matched/missing skills, click Ask HR, verify exactly one HR message and the updated card, then click an old action again to confirm it does not resend. Use another thread for an Ignore test. Try casual chat and completed-work fixtures with live replay to evaluate false positives. Live tests require your own credentials and workspace.

## Behavior and persistence

- Only new human text messages in the configured public channel are ingested. Bots, edits, deletions, private channels, DMs, and attachments are excluded.
- Channel discussion and each thread have separate windows. Threads keep a locally available root plus nine recent replies. Old roots not already observed are not fetched from Slack. Other windows keep ten messages.
- A five-second quiet period triggers analysis; newer input invalidates an in-flight result. Processing is serialized per conversation.
- SQLite stores the latest messages, processed event IDs, opportunities, action state, and twelve fictional employees. Seeding is idempotent and does not overwrite employee edits.
- Matching excludes unavailable employees; senior tasks require seniors. Rank by skill coverage, exact level match, then employee ID. At most three matches are shown, with missing skills. Unknown skills return no matches.
- Normalized titles suppress exact task repeats, including across restarts. The model also receives earlier tasks to reduce semantic repeats; paraphrase suppression is not guaranteed. Ignored tasks remain suppressed in that database, even after restart.
- A timeout during HR posting is marked `hr_uncertain`. Automatic retries are disabled for Slack posts. Check the HR channel for the opportunity ID before manually reconciling the database. Interrupted initial suggestion posts are similarly marked `post_uncertain` and are not automatically reposted. Definitive Slack rejection such as `not_in_channel` leaves HR retryable.
- In-flight analysis is not resumed on restart; a new message schedules it. Run one bot process per database. This is a local MVP, not a distributed worker service.
- Replay always starts fresh. For a fresh real demo, stop the bot and choose a new `DATABASE_PATH` in `.env`, then seed and restart. Existing databases are not deleted by the app.

Messages selected for live analysis leave your machine for OpenAI; requests set `store=False`. This is not a guarantee of zero provider retention. Keep demos fictional. Secrets and databases are gitignored; logs report error types and operational IDs without dumping conversations or keys.

## Configuration

| Variable | Use |
|---|---|
| `OPENAI_API_KEY` | Required for live analysis |
| `OPENAI_MODEL` | Required model ID supporting structured Responses output |
| `SLACK_BOT_TOKEN` | Installed bot token |
| `SLACK_APP_TOKEN` | Socket Mode app-level token |
| `SLACK_CHANNEL_ID` | Public test channel to monitor |
| `HR_CHANNEL_ID` | Separate public HR test channel |
| `DATABASE_PATH` | Defaults to `data/delegation.sqlite3` |
| `DEBOUNCE_SECONDS` | Positive quiet interval; defaults to `5` |

## Troubleshooting and development

- **No Slack events:** check the channel ID, invite the bot, enable `message.channels`, and keep the process running. Private channels are outside this manifest's scope.
- **No AI suggestion:** try live replay to isolate Slack setup, confirm the API key/model, and inspect logs. Clear handoff evidence is required; false or completed tasks should produce no response.
- **HR request rejected:** invite the bot to the HR channel and check scopes. Retry only when the card remains open. For uncertain delivery, check the HR channel first.
- **Candidates missing:** only available seeded employees with overlapping skills qualify. Run `seed` against the same database.
- **Repeated demo produces no card:** previous opportunity fingerprints persist. Use a fresh database or a new thread.

Modules separate typed analysis (`models.py`, `analysis.py`), storage and matching (`store.py`, `candidates.py`), orchestration (`service.py`), Slack rendering/transport (`rendering.py`, `slack.py`), and fixtures/CLI. Tests use fake transports and model clients; passing them does not certify live model accuracy. `prompt-injection` in mock mode tests the pipeline fixture, while its live replay tests model behavior.
