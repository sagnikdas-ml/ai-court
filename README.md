# FindPeople

FindPeople searches the public web for a requested job role, returns the top five distinct candidates, and stores their records in the Ambiguous sheet named `Candidate Pool`.

The sheet schema is:

```text
candidate_id | name | level | skills | status | years | role
```

The local MCP server exposes the same search behavior for development:

```bash
python3 -m pip install -r requirements.txt
python3 ambiguous_agent.py
```

Run it as a network MCP endpoint with streamable HTTP:

```bash
python3 ambiguous_agent.py --transport streamable-http --host 0.0.0.0 --port 8000
```

The endpoint is `http://localhost:8000/mcp`. For a hosted Ambiguous connection, expose that path through HTTPS and use the resulting URL as the MCP server URL. Keep the process running; it is not a one-shot command.

Set `EXA_API_KEY` in the environment or in a local `.exa` file when running the local server. Never commit API keys.

The deployed Ambiguous bot is `FindPeople`; its API channel is configured to search for the supplied role, return five candidates with public source evidence, and append non-duplicate rows to `Candidate Pool`.
