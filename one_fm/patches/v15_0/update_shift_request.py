import frappe
import datetime, click
from frappe.utils.fixtures import sync_fixtures
from one_fm.overrides.shift_request import fetch_approver
from one_fm.utils import get_approver
from one_fm.api.notification import get_employee_user_id

def execute():
    sync_fixtures("one_fm")
    # Pending Approval and Draft 
    open_shift_requests = frappe.get_all("Shift Request", 
        fields=["name", "shift_approver", "department", "workflow_state", "employee"], 
        filters={"shift_approver": ("is", "set"), "workflow_state": ["in", ["Pending Approval", "Draft"]]},
        order_by="creation desc")

    update_sr(open_shift_requests)

    open_shift_requests = frappe.get_all("Shift Request", 
        fields=["name", "shift_approver", "department", "workflow_state", "employee"], 
        filters={"shift_approver": ("is", "set"), "workflow_state": ["in", ["Approved", "Rejected"]]},
        order_by="creation desc")

    update_submitted_sr(open_shift_requests)

def update_submitted_sr(shift_requests):
    for shift_request in shift_requests:
        if frappe.db.exists("Shift Request Approvers", {"parent": shift_request.name}):
            continue
        approver_user_id = shift_request.shift_approver
        doc = frappe.get_doc("Shift Request", shift_request.name)
        try:
            doc.append("custom_shift_approvers", {
                "user": approver_user_id
            })
            for approver in doc.custom_shift_approvers:
                approver.set_user_and_timestamp()
                approver.set_new_name()
                insert_approver(approver)
        except Exception:
            click.echo(frappe.get_traceback())



def update_sr(shift_requests):
    for shift_request in shift_requests:
        employee_user_id = get_employee_user_id(shift_request.employee)
        approver_user_id = shift_request.shift_approver
        doc = frappe.get_doc("Shift Request", shift_request.name)
            
        if shift_request.department == "Operations - ONEFM":        
            other_approvers = []
            if shift_request.department == "Operations - ONEFM":
                other_approvers =[user.approver for user in frappe.get_all("Department Approver", filters={"parent": shift_request.department}, fields=["approver"]) if user.approver != employee_user_id and user.approver != approver_user_id]

            other_approvers.append(approver_user_id)
            for approver in other_approvers:
                doc.append("custom_shift_approvers", {
                    "user": approver
                })
        else:
            doc.append("custom_shift_approvers", {
                "user": approver_user_id
            })

        for approver in doc.custom_shift_approvers:
            approver.set_user_and_timestamp()
            approver.set_new_name()
            insert_approver(approver)


def insert_approver(approver):
    # Migrate directly using sql for submitted Shift Requests
    values = {
        'name': approver.name,
        'owner': approver.owner,
        'creation': approver.creation.strftime("%Y-%m-%d %H:%M:%S.%f") if not isinstance(approver.creation, str) else approver.creation,
        'modified': approver.modified.strftime("%Y-%m-%d %H:%M:%S.%f") if not isinstance(approver.modified, str) else approver.modified,
        'modified_by': approver.modified_by,
        'docstatus': approver.docstatus,
        'idx': approver.idx,
        'user': approver.user,
        'parent': approver.parent,
        'parenttype': approver.parenttype,
        'parentfield': approver.parentfield
    }

    frappe.db.sql("""
        insert into `tabShift Request Approvers` 
            (name, owner, creation, modified, modified_by, docstatus, idx, user, parent, parentfield, parenttype) 
        values 
            (%(name)s, %(owner)s, %(creation)s, %(modified)s, %(modified_by)s, %(docstatus)s, %(idx)s, %(user)s, %(parent)s, %(parentfield)s, %(parenttype)s)
    """, values=values)

    frappe.db.commit()
