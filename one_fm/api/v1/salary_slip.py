import frappe
from frappe import _
from one_fm.api.v1.utils import response

@frappe.whitelist()
def get_salary_slip_list(employee_id: str = None) -> dict:
    """This method returns the list of salary slips for a given employee.

    Args:
        employee_id (str): employee id of user.

    Returns:
         dict: {
			message (str): Brief message indicating the response,
			status_code (int): Status code of response.
			data (List[dict]): List of salary slip objects -> 
            [
                {
                    name,
                    start_date,
                    end_date,
                    status,
                    total_working_days,
                },
            ].
			error (str): Any error handled.
        }
    """
    if not employee_id:
        return response("Bad Request", 400, None, "employee_id required.")

    if not isinstance(employee_id, str):
        return response("Bad Request", 400, None, "employee_id must be of type str.")
    
    try:
        employee = frappe.db.get_value("Employee", {"employee_id": employee_id})

        if not employee:
            return response("Resource not found", 404, None, "No employee found with {employee_id}".format(employee_id=employee_id))
        
        salary_list = frappe.get_all("Salary Slip", filters={'employee': employee}, fields=["name", "start_date", "end_date", "status", "total_working_days"])
        
        if not salary_list or len(salary_list) == 0:
            return response("Resource not found", 404, None, "No salary slips found for user {employee_id}".format(employee_id=employee_id))
        
        return response("Success", 200, []) #salary_list)
    
    except Exception as error:
        return response("Internal Server Error", 500, None, error)

@frappe.whitelist()
def salary_slip_details(salary_slip_id: str = None) -> dict:
    """This method gets the details of a salary slip.

    Args:
        salary_slip_id (str, optional): [description]. Defaults to None.

    Returns:
        dict: {
            message (str): Brief message indicating the response,
			status_code (int): Status code of response.
            data (dict): salary slip object.
            error (str): Any error handled.
        }
    """
    if not salary_slip_id:
        return response("Bad Request", 400, None, "salary_slip_id required.")

    if not isinstance(salary_slip_id, str):
        return response("Bad Request", 400, None, "salary_slip_id must be of type str.")
    
    try:
        salary_slip_doc = frappe.get_doc("Salary Slip", salary_slip_id)
        
        if not salary_slip_doc:
            return response("Resource not found", 404, None, "No record found with id {salary_slip_id}".format(salary_slip_id=salary_slip_id))
        
        return response("Success", 200, salary_slip_doc.as_dict())
    
    except Exception as error:
        return response("Internal Server Error", 500, None, error)
