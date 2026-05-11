# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PCCClearance(Document):
    def validate(self):
        self.auto_fetch_nationality()
        self.update_tracker_status()

    def auto_fetch_nationality(self):
        """Auto-fetch nationality from the Job Applicant linked via CCP."""
        if self.nationality or not self.candidate_country_process:
            return
        job_applicant = frappe.db.get_value(
            "Candidate Country Process", self.candidate_country_process, "job_applicant"
        )
        if job_applicant:
            self.nationality = frappe.db.get_value(
                "Job Applicant", job_applicant, "one_fm_nationality"
            )

    def update_tracker_status(self):
        """Sync status back to the Candidate Country Process tracker row (non-recursive)."""
        if not self.candidate_country_process:
            return
        rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "PCC Clearance"},
            fields=["name"],
            limit=1,
        )
        if not rows:
            return

        updates = {"status": self.status}
        if self.clearance_date:
            updates["actual_date"] = self.clearance_date
        elif self.application_date and self.status == "Applied":
            updates["actual_date"] = self.application_date

        for field, value in updates.items():
            frappe.db.set_value("Candidate Country Process Details", rows[0].name, field, value, update_modified=False)

    def on_update(self):
        """Notify the CCP engine to evaluate downstream triggers."""
        if self.candidate_country_process and self.status in ("Issued", "Rejected"):
            self._notify_ccp()

    def _notify_ccp(self):
        """Reload and save the parent CCP so its dependency engine runs."""
        try:
            ccp = frappe.get_doc("Candidate Country Process", self.candidate_country_process)
            ccp.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(
                f"PCC Clearance {self.name}: failed to notify CCP {self.candidate_country_process}",
                "CCP Notify Error",
            )
