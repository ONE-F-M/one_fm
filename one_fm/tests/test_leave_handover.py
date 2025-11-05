import frappe
import unittest
from frappe.test_runner import make_test_records

class TestLeaveHandover(unittest.TestCase):
    def setUp(self):
        make_test_records("User")
        make_test_records("Employee")
        make_test_records("Leave Application")
        make_test_records("Role")
        make_test_records("Role Profile")
        self.employee = frappe.get_doc("Employee", {"user_id": "test@example.com"})
        self.reliever = frappe.get_doc("Employee", {"user_id": "test1@example.com"})
        self.leave_application = frappe.get_doc("Leave Application", {"employee": self.employee.name})
        self.leave_handover = create_leave_handover(self.employee.name, self.leave_application.name)

    def tearDown(self):
        frappe.db.rollback()

    def test_revert_handover(self):
        self.leave_handover.submit()
        self.leave_handover.reload()
        self.assertEqual(self.leave_handover.docstatus, 1)
        self.assertEqual(self.leave_handover.status, "Transferred")

        reliever_user = frappe.get_doc("User", self.reliever.user_id)
        self.assertIn("Project Manager", reliever_user.get_roles())

        self.leave_handover.revert_handover()
        self.leave_handover.reload()
        self.assertEqual(self.leave_handover.status, "Reverted")

        reliever_user.reload()
        self.assertNotIn("Project Manager", reliever_user.get_roles())
        self.assertEqual(reliever_user.role_profile_name, "Test Role Profile")

def create_leave_handover(employee, leave_application):
    doc = frappe.get_doc({
        "doctype": "Leave Handover",
        "employee": employee,
        "leave_application": leave_application,
        "handover_items": [
            {
                "reference_doctype": "Project",
                "reference_docname": "Test Project",
                "reliever": "test1@example.com",
                "status": "Accepted",
                "roles_assigned": "Project Manager",
                "reliever_role_profile": "Test Role Profile"
            }
        ]
    })
    doc.insert()
    return doc
