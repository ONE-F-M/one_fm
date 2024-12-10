import frappe


def execute():
    frappe.db.set_value("Job Offer", "HR-OFF-2024-00723", "one_fm_erf", "ERF-2024-00059")