# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestOverseasRemedical(FrappeTestCase):
	@patch("one_bpmn.one_bpmn.trigger.on_doc_event")
	def test_saving_leaves_the_tracker_sync_to_the_process_map(self, _trigger):
		Details = frappe.qb.DocType("Candidate Country Process Details")
		rows = (
			frappe.qb.from_(Details)
			.select(Details.parent, Details.name, Details.status)
			.where(Details.process_name == "Remedical results")
			.where(Details.status != "Fit")
			.limit(1)
		).run(as_dict=True)
		if not rows:
			self.skipTest("No Candidate Country Process with a Remedical results tracker row")

		ccp_modified = frappe.db.get_value("Candidate Country Process", rows[0].parent, "modified")
		frappe.get_doc({
			"doctype": "Overseas Remedical",
			"candidate_country_process": rows[0].parent,
			"status": "Fit",
		}).insert()

		self.assertEqual(frappe.db.get_value("Candidate Country Process Details", rows[0].name, "status"), rows[0].status)
		self.assertEqual(frappe.db.get_value("Candidate Country Process", rows[0].parent, "modified"), ccp_modified)
