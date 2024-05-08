import frappe
from frappe.utils import get_url
from one_fm.qr_code_generator import get_qr_code

def execute():
    employee_ids = frappe.get_all("Employee ID", fields=['name', 'employee'])
    
    for employee_id in employee_ids:
        try:
            # Generate the new QR code link
            new_qr_code_link = get_qr_code(get_url(f"/employee-info/{employee_id.employee}"))

            frappe.db.set_value("Employee ID", employee_id.name, 'qr_code_image_link', new_qr_code_link)
        
        except Exception as e:
            frappe.log_error(f"Failed to update QR code for Employee ID {employee_id.name}: {str(e)}")
            
        
        frappe.db.commit()

