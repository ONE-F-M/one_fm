import frappe
from frappe.utils.fixtures import sync_fixtures
from one_fm.setup import delete_custom_fields
from one_fm.custom.custom_field.shift_request import get_shift_request_custom_fields
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields



def execute():
    sync_fixtures("one_fm") 
    pending_worflows = frappe.get_all(
        "Shift Request",
        filters={"workflow_state": "Pending Approver"},
        fields=["name", "parent"]
    )
    delete_custom_fields({
        "Shift Request": [
            {
                "fieldname": "shift_approver",
            },
            {
                "fieldname": "custom_shift_approvers",
            }
        ]
    })
    create_custom_fields(get_shift_request_custom_fields())
    if pending_worflows:
        update_existing_pending_approver_to_pending_approval(pending_worflows)

def update_existing_pending_approver_to_pending_approval(pending_worflows):
    for pending_worflow in pending_worflows:
        try:
            doc = frappe.get_doc("Shift Request", pending_worflow["name"])
            doc.workflow_state = "Pending Approval"
            doc.save()
            frappe.db.commit()     
        except Exception as e:
            frappe.log_error(frappe.get_traceback(), f"Failed to update {pending_worflow['name']}")

