# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestOverseasMedicalAppointmentWAFID(FrappeTestCase):
	@patch("one_bpmn.one_bpmn.trigger.on_doc_event")
	def test_saving_leaves_the_tracker_sync_to_the_process_map(self, _trigger):
		Details = frappe.qb.DocType("Candidate Country Process Details")
		WAFID = frappe.qb.DocType("Overseas Medical Appointment WAFID")
		rows = (
			frappe.qb.from_(WAFID)
			.join(Details)
			.on(Details.parent == WAFID.candidate_country_process)
			.select(WAFID.name.as_("wafid"), Details.name.as_("row"), Details.status)
			.where(Details.process_name == "Medical Result")
			.where(WAFID.status != "Fit")
			.limit(1)
		).run(as_dict=True)
		if not rows:
			self.skipTest("No WAFID record with a Medical Result tracker row")

		wafid = frappe.get_doc("Overseas Medical Appointment WAFID", rows[0].wafid)
		ccp_modified = frappe.db.get_value("Candidate Country Process", wafid.candidate_country_process, "modified")
		wafid.status = "Fit"
		wafid.save()

		self.assertEqual(frappe.db.get_value("Candidate Country Process Details", rows[0].row, "status"), rows[0].status)
		self.assertEqual(
			frappe.db.get_value("Candidate Country Process", wafid.candidate_country_process, "modified"), ccp_modified
		)
