import frappe
from frappe import _

def execute():
    """
    Approve all Attendance Check records for 17th November 2025 and mark them as Present.
    """
    target_date = "2025-11-17"

    # Get all attendance checks in "Pending Approval" state for the target date.
    attendance_checks = frappe.get_all(
        "Attendance Check",
        filters={
            "date": target_date,
            "workflow_state": "Pending Approval",
        },
        fields=["name"]
    )

    if not attendance_checks:
        frappe.msgprint(_(f"No Attendance Check records in 'Pending Approval' state found for {target_date} to approve."))
        return

    processed_count = 0

    for ac in attendance_checks:
        try:
            doc = frappe.get_doc("Attendance Check", ac.name)
            doc.attendance_status = "Present"
            doc.justification = "Approved by Administrator"

            # This flag helps bypass mandatory field validations which might be triggered by the justification change.
            doc.flags.ignore_mandatory = True

            doc.save(ignore_permissions=True)
            doc.submit()

            processed_count += 1
        except Exception:
            frappe.log_error(title=f"Failed to process Attendance Check {ac.name}", message=frappe.get_traceback())

    frappe.msgprint(_(f"Successfully processed and approved {processed_count} Attendance Check records for {target_date}."))
