from erpnext.hr.doctype.employee_transfer.employee_transfer import *

class EmployeeTransferOverride(EmployeeTransfer):

    def on_submit(self):
        employee = frappe.get_doc("Employee", self.employee)
        if self.create_new_employee_id:
            new_employee = frappe.copy_doc(employee)
            new_employee.name = None
            new_employee.employee_number = None
            new_employee = update_employee_work_history(
                new_employee, self.transfer_details, date=self.transfer_date
            )
            if self.new_company and self.company != self.new_company:
                new_employee.internal_work_history = []
                new_employee.date_of_joining = self.transfer_date
                new_employee.company = self.new_company
            # move user_id to new employee before insert
            if employee.user_id and not self.validate_user_in_details():
                new_employee.user_id = employee.user_id
                employee.db_set("user_id", "")
            new_employee.insert()
            self.db_set("new_employee_id", new_employee.name)
            # relieve the old employee
            employee.db_set("relieving_date", self.transfer_date)
            employee.db_set("status", "Left")
        else:
            employee = update_employee_work_history(
                employee, self.transfer_details, date=self.transfer_date
            )
            if self.new_company and self.company != self.new_company:
                employee.company = self.new_company
                employee.date_of_joining = self.transfer_date
            employee.save()

        # update employee schedule
        if self.is_project_transfer and self.update_employee_schedule:
            filters = {
                'employee': self.employee,
                'date': ['>=', self.transfer_date]
            }
            if self.end_date:
                filters['date'] = ['BETWEEN', (self.transfer_date, self.end_date)]
            employee_schedules = frappe.db.get_list('Employee Schedule', filters=filters)
            if employee_schedules:
                frappe.enqueue(update_employee_schedules, **{'employee_schedules': employee_schedules,
                    'shift': self.new_shift, 'site': self.new_site, 'project': self.new_project})


def update_employee_schedules(employee_schedules, shift, site, project):
    try:
        for row in employee_schedules:
            operations_shift = frappe.get_doc('Operations Shift', shift)
            schedule = frappe.get_doc('Employee Schedule', row.name)
            schedule.db_set('shift', shift)
            schedule.db_set('site', site)
            schedule.db_set('project', project)
            schedule.db_set('shift_type', operations_shift.shift_type)
    except Exception as e:
        frappe.log_error(e, "Employee Transfer")