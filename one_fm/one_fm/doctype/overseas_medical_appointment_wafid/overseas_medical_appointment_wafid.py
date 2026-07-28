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

        # 3. A "Fit" result means Remedical is never needed for this candidate --
        # auto-skip its tracker rows instead of leaving them "Pending" forever
        # (previously only fixable by manually picking "Skipped" from the
        # dropdown). Only touches rows still at their default "Pending" state,
        # so it never overwrites a Remedical that's already under way.
        if self.status == "Fit":
            remedical_rows = frappe.get_all(
                "Candidate Country Process Details",
                filters={
                    "parent": self.candidate_country_process,
                    "process_name": ["in", ["Remedical appointment", "Remedical results"]],
                    "status": "Pending",
                },
                fields=["name"],
            )
            for row in remedical_rows:
                frappe.db.set_value(
                    "Candidate Country Process Details", row.name,
                    "status", "Skipped",
                    update_modified=True
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
