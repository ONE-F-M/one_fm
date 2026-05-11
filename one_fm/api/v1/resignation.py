import frappe
import json
import base64
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.model.workflow import apply_workflow
from one_fm.api.mobile_utils import get_param, get_all_params


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def resolve_employee_name(employee_id):
    """Resolves a custom employee_id (e.g. '2202025NP191') to the Frappe PK
    (e.g. 'HR-EMP-01873').  Also accepts the PK directly as a fallback."""
    if not employee_id:
        return None
    name = frappe.db.get_value("Employee", {"employee_id": employee_id}, "name")
    if name:
        return name
    if frappe.db.exists("Employee", employee_id):
        return employee_id
    return None


def handle_attachment_internal(doc, row, attachment_data, field_name):
    """Saves a base64 attachment and links it to field_name on row."""
    if isinstance(attachment_data, str):
        try:
            attachment_data = json.loads(attachment_data)
        except Exception:
            raise frappe.ValidationError(_("Invalid attachment payload. Expected valid JSON data."))

    file_name = attachment_data.get("attachment_name")
    file_base64 = attachment_data.get("attachment")

    if file_name and file_base64:
        try:
            if "," in file_base64:
                file_base64 = file_base64.split(",", 1)[1]
            
            # If sent via form data, '+' might be converted to ' '
            file_base64 = file_base64.replace(" ", "+")
            file_base64 = file_base64.replace("\n", "").replace("\r", "")
            
            # Add padding if missing (Base64 length must be a multiple of 4)
            missing_padding = len(file_base64) % 4
            if missing_padding:
                file_base64 += '=' * (4 - missing_padding)
            
            # Try to decode safely, replacing URL-safe chars if necessary
            # URL safe base64 uses - and _ instead of + and /
            file_base64 = file_base64.replace("-", "+").replace("_", "/")
            content = base64.b64decode(file_base64)
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": file_name,
                "attached_to_doctype": doc.doctype,
                "attached_to_name": doc.name,
                "content": content,
                "is_private": 1
            })
            file_doc.save()
            frappe.db.set_value(row.doctype, row.name, field_name, file_doc.file_url)
        except Exception as e:
            frappe.log_error(f"Attachment failed for {file_name}", str(e))
            frappe.throw(_("Failed to process attachment."), frappe.ValidationError)


# ---------------------------------------------------------------------------
# Public API endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_resignation(
    employee_id=None,
    supervisor=None,
    resignation_initiation_date=None,
    relieving_date=None,
    attachment=None,
    data=None,
    **kwargs
):
    try:
        p = get_all_params(
            "resignation_initiation_date", "relieving_date", "attachment",
            employee_id=employee_id,
            supervisor=supervisor,
        )
        input_id   = p["employee_id"]
        supervisor = p["supervisor"]
        init_date  = p["resignation_initiation_date"]
        rel_date   = p["relieving_date"] or get_param("resignation_date")
        attachment = p["attachment"]

        if not attachment:
            frappe.throw(_("Attachment is mandatory for resignation submission"), frappe.ValidationError)

        employee_name = resolve_employee_name(input_id)
        if not employee_name:
            frappe.throw(f"Employee '{input_id}' not found", frappe.ValidationError)

        employee_user = frappe.db.get_value("Employee", employee_name, "user_id")
        if employee_user != frappe.session.user and not frappe.has_permission("Employee Resignation", ptype="create"):
            frappe.throw(_("Not authorized to submit a resignation for this employee"), frappe.PermissionError)

        emp = frappe.db.get_value(
            "Employee", employee_name,
            ["employee_name", "designation", "project", "department",
             "employment_type", "reports_to"],
            as_dict=True
        )

        # Fetch the employee's linked user_id so the record is owned by them on the desk
        employee_user = frappe.db.get_value("Employee", employee_name, "user_id")

        doc = frappe.new_doc("Employee Resignation")
        doc.owner = employee_user or frappe.session.user
        doc.employee = employee_name
        doc.resignation_initiation_date = init_date
        doc.relieving_date = rel_date
        doc.supervisor = supervisor
        doc.department = emp.get("department")
        doc.employment_type = emp.get("employment_type")
        doc.project_allocation = emp.get("project")
        doc.designation = emp.get("designation")
        # Insert as Draft first so validate() doesn't block on missing letter
        doc.workflow_state = "Draft"

        doc.append("employees", {
            "employee": employee_name,
            "employee_name": emp.get("employee_name"),
            "designation": emp.get("designation"),
            "project_allocation": emp.get("project"),
            "employment_type": emp.get("employment_type"),
            "resignation_letter_date": rel_date,
        })

        doc.insert()

        # Step 2: Attach the letter (must happen after insert so the row has a name)
        if attachment:
            if isinstance(attachment, str):
                try:
                    attachment = json.loads(attachment)
                except Exception:
                    pass
            att_data = attachment if isinstance(attachment, dict) else {
                "attachment_name": get_param("attachment_name", explicit_value=None) or "resignation_letter.png",
                "attachment": attachment,
            }
            for row in doc.employees:
                handle_attachment_internal(doc, row, att_data, "resignation_letter")

        # Step 3: Advance to Pending Supervisor now that the letter is saved
        doc.reload()
        apply_workflow(doc, "Submit to Supervisor")
        return {"status": "success", "message": "Resignation submitted successfully", "name": doc.name}

    except Exception as e:
        frappe.log_error("Create Resignation Error", f"Exception: {str(e)}\n\nTraceback:\n{frappe.get_traceback()}")
        if isinstance(e, frappe.ValidationError) or isinstance(e, frappe.PermissionError):
            raise
        frappe.throw(str(e), frappe.ValidationError)


@frappe.whitelist()
def extend_resignation(
    employee_id=None,
    supervisor=None,
    reason=None,
    extended_date=None,
    resignation_id=None,
    attachment=None,
    data=None,
    **kwargs
):
    """Create an Employee Resignation Date Adjustment for the employee's active resignation."""
    try:
        p = get_all_params(
            "attachment",
            employee_id=employee_id,
            supervisor=supervisor,
            resignation_id=resignation_id,
            reason=reason,
            extended_date=extended_date,
        )
        input_id       = p["employee_id"]
        supervisor     = p["supervisor"]
        reason         = p["reason"]
        extended_date  = p["extended_date"]
        resignation_id = p["resignation_id"]
        attachment     = p["attachment"]

        employee_name = resolve_employee_name(input_id)
        if not employee_name:
            frappe.throw(f"Employee '{input_id}' not found", frappe.ValidationError)
        if not extended_date:
            frappe.throw("extended_date is required", frappe.ValidationError)

        # Find active resignation if not supplied
        if not resignation_id:
            TERMINAL = ["Resigned", "Cancelled", "Resignation Withdrawn", "Withdrawn"]
            active_resignations = frappe.get_list(
                "Employee Resignation",
                filters={"employee": employee_name, "workflow_state": ["not in", TERMINAL]},
                fields=["name"],
                order_by="creation desc",
                limit=1
            )
            if active_resignations:
                resignation_id = active_resignations[0].name

        if not resignation_id:
            frappe.throw("No active resignation found to extend", frappe.ValidationError)

        active_doc = frappe.get_doc("Employee Resignation", resignation_id)
        employee_user = frappe.db.get_value("Employee", employee_name, "user_id")

        ext = frappe.new_doc("Employee Resignation Date Adjustment")
        ext.owner = employee_user or frappe.session.user
        ext.employee_resignation = resignation_id
        ext.supervisor = supervisor or active_doc.supervisor
        ext.extended_relieving_date = extended_date
        # Do NOT set workflow_state before insert — Frappe sets it to the
        # workflow's initial state ('Pending Supervisor') automatically

        for row in active_doc.employees:
            ext.append("employees", {
                "employee": row.employee,
                "employee_name": row.employee_name,
                "designation": row.designation,
                "reason": reason or "Adjustment requested by employee"
            })

        ext.insert()

        # Attach letter after insert so the row has a name
        if attachment and ext.get("employees"):
            if isinstance(attachment, dict):
                att_data = attachment
            else:
                try:
                    att_json = json.loads(attachment)
                    if isinstance(att_json, list):
                        att_json = att_json[0]
                    att_data = att_json if isinstance(att_json, dict) else {"attachment_name": "extension_letter.png", "attachment": attachment}
                except Exception:
                    att_data = {"attachment_name": "extension_letter.png", "attachment": attachment}

            first_row = ext.employees[0]
            handle_attachment_internal(ext, first_row, att_data, "extension_letter")

        return {
            "status": "success",
            "message": "Resignation adjustment submitted successfully",
            "name": ext.name
        }

    except Exception as e:
        frappe.log_error("Extension Error", frappe.get_traceback())
        frappe.throw(str(e), frappe.ValidationError)


@frappe.whitelist()
def withdraw_resignation(
    employee_id=None,
    reason=None,
    attachment=None,
    employee_resignation=None,
    supervisor=None,
    data=None,
    **kwargs
):
    try:
        p = get_all_params(
            "attachment",
            employee_id=employee_id,
            reason=reason,
            employee_resignation=employee_resignation,
            supervisor=supervisor,
        )
        input_id   = p["employee_id"]
        reason     = p["reason"]
        attachment = p["attachment"]
        employee_resignation_id = p["employee_resignation"]
        supervisor_id = p["supervisor"]

        employee_name = resolve_employee_name(input_id)
        if not employee_name:
            frappe.throw(f"Employee '{input_id}' not found", frappe.ValidationError)

        # Find the most recent active resignation
        TERMINAL = ["Resigned", "Cancelled", "Resignation Withdrawn", "Withdrawn"]
        active_resignations = frappe.get_list(
            "Employee Resignation",
            filters={"employee": employee_name, "workflow_state": ["not in", TERMINAL]},
            fields=["name"],
            order_by="creation desc",
            limit=1
        )
        
        active_doc = None
        if active_resignations:
            active_doc = frappe.get_doc("Employee Resignation", active_resignations[0].name)

        if not active_doc:
            frappe.throw("No active resignation found to withdraw", frappe.ValidationError)

        employee_user = frappe.db.get_value("Employee", employee_name, "user_id")
        withdrawal = frappe.new_doc("Employee Resignation Withdrawal")
        withdrawal.owner = employee_user or frappe.session.user
        withdrawal.employee_resignation = active_doc.name
        # Do NOT set workflow_state before insert — Frappe sets it to the
        # workflow's initial state ('Pending Supervisor') automatically

        for row in active_doc.employees:
            withdrawal.append("employees", {
                "employee": row.employee,
                "employee_name": row.employee_name,
                "designation": row.designation,
                "reason": reason or "Employee-initiated withdrawal"
            })

        withdrawal.insert()

        if attachment and withdrawal.get("employees"):
            if isinstance(attachment, dict):
                att_data = attachment
            else:
                try:
                    att_json = json.loads(attachment)
                    if isinstance(att_json, list):
                        att_json = att_json[0]
                    att_data = att_json if isinstance(att_json, dict) else {"attachment_name": "withdrawal_letter.png", "attachment": attachment}
                except Exception:
                    att_data = {"attachment_name": "withdrawal_letter.png", "attachment": attachment}

            # Attach to the first child row on the 'attachment' field
            first_row = withdrawal.employees[0]
            handle_attachment_internal(withdrawal, first_row, att_data, "attachment")

        # Notify offboarding officer
        try:
            offboarding_officer = frappe.db.get_single_value(
                "HR Settings", "offboarding_officer"
            ) if frappe.db.exists("DocType", "HR Settings") else None
            if offboarding_officer:
                frappe.share.add(
                    "Employee Resignation Withdrawal", withdrawal.name,
                    user=offboarding_officer, read=1, notify=1,
                    flags={"ignore_share_permission": True}
                )
        except Exception:
            pass

        return {"status": "success", "message": "Withdrawal submitted", "name": withdrawal.name}

    except Exception as e:
        frappe.log_error("Withdrawal Error", frappe.get_traceback())
        frappe.throw(str(e), frappe.ValidationError)


@frappe.whitelist()
def correct_resignation_date_app(
    employee_id=None,
    resignation_id=None,
    new_date=None,
    new_initiation_date=None,
    attachment=None,
    attachment_name=None,
    data=None,
    **kwargs
):
    try:
        p = get_all_params(
            "new_date", "new_initiation_date", "attachment", "attachment_name",
            employee_id=employee_id,
            resignation_id=resignation_id,
        )
        input_id         = p["employee_id"]
        resignation_id   = p["resignation_id"]
        new_date         = p["new_date"]
        new_initiation   = p["new_initiation_date"]
        attachment       = p["attachment"]
        att_name         = p["attachment_name"] or "corrected_resignation_letter.png"

        if not resignation_id:
            frappe.throw("resignation_id is required", frappe.ValidationError)
        if not new_date:
            frappe.throw("new_date (relieving date) is required", frappe.ValidationError)

        doc = frappe.get_doc("Employee Resignation", resignation_id)

        if doc.workflow_state != "Pending Relieving Date Correction":
            frappe.throw(
                f"Cannot correct date. Current state: {doc.workflow_state}",
                frappe.ValidationError
            )

        doc.relieving_date = new_date
        if new_initiation:
            doc.resignation_initiation_date = new_initiation

        if attachment:
            if isinstance(attachment, str):
                try:
                    attachment = json.loads(attachment)
                except Exception:
                    pass
            att_data = attachment if isinstance(attachment, dict) else {
                "attachment_name": att_name,
                "attachment": attachment,
            }
            for row in doc.employees:
                handle_attachment_internal(doc, row, att_data, "resignation_letter")

        apply_workflow(doc, "Resubmit Date")

        return {
            "status": "success",
            "message": "Resignation date corrected and resubmitted to supervisor",
            "name": doc.name
        }

    except Exception as e:
        frappe.log_error("Correction Error", frappe.get_traceback())
        frappe.throw(str(e), frappe.ValidationError)


@frappe.whitelist()
def get_supervisor_dropdown():
    return frappe.get_all(
        "User",
        filters={"enabled": 1, "user_type": "System User"},
        fields=["name", "full_name"]
    )


@frappe.whitelist()
def get_my_active_resignation(employee_id=None, **kwargs):
    """Returns a single resignation record the employee should act on next,
    prioritising states that require employee action over waiting states."""
    input_id = get_param("employee_id", employee_id)
    employee_name = resolve_employee_name(input_id)
    if not employee_name:
        return None

    employee_user = frappe.db.get_value("Employee", employee_name, "user_id")
    if employee_user != frappe.session.user and not frappe.has_permission("Employee Resignation", ptype="read"):
        frappe.throw(_("Not authorized to view this employee's active resignation"), frappe.PermissionError)

    EMPLOYEE_ACTION_STATES = ["Pending Relieving Date Correction", "Draft"]
    TERMINAL_STATES = {"Resigned", "Cancelled", "Resignation Withdrawn", "Withdrawn"}



    resignations = frappe.get_list(
        "Employee Resignation",
        filters={"employee": employee_name, "workflow_state": ["not in", list(TERMINAL_STATES)]},
        fields=["name", "workflow_state", "resignation_initiation_date", "relieving_date", "creation"],
        order_by="creation desc"
    )

    if not resignations:
        return None



    for record in resignations:
        if record["workflow_state"] in EMPLOYEE_ACTION_STATES:
            return record

    return resignations[0]


@frappe.whitelist()
def get_all_my_resignations(employee_id=None, **kwargs):
    """Returns all non-terminal resignation records for the employee."""
    input_id = get_param("employee_id", employee_id)
    employee_name = resolve_employee_name(input_id)
    if not employee_name:
        return []

    TERMINAL_STATES = {"Resigned", "Cancelled", "Resignation Withdrawn", "Withdrawn"}
    EMPLOYEE_ACTION_STATES = ["Pending Relieving Date Correction", "Draft"]

    resignations = frappe.get_list(
        "Employee Resignation",
        filters={"employee": employee_name},
        fields=["name", "workflow_state", "resignation_initiation_date", "relieving_date", "creation"],
        order_by="creation desc"
    )



    return resignations


@frappe.whitelist()
def get_employee_supervisor(employee_id=None, **kwargs):
    from one_fm.utils import get_approver
    input_id = get_param("employee_id", employee_id)
    employee_name = resolve_employee_name(input_id)
    if not employee_name:
        return {}

    approver_name = get_approver(employee_name)
    if not approver_name:
        return {}

    supervisor = frappe.db.get_value(
        "Employee", approver_name,
        ["user_id", "employee_name"], as_dict=True
    )
    if supervisor and supervisor.get("user_id"):
        return {"user_id": supervisor.get("user_id"), "full_name": supervisor.get("employee_name")}
    return {}
