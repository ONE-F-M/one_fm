import frappe
from frappe import _

@frappe.whitelist()
def fetch_salary_component(salary_structure, base=False):
    """This Function Fetches the Salary Components from a given Salary Structure.
        It further calculates the amount of each component if the component amount is based on
        a formula. In that case, it checks if the base amount exists. If notify it throws an error.

        If the amount of components is not based on a formula, the item just fetches the given amount.

        This action is taken before saving the file.
    Args:
        doc ([doctype]): Salary Structure Assignment.

    Result:
        Appends the "Salary Structure Component" Table with calculated amount.
    """
    component = []
    salary_structure_components = frappe.get_doc("Salary Structure",{"name":salary_structure},['*'])
    if salary_structure_components.earnings:
        for item in salary_structure_components.earnings:
            if item.amount_based_on_formula == 1 and item.formula:
                if not base:
                    frappe.throw("Please Enter Base Amount!!")
                else:
                    formula = item.formula
                    percent = formula.split("*")[1]
                    amount = int(base)*float(percent)
                    if amount != 0 :
                        component.append({"salary_component":item.salary_component,"amount":amount})
            else:
                if item.amount != 0:
                    component.append({"salary_component":item.salary_component,"amount":item.amount})
    return component

def set_salary_components_details_to_salary_structure_assignment(doc, method):
	if doc.salary_structure:
		components = fetch_salary_component(doc.salary_structure, doc.base)
		if components:
			doc.set('salary_structure_components', [])
			for component in components:
				salary_structure_component = doc.append('salary_structure_components')
				salary_structure_component.salary_component = component['salary_component']
				salary_structure_component.amount = component['amount']

def calculate_indemnity_amount(doc, method):
    """This function calculates the Indemnity Amount considering the salary component is "included in indemnity"

    This action takes place on submit.
    Args:
        doc ([doctype]): Salary Structure Assignment

    result: Input calculated "indemnity_amount"
    """
    indemnity_amount = 0
    components = doc.salary_structure_components
    for component in components:
        if component.include_in_indemnity == 1 :
            indemnity_amount = component.amount + indemnity_amount
    doc.indemnity_amount = indemnity_amount
    frappe.db.commit()

def calculate_leave_allocation_amount(doc, method):
    """This function calculates the Leave Allocation Amount considering the salary component is "included in leave allocation"

    This action takes place on submit.
    Args:
        doc ([doctype]): Salary Structure Assignment

    result: Input calculated "leave_allocation_amount"
    """
    leave_allocation_amount = 0
    components = doc.salary_structure_components
    for component in components:
        if component.include_in_leave_allocation == 1 :
            leave_allocation_amount = component.amount + leave_allocation_amount
    doc.leave_allocation_amount = leave_allocation_amount
    frappe.db.commit()
