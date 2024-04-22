import frappe
import time

def execute():
    data = frappe.get_all("Employee", filters={"name": ["like", "HR-EMP%"], "employee_id": ["is", "set"]}, fields=["name", "employee_number"])

    # Get total no of employees and convert into batches of 5
    for employee_batches in batches(data, 5):
        start = time.time()
        # Rename a batch of 5 employees as background job
        frappe.enqueue(patch_employee_naming_series, employee_batches=employee_batches)
        end = time.time()
        print("TIME", end-start)

def patch_employee_naming_series(employee_batches):
    for employee in employee_batches:
        print(employee)
        if employee.employee_number:
            frappe.rename_doc("Employee", employee.name, employee.employee_number)
    frappe.db.commit()

# Generator function to create batches for 5 employees
def batches(employees, batch_size=1):
    total = len(employees)
    for idx in range(0, total, batch_size):
        yield employees[idx:min(idx + batch_size, total)]