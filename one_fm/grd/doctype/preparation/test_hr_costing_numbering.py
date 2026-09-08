# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002179: collapsing the three master fee rows must not leave a hole in the numbering.

Add Row numbers a new row by the table's length, not by its highest idx - create_new.js
client side, _init_child server side. So a gap in the middle is not cosmetic: the next row
HR adds carries an idx a row already has, and the table's order stops being decidable.

The whole thing is one test method on purpose. FrappeTestCase rolls back on
addClassCleanup, so anything a method changes is still there for the next one.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.consolidate_extension_actions import COSTING_PARENT, execute

# total_amount is derived from the components on save, so the fee goes in as a component.
MASTER_ROWS = (
	(3, "Extend 1 month", 30),
	(4, "Extend 2 months", 60),
	(5, "Extend 3 months", 90),
)


def costing_rows():
	return frappe.get_all(
		"GRD Renewal Extension Cost",
		filters=COSTING_PARENT,
		fields=["name", "idx", "renewal_or_extend", "total_amount"],
		order_by="idx asc, creation asc",
	)


class TestHrCostingNumbering(FrappeTestCase):
	def test_the_collapse_leaves_the_table_numbered_one_to_n(self):
		# A site that has not run the patch: the three master rows still sit at 3, 4, 5.
		frappe.db.delete(
			"GRD Renewal Extension Cost", dict(COSTING_PARENT, renewal_or_extend="Extension")
		)
		frappe.db.bulk_insert(
			"GRD Renewal Extension Cost",
			fields=[
				"name", "parent", "parenttype", "parentfield",
				"idx", "renewal_or_extend", "work_permit_amount",
			],
			values=[
				[
					f"wi2179test{position}", "HR Settings", "HR Settings",
					"renewal_extension_cost", idx, action, amount,
				]
				for position, (idx, action, amount) in enumerate(MASTER_ROWS)
			],
		)
		frappe.clear_cache(doctype="HR Settings")

		execute()

		rows = costing_rows()
		self.assertEqual(
			[row.idx for row in rows], list(range(1, len(rows) + 1)),
			"the collapse left a hole - list.remove was used where Document.remove renumbers",
		)

		extension_rows = [row for row in rows if row.renewal_or_extend == "Extension"]
		self.assertEqual(len(extension_rows), 1, "the three master rows did not become one")
		self.assertEqual(
			extension_rows[0].total_amount, 30,
			"the kept row must be the one that states the monthly rate",
		)

		# And a site that already ran the old version, carrying the hole it left: the patch
		# has to close it on the way through, not only avoid making a new one.
		frappe.db.set_value(
			"GRD Renewal Extension Cost", rows[-1].name, "idx", 9, update_modified=False
		)
		frappe.clear_cache(doctype="HR Settings")

		execute()

		rows = costing_rows()
		self.assertEqual(
			[row.idx for row in rows], list(range(1, len(rows) + 1)),
			"a hole left by an earlier run was not repaired",
		)
