# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class VisaStamping(Document):
    def validate(self):
        self.auto_link_pam_visa()
        self.update_tracker_status()

    def auto_link_pam_visa(self):
        """Auto-link PAM Visa from the same Candidate Country Process if not set."""
        if self.pam_visa or not self.candidate_country_process:
            return
        pam_visa = frappe.db.get_value(
            "PAM Visa",
            {"candidate_country_process": self.candidate_country_process},
            "name",
        )
        if pam_visa:
            self.pam_visa = pam_visa

    def update_tracker_status(self):
        """Sync status back to the Candidate Country Process tracker row."""
        if not self.candidate_country_process:
            return
            
        # 1. Update Visa Stamping Appointment row
        apt_rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "Visa stamping appointment"},
            fields=["name"],
            limit=1,
        )
        if apt_rows:
            frappe.db.set_value(
                "Candidate Country Process Details", apt_rows[0].name,
                {
                    "status": self.appointment_status or "Pending",
                    "actual_date": self.submission_date
                },
                update_modified=False
            )

        # 2. Update Visa Stamping Result row
        result_rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "Visa stamping results"},
            fields=["name"],
            limit=1,
        )
        if result_rows:
            frappe.db.set_value(
                "Candidate Country Process Details", result_rows[0].name,
                {
                    "status": self.status or "Pending",
                    "actual_date": self.receiving_date
                },
                update_modified=False
            )

    def on_update(self):
        """Notify the CCP engine to evaluate downstream triggers."""
        if self.candidate_country_process and self.status in ("Stamped", "Rejected"):
            self._notify_ccp()

    def _notify_ccp(self):
        """Reload and save the parent CCP so its dependency engine runs."""
        try:
            ccp = frappe.get_doc("Candidate Country Process", self.candidate_country_process)
            ccp.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(
                f"Visa Stamping {self.name}: failed to notify CCP {self.candidate_country_process}",
                "CCP Notify Error",
            )
