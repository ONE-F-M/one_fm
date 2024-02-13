import frappe

def execute():
    """
    Fetch and split "employee_name_in_arabic" into ("first_name_in_arabic", "second_name_in_arabic", "third_name_in_arabic", "forth_name_in_arabic", "last_name_in_arabic")
    """

    onboard_employees = frappe.get_all("Onboard Employee", fields=['name', 'employee_name_in_arabic'])

    if onboard_employees:
        for job_offer in onboard_employees:
            try:
                splitted_arabic_name = job_offer.employee_name_in_arabic.split()
                first_arabic_name = splitted_arabic_name[0]
                last_arabic_name = splitted_arabic_name[-1] if len(splitted_arabic_name) > 1 else ""
                second_arabic_name = splitted_arabic_name[1] if len(splitted_arabic_name) > 2 else ""
                third_arabic_name = splitted_arabic_name[2] if len(splitted_arabic_name) > 3 else ""
                forth_arabic_name = splitted_arabic_name[3] if len(splitted_arabic_name) > 4 else ""

                frappe.db.set_value("Onboard Employee", job_offer.name, 'first_name_in_arabic', first_arabic_name)
                frappe.db.set_value("Onboard Employee", job_offer.name, 'second_name_in_arabic', second_arabic_name)
                frappe.db.set_value("Onboard Employee", job_offer.name, 'third_name_in_arabic', third_arabic_name)
                frappe.db.set_value("Onboard Employee", job_offer.name, 'forth_name_in_arabic', forth_arabic_name)
                frappe.db.set_value("Onboard Employee", job_offer.name, 'last_name_in_arabic', last_arabic_name)
            except Exception as e:
                frappe.log_error(title=f"Error while splitting arabic name for {job_offer.name}", message=str(e))
                continue

        frappe.db.commit()
