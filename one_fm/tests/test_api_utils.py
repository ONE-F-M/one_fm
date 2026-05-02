import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch
from one_fm.api.v1.utils import resolve_active_user

class TestApiUtils(FrappeTestCase):
    def setUp(self):
        # Create a dummy employee to act as our primary user
        if not frappe.db.exists("Employee", "HR-EMP-00001"):
            doc = frappe.get_doc({
                "doctype": "Employee",
                "name": "HR-EMP-00001",
                "employee": "HR-EMP-00001",
                "user_id": "on_leave@example.com",
                "first_name": "Test",
                "status": "Active"
            })
            doc.flags.ignore_mandatory = True
            doc.insert(ignore_permissions=True)
            
    def test_resolve_active_user_no_leave(self):
        # User is not on leave, should return the same user
        user = resolve_active_user("Administrator")
        self.assertEqual(user, "Administrator")
        
    @patch("one_fm.api.v1.utils.frappe.get_all")
    def test_resolve_active_user_rerouting(self, mock_get_all):
        # Mock get_all to return a Leave Application showing the user is on leave with a custom_reliever
        mock_get_all.return_value = [{"custom_reliever_": "reliever@example.com"}]
        
        user = resolve_active_user("on_leave@example.com")
        self.assertEqual(user, "reliever@example.com")
