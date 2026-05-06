import frappe

def run():
    shifts = frappe.get_all("Operations Shift", fields=["name", "site", "start_time", "end_time"])
    for s in shifts:
        print(f"{s.name}: {s.site} | {s.start_time} -> {s.end_time}")
