import frappe, calendar
from frappe.utils import (
    nowdate, getdate, add_days
)


def employee_schedule_monthly():
    """
        This method auto schedule employees every first day of the month.
    """
    settings = frappe.get_doc('Employee Schedule Setting')
    if settings.active:
        exempt_projects = [row.project for row in settings.exempt_projects]
        projects = frappe.db.get_list(
            'Project',
            filters={'name':['NOT IN', exempt_projects], 'exempt_auto_employee_schedule':0})
        # get dates
        today = getdate()
        last_month_date = add_days(today, -1)
        last_day_of_current_month = calendar.monthrange(today.year, today.month)[1]
        for p in projects:
            employee_schedule = frappe.db.get_list("Employee Schedule", filters={'date':str(last_month_date), 'project':p.name})
            for es in employee_schedule:
                for i in range(1, last_day_of_current_month):
                    try:
                        es = frappe.get_doc("Employee Schedule", es.name)
                        es.creation = ''
                        es.modified_by = ''
                        es.owner = ''
                        es.roster_type = 'Basic'
                        es.employee_availability = 'Working'
                        es.date = f'2022-06-{i}'
                        es.insert()
                    except Exception as e:
                        print(e)
                frappe.db.commit()
