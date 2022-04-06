# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CandidateCountryProcess(Document):
    def after_insert(self):
        if self.agency_process_details:
            for agency_process_details in self.agency_process_details:
                if agency_process_details.reference_type:
                    self.current_process_id = agency_process_details.name
                    self.db_set('current_process_id', agency_process_details.name)
                    break

    def on_submit(self):
        pass

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
