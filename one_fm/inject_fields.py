import frappe
import json
import os

def inject_missing_fields():
    from one_fm.custom.custom_field.employee import get_employee_custom_fields
    
    code_fields = [f.get("fieldname") for f in get_employee_custom_fields().get("Employee", [])]
    db_fields = frappe.get_all("Custom Field", filters={"dt": "Employee"}, fields=["*"])
    
    missing_fields = [f for f in db_fields if f.get("fieldname") not in code_fields and f.get("fieldname") not in ['column_break_heye', 'one_fm_fourth_name_in_arabic', 'one_fm_fourth_name']]
    
    if not missing_fields:
        print("No missing fields.")
        return
        
    print(f"Injecting {len(missing_fields)} fields...")
    
    # Read the file
    file_path = "/Users/kevinmakora/.gemini/antigravity/scratch/frappe-bench/apps/one_fm/one_fm/custom/custom_field/employee.py"
    with open(file_path, "r") as f:
        content = f.read()
        
    # Build dictionary string
    fields_str = ""
    for field in missing_fields:
        field_dict = {}
        for key, value in field.items():
            if key in ["name", "owner", "creation", "modified", "modified_by", "_user_tags", "_comments", "_assign", "_liked_by", "docstatus", "parent", "parenttype", "parentfield", "idx"]:
                continue
            if value is not None and value != "" and value != 0:
                field_dict[key] = value
                
        # Format the dict as a python string
        dict_str = ",\n\t\t\t".join([f'"{k}": {repr(v)}' for k, v in field_dict.items()])
        fields_str += f",\n\t\t\t{{\n\t\t\t\t{dict_str}\n\t\t\t}}"
        
    # Inject it right before the last closing brackets
    target = "\n\t\t]\n\t}"
    if target in content:
        content = content.replace(target, fields_str + target)
        with open(file_path, "w") as f:
            f.write(content)
        print("Successfully injected!")
    else:
        print("Target closing brackets not found!")
