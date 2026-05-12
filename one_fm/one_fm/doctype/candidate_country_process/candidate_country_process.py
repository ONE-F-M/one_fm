# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CandidateCountryProcess(Document):
    def before_insert(self):
        if not self.agency_process_details and self.agency_country_process:
            acp = frappe.get_doc("Agency Country Process", self.agency_country_process)
            for row in acp.agency_process_details:
                # Determine initial status
                initial_status = "Pending"
                pname = (row.process_name or "").lower()
                if "appointment" in pname:
                    initial_status = "Not Booked"
                elif "result" in pname:
                    initial_status = "Yet to apply"
                    
                self.append("agency_process_details", {
                    "process_name": row.process_name,
                    "responsible": row.responsible,
                    "expected_date": frappe.utils.add_days(self.start_date, row.duration_in_days) if row.duration_in_days else None,
                    "reference_type": row.reference_type,
                    "reference_complete_status_field": row.reference_complete_status_field,
                    "reference_complete_status_value": row.reference_complete_status_value,
                    "status": initial_status
                })
        
        if self.agency_process_details:
            first_step = self.agency_process_details[0]
            if "offer" in (first_step.process_name or "").lower():
                first_step.actual_date = self.start_date
                first_step.status = "Approved"

    def after_insert(self):
        created_refs = set()
        if self.agency_process_details:
            for agency_process_details in self.agency_process_details:
                if agency_process_details.reference_type:
                    if not self.current_process_id:
                        self.current_process_id = agency_process_details.name
                        self.db_set('current_process_id', agency_process_details.name)
                        
                    # Autogenerate draft for each unique reference type
                    ref_type = agency_process_details.reference_type
                    if ref_type not in created_refs:
                        try:
                            new_doc = frappe.new_doc(ref_type)
                            if new_doc.meta.has_field("candidate_country_process"):
                                new_doc.candidate_country_process = self.name
                            if new_doc.meta.has_field("job_applicant"):
                                new_doc.job_applicant = self.job_applicant
                            if new_doc.meta.has_field("job_offer"):
                                new_doc.job_offer = self.job_offer
                            
                            new_doc.flags.ignore_mandatory = True
                            new_doc.flags.ignore_permissions = True
                            new_doc.insert()
                            
                            # Update the reference_name in the grid
                            for row in self.agency_process_details:
                                if row.reference_type == ref_type:
                                    row.reference_name = new_doc.name
                                    row.db_update()
                                    
                            created_refs.add(ref_type)
                        except Exception as e:
                            frappe.log_error(f"Failed to auto-generate {ref_type} draft for CCP {self.name}", str(e))

    def on_submit(self):
        pass

    def on_update(self):
        self.calculate_planned_eta()
        self.calculate_live_plan_eta()

    def calculate_planned_eta(self):
        if not self.planned_eta and self.start_date and self.agency_country_process:
            agency_process = frappe.get_doc("Agency Country Process", self.agency_country_process)
            if agency_process.total_duration:
                self.planned_eta = frappe.utils.add_days(self.start_date, agency_process.total_duration)
                frappe.db.set_value("Candidate Country Process", self.name, "planned_eta", self.planned_eta, update_modified=False)

    def calculate_live_plan_eta(self):
        if not self.planned_eta:
            return

        total_delay = 0
        if self.agency_process_details:
            for row in self.agency_process_details:
                if row.actual_date and row.expected_date:
                    delay_days = frappe.utils.date_diff(row.actual_date, row.expected_date)
                    total_delay += delay_days

        new_live_eta = frappe.utils.add_days(self.planned_eta, total_delay)
        if self.live_plan_eta != new_live_eta:
            self.live_plan_eta = new_live_eta
            frappe.db.set_value("Candidate Country Process", self.name, "live_plan_eta", new_live_eta, update_modified=False)

    @frappe.whitelist()
    def get_workflow(self):
        workflow_list = []
        if self.agency_process_details:
            for workflow in self.agency_process_details:
                if workflow.reference_type and workflow.name == self.current_process_id:
                    if workflow.reference_name:
                        workflow_list.append(frappe.get_doc(workflow.reference_type, workflow.reference_name).as_dict())
                    else:
                        workflow_list.append({"new_doc": True, "doctype": workflow.reference_type})
        return workflow_list

def update_candidate_country_process():
    query = """
        select
            dt.name as dt_name, ccp.name as ccp_name, dt.process_name, dt.reference_type, dt.reference_name,
            dt.reference_complete_status_value, dt.reference_complete_status_field, dt.idx
        from
            `tabCandidate Country Process` ccp, `tabCandidate Country Process Details` dt
        where
            ccp.current_process_id=dt.name
    """
    ccp_list = frappe.db.sql(query, as_dict=True)
    for ccp in ccp_list:
        if ccp.reference_type and ccp.ccp_name:
            process_doc = frappe.get_doc(ccp.reference_type, {'candidate_country_process': ccp.ccp_name})
            if process_doc:
                if not ccp.reference_name:
                    frappe.db.set_value('Candidate Country Process Details', ccp.dt_name, 'reference_name', process_doc.name)
                if process_doc.get(ccp.reference_complete_status_field) == ccp.reference_complete_status_value:
                    frappe.db.set_value('Candidate Country Process Details', ccp.dt_name, 'status', 'Approved')
                    ccp_doc = frappe.get_doc('Candidate Country Process', ccp.ccp_name)
                    if len(ccp_doc.agency_process_details) > ccp.idx+1:
                        for process_list in ccp_doc.agency_process_details:
                            if process_list.idx > ccp.idx and process_list.reference_type:
                                ccp_doc.db_set('current_process_id', process_list.name)
                                break
