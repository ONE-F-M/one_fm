"""The PR helper lives in .claude and nothing points at the old scripts/ path."""

import json
from pathlib import Path

from frappe.tests.utils import FrappeTestCase

NEW_PATH = ".claude/open-pr-via-github-app.sh"
OLD_PATH = "scripts/claude-pr.sh"
REPO_ROOT = Path(__file__).resolve().parents[2]


class TestPrHelperPath(FrappeTestCase):
	def test_helper_exists_at_new_path(self):
		self.assertTrue((REPO_ROOT / NEW_PATH).is_file())

	def test_old_helper_is_gone(self):
		self.assertFalse((REPO_ROOT / OLD_PATH).exists())
		self.assertFalse((REPO_ROOT / "scripts").exists())

	def test_settings_allow_and_ask_name_new_path(self):
		permissions = json.loads((REPO_ROOT / ".claude/settings.json").read_text())["permissions"]
		self.assertEqual(permissions["allow"], [f"Bash(bash {NEW_PATH}:*)"])
		self.assertEqual(permissions["ask"], [f"Bash(bash {NEW_PATH} --update:*)"])

	def test_docs_name_only_the_new_path(self):
		claude_md = (REPO_ROOT / "CLAUDE.md").read_text()
		self.assertIn(NEW_PATH, claude_md)
		for name in ("CLAUDE.md", "AGENTS.md"):
			self.assertNotIn(OLD_PATH, (REPO_ROOT / name).read_text(), name)
