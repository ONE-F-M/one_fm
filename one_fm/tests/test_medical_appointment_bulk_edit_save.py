# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""List Actions > Edit sets one field per run. A record missing both Required Transportation
and PRO User must still save when only one of them is set, while leaving Draft still needs both."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.grd.doctype.medical_appointment.medical_appointment import create_medical_appointment


class TestMedicalAppointmentBulkEditSave(FrappeTestCase):
	def setUp(self):
		employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not employee:
			self.skipTest("No active Employee on this site")
		self.appointment = create_medical_appointment(frappe.get_doc("Employee", employee), "First Time")
		self.appointment.db_set("employee_supervisor", "Administrator")
		self.appointment.reload()

	def _in_state(self, state):
		self.appointment.db_set("workflow_state", state)
		self.appointment.reload()
		return self.appointment

	def _bulk_edit(self, doc, data):
		"""What frappe.desk.doctype.bulk_update.bulk_update._bulk_action does per record."""
		doc = frappe.get_doc(doc.doctype, doc.name)
		doc.update(data)
		doc.save()
		return doc

	def test_the_preparation_opens_it_in_draft_with_both_fields_empty(self):
		self.assertEqual(self.appointment.workflow_state, "Draft")
		self.assertFalse(self.appointment.required_transportation)
		self.assertFalse(self.appointment.pro_user)

	def test_setting_pro_user_alone_saves_in_draft(self):
		doc = self._bulk_edit(self.appointment, {"pro_user": "Administrator"})
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "pro_user"), "Administrator")

	def test_setting_required_transportation_alone_saves_in_draft(self):
		doc = self._bulk_edit(self.appointment, {"required_transportation": "No"})
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "required_transportation"), "No")

	def test_setting_one_field_saves_on_a_pending_supervisor_record_missing_both(self):
		doc = self._bulk_edit(self._in_state("Pending Supervisor"), {"required_transportation": "Yes"})
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "required_transportation"), "Yes")
		self.assertEqual(frappe.db.get_value(doc.doctype, doc.name, "workflow_state"), "Pending Supervisor")

	def test_two_runs_fill_both_fields(self):
		self._bulk_edit(self.appointment, {"pro_user": "Administrator"})
		doc = self._bulk_edit(self.appointment, {"required_transportation": "No"})
		values = frappe.db.get_value(doc.doctype, doc.name, ["pro_user", "required_transportation"], as_dict=True)
		self.assertEqual((values.pro_user, values.required_transportation), ("Administrator", "No"))

	def test_leaving_draft_without_pro_user_is_refused(self):
		self.appointment.required_transportation = "No"
		self.appointment.workflow_state = "Pending Supervisor"
		with self.assertRaises(frappe.MandatoryError):
			self.appointment.save()

	def test_leaving_draft_without_required_transportation_is_refused(self):
		self.appointment.pro_user = "Administrator"
		self.appointment.workflow_state = "Pending Supervisor"
		with self.assertRaises(frappe.MandatoryError):
			self.appointment.save()

	def test_leaving_pending_supervisor_without_the_fields_is_refused(self):
		doc = self._in_state("Pending Supervisor")
		doc.workflow_state = "Pending GR Operator"
		with self.assertRaises(frappe.MandatoryError):
			doc.save()

	def test_leaving_draft_with_both_fields_passes_the_check(self):
		self.appointment.pro_user = "Administrator"
		self.appointment.required_transportation = "No"
		self.appointment.workflow_state = "Pending Supervisor"
		self.appointment.validate_fields_required_to_leave_draft()

	def test_the_fields_are_not_mandatory_on_every_save(self):
		meta = frappe.get_meta("Medical Appointment")
		for fieldname in ("required_transportation", "pro_user"):
			self.assertFalse(meta.get_field(fieldname).reqd, fieldname)
