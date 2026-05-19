import frappe

def check_missing_fields():
    from one_fm.custom.custom_field.employee import get_employee_custom_fields
    
    code_fields = [f.get("fieldname") for f in get_employee_custom_fields().get("Employee", [])]
    db_fields = frappe.get_all("Custom Field", filters={"dt": "Employee"}, pluck="fieldname")
    
    missing_in_code = [f for f in db_fields if f not in code_fields]
    
    print("--- MISSING CUSTOM FIELDS ---")
    for f in missing_in_code:
        print(f)
    print("-----------------------------")
