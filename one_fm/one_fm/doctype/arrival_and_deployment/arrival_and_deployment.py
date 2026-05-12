# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ArrivalandDeployment(Document):
    def validate(self):
        if self.workflow_state in ["Joined", "Did Not Arrive"]:
            if self.candidate_country_process:
                if frappe.session.user != self.transportation_manager and "System Manager" not in frappe.get_roles() and frappe.session.user != "Administrator":
                    frappe.throw(_("Only the Transportation Manager can perform this action for Overseas hires."))
                
                if not self.pickup_arranged:
                    frappe.throw(_("Please check 'Pickup Arranged' before proceeding."))
                if not self.pickup_contact:
                    frappe.throw(_("Please enter the Pickup Contact Person before proceeding."))
            else:
                if frappe.session.user != self.general_services and "System Manager" not in frappe.get_roles() and frappe.session.user != "Administrator":
                    frappe.throw(_("Only General Services can perform this action for Local hires."))

        if self.workflow_state == "Pending Onboarding":
            if not self.arrival_date:
                frappe.throw("Please ensure Arrival Date is filled before submitting to Onboarding.")
            if self.candidate_country_process:
                if not self.arrival_time or not self.ticket_attachment or not self.flight_number or not self.airline or not self.arrival_airport:
                    frappe.throw("Please ensure Arrival Time, Flight Number, Airline, Ticket Attachment, and Arrival Airport are filled for Overseas hires before submitting to Onboarding.")

        self.update_tracker_status()

    def before_save(self):
        if self.workflow_state == "Pending Support Departments" and not self.support_assigned_on:
            self.support_assigned_on = frappe.utils.now_datetime()

    def update_tracker_status(self):
        """Sync status back to the Candidate Country Process tracker row (non-recursive)."""
        if not self.candidate_country_process:
            return
        rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "Arrival & Deployment"},
            fields=["name"],
            limit=1,
        )
        if not rows:
            return

        sync_status = self.status
        if self.workflow_state == "Joined":
            sync_status = "Joined"
        elif self.workflow_state == "Did Not Arrive":
            sync_status = "Did Not Arrive"

        updates = {"status": sync_status}
        if self.arrival_date:
            updates["actual_date"] = self.arrival_date

        for field, value in updates.items():
            frappe.db.set_value("Candidate Country Process Details", rows[0].name, field, value, update_modified=True)

    def on_update(self):
        """Notify the CCP engine to evaluate downstream triggers."""
        old_state = self.get_doc_before_save().workflow_state if self.get_doc_before_save() else None

        if self.workflow_state == "Did Not Arrive" and old_state != "Did Not Arrive":
            self.notify_recruiter_did_not_arrive()

        if self.workflow_state == "Pending Support Departments" and old_state != "Pending Support Departments":
            self.assign_support_departments()

        if self.workflow_state == "Joined" and old_state != "Joined":
            self.clear_support_assignments()

        if self.candidate_country_process:
            if self.workflow_state == "Joined" and old_state != "Joined":
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Joined")
            elif self.workflow_state == "Did Not Arrive" and old_state != "Did Not Arrive":
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Did Not Arrive")
            
            if self.workflow_state != old_state:
                from one_fm.one_fm.doctype.candidate_country_process.candidate_country_process import recalculate_ccp_live_eta
                recalculate_ccp_live_eta(self.candidate_country_process)

    def assign_support_departments(self):
        from frappe.desk.form.assign_to import add as add_assignment
        
        assignments = []
        
        if self.warehouse:
            assignments.append({
                "assign_to": [self.warehouse],
                "description": f"Dear {self.warehouse},\n\nKindly arrange their Uniforms and welcome kit accordingly."
            })
            
        if self.general_services:
            assignments.append({
                "assign_to": [self.general_services],
                "description": f"Dear {self.general_services},\n\nKindly confirm the date and time for GS Orientation."
            })
            
        if self.candidate_country_process:
            if self.transportation_manager:
                assignments.append({
                    "assign_to": [self.transportation_manager],
                    "description": f"Dear {self.transportation_manager},\n\nKindly arrange Airport Pick Up & Accommodation Accordingly based on the flight schedules."
                })
            if self.finance:
                assignments.append({
                    "assign_to": [self.finance],
                    "description": f"Dear {self.finance},\n\nKindly arrange 30 KD as Loan Amount for the arriving employees\n\nPFA: Loan Application form for Arriving employees"
                })

        for assign in assignments:
            try:
                add_assignment({
                    "assign_to": assign["assign_to"],
                    "doctype": self.doctype,
                    "name": self.name,
                    "description": assign["description"]
                }, ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"Assignment failed for {self.name}: {str(e)}", "Arrival Assignment Error")

    def clear_support_assignments(self):
        from frappe.desk.form.assign_to import clear as clear_assignment
        try:
            clear_assignment(self.doctype, self.name, ignore_permissions=True)
        except Exception:
            pass


    def notify_recruiter_did_not_arrive(self):
        if not self.recruiter:
            return
            
        recruiter_email = frappe.db.get_value("User", self.recruiter, "email")
        if not recruiter_email:
            return
            
        from frappe.utils import escape_html
        subject = f"Urgent: Candidate Did Not Arrive - {escape_html(self.candidate_name)}"
        message = f'''
        <p>Dear Recruiter,</p>
        <p>Please be informed that the candidate <b>{escape_html(self.candidate_name)}</b> (Passport: {escape_html(self.passport_number) or 'N/A'}) did not arrive as scheduled.</p>
        <p>Please review the <a href="/app/arrival-and-deployment/{self.name}">Arrival and Deployment Document</a> and take necessary action.</p>
        '''
        
        frappe.enqueue(
            method=frappe.sendmail,
            queue='short',
            recipients=[recruiter_email],
            subject=subject,
            message=message
        )



@frappe.whitelist()
def acknowledge_department(docname, field):
    doc = frappe.get_doc("Arrival and Deployment", docname)
    doc.check_permission("write")
    
    allowed_fields = [
        "general_services_acknowledged",
        "warehouse_acknowledged",
        "finance_acknowledged",
        "transport_acknowledged"
    ]
    if field not in allowed_fields:
        frappe.throw("Invalid acknowledgement field.")
        
    frappe.db.set_value("Arrival and Deployment", docname, field, 1)
    return True

def send_daily_acknowledgement_reminders():
    # Fetch documents pending acknowledgement where state is Joined or Pending Support Departments
    docs = frappe.get_all("Arrival and Deployment", filters={"workflow_state": ["in", ["Pending Support Departments", "Joined"]]}, fields=["name", "candidate_country_process", "general_services", "warehouse", "finance", "transportation_manager", "general_services_acknowledged", "warehouse_acknowledged", "finance_acknowledged", "transport_acknowledged"])
    
    for doc in docs:
        reminders = []
        is_overseas = bool(doc.candidate_country_process)
        
        if not doc.general_services_acknowledged and doc.general_services:
            reminders.append({"email": doc.general_services, "dept": "General Services"})
        if not doc.warehouse_acknowledged and doc.warehouse:
            reminders.append({"email": doc.warehouse, "dept": "Warehouse"})
            
        if is_overseas:
            if not doc.finance_acknowledged and doc.finance:
                reminders.append({"email": doc.finance, "dept": "Finance"})
            if not doc.transport_acknowledged and doc.transportation_manager:
                reminders.append({"email": doc.transportation_manager, "dept": "Transportation"})
                
        for reminder in reminders:
            try:
                user_email = frappe.db.get_value("User", reminder["email"], "email")
                if user_email:
                    frappe.enqueue(
                        method=frappe.sendmail,
                        queue='short',
                        recipients=[user_email],
                        subject=f"Reminder: Action Required for {doc.name}",
                        message=f"<p>Dear {reminder['dept']} Team,</p><p>Please note that the Arrival and Deployment document <a href='/app/arrival-and-deployment/{doc.name}'>{doc.name}</a> is pending your acknowledgement.</p><p>Kindly review and acknowledge it at your earliest convenience.</p>"
                    )
            except Exception as e:
                frappe.log_error(f"Failed to send acknowledgement reminder for {doc.name} to {reminder['email']}: {str(e)}", "Acknowledgement Reminder Error")
