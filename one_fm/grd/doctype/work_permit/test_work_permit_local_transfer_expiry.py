# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A Local Transfer completes on the Updated Work Permit Expiry Date; the legacy
Work Permit Expiry Date is neither required nor written to the Employee."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate


def _local_transfer(**values):
	doc = frappe.new_doc("Work Permit")
	doc.update(
		{
			"work_permit_type": "Local Transfer",
			"workflow_state": "Completed",
			"employee": "HR-EMP-TEST",
			"work_permit_expiry_date": None,
			"new_work_permit_expiry_date": add_days(nowdate(), 365),
		}
	)
	doc.update(values)
	return doc


@patch("one_fm.grd.doctype.work_permit.work_permit.WorkPermit.reload")
class TestLocalTransferCompletion(FrappeTestCase):
	def test_completes_without_the_legacy_expiry_date(self, _reload):
		_local_transfer().check_required_document_for_workflow()

	def test_updated_expiry_date_is_required(self, _reload):
		doc = _local_transfer(new_work_permit_expiry_date=None)
		with self.assertRaises(frappe.ValidationError) as cm:
			doc.check_required_document_for_workflow()
		self.assertIn("Updated Work Permit Expiry Date", str(cm.exception))

	def test_employee_gets_the_updated_expiry_date(self, _reload):
		doc = _local_transfer(work_permit_expiry_date=add_days(nowdate(), 10))
		with patch.multiple(
			doc,
			update_wp_child_table_in_transfer_paper=lambda: None,
			recall_create_medical_insurance_transfer=lambda: None,
			notify_grd_transfer_mi_record=lambda: None,
			set_work_permit_attachment_in_employee_doctype=lambda *a: setattr(doc, "_written", a),
		):
			doc.on_submit()
		self.assertEqual(getdate(doc._written[0]), getdate(doc.new_work_permit_expiry_date))
