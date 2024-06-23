from calendar import monthrange
from datetime import date

import frappe
from frappe import _
from frappe.utils import getdate

from one_fm.api.v1.utils import response


def get_context(context):
    print(frappe.form_dict.id)
    customer = frappe.get_doc("Client", {"route_hash": frappe.form_dict.id})
    context.doc = customer
    context.parents = [{'route': customer.route, 'title': _(customer.customer_name)}]


@frappe.whitelist(allow_guest=1)
def get_client_roster(route_hash: str = None):
    try:
        route_hash = frappe.form_dict.id if not route_hash else route_hash
        year, month, today = getdate().year, getdate().month, getdate().day
        num_days = monthrange(year, month)[1]
        dates = [str(date(year, month, day)) for day in range(1, num_days + 1)]
        columns = ["Employee Name", "Job Title"] + dates
        customer_name = frappe.db.get_value("Client", {"route_hash": route_hash}, "customer")
        if not customer_name:
            return response("Bad Request", 400, None, "Customer Does not exist")
        query = f"""
                SELECT 
                    es.employee,
                    es.employee_name, 
                    es.employee_availability, 
                    es.date, 
                    es.site, 
                    opr.post_name
                FROM 
                    `tabEmployee Schedule` as es
                JOIN 
                    `tabOperations Role` as opr
                ON 
                    es.operations_role = opr.name
                WHERE 
                    es.site IN (
                        SELECT name 
                        FROM `tabOperations Site`
                        WHERE project IN (
                            SELECT name 
                            FROM `tabProject`
                            WHERE customer = %s
                        )
                    )
                AND 
                    es.date IN %s
            """

        schedules = frappe.db.sql(query, (customer_name, tuple(dates)), as_dict=True)
        data_dict = dict()
        for obj in schedules:
            if data_dict.get(obj.employee):
                data_dict.get(obj.employee).get("schedule").update({str(obj.date): obj.employee_availability})
            else:
                data_dict.update({
                    obj.employee: {"job_title": obj.post_name,
                                "schedule": {
                                    str(obj.date): obj.employee_availability
                                },
                                "employee_name": obj.employee_name
                                }
                })

        data = list()
        for key, value in data_dict.items():
            to_be_appended_data = [value.get("employee_name"), value.get("job_title"), ] + [
                value.get("schedule").get(the_date) or "Day Off" for the_date in dates]
            
            data.append(to_be_appended_data)
        
        return response("Operation Successful", 200, dict(columns=columns, data=data))
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error while generating client roster")
        return response("Operation Successful", 500, None, str(e))
