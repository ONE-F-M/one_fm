# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Hospitality workspace (WI-001764).

Accommodation Leave Movement is reachable from the Hospitality workspace so an
Accommodation Manager does not have to search for it. Visibility is governed by
the doctype's own permissions, not the workspace, which carries no roles.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

WORKSPACE = ("one_fm", "one_fm", "workspace", "hospitality", "hospitality.json")
ALM = "Accommodation Leave Movement"


class TestHospitalityWorkspace(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.doc = json.loads(frappe.read_file(frappe.get_app_path(*WORKSPACE)))
		cls.links = cls.doc["links"]

	def _card_break(self, label):
		return next(
			link for link in self.links
			if link.get("type") == "Card Break" and link.get("label") == label
		)

	def test_leave_movement_is_linked(self):
		targets = [link.get("link_to") for link in self.links]
		self.assertIn(ALM, targets)

	def test_it_sits_beside_checkin_checkout(self):
		targets = [link.get("link_to") for link in self.links]
		self.assertEqual(
			targets.index(ALM), targets.index("Accommodation Checkin Checkout") + 1
		)

	def test_the_card_break_counts_the_new_link(self):
		# A stale link_count silently truncates the card, hiding the last entries.
		card = self._card_break("Accommodation")
		first = self.links.index(card)
		# Links belonging to this card run until the next Card Break.
		count = 0
		for link in self.links[first + 1 :]:
			if link.get("type") == "Card Break":
				break
			count += 1
		self.assertEqual(card["link_count"], count)

	def test_the_linked_doctype_exists(self):
		self.assertTrue(frappe.db.exists("DocType", ALM))

	def test_the_workspace_is_under_gsd_and_public(self):
		self.assertEqual(self.doc["parent_page"], "GSD")
		self.assertEqual(self.doc["public"], 1)

	def test_visibility_comes_from_the_doctype_permissions(self):
		# The workspace declares no roles, so who sees the link is decided by the
		# doctype's own permissions - Accommodation User is the operational role.
		self.assertEqual(self.doc["roles"], [])
		roles = {p.role for p in frappe.get_meta(ALM).permissions if p.read}
		self.assertIn("Accommodation User", roles)

	def test_the_card_layout_still_renders_the_accommodation_card(self):
		# `content` references cards by name; adding a link must not disturb it.
		blocks = json.loads(self.doc["content"])
		names = [b["data"].get("card_name") for b in blocks if b["type"] == "card"]
		self.assertIn("Accommodation", names)
