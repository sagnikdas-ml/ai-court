import unittest
from unittest.mock import patch

import ambiguous_agent


class AmbiguousAgentTests(unittest.TestCase):
    @patch.object(ambiguous_agent, "find_candidates")
    def test_returns_numbered_candidates(self, search):
        search.return_value = {
            "position_name": "Robotics",
            "candidates": [{"name": "Alice"}, {"name": "Bob"}],
        }

        result = ambiguous_agent.run_candidate_search("Robotics")

        search.assert_called_once_with("Robotics", limit=5, config_path=".exa")
        self.assertEqual(result["candidates"][0]["candidate_number"], 1)
        self.assertEqual(result["candidates"][1]["candidate_number"], 2)

    def test_limit_cannot_exceed_five(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 5"):
            ambiguous_agent.run_candidate_search("Robotics", limit=6)


if __name__ == "__main__":
    unittest.main()
