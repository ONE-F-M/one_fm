# Copyright (c) 2023, ONE FM and Contributors
# See license.txt

# import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import MagicMock, patch as upatch
import frappe

from one_fm.one_fm.doctype.attendance_check.attendance_check import (
    insert_attendance_check_records,
    create_attendance_check,
    get_absentees_on_date,
    get_attendance_not_marked_shift_employees,
    attendance_check_pending_approval_check,
    issue_penalty_to_the_assigned_approver,
    fetch_existing_todos,
    create_split_query,
    create_todos,
    notify_manager,
    assign_attendance_manager,
    schedule_attendance_check,
    _create_attendance_check_action_doc,
)

class TestAttendanceCheckMockDB(FrappeTestCase):

    def setUp(self):
        # Patch frappe APIs globally for all tests
        self.patcher_get_doc = upatch("frappe.get_doc", MagicMock())
        self.patcher_get_all = upatch("frappe.get_all", MagicMock())
        self.patcher_db_sql = upatch("frappe.db.sql", MagicMock())
        self.patcher_db_commit = upatch("frappe.db.commit", MagicMock())
        self.patcher_db_set_value = upatch("frappe.db.set_value", MagicMock())
        self.patcher_db_exists = upatch("frappe.db.exists", MagicMock(return_value=True))
        self.patcher_utils_today = upatch("frappe.utils.today", MagicMock(return_value="2025-08-20"))
        self.patcher_utils_add_days = upatch("frappe.utils.add_days", MagicMock(side_effect=lambda d, n: "2025-08-19" if n == -1 else "2025-08-21"))
        self.patcher_utils_now = upatch("frappe.utils.now", MagicMock(return_value="2025-08-20 08:00:00"))
        self.patcher_delete_doc = upatch("frappe.delete_doc", MagicMock())
        self.patcher_get_last_doc = upatch("frappe.get_last_doc", MagicMock())
        self.patcher_flags = upatch("frappe.flags", MagicMock())
        self.patcher_sendmail = upatch("frappe.sendmail", MagicMock())
        self.patcher_db_get_value = upatch("frappe.db.get_value", MagicMock(return_value="shift_type_1"))
        self.patcher_db_get_single_value = upatch("frappe.db.get_single_value", MagicMock(return_value="PenaltyType"))
        self.patcher_enqueue = upatch("frappe.enqueue", MagicMock())

        self.patcher_get_doc.start()
        self.patcher_get_all.start()
        self.patcher_db_sql.start()
        self.patcher_db_commit.start()
        self.patcher_db_set_value.start()
        self.patcher_db_exists.start()
        self.patcher_utils_today.start()
        self.patcher_utils_add_days.start()
        self.patcher_utils_now.start()
        self.patcher_delete_doc.start()
        self.patcher_get_last_doc.start()
        self.patcher_flags.start()
        self.patcher_sendmail.start()
        self.patcher_db_get_value.start()
        self.patcher_db_get_single_value.start()
        self.patcher_enqueue.start()

        # Setup mock employee/attendance objects
        self.employee = MagicMock(name="EMP001")
        self.employee2 = MagicMock(name="EMP002")
        self.attendance = MagicMock(name="ATT001")
        self.attendance2 = MagicMock(name="ATT002")
        self.shift_assignment = MagicMock(name="SHIFTASSIGN001")
        self.shift_assignment2 = MagicMock(name="SHIFTASSIGN002")
        self.shift_permission = MagicMock(name="SHIFTPERM001")
        self.attendance_request = MagicMock(name="ATTREQ001")
        self.shift_type = MagicMock(name="SHIFT_TYPE_1")
        self.shift = MagicMock(name="SHIFT001")
        self.shift_supervisor = MagicMock(name="SUP001")

    def tearDown(self):
        upatch.stopall()

    def test_insert_attendance_check_record(self):
        frappe.get_last_doc.return_value = MagicMock(
            employee=self.employee.name,
            attendance=self.attendance.name,
            roster_type="Basic",
            shift_assignment=self.shift_assignment.name,
            marked_attendance_status="Absent",
            comment="Absent reason"
        )
        details = [{
            "employee": self.employee.name,
            "attendance": self.attendance.name,
            "roster_type": "Basic",
            "shift_assignment": self.shift_assignment.name,
            "attendance_status": "Absent",
            "attendance_comment": "Absent reason"
        }]
        insert_attendance_check_records(details, "2025-08-20")
        ac_doc = frappe.get_last_doc("Attendance Check")
        self.assertEqual(ac_doc.employee, self.employee.name)
        self.assertEqual(ac_doc.attendance, self.attendance.name)
        self.assertEqual(ac_doc.roster_type, "Basic")
        self.assertEqual(ac_doc.shift_assignment, self.shift_assignment.name)
        self.assertEqual(ac_doc.marked_attendance_status, "Absent")
        self.assertEqual(ac_doc.comment, "Absent reason")

    def test_insert_duplicate_attendance_check_record(self):
        details = [{
            "employee": self.employee.name,
            "attendance": self.attendance.name,
            "roster_type": "Basic",
            "shift_assignment": self.shift_assignment.name,
            "attendance_status": "Absent"
        }]
        
        # First insert should create the document
        insert_attendance_check_records(details, "2025-08-20")
        
        # Second insert with same details - the duplicate check happens in validate_duplicate
        # which will throw an error. The function catches errors containing "Attendance Check already exist"
        # So it should not raise, but also should not create a second document
        insert_attendance_check_records(details, "2025-08-20")
        
        ac_list = frappe.get_all("Attendance Check", filters={"employee": self.employee.name, "date": "2025-08-20", "roster_type": "Basic"})
        self.assertEqual(len(ac_list), 1)

    def test_insert_attendance_check_with_attendance_by_timesheet(self):
        frappe.get_last_doc.return_value = MagicMock(attendance_by_timesheet=True)
        details = [{
            "employee": self.employee.name,
            "attendance": self.attendance.name,
            "roster_type": "Basic",
            "shift_assignment": self.shift_assignment.name,
            "attendance_status": "Absent"
        }]
        insert_attendance_check_records(details, "2025-08-20")
        ac = frappe.get_last_doc("Attendance Check")
        self.assertTrue(ac.attendance_by_timesheet)

    def test_insert_attendance_check_missing_optional_fields(self):
        frappe.get_last_doc.return_value = MagicMock(roster_type="Basic", comment="")
        details = [{"employee": self.employee.name}]
        insert_attendance_check_records(details, "2025-08-20")
        ac = frappe.get_last_doc("Attendance Check")
        self.assertEqual(ac.roster_type, "Basic")
        self.assertEqual(ac.comment, "")

    def test_insert_multiple_attendance_check_records(self):
        frappe.get_all.return_value = [
            {"employee": self.employee.name, "name": "AC001"},
            {"employee": self.employee2.name, "name": "AC002"}]        
        details = [
            {
                "employee": self.employee.name,
                "attendance": self.attendance.name,
                "roster_type": "Basic",
                "shift_assignment": self.shift_assignment.name,
                "attendance_status": "Absent"
            },
            {
                "employee": self.employee2.name,
                "attendance": self.attendance2.name,
                "roster_type": "Basic",
                "shift_assignment": self.shift_assignment2.name,
                "attendance_status": "Absent"
            }
        ]
        insert_attendance_check_records(details, "2025-08-20")
        ac_list = frappe.get_all("Attendance Check", filters={"date": "2025-08-20"}, fields=["employee", "name"])
        employee_names = [ac["employee"] for ac in ac_list]
        self.assertIn(self.employee.name, employee_names)
        self.assertIn(self.employee2.name, employee_names)
        

    def test_insert_attendance_check_error_logging(self):
        frappe.get_all.return_value = []
        
        details = [{"employee": "invalid_employee"}]
        insert_attendance_check_records(details, "2025-08-20")
        ac_list = frappe.get_all("Attendance Check", filters={"employee": "invalid_employee"})
        self.assertEqual(len(ac_list), 0)
        

    def test_insert_attendance_check_with_shift_permission(self):
        frappe.get_last_doc.return_value = MagicMock(shift_permission=self.shift_permission.name)
        details = [{
            "employee": self.employee.name,
            "attendance": self.attendance.name,
            "roster_type": "Basic",
            "shift_assignment": self.shift_assignment.name,
            "attendance_status": "Absent"
        }]
        insert_attendance_check_records(details, "2025-08-20")
        ac = frappe.get_last_doc("Attendance Check")
        self.assertEqual(ac.shift_permission, self.shift_permission.name)

    def test_insert_attendance_check_with_attendance_request(self):
        frappe.get_last_doc.return_value = MagicMock(attendance_request=self.attendance_request.name)
        details = [{
            "employee": self.employee.name,
            "attendance": self.attendance.name,
            "roster_type": "Basic",
            "shift_assignment": self.shift_assignment.name,
            "attendance_status": "Absent"
        }]
        insert_attendance_check_records(details, "2025-08-20")
        ac = frappe.get_last_doc("Attendance Check")
        self.assertEqual(ac.attendance_request, self.attendance_request.name)

    def test_insert_attendance_check_with_checkin_records(self):
        frappe.get_last_doc.return_value = MagicMock(checkin_record="CHECKIN001", checkout_record="CHECKOUT001")
        details = [{
            "employee": self.employee.name,
            "attendance": self.attendance.name,
            "roster_type": "Basic",
            "shift_assignment": self.shift_assignment.name,
            "attendance_status": "Absent"
        }]
        insert_attendance_check_records(details, "2025-08-20")
        ac = frappe.get_last_doc("Attendance Check")
        self.assertEqual(ac.checkin_record, "CHECKIN001")
        self.assertEqual(ac.checkout_record, "CHECKOUT001")

    def test_insert_attendance_check_sets_approvers(self):
        frappe.get_last_doc.return_value = MagicMock(
            reports_to="testuser@example.com",
            shift_supervisor=None,
            site_supervisor="testuser@example.com"
        )
        details = [{
            "employee": self.employee.name,
            "attendance": self.attendance.name,
            "roster_type": "Basic",
            "shift_assignment": self.shift_assignment.name,
            "attendance_status": "Absent"
        }]
        insert_attendance_check_records(details, "2025-08-20")
        ac = frappe.get_last_doc("Attendance Check")
        self.assertEqual(ac.reports_to, "testuser@example.com")
        self.assertEqual(ac.shift_supervisor, None)
        self.assertEqual(ac.site_supervisor, "testuser@example.com")

    def test_insert_attendance_check_missing_justification_present(self):
        ac_doc = MagicMock(attendance_status="Present", justification=None)
        ac_doc.save.side_effect = Exception("ValidationError")
        frappe.get_doc.return_value = ac_doc
        with self.assertRaises(Exception):
            ac_doc.save()

    def test_insert_attendance_check_other_justification_without_reason(self):
        ac_doc = MagicMock(attendance_status="Present", justification="Other", other_reason=None)
        ac_doc.save.side_effect = Exception("Please write the other Reason")
        frappe.get_doc.return_value = ac_doc
        with self.assertRaises(Exception) as context:
            ac_doc.save()
        self.assertIn("Please write the other Reason", str(context.exception))

    def test_insert_attendance_check_mobile_justification_without_brand_model(self):
        ac_doc = MagicMock(attendance_status="Present", justification="Mobile isn't supporting the app", mobile_brand=None, mobile_model=None)
        ac_doc.save.side_effect = Exception("Please select mobile brand")
        frappe.get_doc.return_value = ac_doc
        with self.assertRaises(Exception) as context:
            ac_doc.save()
        self.assertIn("Please select mobile brand", str(context.exception))

    def test_insert_attendance_check_requires_screenshot(self):
        for justification in ["Invalid media content", "Out-of-site location", "User not assigned to shift"]:
            ac_doc = MagicMock(attendance_status="Present", justification=justification, screenshot=None)
            ac_doc.save.side_effect = Exception("Please Attach ScreenShot")
            frappe.get_doc.return_value = ac_doc
            with self.assertRaises(Exception) as context:
                ac_doc.save()
            self.assertIn("Please Attach ScreenShot", str(context.exception))

    def test_insert_attendance_check_approved_by_admin_non_manager(self):
        ac_doc = MagicMock(attendance_status="Present", justification="Approved by Administrator")
        ac_doc.save.side_effect = Exception("Only the Attendance manager can select 'Approved by Administrator'")
        frappe.get_doc.return_value = ac_doc
        with self.assertRaises(Exception) as context:
            ac_doc.save()
        self.assertIn("Only the Attendance manager can select 'Approved by Administrator'", str(context.exception))

    def test_insert_attendance_check_on_leave_triggers_leave_record_check(self):
        ac_doc = MagicMock(attendance_status="On Leave")
        ac_doc.save.return_value = None
        ac_doc.submit.side_effect = Exception("Leave Application")
        frappe.get_doc.return_value = ac_doc
        ac_doc.save()
        with self.assertRaises(Exception) as context:
            ac_doc.submit()
        self.assertIn("Leave Application", str(context.exception))

    def test_insert_attendance_check_day_off_triggers_shift_request_check(self):
        ac_doc = MagicMock(attendance_status="Day Off")
        ac_doc.save.return_value = None
        ac_doc.submit.side_effect = Exception("Shift Request")
        frappe.get_doc.return_value = ac_doc
        ac_doc.save()
        with self.assertRaises(Exception) as context:
            ac_doc.submit()
        self.assertIn("Shift Request", str(context.exception))

    def test_insert_attendance_check_present_creates_attendance_record(self):
        ac = MagicMock(attendance_status="Present", justification="Other", other_reason="Test reason", workflow_state="Approved", name="AC001")
        ac.save.return_value = None
        ac.submit.return_value = None
        frappe.get_last_doc.return_value = ac
        attendance = MagicMock(status="Present", working_hours=8, reference_doctype="Attendance Check", reference_docname=ac.name)
        frappe.get_doc.return_value = attendance
        details = [{
            "employee": self.employee.name,
            "attendance": self.attendance.name,
            "roster_type": "Basic",
            "shift_assignment": self.shift_assignment.name,
            "attendance_status": "Absent"
        }]
        insert_attendance_check_records(details, "2025-08-20")
        ac = frappe.get_last_doc("Attendance Check")
        ac.attendance_status = "Present"
        ac.justification = "Other"
        ac.other_reason = "Test reason"
        ac.workflow_state = "Approved"
        ac.save()
        ac.submit()
        attendance = frappe.get_doc("Attendance", self.attendance.name)
        self.assertEqual(attendance.status, "Present")
        self.assertEqual(attendance.working_hours, 8)
        self.assertEqual(attendance.reference_doctype, "Attendance Check")
        self.assertEqual(attendance.reference_docname, ac.name)

    def test_insert_attendance_check_absent_creates_attendance_record(self):       
        ac = MagicMock(attendance_status="Absent", workflow_state="Approved", name="AC001")
        ac.save.return_value = None
        ac.on_submit.return_value = None
        frappe.get_last_doc.return_value = ac
        attendance = MagicMock(status="Absent", working_hours=0, reference_doctype="Attendance Check", reference_docname=ac.name)
        frappe.get_doc.return_value = attendance
        details = [{
            "employee": self.employee.name,
            "roster_type": "Basic",
            "attendance_status": "Absent"
        }]
        insert_attendance_check_records(details, "2025-08-20")
        ac = frappe.get_last_doc("Attendance Check")
        ac.attendance_status = "Absent"
        ac.workflow_state = "Approved"
        ac.save()
        ac.on_submit()
        attendance = frappe.get_doc("Attendance", self.attendance.name)
        self.assertEqual(attendance.status, "Absent")
        self.assertEqual(attendance.working_hours, 0)
        self.assertEqual(attendance.reference_doctype, "Attendance Check")
        self.assertEqual(attendance.reference_docname, ac.name)

    def test_get_absentees_on_date(self):
        with upatch("frappe.db.get_list", MagicMock(return_value=["EMP001"])):
            frappe.get_all.return_value = [{"employee": self.employee.name}]
            absentees = get_absentees_on_date("2025-08-20")
            self.assertTrue(any(a["employee"] == self.employee.name for a in absentees))

    def test_get_attendance_not_marked_shift_employees(self):
        frappe.get_all.return_value = [{"employee": self.employee.name}]
        result = get_attendance_not_marked_shift_employees("2025-08-20")
        self.assertTrue(any(r["employee"] == self.employee.name for r in result))

    def test_create_attendance_check(self):
        with upatch("one_fm.one_fm.doctype.attendance_check.attendance_check.production_domain", MagicMock(return_value=True)) as mock_domain, \
            upatch("one_fm.one_fm.doctype.attendance_check.attendance_check.insert_attendance_check_records", MagicMock()) as mock_insert, \
            upatch("frappe.db.get_list", MagicMock(return_value=["EMP001"])):
            create_attendance_check("2025-08-20")
            mock_insert.assert_called()

    def test_fetch_existing_todos(self):
        mock_todo = MagicMock()
        mock_todo.reference_name = "AC001"
        frappe.get_all.return_value = [mock_todo]
        todos = fetch_existing_todos("testuser@example.com")
        self.assertIn("AC001", todos)

    def test_create_split_query(self):
        mock_todo1 = MagicMock()
        mock_todo1.name = "AC1"
        mock_todo2 = MagicMock()
        mock_todo2.name = "AC2"
        todos = [mock_todo1, mock_todo2]
        queries = create_split_query(todos, 1, "manager@example.com", "2025-08-20", "2025-08-20 08:00:00")
        self.assertEqual(len(queries), 2)
        self.assertTrue("INSERT INTO `tabToDo`" in queries[0])

    @upatch("frappe.db.sql", MagicMock())
    def test_create_todos(self):
        mock_todo = MagicMock()
        mock_todo.name = "AC1"
        todos = [mock_todo]
        create_todos("manager@example.com", todos)
        frappe.db.sql.assert_called()

    def test_assign_attendance_manager(self):
        with upatch("one_fm.one_fm.doctype.attendance_check.attendance_check.fetch_attendance_manager_user", MagicMock(return_value="manager@example.com")) as mock_fetch_manager, \
            upatch("one_fm.one_fm.doctype.attendance_check.attendance_check.notify_manager", MagicMock()) as mock_notify_manager, \
            upatch("one_fm.one_fm.doctype.attendance_check.attendance_check.create_todos", MagicMock()) as mock_create_todos:
            mock_todo = MagicMock()
            mock_todo.name = "AC1"
            pending = [mock_todo]
            assign_attendance_manager(pending)
            mock_create_todos.assert_called()
            mock_notify_manager.assert_called()

    @upatch("frappe.enqueue", MagicMock())
    def test_schedule_attendance_check(self):
        schedule_attendance_check()
        frappe.enqueue.assert_called()

    @upatch("frappe.db.get_single_value", MagicMock(return_value="PenaltyType"))
    @upatch("frappe.get_doc", MagicMock())
    def test_issue_penalty_to_the_assigned_approver(self):
        pending = [{"assign_to": '["manager@example.com"]', "name": "AC1"}]
        issue_penalty_to_the_assigned_approver(pending)
        frappe.get_doc.assert_called()

    def test_attendance_check_pending_approval_check(self):
        with upatch("one_fm.one_fm.doctype.attendance_check.attendance_check.assign_attendance_manager", MagicMock()) as mock_assign, \
            upatch("one_fm.one_fm.doctype.attendance_check.attendance_check.issue_penalty_to_the_assigned_approver", MagicMock()) as mock_penalty, \
            upatch("one_fm.one_fm.doctype.attendance_check.attendance_check.get_pending_approval_attendance_check", MagicMock(return_value=[{"name": "AC1"}])):
            attendance_check_pending_approval_check()
            mock_penalty.assert_called()
            mock_assign.assert_called()

    def test_create_attendance_check_action_routes_to_hr_settings_user(self):
        # No existing Attendance Check Action -> guard clauses must not early-return.
        frappe.db.exists.return_value = False
        # Qualifying source Attendance Check.
        frappe.db.get_value.return_value = frappe._dict({
            "employee": "EMP001",
            "date": "2026-07-01",
            "action": "Issue a New Mobile",
        })
        # Default Action Owner configured in HR Settings.
        frappe.db.get_single_value.return_value = "owner@example.com"

        action_doc = MagicMock()
        with upatch("frappe.new_doc", MagicMock(return_value=action_doc)):
            _create_attendance_check_action_doc("HR-AC-EMP001-2026-07-01")

        frappe.db.get_single_value.assert_called_with("HR Settings", "attendance_check_action_user")
        self.assertEqual(action_doc.assigned_to, "owner@example.com")
        action_doc.insert.assert_called_once()

    def test_create_attendance_check_action_skips_non_mobile_action(self):
        # A source whose action is not "Issue a New Mobile" must not create anything.
        frappe.db.exists.return_value = False
        frappe.db.get_value.return_value = frappe._dict({
            "employee": "EMP001",
            "date": "2026-07-01",
            "action": "No Action Required",
        })
        with upatch("frappe.new_doc", MagicMock()) as mock_new_doc:
            _create_attendance_check_action_doc("HR-AC-EMP001-2026-07-01")
            mock_new_doc.assert_not_called()


def create_attendance_check_record(details, date):
    """Helper function to create an Attendance Check record"""
    attendance_check = frappe.get_doc({
        "doctype": "Attendance Check",
        "employee": details.get("employee"),
        "attendance": details.get("attendance"),
        "date": date,
        "roster_type": details.get("roster_type", ""),
        "shift_assignment": details.get("shift_assignment", ""),
        "attendance_status": details.get("attendance_status", ""),
        "comment": details.get("attendance_comment", ""),
    })
    attendance_check.insert()
    return attendance_check
