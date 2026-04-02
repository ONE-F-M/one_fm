import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from one_fm.tests.utils import (
    get_test_employee, get_test_leave_type, create_test_leave_allocation,
    create_test_company
)
from one_fm.one_fm.doctype.leave_acknowledgement_form.leave_acknowledgement_form import generate_leave_acknowledgement
from frappe.automation.doctype.assignment_rule.assignment_rule import apply as apply_assignment_rule

class TestLeaveAcknowledgementForm(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        create_test_company()
        self.employee = get_test_employee()

        # Clean up existing data for test isolation
        frappe.db.delete("Leave Acknowledgement Form", {"employee": self.employee.name})
        frappe.db.delete("Leave Allocation", {"employee": self.employee.name})
        frappe.db.delete("Leave Ledger Entry", {"employee": self.employee.name})

        self.leave_type = get_test_leave_type(leave_type_name="Annual Leave", is_carry_forward=1)
        frappe.db.set_value("HR Settings", None, "annual_leave_threshold", 60)

    def tearDown(self):
        frappe.db.rollback()

    def test_set_previous_records_inactive(self):
        # Create a first form
        form1 = frappe.get_doc({
            "doctype": "Leave Acknowledgement Form",
            "employee": self.employee.name,
            "date": nowdate()
        }).insert(ignore_permissions=True)

        # Simulate workflow action that sets it as active
        frappe.db.set_value("Leave Acknowledgement Form", form1.name, "is_active", 1)

        # Create a second form and submit it
        form2 = frappe.get_doc({
            "doctype": "Leave Acknowledgement Form",
            "employee": self.employee.name,
            "date": nowdate()
        }).insert(ignore_permissions=True)
        form2.submit()

        # The first form should have become inactive after form2 is submitted
        self.assertEqual(frappe.db.get_value("Leave Acknowledgement Form", form1.name, "is_active"), 0)
        self.assertEqual(frappe.db.get_value("Leave Acknowledgement Form", form2.name, "is_active"), 0) # Initially 0 logically until approved

    def allocate_carry_forward_leaves(self, amount):
        allocation = create_test_leave_allocation(
            employee=self.employee,
            leave_type=self.leave_type,
            from_date=add_days(nowdate(), -365),
            to_date=add_days(nowdate(), 365),
            new_leaves_allocated=amount
        )
        # Ensure it is considered as carry forward in Ledger to match generator logic
        frappe.db.sql("UPDATE `tabLeave Ledger Entry` SET is_carry_forward = 1 WHERE transaction_name = %s", allocation.name)

    def test_generate_leave_acknowledgement_high_assurance(self):
        frappe.db.set_value("Employee", self.employee.name, "custom_civil_id_assurance_level", "High")
        self.allocate_carry_forward_leaves(65)

        generate_leave_acknowledgement()

        forms = frappe.get_all(
            "Leave Acknowledgement Form",
            filters={"employee": self.employee.name},
            fields=["name", "workflow_state"]
        )

        self.assertEqual(len(forms), 1, "Form should be generated for leaves above threshold")
        self.assertEqual(forms[0].workflow_state, "Pending Confirmation", "High assurance should result in Pending Confirmation state")

        # Check if ToDo is created for employee based on assignment rule logic
        todo = frappe.db.get_value("ToDo", {
            "reference_type": "Leave Acknowledgement Form",
            "reference_name": forms[0].name,
            "allocated_to": self.employee.user_id,
            "status": "Open"
        }, "name")

        self.assertTrue(todo, "ToDo should be created for the employee via rule/logic")

    def test_generate_leave_acknowledgement_low_assurance(self):
        frappe.db.set_value("Employee", self.employee.name, "custom_civil_id_assurance_level", "Low")
        self.allocate_carry_forward_leaves(65)

        generate_leave_acknowledgement()

        forms = frappe.get_all(
            "Leave Acknowledgement Form",
            filters={"employee": self.employee.name},
            fields=["name", "workflow_state"]
        )

        self.assertEqual(len(forms), 1)
        self.assertEqual(forms[0].workflow_state, "Pending HR", "Non-High assurance should result in Pending HR state")

    def test_generate_leave_acknowledgement_below_threshold(self):
        frappe.db.set_value("Employee", self.employee.name, "custom_civil_id_assurance_level", "High")
        self.allocate_carry_forward_leaves(50)

        generate_leave_acknowledgement()

        forms = frappe.get_all("Leave Acknowledgement Form", filters={"employee": self.employee.name})
        self.assertEqual(len(forms), 0, "No form should be generated if below threshold")
        
