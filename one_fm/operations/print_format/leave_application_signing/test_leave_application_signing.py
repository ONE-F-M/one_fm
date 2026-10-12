import frappe
from frappe.modules.import_file import import_file_by_path
from frappe.tests.utils import FrappeTestCase

PRINT_FORMAT = "Leave Application Signing"
AUGUST_MODIFIED = "2026-08-16 02:00:00"


class TestLeaveApplicationSigning(FrappeTestCase):
    def test_migrate_replaces_the_august_copy_of_the_format(self):
        path = frappe.get_app_path(
            "one_fm", "operations", "print_format", "leave_application_signing", "leave_application_signing.json"
        )
        frappe.db.set_value(
            "Print Format", PRINT_FORMAT, {"html": "stale", "modified": AUGUST_MODIFIED}, update_modified=False
        )

        import_file_by_path(path)

        self.assertIn(".rtl .fill", frappe.db.get_value("Print Format", PRINT_FORMAT, "html"))
