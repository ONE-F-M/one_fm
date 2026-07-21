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
            
        # 1. Update Medical Appointment row
        apt_rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "Medical appointment"},
            fields=["name"],
            limit=1,
        )
        if apt_rows:
            frappe.db.set_value(
                "Candidate Country Process Details", apt_rows[0].name,
                {
                    "status": self.appointment_status or "Not Booked",
                    "actual_date": self.appointment_date
                },
                update_modified=True
            )

        # 2. Update Medical Result row
        result_rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "Medical Result"},
            fields=["name"],
            limit=1,
        )
        if result_rows:
            frappe.db.set_value(
                "Candidate Country Process Details", result_rows[0].name,
                {
                    "status": self.status or "Yet to apply",
                    "actual_date": self.result_date
                },
                update_modified=True
            )

        # 3. Skip Re-Medical when the candidate is Fit/Unfit (no re-medical needed);
        # make sure it's active if the result says otherwise. Only touches rows
        # still at Pending/Skipped so genuine re-medical progress is never overwritten.
        remedical_rows = frappe.get_all(
            "Candidate Country Process Details",
            filters={"parent": self.candidate_country_process, "process_name": "Re-Medical"},
            fields=["name", "status"],
            limit=1,
        )
        if remedical_rows:
            remedical_row = remedical_rows[0]
            if self.status in ("Fit", "Unfit") and remedical_row.status == "Pending":
                frappe.db.set_value(
                    "Candidate Country Process Details", remedical_row.name,
                    "status", "Skipped", update_modified=True
                )
            elif self.status == "Medical failed and Proceeded to Remedical" and remedical_row.status == "Skipped":
                frappe.db.set_value(
                    "Candidate Country Process Details", remedical_row.name,
                    "status", "Pending", update_modified=True
                )

    def on_update(self):
        """Notify the CCP engine to evaluate downstream triggers."""
        if self.candidate_country_process and self.status in (
            "Fit",
            "Unfit",
            "Medical failed and Proceeded to Remedical",
        ):
            from one_fm.one_fm.doctype.candidate_country_process.candidate_country_process import recalculate_ccp_live_eta
            recalculate_ccp_live_eta(self.candidate_country_process)
