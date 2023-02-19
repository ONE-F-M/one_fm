import frappe 

def comment_timesheet_in_hrms():
    """
        HRMS overrides Timesheet, this affects restricts the overide in ONE_FM
    """
    app_path = frappe.utils.get_bench_path()+"/apps/hrms/hrms/"
    f = open(app_path+"hooks.py",'r')
    filedata = f.read()
    f.close()

    if not filedata.find('#"Timesheet": "hrms.overrides.employee_timesheet.EmployeeTimesheet",') > 0:
        newdata = filedata.replace(
                '"Timesheet": "hrms.overrides.employee_timesheet.EmployeeTimesheet",',
                '#"Timesheet": "hrms.overrides.employee_timesheet.EmployeeTimesheet",'
        )

        f = open(app_path+"hooks.py",'w')
        f.write(newdata)
        f.close()

