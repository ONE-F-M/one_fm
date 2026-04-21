import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.utils import leave_application_on_cancel
from frappe.utils import getdate, add_days

from unittest.mock import patch

class TestLeaveApplicationCancel(FrappeTestCase):
    def test_leave_application_on_cancel_comparison(self):
        # Create a dummy doc with from_date as a date object
        # This simulates the condition where doc.from_date is a datetime.date object
        doc = frappe._dict({
            "from_date": getdate(add_days(frappe.utils.nowdate(), -1)),
            "employee": "EMP-00001", # Dummy employee
            "doctype": "Leave Application"
        })
        
        # Mock frappe.db.set_value to avoid side effects if employee doesn't exist
        # and update_employee_hajj_status to avoid its internal logic
        with patch("frappe.db.set_value"), \
             patch("one_fm.utils.update_employee_hajj_status"):
            try:
                leave_application_on_cancel(doc, "on_cancel")
            except TypeError as e:
                self.fail(f"leave_application_on_cancel raised TypeError: {e}")
            except Exception as e:
                self.fail(f"leave_application_on_cancel raised an unexpected exception: {e}")

    def test_leave_application_on_cancel_with_string_date(self):
        # Also test with string date to ensure getdate() handles it correctly
        doc = frappe._dict({
            "from_date": add_days(frappe.utils.nowdate(), -1),
            "employee": "EMP-00001",
            "doctype": "Leave Application"
        })
        
        with patch("frappe.db.set_value"), \
             patch("one_fm.utils.update_employee_hajj_status"):
            try:
                leave_application_on_cancel(doc, "on_cancel")
            except TypeError as e:
                self.fail(f"leave_application_on_cancel raised TypeError with string date: {e}")
