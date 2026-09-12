import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import hiwi_search


class HiWiSearchTests(unittest.TestCase):
    def test_extracts_and_deduplicates_candidates(self):
        response = {
            "results": [
                {
                    "url": "https://example.com/alice",
                    "summary": json.dumps({
                        "name": "Alice Example", "current_role": "MSc student",
                        "affiliation": "Example University", "skills": ["Python"],
                        "research_topics": ["robotics"], "evidence": "Works on robot perception.",
                        "match_rationale": "Matches the robotics role.",
                    }),
                },
                {"url": "https://example.com/alice/", "summary": {"name": "Alice Example", "evidence": "Duplicate."}},
                {
                    "url": "https://example.com/bob", "author": "Bob Example",
                    "highlights": ["Research assistant in machine learning."],
                    "summary": {"match_rationale": "Relevant ML work."},
                },
            ]
        }
        self.assertEqual(
            [item["name"] for item in hiwi_search._extract_candidates(response, 5)],
            ["Alice Example", "Bob Example"],
        )

    def test_find_hiwi_candidates_uses_key_file_and_returns_json_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            key_file = Path(temp_dir) / ".exa"
            key_file.write_text("EXA_API_KEY=test-key\n", encoding="utf-8")
            with patch.object(hiwi_search, "_request_exa", return_value={"results": []}) as request:
                result = hiwi_search.find_hiwi_candidates("Data Science HiWi", config_path=key_file)
        self.assertEqual(result, {"position_name": "Data Science HiWi", "candidates": []})
        self.assertEqual(request.call_args.args[0], "test-key")
        self.assertEqual(request.call_args.args[1]["numResults"], 10)

    def test_rejects_empty_position_name(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            hiwi_search.find_hiwi_candidates("  ")
