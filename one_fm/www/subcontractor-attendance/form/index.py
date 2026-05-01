import frappe
from frappe import _
import json

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login"
        raise frappe.Redirect

    supplier = frappe.db.get_value(
        "User Permission",
        {"user": frappe.session.user, "allow": "Supplier"},
        "for_value"
    )

    if not supplier:
        frappe.local.flags.redirect_location = "/"
        raise frappe.Redirect

    context.supplier = supplier
    context.parents = [
        {'name': 'me', 'title': _('My Account'), 'route': '/me'},
        {'name': 'subcontractor-attendance', 'title': _('Subcontract Staff Attendance'), 'route': '/subcontractor-attendance'}
    ]

    from_date = frappe.form_dict.get("from_date")
    to_date = frappe.form_dict.get("to_date")

    context.from_date = from_date or ""
    context.to_date = to_date or ""
    
    employees = {}
    doc_states = []

    if from_date and to_date:
        site_docs = frappe.get_all(
            "Subcontract Staff Attendance",
            filters={
                "subcontractor_name": supplier,
                "from_date": from_date,
                "to_date": to_date
            },
            fields=["name", "site", "workflow_state", "attendance_record_based_on"]
        )

        context.based_on = site_docs[0].attendance_record_based_on if site_docs else "Attendance Status"

        for sdoc in site_docs:
            doc_states.append(sdoc.workflow_state)
            
            items = frappe.get_all(
                "Subcontractor Staff Attendance Item",
                filters={"parent": sdoc.name},
                fields=["*"]
            )
            
            for item in items:
                emp_id = item.employee_id
                if emp_id not in employees:
                    employees[emp_id] = {
                        "employee_id": emp_id,
                        "employee_name": item.employee_name,
                        "employee": item.employee,
                        "days": {}
                    }
                
                for i in range(1, 32):
                    day_field = f"day_{i}"
                    hour_field = f"day_{i}_hour"
                    
                    val = item.get(day_field)
                    hour_val = item.get(hour_field)
                    
                    if context.based_on == "Attendance Status":
                        if val:
                            employees[emp_id]["days"][str(i)] = {
                                "value": val,
                                "site": sdoc.site,
                                "status": sdoc.workflow_state,
                                "parent_doc": sdoc.name,
                                "remarks": item.remarks,
                                "comment": item.comment
                            }
                    else:
                        if hour_val is not None:
                            employees[emp_id]["days"][str(i)] = {
                                "value": hour_val,
                                "status_val": val, 
                                "site": sdoc.site,
                                "status": sdoc.workflow_state,
                                "parent_doc": sdoc.name,
                                "remarks": item.remarks,
                                "comment": item.comment
                            }

        if "Draft" in doc_states:
            compound_state = "Draft"
        elif "Pending Operations Supervisor" in doc_states:
            compound_state = "Pending Operations Supervisor"
        elif "Pending Project Manager" in doc_states:
            compound_state = "Pending Project Manager"
        elif "Approved" in doc_states:
            compound_state = "Approved"
        else:
            compound_state = "New"

        context.compound_state = compound_state
    else:
        context.compound_state = "New"
        context.based_on = "Attendance Status"

    context.merged_data = json.dumps(list(employees.values()))
    context.no_cache = 1
