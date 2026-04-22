import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate
from unittest.mock import patch

from one_fm.tests.utils import create_test_company, make_employee
from frappe.workflow.doctype.workflow_action.workflow_action import apply_workflow


def make_timesheet(employee, approver_user, start_date=None, attendance_by_timesheet=1):
    """
    Create a draft Timesheet document for the given employee.

    - ``employee`` must have a valid ``user_id`` set.
    - ``approver_user`` is the *user_id* (email) of the line-manager / approver.
    - A single time-log entry of 8 hours is appended so that total_hours > 0,
      which is required to pass the before_submit guard.
    - ``ignore_permissions=True`` is used throughout because the test context
      runs as Administrator and we are only verifying workflow/assignment logic,
      not permission checks.
    """
    if start_date is None:
        start_date = nowdate()

    from_time = "{} 08:00:00".format(start_date)
    to_time   = "{} 16:00:00".format(start_date)

    timesheet = frappe.get_doc({
        "doctype": "Timesheet",
        "employee": employee,
        "start_date": start_date,
        "end_date": start_date,
        "approver": approver_user,
        "attendance_by_timesheet": attendance_by_timesheet,
        "time_logs": [
            {
                "activity_type": frappe.db.get_value("Activity Type", {}, "name")
                                 or _ensure_activity_type(),
                "from_time": from_time,
                "to_time":   to_time,
                "hours": 8,
            }
        ],
    })
    timesheet.insert(ignore_permissions=True)
    return timesheet


def _ensure_activity_type():
    """Create a minimal Activity Type if none exists (required child-table field)."""
    if not frappe.db.exists("Activity Type", "General"):
        frappe.get_doc({"doctype": "Activity Type", "activity_type": "General"}).insert(
            ignore_permissions=True
        )
    return "General"


class TestTimesheetWorkflow(FrappeTestCase):
    """
    Test suite for the Timesheet workflow transitions and the two Assignment Rules:

    * **Submit Timesheet - Employee**
      assign_condition : workflow_state == "Draft"
      unassign_condition: workflow_state != "Draft"
      field : owner

    * **Approve Timesheet - Approver**
      assign_condition : workflow_state == "Pending Approval"
      unassign_condition: workflow_state != "Pending Approval"
      field : approver
    """

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setUp(self):
        """
        Prepare master data required by every test.
        - Runs as Administrator.
        - Creates '_Test Company' if missing.
        - Creates an employee (owner/submitter) and a separate approver employee.
        - Cleans up any leftover Timesheets from previous runs.
        """
        frappe.set_user("Administrator")
        create_test_company()

        # Employee who owns / submits the timesheet
        self.employee = make_employee(
            "ts_owner@testcompany.com", company="_Test Company"
        )
        # Employee who is the approver
        self.approver_employee = make_employee(
            "ts_approver@testcompany.com", company="_Test Company"
        )

        # Ensure approver's user_id is set
        self.approver_user = frappe.db.get_value(
            "Employee", self.approver_employee.name, "user_id"
        )
        self.owner_user = frappe.db.get_value(
            "Employee", self.employee.name, "user_id"
        )

        # Point the employee's reports_to to the approver so fetch_approver works
        frappe.db.set_value(
            "Employee", self.employee.name, "reports_to", self.approver_employee.name
        )

        # Clean up stale timesheets from this employee (previous test runs)
        frappe.db.delete("Timesheet", {"employee": self.employee.name})

        _ensure_activity_type()

    def tearDown(self):
        """
        Wipe all Timesheets created during the test and rollback any pending
        transaction so the next test starts from a clean state.
        """
        frappe.db.delete("Timesheet", {"employee": self.employee.name})
        frappe.db.delete("ToDo", {
            "reference_type": "Timesheet",
        })
        frappe.db.rollback()
        frappe.set_user("Administrator")

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _create_draft_timesheet(self):
        """Create and return a fresh Draft timesheet for self.employee."""
        return make_timesheet(
            employee=self.employee.name,
            approver_user=self.approver_user,
        )

    # ------------------------------------------------------------------
    # Test 1
    # ------------------------------------------------------------------

    @patch("frappe.sendmail")
    def test_submit_for_approval_creates_todo_for_approver(self, mock_sendmail):
        """
        Scenario: Employee submits a timesheet for approval.

        Expected:
        - workflow_state transitions from "Draft" → "Pending Approval".
        - Assignment Rule 'Approve Timesheet -Approver' fires and creates an
          Open ToDo allocated to the approver's user account.
        """
        mock_sendmail.return_value = None

        timesheet = self._create_draft_timesheet()

        # Transition: Draft → Pending Approval
        apply_workflow(timesheet, "Submit for Review")
        timesheet.reload()

        self.assertEqual(
            timesheet.workflow_state,
            "Pending Approval",
            "Workflow state should be 'Pending Approval' after Submit for Review",
        )

        # Verify ToDo was created for the approver
        todo = frappe.db.get_value(
            "ToDo",
            {
                "reference_type": "Timesheet",
                "reference_name": timesheet.name,
                "allocated_to": self.approver_user,
                "status": "Open",
            },
            "name",
        )
        self.assertTrue(
            todo,
            "An Open ToDo should be created for the approver when the timesheet "
            "enters 'Pending Approval' state",
        )

        # Also verify DB truth
        db_todo_status = frappe.db.get_value("ToDo", todo, "status")
        self.assertEqual(
            db_todo_status,
            "Open",
            "The ToDo record in the database should have status 'Open'",
        )

    # ------------------------------------------------------------------
    # Test 2
    # ------------------------------------------------------------------

    @patch("frappe.sendmail")
    def test_return_to_draft_creates_todo_for_owner(self, mock_sendmail):
        """
        Scenario: Approver returns the timesheet to Draft (rejects / requests changes).

        Expected:
        - workflow_state transitions Draft → Pending Approval → Draft.
        - When back in 'Draft', Assignment Rule 'Submit Timesheet -Employee' fires
          and creates (or re-creates) an Open ToDo for the document owner.
        - The Approver's ToDo (allocated during Pending Approval) should no longer
          be Open (it is Cancelled by the unassign_condition).
        """
        mock_sendmail.return_value = None

        timesheet = self._create_draft_timesheet()
        owner_user = timesheet.owner  # the frappe user who created the doc

        # Draft → Pending Approval
        apply_workflow(timesheet, "Submit for Review")
        timesheet.reload()

        # Pending Approval → Draft (Return To Draft)
        apply_workflow(timesheet, "Return To Draft")
        timesheet.reload()

        self.assertEqual(
            timesheet.workflow_state,
            "Draft",
            "Workflow state should return to 'Draft' after 'Return To Draft' action",
        )

        # A new Open ToDo should now be allocated to the timesheet OWNER
        todo = frappe.db.get_value(
            "ToDo",
            {
                "reference_type": "Timesheet",
                "reference_name": timesheet.name,
                "allocated_to": owner_user,
                "status": "Open",
            },
            "name",
        )
        self.assertTrue(
            todo,
            "An Open ToDo should be created for the timesheet owner when the "
            "document is returned to 'Draft' state",
        )

        # Verify approver's ToDo is NOT open any more (was unassigned)
        approver_todo_open = frappe.db.get_value(
            "ToDo",
            {
                "reference_type": "Timesheet",
                "reference_name": timesheet.name,
                "allocated_to": self.approver_user,
                "status": "Open",
            },
            "name",
        )
        self.assertFalse(
            approver_todo_open,
            "The approver's ToDo should NOT be Open after the document leaves "
            "'Pending Approval' (unassign_condition should close it)",
        )

    # ------------------------------------------------------------------
    # Test 3
    # ------------------------------------------------------------------

    @patch("frappe.sendmail")
    def test_approve_cancels_approver_todo(self, mock_sendmail):
        """
        Scenario: Approver approves the timesheet.

        Expected:
        - workflow_state transitions Draft → Pending Approval → Approved.
        - Once the document leaves 'Pending Approval', the unassign_condition
          of 'Approve Timesheet -Approver' triggers and the approver's ToDo
          status becomes 'Cancelled'.
        """
        mock_sendmail.return_value = None

        timesheet = self._create_draft_timesheet()

        # Draft → Pending Approval
        apply_workflow(timesheet, "Submit for Review")
        timesheet.reload()

        # Capture the approver ToDo name while it is still in Pending Approval
        approver_todo = frappe.db.get_value(
            "ToDo",
            {
                "reference_type": "Timesheet",
                "reference_name": timesheet.name,
                "allocated_to": self.approver_user,
            },
            "name",
        )

        # Pending Approval → Approved
        apply_workflow(timesheet, "Approve")
        timesheet.reload()

        self.assertEqual(
            timesheet.workflow_state,
            "Approved",
            "Workflow state should be 'Approved' after 'Approve' action",
        )

        # After leaving Pending Approval the ToDo for the approver must be Cancelled
        self.assertTrue(
            approver_todo,
            "A ToDo for the approver must have been created in Pending Approval state",
        )

        todo_status = frappe.db.get_value("ToDo", approver_todo, "status")
        self.assertEqual(
            todo_status,
            "Cancelled",
            "The approver's ToDo should be 'Cancelled' once the timesheet is "
            "approved and leaves 'Pending Approval' state",
        )

        # Double-check via DB query (no leftover Open todo for approver)
        open_approver_todo = frappe.db.get_value(
            "ToDo",
            {
                "reference_type": "Timesheet",
                "reference_name": timesheet.name,
                "allocated_to": self.approver_user,
                "status": "Open",
            },
            "name",
        )
        self.assertFalse(
            open_approver_todo,
            "No Open ToDo should remain for the approver after the timesheet is approved",
        )
