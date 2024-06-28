import frappe
from calendar import monthrange
from frappe import _
from frappe.utils import cint


def get_context(context):
    id = frappe.form_dict.id
    customer = frappe.db.get_value("Client", id, ["route", "customer_name"], as_dict=1)
    context.parents = [{'route': customer.route , 'title': _(customer.customer_name) }]


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_monthly_data(id : str, month : str | None, year : str | None):
    id = frappe.form_dict.id
    customer = frappe.db.get_value("Client", id, "customer")
    customer_project = frappe.db.get_value("Project", {"customer": customer}, "name")

    if not customer or not customer_project:
        return {
            "columns": [],
            "data": []
        }    

    employees = frappe.db.get_list("Employee", {"project": customer_project}, ["name", "employee_name"], ignore_permissions=True)
    filters = frappe._dict({
        "month": month,
        "year": year,
        "company": "One Facilities Management",
    })

    total_days = get_total_days_in_month(filters)
    data = []
    for employee in employees:
        data.append(get_attendance_data_map(employee.name, employee.employee_name, filters, total_days))
    
    return {
        "columns": ["Employee Name", "Designation", "Present days", "Absent days", "Day Off", "Leave", "Unmarked days"],
        "data": data
    }    



def get_attendance_data_map(employee, full_name, filters, total_days):
    """
        Format -> ["John Doe", "Supervisor", 20, 2, 5, 4, 0]
    """
    data = frappe.db.sql("""
        SELECT 
            count(distinct att.attendance_date) as days, att.employee, att.status, op.post_name as designation 
        FROM `tabAttendance` att
        LEFT JOIN `tabOperations Role` op
        ON att.operations_role =op.name
        WHERE
            att.docstatus=1
        AND att.employee=%s
        AND EXTRACT(MONTH FROM att.attendance_date)=%s
        AND EXTRACT(YEAR FROM att.attendance_date)=%s
        GROUP BY att.status
        ORDER BY att.employee_name
    """,(employee, filters.month, filters.year), as_dict=1)

    employee_details = [full_name]
    employee_details.insert(1, next((attendance["designation"] for attendance in data if attendance["designation"]), "N-A"))
    
    att_map = {
        "Present": 0,
        "Absent": 0,
        "Day Off": 0,
        "On Leave": 0,
        "Unmarked": 0,
    }
    
    if data:
        for attendance_data in data:
            if attendance_data.status == "Present":
                att_map["Present"] = attendance_data.days
                total_days = total_days - attendance_data.days
            elif attendance_data.status == "Absent":
                att_map["Absent"] = attendance_data.days
                total_days = total_days - attendance_data.days
            elif attendance_data.status == "Day Off":
                att_map["Day Off"] = attendance_data.days
                total_days = total_days - attendance_data.days
            elif attendance_data.status == "On Leave":
                att_map["On Leave"] = attendance_data.days
                total_days = total_days - attendance_data.days
            att_map["Unmarked"] = total_days

        # Present - Index 2, Absent - Index 3, Day Off - Index 4, Leave - Index 5, Unmarked days - Index 6
        employee_details = employee_details + [att_map["Present"], att_map["Absent"], att_map["Day Off"], att_map["On Leave"], att_map["Unmarked"]]
    else:
        employee_details = employee_details + [att_map["Present"], att_map["Absent"], att_map["Day Off"], att_map["On Leave"], total_days]

    return employee_details

def get_total_days_in_month(filters):
	return monthrange(cint(filters.year), cint(filters.month))[1]
