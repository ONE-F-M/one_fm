import frappe


PARALLEL_MAP = {
    "Job Offer Issuance":   0,
    "Visa Processing":      0,
    "Medical Test":         1,
    "Remedical Test":       1,
    "PCC Clearance":        2,
    "Visa Stamping":        0,
    "Arrival & Deployment": 0,
}


def execute():
    """
    Backfill parallel_group on all existing Candidate Country Process Details rows
    created before the Fork-Join parallel track feature was introduced.
    Also triggers a re-save so the live_plan_date cascade recalculates.
    """
    frappe.reload_doctype("Candidate Country Process Details")
    
    if not frappe.db.has_column("Candidate Country Process Details", "parallel_group"):
        return

    # 1. Stamp correct parallel_group on every existing detail row
    rows = frappe.db.sql(
        "SELECT name, process_name, parallel_group FROM `tabCandidate Country Process Details`",
        as_dict=True,
    )
    for row in rows:
        pg = PARALLEL_MAP.get(row.process_name, 0)
        if row.parallel_group != pg:
            frappe.db.set_value(
                "Candidate Country Process Details",
                row.name,
                "parallel_group",
                pg,
                update_modified=False,
            )

    frappe.db.commit()

    # 2. Re-save each parent CCP so the validate() cascade recalculates live_plan_date
    ccps = frappe.get_all("Candidate Country Process", pluck="name")
    for ccp_name in ccps:
        try:
            doc = frappe.get_doc("Candidate Country Process", ccp_name)
            doc.flags._in_auto_create = True
            doc.save(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(f"Failed to re-save CCP {ccp_name}: {e}")

    frappe.db.commit()
