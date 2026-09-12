import unittest
from unittest.mock import patch

import ambiguous_agent


class AmbiguousAgentTests(unittest.TestCase):
    def test_candidate_rows_have_stable_columns(self):
        rows = ambiguous_agent._candidate_rows([{
            "name": "Alice", "profile_url": "https://example.com/alice",
            "skills": ["Python", "Robotics"], "research_topics": ["Vision"],
        }])
        self.assertEqual(rows[0], ambiguous_agent.SHEET_COLUMNS)
        self.assertEqual(rows[1][0], "Alice")
        self.assertEqual(rows[1][5], "Python; Robotics")
        self.assertEqual(rows[1][6], "Vision")

    def test_sheet_updates_use_a1_cells(self):
        client = ambiguous_agent.AmbiguousClient("test-key", base_url="https://example.test/api")
        with patch.object(client, "_request", return_value={}) as request:
            client.write_sheet("sh_123", [["Name", "URL"], ["Alice", "https://example.com"]])
        payload = request.call_args.args[2]
        self.assertEqual(request.call_args.args[:2], ("PATCH", "/sheets/sh_123/cells"))
        self.assertEqual(payload["updates"][:3], [
            {"cell": "A1", "value": "Name"},
            {"cell": "B1", "value": "URL"},
            {"cell": "A2", "value": "Alice"},
        ])

    @patch.object(ambiguous_agent, "find_hiwi_candidates")
    def test_full_workflow_creates_sheet_writes_rows_and_posts_summary(self, search):
        search.return_value = {"position_name": "Robotics HiWi", "candidates": [{"name": "Alice"}]}
        client = ambiguous_agent.AmbiguousClient("test-key")
        with patch.object(ambiguous_agent, "AmbiguousClient", return_value=client), \
             patch.object(client, "create_sheet", return_value={"id": "sh_123", "url": "https://sheet.test/123"}) as create, \
             patch.object(client, "write_sheet", return_value={}) as write, \
             patch.object(client, "send_chat_message", return_value={"id": "msg_123"}) as send:
            result = ambiguous_agent.run_hiwi_search_in_ambiguous(
                "Robotics HiWi", ambiguous_api_key="test-key", chat_channel_id="ch_123"
            )
        create.assert_called_once_with("HiWi candidates - Robotics HiWi")
        self.assertEqual(write.call_args.args[0], "sh_123")
        send.assert_called_once()
        self.assertEqual(result["sheet_url"], "https://sheet.test/123")
        self.assertEqual(result["chat_message"], {"id": "msg_123"})

    def test_limit_cannot_exceed_five(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 5"):
            ambiguous_agent.run_hiwi_search_in_ambiguous("Robotics", limit=6)


if __name__ == "__main__":
    unittest.main()
