
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from one_fm.tests.utils import (
    get_test_employee, get_test_leave_type, create_test_leave_allocation,
    create_test_company, make_leave_application
)
from one_fm.one_fm.doctype.attendance_check.test_attendance_check import create_attendance_check_record
from one_fm.overrides.leave_application import update_employee_status_after_leave
from frappe.workflow.doctype.workflow_action.workflow_action import apply_workflow
from unittest.mock import patch

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
        self.employee = get_test_employee()

        # Clean up existing test data
        frappe.db.delete("Accommodation Checkin Checkout", {"employee": self.employee.name})
        frappe.db.delete("Attendance Check", {"employee": self.employee.name})
        frappe.db.delete("Leave Application", {"employee": self.employee.name})
        frappe.db.delete("Leave Allocation", {"employee": self.employee.name})
        frappe.db.delete("Comment", {
            "reference_doctype": "Employee",
            "reference_name": self.employee.name
        })

        self.leave_type = get_test_leave_type()
        create_test_leave_allocation(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date=add_days(nowdate(), -30),
            to_date=add_days(nowdate(), 30),
            new_leaves_allocated=25
        )
    
    def tearDown(self):
        """Clean up after each test"""
        # Clean up accommodation checkin checkout records
        frappe.db.delete("Accommodation Checkin Checkout", {"employee": self.employee.name})
        
        # Clean up test accommodation
        frappe.db.delete("Accommodation", {"accommodation": "Test Accommodation"})
        
        # Clean up comments
        frappe.db.delete("Comment", {
            "reference_doctype": "Employee",
            "reference_name": self.employee.name
        })
        
        # Reset employee status to Active
        if frappe.db.exists("Employee", self.employee.name):
            frappe.db.set_value("Employee", self.employee.name, {
                "status": "Active",
                "shift_working": 0,
                "one_fm_provide_accommodation_by_company": 0
            })
        
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _get_or_create_test_accommodation(self):
        """Helper to get or create test accommodation"""
        if not frappe.db.exists("Accommodation", "Test Accommodation"):
            test_accommodation = frappe.get_doc({
                "doctype": "Accommodation",
                "accommodation": "Test Accommodation",
                "company": "_Test Company",
                "capacity": 1,
                "type": "Building",
            }).insert(ignore_permissions=True)
            return test_accommodation
        else:
            return frappe.get_doc("Accommodation", "Test Accommodation")
    
    def _create_draft_attendance_check(self, date, attendance_status="Absent"):
        """Helper to create a draft attendance check"""
        att_check_filters = {
            "employee": self.employee.name,
            "attendance_status": attendance_status
        }
        return create_attendance_check_record(att_check_filters, date)

    @patch("frappe.sendmail")
    def test_approve_leave_application_attendance_checks_approval(self, mock_sendmail):
        """Test 1: suite for approve_attendance_check method"""
        mock_sendmail.return_value = None
        leave_date = add_days(nowdate(), 1)
        attendance_check = self._create_draft_attendance_check(leave_date)

        # Create approved leave application
        leave_application = make_leave_application(
            self.employee.name,
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
        from_date = add_days(nowdate(), 1)
        to_date = add_days(nowdate(), 5)

        # Create attendance checks for all days in the range
        attendance_checks = []
        for i in range(5):
            date = add_days(from_date, i)
            att_check = self._create_draft_attendance_check(date)
            attendance_checks.append(att_check)

        # Create approved leave application
        leave_application = make_leave_application(
            self.employee.name,
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
        from_date = add_days(nowdate(), 1)
        to_date = add_days(nowdate(), 5)

        # Create attendance checks only for days 1, 2
        check_1 = self._create_draft_attendance_check(from_date)
        check_2 = self._create_draft_attendance_check(add_days(from_date, 1))

        # Create approved leave application
        leave_application = make_leave_application(
            self.employee.name,
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
            "employee": self.employee.name,
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
        
        # Set employee as non-shift worker
        frappe.db.set_value("Employee", self.employee.name, {
            "shift_working": 0,
            "status": "Vacation"
        })
        
        # Create leave application with today as resumption date
        leave_application = make_leave_application(
            self.employee.name,
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
        employee_status = frappe.db.get_value("Employee", self.employee.name, "status")
        self.assertEqual(employee_status, "Active", 
                        "Non-shift worker should be set to Active on resumption date")
        
        # Verify comment was created
        comment = frappe.db.exists("Comment", {
            "reference_doctype": "Employee",
            "reference_name": self.employee.name,
            "content": ["like", "%Status changed from Vacation to Active%"]
        })
        self.assertTrue(comment, "Status change comment should be created")

    @patch("frappe.sendmail")
    def test_leave_resumption_shift_worker_no_accommodation_not_returned(self, mock_sendmail):
        """Test 5: Shift worker without accommodation set to Not Returned from Leave"""
        mock_sendmail.return_value = None
        
        # Set employee as shift worker without accommodation
        frappe.db.set_value("Employee", self.employee.name, {
            "shift_working": 1,
            "one_fm_provide_accommodation_by_company": 0,
            "status": "Vacation"
        })
        
        # Create leave application with today as resumption date
        leave_application = make_leave_application(
            self.employee.name,
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
        employee_status = frappe.db.get_value("Employee", self.employee.name, "status")
        self.assertEqual(employee_status, "Not Returned from Leave",
                        "Shift worker without accommodation should be Not Returned from Leave")

    @patch("frappe.sendmail")
    def test_leave_resumption_shift_worker_with_accommodation_no_checkin(self, mock_sendmail):
        """Test 6: Shift worker with accommodation but no check-in set to Not Returned from Leave"""
        mock_sendmail.return_value = None
        
        # Set employee as shift worker with accommodation
        frappe.db.set_value("Employee", self.employee.name, {
            "shift_working": 1,
            "one_fm_provide_accommodation_by_company": 1,
            "status": "Vacation"
        })
        
        # Create leave application with today as resumption date
        from_date = add_days(nowdate(), -5)
        leave_application = make_leave_application(
            self.employee.name,
            from_date,
            add_days(nowdate(), -1),
            self.leave_type.name
        )
        
        leave_application.resumption_date = nowdate()
        leave_application.save()
        self.apply_approve_workflow(leave_application)
        
        # Delete any existing accommodation checkin checkout records
        frappe.db.delete("Accommodation Checkin Checkout", {"employee": self.employee.name})
        
        frappe.db.commit()
        
        update_employee_status_after_leave()
        
        # Verify employee status changed to Not Returned from Leave
        employee_status = frappe.db.get_value("Employee", self.employee.name, "status")
        self.assertEqual(employee_status, "Not Returned from Leave",
                        "Shift worker with accommodation but no check-in should be Not Returned from Leave")

    @patch("frappe.sendmail")
    def test_leave_resumption_shift_worker_with_accommodation_and_checkin(self, mock_sendmail):
        """Test 7: Shift worker with accommodation and check-in set to Active"""
        mock_sendmail.return_value = None
        
        frappe.db.set_value("Employee", self.employee.name, {
            "shift_working": 1,
            "one_fm_provide_accommodation_by_company": 1,
            "status": "Vacation"
        })
        
        from_date = add_days(nowdate(), -5)
        leave_application = make_leave_application(
            self.employee.name,
            from_date,
            add_days(nowdate(), -1),
            self.leave_type.name
        )
        leave_application.resumption_date = nowdate()
        leave_application.save()
        self.apply_approve_workflow(leave_application)
        
        # Get or create test accommodation
        test_accommodation = self._get_or_create_test_accommodation()
        
        checkin = frappe.get_doc({
            "doctype": "Accommodation Checkin Checkout",
            "employee": self.employee.name,
            "checkin_checkout_date_time": add_days(from_date, 1),
            "accommodation": test_accommodation.name,
            "type": "IN",
            "tenant_category": "Granted Service",
            "bed": "010202302333"
        })
        checkin.flags.ignore_validate = True
        checkin.insert(ignore_permissions=True)
        
        frappe.db.commit()

        update_employee_status_after_leave()
        
        employee_status = frappe.db.get_value("Employee", self.employee.name, "status")
        self.assertEqual(employee_status, "Active",
                        "Shift worker with accommodation and check-in should be Active")

    @patch("frappe.sendmail")
    def test_leave_resumption_only_processes_today(self, mock_sendmail):
        """Test 8: Only processes leave applications with resumption date = today"""
        mock_sendmail.return_value = None
        
        # Set employee as non-shift worker
        frappe.db.set_value("Employee", self.employee.name, {
            "shift_working": 0,
            "status": "Vacation"
        })
        
        # Create leave application with tomorrow as resumption date
        leave_application = make_leave_application(
            self.employee.name,
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
        employee_status = frappe.db.get_value("Employee", self.employee.name, "status")
        self.assertEqual(employee_status, "Vacation",
                        "Employee with future resumption date should not be processed")

    @patch("frappe.sendmail")
    def test_leave_resumption_no_change_if_already_correct_status(self, mock_sendmail):
        """Test 9: No comment created if status already correct"""
        mock_sendmail.return_value = None
        
        # Set employee as non-shift worker already Active
        frappe.db.set_value("Employee", self.employee.name, {
            "shift_working": 0,
            "status": "Active"
        })
        
        # Create leave application with today as resumption date
        leave_application = make_leave_application(
            self.employee.name,
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
            "reference_name": self.employee.name
        })
        
        # Run the leave resumption process
        update_employee_status_after_leave()
        
        # Count comments after
        comments_after = frappe.db.count("Comment", {
            "reference_doctype": "Employee",
            "reference_name": self.employee.name
        })
        
        # Verify no new comment created
        self.assertEqual(comments_before, comments_after,
                        "No comment should be created if status unchanged")


    def test_leave_application_on_cancel_comparison(self):
        """Test for issue #5942: TypeError: '<' not supported between instances of 'datetime.date' and 'str'"""
        from one_fm.utils import leave_application_on_cancel
        from frappe.utils import getdate, add_days

        # Create a mock doc where from_date is a datetime.date object
        doc = frappe._dict({
            "from_date": getdate(add_days(nowdate(), -1)),
            "employee": self.employee.name,
            "doctype": "Leave Application"
        })

        # Mock frappe.db.set_value and update_employee_hajj_status to isolate date comparison
        with patch("frappe.db.set_value") as mock_set_value, \
             patch("one_fm.utils.update_employee_hajj_status") as mock_hajj_status:
            
            try:
                leave_application_on_cancel(doc, "on_cancel")
            except TypeError:
                self.fail("leave_application_on_cancel raised TypeError during date comparison")
            
            # Verify that set_value was called since from_date < today
            mock_set_value.assert_called_with("Employee", self.employee.name, "status", "Active")
            mock_hajj_status.assert_called_once()
