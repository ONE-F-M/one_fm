import frappe

def check_versions():
    versions = frappe.get_all("Version", filters={"docname": "ACP002"}, fields=["name", "data"])
    for v in versions:
        import json
        data = json.loads(v.data)
        if "changed" in data:
            print(f"Version {v.name}: Changed fields: {data['changed']}")
        if "row_changed" in data:
            print(f"Version {v.name}: Row changed: {data['row_changed']}")
        if "added" in data:
            print(f"Version {v.name}: Added: {data['added']}")
        if "removed" in data:
            print(f"Version {v.name}: Removed: {len(data['removed'])} rows")
