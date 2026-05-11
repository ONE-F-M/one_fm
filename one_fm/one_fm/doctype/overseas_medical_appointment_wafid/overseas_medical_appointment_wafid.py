# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class OverseasMedicalAppointmentWAFID(Document):
    def validate(self):
        self.update_tracker_status()

    def update_tracker_status(self):
        """Sync status back to the Candidate Country Process tracker row."""
        if not self.candidate_country_process:
            return
        rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "Medical Test"},
            fields=["name"],
            limit=1,
        )
        if not rows:
            return

        updates = {"status": self.status}
        if self.status in ("Fit", "Passed") and self.result_date:
            updates["actual_date"] = self.result_date
        elif self.appointment_date:
            updates["actual_date"] = self.appointment_date

        for field, value in updates.items():
            frappe.db.set_value(
                "Candidate Country Process Details", rows[0].name,
                field, value, update_modified=False
            )

    def on_update(self):
        """Notify the CCP engine to evaluate downstream triggers."""
        if self.candidate_country_process and self.status in ("Fit", "Passed", "Unfit", "Failed"):
            self._notify_ccp()

    def _notify_ccp(self):
        """Reload and save the parent CCP so its dependency engine runs."""
        try:
            ccp = frappe.get_doc("Candidate Country Process", self.candidate_country_process)
            ccp.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(
                f"Overseas Medical WAFID {self.name}: failed to notify CCP {self.candidate_country_process}",
                "CCP Notify Error",
            )
