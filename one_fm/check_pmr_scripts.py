import frappe

def check_scripts():
    scripts = frappe.get_all("Client Script", filters={'dt': 'Project Manpower Request', 'enabled': 1}, fields=['name', 'script'])
    if not scripts:
        print("No active client scripts for PMR.")
    for s in scripts:
        print(f"--- Script: {s.name} ---")
        if 'Canceled' in s.script or 'Cancelled' in s.script or 'action_type' in s.script:
            print("Found reference to Canceled/action_type!")
        else:
            print("No reference found in script.")

def run():
    check_scripts()
