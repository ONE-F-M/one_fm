import frappe

def run():
    allocations = frappe.get_all("Transport Shift Allocation", fields=["name", "shift_name", "shift_start_time", "shift_end_time", "stop_location", "accommodation"], filters={"docstatus": 1})
    for a in allocations:
        print(f"{a.name}: {a.shift_name} | {a.shift_start_time} -> {a.shift_end_time} | {a.stop_location} | {a.accommodation}")
