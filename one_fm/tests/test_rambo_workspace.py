# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Rambo workspace.

The Accommodation Dispatch and Grooming Audit report is a shortcut tile in the
same row as Rambo Employee List and Rambo Assignment.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

WORKSPACE = ("one_fm", "one_fm", "workspace", "rambo", "rambo.json")
REPORT = "Accommodation Dispatch and Grooming Audit"


class TestRamboWorkspace(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.doc = json.loads(frappe.read_file(frappe.get_app_path(*WORKSPACE)))
		cls.content = json.loads(cls.doc["content"])
		cls.blocks = [b["data"]["shortcut_name"] for b in cls.content if b["type"] == "shortcut"]

	def test_report_shortcut_exists(self):
		shortcut = next(s for s in self.doc["shortcuts"] if s["link_to"] == REPORT)
		self.assertEqual(shortcut["type"], "Report")
		self.assertEqual(shortcut["label"], REPORT)

	def test_every_block_has_a_shortcut(self):
		# A block whose name matches no shortcut label renders nothing.
		labels = {s["label"] for s in self.doc["shortcuts"]}
		for name in self.blocks:
			self.assertIn(name, labels)

	def test_report_sits_after_rambo_assignment(self):
		self.assertEqual(self.blocks.index(REPORT), self.blocks.index("Rambo Assignment") + 1)
		block = next(b for b in self.content if b.get("data", {}).get("shortcut_name") == REPORT)
		self.assertEqual(block["data"]["col"], 3)

	def test_the_report_exists(self):
		self.assertTrue(frappe.db.exists("Report", REPORT))

	def test_the_workspace_is_under_gsd(self):
		self.assertEqual(self.doc["parent_page"], "GSD")

	def test_modified_is_bumped(self):
		# migrate skips the file unless modified is newer than the database row.
		self.assertGreater(self.doc["modified"], "2026-06-28 13:00:00")
