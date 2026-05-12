# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ArrivalandDeployment(Document):
    def validate(self):
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
        if self.status == "Completed":
            sync_status = "Joined"

        updates = {"status": sync_status}
        if self.arrival_date:
            updates["actual_date"] = self.arrival_date

        for field, value in updates.items():
            frappe.db.set_value("Candidate Country Process Details", rows[0].name, field, value, update_modified=False)

    def on_update(self):
        """Notify the CCP engine to evaluate downstream triggers."""
        if self.candidate_country_process:
            if self.workflow_state == "Completed":
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Joined")
            elif self.workflow_state == "Did Not Arrive":
                frappe.db.set_value("Candidate Country Process", self.candidate_country_process, "status", "Did Not Arrive")
            self._notify_ccp()

    def _notify_ccp(self):
        """Reload and save the parent CCP so its dependency engine runs."""
        try:
            ccp = frappe.get_doc("Candidate Country Process", self.candidate_country_process)
            ccp.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(
                f"Arrival and Deployment {self.name}: failed to notify CCP {self.candidate_country_process}",
                "CCP Notify Error",
            )

@frappe.whitelist()
def acknowledge_department(docname, field):
    frappe.db.set_value("Arrival and Deployment", docname, field, 1)
    return True
