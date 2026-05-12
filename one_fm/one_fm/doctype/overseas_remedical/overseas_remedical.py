# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OverseasRemedical(Document):
    def validate(self):
        self.update_tracker_status()

    def update_tracker_status(self):
        """Sync status back to the Candidate Country Process tracker row."""
        if not self.candidate_country_process:
            return
            
        # 1. Update Remedical Appointment row
        apt_rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "Remedical appointment"},
            fields=["name"],
            limit=1,
        )
        if apt_rows:
            frappe.db.set_value(
                "Candidate Country Process Details", apt_rows[0].name,
                {
                    "status": self.appointment_status or "Pending",
                    "actual_date": self.appointment_date
                },
                update_modified=False
            )

        # 2. Update Remedical Result row
        result_rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "Remedical results"},
            fields=["name"],
            limit=1,
        )
        if result_rows:
            frappe.db.set_value(
                "Candidate Country Process Details", result_rows[0].name,
                {
                    "status": self.status or "Pending",
                    "actual_date": self.result_date
                },
                update_modified=False
            )

    def on_update(self):
        """Notify the CCP engine to evaluate downstream triggers."""
        if self.candidate_country_process and self.status in ("Fit", "Unfit", "Skipped"):
            self._notify_ccp()

    def _notify_ccp(self):
        """Reload and save the parent CCP so its dependency engine runs."""
        try:
            ccp = frappe.get_doc("Candidate Country Process", self.candidate_country_process)
            ccp.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(
                f"Overseas Remedical {self.name}: failed to notify CCP {self.candidate_country_process}",
                "CCP Notify Error",
            )
