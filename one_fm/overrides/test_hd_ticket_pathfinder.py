import frappe
import unittest
from one_fm.overrides.hd_ticket import create_process_change_request


class TestHDTicketProcessChangeRequest(unittest.TestCase):
    def setUp(self):
        # Create a dummy HD Ticket Type with initiate_process_change_request flag
        if not frappe.db.exists("HD Ticket Type", "Enhancement"):
            frappe.get_doc({
                "doctype": "HD Ticket Type",
                "name": "Enhancement",
            }).insert(ignore_permissions=True)

        frappe.db.set_value("HD Ticket Type", "Enhancement", "initiate_process_change_request", 1)

        # Create a dummy HD Ticket
        self.hd_ticket = frappe.get_doc({
            "doctype": "HD Ticket",
            "subject": "Test Ticket for Process Change Request",
            "description": "Test Description",
            "ticket_type": "Enhancement",
            "status": "Open",
            "priority": "Medium",
            "raised_by": "Administrator"
        }).insert(ignore_permissions=True)

        # Ensure roles exist
        if not frappe.db.exists("Role", "Business Analyst"):
            frappe.get_doc({"doctype": "Role", "role_name": "Business Analyst"}).insert()
        if not frappe.db.exists("Role", "Process Owner"):
            frappe.get_doc({"doctype": "Role", "role_name": "Process Owner"}).insert()

    def tearDown(self):
        frappe.set_user("Administrator")
        # Clean up PCRs linked to this ticket
        for pcr in frappe.get_all("Process Change Request", filters={"hd_ticket": self.hd_ticket.name}):
            frappe.delete_doc("Process Change Request", pcr.name, ignore_permissions=True)
        frappe.delete_doc("HD Ticket", self.hd_ticket.name, ignore_permissions=True)

    def test_create_process_change_request_permission(self):
        # Test with no roles — Guest should be denied
        frappe.set_user("Guest")
        with self.assertRaises(frappe.ValidationError):
            create_process_change_request(self.hd_ticket.name)

        # Test with Business Analyst role
        user = "test_ba@example.com"
        if not frappe.db.exists("User", user):
            frappe.get_doc({
                "doctype": "User",
                "email": user,
                "first_name": "Test BA",
                "roles": [{"role": "Business Analyst"}]
            }).insert(ignore_permissions=True)

        frappe.set_user(user)
        pcr_name = create_process_change_request(self.hd_ticket.name)
        self.assertTrue(frappe.db.exists("Process Change Request", pcr_name))

        # Clean up for next test
        frappe.set_user("Administrator")
        frappe.delete_doc("Process Change Request", pcr_name, ignore_permissions=True)

        # Test with Process Owner role
        user_po = "test_po@example.com"
        if not frappe.db.exists("User", user_po):
            frappe.get_doc({
                "doctype": "User",
                "email": user_po,
                "first_name": "Test PO",
                "roles": [{"role": "Process Owner"}]
            }).insert(ignore_permissions=True)

        frappe.set_user(user_po)
        pcr_name_po = create_process_change_request(self.hd_ticket.name)
        self.assertTrue(frappe.db.exists("Process Change Request", pcr_name_po))

    def test_create_duplicate_pcr(self):
        frappe.set_user("Administrator")
        user = frappe.get_doc("User", "Administrator")
        user.add_roles("Business Analyst")

        pcr_name = create_process_change_request(self.hd_ticket.name)

        with self.assertRaises(frappe.ValidationError):
            create_process_change_request(self.hd_ticket.name)
