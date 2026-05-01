import frappe
from frappe import _

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
        context.docs = []
        return context

    start = frappe.form_dict.get("start", 0)
    
    # Fetch unique (from_date, to_date) groupings for this supplier
    records = frappe.db.sql("""
        SELECT 
            subcontractor_name, from_date, to_date, 
            GROUP_CONCAT(name SEPARATOR ', ') as names,
            GROUP_CONCAT(workflow_state) as states
        FROM `tabSubcontract Staff Attendance`
        WHERE subcontractor_name = %s
        GROUP BY from_date, to_date
        ORDER BY from_date DESC
        LIMIT 20 OFFSET %s
    """, (supplier, start), as_dict=True)

    formatted_docs = []
    for r in records:
        states = r.states.split(',') if r.states else []
        # Calculate compound state
        if "Draft" in states:
            compound_state = "Draft"
            color = "orange"
        elif "Pending Operations Supervisor" in states:
            compound_state = "Pending Operations Supervisor"
            color = "blue"
        elif "Pending Project Manager" in states:
            compound_state = "Pending Project Manager"
            color = "blue"
        else:
            compound_state = "Approved"
            color = "green"

        formatted_docs.append({
            "names": r.names,
            "subcontractor_name": r.subcontractor_name,
            "from_date": r.from_date,
            "to_date": r.to_date,
            "state": compound_state,
            "color": color
        })

    start_num = int(start)
    context.docs = formatted_docs
    context.next_start = start_num + 20 if len(records) == 20 else 0
    context.prev_start = start_num - 20 if start_num >= 20 else 0
    context.supplier = supplier
    context.no_cache = 1
    context.parents = [{'name': 'me', 'title': _('My Account'), 'route': '/me'}]
