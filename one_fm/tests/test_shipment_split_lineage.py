# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A generator delete must not leave overflow cards linked to the deleted card.

The generator deletes with force=True, which skips Frappe's link check. An overflow card
that still named the deleted card in Split From then failed its next full save with
"Could not find Split From". A manual delete keeps the link check and stays blocked.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import _delete_card
from one_fm.patches.v15_0 import clear_dangling_shipment_split_links

DOCTYPE = "Transportation Shipment"


class TestSplitLineage(FrappeTestCase):
	def _card(self, parent=None, root=None):
		doc = frappe.new_doc(DOCTYPE)
		doc.status = "Unassigned"
		doc.trip_direction = "Outward"
		doc.generation_key = f"OPS|SPLIT-LINEAGE-TEST|{frappe.generate_hash(length=6)}"
		if parent:
			doc.is_split_overflow = 1
			doc.split_parent = parent
			doc.split_root = root or parent
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def _lineage(self, name):
		return frappe.db.get_value(DOCTYPE, name, ["split_parent", "split_root"], as_dict=True)

	def _save(self, name):
		doc = frappe.get_doc(DOCTYPE, name)
		doc.flags.ignore_mandatory = True
		doc.save(ignore_permissions=True)

	def test_a_deleted_middle_card_hands_its_children_to_its_parent(self):
		root = self._card()
		middle = self._card(parent=root)
		child = self._card(parent=middle, root=root)

		_delete_card(middle)

		self.assertEqual(self._lineage(child), {"split_parent": root, "split_root": root})
		self._save(child)

	def test_a_deleted_root_leaves_its_overflow_with_no_lineage(self):
		root = self._card()
		child = self._card(parent=root)

		_delete_card(root)

		self.assertEqual(self._lineage(child), {"split_parent": None, "split_root": None})
		self._save(child)

	def test_a_manual_delete_of_a_parent_is_still_blocked(self):
		root = self._card()
		child = self._card(parent=root)

		with self.assertRaises(frappe.LinkExistsError):
			frappe.delete_doc(DOCTYPE, root, ignore_permissions=True)

		self.assertTrue(frappe.db.exists(DOCTYPE, root))
		self.assertEqual(self._lineage(child), {"split_parent": root, "split_root": root})

	def test_the_patch_clears_links_left_by_earlier_deletes(self):
		root = self._card()
		child = self._card(parent=root)
		# What an older force delete left behind: the row is gone, the links are not.
		frappe.db.delete(DOCTYPE, {"name": root})

		clear_dangling_shipment_split_links.execute()

		self.assertEqual(self._lineage(child), {"split_parent": None, "split_root": None})
		self._save(child)
