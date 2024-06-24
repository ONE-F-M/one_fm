from datetime import timedelta
import pandas as pd
from itertools import groupby
import frappe
from frappe import _
from frappe.query_builder.functions import Count, Extract, Sum
from frappe.utils import getdate, add_days, cstr

def get_context(context):
    id = frappe.form_dict.id
    customer = frappe.db.get_value("Client", id, ["route", "customer_name"], as_dict=1)
    context.parents = [{'route': customer.route , 'title': _(customer.customer_name) }]


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_weekly_data(id : str):
    id = frappe.form_dict.id
    customer = frappe.db.get_value("Client", id, "customer")
    customer_project = frappe.db.get_value("Project", {"customer": customer}, "name")

    if not customer or not customer_project:
        return {
            "columns": [],
            "data": []
        }    
        
    start_date = add_days(getdate(), -7)
    end_date = getdate()
    employees = frappe.db.get_list("Employee", {"project": customer_project}, ["name", "designation"], ignore_permissions=True)
    dates = get_column_dates(start_date, end_date)

    # Columns for datatable
    data_columns = ["Employee Name", "Designation"]
    dates_column = [date.strftime("%d-%m-%Y") for date in dates] 
    columns = data_columns + dates_column

    # Data for datatable
    Attendance = frappe.qb.DocType("Attendance")
    Employee = frappe.qb.DocType("Employee")
    query = (
        frappe.qb.from_(Attendance)
        .left_join(Employee)
        .on(Attendance.employee == Employee.name)
        .select(
            Attendance.employee,
            Attendance.employee_name,
            Attendance.attendance_date,
            Attendance.status,
            Employee.designation
        )
        .where(
            (Attendance.docstatus == 1)         
            & (Attendance.employee.isin([employee.name for employee in employees]))
            & (Attendance.attendance_date[start_date:end_date])
        )
    )

    query = query.orderby(Attendance.employee, Attendance.attendance_date)

    attendance_list = query.run(as_dict=1)
 
    data = generate_data_map(dates, attendance_list)
    return {
        "columns": columns,
        "data": data
    }    



def generate_data_map(dates, attendance_list):
    """
        Format => [
            ["John Doe", "Supervisor", "Present", "Absent", "Present", "Absent", "Present", "Absent", "Day Off"],
            ["Jane Doe", "Manager", "Present", "Absent", "Present", "Absent", "Present", "Absent", "Day Off"]   
        ]
    """
    data_map = []

    for key, value in groupby(attendance_list, key=lambda k: (k['employee'], k['employee_name'], k['designation'])):
        row = []
        # Employee Name
        row.append(key[1])
        # Designation
        row.append(key[2])

        for date in dates:
            # If attendance for specific date is not present, then assign Not Available as default status
            status = next((attendance.status for attendance in list(value) if attendance['attendance_date'] == date), "Not Available")
            row.append(status)

        data_map.append(row)
    return data_map


def get_column_dates(start_date, end_date):
    # Returns list of datetime.date objects from start to end date
    return [(start_date+timedelta(days=x)) for x in range((end_date-start_date).days)]