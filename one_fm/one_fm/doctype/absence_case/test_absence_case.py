import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime


class TestAbsenceCase(FrappeTestCase):
	def test_formal_hearing_24h_notice(self):
		# Create a dummy absence case
		doc = frappe.get_doc({
			"doctype": "Absence Case",
			"employee": "HR-EMP-03486",
			"absence_type": "7 Days Consecutive Absence",
			"posting_date": now_datetime().date(),
			"formal_hearing_start_datetime": add_to_date(now_datetime(), hours=1)
		})
		
		# Should fail
		self.assertRaises(frappe.ValidationError, doc.insert)
		
		# Should pass with 25 hours
		doc.formal_hearing_start_datetime = add_to_date(now_datetime(), hours=25)
		doc.insert()
		
	def test_formal_hearing_end_after_start(self):
		doc = frappe.get_doc({
			"doctype": "Absence Case",
			"employee": "HR-EMP-03486",
			"absence_type": "7 Days Consecutive Absence",
			"posting_date": now_datetime().date(),
			"formal_hearing_start_datetime": add_to_date(now_datetime(), hours=25),
			"formal_hearing_end_datetime": add_to_date(now_datetime(), hours=24)
		})
		
		# Should fail
		self.assertRaises(frappe.ValidationError, doc.insert)
		
		# Should pass with end > start
		doc.formal_hearing_end_datetime = add_to_date(now_datetime(), hours=26)
		doc.insert()


class TestAbsenceCaseProcessaHandover(FrappeTestCase):
	def test_workflow_state_can_change_after_submit(self):
		# The absence maps submit the case and set Approved/Rejected in the same step.
		field = frappe.get_meta("Absence Case").get_field("workflow_state")
		self.assertIsNotNone(field)
		self.assertEqual(field.options, "Workflow State")
		self.assertEqual(field.allow_on_submit, 1)
		self.assertFalse(field.is_custom_field)

	def test_hr_officer_rule_is_removed(self):
		from one_fm.patches.v15_0.remove_absence_case_hr_officer_assignment_rule import execute

		execute()
		execute()
		self.assertFalse(frappe.db.exists("Assignment Rule", "Absence Case - HR Officer"))
