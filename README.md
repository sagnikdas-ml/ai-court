# HiWi Candidate Search

Search for public-web leads matching a HiWi position with Exa and publish the results in Ambiguous.

```python
from hiwi_search import find_hiwi_candidates

result = find_hiwi_candidates("Computer Vision HiWi")
```

The result is a JSON-compatible dictionary containing up to five candidate records. The API key is read from `.exa` or the `EXA_API_KEY` environment variable. A command-line invocation is also available:

```bash
python hiwi_search.py "Computer Vision HiWi"
```

Candidate data is sourced from public web pages and should be reviewed before contacting anyone; the tool does not verify availability, identity, or employment status.

## Ambiguous workspace integration

The repository also exposes an MCP server for an Ambiguous AI coworker. The tool searches Exa, creates an Ambiguous Sheet with the structured candidates, and posts a summary to an Ambiguous Chat channel.

Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Configure `EXA_API_KEY`, `AMBIGUOUS_API_KEY`, and `AMBIGUOUS_CHAT_CHANNEL_ID` as environment variables. `AMBIGUOUS_API_URL` defaults to `https://app.ambiguous.ai/api`. The checked-in `.env.example` lists the required variables without containing secrets.

Run the MCP server over stdio:

```bash
python3 ambiguous_agent.py
```

Connect this server to the Ambiguous coworker using the workspace's MCP configuration. Then mention the coworker in Ambiguous Chat with a request such as: `Find HiWi candidates for Computer Vision.`
