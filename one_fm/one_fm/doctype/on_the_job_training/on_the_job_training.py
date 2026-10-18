# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

class OntheJobTraining(Document):
    def validate(self):
        self.validate_dates()
        self.validate_annual_leave_conflict()
        self.validate_extension_request()
        self.calculate_total_scheduled_ojt_days()


    def validate_extension_request(self):
        if self.is_extension_request and self.original_ojt_request:
            original_ojt = frappe.get_doc("On the Job Training", self.original_ojt_request)
            if not original_ojt.end_date:
                frappe.throw(_("Original OJT Request must have an End Date."))

            if getdate(self.start_date) <= getdate(original_ojt.end_date):
                frappe.throw(_("Extension Start Date must be after the End Date of the Original OJT Request."))

    def calculate_total_scheduled_ojt_days(self):
        if self.start_date and self.end_date:
            days = (getdate(self.end_date) - getdate(self.start_date)).days + 1
            if self.is_extension_request and self.original_ojt_request:
                original_ojt_days = frappe.db.get_value("On the Job Training", self.original_ojt_request, "total_scheduled_ojt_days")
                self.total_scheduled_ojt_days = original_ojt_days + days
            else:
                self.total_scheduled_ojt_days = days

    def validate_dates(self):
        today = getdate(frappe.utils.nowdate())

        # A new record has no state until the process map sets Draft, so check it on the first save too.
        if self.is_new() or self.workflow_state == "Draft":
            if self.start_date and getdate(self.start_date) < today:
                frappe.throw(_("The scheduled event Start date cannot be a past date."))

            if self.end_date and getdate(self.end_date) < today:
                frappe.throw(_("The scheduled event End date cannot be a past date."))

        if self.start_date and self.end_date:
            if getdate(self.end_date) < getdate(self.start_date):
                frappe.throw(
                    _("The scheduled end date must be later than Start Date. Please adjust the event details.")
                )

    def validate_annual_leave_conflict(self):
        """Block saving when OJT date range overlaps with an approved Annual Leave."""
        if not self.employee or not self.start_date:
            return

        start_date = getdate(self.start_date)
        end_date = getdate(self.end_date) if self.end_date else start_date

        leave_applications = frappe.get_list(
            "Leave Application",
            filters={
                "employee": self.employee,
                "leave_type": "Annual Leave",
                "status": "Approved",
                "docstatus": 1,
                "from_date": ["<=", end_date],
                "to_date": [">=", start_date],
            },
            fields=["name", "from_date", "to_date"],
        )

        if leave_applications:
            leave = leave_applications[0]
            frappe.throw(
                _("Cannot create On the Job Training for {0} from {1} to {2} "
                  "because it conflicts with an approved Annual Leave ({3}) "
                  "from {4} to {5}. Please adjust the training dates.").format(
                    self.employee_name or self.employee,
                    frappe.utils.formatdate(start_date),
                    frappe.utils.formatdate(end_date),
                    leave.name,
                    frappe.utils.formatdate(leave.from_date),
                    frappe.utils.formatdate(leave.to_date),
                )
            )
    
@frappe.whitelist()
def create_ojt_extension(source_name, target_doc=None):
    source_doc = frappe.get_doc("On the Job Training", source_name)

    doc = frappe.new_doc("On the Job Training")

    doc.is_extension_request = 1
    doc.original_ojt_request = source_doc.name

    doc.on_the_job_training_name = source_doc.on_the_job_training_name
    doc.employee = source_doc.employee
    doc.employee_name = source_doc.employee_name
    doc.employee_id = source_doc.employee_id
    doc.operations_role = source_doc.operations_role
    doc.operations_shift = source_doc.operations_shift
    doc.operations_site = source_doc.operations_site
    doc.operations_supervisor = source_doc.operations_supervisor
    doc.project = source_doc.project
    doc.operations_manager = source_doc.operations_manager
    doc.mentor = source_doc.mentor
    doc.mentor_name = source_doc.mentor_name
    doc.client_agreed_ojt_days = source_doc.client_agreed_ojt_days

    return doc
