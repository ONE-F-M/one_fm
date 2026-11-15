# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""Tests for the Expected Start/End Date validation on Project.

Background (HD Ticket 1878243): a contract saved with an inverted date pair wrote
`expected_start_date` > `expected_end_date` onto the Project through `db.set_value`,
which bypasses validation. Because both fields are read-only for External projects,
the stored pair could never be repaired from the form and every later save of the
project — including an unrelated Project Manager change — was rejected.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate


class TestProjectExpectedDates(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.project = frappe.get_doc({
            "doctype": "Project",
            "project_name": "Test Project Expected Dates",
            "project_type": "External",
            "expected_start_date": nowdate(),
            "expected_end_date": add_days(nowdate(), 30),
            # POC is mandatory for External projects (validate_poc_list)
            "poc": [{"designation": "Test POC"}],
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.db.rollback()

    def test_rejects_inverted_dates_on_insert(self):
        """A new project may not be created with End Date before Start Date."""
        project = frappe.get_doc({
            "doctype": "Project",
            "project_name": "Test Project Inverted Dates",
            "expected_start_date": nowdate(),
            "expected_end_date": add_days(nowdate(), -10),
        })
        self.assertRaises(frappe.ValidationError, project.insert, ignore_permissions=True)

    def test_rejects_inverted_dates_when_a_date_is_changed(self):
        """Editing a date into an invalid pair still throws."""
        self.project.expected_end_date = add_days(self.project.expected_start_date, -1)
        self.assertRaises(frappe.ValidationError, self.project.save, ignore_permissions=True)

    def test_unrelated_edit_allowed_on_stored_inverted_dates(self):
        """A pre-existing inverted pair must not block an unrelated field change.

        The dates are read-only for External projects, so the user has no way to fix
        them here — they are corrected on the linked contract instead.
        """
        # Simulate what Contracts.update_project_start_end_date used to write.
        frappe.db.set_value(
            "Project", self.project.name,
            {
                "expected_start_date": nowdate(),
                "expected_end_date": add_days(nowdate(), -3)
            },
            update_modified=False
        )

        project = frappe.get_doc("Project", self.project.name)
        project.notes = "Project Manager change should not be blocked"
        project.save(ignore_permissions=True)

        self.assertEqual(
            frappe.db.get_value("Project", self.project.name, "notes"),
            "Project Manager change should not be blocked"
        )
