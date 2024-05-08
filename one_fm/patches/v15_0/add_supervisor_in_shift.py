import frappe

def execute():
    shifts = frappe.get_all("Operations Shift",{"status": "Active"})
    for shift in shifts:
        operations_shift = frappe.get_doc("Operations Shift", shift.name)
        if not operations_shift.shift_supervisor:
            operations_shift.append("shift_supervisor",{
                "supervisor": operations_shift.supervisor,
                "supervisor_name": operations_shift.supervisor_name
            })
            operations_shift.save(ignore_permissions=True)
