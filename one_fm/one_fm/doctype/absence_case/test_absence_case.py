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
