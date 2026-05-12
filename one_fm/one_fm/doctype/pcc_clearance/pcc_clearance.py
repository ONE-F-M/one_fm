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
            
        # 1. Update PCC Appointment row
        apt_rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "PCC Appointment"},
            fields=["name"],
            limit=1,
        )
        if apt_rows:
            frappe.db.set_value(
                "Candidate Country Process Details", apt_rows[0].name,
                {
                    "status": self.appointment_status or "Pending",
                    "actual_date": self.application_date
                },
                update_modified=False
            )

        # 2. Update PCC Result row
        result_rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "PCC Result"},
            fields=["name"],
            limit=1,
        )
        if result_rows:
            frappe.db.set_value(
                "Candidate Country Process Details", result_rows[0].name,
                {
                    "status": self.status or "Pending",
                    "actual_date": self.clearance_date
                },
                update_modified=False
            )

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
