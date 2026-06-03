# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# Patch: Migrate from parallel_group to before_task / sequence_type / after_task

import frappe


def execute():
    """
    Convert the old parallel_group numeric field to the new
    before_task / sequence_type / after_task dependency columns.

    Current ACP template flow (all templates ACP006-ACP010):
      1. Job Offer Issuance     (seq)  →  before: (none)            after: Visa Processing
      2. Visa Processing        (seq)  →  before: Job Offer         after: Medical Test, PCC Clearance
      3. Medical Test           (par)  →  before: Visa Processing   after: Visa Stamping
      4. Remedical Test         (par)  →  before: Medical Test      after: Visa Stamping
      5. PCC Clearance          (par)  →  before: Visa Processing   after: Visa Stamping
      6. Visa Stamping          (seq)  →  before: Medical Test, PCC after: Arrival & Deployment
      7. Arrival & Deployment   (seq)  →  before: Visa Stamping     after: (none)
    """
    frappe.reload_doctype("Agency Process Details")
    frappe.reload_doctype("Candidate Country Process Details")

    # ── Define the dependency map for agency templates ────────────────────────
    DEPENDENCY_MAP = {
        "Job Offer Issuance": {
            "before_task": "",
            "sequence_type": "Sequential",
            "after_task": "Visa Processing",
        },
        "Visa Processing": {
            "before_task": "Job Offer Issuance",
            "sequence_type": "Sequential",
            "after_task": "Medical Test, PCC Clearance",
        },
        "Medical Test": {
            "before_task": "Visa Processing",
            "sequence_type": "Parallel",
            "after_task": "Visa Stamping",
        },
        "Remedical Test": {
            "before_task": "Medical Test",
            "sequence_type": "Parallel",
            "after_task": "Visa Stamping",
        },
        "PCC Clearance": {
            "before_task": "Visa Processing",
            "sequence_type": "Parallel",
            "after_task": "Visa Stamping",
        },
        "Visa Stamping": {
            "before_task": "Medical Test, PCC Clearance",
            "sequence_type": "Sequential",
            "after_task": "Arrival & Deployment",
        },
        "Arrival & Deployment": {
            "before_task": "Visa Stamping",
            "sequence_type": "Sequential",
            "after_task": "",
        },
    }

    # ── Update Agency Process Details (templates) ─────────────────────────────
    for process_name, deps in DEPENDENCY_MAP.items():
        frappe.db.sql("""
            UPDATE `tabAgency Process Details`
            SET before_task = %(before_task)s,
                sequence_type = %(sequence_type)s,
                after_task = %(after_task)s
            WHERE process_name = %(process_name)s
        """, {
            "process_name": process_name,
            "before_task": deps["before_task"],
            "sequence_type": deps["sequence_type"],
            "after_task": deps["after_task"],
        })

    # ── Update Candidate Country Process Details (live tracker rows) ──────────
    for process_name, deps in DEPENDENCY_MAP.items():
        frappe.db.sql("""
            UPDATE `tabCandidate Country Process Details`
            SET before_task = %(before_task)s,
                sequence_type = %(sequence_type)s,
                after_task = %(after_task)s
            WHERE process_name = %(process_name)s
        """, {
            "process_name": process_name,
            "before_task": deps["before_task"],
            "sequence_type": deps["sequence_type"],
            "after_task": deps["after_task"],
        })

    frappe.db.commit()
