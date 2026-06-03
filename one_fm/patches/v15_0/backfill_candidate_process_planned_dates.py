import frappe


def execute():
    """
    Data migration: backfill planned_date and live_plan_date from expected_date
    for all Candidate Country Process Details rows created before the field rename.
    """
    frappe.reload_doctype("Candidate Country Process Details")
    frappe.db.sql("""
        UPDATE `tabCandidate Country Process Details`
        SET
            planned_date   = COALESCE(planned_date, expected_date),
            live_plan_date = COALESCE(live_plan_date, expected_date)
        WHERE expected_date IS NOT NULL
    """)
    frappe.db.commit()
