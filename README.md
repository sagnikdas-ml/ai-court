# HiWi Candidate Search

Search for public-web leads matching a HiWi position with Exa.

```python
from hiwi_search import find_hiwi_candidates

result = find_hiwi_candidates("Computer Vision HiWi")
```

The result is a JSON-compatible dictionary containing up to five candidate records. The API key is read from `.exa` or the `EXA_API_KEY` environment variable. A command-line invocation is also available:

```bash
python hiwi_search.py "Computer Vision HiWi"
```

Candidate data is sourced from public web pages and should be reviewed before contacting anyone; the tool does not verify availability, identity, or employment status.
