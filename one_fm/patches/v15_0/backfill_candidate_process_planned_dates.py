import frappe


from frappe.query_builder.functions import Coalesce


def execute():
    """
    Data migration: backfill planned_date and live_plan_date from expected_date
    for all Candidate Country Process Details rows created before the field rename.
    """
    frappe.reload_doctype("Candidate Country Process Details")
    if not frappe.db.has_column("Candidate Country Process Details", "expected_date"):
        return

    details = frappe.qb.DocType("Candidate Country Process Details")
    frappe.qb.update(details).set(
        details.planned_date, Coalesce(details.planned_date, details.expected_date)
    ).set(
        details.live_plan_date, Coalesce(details.live_plan_date, details.expected_date)
    ).where(
        details.expected_date.isnotnull()
    ).run()

    frappe.db.commit()
