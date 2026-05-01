import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.api.v1.resignation import create_resignation

class TestEmployeeResignation(FrappeTestCase):
    def setUp(self):
        # Create a dummy employee to act as our primary user
        if not frappe.db.exists("Employee", "HR-EMP-TEST-99"):
            doc = frappe.get_doc({
                "doctype": "Employee",
                "name": "HR-EMP-TEST-99",
                "employee": "HR-EMP-TEST-99",
                "first_name": "Test Resignation",
                "status": "Active"
            })
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)

    def test_create_resignation_invalid_attachment(self):
        # Testing invalid base64 attachment parsing
        with self.assertRaises(frappe.ValidationError):
            create_resignation(
                employee_id="HR-EMP-TEST-99",
                resignation_initiation_date="2026-04-27",
                relieving_date="2026-05-27",
                attachment={
                    "attachment_name": "invalid_attachment.png",
                    "attachment": "not_a_valid_base64_string"
                }
            )
