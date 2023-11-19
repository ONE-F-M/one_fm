import frappe

def execute():
    payroll_list = frappe.get_list("Payroll Entry",{'status':"Submitted"})
    
    for doc in payroll_list:
        payroll_entry = frappe.get_doc("Payroll Entry", doc)
        salary_count = frappe.db.sql_list(
            f"""
            select Count(distinct employee) as salary_count from `tabSalary Slip`
            where docstatus!= 2 
                and company = '{payroll_entry.company}'
                and start_date = '{payroll_entry.start_date}'
                and end_date = '{payroll_entry.end_date}'
            """, as_dict=1)
        if salary_count[0] != payroll_entry.number_of_employees:
            payroll_entry.db_set({"status": "Pending Salary Slip", "error_message": "", "salary_slips_created": 0})
        else:
            if payroll_entry.salary_slips_created == 0:
                payroll_entry.db_set({"salary_slips_created": 1})
    frappe.db.commit()