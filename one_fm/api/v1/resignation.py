import frappe
import json
import base64
from frappe import _
from frappe.utils.file_manager import save_file


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

def verify_employee_authorization(employee_name):
    """Ensure the logged-in user is authorized to act on behalf of the employee."""
    if frappe.session.user == "Administrator" or "HR Manager" in frappe.get_roles(frappe.session.user):
        return

    employee_user = frappe.db.get_value("Employee", employee_name, "user_id")
    if frappe.session.user != employee_user:
        frappe.log_error(f"AUTH FAIL: session_user={frappe.session.user}, employee_user={employee_user}", "AUTH_DEBUG")
        frappe.throw("Not authorized to perform this action for this employee.", frappe.PermissionError)


def handle_attachment_internal(doc, row, attachment_data, field_name):
    """Saves a base64 attachment and links it to field_name on row."""
    if isinstance(attachment_data, str):
        try:
            attachment_data = json.loads(attachment_data)
        except Exception as e:
            frappe.log_error(str(e), f"Attachment JSON Decode Error for {doc.doctype} {doc.name}")
            frappe.throw(f"Failed to parse attachment data: {str(e)}", frappe.ValidationError)


    if not isinstance(attachment_data, dict):
        frappe.throw(_("Attachment payload must be a JSON object."), frappe.ValidationError)

    file_name = attachment_data.get("attachment_name")
    file_base64 = attachment_data.get("attachment")

    if not file_name or not file_base64:
        frappe.throw(
            _("Attachment payload must include both 'attachment_name' and 'attachment'."),
            frappe.ValidationError
        )

    try:
        content = base64.b64decode(file_base64, validate=True)
        saved_file = save_file(
            file_name, content, doc.doctype, doc.name,
            is_private=1, folder="Home/Attachments"
        )
        file_url = saved_file.file_url
        frappe.db.set_value(row.doctype, row.name, field_name, file_url)
        # Keep the in-memory row in sync with the DB so any subsequent
        # validations/workflow actions using the current doc see the attachment.
        if hasattr(row, "set"):
            row.set(field_name, file_url)
        else:
            setattr(row, field_name, file_url)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"Attachment Save Error for {doc.doctype} {doc.name}")
        frappe.throw(f"Failed to save attachment {file_name}: {str(e)}", frappe.ValidationError)


# ---------------------------------------------------------------------------
# Public API endpoints
# ---------------------------------------------------------------------------

@frappe.whitelist()
def create_resignation(
    employee_id: str = None,
    supervisor: str = None,
    resignation_initiation_date: str = None,
    relieving_date: str = None,
    attachment: str = None,
    data: dict = None,
    **kwargs
) -> dict:
    try:
        input_id = employee_id
        init_date = resignation_initiation_date
        legacy_relieving_date = kwargs.get("resignation_date")
        if relieving_date and legacy_relieving_date and relieving_date != legacy_relieving_date:

            frappe.throw(
                _("Conflicting values provided for relieving_date and resignation_date. Please use relieving_date."),
                frappe.ValidationError
            )
        rel_date = relieving_date or legacy_relieving_date

        if not attachment:
            frappe.throw("A resignation letter attachment is mandatory.", frappe.ValidationError)

        employee_name = resolve_employee_name(input_id)
        if not employee_name:
            frappe.throw(f"Employee '{input_id}' not found", frappe.ValidationError)
            
        verify_employee_authorization(employee_name)

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
            "resignation_letter_date": init_date,
        })

        doc.insert(ignore_permissions=True)

        # Step 2: Attach the letter (must happen after insert so the row has a name)
        if attachment:
            att_str = attachment if isinstance(attachment, str) else json.dumps(attachment)
            try:
                att_data = json.loads(att_str) if isinstance(att_str, str) else att_str
            except Exception:
                att_data = {"attachment_name": "resignation_letter.png", "attachment": att_str}
            
            # The row we appended earlier
            row = doc.employees[0]
            handle_attachment_internal(doc, row, att_data, "resignation_letter")

        # Step 3: Advance using the configured workflow transition now that the letter is saved
        from frappe.model.workflow import apply_workflow
        apply_workflow(doc, "Submit to Offboarding Officer")
        return {"status": "success", "message": "Resignation submitted successfully", "name": doc.name}

    except (frappe.PermissionError, frappe.ValidationError):
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Create Resignation Error")
        frappe.throw(str(e), frappe.ValidationError)


@frappe.whitelist()
def extend_resignation(
    employee_id: str = None,
    supervisor: str = None,
    reason: str = None,
    extended_date: str = None,
    resignation_id: str = None,
    attachment: str = None,
    data: dict = None,
    **kwargs
) -> dict:
    """Create an Employee Resignation Extension for the employee's active resignation."""
    try:
        input_id = employee_id

        employee_name = resolve_employee_name(input_id)
        if not employee_name:
            frappe.throw(f"Employee '{input_id}' not found", frappe.ValidationError)
        verify_employee_authorization(employee_name)
        if not extended_date:
            frappe.throw("extended_date is required", frappe.ValidationError)

        # Find active resignation if not supplied
        if not resignation_id:
            items = frappe.get_list(
                "Employee Resignation Item",
                filters={"employee": employee_name, "parenttype": "Employee Resignation"},
                fields=["parent"], order_by="creation desc"
            )
            TERMINAL = ["Resigned", "Cancelled", "Resignation Withdrawn", "Withdrawn"]
            parents = list(set(i.parent for i in items))
            if parents:
                resigs = frappe.get_list(
                    "Employee Resignation",
                    filters={"name": ["in", parents], "workflow_state": ["not in", TERMINAL]},
                    fields=["name", "workflow_state"],
                    order_by="creation desc",
                    limit=1
                )
                if resigs:
                    resignation_id = resigs[0].name

        if not resignation_id:
            frappe.throw("No active resignation found to extend", frappe.ValidationError)

        active_doc = frappe.get_doc("Employee Resignation", resignation_id)
        employee_user = frappe.db.get_value("Employee", employee_name, "user_id")

        ext = frappe.new_doc("Employee Resignation Extension")
        ext.owner = employee_user or frappe.session.user
        ext.employee_resignation = resignation_id
        ext.supervisor = supervisor or active_doc.supervisor
        # Ensure we only extract the date part (YYYY-MM-DD) if it's an ISO timestamp
        parsed_date = extended_date.split('T')[0] if isinstance(extended_date, str) else extended_date
        ext.extended_relieving_date = parsed_date
        # Do NOT set workflow_state before insert — Frappe sets it to the
        # workflow's initial state ('Pending Supervisor') automatically

        for row in active_doc.employees:
            ext.append("employees", {
                "employee": row.employee,
                "employee_name": row.employee_name,
                "reason": reason or "Extension requested by employee",
            })

        ext.insert(ignore_permissions=True)

        # Attach letter after insert so the row has a name
        if attachment:
            att_str = attachment if isinstance(attachment, str) else json.dumps(attachment)
            try:
                att_data = json.loads(att_str) if isinstance(att_str, str) else att_str
            except Exception:
                att_data = {"attachment_name": "extension_letter.png", "attachment": att_str}
            
            # Attach to the child row (Employee Resignation Extension Item)
            if ext.employees:
                handle_attachment_internal(ext, ext.employees[0], att_data, "extension_letter")
            
        return {
            "status": "success",
            "message": "Resignation extension submitted successfully",
            "name": ext.name
        }

    except (frappe.PermissionError, frappe.ValidationError):
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Extension Error")
        frappe.throw(str(e), frappe.ValidationError)


@frappe.whitelist()
def withdraw_resignation(
    employee_id: str = None,
    reason: str = None,
    attachment: str = None,
    data: dict = None,
    **kwargs
) -> dict:
    try:
        input_id = employee_id

        employee_name = resolve_employee_name(input_id)
        if not employee_name:
            frappe.throw(f"Employee '{input_id}' not found", frappe.ValidationError)
        verify_employee_authorization(employee_name)

        # Find the most recent active resignation
        items = frappe.get_list(
            "Employee Resignation Item",
            filters={"employee": employee_name, "parenttype": "Employee Resignation"},
            fields=["parent"],
            order_by="creation desc"
        )

        active_doc = None
        TERMINAL = ["Resigned", "Cancelled", "Resignation Withdrawn", "Withdrawn"]
        parents = list(set(i.parent for i in items))
        if parents:
            resigs = frappe.get_list(
                "Employee Resignation",
                filters={"name": ["in", parents], "workflow_state": ["not in", TERMINAL]},
                fields=["name", "workflow_state"],
                order_by="creation desc",
                limit=1
            )
            if resigs:
                active_doc = frappe.get_doc("Employee Resignation", resigs[0].name)

        if not active_doc:
            frappe.throw("No active resignation found to withdraw", frappe.ValidationError)

        employee_user = frappe.db.get_value("Employee", employee_name, "user_id")
        withdrawal = frappe.new_doc("Employee Resignation Withdrawal")
        withdrawal.owner = employee_user or frappe.session.user
        withdrawal.employee_resignation = active_doc.name
        withdrawal.reason = reason or "Employee-initiated withdrawal"
        # Do NOT set workflow_state before insert — Frappe sets it to the
        # workflow's initial state ('Pending Supervisor') automatically

        for row in active_doc.employees:
            withdrawal.append("employees", {
                "employee": row.employee,
                "employee_name": row.employee_name,
                "reason": reason or "Employee-initiated withdrawal",
            })

        withdrawal.insert(ignore_permissions=True)

        if attachment:
            att_str = attachment if isinstance(attachment, str) else json.dumps(attachment)
            try:
                att_data = json.loads(att_str) if isinstance(att_str, str) else att_str
            except Exception:
                att_data = {"attachment_name": "withdrawal_letter.png", "attachment": att_str}
                
            if withdrawal.employees:
                handle_attachment_internal(withdrawal, withdrawal.employees[0], att_data, "attachment")
            
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

    except (frappe.PermissionError, frappe.ValidationError):
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Withdrawal Error")
        frappe.throw(str(e), frappe.ValidationError)


@frappe.whitelist()
def correct_resignation_date_app(
    employee_id: str = None,
    resignation_id: str = None,
    new_date: str = None,
    new_initiation_date: str = None,
    attachment: str = None,
    attachment_name: str = None,
    data: dict = None,
    **kwargs
) -> dict:
    try:
        p = get_all_params(
            "new_date", "new_initiation_date", "attachment", "attachment_name",
            employee_id=employee_id,
            resignation_id=resignation_id,
            new_date=new_date,
            new_initiation_date=new_initiation_date,
            attachment=attachment,
            attachment_name=attachment_name,
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
        if doc.employees:
            verify_employee_authorization(doc.employees[0].employee)

        if doc.workflow_state != "Pending Relieving Date Correction":
            frappe.throw(
                f"Cannot correct date. Current state: {doc.workflow_state}",
                frappe.ValidationError
            )

        doc.relieving_date = new_date
        if new_initiation:
            doc.resignation_initiation_date = new_initiation

        if new_initiation:
            for row in doc.employees:
                row.resignation_letter_date = new_initiation

        if attachment:
            att_str = attachment if isinstance(attachment, str) else json.dumps(attachment)
            try:
                att_data = json.loads(att_str) if isinstance(att_str, str) else att_str
            except Exception:
                att_data = {"attachment_name": att_name, "attachment": att_str}
            if doc.employees:
                handle_attachment_internal(doc, doc.employees[0], att_data, "resignation_letter")

        doc.save()
        
        from frappe.model.workflow import apply_workflow
        apply_workflow(doc, "Resubmit Date")
        
        
        return {
            "status": "success",
            "message": "Resignation date corrected and resubmitted to supervisor",
            "name": doc.name
        }

    except (frappe.PermissionError, frappe.ValidationError):
        raise
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Correction Error")
        frappe.throw(str(e), frappe.ValidationError)


@frappe.whitelist()
def get_supervisor_dropdown(**kwargs) -> list:
    return frappe.get_list(
        "User",
        filters={"enabled": 1, "user_type": "System User"},
        fields=["name", "full_name"]
    )


@frappe.whitelist()
def get_my_active_resignation(employee_id: str = None, **kwargs) -> dict:
    """Returns a single resignation record the employee should act on next,
    prioritising states that require employee action over waiting states."""
    input_id = employee_id
    employee_name = resolve_employee_name(input_id)
    if not employee_name:
        return None
    verify_employee_authorization(employee_name)

    EMPLOYEE_ACTION_STATES = ["Pending Relieving Date Correction", "Draft"]
    TERMINAL_STATES = {"Resigned", "Cancelled", "Withdrawn", "Resignation Withdrawn"}

    seen = set()
    items = frappe.get_list(
        "Employee Resignation Item",
        filters={"employee": employee_name, "parenttype": "Employee Resignation"},
        fields=["parent"],
        order_by="creation desc"
    )

    all_records = []
    parents = list(set(i.parent for i in items))
    if parents:
        docs = frappe.get_list(
            "Employee Resignation",
            filters={"name": ["in", parents], "workflow_state": ["not in", list(TERMINAL_STATES)]},
            fields=["name", "workflow_state", "resignation_initiation_date", "relieving_date", "creation", "supervisor"],
            order_by="creation desc"
        )
        for doc in docs:
            doc_dict = dict(doc)
            doc_dict["creation"] = str(doc.creation)
            doc_dict["supervisor_name"] = frappe.db.get_value("User", doc.supervisor, "full_name") if doc.supervisor else None
            all_records.append(doc_dict)

    if not all_records:
        return None

    for record in all_records:
        if record["workflow_state"] in EMPLOYEE_ACTION_STATES:
            return record

    return all_records[0]


@frappe.whitelist()
def get_all_my_resignations(employee_id: str = None, **kwargs) -> list:
    """Returns all resignation records for the employee (history list)."""
    input_id = employee_id
    employee_name = resolve_employee_name(input_id)
    if not employee_name:
        return []
    verify_employee_authorization(employee_name)

    seen = set()
    items = frappe.get_list(
        "Employee Resignation Item",
        filters={"employee": employee_name, "parenttype": "Employee Resignation"},
        fields=["parent"],
        order_by="creation desc"
    )

    results = []
    parents = list(set(i.parent for i in items))
    if parents:
        docs = frappe.get_list(
            "Employee Resignation",
            filters={"name": ["in", parents]},
            fields=["name", "workflow_state", "resignation_initiation_date", "relieving_date", "creation"],
            order_by="creation desc"
        )
        for doc in docs:
            doc_dict = dict(doc)
            doc_dict["creation"] = str(doc.creation)
            results.append(doc_dict)

    return results


@frappe.whitelist()
def get_employee_supervisor(employee_id: str = None, **kwargs) -> dict:
    from one_fm.utils import get_approver
    input_id = employee_id
    employee_name = resolve_employee_name(input_id)
    if not employee_name:
        return {}
    verify_employee_authorization(employee_name)

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
