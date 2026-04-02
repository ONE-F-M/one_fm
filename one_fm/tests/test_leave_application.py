
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate
from unittest.mock import patch, MagicMock

from one_fm.tests.utils import (
    get_test_employee, get_test_leave_type, create_test_leave_allocation,
    create_test_company, make_leave_application, make_employee, create_test_bed_space_type,
    create_test_accommodation_space_type, create_test_accommodation_unit, 
    create_test_accommodation_space, create_test_bed
)
from one_fm.one_fm.doctype.attendance_check.test_attendance_check import create_attendance_check_record
from one_fm.overrides.leave_application import update_employee_status_after_leave
from frappe.workflow.doctype.workflow_action.workflow_action import apply_workflow

class TestLeaveApplicationOverride(FrappeTestCase):
    """
    Complete test suite for the approve_attendance_check method from Leave Application

    This method:
    1. Finds all draft Attendance Check records for the employee within the leave period
    2. Updates their attendance_status to 'On Leave'
    3. Applies workflow approval to each Attendance Check
    4. Handles errors gracefully and logs them
    """

    def setUp(self):
        """Set up test data before each test"""
        frappe.set_user("Administrator")
        create_test_company()
        self.leave_type = get_test_leave_type()

        # Patch user throttle check to allow rapid test user creation
        self.throttle_patch = patch('frappe.core.doctype.user.user.throttle_user_creation')
        self.mock_throttle = self.throttle_patch.start()

    def create_test_employee_with_allocation(self, user_email=None):
        """Create a fresh employee with leave allocation for each test"""
        if user_email is None:
            user_email = f"test_emp_{frappe.utils.random_string(8)}@example.com"

        employee = make_employee(user_email, company="_Test Company")

        # Clean up any existing test data for this employee
        frappe.db.delete("Accommodation Checkin Checkout", {"employee": employee.name})
        frappe.db.delete("Attendance Check", {"employee": employee.name})
        frappe.db.delete("Leave Application", {"employee": employee.name})
        frappe.db.delete("Leave Allocation", {"employee": employee.name})

        # Create fresh leave allocation
        create_test_leave_allocation(
            employee=employee,
            leave_type=self.leave_type,
            from_date=add_days(nowdate(), -30),
            to_date=add_days(nowdate(), 60),
            new_leaves_allocated=75
        )
        
        return employee
    
    def tearDown(self):
        """Clean up after each test"""
        # Stop the throttle patch
        self.throttle_patch.stop()
        
        # Clean up test accommodation records (all test employees cleaned up with rollback)
        frappe.db.delete("Accommodation", {"accommodation": "Test Accommodation"})
        
        # Rollback will clean up all employee data, leave records, and comments
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _get_or_create_test_accommodation(self):
        """Helper to get or create test accommodation"""
        if not frappe.db.exists("Accommodation", "Test Accommodation"):
            test_accommodation = frappe.get_doc({
                "doctype": "Accommodation",
                "accommodation": "Test Accommodation",
                "company": "_Test Company",
                "capacity": 100,
                "type": "Building",
                "total_no_of_accommodation_unit": 10,
            }).insert(ignore_permissions=True)
            return test_accommodation
        else:
            return frappe.get_doc("Accommodation", "Test Accommodation")
    
    def _create_draft_attendance_check(self, employee_name, date, attendance_status="Absent"):
        """Helper to create a draft attendance check"""
        att_check_filters = {
            "employee": employee_name,
            "attendance_status": attendance_status
        }
        return create_attendance_check_record(att_check_filters, date)

    @patch("frappe.sendmail")
    def test_approve_leave_application_attendance_checks_approval(self, mock_sendmail):
        """Test 1: suite for approve_attendance_check method"""
        mock_sendmail.return_value = None
        employee = self.create_test_employee_with_allocation()
        
        leave_date = add_days(nowdate(), 1)
        attendance_check = self._create_draft_attendance_check(employee.name, leave_date)

        # Create approved leave application
        leave_application = make_leave_application(
            employee.name,
            leave_date,
            leave_date,
            self.leave_type.name
        )
        leave_application.save()

        self.apply_approve_workflow(leave_application)

        # Verify attendance check status updated to 'On Leave'
        attendance_check.reload()
        self.assertEqual(attendance_check.attendance_status, "On Leave")
        
        # Verify workflow applied (docstatus = 1)
        self.assertEqual(attendance_check.docstatus, 1)
        
        # Verify database committed
        db_check = frappe.db.get_value(
            "Attendance Check",
            attendance_check.name,
            ["attendance_status", "docstatus"],
            as_dict=True
        )
        self.assertEqual(db_check.attendance_status, "On Leave")
        self.assertEqual(db_check.docstatus, 1)
    
    @patch("frappe.sendmail")
    def test_approve_leave_application_multiple_attendance_checks_approval(self, mock_sendmail):
        """Test 2: Multi-day leave with multiple draft attendance checks"""
        mock_sendmail.return_value = None
        employee = self.create_test_employee_with_allocation()
        
        from_date = add_days(nowdate(), 1)
        to_date = add_days(nowdate(), 5)

        # Create attendance checks for all days in the range
        attendance_checks = []
        for i in range(5):
            date = add_days(from_date, i)
            att_check = self._create_draft_attendance_check(employee.name, date)
            attendance_checks.append(att_check)

        # Create approved leave application
        leave_application = make_leave_application(
            employee.name,
            from_date,
            to_date,
            self.leave_type.name,
        )

        leave_application.save()

        self.apply_approve_workflow(leave_application)
        
        # Verify all attendance checks are updated
        for att_check in attendance_checks:
            att_check.reload()
            self.assertEqual(att_check.attendance_status, "On Leave")
            self.assertEqual(att_check.docstatus, 1)

    @patch("frappe.sendmail")
    def test_partial_attendance_checks_in_range(self, mock_sendmail):
        """Test 3: Some days have attendance checks, some don't"""
        mock_sendmail.return_value = None
        employee = self.create_test_employee_with_allocation()
        
        from_date = add_days(nowdate(), 1)
        to_date = add_days(nowdate(), 5)

        # Create attendance checks only for days 1, 2
        check_1 = self._create_draft_attendance_check(employee.name, from_date)
        check_2 = self._create_draft_attendance_check(employee.name, add_days(from_date, 1))

        # Create approved leave application
        leave_application = make_leave_application(
            employee.name,
            from_date,
            to_date,
            self.leave_type.name
        )
        leave_application.save()

        self.apply_approve_workflow(leave_application)
        
        # Verify only existing checks are updated
        check_1.reload()
        check_2.reload()
        self.assertEqual(check_1.attendance_status, "On Leave")
        self.assertEqual(check_2.attendance_status, "On Leave")

        # Verify only 2 checks exist
        total_checks = frappe.db.count("Attendance Check", {
            "employee": employee.name,
            "date": ["between", [from_date, to_date]]
        })
        self.assertEqual(total_checks, 2)

    def apply_approve_workflow(self, doc):
        """Helper to apply approve workflow steps"""
        apply_workflow(doc, "Submit for Review")
        apply_workflow(doc, "Approve")

    @patch("frappe.sendmail")
    def test_leave_resumption_non_shift_worker_set_to_active(self, mock_sendmail):
        """Test 4: Non-shift worker status set to Active on resumption date"""
        mock_sendmail.return_value = None
        
        employee = self.create_test_employee_with_allocation()
        
        # Set employee as non-shift worker
        frappe.db.set_value("Employee", employee.name, {
            "shift_working": 0,
            "status": "Vacation"
        })
        
        # Create leave application with today as resumption date
        leave_application = make_leave_application(
            employee.name,
            add_days(nowdate(), -5),
            add_days(nowdate(), -1),
            self.leave_type.name
        )
        leave_application.resumption_date = nowdate()
        leave_application.save()
        self.apply_approve_workflow(leave_application)
        
        frappe.db.commit()
        
        update_employee_status_after_leave()
        
        # Verify employee status changed to Active
        employee_status = frappe.db.get_value("Employee", employee.name, "status")
        self.assertEqual(employee_status, "Active", 
                        "Non-shift worker should be set to Active on resumption date")
        
        # Verify comment was created
        comment = frappe.db.exists("Comment", {
            "reference_doctype": "Employee",
            "reference_name": employee.name,
            "content": ["like", "%Status changed from Vacation to Active%"]
        })
        self.assertTrue(comment, "Status change comment should be created")

    @patch("frappe.sendmail")
    def test_leave_resumption_shift_worker_no_accommodation_not_returned(self, mock_sendmail):
        """Test 5: Shift worker without accommodation set to Not Returned from Leave"""
        mock_sendmail.return_value = None
        
        employee = self.create_test_employee_with_allocation()
        
        # Set employee as shift worker without accommodation
        frappe.db.set_value("Employee", employee.name, {
            "shift_working": 1,
            "one_fm_provide_accommodation_by_company": 0,
            "status": "Vacation"
        })
        
        # Create leave application with today as resumption date
        leave_application = make_leave_application(
            employee.name,
            add_days(nowdate(), -5),
            add_days(nowdate(), -1),
            self.leave_type.name
        )
        leave_application.resumption_date = nowdate()
        leave_application.save()
        self.apply_approve_workflow(leave_application)
        
        frappe.db.commit()
        
        update_employee_status_after_leave()
        
        # Verify employee status changed to Not Returned from Leave
        employee_status = frappe.db.get_value("Employee", employee.name, "status")
        self.assertEqual(employee_status, "Not Returned from Leave",
                        "Shift worker without accommodation should be Not Returned from Leave")

    @patch("frappe.sendmail")
    def test_leave_resumption_shift_worker_with_accommodation_no_checkin(self, mock_sendmail):
        """Test 6: Shift worker with accommodation but no check-in set to Not Returned from Leave"""
        mock_sendmail.return_value = None
        
        employee = self.create_test_employee_with_allocation()
        
        # Set employee as shift worker with accommodation
        frappe.db.set_value("Employee", employee.name, {
            "shift_working": 1,
            "one_fm_provide_accommodation_by_company": 1,
            "status": "Vacation"
        })
        
        # Create leave application with today as resumption date
        from_date = add_days(nowdate(), -5)
        leave_application = make_leave_application(
            employee.name,
            from_date,
            add_days(nowdate(), -1),
            self.leave_type.name
        )
        
        leave_application.resumption_date = nowdate()
        leave_application.save()
        self.apply_approve_workflow(leave_application)
        
        # Delete any existing accommodation checkin checkout records
        frappe.db.delete("Accommodation Checkin Checkout", {"employee": employee.name})
        
        frappe.db.commit()
        
        update_employee_status_after_leave()
        
        # Verify employee status changed to Not Returned from Leave
        employee_status = frappe.db.get_value("Employee", employee.name, "status")
        self.assertEqual(employee_status, "Not Returned from Leave",
                        "Shift worker with accommodation but no check-in should be Not Returned from Leave")

    @patch("frappe.sendmail")
    def test_leave_resumption_shift_worker_with_accommodation_and_checkin(self, mock_sendmail):
        """Test 7: Shift worker with accommodation and check-in set to Active"""
        mock_sendmail.return_value = None
        
        employee = self.create_test_employee_with_allocation()
        
        frappe.db.set_value("Employee", employee.name, {
            "shift_working": 1,
            "one_fm_provide_accommodation_by_company": 1,
            "status": "Vacation"
        })
        
        from_date = add_days(nowdate(), -5)
        leave_application = make_leave_application(
            employee.name,
            from_date,
            add_days(nowdate(), -1),
            self.leave_type.name
        )
        leave_application.resumption_date = nowdate()
        leave_application.save()
        self.apply_approve_workflow(leave_application)
        
        # Get or create test accommodation
        test_accommodation = self._get_or_create_test_accommodation()
        
        # Create test accommodation space type
        space_type = create_test_accommodation_space_type()
        
        # Create test bed space type
        bed_space_type = create_test_bed_space_type()
        
        # Create test accommodation unit
        accommodation_unit = create_test_accommodation_unit(test_accommodation.name)
        
        # Create test accommodation space
        accommodation_space = create_test_accommodation_space(
            accommodation=test_accommodation.name,
            accommodation_unit=accommodation_unit.name,
            space_type=space_type.name,
            bed_space_type=bed_space_type.name
        )
        
        # Create a test bed for the accommodation
        bed = create_test_bed(
            accommodation_space=accommodation_space.name,
            bed_id="TEST-BED-001"
        )
        
        checkin = frappe.get_doc({
            "doctype": "Accommodation Checkin Checkout",
            "employee": employee.name,
            "checkin_checkout_date_time": add_days(from_date, 1),
            "accommodation": test_accommodation.name,
            "type": "IN",
            "tenant_category": "Granted Service",
            "bed": bed.name
        })
        checkin.flags.ignore_validate = True
        checkin.insert(ignore_permissions=True)
        
        frappe.db.commit()

        update_employee_status_after_leave()
        
        employee_status = frappe.db.get_value("Employee", employee.name, "status")
        self.assertEqual(employee_status, "Active",
                        "Shift worker with accommodation and check-in should be Active")

    @patch("frappe.sendmail")
    def test_leave_resumption_only_processes_today(self, mock_sendmail):
        """Test 8: Only processes leave applications with resumption date = today"""
        mock_sendmail.return_value = None
        
        employee = self.create_test_employee_with_allocation()
        
        # Set employee as non-shift worker
        frappe.db.set_value("Employee", employee.name, {
            "shift_working": 0,
            "status": "Vacation"
        })
        
        # Create leave application with tomorrow as resumption date
        leave_application = make_leave_application(
            employee.name,
            add_days(nowdate(), -5),
            add_days(nowdate(), -1),
            self.leave_type.name
        )
        leave_application.resumption_date = add_days(nowdate(), 1)
        leave_application.save()
        self.apply_approve_workflow(leave_application)
        
        frappe.db.commit()
        
        update_employee_status_after_leave()
        
        # Verify employee status NOT changed (still Vacation)
        employee_status = frappe.db.get_value("Employee", employee.name, "status")
        self.assertEqual(employee_status, "Vacation",
                        "Employee with future resumption date should not be processed")

    @patch("frappe.sendmail")
    def test_leave_resumption_no_change_if_already_correct_status(self, mock_sendmail):
        """Test 9: No comment created if status already correct"""
        mock_sendmail.return_value = None
        
        employee = self.create_test_employee_with_allocation()
        
        # Set employee as non-shift worker already Active
        frappe.db.set_value("Employee", employee.name, {
            "shift_working": 0,
            "status": "Active"
        })
        
        # Create leave application with today as resumption date
        leave_application = make_leave_application(
            employee.name,
            add_days(nowdate(), -5),
            add_days(nowdate(), -1),
            self.leave_type.name
        )
        leave_application.resumption_date = nowdate()
        leave_application.save()
        self.apply_approve_workflow(leave_application)
        
        frappe.db.commit()
        
        # Count comments before
        comments_before = frappe.db.count("Comment", {
            "reference_doctype": "Employee",
            "reference_name": employee.name
        })
        
        # Run the leave resumption process
        update_employee_status_after_leave()
        
        # Count comments after
        comments_after = frappe.db.count("Comment", {
            "reference_doctype": "Employee",
            "reference_name": employee.name
        })
        
        # Verify no new comment created
        self.assertEqual(comments_before, comments_after,
                        "No comment should be created if status unchanged")
    @patch("frappe.sendmail")
    def test_reliever_assignment_created(self, mock_sendmail):
        """Test 10: Reliever assignment ToDo is created on Pending Reliever state"""
        mock_sendmail.return_value = None

        employee = self.create_test_employee_with_allocation()

        # Create a reliever employee
        # Create a reliever employee distinct from the main test employee
        reliever = make_employee("reliever@example.com")

        from_date = add_days(nowdate(), 1)
        
        leave_application = make_leave_application(
            employee.name,
            from_date,
            add_days(from_date, 2),
            self.leave_type.name
        )
        leave_application.custom_reliever_ = reliever.name
        leave_application.save()

        # Change state to Pending Reliever
        apply_workflow(leave_application, "Submit for Review")

        # Check if ToDo was created for the reliever
        todo = frappe.db.get_value("ToDo", {
            "reference_type": "Leave Application",
            "reference_name": leave_application.name,
            "allocated_to": reliever.user_id,
            "status": "Open"
        }, "name")

        self.assertTrue(todo, "ToDo should be created for the reliever")

    @patch("frappe.sendmail")
    def test_reliever_assignment_closed(self, mock_sendmail):
        """Test 11: Reliever assignment ToDo is closed when state changes from Pending Reliever"""
        mock_sendmail.return_value = None

        employee = self.create_test_employee_with_allocation()

        reliever = make_employee("reliever@example.com")
        from_date = add_days(nowdate(), 1)
        
        leave_application = make_leave_application(
            employee.name,
            from_date,
            add_days(from_date, 2),
            self.leave_type.name
        )
        leave_application.custom_reliever_ = reliever.name
        leave_application.save()

        # Move to Pending Reliever
        apply_workflow(leave_application, "Submit for Review")

        # Now move to next state (e.g. Approve -> Pending Approval)
        apply_workflow(leave_application, "Approve")

        # Check if ToDo is closed
        todo_status = frappe.db.get_value("ToDo", {
            "reference_type": "Leave Application",
            "reference_name": leave_application.name,
            "allocated_to": reliever.user_id
        }, "status")

        self.assertEqual(todo_status, "Cancelled", "ToDo for reliever should be closed")

    @patch("frappe.sendmail")
    def test_leave_approver_assignment_rule_triggers(self, mock_sendmail):
        """Test 12: Leave Approver Assignment rule creates ToDo on Pending Approval"""
        mock_sendmail.return_value = None

        employee = self.create_test_employee_with_allocation()

        from_date = add_days(nowdate(), 1)
        leave_application = make_leave_application(
            employee.name,
            from_date,
            add_days(from_date, 2),
            self.leave_type.name
        )
        leave_application.save()

        # Set low assurance to allow Pending Approval
        frappe.db.set_value("Employee", employee.name, "custom_civil_id_assurance_level", "Low")

        # Move to Pending Approval
        apply_workflow(leave_application, "Submit for Review")

        # Check if ToDo is created for leave_approver based on assignment rule logic
        todo = frappe.db.get_value("ToDo", {
            "reference_type": "Leave Application",
            "reference_name": leave_application.name,
            "allocated_to": leave_application.leave_approver,
            "status": "Open"
        }, "name")

        self.assertTrue(todo, "ToDo should be created for the leave approver via rule/logic")

    @patch("frappe.sendmail")
    def test_leave_application_pending_hr_assignment_rule(self, mock_sendmail):
        """Test 13: Leave Application - Pending HR assignment rule triggers"""
        mock_sendmail.return_value = None

        employee = self.create_test_employee_with_allocation()

        hr_operator = "hr_operator@test.com"
        if not frappe.db.exists("User", hr_operator):
            user = frappe.get_doc({
                "doctype": "User",
                "email": hr_operator,
                "first_name": "HR Operator",
                "enabled": 1,
            })
            user.insert(ignore_permissions=True)
        frappe.db.set_single_value("HR and Payroll Additional Settings", "default_leave_application_operator", hr_operator)

        from_date = add_days(nowdate(), 1)
        leave_application = make_leave_application(
            employee.name,
            from_date,
            add_days(from_date, 2),
            self.leave_type.name
        )
        reliever = make_employee("reliever@example.com")
        leave_application.custom_reliever_ = reliever.name
        leave_application.save()

        # Set civil ID assurance level to "Low" so approval transitions to Pending HR
        frappe.db.set_value("Employee", employee.name, "custom_civil_id_assurance_level", "Low")
        frappe.db.commit()

        # Apply workflow transitions to reach Pending HR state
        # Draft -> Pending Approval (Submit for Review)
        apply_workflow(leave_application, "Submit for Review")
        # Pending Approval -> Pending HR (Approve with Low assurance level)
        apply_workflow(leave_application, "Approve")
        apply_workflow(leave_application, "Approve")
        
        frappe.db.commit()
        leave_application.reload()
        
        # Check if ToDo is created for HR operator on Pending HR state
        todo = frappe.db.get_value("ToDo", {
            "reference_type": "Leave Application",
            "reference_name": leave_application.name,
            "allocated_to": hr_operator,
            "status": "Open"
        }, "name")
        self.assertTrue(todo, "ToDo should be created for HR operator on Pending HR state")


    @patch("frappe.sendmail")
    def test_leave_application_pending_hr_assignment_rule_manual(self, mock_sendmail):
        """Test 14: manual HR operator Assignment"""
        mock_sendmail.return_value = None

        employee = self.create_test_employee_with_allocation()

        hr_operator = "hr_operator@test.com"
        if not frappe.db.exists("User", hr_operator):
            user = frappe.get_doc({
                "doctype": "User",
                "email": hr_operator,
                "first_name": "HR Operator",
                "enabled": 1,
            })
            user.insert(ignore_permissions=True)
        frappe.db.set_single_value("HR and Payroll Additional Settings", "default_leave_application_operator", hr_operator)

        from_date = add_days(nowdate(), 1)
        leave_application = make_leave_application(
            employee.name,
            from_date,
            add_days(from_date, 2),
            self.leave_type.name
        )
        reliever = make_employee("reliever@example.com")
        leave_application.custom_reliever_ = reliever.name
        leave_application.save()

        # Set civil ID assurance level to trigger Pending HR transition
        frappe.db.set_value("Employee", employee.name, "custom_civil_id_assurance_level", "Medium")
        frappe.db.commit()

        # Use workflow transitions to reach Pending HR state
        apply_workflow(leave_application, "Submit for Review")
        apply_workflow(leave_application, "Approve")
        apply_workflow(leave_application, "Approve")
        
        frappe.db.commit()
        leave_application.reload()

        todo = frappe.db.get_value("ToDo", {
            "reference_type": "Leave Application",
            "reference_name": leave_application.name,
            "allocated_to": hr_operator,
            "status": "Open"
        }, "name")
        self.assertTrue(todo, "ToDo should be created for HR operator on Pending HR state")
