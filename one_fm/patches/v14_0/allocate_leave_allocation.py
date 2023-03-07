import frappe
from frappe.utils import getdate
from one_fm.hiring.utils import grant_leave_alloc_for_employee

def execute():
    try:
        """
            Assign Leave Allocations to employees with no leave allocation
        """
        leave_allocation_query = frappe.db.get_list("Leave Allocation", fields=["employee"])
        leave_allocation_list = []
        for i in leave_allocation_query:
            if not i.employee in leave_allocation_list:leave_allocation_list.append(i.employee)
        
        leave_policy_query = frappe.db.sql(f"""
            SELECT lp.name, e.name as employee, e.employee_name, e.date_of_joining, lp.leave_policy, lp.effective_from, 
            lp.effective_to 
            FROM `tabLeave Policy Assignment` lp LEFT JOIN `tabEmployee` e ON e.name=lp.employee
            WHERE e.status='Active' AND lp.employee NOT IN {str(tuple(leave_allocation_list)).replace(',)', ')')}
        """, as_dict=1)

        #reset leaves_allocated in leave policy assignment to 0 for employees with no leave allocation
        frappe.db.sql(f"""
            UPDATE `tabLeave Policy Assignment` SET leaves_allocated=0
            WHERE name IN {str(tuple([i.name for i in leave_policy_query])).replace(',)', ')')}
        """)
        frappe.db.commit()

        # assign leave allocation
        for i in leave_policy_query:
            print(f"Allocating leave to {i.employee} - {i.employee_name}")
            doc = frappe.get_doc("Leave Policy Assignment", i.name)
            grant_leave_alloc_for_employee(doc)
    except:
        pass