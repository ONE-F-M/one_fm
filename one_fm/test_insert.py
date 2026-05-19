import frappe

def run():
    frappe.set_user("k.wanyama@one-fm.com")

    doc = frappe.get_doc({
        "doctype": "Employee Resignation",
        "resignation_initiation_date": "2026-05-01",
        "relieving_date": "2026-05-31",
        "employees": [
            {
                "employee": "HR-EMP-03333"
            }
        ]
    })

    try:
        doc.insert(ignore_permissions=False)
        print("SUCCESS")
    except Exception as e:
        import traceback
        traceback.print_exc()
